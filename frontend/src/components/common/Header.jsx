/**
 * @file Top application header: brand, subtitle, live WebSocket status dot.
 */
import { Link } from 'react-router-dom';
import useStore from '../../store/useStore.js';

/**
 * Sticky header with the AGIS brand and the live stream status indicator.
 * The green dot mirrors the WebSocket connection state from the store.
 * @returns {JSX.Element} Header bar.
 */
export default function Header() {
  const wsConnected = useStore((state) => state.wsConnected);

  return (
    <header className="glass glass-hover sticky top-0 z-40 flex items-center justify-between border-x-0 border-t-0 px-6 py-3">
      <div>
        <Link to="/" className="font-display text-lg font-bold text-white">
          QUANTUM<span className="quantum-text">·AGIS</span>
        </Link>
        <p className="text-[11px] text-slate-400">
          Quantum-inspired Agentic Governance &amp; Intrusion Shield
        </p>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span
          className={`pulse-dot inline-block h-2.5 w-2.5 rounded-full transition-all duration-300 ${
            wsConnected
              ? 'bg-emerald-400 shadow-[0_0_8px_2px_rgba(52,211,153,0.6)]'
              : 'bg-rose-500 shadow-[0_0_8px_2px_rgba(244,63,94,0.6)]'
          }`}
        />
        <span className="text-slate-400">{wsConnected ? 'live' : 'connecting…'}</span>
      </div>
    </header>
  );
}
