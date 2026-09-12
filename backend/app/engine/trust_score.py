"""Trust-score engine — converts layer deviations into a scalar trust value.

Implements the weighted fusion defined in ``app.core.constants``:
T = 1 - sum(w_i * d_i), plus the Chernoff/Hoeffding concentration bound that
quantifies the statistical confidence of the estimate. The calculator is fully
deterministic, stateless, and JSON-serialisable; with the default weights it
reproduces the Layer 5 BTFE fusion exactly.
"""

from __future__ import annotations

import math

from app.core.constants import LAYER_WEIGHTS


class TrustScoreCalculator:
    """Weighted fusion of per-layer deviation scores into a trust score."""

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        """Initialise with the default or custom fusion weights.

        Args:
            weights: Optional mapping of layer name to weight. Defaults to
                ``LAYER_WEIGHTS`` from ``app.core.constants`` (sums to 1.0).
                A copy is stored, so later mutations of the caller's dict or
                of the module constant never leak into the calculator.
        """
        self.weights: dict[str, float] = (
            {str(name): float(value) for name, value in weights.items()}
            if weights is not None
            else dict(LAYER_WEIGHTS)
        )

    def compute(self, deviations: dict[str, float]) -> float:
        """Fuse per-layer deviation scores into the aggregate trust score.

        Implements T = 1 - sum(w_i * d_i) over the registered weights; layers
        that did not report (or unknown layer names) contribute no penalty,
        and the result is clamped to [0, 1].

        Args:
            deviations: Mapping of layer name (e.g. "QGM") to its deviation
                score in [0, 1]. ``None`` values are ignored.

        Returns:
            Trust score in [0, 1]; 1.0 means every reporting layer is clean.
        """
        penalty = 0.0
        for name, deviation in deviations.items():
            weight = self.weights.get(str(name))
            if weight is None or deviation is None:
                continue
            penalty += weight * float(deviation)
        return float(min(1.0, max(0.0, 1.0 - penalty)))

    def compute_chernoff_bound(self, num_samples: int, epsilon: float) -> float:
        """Return the Chernoff/Hoeffding bound on the fusion error probability.

        For n independently sampled layer estimates each in [0, 1], the
        probability that the fused mean deviates by more than epsilon is
        bounded by 2 * exp(-2 * n * epsilon^2), capped at 1.

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
        return float(min(1.0, 2.0 * math.exp(-2.0 * num_samples * float(epsilon) ** 2)))

    def breakdown(self, deviations: dict[str, float]) -> dict[str, float]:
        """Return per-layer weighted contributions for dashboards.

        Args:
            deviations: Mapping of layer name to deviation score.

        Returns:
            Mapping of known layer name to its weighted penalty
            contribution; unknown layer names and ``None`` values are
            omitted.
        """
        contributions: dict[str, float] = {}
        for name, deviation in deviations.items():
            weight = self.weights.get(str(name))
            if weight is None or deviation is None:
                continue
            contributions[str(name)] = float(weight * float(deviation))
        return contributions


#: Backwards-compatible alias for the original stub class name.
TrustScoreEngine = TrustScoreCalculator
