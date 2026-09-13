# 001 — CI pipeline: backend tests + frontend build on every push

**Commit audited:** `b1cd7a8` · **Category:** DX & tooling · **Effort:** S

## Why

Every push to `main` auto-deploys to Render (backend) and Vercel (frontend)
with no automated gate. A regression in `backend/app/**` or a broken frontend
build reaches production before any human notices. A GitHub Actions workflow
that runs the backend suite (397 tests, ~70s) and the frontend production
build (~40s) closes this for near-zero cost.

## Files in scope

- `.github/workflows/ci.yml` (new)

## Files out of scope

- `render.yaml`, `vercel.json` (deployment configs — do not touch)
- Any application code

## Steps

1. Create `.github/workflows/ci.yml` with two jobs:

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: backend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: pip, cache-dependency-path: backend/requirements.txt }
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -q

  frontend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
      - run: npm run build
```

2. Notes for the executor:
   - Python **3.11** exactly — `.python-version` pins 3.11.9 for Render; the
     suite passes on 3.13 locally but 3.11 matches production.
   - Do NOT add `--cov` in CI (the 1000-run FPR + perf tests make the suite
     ~70s; coverage is for `scripts/run_tests.sh` locally).
   - `npm ci` (not `npm install`) — package-lock.json is committed.

## Done criteria

- `git push` → the Actions run shows both jobs green.
- Local equivalents pass: `cd backend && python -m pytest tests/ -q` and
  `cd frontend && npm run build`.

## Maintenance

When a new top-level job is added (e.g. frontend lint), append it to the
same workflow; keep total runtime under ~5 min or split with `needs:`.
