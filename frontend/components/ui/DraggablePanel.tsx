'use client';

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';

interface DraggablePanelProps {
  /** Unique key for localStorage persistence */
  panelId: string;
  /** Optional project ID for per-project position persistence */
  projectId?: string;
  /** Default position if no saved position exists */
  defaultPosition: { x: number; y: number };
  /** Panel content */
  children: ReactNode;
  /** Additional className for the outer wrapper */
  className?: string;
  /** z-index for layering */
  zIndex?: number;
}

function getStorageKey(panelId: string, projectId?: string): string {
  return projectId ? `panel-pos-${projectId}-${panelId}` : `panel-pos-${panelId}`;
}

export function DraggablePanel({
  panelId,
  projectId,
  defaultPosition,
  children,
  className = '',
  zIndex = 20,
}: DraggablePanelProps) {
  const [position, setPosition] = useState(defaultPosition);
  const [isDragging, setIsDragging] = useState(false);
  const dragOffset = useRef({ x: 0, y: 0 });
  const panelRef = useRef<HTMLDivElement>(null);

  // Load saved position from localStorage
  useEffect(() => {
    try {
      const key = getStorageKey(panelId, projectId);
      const saved = localStorage.getItem(key);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
          // Validate position is within viewport
          const maxX = window.innerWidth - 100;
          const maxY = window.innerHeight - 50;
          setPosition({
            x: Math.max(0, Math.min(parsed.x, maxX)),
            y: Math.max(0, Math.min(parsed.y, maxY)),
          });
        }
      }
    } catch {
      // Ignore localStorage errors
    }
  }, [panelId, projectId]);

  // Save position to localStorage
  const savePosition = useCallback(
    (pos: { x: number; y: number }) => {
      try {
        const key = getStorageKey(panelId, projectId);
        localStorage.setItem(key, JSON.stringify(pos));
      } catch {
        // Ignore localStorage errors
      }
    },
    [panelId, projectId]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      // Only drag from the handle area (data-drag-handle attribute)
      const target = e.target as HTMLElement;
      if (!target.closest('[data-drag-handle]')) return;

      e.preventDefault();
      setIsDragging(true);
      dragOffset.current = {
        x: e.clientX - position.x,
        y: e.clientY - position.y,
      };
    },
    [position]
  );

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newX = e.clientX - dragOffset.current.x;
      const newY = e.clientY - dragOffset.current.y;

      // Clamp to viewport bounds
      const maxX = window.innerWidth - (panelRef.current?.offsetWidth || 200);
      const maxY = window.innerHeight - 50;

      const clampedPos = {
        x: Math.max(0, Math.min(newX, maxX)),
        y: Math.max(0, Math.min(newY, maxY)),
      };

      setPosition(clampedPos);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      savePosition(position);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, savePosition, position]);

  return (
    <div
      ref={panelRef}
      className={`absolute ${className}`}
      style={{
        left: position.x,
        top: position.y,
        zIndex,
        cursor: isDragging ? 'grabbing' : undefined,
        userSelect: isDragging ? 'none' : undefined,
      }}
      onMouseDown={handleMouseDown}
    >
      {children}
    </div>
  );
}

/** Small drag handle bar to add at the top of panels */
export function DragHandle({ className = '' }: { className?: string }) {
  return (
    <div
      data-drag-handle
      className={`flex items-center justify-center py-1 cursor-grab active:cursor-grabbing ${className}`}
      title="Drag to move panel"
    >
      <div className="w-8 h-1 rounded-full bg-ink/20 dark:bg-paper/20" />
    </div>
  );
}
