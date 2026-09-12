"""Security-event log endpoints — the audit trail behind the LogsPage.

Routes
------
GET /api/logs           — recent events with optional limit
GET /api/logs/export    — full JSONL export for SIEM hand-off
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import SecurityEvent

router = APIRouter(tags=["logs"])


@router.get("/logs", response_model=list[SecurityEvent])
async def list_events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return."),
    severity: str | None = Query(None, description="Filter by severity: info|warning|critical"),
) -> list[SecurityEvent]:
    """Return recent security events, newest first.

    Args:
        limit: Page size cap (1-1000).
        severity: Optional severity filter.

    Returns:
        List of SecurityEvent entries.
    """
    from app.services.logging_service import logging_service
    from app.models.enums import Severity

    sev = None
    if severity:
        try:
            sev = Severity(severity.lower())
        except ValueError:
            pass  # ignore invalid filter; return all

    return logging_service.list(limit=limit, severity=sev)


@router.get("/logs/export")
async def export_logs() -> dict:
    """Export the full in-memory event log (SIEM hand-off / demo reports).

    Returns:
        Dict containing the event list, count, and export metadata.
    """
    from app.services.logging_service import logging_service

    return logging_service.export()
