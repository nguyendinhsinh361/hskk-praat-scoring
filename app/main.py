"""
HSKK Scoring System - Main Application
API-only application with Praat integration
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.dependencies import get_praat_service
from app.api.router import api_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}...")
    
    # Test Praat connection
    try:
        praat_service = get_praat_service()
        time.sleep(2)  # Wait for container startup
        
        if praat_service.test_connection():
            logger.info("✅ Praat container connected")
        else:
            logger.warning("⚠️ Praat container not ready - will retry on request")
    except Exception as e:
        logger.error(f"❌ Praat initialization failed: {e}")
    
    # Pre-load FunASR model (eliminates ~20s delay on first request)
    try:
        from app.services.tri_core_service import _get_funasr_model
        logger.info("🔄 Pre-loading FunASR model...")
        _get_funasr_model()
        logger.info("✅ FunASR model loaded")
    except Exception as e:
        logger.warning(f"⚠️ FunASR pre-loading failed: {e}")
    
    logger.info("🚀 Application started successfully")
    
    yield
    
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    """Application factory"""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="Chinese Speaking Proficiency Assessment using Praat - API Only",
        version=settings.app_version,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router)
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)