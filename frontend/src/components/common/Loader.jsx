/**
 * @file Quantum-themed loader: rotating atom spinner with optional label.
 */

/**
 * Atom spinner with label.
 * @param {object} props - Component props.
 * @param {string} [props.label] - Text shown next to the spinner.
 * @returns {JSX.Element} Loader element.
 */
export default function Loader({ label = 'Loading…' }) {
  return (
    <div className="flex items-center gap-3 text-sm text-slate-400" role="status" aria-live="polite">
      <svg width="34" height="34" viewBox="0 0 38 38" className="animate-spin" aria-hidden="true">
        <ellipse cx="19" cy="19" rx="15" ry="6.5" fill="none" stroke="#00f0ff" strokeWidth="1.4" opacity="0.9" />
        <ellipse cx="19" cy="19" rx="15" ry="6.5" fill="none" stroke="#a855f7" strokeWidth="1.4" opacity="0.9" transform="rotate(60 19 19)" />
        <ellipse cx="19" cy="19" rx="15" ry="6.5" fill="none" stroke="#0080ff" strokeWidth="1.4" opacity="0.9" transform="rotate(120 19 19)" />
        <circle cx="19" cy="19" r="2.6" fill="#00f0ff" />
      </svg>
      {label}
    </div>
  );
}
