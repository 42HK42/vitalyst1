"""Configuration settings for the Vitalyst Knowledge Graph backend."""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    PROJECT_NAME: str = "Vitalyst Knowledge Graph"
    VERSION: str = "1.0.0-alpha"
    API_V1_STR: str = "/api/v1"
    BACKEND_PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str = "vitalyst"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    CACHE_TTL: int = 3600

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AI Services
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    PERPLEXITY_API_KEY: str
    AI_MODEL: str = "gpt-4"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 2000

    # Monitoring
    LOG_LEVEL: str = "info"
    ENABLE_TRACING: bool = True

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = True
