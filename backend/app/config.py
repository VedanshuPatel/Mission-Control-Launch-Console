"""Application settings loaded from environment / .env at repo root."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "auto"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'mission_control.db'}"

    def resolved_provider(self) -> str:
        provider = (self.llm_provider or "auto").strip().lower()
        if provider == "auto":
            return "gemini" if self.gemini_api_key else "fake"
        return provider
