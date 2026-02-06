'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Box,
  Layers,
  Target,
  Calendar,
  GitBranch,
  Workflow,
} from 'lucide-react';

interface ViewMode {
  id: string;
  label: string;
  icon: React.ReactNode;
  color: string;
  description: string;
  features: string[];
}

const viewModes: ViewMode[] = [
  {
    id: '3d',
    label: '3D Graph',
    icon: <Box className="w-5 h-5" />,
    color: '#22d3ee',
    description: 'Interactive 3D knowledge graph with polygon-shaped entity nodes, force-directed layout, and real-time clustering visualization.',
    features: ['Force-directed layout', 'Entity type filtering', 'Zoom & rotate', 'Node selection'],
  },
  {
    id: 'topic',
    label: 'Topics',
    icon: <Layers className="w-5 h-5" />,
    color: '#a78bfa',
    description: 'AI-powered topic clustering that groups related concepts and shows inter-cluster relationships with LLM-summarized labels.',
    features: ['LLM cluster labels', 'Concept grouping', 'Cluster statistics', 'Keyword extraction'],
  },
  {
    id: 'gaps',
    label: 'Gaps',
    icon: <Target className="w-5 h-5" />,
    color: '#f472b6',
    description: 'Structural gap detection between concept clusters, with AI-generated research questions and paper recommendations.',
    features: ['Gap detection', 'Research questions', 'Paper recommendations', 'Report export'],
  },
  {
    id: 'temporal',
    label: 'Temporal',
    icon: <Calendar className="w-5 h-5" />,
    color: '#fbbf24',
    description: 'Time-axis visualization showing concept emergence by publication year with D3.js bar charts and cumulative growth lines.',
    features: ['Year-by-year bars', 'Cumulative line', 'Top concepts per year', 'Date range filter'],
  },
  {
    id: 'citations',
    label: 'Citations',
    icon: <GitBranch className="w-5 h-5" />,
    color: '#34d399',
    description: 'Litmaps-style paper citation scatter plot built on-demand from Semantic Scholar, showing citation relationships and influence.',
    features: ['Scatter plot (year vs citations)', 'On-demand S2 fetch', 'Local vs external papers', 'DOI linking'],
  },
  {
    id: 'flow',
    label: 'Concept Flow',
    icon: <Workflow className="w-5 h-5" />,
    color: '#c084fc',
    description: 'Unique to ScholaRAG: traces how concepts propagate through citation chains, revealing which ideas influenced which research directions.',
    features: ['Concept-level flow', 'Force-directed graph', 'Citation weight edges', 'Knowledge propagation'],
  },
];

export function ViewModePreview() {
  const [active, setActive] = useState('3d');
  const activeMode = viewModes.find((m) => m.id === active)!;

  return (
    <div className="max-w-6xl mx-auto px-6">
      {/* Tab bar */}
      <div className="flex flex-wrap justify-center gap-2 mb-8">
        {viewModes.map((mode) => {
          const isActive = mode.id === active;
          return (
            <button
              key={mode.id}
              onClick={() => setActive(mode.id)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-medium transition-all duration-300 border"
              style={{
                color: isActive ? mode.color : 'rgba(255,255,255,0.4)',
                borderColor: isActive ? `${mode.color}40` : 'rgba(255,255,255,0.06)',
                backgroundColor: isActive ? `${mode.color}10` : 'transparent',
                boxShadow: isActive ? `0 0 20px ${mode.color}15` : 'none',
              }}
            >
              {mode.icon}
              <span className="hidden sm:inline">{mode.label}</span>
            </button>
          );
        })}
      </div>

      {/* Preview panel */}
      <AnimatePresence mode="wait">
        <motion.div
          key={active}
          className="relative rounded-lg border backdrop-blur-md overflow-hidden"
          style={{
            borderColor: `${activeMode.color}20`,
            background: `linear-gradient(135deg, rgba(255,255,255,0.02), ${activeMode.color}05)`,
          }}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
        >
          {/* Glow accent */}
          <div
            className="absolute top-0 left-0 w-full h-1"
            style={{ background: `linear-gradient(90deg, transparent, ${activeMode.color}60, transparent)` }}
          />

          <div className="p-8 md:p-10 grid md:grid-cols-[1fr_auto] gap-8 items-start">
            {/* Left: Description */}
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div
                  className="flex items-center justify-center w-10 h-10 rounded-md border"
                  style={{
                    color: activeMode.color,
                    borderColor: `${activeMode.color}30`,
                    backgroundColor: `${activeMode.color}10`,
                  }}
                >
                  {activeMode.icon}
                </div>
                <h3 className="font-display text-2xl text-white">{activeMode.label} View</h3>
              </div>
              <p className="text-white/50 leading-relaxed mb-6 max-w-lg">
                {activeMode.description}
              </p>
              <div className="flex flex-wrap gap-2">
                {activeMode.features.map((f) => (
                  <span
                    key={f}
                    className="inline-block px-3 py-1 text-xs font-mono rounded-sm border"
                    style={{
                      color: `${activeMode.color}cc`,
                      borderColor: `${activeMode.color}20`,
                      backgroundColor: `${activeMode.color}08`,
                    }}
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>

            {/* Right: Visual indicator */}
            <div
              className="hidden md:flex flex-col items-center justify-center w-48 h-36 rounded-md border"
              style={{
                borderColor: `${activeMode.color}15`,
                background: `radial-gradient(circle at 50% 50%, ${activeMode.color}08, transparent 70%)`,
              }}
            >
              <div style={{ color: activeMode.color }} className="mb-3 opacity-60">
                {/* Large icon */}
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="opacity-50">
                  <circle cx="24" cy="24" r="20" stroke={activeMode.color} strokeWidth="0.5" opacity="0.3" />
                  <circle cx="24" cy="24" r="12" stroke={activeMode.color} strokeWidth="0.5" opacity="0.5" />
                  <circle cx="24" cy="24" r="4" fill={activeMode.color} opacity="0.6" />
                  {/* Orbital dots */}
                  <circle cx="24" cy="4" r="2" fill={activeMode.color} opacity="0.4" />
                  <circle cx="44" cy="24" r="2" fill={activeMode.color} opacity="0.4" />
                  <circle cx="24" cy="44" r="2" fill={activeMode.color} opacity="0.4" />
                  <circle cx="4" cy="24" r="2" fill={activeMode.color} opacity="0.4" />
                </svg>
              </div>
              <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: `${activeMode.color}60` }}>
                {activeMode.label}
              </span>
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
