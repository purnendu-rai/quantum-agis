"""Tests for the teleportation protocol and measurement statistics."""

import numpy as np
import pytest

from app.core.measurements import (
    bell_measurement,
    chsh_inequality_test,
    measure_pauli_expectation,
    projective_measure,
)
from app.core.quantum_state import QuantumState
from app.core.teleportation import TeleportationProtocol


# --------------------------------------------------------------------- #
#  Teleportation
# --------------------------------------------------------------------- #
def test_bell_pair_marginals_are_maximally_mixed():
    """create_bell_pair returns I/2 marginals of the entangled resource."""
    protocol = TeleportationProtocol()
    alice, bob = protocol.create_bell_pair()
    assert np.allclose(alice.density_matrix(), 0.5 * np.eye(2))
    assert np.allclose(bob.density_matrix(), 0.5 * np.eye(2))


def test_teleportation_preserves_bloch_states():
    """Ideal teleportation reproduces arbitrary message states exactly."""
    protocol = TeleportationProtocol()
    alice, bob = protocol.create_bell_pair()
    for theta in (0.0, np.pi / 4, np.pi / 2, np.pi):
        for phi in (0.0, np.pi / 2, np.pi):
            message = QuantumState.from_bloch_vector(theta, phi)
            result = protocol.teleport(message, alice, bob)
            assert result["fidelity"] > 0.999999


def test_teleportation_returns_required_keys():
    """teleport() returns classical bits, corrections, state and fidelity."""
    protocol = TeleportationProtocol()
    alice, bob = protocol.create_bell_pair()
    result = protocol.teleport(QuantumState.from_bloch_vector(np.pi / 3, 0.4), alice, bob)
    assert set(result.keys()) == {"classical_bits", "corrections", "teleported_state", "fidelity"}
    m1, m2 = result["classical_bits"]
    assert m1 in (0, 1) and m2 in (0, 1)
    expected = (["Z"] if m1 else []) + (["X"] if m2 else [])
    assert result["corrections"] == expected


def test_teleportation_requires_bell_pair():
    """teleport() raises when no pair was created."""
    protocol = TeleportationProtocol()
    message = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    ghost = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    with pytest.raises(ValueError):
        protocol.teleport(message, ghost, ghost)


def test_teleportation_rejects_multi_qubit_message():
    """teleport() raises for a two-qubit message."""
    protocol = TeleportationProtocol()
    alice, bob = protocol.create_bell_pair()
    with pytest.raises(ValueError):
        protocol.teleport(QuantumState.from_bell_state("phi_plus"), alice, bob)


def test_verify_teleportation_accepts_good_fidelity():
    """verify_teleportation passes when fidelity meets the threshold."""
    protocol = TeleportationProtocol()
    alice, bob = protocol.create_bell_pair()
    original = QuantumState.from_bloch_vector(1.1, 0.3)
    result = protocol.teleport(original, alice, bob)
    assert protocol.verify_teleportation(original, result["teleported_state"]) is True


def test_verify_teleportation_rejects_wrong_state():
    """verify_teleportation fails for a clearly different state."""
    protocol = TeleportationProtocol()
    ket0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    ket_plus = QuantumState(np.array([1.0, 1.0]) / np.sqrt(2), num_qubits=1)
    # fidelity(|0>, |+>) = 0.5 < HOM_VISIBILITY_MIN
    assert protocol.verify_teleportation(ket0, ket_plus) is False


# --------------------------------------------------------------------- #
#  Measurements
# --------------------------------------------------------------------- #
def test_projective_measure_z_on_eigenstate():
    """Z-basis measurement of |1> yields outcome 1 with probability 1."""
    ket1 = QuantumState(np.array([0.0, 1.0]), num_qubits=1)
    outcome, probability = projective_measure(ket1, "Z", 0)
    assert outcome == 1
    assert np.isclose(probability, 1.0)


def test_projective_measure_x_basis_alias():
    """'hadamard' is accepted as an alias for the X basis."""
    ket_plus = QuantumState(np.array([1.0, 1.0]) / np.sqrt(2), num_qubits=1)
    outcome, probability = projective_measure(ket_plus, "hadamard", 0)
    assert outcome == 0
    assert np.isclose(probability, 1.0)


def test_pauli_expectation_eigenstates():
    """<Z> = 1 for |0>, -1 for |1>; <X> = 1 for |+>."""
    ket0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    ket1 = QuantumState(np.array([0.0, 1.0]), num_qubits=1)
    ket_plus = QuantumState(np.array([1.0, 1.0]) / np.sqrt(2), num_qubits=1)
    assert np.isclose(measure_pauli_expectation(ket0, "Z", 0), 1.0)
    assert np.isclose(measure_pauli_expectation(ket1, "Z", 0), -1.0)
    assert np.isclose(measure_pauli_expectation(ket_plus, "X", 0), 1.0)


def test_pauli_expectation_bell_marginal_vanishes():
    """<Z> on the I/2 marginal of a Bell pair is 0."""
    pair = QuantumState.from_bell_state("phi_plus")
    marginal = pair.partial_trace(1)
    assert np.isclose(measure_pauli_expectation(marginal, "Z", 0), 0.0)


def test_bell_measurement_bell_state_is_deterministic():
    """Bell measurement of |Phi+> always reports phi_plus with p=1."""
    outcome, probability = bell_measurement(QuantumState.from_bell_state("phi_plus"))
    assert outcome == "phi_plus"
    assert np.isclose(probability, 1.0)


def test_bell_measurement_probabilities_sum_to_one():
    """The four Bell-projector probabilities sum to 1 for any two-qubit state."""
    from app.core.constants import BELL_STATES

    state = QuantumState.from_bloch_vector(0.3, 1.2).tensor_product(
        QuantumState.from_bloch_vector(2.0, 0.1)
    )
    rho = state.density_matrix()
    total = sum(
        np.real(np.trace(rho @ np.outer(vec, vec.conj()))) for vec in BELL_STATES.values()
    )
    assert np.isclose(total, 1.0)


def test_bell_measurement_rejects_single_qubit():
    """bell_measurement raises for a one-qubit register."""
    with pytest.raises(ValueError):
        bell_measurement(QuantumState(np.array([1.0, 0.0]), num_qubits=1))


def test_chsh_bell_state_violation():
    """|Phi+> achieves the Tsirelson bound S = 2*sqrt(2)."""
    s_value = chsh_inequality_test(QuantumState.from_bell_state("phi_plus"))
    assert np.isclose(s_value, 2 * np.sqrt(2), atol=1e-6)


def test_chsh_product_state_is_classical():
    """Product states respect the classical bound S <= 2."""
    state = QuantumState.from_bloch_vector(0.0, 0.0).tensor_product(
        QuantumState.from_bloch_vector(0.0, 0.0)
    )
    assert chsh_inequality_test(state) <= 2.0 + 1e-9


def test_chsh_rejects_single_qubit():
    """chsh_inequality_test raises for a one-qubit register."""
    with pytest.raises(ValueError):
        chsh_inequality_test(QuantumState(np.array([1.0, 0.0]), num_qubits=1))
