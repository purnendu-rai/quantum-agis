"""Pydantic schemas for the public REST API (request/response contracts)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import AttackType, Decision, Severity, Verdict


class VerificationRequest(BaseModel):
    """Inbound signature-verification request."""

    signature: str = Field(..., min_length=1, description="Quantum signature payload to verify.")
    session_id: str = Field(..., description="Client session identifier.")
    channel_snapshot: dict | None = Field(default=None, description="Optional channel metrics supplied by the client.")


class LayerResultOut(BaseModel):
    """Per-layer result exposed to API consumers."""

    layer_id: int
    layer_name: str
    verdict: Verdict
    confidence: float = Field(..., ge=0.0, le=1.0)
    metrics: dict = Field(default_factory=dict)


class VerificationResponse(BaseModel):
    """Outbound verification verdict with trust score and layer breakdown."""

    verdict: Verdict
    decision: Decision
    trust_score: float = Field(..., ge=0.0, le=1.0)
    hom_visibility: float = Field(..., ge=0.0, le=1.0)
    channel_fidelity: float = Field(..., ge=0.0, le=1.0)
    layer_results: list[LayerResultOut] = Field(default_factory=list)


class AttackRequest(BaseModel):
    """Inbound attack-simulation request."""

    attack_type: AttackType
    intensity: float = Field(0.5, ge=0.0, le=1.0)
    session_id: str = Field(..., description="Session under attack.")


class AttackResponse(BaseModel):
    """Outbound attack-simulation report."""

    attack_type: AttackType
    detected: bool
    trust_score_after: float = Field(..., ge=0.0, le=1.0)
    details: dict = Field(default_factory=dict)


class SecurityEvent(BaseModel):
    """Single entry in the security event log feed."""

    timestamp: str
    severity: Severity
    source: str
    message: str
    session_id: str | None = None


class DashboardSnapshot(BaseModel):
    """Aggregated dashboard state (layer grid, trust gauge, alerts)."""

    trust_score: float = Field(..., ge=0.0, le=1.0)
    layer_verdicts: dict[str, Verdict] = Field(default_factory=dict)
    hom_visibility: float = Field(..., ge=0.0, le=1.0)
    channel_fidelity: float = Field(..., ge=0.0, le=1.0)
    active_alerts: list[SecurityEvent] = Field(default_factory=list)
