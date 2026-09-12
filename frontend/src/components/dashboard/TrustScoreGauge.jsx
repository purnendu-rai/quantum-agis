/**
 * @file Circular trust-score gauge (Recharts RadialBarChart) with decision
 * badge; color thresholds: red < 0.90, orange 0.90–0.95, green > 0.95.
 */
import { PolarAngleAxis, RadialBar, RadialBarChart } from 'recharts';
import Badge from '../common/Badge.jsx';
import Card from '../common/Card.jsx';

/**
 * Derive the gauge color from the trust score.
 * @param {number} value - Trust score in [0, 1].
 * @returns {string} Hex color.
 */
function gaugeColor(value) {
  if (value > 0.95) return '#22c55e';
  if (value >= 0.9) return '#ffaa00';
  return '#ff2244';
}

/**
 * Derive the BTFE decision from the trust score (mirrors backend thresholds).
 * @param {number} value - Trust score in [0, 1].
 * @returns {{label: string, variant: string}} Decision label and badge variant.
 */
export function decisionFor(value) {
  if (value > 0.95) return { label: 'ACCEPT', variant: 'pass' };
  if (value < 0.9) return { label: 'REJECT', variant: 'fail' };
  return { label: 'QUARANTINE', variant: 'suspicious' };
}

/**
 * Radial gauge showing the aggregate trust score with the fused decision.
 * @param {object} props - Component props.
 * @param {number} [props.value] - Current trust score in [0, 1].
 * @returns {JSX.Element} Trust score gauge.
 */
export default function TrustScoreGauge({ value = 0 }) {
  const color = gaugeColor(value);
  const decision = decisionFor(value);
  return (
    <Card title="Trust Score" subtitle="BTFE fusion of layers 0–5">
      <div className="flex flex-col items-center">
        <div className="relative">
          <RadialBarChart
            width={200}
            height={200}
            innerRadius="72%"
            outerRadius="100%"
            data={[{ name: 'trust', value: Math.max(0, Math.min(1, value)) * 100, fill: color }]}
            startAngle={90}
            endAngle={-270}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar dataKey="value" cornerRadius={10} background={{ fill: '#1e293b' }} />
          </RadialBarChart>
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <span className="text-3xl font-bold" style={{ color }}>
              {(value * 100).toFixed(1)}%
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
