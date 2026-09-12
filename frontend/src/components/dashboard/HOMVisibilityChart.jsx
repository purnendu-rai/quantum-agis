/**
 * @file HOM visibility trend chart with 0.95 (legitimate) and 0.5 (forgery)
 * threshold reference lines.
 */
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Card from '../common/Card.jsx';
import { formatTimestamp } from '../../utils/formatters.js';

/**
 * Line chart of HOM visibility samples with threshold guides.
 * @param {object} props - Component props.
 * @param {Array<{timestamp: string, visibility: number}>} [props.series] - Data points.
 * @returns {JSX.Element} HOM visibility chart.
 */
export default function HOMVisibilityChart({ series = [] }) {
  const data = series.map((point) => ({
    time: formatTimestamp(point.timestamp),
    visibility: point.visibility,
  }));
  return (
    <Card title="HOM Visibility" subtitle="V_HOM — legitimate ≥ 0.95, forgery < 0.5">
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
          <YAxis domain={[0, 1]} stroke="#64748b" tick={{ fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: '#0d1330', border: '1px solid rgba(0,212,255,0.2)' }}
          />
          <ReferenceLine y={0.95} stroke="#22c55e" strokeDasharray="4 4" label={{ value: '0.95', fill: '#22c55e', fontSize: 10, position: 'insideTopRight' }} />
          <ReferenceLine y={0.5} stroke="#ff2244" strokeDasharray="4 4" label={{ value: '0.5', fill: '#ff2244', fontSize: 10, position: 'insideTopRight' }} />
          <Line dataKey="visibility" stroke="#00d4ff" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
