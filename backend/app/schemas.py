"""Pydantic schemas for API and model structured output."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STATIONS = ("PROP", "GNC", "AVIONICS", "TELEMETRY", "GROUND", "WEATHER", "RANGE")

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


def _require_finite_number(value: Any, field_name: str) -> float:
    if value is None:
        raise ValueError(f"{field_name} is required")
    if isinstance(value, bool) or isinstance(value, str):
        raise ValueError(f"{field_name} must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be a number")
    return number


class ReportIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    engineer_name: str
    station: str
    wind_knots: float
    temp_c: float
    fuel_pct: float
    note: str

    @field_validator("wind_knots", mode="before")
    @classmethod
    def _wind(cls, value: Any) -> float:
        number = _require_finite_number(value, "wind_knots")
        if number < 0 or number > 200:
            raise ValueError("wind_knots must be between 0 and 200")
        return number

    @field_validator("temp_c", mode="before")
    @classmethod
    def _temp(cls, value: Any) -> float:
        number = _require_finite_number(value, "temp_c")
        if number < -100 or number > 100:
            raise ValueError("temp_c must be between -100 and 100")
        return number

    @field_validator("fuel_pct", mode="before")
    @classmethod
    def _fuel(cls, value: Any) -> float:
        number = _require_finite_number(value, "fuel_pct")
        if number < 0 or number > 120:
            raise ValueError("fuel_pct must be between 0 and 120")
        return number

    @field_validator("engineer_name")
    @classmethod
    def _name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("engineer_name is required")
        value = value.strip()
        if len(value) > 80:
            raise ValueError("engineer_name must be 80 characters or fewer")
        return value

    @field_validator("station")
    @classmethod
    def _station(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in STATIONS:
            raise ValueError(
                "station must be one of: PROP, GNC, AVIONICS, TELEMETRY, GROUND, WEATHER, RANGE"
            )
        return value

    @field_validator("note")
    @classmethod
    def _note(cls, value: str) -> str:
        if value is None or not str(value).strip():
            raise ValueError("note is required")
        value = str(value).strip()
        if len(value) > 2000:
            raise ValueError("note must be 2000 characters or fewer")
        return value


class TraceStepOut(BaseModel):
    seq: int
    name: str
    kind: str
    model: str | None = None
    input_tokens: int
    output_tokens: int
    cost_usd: str
    started_at: datetime
    ended_at: datetime
    status: str
    summary: str
    detail: dict | None = None


class BriefingOut(BaseModel):
    text: str
    rounds_used: int
    review_passed: bool
    last_feedback: str
    status: str
    approved_by: str | None = None
    approved_at: datetime | None = None


class ReportOut(BaseModel):
    id: str
    created_at: datetime
    engineer_name: str
    station: str
    wind_knots: float
    temp_c: float
    fuel_pct: float
    note: str
    status: str
    error: str | None = None
    subsystem: str | None = None
    model_severity: str | None = None
    effective_severity: str | None = None
    classification_fallback: bool = False
    verdict: str | None = None
    violations: list | None = None
    brief_by_minutes: int | None = None
    brief_by_at: datetime | None = None
    flags: dict | None = None
    needs_human_review: bool = False
    review_reasons: list | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cost_usd: str = "0.000000"
    briefing: BriefingOut | None = None
    trace_steps: list[TraceStepOut] = Field(default_factory=list)


class ApproveIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    approver_name: str
    acknowledge_flags: bool = False

    @field_validator("approver_name")
    @classmethod
    def _approver(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("approver_name is required")
        value = value.strip()
        if len(value) > 80:
            raise ValueError("approver_name must be 80 characters or fewer")
        return value

    @model_validator(mode="after")
    def _ok(self) -> ApproveIn:
        return self
