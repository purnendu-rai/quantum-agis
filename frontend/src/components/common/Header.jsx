/**
 * @file Top application header: animated atom logo, gradient brand text,
 * live WebSocket status, and a running system clock.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import useStore from '../../store/useStore.js';

/**
 * Animated quantum atom SVG (nucleus + 3 electron orbits).
 * @returns {JSX.Element} Atom icon.
 */
function AtomLogo() {
  return (
    <svg width="38" height="38" viewBox="0 0 38 38" className="animate-spin-slow" aria-hidden="true">
      <ellipse cx="19" cy="19" rx="16" ry="7" fill="none" stroke="#00f0ff" strokeWidth="1.2" opacity="0.8" transform="rotate(0 19 19)" />
      <ellipse cx="19" cy="19" rx="16" ry="7" fill="none" stroke="#a855f7" strokeWidth="1.2" opacity="0.8" transform="rotate(60 19 19)" />
      <ellipse cx="19" cy="19" rx="16" ry="7" fill="none" stroke="#0080ff" strokeWidth="1.2" opacity="0.8" transform="rotate(120 19 19)" />
      <circle cx="19" cy="19" r="3" fill="#00f0ff" style={{ filter: 'drop-shadow(0 0 5px #00f0ff)' }} />
      <circle cx="33" cy="15" r="1.6" fill="#a855f7" style={{ filter: 'drop-shadow(0 0 4px #a855f7)' }} />
    </svg>
  );
}

/**
 * Sticky header: brand, subtitle, live status, running clock, avatar.
 * @returns {JSX.Element} Header bar.
 */
export default function Header() {
  const wsConnected = useStore((state) => state.wsConnected);
  const [clock, setClock] = useState('');

  useEffect(() => {
    /**
     * Refresh the monospace system clock every second.
     */
    function tick() {
      const now = new Date();
      const pad = (n) => String(n).padStart(2, '0');
      setClock(`${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`);
    }
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="glass sticky top-0 z-40 flex items-center justify-between rounded-none border-x-0 border-t-0 px-6 py-3">
      <div className="flex items-center gap-3">
        <AtomLogo />
        <div>
          <Link to="/" className="font-display text-lg font-bold text-white">
            QUANTUM
            <span className="quantum-text">·AGIS</span>
          </Link>
          <p className="text-[11px] text-text-muted">
            Quantum-inspired Agentic Governance &amp; Intrusion Shield
          </p>
        </div>
      </div>

      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`pulse-dot inline-block h-2.5 w-2.5 rounded-full transition-all duration-300 ${
              wsConnected
                ? 'bg-quantum-green shadow-[0_0_8px_2px_rgba(0,255,136,0.6)]'
                : 'bg-quantum-red shadow-[0_0_8px_2px_rgba(255,51,102,0.6)]'
            }`}
          />
          <span className="text-text-secondary">
            WebSocket: {wsConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>
        <span className="font-data hidden text-sm text-quantum-cyan sm:inline">{clock}</span>
        <div
          className="hidden h-8 w-8 rounded-full bg-gradient-to-br from-quantum-cyan to-quantum-purple p-px sm:block"
          title="Operator"
        >
          <div className="flex h-full w-full items-center justify-center rounded-full bg-deep-space text-xs font-bold text-white">
            Q
          </div>
        </div>
      </div>
    </header>
  );
}
