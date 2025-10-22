import asyncio
import uuid
from loguru import logger

from db.database import get_db
from db.repository import ArticleRepository, AnalysisRepository
from task_queue.task_queue import TaskQueue
from task_queue.redis_client import RedisClient
from services.pdf_parser import PDFParser
from services.analysis_service import AnalysisService
from services.theory_classification_service import TheoryClassificationService
from config import config


class AnalysisWorker:
    """
    Background worker that continuously processes article analysis tasks from Redis queue
    """
    
    def __init__(self):
        self.analysis_service = AnalysisService()
        self.theory_service = TheoryClassificationService()
        self.running = False
    
    async def process_task(self, task: dict) -> bool:
        """
        Process a single article analysis task
        
        Args:
            task: Task dictionary from queue
            
        Returns:
            True if processing succeeded, False otherwise
        """
        task_id = task.get("task_id")
        article_id_str = task.get("article_id")
        doi = task.get("doi")
        title = task.get("title", "Unknown")
        pdf_url = task.get("pdf_url")
        abstract = task.get("abstract", "")
        
        logger.info(f"🔄 Processing task {task_id} for article: {title[:50]}...")
        
        if not article_id_str:
            logger.error(f"❌ Task {task_id} missing required field: article_id")
            return False
        
        try:
            article_id = uuid.UUID(article_id_str)
        except ValueError as e:
            logger.error(f"Invalid article_id format: {article_id_str}")
            return False
        
        try:
            pdf_path = None
            full_text = None
            
            # Step 1: Get full text (from PDF or use abstract)
            if pdf_url:
                logger.info(f"📥 Step 1/4: Downloading PDF from: {pdf_url}")
                try:
                    full_text, pdf_path = await PDFParser.download_and_parse(
                        pdf_url,
                        filename=f"{doi.replace('/', '_')}.pdf" if doi else None
                    )
                    
                    if not full_text or len(full_text) < 100:
                        logger.warning(f"PDF text extraction yielded little content, using abstract instead")
                        full_text = abstract
                        if pdf_path:
                            await PDFParser.cleanup_pdf(pdf_path)
                            pdf_path = None
                except Exception as e:
                    logger.warning(f"PDF download/parse failed: {e}, using abstract instead")
                    full_text = abstract
            else:
                logger.info("ℹ️  Step 1/4: No PDF URL provided, using abstract for analysis")
                full_text = abstract
            
            if not full_text or len(full_text) < 50:
                logger.error(f"❌ Insufficient text content for analysis (length: {len(full_text) if full_text else 0})")
                return False
            
            logger.info(f"✓ Step 1/4 Complete: Text ready ({len(full_text)} chars)")
            
            # Step 2: Analyze paper using AI
            logger.info(f"🤖 Step 2/4: Starting AI analysis...")
            analysis_result, cost_info = await self.analysis_service.analyze_paper(
                article_title=title,
                full_text=full_text
            )
            
            logger.info(f"✓ Step 2/5 Complete: Analysis done")
            
            # Step 3: Save analysis to database
            logger.info(f"💾 Step 3/5: Saving analysis to database...")
            async with get_db() as db:
                # Verify article exists
                article = await ArticleRepository.get_by_id(db, article_id)
                if not article:
                    logger.error(f"❌ Article {article_id} not found in database")
                    if pdf_path:
                        await PDFParser.cleanup_pdf(pdf_path)
                    return False
                
                # Save analysis
                await AnalysisRepository.create(
                    db=db,
                    article_id=article_id,
                    analysis=analysis_result,
                    full_text=full_text,
                    cost_info=cost_info,
                )
            
            logger.info(f"✓ Step 3/5 Complete: Analysis saved to DB")
            
            # Step 4: Extract and classify aging theories
            logger.info(f"🧬 Step 4/5: Extracting and classifying aging theories...")
            try:
                theory_result = await self.theory_service.classify_article_theories(
                    article_id=article_id,
                    article_text=full_text,
                    article_title=title
                )
                logger.info(
                    f"✓ Step 4/5 Complete: {theory_result.get('linked_count', 0)} theories linked, "
                    f"{theory_result.get('new_theories_count', 0)} new theories created"
                )
            except Exception as e:
                logger.error(f"⚠️  Theory classification failed: {e}", exc_info=True)
                logger.info("Continuing without theory classification")
            
            # Step 5: Cleanup PDF file if it was downloaded
            logger.info(f"🗑️  Step 5/5: Cleanup...")
            if pdf_path:
                await PDFParser.cleanup_pdf(pdf_path)
                logger.info(f"✓ PDF cleaned up")
            
            logger.info(
                f"✅ Task {task_id} COMPLETED for article {article_id} "
                f"(cost: ${cost_info.total_cost_usd:.6f})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to process task {task_id}: {e}", exc_info=True)
            return False
    
    async def run(self):
        """
        Main worker loop - continuously process tasks from queue
        """
        self.running = True
        logger.info("🚀 Analysis worker started, waiting for tasks...")
        
        # Check Redis connection
        logger.info("🔍 Checking Redis connection...")
        if not await RedisClient.ping():
            logger.error("Redis connection failed, worker cannot start")
            return
        
        processed_count = 0
        error_count = 0
        
        logger.info("✓ Redis connected")
        
        while self.running:
            try:
                # Get next task from queue (blocking with timeout)
                logger.debug("⏳ Waiting for next task from Redis queue...")
                task = await TaskQueue.dequeue_article_task()
                
                if task:
                    task_id = task.get("task_id", "unknown")
                    logger.info(f"📦 Received task {task_id} from queue")
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
            f"Analysis worker stopped. Total processed: {processed_count}, "
            f"errors: {error_count}"
        )
    
    def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info("Stopping analysis worker...")


async def start_worker():
    """
    Start the analysis worker
    Entry point for CLI
    """
    worker = AnalysisWorker()
    
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

