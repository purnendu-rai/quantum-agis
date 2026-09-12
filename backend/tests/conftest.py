"""Shared pytest fixtures for the QUANTUM-AGIS test suite."""

import pytest

from app.models.internal import VerificationContext


@pytest.fixture
def verification_context() -> VerificationContext:
    """Provide a baseline verification context for layer/engine tests.

    Returns:
        VerificationContext with default channel parameters.
    """
    return VerificationContext(
        signature="QGM-HIS-NHGS-TCP-MVS-demo-signature",
        session_id="test-session-001",
        channel_fidelity=0.98,
    )
