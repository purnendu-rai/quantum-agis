"""Tests for the shared math and validation utilities."""

import numpy as np
import pytest

from app.utils.math_utils import clamp, fidelity, trace_distance, von_neumann_entropy
from app.utils.validators import validate_intensity, validate_session_id, validate_signature_format

KET0 = np.array([[1, 0], [0, 0]], dtype=complex)
KET1 = np.array([[0, 0], [0, 1]], dtype=complex)
KET_PLUS = 0.5 * np.ones((2, 2), dtype=complex)
MAXIMALLY_MIXED = 0.5 * np.eye(2, dtype=complex)


class TestMathUtils:
    """Uhlmann fidelity, trace distance, and von Neumann entropy."""

    def test_fidelity_identical_pure_states_is_one(self):
        """F(rho, rho) = 1 for a pure state."""
        assert np.isclose(fidelity(KET0, KET0), 1.0)

    def test_fidelity_orthogonal_pure_states_is_zero(self):
        """F(|0>, |1>) = 0."""
        assert np.isclose(fidelity(KET0, KET1), 0.0)

    def test_fidelity_zero_with_plus_is_half(self):
        """F(|0>, |+>) = 1/2."""
        assert np.isclose(fidelity(KET0, KET_PLUS), 0.5)

    def test_fidelity_mixed_states_bell_marginals(self):
        """Uhlmann fidelity between the two I/2 marginals of a Bell pair is 1."""
        assert np.isclose(fidelity(MAXIMALLY_MIXED, MAXIMALLY_MIXED), 1.0)

    def test_fidelity_rejects_mismatched_dimensions(self):
        """Fidelity raises for matrices of different sizes."""
        with pytest.raises(ValueError):
            fidelity(KET0, np.eye(4, dtype=complex))

    def test_trace_distance_identical_is_zero(self):
        """Identical states are indistinguishable (D = 0)."""
        assert np.isclose(trace_distance(KET0, KET0), 0.0)

    def test_trace_distance_orthogonal_is_one(self):
        """Orthogonal pure states have D = 1."""
        assert np.isclose(trace_distance(KET0, KET1), 1.0)

    def test_trace_distance_rejects_mismatched_dimensions(self):
        """Trace distance raises for matrices of different sizes."""
        with pytest.raises(ValueError):
            trace_distance(KET0, np.eye(4, dtype=complex))

    def test_von_neumann_entropy_pure_state_is_zero(self):
        """Pure states carry no entropy."""
        assert np.isclose(von_neumann_entropy(KET0), 0.0)

    def test_von_neumann_entropy_maximally_mixed_is_one_bit(self):
        """The maximally mixed qubit has S = 1 bit."""
        assert np.isclose(von_neumann_entropy(MAXIMALLY_MIXED), 1.0)

    def test_clamp(self):
        """clamp() bounds values into [low, high]."""
        assert clamp(1.5) == 1.0
        assert clamp(-0.2) == 0.0
        assert clamp(0.42) == 0.42


class TestValidators:
    """Signature, session-id, and intensity validation."""

    def test_valid_signature_formats(self):
        """Base64/hex-style printable payloads are accepted."""
        assert validate_signature_format("AGIS-legit-001")
        assert validate_signature_format("c2hvcnQ")

    def test_invalid_signature_too_short(self):
        """Signatures shorter than 4 characters are rejected."""
        with pytest.raises(ValueError):
            validate_signature_format("ab")

    def test_invalid_signature_whitespace(self):
        """Signatures containing whitespace are rejected."""
        with pytest.raises(ValueError):
            validate_signature_format("bad signature with spaces")

    def test_valid_session_ids(self):
        """Alphanumeric/hyphen/underscore identifiers are accepted."""
        assert validate_session_id("demo-session-001")
        assert validate_session_id("a" * 64)

    def test_invalid_session_id_injection_characters(self):
        """Session ids with injection-prone characters are rejected."""
        with pytest.raises(ValueError):
            validate_session_id("bad;drop table")
        with pytest.raises(ValueError):
            validate_session_id("")

    def test_intensity_normalisation_and_clamping(self):
        """Intensity is clamped into [0, 1]."""
        assert validate_intensity(0.5) == 0.5
        assert validate_intensity(2.0) == 1.0
        assert validate_intensity(-1.0) == 0.0

    def test_intensity_rejects_non_numeric(self):
        """Non-numeric intensity raises TypeError."""
        with pytest.raises(TypeError):
            validate_intensity("high")
