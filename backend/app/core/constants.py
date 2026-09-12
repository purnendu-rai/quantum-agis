"""Physical and framework-wide constants for the quantum simulation core.

All matrices are plain NumPy arrays (pure Python, deployment-safe). This is
the single source of truth for gate definitions, Bell states, layer fusion
weights, and verification thresholds.
"""

import numpy as np

# --- RNG policy -------------------------------------------------------------
# Every stochastic component draws from this one seeded generator so the whole
# simulation is reproducible.
RANDOM_SEED: int = 42

# --- Single-qubit matrices --------------------------------------------------
IDENTITY: np.ndarray = np.eye(2, dtype=complex)
PAULI_X: np.ndarray = np.array([[0, 1], [1, 0]], dtype=complex)
PAULI_Y: np.ndarray = np.array([[0, -1j], [1j, 0]], dtype=complex)
PAULI_Z: np.ndarray = np.array([[1, 0], [0, -1]], dtype=complex)
HADAMARD: np.ndarray = (1.0 / np.sqrt(2.0)) * np.array([[1, 1], [1, -1]], dtype=complex)
PHASE_S: np.ndarray = np.array([[1, 0], [0, 1j]], dtype=complex)
PHASE_S_DAGGER: np.ndarray = np.array([[1, 0], [0, -1j]], dtype=complex)

# --- Two-qubit matrices (control = first qubit, target = second) ------------
CNOT: np.ndarray = np.array(
    [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 0],
    ],
    dtype=complex,
)

# --- Bell states (two-qubit amplitude vectors, index = q0 * 2 + q1) ---------
_SQRT2_INV: float = 1.0 / np.sqrt(2.0)
BELL_PHI_PLUS: np.ndarray = _SQRT2_INV * np.array([1, 0, 0, 1], dtype=complex)
BELL_PHI_MINUS: np.ndarray = _SQRT2_INV * np.array([1, 0, 0, -1], dtype=complex)
BELL_PSI_PLUS: np.ndarray = _SQRT2_INV * np.array([0, 1, 1, 0], dtype=complex)
BELL_PSI_MINUS: np.ndarray = _SQRT2_INV * np.array([0, 1, -1, 0], dtype=complex)

BELL_STATES: dict[str, np.ndarray] = {
    "phi_plus": BELL_PHI_PLUS,
    "phi_minus": BELL_PHI_MINUS,
    "psi_plus": BELL_PSI_PLUS,
    "psi_minus": BELL_PSI_MINUS,
}

# --- Physical constants (SI units) ------------------------------------------
H_BAR: float = 1.054_571_817e-34          # reduced Planck constant, J·s
ELEMENTARY_CHARGE: float = 1.602_176_634e-19  # Coulomb

# --- Trust-score layer weights (must sum to 1.0) ----------------------------
W_QGM: float = 0.25
W_HIS: float = 0.25
W_NHGS: float = 0.20
W_TCP: float = 0.15
W_MVS: float = 0.10
W_BTFE: float = 0.05

LAYER_WEIGHTS: dict[str, float] = {
    "QGM": W_QGM,
    "HIS": W_HIS,
    "NHGS": W_NHGS,
    "TCP": W_TCP,
    "MVS": W_MVS,
    "BTFE": W_BTFE,
}

# --- Verification / detection thresholds ------------------------------------
TRUST_ACCEPT: float = 0.95        # trust score at or above this -> authentic
TRUST_REJECT: float = 0.90        # trust score below this -> rejected
HOM_VISIBILITY_MIN: float = 0.95  # minimum HOM visibility for genuine quantum behaviour
HAMMING_THRESHOLD: float = 0.05   # maximum tolerated signature Hamming distance

# Backwards-compatible aliases used by the decision engine (app/engine).
TRUST_THRESHOLD_ALLOW = TRUST_ACCEPT
TRUST_THRESHOLD_CHALLENGE = TRUST_REJECT
