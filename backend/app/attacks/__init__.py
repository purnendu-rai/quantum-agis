"""Adversarial attack simulators for stress-testing the layer stack.

All attacks are stateless, return the standardized JSON envelope defined in
``base_attack`` (``attack_type`` / ``success`` / ``modified_data`` /
``detected_by`` / ``timestamp``), and are dispatchable by string via
:func:`get_attack_class` so API routes stay thin.
"""

from app.attacks.base_attack import (
    BaseAttack,
    RESULT_KEYS,
    VALID_ATTACK_TYPES,
)
from app.attacks.channel_tampering import ChannelTamperingAttack
from app.attacks.coherent import CoherentAttack
from app.attacks.forgery import ForgeryAttack
from app.attacks.impersonation import ImpersonationAttack
from app.attacks.replay import ReplayAttack

#: Registry mapping AttackType values to their simulator classes.
ATTACK_REGISTRY: dict[str, type[BaseAttack]] = {
    "forgery": ForgeryAttack,
    "impersonation": ImpersonationAttack,
    "replay": ReplayAttack,
    "channel_tampering": ChannelTamperingAttack,
    "coherent": CoherentAttack,
}


def get_attack_class(attack_type: str) -> type[BaseAttack]:
    """Return the simulator class registered for an AttackType value.

    Args:
        attack_type: One of the ``AttackType`` enum values.

    Returns:
        The registered BaseAttack subclass.

    Raises:
        KeyError: If no simulator is registered for the value.
    """
    return ATTACK_REGISTRY[str(attack_type)]


__all__ = [
    "ATTACK_REGISTRY",
    "RESULT_KEYS",
    "VALID_ATTACK_TYPES",
    "BaseAttack",
    "ForgeryAttack",
    "ImpersonationAttack",
    "ReplayAttack",
    "ChannelTamperingAttack",
    "CoherentAttack",
    "get_attack_class",
]
