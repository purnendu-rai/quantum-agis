"""Quantum gate operations on ``QuantumState`` objects (pure NumPy).

Gates are embedded into the full register with Kronecker products; CNOT is
built as a basis-index permutation so control/target can sit at any positions.
All functions return new states and never mutate their inputs.
"""

from __future__ import annotations

import numpy as np

from app.core.constants import (
    CNOT,
    HADAMARD,
    IDENTITY,
    PAULI_X,
    PAULI_Y,
    PAULI_Z,
    PHASE_S_DAGGER,
)
from app.core.quantum_state import QuantumState

_CORRECTIONS: dict[str, np.ndarray] = {
    "I": IDENTITY,
    "X": PAULI_X,
    "Y": PAULI_Y,
    "Z": PAULI_Z,
}


def _apply_operator(state: QuantumState, operator: np.ndarray) -> QuantumState:
    """Apply a full-register unitary to a state, preserving purity.

    Args:
        state: Input state.
        operator: Unitary of dimension 2**num_qubits.

    Returns:
        New QuantumState after the unitary.
    """
    if state._rho is not None:
        rho = operator @ state.density_matrix() @ operator.conj().T
        return QuantumState._from_density(rho, state.num_qubits)
    amps = operator @ state.amplitudes
    return QuantumState(amps, state.num_qubits)


def _embed_1q(gate: np.ndarray, target_qubit: int, num_qubits: int) -> np.ndarray:
    """Embed a single-qubit gate into the full register (little-endian).

    Qubit 0 is the least-significant bit of the basis index, so it occupies
    the LAST Kronecker factor.

    Args:
        gate: 2x2 unitary.
        target_qubit: Qubit the gate acts on (0-based, little-endian).
        num_qubits: Total register size.

    Returns:
        Full 2**n x 2**n operator.
    """
    left = np.eye(2 ** (num_qubits - target_qubit - 1), dtype=complex)
    right = np.eye(2**target_qubit, dtype=complex)
    return np.kron(np.kron(left, gate), right)


def apply_gate(state: QuantumState, gate: np.ndarray, target_qubit: int) -> QuantumState:
    """Apply an arbitrary 2x2 unitary gate to one qubit.

    Args:
        state: Input state.
        gate: 2x2 unitary matrix.
        target_qubit: Qubit index the gate acts on.

    Returns:
        New QuantumState after the gate.

    Raises:
        ValueError: If the qubit index is out of range.
    """
    if not 0 <= target_qubit < state.num_qubits:
        raise ValueError(f"Qubit index {target_qubit} out of range for {state.num_qubits} qubits.")
    return _apply_operator(state, _embed_1q(gate, target_qubit, state.num_qubits))


def pauli_x(state: QuantumState, qubit: int) -> QuantumState:
    """Apply the Pauli-X (bit-flip) gate.

    Args:
        state: Input state.
        qubit: Target qubit index.

    Returns:
        New QuantumState.
    """
    return apply_gate(state, PAULI_X, qubit)


def pauli_y(state: QuantumState, qubit: int) -> QuantumState:
    """Apply the Pauli-Y gate.

    Args:
        state: Input state.
        qubit: Target qubit index.

    Returns:
        New QuantumState.
    """
    return apply_gate(state, PAULI_Y, qubit)


def pauli_z(state: QuantumState, qubit: int) -> QuantumState:
    """Apply the Pauli-Z (phase-flip) gate.

    Args:
        state: Input state.
        qubit: Target qubit index.

    Returns:
        New QuantumState.
    """
    return apply_gate(state, PAULI_Z, qubit)


def hadamard(state: QuantumState, qubit: int) -> QuantumState:
    """Apply the Hadamard gate (Z-basis <-> X-basis rotation).

    Args:
        state: Input state.
        qubit: Target qubit index.

    Returns:
        New QuantumState.
    """
    return apply_gate(state, HADAMARD, qubit)


def _cnot_operator(control: int, target: int, num_qubits: int) -> np.ndarray:
    """Build the full CNOT unitary for arbitrary control/target positions.

    Implemented as the basis permutation |c, t> -> |c, t XOR c>.

    Args:
        control: Control qubit index.
        target: Target qubit index.
        num_qubits: Total register size.

    Returns:
        Full 2**n x 2**n permutation unitary.

    Raises:
        ValueError: If control == target or an index is out of range.
    """
    if control == target:
        raise ValueError("CNOT control and target must differ.")
    for q in (control, target):
        if not 0 <= q < num_qubits:
            raise ValueError(f"Qubit index {q} out of range for {num_qubits} qubits.")
    dim = 2**num_qubits
    indices = np.arange(dim)
    control_bit = (indices >> control) & 1
    destination = indices ^ (control_bit << target)
    unitary = np.zeros((dim, dim), dtype=complex)
    unitary[destination, indices] = 1.0
    return unitary


def cnot(state: QuantumState, control: int, target: int) -> QuantumState:
    """Apply a CNOT with arbitrary control/target positions.

    Args:
        state: Input state.
        control: Control qubit index.
        target: Target qubit index.

    Returns:
        New (generally entangled) QuantumState.
    """
    return _apply_operator(state, _cnot_operator(control, target, state.num_qubits))


def pauli_correction(state: QuantumState, correction: str, qubit: int = 0) -> QuantumState:
    """Apply a classical-feedforward Pauli correction (used by teleportation).

    Args:
        state: Input state.
        correction: One of ``"I"``, ``"X"``, ``"Y"``, ``"Z"`` (case-insensitive).
        qubit: Qubit to correct (default 0).

    Returns:
        Corrected QuantumState.

    Raises:
        KeyError: For an unsupported correction label.
    """
    gate = _CORRECTIONS[correction.upper()]
    return apply_gate(state, gate, qubit)


# Re-exported so teleportation/measurements can reuse the S-dagger rotation.
S_DAGGER = PHASE_S_DAGGER
