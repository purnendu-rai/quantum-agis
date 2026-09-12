"""API route tests for QUANTUM-AGIS backend.

Tests cover the full HTTP surface:
  - GET  /api/health
  - POST /api/verify
  - GET  /api/verify/history
  - GET  /api/attack/types
  - POST /api/attack/{attack_type}
  - GET  /api/dashboard/state
  - GET  /api/dashboard/metrics
  - GET  /api/logs
  - GET  /api/logs/export
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    """Return the FastAPI application (without starting the lifespan loop)."""
    from app.main import app as _app
    return _app


@pytest.fixture
async def client(app):
    """Async test client that bypasses the lifespan to keep tests fast."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_health_ready(client):
    response = await client.get("/api/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "components" in data


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_returns_valid_response(client):
    payload = {
        "signature": "test-quantum-signature-abc123",
        "session_id": "test-session-001",
    }
    response = await client.post("/api/verify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "verdict" in data
    assert "decision" in data
    assert "trust_score" in data
    assert 0.0 <= data["trust_score"] <= 1.0
    assert "layer_results" in data
    assert isinstance(data["layer_results"], list)


@pytest.mark.asyncio
async def test_verify_missing_session_id(client):
    """Should return 422 Unprocessable Entity for missing required fields."""
    response = await client.post("/api/verify", json={"signature": "abc"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_history(client):
    # Seed at least one entry
    await client.post("/api/verify", json={
        "signature": "history-test-sig",
        "session_id": "hist-session",
    })
    response = await client.get("/api/verify/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_verify_history_limit(client):
    response = await client.get("/api/verify/history?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2


# ---------------------------------------------------------------------------
# Attacks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_attack_types(client):
    response = await client.get("/api/attack/types")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    types_returned = {item["type"] for item in data}
    assert "forgery" in types_returned
    assert "impersonation" in types_returned
    assert "replay" in types_returned
    assert "channel_tampering" in types_returned
    assert "coherent" in types_returned


@pytest.mark.asyncio
@pytest.mark.parametrize("attack_type", [
    "forgery", "impersonation", "replay", "channel_tampering", "coherent"
])
async def test_run_attack(client, attack_type):
    response = await client.post(
        f"/api/attack/{attack_type}",
        params={"intensity": 0.7, "session_id": "attack-test-session"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["attack_type"] == attack_type
    assert "detected" in data
    assert "trust_score_after" in data
    assert 0.0 <= data["trust_score_after"] <= 1.0


@pytest.mark.asyncio
async def test_run_attack_invalid_type(client):
    response = await client.post("/api/attack/invalid_attack_xyz")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_state(client):
    response = await client.get("/api/dashboard/state")
    assert response.status_code == 200
    data = response.json()
    assert "trust_score" in data
    assert "layer_verdicts" in data
    assert "hom_visibility" in data
    assert "channel_fidelity" in data
    assert "active_alerts" in data


@pytest.mark.asyncio
async def test_dashboard_metrics(client):
    response = await client.get("/api/dashboard/metrics?metric=trust_score&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "trust_score"
    assert "points" in data
    assert isinstance(data["points"], list)


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_logs(client):
    # Trigger at least one log entry via verification
    await client.post("/api/verify", json={
        "signature": "log-test-sig",
        "session_id": "log-test-session",
    })
    response = await client.get("/api/logs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_logs_with_limit(client):
    response = await client.get("/api/logs?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5


@pytest.mark.asyncio
async def test_list_logs_severity_filter(client):
    response = await client.get("/api/logs?severity=info")
    assert response.status_code == 200
    data = response.json()
    for entry in data:
        assert entry["severity"] == "info"


@pytest.mark.asyncio
async def test_export_logs(client):
    response = await client.get("/api/logs/export")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "count" in data
    assert "exported_at" in data
