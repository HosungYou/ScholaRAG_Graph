'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Cpu,
  Database,
  BookOpen,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react';
/* ============================================================
   StatusBar - VS Design Diverge Style
   Shows real-time system status: LLM, Vectors, Data Source

   Design: Compact, monospace, high-contrast indicators
   ============================================================ */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SystemStatus {
  llm: {
    provider: string;
    model: string;
    connected: boolean;
  };
  vectors: {
    total: number;
    indexed: number;
    status: 'ready' | 'pending' | 'error';
  };
  dataSource: {
    type: 'zotero' | 'pdf' | 'scholarag' | null;
    importedAt: string | null;
    paperCount: number;
  };
}

interface StatusBarProps {
  projectId: string;
}

export function StatusBar({ projectId }: StatusBarProps) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_URL}/api/system/status?project_id=${projectId}`);
      if (!response.ok) throw new Error('Failed to fetch status');
      const data = await response.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch system status:', err);
      setError('Failed to fetch status');
      // Set default status on error
      setStatus({
        llm: { provider: 'unknown', model: 'N/A', connected: false },
        vectors: { total: 0, indexed: 0, status: 'error' },
        dataSource: { type: null, importedAt: null, paperCount: 0 },
      });
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchStatus();
    // Refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Get data source color and label
  const getDataSourceStyle = (type: string | null) => {
    switch (type) {
      case 'zotero':
        return { bg: 'bg-purple-500/10', text: 'text-purple-400', label: 'ZOTERO' };
      case 'pdf':
        return { bg: 'bg-blue-500/10', text: 'text-blue-400', label: 'PDF' };
      case 'scholarag':
        return { bg: 'bg-accent-teal/10', text: 'text-accent-teal', label: 'SCHOLARAG' };
      default:
        return { bg: 'bg-surface/10', text: 'text-muted', label: 'NONE' };
    }
  };

  // Get vector status style
  const getVectorStatusStyle = (status: string) => {
    switch (status) {
      case 'ready':
        return { color: 'text-green-500', icon: CheckCircle2 };
      case 'pending':
        return { color: 'text-amber-500', icon: Loader2 };
      case 'error':
        return { color: 'text-red-500', icon: XCircle };
      default:
        return { color: 'text-muted', icon: Database };
    }
  };

  if (isLoading && !status) {
    return (
      <div className="absolute bottom-4 right-20 flex items-center gap-2 bg-paper/80 dark:bg-ink/80 backdrop-blur px-3 py-2 border border-ink/10 dark:border-paper/10 z-20">
        <Loader2 className="w-4 h-4 text-accent-teal animate-spin" />
        <span className="font-mono text-xs text-muted">Loading status...</span>
      </div>
    );
  }

  const dataSourceStyle = getDataSourceStyle(status?.dataSource?.type ?? null);
  const vectorStatusStyle = getVectorStatusStyle(status?.vectors?.status ?? 'error');
  const VectorIcon = vectorStatusStyle.icon;

  return (
    <div className="absolute bottom-4 right-20 flex items-center gap-3 bg-paper/90 dark:bg-ink/90 backdrop-blur px-3 py-2 border border-ink/10 dark:border-paper/10 z-20">
      {/* LLM Connection Status */}
      <div className="flex items-center gap-2" title={`LLM: ${status?.llm?.provider || 'Unknown'}`}>
        <Cpu className="w-4 h-4 text-muted" />
        <span className={`w-2 h-2 rounded-full ${status?.llm?.connected ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="font-mono text-xs text-ink dark:text-paper truncate max-w-[100px]">
          {status?.llm?.model || 'No LLM'}
        </span>
      </div>

      {/* Divider */}
      <div className="w-px h-4 bg-ink/10 dark:bg-paper/10" />

      {/* Vector Status */}
      <div
        className="flex items-center gap-2"
        title={`Vectors: ${status?.vectors?.indexed || 0}/${status?.vectors?.total || 0} indexed`}
      >
        <VectorIcon className={`w-4 h-4 ${vectorStatusStyle.color} ${status?.vectors?.status === 'pending' ? 'animate-spin' : ''}`} />
        <span className="font-mono text-xs text-ink dark:text-paper">
          {status?.vectors?.indexed || 0}/{status?.vectors?.total || 0}
        </span>
      </div>

      {/* Divider */}
      <div className="w-px h-4 bg-ink/10 dark:bg-paper/10" />

      {/* Data Source Badge */}
      <div className="flex items-center gap-2">
        <BookOpen className="w-4 h-4 text-muted" />
        <span className={`font-mono text-xs px-1.5 py-0.5 ${dataSourceStyle.bg} ${dataSourceStyle.text} uppercase`}>
          {dataSourceStyle.label}
        </span>
        {status?.dataSource?.paperCount ? (
          <span className="font-mono text-xs text-muted">
            ({status.dataSource.paperCount})
          </span>
        ) : null}
      </div>

      {/* Refresh Button */}
      <button
        onClick={fetchStatus}
        disabled={isLoading}
        className="p-1 hover:bg-surface/10 transition-colors disabled:opacity-50"
        title="Refresh status"
      >
        <RefreshCw className={`w-3 h-3 text-muted hover:text-accent-teal ${isLoading ? 'animate-spin' : ''}`} />
      </button>
    </div>
  );
}
