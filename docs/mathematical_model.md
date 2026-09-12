# Mathematical Model

## 1. Layer 0 — QGM (Quantum Genome Mapping)

Each device is fingerprinted by a **100-dimensional genome** g ∈ ℝ¹⁰⁰: ten
samples of each of ten physical parameters (laser jitter, phase noise,
polarization dispersion, spectral width, temporal coherence, amplitude
fluctuation, phase drift, quantum efficiency, dark-count rate, afterpulsing),
drawn uniformly from realistic hardware ranges.

Genomes are compared by **normalised Hamming distance** on the bit string
obtained by thresholding each parameter at its range midpoint:

    d_H(g_a, g_b) = (1/100) · Σ_k [ bit(g_a[k]) ≠ bit(g_b[k]) ]

Verification runs N = 64 Monte-Carlo trials adding 1%-of-range Gaussian
sensor noise; the decision uses the mean distance d̄_H:

- d̄_H ≤ 0.05 (HAMMING_THRESHOLD) → genuine
- d̄_H > 0.25 → forged (unrelated devices score ≈ 0.5)

## 2. Layer 1 — HIS (HOM Interferometry Sentinel)

Two single-photon wavepackets ψ₁, ψ₂ (normalised Gaussians on a time grid)
interfere at a beam splitter. The **Hong-Ou-Mandel visibility** is

    V_HOM = η · ∫ |ψ₁(t) ψ₂(t)|² dt / sqrt( ∫|ψ₁|⁴ dt · ∫|ψ₂|⁴ dt )

with detector efficiency η = 0.98. Identical photons give V = η; a spectral
offset Δ makes the overlap decay like exp(−Δ²/8σ²). Classification:
V ≥ 0.96 genuine, 0.5 ≤ V < 0.96 suspicious, V < 0.5 forged.

Channel drift: `phase_shift = max(0, 0.98 − mean(V_history))`.

## 3. Layer 2 — NHGS (Non-Hermitian Ghost Sensor)

A PT-symmetric tight-binding lattice with alternating on-site gain/loss
(+iγ, −iλ) and hopping κ:

    H[k,k] = iγ (even k), −iλ (odd k);  H[k,k±1] = κ

At γ = λ the lattice sits at an **exceptional point** where eigenvalue pairs
coalesce. Channel tampering (seeded complex noise) moves the spectrum; the
detection signal is the normalised mean eigenvalue displacement

    shift = mean|λ_current − λ_baseline| / mean|λ_baseline|

## 4. Layer 3 — TCP (Temporal Coherence Profiler)

Coherence time of a Lorentzian source: `τ_c = λ² / (c · Δλ)`. Replays present
an out-of-family τ_c; the risk score ramps from 0 inside the **3σ band**
around the historical mean to 1 as the excess reaches 0.15·mean. Timestamp
staleness (> 60 s behind the newest history entry) contributes the same way.

A discrete-time **Hadamard-coin quantum walk** on a 256-site ring provides a
coherence witness: the ballistic spread (std ≈ steps/√2) of a coherent walker
is compared with the diffusive random-walk reference; `walk_score` is their
ratio. The walk costs O(√N) steps for an N-site lattice.

## 5. Layer 4 — MVS (MDI-QDS Verification Shield)

A signature is 512 measurement events `{basis, outcome, correction}`. The
untrusted node's reported outcome b_raw maps to the canonical bit via the
Pauli feed-forward parity: b = b_raw ⊕ [correction ∈ {X, Y}]. Events whose
basis disagrees with the public-key register are sifted out (~2/3 kept). The
**match rate** m = correct/kept must exceed 0.95; forged (random-guess)
signatures sit at the 0.5 floor. Deviation = 1 − m.

## 6. Layer 5 — BTFE (Bayesian Trust Fusion Engine)

Weighted fusion of the sensor deviations dᵢ:

    T = 1 − Σᵢ wᵢ dᵢ,   Σ wᵢ = 1
    (w_QGM, w_HIS, w_NHGS, w_TCP, w_MVS, w_BTFE) = (0.25, 0.25, 0.20, 0.15, 0.10, 0.05)

Decision bands: T > 0.95 → **ACCEPT**, T < 0.90 → **REJECT**, else
**QUARANTINE**. The statistical confidence of the fusion over n independent
layer estimates is bounded by the **Chernoff/Hoeffding inequality**:

    P[|T̂ − T| ≥ ε] ≤ 2 · exp(−2 n ε²)

## 7. Quantum teleportation (checkpoint primitive)

The Layer-3 certification primitive teleports |ψ⟩ through a Bell pair
|Φ⁺⟩ = (|00⟩+|11⟩)/√2 via CNOT ⊗ H on the message register, a joint
computational measurement, and the classical correction X^{m₂} Z^{m₁}. Bob's
conditional post-measurement state equals |ψ⟩ exactly; verification uses the
Uhlmann fidelity F = (Tr √(√ρ₁ ρ₂ √ρ₁))² and the Bures distance
D_B = √(2(1 − √F)).
