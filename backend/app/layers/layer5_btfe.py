"""Layer 5 — BTFE (Bayesian Trust Fusion Engine).

Fuses the deviation scores emitted by Layers 0-4 into a single trust score
T = 1 - sum(w_i * d_i), quantifies the statistical confidence of the
estimate via a Chernoff/Hoeffding tail bound, and maps T onto an access
decision: ACCEPT (T > 0.95), REJECT (T < 0.90), otherwise QUARANTINE.

The layer is fully deterministic (no randomness) and JSON-serialisable.
"""

from __future__ import annotations

import math

from app.core.constants import LAYER_WEIGHTS, TRUST_ACCEPT, TRUST_REJECT, W_BTFE
from app.layers.base_layer import (
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SUSPICIOUS,
    BaseLayer,
)

#: Decisions returned by make_decision.
DECISION_ACCEPT: str = "ACCEPT"
DECISION_QUARANTINE: str = "QUARANTINE"
DECISION_REJECT: str = "REJECT"

_STATUS_BY_DECISION: dict[str, str] = {
    DECISION_ACCEPT: STATUS_PASS,
    DECISION_QUARANTINE: STATUS_SUSPICIOUS,
    DECISION_REJECT: STATUS_FAIL,
}


class BTFELayer(BaseLayer):
    """Weighted trust fusion with a concentration-bound confidence estimate."""

    def __init__(self) -> None:
        """Initialise the fusion engine with the BTFE identity and weight."""
        super().__init__(layer_id=5, layer_name="BTFE", weight=W_BTFE)

    # ------------------------------------------------------------------ #
    #  Fusion mathematics
    # ------------------------------------------------------------------ #
    @staticmethod
    def compute_trust_score(deviations: dict[str, float]) -> float:
        """Fuse per-layer deviation scores into a trust score.

        Implements T = 1 - sum(w_i * d_i) using the registered layer weights;
        layers that did not report contribute no penalty, and the result is
        clamped to [0, 1].

        Args:
            deviations: Mapping of layer name (e.g. "QGM") to its deviation
                score in [0, 1]. Unknown layer names are ignored.

        Returns:
            Trust score in [0, 1]; 1.0 means every reporting layer is clean.
        """
        penalty = sum(
            LAYER_WEIGHTS[name] * float(deviation)
            for name, deviation in deviations.items()
            if name in LAYER_WEIGHTS
        )
        return float(min(1.0, max(0.0, 1.0 - penalty)))

    @staticmethod
    def chernoff_bound(num_samples: int, epsilon: float) -> float:
        """Return the Chernoff/Hoeffding bound on fusion error probability.

        For n independently sampled layer estimates each in [0, 1], the
        probability that the fused mean deviates by more than epsilon is
        bounded by 2 * exp(-2 n epsilon^2) (Hoeffding form of the Chernoff
        bound), capped at 1.

        Args:
            num_samples: Number of fused estimates (n >= 1).
            epsilon: Deviation tolerance in [0, 1].

        Returns:
            Upper bound on the error probability in (0, 1].

        Raises:
            ValueError: If num_samples < 1 or epsilon is negative.
        """
        if num_samples < 1:
            raise ValueError("num_samples must be at least 1.")
        if epsilon < 0.0:
            raise ValueError("epsilon must be non-negative.")
        return float(min(1.0, 2.0 * math.exp(-2.0 * num_samples * epsilon**2)))

    @staticmethod
    def make_decision(trust_score: float) -> str:
        """Map a trust score onto an access decision.

        Args:
            trust_score: Fused trust score in [0, 1].

        Returns:
            "ACCEPT" when T > 0.95, "REJECT" when T < 0.90, else
            "QUARANTINE".
        """
        if trust_score > TRUST_ACCEPT:
            return DECISION_ACCEPT
        if trust_score < TRUST_REJECT:
            return DECISION_REJECT
        return DECISION_QUARANTINE

    # ------------------------------------------------------------------ #
    #  BaseLayer contract
    # ------------------------------------------------------------------ #
    def process(self, input_data: dict) -> dict:
        """Fuse the layer results supplied in ``input_data``.

        Args:
            input_data: Key ``layer_results`` — list of result envelopes
                produced by Layers 0-4 (each with "layer_name" and
                "deviation_score").

        Returns:
            Standard result envelope; status mirrors the decision
            (ACCEPT -> PASS, QUARANTINE -> SUSPICIOUS, REJECT -> FAIL) and
            metrics carry the trust score, decision, Chernoff bound, and the
            per-layer deviations that were fused.
        """
        raw_results = input_data.get("layer_results", [])
        deviations = {
            str(result["layer_name"]): float(result["deviation_score"])
            for result in raw_results
            if isinstance(result, dict)
            and result.get("layer_name") in LAYER_WEIGHTS
            and result.get("deviation_score") is not None
        }

        trust_score = self.compute_trust_score(deviations)
        decision = self.make_decision(trust_score)
        epsilon = max(1e-9, 1.0 - trust_score)
        bound = self.chernoff_bound(max(len(deviations), 1), epsilon)

        return self.make_result(
            _STATUS_BY_DECISION[decision],
            1.0 - trust_score,
            {
                "trust_score": trust_score,
                "decision": decision,
                "chernoff_bound": bound,
                "fused_layers": sorted(deviations.keys()),
                "num_layers": len(deviations),
                "layer_deviations": deviations,
            },
        )
