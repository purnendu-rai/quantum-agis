"""Layer 1 — HIS (HOM Interferometry Sentinel).

Simulates Hong-Ou-Mandel (HOM) two-photon interference. Identical
(indistinguishable) photon wavepackets interfere constructively at the beam
splitter and yield a visibility near the legitimate baseline of 0.98 +/- 0.02;
spectrally distinguishable photons (e.g. a forged source) cannot reproduce
the dip and fall below the forgery cutoff of 0.5.

Visibility is computed as V = eta * integral(|psi_1(t) psi_2(t)|^2 dt)
normalised by each photon's self-overlap, where eta models detector
efficiency. All randomness flows from the seeded RNG policy (seed 42).
"""

from __future__ import annotations

from zlib import crc32

import numpy as np

from app.core.constants import RANDOM_SEED, W_HIS
from app.layers.base_layer import (
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SUSPICIOUS,
    BaseLayer,
    seeded_rng,
)

#: Legitimate-device baseline visibility and its tolerated band.
HOM_BASELINE: float = 0.98
HOM_BASELINE_TOLERANCE: float = 0.02
#: Visibility below this indicates a forged / distinguishable photon source.
HOM_FORGERY_MAX: float = 0.5
#: Detector efficiency cap applied to the normalised overlap.
HOM_DETECTOR_EFFICIENCY: float = 0.98
#: Central-frequency offset applied to forged photons, in temporal sigmas.
FORGED_OFFSET_SIGMAS: float = 4.0
#: Time-grid resolution (points) and half-width (in sigmas) for pulses.
PHOTON_GRID_POINTS: int = 512
PHOTON_GRID_SPAN_SIGMAS: float = 8.0
#: Number of recent visibility samples used for phase-drift estimation.
PHASE_HISTORY_WINDOW: int = 8


class HISLayer(BaseLayer):
    """Detects forged photon sources via HOM-interference visibility."""

    def __init__(self) -> None:
        """Initialise the sentinel with an empty visibility history."""
        super().__init__(layer_id=1, layer_name="HIS", weight=W_HIS)
        self.visibility_history: list[float] = []

    # ------------------------------------------------------------------ #
    #  Photon-pair simulation
    # ------------------------------------------------------------------ #
    @staticmethod
    def simulate_photon_pair(
        spectral_width: float = 1.0, distinguishable: bool = False
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate a pair of single-photon wavepackets on a shared time grid.

        Legitimate pairs share central frequency and (up to ~0.5% jitter)
        spectral width, so they interfere. Distinguishable pairs are offset
        by ``FORGED_OFFSET_SIGMAS`` sigmas, modelling a mismatched source.

        Args:
            spectral_width: Source spectral width (arbitrary units); the
                temporal sigma is 1/spectral_width.
            distinguishable: When True, the second photon is spectrally
                displaced (forged/incompatible source).

        Returns:
            Tuple (psi_1, psi_2) of complex amplitude arrays, each with
            unit norm over the grid.
        """
        rng = seeded_rng(crc32(b"his-photon"))
        sigma_1 = 1.0 / float(spectral_width)
        sigma_2 = sigma_1 * (1.0 + rng.uniform(-0.005, 0.005))
        center_1 = 0.0
        center_2 = (
            FORGED_OFFSET_SIGMAS * sigma_1
            if distinguishable
            else rng.uniform(-0.01, 0.01) * sigma_1
        )
        t = np.linspace(
            -PHOTON_GRID_SPAN_SIGMAS * sigma_1,
            PHOTON_GRID_SPAN_SIGMAS * sigma_1,
            PHOTON_GRID_POINTS,
        )

        def _packet(center: float, sigma: float) -> np.ndarray:
            """Return a normalised Gaussian wavepacket with random global phase.

            Args:
                center: Central time of the packet.
                sigma: Temporal standard deviation.

            Returns:
                Complex amplitude array psi(t) with integral |psi|^2 dt = 1.
            """
            envelope = (1.0 / (2.0 * np.pi * sigma**2)) ** 0.25 * np.exp(
                -((t - center) ** 2) / (4.0 * sigma**2)
            )
            return envelope * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi))

        return _packet(center_1, sigma_1), _packet(center_2, sigma_2)

    # ------------------------------------------------------------------ #
    #  Interference metrics
    # ------------------------------------------------------------------ #
    @staticmethod
    def compute_hom_visibility(
        photon_1: np.ndarray, photon_2: np.ndarray, dt: float = 1.0
    ) -> float:
        """Compute HOM visibility from two wavepackets.

        Implements V = eta * integral(|psi_1(t) psi_2(t)|^2 dt), normalised
        by the photons' self-overlaps so identical photons give eta and
        spectrally disjoint photons give ~0.

        Args:
            photon_1: First wavepacket amplitude array.
            photon_2: Second wavepacket amplitude array.
            dt: Time-grid spacing (cancels in the normalised ratio).

        Returns:
            Visibility in [0, 1].
        """
        psi_1 = np.asarray(photon_1, dtype=complex)
        psi_2 = np.asarray(photon_2, dtype=complex)
        overlap = np.trapezoid(np.abs(psi_1 * psi_2) ** 2, dx=dt)
        reference = np.sqrt(
            np.trapezoid(np.abs(psi_1) ** 4, dx=dt)
            * np.trapezoid(np.abs(psi_2) ** 4, dx=dt)
        )
        if reference <= 0.0:
            return 0.0
        return float(np.clip(HOM_DETECTOR_EFFICIENCY * overlap / reference, 0.0, 1.0))

    @staticmethod
    def compute_phase_shift(visibility_history: list[float]) -> float:
        """Estimate accumulated channel phase drift from visibility history.

        The drift is the amount by which the recent mean visibility has
        fallen below the legitimate baseline (clipped at zero).

        Args:
            visibility_history: Recent visibility samples, oldest first.

        Returns:
            Non-negative drift estimate; ~0 for a healthy channel.
        """
        recent = [float(v) for v in list(visibility_history)[-PHASE_HISTORY_WINDOW:]]
        if not recent:
            return 0.0
        return float(max(0.0, HOM_BASELINE - float(np.mean(recent))))

    # ------------------------------------------------------------------ #
    #  BaseLayer contract
    # ------------------------------------------------------------------ #
    def process(self, input_data: dict) -> dict:
        """Simulate one HOM exchange and classify the photon source.

        Args:
            input_data: Optional keys — ``spectral_width`` (float, default
                1.0), ``forged`` (bool; also accepts ``distinguishable``),
                and ``visibility_history`` (list of prior visibilities).

        Returns:
            Standard result envelope; metrics carry the visibility, phase
            shift, and classification band.
        """
        spectral_width = float(input_data.get("spectral_width", 1.0))
        distinguishable = bool(
            input_data.get("forged", False) or input_data.get("distinguishable", False)
        )

        psi_1, psi_2 = self.simulate_photon_pair(spectral_width, distinguishable=distinguishable)
        visibility = self.compute_hom_visibility(psi_1, psi_2)
        self.visibility_history.append(visibility)

        history = list(input_data.get("visibility_history", [])) + [visibility]
        phase_shift = self.compute_phase_shift(history)

        if visibility >= HOM_BASELINE - HOM_BASELINE_TOLERANCE:
            status = STATUS_PASS
        elif visibility >= HOM_FORGERY_MAX:
            status = STATUS_SUSPICIOUS
        else:
            status = STATUS_FAIL
        deviation = max(0.0, (HOM_BASELINE - visibility) / HOM_BASELINE)

        return self.make_result(
            status,
            deviation,
            {
                "hom_visibility": visibility,
                "phase_shift": phase_shift,
                "spectral_width": spectral_width,
                "distinguishable": distinguishable,
                "baseline": HOM_BASELINE,
                "within_baseline_band": bool(
                    abs(visibility - HOM_BASELINE) <= HOM_BASELINE_TOLERANCE
                ),
            },
        )
