from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from db.database import init_db, close_db
from task_queue.redis_client import RedisClient
from api.routes import articles, discovery, sources, queue, costs, theories, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown
    """
    # Startup
    logger.info("Starting Aging Research Service API...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
    
    # Check Redis connection
    try:
        redis_available = await RedisClient.ping()
        if redis_available:
            logger.info("✓ Redis connection successful")
        else:
            logger.warning("✗ Redis connection failed")
    except Exception as e:
        logger.warning(f"✗ Redis connection error: {e}")
    
    logger.info("API is ready to accept requests")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Aging Research Service API...")
    
    try:
        await close_db()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"✗ Error closing database: {e}")
    
    try:
        await RedisClient.close()
        logger.info("✓ Redis connection closed")
    except Exception as e:
        logger.error(f"✗ Error closing Redis: {e}")
    
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Aging Research Service",
    description="Agentic service for discovering, classifying, and analyzing aging research papers",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(articles.router, prefix="/api")
app.include_router(discovery.router, prefix="/api")
app.include_router(theories.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(queue.router, prefix="/api")
app.include_router(costs.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": "Aging Research Service",
        "version": "1.0.0",
        "description": "Agentic service for discovering and analyzing aging research papers",
        "endpoints": {
            "articles": "/api/articles",
            "discovery": "/api/discover",
            "theories": "/api/theories",
            "sources": "/api/sources",
            "queue": "/api/queue",
            "costs": "/api/costs",
            "export": "/api/export",
            "docs": "/docs",
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    # Check database
    db_healthy = True
    try:
        from db.database import engine
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_healthy = False
    
    # Check Redis
    redis_healthy = await RedisClient.ping()
    
    status = "healthy" if (db_healthy and redis_healthy) else "degraded"
    
    return {
        "status": status,
        "database": "healthy" if db_healthy else "unhealthy",
        "redis": "healthy" if redis_healthy else "unhealthy",
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run with: python app.py
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

