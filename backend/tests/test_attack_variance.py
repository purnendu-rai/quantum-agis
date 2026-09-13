"""Dynamic-attack tests: identical attacks must produce varying results.

The simulation is expected to show natural quantum-noise variance — the same
attack run repeatedly yields slightly different trust scores and intensities
while detection stays guaranteed.
"""

from __future__ import annotations

import statistics

import pytest

from app.api.routes.attacks import _ATTACK_PAYLOAD_FLAGS
from app.services.simulation_service import simulation_service


@pytest.mark.asyncio
async def test_repeated_coherent_attacks_vary_and_stay_detected():
    """Three identical coherent attacks give different trust scores, all REJECT."""
    scores: list[float] = []
    intensities: list[float] = []
    for _ in range(3):
        result = await simulation_service.run_attack(
            "coherent",
            {
                "signature": "AGIS-var",
                "session_id": "variance",
                "intensity": 0.60,
                **_ATTACK_PAYLOAD_FLAGS["coherent"],
            },
        )
        trust = float(result["trust_score"])
        scores.append(trust)
        intensities.append(float(result["intensity"]))
        assert result["decision"] in ("REJECT", "QUARANTINE"), (
            "variance must never flip a detected attack to ACCEPT"
        )

    assert len(set(scores)) == 3, f"trust scores identical across runs: {scores}"
    assert statistics.pstdev(scores) > 0.001, "trust scores show no variance"
    assert len(set(intensities)) == 3, f"intensities identical across runs: {intensities}"
    for intensity in intensities:
        assert 0.1 <= intensity <= 1.0


@pytest.mark.asyncio
@pytest.mark.parametrize("attack_type", ["forgery", "impersonation", "replay", "channel_tampering"])
async def test_every_attack_type_varies_and_stays_rejected(attack_type):
    """Two runs of each attack type differ, and both are rejected."""
    decisions: list[str] = []
    scores: list[float] = []
    for _ in range(2):
        result = await simulation_service.run_attack(
            attack_type,
            {
                "signature": "AGIS-var",
                "session_id": "variance",
                "intensity": 0.60,
                **_ATTACK_PAYLOAD_FLAGS[attack_type],
            },
        )
        decisions.append(result["decision"])
        scores.append(float(result["trust_score"]))

    assert all(d in ("REJECT", "QUARANTINE") for d in decisions)
    assert scores[0] != scores[1], f"{attack_type} produced identical trust twice: {scores}"


@pytest.mark.asyncio
async def test_legitimate_verification_stays_accepted_under_dynamic_seeds():
    """Dynamic seeds never push a legitimate signature out of ACCEPT."""
    for _ in range(5):
        result = await simulation_service.run_verification(
            {"signature": "AGIS-dynamic-legit", "session_id": "variance"}
        )
        assert result["decision"] == "ACCEPT"
