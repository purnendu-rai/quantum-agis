/**
 * @file Custom quantum cursor: glowing arrowhead that eases toward the
 * pointer, leaving a particle trail. Rendered on a full-screen canvas layer.
 * Desktop-only (fine pointer) and disabled under reduced-motion.
 */
import { useEffect, useRef } from "react";

/**
 * Quantum cursor overlay with particle trail.
 * @returns {null} Renders nothing into the React tree (canvas layer only).
 */
export default function QuantumCursor() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!finePointer || reducedMotion) return undefined;

    // Hide the native OS cursor while the quantum cursor layer is active.
    document.body.classList.add("quantum-cursor");

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let raf = 0;
    let running = true;

    /** Resize the canvas to the full viewport. */
    function resize() {
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    const state = {
      x: window.innerWidth / 2,
      y: window.innerHeight / 2,
      tx: window.innerWidth / 2,
      ty: window.innerHeight / 2,
      angle: 0,
      pressed: false,
      particles: [],
    };

    /** Spawn a few trail particles at the pointer. */
    function emitTrail(count) {
      for (let i = 0; i < count; i++) {
        if (state.particles.length > 90) state.particles.shift();
        state.particles.push({
          x: state.x,
          y: state.y,
          vx: (Math.random() - 0.5) * 1.6,
          vy: (Math.random() - 0.5) * 1.6 + 0.3,
          life: 1,
          size: 1 + Math.random() * 2.2,
          hue: Math.random() > 0.5 ? 187 : 270, // quantum cyan / purple
        });
      }
    }

    function onMove(event) {
      state.tx = event.clientX;
      state.ty = event.clientY;
    }
    function onDown() {
      state.pressed = true;
      emitTrail(14);
    }
    function onUp() {
      state.pressed = false;
    }

    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("mousedown", onDown);
    window.addEventListener("mouseup", onUp);

    let lastEmit = 0;
    /** Animation loop: ease cursor, update particles, draw. */
    function frame(timestamp) {
      if (!running) return;
      // Ease toward the pointer (the trailing feel).
      state.x += (state.tx - state.x) * 0.22;
      state.y += (state.ty - state.y) * 0.22;

      const dx = state.tx - state.x;
      const dy = state.ty - state.y;
      const speed = Math.hypot(dx, dy);
      if (speed > 0.5) state.angle = Math.atan2(dy, dx);
      if (speed > 2 && timestamp - lastEmit > 28) {
        emitTrail(2);
        lastEmit = timestamp;
      }

      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

      // Particle trail.
      for (let i = state.particles.length - 1; i >= 0; i--) {
        const p = state.particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.life -= 0.022;
        if (p.life <= 0) {
          state.particles.splice(i, 1);
          continue;
        }
        ctx.globalAlpha = p.life * 0.85;
        ctx.fillStyle = `hsl(${p.hue} 100% ${55 + p.life * 15}%)`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      // Glow ring.
      ctx.save();
      ctx.translate(state.x, state.y);
      const ringRadius = state.pressed ? 15 : 11;
      ctx.strokeStyle = state.pressed ? "rgba(106, 13, 173, 0.9)" : "rgba(0, 212, 255, 0.75)";
      ctx.lineWidth = state.pressed ? 2.5 : 1.5;
      ctx.shadowColor = state.pressed ? "rgba(106, 13, 173, 0.9)" : "rgba(0, 212, 255, 0.9)";
      ctx.shadowBlur = 14;
      ctx.beginPath();
      ctx.arc(0, 0, ringRadius, 0, Math.PI * 2);
      ctx.stroke();

      // Arrowhead pointing along movement direction.
      ctx.rotate(state.angle);
      ctx.fillStyle = state.pressed ? "#6a0dad" : "#00d4ff";
      ctx.beginPath();
      ctx.moveTo(9, 0);
      ctx.lineTo(-5, 5);
      ctx.lineTo(-2, 0);
      ctx.lineTo(-5, -5);
      ctx.closePath();
      ctx.fill();
      ctx.restore();

      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      document.body.classList.remove("quantum-cursor");
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-[9999]"
    />
  );
}
