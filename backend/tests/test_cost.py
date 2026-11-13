"""Report cost is plain Decimal math at paid-tier rates."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from app.config import Settings
from app.domain.cost import PRICES, UnknownModelPrice, report_cost, step_cost


def test_fake_model_step_cost_example():
    assert step_cost("fake-model", 1000, 500) == Decimal("0.002000")


def test_zero_tokens_cost_zero():
    assert step_cost("fake-model", 0, 0) == Decimal("0.000000")


def test_rounding_is_half_up_at_six_decimal_places():
    # gemini-3.8-flash: 2 input tokens * $0.75 / 1M = 0.0000015 → 0.000002
    assert step_cost("gemini-3.8-flash", 2, 0) == Decimal("0.000002")


@dataclass
class _Step:
    model: str | None
    input_tokens: int
    output_tokens: int


def test_report_cost_sums_rounded_step_costs_including_code_at_zero():
    steps = [
        _Step(model="fake-model", input_tokens=1000, output_tokens=500),
        _Step(model="code", input_tokens=0, output_tokens=0),
        _Step(model=None, input_tokens=0, output_tokens=0),
        _Step(model="fake-model", input_tokens=0, output_tokens=0),
    ]
    expected = (
        step_cost("fake-model", 1000, 500)
        + Decimal("0.000000")
        + Decimal("0.000000")
        + step_cost("fake-model", 0, 0)
    )
    assert report_cost(steps) == expected
    assert report_cost(steps) == Decimal("0.002000")


def test_unknown_model_raises():
    with pytest.raises(UnknownModelPrice):
        step_cost("no-such-model", 1, 1)


def test_configured_gemini_model_is_in_prices():
    model = Settings().gemini_model
    assert model == "gemini-3.8-flash"
    assert model in PRICES
