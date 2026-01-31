from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging import setup_logging
from app.db import init_db, close_db
from app.api import auth_router, profiles_router

# Initialize logging
logger = setup_logging()
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0"
)

# CORS middleware (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(profiles_router)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize database and PostGIS
    await init_db()
    logger.info("Database initialized with PostGIS support")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.app_name}")

    # Close database connections
    await close_db()


@app.get("/health")
async def health_check():
    """Health check endpoint - returns 200 if app is running"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.environment
    }


@app.get("/")
async def root():
    """Root endpoint - basic info"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "0.1.0",
        "docs": "/docs"
    }
