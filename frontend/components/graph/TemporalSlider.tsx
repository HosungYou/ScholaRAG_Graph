'use client';

import { useState, useCallback, useMemo } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Clock,
  ChevronLeft,
  ChevronRight,
  Calendar,
  TrendingUp,
} from 'lucide-react';

/* ============================================================
   TemporalSlider - Time-based Graph Evolution Control
   Phase 2: InfraNodus Integration

   A slider control that allows users to:
   - Scrub through years to see graph evolution
   - Animate the timeline with play/pause
   - See year distribution histogram

   Design: VS Design Diverge Style (Direction B - Editorial Research)
   ============================================================ */

interface TemporalSliderProps {
  currentYear: number;
  yearRange: { min: number; max: number };
  isAnimating: boolean;
  animationSpeed: number;
  onYearChange: (year: number) => void;
  onToggleAnimation: () => void;
  onSpeedChange: (speed: number) => void;
  onReset: () => void;
  onSkipToEnd: () => void;
  nodesByYear?: Map<number, number>;
  totalVisibleNodes: number;
  totalVisibleEdges: number;
  // Minimize toggle
  isMinimized?: boolean;
  onToggleMinimize?: () => void;
}

// Speed presets in milliseconds
const SPEED_PRESETS = [
  { label: '0.5x', value: 2000 },
  { label: '1x', value: 1000 },
  { label: '2x', value: 500 },
  { label: '4x', value: 250 },
];

export function TemporalSlider({
  currentYear,
  yearRange,
  isAnimating,
  animationSpeed,
  onYearChange,
  onToggleAnimation,
  onSpeedChange,
  onReset,
  onSkipToEnd,
  nodesByYear,
  totalVisibleNodes,
  totalVisibleEdges,
  isMinimized = false,
  onToggleMinimize,
}: TemporalSliderProps) {
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);

  // Calculate histogram data
  const histogramData = useMemo(() => {
    if (!nodesByYear || nodesByYear.size === 0) return [];

    const maxCount = Math.max(...Array.from(nodesByYear.values()));
    const years: { year: number; count: number; height: number }[] = [];

    for (let year = yearRange.min; year <= yearRange.max; year++) {
      const count = nodesByYear.get(year) || 0;
      years.push({
        year,
        count,
        height: maxCount > 0 ? (count / maxCount) * 100 : 0,
      });
    }

    return years;
  }, [nodesByYear, yearRange]);

  // Calculate progress percentage
  const progress = useMemo(() => {
    const range = yearRange.max - yearRange.min;
    if (range === 0) return 100;
    return ((currentYear - yearRange.min) / range) * 100;
  }, [currentYear, yearRange]);

  // Handle slider change
  const handleSliderChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onYearChange(parseInt(e.target.value, 10));
  }, [onYearChange]);

  // Handle year step
  const handleYearStep = useCallback((delta: number) => {
    const newYear = Math.max(yearRange.min, Math.min(yearRange.max, currentYear + delta));
    onYearChange(newYear);
  }, [currentYear, yearRange, onYearChange]);

  // Get current speed label
  const currentSpeedLabel = useMemo(() => {
    const preset = SPEED_PRESETS.find(p => p.value === animationSpeed);
    return preset?.label || '1x';
  }, [animationSpeed]);

  // Minimized view
  if (isMinimized) {
    return (
      <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-20">
        <button
          onClick={onToggleMinimize}
          className="bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 px-4 py-2 flex items-center gap-2 hover:bg-surface/10 transition-colors"
        >
          <Clock className="w-4 h-4 text-accent-teal" />
          <span className="font-mono text-sm text-ink dark:text-paper">{currentYear}</span>
          {isAnimating && (
            <div className="w-2 h-2 bg-accent-teal rounded-full animate-pulse" />
          )}
        </button>
      </div>
    );
  }

  return (
    <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-20 w-full max-w-2xl px-4">
      <div className="bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 p-4 relative">
        {/* Decorative corner accent */}
        <div className="absolute top-0 left-0 w-16 h-16 bg-accent-teal/10 transform -rotate-45 -translate-x-8 -translate-y-8" />

        {/* Header */}
        <div className="flex items-center justify-between mb-4 relative">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 flex items-center justify-center bg-accent-teal/10">
              <TrendingUp className="w-3 h-3 text-accent-teal" />
            </div>
            <span className="font-mono text-xs uppercase tracking-wider text-muted">
              Graph Evolution
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Stats */}
            <span className="font-mono text-xs text-muted">
              {totalVisibleNodes} nodes / {totalVisibleEdges} edges
            </span>

            {/* Minimize button */}
            {onToggleMinimize && (
              <button
                onClick={onToggleMinimize}
                className="p-1 hover:bg-surface/10 transition-colors"
                title="Minimize"
              >
                <ChevronRight className="w-4 h-4 text-muted rotate-90" />
              </button>
            )}
          </div>
        </div>

        {/* Current Year Display */}
        <div className="text-center mb-4">
          <div className="inline-flex items-center gap-3 bg-surface/5 px-6 py-2">
            <Calendar className="w-5 h-5 text-accent-teal" />
            <span className="font-mono text-3xl font-bold text-ink dark:text-paper">
              {currentYear}
            </span>
          </div>
        </div>

        {/* Histogram (mini visualization of nodes per year) */}
        {histogramData.length > 0 && (
          <div className="h-8 flex items-end gap-px mb-2 px-2">
            {histogramData.map(({ year, count, height }) => (
              <div
                key={year}
                className="flex-1 relative group"
                style={{
                  minWidth: '2px',
                  maxWidth: histogramData.length > 30 ? '8px' : '16px',
                }}
              >
                <div
                  className={`w-full transition-all ${
                    year <= currentYear
                      ? year === currentYear
                        ? 'bg-accent-teal'
                        : 'bg-accent-teal/50'
                      : 'bg-surface/20'
                  }`}
                  style={{ height: `${Math.max(2, height)}%` }}
                />
                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-ink text-paper font-mono text-xs opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                  {year}: {count} nodes
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Slider Track */}
        <div className="relative mb-4">
          {/* Progress bar background */}
          <div className="absolute inset-y-0 left-0 right-0 h-2 top-1/2 -translate-y-1/2 bg-surface/10" />

          {/* Progress bar fill */}
          <div
            className="absolute inset-y-0 left-0 h-2 top-1/2 -translate-y-1/2 bg-accent-teal transition-all"
            style={{ width: `${progress}%` }}
          />

          {/* Actual slider input */}
          <input
            type="range"
            min={yearRange.min}
            max={yearRange.max}
            value={currentYear}
            onChange={handleSliderChange}
            className="relative w-full h-4 appearance-none bg-transparent cursor-pointer z-10
              [&::-webkit-slider-thumb]:appearance-none
              [&::-webkit-slider-thumb]:w-4
              [&::-webkit-slider-thumb]:h-4
              [&::-webkit-slider-thumb]:bg-accent-teal
              [&::-webkit-slider-thumb]:border-2
              [&::-webkit-slider-thumb]:border-paper
              [&::-webkit-slider-thumb]:dark:border-ink
              [&::-webkit-slider-thumb]:cursor-pointer
              [&::-webkit-slider-thumb]:transition-transform
              [&::-webkit-slider-thumb]:hover:scale-125
              [&::-moz-range-thumb]:w-4
              [&::-moz-range-thumb]:h-4
              [&::-moz-range-thumb]:bg-accent-teal
              [&::-moz-range-thumb]:border-2
              [&::-moz-range-thumb]:border-paper
              [&::-moz-range-thumb]:dark:border-ink
              [&::-moz-range-thumb]:cursor-pointer"
          />
        </div>

        {/* Year labels */}
        <div className="flex items-center justify-between mb-4 px-1">
          <span className="font-mono text-xs text-muted">{yearRange.min}</span>
          <span className="font-mono text-xs text-muted">{yearRange.max}</span>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-center gap-2">
          {/* Skip to start */}
          <button
            onClick={onReset}
            className="p-2 hover:bg-surface/10 transition-colors"
            title="Skip to start"
          >
            <SkipBack className="w-4 h-4 text-muted hover:text-ink dark:hover:text-paper" />
          </button>

          {/* Step back */}
          <button
            onClick={() => handleYearStep(-1)}
            className="p-2 hover:bg-surface/10 transition-colors"
            title="Previous year"
          >
            <ChevronLeft className="w-4 h-4 text-muted hover:text-ink dark:hover:text-paper" />
          </button>

          {/* Play/Pause */}
          <button
            onClick={onToggleAnimation}
            className={`p-3 transition-colors ${
              isAnimating
                ? 'bg-accent-teal text-white'
                : 'bg-surface/10 hover:bg-surface/20 text-ink dark:text-paper'
            }`}
            title={isAnimating ? 'Pause' : 'Play'}
          >
            {isAnimating ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5" />
            )}
          </button>

          {/* Step forward */}
          <button
            onClick={() => handleYearStep(1)}
            className="p-2 hover:bg-surface/10 transition-colors"
            title="Next year"
          >
            <ChevronRight className="w-4 h-4 text-muted hover:text-ink dark:hover:text-paper" />
          </button>

          {/* Skip to end */}
          <button
            onClick={onSkipToEnd}
            className="p-2 hover:bg-surface/10 transition-colors"
            title="Skip to end"
          >
            <SkipForward className="w-4 h-4 text-muted hover:text-ink dark:hover:text-paper" />
          </button>

          {/* Speed selector */}
          <div className="relative ml-4">
            <button
              onClick={() => setShowSpeedMenu(!showSpeedMenu)}
              className="flex items-center gap-1 px-3 py-1.5 bg-surface/10 hover:bg-surface/20 transition-colors"
            >
              <Clock className="w-3 h-3 text-muted" />
              <span className="font-mono text-xs text-ink dark:text-paper">
                {currentSpeedLabel}
              </span>
            </button>

            {/* Speed menu dropdown */}
            {showSpeedMenu && (
              <div className="absolute bottom-full left-0 mb-1 bg-paper dark:bg-ink border border-ink/10 dark:border-paper/10 py-1 min-w-[80px]">
                {SPEED_PRESETS.map(({ label, value }) => (
                  <button
                    key={value}
                    onClick={() => {
                      onSpeedChange(value);
                      setShowSpeedMenu(false);
                    }}
                    className={`w-full px-3 py-1.5 text-left font-mono text-xs hover:bg-surface/10 transition-colors ${
                      animationSpeed === value
                        ? 'text-accent-teal bg-accent-teal/10'
                        : 'text-ink dark:text-paper'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
