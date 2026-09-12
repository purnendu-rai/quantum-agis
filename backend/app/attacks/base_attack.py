"""Abstract base class for all attack simulators.

Every attack consumes a plain ``context`` dict and returns a standard,
JSON-serialisable envelope that is directly usable by the API:

    {"attack_type": str, "success": bool, "modified_data": dict,
     "detected_by": list, "timestamp": str}

``modified_data`` contains keys understood by ``VerificationEngine.verify``
(e.g. ``forged``, ``replay``, ``tampered``, ``claimed_genome``), so a route
handler can chain attack execution straight into re-verification. Attacks are
stateless: no instance state is mutated, no files are read or written, and all
randomness follows the framework's seeded-RNG policy (``RANDOM_SEED`` = 42),
so repeated runs against the same context produce identical results.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from zlib import crc32

import numpy as np

from app.layers.base_layer import seeded_rng, utc_now_iso
from app.models.enums import AttackType

#: Canonical keys of the standardized attack result envelope.
RESULT_KEYS: tuple[str, ...] = (
    "attack_type",
    "success",
    "modified_data",
    "detected_by",
    "timestamp",
)

#: Valid attack-type strings, derived from the shared enum.
VALID_ATTACK_TYPES: tuple[str, ...] = tuple(t.value for t in AttackType)


class BaseAttack(ABC):
    """Contract implemented by every attack simulator."""

    #: Short human-readable name (class attribute, e.g. "Forgery").
    name: str = "Attack"
    #: One-line description of the adversarial strategy.
    description: str = ""
    #: Layer names expected to flag this attack (e.g. ["QGM", "HIS"]).
    EXPECTED_DETECTION: tuple[str, ...] = ()

    def __init__(self, attack_type: str, intensity: float = 0.5) -> None:
        """Configure the attack identity and strength.

        Args:
            attack_type: One of the ``AttackType`` enum values (validated).
            intensity: Attack strength in [0, 1]; 1.0 is maximal
                interference. Values outside the range are clamped.

        Raises:
            ValueError: If ``attack_type`` is not a known AttackType value.
        """
        if str(attack_type) not in VALID_ATTACK_TYPES:
            raise ValueError(
                f"Unknown attack_type {attack_type!r}; expected one of {VALID_ATTACK_TYPES}."
            )
        self.attack_type: str = str(attack_type)
        self.intensity: float = float(min(1.0, max(0.0, float(intensity))))

    # ------------------------------------------------------------------ #
    #  Contract
    # ------------------------------------------------------------------ #
    @abstractmethod
    def execute(self, context: dict) -> dict:
        """Run the attack against the given context.

        Args:
            context: Session/channel snapshot. Recognised keys include
                ``session_id``, ``signature``, ``public_key``, ``device_id``,
                and ``timestamp``; all keys are optional and the context is
                treated as read-only.

        Returns:
            Standardized JSON envelope (see module docstring).
        """
        raise NotImplementedError

    @staticmethod
    def get_parameters() -> dict:
        """Return the tunable parameters and defaults for this attack."""
        return {"intensity": 0.5}

    # ------------------------------------------------------------------ #
    #  Shared helpers (stateless)
    # ------------------------------------------------------------------ #
    def _envelope(self, modified_data: dict, success: bool = True) -> dict:
        """Build the standardized, JSON-serialisable result envelope.

        Args:
            modified_data: Payload keys describing the perturbation; merged
                with the attack type so callers can feed it straight into
                ``VerificationEngine.verify``.
            success: Whether the attack perturbed the channel (True unless
                the simulation itself was a no-op).

        Returns:
            Envelope dict with exactly the RESULT_KEYS entries; the attack
            type is mirrored into ``modified_data["attack_type"]``.
        """
        payload = dict(modified_data)
        payload.setdefault("attack_type", self.attack_type)
        payload.setdefault("intensity", self.intensity)
        payload["expected_detection"] = list(self.EXPECTED_DETECTION)
        return {
            "attack_type": self.attack_type,
            "success": bool(success),
            "modified_data": payload,
            "detected_by": list(self.EXPECTED_DETECTION),
            "timestamp": utc_now_iso(),
        }

    def _rng(self) -> np.random.Generator:
        """Return the attack's deterministic RNG stream.

        Derived from the framework seed policy plus a CRC32 of the attack
        type, so results are reproducible without any stored state.

        Returns:
            A fresh ``numpy.random.default_rng`` generator.
        """
        return seeded_rng(crc32(self.attack_type.encode("utf-8")))

