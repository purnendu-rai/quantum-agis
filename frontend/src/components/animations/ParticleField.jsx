/**
 * @file Canvas particle field: 100 glowing quantum particles with
 * entanglement lines between neighbours and to the pointer. 60fps target,
 * capped particle count, disabled under reduced motion.
 */
import { useEffect, useRef } from "react";

const PARTICLE_COUNT = 100;
const LINK_DISTANCE = 120;

/**
 * Quantum entanglement particle field.
 * @returns {null} Renders nothing into the React tree.
 */
export default function ParticleField() {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;

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
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      size: 0.7 + Math.random() * 1.6,
      cyan: Math.random() > 0.45,
    }));
    const pointer = { x: -9999, y: -9999 };

    function onMove(event) {
      pointer.x = event.clientX;
      pointer.y = event.clientY;
    }
    window.addEventListener("mousemove", onMove, { passive: true });

    /** Animation loop: drift, entangle neighbours, link to the pointer. */
    function frame() {
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

      // Neighbour entanglement lines.
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i];
          const b = particles[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < LINK_DISTANCE) {
            ctx.globalAlpha = (1 - d / LINK_DISTANCE) * 0.14;
            ctx.strokeStyle = a.cyan ? "rgba(0, 240, 255, 1)" : "rgba(168, 85, 247, 1)";
            ctx.lineWidth = 0.5;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      // Pointer entanglement.
      for (const p of particles) {
        const pd = Math.hypot(p.x - pointer.x, p.y - pointer.y);
        if (pd < LINK_DISTANCE) {
          ctx.globalAlpha = (1 - pd / LINK_DISTANCE) * 0.4;
          ctx.strokeStyle = "rgba(0, 240, 255, 0.9)";
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(pointer.x, pointer.y);
          ctx.stroke();
        }
      }

      // Particles.
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > window.innerWidth) p.vx *= -1;
        if (p.y < 0 || p.y > window.innerHeight) p.vy *= -1;
        ctx.globalAlpha = 0.7;
        ctx.fillStyle = p.cyan ? "rgba(0, 240, 255, 1)" : "rgba(168, 85, 247, 1)";
        ctx.shadowColor = p.cyan ? "rgba(0, 240, 255, 0.9)" : "rgba(168, 85, 247, 0.9)";
        ctx.shadowBlur = 5;
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
