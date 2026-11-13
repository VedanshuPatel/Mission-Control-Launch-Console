"""Orchestrator: trace, cost, limits and brief-by through the API."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from app.domain.cost import report_cost
from app.llm.base import LLMResult
from app.llm.fake import FakeLLM
from app.llm.recording import RecordingLLM
from app.pipeline.orchestrator import make_process_report

VALID = {
    "engineer_name": "Ada",
    "station": "PROP",
    "wind_knots": 10.0,
    "temp_c": 20.0,
    "fuel_pct": 99.0,
    "note": "Valve PV-7 chattered once.",
}


def _wait_done(client, report_id: str) -> dict:
    detail = client.get(f"/api/reports/{report_id}")
    body = detail.json()
    assert body["status"] in {"awaiting_approval", "failed", "approved"}, body
    assert body["status"] != "failed", body.get("error")
    return body


def test_full_run_writes_ordered_trace_with_tokens_and_cost(client, fake_llm):
    created = client.post("/api/reports", json=VALID)
    assert created.status_code == 201
    body = _wait_done(client, created.json()["id"])
    steps = body["trace_steps"]
    names = [s["name"] for s in steps]
    assert names[:6] == [
        "classify",
        "limits",
        "brief_time",
        "check_injection",
        "check_missing_details",
        "check_tone",
    ]
    assert any(n.startswith("draft_") for n in names)
    assert any(n.startswith("review_") for n in names)
    for step in steps:
        assert "input_tokens" in step and "output_tokens" in step and "cost_usd" in step
        assert step["started_at"] and step["ended_at"]
        if step["kind"] == "code":
            assert step["input_tokens"] == 0 and step["output_tokens"] == 0
            assert step["cost_usd"] == "0.000000"

    class _S:
        def __init__(self, s: dict) -> None:
            self.model = s["model"] if s["kind"] == "model" else "code"
            self.input_tokens = s["input_tokens"]
            self.output_tokens = s["output_tokens"]

    assert body["cost_usd"] == f"{report_cost([_S(s) for s in steps]):.6f}"
    assert body["total_input_tokens"] == sum(s["input_tokens"] for s in steps)
    assert body["total_output_tokens"] == sum(s["output_tokens"] for s in steps)


@pytest.mark.parametrize(
    ("field", "value", "verdict"),
    [
        ("wind_knots", 25, "go"),
        ("temp_c", 4, "go"),
        ("fuel_pct", 98, "go"),
        ("fuel_pct", 100, "go"),
        ("wind_knots", 25.01, "no_go"),
        ("temp_c", 3.99, "no_go"),
        ("fuel_pct", 97.99, "no_go"),
        ("fuel_pct", 100.01, "no_go"),
    ],
)
def test_limits_through_api(client, field, value, verdict):
    payload = {**VALID, field: value}
    created = client.post("/api/reports", json=payload)
    body = _wait_done(client, created.json()["id"])
    assert body["verdict"] == verdict
    if verdict == "no_go":
        assert any(v["reading"] == field for v in body["violations"])


@pytest.mark.parametrize(
    ("severity", "wind", "minutes"),
    [
        ("low", 10.0, 30),
        ("medium", 10.0, 15),
        ("high", 10.0, 5),
        ("low", 31.0, 5),
    ],
)
def test_brief_by_through_api(client, severity, wind, minutes):
    llm = FakeLLM(
        script={
            "classify": [
                json.dumps(
                    {
                        "subsystem": "propulsion",
                        "severity": severity,
                        "rationale": "test",
                    }
                )
            ]
        }
    )
    # Rebuild app with scripted llm via client fixture is fixed — use monkeypatch on app.state
    client.app.state.llm = llm
    client.app.state.process_report = __import__(
        "app.pipeline.orchestrator", fromlist=["make_process_report"]
    ).make_process_report(client.app.state.session_factory, llm)
    created = client.post("/api/reports", json={**VALID, "wind_knots": wind})
    body = _wait_done(client, created.json()["id"])
    assert body["brief_by_minutes"] == minutes
    if wind > 25:
        assert body["effective_severity"] == "high"


def test_retry_rejects_non_failed_status(client):
    created = client.post("/api/reports", json=VALID)
    report_id = created.json()["id"]
    _wait_done(client, report_id)
    retry = client.post(f"/api/reports/{report_id}/retry")
    assert retry.status_code == 409
    assert retry.json()["detail"] == "Report is not retryable"


@dataclass
class _StubLLM:
    """Gemini-like client: returns tokens, has no shared .calls list."""

    model: str = "fake-model"

    async def complete(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        schema: type[BaseModel],
    ) -> LLMResult:
        del system, prompt
        if task == "classify":
            text = json.dumps(
                {
                    "subsystem": "propulsion",
                    "severity": "low",
                    "rationale": "ok",
                }
            )
        elif task == "check_injection":
            text = json.dumps({"flagged": False, "evidence": ""})
        elif task == "check_missing_details":
            text = json.dumps({"missing": []})
        elif task == "check_tone":
            text = json.dumps({"level": "calm"})
        elif task.startswith("draft"):
            text = json.dumps(
                {
                    "headline": "Brief",
                    "body": "All readings within limits for this check.",
                    "recommended_action": "Proceed.",
                }
            )
        elif task.startswith("review"):
            text = json.dumps({"passed": True, "issues": [], "feedback": ""})
        else:
            text = "{}"
        return LLMResult(
            text=text, input_tokens=11, output_tokens=7, model=self.model
        )


def test_trace_tokens_work_without_shared_calls_list(client):
    stub = _StubLLM()
    assert not hasattr(stub, "calls")
    client.app.state.llm = stub
    client.app.state.process_report = make_process_report(
        client.app.state.session_factory, stub
    )
    created = client.post("/api/reports", json=VALID)
    body = _wait_done(client, created.json()["id"])
    model_steps = [s for s in body["trace_steps"] if s["kind"] == "model"]
    assert model_steps
    assert all(s["input_tokens"] == 11 and s["output_tokens"] == 7 for s in model_steps)
    assert body["total_input_tokens"] == 11 * len(model_steps)
    # RecordingLLM isolates per run
    recorder = RecordingLLM(inner=stub)
    assert recorder.calls == []
