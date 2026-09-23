/**
 * @file Colored status badge (pass/fail/suspicious/info and verdict tones).
 */
const VARIANTS = {
  pass: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  fail: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
  suspicious: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  info: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40',
  gray: 'bg-slate-500/15 text-slate-300 border-slate-500/40',
  green: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  amber: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  red: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
  blue: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40',
};

/**
 * Inline badge for statuses such as PASS / FAIL / SUSPICIOUS / INFO.
 * @param {object} props - Component props.
 * @param {string} props.label - Badge text.
 * @param {keyof typeof VARIANTS} [props.variant] - Color scheme key
 *   (pass | fail | suspicious | info, or legacy green/amber/red/blue/gray).
 * @returns {JSX.Element} Badge element.
 */
export default function Badge({ label, variant = 'gray', tone }) {
  const key = VARIANTS[variant] ? variant : tone && VARIANTS[tone] ? tone : 'gray';
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold tracking-wider uppercase tabular-nums shadow-sm ${VARIANTS[key]}`}
    >
      {label}
    </span>
  );
}
