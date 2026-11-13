# Tool choices — Mission Control

Stack decisions for Meridian Launch Services' Go/No-Go Launch Console.
Model ID and paid-tier rates are confirmed against Google AI docs when cost
code lands (branch `feature/domain-rules`); free-tier Flash as of Nov 2026
is listed as Gemini 3.8 Flash.

## Back end

**Choice:** Python 3.12 + FastAPI (uv for deps)

**Reason:** Native `async` makes the three concurrent checks a plain
`asyncio.gather`. Pydantic v2 validates both form input and model JSON
replies with the same tool.

**Rejected alternative:** Flask — sync by default, no built-in request
validation, so concurrency and schema checks would be bolted on.

**Customer concern:** Reliability under a 90-minute clock. The report is
saved *before* any model call, so a model or API failure never loses a
report. Failed runs can be retried.

## Front end

**Choice:** React + Vite + TypeScript (the React version `npm create vite@latest` scaffolds)

**Reason:** Live-updating detail view (polling), one component per trace
card, typed API responses. Vitest + Testing Library for fast tests.

**Rejected alternative:** Server-rendered Jinja/HTMX — harder to keep a
live, stateful trace + approval panel in sync and to unit-test.

**Customer concern:** Flight Director readability. The GO / NO-GO verdict
is large, uses a text label plus color (never color alone), and the
brief-by countdown is always visible.

## Database

**Choice:** SQLite via SQLAlchemy 2.0 (file at `data/mission_control.db`, WAL mode)

**Reason:** Zero ops, one file, ACID, survives restarts, enough for a
single console.

**Rejected alternative:** PostgreSQL — needs a server and a container for
graders, overkill for one site.

**Customer concern:** Audit trail. Every report, trace step, token count,
cost and approval (who and when) is persisted. Backup means copying one
file.

## Model

**Choice:** Gemini Flash, free tier (Google AI Studio key, `google-genai` SDK). Model ID is configurable.

**Reason:** $0 to run. Native JSON-schema structured output. Fast enough
for about 10 calls per report. No local hardware needed, so a grader can
run it with just a free key.

**Rejected alternative:** Local Ollama — also free and keeps data on the
machine, but needs a multi-GB model download, is slow on laptops, and
small local models follow JSON schemas less reliably.

**Customer concern:** Data privacy + quotas. Free-tier prompts may be used
by Google to improve products, and free quotas are best-effort and can
change. Production should move to a paid tier or another provider. The
`LLMClient` interface makes that a one-file swap.
