"""Dashboard endpoints — aggregated state for the React monitoring UI.

Routes
------
GET /api/dashboard/state    — current system state snapshot
GET /api/dashboard/metrics  — time-series metric history
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.enums import Verdict
from app.models.schemas import DashboardSnapshot, SecurityEvent

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/state", response_model=DashboardSnapshot)
async def dashboard_state() -> DashboardSnapshot:
    """Return the current dashboard state in a single round-trip.

    Returns:
        DashboardSnapshot with trust score, layer verdicts, and alerts.
    """
    from app.services.metrics_service import metrics_service
    from app.services.logging_service import logging_service
    from app.models.enums import Severity

    latest = metrics_service.latest_values()
    trust_score = float(latest.get("trust_score", 0.95))
    hom_visibility = float(latest.get("hom_visibility", 0.95))
    channel_fidelity = float(latest.get("channel_fidelity", 0.95))

    # Build layer verdicts from latest trust — placeholder until wired per layer
    layer_verdicts: dict[str, Verdict] = {
        "QGM": Verdict.AUTHENTIC if trust_score > 0.8 else Verdict.SUSPICIOUS,
        "HIS": Verdict.AUTHENTIC if hom_visibility > 0.7 else Verdict.SUSPICIOUS,
        "NHGS": Verdict.AUTHENTIC if trust_score > 0.75 else Verdict.SUSPICIOUS,
        "TCP": Verdict.AUTHENTIC if channel_fidelity > 0.7 else Verdict.SUSPICIOUS,
        "MVS": Verdict.AUTHENTIC if trust_score > 0.85 else Verdict.SUSPICIOUS,
        "BTFE": Verdict.AUTHENTIC if trust_score > 0.90 else Verdict.SUSPICIOUS,
    }

    # Active alerts: last 5 warning/critical events
    alerts = logging_service.list(limit=5, severity=Severity.WARNING) + \
              logging_service.list(limit=5, severity=Severity.CRITICAL)

    return DashboardSnapshot(
        trust_score=trust_score,
        layer_verdicts=layer_verdicts,
        hom_visibility=hom_visibility,
        channel_fidelity=channel_fidelity,
        active_alerts=alerts[:5],
    )


@router.get("/dashboard/metrics")
async def dashboard_metrics(
    metric: str = Query("trust_score", description="Metric name to query"),
    limit: int = Query(50, ge=1, le=500, description="Number of data points"),
) -> dict:
    """Return time-series metric history for a given metric.

    Args:
        metric: Metric name (trust_score, hom_visibility, channel_fidelity).
        limit: Number of data points to return.

    Returns:
        Dict with metric name and list of {timestamp, value} points.
    """
    from app.services.metrics_service import metrics_service

    points = metrics_service.history(metric, limit=limit)
    return {
        "metric": metric,
        "points": points,
        "count": len(points),
    }


@router.get("/dashboard/nh-spectrum")
async def nh_spectrum(
    tampering: float = Query(0.0, ge=0.0, le=1.0, description="Tampering intensity for the demo probe."),
) -> dict:
    """Return the NHGS lattice eigenvalue spectrum for the dashboard chart.

    Args:
        tampering: When > 0, injects seeded complex lattice noise at that
            intensity so the UI can visualise spectral drift live.

    Returns:
        Dict with ``spectrum`` and ``baseline`` as [real, imag] pairs,
        ``exceptional_points`` as index pairs, and the applied tampering.
    """
    from zlib import crc32

    import numpy as np

    from app.layers.base_layer import seeded_rng
    from app.layers.layer2_nhgs import (
        DEFAULT_GAIN,
        DEFAULT_LATTICE_SIZE,
        DEFAULT_LOSS,
        TAMPER_NOISE_SCALE,
        NHGSLayer,
    )

    layer = NHGSLayer()
    lattice = layer.construct_lattice(DEFAULT_LATTICE_SIZE, DEFAULT_GAIN, DEFAULT_LOSS)
    if tampering > 0.0:
        rng = seeded_rng(crc32(b"nhgs-tamper"))
        noise_scale = TAMPER_NOISE_SCALE * float(tampering)
        lattice = lattice + noise_scale * (
            rng.standard_normal(lattice.shape) + 1j * rng.standard_normal(lattice.shape)
        )
    spectrum = layer.compute_eigenvalues(lattice)
    exceptional = layer.find_exceptional_points(spectrum)
    baseline = layer.BASELINE_SPECTRUM

    return {
        "spectrum": [[float(z.real), float(z.imag)] for z in np.asarray(spectrum, dtype=complex)],
        "baseline": [[float(z.real), float(z.imag)] for z in np.asarray(baseline, dtype=complex)],
        "exceptional_points": [[int(i), int(j)] for i, j in exceptional],
        "tampering": float(tampering),
    }
