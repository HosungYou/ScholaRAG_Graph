'use client';

import { useRef, useEffect, useState } from 'react';
import { motion, useInView } from 'framer-motion';

interface StatItem {
  value: number;
  suffix?: string;
  label: string;
  color: string;
}

const stats: StatItem[] = [
  { value: 469, label: 'Concepts Extracted', color: '#22d3ee' },
  { value: 4170, label: 'Relationships Found', color: '#a78bfa' },
  { value: 6, label: 'AI Agents', color: '#c084fc' },
  { value: 34, label: 'Papers Analyzed', color: '#f472b6' },
  { value: 5, label: 'Topic Clusters', color: '#818cf8' },
  { value: 10, label: 'Research Gaps', color: '#22d3ee' },
];

function AnimatedNumber({ target, duration = 2000, inView }: { target: number; duration?: number; inView: boolean }) {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.floor(eased * target));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [inView, target, duration]);

  return <>{current.toLocaleString()}</>;
}

export function LiveStats() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <div ref={ref} className="w-full overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              className="relative text-center py-6 px-3 rounded-lg border backdrop-blur-sm group"
              style={{
                borderColor: `${stat.color}15`,
                background: `linear-gradient(135deg, ${stat.color}05, transparent)`,
              }}
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.08 }}
            >
              {/* Glow on hover */}
              <div
                className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                style={{
                  background: `radial-gradient(circle at 50% 50%, ${stat.color}10, transparent 70%)`,
                }}
              />
              <div
                className="font-mono text-3xl md:text-4xl font-bold mb-1 relative"
                style={{ color: stat.color }}
              >
                <AnimatedNumber target={stat.value} inView={inView} />
              </div>
              <div className="text-[11px] uppercase tracking-widest text-white/40 font-mono relative">
                {stat.label}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
