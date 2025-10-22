from fastapi import APIRouter
from loguru import logger

from api.schemas import QueueStatsResponse
from task_queue.task_queue import TaskQueue
from task_queue.redis_client import RedisClient

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("/stats", response_model=QueueStatsResponse)
async def get_queue_stats():
    """
    Get current queue statistics
    """
    stats = await TaskQueue.get_queue_stats()
    
    return QueueStatsResponse(
        queue_name=stats["queue_name"],
        queue_length=stats["queue_length"],
        total_connections=stats["total_connections"],
        total_commands=stats["total_commands"],
    )


@router.get("/peek")
async def peek_next_task():
    """
    Peek at the next task in the queue without removing it
    """
    task = await TaskQueue.peek_next_task()
    
    if not task:
        return {
            "message": "Queue is empty",
            "task": None,
        }
    
    return {
        "message": "Next task in queue",
        "task": task,
    }


@router.post("/clear")
async def clear_queue():
    """
    Clear all tasks from the queue (use with caution!)
    """
    count = await TaskQueue.clear_queue()
    
    logger.warning(f"Queue cleared: {count} tasks removed")
    
    return {
        "status": "success",
        "message": f"Queue cleared, {count} tasks removed",
        "count": count,
    }


@router.get("/health")
async def check_queue_health():
    """
    Check if Redis/queue is accessible
    """
    is_healthy = await RedisClient.ping()
    
    if is_healthy:
        queue_length = await TaskQueue.get_queue_length()
        return {
            "status": "healthy",
            "redis_connected": True,
            "queue_length": queue_length,
        }
    else:
        return {
            "status": "unhealthy",
            "redis_connected": False,
            "error": "Cannot connect to Redis",
        }

