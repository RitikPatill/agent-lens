#!/usr/bin/env bash
# scripts/record_demo.sh — start collector + dashboard, run demo, leave services up for GIF recording
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# 1. Check required env vars
# ---------------------------------------------------------------------------
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Error: ANTHROPIC_API_KEY is not set."
  echo "  export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Install dependencies (quiet)
# ---------------------------------------------------------------------------
echo "Installing Python packages..."
py -3.11 -m pip install -e "sdk/[dev]" -q
py -3.11 -m pip install -e "server/[dev]" -q

echo "Installing Node packages..."
(cd dashboard && npm install --silent)

# ---------------------------------------------------------------------------
# 3. Start services
# ---------------------------------------------------------------------------
mkdir -p logs

DB_PATH="$(pwd)/agentlens_demo.db"

echo "Starting collector (port 8000)..."
DATABASE_URL="sqlite:///${DB_PATH}" \
  py -3.11 -m uvicorn agentlens_server.main:app \
    --port 8000 \
    --log-level warning \
    > logs/collector.log 2>&1 &
COLLECTOR_PID=$!

echo "Starting dashboard (port 5173)..."
(cd dashboard && npm run dev -- --port 5173 --host) \
  > logs/dashboard.log 2>&1 &
DASHBOARD_PID=$!

# ---------------------------------------------------------------------------
# 4. Cleanup trap
# ---------------------------------------------------------------------------
trap 'echo ""; echo "Stopping services..."; kill "$COLLECTOR_PID" "$DASHBOARD_PID" 2>/dev/null; exit 0' EXIT INT TERM

# ---------------------------------------------------------------------------
# 5. Wait for collector to be ready
# ---------------------------------------------------------------------------
echo -n "Waiting for collector"
RETRIES=0
MAX_RETRIES=40
until curl -sf "http://localhost:8000/v1/runs" > /dev/null 2>&1; do
  RETRIES=$((RETRIES + 1))
  if [[ $RETRIES -ge $MAX_RETRIES ]]; then
    echo ""
    echo "Error: Collector failed to start after ${MAX_RETRIES} attempts — check logs/collector.log"
    exit 1
  fi
  echo -n "."
  sleep 0.5
done
echo " ready."

# ---------------------------------------------------------------------------
# 6. Print dashboard URL
# ---------------------------------------------------------------------------
echo ""
echo "  Dashboard → http://localhost:5173"
echo ""

# ---------------------------------------------------------------------------
# 7. Run the demo
# ---------------------------------------------------------------------------
if [[ "${DRY_RUN:-}" == "1" ]]; then
  echo "[DRY_RUN] Skipping example run."
else
  AGENTLENS_ENDPOINT="http://localhost:8000" \
    py -3.11 examples/research_assistant.py "How did SpaceX land Starship?"
fi

# ---------------------------------------------------------------------------
# 8. Keep services alive for GIF recording
# ---------------------------------------------------------------------------
echo ""
echo "Run complete. Open http://localhost:5173 to inspect the trace."
echo "Press Ctrl-C to stop services."
wait
