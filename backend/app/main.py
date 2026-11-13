"""FastAPI application factory. Serves API and (later) the built frontend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.llm.factory import ensure_llm

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(settings: Settings | None = None, llm: Any = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Mission Control", version="0.1.0")
    app.state.settings = settings
    app.state.llm = ensure_llm(settings, llm)

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
