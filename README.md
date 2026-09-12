# QUANTUM-AGIS

**Quantum-inspired Agentic Governance & Intrusion Shield** — a six-layer quantum-secured communication and threat-detection framework (SIH 2026 project).

## Architecture

Signatures are verified by a stack of six layers, each backed by a quantum primitive:

| # | Layer | Name | Quantum primitive |
|---|-------|------|-------------------|
| 0 | QGM | Quantum Gate Marker | Session-bound gate ordering |
| 1 | HIS | Holographic Identity Seal | Distributed identity encoding |
| 2 | NHGS | Non-Hermitian Gate Shield | NH spectrum amplification of tampering |
| 3 | TCP | Teleportation Checkpoint | Entanglement + fidelity certification |
| 4 | MVS | Multi-Vector Signature | Multi-basis measurement agreement |
| 5 | BTFE | Bayesian Threat Fusion Engine | Bayesian fusion of L0–L4 evidence |

Layer outputs are fused into a **trust score** (0–1) and mapped to an access
decision: `ALLOW`, `CHALLENGE`, or `DENY`. A simulator can launch forgery,
impersonation, replay, channel-tampering, and coherent attacks against the
stack to measure detection rates live on the dashboard.

## Repository layout

```
quantum-agis/
├── backend/          FastAPI + QuTiP API (see backend/README.md)
├── frontend/         React 19 + Vite dashboard (see frontend/README.md)
├── docs/             Architecture and API notes
├── scripts/          Developer helper scripts
├── render.yaml       Render deployment for the backend
├── vercel.json       Vercel SPA rewrite for the frontend
└── docker-compose.yml Local full-stack orchestration
```

## Quick start (local)

```bash
# backend — from repo root
python -m venv venv && source venv/Scripts/activate   # Windows Git Bash
cd backend && pip install -r requirements.txt && cp .env.example .env
uvicorn app.main:app --reload                          # http://localhost:8000/docs

# frontend — new terminal
cd frontend && cp .env.example .env && npm install && npm run dev   # http://localhost:5173
```

## Deployment

| Target | Config | Notes |
|--------|--------|-------|
| Backend → Render | `render.yaml` | Root-dir `backend`, health check `/api/health` |
| Frontend → Vercel | `vercel.json` | SPA rewrite; set `VITE_API_URL`, `VITE_WS_URL` |
| Local/Demo → Docker | `docker-compose.yml` | `docker compose up --build` |

After the backend is deployed, point `CORS_ORIGINS` (backend env) at the
deployed Vercel domain.

## Status

- [x] Project skeleton, deployment wiring, contract tests
- [ ] Quantum core implementation (states, gates, teleportation)
- [ ] Layer implementations L0–L5
- [ ] Attack simulators + trust/decision engines
- [ ] Live dashboard wiring (REST + WebSocket)
