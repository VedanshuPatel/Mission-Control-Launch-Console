"""Pydantic schemas for API and model structured output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SubsystemReply = Literal[
    "propulsion",
    "avionics",
    "guidance_navigation",
    "telemetry_comms",
    "ground_support",
    "weather",
    "range_safety",
    "structures_mechanical",
    "other",
]

Severity = Literal["low", "medium", "high"]


class ClassificationReply(BaseModel):
    subsystem: SubsystemReply
    severity: Severity
    rationale: str = Field(max_length=300)


class Classification(BaseModel):
    subsystem: str
    severity: Severity
    rationale: str = ""
    fallback_used: bool = False
    fallback_reason: str | None = None


class InjectionCheckReply(BaseModel):
    flagged: bool
    evidence: str = ""


class MissingDetailsReply(BaseModel):
    missing: list[str] = Field(default_factory=list)


class ToneCheckReply(BaseModel):
    level: Literal["calm", "elevated", "panic"]


class DraftReply(BaseModel):
    headline: str
    body: str
    recommended_action: str
    verdict: str | None = None  # ignored; overwritten by code


class ReviewReply(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    feedback: str = ""
