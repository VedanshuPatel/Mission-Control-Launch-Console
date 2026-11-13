"""Run the full report pipeline and persist trace steps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.domain.brief_time import brief_by_at, brief_minutes, effective_severity
from app.domain.cost import report_cost, step_cost
from app.domain.limits import evaluate_limits
from app.llm.base import LLMClient
from app.llm.recording import RecordingLLM
from app.orm import Briefing, Report, TraceStep
from app.pipeline.briefing import draft_briefing
from app.pipeline.checks import run_checks
from app.pipeline.classify import classify_report


def _now() -> datetime:
    return datetime.now(UTC)


def _add_step(
    session: Session,
    *,
    report_id: str,
    seq: int,
    name: str,
    kind: str,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    started_at: datetime,
    ended_at: datetime,
    status: str,
    summary: str,
    detail: dict | None = None,
) -> TraceStep:
    if kind == "model" and model:
        cost = step_cost(model, input_tokens, output_tokens)
    else:
        cost = Decimal("0.000000")
    step = TraceStep(
        id=str(uuid.uuid4()),
        report_id=report_id,
        seq=seq,
        name=name,
        kind=kind,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=f"{cost:.6f}",
        started_at=started_at,
        ended_at=ended_at,
        status=status,
        summary=summary,
        detail=detail,
    )
    session.add(step)
    return step


def _call_tokens(
    llm: RecordingLLM, call_before: int, task: str | None = None
) -> tuple[int, int, str, Any]:
    model = llm.model
    calls = list(llm.calls)[call_before:]
    if task is not None:
        calls = [c for c in calls if c.task == task]
    if not calls:
        return 0, 0, model, None
    c = calls[-1] if task is None else calls[0]
    return c.input_tokens, c.output_tokens, model, c


def make_process_report(session_factory: sessionmaker[Session], llm: LLMClient):
    async def process_report(report_id: str) -> None:
        # Per-run recorder so concurrent reports never share a call log, and
        # Gemini (which has no .calls) still yields tokens into the trace.
        recorder = RecordingLLM(inner=llm)
        await _process(report_id, session_factory, recorder)

    return process_report


async def _process(
    report_id: str, session_factory: sessionmaker[Session], llm: RecordingLLM
) -> None:
    session = session_factory()
    try:
        # Claim only if still queued — blocks duplicate workers from racing.
        claimed = session.execute(
            update(Report)
            .where(Report.id == report_id, Report.status == "received")
            .values(status="processing", error=None)
        )
        session.commit()
        if claimed.rowcount != 1:
            return

        report = session.get(Report, report_id)
        if report is None:
            return

        # Fresh run: drop any leftover steps from a prior attempt.
        session.execute(delete(TraceStep).where(TraceStep.report_id == report_id))
        session.flush()

        seq = 0

        # 1. classify
        before = len(llm.calls)
        started = _now()
        classification = await classify_report(llm, note=report.note)
        ended = _now()
        in_t, out_t, model, call = _call_tokens(llm, before)
        if call is not None:
            started, ended = call.started_at, call.ended_at
        seq += 1
        _add_step(
            session,
            report_id=report_id,
            seq=seq,
            name="classify",
            kind="model",
            model=model,
            input_tokens=in_t,
            output_tokens=out_t,
            started_at=started,
            ended_at=ended,
            status="fallback" if classification.fallback_used else "ok",
            summary=f"{classification.subsystem}/{classification.severity}",
            detail=classification.model_dump(),
        )
        report.subsystem = classification.subsystem
        report.model_severity = classification.severity
        report.classification_fallback = classification.fallback_used

        # 2. limits
        started = _now()
        limits = evaluate_limits(report.wind_knots, report.temp_c, report.fuel_pct)
        ended = _now()
        seq += 1
        _add_step(
            session,
            report_id=report_id,
            seq=seq,
            name="limits",
            kind="code",
            model=None,
            input_tokens=0,
            output_tokens=0,
            started_at=started,
            ended_at=ended,
            status="ok",
            summary=limits.verdict,
            detail={
                "verdict": limits.verdict,
                "violations": [v.__dict__ for v in limits.violations],
            },
        )
        report.verdict = limits.verdict
        report.violations = [v.__dict__ for v in limits.violations]

        # 3. brief_time
        started = _now()
        has_violation = bool(limits.violations)
        eff = effective_severity(classification.severity, has_violation)
        minutes = brief_minutes(eff)
        by_at = brief_by_at(report.created_at, minutes)
        ended = _now()
        seq += 1
        summary = f"{eff}/{minutes}m"
        if has_violation and classification.severity != "high":
            summary += " (raised to high by violation)"
        _add_step(
            session,
            report_id=report_id,
            seq=seq,
            name="brief_time",
            kind="code",
            model=None,
            input_tokens=0,
            output_tokens=0,
            started_at=started,
            ended_at=ended,
            status="ok",
            summary=summary,
            detail={"effective_severity": eff, "minutes": minutes},
        )
        report.effective_severity = eff
        report.brief_by_minutes = minutes
        report.brief_by_at = by_at

        # 4-6 concurrent checks
        before = len(llm.calls)
        checks = await run_checks(llm, note=report.note)
        for name, result_obj in [
            ("check_injection", checks.injection),
            ("check_missing_details", checks.missing),
            ("check_tone", checks.tone),
        ]:
            in_t, out_t, model, call = _call_tokens(llm, before, task=name)
            started = call.started_at if call else _now()
            ended = call.ended_at if call else _now()
            seq += 1
            status = "error" if getattr(result_obj, "check_unavailable", False) else "ok"
            _add_step(
                session,
                report_id=report_id,
                seq=seq,
                name=name,
                kind="model",
                model=model,
                input_tokens=in_t,
                output_tokens=out_t,
                started_at=started,
                ended_at=ended,
                status=status,
                summary=str(result_obj),
                detail=result_obj.__dict__,
            )

        report.flags = {
            "injection": checks.injection.__dict__,
            "missing": checks.missing.__dict__,
            "tone": checks.tone.__dict__,
        }
        report.needs_human_review = checks.needs_human_review
        report.review_reasons = checks.review_reasons

        # draft / review loop
        facts = {
            "verdict": report.verdict,
            "violations": report.violations,
            "readings": {
                "wind_knots": report.wind_knots,
                "temp_c": report.temp_c,
                "fuel_pct": report.fuel_pct,
            },
            "classification": classification,
            "flags": {
                "injection_flagged": checks.injection.flagged,
                "review_reasons": checks.review_reasons,
            },
            "brief_by": f"{minutes} minutes",
            "note": report.note,
        }
        before = len(llm.calls)
        briefing = await draft_briefing(llm, facts=facts)
        for c in list(llm.calls)[before:]:
            seq += 1
            _add_step(
                session,
                report_id=report_id,
                seq=seq,
                name=c.task,
                kind="model",
                model=llm.model,
                input_tokens=c.input_tokens,
                output_tokens=c.output_tokens,
                started_at=c.started_at,
                ended_at=c.ended_at,
                status="ok",
                summary=c.task,
                detail=None,
            )

        if report.briefing is None:
            session.add(
                Briefing(
                    id=str(uuid.uuid4()),
                    report_id=report_id,
                    text=briefing.text,
                    rounds_used=briefing.rounds_used,
                    review_passed=briefing.review_passed,
                    last_feedback=briefing.last_feedback,
                    status="pending",
                )
            )
        else:
            report.briefing.text = briefing.text
            report.briefing.rounds_used = briefing.rounds_used
            report.briefing.review_passed = briefing.review_passed
            report.briefing.last_feedback = briefing.last_feedback
            report.briefing.status = "pending"
            report.briefing.approved_by = None
            report.briefing.approved_at = None

        session.flush()
        steps = session.scalars(
            select(TraceStep)
            .where(TraceStep.report_id == report_id)
            .order_by(TraceStep.seq)
        ).all()

        class _CostStep:
            def __init__(self, model: str | None, inp: int, out: int) -> None:
                self.model = model
                self.input_tokens = inp
                self.output_tokens = out

        cost_steps = [
            _CostStep(
                s.model if s.kind == "model" else "code",
                s.input_tokens,
                s.output_tokens,
            )
            for s in steps
        ]
        total_cost = report_cost(cost_steps)
        report.total_input_tokens = sum(s.input_tokens for s in steps)
        report.total_output_tokens = sum(s.output_tokens for s in steps)
        report.cost_usd = f"{total_cost:.6f}"
        report.status = "awaiting_approval"
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        report = session.get(Report, report_id)
        if report is not None:
            report.status = "failed"
            report.error = str(exc)
            session.commit()
    finally:
        session.close()
