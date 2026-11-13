"""Brief-by timing from effective severity — plain code only."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

Severity = Literal["low", "medium", "high"]

_MINUTES: dict[Severity, int] = {
    "high": 5,
    "medium": 15,
    "low": 30,
}


def effective_severity(model_severity: Severity, has_violation: bool) -> Severity:
    """Any launch-limit violation raises severity to high."""
    if has_violation:
        return "high"
    return model_severity


def brief_minutes(severity: Severity) -> int:
    return _MINUTES[severity]


def brief_by_at(created_at: datetime, minutes: int) -> datetime:
    return created_at + timedelta(minutes=minutes)
