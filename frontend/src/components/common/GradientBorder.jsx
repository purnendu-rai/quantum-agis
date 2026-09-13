/**
 * @file Gradient border wrapper — a 1px gradient frame around any content.
 */

/**
 * Gradient border container.
 * @param {object} props - Component props.
 * @param {React.ReactNode} props.children - Wrapped content.
 * @param {string} [props.from] - Gradient start color.
 * @param {string} [props.to] - Gradient end color.
 * @param {string} [props.className] - Extra classes for the inner box.
 * @returns {JSX.Element} Gradient-bordered content.
 */
export default function GradientBorder({ children, from = "#00f0ff", to = "#a855f7", className = "" }) {
  return (
    <div
      className="rounded-xl p-px"
      style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}
    >
      <div className={`rounded-[11px] bg-void ${className}`}>{children}</div>
    </div>
  );
}
