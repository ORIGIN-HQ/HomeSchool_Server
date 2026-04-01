from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List, Union

class Settings(BaseSettings):
    # Application
    app_name: str = "Homeschool API"
    debug: bool = False
    environment: str = "production"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    
    # CORS Configuration
    cors_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: Union[str, List[str]] = "*"  # Changed to Union
    cors_allow_headers: Union[str, List[str]] = "*"  # Changed to Union
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    
    # Database
    database_url: str = ""
    db_pool_size: int = 5
    db_max_overflow: int = 10
    
    # PostgreSQL Individual Settings (for flexibility)
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    postgres_host: Optional[str] = "postgres"
    postgres_port: Optional[int] = 5432
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"
    
    def get_database_url(self) -> str:
        """Returns the database URL, constructing it from individual components if needed."""
        if self.database_url and self.database_url.startswith("postgresql://"):
            return self.database_url
        
        if all([self.postgres_user, self.postgres_password, self.postgres_db]):
            return (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        
        raise ValueError("Database configuration incomplete")
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string or return list."""
        if isinstance(self.cors_origins, str):
            if self.cors_origins == "*":
                return ["*"]
            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return list(self.cors_origins)
    
    def get_cors_methods(self) -> List[str]:
        """Parse CORS methods from comma-separated string or return list."""
        if isinstance(self.cors_allow_methods, str):
            if self.cors_allow_methods == "*":
                return ["*"]
            return [method.strip() for method in self.cors_allow_methods.split(",") if method.strip()]
        return list(self.cors_allow_methods)
    
    def get_cors_headers(self) -> List[str]:
        """Parse CORS headers from comma-separated string or return list."""
        if isinstance(self.cors_allow_headers, str):
            if self.cors_allow_headers == "*":
                return ["*"]
            return [header.strip() for header in self.cors_allow_headers.split(",") if header.strip()]
        return list(self.cors_allow_headers)


@lru_cache
def get_settings() -> Settings:
    """
    Returns cached settings instance.
    This ensures settings are only loaded once and reused across the application.
    """
    return Settings()
