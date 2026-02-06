'use client';

import { useEffect, useRef, useCallback } from 'react';

/* ============================================================
   HeroBackground - Dynamic Knowledge Graph Visualization
   VS Design Diverge: Direction B (T-Score 0.4) "Editorial Research"

   Represents ScholaRAG's core functionality:
   - Floating polygonal nodes (Concept, Method, Finding, etc.)
   - Dynamic connection lines forming between nodes
   - Particles flowing along edges (data/knowledge transfer)
   - Subtle mouse interaction

   Design Principles:
   - No generic gradient backgrounds
   - Polygon shapes (not circles)
   - Uses accent colors: teal, amber, red
   - Subtle, professional animation (not flashy)
   ============================================================ */

interface Node {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  type: 'hexagon' | 'diamond' | 'pentagon' | 'square';
  size: number;
  color: string;
  opacity: number;
}

interface Edge {
  from: number;
  to: number;
  progress: number;
  active: boolean;
}

const COLORS = {
  cyan: '#22d3ee',
  violet: '#a78bfa',
  purple: '#c084fc',
  pink: '#f472b6',
  indigo: '#818cf8',
};

const NODE_TYPES: Node['type'][] = ['hexagon', 'diamond', 'pentagon', 'square'];

// Animation settings - make it more dynamic
const ANIMATION_CONFIG = {
  nodeSpeed: 0.8,        // Increased from 0.3
  particleSpeed: 0.008,  // Increased from 0.003
  connectionDistance: 350, // Increased from 300
  mouseRepelStrength: 0.05, // Increased from 0.02
  edgeOpacity: 0.25,     // Increased from 0.15
};

export function HeroBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const nodesRef = useRef<Node[]>([]);
  const edgesRef = useRef<Edge[]>([]);
  const mouseRef = useRef({ x: 0, y: 0, active: false });

  // Draw polygon shapes
  const drawPolygon = useCallback(
    (ctx: CanvasRenderingContext2D, x: number, y: number, size: number, type: Node['type'], color: string, opacity: number) => {
      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.strokeStyle = color;
      ctx.fillStyle = color + '15'; // 15% opacity fill
      ctx.lineWidth = 1.5;

      ctx.beginPath();

      switch (type) {
        case 'hexagon':
          for (let i = 0; i < 6; i++) {
            const angle = (Math.PI / 3) * i - Math.PI / 2;
            const px = x + size * Math.cos(angle);
            const py = y + size * Math.sin(angle);
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          }
          break;

        case 'diamond':
          ctx.moveTo(x, y - size);
          ctx.lineTo(x + size * 0.7, y);
          ctx.lineTo(x, y + size);
          ctx.lineTo(x - size * 0.7, y);
          break;

        case 'pentagon':
          for (let i = 0; i < 5; i++) {
            const angle = ((Math.PI * 2) / 5) * i - Math.PI / 2;
            const px = x + size * Math.cos(angle);
            const py = y + size * Math.sin(angle);
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          }
          break;

        case 'square':
          const half = size * 0.7;
          ctx.rect(x - half, y - half, half * 2, half * 2);
          break;
      }

      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.restore();
    },
    []
  );

  // Initialize nodes
  const initNodes = useCallback((width: number, height: number) => {
    const nodeCount = Math.floor((width * height) / 25000); // More nodes (was 40000)
    const colorKeys = Object.keys(COLORS) as (keyof typeof COLORS)[];

    nodesRef.current = Array.from({ length: Math.max(25, Math.min(50, nodeCount)) }, (_, i) => ({
      id: i,
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * ANIMATION_CONFIG.nodeSpeed,
      vy: (Math.random() - 0.5) * ANIMATION_CONFIG.nodeSpeed,
      type: NODE_TYPES[Math.floor(Math.random() * NODE_TYPES.length)],
      size: 10 + Math.random() * 18, // Larger nodes (was 8-20)
      color: COLORS[colorKeys[Math.floor(Math.random() * colorKeys.length)]],
      opacity: 0.4 + Math.random() * 0.4, // More visible (was 0.3-0.7)
    }));

    // Initialize edges - more connections
    edgesRef.current = [];
    nodesRef.current.forEach((node, i) => {
      // Connect to 2-4 nearby nodes (was 1-2)
      const connections = 2 + Math.floor(Math.random() * 3);
      for (let c = 0; c < connections; c++) {
        const targetIndex = (i + 1 + Math.floor(Math.random() * 5)) % nodesRef.current.length;
        if (targetIndex !== i) {
          edgesRef.current.push({
            from: i,
            to: targetIndex,
            progress: Math.random(),
            active: Math.random() > 0.3, // More active edges (was 0.5)
          });
        }
      }
    });
  }, []);

  // Animation loop
  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Update and draw edges
    edgesRef.current.forEach((edge) => {
      const fromNode = nodesRef.current[edge.from];
      const toNode = nodesRef.current[edge.to];
      if (!fromNode || !toNode) return;

      const dx = toNode.x - fromNode.x;
      const dy = toNode.y - fromNode.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      // Only draw edges within reasonable distance
      if (dist < ANIMATION_CONFIG.connectionDistance) {
        const opacity = Math.max(0, ANIMATION_CONFIG.edgeOpacity * (1 - dist / ANIMATION_CONFIG.connectionDistance));

        // Draw edge line with gradient effect
        ctx.save();
        ctx.globalAlpha = opacity;

        // Create gradient for edge
        const gradient = ctx.createLinearGradient(fromNode.x, fromNode.y, toNode.x, toNode.y);
        gradient.addColorStop(0, fromNode.color);
        gradient.addColorStop(1, toNode.color);
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([6, 4]);

        ctx.beginPath();
        ctx.moveTo(fromNode.x, fromNode.y);
        ctx.lineTo(toNode.x, toNode.y);
        ctx.stroke();
        ctx.restore();

        // Draw flowing particle on active edges
        if (edge.active) {
          edge.progress += ANIMATION_CONFIG.particleSpeed;
          if (edge.progress > 1) edge.progress = 0;

          const px = fromNode.x + dx * edge.progress;
          const py = fromNode.y + dy * edge.progress;

          // Draw glowing particle
          ctx.save();
          ctx.globalAlpha = opacity * 3;
          ctx.fillStyle = fromNode.color;
          ctx.shadowColor = fromNode.color;
          ctx.shadowBlur = 8;
          ctx.beginPath();
          ctx.arc(px, py, 3, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }
      }
    });

    // Update and draw nodes
    nodesRef.current.forEach((node) => {
      // Mouse interaction - stronger repulsion
      if (mouseRef.current.active) {
        const dx = node.x - mouseRef.current.x;
        const dy = node.y - mouseRef.current.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 200 && dist > 0) {
          const force = (200 - dist) / 200 * ANIMATION_CONFIG.mouseRepelStrength;
          node.vx += (dx / dist) * force;
          node.vy += (dy / dist) * force;
        }
      }

      // Add subtle oscillation for constant movement
      node.vx += (Math.random() - 0.5) * 0.02;
      node.vy += (Math.random() - 0.5) * 0.02;

      // Apply velocity
      node.x += node.vx;
      node.y += node.vy;

      // Damping
      node.vx *= 0.99;
      node.vy *= 0.99;

      // Boundary bounce
      if (node.x < node.size || node.x > width - node.size) {
        node.vx *= -1;
        node.x = Math.max(node.size, Math.min(width - node.size, node.x));
      }
      if (node.y < node.size || node.y > height - node.size) {
        node.vy *= -1;
        node.y = Math.max(node.size, Math.min(height - node.size, node.y));
      }

      // Draw node with glow effect
      ctx.save();
      ctx.shadowColor = node.color;
      ctx.shadowBlur = 12;
      drawPolygon(ctx, node.x, node.y, node.size, node.type, node.color, node.opacity);
      ctx.restore();
    });

    animationRef.current = requestAnimationFrame(animate);
  }, [drawPolygon]);

  // Setup and cleanup
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleResize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;

      const { width, height } = parent.getBoundingClientRect();
      canvas.width = width;
      canvas.height = height;
      initNodes(width, height);
    };

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        active: true,
      };
    };

    const handleMouseLeave = () => {
      mouseRef.current.active = false;
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseleave', handleMouseLeave);

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', handleResize);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mouseleave', handleMouseLeave);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [animate, initNodes]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-auto"
      aria-hidden="true"
    />
  );
}
