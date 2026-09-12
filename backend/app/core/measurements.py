"""Measurement operators and statistics (pure NumPy/SciPy).

Provides projective single-qubit measurements in the X/Y/Z bases, Pauli
expectation values, Bell-basis measurement, and the CHSH inequality test used
to certify genuine quantum behaviour on the AGIS channel.
"""

from __future__ import annotations

import numpy as np

from app.core.constants import (
    BELL_STATES,
    HADAMARD,
    IDENTITY,
    PAULI_X,
    PAULI_Y,
    PAULI_Z,
    PHASE_S_DAGGER,
)
from app.core.gates import _embed_1q, apply_gate
from app.core.quantum_state import QuantumState, RNG, _kron_all

_PAULI_MAP: dict[str, np.ndarray] = {"X": PAULI_X, "Y": PAULI_Y, "Z": PAULI_Z}
_BASIS_ALIASES: dict[str, str] = {
    "computational": "Z",
    "z": "Z",
    "x": "X",
    "hadamard": "X",
    "y": "Y",
}
_BELL_NAMES: tuple[str, ...] = ("phi_plus", "phi_minus", "psi_plus", "psi_minus")


def _outcome_probabilities(rho: np.ndarray, projector: np.ndarray) -> float:
    """Return the probability Tr(rho P) for a projector P, clipped to [0, 1].

    Args:
        rho: Density matrix.
        projector: Projection operator.

    Returns:
        Probability in [0, 1].
    """
    return float(np.clip(np.real(np.trace(rho @ projector)), 0.0, 1.0))


def _rotate_to_z(state: QuantumState, basis: str, qubit: int) -> QuantumState:
    """Rotate a state so that measuring ``basis`` is equivalent to measuring Z.

    Args:
        state: Input state.
        basis: Normalised basis label (``X``, ``Y`` or ``Z``).
        qubit: Qubit to rotate.

    Returns:
        Rotated copy of the state (Z |-> Z, X -> Z via H, Y -> Z via H Sdg).
    """
    if basis == "Z":
        return state
    if basis == "X":
        return apply_gate(state, HADAMARD, qubit)
    # Y -> Z: apply (H Sdg) to the qubit, since (H Sdg) Y (S H) = Z.
    return apply_gate(apply_gate(state, PHASE_S_DAGGER, qubit), HADAMARD, qubit)


def projective_measure(state: QuantumState, basis: str, qubit: int) -> tuple[int, float]:
    """Measure one qubit in the given Pauli basis and sample an outcome.

    The input state is not collapsed; the returned probability is the exact
    Born probability of the sampled outcome.

    Args:
        state: Input state.
        basis: ``"Z"``/``"computational"``, ``"X"``/``"hadamard"`` or ``"Y"``.
        qubit: Qubit to measure.

    Returns:
        Tuple of (outcome 0 or 1, its probability).

    Raises:
        KeyError: For an unknown basis label.
    """
    label = _BASIS_ALIASES[basis.lower()]
    rotated = _rotate_to_z(state, label, qubit)
    rho = rotated.density_matrix()
    p0 = _outcome_probabilities(rho, _embed_1q(np.array([[1, 0], [0, 0]], dtype=complex), qubit, state.num_qubits))
    outcome = int(RNG.random() < 1.0 - p0)  # 0 with prob p0, 1 with prob 1-p0
    probability = p0 if outcome == 0 else 1.0 - p0
    return outcome, float(probability)


def measure_pauli_expectation(state: QuantumState, pauli: str, qubit: int) -> float:
    """Return the expectation value <P_qubit> of a single-qubit Pauli operator.

    Args:
        state: Input state.
        pauli: ``"X"``, ``"Y"`` or ``"Z"``.
        qubit: Qubit the operator acts on.

    Returns:
        Expectation value in [-1, 1].

    Raises:
        KeyError: For an unsupported Pauli label.
    """
    operator = _embed_1q(_PAULI_MAP[pauli.upper()], qubit, state.num_qubits)
    return float(np.clip(np.real(np.trace(state.density_matrix() @ operator)), -1.0, 1.0))


def bell_measurement(state: QuantumState) -> tuple[str, float]:
    """Project a two-qubit state onto the Bell basis and sample an outcome.

    Args:
        state: Two-qubit input state.

    Returns:
        Tuple of (Bell state name, its Born probability).

    Raises:
        ValueError: If the state is not a two-qubit register.
    """
    if state.num_qubits != 2:
        raise ValueError("Bell measurement requires exactly two qubits.")
    rho = state.density_matrix()
    probabilities = {
        name: _outcome_probabilities(rho, np.outer(vec, vec.conj()))
        for name, vec in BELL_STATES.items()
    }
    names = list(probabilities.keys())
    probs = np.array([probabilities[n] for n in names], dtype=float)
    probs = probs / probs.sum()  # guard against rounding drift
    sampled = names[int(RNG.choice(len(names), p=probs))]
    return sampled, float(probabilities[sampled])


def chsh_inequality_test(state: QuantumState) -> float:
    """Compute the CHSH parameter S = |E(a0,b0) + E(a0,b1) + E(a1,b0) - E(a1,b1)|.

    Uses the standard maximal-violation angles in the X-Z plane:
    a0 = 0, a1 = pi/2, b0 = pi/4, b1 = -pi/4, with each analyser direction
    n(theta) = cos(theta) Z + sin(theta) X. A Bell state yields S = 2*sqrt(2);
    classical states are bounded by S <= 2.

    Args:
        state: Two-qubit input state.

    Returns:
        CHSH parameter S in [0, 2*sqrt(2)].

    Raises:
        ValueError: If the state is not a two-qubit register.
    """
    if state.num_qubits != 2:
        raise ValueError("CHSH test requires exactly two qubits.")
    rho = state.density_matrix()

    def _correlation(theta_a: float, theta_b: float) -> float:
        """Return E(a, b) for analyser angles in the X-Z plane.

        Args:
            theta_a: Analyser angle for qubit 0.
            theta_b: Analyser angle for qubit 1.

        Returns:
            Correlation coefficient in [-1, 1].
        """

        def _direction(theta: float) -> np.ndarray:
            """Return the 2x2 observable cos(theta) Z + sin(theta) X.

            Args:
                theta: Angle in radians.

            Returns:
                2x2 Hermitian observable matrix.
            """
            return np.cos(theta) * PAULI_Z + np.sin(theta) * PAULI_X

        # Little-endian register: qubit 0 occupies the LAST Kronecker factor.
        observable = np.kron(_direction(theta_b), _direction(theta_a))
        return float(np.clip(np.real(np.trace(rho @ observable)), -1.0, 1.0))

    a0, a1, b0, b1 = 0.0, np.pi / 2, np.pi / 4, -np.pi / 4
    s_value = (
        _correlation(a0, b0)
        + _correlation(a0, b1)
        + _correlation(a1, b0)
        - _correlation(a1, b1)
    )
    return float(abs(s_value))


def _identity_operator(num_qubits: int) -> np.ndarray:
    """Return the identity operator over an N-qubit register.

    Args:
        num_qubits: Register size.

    Returns:
        2**n x 2**n identity matrix.
    """
    return _kron_all([IDENTITY] * num_qubits)
