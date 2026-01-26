"""Application configuration settings."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_database_url() -> str:
    """Get the default database URL, using Fly Volume path if available."""
    if os.path.isdir("/data"):
        return "sqlite:////data/electric.db"
    return "sqlite:///./electric.db"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "Electric"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database - defaults to Fly Volume path if /data exists
    DATABASE_URL: str = _get_default_database_url()

    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()
