/**
 * @file Live attack alert feed: sliding Framer Motion entries, severity
 * icons, decision-colored borders, trust badges, and hover gradients.
 */
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, Info, ShieldAlert } from 'lucide-react';
import Badge from '../common/Badge.jsx';
import GlassCard from '../common/GlassCard.jsx';
import { formatTimestamp } from '../../utils/formatters.js';

const SEVERITY_META = {
  info: { Icon: Info, border: '#00f0ff', variant: 'info' },
  warning: { Icon: AlertTriangle, border: '#ffb800', variant: 'suspicious' },
  critical: { Icon: ShieldAlert, border: '#ff3366', variant: 'fail' },
};

/**
 * Extract a decision string from an event (structured field or message).
 * @param {object} event - Security event payload.
 * @returns {string|null} Decision string, or null when unknown.
 */
function parseDecision(event) {
  if (event.decision) return String(event.decision).toLowerCase();
  const match = /decision=(\w+)/.exec(event.message ?? '');
  return match ? match[1].toLowerCase() : null;
}

/**
 * Extract a trust score from an event.
 * @param {object} event - Security event payload.
 * @returns {number|null} Trust score in [0, 1], or null.
 */
function parseTrust(event) {
  if (typeof event.trust_score === 'number') return event.trust_score;
  const match = /trust=([\d.]+)/.exec(event.message ?? '');
  return match ? Number(match[1]) : null;
}

/**
 * Scrolling list of the last 20 security events with slide-in animation.
 * @param {object} props - Component props.
 * @param {Array<object>} [props.events] - SecurityEvent payloads, newest first.
 * @returns {JSX.Element} Alert feed panel.
 */
export default function AttackAlertFeed({ events = [] }) {
  const recent = events.slice(0, 20);
  return (
    <GlassCard
      title="Attack Alerts"
      subtitle="Last 20 security events (live via WebSocket)"
      accent="#ff3366"
    >
      {recent.length === 0 && <p className="text-sm text-slate-500">No events yet.</p>}
      <ul className="max-h-64 space-y-2 overflow-y-auto pr-1">
        <AnimatePresence initial={false}>
          {recent.map((event, index) => {
            const decision = parseDecision(event);
            const trust = parseTrust(event);
            const meta = SEVERITY_META[event.severity] ?? SEVERITY_META.info;
            return (
              <motion.li
                key={`${event.timestamp}-${event.source}-${index}`}
                initial={{ x: 50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: -30, opacity: 0 }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
                className="flex items-center gap-2.5 rounded-md border-l-2 bg-slate-950/60 px-2.5 py-1.5 text-xs transition-colors hover:bg-gradient-to-r hover:from-quantum-cyan/5 hover:to-transparent"
                style={{ borderColor: decision === 'accept' ? '#00ff88' : decision === 'reject' ? '#ff3366' : meta.border }}
              >
                <meta.Icon size={13} style={{ color: meta.border }} className="shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-medium text-slate-200">{event.message ?? event.source}</div>
                  <div className="font-data tabular-nums text-xs text-slate-400">
                    {event.timestamp ? formatTimestamp(event.timestamp) : ''} · {event.source}
                    {trust !== null && ` · trust ${trust.toFixed(3)}`}
                  </div>
                  {/* Mini trust progress bar */}
                  {trust !== null && (
                    <div className="mt-1 h-0.5 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-0.5 rounded-full"
                        style={{
                          width: `${trust * 100}%`,
                          background: decision === 'accept' ? '#00ff88' : decision === 'reject' ? '#ff3366' : '#ffb800',
                        }}
                      />
                    </div>
                  )}
                </div>
                <Badge
                  label={decision ? decision.toUpperCase() : event.severity?.toUpperCase() ?? 'INFO'}
                  variant={meta.variant}
                />
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ul>
    </GlassCard>
  );
}
