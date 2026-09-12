"""Verification engine — orchestrates the six-layer AGIS stack per request.

Layers 0-4 (sensors) run concurrently on the asyncio default thread pool via
``asyncio.gather`` + ``asyncio.to_thread``, so the CPU-bound layer physics
never blocks the event loop. Their deviation scores are then fused by
Layer 5 (BTFE), scored by TrustScoreCalculator, and mapped to an access
decision by DecisionEngine.

The engine is instantiable at application startup and stateless between
requests: layer result histories are reset after every verification, so the
same input always yields the same output regardless of prior traffic. No
files are read or written at any point.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Sequence

from app.engine.decision_engine import DecisionEngine
from app.engine.trust_score import TrustScoreCalculator
from app.layers.base_layer import STATUS_FAIL, BaseLayer, utc_now_iso
from app.layers.layer0_qgm import QGMLayer
from app.layers.layer1_his import HISLayer
from app.layers.layer2_nhgs import NHGSLayer
from app.layers.layer3_tcp import TCPLayer
from app.layers.layer4_mvs import MVSLayer
from app.layers.layer5_btfe import (
    BTFELayer,
    DECISION_ACCEPT,
    DECISION_QUARANTINE,
    DECISION_REJECT,
)
from app.models.enums import Decision, Verdict

logger = logging.getLogger("app.engine.verification")

#: layer_name of the fusion stage that consumes the sensor deviations.
FUSION_LAYER_NAME: str = "BTFE"

#: BTFE decision -> API verdict (authentic/suspicious/rejected).
_VERDICT_BY_DECISION: dict[str, Verdict] = {
    DECISION_ACCEPT: Verdict.AUTHENTIC,
    DECISION_QUARANTINE: Verdict.SUSPICIOUS,
    DECISION_REJECT: Verdict.REJECTED,
}

#: BTFE decision -> API access decision (allow/challenge/deny).
_API_DECISION_BY_DECISION: dict[str, Decision] = {
    DECISION_ACCEPT: Decision.ACCEPT,
    DECISION_QUARANTINE: Decision.QUARANTINE,
    DECISION_REJECT: Decision.REJECT,
}


class VerificationEngine:
    """Async orchestrator of the L0-L5 verification pipeline."""

    def __init__(self, layers: Sequence[BaseLayer] | None = None) -> None:
        """Wire the layer stack, trust calculator, and decision engine.

        Args:
            layers: Optional custom stack; defaults to a fresh instantiation
                of all six layers (QGM, HIS, NHGS, TCP, MVS, BTFE, in order),
                so the engine is fully usable straight from app startup.
        """
        if layers is None:
            layers = (
                QGMLayer(),
                HISLayer(),
                NHGSLayer(),
                TCPLayer(),
                MVSLayer(),
                BTFELayer(),
            )
        self.layers: list[BaseLayer] = list(layers)
        self.trust_calculator: TrustScoreCalculator = TrustScoreCalculator()
        self.decision_engine: DecisionEngine = DecisionEngine()

    # ------------------------------------------------------------------ #
    #  Stack helpers
    # ------------------------------------------------------------------ #
    @property
    def sensor_layers(self) -> list[BaseLayer]:
        """Layers 0-4 whose deviation scores feed the fusion stage."""
        return [layer for layer in self.layers if layer.layer_name != FUSION_LAYER_NAME]

    @property
    def fusion_layer(self) -> BaseLayer | None:
        """Layer 5 (BTFE) fusing the sensor deviations, if registered."""
        for layer in reversed(self.layers):
            if layer.layer_name == FUSION_LAYER_NAME:
                return layer
        return None

    def register_layer(self, layer: BaseLayer) -> None:
        """Append an additional layer to the execution stack.

        Args:
            layer: BaseLayer instance to append.
        """
        self.layers.append(layer)

    # ------------------------------------------------------------------ #
    #  Execution
    # ------------------------------------------------------------------ #
    async def _run_sensor(self, layer: BaseLayer, payload: dict) -> dict:
        """Execute one sensor layer off the event loop, isolating crashes.

        Args:
            layer: Sensor layer to run.
            payload: Shared request payload (treated as read-only).

        Returns:
            The layer envelope; on an unexpected exception, a FAIL envelope
            with deviation 1.0 (a crashed sensor must never stall the
            pipeline).
        """
        try:
            return await asyncio.to_thread(layer.process, payload)
        except Exception as exc:  # noqa: BLE001 - deliberate isolation barrier
            logger.exception("Layer %s crashed during verification.", layer.layer_name)
            return {
                "layer_id": layer.layer_id,
                "layer_name": layer.layer_name,
                "status": STATUS_FAIL,
                "deviation_score": 1.0,
                "metrics": {"error": f"{type(exc).__name__}: {exc}"},
                "timestamp": utc_now_iso(),
            }

    async def verify(self, signature_data: dict | None = None) -> dict:
        """Run the full pipeline against one submitted signature.

        Pipeline: (1) Layers 0-4 execute in parallel — each dispatched via
        ``asyncio.to_thread`` inside a single ``asyncio.gather``, keeping the
        event loop free; (2) all deviations are passed to Layer 5 (BTFE) for
        fusion; (3) the trust score is recomputed by the trust calculator and
        mapped to an access decision by the decision engine; (4) the full
        result dict is returned.

        Args:
            signature_data: Request payload; every layer selects only the
                keys it understands (e.g. ``forged``, ``tampered``,
                ``replay``, ``device_id``, ``claimed_genome``, ``signature``,
                ``session_id``). Missing keys mean the genuine/default
                scenario for that layer.

        Returns:
            JSON-serialisable dict with ``trust_score``, ``decision``
            (ACCEPT/QUARANTINE/REJECT), ``verdict`` and ``api_decision``
            values, per-sensor ``deviations``, the ``chernoff_bound``
            confidence, ordered ``layer_results`` (0-5), ``num_layers``, and
            a UTC ``timestamp``.
        """
        request = dict(signature_data or {})

        sensors = self.sensor_layers
        fusion = self.fusion_layer

        gather_tasks = [self._run_sensor(layer, request) for layer in sensors]
        sensor_results = await asyncio.gather(*gather_tasks)
        deviations = {
            str(result["layer_name"]): float(result["deviation_score"])
            for result in sensor_results
        }

        fusion_result = None
        if fusion is not None:
            fusion_payload = {"layer_results": sensor_results}
            fusion_result = await asyncio.to_thread(fusion.process, fusion_payload)

        trust_score = self.trust_calculator.compute(deviations)
        decision = self.decision_engine.decide(trust_score)
        chernoff_bound = self.trust_calculator.compute_chernoff_bound(
            max(len(deviations), 1), max(1e-9, 1.0 - trust_score)
        )
        self.decision_engine.log_decision(decision, trust_score, deviations)

        layer_results = list(sensor_results)
        if fusion_result is not None:
            layer_results.append(fusion_result)

        result = {
            "trust_score": trust_score,
            "decision": decision,
            "verdict": _VERDICT_BY_DECISION.get(decision, Verdict.SUSPICIOUS).value,
            "api_decision": _API_DECISION_BY_DECISION.get(decision, Decision.QUARANTINE).value,
            "deviations": deviations,
            "chernoff_bound": chernoff_bound,
            "layer_results": layer_results,
            "num_layers": len(layer_results),
            "timestamp": utc_now_iso(),
        }
        if "session_id" in request:
            result["session_id"] = str(request["session_id"])

        # Statelessness hygiene: drop per-request result histories so repeated
        # verifications stay independent and memory remains bounded.
        for layer in self.layers:
            layer.reset()

        return result


#: Process-wide engine instance, created lazily on first use.
_ENGINE: VerificationEngine | None = None


def get_engine() -> VerificationEngine:
    """Return the process-wide :class:`VerificationEngine` singleton.

    Safe to call at application startup (e.g. from the FastAPI lifespan) or
    per request; the first call instantiates all six layers synchronously
    with no blocking side effects.

    Returns:
        The shared VerificationEngine instance.
    """
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = VerificationEngine()
    return _ENGINE
