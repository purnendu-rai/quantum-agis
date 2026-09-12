"""Decision engine — maps a trust score onto an access decision.

Thresholds default to the framework constants ``TRUST_ACCEPT`` (0.95) and
``TRUST_REJECT`` (0.90), mirroring the Layer 5 BTFE policy: scores above the
accept threshold are ACCEPT, scores below the reject threshold are REJECT,
and the in-between band is QUARANTINE. Auditing is performed through the
standard ``logging`` module (in-memory handlers only), so the call never
blocks the event loop and no file I/O is performed.
"""

from __future__ import annotations

import logging

from app.core.constants import TRUST_ACCEPT, TRUST_REJECT
from app.layers.layer5_btfe import DECISION_ACCEPT, DECISION_QUARANTINE, DECISION_REJECT

logger = logging.getLogger("app.engine.decision")

#: Log severity per decision (unknown decision strings fall back to INFO).
_LOG_LEVEL_BY_DECISION: dict[str, int] = {
    DECISION_ACCEPT: logging.INFO,
    DECISION_QUARANTINE: logging.WARNING,
    DECISION_REJECT: logging.ERROR,
}


class DecisionEngine:
    """Threshold-based access policy over the fused trust score."""

    def __init__(
        self,
        accept_threshold: float = TRUST_ACCEPT,
        reject_threshold: float = TRUST_REJECT,
    ) -> None:
        """Configure the decision thresholds.

        Args:
            accept_threshold: Trust score strictly above which access is
                accepted (default 0.95).
            reject_threshold: Trust score strictly below which access is
                rejected (default 0.90).

        Raises:
            ValueError: If thresholds fall outside [0, 1] or are inverted.
        """
        accept = float(accept_threshold)
        reject = float(reject_threshold)
        if not (0.0 <= reject <= accept <= 1.0):
            raise ValueError(
                f"Need 0 <= reject ({reject}) <= accept ({accept}) <= 1."
            )
        self.accept_threshold: float = accept
        self.reject_threshold: float = reject

    def decide(self, trust_score: float) -> str:
        """Map a trust score onto an access decision.

        Mirrors the BTFE layer policy: strictly above the accept threshold
        -> ACCEPT, strictly below the reject threshold -> REJECT, otherwise
        QUARANTINE (the suspicious band).

        Args:
            trust_score: Fused trust score in [0, 1].

        Returns:
            "ACCEPT", "QUARANTINE", or "REJECT".
        """
        score = float(trust_score)
        if score > self.accept_threshold:
            return DECISION_ACCEPT
        if score < self.reject_threshold:
            return DECISION_REJECT
        return DECISION_QUARANTINE

    def log_decision(
        self,
        decision: str,
        trust_score: float,
        deviations: dict | None = None,
    ) -> None:
        """Emit a structured, non-blocking audit entry for a decision.

        Severity escalates with the decision: INFO for ACCEPT, WARNING for
        QUARANTINE, and ERROR for REJECT. Only in-memory ``logging`` handlers
        are touched — never a blocking file or network write.

        Args:
            decision: Decision string, e.g. from :meth:`decide`.
            trust_score: Trust score the decision was based on.
            deviations: Optional per-layer deviation mapping to audit.
        """
        logger.log(
            _LOG_LEVEL_BY_DECISION.get(decision, logging.INFO),
            "decision=%s trust_score=%.4f deviations=%s",
            decision,
            float(trust_score),
            deviations or {},
        )
