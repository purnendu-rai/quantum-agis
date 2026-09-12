"""Coherent attack — coordinated multi-vector adversary.

Combines forgery, replay, and channel tampering in a single adaptive
strategy; the hardest detection case and the benchmark for Layer 5. The
attacker entangles an ancilla qubit with the channel, so every sensor layer
sees its characteristic perturbation at once and multiple layers trigger.
"""

from __future__ import annotations

from app.attacks.base_attack import BaseAttack
from app.layers.layer2_nhgs import DEFAULT_GAIN, DEFAULT_LOSS, NHGSLayer
from app.layers.layer3_tcp import TCPLayer

#: Fraction of the total intensity allocated to each sub-vector.
_SUB_WEIGHTS: dict[str, float] = {"forgery": 0.34, "replay": 0.33, "tampering": 0.33}

#: Sub-perturbations this coherent adversary composes.
COMPOSED_PERTURBATIONS: tuple[str, ...] = ("forged", "replay", "tampered")


class CoherentAttack(BaseAttack):
    """Simulates a full-spectrum adaptive adversary."""

    name = "Coherent Attack"
    description = (
        "Entangles an ancilla qubit with the channel and composes forgery, "
        "replay, and tampering in one adaptive campaign."
    )
    EXPECTED_DETECTION = ("QGM", "HIS", "NHGS", "TCP", "MVS")

    def __init__(self, intensity: float = 0.5) -> None:
        """Configure the coherent attack.

        Args:
            intensity: Attack strength in [0, 1] (scales every sub-vector).
        """
        super().__init__("coherent", intensity=intensity)

    def execute(self, context: dict) -> dict:
        """Run the composed multi-vector campaign against the channel.

        The adversary entangles an ancilla qubit with the channel (a
        normalised 2-qubit statevector on the seeded stream; its concurrence
        proxy bounds the injected entanglement) and simultaneously perturbs
        the session with forgery, replay, and tampering — each scaled by the
        intensity share allocated to it.

        Args:
            context: Read-only session snapshot; ``session_id``,
                ``signature``, and ``public_key`` are recognised.

        Returns:
            Standardized envelope whose ``modified_data`` sets every engine
            flag at once (``forged``, ``replay``, ``tampered``) alongside
            the entanglement metrics, so re-verification sees all vectors.
        """
        rng = self._rng()
        session_id = str(context.get("session_id", "unknown-session"))

        # Ancilla entangled with the channel: normalised 2-qubit statevector.
        amplitudes = rng.normal(size=4) + 1j * rng.normal(size=4)
        ancilla_state = amplitudes / np_abs_sum(amplitudes)
        concurrence_proxy = float(
            2.0
            * abs(
                ancilla_state[0] * ancilla_state[3] - ancilla_state[1] * ancilla_state[2]
            )
        )

        # Sub-vector intensities (shares sum to the total intensity).
        shares = {name: _SUB_WEIGHTS[name] * self.intensity for name in _SUB_WEIGHTS}

        # Spectral perturbation for the tampering share.
        sensor = NHGSLayer()
        lattice = sensor.construct_lattice(
            size=4,
            gain=DEFAULT_GAIN + shares["tampering"],
            loss=DEFAULT_LOSS - shares["tampering"],
        )
        spectrum = sensor.compute_eigenvalues(lattice)

        # Coherence length of the perturbed photon statistics: noise broadens
        # the linewidth, shortening tau_c relative to the enrolled source.
        photon_statistics = {
            "center_wavelength_m": 1550e-9,
            "linewidth_m": 3e-9 * (1.0 + shares["replay"] + shares["tampering"]),
        }
        tau_c = TCPLayer().compute_coherence_length(photon_statistics)

        return self._envelope(
            {
                "session_id": session_id,
                "forged": True,
                "replay": True,
                "tampered": True,
                "noise_level": shares["tampering"],
                "entangled_ancilla_state": [
                    [float(value.real), float(value.imag)] for value in ancilla_state
                ],
                "concurrence_proxy": concurrence_proxy,
                "lattice_shape": list(lattice.shape),
                "lattice_gain": float(DEFAULT_GAIN + shares["tampering"]),
                "lattice_loss": float(DEFAULT_LOSS - shares["tampering"]),
                "perturbed_spectrum_spread": float(
                    spectrum.real.max() - spectrum.real.min()
                ),
                "perturbed_tau_c": tau_c,
                "sub_intensities": shares,
                "composed": list(COMPOSED_PERTURBATIONS),
            }
        )


def np_abs_sum(state) -> float:
    """Return the L1 magnitude sum of a complex statevector (JSON float).

    Args:
        state: Sequence of complex amplitudes.

    Returns:
        Sum of the absolute amplitudes.
    """
    import numpy as np

    return float(np.abs(np.asarray(state, dtype=complex)).sum())
