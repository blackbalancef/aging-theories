import redis.asyncio as redis
from loguru import logger

from config import config


class RedisClient:
    """Redis client singleton for managing Redis connections"""
    
    _instance: redis.Redis = None
    
    @classmethod
    async def get_client(cls) -> redis.Redis:
        """
        Get or create Redis client instance
        
        Returns:
            Redis client instance
        """
        if cls._instance is None:
            cls._instance = await redis.from_url(
                config.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
            )
            logger.info(f"Redis client connected to {config.redis_url}")
        
        return cls._instance
    
    @classmethod
    async def close(cls):
        """Close Redis connection"""
        if cls._instance:
            await cls._instance.aclose()
            cls._instance = None
            logger.info("Redis client connection closed")
    
    @classmethod
    async def ping(cls) -> bool:
        """
        Check if Redis is available
        
        Returns:
            True if Redis is available, False otherwise
        """
        try:
            client = await cls.get_client()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

