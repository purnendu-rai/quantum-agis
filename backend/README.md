# QUANTUM-AGIS Backend

FastAPI backend for the Quantum-inspired Agentic Governance & Intrusion Shield (AGIS) framework.

## Structure

- `app/core/` — quantum primitives (states, gates, teleportation, measurements)
- `app/layers/` — the six-layer security stack (QGM → BTFE)
- `app/attacks/` — adversarial simulators (forgery, impersonation, replay, tampering, coherent)
- `app/engine/` — verification orchestration, trust scoring, decision policy
- `app/api/` — REST routes + WebSocket streaming
- `app/services/` — simulation, logging, metrics services
- `tests/` — pytest suite (contract tests for every layer and attack)

## Local development

```bash
# from the repo root
python -m venv venv
source venv/Scripts/activate        # Windows Git Bash (venv\Scripts\activate on cmd)

cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload       # http://localhost:8000 — docs at /docs
```

## Tests

```bash
pytest              # from backend/, with the venv active
pytest --cov=app    # with coverage
```

## Deployment

- **Docker**: build with `docker build -t quantum-agis-backend .` (see `Dockerfile`)
- **Render**: wired via the root `render.yaml` (`cd backend && uvicorn app.main:app`)
- Env vars are documented in `.env.example`; `CORS_ORIGINS` must list the frontend origin.
