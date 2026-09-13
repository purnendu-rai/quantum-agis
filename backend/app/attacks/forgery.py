"""Forgery attack — submits a fabricated quantum signature.

Models an adversary that crafts a counterfeit signature from random quantum
states without access to the legitimate quantum gate marker sequence or the
genuine device fingerprint. The fabricated genome is unrelated to the enrolled
one (Hamming distance near 0.5), so Layer 0 (QGM) flags the device mismatch
while Layer 1 (HIS) flags the impossible fidelity of the fake marker sequence.
"""

from __future__ import annotations

import numpy as np

from app.attacks.base_attack import BaseAttack
from app.layers.layer0_qgm import GENOME_DIMENSION, GENOME_PARAMS, QGMLayer

#: Signature prefix marking the fabricated payload.
FORGED_SIGNATURE_PREFIX: str = "FORGED-QSIG"


class ForgeryAttack(BaseAttack):
    """Simulates a forged-signature injection attempt."""

    name = "Forgery"
    description = "Injects a fabricated signature built from random quantum states."
    EXPECTED_DETECTION = ("QGM", "HIS")

    def __init__(self, intensity: float = 0.5) -> None:
        """Configure the forgery attack.

        Args:
            intensity: Attack strength in [0, 1] (scales genome distortion).
        """
        super().__init__("forgery", intensity=intensity)

    def execute(self, context: dict) -> dict:
        """Craft a counterfeit signature from random quantum states.

        A random complex statevector is drawn on the seeded stream; its
        amplitude magnitudes drive a fake 100-dimensional genome that shares
        no relation to the enrolled device fingerprint. The fake signature
        string is likewise derived from the random amplitudes.

        Args:
            context: Read-only session snapshot; ``session_id`` is echoed.

        Returns:
            Standardized envelope. ``modified_data`` carries ``forged=True``,
            the fabricated ``signature``, the ``claimed_genome`` (which makes
            QGM fail) and descriptors of the random state (which make HIS
            flag the impossible marker fidelity).
        """
        rng = self._rng()
        intensity = self.sample_intensity(rng)
        session_id = str(context.get("session_id", "unknown-session"))

        # Random quantum state on GENOME_DIMENSION amplitudes (normalised).
        amplitudes = rng.normal(size=GENOME_DIMENSION) + 1j * rng.normal(size=GENOME_DIMENSION)
        statevector = amplitudes / np.linalg.norm(amplitudes)

        # Distort toward the extremes of each physical range by intensity.
        claimed_genome = np.empty(GENOME_DIMENSION)
        for index, (_name, (low, high, _unit)) in enumerate(GENOME_PARAMS.items()):
            block = statevector[index * 10 : (index + 1) * 10].real
            target = high if block.mean() >= 0 else low
            claimed_genome[index * 10 : (index + 1) * 10] = (
                (1.0 - intensity) * (low + high) / 2.0 + intensity * target
            )

        # Signature string from the quantised state phases.
        phases = np.angle(statevector[:16])
        fake_signature = FORGED_SIGNATURE_PREFIX + "-" + "".join(
            f"{int((phase + np.pi) / (2 * np.pi) * 15):x}" for phase in phases
        )

        return self._envelope(
            {
                "session_id": session_id,
                "forged": True,
                "forged_signature": fake_signature,
                "claimed_genome": claimed_genome.tolist(),
                "forged_state_norm": float(np.linalg.norm(statevector)),
                "forged_state_purity_proxy": float(
                    np.sum(np.abs(statevector) ** 4)
                ),
            }
        )

