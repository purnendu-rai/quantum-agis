"""Application configuration loaded from environment variables.

Uses pydantic-settings so every value can be overridden via env vars or a
local ``.env`` file (see ``.env.example``). Production deploys (Render, Docker)
inject the same variables, so no code changes are needed between environments.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central, env-driven application settings."""

    APP_NAME: str = "QUANTUM-AGIS"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS_ORIGINS split into a list of origin URLs."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Whether the app is running in production mode."""
        return self.ENVIRONMENT == "production"

    class Config:
        env_file = ".env"
        case_sensitive = True


#: Module-level settings instance (spec-style single import point).
settings = Settings()


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one per process)."""
    return settings
