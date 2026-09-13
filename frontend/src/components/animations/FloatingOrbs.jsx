/**
 * @file Floating gradient orbs (Framer Motion) — three large blurred circles
 * drifting slowly behind the content for depth.
 */
import { motion } from "framer-motion";

const ORBS = [
  { color: "#00f0ff", size: 420, x: "8%", y: "6%", duration: 26 },
  { color: "#a855f7", size: 380, x: "72%", y: "60%", duration: 32 },
  { color: "#0080ff", size: 340, x: "45%", y: "35%", duration: 22 },
];

/**
 * Three blurred quantum orbs, GPU-animated with transform only.
 * @returns {JSX.Element} Orb layer.
 */
export default function FloatingOrbs() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      {ORBS.map((orb) => (
        <motion.div
          key={orb.color}
          className="absolute rounded-full"
          style={{
            width: orb.size,
            height: orb.size,
            left: orb.x,
            top: orb.y,
            background: `radial-gradient(circle, ${orb.color}55 0%, transparent 70%)`,
            filter: "blur(100px)",
            opacity: 0.2,
          }}
          animate={{
            x: [0, 60, -40, 0],
            y: [0, -50, 30, 0],
          }}
          transition={{ duration: orb.duration, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}
