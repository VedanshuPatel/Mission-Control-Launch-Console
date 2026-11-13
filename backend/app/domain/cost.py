"""Token cost estimates at paid-tier list rates (free tier bills $0)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol


class UnknownModelPrice(LookupError):
    """Raised when a model has no entry in PRICES."""


@dataclass(frozen=True)
class Price:
    input_per_mtok: Decimal
    output_per_mtok: Decimal


# Checked 13 Nov 2026 against https://ai.google.dev/gemini-api/docs/pricing
# gemini-3.8-flash paid tier through 31 Dec 2026: $0.75 in / $3.75 out per 1M tokens.
PRICES: dict[str, Price] = {
    "fake-model": Price(
        input_per_mtok=Decimal("1.00"),
        output_per_mtok=Decimal("2.00"),
    ),
    "gemini-3.8-flash": Price(
        input_per_mtok=Decimal("0.75"),
        output_per_mtok=Decimal("3.75"),
    ),
}

_QUANT = Decimal("0.000001")


class CostStep(Protocol):
    model: str | None
    input_tokens: int
    output_tokens: int


def step_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    try:
        price = PRICES[model]
    except KeyError as exc:
        raise UnknownModelPrice(model) from exc

    raw = (Decimal(input_tokens) / Decimal(1_000_000)) * price.input_per_mtok + (
        Decimal(output_tokens) / Decimal(1_000_000)
    ) * price.output_per_mtok
    return raw.quantize(_QUANT, rounding=ROUND_HALF_UP)


def report_cost(steps: list[CostStep] | tuple[CostStep, ...]) -> Decimal:
    total = Decimal("0.000000")
    for step in steps:
        model = step.model
        if not model or model == "code":
            continue
        total += step_cost(model, step.input_tokens, step.output_tokens)
    return total
