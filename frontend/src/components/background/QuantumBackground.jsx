/**
 * @file Layered animated quantum background:
 *  L1 deep gradient · L2 particle field (100 particles, entanglement links)
 *  L3 circuit grid · L4 floating blurred orbs (Framer Motion).
 */
import ParticleField from "../animations/ParticleField.jsx";
import FloatingOrbs from "../animations/FloatingOrbs.jsx";

/**
 * Full-screen animated quantum background stack.
 * @returns {JSX.Element} Background layers.
 */
export default function QuantumBackground() {
  return (
    <>
      {/* L1: deep gradient */}
      <div
        aria-hidden="true"
        className="fixed inset-0 z-[-3]"
        style={{
          background:
            "linear-gradient(180deg, #030014 0%, #0a0a1f 55%, #13132e 100%)",
        }}
      />
      {/* L3: quantum circuit grid */}
      <div
        aria-hidden="true"
        className="quantum-grid fixed inset-0 z-[-2]"
      />
      {/* L2 + L4 */}
      <ParticleField />
      <FloatingOrbs />
    </>
  );
}
