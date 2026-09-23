/**
 * @file Premium trust-score gauge: gradient SVG arc animated with Framer
 * Motion, counting number, orbiting electron dots, rotating outer ring, and
 * a pulsing glow that matches the decision band. Live via the Zustand store.
 */
import { motion } from "framer-motion";
import { useStore } from "../../store/useStore.js";
import Badge from "../common/Badge.jsx";
import AnimatedNumber from "../animations/AnimatedNumber.jsx";
import GlassCard from "../common/GlassCard.jsx";

const RADIUS = 96;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Band lookup: colors, gradient stops, decision label. */
const BANDS = {
  accept: {
    from: "#00ff88",
    to: "#00f0ff",
    color: "#00ff88",
    glow: "rgba(0, 255, 136, 0.35)",
    label: "ACCEPT",
    variant: "pass",
  },
  quarantine: {
    from: "#ffb800",
    to: "#ff8800",
    color: "#ffb800",
    glow: "rgba(255, 184, 0, 0.35)",
    label: "QUARANTINE",
    variant: "suspicious",
  },
  reject: {
    from: "#ff3366",
    to: "#ff00ff",
    color: "#ff3366",
    glow: "rgba(255, 51, 102, 0.35)",
    label: "REJECT",
    variant: "fail",
  },
};

/**
 * Resolve the decision band for a trust score.
 * @param {number} value - Trust score in [0, 1].
 * @returns {{key: string, config: object}} Band key and config.
 */
function bandFor(value) {
  if (value > 0.95) return { key: "accept", config: BANDS.accept };
  if (value < 0.9) return { key: "reject", config: BANDS.reject };
  return { key: "quarantine", config: BANDS.quarantine };
}

/**
 * Live trust-score gauge (store-driven, 600ms ease-out animation).
 * @param {object} props - Component props.
 * @param {number} [props.value] - Optional explicit override of the store value.
 * @returns {JSX.Element} Animated gauge card.
 */
export default function TrustScoreGauge({ value }) {
  const storeTrust = useStore((state) => state.trustScore);
  const raw = typeof value === "number" ? value : storeTrust;
  const trustScore = Math.min(1, Math.max(0, typeof raw === "number" && !Number.isNaN(raw) ? raw : 0));

  const { key: bandKey, config: band } = bandFor(trustScore);
  const targetOffset = CIRCUMFERENCE * (1 - trustScore);

  return (
    <GlassCard
      title="TRUST SCORE"
      accent={band.color}
      className="overflow-visible"
    >
      <div className="relative flex items-center justify-center py-2">
        {/* Pulsing glow behind the gauge */}
        <motion.div
          aria-hidden="true"
          className="absolute rounded-full"
          style={{ width: 190, height: 190 }}
          animate={{ boxShadow: [`0 0 40px 8px ${band.glow}`, `0 0 70px 14px ${band.glow}`] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />

        {/* Rotating outer decorative ring */}
        <svg
          aria-hidden="true"
          className="animate-spin-slow absolute"
          width={240}
          height={240}
          viewBox="0 0 240 240"
        >
          <circle
            cx="120"
            cy="120"
            r="114"
            fill="none"
            stroke="rgba(0, 240, 255, 0.25)"
            strokeWidth="1"
            strokeDasharray="3 9"
          />
        </svg>

        {/* Orbiting electron dots */}
        {[10, 14, 18].map((duration, index) => (
          <div
            key={duration}
            aria-hidden="true"
            className="pointer-events-none absolute"
            style={{ width: 240, height: 240, animation: `spin ${duration}s linear infinite` }}
          >
            <div
              className="absolute rounded-full"
              style={{
                width: 6 - index,
                height: 6 - index,
                top: 10 + index * 3,
                left: "50%",
                marginLeft: -2,
                background: index % 2 === 0 ? "#00f0ff" : "#a855f7",
                boxShadow: `0 0 8px ${index % 2 === 0 ? "#00f0ff" : "#a855f7"}`,
              }}
            />
          </div>
        ))}

        {/* Main gauge arc with gradient stroke */}
        <svg width={240} height={240} viewBox="0 0 240 240" className="relative">
          <defs>
            <linearGradient id={`gauge-grad-${bandKey}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={band.from} />
              <stop offset="100%" stopColor={band.to} />
            </linearGradient>
          </defs>
          <circle
            cx="120"
            cy="120"
            r={RADIUS}
            fill="none"
            stroke="#1e293b"
            strokeWidth="14"
          />
          <motion.circle
            cx="120"
            cy="120"
            r={RADIUS}
            fill="none"
            stroke={`url(#gauge-grad-${bandKey})`}
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            initial={{ strokeDashoffset: CIRCUMFERENCE }}
            animate={{ strokeDashoffset: targetOffset }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            transform="rotate(-90 120 120)"
          />
        </svg>

        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs font-bold tracking-[0.2em] uppercase text-slate-300">
            TRUST SCORE
          </span>
          <AnimatedNumber
            value={trustScore * 100}
            decimals={1}
            suffix="%"
            className="font-data tabular-nums text-4xl font-extrabold tracking-tight text-white drop-shadow-[0_0_16px_rgba(0,240,255,0.35)]"
          />
          <span className="font-data tabular-nums mt-1 text-xs font-semibold text-slate-400">
            BTFE Fusion: {trustScore.toFixed(4)}
          </span>
        </div>
      </div>

      <div className="mt-1 flex justify-center">
        <Badge label={`DECISION: ${band.label}`} variant={band.variant} />
      </div>
    </GlassCard>
  );
}
