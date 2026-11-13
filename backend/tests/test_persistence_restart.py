"""Reports survive process restart; stale processing is failed and retryable."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import Settings
from app.llm.fake import FakeLLM
from app.main import create_app
from app.orm import Base


VALID = {
    "engineer_name": "Ada",
    "station": "PROP",
    "wind_knots": 10.0,
    "temp_c": 20.0,
    "fuel_pct": 99.0,
    "note": "Restart persistence check.",
}


def test_report_survives_app_restart(tmp_path: Path):
    db_path = tmp_path / "shared.db"
    database_url = f"sqlite:///{db_path}"
    settings_a = Settings(
        llm_provider="fake",
        gemini_api_key="",
        gemini_model="fake-model",
        database_url=database_url,
    )
    app_a = create_app(settings_a, llm=FakeLLM())
    with TestClient(app_a) as client_a:
        created = client_a.post("/api/reports", json=VALID)
        assert created.status_code == 201
        report_id = created.json()["id"]
        fields = created.json()

    # Dispose app A's engine
    engine_a = app_a.state.engine
    engine_a.dispose()
    del app_a

    settings_b = Settings(
        llm_provider="fake",
        gemini_api_key="",
        gemini_model="fake-model",
        database_url=database_url,
    )
    app_b = create_app(settings_b, llm=FakeLLM())
    with TestClient(app_b) as client_b:
        detail = client_b.get(f"/api/reports/{report_id}")
        assert detail.status_code == 200
        body = detail.json()
        for key in ("engineer_name", "station", "wind_knots", "temp_c", "fuel_pct", "note"):
            assert body[key] == fields[key]


def test_startup_marks_stale_processing_failed_and_retry(tmp_path: Path):
    db_path = tmp_path / "stale.db"
    database_url = f"sqlite:///{db_path}"
    # Create schema and a stale processing row without going through the API.
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO reports (
                  id, created_at, engineer_name, station, wind_knots, temp_c, fuel_pct,
                  note, status, error, classification_fallback, needs_human_review,
                  total_input_tokens, total_output_tokens, cost_usd
                ) VALUES (
                  '11111111-1111-1111-1111-111111111111',
                  '2026-01-01T00:00:00+00:00',
                  'Ada', 'PROP', 10.0, 20.0, 99.0,
                  'stale', 'processing', NULL, 0, 0, 0, 0, '0.000000'
                )
                """
            )
        )
    engine.dispose()

    settings = Settings(
        llm_provider="fake",
        gemini_api_key="",
        gemini_model="fake-model",
        database_url=database_url,
    )
    app = create_app(settings, llm=FakeLLM())
    with TestClient(app) as client:
        detail = client.get("/api/reports/11111111-1111-1111-1111-111111111111")
        assert detail.status_code == 200
        assert detail.json()["status"] == "failed"
        assert detail.json()["error"] == "interrupted by restart"
        retry = client.post("/api/reports/11111111-1111-1111-1111-111111111111/retry")
        assert retry.status_code == 202
        after = client.get("/api/reports/11111111-1111-1111-1111-111111111111")
        assert after.json()["status"] in {
            "received",
            "processing",
            "awaiting_approval",
            "failed",
        }
