from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging import setup_logging
from app.db import init_db, close_db
from app.api import auth_router, profiles_router, map_router, contact_router

# Initialize logging
logger = setup_logging()
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0"
)

# CORS middleware - configured from environment variables
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.get_cors_methods(),
    allow_headers=settings.get_cors_headers(),
)

# Include routers (Consider Versioning when we Scale)
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(map_router)
app.include_router(contact_router)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Database URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'Not configured'}")

    # Initialize database and PostGIS
    try:
        await init_db()
        logger.info("Database initialized with PostGIS support")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't raise in production - allow app to start and retry connections
        if settings.debug:
            raise


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.app_name}")

    # Close database connections
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker healthcheck and monitoring.
    Returns 200 if app is running.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.environment,
        "version": "0.1.0"
    }


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness check - verifies database connectivity.
    Use this for Kubernetes readiness probes or load balancer checks.
    """
    from app.db import engine
    from sqlalchemy import text
    
    try:
        # Try to execute a simple query
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "database": "connected",
            "app": settings.app_name
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not ready",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/")
async def root():
    """Root endpoint - basic API information"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "environment": settings.environment
    }
