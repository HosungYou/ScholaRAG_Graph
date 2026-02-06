'use client';

import { useEffect, useRef } from 'react';

/**
 * Full-page cosmic starfield background.
 * Renders twinkling stars on a canvas with nebula CSS overlays.
 * Fixed position — sits behind all page content.
 */

interface Star {
  x: number;
  y: number;
  size: number;
  opacity: number;
  twinkleSpeed: number;
  twinklePhase: number;
  color: string;
}

const STAR_COLORS = [
  '#ffffff',
  '#e0e7ff',
  '#c7d2fe',
  '#a5b4fc',
  '#818cf8',
  '#22d3ee',
  '#c084fc',
];

export function CosmicStarfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const starsRef = useRef<Star[]>([]);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = document.documentElement.scrollHeight;
      initStars(canvas.width, canvas.height);
    };

    const initStars = (w: number, h: number) => {
      const count = Math.floor((w * h) / 3000);
      starsRef.current = Array.from({ length: Math.min(count, 600) }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        size: Math.random() < 0.92 ? 0.5 + Math.random() * 1.2 : 1.5 + Math.random() * 2,
        opacity: 0.3 + Math.random() * 0.7,
        twinkleSpeed: 0.005 + Math.random() * 0.02,
        twinklePhase: Math.random() * Math.PI * 2,
        color: STAR_COLORS[Math.floor(Math.random() * STAR_COLORS.length)],
      }));
    };

    let time = 0;
    const animate = () => {
      if (!canvas || !ctx) return;
      time += 1;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      starsRef.current.forEach((star) => {
        const twinkle = Math.sin(time * star.twinkleSpeed + star.twinklePhase);
        const alpha = star.opacity * (0.5 + 0.5 * twinkle);

        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fillStyle = star.color;
        ctx.globalAlpha = alpha;
        ctx.fill();

        // Glow for larger stars
        if (star.size > 1.5) {
          ctx.beginPath();
          ctx.arc(star.x, star.y, star.size * 3, 0, Math.PI * 2);
          ctx.fillStyle = star.color;
          ctx.globalAlpha = alpha * 0.15;
          ctx.fill();
        }
      });

      ctx.globalAlpha = 1;
      animRef.current = requestAnimationFrame(animate);
    };

    resize();
    animate();

    const resizeObserver = new ResizeObserver(() => resize());
    resizeObserver.observe(document.documentElement);

    return () => {
      cancelAnimationFrame(animRef.current);
      resizeObserver.disconnect();
    };
  }, []);

  return (
    <>
      {/* Starfield canvas */}
      <canvas
        ref={canvasRef}
        className="fixed inset-0 w-full h-full pointer-events-none"
        style={{ zIndex: 0 }}
        aria-hidden="true"
      />
      {/* Nebula overlays */}
      <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }} aria-hidden="true">
        {/* Top-left purple nebula */}
        <div
          className="absolute"
          style={{
            top: '-10%',
            left: '-10%',
            width: '60%',
            height: '50%',
            background: 'radial-gradient(ellipse, rgba(108, 60, 227, 0.12) 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
        {/* Center-right cyan nebula */}
        <div
          className="absolute"
          style={{
            top: '30%',
            right: '-5%',
            width: '50%',
            height: '40%',
            background: 'radial-gradient(ellipse, rgba(34, 211, 238, 0.08) 0%, transparent 70%)',
            filter: 'blur(100px)',
          }}
        />
        {/* Bottom magenta nebula */}
        <div
          className="absolute"
          style={{
            bottom: '5%',
            left: '20%',
            width: '40%',
            height: '35%',
            background: 'radial-gradient(ellipse, rgba(236, 72, 153, 0.06) 0%, transparent 70%)',
            filter: 'blur(90px)',
          }}
        />
        {/* Mid-section purple wash */}
        <div
          className="absolute"
          style={{
            top: '55%',
            left: '-5%',
            width: '45%',
            height: '30%',
            background: 'radial-gradient(ellipse, rgba(76, 29, 149, 0.1) 0%, transparent 65%)',
            filter: 'blur(70px)',
          }}
        />
      </div>
    </>
  );
}
