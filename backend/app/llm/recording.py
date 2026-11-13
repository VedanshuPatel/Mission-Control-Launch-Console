"""Per-run LLM call recorder — works for FakeLLM and GeminiLLM alike."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import BaseModel

from app.llm.base import LLMClient, LLMResult


@dataclass
class RecordedCall:
    task: str
    system: str
    prompt: str
    schema: type[BaseModel]
    started_at: datetime
    ended_at: datetime
    text: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class RecordingLLM:
    """Wraps any LLMClient and records each complete() for orchestrator traces."""

    inner: LLMClient
    calls: list[RecordedCall] = field(default_factory=list)

    @property
    def model(self) -> str:
        return self.inner.model

    async def complete(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        schema: type[BaseModel],
    ) -> LLMResult:
        started = datetime.now(UTC)
        result = await self.inner.complete(
            task=task, system=system, prompt=prompt, schema=schema
        )
        ended = datetime.now(UTC)
        self.calls.append(
            RecordedCall(
                task=task,
                system=system,
                prompt=prompt,
                schema=schema,
                started_at=started,
                ended_at=ended,
                text=result.text,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
        )
        return result
