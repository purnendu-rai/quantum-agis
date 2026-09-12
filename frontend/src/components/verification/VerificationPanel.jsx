/**
 * @file Panel for generating a signature, verifying it against the live
 * 6-layer stack, and inspecting the trust/decision/layer breakdown.
 */
import { useState } from 'react';
import { formatTrustScore } from '../../utils/formatters.js';
import useVerification from '../../hooks/useVerification.js';
import { useStore } from '../../store/useStore.js';
import Badge from '../common/Badge.jsx';
import Card from '../common/Card.jsx';
import Loader from '../common/Loader.jsx';
import SignatureInput from './SignatureInput.jsx';

/**
 * Build a fresh random legitimate-style signature string.
 * @returns {string} e.g. "AGIS-3f9c2a71b4".
 */
function generateSignature() {
  const hex = Array.from({ length: 10 }, () =>
    Math.floor(Math.random() * 16).toString(16)
  ).join('');
  return `AGIS-${hex}`;
}

/**
 * Verification console: signature input, generate/verify actions, and the
 * per-layer result breakdown from the live backend.
 * @returns {JSX.Element} Verification panel.
 */
export default function VerificationPanel() {
  const sessionId = useStore((state) => state.sessionId);
  const { verify, result, isLoading, error } = useVerification();
  const [signature, setSignature] = useState('');

  /**
   * Submit the current signature for verification.
   */
  async function handleVerify() {
    await verify(signature, sessionId);
  }

  return (
    <Card title="Signature Verification" subtitle="Full 6-layer AGIS stack">
      <SignatureInput
        value={signature}
        onChange={setSignature}
        onGenerate={() => setSignature(generateSignature())}
        onSubmit={handleVerify}
        busy={isLoading}
      />
      {isLoading && (
        <div className="mt-4">
          <Loader label="Running QGM → HIS → NHGS → TCP → MVS → BTFE…" />
        </div>
      )}
      {error && (
        <p className="mt-4 text-sm text-rose-300">
          Verification failed: {String(error?.message || error)}
        </p>
      )}
      {result && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              label={result.verdict.toUpperCase()}
              variant={
                result.verdict === 'authentic'
                  ? 'pass'
                  : result.verdict === 'rejected'
                    ? 'fail'
                    : 'suspicious'
              }
            />
            <span className="text-slate-300">
              decision: <span className="font-semibold text-quantum-blue">{result.decision}</span>
            </span>
            <span className="text-slate-400">trust {formatTrustScore(result.trust_score)}</span>
            <span className="text-slate-400">
              V_HOM {(result.hom_visibility * 100).toFixed(1)}%
            </span>
            <span className="text-slate-400">
              fidelity {(result.channel_fidelity * 100).toFixed(1)}%
            </span>
          </div>
          <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
            {result.layer_results.map((layer) => (
              <li
                key={layer.layer_id}
                className="flex items-center justify-between rounded border px-3 py-1.5"
                style={{ borderColor: 'rgba(0, 212, 255, 0.2)' }}
              >
                <span className="text-slate-300">
                  L{layer.layer_id} {layer.layer_name}
                </span>
                <span className="flex items-center gap-2">
                  <span className="text-xs text-slate-500">
                    conf {(layer.confidence * 100).toFixed(0)}%
                  </span>
                  <Badge
                    label={layer.verdict.toUpperCase()}
                    variant={
                      layer.verdict === 'authentic'
                        ? 'pass'
                        : layer.verdict === 'rejected'
                          ? 'fail'
                          : 'suspicious'
                    }
                  />
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
