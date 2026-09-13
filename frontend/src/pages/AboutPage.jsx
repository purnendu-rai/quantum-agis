/**
 * @file Project overview page: animated circuit hero, architecture flow,
 * hover-highlighted trust formula, team, and references.
 */
import { motion } from 'framer-motion';
import { ExternalLink } from 'lucide-react';
import GlassCard from '../components/common/GlassCard.jsx';

const LAYERS = [
  { id: 0, code: 'QGM', name: 'Quantum Genome Mapping', detail: '100-dim device fingerprint, Hamming-distance verification', color: '#00f0ff' },
  { id: 1, code: 'HIS', name: 'HOM Interferometry Sentinel', detail: 'V_HOM two-photon interference, forgery cutoff 0.5', color: '#0080ff' },
  { id: 2, code: 'NHGS', name: 'Non-Hermitian Ghost Sensor', detail: 'PT-lattice spectrum, exceptional-point drift detection', color: '#a855f7' },
  { id: 3, code: 'TCP', name: 'Temporal Coherence Profiler', detail: 'Coherence-length profile + O(√N) quantum walk', color: '#7c3aed' },
  { id: 4, code: 'MVS', name: 'MDI-QDS Verification Shield', detail: 'Measurement-device-independent signature sifting', color: '#ffd700' },
  { id: 5, code: 'BTFE', name: 'Bayesian Trust Fusion Engine', detail: 'T = 1 − Σ wᵢ·dᵢ, Chernoff confidence, ACCEPT/REJECT', color: '#00ff88' },
];

/** Formula terms with per-term explanation for hover highlight. */
const FORMULA_TERMS = [
  { tex: 'T', meaning: 'Trust score in [0, 1]' },
  { tex: '1 −', meaning: 'Deviation subtracts from perfect trust' },
  { tex: 'Σ', meaning: 'Weighted sum across all layers' },
  { tex: 'wᵢ', meaning: 'Layer weight (QGM 0.25 … BTFE 0.05)' },
  { tex: 'dᵢ', meaning: 'Layer deviation score in [0, 1]' },
];

/**
 * Project explainer for the AGIS framework.
 * @returns {JSX.Element} About page content.
 */
export default function AboutPage() {
  return (
    <div className="space-y-6">
      {/* Hero with animated quantum circuit */}
      <div className="relative overflow-hidden rounded-xl border border-white/10 bg-cosmos/50 p-6">
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 h-full w-full opacity-40"
          viewBox="0 0 800 200"
          preserveAspectRatio="xMidYMid slice"
        >
          {/* Quantum circuit wires with travelling dashes */}
          {[40, 90, 140].map((y, index) => (
            <motion.line
              key={y}
              x1="0"
              y1={y}
              x2="800"
              y2={y}
              stroke={index === 1 ? '#a855f7' : '#00f0ff'}
              strokeWidth="1"
              strokeDasharray="6 14"
              animate={{ strokeDashoffset: [0, -80] }}
              transition={{ duration: 2 + index * 0.6, repeat: Infinity, ease: 'linear' }}
            />
          ))}
          {/* Gates */}
          {[[120, 40], [260, 90], [420, 40], [420, 140], [580, 90], [700, 40]].map(([x, y], index) => (
            <rect
              key={index}
              x={x - 14}
              y={y - 14}
              width="28"
              height="28"
              rx="6"
              fill="rgba(0, 240, 255, 0.08)"
              stroke="#00f0ff"
              strokeWidth="1"
            />
          ))}
          <circle cx="260" cy="40" r="5" fill="#a855f7" />
          <line x1="260" y1="40" x2="260" y2="140" stroke="#a855f7" strokeWidth="1" />
          <circle cx="420" cy="140" r="5" fill="#00f0ff" />
        </svg>
        <div className="relative">
          <h1 className="text-2xl font-bold text-white">QUANTUM-AGIS</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-text-secondary">
            Quantum-inspired Agentic Governance &amp; Intrusion Shield — a six-layer
            quantum-secured communication and threat-detection framework built for
            SIH 2026. Signatures are verified by quantum measurement statistics —
            never machine learning — and fused into a single trust score.
          </p>
        </div>
      </div>

      {/* Animated trust formula */}
      <GlassCard title="The Trust Formula" subtitle="Hover each term to see what it means" accent="#00ff88">
        <div className="flex flex-wrap items-center justify-center gap-3 py-4 font-data text-2xl">
          {FORMULA_TERMS.map((term) => (
            <motion.div
              key={term.tex}
              className="group relative cursor-pointer rounded-lg border border-white/10 bg-white/5 px-4 py-2"
              whileHover={{ scale: 1.08 }}
            >
              <span className="text-quantum-cyan">{term.tex}</span>
              <span className="pointer-events-none absolute -top-9 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded border border-quantum-cyan/30 bg-cosmos px-2.5 py-1 text-[11px] font-sans text-slate-200 group-hover:block">
                {term.meaning}
              </span>
            </motion.div>
          ))}
        </div>
        <p className="mt-2 text-center text-xs text-slate-500">
          T &gt; 0.95 → ACCEPT · 0.90–0.95 → QUARANTINE · T &lt; 0.90 → REJECT · confidence bounded by 2e^(−2nε²)
        </p>
      </GlassCard>

      {/* Layer cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {LAYERS.map((layer) => (
          <motion.div
            key={layer.code}
            whileHover={{ y: -4 }}
            transition={{ type: 'spring', stiffness: 320, damping: 22 }}
            className="glass glass-hover relative overflow-hidden p-4"
            style={{ borderColor: `${layer.color}33` }}
          >
            <div className="text-sm font-bold" style={{ color: layer.color }}>
              L{layer.id} {layer.code}
            </div>
            <div className="text-xs text-slate-300">{layer.name}</div>
            <p className="mt-1 text-[11px] text-slate-500">{layer.detail}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <GlassCard title="Tech Stack" accent="#a855f7">
          <ul className="space-y-1.5 text-sm text-slate-300">
            <li>⚛️ Backend — Python 3.11+, FastAPI, NumPy/SciPy, WebSocket streaming</li>
            <li>🖥️ Frontend — React 19 + Vite, TailwindCSS, Recharts, Framer Motion, Zustand</li>
            <li>☁️ Deployment — Render (backend), Vercel (frontend), Docker Compose, GitHub Actions CI</li>
            <li>🔒 Determinism — seeded simulation (seed 42) with dynamic attack variance</li>
          </ul>
        </GlassCard>
        <GlassCard title="Team & References" accent="#ffd700">
          <p className="text-sm text-slate-300">
            <span className="text-slate-400">Team:</span> SIH 2026 — QUANTUM-AGIS team.
          </p>
          <ul className="mt-2 space-y-1 text-xs text-slate-400">
            <li>• Hong, Ou &amp; Mandell (1987) — two-photon interference</li>
            <li>• Bender et al. — PT-symmetric quantum mechanics, exceptional points</li>
            <li>• Lo, Curty &amp; Qi (2012) — measurement-device-independent QKD</li>
            <li>• Bennett &amp; Brassard (1984) — BB84</li>
          </ul>
          <a
            href="https://github.com/purnendu-rai/quantum-agis"
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex items-center gap-2 rounded border border-white/10 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-quantum-cyan/40 hover:text-white"
          >
            <ExternalLink size={13} /> github.com/purnendu-rai/quantum-agis
          </a>
        </GlassCard>
      </div>
    </div>
  );
}
