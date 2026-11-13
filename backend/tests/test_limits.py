"""Launch limits: plain code only, exact-on and just-past boundaries."""

from __future__ import annotations

import inspect

import pytest

from app.domain.limits import evaluate_limits


def test_nominal_readings_are_go():
    result = evaluate_limits(wind_knots=10.0, temp_c=20.0, fuel_pct=99.0)
    assert result.verdict == "go"
    assert result.violations == []


@pytest.mark.parametrize(
    ("wind_knots", "temp_c", "fuel_pct"),
    [
        (25, 20.0, 99.0),
        (25.0, 20.0, 99.0),
        (10.0, 4, 99.0),
        (10.0, 4.0, 99.0),
        (10.0, 20.0, 98),
        (10.0, 20.0, 98.0),
        (10.0, 20.0, 100),
        (10.0, 20.0, 100.0),
        (25.0, 4.0, 98.0),
        (25.0, 4.0, 100.0),
    ],
)
def test_exactly_on_each_limit_passes(wind_knots, temp_c, fuel_pct):
    result = evaluate_limits(wind_knots=wind_knots, temp_c=temp_c, fuel_pct=fuel_pct)
    assert result.verdict == "go"
    assert result.violations == []


@pytest.mark.parametrize(
    ("wind_knots", "temp_c", "fuel_pct", "reading", "value", "limit", "message"),
    [
        (
            25.01,
            20.0,
            99.0,
            "wind_knots",
            25.01,
            "<= 25",
            "wind_knots 25.01 exceeds limit of 25 knots",
        ),
        (26, 20.0, 99.0, "wind_knots", 26.0, "<= 25", "wind_knots 26 exceeds limit of 25 knots"),
        (10.0, 3.99, 99.0, "temp_c", 3.99, ">= 4", "temp_c 3.99 is below limit of 4 C"),
        (10.0, 3, 99.0, "temp_c", 3.0, ">= 4", "temp_c 3 is below limit of 4 C"),
        (
            10.0,
            20.0,
            97.99,
            "fuel_pct",
            97.99,
            "98..100",
            "fuel_pct 97.99 is below limit of 98 percent",
        ),
        (10.0, 20.0, 97, "fuel_pct", 97.0, "98..100", "fuel_pct 97 is below limit of 98 percent"),
        (
            10.0,
            20.0,
            100.01,
            "fuel_pct",
            100.01,
            "98..100",
            "fuel_pct 100.01 exceeds limit of 100 percent",
        ),
    ],
)
def test_just_past_each_limit_fails(
    wind_knots, temp_c, fuel_pct, reading, value, limit, message
):
    result = evaluate_limits(wind_knots=wind_knots, temp_c=temp_c, fuel_pct=fuel_pct)
    assert result.verdict == "no_go"
    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.reading == reading
    assert violation.value == value
    assert violation.limit == limit
    assert violation.message == message


def test_multiple_violations_reported_in_wind_temp_fuel_order():
    result = evaluate_limits(wind_knots=31.0, temp_c=2.0, fuel_pct=90.0)
    assert result.verdict == "no_go"
    assert [v.reading for v in result.violations] == ["wind_knots", "temp_c", "fuel_pct"]
    assert result.violations[0].message == "wind_knots 31 exceeds limit of 25 knots"


def test_evaluate_limits_signature_accepts_only_three_readings():
    sig = inspect.signature(evaluate_limits)
    assert list(sig.parameters) == ["wind_knots", "temp_c", "fuel_pct"]
