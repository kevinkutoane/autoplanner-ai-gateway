"""Typed configuration for AutoPlanner AI Gateway using Pydantic Settings."""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Deployment
    ENVIRONMENT: str = Field(default="development", description="Environment: development | staging | production")
    PORT: int = Field(default=8080, description="Listening port for Cloud Run")
    GATEWAY_VERSION: str = Field(default="1.0.0", description="Gateway software version")

    # Authentication & Security
    AUTH_REQUIRED: bool = Field(
        default=True,
        description="Whether Bearer authentication is strictly enforced",
    )
    DEV_BEARER_TOKEN: Optional[str] = Field(
        default="dev-secret-token",
        description="Static bearer token allowed during local development",
    )
    API_KEYS: List[str] = Field(
        default_factory=list,
        description="List of valid API tokens for client authorization",
    )

    # Upstream Gemini Configuration
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API credential injected from Secret Manager",
    )
    FAST_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Model identifier used for fast/operational requests",
    )
    PRO_MODEL: str = Field(
        default="gemini-2.5-pro",
        description="Model identifier used for complex reasoning/synthesis",
    )

    # Request & Abuse Guardrails
    MAX_REQUEST_BYTES: int = Field(
        default=262144,  # 256 KB
        description="Maximum allowed HTTP request payload in bytes",
    )
    MAX_INPUT_TEXT_CHARS: int = Field(
        default=50000,
        description="Maximum characters allowed in text input fields",
    )
    MAX_CONTEXT_SERIALIZED_BYTES: int = Field(
        default=131072,  # 128 KB
        description="Maximum serialized bytes for invocation context",
    )
    REQUEST_TIMEOUT_SECONDS: float = Field(
        default=30.0,
        description="Total gateway request execution timeout",
    )
    UPSTREAM_TIMEOUT_SECONDS: float = Field(
        default=25.0,
        description="Upstream Gemini HTTP call timeout",
    )
    RATE_LIMIT_RPM: int = Field(
        default=60,
        description="Per-client requests permitted per minute",
    )

    @field_validator("API_KEYS", mode="before")
    @classmethod
    def parse_api_keys(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            return [k.strip() for k in v.split(",") if k.strip()]
        return v or []

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")


# Singleton instance
settings = Settings()
