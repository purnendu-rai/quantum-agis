# Setup Guide

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.11+ | `python --version` |
| Node.js | 20+ LTS | `node --version` |
| npm | 10+ | `npm --version` |
| Git | 2.40+ | `git --version` |

## Option A — one-script setup

```bash
./scripts/setup.sh        # installs backend + frontend deps, creates .env files
./scripts/run_dev.sh      # backend on :8000, frontend on :5173
```

## Option B — manual setup

### Backend

```bash
python -m venv venv
source venv/Scripts/activate        # Windows Git Bash (venv/bin/activate on Unix)
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000 — SwaggerUI: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
npm install
cp .env.example .env               # VITE_API_URL / VITE_WS_URL
npm run dev
```

- Dashboard: http://localhost:5173 (proxies nothing; calls the API directly —
  backend CORS already allows the dev origin)

## Tests

```bash
./scripts/run_tests.sh             # full suite + coverage (HTML in backend/htmlcov)
```

Integration guarantees covered by the suite: legitimate → ACCEPT, every
attack → REJECT, false-positive rate 0 over 1000 signatures, and mean
verification latency < 100 ms across 1000 runs.

## Docker

```bash
docker compose up --build          # backend :8000 + frontend :5173
# backend image only:
docker build -t quantum-agis-backend backend/
```

## Production deployment

### Backend → Render

1. Push the repo to GitHub; create a Render **Blueprint** from `render.yaml`.
2. Render installs `backend/requirements.txt` and starts
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Health check: `/api/health`. Set `CORS_ORIGINS` to the Vercel domain.

### Frontend → Vercel

1. Import the repo; Vercel auto-detects Vite (`frontend/` as root).
2. Environment variables (see `frontend/.env.production`):
   `VITE_API_URL=https://quantum-agis-backend.onrender.com`,
   `VITE_WS_URL=wss://quantum-agis-backend.onrender.com`.
3. `vercel.json` rewrites all routes to the SPA entry so client routing
   survives a hard refresh.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Header shows "connecting…" | Backend down or `VITE_WS_URL` wrong — check `/api/health` |
| 422 on verify | Signature must be ≥ 4 printable characters; `session_id` required |
| CORS errors in prod | Add the Vercel origin to the backend `CORS_ORIGINS` env var |
| Charts empty | Background simulation fills metrics every 2 s — wait a few seconds |
