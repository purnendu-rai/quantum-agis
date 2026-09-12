"""Channel-tampering attack — injects noise into the quantum channel.

Models a man-in-the-middle that floods the photonic channel with
depolarising noise and perturbs the gain/loss balance of the receiving
non-Hermitian lattice. The spectral distortion of the PT-symmetric sensor
breaks the exceptional-point calibration, so Layer 2 (NHGS) flags the
perturbation while the payload itself remains authentic.
"""

from __future__ import annotations

import numpy as np

from app.attacks.base_attack import BaseAttack
from app.layers.layer2_nhgs import (
    DEFAULT_GAIN,
    DEFAULT_LOSS,
    DEFAULT_LATTICE_SIZE,
    NHGSLayer,
)

#: Labels for the injected noise channels.
NOISE_CHANNELS: tuple[str, ...] = ("depolarising", "phase_flipping", "gain_loss")


class ChannelTamperingAttack(BaseAttack):
    """Simulates man-in-the-middle noise injection on the channel."""

    name = "Channel Tampering"
    description = "Floods the channel with depolarising noise and skews the NH lattice."
    EXPECTED_DETECTION = ("NHGS",)

    def __init__(self, intensity: float = 0.5) -> None:
        """Configure the channel-tampering attack.

        Args:
            intensity: Attack strength in [0, 1] (scales noise and lattice
                perturbation).
        """
        super().__init__("channel_tampering", intensity=intensity)

    def execute(self, context: dict) -> dict:
        """Inject depolarising noise and perturb the non-Hermitian lattice.

        The noise level is ``intensity``-scaled; the lattice gain is raised
        and the loss lowered by the same factor, pushing the PT sensor away
        from its balanced operating point. The perturbed lattice is drawn on
        the seeded stream only (no file I/O), so its eigenvalues quantify the
        spectral distortion Layer 2 observes.

        Args:
            context: Read-only session snapshot; ``session_id`` is echoed.

        Returns:
            Standardized envelope whose ``modified_data`` carries
            ``tampered=True``, the noise level, the injected channel labels,
            and the perturbed ``lattice`` (4x4, nested lists) plus its
            eigenvalue spread.
        """
        rng = self._rng()
        session_id = str(context.get("session_id", "unknown-session"))

        # Depolarising noise level in [0, 1].
        noise_level = float(rng.uniform(0.2, 1.0) * self.intensity)

        # Balanced lattice, then skew gain/loss away from calibration.
        sensor = NHGSLayer()
        lattice = sensor.construct_lattice(
            size=DEFAULT_LATTICE_SIZE,
            gain=DEFAULT_GAIN + self.intensity,
            loss=DEFAULT_LOSS - self.intensity,
        )
        spectrum = sensor.compute_eigenvalues(lattice)
        spread = float(spectrum.real.max() - spectrum.real.min())

        return self._envelope(
            {
                "session_id": session_id,
                "tampered": True,
                "noise_level": noise_level,
                "noise_channels": list(NOISE_CHANNELS),
                "lattice_shape": list(lattice.shape),
                "lattice_gain": float(DEFAULT_GAIN + self.intensity),
                "lattice_loss": float(DEFAULT_LOSS - self.intensity),
                "perturbed_spectrum_spread": spread,
            }
        )
