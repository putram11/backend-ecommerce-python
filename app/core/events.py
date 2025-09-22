from fastapi import FastAPI
from loguru import logger
from .config import settings
from ..services.storage import storage_service


async def startup_event(app: FastAPI) -> None:
    """Initialize services on startup"""
    logger.info("Starting up backend ecommerce diecast...")
    
    # Ensure MinIO bucket exists
    try:
        await storage_service.create_bucket_if_not_exists(settings.MINIO_BUCKET)
        logger.info(f"MinIO bucket '{settings.MINIO_BUCKET}' initialized")
    except Exception as e:
        logger.error(f"Failed to initialize MinIO bucket: {e}")
        raise


async def shutdown_event(app: FastAPI) -> None:
    """Cleanup on shutdown"""
    logger.info("Shutting down backend ecommerce diecast...")
    # Close any remaining connections if needed