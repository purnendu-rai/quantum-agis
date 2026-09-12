/**
 * @file Channel fidelity trend chart with the normal operating range
 * (0.90–1.00) highlighted.
 */
import {
  Area,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Card from '../common/Card.jsx';
import { formatTimestamp } from '../../utils/formatters.js';

/**
 * Line chart of channel fidelity samples with the normal band shaded.
 * @param {object} props - Component props.
 * @param {Array<{timestamp: string, fidelity: number}>} [props.series] - Data points.
 * @returns {JSX.Element} Fidelity chart.
 */
export default function QuantumChannelFidelity({ series = [] }) {
  const data = series.map((point) => ({
    time: formatTimestamp(point.timestamp),
    fidelity: point.fidelity,
  }));
  return (
    <Card title="Channel Fidelity" subtitle="Normal operating range 0.90 – 1.00">
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
          <YAxis domain={[0, 1]} stroke="#64748b" tick={{ fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: '#0d1330', border: '1px solid rgba(0,212,255,0.2)' }}
          />
          <ReferenceArea y1={0.9} y2={1.0} fill="#22c55e" fillOpacity={0.08} />
          <ReferenceArea y1={0} y2={0.9} fill="#ff2244" fillOpacity={0.04} />
          <Line dataKey="fidelity" stroke="#34d399" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
