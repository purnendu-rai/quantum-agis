"""Layer 0 — QGM (Quantum Genome Mapping).

Builds a 100-dimensional "quantum genome" fingerprint of a photonics device
from ten physical parameters (ten samples each), drawn by Monte Carlo from
realistic hardware ranges. Devices are identified by comparing binarised
genomes: the Hamming distance of a genuine re-enrolment stays below
``HAMMING_THRESHOLD`` while an unrelated (forged) genome lands near 0.5.

Genome layout (fixed order, 10 values per parameter):

    laser_jitter[ps], phase_noise[rad], polarization_dispersion[ps/nm],
    spectral_width[nm], temporal_coherence[fs], amplitude_fluctuation[%],
    phase_drift[rad/s], quantum_efficiency[ratio], dark_count_rate[Hz],
    afterpulsing[%]
"""

from __future__ import annotations

from zlib import crc32

import numpy as np

from app.core.constants import HAMMING_THRESHOLD, RANDOM_SEED, W_QGM
from app.layers.base_layer import (
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SUSPICIOUS,
    BaseLayer,
    seeded_rng,
)

#: Values per parameter block in the genome vector.
GENOME_BLOCK_SIZE: int = 10
#: Number of Monte Carlo noise trials used by verify_genome.
MONTE_CARLO_TRIALS: int = 64
#: Sensor noise used during verification, as a fraction of each range width.
MONTE_CARLO_NOISE_FRACTION: float = 0.01
#: Default device identity enrolled at construction time.
DEFAULT_DEVICE_ID: str = "AGIS-DEVICE-001"
#: Hamming distance above which a genome is treated as unrelated.
HAMMING_SUSPICIOUS_LIMIT: float = 0.25

#: Physical parameter table: name -> (low, high, unit).
GENOME_PARAMS: dict[str, tuple[float, float, str]] = {
    "laser_jitter": (0.1, 0.5, "ps"),
    "phase_noise": (0.01, 0.1, "rad"),
    "polarization_dispersion": (0.05, 0.5, "ps/nm"),
    "spectral_width": (0.5, 5.0, "nm"),
    "temporal_coherence": (100.0, 1000.0, "fs"),
    "amplitude_fluctuation": (0.5, 5.0, "percent"),
    "phase_drift": (0.001, 0.01, "rad/s"),
    "quantum_efficiency": (0.6, 0.9, "ratio"),
    "dark_count_rate": (100.0, 1000.0, "Hz"),
    "afterpulsing": (0.1, 2.0, "percent"),
}

PARAM_ORDER: tuple[str, ...] = tuple(GENOME_PARAMS.keys())
GENOME_DIMENSION: int = len(PARAM_ORDER) * GENOME_BLOCK_SIZE


class QGMLayer(BaseLayer):
    """Verifies a claimed device genome against the enrolled fingerprint."""

    def __init__(self, device_id: str = DEFAULT_DEVICE_ID) -> None:
        """Enrol the genome of ``device_id``.

        Args:
            device_id: Identifier of the device this instance vouches for.
        """
        super().__init__(layer_id=0, layer_name="QGM", weight=W_QGM)
        self.device_id: str = device_id
        self.enrolled_genome: np.ndarray = self.generate_genome(device_id)

    # ------------------------------------------------------------------ #
    #  Genome construction
    # ------------------------------------------------------------------ #
    @staticmethod
    def generate_genome(device_id: str) -> np.ndarray:
        """Generate the deterministic 100-dimensional genome of a device.

        The seed is derived from ``RANDOM_SEED`` (42) plus a stable CRC32 of
        the device id, so the same device always produces the same genome
        (across processes and machines), while different devices differ.

        Args:
            device_id: Unique device identifier.

        Returns:
            Float array of shape (100,) laid out per GENOME_PARAMS order.
        """
        rng = np.random.default_rng([RANDOM_SEED, crc32(device_id.encode("utf-8"))])
        blocks = [
            rng.uniform(low, high, GENOME_BLOCK_SIZE)
            for low, high, _unit in GENOME_PARAMS.values()
        ]
        return np.concatenate(blocks).astype(float)

    # ------------------------------------------------------------------ #
    #  Comparison
    # ------------------------------------------------------------------ #
    @staticmethod
    def _binarize(genome: np.ndarray) -> np.ndarray:
        """Binarise each parameter value against its range midpoint.

        Args:
            genome: Flat genome vector of length 100.

        Returns:
            Boolean bit array of length 100.
        """
        bits: list[np.ndarray] = []
        for index, (_name, (low, high, _unit)) in enumerate(GENOME_PARAMS.items()):
            block = genome[index * GENOME_BLOCK_SIZE : (index + 1) * GENOME_BLOCK_SIZE]
            bits.append(block > 0.5 * (low + high))
        return np.concatenate(bits)

    @staticmethod
    def compute_hamming_distance(genome_a: np.ndarray, genome_b: np.ndarray) -> float:
        """Return the normalised Hamming distance between two genomes.

        Args:
            genome_a: First genome vector (length 100).
            genome_b: Second genome vector (length 100).

        Returns:
            Fraction of differing bits in [0, 1]; ~0 for the same device,
            ~0.5 for unrelated devices.

        Raises:
            ValueError: If either genome has the wrong dimension.
        """
        a = np.asarray(genome_a, dtype=float).ravel()
        b = np.asarray(genome_b, dtype=float).ravel()
        if a.size != GENOME_DIMENSION or b.size != GENOME_DIMENSION:
            raise ValueError(f"Genomes must have {GENOME_DIMENSION} entries.")
        return float(np.mean(QGMLayer._binarize(a) != QGMLayer._binarize(b)))

    # ------------------------------------------------------------------ #
    #  Verification
    # ------------------------------------------------------------------ #
    def verify_genome(self, claimed_genome: np.ndarray) -> dict:
        """Compare a claimed genome against the enrolled one via Monte Carlo.

        Each trial adds independent 1%-of-range sensor noise to both genomes
        before binarising, yielding a robust mean Hamming distance and its
        standard deviation.

        Args:
            claimed_genome: Genome vector submitted for verification.

        Returns:
            Dict with ``hamming_distance``, ``hamming_std``, ``status``,
            ``deviation_score``, ``matched``, and ``monte_carlo_trials``.
        """
        claimed = np.asarray(claimed_genome, dtype=float).ravel()
        widths = np.concatenate(
            [
                np.full(GENOME_BLOCK_SIZE, high - low)
                for low, high, _unit in GENOME_PARAMS.values()
            ]
        )
        sigma = MONTE_CARLO_NOISE_FRACTION * widths
        rng = seeded_rng(crc32(b"qgm-verify"))

        hamming_samples = np.empty(MONTE_CARLO_TRIALS)
        for trial in range(MONTE_CARLO_TRIALS):
            noisy_enrolled = self.enrolled_genome + rng.normal(0.0, sigma)
            noisy_claimed = claimed + rng.normal(0.0, sigma)
            hamming_samples[trial] = self.compute_hamming_distance(noisy_enrolled, noisy_claimed)

        mean_hamming = float(np.mean(hamming_samples))
        if mean_hamming <= HAMMING_THRESHOLD:
            status = STATUS_PASS
        elif mean_hamming <= HAMMING_SUSPICIOUS_LIMIT:
            status = STATUS_SUSPICIOUS
        else:
            status = STATUS_FAIL

        return {
            "hamming_distance": mean_hamming,
            "hamming_std": float(np.std(hamming_samples)),
            "status": status,
            "deviation_score": float(np.clip(mean_hamming, 0.0, 1.0)),
            "matched": bool(mean_hamming <= HAMMING_THRESHOLD),
            "monte_carlo_trials": MONTE_CARLO_TRIALS,
        }

    # ------------------------------------------------------------------ #
    #  BaseLayer contract
    # ------------------------------------------------------------------ #
    def process(self, input_data: dict) -> dict:
        """Verify the device genome claimed in ``input_data``.

        Args:
            input_data: Optional keys — ``device_id`` (str; re-enrols when it
                differs from the enrolled device), ``claimed_genome``
                (sequence of 100 floats; omitted means the genuine device is
                reporting, so the enrolled genome is echoed back) and
                ``impersonation`` (bool; simulates an attacker submitting the
                enrolled genome of a *different* device).

        Returns:
            Standard result envelope; metrics carry the Hamming statistics.
        """
        device_id = str(input_data.get("device_id", self.device_id))
        if device_id != self.device_id:
            self.device_id = device_id
            self.enrolled_genome = self.generate_genome(device_id)

        claimed = input_data.get("claimed_genome")
        if claimed is None and input_data.get("impersonation"):
            # Attacker presents the genome of a different (intruder) device.
            claimed = self.generate_genome("INTRUDER-DEVICE-66")
        if claimed is None:
            claimed = self.enrolled_genome.copy()

        verdict = self.verify_genome(claimed)
        return self.make_result(
            verdict["status"],
            verdict["deviation_score"],
            {
                "device_id": device_id,
                "hamming_distance": verdict["hamming_distance"],
                "hamming_std": verdict["hamming_std"],
                "matched": verdict["matched"],
                "genome_dimension": GENOME_DIMENSION,
                "monte_carlo_trials": verdict["monte_carlo_trials"],
            },
        )
