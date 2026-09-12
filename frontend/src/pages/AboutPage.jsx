/**
 * @file Project overview page: architecture, team, and references.
 */
import Card from '../components/common/Card.jsx';

const LAYERS = [
  { id: 0, code: 'QGM', name: 'Quantum Genome Mapping', detail: '100-dim device fingerprint, Hamming-distance verification' },
  { id: 1, code: 'HIS', name: 'HOM Interferometry Sentinel', detail: 'V_HOM two-photon interference, forgery cutoff 0.5' },
  { id: 2, code: 'NHGS', name: 'Non-Hermitian Ghost Sensor', detail: 'PT-lattice spectrum, exceptional-point drift detection' },
  { id: 3, code: 'TCP', name: 'Temporal Coherence Profiler', detail: 'Coherence-length profile + O(√N) quantum walk' },
  { id: 4, code: 'MVS', name: 'MDI-QDS Verification Shield', detail: 'Measurement-device-independent signature sifting' },
  { id: 5, code: 'BTFE', name: 'Bayesian Trust Fusion Engine', detail: 'T = 1 − Σ wᵢdᵢ, Chernoff confidence, ACCEPT/QUARANTINE/REJECT' },
];

/**
 * Project explainer for the AGIS framework.
 * @returns {JSX.Element} About page content.
 */
export default function AboutPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">About QUANTUM-AGIS</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-300">
          QUANTUM-AGIS (Quantum-inspired Agentic Governance &amp; Intrusion Shield) is a six-layer
          quantum-secured communication and threat-detection framework built for SIH 2026. Every
          transmission is verified by a stack of quantum checks — device genomes, Hong-Ou-Mandel
          interference, non-Hermitian spectral probes, teleportation-grade coherence profiling, and
          measurement-device-independent signature sifting — whose deviation scores are fused by a
          Bayesian engine into a single trust score and access decision.
        </p>
      </div>

      <Card title="Architecture" subtitle="Verification pipeline">
        <pre className="overflow-x-auto rounded bg-slate-950 p-4 text-[11px] leading-relaxed text-slate-300">
{`  Client signature
        │
        ▼
  ┌─────────────────────────────────────────────────────┐
  │  L0 QGM ─► L1 HIS ─► L2 NHGS ─► L3 TCP ─► L4 MVS    │
  │     (each layer emits status + deviation_score)     │
  └──────────────────────┬──────────────────────────────┘
                         ▼
              ┌─────────────────────┐
              │  L5 BTFE (fusion)   │   T = 1 − Σ wᵢ·dᵢ
              └──────────┬──────────┘
                         ▼
        T > 0.95 → ACCEPT   0.90–0.95 → QUARANTINE
        T < 0.90 → REJECT   (Chernoff bound on confidence)`}
        </pre>
      </Card>

      <Card title="Security Layers">
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {LAYERS.map((layer) => (
            <li
              key={layer.code}
              className="rounded border px-3 py-2"
              style={{ borderColor: 'rgba(0, 212, 255, 0.2)' }}
            >
              <span className="text-sm font-semibold text-quantum-blue">
                L{layer.id} {layer.code}
              </span>
              <span className="ml-2 text-xs text-slate-400">{layer.name}</span>
              <p className="mt-1 text-xs text-slate-500">{layer.detail}</p>
            </li>
          ))}
        </ul>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Tech Stack">
          <ul className="space-y-1 text-sm text-slate-300">
            <li>⚛️ Backend — Python 3.11+, FastAPI, NumPy/SciPy, WebSocket streaming</li>
            <li>🖥️ Frontend — React 19 + Vite, TailwindCSS, Recharts, Zustand</li>
            <li>☁️ Deployment — Render (backend), Vercel (frontend), Docker Compose</li>
            <li>🔒 Determinism — all simulation randomness seeded (seed = 42)</li>
          </ul>
        </Card>
        <Card title="Team & References">
          <p className="text-sm text-slate-300">
            <span className="text-slate-400">Team:</span> SIH 2026 — QUANTUM-AGIS team (add your
            members here).
          </p>
          <ul className="mt-2 space-y-1 text-xs text-slate-400">
            <li>• Hong, Ou &amp; Mandell (1987) — Measurement of subpicosecond time intervals by two-photon interference</li>
            <li>• Bender et al. — PT-symmetric quantum mechanics and exceptional points</li>
            <li>• Lo, Curty &amp; Qi (2012) — Measurement-device-independent quantum key distribution</li>
            <li>• Bennett &amp; Brassard (1984) — Quantum cryptography (BB84)</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
