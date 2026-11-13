"""Human-only briefing approval — the only writer of status=approved."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.reports import _report_out, get_db
from app.orm import Report, TraceStep
from app.schemas import ApproveIn, ReportOut

router = APIRouter(prefix="/api/reports", tags=["approvals"])


@router.post("/{report_id}/briefing/approve", response_model=ReportOut)
def approve_briefing(
    report_id: str,
    payload: ApproveIn,
    request: Request,
    db: Session = Depends(get_db),
) -> ReportOut:
    report = db.scalar(
        select(Report)
        .where(Report.id == report_id)
        .options(selectinload(Report.briefing), selectinload(Report.trace_steps))
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status == "processing" or report.briefing is None:
        raise HTTPException(status_code=409, detail="Briefing is not pending")
    if report.briefing.status != "pending":
        raise HTTPException(status_code=409, detail="Briefing is not pending")
    if report.needs_human_review and not payload.acknowledge_flags:
        return JSONResponse(
            status_code=422,
            content={
                "errors": [
                    {
                        "field": "acknowledge_flags",
                        "message": "acknowledge_flags is required when needs_human_review is true",
                    }
                ]
            },
        )

    now = datetime.now(UTC)
    report.briefing.status = "approved"
    report.briefing.approved_by = payload.approver_name
    report.briefing.approved_at = now
    report.status = "approved"

    seq = max((s.seq for s in report.trace_steps), default=0) + 1
    db.add(
        TraceStep(
            id=str(uuid.uuid4()),
            report_id=report_id,
            seq=seq,
            name="human_approval",
            kind="human",
            model=None,
            input_tokens=0,
            output_tokens=0,
            cost_usd="0.000000",
            started_at=now,
            ended_at=now,
            status="ok",
            summary=f"Approved by {payload.approver_name}",
            detail={"approver_name": payload.approver_name},
        )
    )
    db.commit()
    db.refresh(report)
    report = db.scalar(
        select(Report)
        .where(Report.id == report_id)
        .options(selectinload(Report.briefing), selectinload(Report.trace_steps))
    )
    assert report is not None
    return _report_out(report)
