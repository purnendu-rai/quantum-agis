/**
 * @file Large attack launch button with icon, loading state, and a
 * success/failure (detected/bypassed) indicator after the run.
 */
import { useState } from 'react';

/**
 * Button that fires one attack run via the callback and reflects its outcome.
 * @param {object} props - Component props.
 * @param {string} props.label - Display name of the attack.
 * @param {string} props.attackType - Backend attack-type id.
 * @param {string} [props.icon] - Emoji icon shown above the label.
 * @param {string} [props.description] - One-line description of the strategy.
 * @param {(attackType: string, intensity: number) => Promise<object>} props.onLaunch - Async launcher.
 * @param {number} [props.intensity] - Attack strength in [0, 1].
 * @param {boolean} [props.disabled] - True while another attack runs.
 * @param {object|null} [props.result] - This attack's latest AttackResponse.
 * @returns {JSX.Element} Attack launch button.
 */
export default function AttackButton({
  label,
  attackType,
  icon = '⚔️',
  description = '',
  onLaunch,
  intensity = 0.5,
  disabled = false,
  result = null,
}) {
  const [running, setRunning] = useState(false);
  const busy = running || disabled;

  /**
   * Trigger the attack via the callback, toggling the busy indicator.
   * @returns {Promise<void>}
   */
  async function handleClick() {
    setRunning(true);
    try {
      await onLaunch?.(attackType, intensity);
    } finally {
      setRunning(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={busy}
      title={description}
      className="flex flex-col items-center gap-1 rounded-lg border border-rose-500/30 bg-rose-500/5 px-3 py-3 text-center transition-all hover:border-rose-400/60 hover:bg-rose-500/15 hover:shadow-[0_0_12px_rgba(255,34,68,0.25)] disabled:opacity-50"
    >
      <span className="text-xl">{busy ? '⏳' : icon}</span>
      <span className="text-xs font-medium text-rose-200">{label}</span>
      <span className="text-[10px] leading-tight text-slate-500">{description}</span>
      {result && (
        <span
          className={`text-[10px] font-semibold ${
            result.detected ? 'text-emerald-300' : 'text-rose-300'
          }`}
        >
          {result.detected ? '✓ detected' : '✗ bypassed'}
        </span>
      )}
    </button>
  );
}
