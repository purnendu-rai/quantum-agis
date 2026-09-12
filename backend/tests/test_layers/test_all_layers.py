"""Contract and behaviour tests for the security layer stack.

Covers the shared BaseLayer envelope (JSON-serialisability) and behaviour of
every implemented layer: 0 (QGM), 1 (HIS), 2 (NHGS), 3 (TCP), 4 (MVS) and
5 (BTFE).
"""

import json
import math
from datetime import datetime

import numpy as np
import pytest

from app.core.constants import HAMMING_THRESHOLD, LAYER_WEIGHTS
from app.core.quantum_state import QuantumState
from app.layers import (
    BTFELayer,
    HISLayer,
    MVSLayer,
    NHGSLayer,
    QGMLayer,
    TCPLayer,
)
from app.layers.base_layer import RESULT_KEYS, STATUS_FAIL, STATUS_PASS, STATUS_SUSPICIOUS
from app.layers.layer0_qgm import GENOME_PARAMS, QGMLayer as QGM
from app.layers.layer1_his import HOM_BASELINE, HOM_FORGERY_MAX
from app.layers.layer2_nhgs import (
    NHGS_SHIFT_PASS_MAX,
    NHGS_SHIFT_SUSPICIOUS_MAX,
)
from app.layers.layer3_tcp import (
    REPLAY_LINEWIDTH_FACTOR,
    REPLAY_RISK_FAIL,
    REPLAY_RISK_SUSPICIOUS,
    WALK_GENUINE_MIN,
)
from app.layers.layer4_mvs import MVS_FORGERY_MAX, MVS_MATCH_THRESHOLD


def _forged_genome(seed: int = 7) -> np.ndarray:
    """Build an unrelated device genome from an independent RNG.

    Args:
        seed: Seed for the forged genome generator.

    Returns:
        A 100-dimensional genome sampled from the same physical ranges.
    """
    rng = np.random.default_rng(seed)
    return np.concatenate(
        [rng.uniform(low, high, 10) for low, high, _unit in GENOME_PARAMS.values()]
    )


# ===================================================================== #
#  BaseLayer contract
# ===================================================================== #
@pytest.mark.parametrize(
    "layer_builder", [QGMLayer, HISLayer, NHGSLayer, TCPLayer, MVSLayer, BTFELayer]
)
def test_envelope_has_exactly_the_spec_keys(layer_builder):
    """process() returns the six-key envelope required by the contract."""
    result = layer_builder().process({})
    assert set(result.keys()) == set(RESULT_KEYS)


@pytest.mark.parametrize(
    "layer_builder", [QGMLayer, HISLayer, NHGSLayer, TCPLayer, MVSLayer, BTFELayer]
)
def test_envelope_is_json_serialisable(layer_builder):
    """Every layer output round-trips through json.dumps."""
    result = layer_builder().process({"forged": True} if layer_builder is HISLayer else {})
    parsed = json.loads(json.dumps(result))
    assert parsed["layer_id"] == result["layer_id"]
    assert parsed["metrics"] == result["metrics"]


@pytest.mark.parametrize(
    "layer_builder", [QGMLayer, HISLayer, NHGSLayer, TCPLayer, MVSLayer, BTFELayer]
)
def test_timestamp_is_parseable_iso_utc(layer_builder):
    """The envelope timestamp parses as ISO-8601 and carries timezone info."""
    result = layer_builder().process({})
    parsed = datetime.fromisoformat(result["timestamp"])
    assert parsed.tzinfo is not None


def test_layer_identities_and_weights_match_constants():
    """Layer id/name/weight agree with the registry in core.constants."""
    for layer in (QGMLayer(), HISLayer(), NHGSLayer(), TCPLayer(), MVSLayer(), BTFELayer()):
        assert 0 <= layer.layer_id <= 5
        assert layer.weight == LAYER_WEIGHTS[layer.layer_name]


def test_layer_ids_unique():
    """No two layers share the same layer_id."""
    layers = [QGMLayer(), HISLayer(), NHGSLayer(), TCPLayer(), MVSLayer(), BTFELayer()]
    ids = [layer.layer_id for layer in layers]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("layer_cls", [NHGSLayer, TCPLayer, MVSLayer])
def test_layers_2_to_4_process_empty_payload(layer_cls):
    """Layers 2-4 run to completion on an empty payload and stay clean."""
    result = layer_cls().process({})
    assert set(result.keys()) == set(RESULT_KEYS)
    assert result["status"] == STATUS_PASS
    assert result["deviation_score"] == 0.0


# ===================================================================== #
#  Layer 0 — QGM (Quantum Genome Mapping)
# ===================================================================== #
class TestQGM:
    """Genome generation, Hamming distance, and Monte Carlo verification."""

    def test_genome_shape_and_ranges(self):
        """The genome has 100 entries, all within their physical ranges."""
        genome = QGM.generate_genome("device-A")
        assert genome.shape == (100,)
        for index, (_name, (low, high, _unit)) in enumerate(GENOME_PARAMS.items()):
            block = genome[index * 10 : (index + 1) * 10]
            assert block.min() >= low
            assert block.max() <= high

    def test_genome_is_deterministic_per_device(self):
        """The same device id always yields the identical genome."""
        assert np.array_equal(QGM.generate_genome("device-A"), QGM.generate_genome("device-A"))

    def test_different_devices_have_different_genomes(self):
        """Unrelated devices land ~0.5 Hamming distance apart."""
        genome_a = QGM.generate_genome("device-A")
        genome_b = QGM.generate_genome("device-B")
        distance = QGM.compute_hamming_distance(genome_a, genome_b)
        assert 0.35 < distance < 0.65

    def test_hamming_distance_of_identical_genomes_is_zero(self):
        """A genome compared with itself has Hamming distance 0."""
        genome = QGM.generate_genome("device-A")
        assert QGM.compute_hamming_distance(genome, genome.copy()) == 0.0

    def test_hamming_distance_rejects_wrong_dimension(self):
        """compute_hamming_distance raises on malformed genomes."""
        with pytest.raises(ValueError):
            QGM.compute_hamming_distance(np.zeros(50), np.zeros(50))

    def test_verify_genuine_genome_passes(self):
        """The enrolled device's own genome verifies as PASS."""
        layer = QGMLayer()
        verdict = layer.verify_genome(layer.enrolled_genome.copy())
        assert verdict["status"] == STATUS_PASS
        assert verdict["matched"] is True
        assert verdict["hamming_distance"] <= HAMMING_THRESHOLD
        assert verdict["monte_carlo_trials"] > 0

    def test_verify_forged_genome_fails(self):
        """An unrelated genome lands near 0.5 and is rejected."""
        layer = QGMLayer()
        verdict = layer.verify_genome(_forged_genome())
        assert verdict["status"] == STATUS_FAIL
        assert verdict["matched"] is False
        assert verdict["hamming_distance"] > 0.25

    def test_process_genuine_device_envelope(self):
        """process() with no claimed genome treats the device as genuine."""
        result = QGMLayer().process({"device_id": "device-A"})
        assert result["layer_id"] == 0
        assert result["layer_name"] == "QGM"
        assert result["status"] == STATUS_PASS
        assert result["deviation_score"] <= HAMMING_THRESHOLD
        assert result["metrics"]["matched"] is True

    def test_process_with_claimed_genuine_genome(self):
        """An explicit genuine claim still passes after Monte Carlo noise."""
        layer = QGMLayer(device_id="device-A")
        result = layer.process({"claimed_genome": layer.enrolled_genome.tolist()})
        assert result["status"] == STATUS_PASS

    def test_process_with_forged_genome(self):
        """A forged claimed genome produces a FAIL envelope."""
        result = QGMLayer().process({"claimed_genome": _forged_genome().tolist()})
        assert result["status"] == STATUS_FAIL
        assert result["deviation_score"] > 0.25

    def test_process_re_enrols_new_device_id(self):
        """Supplying a new device_id re-enrols and accepts that device."""
        layer = QGMLayer(device_id="device-A")
        new_genome = QGM.generate_genome("device-B")
        result = layer.process({"device_id": "device-B", "claimed_genome": new_genome.tolist()})
        assert result["status"] == STATUS_PASS
        assert layer.device_id == "device-B"


# ===================================================================== #
#  Layer 1 — HIS (HOM Interferometry Sentinel)
# ===================================================================== #
class TestHIS:
    """Photon simulation, visibility physics, and forgery detection."""

    @staticmethod
    def _manual_packet(t: np.ndarray, center: float, sigma: float) -> np.ndarray:
        """Build a normalised Gaussian wavepacket on the given grid.

        Args:
            t: Time grid.
            center: Packet centre.
            sigma: Temporal width.

        Returns:
            Real amplitude array with unit L2-weighted norm.
        """
        return (1.0 / (2.0 * np.pi * sigma**2)) ** 0.25 * np.exp(
            -((t - center) ** 2) / (4.0 * sigma**2)
        )

    def test_simulated_pair_shape_and_norm(self):
        """Photon pairs share one grid and each integrate to unit norm."""
        psi_1, psi_2 = HISLayer.simulate_photon_pair(1.0)
        assert psi_1.shape == psi_2.shape == (512,)
        dt = 16.0 / 511.0  # grid spacing for sigma=1 over [-8, 8]
        assert np.isclose(np.trapezoid(np.abs(psi_1) ** 2, dx=dt), 1.0, atol=1e-6)
        assert np.isclose(np.trapezoid(np.abs(psi_2) ** 2, dx=dt), 1.0, atol=1e-6)

    def test_visibility_identical_photons_hits_baseline(self):
        """Indistinguishable photons give V within the 0.98 +/- 0.02 band."""
        psi_1, psi_2 = HISLayer.simulate_photon_pair(1.0)
        visibility = HISLayer.compute_hom_visibility(psi_1, psi_2)
        assert abs(visibility - HOM_BASELINE) <= 0.02

    def test_visibility_of_same_array_with_itself(self):
        """A wavepacket interfering with itself yields the eta ceiling."""
        psi = self._manual_packet(np.linspace(-8, 8, 512), 0.0, 1.0)
        visibility = HISLayer.compute_hom_visibility(psi, psi)
        assert np.isclose(visibility, 0.98, atol=1e-3)

    def test_visibility_disjoint_photons_below_forgery_cutoff(self):
        """Spectrally displaced photons cannot reproduce the dip."""
        psi_1, psi_2 = HISLayer.simulate_photon_pair(1.0, distinguishable=True)
        visibility = HISLayer.compute_hom_visibility(psi_1, psi_2)
        assert visibility < HOM_FORGERY_MAX

    def test_visibility_partial_offset_lands_in_suspicious_band(self):
        """A one-sigma offset degrades V into the SUSPICIOUS band."""
        t = np.linspace(-8, 8, 512)
        psi_1 = self._manual_packet(t, 0.0, 1.0)
        psi_2 = self._manual_packet(t, 1.0, 1.0)
        visibility = HISLayer.compute_hom_visibility(psi_1, psi_2)
        assert 0.5 <= visibility < 0.96

    def test_visibility_two_sigma_offset_is_forgery(self):
        """A two-sigma offset falls below the forgery cutoff."""
        t = np.linspace(-8, 8, 512)
        psi_1 = self._manual_packet(t, 0.0, 1.0)
        psi_2 = self._manual_packet(t, 2.0, 1.0)
        visibility = HISLayer.compute_hom_visibility(psi_1, psi_2)
        assert visibility < HOM_FORGERY_MAX

    def test_phase_shift_healthy_history_is_zero(self):
        """A history at the baseline reports no drift."""
        assert HISLayer.compute_phase_shift([0.98, 0.975, 0.985]) < 1e-9

    def test_phase_shift_detects_degradation(self):
        """A declining visibility history produces a positive drift."""
        drift = HISLayer.compute_phase_shift([0.90, 0.85])
        assert drift > 0.1

    def test_phase_shift_empty_history(self):
        """An empty history reports zero drift."""
        assert HISLayer.compute_phase_shift([]) == 0.0

    def test_process_legitimate_exchange_passes(self):
        """A genuine HOM exchange produces a PASS envelope."""
        result = HISLayer().process({})
        assert result["layer_id"] == 1
        assert result["layer_name"] == "HIS"
        assert result["status"] == STATUS_PASS
        assert result["metrics"]["hom_visibility"] >= 0.96
        assert result["metrics"]["within_baseline_band"] is True

    def test_process_forged_exchange_fails(self):
        """A forged photon source produces a FAIL envelope."""
        result = HISLayer().process({"forged": True})
        assert result["status"] == STATUS_FAIL
        assert result["metrics"]["hom_visibility"] < HOM_FORGERY_MAX
        assert result["deviation_score"] > 0.4

    def test_process_records_visibility_history(self):
        """process() appends each visibility to the internal history."""
        layer = HISLayer()
        layer.process({})
        layer.process({"forged": True})
        assert len(layer.visibility_history) == 2
        assert layer.visibility_history[1] < layer.visibility_history[0]


# ===================================================================== #
#  Layer 5 — BTFE (Bayesian Trust Fusion Engine)
# ===================================================================== #
class TestBTFE:
    """Trust fusion, Chernoff bound, and decision thresholds."""

    def test_trust_score_all_clean_layers_is_one(self):
        """Zero deviations everywhere fuse to T = 1.0."""
        deviations = {name: 0.0 for name in LAYER_WEIGHTS}
        assert BTFELayer.compute_trust_score(deviations) == 1.0

    def test_trust_score_formula_exact(self):
        """T = 1 - sum(w_i d_i) holds exactly for partial inputs."""
        assert np.isclose(BTFELayer.compute_trust_score({"QGM": 0.2}), 0.95)
        deviations = {"QGM": 0.2, "HIS": 0.2, "NHGS": 0.2, "TCP": 0.2, "MVS": 0.2, "BTFE": 0.2}
        assert np.isclose(BTFELayer.compute_trust_score(deviations), 0.80)

    def test_trust_score_ignores_unknown_layers(self):
        """Unknown layer names contribute no penalty."""
        assert BTFELayer.compute_trust_score({"UNKNOWN": 1.0}) == 1.0

    def test_trust_score_clamped_to_zero(self):
        """All-max deviations floor the score at 0.0."""
        deviations = {name: 1.0 for name in LAYER_WEIGHTS}
        assert BTFELayer.compute_trust_score(deviations) == 0.0

    def test_chernoff_bound_value(self):
        """The Hoeffding bound 2 exp(-2 n eps^2) is computed exactly."""
        assert np.isclose(BTFELayer.chernoff_bound(100, 0.1), 2.0 * np.exp(-2.0))

    def test_chernoff_bound_capped_at_one(self):
        """Small-sample bounds are capped at 1."""
        assert BTFELayer.chernoff_bound(1, 0.0) == 1.0
        assert BTFELayer.chernoff_bound(1, 0.1) == 1.0

    def test_chernoff_bound_decreases_with_samples(self):
        """More samples tighten the bound monotonically."""
        assert BTFELayer.chernoff_bound(10, 0.2) < BTFELayer.chernoff_bound(5, 0.2)

    def test_chernoff_bound_validates_inputs(self):
        """Invalid sample counts and negative epsilon raise ValueError."""
        with pytest.raises(ValueError):
            BTFELayer.chernoff_bound(0, 0.1)
        with pytest.raises(ValueError):
            BTFELayer.chernoff_bound(10, -0.1)

    @pytest.mark.parametrize(
        "score, expected",
        [
            (1.0, "ACCEPT"),
            (0.96, "ACCEPT"),
            (0.95, "QUARANTINE"),   # boundary: ACCEPT needs strictly > 0.95
            (0.92, "QUARANTINE"),
            (0.90, "QUARANTINE"),   # boundary: REJECT needs strictly < 0.90
            (0.89, "REJECT"),
            (0.0, "REJECT"),
        ],
    )
    def test_decision_thresholds(self, score, expected):
        """The ACCEPT/QUARANTINE/REJECT boundaries match the spec."""
        assert BTFELayer.make_decision(score) == expected

    def test_process_fuses_clean_layers_to_accept(self):
        """All-clean layer results fuse to ACCEPT / PASS."""
        layer_results = [
            {"layer_name": name, "deviation_score": 0.0}
            for name in ("QGM", "HIS", "NHGS", "TCP", "MVS")
        ]
        result = BTFELayer().process({"layer_results": layer_results})
        assert result["layer_id"] == 5
        assert result["status"] == STATUS_PASS
        assert result["metrics"]["decision"] == "ACCEPT"
        assert result["metrics"]["trust_score"] == 1.0
        assert result["deviation_score"] == 0.0

    def test_process_fuses_attack_to_reject(self):
        """Heavy deviations fuse below 0.90 and are REJECTED."""
        layer_results = [
            {"layer_name": "QGM", "deviation_score": 0.5},
            {"layer_name": "HIS", "deviation_score": 0.5},
            {"layer_name": "NHGS", "deviation_score": 0.5},
        ]
        result = BTFELayer().process({"layer_results": layer_results})
        # T = 1 - (0.25 + 0.25 + 0.20) * 0.5 = 0.65 < 0.90
        assert result["metrics"]["decision"] == "REJECT"
        assert result["status"] == STATUS_FAIL
        assert result["metrics"]["trust_score"] < 0.90

    def test_process_moderate_deviation_quarantines(self):
        """A mid-range score lands in the QUARANTINE / SUSPICIOUS band."""
        layer_results = [{"layer_name": "QGM", "deviation_score": 0.24}]
        result = BTFELayer().process({"layer_results": layer_results})
        # T = 1 - 0.25 * 0.24 = 0.94 -> QUARANTINE
        assert result["metrics"]["decision"] == "QUARANTINE"
        assert result["status"] == STATUS_SUSPICIOUS

    def test_process_end_to_end_with_real_layer_outputs(self):
        """The envelope chain QGM -> HIS -> BTFE fuses correctly."""
        qgm_result = QGMLayer().process({})
        his_result = HISLayer().process({})
        btfe_result = BTFELayer().process({"layer_results": [qgm_result, his_result]})
        assert btfe_result["metrics"]["trust_score"] > 0.95
        assert btfe_result["metrics"]["decision"] == "ACCEPT"
        assert btfe_result["metrics"]["num_layers"] == 2
        json.dumps(btfe_result)  # must not raise

# ===================================================================== #
#  Layer 2 — NHGS (Non-Hermitian Ghost Sensor)
# ===================================================================== #
class TestNHGS:
    """PT-lattice construction, exceptional points, and spectral tamper checks."""

    def test_construct_lattice_shape_and_pt_diagonal(self):
        """The default lattice is a 4x4 matrix with alternating imaginary gain."""
        lattice = NHGSLayer.construct_lattice(4, 0.5, -0.5)
        assert lattice.shape == (4, 4)
        assert np.iscomplexobj(lattice)
        diag = np.diag(lattice)
        assert np.allclose(np.real(diag), 0.0)
        assert np.allclose(np.imag(diag), [0.5, -0.5, 0.5, -0.5])

    def test_construct_lattice_hopped_and_symmetric_off_diagonal(self):
        """Nearest-neighbour hopping couples adjacent sites symmetrically."""
        lattice = NHGSLayer.construct_lattice(3, 0.5, -0.5)
        assert np.allclose(lattice[0, 1], 1.0)
        assert np.allclose(lattice[1, 0], 1.0)
        assert np.allclose(lattice[0, 2], 0.0)

    def test_zero_gain_lattice_is_hermitian(self):
        """Without gain/loss the lattice is a real symmetric (Hermitian) chain."""
        lattice = NHGSLayer.construct_lattice(4, 0.0, 0.0)
        assert np.allclose(lattice, lattice.conj().T)

    def test_compute_eigenvalues_default_lattice_all_real(self):
        """Below the exceptional point the PT-lattice spectrum stays real."""
        spectrum = NHGSLayer.compute_eigenvalues(NHGSLayer.construct_lattice(4, 0.5, -0.5))
        assert spectrum.shape == (4,)
        assert np.all(np.abs(spectrum.imag) < 1e-8)

    def test_find_exceptional_points_at_dimer_ep(self):
        """At the exceptional point the two eigenvalues coalesce to one pair."""
        spectrum = NHGSLayer.compute_eigenvalues(NHGSLayer.construct_lattice(2, 1.0, -1.0))
        assert NHGSLayer.find_exceptional_points(spectrum) == [(0, 1)]

    def test_find_exceptional_points_empty_for_default_lattice(self):
        """The healthy lattice shows no coalesced eigenvalue pairs."""
        spectrum = NHGSLayer.compute_eigenvalues(NHGSLayer.construct_lattice(4, 0.5, -0.5))
        assert NHGSLayer.find_exceptional_points(spectrum) == []

    def test_detect_spectral_shift_identical_spectra_zero(self):
        """A spectrum compared with itself yields zero shift."""
        assert NHGSLayer.detect_spectral_shift(
            NHGSLayer.BASELINE_SPECTRUM, NHGSLayer.BASELINE_SPECTRUM
        ) == pytest.approx(0.0)

    def test_detect_spectral_shift_grows_past_ep(self):
        """Driving the lattice beyond its EP pushes the shift well above a half."""
        baseline = NHGSLayer.compute_eigenvalues(NHGSLayer.construct_lattice(4, 0.5, -0.5))
        beyond = NHGSLayer.compute_eigenvalues(NHGSLayer.construct_lattice(4, 1.0, -1.0))
        assert NHGSLayer.detect_spectral_shift(baseline, beyond) > 0.5

    def test_detect_spectral_shift_rejects_mismatched_dimensions(self):
        """Different-size spectra cannot be compared."""
        with pytest.raises(ValueError):
            NHGSLayer.detect_spectral_shift([1j, 2j], [1j])

    def test_process_default_passes(self):
        """The enrolled device reproduces the baseline spectrum exactly."""
        result = NHGSLayer().process({})
        assert result["layer_id"] == 2
        assert result["layer_name"] == "NHGS"
        assert result["status"] == STATUS_PASS
        assert result["deviation_score"] == 0.0
        assert result["metrics"]["spectral_shift"] == 0.0

    def test_process_tampered_fails(self):
        """Seeded channel noise drives the spectrum past the FAIL band."""
        result = NHGSLayer().process({"tampered": True})
        assert result["status"] == STATUS_FAIL
        assert result["metrics"]["spectral_shift"] > NHGS_SHIFT_SUSPICIOUS_MAX

    def test_process_past_ep_fails_with_broken_modes(self):
        """Excess gain crosses the exceptional point and creates ghost modes."""
        result = NHGSLayer().process({"gain": 1.0, "loss": -1.0})
        assert result["status"] == STATUS_FAIL
        assert result["metrics"]["broken_modes"] == 2

    def test_process_small_gain_drift_is_suspicious(self):
        """A mild detuning sits inside the SUSPICIOUS shift band."""
        result = NHGSLayer().process({"gain": 0.3, "loss": -0.3})
        assert result["status"] == STATUS_SUSPICIOUS
        shift = result["metrics"]["spectral_shift"]
        assert NHGS_SHIFT_PASS_MAX < shift <= NHGS_SHIFT_SUSPICIOUS_MAX

# ===================================================================== #
#  Layer 3 — TCP (Temporal Coherence Profiler)
# ===================================================================== #
class TestTCP:
    """Coherence-time physics, quantum-walk verification, and replay checks."""

    def test_compute_coherence_length_defaults_to_baseline(self):
        """Empty statistics fall back to the class-level baseline constant."""
        assert TCPLayer.compute_coherence_length({}) == pytest.approx(TCPLayer.BASELINE_TAU_C)

    def test_compute_coherence_length_narrower_linewidth_gives_longer_tau(self):
        """Linewidth and coherence time are inversely related."""
        wide = TCPLayer.compute_coherence_length({"linewidth_m": 10e-12})
        narrow = TCPLayer.compute_coherence_length({"linewidth_m": 2.5e-12})
        assert narrow > wide

    def test_compute_coherence_length_scales_with_wavelength_squared(self):
        """Doubling the wavelength quadruples tau_c at fixed linewidth."""
        base = TCPLayer.compute_coherence_length(
            {"center_wavelength_m": 1550e-9, "linewidth_m": 5e-12}
        )
        doubled = TCPLayer.compute_coherence_length(
            {"center_wavelength_m": 2 * 1550e-9, "linewidth_m": 5e-12}
        )
        assert doubled == pytest.approx(4.0 * base)

    def test_compute_coherence_length_rejects_nonpositive_linewidth(self):
        """A zero linewidth is unphysical and rejected."""
        with pytest.raises(ValueError):
            TCPLayer.compute_coherence_length({"linewidth_m": 0.0})

    def test_quantum_walk_uses_sqrt_n_steps(self):
        """The walk cost stays O(sqrt(N)) with floor(sqrt(N)) default steps."""
        result = TCPLayer.quantum_walk_verify({"positions": 1024})
        assert result["steps"] == 32
        assert result["positions"] == 1024
        assert result["genuine_quantum"] is True
        assert result["walk_score"] == 1.0

    def test_quantum_walk_pure_spread_is_superlinear(self):
        """A coherent walker's spread beats the diffusive sqrt(steps) scaling."""
        result = TCPLayer.quantum_walk_verify({"positions": 256})
        assert result["spread_std"] > 1.5 * math.sqrt(result["steps"])

    def test_quantum_walk_decoherent_is_detected(self):
        """A decohered walker scores below the genuine threshold."""
        result = TCPLayer.quantum_walk_verify({"positions": 256, "decoherent": True})
        assert result["genuine_quantum"] is False
        assert result["walk_score"] < WALK_GENUINE_MIN
        assert result["spread_std"] < result["expected_quantum_std"]

    def test_quantum_walk_distribution_is_normalised(self):
        """The observed distribution is a valid probability mass over positions."""
        result = TCPLayer.quantum_walk_verify({"positions": 64})
        assert len(result["distribution"]) == 64
        assert sum(result["distribution"]) == pytest.approx(1.0, abs=1e-9)

    def test_quantum_walk_accepts_explicit_steps(self):
        """Callers may override the O(sqrt(N)) step budget."""
        result = TCPLayer.quantum_walk_verify({"positions": 64}, steps=5)
        assert result["steps"] == 5

    def test_quantum_walk_accepts_amplitude_state(self):
        """A flat (2, N) amplitude array seeds the walker directly."""
        result = TCPLayer.quantum_walk_verify([1.0, 0.0, 0.0, 0.0], steps=1)
        assert result["positions"] == 2
        assert result["genuine_quantum"] is True
        assert sum(result["distribution"]) == pytest.approx(1.0, abs=1e-9)

    def test_check_replay_within_3_sigma_is_zero(self):
        """Tau_c inside the 3-sigma band contributes no replay risk."""
        tau = TCPLayer.BASELINE_TAU_C
        history = [tau, tau * 1.001, tau * 0.999]
        assert TCPLayer.check_replay(tau * 1.0001, None, history) == 0.0

    def test_check_replay_outlier_exceeds_fail_band(self):
        """A replayed (out-of-family) tau_c exceeds the FAIL threshold."""
        tau = TCPLayer.BASELINE_TAU_C
        risk = TCPLayer.check_replay(tau / REPLAY_LINEWIDTH_FACTOR, None, [tau] * 3)
        assert risk >= REPLAY_RISK_FAIL

    def test_check_replay_empty_history_has_no_risk(self):
        """Without a historical profile nothing can be flagged."""
        assert TCPLayer.check_replay(1e-6, None, []) == 0.0

    def test_check_replay_stale_timestamp_is_flagged(self):
        """An exchange carrying a timestamp older than history is suspicious."""
        history = [{"coherence_length": 1.0, "timestamp": "2026-09-12T12:00:00Z"}]
        risk = TCPLayer.check_replay(1.0, "2026-09-12T09:00:00Z", history)
        assert risk > 0.0

    def test_process_default_passes(self):
            """The enrolled source matches the baseline profile exactly."""
            result = TCPLayer().process({})
            assert result["layer_id"] == 3
            assert result["layer_name"] == "TCP"
            assert result["status"] == STATUS_PASS
            assert result["metrics"]["replay_risk"] == 0.0
            assert result["metrics"]["genuine_quantum_walk"] is True
            assert result["metrics"]["coherence_time_s"] == pytest.approx(TCPLayer.BASELINE_TAU_C)

    def test_process_replay_fails(self):
            """A simulated replay signature leaves the 3-sigma family and fails."""
            result = TCPLayer().process({"replay": True})
            assert result["status"] == STATUS_FAIL
            assert result["metrics"]["replay_risk"] >= REPLAY_RISK_FAIL
            assert result["deviation_score"] > 0.4

    def test_process_stale_timestamp_fails(self):
            """A stale timestamp against a timestamped history triggers a replay FAIL."""
            result = TCPLayer().process(
                {
                    "timestamp": "2026-09-12T09:00:00Z",
                    "history": [
                        {
                            "coherence_length": TCPLayer.BASELINE_TAU_C,
                            "timestamp": "2026-09-12T12:00:00Z",
                        }
                    ],
                }
            )
            assert result["status"] == STATUS_FAIL
            assert result["metrics"]["replay_risk"] > 0.0

    def test_process_decoherent_channel_suspicious(self):
            """Channel decoherence degrades the walk below the genuine threshold."""
            result = TCPLayer().process({"decoherent": True})
            assert result["status"] == STATUS_SUSPICIOUS
            assert result["metrics"]["genuine_quantum_walk"] is False

    def test_process_accepts_explicit_coherence_length(self):
            """An explicit tau_c at the baseline still passes."""
            result = TCPLayer().process({"coherence_length": TCPLayer.BASELINE_TAU_C})
            assert result["status"] == STATUS_PASS
            assert result["metrics"]["coherence_time_s"] == pytest.approx(TCPLayer.BASELINE_TAU_C)

    def test_process_custom_history_extends_baseline(self):
            """User-supplied history drives the historical mean metric."""
            tau = TCPLayer.BASELINE_TAU_C
            result = TCPLayer().process({"history": [tau, tau]})
            assert result["status"] == STATUS_PASS
            assert result["metrics"]["historical_mean"] == pytest.approx(tau)

# ===================================================================== #
#  Layer 4 — MVS (MDI-QDS Verification Shield)
# ===================================================================== #
class TestMVS:
    """Pauli corrections, projective measurements, and MDI signature checks."""

    def test_apply_pauli_correction_x_flips_qubit(self):
        """X corrects |0> into |1> with unit fidelity."""
        flipped = MVSLayer.apply_pauli_correction(QuantumState([1.0, 0.0], num_qubits=1), "X")
        assert flipped.fidelity(QuantumState([0.0, 1.0], num_qubits=1)) > 0.999

    def test_apply_pauli_correction_identity_leaves_state(self):
        """The identity correction leaves the state untouched."""
        state = QuantumState([0.0, 1.0], num_qubits=1)
        assert MVSLayer.apply_pauli_correction(state, "I").fidelity(state) > 0.999

    def test_apply_pauli_correction_z_negates_phase(self):
        """Z negates the |1> amplitude without changing measurement outcomes."""
        zed = MVSLayer.apply_pauli_correction(QuantumState([0.0, 1.0], num_qubits=1), "Z")
        assert zed.amplitudes.tolist()[1] == pytest.approx(-1.0 + 0j)

    def test_apply_pauli_correction_rejects_unknown_label(self):
        """An unsupported correction label raises KeyError."""
        with pytest.raises(KeyError):
            MVSLayer.apply_pauli_correction(QuantumState([1.0, 0.0], num_qubits=1), "H")

    def test_projective_measurement_z_eigenstates_are_deterministic(self):
        """Z-basis eigenstates return their eigenvalue bit with unit probability."""
        zero_bit, p_zero = MVSLayer.projective_measurement(QuantumState([1.0, 0.0], num_qubits=1), "Z")
        one_bit, p_one = MVSLayer.projective_measurement(QuantumState([0.0, 1.0], num_qubits=1), "Z")
        assert zero_bit == 0 and p_zero == pytest.approx(1.0)
        assert one_bit == 1 and p_one == pytest.approx(1.0)

    def test_projective_measurement_x_eigenstates_are_deterministic(self):
        """X-basis eigenstates return their eigenvalue bit with unit probability."""
        plus_bit, p_plus = MVSLayer.projective_measurement(
            QuantumState([1.0 / math.sqrt(2), 1.0 / math.sqrt(2)], num_qubits=1), "X"
        )
        minus_bit, p_minus = MVSLayer.projective_measurement(
            QuantumState([1.0 / math.sqrt(2), -1.0 / math.sqrt(2)], num_qubits=1), "X"
        )
        assert plus_bit == 0 and p_plus == pytest.approx(1.0)
        assert minus_bit == 1 and p_minus == pytest.approx(1.0)

    def test_make_public_key_is_deterministic(self):
        """The same seed always produces the identical public key."""
        key_a = MVSLayer.make_public_key(length=32)
        key_b = MVSLayer.make_public_key(length=32)
        assert key_a["bases"] == key_b["bases"]
        assert key_a["expected"] == key_b["expected"]

    def test_mdi_verify_genuine_signature_passes(self):
        """A genuine signer saturates the corrected-bit match rate."""
        key = MVSLayer.make_public_key()
        signature = MVSLayer.generate_signature(key)
        verdict = MVSLayer.mdi_verify(signature, key)
        assert verdict["verified"] is True
        assert verdict["match_rate"] >= MVS_MATCH_THRESHOLD
        assert verdict["correct_events"] == verdict["kept_events"]

    def test_mdi_verify_forged_signature_rejected(self):
        """An unrelated signer lands near the random-guessing floor."""
        key = MVSLayer.make_public_key()
        signature = MVSLayer.generate_signature(key, forgery=True)
        verdict = MVSLayer.mdi_verify(signature, key)
        assert verdict["verified"] is False
        assert verdict["match_rate"] < MVS_FORGERY_MAX

    def test_mdi_verify_sifts_mismatched_bases(self):
        """Events in disagreeing bases are discarded rather than counted."""
        key = MVSLayer.make_public_key(length=64)
        signature = MVSLayer.generate_signature(key, seed_label=b"mvs-sift")
        verdict = MVSLayer.mdi_verify(signature, key)
        assert 0 < verdict["kept_events"] <= 64
        assert verdict["discarded_events"] > 0

    def test_mdi_verify_quantum_state_path(self):
        """Events carrying raw states verify through the unitary feed-forward."""
        key = MVSLayer.make_public_key(length=32)
        signature = MVSLayer.generate_signature(key, seed_label=b"mvs-quantum", include_states=True)
        verdict = MVSLayer.mdi_verify(signature, key)
        assert verdict["verified"] is True

    def test_mdi_verify_rejects_malformed_key(self):
        """A public key without the expected registers raises ValueError."""
        with pytest.raises(ValueError):
            MVSLayer.mdi_verify(MVSLayer.generate_signature(MVSLayer.make_public_key()), {})

    def test_process_default_passes(self):
            """The enrolled signer's matched signature passes at full agreement."""
            result = MVSLayer().process({})
            assert result["layer_id"] == 4
            assert result["layer_name"] == "MVS"
            assert result["status"] == STATUS_PASS
            assert result["metrics"]["match_rate"] == 1.0
            assert result["deviation_score"] == 0.0

    def test_process_forged_signature_fails(self):
            """A forged signature cannot satisfy the MDI match threshold."""
            result = MVSLayer().process({"forged": True})
            assert result["status"] == STATUS_FAIL
            assert result["metrics"]["match_rate"] < MVS_FORGERY_MAX
            assert result["deviation_score"] > 0.4

    def test_process_tampered_signature_suspicious(self):
            """Partial outcome corruption lands in the SUSPICIOUS band."""
            result = MVSLayer().process({"tampered": 0.25})
            assert result["status"] == STATUS_SUSPICIOUS
            assert 0.05 < result["deviation_score"] < 0.4

    def test_process_accepts_explicit_public_key(self):
            """A caller-supplied key and genuine signature still verify."""
            key = MVSLayer.make_public_key(length=32, device_id="caller-device")
            signature = MVSLayer.generate_signature(key, seed_label=b"mvs-caller")
            result = MVSLayer().process({"signature": signature, "public_key": key})
            assert result["status"] == STATUS_PASS
            assert result["metrics"]["device_id"] == "caller-device"
