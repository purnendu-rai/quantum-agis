"""Layer 2 — NHGS (Non-Hermitian Ghost Sensor).

Fingerprints a quantum channel through the eigenvalue spectrum of a
non-Hermitian (PT-symmetric) tight-binding lattice with balanced gain and
loss. A healthy channel reproduces the enrolled spectrum; tampering injects
energy/phase noise that drives the lattice across an exceptional point where
pairs of eigenvalues coalesce and the all-real spectrum turns complex. The
spectral shift relative to the enrolled baseline is the detection signal.

The layer is stateless: the enrolled baseline spectrum is a class-level
constant derived from the default lattice parameters, and no per-instance
state is required by the analysis.
"""

from __future__ import annotations

import numpy as np

from app.core.constants import W_NHGS
from app.layers.base_layer import (
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SUSPICIOUS,
    BaseLayer,
    request_rng,
)

#: Default lattice geometry — a 4-site chain (Hamiltonian matrix is 4x4).
DEFAULT_LATTICE_SIZE: int = 4
#: Gain/loss amplitudes of the enrolled (legitimate) lattice.
DEFAULT_GAIN: float = 0.5
DEFAULT_LOSS: float = -0.5
#: Nearest-neighbour hopping amplitude.
HOPPING_STRENGTH: float = 1.0
#: Complex-plane distance below which an eigenvalue pair counts as coalesced
#: (i.e. sitting at an exceptional point).
EP_COALESCENCE_TOLERANCE: float = 1e-4
#: Spectral-shift classification bands (relative to the enrolled spectrum).
#: shift <= PASS_MAX is healthy; <= SUSPICIOUS_MAX is watch; anything above
#: signals active tampering / a broken PT phase.
NHGS_SHIFT_PASS_MAX: float = 0.08
NHGS_SHIFT_SUSPICIOUS_MAX: float = 0.35
#: Imaginary-part threshold used to count PT-broken ("ghost") eigenmodes.
BROKEN_MODE_IMAG_TOL: float = 1e-8
#: Complex-noise scale applied when a tampering probe is requested.
TAMPER_NOISE_SCALE: float = 0.25


def _pt_lattice(size: int, gain: float, loss: float, hopping: float) -> np.ndarray:
    """Return the balanced gain/loss tight-binding matrix of ``size`` sites.

    Even sites carry +i*gain, odd sites carry +i*loss, and neighbouring sites
    are coupled by the real hopping amplitude.

    Args:
        size: Number of lattice sites (Hamiltonian dimension).
        gain: Imaginary on-site amplitude of the gain sublattice.
        loss: Imaginary on-site amplitude of the loss sublattice.
        hopping: Nearest-neighbour coupling.

    Returns:
        Complex Hermitian-conjugate-*breaking* matrix of shape (size, size).
    """
    lattice = np.zeros((size, size), dtype=complex)
    for site in range(size):
        lattice[site, site] = 1j * (gain if site % 2 == 0 else loss)
        if site + 1 < size:
            lattice[site, site + 1] = hopping
            lattice[site + 1, site] = hopping
    return lattice


class NHGSLayer(BaseLayer):
    """Fingerprints channels with a non-Hermitian spectral probe."""

    #: Enrolled spectrum of the default legitimate lattice (deterministic,
    #: class-level constant — never stored per instance or read from a file).
    BASELINE_SPECTRUM: tuple[complex, ...] = tuple(
        np.sort_complex(
            np.linalg.eigvals(
                _pt_lattice(DEFAULT_LATTICE_SIZE, DEFAULT_GAIN, DEFAULT_LOSS, HOPPING_STRENGTH)
            )
        )
    )

    def __init__(self) -> None:
        """Initialise the NHGS layer identity and fusion weight."""
        super().__init__(layer_id=2, layer_name="NHGS", weight=W_NHGS)

    # ------------------------------------------------------------------ #
    #  Lattice construction and spectral analysis
    # ------------------------------------------------------------------ #
    @staticmethod
    def construct_lattice(size: int, gain: float, loss: float) -> np.ndarray:
        """Build the gain/loss (PT-symmetric) lattice Hamiltonian.

        Args:
            size: Number of lattice sites.
            gain: Gain amplitude for the gain sublattice.
            loss: Loss amplitude for the loss sublattice.

        Returns:
            Complex non-Hermitian matrix of shape (size, size).
        """
        return _pt_lattice(int(size), float(gain), float(loss), HOPPING_STRENGTH)

    @staticmethod
    def compute_eigenvalues(lattice: np.ndarray) -> np.ndarray:
        """Diagonalise the lattice Hamiltonian.

        Args:
            lattice: Square non-Hermitian matrix.

        Returns:
            Complex eigenvalue array (unsorted), length = lattice shape.
        """
        return np.asarray(np.linalg.eigvals(np.asarray(lattice, dtype=complex)))

    @staticmethod
    def find_exceptional_points(spectrum) -> list[tuple[int, int]]:
        """Locate exceptional points where eigenvalues coalesce.

        Two eigenvalues are treated as coalesced when their complex-plane
        distance does not exceed ``sqrt(n) * EP_COALESCENCE_TOLERANCE``.

        Args:
            spectrum: Array of eigenvalues.

        Returns:
            List of ``(i, j)`` index pairs (with ``i < j``) whose eigenvalues
            have coalesced within tolerance.
        """
        values = np.asarray(spectrum, dtype=complex).ravel()
        limit = np.sqrt(max(values.size, 1)) * EP_COALESCENCE_TOLERANCE
        pairs: list[tuple[int, int]] = []
        for i in range(values.size):
            for j in range(i + 1, values.size):
                if abs(values[i] - values[j]) <= limit:
                    pairs.append((int(i), int(j)))
        return pairs

    @staticmethod
    def detect_spectral_shift(
        baseline_spectrum, current_spectrum, scale: float | None = None
    ) -> float:
        """Measure the mean eigenvalue drift of one spectrum against another.

        Both spectra are sorted identically (by real then imaginary part)
        before pairwise comparison, so the measure is permutation-invariant.
        The shift is normalised by the mean eigenvalue magnitude of the
        baseline (unless an explicit ``scale`` is supplied).

        Args:
            baseline_spectrum: Enrolled (reference) eigenvalue array.
            current_spectrum: Channel snapshot eigenvalue array.
            scale: Optional explicit normalisation scale; defaults to the mean
                |lambda| of the baseline.

        Returns:
            Non-negative normalised spectral shift.

        Raises:
            ValueError: If the two spectra have different lengths.
        """
        reference = np.sort_complex(np.asarray(baseline_spectrum, dtype=complex).ravel())
        current = np.sort_complex(np.asarray(current_spectrum, dtype=complex).ravel())
        if reference.size != current.size:
            raise ValueError(
                "baseline and current spectra must have the same number of eigenvalues "
                f"({reference.size} vs {current.size})."
            )
        if scale is None:
            scale = float(np.mean(np.abs(reference)))
        scale = max(abs(float(scale)), 1e-12)
        return float(np.mean(np.abs(current - reference)) / scale)

    # ------------------------------------------------------------------ #
    #  BaseLayer contract
    # ------------------------------------------------------------------ #
    def process(self, input_data: dict) -> dict:
        """Analyse the channel spectrum for non-Hermitian tamper signatures.

        Args:
            input_data: Optional keys —
                ``size`` (int, default 4), ``gain`` and ``loss`` (floats,
                defaults 0.5 / -0.5), ``tampered`` (bool; injects seeded
                complex lattice noise), ``spectrum`` (explicit current
                eigenvalue array, skipping lattice construction) and
                ``baseline_spectrum`` (overrides the enrolled baseline).

        Returns:
            Standard result envelope; status is PASS when the spectrum sits
            on the enrolled baseline, SUSPICIOUS inside the drift band, and
            FAIL when the lattice is driven past its exceptional point.
        """
        size = int(input_data.get("size", DEFAULT_LATTICE_SIZE))
        gain = float(input_data.get("gain", DEFAULT_GAIN))
        loss = float(input_data.get("loss", DEFAULT_LOSS))
        tampered = bool(input_data.get("tampered", False))
        intensity = float(np.clip(float(input_data.get("intensity", 1.0)), 0.1, 1.0))

        baseline = input_data.get("baseline_spectrum")
        if baseline is None:
            baseline = self.BASELINE_SPECTRUM

        current = input_data.get("spectrum")
        if current is None:
            lattice = self.construct_lattice(size, gain, loss)
            if tampered:
                rng = request_rng(input_data, "nhgs-tamper")
                lattice = lattice + TAMPER_NOISE_SCALE * (
                    rng.standard_normal(lattice.shape) + 1j * rng.standard_normal(lattice.shape)
                )
            current = self.compute_eigenvalues(lattice)
        current = np.asarray(current, dtype=complex)

        shift = self.detect_spectral_shift(baseline, current)
        exceptional_points = self.find_exceptional_points(current)
        broken_modes = int(np.sum(np.abs(current.imag) > BROKEN_MODE_IMAG_TOL))

        if shift <= NHGS_SHIFT_PASS_MAX:
            status = STATUS_PASS
        elif shift <= NHGS_SHIFT_SUSPICIOUS_MAX:
            status = STATUS_SUSPICIOUS
        else:
            status = STATUS_FAIL
        # Coalesced eigenvalues (an exceptional point in the channel) always
        # warrant a closer look, even if the mean shift is still small.
        if status == STATUS_PASS and exceptional_points:
            status = STATUS_SUSPICIOUS

        return self.make_result(
            status,
            shift,
            {
                "lattice_size": size,
                "gain": gain,
                "loss": loss,
                "intensity": intensity,
                "spectral_shift": shift,
                "exceptional_points": exceptional_points,
                "broken_modes": broken_modes,
                "baseline_scale": float(np.mean(np.abs(np.asarray(baseline, dtype=complex)))),
            },
        )
