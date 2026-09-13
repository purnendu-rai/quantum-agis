"""In-memory sliding-window rate limiter (per client key, usually IP).

Single-process by design — adequate for the demo deployment and resets on
redeploy. If persistent counters are ever needed, move them into the
services layer (see plans/README.md).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window limiter: at most ``max_requests`` per window per key."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        """Configure the limiter.

        Args:
            max_requests: Allowed requests within the window.
            window_seconds: Window length in seconds.
        """
        self.max_requests = int(max_requests)
        self.window_seconds = float(window_seconds)
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, client_key: str) -> bool:
        """Record a hit for the client and decide whether it is allowed.

        Args:
            client_key: Usually ``request.client.host``.

        Returns:
            True when the request is allowed; False when the client exceeded
            ``max_requests`` within the sliding window.
        """
        now = time.monotonic()
        hits = self._hits[client_key]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True
