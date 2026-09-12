"""Quantum teleportation protocol (pure NumPy, deterministic).

Implements the standard teleportation circuit: a shared Bell pair, CNOT +
Hadamard on the message register, joint measurement of the message and Alice's
half, and Pauli feed-forward corrections on Bob's qubit. Bob's state is
conditioned on the sampled measurement outcomes, so after the classical
corrections it reproduces the message state exactly (fidelity 1.0); outcome
sampling uses the module's seeded RNG, making full runs reproducible.
"""

from __future__ import annotations

import numpy as np

from app.core.constants import (
    BELL_PHI_PLUS,
    HADAMARD,
    HOM_VISIBILITY_MIN,
    IDENTITY,
    PAULI_X,
    PAULI_Z,
)
from app.core.gates import _cnot_operator
from app.core.quantum_state import QuantumState, RNG, _kron_all, _partial_trace_matrix


class TeleportationProtocol:
    """Ideal three-qubit teleportation of a message qubit through a Bell pair.

    Register layout: qubit 0 = message, qubit 1 = Alice's pair half,
    qubit 2 = Bob's pair half.
    """

    def __init__(self) -> None:
        """Initialise the protocol with no shared pair created yet."""
        self._pair_state: QuantumState | None = None

    def create_bell_pair(self) -> tuple[QuantumState, QuantumState]:
        """Create the entangled |Phi+> resource shared by Alice and Bob.

        The returned objects are the single-qubit *marginals* of the joint
        pair (each the maximally mixed state I/2, as quantum mechanics
        requires). The pure two-qubit joint state is cached internally and
        used by :meth:`teleport`.

        Returns:
            Tuple of (alice_marginal, bob_marginal), each a one-qubit mixed state.
        """
        self._pair_state = QuantumState(BELL_PHI_PLUS, num_qubits=2)
        rho = self._pair_state.density_matrix()
        alice = QuantumState._from_density(_partial_trace_matrix(rho, keep=[0], n=2), 1)
        bob = QuantumState._from_density(_partial_trace_matrix(rho, keep=[1], n=2), 1)
        return alice, bob

    def teleport(self, message_state: QuantumState, alice_qubit: QuantumState, bob_qubit: QuantumState) -> dict:
        """Teleport ``message_state`` from Alice to Bob and report the run.

        Args:
            message_state: Arbitrary single-qubit state to transmit.
            alice_qubit: Alice's pair half (validated as a single qubit).
            bob_qubit: Bob's pair half (validated as a single qubit).

        Returns:
            Dict with keys:
                - ``"classical_bits"``: sampled (m1, m2) measurement outcomes.
                - ``"corrections"``: Pauli corrections applied to Bob's qubit.
                - ``"teleported_state"``: Bob's post-protocol state.
                - ``"fidelity"``: fidelity of the teleported vs original state.

        Raises:
            ValueError: If any operand is not a single-qubit state or no pair exists.
        """
        if message_state.num_qubits != 1 or alice_qubit.num_qubits != 1 or bob_qubit.num_qubits != 1:
            raise ValueError("Teleportation operates on single-qubit states only.")
        if self._pair_state is None:
            raise ValueError("No Bell pair created; call create_bell_pair() first.")

        # Full 3-qubit register, little-endian: qubit 0 = message (LAST
        # Kronecker factor), qubit 1 = Bob's half, qubit 2 = Alice's half.
        register_amps = np.kron(self._pair_state.amplitudes, message_state.amplitudes)
        register_rho = np.outer(register_amps, register_amps.conj())

        # Step 1: CNOT with message as control, Alice's half as target.
        u_cnot = _cnot_operator(control=0, target=2, num_qubits=3)
        # Step 2: Hadamard on the message qubit (qubit 0 = last factor).
        u_hadamard = _kron_all([IDENTITY, IDENTITY, HADAMARD])
        register_rho = u_hadamard @ (u_cnot @ register_rho @ u_cnot.conj().T) @ u_hadamard.conj().T

        # Step 3: joint measurement distribution over (message m1, alice m2).
        diag = np.real(np.diag(register_rho))
        # Flat diagonal index = m1 + 2*bob + 4*m2, so C-order reshape axes
        # are [m2, bob, m1]; summing out Bob leaves axes [m2, m1].
        joint_probs = diag.reshape(2, 2, 2).sum(axis=1)
        flat = joint_probs.ravel() / joint_probs.sum()   # flat index = 2*m2 + m1
        sample = int(RNG.choice(4, p=flat))
        m1, m2 = sample % 2, sample // 2

        # Step 4: condition on the measured outcomes. The projector pins
        # qubits 0 (m1) and 2 (m2); the surviving 2-dim subspace IS Bob.
        # Basis indices with q0=m1, q2=m2 and bob bit free: {m1+4*m2, m1+4*m2+2}.
        basis_indices = [m1 + 4 * m2, m1 + 4 * m2 + 2]
        sub_block = register_rho[np.ix_(basis_indices, basis_indices)]
        probability = float(np.real(np.trace(sub_block)))
        bob_rho = sub_block / probability

        # Step 5: classical feed-forward — Bob's conditional state is
        # X^{m2} Z^{m1} |psi><psi| Z^{m1} X^{m2}; applying the matching
        # Pauli correction recovers |psi> exactly (global phases cancel in rho).
        if m1:
            bob_rho = PAULI_Z @ bob_rho @ PAULI_Z
        if m2:
            bob_rho = PAULI_X @ bob_rho @ PAULI_X
        teleported = QuantumState._from_density(bob_rho, 1)

        corrections = ([] + (["Z"] if m1 else []) + (["X"] if m2 else []))
        return {
            "classical_bits": (m1, m2),
            "corrections": corrections,
            "teleported_state": teleported,
            "fidelity": message_state.fidelity(teleported),
        }

    def verify_teleportation(self, original: QuantumState, teleported: QuantumState) -> bool:
        """Check whether a teleported state faithfully reproduces the original.

        Args:
            original: The message state that entered the protocol.
            teleported: The state recovered on Bob's side.

        Returns:
            True when the fidelity meets the HOM_VISIBILITY_MIN threshold.
        """
        return original.fidelity(teleported) >= HOM_VISIBILITY_MIN
