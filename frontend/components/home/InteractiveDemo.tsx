'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, User, Lightbulb, Beaker, Hexagon } from 'lucide-react';

interface DemoNode {
  id: string;
  label: string;
  type: string;
  icon: React.ReactNode;
  x: number;
  y: number;
  color: string;
  connections: string[];
}

const nodes: DemoNode[] = [
  {
    id: 'p1',
    label: 'Attention Is All You Need',
    type: 'Paper',
    icon: <FileText className="w-3.5 h-3.5" />,
    x: 50,
    y: 20,
    color: '#3B82F6',
    connections: ['a1', 'c1', 'm1'],
  },
  {
    id: 'a1',
    label: 'Vaswani et al.',
    type: 'Author',
    icon: <User className="w-3.5 h-3.5" />,
    x: 15,
    y: 45,
    color: '#10B981',
    connections: ['p1'],
  },
  {
    id: 'c1',
    label: 'Self-Attention',
    type: 'Concept',
    icon: <Lightbulb className="w-3.5 h-3.5" />,
    x: 78,
    y: 42,
    color: '#8B5CF6',
    connections: ['p1', 'm1', 'c2'],
  },
  {
    id: 'm1',
    label: 'Transformer',
    type: 'Method',
    icon: <Beaker className="w-3.5 h-3.5" />,
    x: 35,
    y: 72,
    color: '#F59E0B',
    connections: ['p1', 'c1'],
  },
  {
    id: 'c2',
    label: 'Multi-Head Attention',
    type: 'Concept',
    icon: <Hexagon className="w-3.5 h-3.5" />,
    x: 70,
    y: 78,
    color: '#EC4899',
    connections: ['c1'],
  },
];

function getNodeCenter(node: DemoNode, containerW: number, containerH: number) {
  return {
    cx: (node.x / 100) * containerW,
    cy: (node.y / 100) * containerH,
  };
}

export function InteractiveDemo() {
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const containerW = 320;
  const containerH = 280;

  const activeConnections = activeNode
    ? nodes.find((n) => n.id === activeNode)?.connections ?? []
    : [];

  return (
    <div
      className="relative backdrop-blur-xl bg-surface/40 border border-white/10 rounded-lg overflow-hidden"
      style={{ width: containerW, height: containerH }}
    >
      {/* Grid pattern background */}
      <div className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.5) 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      />

      {/* SVG edges */}
      <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 1 }}>
        {nodes.flatMap((node) =>
          node.connections.map((targetId) => {
            const target = nodes.find((n) => n.id === targetId);
            if (!target) return null;
            // Avoid duplicate edges
            if (node.id > targetId) return null;
            const from = getNodeCenter(node, containerW, containerH);
            const to = getNodeCenter(target, containerW, containerH);
            const isHighlighted =
              activeNode === node.id || activeNode === targetId;

            return (
              <motion.line
                key={`${node.id}-${targetId}`}
                x1={from.cx}
                y1={from.cy}
                x2={to.cx}
                y2={to.cy}
                stroke={isHighlighted ? node.color : 'rgba(255,255,255,0.12)'}
                strokeWidth={isHighlighted ? 2 : 1}
                strokeDasharray={isHighlighted ? 'none' : '4 4'}
                animate={{
                  stroke: isHighlighted ? node.color : 'rgba(255,255,255,0.12)',
                  strokeWidth: isHighlighted ? 2 : 1,
                }}
                transition={{ duration: 0.3 }}
              />
            );
          })
        )}
      </svg>

      {/* Nodes */}
      {nodes.map((node) => {
        const isActive = activeNode === node.id;
        const isConnected = activeConnections.includes(node.id);
        const dimmed = activeNode !== null && !isActive && !isConnected;

        return (
          <motion.div
            key={node.id}
            className="absolute flex items-center gap-1.5 cursor-pointer select-none"
            style={{
              left: `${node.x}%`,
              top: `${node.y}%`,
              transform: 'translate(-50%, -50%)',
              zIndex: isActive ? 10 : 2,
            }}
            onMouseEnter={() => setActiveNode(node.id)}
            onMouseLeave={() => setActiveNode(null)}
            animate={{
              opacity: dimmed ? 0.3 : 1,
              scale: isActive ? 1.15 : 1,
            }}
            transition={{ duration: 0.2 }}
          >
            <div
              className="flex items-center gap-1.5 px-2 py-1 rounded-sm backdrop-blur-sm border text-xs font-medium whitespace-nowrap"
              style={{
                color: node.color,
                borderColor: isActive ? node.color : `${node.color}40`,
                backgroundColor: isActive ? `${node.color}25` : `${node.color}10`,
                boxShadow: isActive ? `0 0 16px ${node.color}30` : 'none',
              }}
            >
              {node.icon}
              <span className="max-w-[100px] truncate">{node.label}</span>
            </div>

            {/* Tooltip on hover */}
            <AnimatePresence>
              {isActive && (
                <motion.div
                  className="absolute top-full mt-1 left-1/2 -translate-x-1/2 px-2 py-1 text-[10px] text-white/70 bg-black/60 backdrop-blur-sm rounded-sm whitespace-nowrap"
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  style={{ zIndex: 20 }}
                >
                  {node.type} · {node.connections.length} connections
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}

      {/* Label */}
      <div className="absolute bottom-2 right-3 text-[10px] font-mono text-white/30">
        Interactive Preview
      </div>
    </div>
  );
}
