/**
 * @file Quantum field background: drifting entangled particles that link to
 * the pointer with faint "entanglement" lines. Disabled under reduced motion
 * (requestAnimationFrame also auto-pauses in hidden tabs).
 */
import { useEffect, useRef } from "react";

const PARTICLE_COUNT = 55;
const LINK_DISTANCE = 130;

/**
 * Full-screen quantum particle field.
 * @returns {null} Renders nothing into the React tree (canvas layer only).
 */
export default function QuantumBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) return undefined;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let raf = 0;

    /** Resize the canvas to the viewport. */
    function resize() {
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    const particles = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      size: 0.8 + Math.random() * 1.8,
      hue: Math.random() > 0.6 ? 270 : 187,
    }));
    const pointer = { x: -9999, y: -9999 };

    function onMove(event) {
      pointer.x = event.clientX;
      pointer.y = event.clientY;
    }
    window.addEventListener("mousemove", onMove, { passive: true });

    /** Animation loop: drift particles, draw links to the pointer. */
    function frame() {
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > window.innerWidth) p.vx *= -1;
        if (p.y < 0 || p.y > window.innerHeight) p.vy *= -1;

        // Pointer entanglement: link nearby particles to the cursor.
        const pd = Math.hypot(p.x - pointer.x, p.y - pointer.y);
        if (pd < LINK_DISTANCE) {
          ctx.globalAlpha = (1 - pd / LINK_DISTANCE) * 0.35;
          ctx.strokeStyle = "rgba(0, 212, 255, 0.8)";
          ctx.lineWidth = 0.6;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(pointer.x, pointer.y);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }

      for (const p of particles) {
        ctx.globalAlpha = 0.55;
        ctx.fillStyle = `hsl(${p.hue} 100% 65%)`;
        ctx.shadowColor = `hsl(${p.hue} 100% 65%)`;
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      ctx.shadowBlur = 0;

      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0"
    />
  );
}
