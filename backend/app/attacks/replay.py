"""Replay attack — retransmits a previously valid signed exchange.

Models an adversary that captures a legitimate signature and re-injects it
after a delay. The signature itself is authentic, but its temporal coherence
profile is stale: Layer 3 (TCP) flags the coherence-length mismatch and the
timestamp staleness, even though every other layer sees a genuine payload.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.attacks.base_attack import BaseAttack

#: Minimum replay delay (the captured exchange is at least this stale).
REPLAY_DELAY_SECONDS: float = 1.5

#: Deterministic capture epoch of the replayed exchange (ISO-8601, UTC).
#: A replayed exchange is by definition an *old* one; anchoring it to a fixed
#: epoch keeps the attack output identical across runs (no local state),
#: while still lying far outside the coherence window TCP tolerates.
CAPTURED_EXCHANGE_EPOCH: str = "2024-01-01T00:00:00+00:00"


class ReplayAttack(BaseAttack):
    """Simulates capture-and-replay of a past session."""

    name = "Replay"
    description = "Replays a previously captured valid exchange after a delay."
    EXPECTED_DETECTION = ("TCP",)

    def __init__(self, intensity: float = 0.5) -> None:
        """Configure the replay attack.

        Args:
            intensity: Attack strength in [0, 1] (scales the replay delay).
        """
        super().__init__("replay", intensity=intensity)

    def execute(self, context: dict) -> dict:
        """Capture the legitimate signature and replay it stale.

        The captured signature (``context["signature"]``, or a deterministic
        stand-in when absent) is retransmitted unchanged, but its timestamp
        is pushed ``REPLAY_DELAY_SECONDS`` (scaled by intensity) back from
        the fixed capture epoch — far exceeding the coherence window Layer 3
        tolerates, and identical on every run (no wall-clock dependence).

        Args:
            context: Read-only session snapshot; ``session_id`` and
                ``signature`` are recognised.

        Returns:
            Standardized envelope whose ``modified_data`` carries
            ``replay=True``, the captured signature, and the stale
            ``timestamp`` that triggers the TCP coherence check.
        """
        session_id = str(context.get("session_id", "unknown-session"))
        captured_signature = context.get("signature")
        if captured_signature is None:
            captured_signature = f"CAPTURED-QSIG-{session_id}"

        # Replay after 1+ second: scale the base delay by intensity.
        delay = REPLAY_DELAY_SECONDS + self.intensity * 10.0
        captured_at = datetime.fromisoformat(CAPTURED_EXCHANGE_EPOCH)
        stale_timestamp = (captured_at - timedelta(seconds=delay)).isoformat()

        return self._envelope(
            {
                "session_id": session_id,
                "replay": True,
                "replayed_signature": captured_signature,
                "timestamp": stale_timestamp,
                "replay_delay_seconds": float(delay),
            }
        )

