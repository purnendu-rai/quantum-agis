#!/usr/bin/env bash
# Start the QUANTUM-AGIS backend and frontend together for local development.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT/backend"
"$ROOT/venv/Scripts/python.exe" -m uvicorn app.main:app --reload &
BACK_PID=$!

cd "$ROOT/frontend"
npm run dev &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null' EXIT
echo "Backend: http://localhost:8000 | Frontend: http://localhost:5173"
wait
