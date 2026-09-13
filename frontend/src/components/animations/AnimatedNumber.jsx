/**
 * @file Smooth counting number — animated with Framer Motion's `animate`.
 */
import { useEffect, useRef, useState } from 'react';
import { animate } from 'framer-motion';

/**
 * Animated number that counts to the target when it changes.
 * @param {object} props - Component props.
 * @param {number} props.value - Target numeric value.
 * @param {number} [props.decimals] - Decimal places (default 1).
 * @param {string} [props.suffix] - Suffix after the number.
 * @param {number} [props.duration] - Animation seconds (default 0.6).
 * @param {string} [props.className] - Extra classes.
 * @returns {JSX.Element} Counting number span.
 */
export default function AnimatedNumber({ value, decimals = 1, suffix = '', duration = 0.6, className = '' }) {
  const safe = Number.isFinite(value) ? value : 0;
  const [display, setDisplay] = useState(safe);
  const previous = useRef(safe);

  useEffect(() => {
    const controls = animate(previous.current, safe, {
      duration,
      ease: 'easeOut',
      onUpdate: (latest) => setDisplay(latest),
    });
    previous.current = safe;
    return () => controls.stop();
  }, [safe, duration]);

  return (
    <span className={className}>
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}
