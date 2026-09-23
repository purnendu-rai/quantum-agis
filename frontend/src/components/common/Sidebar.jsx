/**
 * @file Left navigation sidebar: icon nav with animated active state and
 * quantum-themed footer stats.
 */
import { FileText, Info, LayoutDashboard, Zap } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/attacks', label: 'Attack Simulator', Icon: Zap },
  { to: '/logs', label: 'Logs', Icon: FileText },
  { to: '/about', label: 'About', Icon: Info },
];

/**
 * Glass sidebar with quantum stats footer.
 * @returns {JSX.Element} Sidebar navigation.
 */
export default function Sidebar() {
  return (
    <nav className="glass sticky top-[65px] z-30 flex h-[calc(100vh-65px)] w-56 shrink-0 flex-col justify-between rounded-none border-y-0 border-l-0 px-3 py-4">
      <ul className="space-y-1">
        {NAV_ITEMS.map(({ to, label, Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-md border-l-2 px-3 py-2 text-sm font-medium tracking-normal transition-all duration-200 ${
                  isActive
                    ? 'border-l-quantum-cyan bg-gradient-to-r from-quantum-cyan/20 to-quantum-purple/20 text-white font-semibold shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                    : 'border-l-transparent text-slate-300 hover:translate-x-1 hover:border-slate-600 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              <Icon size={16} className="shrink-0" />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="border-t border-white/5 pt-3 text-center text-xs font-medium leading-relaxed text-slate-400">
        <span className="font-data tabular-nums font-semibold text-quantum-cyan">6</span> Layers ·{' '}
        <span className="font-data tabular-nums font-semibold text-quantum-purple">5</span> Attacks ·{' '}
        <span className="font-data tabular-nums font-semibold text-quantum-green">0</span> AI
      </div>
    </nav>
  );
}
