import { useCallback, useState } from 'react';
import { verifySignature } from '../api/verification';
import useStore from '../store/useStore';

/**
 * Wraps POST /api/verify with loading/error state and mirrors the trust
 * score into the global store.
 * @returns {{verify: Function, result: object|null, isLoading: boolean, error: Error|null}} Verification controls.
 */
export function useVerification() {
  const setTrustScore = useStore((state) => state.setTrustScore);
  const setMetrics = useStore((state) => state.setMetrics);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  /**
   * Submit a signature for full-stack verification and store the response.
   * @param {string} signature - Signature payload.
   * @param {string} sessionId - Active session id.
   * @param {object} [channelSnapshot] - Optional layer flags (attack context).
   */
  const verify = useCallback(
    async (signature, sessionId, channelSnapshot) => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await verifySignature(signature, sessionId, channelSnapshot);
        setResult(data);
        if (typeof data.trust_score === 'number') {
          setTrustScore(data.trust_score);
        }
        if (data.layer_results) {
          setMetrics({ layer_results: data.layer_results });
        }
        return data;
      } catch (err) {
        setError(err);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [setTrustScore, setMetrics]
  );

  return { verify, result, isLoading, error };
}

export default useVerification;
