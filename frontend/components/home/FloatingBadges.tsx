'use client';

import { motion } from 'framer-motion';

interface Badge {
  label: string;
  color: string;
  x: string;
  y: string;
  delay: number;
}

const badges: Badge[] = [
  { label: 'Neo4j', color: '#22d3ee', x: '5%', y: '15%', delay: 0 },
  { label: 'pgvector', color: '#a78bfa', x: '78%', y: '8%', delay: 0.3 },
  { label: 'Claude', color: '#c084fc', x: '88%', y: '55%', delay: 0.6 },
  { label: 'React Flow', color: '#818cf8', x: '2%', y: '65%', delay: 0.9 },
  { label: 'GraphRAG', color: '#f472b6', x: '42%', y: '85%', delay: 1.2 },
  { label: 'LangChain', color: '#34d399', x: '70%', y: '78%', delay: 0.4 },
  { label: 'Next.js', color: '#e0e7ff', x: '15%', y: '88%', delay: 0.7 },
  { label: 'PostgreSQL', color: '#60a5fa', x: '55%', y: '5%', delay: 1.0 },
];

export function FloatingBadges() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
      {badges.map((badge) => (
        <motion.div
          key={badge.label}
          className="absolute"
          style={{ left: badge.x, top: badge.y }}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{
            opacity: [0, 0.7, 0.5, 0.7],
            scale: [0.5, 1, 0.95, 1],
            y: [0, -8, 4, -8],
          }}
          transition={{
            duration: 6,
            delay: badge.delay,
            repeat: Infinity,
            repeatType: 'reverse',
            ease: 'easeInOut',
          }}
        >
          <span
            className="inline-block px-3 py-1.5 text-xs font-mono font-medium rounded-sm backdrop-blur-md border"
            style={{
              color: badge.color,
              borderColor: `${badge.color}30`,
              backgroundColor: `${badge.color}10`,
            }}
          >
            {badge.label}
          </span>
        </motion.div>
      ))}
    </div>
  );
}
