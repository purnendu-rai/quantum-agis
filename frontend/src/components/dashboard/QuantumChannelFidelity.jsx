/**
 * @file Channel fidelity chart: gradient-stroke line with shaded safe zone
 * and a live indicator dot at the newest sample. Memoized.
 */
import { memo } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import GlassCard from '../common/GlassCard.jsx';
import { CHART_TOOLTIP_STYLE } from './HOMVisibilityChart.jsx';
import { formatTimestamp } from '../../utils/formatters.js';

/**
 * Line chart of channel fidelity samples with the normal band shaded and a
 * glowing "current value" dot at the end of the line.
 * @param {object} props - Component props.
 * @param {Array<{timestamp: string, fidelity: number}>} props.series - Data points.
 * @returns {JSX.Element} Fidelity chart.
 */
function QuantumChannelFidelity({ series = [] }) {
  const data = series.map((point) => ({
    time: formatTimestamp(point.timestamp),
    fidelity: point.fidelity,
  }));
  const last = data[data.length - 1];
  return (
    <GlassCard title="Channel Fidelity" subtitle="Normal operating range 0.90 – 1.00" accent="#00ff88">
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="fidelityStroke" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#00ff88" />
              <stop offset="100%" stopColor="#00f0ff" />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="time" stroke="#606080" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 1]} stroke="#606080" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <ReferenceArea y1={0.9} y2={1.0} fill="#00ff88" fillOpacity={0.08} />
          <ReferenceArea y1={0} y2={0.9} fill="#ff3366" fillOpacity={0.04} />
          <Line
            type="monotone"
            dataKey="fidelity"
            stroke="url(#fidelityStroke)"
            strokeWidth={2.5}
            dot={false}
            isAnimationActive
            animationDuration={500}
          />
          {/* Live current-value indicator */}
          {last && (
            <Line
              data={[{ time: last.time, fidelity: last.fidelity }]}
              dataKey="fidelity"
              stroke="none"
              dot={{ r: 4, fill: '#00f0ff', stroke: '#ffffff', strokeWidth: 1.5 }}
              isAnimationActive={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </GlassCard>
  );
}

export default memo(QuantumChannelFidelity);
