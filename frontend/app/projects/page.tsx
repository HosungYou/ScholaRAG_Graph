'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Network, Plus, ArrowRight, FileText, Users, Hexagon, AlertTriangle, Play, RefreshCw, Clock, CheckCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { Header, Footer } from '@/components/layout';
import {
  ThemeToggle,
  ErrorDisplay,
  ProjectListSkeleton,
  ErrorBoundary,
} from '@/components/ui';
import type { Project, ImportJob } from '@/types';

/* ============================================================
   ScholaRAG Graph - Projects Page
   VS Design Diverge: Direction B (T-Score 0.4) "Editorial Research"

   Design Principles:
   - List view by default (not card grid)
   - Project numbers (01, 02, 03) instead of icons
   - Monospace metrics display
   - Line-based row structure
   - Hover reveals arrow indicator
   ============================================================ */

function ProjectRow({ project, index }: { project: Project; index: number }) {
  const projectNumber = String(index + 1).padStart(2, '0');
  const createdDate = new Date(project.created_at);
  const dateStr = createdDate.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
  const timeStr = createdDate.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

  return (
    <Link
      href={`/projects/${project.id}`}
      className="project-row group flex items-center gap-6 py-6 border-b border-ink/10 dark:border-paper/10 hover:bg-surface/5 transition-colors -mx-6 px-6"
    >
      {/* Number Indicator */}
      <div className="flex-shrink-0 w-12">
        <span className="font-mono text-2xl text-accent-teal/40 group-hover:text-accent-teal transition-colors">
          {projectNumber}
        </span>
      </div>

      {/* Project Info */}
      <div className="flex-1 min-w-0">
        <h3 className="font-display text-xl text-ink dark:text-paper group-hover:text-accent-teal transition-colors truncate">
          {project.name}
        </h3>
        {project.research_question && (
          <p className="text-muted text-sm mt-1 line-clamp-1">
            {project.research_question}
          </p>
        )}
      </div>

      {/* Metrics */}
      <div className="hidden md:flex items-center gap-8">
        {project.stats?.total_papers !== undefined && (
          <div className="text-right">
            <div className="font-mono text-lg text-ink dark:text-paper">
              {project.stats.total_papers}
            </div>
            <div className="text-xs text-muted uppercase tracking-wider">papers</div>
          </div>
        )}
        {project.stats?.total_authors !== undefined && (
          <div className="text-right">
            <div className="font-mono text-lg text-ink dark:text-paper">
              {project.stats.total_authors}
            </div>
            <div className="text-xs text-muted uppercase tracking-wider">authors</div>
          </div>
        )}
      </div>

      {/* Date & Time */}
      <div className="hidden sm:block text-right w-32">
        <div className="font-mono text-sm text-muted">{dateStr}</div>
        <div className="font-mono text-xs text-muted/60">{timeStr}</div>
      </div>

      {/* Arrow */}
      <div className="flex-shrink-0 w-8">
        <ArrowRight className="w-5 h-5 text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </Link>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-20">
      <div className="relative inline-block mb-8">
        <Hexagon className="w-24 h-24 text-accent-teal/20" strokeWidth={1} />
        <Network className="w-10 h-10 text-accent-teal absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
      </div>

      <h3 className="font-display text-2xl text-ink dark:text-paper mb-3">
        No Projects Yet
      </h3>
      <p className="text-muted max-w-md mx-auto mb-8">
        Import your ScholaRAG folder to create your first Knowledge Graph
        and start exploring research connections.
      </p>

      <Link
        href="/import"
        className="btn btn--primary inline-flex items-center gap-2"
      >
        <Plus className="w-5 h-5" />
        <span>Import ScholaRAG Project</span>
      </Link>
    </div>
  );
}

/**
 * Interrupted Imports Section
 * Shows import jobs that were interrupted (e.g., by server restart)
 * and allows users to resume them.
 */
function InterruptedImportsSection() {
  const queryClient = useQueryClient();
  const [resumingJobId, setResumingJobId] = useState<string | null>(null);

  const { data: interruptedJobs, isLoading } = useQuery({
    queryKey: ['interruptedJobs'],
    queryFn: () => api.getImportJobs('interrupted', 10),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const resumeMutation = useMutation({
    mutationFn: (jobId: string) => api.resumeImport(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['interruptedJobs'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
    onError: (error) => {
      console.error('Failed to resume import:', error);
      alert(`Resume 실패: ${error instanceof Error ? error.message : 'Unknown error'}`);
    },
    onSettled: () => {
      setResumingJobId(null);
    },
  });

  const handleResume = async (jobId: string) => {
    setResumingJobId(jobId);
    resumeMutation.mutate(jobId);
  };

  if (isLoading || !interruptedJobs || interruptedJobs.length === 0) {
    return null;
  }

  return (
    <div className="mb-8 p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
        <h3 className="font-display text-lg text-amber-800 dark:text-amber-200">
          중단된 Import ({interruptedJobs.length}개)
        </h3>
      </div>

      <div className="space-y-3">
        {interruptedJobs.map((job) => {
          const createdDate = new Date(job.created_at);
          const dateStr = createdDate.toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
          });
          const timeStr = createdDate.toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit',
          });
          const progress = Math.round((job.progress || 0) * 100);
          const isResuming = resumingJobId === job.job_id;

          return (
            <div
              key={job.job_id}
              className="flex items-center gap-4 p-3 bg-white dark:bg-ink/50 rounded border border-amber-100 dark:border-amber-900"
            >
              {/* Status Icon */}
              <div className="flex-shrink-0">
                <Clock className="w-5 h-5 text-amber-500" />
              </div>

              {/* Job Info */}
              <div className="flex-1 min-w-0">
                <div className="font-medium text-ink dark:text-paper truncate">
                  {job.metadata?.project_name || 'Import Job'}
                </div>
                <div className="text-sm text-muted">
                  {dateStr} {timeStr} • 진행률 {progress}%
                  {job.message && ` • ${job.message}`}
                </div>
              </div>

              {/* Resume Button */}
              <button
                onClick={() => handleResume(job.job_id)}
                disabled={isResuming}
                className="flex-shrink-0 flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 disabled:bg-amber-300 text-white rounded-lg transition-colors"
              >
                {isResuming ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>재개 중...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    <span>Resume</span>
                  </>
                )}
              </button>
            </div>
          );
        })}
      </div>

      <p className="mt-3 text-sm text-amber-700 dark:text-amber-300">
        서버 재시작으로 중단된 Import입니다. Resume 버튼을 클릭하면 중단된 지점부터 다시 시작합니다.
      </p>
    </div>
  );
}

function ProjectsContent() {
  const { data: projects, isLoading, error, refetch } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects(),
  });

  if (isLoading) {
    return <ProjectListSkeleton count={6} />;
  }

  if (error) {
    return (
      <ErrorDisplay
        error={error as Error}
        title="Failed to load projects"
        message="Please check if the backend server is running."
        onRetry={() => refetch()}
      />
    );
  }

  if (!projects || projects.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="divide-y-0">
      {/* List Header */}
      <div className="hidden md:flex items-center gap-6 py-3 border-b border-ink/20 dark:border-paper/20 text-xs text-muted uppercase tracking-wider font-mono">
        <div className="w-12">#</div>
        <div className="flex-1">Project</div>
        <div className="w-16 text-right">Papers</div>
        <div className="w-16 text-right">Authors</div>
        <div className="w-32 text-right">Created</div>
        <div className="w-8"></div>
      </div>

      {/* Project Rows */}
      {projects.map((project, index) => (
        <ProjectRow key={project.id} project={project} index={index} />
      ))}
    </div>
  );
}

export default function ProjectsPage() {
  return (
    <div className="min-h-screen bg-paper dark:bg-ink flex flex-col">
      <a href="#main-content" className="skip-link">
        메인 콘텐츠로 건너뛰기
      </a>

      <Header
        breadcrumbs={[{ label: 'Projects' }]}
        rightContent={
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/import"
              className="btn btn--primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">Import Project</span>
            </Link>
          </div>
        }
      />

      <main id="main-content" className="flex-1 max-w-5xl mx-auto px-6 py-8 md:py-12 w-full">
        {/* Page Header */}
        <div className="mb-8 md:mb-12">
          <span className="text-accent-teal font-mono text-sm tracking-widest uppercase">
            Research Portfolio
          </span>
          <h1 className="font-display text-3xl md:text-4xl text-ink dark:text-paper mt-2">
            Your Projects
          </h1>
        </div>

        <ErrorBoundary>
          <InterruptedImportsSection />
          <ProjectsContent />
        </ErrorBoundary>
      </main>

      <Footer minimal />
    </div>
  );
}
