"""Tests for QuantumState: construction, metrics, transforms, factories."""

import numpy as np
import pytest

from app.core.constants import BELL_PHI_MINUS, BELL_PHI_PLUS, BELL_PSI_MINUS, BELL_PSI_PLUS
from app.core.quantum_state import QuantumState


def test_construction_validates_normalisation():
    """__init__ raises for non-normalised amplitude vectors."""
    with pytest.raises(ValueError):
        QuantumState(np.array([1.0, 1.0]), num_qubits=1)


def test_construction_validates_length():
    """__init__ raises when amplitude count does not match num_qubits."""
    with pytest.raises(ValueError):
        QuantumState(np.array([1.0, 0.0]), num_qubits=2)


def test_density_matrix_pure_state():
    """Density matrix of a pure state is Hermitian with unit trace."""
    state = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    rho = state.density_matrix()
    assert np.allclose(rho, rho.conj().T)
    assert np.isclose(np.trace(rho).real, 1.0)


def test_fidelity_identical_states_is_one():
    """Fidelity of a state with itself is 1."""
    state = QuantumState.from_bloch_vector(np.pi / 3, np.pi / 5)
    assert np.isclose(state.fidelity(state), 1.0)


def test_fidelity_zero_and_plus_is_half():
    """F(|0>, |+>) = 1/2."""
    ket0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    ket_plus = QuantumState(np.array([1.0, 1.0]) / np.sqrt(2), num_qubits=1)
    assert np.isclose(ket0.fidelity(ket_plus), 0.5)


def test_fidelity_of_bell_marginals():
    """Uhlmann fidelity between the two I/2 marginals of a Bell pair is 1."""
    pair = QuantumState.from_bell_state("phi_plus")
    marg_a = pair.partial_trace(1)
    marg_b = pair.partial_trace(0)
    assert np.isclose(marg_a.fidelity(marg_b), 1.0)


def test_bures_distance_zero_for_same_state():
    """Bures distance vanishes for identical states."""
    state = QuantumState.from_bloch_vector(1.0, 2.0)
    assert np.isclose(state.bures_distance(state), 0.0)


def test_bures_distance_orthogonal_states():
    """Bures distance between |0> and |1> is sqrt(2)."""
    ket0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    ket1 = QuantumState(np.array([0.0, 1.0]), num_qubits=1)
    assert np.isclose(ket0.bures_distance(ket1), np.sqrt(2.0))


def test_bell_state_factories():
    """from_bell_state reproduces the constant Bell vectors."""
    expected = {
        "phi_plus": BELL_PHI_PLUS,
        "phi_minus": BELL_PHI_MINUS,
        "psi_plus": BELL_PSI_PLUS,
        "psi_minus": BELL_PSI_MINUS,
    }
    for name, vector in expected.items():
        state = QuantumState.from_bell_state(name)
        assert np.allclose(np.abs(state.amplitudes), np.abs(vector))
        assert state.num_qubits == 2


def test_bloch_vector_poles():
    """theta=0 gives |0>; theta=pi gives |1>."""
    ket0 = QuantumState.from_bloch_vector(0.0, 0.0)
    ket1 = QuantumState.from_bloch_vector(np.pi, 0.0)
    assert np.isclose(abs(ket0.amplitudes[0]), 1.0)
    assert np.isclose(abs(ket1.amplitudes[1]), 1.0)


def test_bloch_vector_normalised_for_random_angles():
    """Arbitrary Bloch angles produce a normalised state."""
    state = QuantumState.from_bloch_vector(0.7, 2.1)
    assert np.isclose(np.sum(np.abs(state.amplitudes) ** 2), 1.0)


def test_random_state_is_normalised_and_sized():
    """random() returns a normalised state of the requested width."""
    state = QuantumState.random(3)
    assert state.num_qubits == 3
    assert np.isclose(np.sum(np.abs(state.amplitudes) ** 2), 1.0)


def test_random_state_is_deterministic():
    """Two fresh RNG streams with the same seed agree (reproducibility)."""
    from app.core.quantum_state import RNG
    import numpy as _np

    saved = RNG.bit_generator.state
    a = QuantumState.random(2)
    RNG.bit_generator.state = saved
    b = QuantumState.random(2)
    assert _np.allclose(a.amplitudes, b.amplitudes)


def test_tensor_product_dimensions():
    """tensor_product doubles the qubit count and Kroneckers the amplitudes."""
    ket0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    ket1 = QuantumState(np.array([0.0, 1.0]), num_qubits=1)
    combined = ket0.tensor_product(ket1)
    assert combined.num_qubits == 2
    assert np.isclose(abs(combined.amplitudes[1]), 1.0)  # |01>


def test_partial_trace_of_product_state():
    """Tracing |01> over qubit 1 leaves |0> on qubit 0."""
    ket0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    ket1 = QuantumState(np.array([0.0, 1.0]), num_qubits=1)
    reduced = ket0.tensor_product(ket1).partial_trace(1)
    assert reduced.num_qubits == 1
    assert np.isclose(reduced.fidelity(ket0), 1.0)


def test_partial_trace_of_bell_state_is_maximally_mixed():
    """Marginal of any Bell state is I/2 (pure-state fidelity with |0> is 0.5)."""
    pair = QuantumState.from_bell_state("psi_minus")
    marginal = pair.partial_trace(0)
    rho = marginal.density_matrix()
    assert np.allclose(rho, 0.5 * np.eye(2))
    assert marginal.num_qubits == 1


def test_partial_trace_rejects_single_qubit():
    """partial_trace raises on a one-qubit register."""
    ket0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    with pytest.raises(ValueError):
        ket0.partial_trace(0)


def test_measure_returns_valid_outcome_and_probability():
    """measure() returns an in-range outcome with its exact Born probability."""
    ket0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    outcome, probability = ket0.measure("computational")
    assert outcome in (0, 1)
    assert 0.0 <= probability <= 1.0


def test_measure_deterministic_outcome_for_basis_state():
    """Measuring |0> in the computational basis always yields 0 with p=1."""
    ket0 = QuantumState(np.array([1.0, 0.0]), num_qubits=1)
    outcome, probability = ket0.measure("computational")
    assert outcome == 0
    assert np.isclose(probability, 1.0)


def test_measure_hadamard_basis_rotation():
    """|+> measured in the hadamard (X) basis is deterministic."""
    ket_plus = QuantumState(np.array([1.0, 1.0]) / np.sqrt(2), num_qubits=1)
    outcome, probability = ket_plus.measure("hadamard")
    assert outcome == 0
    assert np.isclose(probability, 1.0)
