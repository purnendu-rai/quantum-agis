/**
 * @file Glassmorphism card with gradient border option and hover lift.
 */
import { motion } from "framer-motion";
import clsx from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Premium glass card.
 * @param {object} props - Component props.
 * @param {string} [props.title] - Card title.
 * @param {string} [props.subtitle] - Secondary line under the title.
 * @param {React.ReactNode} props.children - Card body.
 * @param {string} [props.className] - Extra classes.
 * @param {string} [props.accent] - Accent color for the title glow.
 * @param {boolean} [props.hoverLift] - Lift on hover (default true).
 * @returns {JSX.Element} Glass card.
 */
export default function GlassCard({ title, subtitle, children, className = "", accent = "#00f0ff", hoverLift = true }) {
  return (
    <motion.section
      whileHover={hoverLift ? { y: -4 } : undefined}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
      className={twMerge(
        clsx(
          "relative overflow-hidden rounded-xl border border-white/10 bg-cosmos/60 p-4 backdrop-blur-xl",
          "hover:border-quantum-cyan/30 hover:shadow-[0_0_30px_rgba(0,240,255,0.12)]",
          className
        )
      )}
    >
      {/* Top accent line */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${accent}88, transparent)` }}
      />
      {title && (
        <h3 className="text-sm font-semibold tracking-tight text-white">
          {title}
          <span className="ml-2 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: accent, boxShadow: `0 0 8px ${accent}` }} />
        </h3>
      )}
      {subtitle && <p className="mt-0.5 text-xs text-text-secondary">{subtitle}</p>}
      <div className={title || subtitle ? "mt-3" : ""}>{children}</div>
    </motion.section>
  );
}
