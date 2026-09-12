"""Impersonation attack — copies a victim's public key to pose as them.

Models an adversary that harvests a legitimate user's public key (and identity
seal) and presents it as their own. Because the copied credentials are bound
to the victim's quantum device fingerprint, the attacker's own genome cannot
reproduce it: Layer 0 (QGM) flags the device mismatch even though the public
key material itself is authentic.
"""

from __future__ import annotations

from zlib import crc32

from app.attacks.base_attack import BaseAttack
from app.layers.base_layer import seeded_rng
from app.layers.layer0_qgm import GENOME_DIMENSION, QGMLayer

#: Device identity the adversary's own hardware maps to.
IMPERSONATOR_DEVICE_ID: str = "AGIS-ATTACKER-DEVICE"


class ImpersonationAttack(BaseAttack):
    """Simulates identity theft via public-key replay."""

    name = "Impersonation"
    description = "Reuses a stolen public key while the device fingerprint mismatches."
    EXPECTED_DETECTION = ("QGM",)

    def __init__(self, intensity: float = 0.5) -> None:
        """Configure the impersonation attack.

        Args:
            intensity: Attack strength in [0, 1] (scales genome distortion).
        """
        super().__init__("impersonation", intensity=intensity)

    def execute(self, context: dict) -> dict:
        """Copy the victim's public key and attach the attacker's genome.

        The victim's public key (from ``context["public_key"]``, or a
        deterministic stand-in when absent) is copied verbatim, but the
        claimed genome is the attacker's own device genome — guaranteed
        unrelated to the victim's enrolled fingerprint, so QGM detects the
        identity/fingerprint split.

        Args:
            context: Read-only session snapshot; ``session_id``,
                ``public_key``, and ``device_id`` are recognised.

        Returns:
            Standardized envelope whose ``modified_data`` carries the stolen
            ``public_key``, the ``claimed_genome`` of the attacker device
            (distorted by intensity), and ``impersonated=True``.
        """
        rng = seeded_rng(crc32(b"impersonation-genome"))
        session_id = str(context.get("session_id", "unknown-session"))
        victim_device = str(context.get("device_id", "AGIS-DEVICE-001"))

        # Public key is copied verbatim from the victim (stand-in if absent).
        public_key = context.get("public_key")
        if public_key is None:
            public_key = f"PUBKEY-{victim_device}-{session_id}"

        # Attacker's own genome: victim-independent, distorted by intensity.
        attacker_genome = QGMLayer.generate_genome(IMPERSONATOR_DEVICE_ID)
        centre = attacker_genome.mean()
        claimed_genome = (1.0 - self.intensity) * attacker_genome + self.intensity * centre

        return self._envelope(
            {
                "session_id": session_id,
                "impersonated": True,
                "stolen_public_key": public_key,
                "device_id": IMPERSONATOR_DEVICE_ID,
                "claimed_genome": claimed_genome.tolist()[
                    :GENOME_DIMENSION
                ],
                "victim_device_id": victim_device,
            }
        )

