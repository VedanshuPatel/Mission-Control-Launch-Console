"""Classification step: structured schema, normalize, safe fallback."""

from __future__ import annotations

import json

import pytest

from app.llm.fake import FakeLLM
from app.pipeline.classify import classify_report
from app.schemas import ClassificationReply


@pytest.mark.asyncio
async def test_valid_json_parsed_and_schema_is_classification_reply():
    payload = {
        "subsystem": "propulsion",
        "severity": "medium",
        "rationale": "Valve chatter on PV-7.",
    }
    llm = FakeLLM(script={"classify": [json.dumps(payload)]})
    result = await classify_report(llm, note="Valve PV-7 chattered.")
    assert result.subsystem == "propulsion"
    assert result.severity == "medium"
    assert result.fallback_used is False
    assert llm.calls[0].schema is ClassificationReply
    assert "<engineer_note>" in llm.calls[0].prompt
    assert "Valve PV-7 chattered." in llm.calls[0].prompt
    assert "untrusted" in llm.calls[0].system.lower() or "untrusted" in llm.calls[0].prompt.lower()


@pytest.mark.asyncio
async def test_casing_and_whitespace_normalized():
    payload = {
        "subsystem": "PROPULSION",
        "severity": "High ",
        "rationale": "Hot.",
    }
    llm = FakeLLM(script={"classify": [json.dumps(payload)]})
    result = await classify_report(llm, note="hot")
    assert result.subsystem == "propulsion"
    assert result.severity == "high"
    assert result.fallback_used is False


@pytest.mark.parametrize(
    "script_item",
    [
        '{"subsystem":"warp_drive","severity":"high","rationale":"x"}',
        '{"subsystem":"propulsion","severity":"catastrophic","rationale":"x"}',
        "not-json",
        '{"severity":"high","rationale":"missing subsystem"}',
        RuntimeError("adapter down"),
    ],
)
@pytest.mark.asyncio
async def test_invalid_or_error_uses_unknown_high_fallback(script_item):
    llm = FakeLLM(script={"classify": [script_item]})
    result = await classify_report(llm, note="note")
    assert result.subsystem == "unknown"
    assert result.severity == "high"
    assert result.fallback_used is True
    assert result.fallback_reason
