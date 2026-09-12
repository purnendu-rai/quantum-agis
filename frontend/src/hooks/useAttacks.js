import { useCallback, useState } from 'react';
import { runAttack } from '../api/attacks';
import useStore from '../store/useStore';

/**
 * Wraps POST /api/attack/{type} with loading/error state and mirrors the
 * post-attack trust score into the global store.
 * @returns {{launchAttack: Function, result: object|null, isLoading: boolean, error: Error|null}} Attack controls.
 */
export function useAttacks() {
  const addEvent = useStore((state) => state.addEvent);
  const setTrustScore = useStore((state) => state.setTrustScore);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  /**
   * Launch a simulated attack and record the outcome.
   * @param {string} attackType - AttackType enum value.
   * @param {number} intensity - Strength in [0, 1].
   * @param {string} sessionId - Target session id.
   * @returns {Promise<object|null>} AttackResponse payload (null on error).
   */
  const launchAttack = useCallback(
    async (attackType, intensity, sessionId) => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await runAttack(attackType, intensity, sessionId);
        setResult(data);
        addEvent({
          severity: 'warning',
          source: `attack.${attackType}`,
          message: `${attackType} ${data?.detected ? 'DETECTED' : 'BYPASSED'} | trust=${(
            data?.trust_score_after ?? 0
          ).toFixed(3)}`,
          timestamp: new Date().toISOString(),
        });
        if (typeof data?.trust_score_after === 'number') {
          setTrustScore(data.trust_score_after);
        }
        return data;
      } catch (err) {
        setError(err);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [addEvent, setTrustScore]
  );

  return { launchAttack, result, isLoading, error };
}

export default useAttacks;
