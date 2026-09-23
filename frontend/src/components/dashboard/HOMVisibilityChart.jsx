/**
 * @file HOM visibility chart: gradient area chart with animated line,
 * threshold reference lines, and glassmorphism tooltip. Wrapped in
 * GlassCard. Parent should pass memoized series data.
 */
import { memo } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import GlassCard from '../common/GlassCard.jsx';
import { formatTimestamp } from '../../utils/formatters.js';

/** Glassmorphism tooltip style shared by all charts. */
export const CHART_TOOLTIP_STYLE = {
  background: 'rgba(19, 19, 46, 0.92)',
  backdropFilter: 'blur(16px)',
  border: '1px solid rgba(0, 240, 255, 0.35)',
  borderRadius: 8,
  fontSize: 12,
  fontFamily: 'JetBrains Mono, ui-monospace, monospace',
  color: '#ffffff',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
};

/**
 * Area chart of HOM visibility samples with threshold guides.
 * @param {object} props - Component props.
 * @param {Array<{timestamp: string, visibility: number}>} props.series - Data points.
 * @returns {JSX.Element} HOM visibility chart.
 */
function HOMVisibilityChart({ series = [] }) {
  const data = series.map((point) => ({
    time: formatTimestamp(point.timestamp),
    visibility: point.visibility,
  }));
  return (
    <GlassCard title="HOM Visibility" subtitle="V_HOM — legitimate ≥ 0.95, forgery < 0.5" accent="#00f0ff">
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="homFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00f0ff" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#00f0ff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="time" stroke="#94a3b8" tick={{ fontSize: 11, fill: '#94a3b8', fontFamily: 'JetBrains Mono, monospace' }} />
          <YAxis domain={[0, 1]} stroke="#94a3b8" tick={{ fontSize: 11, fill: '#94a3b8', fontFamily: 'JetBrains Mono, monospace' }} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <ReferenceLine
            y={0.95}
            stroke="#00ff88"
            strokeDasharray="4 4"
            label={{ value: '0.95', fill: '#00ff88', fontSize: 10, position: 'insideTopRight' }}
          />
          <ReferenceLine
            y={0.5}
            stroke="#ff3366"
            strokeDasharray="4 4"
            label={{ value: '0.5', fill: '#ff3366', fontSize: 10, position: 'insideTopRight' }}
          />
          <Area
            type="monotone"
            dataKey="visibility"
            stroke="#00f0ff"
            strokeWidth={2}
            fill="url(#homFill)"
            isAnimationActive
            animationDuration={500}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </GlassCard>
  );
}

export default memo(HOMVisibilityChart);
