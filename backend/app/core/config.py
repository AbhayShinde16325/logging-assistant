"""Application settings — task T-010.

All variables are documented in ../../.env.example; every new variable must be added to BOTH
files in the same PR (backend/AGENTS.md conventions). Loads environment variables (with an
optional .env at the repo root when present).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    api_bearer_token: str | None = os.getenv("API_BEARER_TOKEN") or None

    # Backend
    backend_host: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    # LLM / Ollama (Developer A)
    model_provider: str = os.getenv("MODEL_PROVIDER", "auto")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

    # Google Sheets (Developer B)
    google_sheets_spreadsheet_id: str | None = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID") or None
    google_application_credentials: str | None = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or None
    reconciliation_poll_seconds: int = int(os.getenv("RECONCILIATION_POLL_SECONDS", "60"))

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sheets_configured(self) -> bool:
        return bool(self.google_sheets_spreadsheet_id and self.google_application_credentials)


@lru_cache
def get_settings() -> Settings:
    return Settings()
