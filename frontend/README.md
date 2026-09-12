# QUANTUM-AGIS Frontend

React 19 + Vite dashboard for the QUANTUM-AGIS security framework.

## Structure

- `src/components/common/` — layout primitives (Header, Sidebar, Card, Loader, Badge)
- `src/components/dashboard/` — live monitoring widgets (trust gauge, charts, alert feed)
- `src/components/attack/` — attack-simulator console
- `src/components/verification/` — signature verification UI
- `src/pages/` — routed pages (Dashboard, Attack Simulator, Logs, About)
- `src/hooks/` — data-fetching and WebSocket hooks
- `src/store/` — Zustand global store
- `src/api/` — Axios client + WebSocket wrapper

## Local development

```bash
cd frontend
cp .env.example .env      # point VITE_API_URL / VITE_WS_URL at the backend
npm install
npm run dev               # http://localhost:5173 (proxies /api and /ws to :8000)
```

## Deployment (Vercel)

The root `vercel.json` (and this folder's copy) serves the SPA with a catch-all
rewrite so client-side routes work on refresh. Set the env vars `VITE_API_URL`
and `VITE_WS_URL` to the deployed backend URL (e.g. the Render service).
