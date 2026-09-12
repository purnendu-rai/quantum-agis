"""Health and readiness endpoints for uptime monitoring (Render/uptime pings)."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Liveness probe — required by Render for uptime monitoring.

    Returns:
        Dict with status, version, and environment.
    """
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/ready")
async def readiness_check() -> dict:
    """Readiness probe: confirms services are initialised."""
    from app.services.simulation_service import simulation_service
    from app.services.logging_service import logging_service
    from app.services.metrics_service import metrics_service

    return {
        "status": "ready",
        "components": {
            "simulation": "ok" if simulation_service is not None else "unavailable",
            "logging": "ok" if logging_service is not None else "unavailable",
            "metrics": "ok" if metrics_service is not None else "unavailable",
        },
    }
