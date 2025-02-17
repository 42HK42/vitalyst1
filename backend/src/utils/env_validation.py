"""Environment validation utilities."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, constr, validator
from pydantic_settings import BaseSettings


class LogLevel(str, Enum):
    """Log level enumeration."""

    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"


class SecurityConfig(BaseModel):
    """Security configuration settings."""

    key_rotation_enabled: bool = Field(True, description="Enable key rotation")
    key_rotation_interval: str = Field("30d", description="Key rotation interval")
    key_algorithm: str = Field("AES-256-GCM", description="Encryption algorithm")
    key_length: int = Field(256, description="Key length in bits")
    max_login_attempts: int = Field(5, description="Maximum login attempts")
    lockout_duration: str = Field("15m", description="Account lockout duration")
    min_password_length: int = Field(12, description="Minimum password length")
    require_numbers: bool = Field(True, description="Require numbers in password")
    require_symbols: bool = Field(True, description="Require symbols in password")
    require_uppercase: bool = Field(True, description="Require uppercase in password")
    require_lowercase: bool = Field(True, description="Require lowercase in password")


class EnvironmentSettings(BaseSettings):
    """Environment settings validation."""

    # Base Configuration
    app_name: str = Field("vitalyst", description="Application name")
    app_version: str = Field(..., description="Application version")
    api_version: str = Field("v1", description="API version")
    debug: bool = Field(False, description="Debug mode")
    log_level: LogLevel = Field(LogLevel.INFO, description="Log level")

    # Server Configuration
    api_port: int = Field(8000, ge=1, le=65535, description="API port")
    api_host: str = Field("0.0.0.0", description="API host")
    rate_limit_window: str = Field("15m", description="Rate limit window")
    rate_limit_max_requests: int = Field(100, description="Max requests per window")
    cors_origins: list[str] = Field([], description="CORS allowed origins")

    # Database Configuration
    neo4j_uri: str = Field(..., description="Neo4j URI")
    neo4j_user: str = Field(..., description="Neo4j username")
    neo4j_password: str = Field(..., description="Neo4j password")
    neo4j_database: str = Field("neo4j", description="Neo4j database name")
    neo4j_encryption: bool = Field(True, description="Enable Neo4j encryption")
    neo4j_connection_timeout: int = Field(20000, description="Connection timeout")
    neo4j_max_connection_poolsize: int = Field(100, description="Max connections")

    # Redis Configuration
    redis_host: str = Field(..., description="Redis host")
    redis_port: int = Field(6379, description="Redis port")
    redis_password: Optional[str] = Field(None, description="Redis password")
    redis_db: int = Field(0, description="Redis database number")
    redis_ssl: bool = Field(True, description="Enable Redis SSL")

    # Authentication
    auth0_domain: HttpUrl = Field(..., description="Auth0 domain")
    auth0_audience: HttpUrl = Field(..., description="Auth0 audience")
    auth0_client_id: str = Field(..., description="Auth0 client ID")
    auth0_client_secret: str = Field(..., description="Auth0 client secret")
    jwt_secret: str = Field(..., description="JWT secret key")
    jwt_expiration: str = Field("1h", description="JWT expiration time")
    refresh_token_expiration: str = Field("30d", description="Refresh token expiration")

    # AI Services
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field("gpt-4", description="OpenAI model")
    openai_max_tokens: int = Field(2000, description="OpenAI max tokens")
    openai_temperature: float = Field(0.7, ge=0, le=1, description="OpenAI temperature")
    claude_api_key: Optional[str] = Field(None, description="Claude API key")
    claude_model: Optional[str] = Field(None, description="Claude model")
    ai_fallback_strategy: str = Field("sequential", description="AI fallback strategy")

    # Monitoring
    prometheus_enabled: bool = Field(True, description="Enable Prometheus")
    prometheus_port: int = Field(9090, description="Prometheus port")
    grafana_port: int = Field(3000, description="Grafana port")
    metrics_prefix: str = Field("vitalyst", description="Metrics prefix")
    health_check_interval: str = Field("30s", description="Health check interval")
    tracing_enabled: bool = Field(True, description="Enable tracing")
    jaeger_endpoint: HttpUrl = Field(..., description="Jaeger endpoint")

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def validate_environment() -> EnvironmentSettings:
    """Validate environment variables and return settings."""
    try:
        settings = EnvironmentSettings()
        return settings
    except Exception as e:
        raise ValueError(f"Environment validation failed: {str(e)}") from e
