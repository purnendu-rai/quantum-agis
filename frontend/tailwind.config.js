/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}", "./node_modules/@tremor/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Background layers
        void: "#030014",
        "deep-space": "#0a0a1f",
        cosmos: "#13132e",
        nebula: "#1a1a3e",
        // Quantum primary
        "quantum-cyan": "#00f0ff",
        "quantum-blue": "#0080ff",
        "quantum-purple": "#a855f7",
        "quantum-magenta": "#ff00ff",
        "quantum-green": "#00ff88",
        "quantum-red": "#ff3366",
        "quantum-amber": "#ffb800",
        "quantum-gold": "#ffd700",
        "quantum-violet": "#7c3aed",
        // Text
        "text-primary": "#ffffff",
        "text-secondary": "#a0a0c0",
        "text-muted": "#606080",
      },
      fontFamily: {
        sans: ["Outfit", "system-ui", "sans-serif"],
        data: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
        float: "float 6s ease-in-out infinite",
        "spin-slow": "spin 20s linear infinite",
        shimmer: "shimmer 2s linear infinite",
        scan: "scan 3s ease-in-out infinite",
        gradient: "gradient 8s ease infinite",
        orbit: "orbit 20s linear infinite",
        wave: "wave 3s ease-in-out infinite",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 20px rgba(0, 240, 255, 0.5)" },
          "50%": { opacity: "0.8", boxShadow: "0 0 40px rgba(0, 240, 255, 0.8)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        gradient: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        orbit: {
          "0%": { transform: "rotate(0deg) translateX(100px) rotate(0deg)" },
          "100%": { transform: "rotate(360deg) translateX(100px) rotate(-360deg)" },
        },
        wave: {
          "0%, 100%": { transform: "scale(1)" },
          "50%": { transform: "scale(1.05)" },
        },
      },
    },
  },
  plugins: [],
}
