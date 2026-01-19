'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Lightbulb, Beaker, Trophy, AlertCircle, Database, Target, Sparkles, AlertTriangle, FileText, User } from 'lucide-react';
import clsx from 'clsx';

/* ============================================================
   ScholaRAG Graph - Polygonal Node Component
   VS Design Diverge: Direction B (T-Score 0.4)

   Breaking from generic circular nodes with distinctive shapes:
   - Concept: Hexagon (6-sided - central ideas)
   - Method: Diamond (4-sided rotated - processes)
   - Finding: Square (4-sided - concrete results)
   - Problem: Pentagon (5-sided - challenges)
   - Dataset: Octagon (8-sided - data containers)
   - Metric: Circle (continuous - measurements)
   - Innovation: Star (pointed - breakthroughs)
   - Limitation: Triangle (3-sided - constraints)
   ============================================================ */

interface PolygonNodeData {
  label: string;
  entityType: string;
  properties?: Record<string, any>;
  isHighlighted?: boolean;
  centralityDegree?: number;
  centralityBetweenness?: number;
  centralityPagerank?: number;
  clusterId?: number;
  clusterColor?: string;
  isGapBridge?: boolean;
  definition?: string;
  paperCount?: number;
}

// Entity type icons (Hybrid Mode: Paper/Author + Concept-Centric)
const iconMap: Record<string, React.ReactNode> = {
  // Hybrid Mode entities
  Paper: <FileText className="w-full h-full" />,
  Author: <User className="w-full h-full" />,
  // Concept-centric entities
  Concept: <Lightbulb className="w-full h-full" />,
  Method: <Beaker className="w-full h-full" />,
  Finding: <Trophy className="w-full h-full" />,
  Problem: <AlertCircle className="w-full h-full" />,
  Dataset: <Database className="w-full h-full" />,
  Metric: <Target className="w-full h-full" />,
  Innovation: <Sparkles className="w-full h-full" />,
  Limitation: <AlertTriangle className="w-full h-full" />,
};

// Entity type colors (VS Design Diverge palette - Hybrid Mode)
const entityColors: Record<string, string> = {
  // Hybrid Mode entities (Paper-centric visualization)
  Paper: '#6366F1',      // Indigo - Rectangle
  Author: '#A855F7',     // Purple - Circle
  // Concept-centric entities
  Concept: '#8B5CF6',    // Violet - Hexagon
  Method: '#F59E0B',     // Amber - Diamond
  Finding: '#10B981',    // Emerald - Square
  Problem: '#EF4444',    // Red - Pentagon
  Dataset: '#3B82F6',    // Blue - Octagon
  Metric: '#EC4899',     // Pink - Circle
  Innovation: '#14B8A6', // Teal - Star
  Limitation: '#F97316', // Orange - Triangle
};

// Cluster colors - high-contrast palette
const clusterColors = [
  '#E63946', '#2EC4B6', '#F4A261', '#457B9D', '#A8DADC',
  '#9D4EDD', '#06D6A0', '#118AB2', '#EF476F', '#FFD166',
  '#073B4C', '#7209B7',
];

// SVG Path generators for different polygon shapes
const polygonPaths: Record<string, (size: number) => string> = {
  // Rectangle - horizontal (Paper)
  rectangle: (size: number) => {
    const width = size;
    const height = size * 0.7;
    const y = (size - height) / 2;
    return `M0,${y} L${width},${y} L${width},${y + height} L0,${y + height}Z`;
  },

  // Hexagon - 6 sides (Concept)
  hexagon: (size: number) => {
    const r = size / 2;
    const points = [];
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 6;
      points.push(`${r + r * Math.cos(angle)},${r + r * Math.sin(angle)}`);
    }
    return `M${points.join('L')}Z`;
  },

  // Diamond - 4 sides rotated 45° (Method)
  diamond: (size: number) => {
    const r = size / 2;
    return `M${r},0 L${size},${r} L${r},${size} L0,${r}Z`;
  },

  // Square - 4 sides (Finding)
  square: (size: number) => {
    const margin = size * 0.1;
    return `M${margin},${margin} L${size - margin},${margin} L${size - margin},${size - margin} L${margin},${size - margin}Z`;
  },

  // Pentagon - 5 sides (Problem)
  pentagon: (size: number) => {
    const r = size / 2;
    const points = [];
    for (let i = 0; i < 5; i++) {
      const angle = (Math.PI * 2 / 5) * i - Math.PI / 2;
      points.push(`${r + r * Math.cos(angle)},${r + r * Math.sin(angle)}`);
    }
    return `M${points.join('L')}Z`;
  },

  // Octagon - 8 sides (Dataset)
  octagon: (size: number) => {
    const r = size / 2;
    const points = [];
    for (let i = 0; i < 8; i++) {
      const angle = (Math.PI / 4) * i - Math.PI / 8;
      points.push(`${r + r * 0.92 * Math.cos(angle)},${r + r * 0.92 * Math.sin(angle)}`);
    }
    return `M${points.join('L')}Z`;
  },

  // Circle (Metric)
  circle: (size: number) => {
    const r = size / 2;
    return `M${r},0 A${r},${r} 0 1,1 ${r},${size} A${r},${r} 0 1,1 ${r},0`;
  },

  // Star - 5 pointed (Innovation)
  star: (size: number) => {
    const r = size / 2;
    const innerR = r * 0.4;
    const points = [];
    for (let i = 0; i < 10; i++) {
      const radius = i % 2 === 0 ? r : innerR;
      const angle = (Math.PI / 5) * i - Math.PI / 2;
      points.push(`${r + radius * Math.cos(angle)},${r + radius * Math.sin(angle)}`);
    }
    return `M${points.join('L')}Z`;
  },

  // Triangle - 3 sides (Limitation)
  triangle: (size: number) => {
    const r = size / 2;
    return `M${r},${size * 0.1} L${size * 0.9},${size * 0.85} L${size * 0.1},${size * 0.85}Z`;
  },
};

// Map entity types to polygon shapes
// Map entity types to polygon shapes (Hybrid Mode)
const entityShapes: Record<string, string> = {
  // Hybrid Mode entities
  Paper: 'rectangle',      // 논문: 직사각형 (문서 형태)
  Author: 'circle',        // 저자: 원형 (사람 노드)
  // Concept-centric entities
  Concept: 'hexagon',
  Method: 'diamond',
  Finding: 'square',
  Problem: 'pentagon',
  Dataset: 'octagon',
  Metric: 'circle',
  Innovation: 'star',
  Limitation: 'triangle',
};

/**
 * Calculate node size based on centrality metrics
 */
function calculateSize(data: PolygonNodeData): number {
  const MIN_SIZE = 36;
  const MAX_SIZE = 90;

  const pagerank = data.centralityPagerank ?? 0;
  const betweennessBonus = (data.centralityBetweenness ?? 0) * 0.15;

  const size = MIN_SIZE + (MAX_SIZE - MIN_SIZE) * (pagerank + betweennessBonus);
  return Math.min(MAX_SIZE, Math.max(MIN_SIZE, size));
}

/**
 * Get node color based on cluster or entity type
 */
function getNodeColor(data: PolygonNodeData): string {
  if (data.clusterColor) return data.clusterColor;
  if (data.clusterId !== undefined && data.clusterId !== null) {
    return clusterColors[data.clusterId % clusterColors.length];
  }
  return entityColors[data.entityType] ?? '#6B7280';
}

function PolygonNodeComponent({ data, selected }: NodeProps<PolygonNodeData>) {
  const size = calculateSize(data);
  const color = getNodeColor(data);
  const shapeName = entityShapes[data.entityType] ?? 'hexagon';
  const pathGenerator = polygonPaths[shapeName];
  const path = pathGenerator ? pathGenerator(size) : polygonPaths.hexagon(size);
  const icon = iconMap[data.entityType];

  // Calculate icon size (smaller relative to node)
  const iconSize = Math.max(14, size * 0.32);

  // Truncate label
  const displayLabel = data.label.length > 18
    ? data.label.substring(0, 16) + '…'
    : data.label;

  return (
    <div
      className={clsx(
        'scholar-node relative group cursor-pointer',
        data.isHighlighted && 'highlighted',
        data.isGapBridge && 'gap-bridge'
      )}
      style={{ width: size, height: size }}
      title={`${data.label}${data.definition ? `\n\n${data.definition}` : ''}`}
    >
      {/* Connection Handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-1.5 !h-1.5 !bg-white/50 !border-0 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ top: 0 }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-1.5 !h-1.5 !bg-white/50 !border-0 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ bottom: 0 }}
      />
      <Handle
        type="target"
        position={Position.Left}
        className="!w-1.5 !h-1.5 !bg-white/50 !border-0 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ left: 0 }}
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-1.5 !h-1.5 !bg-white/50 !border-0 opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ right: 0 }}
      />

      {/* SVG Polygon Shape */}
      <svg
        className="scholar-node__shape absolute inset-0"
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
      >
        {/* Glow effect for selected/highlighted */}
        <defs>
          <filter id={`glow-${data.label.replace(/\s/g, '-')}`}>
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id={`grad-${data.label.replace(/\s/g, '-')}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="1" />
            <stop offset="100%" stopColor={color} stopOpacity="0.7" />
          </linearGradient>
        </defs>

        {/* Main Shape */}
        <path
          d={path}
          fill={`url(#grad-${data.label.replace(/\s/g, '-')})`}
          stroke={selected ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.3)'}
          strokeWidth={selected ? 2.5 : 1.5}
          filter={selected || data.isHighlighted ? `url(#glow-${data.label.replace(/\s/g, '-')})` : undefined}
          className="transition-all duration-200"
        />

        {/* Inner highlight for depth */}
        <path
          d={path}
          fill="none"
          stroke="rgba(255,255,255,0.15)"
          strokeWidth="1"
          transform={`translate(${size * 0.02}, ${size * 0.02}) scale(0.96)`}
        />
      </svg>

      {/* Icon */}
      {icon && (
        <div
          className="scholar-node__icon absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-white/90"
          style={{ width: iconSize, height: iconSize }}
        >
          {icon}
        </div>
      )}

      {/* External Label */}
      <div
        className="scholar-node__label absolute whitespace-nowrap text-center pointer-events-none"
        style={{
          top: size + 6,
          left: '50%',
          transform: 'translateX(-50%)',
          fontSize: '11px',
          color: 'rgba(255,255,255,0.75)',
          textShadow: '0 1px 3px rgba(0,0,0,0.8)',
          maxWidth: size * 1.8,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {displayLabel}
      </div>

      {/* Paper Count Badge */}
      {data.paperCount && data.paperCount > 0 && (
        <div
          className="absolute flex items-center justify-center font-mono font-medium"
          style={{
            top: -4,
            right: -4,
            width: Math.max(18, size * 0.28),
            height: Math.max(18, size * 0.28),
            fontSize: Math.max(9, size * 0.12),
            backgroundColor: '#2EC4B6',
            color: 'white',
            borderRadius: '4px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
          }}
        >
          {data.paperCount}
        </div>
      )}

      {/* Gap Bridge Indicator */}
      {data.isGapBridge && (
        <div
          className="absolute flex items-center justify-center"
          style={{
            bottom: -4,
            right: -4,
            width: 20,
            height: 20,
            backgroundColor: '#F4A261',
            borderRadius: '4px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
          }}
          title="Bridge Concept - Connects Research Gaps"
        >
          <Sparkles className="w-3 h-3 text-white" />
        </div>
      )}

      {/* Hover Tooltip */}
      <div
        className="absolute left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50"
        style={{ bottom: size + 8 }}
      >
        <div
          className="px-4 py-3 max-w-xs"
          style={{
            backgroundColor: 'rgb(26, 26, 46)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '4px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          }}
        >
          <div className="font-medium text-white text-sm">{data.label}</div>
          <div className="text-xs mt-0.5" style={{ color: color }}>{data.entityType}</div>

          {data.definition && (
            <div className="mt-2 text-xs text-white/60 line-clamp-2">
              {data.definition}
            </div>
          )}

          <div className="mt-2 flex gap-4 text-xs font-mono">
            {data.paperCount !== undefined && (
              <span style={{ color: '#2EC4B6' }}>
                {data.paperCount} paper{data.paperCount !== 1 ? 's' : ''}
              </span>
            )}
            {data.centralityPagerank !== undefined && (
              <span style={{ color: '#F4A261' }}>
                {(data.centralityPagerank * 100).toFixed(0)}% importance
              </span>
            )}
          </div>
        </div>
        {/* Arrow pointing down */}
        <div
          className="absolute left-1/2 -translate-x-1/2"
          style={{
            top: '100%',
            borderLeft: '6px solid transparent',
            borderRight: '6px solid transparent',
            borderTop: '6px solid rgb(26, 26, 46)',
          }}
        />
      </div>
    </div>
  );
}

export const PolygonNode = memo(PolygonNodeComponent);

// Also export as CircularNode for backwards compatibility
export const CircularNode = PolygonNode;
