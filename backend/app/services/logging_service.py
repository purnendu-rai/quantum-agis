"""Logging service — in-memory security event log with ring-buffer retention.

Feeds the /api/logs endpoints and the WebSocket alert stream. Every recorded
event is also appended to ``logs/security_events.jsonl`` (one JSON object per
line) under a threading lock, so concurrent writers never interleave partial
lines. The in-memory ring buffer keeps reads bounded; the JSONL file is the
persistent audit trail for SIEM hand-off.
"""

from __future__ import annotations

import json
import threading
from collections import deque
from pathlib import Path

from app.layers.base_layer import utc_now_iso
from app.models.enums import Severity
from app.models.schemas import SecurityEvent

#: Directory holding the persistent JSONL audit trail (relative to backend/).
LOG_DIR: Path = Path(__file__).resolve().parents[2] / "logs"


class LoggingService:
    """Bounded in-memory event log with a persistent JSONL audit trail."""

    def __init__(self, max_events: int = 1000, log_path: Path | None = None) -> None:
        """Configure retention and the audit-file location.

        Args:
            max_events: Ring-buffer capacity before oldest events are dropped.
            log_path: Optional override for the JSONL file location.
        """
        self._events: deque[SecurityEvent] = deque(maxlen=max_events)
        self._log_path: Path = log_path if log_path is not None else LOG_DIR / "security_events.jsonl"
        self._lock = threading.Lock()
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        severity: Severity,
        source: str,
        message: str,
        session_id: str | None = None,
    ) -> SecurityEvent:
        """Append a security event to the log and the JSONL audit trail.

        Args:
            severity: Event severity level.
            source: Emitting component (layer name, attack name, engine).
            message: Human-readable description.
            session_id: Optional related session.

        Returns:
            The stored SecurityEvent.
        """
        event = SecurityEvent(
            timestamp=utc_now_iso(),
            severity=severity,
            source=source,
            message=message,
            session_id=session_id,
        )
        with self._lock:
            self._events.appendleft(event)
            line = json.dumps(event.model_dump(), separators=(",", ":"))
            with open(self._log_path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return event

    def list(
        self,
        limit: int = 100,
        severity: Severity | None = None,
    ) -> list[SecurityEvent]:
        """Return recent events, newest first, optionally filtered.

        Args:
            limit: Maximum number of events.
            severity: Optional severity filter.

        Returns:
            List of SecurityEvent.
        """
        cap = max(0, int(limit))
        with self._lock:
            events = [event for event in self._events if severity is None or event.severity == severity]
        return events[:cap]

    def export(self) -> dict:
        """Return the full log payload plus export metadata.

        Returns:
            Dict with the event list, count, and audit-file path.
        """
        with self._lock:
            events = list(self._events)
        return {
            "events": [event.model_dump() for event in events],
            "count": len(events),
            "exported_at": utc_now_iso(),
            "log_file": str(self._log_path),
        }


#: Module-level singleton shared by routes and the WebSocket stream.
logging_service = LoggingService()
