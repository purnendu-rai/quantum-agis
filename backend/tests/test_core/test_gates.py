"""Tests for gate operations: Pauli, Hadamard, CNOT, corrections."""

import numpy as np
import pytest

from app.core.gates import apply_gate, cnot, hadamard, pauli_correction, pauli_x, pauli_y, pauli_z
from app.core.quantum_state import QuantumState

KET0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
KET1 = QuantumState(np.array([0.0, 1.0]), num_qubits=1)
KET_PLUS = QuantumState(np.array([1.0, 1.0]) / np.sqrt(2), num_qubits=1)
KET_MINUS = QuantumState(np.array([1.0, -1.0]) / np.sqrt(2), num_qubits=1)


def test_pauli_x_flips_bit():
    """X|0> = |1>."""
    assert np.isclose(pauli_x(KET0, 0).fidelity(KET1), 1.0)


def test_pauli_y_action():
    """Y|0> = i|1>, equivalent to |1> up to global phase."""
    assert np.isclose(pauli_y(KET0, 0).fidelity(KET1), 1.0)


def test_pauli_z_flips_phase():
    """Z|+> = |->."""
    assert np.isclose(pauli_z(KET_PLUS, 0).fidelity(KET_MINUS), 1.0)


def test_hadamard_creates_superposition():
    """H|0> = |+>."""
    assert np.isclose(hadamard(KET0, 0).fidelity(KET_PLUS), 1.0)


def test_hadamard_is_self_inverse():
    """H H = I."""
    assert np.isclose(hadamard(hadamard(KET0, 0), 0).fidelity(KET0), 1.0)


def test_apply_gate_preserves_normalisation():
    """Any unitary application keeps the state normalised."""
    state = QuantumState.from_bloch_vector(0.9, 1.3)
    rotated = apply_gate(state, (1 / np.sqrt(2)) * np.array([[1, -1j], [-1j, 1]]), 0)
    assert np.isclose(np.sum(np.abs(rotated.amplitudes) ** 2), 1.0)


def test_apply_gate_rejects_bad_qubit_index():
    """apply_gate raises for an out-of-range qubit."""
    with pytest.raises(ValueError):
        apply_gate(KET0, np.eye(2), 5)


def test_cnot_creates_bell_state():
    """CNOT(0->1) on H|0>|0> produces |Phi+>."""
    prepared = hadamard(QuantumState(np.array([1, 0, 0, 0]), num_qubits=2), 0)
    entangled = cnot(prepared, control=0, target=1)
    assert np.isclose(entangled.fidelity(QuantumState.from_bell_state("phi_plus")), 1.0)


def test_cnot_reversed_qubit_order():
    """CNOT with control=1, target=0 flips qubit 0 when qubit 1 is 1 (little-endian: |10> -> |11>)."""
    input_state = QuantumState(np.array([0.0, 0.0, 1.0, 0.0]), num_qubits=2)  # q1=1, q0=0
    output = cnot(input_state, control=1, target=0)
    expected = QuantumState(np.array([0.0, 0.0, 0.0, 1.0]), num_qubits=2)  # q1=1, q0=1
    assert np.isclose(output.fidelity(expected), 1.0)


def test_cnot_rejects_same_qubit():
    """CNOT raises when control equals target."""
    with pytest.raises(ValueError):
        cnot(KET0, control=0, target=0)


def test_pauli_correction_applies_x():
    """pauli_correction('X') flips |0> to |1>."""
    assert np.isclose(pauli_correction(KET0, "x").fidelity(KET1), 1.0)


def test_pauli_correction_identity_is_noop():
    """pauli_correction('I') leaves the state unchanged."""
    assert np.isclose(pauli_correction(KET_PLUS, "I").fidelity(KET_PLUS), 1.0)


def test_pauli_correction_supports_z():
    """pauli_correction('Z') acts as a phase flip."""
    assert np.isclose(pauli_correction(KET_PLUS, "Z").fidelity(KET_MINUS), 1.0)


def test_gates_do_not_mutate_input():
    """All gate functions return new states, leaving inputs untouched."""
    before = KET0.amplitudes.copy()
    pauli_x(KET0, 0)
    assert np.allclose(KET0.amplitudes, before)
