"""SQLAlchemy ORM models for reports, briefings, and trace steps."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    engineer_name: Mapped[str] = mapped_column(String(80))
    station: Mapped[str] = mapped_column(String(32))
    wind_knots: Mapped[float] = mapped_column(Float)
    temp_c: Mapped[float] = mapped_column(Float)
    fuel_pct: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(32), default="received")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    subsystem: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    effective_severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    classification_fallback: Mapped[bool] = mapped_column(default=False)

    verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    violations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    brief_by_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    brief_by_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    needs_human_review: Mapped[bool] = mapped_column(default=False)
    review_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)

    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[str] = mapped_column(String(32), default="0.000000")

    briefing: Mapped[Briefing | None] = relationship(back_populates="report", uselist=False)
    trace_steps: Mapped[list[TraceStep]] = relationship(
        back_populates="report", order_by="TraceStep.seq"
    )


class Briefing(Base):
    __tablename__ = "briefings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), unique=True)
    text: Mapped[str] = mapped_column(Text, default="")
    rounds_used: Mapped[int] = mapped_column(Integer, default=0)
    review_passed: Mapped[bool] = mapped_column(default=False)
    last_feedback: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    approved_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    report: Mapped[Report] = relationship(back_populates="briefing")


class TraceStep(Base):
    __tablename__ = "trace_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"))
    seq: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))  # code|model|human
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[str] = mapped_column(String(32), default="0.000000")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="ok")
    summary: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    report: Mapped[Report] = relationship(back_populates="trace_steps")
