# System Architecture

## High-level topology

```
┌────────────────────┐         HTTPS / WSS          ┌────────────────────┐
│  React dashboard   │ ◄──────────────────────────► │  FastAPI backend   │
│  (Vercel, SPA)     │   REST + WebSocket stream    │  (Render / Docker) │
└────────────────────┘                              └─────────┬──────────┘
                                                              │
                                              ┌───────────────▼───────────────┐
                                              │      Verification engine      │
                                              │  L0 QGM  L1 HIS  L2 NHGS      │
                                              │  L3 TCP  L4 MVS  ─► L5 BTFE   │
                                              └───────────────────────────────┘
```

## Verification pipeline

1. **Sensor layers (0–4) execute in parallel** — each layer is dispatched via
   `asyncio.to_thread` inside a single `asyncio.gather`, so the pure-CPU
   quantum simulations never block the event loop.
2. Every sensor emits the standard envelope: `{layer_id, layer_name, status,
   deviation_score, metrics, timestamp}`.
3. **Layer 5 (BTFE)** fuses all deviations: `T = 1 − Σ wᵢ·dᵢ` with weights
   QGM 0.25, HIS 0.25, NHGS 0.20, TCP 0.15, MVS 0.10, BTFE 0.05.
4. **Decision engine** maps T: `> 0.95 ACCEPT`, `< 0.90 REJECT`, else
   `QUARANTINE`. The Chernoff/Hoeffding bound `2·e^(−2nε²)` quantifies the
   confidence of the fusion.

## Backend module map

| Module | Responsibility |
|--------|----------------|
| `app/core/` | Quantum primitives: states, gates, teleportation, measurements (pure NumPy/SciPy, seeded RNG 42) |
| `app/layers/` | Six security layers + shared `BaseLayer` envelope |
| `app/attacks/` | Five adversarial simulators (forgery, impersonation, replay, tampering, coherent) |
| `app/engine/` | `VerificationEngine` orchestration, trust calculator, decision engine |
| `app/api/` | REST routers + `/ws/live` stream (`dashboard_update` @500ms, `new_event`, `attack_detected`) |
| `app/services/` | Simulation traffic generator, in-memory log ring buffer, metric time series |

## Frontend module map

| Module | Responsibility |
|--------|----------------|
| `src/api/` | Axios client (`VITE_API_URL`) + WebSocket factory with exponential backoff |
| `src/hooks/` | `useWebSocket` (type-dispatch to store), `useVerification`, `useAttacks` |
| `src/store/` | Zustand: layer statuses, trust score, event feed, metrics, connection flag |
| `src/components/` | Common primitives + dashboard widgets + attack/verification consoles |

## Deployment

| Target | Config | Notes |
|--------|--------|-------|
| Backend | Render (`render.yaml`), Docker (`backend/Dockerfile`) | Health check `/api/health`, `$PORT` binding |
| Frontend | Vercel (`vercel.json` SPA rewrite) | `.env.production` points at the Render URL |
| Local | `docker-compose.yml` or `scripts/run_dev.sh` | Full stack with proxy-free CORS |

## Determinism & statelessness

- All stochastic components draw from `numpy.random.default_rng` streams
  derived from `RANDOM_SEED = 42` (per-device genomes via CRC32 labels).
- Layers are stateless; per-session history lives only in the services layer.
- No file I/O in layer or engine logic — in-memory ring buffers only.
