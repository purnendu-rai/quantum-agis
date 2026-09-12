"""Abstract base class shared by all security layers (0-5).

Every layer consumes a plain ``input_data`` dict and returns a standard
result envelope that is directly JSON-serialisable. Layers perform no file
I/O; all randomness is drawn from ``numpy.random.default_rng`` seeded from
``RANDOM_SEED`` (42) so runs are reproducible.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.core.constants import RANDOM_SEED

#: Canonical keys of the layer result envelope.
RESULT_KEYS: tuple[str, ...] = (
    "layer_id",
    "layer_name",
    "status",
    "deviation_score",
    "metrics",
    "timestamp",
)

STATUS_PASS: str = "PASS"
STATUS_SUSPICIOUS: str = "SUSPICIOUS"
STATUS_FAIL: str = "FAIL"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        Timezone-aware ISO-8601 timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()


def to_jsonable(value: Any) -> Any:
    """Recursively convert NumPy scalars/arrays into native JSON types.

    Args:
        value: Arbitrary object tree possibly containing NumPy types.

    Returns:
        The same tree with NumPy types replaced by float/int/bool/list.
    """
    if isinstance(value, np.ndarray):
        return [to_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def seeded_rng(*stream_labels: int) -> np.random.Generator:
    """Return a fresh RNG deterministically derived from RANDOM_SEED (42).

    Args:
        stream_labels: Extra integers (e.g. crc32 labels) individualising
            the stream while keeping the global seed policy.

    Returns:
        A ``numpy.random.default_rng`` generator.
    """
    return np.random.default_rng([RANDOM_SEED, *stream_labels])


class BaseLayer(ABC):
    """Contract implemented by every layer in the AGIS stack."""

    def __init__(self, layer_id: int, layer_name: str, weight: float) -> None:
        """Store the layer identity and its fusion weight.

        Args:
            layer_id: Position of the layer in the stack (0-5).
            layer_name: Short code, e.g. "QGM".
            weight: Fusion weight used by the BTFE trust formula.
        """
        self.layer_id: int = layer_id
        self.layer_name: str = layer_name
        self.weight: float = float(weight)
        self.enabled: bool = True
        self._history: list[dict] = []

    @abstractmethod
    def process(self, input_data: dict) -> dict:
        """Run the layer check against the request data.

        Args:
            input_data: Layer-specific payload (see each layer's docstring).

        Returns:
            Standard envelope: ``{"layer_id", "layer_name", "status",
            "deviation_score", "metrics", "timestamp"}`` where status is
            "PASS" | "SUSPICIOUS" | "FAIL".
        """
        raise NotImplementedError

    def make_result(self, status: str, deviation_score: float, metrics: dict) -> dict:
        """Build the standard, JSON-serialisable result envelope.

        Args:
            status: One of PASS / SUSPICIOUS / FAIL.
            deviation_score: Layer deviation in [0, 1] (clipped).
            metrics: Layer-specific metric dict (auto-converted to JSON types).

        Returns:
            The result envelope as a plain Python dict.
        """
        result = {
            "layer_id": self.layer_id,
            "layer_name": self.layer_name,
            "status": status,
            "deviation_score": float(np.clip(deviation_score, 0.0, 1.0)),
            "metrics": to_jsonable(metrics),
            "timestamp": utc_now_iso(),
        }
        self._history.append(result)
        return result

    def reset(self) -> None:
        """Clear per-session result history."""
        self._history.clear()
