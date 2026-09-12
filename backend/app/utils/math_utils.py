"""Mathematical helpers shared by quantum modules.

All functions are pure, operate on NumPy density matrices (plain complex
arrays), and raise ValueError on non-density-matrix input so they can be
unit-tested without the service layer.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import sqrtm


def _as_density_matrix(rho) -> np.ndarray:
    """Validate and coerce an input into a square complex density matrix.

    Args:
        rho: Array-like candidate density matrix.

    Returns:
        Complex ndarray of shape (d, d).

    Raises:
        ValueError: If the input is not a square 2-D matrix.
    """
    matrix = np.asarray(rho, dtype=complex)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("rho must be a square 2-D density matrix.")
    return matrix


def fidelity(rho_a, rho_b) -> float:
    """Compute the Uhlmann state fidelity between two density matrices.

    For pure inputs (rank-1 rho) this reduces to F = |<a|b>|^2; otherwise
    F = (Tr sqrt(sqrt(rho_a) rho_b sqrt(rho_a)))^2.

    Args:
        rho_a: First density matrix (square array-like).
        rho_b: Second density matrix (square array-like).

    Returns:
        Fidelity in [0, 1].
    """
    a = _as_density_matrix(rho_a)
    b = _as_density_matrix(rho_b)
    if a.shape != b.shape:
        raise ValueError("Density matrices must have equal dimensions.")
    # Pure-state shortcut: single dominant eigenvalue means a rank-1 state.
    if _is_pure(a) and _is_pure(b):
        vec_a = _dominant_eigenvector(a)
        vec_b = _dominant_eigenvector(b)
        return float(np.clip(np.abs(np.vdot(vec_a, vec_b)) ** 2, 0.0, 1.0))
    sqrt_a = sqrtm(a)
    inner = sqrtm(sqrt_a @ b @ sqrt_a)
    return float(np.clip(np.real(np.trace(inner)) ** 2, 0.0, 1.0))


def trace_distance(rho_a, rho_b) -> float:
    """Compute the trace distance between two density matrices.

    D(a, b) = 1/2 * sum of singular values of (a - b); 0 means the states are
    indistinguishable by any measurement.

    Args:
        rho_a: First density matrix (square array-like).
        rho_b: Second density matrix (square array-like).

    Returns:
        Trace distance in [0, 1].
    """
    a = _as_density_matrix(rho_a)
    b = _as_density_matrix(rho_b)
    if a.shape != b.shape:
        raise ValueError("Density matrices must have equal dimensions.")
    singular_values = np.linalg.svd(a - b, compute_uv=False)
    return float(np.clip(0.5 * np.sum(singular_values), 0.0, 1.0))


def von_neumann_entropy(rho) -> float:
    """Compute the von Neumann entropy of a density matrix in bits.

    S(rho) = -Tr(rho log2 rho), evaluated via the eigenvalues; a pure state
    has S = 0 and the maximally mixed qubit state has S = 1.

    Args:
        rho: Density matrix (square array-like).

    Returns:
        Entropy in bits (>= 0).
    """
    matrix = _as_density_matrix(rho)
    eigenvalues = np.linalg.eigvalsh(matrix)
    probs = np.clip(np.real(eigenvalues), 0.0, None)
    probs = probs[probs > 1e-12]
    if probs.size == 0:
        return 0.0
    entropy = float(-np.sum(probs * np.log2(probs)))
    return float(max(0.0, entropy))


def _is_pure(rho: np.ndarray, tol: float = 1e-9) -> bool:
    """Check whether a density matrix is pure (Tr rho^2 == 1).

    Args:
        rho: Density matrix.
        tol: Numerical tolerance.

    Returns:
        True when the purity is 1 within tolerance.
    """
    return bool(abs(float(np.real(np.trace(rho @ rho))) - 1.0) < tol)


def _dominant_eigenvector(rho: np.ndarray) -> np.ndarray:
    """Return the normalised eigenvector of the largest eigenvalue.

    Args:
        rho: Density matrix.

    Returns:
        Complex eigenvector of the dominant eigenvalue.
    """
    eigenvalues, eigenvectors = np.linalg.eigh(rho)
    return eigenvectors[:, int(np.argmax(eigenvalues))]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into [low, high].

    Args:
        value: Input value.
        low: Lower bound.
        high: Upper bound.

    Returns:
        The clamped value.
    """
    return float(max(low, min(high, value)))
