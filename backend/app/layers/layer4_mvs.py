"""Layer 4 — MVS (MDI-QDS Verification Shield).

Measurement-device-independent quantum digital signature verification. A
signature is a collection of measurement events; each event holds the basis
the untrusted node reported, the raw outcome, and the Pauli correction that
the two-party Bell measurement dictates. The verifier applies the Pauli
feed-forward (either unitarily on the recovered state or as a bit flip on the
reported outcome), sifts to the events whose basis matches the public key,
and scores the corrected-bit agreement. Genuine signers saturate the match
rate; forgeries land near the random-guessing floor of 50%.

The enrolled public key and the genuine signature generator are deterministic
class-level constants/seeds, so the layer is stateless.
"""

from __future__ import annotations

from typing import Any
from zlib import crc32

import numpy as np

from app.core.constants import W_MVS
from app.core.gates import pauli_correction
from app.core.measurements import projective_measure
from app.core.quantum_state import QuantumState
from app.layers.base_layer import (
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SUSPICIOUS,
    BaseLayer,
    seeded_rng,
)

#: Measurement bases used for MDI-QDS sifting (Pauli eigenbases).
MVS_BASES: tuple[str, ...] = ("Z", "X", "Y")
#: Pauli corrections a middle node can report after the Bell measurement.
MVS_CORRECTIONS: tuple[str, ...] = ("I", "Z", "X", "Y")
#: Corrections that flip the reported bit (X/Y flip; I/Z only phase-shift).
MVS_BIT_FLIP_CORRECTIONS: frozenset[str] = frozenset({"X", "Y"})
#: Number of measurement events per signature. Kept high enough that the
#: random-guessing match floor (~0.50) is statistically well separated from
#: genuine agreement after sifting (roughly one third of the events survive).
MVS_SIGNATURE_LENGTH: int = 512
#: Match rate needed to accept a signature as genuine.
MVS_MATCH_THRESHOLD: float = 0.95
#: Match rate at or below which the signature is treated as a forgery.
MVS_FORGERY_MAX: float = 0.62
#: Fraction of outcomes corrupted when ``tampered=True`` is requested.
MVS_TAMPER_FRACTION: float = 0.25
#: Identity of the enrolled public key.
DEFAULT_KEY_DEVICE_ID: str = "AGIS-PUBKEY-001"


def _assemble_public_key(length: int, device_id: str, rng: np.random.Generator) -> dict:
    """Build a public key from an RNG: bases and expected bits per position.

    Args:
        length: Number of key positions.
        device_id: Owner identity string.
        rng: Seeded random generator (deterministic policy).

    Returns:
        Public key dict with ``bases``, ``expected``, ``device_id``, ``length``.
    """
    bases = [MVS_BASES[int(rng.integers(0, len(MVS_BASES)))] for _ in range(length)]
    expected = [int(bit) for bit in rng.integers(0, 2, size=length)]
    return {
        "bases": bases,
        "expected": expected,
        "device_id": device_id,
        "length": length,
    }


def _public_key(seed_label: bytes, length: int, device_id: str) -> dict:
    """Deterministically generate a public key from a seed label.

    Args:
        seed_label: Bytes label individualising the stream (e.g. b"mvs-genesis").
        length: Number of key positions.
        device_id: Owner identity string.

    Returns:
        Public key dict.
    """
    rng = seeded_rng(crc32(seed_label), crc32(device_id.encode("utf-8")))
    return _assemble_public_key(int(length), str(device_id), rng)


class MVSLayer(BaseLayer):
    """Scans signatures across bases and scores MDI-QDS agreement."""

    #: Enrolled (public) key of the legitimate signer — a deterministic
    #: class-level constant, never stored per instance or read from disk.
    BASELINE_PUBLIC_KEY: dict = _public_key(
        b"mvs-genesis", MVS_SIGNATURE_LENGTH, DEFAULT_KEY_DEVICE_ID
    )

    def __init__(self) -> None:
        """Initialise the MVS layer identity and fusion weight."""
        super().__init__(layer_id=4, layer_name="MVS", weight=W_MVS)

    # ------------------------------------------------------------------ #
    #  Key and signature construction
    # ------------------------------------------------------------------ #
    @staticmethod
    def make_public_key(
        length: int = MVS_SIGNATURE_LENGTH,
        device_id: str = DEFAULT_KEY_DEVICE_ID,
        seed_label: bytes = b"mvs-key",
    ) -> dict:
        """Generate a deterministic public key.

        Args:
            length: Number of key positions.
            device_id: Owner identity string.
            seed_label: Bytes label for the seeded stream.

        Returns:
            Public key dict with ``bases``, ``expected``, ``device_id``,
            ``length``.
        """
        return _public_key(seed_label, int(length), str(device_id))

    @classmethod
    def generate_signature(
        cls,
        public_key: dict,
        *,
        seed_label: bytes = b"mvs-sign",
        forgery: bool = False,
        tamper_fraction: float = 0.0,
        include_states: bool = False,
    ) -> dict:
        """Produce a measurement-event signature against ``public_key``.

        Genuine events encode the public-key bit in the corrected outcome so
        the match rate saturates; forged events report random outcomes; a
        tampering fraction flips a requested share of corrections.

        Args:
            public_key: Key dict produced by :meth:`make_public_key`.
            seed_label: Bytes label for the deterministic signature stream.
            forgery: When True, outcomes are random guesses (unrelated signer).
            tamper_fraction: Share of events whose corrected bit is flipped.
            include_states: When True, every event also carries the raw
                post-correction single-qubit amplitudes, so :meth:`mdi_verify`
                re-derives the outcome through the quantum state path.

        Returns:
            Signature dict with ``events``, ``device_id`` and ``length``.
        """
        key = cls._normalise_key(public_key)
        length = key["length"]
        rng = seeded_rng(crc32(seed_label))
        events = []
        for index in range(length):
            basis = MVS_BASES[int(rng.integers(0, len(MVS_BASES)))]
            correction = MVS_CORRECTIONS[int(rng.integers(0, len(MVS_CORRECTIONS)))]
            flip = 1 if correction in MVS_BIT_FLIP_CORRECTIONS else 0
            expected = key["expected"][index]
            if forgery:
                outcome = int(rng.integers(0, 2))
            elif rng.random() < tamper_fraction:
                outcome = 1 - (expected ^ flip)
            else:
                outcome = expected ^ flip
            event: dict[str, Any] = {
                "basis": basis,
                "outcome": outcome,
                "correction": correction,
            }
            if include_states:
                canonical = QuantumState(
                    cls._canonical_amplitude(expected, basis), num_qubits=1
                )
                raw = cls.apply_pauli_correction(canonical, correction)
                event["state"] = raw.amplitudes.tolist()
            events.append(event)
        return {"events": events, "device_id": key["device_id"], "length": length}

    @staticmethod
    def _canonical_amplitude(bit: int, basis: str) -> list[float | complex]:
        """Return the +1/-1 eigenstate of ``basis`` for the given bit.

        Args:
            bit: Expected canonical measurement bit (0 -> +1 eigenstate).
            basis: One of ``Z``, ``X``, ``Y``.

        Returns:
            Two complex amplitudes of the corresponding eigenstate.
        """
        half = 1.0 / np.sqrt(2.0)
        if basis == "Z":
            return [1.0, 0.0] if bit == 0 else [0.0, 1.0]
        if basis == "X":
            return [half, half] if bit == 0 else [half, -half]
        # Y eigenstates: |+i> (bit 0) and |-i> (bit 1).
        return [half, half * 1j] if bit == 0 else [half, -half * 1j]

    @staticmethod
    def _normalise_key(public_key: dict) -> dict:
        """Validate and canonicalise a public key dict.

        Args:
            public_key: Raw key with ``expected`` and ``bases`` sequences.

        Returns:
            Normalised key dict.

        Raises:
            ValueError: If the key is malformed or the registers are misaligned.
        """
        if not isinstance(public_key, dict) or "expected" not in public_key or "bases" not in public_key:
            raise ValueError("public key must contain 'expected' and 'bases' sequences.")
        expected = [int(bit) for bit in public_key["expected"]]
        bases = [str(basis) for basis in public_key["bases"]]
        if len(expected) != len(bases):
            raise ValueError("public key 'expected' and 'bases' must have equal length.")
        return {
            "bases": bases,
            "expected": expected,
            "device_id": str(public_key.get("device_id", DEFAULT_KEY_DEVICE_ID)),
            "length": len(expected),
        }

    # ------------------------------------------------------------------ #
    #  Measurement-device-independent building blocks
    # ------------------------------------------------------------------ #
    @staticmethod
    def apply_pauli_correction(state: QuantumState, correction: str) -> QuantumState:
        """Apply a classical-feedforward Pauli correction to a qubit.

        Args:
            state: Single-qubit state recovered from the untrusted node.
            correction: One of ``I``, ``X``, ``Y``, ``Z`` (case-insensitive).

        Returns:
            Corrected QuantumState.

        Raises:
            KeyError: For an unsupported correction label.
        """
        return pauli_correction(state, correction, qubit=0)

    @staticmethod
    def projective_measurement(state: QuantumState, basis: str) -> tuple[int, float]:
        """Projectively measure one qubit and sample a Born outcome.

        Args:
            state: Single-qubit state to measure.
            basis: ``Z``/``computational``, ``X``/``hadamard`` or ``Y``.

        Returns:
            Tuple of (outcome 0|1, its Born probability).
        """
        return projective_measure(state, basis, qubit=0)

    @classmethod
    def _event_outcome(cls, event: dict) -> tuple[int, bool]:
        """Derive the canonical bit of one measurement event.

        Two paths feed a result: the node may report a raw ``outcome`` that a
        classical bit-flip correction maps to the canonical bit, or it may hand
        over the ``state`` recovered before the Pauli feed-forward, in which
        case the correction is applied unitarily and the outcome is re-derived
        by a projective measurement in the event's basis.

        Args:
            event: Single signature measurement event.

        Returns:
            Tuple of (canonical bit, True when derived via the state path).
        """
        basis = str(event.get("basis", "Z"))
        correction = str(event.get("correction", "I"))
        if "state" in event and event["state"] is not None:
            amplitudes = np.asarray(event["state"], dtype=complex).ravel()
            recovered = QuantumState(amplitudes, num_qubits=1)
            corrected = cls.apply_pauli_correction(recovered, correction)
            outcome, _probability = cls.projective_measurement(corrected, basis)
            return int(outcome), True
        return int(event["outcome"]), False

    # ------------------------------------------------------------------ #
    #  MDI verification
    # ------------------------------------------------------------------ #
    @classmethod
    def mdi_verify(cls, signature: Any, public_key: dict) -> dict:
        """Verify a signature against the public key in a measurement-device
        independent way.

        Events whose basis disagrees with the key register are discarded
        (sifting). The remaining events have their Pauli feed-forward applied
        (classically or unitarily) and are compared with the expected bits.

        Args:
            signature: Dict with an ``events`` list (or a bare list of event
                dicts), as produced by :meth:`generate_signature`.
            public_key: Public key dict for the claimed signer.

        Returns:
            Dict with ``match_rate``, ``verified``, ``kept_events``,
            ``discarded_events`` and ``correct_events``.
        """
        events = signature["events"] if isinstance(signature, dict) else list(signature)
        key = cls._normalise_key(public_key)

        kept = 0
        correct = 0
        discarded = 0
        for index, event in enumerate(events):
            if index >= key["length"] or str(event.get("basis", "Z")) != key["bases"][index]:
                discarded += 1
                continue
            canonical_bit, via_state = cls._event_outcome(event)
            if not via_state:
                correction = str(event.get("correction", "I"))
                canonical_bit = canonical_bit ^ (1 if correction in MVS_BIT_FLIP_CORRECTIONS else 0)
            kept += 1
            if canonical_bit == key["expected"][index]:
                correct += 1

        match_rate = correct / kept if kept else 0.0
        verified = bool(match_rate >= MVS_MATCH_THRESHOLD)
        return {
            "match_rate": float(match_rate),
            "verified": verified,
            "kept_events": kept,
            "discarded_events": discarded,
            "correct_events": correct,
            "agreement": verified,
        }
# ------------------------------------------------------------------ #
    #  BaseLayer contract
    # ------------------------------------------------------------------ #
    def process(self, input_data: dict) -> dict:
        """Verify the submitted signature across all measurement bases.

        Args:
            input_data: Optional keys —
                ``signature`` (event list/dict; omitted means the genuine
                signer reports, so a matched signature is generated),
                ``public_key`` (key dict; defaults to the enrolled baseline),
                ``forged`` (bool; simulates an unrelated signer) and
                ``tampered`` (bool or fraction in [0, 1]; corrupts that share
                of corrected outcome bits).

        Returns:
            Standard result envelope; PASS at full agreement, SUSPICIOUS for
            a degraded match, and FAIL for a forgery.
        """
        public_key = input_data.get("public_key") or self.BASELINE_PUBLIC_KEY
        signature = input_data.get("signature")

        forged = bool(input_data.get("forged", False))
        tampered = input_data.get("tampered", False)
        if isinstance(tampered, bool):
            tamper_fraction = MVS_TAMPER_FRACTION if tampered else 0.0
        else:
            tamper_fraction = float(tampered)

        # A plain string signature (e.g. passed from API routes) is not a
        # structured MDI event list; treat it as absent so generate_signature
        # produces the correct event-list structure for mdi_verify.
        if not isinstance(signature, (dict, list)):
            signature = None

        if signature is None:
            signature = self.generate_signature(
                public_key, forgery=forged, tamper_fraction=tamper_fraction
            )

        verdict = self.mdi_verify(signature, public_key)
        match_rate = verdict["match_rate"]
        deviation = float(max(0.0, 1.0 - match_rate))

        if verdict["verified"]:
            status = STATUS_PASS
        elif match_rate > MVS_FORGERY_MAX:
            status = STATUS_SUSPICIOUS
        else:
            status = STATUS_FAIL

        return self.make_result(
            status,
            deviation,
            {
                "match_rate": match_rate,
                "verified": verdict["verified"],
                "kept_events": verdict["kept_events"],
                "discarded_events": verdict["discarded_events"],
                "correct_events": verdict["correct_events"],
                "signature_length": MVS_SIGNATURE_LENGTH,
                "device_id": str(public_key.get("device_id", DEFAULT_KEY_DEVICE_ID)),
                "forged": forged,
            },
        )
