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
    <header
      className="flex items-center justify-between border-b px-6 py-3"
      style={{ borderColor: 'rgba(0, 212, 255, 0.2)' }}
    >
      <div>
        <Link to="/" className="text-lg font-semibold tracking-widest text-white">
          QUANTUM<span className="text-quantum-blue">·</span>AGIS
        </Link>
        <p className="text-[11px] text-slate-400">
          Quantum-inspired Agentic Governance &amp; Intrusion Shield
        </p>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full transition-all duration-300 ${
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
