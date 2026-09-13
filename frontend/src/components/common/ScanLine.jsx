/**
 * @file Animated scan line overlay — sweeps top-to-bottom inside its parent.
 */

/**
 * Decorative scan line (position absolute, parent needs relative + overflow hidden).
 * @param {object} [props] - Component props.
 * @param {string} [props.color] - Scan line tint.
 * @returns {JSX.Element} Scan line overlay.
 */
export default function ScanLine({ color = "rgba(0, 240, 255, 0.07)" }) {
  return (
    <div aria-hidden="true" className="scanline">
      <style>{`.scanline::after { background: linear-gradient(180deg, transparent, ${color}, transparent); }`}</style>
    </div>
  );
}
