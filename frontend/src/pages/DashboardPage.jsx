/**
 * @file Main monitoring dashboard: gauge + layer grid, trend charts, live
 * alert feed, NH spectrum, and the verification console. WebSocket connects
 * on mount; REST data refreshes on a 5s interval.
 */
import { useCallback, useEffect, useState } from 'react';
import { getDashboardState, getMetricHistory, getVerificationHistory } from '../api/verification.js';
import { REFRESH_INTERVAL_MS } from '../utils/constants.js';
import useStore from '../store/useStore.js';
import Loader from '../components/common/Loader.jsx';
import VerificationPanel from '../components/verification/VerificationPanel.jsx';
import AttackAlertFeed from '../components/dashboard/AttackAlertFeed.jsx';
import HOMVisibilityChart from '../components/dashboard/HOMVisibilityChart.jsx';
import LayerStatusGrid from '../components/dashboard/LayerStatusGrid.jsx';
import NHSPectrumView from '../components/dashboard/NHSPectrumView.jsx';
import QuantumChannelFidelity from '../components/dashboard/QuantumChannelFidelity.jsx';
import TrustScoreGauge from '../components/dashboard/TrustScoreGauge.jsx';

/**
 * Poll the dashboard state, metric series, and latest verification (for
 * per-layer deviation scores), then render every widget.
 * @returns {JSX.Element} Dashboard layout.
 */
export default function DashboardPage() {
  const [snapshot, setSnapshot] = useState(null);
  const [homSeries, setHomSeries] = useState([]);
  const [fidelitySeries, setFidelitySeries] = useState([]);
  const [deviations, setDeviations] = useState({});
  const [error, setError] = useState(null);
  const liveEvents = useStore((state) => state.recentEvents);
  const wsConnected = useStore((state) => state.wsConnected);
  const storeTrust = useStore((state) => state.trustScore);
  const setStoreTrust = useStore((state) => state.setTrustScore);

  const refresh = useCallback(async () => {
    try {
      const [state, hom, fidelity, lastVerify] = await Promise.all([
        getDashboardState(),
        getMetricHistory('hom_visibility', 60),
        getMetricHistory('channel_fidelity', 60),
        getVerificationHistory(1).catch(() => []),
      ]);
      setSnapshot(state);
      if (typeof state.trust_score === 'number') {
        setStoreTrust(state.trust_score); // seed the live value; WS keeps it current
      }
      setHomSeries(hom.points.map((p) => ({ timestamp: p.timestamp, visibility: p.value })));
      setFidelitySeries(fidelity.points.map((p) => ({ timestamp: p.timestamp, fidelity: p.value })));
      const latest = lastVerify[0];
      if (latest?.layer_results) {
        setDeviations(
          Object.fromEntries(
            latest.layer_results.map((layer) => [layer.layer_name, 1 - layer.confidence])
          )
        );
      }
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const alerts = liveEvents.length > 0 ? liveEvents : (snapshot?.active_alerts ?? []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Security Dashboard</h1>
        <span className="text-xs text-slate-500">
          WebSocket: {wsConnected ? '🟢 live' : '🔴 reconnecting…'}
        </span>
      </div>
      {error && <p className="text-xs text-rose-300">backend unreachable — retrying automatically…</p>}
      {!snapshot && !error && (
        <Loader label="Connecting to the AGIS verification stack…" />
      )}
      <div className={`grid grid-cols-1 gap-6 lg:grid-cols-2 ${snapshot ? '' : 'opacity-40'}`}>
        {/* Row 1 */}
        <TrustScoreGauge value={storeTrust} />
        <LayerStatusGrid layerVerdicts={snapshot?.layer_verdicts ?? {}} deviations={deviations} />
        {/* Row 2 */}
        <HOMVisibilityChart series={homSeries} />
        <AttackAlertFeed events={alerts} />
        {/* Row 3 */}
        <QuantumChannelFidelity series={fidelitySeries} />
        <NHSPectrumView />
      </div>
      {/* Row 4 */}
      <VerificationPanel />
    </div>
  );
}
