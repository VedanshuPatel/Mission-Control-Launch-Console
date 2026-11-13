"""Report filing, list, detail, and retry endpoints."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.orm import Report
from app.schemas import BriefingOut, ReportIn, ReportOut, TraceStepOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _report_out(report: Report) -> ReportOut:
    briefing = None
    if report.briefing is not None:
        b = report.briefing
        briefing = BriefingOut(
            text=b.text,
            rounds_used=b.rounds_used,
            review_passed=b.review_passed,
            last_feedback=b.last_feedback,
            status=b.status,
            approved_by=b.approved_by,
            approved_at=b.approved_at,
        )
    steps = [
        TraceStepOut(
            seq=s.seq,
            name=s.name,
            kind=s.kind,
            model=s.model,
            input_tokens=s.input_tokens,
            output_tokens=s.output_tokens,
            cost_usd=s.cost_usd,
            started_at=s.started_at,
            ended_at=s.ended_at,
            status=s.status,
            summary=s.summary,
            detail=s.detail,
        )
        for s in (report.trace_steps or [])
    ]
    return ReportOut(
        id=report.id,
        created_at=report.created_at,
        engineer_name=report.engineer_name,
        station=report.station,
        wind_knots=report.wind_knots,
        temp_c=report.temp_c,
        fuel_pct=report.fuel_pct,
        note=report.note,
        status=report.status,
        error=report.error,
        subsystem=report.subsystem,
        model_severity=report.model_severity,
        effective_severity=report.effective_severity,
        classification_fallback=report.classification_fallback,
        verdict=report.verdict,
        violations=report.violations,
        brief_by_minutes=report.brief_by_minutes,
        brief_by_at=report.brief_by_at,
        flags=report.flags,
        needs_human_review=report.needs_human_review,
        review_reasons=report.review_reasons,
        total_input_tokens=report.total_input_tokens,
        total_output_tokens=report.total_output_tokens,
        cost_usd=report.cost_usd,
        briefing=briefing,
        trace_steps=steps,
    )


def get_db(request: Request) -> Session:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@router.post("", status_code=201, response_model=ReportOut)
def create_report(
    payload: ReportIn,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> ReportOut:
    report = Report(
        id=str(uuid.uuid4()),
        created_at=datetime.now(UTC),
        engineer_name=payload.engineer_name,
        station=payload.station,
        wind_knots=payload.wind_knots,
        temp_c=payload.temp_c,
        fuel_pct=payload.fuel_pct,
        note=payload.note,
        status="received",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    report_id = report.id
    out = _report_out(report)
    processor: Callable[..., Any] = request.app.state.process_report
    background.add_task(processor, report_id)
    return out


@router.get("", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db)) -> list[ReportOut]:
    rows = db.scalars(
        select(Report)
        .options(selectinload(Report.briefing), selectinload(Report.trace_steps))
        .order_by(Report.created_at.desc())
    ).all()
    return [_report_out(r) for r in rows]


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db)) -> ReportOut:
    report = db.scalar(
        select(Report)
        .where(Report.id == report_id)
        .options(selectinload(Report.briefing), selectinload(Report.trace_steps))
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_out(report)


@router.post("/{report_id}/retry", status_code=202, response_model=ReportOut)
def retry_report(
    report_id: str,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
) -> ReportOut:
    report = db.scalar(select(Report).where(Report.id == report_id))
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status not in {"failed", "received"}:
        raise HTTPException(status_code=409, detail="Report is not retryable")
    report.status = "received"
    report.error = None
    db.commit()
    db.refresh(report)
    out = _report_out(report)
    processor: Callable[..., Any] = request.app.state.process_report
    background.add_task(processor, report_id)
    return out
