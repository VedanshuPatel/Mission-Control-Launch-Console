# Mission Control — Go/No-Go Launch Console

Meridian Launch Services console: engineers file anomaly reports; a
pipeline classifies, checks limits, and drafts a briefing; only a person
approves.

## Commands

```bash
make start   # installs deps, builds UI, serves app at http://localhost:8000
make test    # runs all backend + frontend tests (no network, no API key)
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (installs Python 3.12)
- Node 22+
- `make`

## Configuration

Copy `.env.example` to `.env`. `GEMINI_API_KEY` is optional — without it the
app runs in **demo mode** with the fake model.

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `auto` \| `gemini` \| `fake` (`auto` uses Gemini when a key is set) |
| `GEMINI_API_KEY` | Google AI Studio key (optional) |
| `GEMINI_MODEL` | Gemini model ID (see `.env.example`) |
| `DATABASE_URL` | SQLite URL (default `sqlite:///data/mission_control.db`) |

Tool choices (reason, rejected alternative, customer concern per layer):
see [`TOOL_CHOICES.md`](TOOL_CHOICES.md).

## Status

Scaffold through model-steps are on `main`. Branch `feature/backend-api`
wires SQLite persistence, filing/validation, the orchestrator trace, and
human-only approval. Console UI follows. Full smoke lands with the
docs/smoke branch; `scripts/smoke.sh` currently checks health only.

`make test-backend` only needs `uv`; `make test-frontend` only needs Node —
so each CI job can stay lean. `make install` / `make start` still require both.

Default model: `gemini-3.8-flash` (see `.env.example` and `TOOL_CHOICES.md`).

## Requirements map

Filled in as features land. "Sent to review" (hidden instructions): a
flagged note is reviewed by the model reviewer **and** tagged for the
human Flight Director (`needs_human_review`, acknowledgement required).

| Requirement | Where | Tests |
|---|---|---|
| Health / demo provider | `backend/app/main.py` | `test_health.py` |
| Console title shell | `frontend/src/App.tsx` | `App.test.tsx` |
| Launch limits (plain code) | `backend/app/domain/limits.py` | `test_limits.py`, `test_domain_isolation.py` |
| Brief-by time | `backend/app/domain/brief_time.py` | `test_brief_time.py` |
| Cost at paid-tier rates | `backend/app/domain/cost.py` | `test_cost.py` |
| One LLM interface + fake (offline) | `backend/app/llm/` | `test_llm_fake.py`, `test_no_network.py`, `test_single_llm_interface.py`, `test_gemini_adapter.py` |
| Sorting (structured + fallback) | `backend/app/pipeline/classify.py` | `test_classify.py` |
| Three checks + hidden instructions | `backend/app/pipeline/checks.py` | `test_checks.py` |
| Draft/review loop (pending only) | `backend/app/pipeline/briefing.py` | `test_briefing_loop.py` |
| Filing + restart persistence | `backend/app/api/reports.py` | `test_reports_api.py`, `test_persistence_restart.py` |
| Orchestrator trace + cost | `backend/app/pipeline/orchestrator.py` | `test_orchestrator.py` |
| Hidden instruction E2E | `backend/app/pipeline/` | `test_hidden_instruction.py` |
| Human-only approval | `backend/app/api/approvals.py` | `test_approval.py` |

## Test run

```text
$ make test
cd backend && uv run --frozen pytest
........................................................................ [ 54%]
.............................................................            [100%]
137 passed in 0.76s
cd frontend && npx vitest run

 Test Files  1 passed (1)
      Tests  1 passed (1)
```
