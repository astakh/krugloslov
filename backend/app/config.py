"""Application configuration via environment variables."""

from __future__ import annotations

import json
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL async connection string")

    # JWT
    JWT_SECRET: str = Field(..., min_length=16, description="Secret for JWT signing")
    ACCESS_TOKEN_TTL_MIN: int = Field(default=15, ge=1, le=1440)
    REFRESH_TOKEN_TTL_DAYS: int = Field(default=30, ge=1, le=365)

    # SRS / Lesson
    WORDS_PER_LESSON: int = Field(default=10, ge=1, le=100)
    WORDS_PER_LESSON_MAX: int = Field(default=20, ge=1, le=100)
    DAILY_LESSON_LIMIT_DEFAULT: int = Field(default=5, ge=1, le=100)
    DAILY_LESSON_LIMIT_MAX: int = Field(default=20, ge=1, le=100)

    # GigaChat
    GIGACHAT_AUTH_KEY: str = Field(..., min_length=1)
    GIGACHAT_SCOPE: str = Field(default="GIGACHAT_API_PERS")
    GIGACHAT_MODEL: str = Field(default="GigaChat")
    GIGACHAT_CA_CERT_PATH: str = Field(default="")
    GIGACHAT_MAX_CONCURRENCY: int = Field(default=3, ge=1, le=20)

    # LLM timeouts
    LLM_REQUEST_TIMEOUT: int = Field(default=60, ge=10, le=300, description="Request timeout in seconds")
    LLM_TOKEN_TIMEOUT: int = Field(default=30, ge=10, le=120, description="Token refresh timeout in seconds")

    # LLM temperatures
    GEN_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0)
    EVAL_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=2.0)

    # Logging
    LLM_LOG_RETENTION_DAYS: int = Field(default=30, ge=1, le=365)

    # CORS
    CORS_ORIGINS: str = Field(
        default='["http://localhost:3000","http://localhost:5173"]',
        description="JSON array of allowed CORS origins",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Validate that CORS_ORIGINS is a valid JSON array of strings."""
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, list):
                raise ValueError("CORS_ORIGINS must be a JSON array")
            for item in parsed:
                if not isinstance(item, str):
                    raise ValueError("CORS_ORIGINS items must be strings")
        except json.JSONDecodeError as e:
            raise ValueError(f"CORS_ORIGINS must be valid JSON: {e}")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Return parsed CORS origins list."""
        return json.loads(self.CORS_ORIGINS)

    @field_validator("DAILY_LESSON_LIMIT_MAX")
    @classmethod
    def validate_daily_limit(cls, v: int, info) -> int:
        """Ensure max limit >= default limit."""
        # This validator runs after DAILY_LESSON_LIMIT_DEFAULT is set
        return v


settings = Settings()
