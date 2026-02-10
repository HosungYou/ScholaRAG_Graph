'use client';

import { useEffect, useRef, useMemo, useCallback } from 'react';
import * as d3 from 'd3';
import type { ConceptCluster, StructuralGap, GraphEdge, TopicNode, TopicLink, TopicViewData } from '@/types';

// Cluster color palette (matches Graph3D)
const CLUSTER_COLORS = [
  '#FF6B6B', // Coral Red
  '#4ECDC4', // Turquoise
  '#45B7D1', // Sky Blue
  '#96CEB4', // Sage Green
  '#FFEAA7', // Soft Yellow
  '#DDA0DD', // Plum
  '#98D8C8', // Mint
  '#F7DC6F', // Gold
  '#BB8FCE', // Lavender
  '#85C1E9', // Light Blue
  '#F8B500', // Amber
  '#82E0AA', // Light Green
];

interface TopicViewModeProps {
  clusters: ConceptCluster[];
  gaps: StructuralGap[];
  edges: GraphEdge[];
  onClusterClick?: (clusterId: number) => void;
  onClusterHover?: (clusterId: number | null) => void;
  highlightedClusterId?: number | null;
  width?: number;
  height?: number;
}

export function TopicViewMode({
  clusters,
  gaps,
  edges,
  onClusterClick,
  onClusterHover,
  highlightedClusterId,
  width = 800,
  height = 600,
}: TopicViewModeProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<TopicNode, TopicLink> | null>(null);

  // Convert clusters and gaps to TopicViewData
  const topicData = useMemo((): TopicViewData => {
    // Create topic nodes from clusters
    const nodes: TopicNode[] = clusters.map((cluster, index) => ({
      id: `cluster-${cluster.cluster_id}`,
      clusterId: cluster.cluster_id,
      label: (cluster.label && cluster.label.replace(/[\s/,]+/g, '').length > 0)
        ? cluster.label
        : `Cluster ${cluster.cluster_id + 1}`,
      size: cluster.size,
      color: CLUSTER_COLORS[index % CLUSTER_COLORS.length],
      conceptIds: cluster.concepts,
      conceptNames: cluster.concept_names,
      density: cluster.density,
    }));

    // Count inter-cluster connections
    const connectionMap = new Map<string, number>();
    edges.forEach((edge) => {
      // Find which clusters source and target belong to
      const sourceCluster = clusters.find((c) => c.concepts.includes(edge.source));
      const targetCluster = clusters.find((c) => c.concepts.includes(edge.target));

      if (sourceCluster && targetCluster && sourceCluster.cluster_id !== targetCluster.cluster_id) {
        const key = [
          Math.min(sourceCluster.cluster_id, targetCluster.cluster_id),
          Math.max(sourceCluster.cluster_id, targetCluster.cluster_id),
        ].join('-');
        connectionMap.set(key, (connectionMap.get(key) || 0) + 1);
      }
    });

    // Build valid node ID set for link filtering
    const validNodeIds = new Set(nodes.map((n) => n.id));

    // Create links from connections
    const links: TopicLink[] = [];

    // Add connection links
    connectionMap.forEach((count, key) => {
      const [a, b] = key.split('-').map(Number);
      const sourceId = `cluster-${a}`;
      const targetId = `cluster-${b}`;

      if (validNodeIds.has(sourceId) && validNodeIds.has(targetId)) {
        links.push({
          id: `connection-${key}`,
          source: sourceId,
          target: targetId,
          type: 'connection',
          weight: count,
          connectionCount: count,
        });
      }
    });

    // Add gap links
    gaps.forEach((gap) => {
      const key = [
        Math.min(gap.cluster_a_id, gap.cluster_b_id),
        Math.max(gap.cluster_a_id, gap.cluster_b_id),
      ].join('-');

      const sourceId = `cluster-${gap.cluster_a_id}`;
      const targetId = `cluster-${gap.cluster_b_id}`;

      // Check if there's already a connection link
      const existingLink = links.find((l) => l.id === `connection-${key}`);

      if (!existingLink && validNodeIds.has(sourceId) && validNodeIds.has(targetId)) {
        links.push({
          id: `gap-${gap.id}`,
          source: sourceId,
          target: targetId,
          type: 'gap',
          weight: gap.gap_strength,
          gapId: gap.id,
        });
      }
    });

    return { nodes, links };
  }, [clusters, gaps, edges]);

  // Calculate node dimensions based on size
  const getNodeDimensions = useCallback((size: number) => {
    const minSize = 60;
    const maxSize = 150;
    const maxConcepts = Math.max(...clusters.map((c) => c.size), 1);
    const scale = (size / maxConcepts) * (maxSize - minSize) + minSize;
    return { width: scale, height: scale * 0.6 };
  }, [clusters]);

  // D3 Force Simulation
  useEffect(() => {
    if (!svgRef.current || topicData.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Create container group for zoom
    const container = svg.append('g').attr('class', 'container');

    // Zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Copy nodes and links for simulation
    const nodes = topicData.nodes.map((d) => ({ ...d }));
    const links = topicData.links.map((d) => ({
      ...d,
      source: d.source as string,
      target: d.target as string,
    }));

    // Create simulation
    const simulation = d3
      .forceSimulation<TopicNode>(nodes)
      .force(
        'link',
        d3
          .forceLink<TopicNode, TopicLink>(links)
          .id((d) => d.id)
          .distance(200)
          .strength(0.3)
      )
      .force('charge', d3.forceManyBody().strength(-500))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((d) => {
        const dims = getNodeDimensions((d as TopicNode).size);
        return Math.max(dims.width, dims.height) / 2 + 20;
      }));

    simulationRef.current = simulation;

    // Create links
    const linkGroup = container.append('g').attr('class', 'links');

    const link = linkGroup
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', (d) => (d.type === 'gap' ? '#FFAA00' : 'rgba(255, 255, 255, 0.3)'))
      .attr('stroke-width', (d) => (d.type === 'gap' ? 2 : Math.min(d.weight || 1, 5)))
      .attr('stroke-dasharray', (d) => (d.type === 'gap' ? '8,4' : 'none'))
      .attr('opacity', (d) => (d.type === 'gap' ? 0.8 : 0.5));

    // v0.10.0: Cluster boundary visualization (convex hull)
    const hullGroup = container.append('g').attr('class', 'hulls');

    // Create node groups
    const nodeGroup = container.append('g').attr('class', 'nodes');

    const node = nodeGroup
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', 'topic-node')
      .style('cursor', 'pointer');

    // Add drag behavior with type assertion
    const dragBehavior = d3
      .drag<SVGGElement, TopicNode>()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    // Type assertion needed due to D3 selection types
    (node as d3.Selection<SVGGElement, TopicNode, SVGGElement, unknown>).call(dragBehavior);

    // Add rectangles to nodes
    node
      .append('rect')
      .attr('width', (d) => getNodeDimensions(d.size).width)
      .attr('height', (d) => getNodeDimensions(d.size).height)
      .attr('x', (d) => -getNodeDimensions(d.size).width / 2)
      .attr('y', (d) => -getNodeDimensions(d.size).height / 2)
      .attr('rx', 8)
      .attr('ry', 8)
      .attr('fill', (d) => d.color)
      .attr('fill-opacity', 0.15)
      .attr('stroke', (d) => d.color)
      .attr('stroke-width', 2);

    // v0.10.0: Enhanced cluster labels - larger, color-matched, with text shadow
    node
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('fill', (d) => d.color)
      .attr('font-size', '16px')
      .attr('font-weight', 'bold')
      .attr('font-family', 'system-ui, -apple-system, sans-serif')
      .style('text-shadow', '0 1px 4px rgba(0,0,0,0.9), 0 0 12px rgba(0,0,0,0.7), 0 0 2px rgba(0,0,0,1)')
      .text((d) => d.label.length > 30 ? d.label.slice(0, 30) + '...' : d.label);

    // Add size indicator
    node
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('y', 18)
      .attr('fill', 'rgba(255, 255, 255, 0.6)')
      .attr('font-size', '11px')
      .attr('font-family', 'monospace')
      .text((d) => `${d.size} concepts`);

    // v0.14.0: Add concept preview on hover (shows top concept names)
    node
      .append('text')
      .attr('class', 'concept-preview')
      .attr('text-anchor', 'middle')
      .attr('y', 32)
      .attr('fill', 'rgba(255, 255, 255, 0.4)')
      .attr('font-size', '9px')
      .attr('font-family', 'monospace')
      .attr('opacity', 0)
      .text((d) => {
        const names = d.conceptNames?.filter((n: string) => n && n.trim()).slice(0, 3) || [];
        return names.length > 0 ? names.join(', ') : '';
      });

    // Interaction handlers
    node
      .on('click', (event, d) => {
        event.stopPropagation();
        onClusterClick?.(d.clusterId);
      })
      .on('mouseenter', (event, d) => {
        onClusterHover?.(d.clusterId);
        d3.select(event.currentTarget)
          .transition()
          .duration(150)
          .attr('transform', (d: any) => `translate(${d.x ?? 0},${d.y ?? 0}) scale(1.02)`);
        d3.select(event.currentTarget)
          .select('rect')
          .transition()
          .duration(150)
          .attr('stroke-width', 3);
        d3.select(event.currentTarget)
          .select('.concept-preview')
          .transition()
          .duration(200)
          .attr('opacity', 1);
      })
      .on('mouseleave', (event, d) => {
        onClusterHover?.(null);
        d3.select(event.currentTarget)
          .transition()
          .duration(150)
          .attr('transform', (d: any) => `translate(${d.x ?? 0},${d.y ?? 0}) scale(1)`);
        d3.select(event.currentTarget)
          .select('rect')
          .transition()
          .duration(150)
          .attr('stroke-width', 2);
        d3.select(event.currentTarget)
          .select('.concept-preview')
          .transition()
          .duration(200)
          .attr('opacity', 0);
      });

    // Update positions on tick
    // Note: D3 forceLink mutates source/target from string IDs to node objects
    simulation.on('tick', () => {
      link
        .attr('x1', (d) => ((d.source as unknown) as TopicNode).x ?? 0)
        .attr('y1', (d) => ((d.source as unknown) as TopicNode).y ?? 0)
        .attr('x2', (d) => ((d.target as unknown) as TopicNode).x ?? 0)
        .attr('y2', (d) => ((d.target as unknown) as TopicNode).y ?? 0);

      node.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);

      // v0.10.0: Update convex hull boundaries
      hullGroup.selectAll('path').remove();
      const clusterGroups = new Map<number, Array<[number, number]>>();
      nodes.forEach((n) => {
        if (n.x !== undefined && n.y !== undefined) {
          const points = clusterGroups.get(n.clusterId) || [];
          const dims = getNodeDimensions(n.size);
          const pad = Math.max(dims.width, dims.height) / 2 + 15;
          // Add padded points around the node for a smoother hull
          points.push([n.x - pad, n.y - pad]);
          points.push([n.x + pad, n.y - pad]);
          points.push([n.x - pad, n.y + pad]);
          points.push([n.x + pad, n.y + pad]);
          clusterGroups.set(n.clusterId, points);
        }
      });

      clusterGroups.forEach((points, clusterId) => {
        if (points.length < 6) return; // Need at least 3 nodes (6 corner points)
        const hull = d3.polygonHull(points);
        if (hull) {
          const clusterIndex = clusters.findIndex((c) => c.cluster_id === clusterId);
          const color = CLUSTER_COLORS[clusterIndex % CLUSTER_COLORS.length] || '#888';
          hullGroup
            .append('path')
            .attr('d', `M${hull.join('L')}Z`)
            .attr('fill', color)
            .attr('fill-opacity', 0.04)
            .attr('stroke', color)
            .attr('stroke-opacity', 0.15)
            .attr('stroke-width', 1)
            .attr('stroke-linejoin', 'round');
        }
      });
    });

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [topicData, width, height, getNodeDimensions, onClusterClick, onClusterHover]);

  // Update highlight when highlightedClusterId changes
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);

    svg.selectAll('.topic-node rect')
      .transition()
      .duration(150)
      .attr('fill-opacity', (d) => {
        const node = d as TopicNode;
        if (highlightedClusterId === null || highlightedClusterId === undefined) {
          return 0.15;
        }
        return node.clusterId === highlightedClusterId ? 0.4 : 0.05;
      })
      .attr('stroke-opacity', (d) => {
        const node = d as TopicNode;
        if (highlightedClusterId === null || highlightedClusterId === undefined) {
          return 1;
        }
        return node.clusterId === highlightedClusterId ? 1 : 0.3;
      });
  }, [highlightedClusterId]);

  if (clusters.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-[#0d1117]">
        <div className="text-center">
          <p className="font-mono text-xs uppercase tracking-wider text-muted">
            No clusters available for Topic View
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-[#0d1117] relative">
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ background: '#0d1117' }}
      />

      {/* v0.10.0: Enhanced Legend with cluster colors */}
      <div className="absolute bottom-4 right-4 bg-[#161b22]/90 backdrop-blur-sm border border-[#30363d] rounded-lg p-3 max-w-[200px]">
        <div className="text-xs font-mono text-[#8b949e] mb-2 uppercase tracking-wider">Topic Clusters</div>
        {/* Cluster colors */}
        {clusters.length > 0 && (
          <div className="mb-2 space-y-1">
            {clusters.slice(0, 8).map((cluster, i) => (
              <div key={cluster.cluster_id} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-sm flex-shrink-0"
                  style={{ backgroundColor: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }}
                />
                <span className="text-xs text-[#c9d1d9] truncate">
                  {(cluster.label && cluster.label.replace(/[\s/,]+/g, '').length > 0)
                    ? cluster.label
                    : `Cluster ${cluster.cluster_id + 1}`}
                </span>
                <span className="text-xs text-[#484f58] flex-shrink-0">
                  ({cluster.size})
                </span>
              </div>
            ))}
            {clusters.length > 8 && (
              <span className="text-xs text-[#484f58]">+{clusters.length - 8} more</span>
            )}
          </div>
        )}
        {/* Edge types */}
        <div className="border-t border-[#30363d] pt-2 space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-white/30" />
            <span className="text-xs text-[#8b949e]">Connections</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 border-t-2 border-dashed border-amber-500" />
            <span className="text-xs text-[#8b949e]">Structural Gap</span>
          </div>
        </div>
      </div>

      {/* Topic View Badge */}
      <div className="absolute top-4 left-4 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 px-3 py-1.5">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-accent-violet" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
          <span className="font-mono text-xs uppercase tracking-wider text-muted">
            Topic View
          </span>
          <span className="text-xs text-muted">
            • {clusters.length} clusters
          </span>
        </div>
      </div>
    </div>
  );
}

export default TopicViewMode;
