"""Shared LLM types and Protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


@dataclass(frozen=True)
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LLMClient(Protocol):
    model: str

    async def complete(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        schema: type[BaseModel],
    ) -> LLMResult: ...
