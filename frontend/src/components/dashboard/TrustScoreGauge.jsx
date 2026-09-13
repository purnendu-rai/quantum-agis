/**
 * @file Circular trust-score gauge (Recharts RadialBarChart) that updates
 * live from the Zustand store — the WebSocket stream re-seeds the store's
 * trust score every 500 ms, and the arc animates on every change.
 */
import { PolarAngleAxis, RadialBar, RadialBarChart } from "recharts";
import { useStore } from "../../store/useStore.js";
import Badge from "../common/Badge.jsx";
import Card from "../common/Card.jsx";

/**
 * Gauge color for a trust score.
 * @param {number} value - Trust score in [0, 1].
 * @returns {string} Hex color: green ACCEPT, orange QUARANTINE, red REJECT.
 */
function getColor(value) {
  if (value > 0.95) return "#00cc66";
  if (value >= 0.9) return "#ffaa00";
  return "#ff2244";
}

/**
 * Decision label for a trust score.
 * @param {number} value - Trust score in [0, 1].
 * @returns {{label: string, variant: string}} Decision and badge variant.
 */
function decisionFor(value) {
  if (value > 0.95) return { label: "ACCEPT", variant: "pass" };
  if (value < 0.9) return { label: "REJECT", variant: "fail" };
  return { label: "QUARANTINE", variant: "suspicious" };
}

/**
 * Live trust-score gauge. Reads straight from the Zustand store so every
 * WebSocket trust update animates the arc, the percentage, and the decision
 * badge together.
 *
 * @param {object} props - Component props.
 * @param {number} [props.value] - Optional explicit override (defaults to the
 *   store's live trust score).
 * @returns {JSX.Element} Trust score gauge.
 */
export default function TrustScoreGauge({ value }) {
  const storeTrust = useStore((state) => state.trustScore);

  // Edge cases: null/undefined -> 0; clamp into [0, 1].
  const raw = typeof value === "number" ? value : storeTrust;
  const trustScore = Math.min(1, Math.max(0, typeof raw === "number" && !Number.isNaN(raw) ? raw : 0));
  const percentage = Math.round(trustScore * 100);
  const color = getColor(trustScore);
  const decision = decisionFor(trustScore);

  return (
    <Card title="Trust Score" subtitle={`BTFE Fusion: ${trustScore.toFixed(4)} (live)`}>
      <div className="flex flex-col items-center">
        <div className="relative">
          <RadialBarChart
            key={`gauge-${percentage}`}
            cx="50%"
            cy="50%"
            innerRadius="70%"
            outerRadius="100%"
            barSize={20}
            data={[{ value: percentage, fill: color }]}
            startAngle={90}
            endAngle={-270}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar
              background={{ fill: "#1e293b" }}
              dataKey="value"
              cornerRadius={10}
              isAnimationActive={true}
              animationDuration={500}
            />
          </RadialBarChart>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="text-3xl font-bold transition-colors duration-500"
              style={{ color }}
            >
              {percentage}%
            </span>
            <span className="mt-0.5 text-[10px] text-slate-500">
              BTFE Fusion: {trustScore.toFixed(4)}
            </span>
          </div>
        </div>
        <div className="mt-2">
          <Badge label={`DECISION: ${decision.label}`} variant={decision.variant} />
        </div>
      </div>
    </Card>
  );
}
