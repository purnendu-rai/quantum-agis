"""End-to-end integration tests for the full 6-layer AGIS pipeline.

Exercises the real engine exactly as production does: legitimate signatures
must be ACCEPTed, every attack strategy must be REJECTed, and the false
positive rate over 1000 legitimate signatures must be zero.
"""

from __future__ import annotations

import pytest

from app.engine.verification_engine import get_engine
#: Attack strategies mapped to the payload flags the layers understand.
ATTACK_FLAGS: dict[str, dict] = {
    "forgery": {"forged": True},
    "impersonation": {"impersonation": True},
    "replay": {"replay": True},
    "channel_tampering": {"tampered": True},
    "coherent": {"forged": True, "tampered": True, "replay": True},
}

#: False-positive-rate sample size (spec: 1000 legitimate signatures).
FPR_SAMPLE_SIZE: int = 1000


@pytest.fixture
def engine():
    """Provide the process-wide verification engine.

    Returns:
        The shared VerificationEngine instance.
    """
    return get_engine()


@pytest.mark.asyncio
async def test_legitimate_signature_is_accepted(engine):
    """A genuine signature passes the full stack with an ACCEPT decision."""
    result = await engine.verify(
        {"signature": "AGIS-integration-legit-001", "session_id": "integration"}
    )
    assert result["decision"] == "ACCEPT"
    assert result["trust_score"] > 0.95


@pytest.mark.parametrize("attack_type,flags", sorted(ATTACK_FLAGS.items()))
@pytest.mark.asyncio
async def test_each_attack_is_rejected(engine, attack_type, flags):
    """Every attack strategy drops the trust score below the reject band."""
    result = await engine.verify(
        {"signature": f"AGIS-integration-{attack_type}", "session_id": "integration", **flags}
    )
    assert result["decision"] == "REJECT", (
        f"{attack_type} was not rejected (trust={result['trust_score']:.3f})"
    )
    assert result["trust_score"] < 0.90


@pytest.mark.asyncio
async def test_false_positive_rate_is_zero_over_1000_legitimate_signatures(engine):
    """No legitimate signature out of 1000 is ever rejected or quarantined."""
    false_positives = 0
    for index in range(FPR_SAMPLE_SIZE):
        result = await engine.verify(
            {"signature": f"AGIS-legit-{index:05d}", "session_id": "fpr-batch"}
        )
        if result["decision"] != "ACCEPT":
            false_positives += 1
    assert false_positives == 0, (
        f"{false_positives}/{FPR_SAMPLE_SIZE} legitimate signatures were falsely flagged"
    )


@pytest.mark.asyncio
async def test_attack_then_legitimate_recovers(engine):
    """After an attack the channel returns to ACCEPT for a genuine signature."""
    await engine.verify(
        {"signature": "AGIS-attack-run", "session_id": "integration", **ATTACK_FLAGS["coherent"]}
    )
    recovery = await engine.verify(
        {"signature": "AGIS-recovery-run", "session_id": "integration"}
    )
    assert recovery["decision"] == "ACCEPT"


@pytest.mark.asyncio
async def test_result_is_json_serialisable(engine):
    """The engine result contains only JSON-safe types end to end."""
    import json

    result = await engine.verify({"signature": "AGIS-json-check", "session_id": "integration"})
    parsed = json.loads(json.dumps(result))
    assert parsed["trust_score"] == result["trust_score"]
    assert len(parsed["layer_results"]) == 6
