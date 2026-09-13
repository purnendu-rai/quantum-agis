# 002 — API hardening: input validation, rate limiting, WS shutdown

**Commit audited:** `b1cd7a8` · **Category:** Security / Correctness · **Effort:** S

## Why

Findings 2, 3, 4 (see `plans/README.md`). The API is publicly deployed and
every `/api/verify` call runs a CPU-bound simulation. Input validators exist
but are dead code; there is no per-client rate limit; the WebSocket
broadcaster task leaks past shutdown.

## Files in scope

- `backend/app/utils/rate_limiter.py` (new)
- `backend/app/api/routes/verification.py` (add validation + limiter)
- `backend/app/api/routes/attacks.py` (add validation + limiter)
- `backend/app/api/websocket.py` (add `shutdown()`; call from lifespan)
- `backend/app/main.py` (call the WS shutdown in `_lifespan`)
- `backend/tests/test_api_hardening.py` (new)

## Files out of scope

- Layer/attack logic (`app/layers/`, `app/attacks/`, `app/core/`)
- `app/services/*`

## Steps

1. **Rate limiter** — `app/utils/rate_limiter.py`:

```python
"""In-memory sliding-window rate limiter (per client IP)."""
import time
from collections import defaultdict, deque

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, client_key: str) -> bool:
        """Return True when allowed; record the hit otherwise False."""
        now = time.monotonic()
        hits = self._hits[client_key]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True
```

2. **Wire into routes** as FastAPI dependencies:

```python
from fastapi import Request
from app.utils.rate_limiter import RateLimiter

verify_limiter = RateLimiter(max_requests=60, window_seconds=60.0)
attack_limiter = RateLimiter(max_requests=30, window_seconds=60.0)

def enforce(limiter: RateLimiter, request: Request):
    if not limiter.check(request.client.host):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Retry in a minute.")
```

Add `dependencies` or a first-line call in `verify_signature` /
`run_attack`. Limits are generous (the demo UI fires a few per minute);
60/min verify + 30/min attack will not affect tests or demos.

3. **Wire validators** (they already exist in `app/utils/validators.py`):

In `verify_signature`, before processing:

```python
from app.utils.validators import validate_signature_format, validate_session_id
try:
    validate_signature_format(request.signature)
    validate_session_id(request.session_id)
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc))
```

In `run_attack`: `validate_session_id(session_id)` (400 on ValueError) and
replace the manual clamp with `intensity = validate_intensity(intensity)`.

4. **WS shutdown** — in `app/api/websocket.py` add:

```python
def shutdown() -> None:
    """Cancel the periodic broadcaster (called from app lifespan)."""
    global _broadcaster_task
    if _broadcaster_task is not None and not _broadcaster_task.done():
        _broadcaster_task.cancel()
```

Call it in `main.py` `_lifespan` after `simulation_service.stop()`.

5. **Tests** — `backend/tests/test_api_hardening.py`:
   - `test_verify_rejects_oversized_signature`: POST `/api/verify` with a
     5000-char signature → expect 400 (pattern allows ≤ 4096).
   - `test_verify_rejects_bad_session_id`: `session_id: "bad; drop"` → 400.
   - `test_rate_limit_returns_429`: instantiate `RateLimiter(2, 60)`, three
     `check("ip")` calls → True, True, False (unit-level, no HTTP loop).
   - Pattern reference: existing `backend/tests/test_api/test_routes.py`.

## Done criteria

- `python -m pytest tests/ -q` → all green (was 397).
- `curl -X POST /api/verify -d '{"signature":"ab","session_id":"s"}'` → 400.
- 61 rapid verify calls → the 61st returns 429.

## Maintenance

Rate-limiter state is per-process (resets on deploy) — fine for the demo;
if a database lands (direction item), move counters there.
