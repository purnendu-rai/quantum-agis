"""WebSocket endpoint for real-time dashboard streaming.

Message protocol (all JSON, one object per frame):

- ``{"type": "dashboard_update", "data": {...}}`` — pushed every 500 ms with
  the full dashboard snapshot: layer_statuses, trust_score, recent_events,
  metrics.
- ``{"type": "new_event", "data": {event}}`` — pushed the moment a security
  event is recorded (verification, attack, …).
- ``{"type": "attack_detected", "data": {attack result}}`` — pushed as soon
  as an attack simulation completes.

All sends funnel through :class:`ConnectionManager` so no two tasks ever write
to the same socket concurrently.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("app.api.websocket")

router = APIRouter(tags=["websocket"])

#: Canonical layer order for the layer_statuses array.
LAYER_ORDER: list[str] = ["QGM", "HIS", "NHGS", "TCP", "MVS", "BTFE"]

#: Periodic dashboard_update cadence (seconds).
BROADCAST_INTERVAL_S: float = 0.5

#: How many recent events ride along in each dashboard_update.
RECENT_EVENTS_LIMIT: int = 20


class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts messages."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WS client connected — total=%d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass
        logger.info("WS client disconnected — total=%d", len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        """Send a JSON payload to every connected client, dropping dead sockets.

        Args:
            message: JSON-serialisable frame (with a "type" field).
        """
        text = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in list(self.active_connections):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def notify(self, event_type: str, data: dict) -> None:
        """Broadcast a typed event frame (``new_event``, ``attack_detected``, …).

        Args:
            event_type: Value of the frame's ``type`` field.
            data: Event payload (must be JSON-serialisable).
        """
        await self.broadcast({"type": event_type, "data": data})

    def notify_nowait(self, event_type: str, data: dict) -> None:
        """Schedule a typed event broadcast from sync code.

        Safe to call from synchronous services running inside the event loop;
        silently drops the notification when no loop is available.

        Args:
            event_type: Value of the frame's ``type`` field.
            data: Event payload.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.notify(event_type, data))


#: Module-level singleton — imported by services and routes.
manager = ConnectionManager()


def _layer_statuses() -> list[dict]:
    """Build the per-layer status array for the dashboard_update frame.

    Reads the most recent engine result; falls back to trust-derived verdicts
    when no verification has run yet.

    Returns:
        List of ``{"layer_id", "layer_name", "status", "deviation_score"}``
        dicts in canonical LAYER_ORDER.
    """
    from app.services.metrics_service import metrics_service
    from app.services.simulation_service import simulation_service

    statuses: dict[str, dict] = {}
    latest = simulation_service.get_recent_events(1)
    if latest:
        for result in latest[0].get("layer_results", []):
            statuses[result.get("layer_name", "")] = {
                "layer_id": result.get("layer_id", 0),
                "layer_name": result.get("layer_name", ""),
                "status": result.get("status", "PASS"),
                "deviation_score": float(result.get("deviation_score", 0.0)),
            }

    trust = float(metrics_service.latest_values().get("trust_score", 0.95))
    fallback_status = "PASS" if trust > 0.95 else ("SUSPICIOUS" if trust >= 0.90 else "FAIL")
    return [
        statuses.get(
            name,
            {"layer_id": index, "layer_name": name, "status": fallback_status, "deviation_score": 0.0},
        )
        for index, name in enumerate(LAYER_ORDER)
    ]


def _build_dashboard_update() -> dict:
    """Collect the full dashboard snapshot for the periodic push.

    Returns:
        ``{"type": "dashboard_update", "data": {...}}`` with layer_statuses,
        trust_score, recent_events, and metrics.
    """
    try:
        from app.services.logging_service import logging_service
        from app.services.metrics_service import metrics_service

        latest = metrics_service.latest_values()
        events = logging_service.list(limit=RECENT_EVENTS_LIMIT)
        return {
            "type": "dashboard_update",
            "data": {
                "layer_statuses": _layer_statuses(),
                "trust_score": latest.get("trust_score", 0.95),
                "recent_events": [event.model_dump() for event in events],
                "metrics": {
                    "hom_visibility": latest.get("hom_visibility", 0.95),
                    "channel_fidelity": latest.get("channel_fidelity", 0.95),
                },
            },
        }
    except Exception as exc:  # never kill the stream over a snapshot error
        logger.exception("Failed to build dashboard_update payload.")
        return {"type": "error", "detail": str(exc)}


async def _broadcast_periodically() -> None:
    """Push a dashboard_update frame every 500 ms until the app stops."""
    while True:
        await manager.broadcast(_build_dashboard_update())
        await asyncio.sleep(BROADCAST_INTERVAL_S)


_broadcaster_task: asyncio.Task | None = None


def _ensure_broadcaster() -> None:
    """Start the single periodic broadcast task on the first connection."""
    global _broadcaster_task
    if _broadcaster_task is None or _broadcaster_task.done():
        _broadcaster_task = asyncio.create_task(_broadcast_periodically())
        logger.info("Periodic dashboard_update broadcaster started.")


def shutdown() -> None:
    """Cancel the periodic broadcaster task (called from the app lifespan)."""
    global _broadcaster_task
    if _broadcaster_task is not None and not _broadcaster_task.done():
        _broadcaster_task.cancel()
        logger.info("Periodic dashboard_update broadcaster stopped.")


@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Stream live dashboard updates and instant events to a client.

    The periodic 500 ms snapshot is broadcast by one shared task; event-driven
    frames (new_event, attack_detected) are pushed the moment they happen.

    Args:
        websocket: Incoming WebSocket connection from the frontend.
    """
    await manager.connect(websocket)
    _ensure_broadcaster()
    try:
        while True:
            # Client pings/control messages are accepted without blocking.
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
