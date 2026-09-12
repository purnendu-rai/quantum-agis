/**
 * @file Attack-simulator page: console on top, attack-only event log and
 * post-attack state below.
 */
import { useCallback, useEffect, useState } from 'react';
import { getDashboardState } from '../api/verification.js';
import { getSecurityEvents } from '../api/logs.js';
import SecurityEventLog from '../components/dashboard/SecurityEventLog.jsx';
import TrustScoreGauge from '../components/dashboard/TrustScoreGauge.jsx';
import AttackPanel from '../components/attack/AttackPanel.jsx';

/**
 * Attack lab: launch scenarios at the top; below, the trust gauge and an
 * event log filtered to attack sources only.
 * @returns {JSX.Element} Attack simulator page.
 */
export default function AttackSimulatorPage() {
  const [snapshot, setSnapshot] = useState(null);
  const [attackEvents, setAttackEvents] = useState([]);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [state, events] = await Promise.all([
        getDashboardState(),
        getSecurityEvents({ limit: 200 }),
      ]);
      setSnapshot(state);
      setAttackEvents(events.filter((event) => event.source?.startsWith('attack')));
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [refresh]);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Attack Simulator</h1>
      {error && <p className="text-xs text-rose-300">backend unreachable — retrying…</p>}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <AttackPanel />
        </div>
        <TrustScoreGauge value={snapshot?.trust_score ?? 0} />
      </div>
      <SecurityEventLog events={attackEvents} />
    </div>
  );
}
