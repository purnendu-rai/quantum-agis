"""Tests for the verification engine: orchestration, trust score, and decisions.

Covers the three engine modules:
- VerificationEngine: six-layer orchestration with asyncio parallelism,
  per-layer crash isolation, and stateless repeatability;
- TrustScoreCalculator: weighted deviation fusion and the Chernoff bound;
- DecisionEngine: threshold policy and non-blocking audit logging.
"""

import asyncio
import inspect
import json
import logging
import math

import pytest

from app.core.constants import (
    LAYER_WEIGHTS,
    TRUST_ACCEPT,
    TRUST_REJECT,
    W_HIS,
    W_MVS,
    W_QGM,
    W_TCP,
)
from app.engine.decision_engine import DecisionEngine
from app.engine.trust_score import TrustScoreCalculator, TrustScoreEngine
from app.engine.verification_engine import VerificationEngine, get_engine
from app.layers.base_layer import BaseLayer
from app.layers.layer0_qgm import QGMLayer
from app.layers.layer1_his import HISLayer
from app.layers.layer2_nhgs import NHGSLayer
from app.layers.layer3_tcp import TCPLayer
from app.layers.layer4_mvs import MVSLayer
from app.layers.layer5_btfe import (
    BTFELayer,
    DECISION_ACCEPT,
    DECISION_QUARANTINE,
    DECISION_REJECT,
)
from app.models.enums import Decision, Verdict

_ENVELOPE_KEYS = {"layer_id", "layer_name", "status", "deviation_score", "metrics", "timestamp"}


class _CrashingLayer(BaseLayer):
    """Sensor stub that always raises, used to exercise failure isolation."""

    def __init__(self) -> None:
        super().__init__(layer_id=1, layer_name="HIS", weight=W_HIS)

    def process(self, input_data: dict) -> dict:
        raise RuntimeError("sensor exploded")


class TestVerificationEngineOrchestration:
    """Async pipeline: parallel sensors -> BTFE fusion -> trust + decision."""

    @pytest.mark.asyncio
    async def test_genuine_input_accepted(self):
        result = await VerificationEngine().verify({})
        assert result["decision"] == DECISION_ACCEPT
        assert result["verdict"] == Verdict.AUTHENTIC.value
        assert result["api_decision"] == Decision.ACCEPT.value
        assert result["trust_score"] == pytest.approx(0.999, abs=2e-3)

    @pytest.mark.asyncio
    async def test_forged_input_rejected(self):
        result = await VerificationEngine().verify({"forged": True})
        assert result["decision"] == DECISION_REJECT
        assert result["verdict"] == Verdict.REJECTED.value
        assert result["api_decision"] == Decision.REJECT.value
        # HIS deviation ~0.982 and MVS ~0.5 -> trust ~0.70 << 0.90.
        assert result["trust_score"] < TRUST_REJECT - 0.05
        assert result["deviations"]["HIS"] > 0.9

    @pytest.mark.asyncio
    async def test_replay_input_rejected(self):
        result = await VerificationEngine().verify({"replay": True})
        assert result["decision"] == DECISION_REJECT
        assert result["deviations"]["TCP"] == 1.0

    @pytest.mark.asyncio
    async def test_tampered_input_rejected(self):
        result = await VerificationEngine().verify({"tampered": True})
        assert result["decision"] == DECISION_REJECT
        assert result["deviations"]["NHGS"] > 0.3
        assert result["deviations"]["MVS"] > 0.2

    @pytest.mark.asyncio
    async def test_coherent_attack_scores_lowest(self):
        engine = VerificationEngine()
        coherent = await engine.verify({"forged": True, "tampered": True, "replay": True})
        single = await engine.verify({"forged": True})
        assert coherent["trust_score"] < single["trust_score"] < TRUST_REJECT

    @pytest.mark.asyncio
    async def test_all_six_layers_reported_in_order(self):
        result = await VerificationEngine().verify({})
        assert result["num_layers"] == 6
        assert [item["layer_id"] for item in result["layer_results"]] == [0, 1, 2, 3, 4, 5]
        assert [item["layer_name"] for item in result["layer_results"]] == [
            "QGM",
            "HIS",
            "NHGS",
            "TCP",
            "MVS",
            "BTFE",
        ]

    @pytest.mark.asyncio
    async def test_layer_results_are_valid_envelopes(self):
        result = await VerificationEngine().verify({"forged": True})
        for item in result["layer_results"]:
            assert _ENVELOPE_KEYS <= set(item)
            assert 0.0 <= item["deviation_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_btfe_receives_all_sensor_envelopes(self):
        result = await VerificationEngine().verify({"forged": True})
        fused = result["layer_results"][-1]["metrics"]["fused_layers"]
        assert sorted(fused) == ["HIS", "MVS", "NHGS", "QGM", "TCP"]

    @pytest.mark.asyncio
    async def test_engine_trust_matches_btfe_fusion(self):
        result = await VerificationEngine().verify({"replay": True})
        fusion = result["layer_results"][-1]
        assert result["trust_score"] == pytest.approx(fusion["metrics"]["trust_score"])
        assert result["decision"] == fusion["metrics"]["decision"]

    @pytest.mark.asyncio
    async def test_deviations_cover_all_five_sensors(self):
        result = await VerificationEngine().verify({})
        assert set(result["deviations"]) == {"QGM", "HIS", "NHGS", "TCP", "MVS"}
        assert all(0.0 <= value <= 1.0 for value in result["deviations"].values())

    @pytest.mark.asyncio
    async def test_none_payload_treated_as_genuine(self):
        result = await VerificationEngine().verify(None)
        assert result["decision"] == DECISION_ACCEPT

    @pytest.mark.asyncio
    async def test_session_id_echoed_when_present(self):
        result = await VerificationEngine().verify({"session_id": "sess-42"})
        assert result["session_id"] == "sess-42"

    @pytest.mark.asyncio
    async def test_result_is_json_serialisable(self):
        result = await VerificationEngine().verify({"forged": True, "replay": True})
        assert json.loads(json.dumps(result))["decision"] == DECISION_REJECT

    @pytest.mark.asyncio
    async def test_chernoff_bound_present_and_bounded(self):
        result = await VerificationEngine().verify({})
        assert 0.0 <= result["chernoff_bound"] <= 1.0


def _engine_with_crashing_his() -> VerificationEngine:
    """Return a default engine whose HIS sensor is replaced by a failing stub."""
    return VerificationEngine(
        layers=[
            QGMLayer(),
            _CrashingLayer(),
            NHGSLayer(),
            TCPLayer(),
            MVSLayer(),
            BTFELayer(),
        ]
    )


class TestEngineFailureIsolationAndStatelessness:
    """A crashed sensor must never stall the pipeline; repeats stay identical."""

    @pytest.mark.asyncio
    async def test_crashed_sensor_becomes_fail_envelope(self):
        result = await _engine_with_crashing_his().verify({})
        his = next(item for item in result["layer_results"] if item["layer_name"] == "HIS")
        assert his["status"] == "FAIL"
        assert his["deviation_score"] == 1.0
        assert "sensor exploded" in his["metrics"]["error"]

    @pytest.mark.asyncio
    async def test_pipeline_completes_despite_crash(self):
        result = await _engine_with_crashing_his().verify({})
        assert result["num_layers"] == 6
        assert result["decision"] in {DECISION_ACCEPT, DECISION_QUARANTINE, DECISION_REJECT}

    @pytest.mark.asyncio
    async def test_crashed_sensor_drives_full_penalty(self):
        result = await _engine_with_crashing_his().verify({})
        assert result["deviations"]["HIS"] == 1.0
        assert result["decision"] != DECISION_ACCEPT

    @pytest.mark.asyncio
    async def test_repeated_verifications_are_identical(self):
        engine = VerificationEngine()
        payload = {"forged": True, "tampered": True}
        first = await engine.verify(payload)
        second = await engine.verify(payload)
        assert first["trust_score"] == second["trust_score"]
        assert first["deviations"] == second["deviations"]
        assert first["decision"] == second["decision"]

    @pytest.mark.asyncio
    async def test_engine_stateless_between_requests(self):
        engine = VerificationEngine()
        attack = await engine.verify({"forged": True})
        genuine = await engine.verify({})
        assert attack["decision"] == DECISION_REJECT
        assert genuine["decision"] == DECISION_ACCEPT
        assert genuine["trust_score"] > 0.99
        assert all(len(layer._history) == 0 for layer in engine.layers)

    @pytest.mark.asyncio
    async def test_concurrent_verifications_are_independent(self):
        engine = VerificationEngine()
        results = await asyncio.gather(
            engine.verify({}),
            engine.verify({"forged": True}),
            engine.verify({"replay": True}),
            engine.verify({}),
        )
        assert results[0]["decision"] == DECISION_ACCEPT
        assert results[1]["decision"] == DECISION_REJECT
        assert results[2]["decision"] == DECISION_REJECT
        assert results[3]["decision"] == DECISION_ACCEPT
        assert results[0]["trust_score"] == results[3]["trust_score"]

    @pytest.mark.asyncio
    async def test_sensor_layers_run_off_event_loop(self, monkeypatch):
        # All layer.process calls must be dispatched via asyncio.to_thread.
        from app.engine import verification_engine as module

        dispatched = []
        real_to_thread = asyncio.to_thread

        async def spy_to_thread(func, *args, **kwargs):
            dispatched.append(func.__self__ if hasattr(func, "__self__") else func)
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(module.asyncio, "to_thread", spy_to_thread)
        await module.VerificationEngine().verify({})
        assert len(dispatched) == 6  # 5 sensors + fusion, none on the loop


class TestTrustScoreCalculator:
    """Weighted fusion T = 1 - sum(w_i * d_i) plus the Chernoff bound."""

    def test_default_weights_match_framework_constants(self):
        calculator = TrustScoreCalculator()
        assert calculator.weights == LAYER_WEIGHTS
        assert calculator.weights["QGM"] == W_QGM == 0.25
        assert calculator.weights["HIS"] == W_HIS == 0.25
        assert calculator.weights["TCP"] == W_TCP == 0.15
        assert calculator.weights["MVS"] == W_MVS == 0.10
        assert pytest.approx(sum(calculator.weights.values())) == 1.0

    def test_custom_weights_are_stored(self):
        calculator = TrustScoreCalculator(weights={"QGM": 0.6, "HIS": 0.4})
        assert calculator.weights == {"QGM": 0.6, "HIS": 0.4}

    def test_perfectly_clean_layers_score_one(self):
        deviations = {"QGM": 0.0, "HIS": 0.0, "NHGS": 0.0, "TCP": 0.0, "MVS": 0.0}
        assert TrustScoreCalculator().compute(deviations) == 1.0

    def test_fully_deviated_layers_score_zero(self):
        deviations = {name: 1.0 for name in LAYER_WEIGHTS}
        assert TrustScoreCalculator().compute(deviations) == 0.0

    def test_weighted_fusion_matches_hand_computation(self):
        deviations = {"HIS": 0.8, "MVS": 0.5}
        expected = 1.0 - (0.25 * 0.8 + 0.10 * 0.5)
        assert TrustScoreCalculator().compute(deviations) == pytest.approx(expected)

    @pytest.mark.asyncio
    async def test_calculator_reproduces_engine_fusion(self):
        engine = VerificationEngine()
        result = await engine.verify({"forged": True, "replay": True})
        assert TrustScoreCalculator().compute(result["deviations"]) == pytest.approx(
            result["trust_score"]
        )

    def test_unknown_layer_names_are_ignored(self):
        calculator = TrustScoreCalculator()
        assert calculator.compute({"UNKNOWN": 1.0, "HIS": 0.0}) == 1.0

    def test_missing_layers_contribute_no_penalty(self):
        calculator = TrustScoreCalculator()
        assert calculator.compute({"TCP": 1.0}) == pytest.approx(1.0 - W_TCP)

    def test_none_deviation_is_ignored(self):
        calculator = TrustScoreCalculator()
        assert calculator.compute({"HIS": None, "TCP": 0.0}) == 1.0

    def test_result_is_clamped_into_unit_interval(self):
        calculator = TrustScoreCalculator()
        assert calculator.compute({}) == 1.0
        assert calculator.compute({"QGM": 5.0}) == 0.0

    def test_scores_are_deterministic(self):
        calculator = TrustScoreCalculator()
        deviations = {"HIS": 0.3, "NHGS": 0.4}
        assert calculator.compute(deviations) == calculator.compute(dict(deviations))

    def test_chernoff_bound_decreases_with_more_samples(self):
        calculator = TrustScoreCalculator()
        assert calculator.compute_chernoff_bound(10, 0.1) > calculator.compute_chernoff_bound(100, 0.1)

    def test_chernoff_bound_decreases_with_stricter_epsilon(self):
        calculator = TrustScoreCalculator()
        assert calculator.compute_chernoff_bound(50, 0.05) > calculator.compute_chernoff_bound(50, 0.2)

    def test_chernoff_bound_matches_closed_form(self):
        calculator = TrustScoreCalculator()
        expected = 2.0 * math.exp(-2.0 * 100 * 0.1 ** 2)
        assert calculator.compute_chernoff_bound(100, 0.1) == pytest.approx(expected)

    def test_chernoff_bound_is_capped_at_one(self):
        calculator = TrustScoreCalculator()
        assert calculator.compute_chernoff_bound(1, 0.0) == 1.0

    @pytest.mark.parametrize("num_samples,epsilon", [(0, 0.1), (-3, 0.1), (10, -0.5)])
    def test_chernoff_bound_rejects_invalid_inputs(self, num_samples, epsilon):
        with pytest.raises(ValueError):
            TrustScoreCalculator().compute_chernoff_bound(num_samples, epsilon)

    def test_breakdown_returns_weighted_contributions(self):
        calculator = TrustScoreCalculator()
        breakdown = calculator.breakdown({"HIS": 0.8, "TCP": 1.0, "UNKNOWN": 0.9})
        assert breakdown == {
            "HIS": pytest.approx(0.25 * 0.8),
            "TCP": pytest.approx(0.15),
        }

    def test_weights_copy_shields_against_caller_mutation(self):
        custom = {"QGM": 1.0}
        calculator = TrustScoreCalculator(weights=custom)
        custom["QGM"] = 0.0
        assert calculator.weights["QGM"] == 1.0

    def test_legacy_engine_alias_points_to_calculator(self):
        assert TrustScoreEngine is TrustScoreCalculator


class TestDecisionEngine:
    """Threshold policy: ACCEPT above 0.95, REJECT below 0.90, else QUARANTINE."""

    def test_default_thresholds_match_framework_constants(self):
        engine = DecisionEngine()
        assert engine.accept_threshold == TRUST_ACCEPT == 0.95
        assert engine.reject_threshold == TRUST_REJECT == 0.90

    def test_custom_thresholds_are_stored(self):
        engine = DecisionEngine(accept_threshold=0.8, reject_threshold=0.5)
        assert engine.accept_threshold == 0.8
        assert engine.reject_threshold == 0.5

    def test_scores_above_accept_threshold_are_accepted(self):
        engine = DecisionEngine()
        assert engine.decide(0.96) == DECISION_ACCEPT
        assert engine.decide(1.0) == DECISION_ACCEPT

    def test_scores_below_reject_threshold_are_rejected(self):
        engine = DecisionEngine()
        assert engine.decide(0.89) == DECISION_REJECT
        assert engine.decide(0.0) == DECISION_REJECT

    def test_in_between_band_quarantines(self):
        engine = DecisionEngine()
        assert engine.decide(0.90) == DECISION_QUARANTINE
        assert engine.decide(0.925) == DECISION_QUARANTINE
        assert engine.decide(0.95) == DECISION_QUARANTINE

    def test_threshold_boundaries_use_strict_inequality(self):
        engine = DecisionEngine()
        assert engine.decide(engine.accept_threshold) == DECISION_QUARANTINE
        assert engine.decide(engine.reject_threshold) == DECISION_QUARANTINE

    @pytest.mark.parametrize("accept,reject", [(0.4, 0.6), (1.5, 0.5), (-0.1, 0.5)])
    def test_invalid_thresholds_rejected(self, accept, reject):
        with pytest.raises(ValueError):
            DecisionEngine(accept_threshold=accept, reject_threshold=reject)

    def test_log_decision_accept_logs_info(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.engine.decision"):
            DecisionEngine().log_decision(DECISION_ACCEPT, 0.99, {"HIS": 0.0})
        assert caplog.records[-1].levelno == logging.INFO
        assert "ACCEPT" in caplog.records[-1].getMessage()

    def test_log_decision_reject_logs_error(self, caplog):
        with caplog.at_level(logging.ERROR, logger="app.engine.decision"):
            DecisionEngine().log_decision(DECISION_REJECT, 0.5, {"HIS": 0.98})
        assert caplog.records[-1].levelno == logging.ERROR

    def test_log_decision_quarantine_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="app.engine.decision"):
            DecisionEngine().log_decision(DECISION_QUARANTINE, 0.92, {})
        assert caplog.records[-1].levelno == logging.WARNING

    def test_log_decision_handles_missing_deviations(self, caplog):
        with caplog.at_level(logging.INFO, logger="app.engine.decision"):
            DecisionEngine().log_decision(DECISION_ACCEPT, 1.0, None)
        assert "deviations={}" in caplog.records[-1].getMessage()

    def test_log_decision_never_blocks_or_writes_files(self, tmp_path, monkeypatch):
        # Patch open() to fail: logging must not touch the filesystem.
        def _boom(*args, **kwargs):
            raise AssertionError("log_decision must not perform file I/O")

        monkeypatch.setattr("builtins.open", _boom)
        DecisionEngine().log_decision(DECISION_ACCEPT, 0.99, {})  # must not raise


def test_app_boot():
    """FastAPI app object is importable and correctly titled."""
    from app.main import app

    assert app.title == "QUANTUM-AGIS"


class TestEngineConstruction:
    """Engine wiring: the full stack is instantiated synchronously at startup."""

    def test_engine_instantiates_all_six_layers(self):
        engine = VerificationEngine()
        assert [type(layer) for layer in engine.layers] == [
            QGMLayer,
            HISLayer,
            NHGSLayer,
            TCPLayer,
            MVSLayer,
            BTFELayer,
        ]

    def test_layers_carry_expected_identity_and_order(self):
        engine = VerificationEngine()
        assert [layer.layer_id for layer in engine.layers] == [0, 1, 2, 3, 4, 5]
        assert [layer.layer_name for layer in engine.layers] == [
            "QGM",
            "HIS",
            "NHGS",
            "TCP",
            "MVS",
            "BTFE",
        ]

    def test_sensor_and_fusion_partition(self):
        engine = VerificationEngine()
        assert [layer.layer_name for layer in engine.sensor_layers] == [
            "QGM",
            "HIS",
            "NHGS",
            "TCP",
            "MVS",
        ]
        assert isinstance(engine.fusion_layer, BTFELayer)

    def test_verify_is_a_coroutine_function(self):
        assert inspect.iscoroutinefunction(VerificationEngine.verify)

    def test_register_layer_appends(self):
        engine = VerificationEngine()
        extra = QGMLayer()
        engine.register_layer(extra)
        assert engine.layers[-1] is extra

    def test_custom_layer_stack_is_accepted(self):
        engine = _engine_with_crashing_his()
        assert type(engine.layers[1]) is _CrashingLayer
        assert isinstance(engine.fusion_layer, BTFELayer)

    def test_get_engine_returns_singleton(self):
        first = get_engine()
        second = get_engine()
        assert first is second
        assert isinstance(first, VerificationEngine)
        assert len(first.layers) == 6

    def test_engines_are_independent_instances(self):
        one = VerificationEngine()
        two = VerificationEngine()
        assert one is not two
        assert one.layers[0] is not two.layers[0]
