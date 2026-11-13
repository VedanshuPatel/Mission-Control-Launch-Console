"""Launch limit checks — verdict and violations from readings only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Violation:
    reading: str
    value: float
    limit: str
    message: str


@dataclass(frozen=True)
class LimitResult:
    verdict: Literal["go", "no_go"]
    violations: list[Violation]


def evaluate_limits(wind_knots: float, temp_c: float, fuel_pct: float) -> LimitResult:
    """Return go/no_go from readings alone. No access to note or model output."""
    violations: list[Violation] = []

    if wind_knots > 25:
        violations.append(
            Violation(
                reading="wind_knots",
                value=float(wind_knots),
                limit="<= 25",
                message=f"wind_knots {wind_knots} exceeds limit of 25 knots",
            )
        )

    if temp_c < 4:
        violations.append(
            Violation(
                reading="temp_c",
                value=float(temp_c),
                limit=">= 4",
                message=f"temp_c {temp_c} is below limit of 4 C",
            )
        )

    if fuel_pct < 98:
        violations.append(
            Violation(
                reading="fuel_pct",
                value=float(fuel_pct),
                limit="98..100",
                message=f"fuel_pct {fuel_pct} is below limit of 98 percent",
            )
        )
    elif fuel_pct > 100:
        violations.append(
            Violation(
                reading="fuel_pct",
                value=float(fuel_pct),
                limit="98..100",
                message=f"fuel_pct {fuel_pct} exceeds limit of 100 percent",
            )
        )

    verdict: Literal["go", "no_go"] = "no_go" if violations else "go"
    return LimitResult(verdict=verdict, violations=violations)
