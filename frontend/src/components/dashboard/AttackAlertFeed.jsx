/**
 * @file Scrolling feed of the last 20 attack/security events, color-coded by
 * decision parsed from the event stream.
 */
import { useMemo } from 'react';
import Badge from '../common/Badge.jsx';
import Card from '../common/Card.jsx';
import { formatTimestamp } from '../../utils/formatters.js';

/** Decision → badge variant + accent color. */
const DECISION_STYLES = {
  accept: { variant: 'pass', color: '#22c55e' },
  reject: { variant: 'fail', color: '#ff2244' },
  quarantine: { variant: 'suspicious', color: '#ffaa00' },
};

/**
 * Extract a decision string ("accept" | "reject" | "quarantine") from an
 * event, preferring structured fields and falling back to message parsing.
 * @param {object} event - Security event payload.
 * @returns {string|null} Decision string, or null when unknown.
 */
function parseDecision(event) {
  if (event.decision) return String(event.decision).toLowerCase();
  const match = /decision=(\w+)/.exec(event.message ?? '');
  return match ? match[1].toLowerCase() : null;
}

/**
 * Extract a trust score from an event (structured field or message text).
 * @param {object} event - Security event payload.
 * @returns {number|null} Trust score in [0, 1], or null.
 */
function parseTrust(event) {
  if (typeof event.trust_score === 'number') return event.trust_score;
  const match = /trust=([\d.]+)/.exec(event.message ?? '');
  return match ? Number(match[1]) : null;
}

/**
 * Scrolling list of the most recent security events with decision coloring.
 * @param {object} props - Component props.
 * @param {Array<object>} [props.events] - SecurityEvent payloads, newest first.
 * @returns {JSX.Element} Alert feed panel.
 */
export default function AttackAlertFeed({ events = [] }) {
  const recent = useMemo(() => events.slice(0, 20), [events]);
  return (
    <Card title="Attack Alerts" subtitle="Last 20 security events (live via WebSocket)">
      {recent.length === 0 && <p className="text-sm text-slate-500">No events yet.</p>}
      <ul className="max-h-64 space-y-1.5 overflow-y-auto pr-1">
        {recent.map((event, index) => {
          const decision = parseDecision(event);
          const trust = parseTrust(event);
          const style = DECISION_STYLES[decision] ?? { variant: 'info', color: '#00ccff' };
          return (
            <li
              key={`${event.timestamp}-${index}`}
              className="flex items-center justify-between gap-2 rounded border-l-2 bg-slate-950/60 px-2 py-1.5 text-xs"
              style={{ borderColor: style.color }}
            >
              <div className="min-w-0">
                <div className="truncate text-slate-300">{event.message ?? event.source}</div>
                <div className="text-[10px] text-slate-500">
                  {event.timestamp ? formatTimestamp(event.timestamp) : ''} · {event.source}
                  {trust !== null && ` · trust ${trust.toFixed(3)}`}
                </div>
              </div>
              <Badge
                label={decision ? decision.toUpperCase() : (event.severity ?? 'info').toUpperCase()}
                variant={style.variant}
              />
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
