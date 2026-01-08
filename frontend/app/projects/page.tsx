'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Network, Plus, Calendar, FileText, Users } from 'lucide-react';
import { api } from '@/lib/api';
import { Header, Footer } from '@/components/layout';
import {
  ThemeToggle,
  ErrorDisplay,
  ProjectListSkeleton,
  ErrorBoundary,
} from '@/components/ui';
import type { Project } from '@/types';

function ProjectCard({ project }: { project: Project }) {
  return (
    <Link
      href={`/projects/${project.id}`}
      className="group bg-white dark:bg-gray-800 rounded-xl border dark:border-gray-700 shadow-sm hover:shadow-md transition-all p-5 sm:p-6 touch-target"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50 transition-colors">
          <Network className="w-6 h-6 text-blue-600 dark:text-blue-400" />
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1">
          <Calendar className="w-4 h-4" />
          {new Date(project.created_at).toLocaleDateString('ko-KR')}
        </span>
      </div>

      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-1">
        {project.name}
      </h3>

      {project.research_question && (
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-4 line-clamp-2">
          {project.research_question}
        </p>
      )}

      {project.stats && (
        <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
          {project.stats.total_papers !== undefined && (
            <span className="flex items-center gap-1">
              <FileText className="w-4 h-4" />
              {project.stats.total_papers} papers
            </span>
          )}
          {project.stats.total_authors !== undefined && (
            <span className="flex items-center gap-1">
              <Users className="w-4 h-4" />
              {project.stats.total_authors} authors
            </span>
          )}
        </div>
      )}
    </Link>
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
        title="프로젝트를 불러올 수 없습니다"
        message="백엔드 서버가 실행 중인지 확인해주세요."
        onRetry={() => refetch()}
      />
    );
  }

  if (!projects || projects.length === 0) {
    return (
      <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border dark:border-gray-700">
        <Network className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          프로젝트가 없습니다
        </h3>
        <p className="text-gray-600 dark:text-gray-300 mb-6">
          ScholaRAG 폴더를 Import하여 첫 번째 Knowledge Graph를 만들어보세요.
        </p>
        <Link
          href="/import"
          className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors touch-target"
        >
          <Plus className="w-5 h-5" />
          Import ScholaRAG Project
        </Link>
      </div>
    );
  }

  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  );
}

export default function ProjectsPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      <a href="#main-content" className="skip-link">
        메인 콘텐츠로 건너뛰기
      </a>

      <Header
        breadcrumbs={[{ label: 'Projects' }]}
        rightContent={
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link
              href="/import"
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors touch-target"
            >
              <Plus className="w-5 h-5" />
              <span className="hidden sm:inline">Import Project</span>
            </Link>
          </div>
        }
      />

      <main id="main-content" className="flex-1 max-w-7xl mx-auto px-4 py-6 sm:py-8 w-full">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Your Projects
        </h2>

        <ErrorBoundary>
          <ProjectsContent />
        </ErrorBoundary>
      </main>

      <Footer minimal />
    </div>
  );
}
