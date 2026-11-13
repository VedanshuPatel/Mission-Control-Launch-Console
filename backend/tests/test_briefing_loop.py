"""Draft → review loop: max 3 rounds, feedback forward, code verdict header."""

from __future__ import annotations

import json

import pytest

from app.llm.fake import FakeLLM
from app.pipeline.briefing import draft_briefing
from app.schemas import Classification


def _facts(**overrides):
    base = {
        "verdict": "no_go",
        "violations": [
            {
                "reading": "wind_knots",
                "value": 31.0,
                "limit": "<= 25",
                "message": "wind_knots 31 exceeds limit of 25 knots",
            }
        ],
        "readings": {"wind_knots": 31.0, "temp_c": 20.0, "fuel_pct": 99.0},
        "classification": Classification(
            subsystem="propulsion", severity="high", rationale="wind"
        ),
        "flags": {"injection_flagged": False},
        "brief_by": "5 minutes",
        "note": "Valve PV-7 chattered.",
    }
    base.update(overrides)
    return base


def _draft(body: str, verdict: str | None = None) -> str:
    payload = {
        "headline": "Brief",
        "body": body,
        "recommended_action": "Hold",
    }
    if verdict is not None:
        payload["verdict"] = verdict
    return json.dumps(payload)


def _review(passed: bool, feedback: str = "") -> str:
    return json.dumps({"passed": passed, "issues": [], "feedback": feedback})


GOOD_BODY = (
    "Wind reading wind_knots is outside limits. Valve PV-7 chatter noted. "
    "Recommend hold for Flight Director review."
)


@pytest.mark.asyncio
async def test_reviewer_passes_on_round_1():
    llm = FakeLLM(
        script={
            "draft_1": [_draft(GOOD_BODY)],
            "review_1": [_review(True)],
        }
    )
    result = await draft_briefing(llm, facts=_facts())
    assert result.rounds_used == 1
    assert result.review_passed is True
    assert result.status == "pending"
    drafts = [c for c in llm.calls if c.task.startswith("draft")]
    reviews = [c for c in llm.calls if c.task.startswith("review")]
    assert len(drafts) == 1 and len(reviews) == 1


@pytest.mark.asyncio
async def test_reviewer_passes_on_round_2():
    llm = FakeLLM(
        script={
            "draft_1": [_draft(GOOD_BODY)],
            "review_1": [_review(False, feedback="MENTION VALVE PV-7")],
            "draft_2": [_draft(GOOD_BODY + " Valve PV-7 secured.")],
            "review_2": [_review(True)],
        }
    )
    result = await draft_briefing(llm, facts=_facts())
    assert result.rounds_used == 2
    assert result.review_passed is True
    drafts = [c for c in llm.calls if c.task.startswith("draft")]
    reviews = [c for c in llm.calls if c.task.startswith("review")]
    assert len(drafts) == 2 and len(reviews) == 2


@pytest.mark.asyncio
async def test_always_fails_stops_at_three_rounds():
    llm = FakeLLM(
        script={
            "draft_1": [_draft(GOOD_BODY)],
            "review_1": [_review(False, "a")],
            "draft_2": [_draft(GOOD_BODY)],
            "review_2": [_review(False, "b")],
            "draft_3": [_draft(GOOD_BODY)],
            "review_3": [_review(False, "c")],
        }
    )
    result = await draft_briefing(llm, facts=_facts())
    assert result.rounds_used == 3
    assert result.review_passed is False
    assert result.text  # still produced
    assert result.status == "pending"
    drafts = [c for c in llm.calls if c.task.startswith("draft")]
    reviews = [c for c in llm.calls if c.task.startswith("review")]
    assert len(drafts) == 3 and len(reviews) == 3


@pytest.mark.asyncio
async def test_feedback_flows_to_next_draft_prompt():
    llm = FakeLLM(
        script={
            "draft_1": [_draft(GOOD_BODY)],
            "review_1": [_review(False, feedback="MENTION VALVE PV-7")],
            "draft_2": [_draft(GOOD_BODY + " Valve PV-7")],
            "review_2": [_review(True)],
        }
    )
    await draft_briefing(llm, facts=_facts())
    draft2 = next(c for c in llm.calls if c.task == "draft_2")
    assert "MENTION VALVE PV-7" in draft2.prompt


@pytest.mark.asyncio
async def test_body_over_120_words_fails_code_check():
    long_body = " ".join(["word"] * 121) + " wind_knots"
    llm = FakeLLM(
        script={
            "draft_1": [_draft(long_body)],
            "review_1": [_review(True)],  # model passes; code must fail
            "draft_2": [_draft(GOOD_BODY)],
            "review_2": [_review(True)],
        }
    )
    result = await draft_briefing(llm, facts=_facts())
    assert result.rounds_used == 2
    assert result.review_passed is True


@pytest.mark.asyncio
async def test_header_uses_code_verdict_not_draft_claim():
    llm = FakeLLM(
        script={
            "draft_1": [_draft(GOOD_BODY, verdict="go")],
            "review_1": [_review(True)],
        }
    )
    result = await draft_briefing(llm, facts=_facts(verdict="no_go"))
    assert "NO-GO" in result.text.upper() or "NO_GO" in result.text.upper()
    assert "wind_knots" in result.text


@pytest.mark.asyncio
async def test_all_invalid_drafts_use_template():
    llm = FakeLLM(
        script={
            "draft_1": ["not-json"],
            "review_1": [_review(False)],
            "draft_2": ["still-bad"],
            "review_2": [_review(False)],
            "draft_3": ["{}"],
            "review_3": [_review(False)],
        }
    )
    result = await draft_briefing(llm, facts=_facts())
    assert result.review_passed is False
    assert result.used_template is True
    assert "NO-GO" in result.text.upper() or "NO_GO" in result.text.upper()


@pytest.mark.asyncio
async def test_pipeline_never_sets_approved():
    llm = FakeLLM(
        script={
            "draft_1": [_draft(GOOD_BODY)],
            "review_1": [_review(True)],
        }
    )
    result = await draft_briefing(llm, facts=_facts())
    assert result.status == "pending"
    assert result.status != "approved"


@pytest.mark.asyncio
async def test_body_missing_violation_reading_fails_code_check():
    body = "Anomaly noted. Recommend hold for review."  # no wind_knots
    llm = FakeLLM(
        script={
            "draft_1": [_draft(body)],
            "review_1": [_review(True)],
            "draft_2": [_draft(GOOD_BODY)],
            "review_2": [_review(True)],
        }
    )
    result = await draft_briefing(llm, facts=_facts())
    assert result.rounds_used == 2


@pytest.mark.asyncio
async def test_invalid_reviewer_json_counts_as_failed():
    llm = FakeLLM(
        script={
            "draft_1": [_draft(GOOD_BODY)],
            "review_1": ["not-json"],
            "draft_2": [_draft(GOOD_BODY)],
            "review_2": [_review(True)],
        }
    )
    result = await draft_briefing(llm, facts=_facts())
    assert result.rounds_used == 2
    assert result.review_passed is True


@pytest.mark.asyncio
async def test_previous_draft_kept_when_later_draft_invalid():
    llm = FakeLLM(
        script={
            "draft_1": [_draft(GOOD_BODY)],
            "review_1": [_review(False, "fix it")],
            "draft_2": ["not-json"],
            "review_2": [_review(False)],
            "draft_3": [_draft(GOOD_BODY + " Fixed.")],
            "review_3": [_review(True)],
        }
    )
    await draft_briefing(llm, facts=_facts())
    draft3 = next(c for c in llm.calls if c.task == "draft_3")
    assert "Previous draft JSON" in draft3.prompt
    assert "wind_knots" in draft3.prompt
