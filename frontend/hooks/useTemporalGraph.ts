'use client';

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import type { GraphData, GraphEntity, GraphEdge } from '@/types';

/* ============================================================
   useTemporalGraph Hook
   Phase 2: Temporal Graph Evolution

   Manages the time-based filtering and animation state for
   visualizing how the knowledge graph evolved over years.
   ============================================================ */

interface TemporalGraphState {
  currentYear: number;
  isAnimating: boolean;
  animationSpeed: number; // ms per year
  yearRange: { min: number; max: number };
}

interface UseTemporalGraphOptions {
  defaultSpeed?: number; // Default animation speed in ms
  autoPlay?: boolean; // Start animation automatically
}

interface UseTemporalGraphReturn {
  // State
  currentYear: number;
  isAnimating: boolean;
  animationSpeed: number;
  yearRange: { min: number; max: number };

  // Filtered data
  filteredNodes: GraphEntity[];
  filteredEdges: GraphEdge[];

  // Actions
  setCurrentYear: (year: number) => void;
  setYearRange: (range: { min: number; max: number }) => void;
  toggleAnimation: () => void;
  startAnimation: () => void;
  stopAnimation: () => void;
  setAnimationSpeed: (speed: number) => void;
  resetToStart: () => void;
  resetToEnd: () => void;

  // Stats
  nodesByYear: Map<number, number>;
  totalVisibleNodes: number;
  totalVisibleEdges: number;
}

export function useTemporalGraph(
  fullGraphData: GraphData | null,
  options: UseTemporalGraphOptions = {}
): UseTemporalGraphReturn {
  const { defaultSpeed = 1000, autoPlay = false } = options;

  // Calculate year range from data
  const calculatedYearRange = useMemo(() => {
    if (!fullGraphData || fullGraphData.nodes.length === 0) {
      return { min: 2000, max: new Date().getFullYear() };
    }

    let min = Infinity;
    let max = -Infinity;

    for (const node of fullGraphData.nodes) {
      const firstYear = node.properties?.first_seen_year as number | undefined;
      const lastYear = node.properties?.last_seen_year as number | undefined;
      const year = node.properties?.year as number | undefined;

      const nodeMin = firstYear ?? year;
      const nodeMax = lastYear ?? firstYear ?? year;

      if (nodeMin && nodeMin < min) min = nodeMin;
      if (nodeMax && nodeMax > max) max = nodeMax;
    }

    // Fallback if no years found
    if (min === Infinity) min = 2000;
    if (max === -Infinity) max = new Date().getFullYear();

    return { min, max };
  }, [fullGraphData]);

  // State
  const [yearRange, setYearRange] = useState(calculatedYearRange);
  const [currentYear, setCurrentYear] = useState(calculatedYearRange.max);
  const [isAnimating, setIsAnimating] = useState(autoPlay);
  const [animationSpeed, setAnimationSpeed] = useState(defaultSpeed);

  // Animation timer ref
  const animationRef = useRef<NodeJS.Timeout | null>(null);

  // Update year range when data changes
  useEffect(() => {
    setYearRange(calculatedYearRange);
    setCurrentYear(calculatedYearRange.max);
  }, [calculatedYearRange]);

  // Animation effect
  useEffect(() => {
    if (!isAnimating) {
      if (animationRef.current) {
        clearInterval(animationRef.current);
        animationRef.current = null;
      }
      return;
    }

    animationRef.current = setInterval(() => {
      setCurrentYear(prev => {
        const next = prev + 1;
        if (next > yearRange.max) {
          // Loop back to start
          return yearRange.min;
        }
        return next;
      });
    }, animationSpeed);

    return () => {
      if (animationRef.current) {
        clearInterval(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [isAnimating, animationSpeed, yearRange.min, yearRange.max]);

  // Filter nodes based on current year
  const filteredNodes = useMemo(() => {
    if (!fullGraphData) return [];

    return fullGraphData.nodes.filter(node => {
      const firstYear = node.properties?.first_seen_year as number | undefined;
      const year = node.properties?.year as number | undefined;

      const nodeYear = firstYear ?? year;

      // If node has no year, always show it
      if (!nodeYear) return true;

      // Show if node appeared by current year
      return nodeYear <= currentYear;
    }).map(node => {
      // Add opacity based on how recently the node appeared
      const firstYear = node.properties?.first_seen_year as number | undefined;
      const lastYear = node.properties?.last_seen_year as number | undefined;
      const year = node.properties?.year as number | undefined;

      const nodeYear = firstYear ?? year;

      // Calculate opacity: newer nodes are more opaque
      let opacity = 1.0;
      if (nodeYear && lastYear) {
        // Fade out if node hasn't been seen recently
        const yearsSinceLastSeen = currentYear - (lastYear ?? nodeYear);
        if (yearsSinceLastSeen > 5) {
          opacity = Math.max(0.3, 1 - yearsSinceLastSeen * 0.1);
        }
      }

      return {
        ...node,
        properties: {
          ...node.properties,
          temporal_opacity: opacity,
          is_recent: nodeYear === currentYear,
        },
      };
    });
  }, [fullGraphData, currentYear]);

  // Filter edges - only show edges between visible nodes
  const filteredEdges = useMemo(() => {
    if (!fullGraphData) return [];

    const visibleNodeIds = new Set(filteredNodes.map(n => n.id));

    return fullGraphData.edges.filter(edge => {
      // Only show edge if both endpoints are visible
      if (!visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target)) {
        return false;
      }

      // Check edge's first_seen_year if available
      const edgeYear = edge.properties?.first_seen_year as number | undefined;
      if (edgeYear && edgeYear > currentYear) {
        return false;
      }

      return true;
    });
  }, [fullGraphData, filteredNodes, currentYear]);

  // Count nodes by year (for histogram)
  const nodesByYear = useMemo(() => {
    const counts = new Map<number, number>();

    if (!fullGraphData) return counts;

    for (const node of fullGraphData.nodes) {
      const year = (node.properties?.first_seen_year ??
                   node.properties?.year) as number | undefined;

      if (year) {
        counts.set(year, (counts.get(year) || 0) + 1);
      }
    }

    return counts;
  }, [fullGraphData]);

  // Actions
  const toggleAnimation = useCallback(() => {
    setIsAnimating(prev => !prev);
  }, []);

  const startAnimation = useCallback(() => {
    setIsAnimating(true);
  }, []);

  const stopAnimation = useCallback(() => {
    setIsAnimating(false);
  }, []);

  const resetToStart = useCallback(() => {
    setIsAnimating(false);
    setCurrentYear(yearRange.min);
  }, [yearRange.min]);

  const resetToEnd = useCallback(() => {
    setIsAnimating(false);
    setCurrentYear(yearRange.max);
  }, [yearRange.max]);

  return {
    // State
    currentYear,
    isAnimating,
    animationSpeed,
    yearRange,

    // Filtered data
    filteredNodes,
    filteredEdges,

    // Actions
    setCurrentYear,
    setYearRange,
    toggleAnimation,
    startAnimation,
    stopAnimation,
    setAnimationSpeed,
    resetToStart,
    resetToEnd,

    // Stats
    nodesByYear,
    totalVisibleNodes: filteredNodes.length,
    totalVisibleEdges: filteredEdges.length,
  };
}
