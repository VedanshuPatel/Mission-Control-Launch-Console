"""FakeLLM: scripted replies, recording, tokens, optional barrier."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from app.llm.fake import FakeLLM


class _Reply(BaseModel):
    ok: bool


@pytest.mark.asyncio
async def test_scripted_responses_in_order_and_records_calls():
    llm = FakeLLM(script={"classify": ['{"ok": true}', '{"ok": false}']})
    first = await llm.complete(
        task="classify", system="sys", prompt="p1", schema=_Reply
    )
    second = await llm.complete(
        task="classify", system="sys", prompt="p2", schema=_Reply
    )
    assert first.text == '{"ok": true}'
    assert second.text == '{"ok": false}'
    assert first.model == "fake-model"
    assert len(llm.calls) == 2
    assert llm.calls[0].task == "classify"
    assert llm.calls[0].system == "sys"
    assert llm.calls[0].prompt == "p1"
    assert llm.calls[0].schema is _Reply
    assert llm.calls[0].started_at <= llm.calls[0].ended_at
    assert llm.calls[1].prompt == "p2"


@pytest.mark.asyncio
async def test_scripted_exception_is_raised():
    llm = FakeLLM(script={"classify": [RuntimeError("boom")]})
    with pytest.raises(RuntimeError, match="boom"):
        await llm.complete(task="classify", system="s", prompt="p", schema=_Reply)


@pytest.mark.asyncio
async def test_callable_script_receives_prompt():
    llm = FakeLLM(
        script={
            "classify": [
                lambda prompt: '{"ok": true}' if prompt == "yes" else '{"ok": false}'
            ]
        }
    )
    result = await llm.complete(task="classify", system="s", prompt="yes", schema=_Reply)
    assert result.text == '{"ok": true}'


@pytest.mark.asyncio
async def test_token_counts_are_deterministic():
    llm = FakeLLM()
    system, prompt, text = "abcd", "efgh", "ijkl"
    # Force scripted text length via script
    llm = FakeLLM(script={"classify": [text]})
    result = await llm.complete(task="classify", system=system, prompt=prompt, schema=_Reply)
    assert result.input_tokens == len(system + prompt) // 4
    assert result.output_tokens == len(text) // 4


@pytest.mark.asyncio
async def test_barrier_on_check_tasks_proves_concurrency():
    barrier = asyncio.Barrier(3)
    llm = FakeLLM(barrier=barrier)

    async def run(task: str) -> None:
        await llm.complete(task=task, system="s", prompt="p", schema=_Reply)

    await asyncio.wait_for(
        asyncio.gather(
            run("check_injection"),
            run("check_missing_details"),
            run("check_tone"),
        ),
        timeout=1.0,
    )
    windows = [(c.started_at, c.ended_at) for c in llm.calls if c.task.startswith("check_")]
    assert len(windows) == 3
    # Overlap: each call started before all others ended
    starts = [w[0] for w in windows]
    ends = [w[1] for w in windows]
    assert max(starts) <= min(ends)
