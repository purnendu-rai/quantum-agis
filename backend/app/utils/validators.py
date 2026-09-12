"""Input validation helpers for API payloads and internal structures."""

from __future__ import annotations

import re

#: Session identifiers: letters, digits, hyphens, underscores; 1-64 chars.
_SESSION_ID_PATTERN: re.Pattern = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

#: Signature payloads: printable ASCII without whitespace, 4-4096 chars.
_SIGNATURE_PATTERN: re.Pattern = re.compile(r"^[\x21-\x7e]{4,4096}$")


def validate_signature_format(signature: str) -> bool:
    """Check the structural format of a submitted quantum signature.

    A valid payload is 4-4096 printable non-whitespace ASCII characters
    (base64/hex-style tokens satisfy this).

    Args:
        signature: Raw signature payload.

    Returns:
        True when the payload matches the expected format.

    Raises:
        ValueError: On structurally invalid payloads.
    """
    text = str(signature)
    if not _SIGNATURE_PATTERN.match(text):
        raise ValueError(
            "signature must be 4-4096 printable non-whitespace ASCII characters."
        )
    return True


def validate_session_id(session_id: str) -> bool:
    """Check that a session identifier is well-formed and safe.

    Args:
        session_id: Client-supplied session identifier.

    Returns:
        True when the identifier is valid.

    Raises:
        ValueError: On empty or unsafe identifiers.
    """
    text = str(session_id)
    if not _SESSION_ID_PATTERN.match(text):
        raise ValueError(
            "session_id must be 1-64 characters of [A-Za-z0-9_-] (injection-safe)."
        )
    return True


def validate_intensity(value: float) -> float:
    """Normalise an attack-intensity value into [0, 1].

    Args:
        value: Raw intensity input.

    Returns:
        Clamped intensity as a float.

    Raises:
        TypeError: When the value is not numeric.
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("intensity must be a number.") from exc
    return float(min(1.0, max(0.0, numeric)))
