# AGENTS.md - HomeSchool Server Development Guide

This document provides coding agents with essential information about the HomeSchool Server codebase, a FastAPI-based backend with PostGIS integration for geospatial features.

## Technology Stack

- **Framework**: FastAPI (v0.128.0) with async/await throughout
- **Database**: PostgreSQL with PostGIS extension via Docker
- **ORM**: SQLAlchemy (v2.0.46) + GeoAlchemy2 for spatial operations
- **Authentication**: JWT tokens + Google OAuth2 integration
- **Validation**: Pydantic (v2.12.5) with custom validators
- **Migrations**: Alembic for database version control
- **Testing**: pytest + pytest-asyncio with TestClient

## Build/Lint/Test Commands

### Development Server
```bash
# Start development server with auto-reload
uvicorn app.main:app --reload

# Start with custom host/port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Database Operations
```bash
# Start PostgreSQL with PostGIS (required first)
docker-compose up -d

# Run all migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Downgrade one revision
alembic downgrade -1
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_map_pins.py

# Run single test function
pytest tests/test_map_pins.py::test_create_map_pin

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app

# Run tests matching pattern
pytest -k "map_pin"
```

### Linting and Code Quality
```bash
# Run flake8 linting (follows .flake8 config)
flake8 app/ tests/

# Check specific file
flake8 app/api/map.py

# Run security checks (if bandit installed)
bandit -r app/
```

### Dependencies
```bash
# Install dependencies
pip install -r requirements.txt

# Generate updated requirements
pip freeze > requirements.txt
```

## Code Style Guidelines

### Import Organization
```python
# 1. Standard library imports
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from uuid import uuid4

# 2. Third-party imports (alphabetical)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import Session

# 3. Local application imports (alphabetical)
from app.core.auth import get_current_user
from app.db import get_db
from app.schemas.auth import AuthResponse
from app.services.google_auth import GoogleAuthService
```

### File and Directory Naming
- **Files**: `snake_case.py` (e.g., `google_auth.py`, `map_pins.py`)
- **Directories**: `snake_case` (e.g., `api/`, `schemas/`, `services/`)
- **Test files**: `test_*.py` (e.g., `test_map_pins.py`)
- **Database models**: `snake_case` table names, PascalCase class names

### Variable and Function Naming
```python
# Variables and functions: snake_case
user_profile = UserProfile(...)
access_token = create_access_token(data)
google_client_id = settings.google_client_id

# Constants: UPPER_SNAKE_CASE
ACCESS_TOKEN_EXPIRE_DAYS = 30
ALGORITHM = "HS256"
SECRET_KEY = "your-secret-key"

# Classes: PascalCase
class GoogleAuthService:
class UserProfile(BaseModel):
class TimestampMixin:

# Database models: PascalCase with snake_case table names
class User(Base):
    __tablename__ = "users"
```

### Type Annotations
Always use type hints for function parameters and return types:
```python
# Function signatures with types
async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:

async def verify_google_token(token: str) -> dict:

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:

# Pydantic models with proper typing
class UserProfile(BaseModel):
    email: str
    name: str
    created_at: datetime
    location: Optional[Dict[str, float]] = None
```

### FastAPI Route Patterns
```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/v1", tags=["feature"])

# Dependency injection pattern
CurrentUserDep = Depends(get_current_user)
DBDep = Depends(get_db)

@router.post("/endpoint", response_model=ResponseSchema)
async def endpoint_function(
    request: RequestSchema,
    current_user: dict = CurrentUserDep,
    db: Session = DBDep,
) -> ResponseSchema:
    """
    Endpoint description.
    
    Args:
        request: Request payload description
        current_user: Authenticated user from JWT token
        db: Database session
        
    Returns:
        ResponseSchema: Description of return value
        
    Raises:
        HTTPException: When validation fails or unauthorized
    """
    # Implementation here
```

### Error Handling
```python
# HTTP exceptions with consistent patterns
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)

raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Validation error occurred"
)

# Always log errors before raising
import logging
logger = logging.getLogger(__name__)

try:
    result = await some_operation()
except Exception as e:
    logger.error(f"Operation failed: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error"
    )
```

### Database Patterns
```python
# SQLAlchemy models with TimestampMixin
from app.db.mixins import TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)

# Async database operations
async def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

# PostGIS/Geospatial queries
from geoalchemy2 import Geography
from sqlalchemy import func

# Distance queries
nearby_pins = db.query(MapPin).filter(
    func.ST_DWithin(
        MapPin.location,
        func.ST_Point(longitude, latitude),
        radius_meters
    )
).all()
```

### Configuration and Settings
```python
# Use Pydantic settings for configuration
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Homeschool API"
    debug: bool = True
    database_url: str
    secret_key: str
    google_client_id: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

# Singleton pattern for settings
@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### Testing Patterns
```python
# Test file structure
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test function naming: test_action_expected_result
def test_create_map_pin_success():
    """Test successful map pin creation."""
    # Arrange
    pin_data = {
        "title": "Test Pin",
        "latitude": 40.7128,
        "longitude": -74.0060
    }
    
    # Act
    response = client.post("/api/v1/map/pins", json=pin_data)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["title"] == "Test Pin"

# Async test functions
@pytest.mark.asyncio
async def test_async_operation():
    """Test async database operations."""
    result = await some_async_function()
    assert result is not None
```

## Environment Setup

### Required Environment Variables
```env
# Application
ENV=development
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/homeschool_db
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/homeschool_test

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
```

### Development Workflow
1. Start PostgreSQL: `docker-compose up -d`
2. Run migrations: `alembic upgrade head`
3. Start server: `uvicorn app.main:app --reload`
4. Run tests: `pytest`
5. Check linting: `flake8 app/ tests/`

## Key Project Structure
```
app/
├── api/           # FastAPI route modules
├── core/          # Auth, logging, dependencies
├── db/            # SQLAlchemy models and database config
├── schemas/       # Pydantic request/response models
└── services/      # Business logic layer
tests/             # Test suite with conftest.py
alembic/           # Database migrations
```

## Important Notes
- Always use async/await for database operations and external API calls
- PostGIS extension must be enabled for geospatial features
- JWT tokens expire after 30 days (configurable)
- All endpoints require authentication except `/auth/google`
- Use dependency injection for database sessions and current user
- Follow the layered architecture: API → Service → Database
- Maximum line length: 120 characters (flake8 configured)
- Test database is isolated and recreated for each test