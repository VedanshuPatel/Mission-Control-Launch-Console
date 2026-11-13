"""FastAPI application factory. Serves API and (later) the built frontend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.errors import register_exception_handlers
from app.api.reports import router as reports_router
from app.config import Settings
from app.db import init_db, make_engine, make_session_factory
from app.domain.cost import PRICES, UnknownModelPrice
from app.llm.factory import ensure_llm
from app.orm import Report

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _stub_process_report(session_factory):  # noqa: ANN001
    """Placeholder processor used until the orchestrator lands (4b)."""

    def process(report_id: str) -> None:
        session = session_factory()
        try:
            report = session.get(Report, report_id)
            if report is None:
                return
            report.status = "awaiting_approval"
            session.commit()
        finally:
            session.close()

    return process


def create_app(settings: Settings | None = None, llm: Any = None) -> FastAPI:
    settings = settings or Settings()
    # Fail fast if the configured model has no price entry.
    priced_model = (
        "fake-model" if settings.resolved_provider() == "fake" else settings.gemini_model
    )
    if priced_model not in PRICES:
        raise UnknownModelPrice(priced_model)

    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    init_db(engine)

    app = FastAPI(title="Mission Control", version="0.1.0")
    app.state.settings = settings
    app.state.llm = ensure_llm(settings, llm)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.process_report = _stub_process_report(session_factory)

    register_exception_handlers(app)
    app.include_router(reports_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "provider": settings.resolved_provider(),
        }

    if FRONTEND_DIST.is_dir():
        assets = FRONTEND_DIST / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()
