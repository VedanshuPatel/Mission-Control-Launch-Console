"""Brief-by time follows effective severity; violations raise to high."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.brief_time import brief_by_at, brief_minutes, effective_severity


@pytest.mark.parametrize(
    ("severity", "minutes"),
    [
        ("high", 5),
        ("medium", 15),
        ("low", 30),
    ],
)
def test_brief_minutes_by_severity(severity, minutes):
    assert brief_minutes(severity) == minutes


@pytest.mark.parametrize("model_severity", ["low", "medium", "high"])
def test_any_violation_raises_effective_severity_to_high(model_severity):
    assert effective_severity(model_severity, has_violation=True) == "high"
    assert brief_minutes(effective_severity(model_severity, has_violation=True)) == 5


@pytest.mark.parametrize("model_severity", ["low", "medium", "high"])
def test_no_violation_keeps_model_severity(model_severity):
    assert effective_severity(model_severity, has_violation=False) == model_severity


def test_fallback_classification_gives_five_minutes():
    # Fallback classification uses severity high (conservative).
    assert brief_minutes(effective_severity("high", has_violation=False)) == 5


def test_brief_by_at_is_created_at_plus_minutes():
    created = datetime(2026, 11, 13, 14, 0, 0, tzinfo=UTC)
    assert brief_by_at(created, 5) == created + timedelta(minutes=5)
    assert brief_by_at(created, 15) == created + timedelta(minutes=15)
    assert brief_by_at(created, 30) == created + timedelta(minutes=30)
