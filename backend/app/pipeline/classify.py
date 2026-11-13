"""Classify a report by subsystem and severity with a safe fallback."""

from __future__ import annotations

import json

from pydantic import ValidationError

from app.llm.base import LLMClient
from app.pipeline import prompts
from app.schemas import Classification, ClassificationReply

_SUBSYSTEMS = {
    "propulsion",
    "avionics",
    "guidance_navigation",
    "telemetry_comms",
    "ground_support",
    "weather",
    "range_safety",
    "structures_mechanical",
    "other",
}
_SEVERITIES = {"low", "medium", "high"}


def _normalize(raw: dict) -> dict:
    out = dict(raw)
    if "subsystem" in out and isinstance(out["subsystem"], str):
        out["subsystem"] = out["subsystem"].strip().lower()
    if "severity" in out and isinstance(out["severity"], str):
        out["severity"] = out["severity"].strip().lower()
    return out


def _fallback(reason: str) -> Classification:
    return Classification(
        subsystem="unknown",
        severity="high",
        rationale="",
        fallback_used=True,
        fallback_reason=reason,
    )


async def classify_report(llm: LLMClient, *, note: str) -> Classification:
    try:
        result = await llm.complete(
            task="classify",
            system=prompts.CLASSIFY_SYSTEM,
            prompt=prompts.classify_prompt(note),
            schema=ClassificationReply,
        )
    except Exception as exc:  # noqa: BLE001 — any adapter failure → fallback
        return _fallback(f"adapter error: {exc}")

    try:
        data = json.loads(result.text)
        if not isinstance(data, dict):
            return _fallback("reply was not a JSON object")
        data = _normalize(data)
        if data.get("subsystem") not in _SUBSYSTEMS:
            return _fallback(f"unknown subsystem: {data.get('subsystem')!r}")
        if data.get("severity") not in _SEVERITIES:
            return _fallback(f"unknown severity: {data.get('severity')!r}")
        reply = ClassificationReply.model_validate(data)
        return Classification(
            subsystem=reply.subsystem,
            severity=reply.severity,
            rationale=reply.rationale,
            fallback_used=False,
            fallback_reason=None,
        )
    except (json.JSONDecodeError, ValidationError, TypeError, KeyError) as exc:
        return _fallback(f"invalid classification reply: {exc}")
