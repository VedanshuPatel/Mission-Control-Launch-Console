"""Build an LLMClient from Settings."""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.llm.base import LLMClient
from app.llm.fake import FakeLLM


def build_llm(settings: Settings) -> LLMClient:
    provider = settings.resolved_provider()
    if provider == "fake":
        return FakeLLM()
    if provider == "gemini":
        from app.llm.gemini import GeminiLLM  # local import keeps SDK out of this file

        return GeminiLLM(api_key=settings.gemini_api_key, model=settings.gemini_model)
    raise ValueError(f"Unknown LLM provider: {provider!r}")


def ensure_llm(settings: Settings, llm: Any | None) -> LLMClient:
    return llm if llm is not None else build_llm(settings)
