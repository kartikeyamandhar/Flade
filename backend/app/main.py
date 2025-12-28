"""
Main FastAPI application.
Sets up the API server with CORS, logging, and database connections.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

from app.core.config import settings
from app.core.database import db
from app.api.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces deprecated on_event decorators.
    """
    # Startup
    logger.info("Starting application...")
    try:
        db.connect()
        logger.info("✓ Application started successfully")
    except Exception as e:
        logger.error(f"✗ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    db.close()
    logger.info("✓ Application shut down")


# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered instruction manual knowledge graph with hybrid retrieval",
    lifespan=lifespan
)

# CORS middleware (for React frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1", tags=["API"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Manual Knowledge Graph API",
        "version": settings.VERSION,
        "docs": "/docs",
        "endpoints": {
            "upload": "/api/v1/upload",
            "query": "/api/v1/query",
            "documents": "/api/v1/documents",
            "status": "/api/v1/documents/{id}/status",
            "graph_stats": "/api/v1/graph/{id}/stats"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )