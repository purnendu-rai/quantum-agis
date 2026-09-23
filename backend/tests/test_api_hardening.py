"""Tests for API hardening: input validation and rate limiting."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.rate_limiter import RateLimiter


@pytest.fixture
def client() -> TestClient:
    """Provide a TestClient for the app.

    Returns:
        TestClient instance.
    """
    return TestClient(app)


class TestInputValidation:
    """400 responses for structurally invalid payloads."""

    def test_verify_rejects_oversized_signature(self, client: TestClient):
        """Signatures above 4096 characters are rejected with 400."""
        response = client.post(
            "/api/verify",
            json={"signature": "A" * 5000, "session_id": "hardening"},
        )
        assert response.status_code == 400

    def test_verify_rejects_unsafe_session_id(self, client: TestClient):
        """Injection-prone session identifiers are rejected with 400."""
        response = client.post(
            "/api/verify",
            json={"signature": "AGIS-ok-signature", "session_id": "bad; drop table"},
        )
        assert response.status_code == 400

    def test_verify_rejects_short_signature(self, client: TestClient):
        """Signatures shorter than 4 characters are rejected with 400."""
        response = client.post(
            "/api/verify",
            json={"signature": "ab", "session_id": "hardening"},
        )
        assert response.status_code == 400

    def test_attack_rejects_unsafe_session_id(self, client: TestClient):
        """Attack endpoint rejects unsafe session identifiers with 400."""
        response = client.post(
            "/api/attack/forgery",
            params={"intensity": 0.5, "session_id": "bad session"},
        )
        assert response.status_code == 400


class TestRateLimiting:
    """Sliding-window limiter unit behaviour."""

    def test_allows_requests_under_limit(self):
        """Requests within the limit are allowed."""
        limiter = RateLimiter(max_requests=3, window_seconds=60.0)
        assert limiter.check("ip-1") is True
        assert limiter.check("ip-1") is True
        assert limiter.check("ip-1") is True

    def test_blocks_requests_over_limit(self):
        """The request that exceeds the limit is blocked."""
        limiter = RateLimiter(max_requests=2, window_seconds=60.0)
        limiter.check("ip-2")
        limiter.check("ip-2")
        assert limiter.check("ip-2") is False

    def test_keys_are_isolated(self):
        """One client exhausting the limit does not affect another."""
        limiter = RateLimiter(max_requests=1, window_seconds=60.0)
        limiter.check("ip-a")
        assert limiter.check("ip-b") is True

    def test_window_slides(self):
        """Hits older than the window no longer count against the client."""
        limiter = RateLimiter(max_requests=1, window_seconds=0.05)
        assert limiter.check("ip-c") is True
        assert limiter.check("ip-c") is False
        import time

        time.sleep(0.06)
        assert limiter.check("ip-c") is True


class TestSecurityHeaders:
    """Defensive HTTP headers applied to all responses."""

    def test_security_headers_present(self, client: TestClient):
        """Responses include nosniff, DENY, and Referrer-Policy."""
        response = client.get("/api/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

