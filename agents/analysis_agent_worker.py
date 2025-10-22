import asyncio
import uuid
from loguru import logger

from agents.analysis_agent import AnalysisAgent
from task_queue.task_queue import TaskQueue
from task_queue.redis_client import RedisClient
from db.database import get_db
from db.repository import ArticleRepository


class AnalysisAgentWorker:
    """
    Background worker that processes article analysis tasks using Analysis Agent
    """
    
    def __init__(self):
        self.analysis_agent = AnalysisAgent()
        self.running = False
    
    async def process_task(self, task: dict) -> bool:
        """
        Process a single article analysis task using Analysis Agent
        
        Args:
            task: Task dictionary from queue
            
        Returns:
            True if processing succeeded, False otherwise
        """
        task_id = task.get("task_id")
        article_id_str = task.get("article_id")
        doi = task.get("doi")
        title = task.get("title", "Unknown")
        abstract = task.get("abstract", "")
        pdf_url = task.get("pdf_url")
        
        logger.info(f"Processing task {task_id} for article: {title[:50]}...")
        
        if not article_id_str:
            logger.error(f"Task {task_id} missing article_id")
            return False
        
        try:
            article_id = uuid.UUID(article_id_str)
        except ValueError as e:
            logger.error(f"Invalid article_id format: {article_id_str}")
            return False
        
        try:
            # Verify article exists in database
            async with get_db() as db:
                article = await ArticleRepository.get_by_id(db, article_id)
                if not article:
                    logger.error(f"Article {article_id} not found in database")
                    return False
            
            # Run Analysis Agent
            logger.info(f"Starting Analysis Agent for article {article_id}")
            result = await self.analysis_agent.analyze_article(
                article_id=article_id,
                doi=doi,
                title=title,
                abstract=abstract,
                pdf_url=pdf_url,
            )
            
            if result.get("status") == "success":
                logger.info(
                    f"✓ Successfully analyzed article {article_id}\n"
                    f"  Actuality Score: {result.get('actuality_score', 'N/A')}\n"
                    f"  Controversy Level: {result.get('controversy_level', 'N/A')}\n"
                    f"  Theories Extracted: {result.get('theories_extracted', 0)}\n"
                    f"  Cost: ${result.get('cost', 0):.6f}"
                )
                return True
            else:
                logger.error(f"Analysis failed for article {article_id}: {result.get('error')}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to process task {task_id}: {e}", exc_info=True)
            return False
    
    async def run(self):
        """
        Main worker loop - continuously process tasks from queue
        """
        self.running = True
        logger.info("Analysis Agent Worker started, waiting for tasks...")
        
        # Check Redis connection
        if not await RedisClient.ping():
            logger.error("Redis connection failed, worker cannot start")
            return
        
        processed_count = 0
        error_count = 0
        
        while self.running:
            try:
                # Get next task from queue (blocking with timeout)
                task = await TaskQueue.dequeue_article_task()
                
                if task:
                    success = await self.process_task(task)
                    
                    if success:
                        processed_count += 1
                    else:
                        error_count += 1
                    
                    logger.info(
                        f"Worker stats: {processed_count} processed, {error_count} errors"
                    )
                else:
                    # No task available, log idle status
                    queue_length = await TaskQueue.get_queue_length()
                    if queue_length == 0:
                        logger.debug("Queue is empty, waiting for tasks...")
                
            except asyncio.CancelledError:
                logger.info("Worker received cancellation signal")
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                # Wait before retrying to avoid tight loop on persistent errors
                await asyncio.sleep(5)
        
        logger.info(
            f"Analysis Agent Worker stopped. Total processed: {processed_count}, "
            f"errors: {error_count}"
        )
    
    def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info("Stopping Analysis Agent Worker...")


async def start_worker():
    """
    Start the analysis agent worker
    Entry point for CLI
    """
    worker = AnalysisAgentWorker()
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        worker.stop()
    finally:
        await RedisClient.close()


if __name__ == "__main__":
    # Run worker directly
    asyncio.run(start_worker())

