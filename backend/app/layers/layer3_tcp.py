"""Layer 3 — TCP (Temporal Coherence Profiler).

Characterises each exchange by its temporal coherence length tau_c
(L_c = c * tau_c) derived from the photon source linewidth, and verifies a
coin-position quantum walk that spreads in O(sqrt(N)) steps. A coherent
walker spreads ballistically; a decohered (channelled) walker degrades to a
random walk with much lower spread.

Replay attacks present an out-of-family spectral fingerprint — either an
anomalous tau_c or a stale timestamp — so each exchange is compared against
the historical tau_c profile using a 3-sigma acceptance band
(legitimate: tau_c within 3 sigma of the historical mean).

The layer is stateless: the baseline tau_c is a class-level constant and the
quantum-walk evolution is deterministic.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Sequence

import numpy as np

from app.core.constants import W_TCP
from app.layers.base_layer import (
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SUSPICIOUS,
    BaseLayer,
    utc_now_iso,
)

#: Speed of light in vacuum (m/s).
SPEED_OF_LIGHT: float = 2.997_924_58e8
#: Default source parameters of the enrolled (legitimate) photon statistics.
DEFAULT_CENTER_WAVELENGTH_M: float = 1550e-9
DEFAULT_LINEWIDTH_M: float = 5e-12
#: Acceptance band — legitimate tau_c must lie within 3 sigma of the mean.
COHERENCE_SIGMA_MULTIPLIER: float = 3.0
#: Relative floor on the historical std (baselines are noiseless constants).
COHERENCE_STD_FLOOR_FRACTION: float = 1e-3
#: Excess normalisation window as a fraction of the historical mean.
COHERENCE_WINDOW_FRACTION: float = 0.15
#: Linewidth multiplier applied when a replay signature is simulated.
REPLAY_LINEWIDTH_FACTOR: float = 0.6
#: Number of pristine baseline samples used when no history is supplied.
HISTORY_SEED_SAMPLES: int = 3
#: Replay-risk classification bands.
REPLAY_RISK_SUSPICIOUS: float = 0.15
REPLAY_RISK_FAIL: float = 0.5
#: Timestamp staleness thresholds (seconds).
STALE_AFTER_S: float = 60.0
STALE_WINDOW_S: float = 3600.0
#: Default quantum-walk register; the walk cost stays O(sqrt(N)) steps.
DEFAULT_WALK_POSITIONS: int = 256
#: walk_score at or above this means the walker stayed quantum-coherent.
WALK_GENUINE_MIN: float = 0.8


def _symmetric_seed(positions: int) -> np.ndarray:
    """Return the symmetry-friendly (|0> + i|1>)/sqrt(2) coin at the centre.

    Args:
        positions: Number of lattice sites for the walk.

    Returns:
        Complex array of shape (2, positions) with unit norm.
    """
    centre = positions // 2
    seed = np.zeros((2, positions), dtype=complex)
    seed[0, centre] = 1.0 / np.sqrt(2.0)
    seed[1, centre] = 1j / np.sqrt(2.0)
    return seed


class TCPLayer(BaseLayer):
    """Profiles temporal coherence and flags out-of-family (replayed) exchanges."""

    #: Enrolled coherence time of the default source (class-level constant,
    #: never read from disk and never stored per instance).
    BASELINE_TAU_C: float = (
        DEFAULT_CENTER_WAVELENGTH_M**2 / (SPEED_OF_LIGHT * DEFAULT_LINEWIDTH_M)
    )

    def __init__(self) -> None:
        """Initialise the TCP layer identity and fusion weight."""
        super().__init__(layer_id=3, layer_name="TCP", weight=W_TCP)

    # ------------------------------------------------------------------ #
    #  Temporal coherence
    # ------------------------------------------------------------------ #
    @staticmethod
    def compute_coherence_length(photon_statistics: dict | None) -> float:
        """Compute the temporal coherence length tau_c of a photon source.

        Uses the textbook Lorentzian relation tau_c = lambda^2 / (c * dlambda).

        Args:
            photon_statistics: Dict with optional ``center_wavelength_m`` and
                ``linewidth_m`` keys; sensible defaults fill the rest.

        Returns:
            Coherence time tau_c in seconds (the spatial coherence length is
            simply c*tau_c).

        Raises:
            ValueError: If the linewidth or wavelength is non-positive.
        """
        stats = dict(photon_statistics or {})
        center = float(stats.get("center_wavelength_m", DEFAULT_CENTER_WAVELENGTH_M))
        linewidth = float(stats.get("linewidth_m", DEFAULT_LINEWIDTH_M))
        if linewidth <= 0.0:
            raise ValueError("photon linewidth must be positive.")
        if center <= 0.0:
            raise ValueError("center wavelength must be positive.")
        return center**2 / (SPEED_OF_LIGHT * linewidth)

    # ------------------------------------------------------------------ #
    #  Coherence replay check
    # ------------------------------------------------------------------ #
    @staticmethod
    def _history_entry_value(entry: Any) -> float:
        """Extract a scalar tau_c from a plain number or a history dict.

        Args:
            entry: A float or a dict carrying ``coherence_length`` / ``tau_c``.

        Returns:
            The numeric coherence value.
        """
        if isinstance(entry, dict):
            if "coherence_length" in entry:
                return float(entry["coherence_length"])
            return float(entry["tau_c"])
        return float(entry)

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        """Parse an ISO-8601 timestamp into an aware datetime.

        Args:
            value: Timestamp string or datetime.

        Returns:
            Timezone-aware datetime, or None when unparsable.
        """
        if value is None:
            return None
        try:
            text = str(value).strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None

    @classmethod
    def check_replay(
        cls,
        coherence_length: float,
        timestamp: Any = None,
        history: Sequence | None = None,
    ) -> float:
        """Score how far an exchange falls outside the historical profile.

        Legitimate exchanges keep tau_c inside the 3-sigma band around the
        historical mean (risk 0). The score ramps linearly to 1 with the
        excess over 3 sigma. A timestamp that is markedly older than the most
        recent history entry is equally treated as a replay signature.

        Args:
            coherence_length: Measured tau_c (or any consistent unit).
            timestamp: ISO-8601 timestamp of the exchange under test.
            history: Past observations as floats or dicts with
                ``coherence_length`` / ``tau_c`` and optional ``timestamp``.

        Returns:
            Replay risk in [0, 1]; 0 means fully within the trusted band.
        """
        values: list[float] = []
        reference_times: list[datetime] = []
        for entry in history or []:
            values.append(cls._history_entry_value(entry))
            if isinstance(entry, dict) and entry.get("timestamp") is not None:
                parsed = cls._parse_timestamp(entry.get("timestamp"))
                if parsed is not None:
                    reference_times.append(parsed)
        if not values:
            return 0.0

        mean = float(np.mean(values))
        sigma = max(float(np.std(values)), COHERENCE_STD_FLOOR_FRACTION * max(mean, 1e-30))
        excess = max(0.0, abs(float(coherence_length) - mean) - COHERENCE_SIGMA_MULTIPLIER * sigma)
        window = COHERENCE_WINDOW_FRACTION * max(mean, 1e-30)
        spectral_risk = float(np.clip(excess / window, 0.0, 1.0)) if window > 0.0 else (
            0.0 if excess <= 0.0 else 1.0
        )
        staleness = cls._staleness_risk(timestamp, reference_times)
        return float(max(spectral_risk, staleness))

    @classmethod
    def _staleness_risk(cls, timestamp: Any, reference_times: list[datetime]) -> float:
        """Scoring helper: is the exchange timestamp stale relative to history?

        Args:
            timestamp: Timestamp of the exchange under test.
            reference_times: Timestamps seen in the history profile.

        Returns:
            Staleness risk in [0, 1], 0 when fresh or unknown.
        """
        submitted = cls._parse_timestamp(timestamp)
        if submitted is None or not reference_times:
            return 0.0
        newest = max(reference_times)
        if submitted >= newest:
            return 0.0
        overdue = max(0.0, (newest - submitted).total_seconds() - STALE_AFTER_S)
        return float(np.clip(overdue / STALE_WINDOW_S, 0.0, 1.0))

# ------------------------------------------------------------------ #
    #  Quantum walk verification
    # ------------------------------------------------------------------ #
    @classmethod
    def _parse_walk_input(cls, state: Any) -> tuple[int, bool, np.ndarray | None]:
        """Normalise a ``quantum_walk_verify`` state argument.

        Supported forms: ``None`` (defaults), an int position count, a dict
        with ``positions`` / ``decoherent`` / ``initial``, or an even-length
        amplitude array treated as a (2, N) coin-position state.

        Args:
            state: Raw walk configuration.

        Returns:
            Tuple of (positions, decoherent, initial amplitudes or None).
        """
        decoherent = False
        initial: np.ndarray | None = None
        if state is None:
            positions = DEFAULT_WALK_POSITIONS
        elif isinstance(state, dict):
            positions = int(state.get("positions", DEFAULT_WALK_POSITIONS))
            decoherent = bool(state.get("decoherent", False))
            raw = state.get("initial", state.get("amplitudes"))
            if raw is not None:
                initial = cls._validate_initial(np.asarray(raw, dtype=complex), positions)
        elif isinstance(state, (int, np.integer)):
            positions = int(state)
        else:
            values = np.asarray(state, dtype=complex).ravel()
            positions = values.size // 2
            initial = cls._validate_initial(values, positions)
        return positions, decoherent, initial

    @staticmethod
    def _validate_initial(amplitudes: np.ndarray, positions: int) -> np.ndarray:
        """Reshape and normalise an initial coin-position amplitude vector.

        Args:
            amplitudes: Flat array of length 2*positions.
            positions: Number of lattice sites.

        Returns:
            Normalised array of shape (2, positions).

        Raises:
            ValueError: If the length does not fit the position count.
        """
        flat = amplitudes.ravel()
        if flat.size != 2 * positions:
            raise ValueError(
                f"initial amplitudes must have length 2*positions={2 * positions}, got {flat.size}."
            )
        matrix = flat.reshape(2, positions)
        norm = float(np.linalg.norm(matrix))
        if norm > 0.0:
            matrix = matrix / norm
        return matrix

    @staticmethod
    def _pure_evolution(amplitudes: np.ndarray, steps: int) -> tuple[np.ndarray, float]:
        """Run a deterministic Hadamard-coined quantum walk with reflections.

        Each step applies the Hadamard coin then a conditional shift; the
        boundaries reflect so the wavefunction stays normalised.

        Args:
            amplitudes: Initial (2, N) coin-position amplitudes.
            steps: Number of walk steps.

        Returns:
            Tuple of (position probability distribution, positional std).
        """
        amp = np.array(amplitudes, dtype=complex)
        for _ in range(steps):
            coin_0 = (amp[0] + amp[1]) / np.sqrt(2.0)
            coin_1 = (amp[0] - amp[1]) / np.sqrt(2.0)
            swept = np.zeros_like(amp)
            swept[0, 1:] += coin_0[:-1]      # coin-0 walker hops left
            swept[0, 0] += coin_0[0]         # reflect at the left edge
            swept[1, :-1] += coin_1[1:]      # coin-1 walker hops right
            swept[1, -1] += coin_1[-1]       # reflect at the right edge
            amp = swept
        prob = np.abs(amp) ** 2
        prob = prob.sum(axis=0)
        total = prob.sum()
        if total > 0.0:
            prob = prob / total
        positions = np.arange(amp.shape[1])
        mean = float(prob @ positions)
        std = float(np.sqrt(max((prob @ (positions - mean) ** 2), 0.0)))
        return prob, std

    @staticmethod
    def _classical_evolution(positions: int, steps: int) -> tuple[np.ndarray, float]:
        """Run a reflected classical random walk (decoherence reference).

        Args:
            positions: Number of lattice sites.
            steps: Number of walk steps.

        Returns:
            Tuple of (position probability distribution, positional std).
        """
        prob = np.zeros(positions)
        prob[positions // 2] = 1.0
        for _ in range(steps):
            drifted = np.zeros(positions)
            drifted[1:] += 0.5 * prob[:-1]   # hop right
            drifted[:-1] += 0.5 * prob[1:]   # hop left
            drifted[0] += 0.5 * prob[0]      # reflect at the left edge
            drifted[-1] += 0.5 * prob[-1]    # reflect at the right edge
            prob = drifted
        index = np.arange(positions)
        mean = float(prob @ index)
        std = float(np.sqrt(max((prob @ (index - mean) ** 2), 0.0)))
        return prob, std
    @classmethod
    def quantum_walk_verify(cls, state: Any = None, steps: int | None = None) -> dict:
        """Run the O(sqrt(N)) coherence walk and score its spread.

        The walker starts from a symmetric delocalised coin at the lattice
        centre and evolves for ``floor(sqrt(N))`` steps (configurable). A
        coherent walker spreads ballistically, so its spread reproduces the
        exact quantum evolution; a decohered walker degrades towards the
        diffusive random-walk spread and receives a proportionally lower
        ``walk_score``.

        Args:
            state: ``None``, an int position count, a config dict
                (``positions`` / ``decoherent`` / ``initial``) or a flat
                (2, N) amplitude array.
            steps: Number of walk steps; defaults to floor(sqrt(positions)).

        Returns:
            Dict with ``positions``, ``steps``, ``spread_std``,
            ``expected_quantum_std``, ``walk_score`` in [0, 1],
            ``genuine_quantum`` (bool), ``decoherent`` (bool) and the observed
            ``distribution`` (position probabilities, JSON-safe).
        """
        positions, decoherent, initial = cls._parse_walk_input(state)
        if steps is None:
            steps = max(1, int(math.floor(math.sqrt(positions))))
        steps = max(1, int(steps))
        if initial is None:
            initial = _symmetric_seed(positions)

        expected_prob, expected_std = cls._pure_evolution(initial, steps)
        if decoherent:
            observed_prob, observed_std = cls._classical_evolution(positions, steps)
            score = float(np.clip(observed_std / max(expected_std, 1e-12), 0.0, 1.0))
        else:
            observed_prob, observed_std = expected_prob, expected_std
            score = 1.0

        return {
            "positions": positions,
            "steps": steps,
            "spread_std": float(observed_std),
            "expected_quantum_std": float(expected_std),
            "walk_score": score,
            "genuine_quantum": bool(score >= WALK_GENUINE_MIN),
            "decoherent": bool(decoherent),
            "distribution": [float(value) for value in observed_prob],
        }
# ------------------------------------------------------------------ #
    #  BaseLayer contract
    # ------------------------------------------------------------------ #
    def process(self, input_data: dict) -> dict:
        """Profile the exchange coherence and screen it for replay attacks.

        Args:
            input_data: Optional keys —
                ``photon_statistics`` (dict with ``linewidth_m`` /
                ``center_wavelength_m``), ``replay`` (bool; simulates an
                out-of-family source), ``coherence_length`` (explicit tau_c
                override), ``timestamp`` (ISO-8601), ``history`` (past tau_c
                samples), ``state`` (quantum-walk config) and ``decoherent``
                (bool; simulate channel decoherence).

        Returns:
            Standard result envelope; PASS when tau_c sits inside the 3-sigma
            historical band and the walker stays coherent, SUSPICIOUS for a
            drift or decohered walk, and FAIL for a replay.
        """
        replay = bool(input_data.get("replay", False))
        stats = dict(input_data.get("photon_statistics") or {})
        if replay:
            stats.setdefault("linewidth_m", DEFAULT_LINEWIDTH_M * REPLAY_LINEWIDTH_FACTOR)

        if "coherence_length" in input_data and input_data["coherence_length"] is not None:
            tau_c = float(input_data["coherence_length"])
        else:
            tau_c = self.compute_coherence_length(stats)

        timestamp = input_data.get("timestamp")
        if timestamp is None:
            timestamp = utc_now_iso()
        timestamp = str(timestamp)

        history = input_data.get("history")
        if history is None:
            history = [self.BASELINE_TAU_C] * HISTORY_SEED_SAMPLES

        replay_risk = self.check_replay(tau_c, timestamp, history)

        walk_state = input_data.get("state")
        if walk_state is None:
            walk_state = {
                "positions": DEFAULT_WALK_POSITIONS,
                "decoherent": bool(input_data.get("decoherent", False)),
            }
        walk = self.quantum_walk_verify(walk_state, input_data.get("steps"))

        if replay_risk >= REPLAY_RISK_FAIL:
            status = STATUS_FAIL
        elif replay_risk >= REPLAY_RISK_SUSPICIOUS:
            status = STATUS_SUSPICIOUS
        elif not walk["genuine_quantum"]:
            status = STATUS_SUSPICIOUS
        else:
            status = STATUS_PASS

        deviation = float(max(replay_risk, 1.0 - walk["walk_score"]))
        historical_mean, historical_std = self._history_summary(history)
        band = COHERENCE_SIGMA_MULTIPLIER * max(
            historical_std, COHERENCE_STD_FLOOR_FRACTION * max(historical_mean, 1e-30)
        )

        return self.make_result(
            status,
            deviation,
            {
                "coherence_time_s": tau_c,
                "coherence_length_m": SPEED_OF_LIGHT * tau_c,
                "linewidth_m": float(stats.get("linewidth_m", DEFAULT_LINEWIDTH_M)),
                "replay_risk": replay_risk,
                "historical_mean": historical_mean,
                "historical_std": historical_std,
                "within_3_sigma": bool(abs(tau_c - historical_mean) <= band),
                "genuine_quantum_walk": walk["genuine_quantum"],
                "walk_score": walk["walk_score"],
                "walk_positions": walk["positions"],
                "walk_steps": walk["steps"],
                "expected_quantum_std": walk["expected_quantum_std"],
            },
        )

    @classmethod
    def _history_summary(cls, history: Sequence) -> tuple[float, float]:
        """Return (mean, std) of the historical coherence samples.

        Args:
            history: Sequence of floats or history dicts.

        Returns:
            Tuple of mean and standard deviation (zeros when empty).
        """
        values = [cls._history_entry_value(entry) for entry in history or []]
        if not values:
            return 0.0, 0.0
        return float(np.mean(values)), float(np.std(values))
