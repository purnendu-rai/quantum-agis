# QUANTUM-AGIS — Improvement Plans (advisor run)

Audited at commit `b1cd7a8` (2026-09-12). Standard effort, all nine categories,
audited directly by the host agent (codebase authored/reviewed in-session; no
subagent fan-out needed). Not audited: `frontend/src/components/dashboard/*`
rendering edge cases beyond compile-time, Render/Vercel dashboard settings.

## Findings table (vetted)

| # | Finding | Category | Impact | Effort | Risk | Evidence |
|---|---------|----------|--------|--------|------|----------|
| 1 | No CI pipeline — pushes deploy straight to prod untested | DX & tooling | HIGH | S | none | `.github/workflows/` absent; Render+Vercel auto-deploy on push |
| 2 | No input validation on API routes — `app/utils/validators.py` is dead code (0 imports) | Security | MEDIUM-HIGH | S | none | `grep validate_ backend/app/api/` → 0 hits; `verification.py:31-33`, `attacks.py:112` |
| 3 | No rate limiting on `/api/verify` + `/api/attack/*` — each call burns ~18ms of CPU-bound simulation; trivial DoS | Security | MEDIUM | S | low | grep confirms no limiter anywhere |
| 4 | WebSocket broadcaster task never cancelled on shutdown | Correctness | LOW | S | none | `websocket.py:_ensure_broadcaster` vs `main.py:38-42` (only sim loop stopped) |
| 5 | Attack panel hardcodes intensity=0.6 — judges can't demo intensity effects | Direction (UX) | MEDIUM | S | none | `AttackPanel.jsx:51` `launchAttack(attackType, intensity=0.6, ...)` per-button fixed call |
| 6 | Frontend has zero tests — no vitest/jest in `package.json` | Test coverage | HIGH | M | low | `grep vitest frontend/package.json` → 0 |
| 7 | Duplicated history state: route-level deques duplicate `simulation_service._event_window` | Tech debt | MEDIUM | M | low | `verification.py:23`, `attacks.py:22` vs `simulation_service.py:37` |

## Considered and rejected

- "In-memory stores lose data on restart" — by design for the demo (documented in docs/architecture.md); persistence is a direction item, not a defect.
- "WS broadcaster runs even with zero clients" — negligible cost; the task-cancellation fix ships with finding 4.

## Direction suggestions (not ranked against defects)

- **SQLite persistence for security events** — makes the `/api/logs/export` SIEM story real and survives restarts. M effort.
- **Attack intensity slider + per-attack parameter panels** — turns the demo into an interactive lab for judges (see plan 003).
- **Public-key enrollment flow** — the PS mentions key distribution; a UI page showing Bell-pair distribution stats would strengthen the teleportation-QDS narrative. L effort.

## Execution order

| Plan | Title | Status | Depends on |
|------|-------|--------|------------|
| 001 | CI pipeline (backend tests + frontend build on every push) | DONE | — |
| 002 | API hardening: input validation + rate limiting + WS shutdown | DONE | — |
| 003 | Attack intensity slider in the UI | DONE | — |
| 004 | Frontend unit tests (vitest: formatters, store) | DONE | — |
| 005 | Centralize verification/attack history into simulation_service (+ /api/attack/history endpoint) | DONE | — |

001 and 002 are independent; 003 is independent; land all three before any
refactor of the routes they touch (005).
