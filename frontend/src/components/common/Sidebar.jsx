/**
 * @file Left navigation sidebar with quantum-blue active highlight.
 */
import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/attacks', label: 'Attack Simulator' },
  { to: '/logs', label: 'Logs' },
  { to: '/about', label: 'About' },
];

/**
 * Fixed sidebar listing the primary application pages. The active link gets
 * a quantum-blue left border and glow.
 * @returns {JSX.Element} Sidebar navigation.
 */
export default function Sidebar() {
  return (
    <nav
      className="w-56 shrink-0 border-r px-3 py-4"
      style={{ borderColor: 'rgba(0, 212, 255, 0.2)' }}
    >
      <ul className="space-y-1">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              className={({ isActive }) =>
                `block rounded-md border-l-2 px-3 py-2 text-sm transition-all ${
                  isActive
                    ? 'border-quantum-blue bg-slate-900 text-quantum-blue shadow-[0_0_10px_rgba(0,212,255,0.25)]'
                    : 'border-transparent text-slate-300 hover:border-slate-600 hover:bg-slate-900/60'
                }`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
