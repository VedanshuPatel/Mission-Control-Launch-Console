"""Gemini Flash adapter — the only module allowed to import google.genai."""

from __future__ import annotations

import asyncio
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError
from pydantic import BaseModel

from app.llm.base import LLMResult

LLM_MAX_CONCURRENCY = 3
_MAX_TRIES = 3


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, ServerError):
        return True
    if isinstance(exc, ClientError) and getattr(exc, "code", None) == 429:
        return True
    if isinstance(exc, APIError):
        code = getattr(exc, "code", None)
        if isinstance(code, int) and code >= 500:
            return True
    return False


class GeminiLLM:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: Any | None = None,
        max_concurrency: int = LLM_MAX_CONCURRENCY,
    ) -> None:
        self.model = model
        self._client = client if client is not None else genai.Client(api_key=api_key)
        self._sem = asyncio.Semaphore(max_concurrency)

    async def complete(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        schema: type[BaseModel],
    ) -> LLMResult:
        del task  # task is for tracing at call sites; Gemini call uses system/prompt/schema
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
        )
        last_exc: BaseException | None = None
        async with self._sem:
            for attempt in range(_MAX_TRIES):
                try:
                    response = await self._client.aio.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config,
                    )
                    usage = getattr(response, "usage_metadata", None)
                    prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
                    candidates = int(getattr(usage, "candidates_token_count", 0) or 0)
                    thoughts = int(getattr(usage, "thoughts_token_count", 0) or 0)
                    text = getattr(response, "text", None) or ""
                    return LLMResult(
                        text=text,
                        input_tokens=prompt_tokens,
                        output_tokens=candidates + thoughts,
                        model=self.model,
                    )
                except Exception as exc:  # noqa: BLE001 — narrow via _is_retryable
                    last_exc = exc
                    if _is_retryable(exc) and attempt < _MAX_TRIES - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise
        assert last_exc is not None
        raise last_exc
