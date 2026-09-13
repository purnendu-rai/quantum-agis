/**
 * @file Premium layer status grid: glass cards with lucide icons, pulsing
 * status badges, animated deviation progress bars, and per-layer colored
 * glow. Each card carries an animated scan line.
 */
import { motion } from 'framer-motion';
import { Brain, Clock, Eye, Fingerprint, Shield, Waves } from 'lucide-react';
import Badge from '../common/Badge.jsx';
import ScanLine from '../common/ScanLine.jsx';
import { LAYER_NAMES } from '../../utils/constants.js';

/** Per-layer icon, color, and full name (index-aligned with LAYER_NAMES). */
const LAYERS = [
  { Icon: Fingerprint, color: '#00f0ff', name: 'Genome Mapping' },
  { Icon: Waves, color: '#0080ff', name: 'HOM Interferometry' },
  { Icon: Eye, color: '#a855f7', name: 'Ghost Sensor' },
  { Icon: Clock, color: '#7c3aed', name: 'Temporal Coherence' },
  { Icon: Shield, color: '#ffd700', name: 'MDI-QDS Shield' },
  { Icon: Brain, color: '#00ff88', name: 'Bayesian Fusion' },
];

/**
 * Renders one card per security layer with live verdict, deviation score,
 * and a deviation progress bar.
 * @param {object} props - Component props.
 * @param {object} [props.layerVerdicts] - Map of layer code → verdict string.
 * @param {object} [props.deviations] - Map of layer code → deviation in [0, 1].
 * @returns {JSX.Element} 3x2 layer status grid.
 */
export default function LayerStatusGrid({ layerVerdicts = {}, deviations = {} }) {
  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-3">
      {LAYER_NAMES.map((name, index) => {
        const { Icon, color, name: fullName } = LAYERS[index];
        const verdict = layerVerdicts[name] ?? 'unknown';
        const deviation = deviations[name];
        const failing = verdict === 'rejected' || verdict === 'unknown';
        return (
          <motion.div
            key={name}
            whileHover={{ y: -4 }}
            transition={{ type: 'spring', stiffness: 320, damping: 22 }}
            className="glass glass-hover relative overflow-hidden p-3"
            style={{ borderColor: `${color}33` }}
            title={`${name} — ${fullName}`}
          >
            <ScanLine color={`${color}14`} />
            <div className="relative flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Icon size={14} style={{ color, filter: `drop-shadow(0 0 4px ${color}88)` }} />
                <span className="text-[10px] text-slate-500">L{index}</span>
              </div>
              <Badge
                label={verdict === 'unknown' ? '—' : verdict.toUpperCase()}
                variant={
                  verdict === 'authentic'
                    ? 'pass'
                    : verdict === 'rejected'
                      ? 'fail'
                      : verdict === 'suspicious'
                        ? 'suspicious'
                        : 'gray'
                }
              />
            </div>
            <div className="relative mt-1.5 text-sm font-bold" style={{ color }}>
              {name}
            </div>
            <div className="text-[10px] text-slate-500">{fullName}</div>

            {/* Deviation progress bar */}
            <div className="mt-2">
              <div className="flex items-center justify-between text-[10px] text-slate-500">
                <span>deviation</span>
                <span className="font-data text-slate-400">
                  {typeof deviation === 'number' ? deviation.toFixed(3) : '—'}
                </span>
              </div>
              <div className="mt-1 h-1 overflow-hidden rounded-full bg-slate-800">
                <motion.div
                  className="h-1 rounded-full"
                  style={{ background: color, boxShadow: `0 0 6px ${color}` }}
                  initial={{ width: '0%' }}
                  animate={{ width: `${Math.min(100, (deviation ?? 0) * 100)}%` }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                />
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
