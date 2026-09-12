/**
 * @file Controlled signature input with mode-aware generate helper.
 */

/**
 * Controlled input capturing the signature to verify.
 * @param {object} props - Component props.
 * @param {string} props.value - Current signature text.
 * @param {(value: string) => void} props.onChange - Text change handler.
 * @param {() => void} props.onGenerate - Fill the input with a generated signature.
 * @param {string} [props.generateLabel] - Label of the generate button (mode-aware).
 * @param {string} [props.generateClass] - Tailwind classes for the generate button.
 * @param {() => void} props.onSubmit - Submit the current signature for verification.
 * @param {boolean} [props.busy] - True while verification is in flight.
 * @returns {JSX.Element} Signature input controls.
 */
export default function SignatureInput({
  value,
  onChange,
  onGenerate,
  generateLabel = "🎲 Generate Legitimate Signature",
  generateClass = "border-quantum-purple/50 bg-quantum-purple/20 text-purple-200 hover:bg-quantum-purple/30",
  onSubmit,
  busy = false,
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && value && !busy) onSubmit();
        }}
        placeholder="Paste or generate a quantum signature…"
        className="min-w-48 flex-1 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-quantum-blue focus:outline-none"
      />
      <button
        type="button"
        onClick={onGenerate}
        className={`rounded border px-3 py-2 text-sm ${generateClass}`}
      >
        {generateLabel}
      </button>
      <button
        type="submit"
        disabled={busy || !value}
        onClick={(event) => {
          event.preventDefault();
          onSubmit();
        }}
        className="rounded border border-quantum-blue/40 bg-quantum-blue/10 px-4 py-2 text-sm text-cyan-200 hover:bg-quantum-blue/20 hover:shadow-[0_0_10px_rgba(0,212,255,0.3)] disabled:opacity-50"
      >
        {busy ? "Verifying…" : "Verify Signature"}
      </button>
    </div>
  );
}
