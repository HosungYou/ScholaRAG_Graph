'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { api } from '@/lib/api';

interface TimelineBucket {
  year: number;
  new_concepts: number;
  total_concepts: number;
  top_concepts: string[];
}

interface TimelineData {
  min_year: number | null;
  max_year: number | null;
  buckets: TimelineBucket[];
  total_with_year: number;
  total_without_year: number;
}

interface TemporalViewProps {
  projectId: string;
}

export function TemporalView({ projectId }: TemporalViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredYear, setHoveredYear] = useState<number | null>(null);

  // Fetch timeline data on mount
  useEffect(() => {
    let cancelled = false;
    async function fetchTimeline() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getTemporalTimeline(projectId);
        if (!cancelled) {
          setData(result);
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message || 'Failed to load timeline data');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    fetchTimeline();
    return () => { cancelled = true; };
  }, [projectId]);

  // D3 rendering
  useEffect(() => {
    if (!data || !data.buckets.length || data.min_year === null || !svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = Math.min(400, Math.max(280, container.clientHeight - 120));
    const margin = { top: 20, right: 60, bottom: 50, left: 50 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Clear previous
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const buckets = data.buckets;

    // Scales
    const x = d3.scaleBand<number>()
      .domain(buckets.map(d => d.year))
      .range([0, innerWidth])
      .padding(0.2);

    const yLeft = d3.scaleLinear()
      .domain([0, d3.max(buckets, d => d.new_concepts) || 1])
      .nice()
      .range([innerHeight, 0]);

    const yRight = d3.scaleLinear()
      .domain([0, d3.max(buckets, d => d.total_concepts) || 1])
      .nice()
      .range([innerHeight, 0]);

    // Tick filter for overcrowded x-axis (max ~12 labels)
    const allYears = buckets.map(d => d.year);
    const maxTicks = 12;
    const tickValues = allYears.length <= maxTicks
      ? allYears
      : allYears.filter((_, i) => i % Math.ceil(allYears.length / maxTicks) === 0 || i === allYears.length - 1);

    // X axis
    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(x).tickValues(tickValues).tickFormat(d => String(d)))
      .selectAll('text')
      .attr('class', 'fill-muted')
      .style('font-size', '10px')
      .style('font-family', 'monospace')
      .attr('transform', allYears.length > 20 ? 'rotate(-45)' : 'rotate(0)')
      .style('text-anchor', allYears.length > 20 ? 'end' : 'middle');

    // Y axis left (new concepts)
    g.append('g')
      .call(d3.axisLeft(yLeft).ticks(5))
      .selectAll('text')
      .attr('class', 'fill-muted')
      .style('font-size', '10px')
      .style('font-family', 'monospace');

    // Y axis right (cumulative)
    g.append('g')
      .attr('transform', `translate(${innerWidth},0)`)
      .call(d3.axisRight(yRight).ticks(5))
      .selectAll('text')
      .style('fill', '#E67E22')
      .style('font-size', '10px')
      .style('font-family', 'monospace');

    // Y axis labels
    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -40)
      .attr('x', -innerHeight / 2)
      .attr('text-anchor', 'middle')
      .style('font-size', '11px')
      .style('font-family', 'monospace')
      .attr('class', 'fill-muted')
      .text('New Concepts');

    g.append('text')
      .attr('transform', 'rotate(90)')
      .attr('y', -innerWidth - 45)
      .attr('x', innerHeight / 2)
      .attr('text-anchor', 'middle')
      .style('font-size', '11px')
      .style('font-family', 'monospace')
      .style('fill', '#E67E22')
      .text('Cumulative');

    // Bars (new concepts)
    g.selectAll('.bar')
      .data(buckets)
      .join('rect')
      .attr('class', 'bar')
      .attr('x', d => x(d.year)!)
      .attr('y', d => yLeft(d.new_concepts))
      .attr('width', x.bandwidth())
      .attr('height', d => innerHeight - yLeft(d.new_concepts))
      .attr('fill', '#2EC4B6')
      .attr('opacity', 0.85)
      .attr('rx', 2)
      .on('mouseenter', function(event, d) {
        d3.select(this).attr('fill', '#45B7D1').attr('opacity', 1);
        setHoveredYear(d.year);
        // Position tooltip
        if (tooltipRef.current) {
          const rect = (event.target as SVGRectElement).getBoundingClientRect();
          const containerRect = container.getBoundingClientRect();
          tooltipRef.current.style.left = `${rect.left - containerRect.left + rect.width / 2}px`;
          tooltipRef.current.style.top = `${rect.top - containerRect.top - 8}px`;
        }
      })
      .on('mouseleave', function() {
        d3.select(this).attr('fill', '#2EC4B6').attr('opacity', 0.85);
        setHoveredYear(null);
      });

    // Cumulative line
    const line = d3.line<TimelineBucket>()
      .x(d => (x(d.year) || 0) + x.bandwidth() / 2)
      .y(d => yRight(d.total_concepts))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(buckets)
      .attr('fill', 'none')
      .attr('stroke', '#E67E22')
      .attr('stroke-width', 2.5)
      .attr('d', line);

    // Cumulative dots
    g.selectAll('.dot')
      .data(buckets)
      .join('circle')
      .attr('class', 'dot')
      .attr('cx', d => (x(d.year) || 0) + x.bandwidth() / 2)
      .attr('cy', d => yRight(d.total_concepts))
      .attr('r', 3.5)
      .attr('fill', '#E67E22')
      .attr('stroke', 'white')
      .attr('stroke-width', 1.5);

    // Grid lines
    g.selectAll('.grid-line')
      .data(yLeft.ticks(5))
      .join('line')
      .attr('class', 'grid-line')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', d => yLeft(d))
      .attr('y2', d => yLeft(d))
      .attr('stroke', 'currentColor')
      .attr('stroke-opacity', 0.06)
      .attr('stroke-dasharray', '3,3');

  }, [data]);

  // Get hovered bucket for tooltip
  const hoveredBucket = data?.buckets.find(b => b.year === hoveredYear) || null;

  // Loading state
  if (loading) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-paper dark:bg-ink">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-teal border-t-transparent rounded-full animate-spin" />
          <span className="font-mono text-xs text-muted uppercase tracking-wider">Loading timeline...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-paper dark:bg-ink">
        <div className="flex flex-col items-center gap-3 text-center px-8">
          <span className="text-accent-red text-lg">!</span>
          <span className="font-mono text-xs text-muted">{error}</span>
        </div>
      </div>
    );
  }

  // Empty state
  if (!data || !data.buckets.length || data.min_year === null) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-paper dark:bg-ink">
        <div className="flex flex-col items-center gap-3 text-center px-8">
          <span className="text-muted text-2xl">⏳</span>
          <span className="font-mono text-sm text-ink dark:text-paper">No temporal data available</span>
          <span className="font-mono text-xs text-muted max-w-sm">
            Entities need year information (first_seen_year or source_year) for timeline visualization.
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 bg-paper dark:bg-ink overflow-hidden flex flex-col" ref={containerRef}>
      {/* Header */}
      <div className="flex-none px-4 pt-3 pb-2 border-b border-ink/10 dark:border-paper/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="font-mono text-sm font-medium text-ink dark:text-paper uppercase tracking-wider">
              Temporal Timeline
            </h3>
            <span className="font-mono text-xs text-muted">
              {data.min_year} — {data.max_year}
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-muted">
            <span>{data.total_with_year} with year</span>
            {data.total_without_year > 0 && (
              <span className="text-accent-amber">{data.total_without_year} undated</span>
            )}
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-2">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#2EC4B6' }} />
            <span className="font-mono text-xs text-muted">New Concepts</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 rounded" style={{ backgroundColor: '#E67E22' }} />
            <div className="w-2 h-2 rounded-full border-2" style={{ borderColor: '#E67E22' }} />
            <span className="font-mono text-xs text-muted">Cumulative</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 relative px-2 py-2 min-h-0">
        <svg ref={svgRef} className="w-full h-full" />

        {/* Tooltip */}
        {hoveredBucket && (
          <div
            ref={tooltipRef}
            className="absolute pointer-events-none z-50 -translate-x-1/2 -translate-y-full"
          >
            <div className="bg-ink dark:bg-paper text-paper dark:text-ink px-3 py-2 rounded shadow-lg border border-ink/20 dark:border-paper/20 min-w-[180px]">
              <div className="font-mono text-xs font-bold mb-1">{hoveredBucket.year}</div>
              <div className="flex justify-between font-mono text-xs gap-4">
                <span className="text-paper/70 dark:text-ink/70">New:</span>
                <span style={{ color: '#2EC4B6' }}>+{hoveredBucket.new_concepts}</span>
              </div>
              <div className="flex justify-between font-mono text-xs gap-4">
                <span className="text-paper/70 dark:text-ink/70">Total:</span>
                <span style={{ color: '#E67E22' }}>{hoveredBucket.total_concepts}</span>
              </div>
              {hoveredBucket.top_concepts.length > 0 && (
                <div className="mt-1.5 pt-1.5 border-t border-paper/20 dark:border-ink/20">
                  <div className="font-mono text-xs text-paper/50 dark:text-ink/50 mb-0.5">Top concepts:</div>
                  {hoveredBucket.top_concepts.slice(0, 3).map((c, i) => (
                    <div key={i} className="font-mono text-xs truncate text-paper/80 dark:text-ink/80">
                      {c}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
