"""GeminiLLM adapter — stubbed SDK only, no network."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai.errors import ClientError
from pydantic import BaseModel

from app.config import Settings
from app.llm.factory import build_llm
from app.llm.gemini import GeminiLLM


class _Reply(BaseModel):
    ok: bool


def _stub_response(*, text: str, prompt: int, candidates: int, thoughts: int | None):
    usage = SimpleNamespace(
        prompt_token_count=prompt,
        candidates_token_count=candidates,
        thoughts_token_count=thoughts,
    )
    return SimpleNamespace(text=text, usage_metadata=usage)


@pytest.mark.asyncio
async def test_maps_stubbed_response_including_thoughts_as_output(monkeypatch):
    generate = AsyncMock(
        return_value=_stub_response(
            text='{"ok": true}', prompt=10, candidates=4, thoughts=6
        )
    )
    client = MagicMock()
    client.aio.models.generate_content = generate

    llm = GeminiLLM(api_key="dummy", model="gemini-3.8-flash", client=client)
    result = await llm.complete(
        task="classify", system="sys", prompt="hello", schema=_Reply
    )

    assert result.text == '{"ok": true}'
    assert result.input_tokens == 10
    assert result.output_tokens == 10  # 4 candidates + 6 thoughts
    assert result.model == "gemini-3.8-flash"
    generate.assert_awaited_once()
    kwargs = generate.await_args.kwargs
    assert kwargs["model"] == "gemini-3.8-flash"
    assert kwargs["contents"] == "hello"
    assert kwargs["config"].system_instruction == "sys"
    assert kwargs["config"].response_mime_type == "application/json"
    assert kwargs["config"].response_schema is _Reply


@pytest.mark.asyncio
async def test_retries_429_then_gives_up(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("app.llm.gemini.asyncio.sleep", fake_sleep)

    generate = AsyncMock(side_effect=ClientError(429, {"error": {"message": "rate"}}))
    client = MagicMock()
    client.aio.models.generate_content = generate

    llm = GeminiLLM(api_key="dummy", model="gemini-3.8-flash", client=client)
    with pytest.raises(ClientError):
        await llm.complete(task="classify", system="s", prompt="p", schema=_Reply)

    assert generate.await_count == 3
    assert len(sleeps) == 2
    assert sleeps[0] < sleeps[1]


def test_build_llm_returns_gemini_for_provider_gemini():
    settings = Settings(
        llm_provider="gemini",
        gemini_api_key="dummy-key",
        gemini_model="gemini-3.8-flash",
    )
    llm = build_llm(settings)
    assert isinstance(llm, GeminiLLM)
    assert llm.model == "gemini-3.8-flash"


def test_build_llm_returns_gemini_for_auto_with_key():
    settings = Settings(
        llm_provider="auto",
        gemini_api_key="dummy-key",
        gemini_model="gemini-3.8-flash",
    )
    llm = build_llm(settings)
    assert isinstance(llm, GeminiLLM)
