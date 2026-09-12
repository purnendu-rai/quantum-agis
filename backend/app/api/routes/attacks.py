"""Attack-simulation endpoints — drives the adversarial test harness.

Routes
------
POST /api/attack/{attack_type}  — run a named attack and re-verify
GET  /api/attack/types          — list supported attack types
"""

from __future__ import annotations

import random
from typing import Any

from fastapi import APIRouter, HTTPException, Path

from app.models.enums import AttackType, Decision, Severity, Verdict
from app.models.schemas import AttackResponse

router = APIRouter(tags=["attacks"])

# Rolling window of attack history
_attack_history: list[AttackResponse] = []
_MAX_HISTORY = 100

# Per-attack descriptions for the frontend AttackPanel
_ATTACK_DESCRIPTORS: list[dict[str, Any]] = [
    {
        "type": AttackType.FORGERY.value,
        "label": "Quantum Forgery",
        "description": "Attempts to submit a fabricated quantum signature.",
        "parameters": {"intensity": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5}},
    },
    {
        "type": AttackType.IMPERSONATION.value,
        "label": "Identity Impersonation",
        "description": "Clones a legitimate node's quantum genome to hijack session.",
        "parameters": {"intensity": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5}},
    },
    {
        "type": AttackType.REPLAY.value,
        "label": "Replay Attack",
        "description": "Re-sends a previously captured authentic signature.",
        "parameters": {"intensity": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5}},
    },
    {
        "type": AttackType.CHANNEL_TAMPERING.value,
        "label": "Channel Tampering",
        "description": "Injects noise into the quantum channel to disrupt fidelity.",
        "parameters": {"intensity": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5}},
    },
    {
        "type": AttackType.COHERENT.value,
        "label": "Coherent Attack",
        "description": "Sophisticated multi-layer coordinated quantum attack.",
        "parameters": {"intensity": {"type": "float", "min": 0.0, "max": 1.0, "default": 0.5}},
    },
]

# Mapping from attack type to the payload flags that layer processors understand
_ATTACK_PAYLOAD_FLAGS: dict[str, dict] = {
    AttackType.FORGERY.value: {"forged": True},
    AttackType.IMPERSONATION.value: {"impersonation": True},
    AttackType.REPLAY.value: {"replay": True},
    AttackType.CHANNEL_TAMPERING.value: {"tampered": True},
    AttackType.COHERENT.value: {"forged": True, "tampered": True, "replay": True},
}


@router.get("/attack/types", response_model=list[dict])
async def list_attack_types() -> list[dict]:
    """List supported attack types and their tunable parameters.

    Returns:
        List of attack descriptors for the frontend AttackPanel.
    """
    return _ATTACK_DESCRIPTORS


@router.post("/attack/{attack_type}", response_model=AttackResponse)
async def run_attack(
    attack_type: str = Path(..., description="One of: forgery, impersonation, replay, channel_tampering, coherent"),
    intensity: float = 0.5,
    session_id: str = "attack-session",
) -> AttackResponse:
    """Execute a simulated attack then re-verify the channel.

    Args:
        attack_type: The attack variant to simulate.
        intensity: Fraction in [0, 1] controlling how aggressive the attack is.
        session_id: Session identifier to target.

    Returns:
        AttackResponse with detection status and post-attack trust score.
    """
    from app.services.simulation_service import simulation_service
    from app.services.logging_service import logging_service
    from app.services.metrics_service import metrics_service

    # Validate attack type
    try:
        at = AttackType(attack_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown attack type '{attack_type}'. Valid: {[e.value for e in AttackType]}",
        )

    # Build attacked payload — flags tell layers to simulate the attack
    flags = _ATTACK_PAYLOAD_FLAGS.get(at.value, {})
    payload: dict = {
        "session_id": session_id,
        "signature": f"ATTACK-{at.value}-{random.randint(1000, 9999)}",
        "intensity": float(max(0.0, min(1.0, intensity))),
        **flags,
    }

    raw = await simulation_service.run_attack(at.value, payload)

    trust_score_after = float(raw.get("trust_score", 0.0))
    decision_val = raw.get("api_decision", Decision.REJECT.value)
    detected = decision_val in (Decision.REJECT.value, Decision.QUARANTINE.value)

    details = {
        "attack_intensity": intensity,
        "decision": decision_val,
        "deviations": raw.get("deviations", {}),
        "chernoff_bound": raw.get("chernoff_bound", 0.0),
    }

    resp = AttackResponse(
        attack_type=at,
        detected=detected,
        trust_score_after=trust_score_after,
        details=details,
    )

    # Track history
    _attack_history.append(resp)
    if len(_attack_history) > _MAX_HISTORY:
        _attack_history.pop(0)

    # Log the attack event
    logging_service.record(
        severity=Severity.WARNING if detected else Severity.CRITICAL,
        source=f"attack.{at.value}",
        message=(
            f"Attack {at.value} {'DETECTED' if detected else 'UNDETECTED'} "
            f"| trust={trust_score_after:.3f} | intensity={intensity:.2f}"
        ),
        session_id=session_id,
    )
    metrics_service.record("trust_score", trust_score_after)

    return resp
