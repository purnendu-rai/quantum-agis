/**
 * @file Security event log page: full table with severity/text filters and a
 * JSON export download.
 */
import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { exportLogs, getSecurityEvents } from '../api/logs.js';
import SecurityEventLog from '../components/dashboard/SecurityEventLog.jsx';
import Card from '../components/common/Card.jsx';

const SEVERITIES = ['all', 'info', 'warning', 'critical'];

/**
 * Full-page audit trail of security events with filter controls and a
 * one-click JSON export.
 * @returns {JSX.Element} Logs page layout.
 */
export default function LogsPage() {
  const [events, setEvents] = useState([]);
  const [severity, setSeverity] = useState('all');
  const [search, setSearch] = useState('');
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getSecurityEvents({
        limit: 500,
        severity: severity === 'all' ? undefined : severity,
      });
      setEvents(data);
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, [severity]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [refresh]);

  const filtered = events.filter(
    (event) =>
      !search ||
      event.message?.toLowerCase().includes(search.toLowerCase()) ||
      event.source?.toLowerCase().includes(search.toLowerCase())
  );

  /**
   * Download the full event log as a JSON file via a temporary object URL.
   */
  async function handleExport() {
    const payload = await exportLogs();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `agis-security-logs-${new Date().toISOString().slice(0, 19)}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Security Logs</h1>
        <div className="flex flex-wrap items-center gap-2">
          {SEVERITIES.map((level) => (
            <button
              key={level}
              type="button"
              onClick={() => setSeverity(level)}
              className={`relative rounded px-3 py-1 text-xs transition-colors ${
                severity === level ? 'text-quantum-cyan' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {severity === level && (
                <motion.span
                  layoutId="severity-pill"
                  className="absolute inset-0 rounded border border-quantum-cyan/60 bg-quantum-cyan/10"
                  transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                />
              )}
              <span className="relative">{level}</span>
            </button>
          ))}
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search events…"
            className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-300 focus:border-quantum-blue focus:outline-none"
          />
          <button
            type="button"
            onClick={handleExport}
            className="rounded border border-quantum-purple/50 bg-quantum-purple/20 px-3 py-1 text-xs text-purple-200 hover:bg-quantum-purple/30"
          >
            ⬇ Export JSON
          </button>
        </div>
      </div>
      {error && <p className="text-xs text-rose-300">backend unreachable — retrying…</p>}
      <Card>
        <SecurityEventLog events={filtered} />
      </Card>
    </div>
  );
}
