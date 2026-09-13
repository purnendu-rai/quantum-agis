"""Simulation service — generates legitimate background verification traffic.

Singleton managing:
- A VerificationEngine instance (shared with route handlers)
- A background asyncio task that generates a legitimate signature every 2 s
- A rolling window of the last 100 verification events

The background loop is started by the FastAPI lifespan hook in ``main.py``
and stopped on shutdown. Route handlers call ``run_verification`` and
``run_attack`` through the singleton so all traffic is funnelled through a
single engine instance.
"""

from __future__ import annotations

import asyncio
import logging
import random
import string
import time
from collections import deque
from datetime import datetime, timezone

from app.engine.verification_engine import _API_DECISION_BY_DECISION, _VERDICT_BY_DECISION

logger = logging.getLogger("app.services.simulation")

_LEGITIMATE_SESSION_ID = "sim-background"


class SimulationService:
    """Facade over the verification pipeline for route handlers."""

    def __init__(self) -> None:
        """Wire engines and initialise state."""
        from app.engine.verification_engine import get_engine

        self._engine = get_engine()
        self._running = False
        self._event_window: deque[dict] = deque(maxlen=100)

    # ------------------------------------------------------------------ #
    #  Public API used by route handlers
    # ------------------------------------------------------------------ #

    async def run_verification(self, payload: dict) -> dict:
        """Execute a full verification cycle for a request.

        Broadcasts a ``new_event`` WebSocket frame with the outcome.

        Args:
            payload: Dict with at minimum ``signature`` and ``session_id``.

        Returns:
            Raw engine result dict.
        """
        result = await self._engine.verify(payload)
        self._event_window.appendleft(result)
        self._broadcast_verification_event(result, payload)
        return result

    async def run_attack(self, attack_type: str, payload: dict) -> dict:
        """Execute an attack simulation then re-verify the channel.

        Every run is unique: the effective intensity fluctuates around the
        requested baseline (Gaussian, sigma = 0.05), a fresh per-request seed
        drives the layer Monte-Carlo streams, and a small Gaussian
        measurement-noise term (+/- 0.01) is applied to each layer deviation
        before the trust score is recomputed. Detection is guaranteed: an
        attack detected before the noise cannot flip to ACCEPT after it.

        Broadcasts ``attack_detected`` (the attack result) and ``new_event``
        WebSocket frames.

        Args:
            attack_type: Attack variant name.
            payload: Payload with attack flags set and the requested intensity.

        Returns:
            Raw engine result dict (with perturbed deviations/trust).
        """
        import numpy as np

        # 1. Stochastic attack intensity: Gaussian around the requested
        #    baseline (default 0.60), sigma = 0.05, clipped to [0.1, 1.0].
        dynamic_rng = np.random.default_rng()
        requested = float(payload.get("intensity", 0.60) or 0.60)
        effective_intensity = float(np.clip(dynamic_rng.normal(requested, 0.05), 0.1, 1.0))

        # 2. Fresh per-request seed -> layer Monte-Carlo streams re-seed.
        attack_seed = int(time.time_ns() % (2**63))
        payload = dict(payload)
        payload["intensity"] = effective_intensity
        payload["attack_seed"] = attack_seed

        result = await self._engine.verify(payload)
        self._event_window.appendleft(result)

        # 3. Quantum measurement noise on each layer deviation (+/- 0.01),
        #    then recompute trust/decision so the dashboard stays consistent.
        pre_decision = str(result.get("decision", "REJECT"))
        noise_rng = np.random.default_rng()
        perturbed = {
            name: float(np.clip(dev + noise_rng.normal(0.0, 0.01), 0.0, 1.0))
            for name, dev in result.get("deviations", {}).items()
        }
        trust_score = float(self._engine.trust_calculator.compute(perturbed))
        decision = str(self._engine.decision_engine.decide(trust_score))

        # 4. Detection guarantee: noise only moves the decimals, never the
        #    verdict. A detected attack cannot escape via statistical jitter.
        if pre_decision in ("REJECT", "QUARANTINE") and decision == "ACCEPT":
            trust_score = 0.88
            decision = "REJECT"

        verdict = _VERDICT_BY_DECISION.get(decision, "suspicious")
        result["trust_score"] = trust_score
        result["decision"] = decision
        result["verdict"] = verdict
        result["api_decision"] = _API_DECISION_BY_DECISION.get(decision, "challenge")
        result["deviations"] = perturbed
        result["intensity"] = effective_intensity
        result["chernoff_bound"] = self._engine.trust_calculator.compute_chernoff_bound(
            max(len(perturbed), 1), max(1e-9, 1.0 - trust_score)
        )
        for layer_result in result.get("layer_results", []):
            name = str(layer_result.get("layer_name", ""))
            if name in perturbed:
                layer_result["deviation_score"] = perturbed[name]
                layer_result["confidence"] = 1.0 - perturbed[name]

        detected = decision in ("REJECT", "QUARANTINE")

        from app.api.websocket import manager

        await manager.notify(
            "attack_detected",
            {
                "attack_type": attack_type,
                "detected": detected,
                "trust_score_after": trust_score,
                "decision": decision,
                "details": {
                    "deviations": perturbed,
                    "chernoff_bound": result.get("chernoff_bound", 0.0),
                    "intensity": effective_intensity,
                },
            },
        )
        self._broadcast_verification_event(result, payload, source=f"attack.{attack_type}")
        logger.warning(
            "Attack simulation: type=%s trust_after=%.3f intensity=%.2f",
            attack_type,
            trust_score,
            effective_intensity,
        )
        return result

    def get_recent_events(self, limit: int = 100) -> list[dict]:
        """Return the rolling window of recent verification events.

        Args:
            limit: Maximum events to return.

        Returns:
            List of raw engine result dicts, newest first.
        """
        return list(self._event_window)[:limit]

    # ------------------------------------------------------------------ #
    #  Background task
    # ------------------------------------------------------------------ #

    async def start_background_loop(self) -> None:
        """Generate a legitimate signature verification every 2 seconds.

        Runs until ``stop()`` is called. Metrics and logs are updated on each
        cycle so the dashboard always has fresh data even when no API calls
        are being made.
        """
        self._running = True
        logger.info("Background simulation loop started.")
        while self._running:
            try:
                await self._generate_legitimate_event()
            except Exception:
                logger.exception("Background simulation error (continuing).")
            await asyncio.sleep(2.0)
        logger.info("Background simulation loop stopped.")

    def stop(self) -> None:
        """Signal the background loop to exit on its next iteration."""
        self._running = False

    # ------------------------------------------------------------------ #
    #  Internals
    # ------------------------------------------------------------------ #

    def _broadcast_verification_event(
        self, result: dict, payload: dict, source: str = "verification"
    ) -> None:
        """Push a ``new_event`` WebSocket frame for a finished verification.

        Args:
            result: Raw engine result dict.
            payload: The request payload that produced the result.
            source: Event source label (e.g. "verification", "attack.forgery").
        """
        from app.api.websocket import manager

        trust_score = float(result.get("trust_score", 0.0))
        decision = str(result.get("api_decision", "quarantine"))
        verdict = str(result.get("verdict", "suspicious"))
        manager.notify_nowait(
            "new_event",
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": "info" if decision == "accept" else "warning",
                "source": source,
                "message": (
                    f"Verification {verdict} | trust={trust_score:.3f} "
                    f"| decision={decision}"
                ),
                "session_id": str(payload.get("session_id", "unknown")),
                "decision": decision,
                "trust_score": trust_score,
            },
        )

    async def _generate_legitimate_event(self) -> None:
        """Produce and record one synthetic legitimate verification."""
        from app.services.logging_service import logging_service
        from app.services.metrics_service import metrics_service
        from app.models.enums import Severity

        signature = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        payload = {
            "signature": signature,
            "session_id": _LEGITIMATE_SESSION_ID,
        }

        result = await self._engine.verify(payload)
        trust_score = float(result.get("trust_score", 0.95))
        # Simulate slight jitter for dashboard charts
        hom_visibility = min(1.0, max(0.0, trust_score + random.gauss(0, 0.02)))
        channel_fidelity = min(1.0, max(0.0, trust_score + random.gauss(0, 0.02)))

        metrics_service.record("trust_score", trust_score)
        metrics_service.record("hom_visibility", hom_visibility)
        metrics_service.record("channel_fidelity", channel_fidelity)

        self._event_window.appendleft(result)

        logging_service.record(
            severity=Severity.INFO,
            source="simulation",
            message=(
                f"Background verification | trust={trust_score:.3f} "
                f"| hom={hom_visibility:.3f} | fidelity={channel_fidelity:.3f}"
            ),
            session_id=_LEGITIMATE_SESSION_ID,
        )


#: Module-level singleton — imported directly by route handlers and main.py.
simulation_service = SimulationService()
