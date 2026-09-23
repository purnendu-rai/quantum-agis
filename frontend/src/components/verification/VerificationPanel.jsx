/**
 * @file Panel for generating legitimate, tampered, or forged signatures and
 * watching the 6-layer stack accept or reject them — the core judge demo.
 */
import { useState } from "react";
import { formatTrustScore } from "../../utils/formatters.js";
import useVerification from "../../hooks/useVerification.js";
import { useStore } from "../../store/useStore.js";
import Badge from "../common/Badge.jsx";
import Card from "../common/Card.jsx";
import Loader from "../common/Loader.jsx";
import SignatureInput from "./SignatureInput.jsx";

/**
 * Build a fresh random legitimate-style signature string.
 * @returns {string} e.g. "AGIS-3f9c2a71b4".
 */
function generateLegitSignature() {
  const hex = Array.from({ length: 10 }, () =>
    Math.floor(Math.random() * 16).toString(16)
  ).join("");
  return `AGIS-${hex}`;
}

/** Flip ~25% of a signature's characters to simulate bit-level corruption. */
function tamperSignature(signature) {
  const chars = signature.split("");
  const flipped = chars.map((char, index) =>
    index > 0 && index % 4 === 0 ? String.fromCharCode(33 + ((char.charCodeAt(0) * 7) % 90)) : char
  );
  return flipped.join("");
}

/**
 * Demo modes: each generates a different signature class and passes the
 * matching adversarial flags to the verification pipeline.
 */
const MODES = {
  legitimate: {
    label: "Legitimate",
    chip: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
    flags: {},
    generate: () => generateLegitSignature(),
    generateLabel: "🎲 Generate Legitimate Signature",
    generateClass: "border-quantum-purple/50 bg-quantum-purple/20 text-purple-200 hover:bg-quantum-purple/30",
    hint: "Honest signer — qubit outcomes agree with the public key in every sifted basis. Expect ACCEPT (match rate 1.0, V_HOM 0.98).",
    expected: { verdict: "AUTHENTIC", variant: "pass" },
  },
  tampered: {
    label: "Tampered",
    chip: "border-amber-500/50 bg-amber-500/10 text-amber-300",
    flags: { tampered: true },
    generate: () => tamperSignature(generateLegitSignature()),
    generateLabel: "🦠 Generate Tampered Signature",
    generateClass: "border-amber-500/50 bg-amber-500/20 text-amber-200 hover:bg-amber-500/30",
    hint: "~25% of signature bits corrupted in transit — match rate drops to ~0.70 and the NH spectrum drifts. Expect REJECT.",
    expected: { verdict: "REJECTED", variant: "fail" },
  },
  forged: {
    label: "Forged",
    chip: "border-rose-500/50 bg-rose-500/10 text-rose-300",
    flags: { forged: true },
    generate: () => `FRG-${generateLegitSignature().slice(5)}`,
    generateLabel: "⚔️ Generate Forged Signature",
    generateClass: "border-rose-500/50 bg-rose-500/20 text-rose-200 hover:bg-rose-500/30",
    hint: "Attacker fabricates the signature without the quantum key — outcomes are random guesses (match rate ≈ 0.50 = the random-guess floor, V_HOM collapses). Expect REJECT.",
    expected: { verdict: "REJECTED", variant: "fail" },
  },
};

/**
 * Verification console: pick a signature class, generate it, verify it
 * against the live 6-layer stack, and inspect the per-layer breakdown.
 * @returns {JSX.Element} Verification panel.
 */
export default function VerificationPanel() {
  const sessionId = useStore((state) => state.sessionId);
  const { verify, result, isLoading, error } = useVerification();
  const [signature, setSignature] = useState("");
  const [mode, setMode] = useState("legitimate");
  const active = MODES[mode];

  /**
   * Submit the current signature for verification with the mode's flags.
   */
  async function handleVerify() {
    await verify(signature, sessionId, active.flags);
  }

  /**
   * Generate a signature of the selected class.
   */
  function handleGenerate() {
    setSignature(active.generate());
  }

  return (
    <Card title="Signature Verification" subtitle="Full 6-layer AGIS stack — test legitimate, tampered, and forged signatures">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-400">Signature class:</span>
        {Object.entries(MODES).map(([key, config]) => (
          <button
            key={key}
            type="button"
            onClick={() => setMode(key)}
            className={`rounded-md border px-3.5 py-1 text-xs font-semibold tracking-wide transition-all ${
              mode === key ? config.chip : "border-slate-700 text-slate-400 hover:text-slate-200"
            }`}
          >
            {config.label}
          </button>
        ))}
      </div>
      <SignatureInput
        value={signature}
        onChange={setSignature}
        onGenerate={handleGenerate}
        generateLabel={active.generateLabel}
        generateClass={active.generateClass}
        onSubmit={handleVerify}
        busy={isLoading}
      />
      <p className="mt-2 text-xs leading-relaxed text-slate-300">{active.hint}</p>
      {isLoading && (
        <div className="mt-4">
          <Loader label="Running QGM → HIS → NHGS → TCP → MVS → BTFE…" />
        </div>
      )}
      {error && (
        <p className="mt-4 text-sm font-medium text-rose-300">
          Verification failed: {String(error?.message || error)}
        </p>
      )}
      {result && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2.5">
            <Badge
              label={result.verdict.toUpperCase()}
              variant={
                result.verdict === "authentic"
                  ? "pass"
                  : result.verdict === "rejected"
                    ? "fail"
                    : "suspicious"
              }
            />
            <span className="text-xs font-medium text-slate-300">
              decision: <span className="font-bold text-quantum-cyan">{result.decision}</span>
            </span>
            <span className="font-data tabular-nums text-xs font-medium text-slate-300">trust {formatTrustScore(result.trust_score)}</span>
            <span className="font-data tabular-nums text-xs font-medium text-slate-300">
              V_HOM {(result.hom_visibility * 100).toFixed(1)}%
            </span>
            <span className="font-data tabular-nums text-xs font-medium text-slate-300">
              fidelity {(result.channel_fidelity * 100).toFixed(1)}%
            </span>
            <span className="text-xs font-medium text-slate-400">tested: {MODES[mode].label}</span>
          </div>
          {result.decision !== "ACCEPT" && (
            <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3.5 py-2 text-xs font-medium leading-relaxed text-rose-200">
              🚨 Threat detected: this {MODES[mode].label.toLowerCase()} signature failed
              verification — measurement statistics deviated beyond the acceptance thresholds,
              so the stack refused the signature.
            </p>
          )}
          <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
            {result.layer_results.map((layer) => (
              <li
                key={layer.layer_id}
                className="flex items-center justify-between rounded-lg border px-3 py-1.5 bg-slate-950/40"
                style={{ borderColor: "rgba(0, 240, 255, 0.2)" }}
              >
                <span className="text-xs font-medium text-slate-200">
                  <span className="font-data tabular-nums font-semibold text-quantum-cyan mr-1.5">L{layer.layer_id}</span>
                  {layer.layer_name}
                </span>
                <span className="flex items-center gap-2">
                  <span className="font-data tabular-nums text-xs font-medium text-slate-400">
                    conf {(layer.confidence * 100).toFixed(0)}%
                  </span>
                  <Badge
                    label={layer.verdict.toUpperCase()}
                    variant={
                      layer.verdict === "authentic"
                        ? "pass"
                        : layer.verdict === "rejected"
                          ? "fail"
                          : "suspicious"
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
