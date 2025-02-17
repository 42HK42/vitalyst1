"""Security configuration and utilities."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from cryptography.fernet import Fernet
from pydantic import BaseModel, Field


class PasswordPolicy(BaseModel):
    """Password policy configuration."""

    min_length: int = Field(12, description="Minimum password length")
    require_numbers: bool = Field(True, description="Require numbers in password")
    require_symbols: bool = Field(True, description="Require symbols in password")
    require_uppercase: bool = Field(True, description="Require uppercase in password")
    require_lowercase: bool = Field(True, description="Require lowercase in password")

    def validate_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """Validate a password against the policy."""
        if len(password) < self.min_length:
            return False, f"Password must be at least {self.min_length} characters"

        if self.require_numbers and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"

        if self.require_symbols and not any(not c.isalnum() for c in password):
            return False, "Password must contain at least one symbol"

        if self.require_uppercase and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if self.require_lowercase and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        return True, None


class KeyRotation(BaseModel):
    """Key rotation configuration."""

    enabled: bool = Field(True, description="Enable key rotation")
    interval: timedelta = Field(
        default_factory=lambda: timedelta(days=30),
        description="Key rotation interval",
    )
    algorithm: str = Field("AES-256-GCM", description="Encryption algorithm")
    key_length: int = Field(256, description="Key length in bits")


class RateLimit(BaseModel):
    """Rate limiting configuration."""

    window: timedelta = Field(
        default_factory=lambda: timedelta(minutes=15),
        description="Rate limit window",
    )
    max_requests: int = Field(100, description="Maximum requests per window")
    skip_paths: list[str] = Field(
        default_factory=lambda: ["/health", "/metrics"],
        description="Paths to skip rate limiting",
    )


class SecurityConfig(BaseModel):
    """Security configuration."""

    key_rotation: KeyRotation = Field(
        default_factory=KeyRotation,
        description="Key rotation settings",
    )
    password_policy: PasswordPolicy = Field(
        default_factory=PasswordPolicy,
        description="Password policy settings",
    )
    rate_limit: RateLimit = Field(
        default_factory=RateLimit,
        description="Rate limiting settings",
    )
    max_login_attempts: int = Field(5, description="Maximum login attempts")
    lockout_duration: timedelta = Field(
        default_factory=lambda: timedelta(minutes=15),
        description="Account lockout duration",
    )


class SecretManager:
    """Secret management utility."""

    def __init__(self):
        """Initialize the secret manager."""
        self._fernet = None
        self._key_created = None
        self._rotation_interval = timedelta(days=30)

    def _create_key(self) -> None:
        """Create a new encryption key."""
        key = Fernet.generate_key()
        self._fernet = Fernet(key)
        self._key_created = datetime.now(timezone.utc)

    def _should_rotate(self) -> bool:
        """Check if the key should be rotated."""
        if not self._key_created:
            return True
        return (
            datetime.now(timezone.utc) - self._key_created
        ) > self._rotation_interval

    def encrypt(self, data: str) -> str:
        """Encrypt data."""
        if self._should_rotate():
            self._create_key()
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        if not self._fernet:
            raise ValueError("No encryption key available")
        return self._fernet.decrypt(encrypted_data.encode()).decode()


class SecurityService:
    """Security service implementation."""

    def __init__(self, config: SecurityConfig, secret_manager: SecretManager):
        """Initialize the security service."""
        self.config = config
        self.secret_manager = secret_manager
        self._failed_attempts: Dict[str, Dict[str, int | datetime]] = {}

    def validate_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """Validate a password against the policy."""
        return self.config.password_policy.validate_password(password)

    def check_rate_limit(self, path: str, ip: str) -> bool:
        """Check if a request should be rate limited."""
        if path in self.config.rate_limit.skip_paths:
            return True

        key = f"{ip}:{path}"
        now = datetime.now(timezone.utc)

        # Clean up old entries
        self._failed_attempts = {
            k: v
            for k, v in self._failed_attempts.items()
            if now - v["timestamp"] < self.config.rate_limit.window
        }

        if key not in self._failed_attempts:
            self._failed_attempts[key] = {"count": 1, "timestamp": now}
            return True

        if self._failed_attempts[key]["count"] >= self.config.rate_limit.max_requests:
            return False

        self._failed_attempts[key]["count"] += 1
        return True

    def generate_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)

    def constant_time_compare(self, val1: str, val2: str) -> bool:
        """Compare two strings in constant time."""
        return hmac.compare_digest(
            hashlib.sha256(val1.encode()).digest(),
            hashlib.sha256(val2.encode()).digest(),
        )
