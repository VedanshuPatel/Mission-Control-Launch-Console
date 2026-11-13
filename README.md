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

## Status (Branch 0 — scaffold)

Walking skeleton: `/api/health`, React shell, Makefile, and CI. Domain
rules, LLM layer, pipeline, API, and full console UI land on later
branches. Full smoke (file → approve → restart) lands with the docs/smoke
branch; `scripts/smoke.sh` currently checks health only.

`make test-backend` only needs `uv`; `make test-frontend` only needs Node —
so each CI job can stay lean. `make install` / `make start` still require both.

## Requirements map

Filled in as features land. "Sent to review" (hidden instructions): a
flagged note is reviewed by the model reviewer **and** tagged for the
human Flight Director (`needs_human_review`, acknowledgement required).

| Requirement | Where | Tests |
|---|---|---|
| Health / demo provider | `backend/app/main.py` | `test_health.py` |
| Console title shell | `frontend/src/App.tsx` | `App.test.tsx` |

## Test run

```text
$ make test
cd backend && uv run --frozen pytest
.                                                                        [100%]
1 passed in 0.01s
cd frontend && npx vitest run

 Test Files  1 passed (1)
      Tests  1 passed (1)
```
