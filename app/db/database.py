"""
Database configuration and session management.
Includes PostGIS support for geospatial queries.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import get_settings

settings = get_settings()

# Database URL
DATABASE_URL = settings.database_url

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,  # Verify connections before using them
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


# Dependency for FastAPI routes
def get_db():
    """
    FastAPI dependency that provides a database session.
    Automatically closes the session after the request.
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """
    Initialize database:
    - Create all tables
    - Enable PostGIS extension
    """
    from sqlalchemy import text
    
    # Create PostGIS extension
    with engine.connect() as conn:
        # Enable PostGIS (requires superuser or extension creation privileges)
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
            print(" PostGIS extension enabled")
        except Exception as e:
            print(f"Could not enable PostGIS (may already exist): {e}")
    
    # Import all models to ensure they're registered
    import app.db.models  # noqa
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created")


async def close_db():
    """
    Close database connections on shutdown.
    """
    engine.dispose()
    print("Database connections closed")
