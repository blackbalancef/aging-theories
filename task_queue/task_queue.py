import json
import uuid
from typing import Optional
from loguru import logger

from config import config
from task_queue.redis_client import RedisClient


class TaskQueue:
    """
    Redis-based task queue for article analysis
    """
    
    @staticmethod
    async def enqueue_article_task(article_data: dict) -> str:
        """
        Add an article analysis task to the queue
        
        Args:
            article_data: Dictionary containing article information
                Required fields: article_id, doi, title
                Optional fields: pdf_url, full_text_url, abstract
        
        Returns:
            Task ID (string)
        """
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            **article_data
        }
        
        client = await RedisClient.get_client()
        
        # Add to queue using LPUSH (left push) - FIFO queue with RPOP
        await client.lpush(config.redis_queue_name, json.dumps(task))
        
        logger.info(
            f"Enqueued task {task_id} for article: {article_data.get('title', 'Unknown')[:50]}"
        )
        
        return task_id
    
    @staticmethod
    async def dequeue_article_task() -> Optional[dict]:
        """
        Get the next article analysis task from the queue (blocking)
        
        Returns:
            Task dictionary or None if queue is empty
        """
        client = await RedisClient.get_client()
        
        # BRPOP blocks until an item is available (timeout in seconds)
        result = await client.brpop(config.redis_queue_name, timeout=config.worker_poll_interval)
        
        if result:
            queue_name, task_json = result
            task = json.loads(task_json)
            logger.info(f"Dequeued task {task.get('task_id')} for article: {task.get('title', 'Unknown')[:50]}")
            return task
        
        return None
    
    @staticmethod
    async def get_queue_length() -> int:
        """
        Get the current length of the queue
        
        Returns:
            Number of tasks in queue
        """
        client = await RedisClient.get_client()
        length = await client.llen(config.redis_queue_name)
        return length
    
    @staticmethod
    async def clear_queue() -> int:
        """
        Clear all tasks from the queue
        
        Returns:
            Number of tasks removed
        """
        client = await RedisClient.get_client()
        length = await client.llen(config.redis_queue_name)
        await client.delete(config.redis_queue_name)
        logger.warning(f"Cleared {length} tasks from queue")
        return length
    
    @staticmethod
    async def peek_next_task() -> Optional[dict]:
        """
        Peek at the next task without removing it
        
        Returns:
            Task dictionary or None if queue is empty
        """
        client = await RedisClient.get_client()
        
        # LINDEX gets element at index without removing it
        task_json = await client.lindex(config.redis_queue_name, -1)
        
        if task_json:
            task = json.loads(task_json)
            return task
        
        return None
    
    @staticmethod
    async def get_queue_stats() -> dict:
        """
        Get queue statistics
        
        Returns:
            Dictionary with queue stats
        """
        client = await RedisClient.get_client()
        
        queue_length = await client.llen(config.redis_queue_name)
        
        # Get Redis info
        info = await client.info('stats')
        
        return {
            "queue_name": config.redis_queue_name,
            "queue_length": queue_length,
            "total_connections": info.get('total_connections_received', 0),
            "total_commands": info.get('total_commands_processed', 0),
        }

