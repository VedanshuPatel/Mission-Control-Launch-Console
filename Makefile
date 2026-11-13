.PHONY: doctor install start dev test test-backend test-frontend lint smoke

doctor:
	@command -v uv   >/dev/null || { echo "Missing uv: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	@command -v node >/dev/null || { echo "Missing Node 22+: https://nodejs.org"; exit 1; }

backend/.venv: backend/uv.lock
	cd backend && uv sync --frozen --group dev
	@touch backend/.venv

frontend/node_modules: frontend/package-lock.json
	cd frontend && npm ci
	@touch frontend/node_modules

install: doctor backend/.venv frontend/node_modules

start: install
	npm --prefix frontend run build
	cd backend && uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000

dev: install
	@echo "Start API:  cd backend && uv run --frozen uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
	@echo "Start UI:   npm --prefix frontend run dev"
	cd backend && uv run --frozen uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
	npm --prefix frontend run dev

test-backend: doctor backend/.venv
	cd backend && uv run --frozen pytest

test-frontend: doctor frontend/node_modules
	cd frontend && npx vitest run

test: test-backend test-frontend

lint: install
	cd backend && uv run --frozen ruff check .
	cd frontend && npx tsc --noEmit

smoke: install
	./scripts/smoke.sh
