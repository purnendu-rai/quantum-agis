"""Metrics service — tracks time-series dashboard metrics.

Stores trust score, HOM visibility, and channel fidelity samples for the
dashboard trend charts and the WebSocket metric ticks. Every series is a
bounded deque, so memory stays flat no matter how long the app runs. Reads
and writes are guarded by a threading lock, so samples recorded from the
background simulation task and from concurrent API calls never interleave
partially. No files are read or written at any point.
"""

from __future__ import annotations

import threading
from collections import deque

from app.layers.base_layer import utc_now_iso


class MetricsService:
    """Bounded time-series store for dashboard metrics."""

    def __init__(self, max_points: int = 500) -> None:
        """Configure retention.

        Args:
            max_points: Maximum samples retained per metric.
        """
        self.max_points = int(max(1, max_points))
        self._series: dict[str, deque] = {}
        self._lock = threading.Lock()

    def record(self, metric: str, value: float, timestamp: str | None = None) -> None:
        """Append a sample to a metric series.

        Args:
            metric: Metric name (e.g. "trust_score", "hom_visibility").
            value: Sampled value.
            timestamp: ISO timestamp; defaults to now (UTC).
        """
        point = {
            "timestamp": timestamp if timestamp is not None else utc_now_iso(),
            "value": float(value),
        }
        with self._lock:
            series = self._series.get(str(metric))
            if series is None:
                series = self._series[str(metric)] = deque(maxlen=self.max_points)
            series.appendleft(point)

    def history(self, metric: str, limit: int | None = None) -> list[dict]:
        """Return recent samples for a metric.

        Args:
            metric: Metric name to read.
            limit: Optional cap on returned points.

        Returns:
            List of {timestamp, value} points, oldest first.
        """
        cap = self.max_points if limit is None else max(0, int(limit))
        with self._lock:
            series = self._series.get(str(metric))
            points = [dict(point) for point in series] if series is not None else []
        # Deque is newest-first (appendleft); reverse for oldest-first reads.
        return list(reversed(points))[:cap]

    def latest(self, metric: str) -> dict | None:
        """Return the most recent sample of a metric, if any.

        Args:
            metric: Metric name to read.

        Returns:
            Latest point dict, or None when no samples exist.
        """
        with self._lock:
            series = self._series.get(str(metric))
            if series is None:
                return None
            point = dict(series[0])
        return point

    def latest_values(self) -> dict[str, float]:
        """Return the newest value of every recorded metric.

        Returns:
            Mapping of metric name to its most recent value.
        """
        with self._lock:
            return {name: float(series[0]["value"]) for name, series in self._series.items() if series}


#: Module-level singleton shared by routes, the WebSocket stream, and the
#: background simulation task.
metrics_service = MetricsService()
