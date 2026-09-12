"""Enumerations shared across the backend: verdicts, decisions, attack types."""

from enum import Enum


class Verdict(str, Enum):
    """Outcome emitted by a verification layer or the fused engine."""

    AUTHENTIC = "authentic"
    SUSPICIOUS = "suspicious"
    REJECTED = "rejected"


class Decision(str, Enum):
    """Final access decision derived from the trust score."""

    ACCEPT = "accept"
    REJECT = "reject"
    QUARANTINE = "quarantine"


class AttackType(str, Enum):
    """Adversarial strategies simulated by the attack modules."""

    FORGERY = "forgery"
    IMPERSONATION = "impersonation"
    REPLAY = "replay"
    CHANNEL_TAMPERING = "channel_tampering"
    COHERENT = "coherent"


class LayerStatus(str, Enum):
    """Execution status reported by a verification layer."""

    PASS = "pass"
    FAIL = "fail"
    SUSPICIOUS = "suspicious"


class Severity(str, Enum):
    """Alert severity used in the security event log feed."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
