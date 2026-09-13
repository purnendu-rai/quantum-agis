"""Signature-verification endpoints — the core AGIS workflow.

Routes
------
POST /api/verify          — run the full layer stack
GET  /api/verify/history  — list past verification events
"""

from __future__ import annotations

import uuid
from collections import deque
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.models.enums import Decision, Verdict
from app.models.schemas import LayerResultOut, VerificationRequest, VerificationResponse
from app.utils.rate_limiter import RateLimiter
from app.utils.validators import validate_session_id, validate_signature_format

router = APIRouter(tags=["verification"])

# In-memory rolling window of the last 100 verification results
_history: deque[VerificationResponse] = deque(maxlen=100)

#: 60 verifications per minute per client — generous for the demo UI.
_verify_limiter = RateLimiter(max_requests=60, window_seconds=60.0)


@router.post("/verify", response_model=VerificationResponse)
async def verify_signature(request: Request, request_body: VerificationRequest) -> VerificationResponse:
    """Run the full 6-layer AGIS stack against a submitted signature.

    Args:
        request: Signature payload plus session identifier.

    Returns:
        VerificationResponse with verdict, decision, and per-layer results.
    """
    client_key = request.client.host if request.client else "testclient"
    if not _verify_limiter.check(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Retry in a minute.")

    from app.services.simulation_service import simulation_service
    from app.services.logging_service import logging_service
    from app.services.metrics_service import metrics_service
    from app.models.enums import Severity

    try:
        validate_signature_format(request_body.signature)
        validate_session_id(request_body.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    payload: dict = {
        "signature": request_body.signature,
        "session_id": request_body.session_id,
    }
    if request_body.channel_snapshot:
        payload.update(request_body.channel_snapshot)

    raw = await simulation_service.run_verification(payload)

    # Map engine output to API schema
    layer_results = [
        LayerResultOut(
            layer_id=lr.get("layer_id", i),
            layer_name=lr.get("layer_name", f"layer_{i}"),
            verdict=_status_to_verdict(lr.get("status", "pass")),
            confidence=max(0.0, min(1.0, 1.0 - float(lr.get("deviation_score", 0.0)))),
            metrics=lr.get("metrics", {}),
        )
        for i, lr in enumerate(raw.get("layer_results", []))
    ]

    trust_score = float(raw.get("trust_score", 0.5))
    verdict_val = raw.get("verdict", Verdict.SUSPICIOUS.value)
    verdict = Verdict(verdict_val) if isinstance(verdict_val, str) else verdict_val

    api_decision_val = raw.get("api_decision", Decision.QUARANTINE.value)
    decision = Decision(api_decision_val) if isinstance(api_decision_val, str) else api_decision_val

    # Derive HOM visibility and channel fidelity from layer metrics if present
    hom_visibility = _extract_metric(raw, "hom_visibility", 0.95)
    channel_fidelity = _extract_metric(raw, "channel_fidelity", 0.95)

    response = VerificationResponse(
        verdict=verdict,
        decision=decision,
        trust_score=trust_score,
        hom_visibility=hom_visibility,
        channel_fidelity=channel_fidelity,
        layer_results=layer_results,
    )
    _history.appendleft(response)

    # Record metrics and log
    metrics_service.record("trust_score", trust_score)
    metrics_service.record("hom_visibility", hom_visibility)
    metrics_service.record("channel_fidelity", channel_fidelity)
    logging_service.record(
        severity=Severity.INFO if decision == Decision.ACCEPT else Severity.WARNING,
        source="verification",
        message=f"Verification {verdict.value} | trust={trust_score:.3f} | decision={decision.value}",
        session_id=request_body.session_id,
    )

    return response


@router.get("/verify/history", response_model=list[VerificationResponse])
async def verification_history(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[VerificationResponse]:
    """Return recent verification results, newest first.

    Args:
        limit: Maximum events to return (1-100).

    Returns:
        List of VerificationResponse entries.
    """
    return list(_history)[:limit]


# ── helpers ───────────────────────────────────────────────────────────────────

def _status_to_verdict(status: str) -> Verdict:
    mapping = {
        "pass": Verdict.AUTHENTIC,
        "fail": Verdict.REJECTED,
        "suspicious": Verdict.SUSPICIOUS,
    }
    return mapping.get(str(status).lower(), Verdict.SUSPICIOUS)


def _extract_metric(raw: dict, key: str, default: float) -> float:
    """Try to pull a named metric out of the engine result."""
    if key in raw:
        return max(0.0, min(1.0, float(raw[key])))
    # Scan layer metrics for the key
    for lr in raw.get("layer_results", []):
        metrics = lr.get("metrics", {})
        if key in metrics:
            return max(0.0, min(1.0, float(metrics[key])))
    return default
