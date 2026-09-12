/**
 * @file Non-Hermitian eigenvalue spectrum bar chart with exceptional-point
 * highlighting and a tampering probe slider (live via /dashboard/nh-spectrum).
 */
import { useCallback, useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getNhSpectrum } from '../../api/verification.js';
import Card from '../common/Card.jsx';
import Loader from '../common/Loader.jsx';

/**
 * Compute the magnitude of an [real, imag] eigenvalue pair.
 * @param {Array<number>} pair - [real, imag] components.
 * @returns {number} Absolute value |lambda|.
 */
function magnitude(pair) {
  return Math.hypot(pair[0], pair[1]);
}

/**
 * Bar chart of the NHGS lattice eigenvalue spectrum. Bars belonging to an
 * exceptional-point pair are highlighted red; the baseline mean magnitude is
 * drawn as a reference line. A slider injects seeded lattice noise to
 * visualise spectral drift live.
 * @returns {JSX.Element} Spectrum view.
 */
export default function NHSPectrumView() {
  const [tampering, setTampering] = useState(0);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const fetchSpectrum = useCallback(async (level) => {
    try {
      const payload = await getNhSpectrum(level);
      const eps = new Set(payload.exceptional_points.flat());
      setData({
        exceptional: eps,
        baselineMean:
          payload.baseline.reduce((sum, pair) => sum + magnitude(pair), 0) / payload.baseline.length,
        bars: payload.spectrum.map((pair, index) => ({
          mode: `λ${index}`,
          magnitude: magnitude(pair),
          exceptional: eps.has(index),
        })),
      });
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    fetchSpectrum(tampering);
  }, [tampering, fetchSpectrum]);

  return (
    <Card title="NH Spectrum (NHGS)" subtitle="Eigenvalue magnitudes — red bars sit at exceptional points">
      <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
        <span>tampering probe:</span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={tampering}
          onChange={(event) => setTampering(Number(event.target.value))}
          className="flex-1 accent-cyan-400"
        />
        <span className="w-8 font-mono text-slate-300">{tampering.toFixed(1)}</span>
      </div>
      {error && <p className="text-xs text-rose-300">spectrum feed unavailable</p>}
      {!data && !error && <Loader label="diagonalising lattice…" />}
      {data && (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data.bars} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
            <XAxis dataKey="mode" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
            <Tooltip
              contentStyle={{ background: '#0d1330', border: '1px solid rgba(0,212,255,0.2)' }}
            />
            <ReferenceLine
              y={data.baselineMean}
              stroke="#64748b"
              strokeDasharray="4 4"
              label={{ value: 'baseline', fill: '#64748b', fontSize: 10, position: 'insideTopRight' }}
            />
            <Bar dataKey="magnitude" radius={[4, 4, 0, 0]}>
              {data.bars.map((bar, index) => (
                <Cell
                  key={index}
                  fill={bar.exceptional ? '#ff2244' : '#00d4ff'}
                  className={bar.exceptional ? 'drop-shadow-[0_0_6px_rgba(255,34,68,0.6)]' : ''}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
