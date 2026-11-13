"""Draft → review loop (max 3). Never sets status to approved."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.llm.base import LLMClient
from app.pipeline import prompts
from app.schemas import DraftReply, ReviewReply

_MAX_ROUNDS = 3
_MAX_BODY_WORDS = 120


@dataclass
class BriefingResult:
    text: str
    rounds_used: int
    review_passed: bool
    last_feedback: str
    status: str  # always "pending" from pipeline
    used_template: bool = False
    headline: str = ""
    body: str = ""
    recommended_action: str = ""


def _verdict_label(verdict: str) -> str:
    return "NO-GO" if verdict == "no_go" else "GO"


def _header(facts: dict[str, Any]) -> str:
    verdict = facts.get("verdict", "no_go")
    label = _verdict_label(str(verdict))
    violations = facts.get("violations") or []
    if violations:
        bits = []
        for v in violations:
            if isinstance(v, dict):
                reading = v.get("reading", "?")
                message = v.get("message") or f"{reading} out of limits"
                bits.append(str(message))
            else:
                bits.append(str(getattr(v, "message", v)))
        detail = "; ".join(bits)
        return f"VERDICT: {label} — {detail}"
    return f"VERDICT: {label}"


def _assemble(facts: dict[str, Any], draft: DraftReply) -> str:
    header = _header(facts)
    return (
        f"{header}\n\n{draft.headline}\n\n{draft.body}\n\n"
        f"Recommended action: {draft.recommended_action}"
    )


def _word_count(text: str) -> int:
    return len(text.split())


def _code_check_issues(draft: DraftReply, facts: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if _word_count(draft.body) > _MAX_BODY_WORDS:
        issues.append(f"body exceeds {_MAX_BODY_WORDS} words")
    violations = facts.get("violations") or []
    for v in violations:
        reading = v.get("reading") if isinstance(v, dict) else getattr(v, "reading", None)
        if reading and reading not in draft.body:
            issues.append(f"body must mention violated reading {reading}")
    return issues


def _draft_prompt(
    facts: dict[str, Any],
    *,
    prev: DraftReply | None,
    feedback: str | None,
) -> str:
    parts = [
        "Draft a Flight Director briefing from these facts (code verdict is authoritative):",
        json.dumps(
            {
                "verdict": facts.get("verdict"),
                "violations": facts.get("violations"),
                "readings": facts.get("readings"),
                "classification": (
                    facts["classification"].model_dump()
                    if hasattr(facts.get("classification"), "model_dump")
                    else facts.get("classification")
                ),
                "flags": facts.get("flags"),
                "brief_by": facts.get("brief_by"),
            },
            default=str,
        ),
        prompts.wrap_engineer_note(str(facts.get("note", ""))),
    ]
    if prev is not None:
        parts.append(f"Previous draft JSON: {prev.model_dump_json()}")
    if feedback:
        parts.append(f"Reviewer feedback to address: {feedback}")
    return "\n\n".join(parts)


def _review_prompt(facts: dict[str, Any], draft: DraftReply) -> str:
    facts_json = json.dumps(
        {
            "verdict": facts.get("verdict"),
            "violations": facts.get("violations"),
            "flags": facts.get("flags"),
        },
        default=str,
    )
    return "\n\n".join(
        [
            "Review this draft against facts. Code verdict must be respected.",
            f"Facts: {facts_json}",
            f"Draft: {draft.model_dump_json()}",
            prompts.wrap_engineer_note(str(facts.get("note", ""))),
        ]
    )


def _template_draft(facts: dict[str, Any]) -> DraftReply:
    readings = ", ".join(
        f"{k}={v}" for k, v in (facts.get("readings") or {}).items()
    )
    return DraftReply(
        headline="Template briefing",
        body=(
            f"Automated briefing for verdict {_verdict_label(str(facts.get('verdict')))}. "
            f"Readings: {readings}. Violations listed in the header."
        ),
        recommended_action="Await Flight Director decision.",
    )


async def draft_briefing(llm: LLMClient, *, facts: dict[str, Any]) -> BriefingResult:
    feedback: str | None = None
    prev: DraftReply | None = None
    last_valid: DraftReply | None = None
    last_feedback = ""
    review_passed = False
    rounds_used = 0
    used_template = False

    for round_n in range(1, _MAX_ROUNDS + 1):
        rounds_used = round_n
        draft: DraftReply | None = None
        try:
            raw = await llm.complete(
                task=f"draft_{round_n}",
                system=prompts.DRAFT_SYSTEM,
                prompt=_draft_prompt(facts, prev=prev, feedback=feedback),
                schema=DraftReply,
            )
            draft = DraftReply.model_validate_json(raw.text)
            last_valid = draft
        except (ValidationError, json.JSONDecodeError, ValueError, TypeError):
            feedback = "previous draft was not valid JSON"
            last_feedback = feedback
            # Still run a review slot with failed pass semantics
            try:
                await llm.complete(
                    task=f"review_{round_n}",
                    system=prompts.REVIEW_SYSTEM,
                    prompt="Previous draft was not valid JSON. Mark passed=false.",
                    schema=ReviewReply,
                )
            except Exception:  # noqa: BLE001
                pass
            # Keep prev as the last valid draft (do not wipe with None).
            continue

        code_issues = _code_check_issues(draft, facts)
        passed = False
        review_feedback = ""
        try:
            rev_raw = await llm.complete(
                task=f"review_{round_n}",
                system=prompts.REVIEW_SYSTEM,
                prompt=_review_prompt(facts, draft),
                schema=ReviewReply,
            )
            review = ReviewReply.model_validate_json(rev_raw.text)
            passed = bool(review.passed)
            review_feedback = review.feedback
            if review.issues:
                review_feedback = (
                    (review_feedback + " " if review_feedback else "")
                    + "; ".join(review.issues)
                ).strip()
        except (ValidationError, json.JSONDecodeError, ValueError, TypeError, Exception):
            passed = False
            review_feedback = "reviewer reply was not valid JSON"

        if code_issues:
            passed = False
            review_feedback = (
                (review_feedback + " " if review_feedback else "")
                + "; ".join(code_issues)
            ).strip()

        last_feedback = review_feedback
        if passed:
            review_passed = True
            break
        feedback = review_feedback or "revise the draft"
        prev = draft

    if last_valid is None:
        used_template = True
        last_valid = _template_draft(facts)

    text = _assemble(facts, last_valid)
    return BriefingResult(
        text=text,
        rounds_used=rounds_used,
        review_passed=review_passed,
        last_feedback=last_feedback,
        status="pending",
        used_template=used_template,
        headline=last_valid.headline,
        body=last_valid.body,
        recommended_action=last_valid.recommended_action,
    )
