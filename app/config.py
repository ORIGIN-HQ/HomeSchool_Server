from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    app_name: str = "Homeschool API"
    debug: bool = True
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    secret_key: str = "dev-secret-key-change-in-production"

    # Clerk Authentication
    clerk_publishable_key: str = ""
    clerk_secret_key: str = ""
    clerk_jwt_issuer: str = ""  # e.g., https://your-app.clerk.accounts.dev

    # Google OAuth (legacy - kept for reference)
    google_client_id: str = ""
    google_client_secret: str = ""
    
    # Database - will use DATABASE_URL from environment if available
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://homeschool_user:homeschool_pass@localhost:5432/homeschool_db"
    )
    db_pool_size: int = 5
    db_max_overflow: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure PostgreSQL URL uses the correct driver for SQLAlchemy
        if self.database_url and self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql+psycopg2://", 1)

@lru_cache
def get_settings() -> Settings:
    return Settings()