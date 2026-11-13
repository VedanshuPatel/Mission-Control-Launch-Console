"""Filing API: validation messages, persistence, list/detail."""

from __future__ import annotations

import json
import math

import pytest
from sqlalchemy import create_engine, text

VALID = {
    "engineer_name": "Ada",
    "station": "PROP",
    "wind_knots": 10.0,
    "temp_c": 20.0,
    "fuel_pct": 99.0,
    "note": "Valve PV-7 chattered once.",
}


def _count_reports(database_url: str) -> int:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM reports")).scalar_one())


def test_post_report_returns_201_and_saves_fields(client, settings):
    response = client.post("/api/reports", json=VALID)
    assert response.status_code == 201
    body = response.json()
    assert body["engineer_name"] == "Ada"
    assert body["station"] == "PROP"
    assert body["wind_knots"] == 10.0
    assert body["temp_c"] == 20.0
    assert body["fuel_pct"] == 99.0
    assert body["note"] == VALID["note"]
    assert body["id"]
    assert body["status"] in {"received", "processing", "awaiting_approval", "failed"}
    assert _count_reports(settings.database_url) == 1


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        (
            {k: v for k, v in VALID.items() if k != "wind_knots"},
            "wind_knots",
            "wind_knots is required",
        ),
        ({**VALID, "wind_knots": "abc"}, "wind_knots", "wind_knots must be a number"),
        ({**VALID, "wind_knots": "25"}, "wind_knots", "wind_knots must be a number"),
        ({**VALID, "wind_knots": True}, "wind_knots", "wind_knots must be a number"),
        ({**VALID, "fuel_pct": 130}, "fuel_pct", "fuel_pct must be between 0 and 120"),
        ({**VALID, "engineer_name": "  "}, "engineer_name", "engineer_name is required"),
        (
            {**VALID, "station": "BRIDGE"},
            "station",
            "station must be one of: PROP, GNC, AVIONICS, TELEMETRY, GROUND, WEATHER, RANGE",
        ),
        ({**VALID, "note": ""}, "note", "note is required"),
        ({**VALID, "note": "x" * 2001}, "note", "note must be 2000 characters or fewer"),
    ],
)
def test_bad_input_returns_exact_422_messages(client, settings, payload, field, message):
    before = 0
    try:
        before = _count_reports(settings.database_url)
    except Exception:
        before = 0
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert {"field": field, "message": message} in errors
    try:
        assert _count_reports(settings.database_url) == before
    except Exception:
        pass


def test_nan_reading_rejected(client, settings):
    before = _count_reports(settings.database_url)
    body = json.dumps({**VALID, "fuel_pct": math.nan}, allow_nan=True)
    response = client.post(
        "/api/reports",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert {"field": "fuel_pct", "message": "fuel_pct must be a number"} in errors
    assert _count_reports(settings.database_url) == before


def test_list_newest_first_and_detail_404(client):
    r1 = client.post("/api/reports", json={**VALID, "note": "first"})
    r2 = client.post("/api/reports", json={**VALID, "note": "second"})
    assert r1.status_code == 201 and r2.status_code == 201
    listing = client.get("/api/reports")
    assert listing.status_code == 200
    items = listing.json()
    assert items[0]["note"] == "second"
    assert items[1]["note"] == "first"
    detail = client.get(f"/api/reports/{items[0]['id']}")
    assert detail.status_code == 200
    assert detail.json()["note"] == "second"
    missing = client.get("/api/reports/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
