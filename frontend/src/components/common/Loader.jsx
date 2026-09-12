/**
 * @file Loading indicator used while API calls are in flight.
 */

/**
 * Spinner with optional label.
 * @param {object} props - Component props.
 * @param {string} [props.label] - Text shown next to the spinner.
 * @returns {JSX.Element} Loader element.
 */
export default function Loader({ label = "Loading…" }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-400" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-cyan-400" />
      {label}
    </div>
  );
}
