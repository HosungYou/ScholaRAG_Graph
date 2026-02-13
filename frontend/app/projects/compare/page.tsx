'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { Header, Footer } from '@/components/layout';
import { ThemeToggle, ErrorDisplay, ErrorBoundary } from '@/components/ui';
import { GraphComparison } from '@/components/graph/GraphComparison';
import { GitCompare, Loader2 } from 'lucide-react';

/* ============================================================
   ScholaRAG Graph - Project Comparison Page
   Phase 5: InfraNodus Integration

   Allows users to compare two project knowledge graphs to see:
   - Common entities (intersection)
   - Unique entities (difference)
   - Similarity metrics

   Design: VS Design Diverge Style
   ============================================================ */

function CompareContent() {
  const { user } = useAuth();
  const { data: projects, isLoading, error, refetch } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects(),
    enabled: !!user,  // BUG-043: Only fetch when authenticated
    retry: (failureCount, error) => {
      if (error instanceof Error && 'status' in error) {
        const status = (error as any).status;
        if (status === 401 || status === 403) return false;
      }
      return failureCount < 2;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="w-10 h-10 text-accent-teal animate-spin mx-auto mb-4" />
          <p className="font-mono text-sm text-muted">Loading projects...</p>
        </div>
      </div>
    );
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

  if (!projects || projects.length < 2) {
    return (
      <div className="text-center py-20">
        <div className="w-20 h-20 flex items-center justify-center bg-surface/5 mx-auto mb-4">
          <GitCompare className="w-10 h-10 text-muted" />
        </div>
        <h3 className="font-display text-xl text-ink dark:text-paper mb-3">
          Need More Projects
        </h3>
        <p className="text-muted max-w-md mx-auto">
          You need at least two projects to compare. Import more ScholaRAG
          projects to use the comparison feature.
        </p>
      </div>
    );
  }

  return <GraphComparison projects={projects} />;
}

export default function ComparePage() {
  return (
    <div className="min-h-screen bg-paper dark:bg-ink flex flex-col">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <Header
        breadcrumbs={[
          { label: 'Projects', href: '/projects' },
          { label: 'Compare' },
        ]}
        rightContent={<ThemeToggle />}
      />

      <main id="main-content" className="flex-1">
        <ErrorBoundary>
          <CompareContent />
        </ErrorBoundary>
      </main>

      <Footer minimal />
    </div>
  );
}
