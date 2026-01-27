"""
Core Configuration Module

Provides centralized settings management for the Basketball Analytics Platform
using Pydantic Settings. Configuration values are loaded from environment
variables and .env files with sensible defaults.

This module exports:
    - Settings: The Pydantic BaseSettings class with all configuration
    - settings: A singleton instance for application-wide use

Usage:
    from src.core import settings

    print(settings.PROJECT_NAME)
    print(settings.DATABASE_URL)

Environment variables override defaults. Create a .env file in the project
root to set values without modifying environment variables directly.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env files.

    This class uses Pydantic Settings to provide type-safe configuration
    with automatic environment variable loading and validation.

    Attributes:
        PROJECT_NAME: Display name for the application.
        DEBUG: Enable debug mode for detailed logging and error messages.
        DATABASE_URL: SQLAlchemy database connection string.
        TEST_DATABASE_URL: Database URL used during test runs.
        API_PREFIX: URL prefix for all API routes.
        LLM_MODEL: The LLM model to use for chat (e.g., gpt-4).
        LLM_TEMPERATURE: Temperature setting for LLM responses (0.0-1.0).
        OPENAI_API_KEY: API key for OpenAI services.
        CORS_ORIGINS: List of allowed origins for CORS.

    Example:
        >>> from src.core.config import Settings
        >>> settings = Settings()
        >>> settings.PROJECT_NAME
        'Basketball Analytics'
        >>> settings.DEBUG
        False
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str = "Basketball Analytics"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./basketball.db"
    TEST_DATABASE_URL: str = "sqlite:///:memory:"

    # API
    API_PREFIX: str = "/api/v1"

    # LLM Configuration
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.7
    OPENAI_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure only one Settings instance is created,
    avoiding repeated .env file reads.

    Returns:
        Settings: The application settings singleton.

    Example:
        >>> settings = get_settings()
        >>> settings.PROJECT_NAME
        'Basketball Analytics'
    """
    return Settings()


# Singleton instance for convenient imports
settings = get_settings()
