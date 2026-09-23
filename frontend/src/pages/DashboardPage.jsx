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
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Security Dashboard</h1>
          <p className="mt-1 text-xs font-normal text-slate-300">
            Real-time multi-layer quantum signature telemetry, trust scoring, and active intrusion shield
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-cosmos/80 px-3.5 py-1 text-xs font-medium backdrop-blur-md">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              wsConnected ? 'bg-quantum-green animate-pulse shadow-[0_0_8px_#00ff88]' : 'bg-quantum-red'
            }`}
          />
          <span className="font-data tabular-nums font-semibold tracking-wider text-slate-200">
            {wsConnected ? 'LIVE TELEMETRY' : 'RECONNECTING'}
          </span>
        </div>
      </div>
      {error && <p className="text-xs text-rose-300">backend unreachable — retrying automatically…</p>}
      {!snapshot && !error && (
        <Loader label="Connecting to the AGIS verification stack…" />
      )}
      <div className={`grid grid-cols-1 gap-6 lg:grid-cols-12 ${snapshot ? '' : 'opacity-40'}`}>
        {/* Row 1 — Trust Score (4) | Layer Status (8) */}
        <div className="lg:col-span-4">
          <TrustScoreGauge />
        </div>
        <div className="lg:col-span-8">
          <LayerStatusGrid layerVerdicts={snapshot?.layer_verdicts ?? {}} deviations={deviations} />
        </div>
        {/* Row 2 — HOM (6) | Alerts (6) */}
        <div className="lg:col-span-6">
          <HOMVisibilityChart series={homSeries} />
        </div>
        <div className="lg:col-span-6">
          <AttackAlertFeed events={alerts} />
        </div>
        {/* Row 3 — Fidelity (6) | NH Spectrum (6) */}
        <div className="lg:col-span-6">
          <QuantumChannelFidelity series={fidelitySeries} />
        </div>
        <div className="lg:col-span-6">
          <NHSPectrumView />
        </div>
      </div>
      {/* Row 4 */}
      <div className="mt-6">
        <VerificationPanel />
      </div>
    </div>
  );
}
