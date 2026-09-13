/**
 * @file Panel hosting the attack-simulation controls, per-layer deviation
 * visualisation, and the primary-detector readout.
 */
import { useState } from 'react';
import { runAttack } from '../../api/attacks.js';
import { ATTACK_TYPE_LABELS, LAYER_NAMES } from '../../utils/constants.js';
import { useStore } from '../../store/useStore.js';
import useAttacks from '../../hooks/useAttacks.js';
import Badge from '../common/Badge.jsx';
import Card from '../common/Card.jsx';
import AttackButton from './AttackButton.jsx';

/** Icon + description per attack strategy, keyed by backend attack id. */
const ATTACK_META = {
  forgery: { icon: '🖋️', description: 'Fabricated quantum signature injection' },
  impersonation: { icon: '🎭', description: 'Stolen identity-seal replay' },
  replay: { icon: '⏱️', description: 'Retransmission of a stale exchange' },
  channel_tampering: { icon: '⚡', description: 'Active noise on the quantum channel' },
  coherent: { icon: '🌐', description: 'Coordinated full-spectrum adversary' },
};

/**
 * Derive the layer most responsible for detection (highest deviation).
 * @param {object} [details] - AttackResponse.details with a deviations map.
 * @returns {{layer: string, deviation: number}|null} Primary detector, if any.
 */
function primaryDetector(details) {
  const deviations = details?.deviations;
  if (!deviations) return null;
  const entries = Object.entries(deviations).sort((a, b) => b[1] - a[1]);
  return entries.length ? { layer: entries[0][0], deviation: entries[0][1] } : null;
}

/**
 * Attack console: launch any of the five strategies against the live stack,
 * then inspect the detection verdict and per-layer deviation bars.
 * @returns {JSX.Element} Attack panel.
 */
export default function AttackPanel() {
  const sessionId = useStore((state) => state.sessionId);
  const setTrustScore = useStore((state) => state.setTrustScore);
  const { launchAttack, result, isLoading, error } = useAttacks();
  const [intensity, setIntensity] = useState(0.6);

  /**
   * Run one attack through the API and mirror the trust score into the store.
   * @param {string} attackType - Backend attack id.
   * @param {number} intensity - Strength in [0, 1].
   * @returns {Promise<object|null>} AttackResponse payload.
   */
  async function handleLaunch(attackType, intensity) {
    const data = await launchAttack(attackType, intensity, sessionId);
    if (data && typeof data.trust_score_after === 'number') {
      setTrustScore(data.trust_score_after);
    }
    return data;
  }

  const detector = primaryDetector(result?.details);
  const deviations = result?.details?.deviations ?? {};

  return (
    <Card title="Attack Simulator" subtitle="Adversarial scenarios against the live 6-layer stack">
      <div className="mb-4 flex items-center gap-3 text-xs text-slate-400">
        <span>attack intensity:</span>
        <input
          type="range"
          min="0.1"
          max="1"
          step="0.05"
          value={intensity}
          onChange={(event) => setIntensity(Number(event.target.value))}
          className="flex-1 accent-rose-400"
        />
        <span className="w-10 font-mono text-rose-300">{intensity.toFixed(2)}</span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {ATTACK_TYPE_LABELS.map((attack) => (
          <AttackButton
            key={attack.id}
            label={attack.label}
            attackType={attack.id}
            icon={ATTACK_META[attack.id]?.icon ?? '⚔️'}
            description={ATTACK_META[attack.id]?.description ?? ''}
            disabled={isLoading}
            onLaunch={handleLaunch}
            intensity={intensity}
            result={result?.attack_type === attack.id ? result : null}
          />
        ))}
      </div>

      {isLoading && <p className="mt-4 animate-pulse text-sm text-quantum-blue">Executing attack…</p>}
      {error && (
        <p className="mt-4 text-sm text-rose-300">Attack failed: {String(error?.message || error)}</p>
      )}

      {result && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge label={result.detected ? 'DETECTED' : 'BYPASSED'} variant={result.detected ? 'pass' : 'fail'} />
            <span className="text-slate-300">{result.attack_type}</span>
            <span className="text-slate-400">
              trust after:{' '}
              <span className="font-mono text-quantum-blue">
                {(result.trust_score_after * 100).toFixed(1)}%
              </span>
            </span>
            {detector && (
              <span className="text-slate-400">
                detected by <span className="font-semibold text-amber-300">{detector.layer}</span>{' '}
                (deviation {detector.deviation.toFixed(3)})
              </span>
            )}
          </div>
          <div className="space-y-1.5">
            {LAYER_NAMES.map((name) => {
              const value = deviations[name];
              if (typeof value !== 'number') return null;
              return (
                <div key={name} className="flex items-center gap-2 text-xs">
                  <span className="w-12 text-slate-400">{name}</span>
                  <div className="h-2 flex-1 rounded bg-slate-800">
                    <div
                      className="h-2 rounded transition-all"
                      style={{
                        width: `${Math.min(100, value * 100)}%`,
                        background: value > 0.25 ? '#ff2244' : value > 0.05 ? '#ffaa00' : '#22c55e',
                      }}
                    />
                  </div>
                  <span className="w-14 text-right font-mono text-slate-400">
                    {value.toFixed(3)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}
