"""Scripted FakeLLM for tests and demo mode — never touches the network."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import BaseModel

from app.llm.base import LLMResult

ScriptItem = str | BaseException | Callable[[str], str]

_DEFAULTS: dict[str, str] = {
    "classify": (
        '{"subsystem":"other","severity":"low",'
        '"rationale":"Nominal note; no elevated concern."}'
    ),
    "check_injection": '{"flagged":false,"evidence":""}',
    "check_missing_details": '{"missing":[]}',
    "check_tone": '{"level":"calm"}',
    "draft": (
        '{"headline":"Status update","body":"Readings within limits. '
        'No action required.","recommended_action":"Continue countdown."}'
    ),
    "review": '{"passed":true,"issues":[],"feedback":""}',
}


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
class FakeLLM:
    script: dict[str, list[ScriptItem]] = field(default_factory=dict)
    barrier: asyncio.Barrier | None = None
    model: str = "fake-model"
    calls: list[RecordedCall] = field(default_factory=list)
    _cursors: dict[str, int] = field(default_factory=dict)

    async def complete(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        schema: type[BaseModel],
    ) -> LLMResult:
        started = datetime.now(UTC)
        if self.barrier is not None and task.startswith("check_"):
            await self.barrier.wait()

        item = self._next_script_item(task)
        if isinstance(item, BaseException):
            ended = datetime.now(UTC)
            self.calls.append(
                RecordedCall(
                    task=task,
                    system=system,
                    prompt=prompt,
                    schema=schema,
                    started_at=started,
                    ended_at=ended,
                )
            )
            raise item

        if callable(item):
            text = item(prompt)
        else:
            text = item

        ended = datetime.now(UTC)
        in_tok = len(system + prompt) // 4
        out_tok = len(text) // 4
        self.calls.append(
            RecordedCall(
                task=task,
                system=system,
                prompt=prompt,
                schema=schema,
                started_at=started,
                ended_at=ended,
                text=text,
                input_tokens=in_tok,
                output_tokens=out_tok,
            )
        )
        return LLMResult(
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            model=self.model,
        )

    def _next_script_item(self, task: str) -> ScriptItem:
        queue = self.script.get(task, [])
        idx = self._cursors.get(task, 0)
        if idx < len(queue):
            self._cursors[task] = idx + 1
            return queue[idx]
        # Happy-path fallback by task family
        if task.startswith("draft"):
            return _DEFAULTS["draft"]
        if task.startswith("review"):
            return _DEFAULTS["review"]
        return _DEFAULTS.get(task, '{"ok":true}')
