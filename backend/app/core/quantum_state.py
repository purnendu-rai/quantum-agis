"""Quantum state representation (pure NumPy/SciPy, deployment-safe).

``QuantumState`` stores an N-qubit state. Pure states hold a normalised
amplitude vector; states produced by ``partial_trace`` may be mixed and hold a
density matrix instead. All stochastic behaviour draws from the module-level
seeded RNG (``RANDOM_SEED``) so results are reproducible.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import sqrtm

from app.core.constants import BELL_STATES, HADAMARD, RANDOM_SEED

# Single deterministic RNG shared by quantum_state, measurements, teleportation.
RNG = np.random.default_rng(RANDOM_SEED)

_NORMALISATION_TOL: float = 1e-6


class QuantumState:
    """An N-qubit quantum state (pure statevector or mixed density matrix)."""

    def __init__(self, amplitudes: np.ndarray, num_qubits: int) -> None:
        """Build a pure state from a normalised amplitude vector.

        Args:
            amplitudes: Complex amplitudes in the computational basis, length 2**num_qubits.
            num_qubits: Number of qubits in the register.

        Raises:
            ValueError: If the length does not match or the vector is not normalised.
        """
        amps = np.asarray(amplitudes, dtype=complex).ravel()
        if amps.size != 2**num_qubits:
            raise ValueError(
                f"Expected {2**num_qubits} amplitudes for {num_qubits} qubits, got {amps.size}."
            )
        norm = float(np.sum(np.abs(amps) ** 2))
        if not np.isclose(norm, 1.0, atol=_NORMALISATION_TOL):
            raise ValueError(f"State is not normalised: sum |a|^2 = {norm:.8f}.")
        self.num_qubits: int = num_qubits
        self._amplitudes: np.ndarray = amps
        self._rho: np.ndarray | None = None  # set only for mixed states

    # ------------------------------------------------------------------ #
    #  Internal factory
    # ------------------------------------------------------------------ #
    @classmethod
    def _from_density(cls, rho: np.ndarray, num_qubits: int) -> "QuantumState":
        """Construct a (possibly mixed) state directly from a density matrix.

        Args:
            rho: Density matrix of shape (2**n, 2**n) with unit trace.
            num_qubits: Number of qubits.

        Returns:
            QuantumState holding the mixed state.
        """
        state = cls.__new__(cls)
        state.num_qubits = num_qubits
        state._amplitudes = np.zeros(2**num_qubits, dtype=complex)
        state._rho = np.asarray(rho, dtype=complex)
        return state

    # ------------------------------------------------------------------ #
    #  Core properties and metrics
    # ------------------------------------------------------------------ #
    @property
    def amplitudes(self) -> np.ndarray:
        """Return the amplitude vector (zeros for mixed states)."""
        return self._amplitudes

    def density_matrix(self) -> np.ndarray:
        """Return the density matrix rho = |psi><psi| (or the stored mixed rho)."""
        if self._rho is not None:
            return self._rho.copy()
        return np.outer(self._amplitudes, self._amplitudes.conj())

    def fidelity(self, other: "QuantumState") -> float:
        """Return the state fidelity F in [0, 1] against another state.

        Pure-pure states use F = |<a|b>|^2; mixed states use the Uhlmann
        fidelity F = (Tr sqrt(sqrt(rho_a) rho_b sqrt(rho_a)))^2.

        Args:
            other: Reference state.

        Returns:
            Fidelity in [0, 1].
        """
        if self._rho is None and other._rho is None:
            overlap = np.vdot(self._amplitudes, other._amplitudes)
            return float(np.abs(overlap) ** 2)
        rho_a = self.density_matrix()
        rho_b = other.density_matrix()
        sqrt_a = sqrtm(rho_a)
        inner = sqrtm(sqrt_a @ rho_b @ sqrt_a)
        return float(np.real(np.trace(inner)) ** 2)

    def bures_distance(self, other: "QuantumState") -> float:
        """Return the Bures distance D_B = sqrt(2 (1 - sqrt(F))).

        Args:
            other: Reference state.

        Returns:
            Bures distance in [0, sqrt(2)].
        """
        return float(np.sqrt(max(0.0, 2.0 * (1.0 - np.sqrt(self.fidelity(other))))))

    # ------------------------------------------------------------------ #
    #  Transformations
    # ------------------------------------------------------------------ #
    def partial_trace(self, qubit_index: int) -> "QuantumState":
        """Trace out ``qubit_index`` and return the remaining (N-1)-qubit state.

        Args:
            qubit_index: Index of the qubit to discard (0-based, little-endian).

        Returns:
            Reduced QuantumState, generally mixed.

        Raises:
            ValueError: If the register has only one qubit or the index is out of range.
        """
        if self.num_qubits < 2:
            raise ValueError("Cannot partial-trace a single-qubit state.")
        if not 0 <= qubit_index < self.num_qubits:
            raise ValueError(f"Qubit index {qubit_index} out of range for {self.num_qubits} qubits.")
        kept = [q for q in range(self.num_qubits) if q != qubit_index]
        reduced = _partial_trace_matrix(self.density_matrix(), keep=kept, n=self.num_qubits)
        return QuantumState._from_density(reduced, self.num_qubits - 1)

    def tensor_product(self, other: "QuantumState") -> "QuantumState":
        """Return the Kronecker product self (x) other as a new pure state.

        Args:
            other: State appended as the higher-order (later) qubits.

        Returns:
            Combined QuantumState with num_qubits = self + other.

        Raises:
            ValueError: If either operand is mixed.
        """
        if self._rho is not None or other._rho is not None:
            raise ValueError("Tensor product requires pure states.")
        combined = np.kron(self._amplitudes, other._amplitudes)
        return QuantumState(combined, self.num_qubits + other.num_qubits)

    def measure(self, basis: str = "computational") -> tuple[int, float]:
        """Sample a full-register measurement outcome.

        Args:
            basis: ``"computational"`` (Z) or ``"hadamard"`` (X on every qubit).

        Returns:
            Tuple of (outcome index in the chosen basis, its probability).
        """
        rho = self.density_matrix()
        if basis in ("hadamard", "x"):
            rot = _kron_all([HADAMARD] * self.num_qubits)
            rho = rot @ rho @ rot.conj().T
        probs = np.clip(np.real(np.diag(rho)), 0.0, None)
        total = probs.sum()
        probs = probs / total if total > 0 else probs
        outcome = int(RNG.choice(probs.size, p=probs))
        return outcome, float(probs[outcome])

    # ------------------------------------------------------------------ #
    #  Factories
    # ------------------------------------------------------------------ #
    @classmethod
    def from_bell_state(cls, state_type: str) -> "QuantumState":
        """Create a two-qubit Bell state by name.

        Args:
            state_type: One of ``phi_plus``, ``phi_minus``, ``psi_plus``, ``psi_minus``.

        Returns:
            QuantumState for the Bell pair.

        Raises:
            KeyError: For an unknown state_type.
        """
        return cls(BELL_STATES[state_type], num_qubits=2)

    @classmethod
    def from_bloch_vector(cls, theta: float, phi: float) -> "QuantumState":
        """Create a single-qubit state from Bloch-sphere angles.

        Args:
            theta: Polar angle in radians (0 = |0>, pi = |1>).
            phi: Azimuthal angle in radians.

        Returns:
            QuantumState for cos(theta/2)|0> + e^{i phi} sin(theta/2)|1>.
        """
        amps = np.array([np.cos(theta / 2), np.exp(1j * phi) * np.sin(theta / 2)], dtype=complex)
        return cls(amps, num_qubits=1)

    @classmethod
    def random(cls, num_qubits: int) -> "QuantumState":
        """Create a random pure state (Haar-like) from the seeded RNG.

        Args:
            num_qubits: Number of qubits.

        Returns:
            Normalised random QuantumState.
        """
        real = RNG.standard_normal(2**num_qubits)
        imag = RNG.standard_normal(2**num_qubits)
        amps = (real + 1j * imag).astype(complex)
        amps /= np.linalg.norm(amps)
        return cls(amps, num_qubits=num_qubits)


# ---------------------------------------------------------------------- #
#  Module-level helpers
# ---------------------------------------------------------------------- #
def _kron_all(mats: list[np.ndarray]) -> np.ndarray:
    """Kronecker-product a list of matrices left-to-right.

    Args:
        mats: Matrices in qubit order (qubit 0 first).

    Returns:
        Combined operator of dimension 2**len(mats).
    """
    result = np.array([[1.0 + 0j]])
    for mat in mats:
        result = np.kron(result, mat)
    return result


def _partial_trace_matrix(rho: np.ndarray, keep: list[int], n: int) -> np.ndarray:
    """Compute the partial trace of a density matrix over the discarded qubits.

    Args:
        rho: Density matrix of shape (2**n, 2**n).
        keep: Indices of qubits to retain.
        n: Total qubit count.

    Returns:
        Reduced density matrix over the kept qubits (ascending index order).
    """
    traced = [q for q in range(n) if q not in keep]
    tensor = rho.reshape([2] * (2 * n))
    for i, q in enumerate(sorted(traced)):
        axis1 = q - i                     # row axis after previous removals
        axis2 = n + q - 2 * i             # column axis after previous removals
        tensor = np.trace(tensor, axis1=axis1, axis2=axis2)
    kept_sorted = sorted(keep)
    dim = 2 ** len(kept_sorted)
    return tensor.reshape(dim, dim)
