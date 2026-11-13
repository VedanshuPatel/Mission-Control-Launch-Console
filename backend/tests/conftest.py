"""Shared pytest fixtures. Autouse: no Gemini key, fake LLM provider."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.llm.fake import FakeLLM
from app.main import create_app


@pytest.fixture(autouse=True)
def _force_fake_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "fake")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    db_path = tmp_path / "test.db"
    return Settings(
        llm_provider="fake",
        gemini_api_key="",
        gemini_model="fake-model",
        database_url=f"sqlite:///{db_path}",
    )


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def app(settings: Settings, fake_llm: FakeLLM):
    return create_app(settings, llm=fake_llm)


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
