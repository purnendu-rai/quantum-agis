"""Internal data structures used between engine components (not API-facing)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import AttackType, Verdict


@dataclass
class VerificationContext:
    """Request-scoped state threaded through the layer stack."""

    signature: str
    session_id: str
    channel_fidelity: float = 0.98
    layer_results: list["LayerResult"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class LayerResult:
    """Outcome of a single layer execution."""

    layer_id: int
    layer_name: str
    verdict: Verdict
    confidence: float
    metrics: dict = field(default_factory=dict)


@dataclass
class AttackScenario:
    """Snapshot of a channel/session an attack simulator operates on."""

    session_id: str
    channel_fidelity: float = 0.98
    hom_visibility: float = 0.95
    signature: str | None = None


@dataclass
class AttackResult:
    """Outcome of an attack simulation."""

    attack_type: AttackType
    detected: bool
    trust_score_after: float
    details: dict = field(default_factory=dict)
