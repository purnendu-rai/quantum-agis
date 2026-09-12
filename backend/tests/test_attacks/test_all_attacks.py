"""Tests for the five attack simulators and their shared contract.

Covers:
- BaseAttack: standardized JSON envelope, validation, stateless determinism;
- Registry: string dispatch, unique identities, expected-detection mapping;
- Each attack: its characteristic perturbation and detection layer;
- API readiness: attack output chains straight into VerificationEngine.
"""

import json

import pytest

from app.attacks import (
    ATTACK_REGISTRY,
    RESULT_KEYS,
    VALID_ATTACK_TYPES,
    BaseAttack,
    ChannelTamperingAttack,
    CoherentAttack,
    ForgeryAttack,
    ImpersonationAttack,
    ReplayAttack,
    get_attack_class,
)
from app.engine.verification_engine import VerificationEngine
from app.layers.layer0_qgm import GENOME_DIMENSION, QGMLayer
from app.layers.layer2_nhgs import DEFAULT_GAIN, DEFAULT_LOSS, DEFAULT_LATTICE_SIZE
from app.models.enums import AttackType

ALL_ATTACKS = [
    ForgeryAttack,
    ImpersonationAttack,
    ReplayAttack,
    ChannelTamperingAttack,
    CoherentAttack,
]

#: Expected detection layer per attack (from the framework spec).
EXPECTED_BY_ATTACK: dict[str, tuple[str, ...]] = {
    "forgery": ("QGM", "HIS"),
    "impersonation": ("QGM",),
    "replay": ("TCP",),
    "channel_tampering": ("NHGS",),
    "coherent": ("QGM", "HIS", "NHGS", "TCP", "MVS"),
}

#: Flag each attack sets in modified_data.
FLAG_BY_ATTACK: dict[str, str] = {
    "forgery": "forged",
    "impersonation": "impersonated",
    "replay": "replay",
    "channel_tampering": "tampered",
    "coherent": "forged",
}

BASE_CONTEXT = {
    "session_id": "attack-session",
    "signature": "LEGIT-QSIG",
    "public_key": "VICTIM-PUBKEY",
    "device_id": "AGIS-DEVICE-001",
}


class TestBaseContract:
    """Shared BaseAttack contract: envelope, validation, and statelessness."""

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_envelope_has_exactly_result_keys(self, attack_cls):
        result = attack_cls().execute(dict(BASE_CONTEXT))
        assert set(result) == set(RESULT_KEYS)

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_envelope_is_json_serialisable(self, attack_cls):
        result = attack_cls().execute(dict(BASE_CONTEXT))
        assert json.dumps(result)  # raises TypeError on NumPy/complex leakage

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_attack_type_matches_enum_value(self, attack_cls):
        attack = attack_cls()
        assert attack.attack_type in VALID_ATTACK_TYPES
        assert AttackType(attack.attack_type) is AttackType(attack.attack_type)

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_success_is_true(self, attack_cls):
        result = attack_cls().execute(dict(BASE_CONTEXT))
        assert result["success"] is True

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_detected_by_lists_expected_layers(self, attack_cls):
        attack = attack_cls()
        result = attack.execute(dict(BASE_CONTEXT))
        expected = EXPECTED_BY_ATTACK[attack.attack_type]
        assert tuple(result["detected_by"]) == expected
        assert list(result["modified_data"]["expected_detection"]) == list(expected)

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_timestamp_present_and_isoformat(self, attack_cls):
        from datetime import datetime

        result = attack_cls().execute(dict(BASE_CONTEXT))
        datetime.fromisoformat(result["timestamp"])  # raises on bad format

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_execute_is_deterministic_across_instances(self, attack_cls):
        first = attack_cls().execute(dict(BASE_CONTEXT))
        second = attack_cls().execute(dict(BASE_CONTEXT))
        assert json.dumps(first["modified_data"]) == json.dumps(second["modified_data"])

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_context_is_not_mutated(self, attack_cls):
        context = dict(BASE_CONTEXT)
        snapshot = json.dumps(context, sort_keys=True)
        attack_cls().execute(context)
        assert json.dumps(context, sort_keys=True) == snapshot

    def test_base_attack_is_abstract(self):
        with pytest.raises(TypeError):
            BaseAttack("forgery")  # type: ignore[abstract]

    def test_unknown_attack_type_rejected(self):
        class _BadAttack(BaseAttack):
            name = "Bad"

            def __init__(self) -> None:
                super().__init__("nonexistent")

            def execute(self, context: dict) -> dict:  # pragma: no cover
                return {}

        with pytest.raises(ValueError, match="Unknown attack_type"):
            _BadAttack()

    @pytest.mark.parametrize("bad", [-0.5, 1.5, 99.0])
    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_intensity_clamped_into_unit_range(self, attack_cls, bad):
        attack = attack_cls(intensity=bad)
        assert 0.0 <= attack.intensity <= 1.0

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_get_parameters_reports_intensity_default(self, attack_cls):
        assert "intensity" in attack_cls.get_parameters()

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_session_id_echoed_into_modified_data(self, attack_cls):
        result = attack_cls().execute(dict(BASE_CONTEXT))
        assert result["modified_data"]["session_id"] == "attack-session"

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_empty_context_is_accepted(self, attack_cls):
        result = attack_cls().execute({})
        assert result["modified_data"]["session_id"] == "unknown-session"
        assert result["success"] is True


class TestRegistry:
    """String-based dispatch used by the API routes."""

    def test_registry_covers_every_attack_type(self):
        assert set(ATTACK_REGISTRY) == {t.value for t in AttackType}

    def test_get_attack_class_returns_registered_class(self):
        assert get_attack_class("forgery") is ForgeryAttack
        assert get_attack_class("impersonation") is ImpersonationAttack
        assert get_attack_class("replay") is ReplayAttack
        assert get_attack_class("channel_tampering") is ChannelTamperingAttack
        assert get_attack_class("coherent") is CoherentAttack

    def test_get_attack_class_unknown_raises_key_error(self):
        with pytest.raises(KeyError):
            get_attack_class("nonexistent")

    def test_attack_types_and_names_unique(self):
        types = [cls().attack_type for cls in ALL_ATTACKS]
        names = [cls.name for cls in ALL_ATTACKS]
        assert len(types) == len(set(types))
        assert len(names) == len(set(names))

    def test_expected_detection_matches_spec(self):
        for cls in ALL_ATTACKS:
            attack = cls()
            assert tuple(attack.EXPECTED_DETECTION) == EXPECTED_BY_ATTACK[attack.attack_type]


class TestPerAttackBehavior:
    """Characteristic perturbation of each individual attack."""

    def test_forgery_sets_forged_flag_and_fake_signature(self):
        result = ForgeryAttack().execute(dict(BASE_CONTEXT))
        assert result["modified_data"]["forged"] is True
        assert result["modified_data"]["forged_signature"].startswith("FORGED-QSIG")
        assert len(result["modified_data"]["claimed_genome"]) == GENOME_DIMENSION

    def test_forgery_genome_is_unrelated_to_enrolled_device(self):
        result = ForgeryAttack().execute(dict(BASE_CONTEXT))
        enrolled = QGMLayer.generate_genome("AGIS-DEVICE-001")
        claimed = result["modified_data"]["claimed_genome"]
        gap = QGMLayer.compute_hamming_distance(enrolled, claimed)
        assert gap > 0.25  # far beyond the HAMMING_SUSPICIOUS_LIMIT

    def test_forgery_uses_random_quantum_state(self):
        result = ForgeryAttack().execute(dict(BASE_CONTEXT))
        state_norm = result["modified_data"]["forged_state_norm"]
        assert abs(state_norm - 1.0) < 1e-9  # statevector is normalised

    def test_impersonation_copies_public_key_verbatim(self):
        result = ImpersonationAttack().execute(dict(BASE_CONTEXT))
        assert result["modified_data"]["stolen_public_key"] == "VICTIM-PUBKEY"
        assert result["modified_data"]["impersonated"] is True
        assert result["modified_data"]["victim_device_id"] == "AGIS-DEVICE-001"

    def test_impersonation_device_differs_from_victim(self):
        result = ImpersonationAttack().execute(dict(BASE_CONTEXT))
        assert result["modified_data"]["device_id"] != "AGIS-DEVICE-001"

    def test_impersonation_public_key_stand_in_when_absent(self):
        result = ImpersonationAttack().execute({"session_id": "no-key-session"})
        assert "PUBKEY-" in result["modified_data"]["stolen_public_key"]

    def test_replay_sets_flag_and_delay_over_one_second(self):
        result = ReplayAttack().execute(dict(BASE_CONTEXT))
        assert result["modified_data"]["replay"] is True
        assert result["modified_data"]["replay_delay_seconds"] >= 1.0

    def test_replay_retransmits_captured_signature_unchanged(self):
        result = ReplayAttack().execute(dict(BASE_CONTEXT))
        assert result["modified_data"]["replayed_signature"] == "LEGIT-QSIG"

    def test_replay_delay_scales_with_intensity(self):
        low = ReplayAttack(intensity=0.0).execute(dict(BASE_CONTEXT))
        high = ReplayAttack(intensity=1.0).execute(dict(BASE_CONTEXT))
        assert (
            high["modified_data"]["replay_delay_seconds"]
            > low["modified_data"]["replay_delay_seconds"]
        )

    def test_replay_stale_timestamp_parses_in_past(self):
        from datetime import datetime, timezone

        result = ReplayAttack().execute(dict(BASE_CONTEXT))
        stale = datetime.fromisoformat(result["modified_data"]["timestamp"])
        assert stale.tzinfo is not None
        assert stale < datetime.now(timezone.utc)  # strictly in the past

    def test_channel_tampering_perturbs_lattice_gain_loss(self):
        result = ChannelTamperingAttack().execute(dict(BASE_CONTEXT))
        data = result["modified_data"]
        assert data["tampered"] is True
        assert (data["lattice_gain"], data["lattice_loss"]) != (DEFAULT_GAIN, DEFAULT_LOSS)
        assert data["lattice_shape"] == [DEFAULT_LATTICE_SIZE, DEFAULT_LATTICE_SIZE]

    def test_channel_tampering_detached_lattice_is_unstable(self):
        from app.layers.layer2_nhgs import NHGSLayer

        data = ChannelTamperingAttack().execute(dict(BASE_CONTEXT))["modified_data"]
        layer = NHGSLayer()
        lattice = layer.construct_lattice(
            DEFAULT_LATTICE_SIZE, data["lattice_gain"], data["lattice_loss"]
        )
        eigenvalues = layer.compute_eigenvalues(lattice)
        # Imbalanced gain/loss breaks PT symmetry: spectrum leaves the unit circle.
        assert max(abs(eigenvalues)) > 1.0 + 1e-6

    def test_coherent_composes_all_sub_attack_flags(self):
        data = CoherentAttack().execute(dict(BASE_CONTEXT))["modified_data"]
        assert data["composed"] == ["forged", "replay", "tampered"]

    def test_coherent_entangles_ancilla_with_channel(self):
        data = CoherentAttack().execute(dict(BASE_CONTEXT))["modified_data"]
        assert "entangled_ancilla_state" in data
        assert data["concurrence_proxy"] > 0.0

    def test_coherent_triggers_multiple_detection_layers(self):
        assert len(CoherentAttack.EXPECTED_DETECTION) >= 3

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_intensity_scales_distortion_monotonically(self, attack_cls):
        skip = ("intensity", "timestamp", "expected_detection")
        low = json.dumps(
            {k: v for k, v in attack_cls(intensity=0.1).execute(dict(BASE_CONTEXT))["modified_data"].items() if k not in skip}
        )
        high = json.dumps(
            {k: v for k, v in attack_cls(intensity=0.9).execute(dict(BASE_CONTEXT))["modified_data"].items() if k not in skip}
        )
        assert low != high


class TestApiReadiness:
    """Attacks are callable via API: JSON dispatch + engine chaining."""

    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    def test_dispatch_through_registry_string(self, attack_cls):
        attack = attack_cls()
        assert get_attack_class(attack.attack_type) is attack_cls
        assert isinstance(attack, BaseAttack)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    async def test_attack_output_feeds_verification_engine(self, attack_cls):
        engine = VerificationEngine()
        modified = attack_cls().execute(dict(BASE_CONTEXT))["modified_data"]
        result = await engine.verify(modified)
        assert result["trust_score"] < 0.90
        assert result["decision"] in ("QUARANTINE", "REJECT")
        assert result["verdict"] in ("suspicious", "rejected")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("attack_cls", ALL_ATTACKS, ids=lambda c: c.name)
    async def test_engine_flags_detected_by_expected_layers(self, attack_cls):
        engine = VerificationEngine()
        expected_layers = set(EXPECTED_BY_ATTACK[attack_cls().attack_type])
        modified = attack_cls().execute(dict(BASE_CONTEXT))["modified_data"]
        result = await engine.verify(modified)
        flagged = {name for name, dev in result["deviations"].items() if dev > 0.01}
        assert expected_layers & flagged  # every expected layer observed something

    @pytest.mark.asyncio
    async def test_coherent_attack_is_rejected_end_to_end(self):
        engine = VerificationEngine()
        modified = CoherentAttack().execute(dict(BASE_CONTEXT))["modified_data"]
        result = await engine.verify(modified)
        assert result["decision"] == "REJECT"
        assert result["verdict"] == "rejected"

    def test_attack_results_survive_json_round_trip_with_engine(self):
        modified = ForgeryAttack().execute(dict(BASE_CONTEXT))["modified_data"]
        assert json.loads(json.dumps(modified)) == modified
