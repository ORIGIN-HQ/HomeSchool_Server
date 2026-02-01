from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    app_name: str = "Homeschool API"
    debug: bool = True
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    secret_key: str = "dev-secret-key-change-in-production"  # Default for migrations/CI

    # Google OAuth
    google_client_id: str = ""  # Empty default for CI/CD and migrations
    google_client_secret: str = ""  # Not used for token verification, but may be needed later

    # Database
    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
