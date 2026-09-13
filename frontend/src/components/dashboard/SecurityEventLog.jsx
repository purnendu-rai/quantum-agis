/**
 * @file Paginated security event table with event-type filter.
 */
import { AnimatePresence, motion } from 'framer-motion';
import { useMemo, useState } from 'react';
import Badge from '../common/Badge.jsx';
import { formatTimestamp } from '../../utils/formatters.js';

const PAGE_SIZE = 10;

/**
 * Extract a decision string from an event message (backend embeds
 * "decision=…" in log text).
 * @param {object} event - Security event payload.
 * @returns {string} Decision label or "—".
 */
function parseDecision(event) {
  const match = /decision=(\w+)/.exec(event.message ?? '');
  return match ? match[1].toUpperCase() : '—';
}

/**
 * Extract a trust score from an event message.
 * @param {object} event - Security event payload.
 * @returns {string} Formatted trust score or "—".
 */
function parseTrust(event) {
  const match = /trust=([\d.]+)/.exec(event.message ?? '');
  return match ? Number(match[1]).toFixed(3) : '—';
}

/**
 * Tabular audit trail: Timestamp, Event Type, Severity, Decision, Trust,
 * Details — paginated 10 rows per page with an event-type filter.
 * @param {object} props - Component props.
 * @param {Array<object>} props.events - SecurityEvent payloads.
 * @returns {JSX.Element} Event log table with filter and pagination.
 */
export default function SecurityEventLog({ events = [] }) {
  const [page, setPage] = useState(0);
  const [typeFilter, setTypeFilter] = useState('all');

  const eventTypes = useMemo(
    () => ['all', ...Array.from(new Set(events.map((event) => event.source))).sort()],
    [events]
  );
  const filtered = useMemo(
    () => (typeFilter === 'all' ? events : events.filter((event) => event.source === typeFilter)),
    [events, typeFilter]
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const rows = filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500">Event type:</span>
        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(0);
          }}
          className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-300"
        >
          {eventTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        <span className="text-xs text-slate-500">
          {filtered.length} event{filtered.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="uppercase text-slate-500">
            <tr>
              <th className="py-1.5 pr-2">Timestamp</th>
              <th className="py-1.5 pr-2">Event Type</th>
              <th className="py-1.5 pr-2">Severity</th>
              <th className="py-1.5 pr-2">Decision</th>
              <th className="py-1.5 pr-2">Trust</th>
              <th className="py-1.5">Details</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
            {rows.map((event, index) => {
              const decision = parseDecision(event);
              return (
                <motion.tr
                  key={`${event.timestamp}-${event.source}-${index}`}
                  initial={{ opacity: 0, x: -14 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.22, ease: 'easeOut' }}
                  className="border-t border-slate-800/70 hover:bg-quantum-cyan/5"
                >
                  <td className="py-1.5 pr-2 font-mono text-slate-400">
                    {event.timestamp ? formatTimestamp(event.timestamp) : '—'}
                  </td>
                  <td className="py-1.5 pr-2 text-slate-300">{event.source}</td>
                  <td className="py-1.5 pr-2">
                    <Badge
                      label={event.severity?.toUpperCase() ?? 'INFO'}
                      variant={
                        event.severity === 'critical'
                          ? 'fail'
                          : event.severity === 'warning'
                            ? 'suspicious'
                            : 'info'
                      }
                    />
                  </td>
                  <td className="py-1.5 pr-2 text-slate-300">{decision}</td>
                  <td className="py-1.5 pr-2 font-mono text-slate-300">{parseTrust(event)}</td>
                  <td className="py-1.5 text-slate-400">{event.message}</td>
                </motion.tr>
              );
            })}
            </AnimatePresence>
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-4 text-center text-slate-500">
                  No events match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <button
          type="button"
          disabled={safePage === 0}
          onClick={() => setPage(safePage - 1)}
          className="rounded border border-slate-700 px-2 py-1 disabled:opacity-40"
        >
          ← Prev
        </button>
        <span>
          page {safePage + 1} / {pageCount}
        </span>
        <button
          type="button"
          disabled={safePage >= pageCount - 1}
          onClick={() => setPage(safePage + 1)}
          className="rounded border border-slate-700 px-2 py-1 disabled:opacity-40"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
