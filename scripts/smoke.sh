#!/usr/bin/env bash
# Placeholder: full smoke (file report, approve, restart) lands in branch 6.
# For now, verify make start can serve /api/health with the fake provider.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export LLM_PROVIDER=fake
export GEMINI_API_KEY=""
export DATABASE_URL="sqlite:///${ROOT}/data/smoke_tmp.db"
mkdir -p data

cleanup() {
  pkill -f "uvicorn app.main:app" 2>/dev/null || true
}
trap cleanup EXIT

cleanup
make start &
SERVER_PID=$!

for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8000/api/health >/tmp/mc_health.json 2>/dev/null; then
    break
  fi
  sleep 0.5
done

python3 - <<'PY'
import json, sys
body = json.load(open("/tmp/mc_health.json"))
assert body.get("status") == "ok", body
assert body.get("provider") == "fake", body
print("smoke (scaffold): health ok, provider=fake")
PY

kill "$SERVER_PID" 2>/dev/null || true
cleanup
