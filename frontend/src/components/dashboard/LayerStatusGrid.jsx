/**
 * @file Grid of six layer cards with status badge, deviation score, and
 * per-layer color-coded borders.
 */
import Badge from '../common/Badge.jsx';
import Card from '../common/Card.jsx';
import { LAYER_NAMES, LAYER_FULL_NAMES } from '../../utils/constants.js';

/** Border color per layer index, aligned with LAYER_NAMES. */
const LAYER_COLORS = ['#0055ff', '#00ccff', '#ffaa00', '#aa44ff', '#ff2244', '#ffcc00'];

/**
 * Renders one card per security layer with its live verdict and deviation.
 * @param {object} props - Component props.
 * @param {object} [props.layerVerdicts] - Map of layer code → verdict string
 *   ("authentic" | "suspicious" | "rejected").
 * @param {object} [props.deviations] - Map of layer code → deviation in [0, 1].
 * @returns {JSX.Element} 3x2 layer status grid.
 */
export default function LayerStatusGrid({ layerVerdicts = {}, deviations = {} }) {
  return (
    <Card title="Layer Status" subtitle="Live verdict and deviation per security layer">
      <div className="grid grid-cols-3 gap-3">
        {LAYER_NAMES.map((name, index) => {
          const verdict = layerVerdicts[name] ?? 'unknown';
          const deviation = deviations[name];
          const badge =
            verdict === 'authentic' ? 'pass' : verdict === 'rejected' ? 'fail' : 'suspicious';
          return (
            <div
              key={name}
              className="rounded-md border bg-slate-950/60 p-3"
              style={{ borderColor: `${LAYER_COLORS[index]}66` }}
              title={`${name} — ${LAYER_FULL_NAMES[index]}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-500">L{index}</span>
                <Badge
                  label={verdict === 'unknown' ? '—' : verdict.toUpperCase()}
                  variant={verdict === 'unknown' ? 'gray' : badge}
                />
              </div>
              <div className="mt-1 text-sm font-semibold" style={{ color: LAYER_COLORS[index] }}>
                {name}
              </div>
              <div className="text-[10px] text-slate-500">{LAYER_FULL_NAMES[index]}</div>
              <div className="mt-1 text-xs text-slate-400">
                deviation:{' '}
                <span className="font-mono text-slate-300">
                  {typeof deviation === 'number' ? deviation.toFixed(3) : '—'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
