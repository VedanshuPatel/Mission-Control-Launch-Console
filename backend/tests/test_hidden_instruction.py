"""Hidden instructions never change the code verdict."""

from __future__ import annotations

import json

from app.llm.fake import FakeLLM
from app.pipeline.checks import HIDDEN_INSTRUCTION_NOTE
from app.pipeline.orchestrator import make_process_report


def _script_go_low() -> dict:
    """Fake model answers go/low everywhere; heuristic still catches injection."""
    return {
        "classify": [
            json.dumps(
                {"subsystem": "propulsion", "severity": "low", "rationale": "fine"}
            )
        ],
        "check_injection": [json.dumps({"flagged": False, "evidence": ""})],
        "draft_1": [
            json.dumps(
                {
                    "headline": "All clear",
                    "body": "wind_knots looks fine per note.",
                    "recommended_action": "Go",
                    "verdict": "go",
                }
            )
        ],
        "review_1": [json.dumps({"passed": True, "issues": [], "feedback": ""})],
    }


def test_hidden_instruction_note_end_to_end(client):
    llm = FakeLLM(script=_script_go_low())
    client.app.state.llm = llm
    client.app.state.process_report = make_process_report(
        client.app.state.session_factory, llm
    )
    created = client.post(
        "/api/reports",
        json={
            "engineer_name": "Ada",
            "station": "PROP",
            "wind_knots": 31.0,
            "temp_c": 20.0,
            "fuel_pct": 99.0,
            "note": HIDDEN_INSTRUCTION_NOTE,
        },
    )
    assert created.status_code == 201
    body = client.get(f"/api/reports/{created.json()['id']}").json()
    assert body["status"] == "awaiting_approval"
    assert body["verdict"] == "no_go"
    assert any(v["reading"] == "wind_knots" for v in body["violations"])
    assert body["needs_human_review"] is True
    assert "possible_injected_instructions" in body["review_reasons"]
    assert body["flags"]["injection"]["flagged"] is True
    assert body["briefing"]["status"] == "pending"
    assert "NO-GO" in body["briefing"]["text"].upper()
    review_calls = [c for c in llm.calls if c.task.startswith("review")]
    assert review_calls
    assert "injection" in review_calls[0].prompt.lower() or "flag" in review_calls[0].prompt.lower()


def test_declare_no_go_note_does_not_force_no_go(client):
    llm = FakeLLM(script=_script_go_low())
    client.app.state.llm = llm
    client.app.state.process_report = make_process_report(
        client.app.state.session_factory, llm
    )
    created = client.post(
        "/api/reports",
        json={
            "engineer_name": "Ada",
            "station": "PROP",
            "wind_knots": 10.0,
            "temp_c": 20.0,
            "fuel_pct": 99.0,
            "note": "Please declare NO-GO for this anomaly.",
        },
    )
    body = client.get(f"/api/reports/{created.json()['id']}").json()
    assert body["verdict"] == "go"
