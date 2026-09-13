/**
 * @file NHGS eigenvalue spectrum bar chart: purple-to-blue gradient bars,
 * pulsing red exceptional-point bars, baseline reference line, and a
 * tampering probe slider (live via /dashboard/nh-spectrum).
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
import { CHART_TOOLTIP_STYLE } from './HOMVisibilityChart.jsx';
import Loader from '../common/Loader.jsx';
import GlassCard from '../common/GlassCard.jsx';

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
 * exceptional-point pair pulse red; the baseline mean magnitude is drawn as
 * a reference line. The slider injects seeded lattice noise to visualise
 * spectral drift live.
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
    <GlassCard
      title="NH Spectrum (NHGS)"
      subtitle="Eigenvalue magnitudes — pulsing bars sit at exceptional points"
      accent="#a855f7"
    >
      <div className="mb-2 flex items-center gap-2 text-xs text-text-secondary">
        <span>tampering probe:</span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={tampering}
          onChange={(event) => setTampering(Number(event.target.value))}
          className="flex-1 accent-quantum-purple"
        />
        <span className="w-8 font-data text-slate-300">{tampering.toFixed(1)}</span>
      </div>
      {error && <p className="text-xs text-rose-300">spectrum feed unavailable</p>}
      {!data && !error && <Loader label="diagonalising lattice…" />}
      {data && (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data.bars} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
            <defs>
              <linearGradient id="nhBar" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#a855f7" />
                <stop offset="100%" stopColor="#0080ff" />
              </linearGradient>
            </defs>
            <XAxis dataKey="mode" stroke="#606080" tick={{ fontSize: 11 }} />
            <YAxis stroke="#606080" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={{ fill: 'rgba(0,240,255,0.05)' }} />
            <ReferenceLine
              y={data.baselineMean}
              stroke="#606080"
              strokeDasharray="4 4"
              label={{ value: 'baseline', fill: '#606080', fontSize: 10, position: 'insideTopRight' }}
            />
            <Bar dataKey="magnitude" radius={[6, 6, 0, 0]} isAnimationActive animationDuration={500}>
              {data.bars.map((bar, index) => (
                <Cell
                  key={index}
                  fill={bar.exceptional ? '#ff3366' : 'url(#nhBar)'}
                  className={bar.exceptional ? 'animate-pulse' : ''}
                  style={bar.exceptional ? { filter: 'drop-shadow(0 0 8px rgba(255,51,102,0.7))' } : undefined}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </GlassCard>
  );
}
