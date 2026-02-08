export {};

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ImportProgress } from '@/components/import/ImportProgress';
import type { ImportJob, ImportReliabilitySummary } from '@/types';

const mockPush = jest.fn();
const mockBack = jest.fn();
const mockGetImportStatus = jest.fn();
const mockGetResumeInfo = jest.fn();
const mockResumeImport = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    back: mockBack,
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
}));

jest.mock('@/lib/api', () => ({
  api: {
    getImportStatus: (...args: unknown[]) => mockGetImportStatus(...args),
    getResumeInfo: (...args: unknown[]) => mockGetResumeInfo(...args),
    resumeImport: (...args: unknown[]) => mockResumeImport(...args),
  },
}));

const reliabilitySummaryFixture: ImportReliabilitySummary = {
  raw_entities_extracted: 100,
  entities_after_resolution: 40,
  merges_applied: 12,
  canonicalization_rate: 0.9,
  llm_pairs_reviewed: 4,
  llm_pairs_confirmed: 3,
  llm_confirmation_accept_rate: 0.75,
  potential_false_merge_count: 1,
  potential_false_merge_ratio: 0.025,
  potential_false_merge_samples: [
    {
      entity_type: 'Concept',
      context_bucket: 'ai_core',
      left: 'Graph Attention Network',
      right: 'GAT',
      similarity: 0.96,
    },
  ],
  relationships_created: 22,
  evidence_backed_relationships: 18,
  provenance_coverage: 0.8,
  low_trust_edges: 5,
  low_trust_edge_ratio: 0.12,
};

function buildCompletedJob(overrides?: Partial<ImportJob>): ImportJob {
  return {
    job_id: 'job-1',
    status: 'completed',
    progress: 1,
    current_step: 'finalize',
    project_id: 'project-fallback',
    result: {
      project_id: undefined,
      nodes_created: 12,
      edges_created: 34,
    },
    ...overrides,
  };
}

function buildInterruptedJob(overrides?: Partial<ImportJob>): ImportJob {
  return {
    job_id: 'job-1',
    status: 'interrupted',
    progress: 0.3,
    current_step: 'extract_entities',
    error: 'Import interrupted by server restart',
    ...overrides,
  };
}

describe('ImportProgress', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('uses project_id fallback for completion callback and Open Project navigation', async () => {
    mockGetImportStatus.mockResolvedValueOnce(buildCompletedJob());
    const onComplete = jest.fn();

    render(<ImportProgress jobId="job-1" onComplete={onComplete} />);

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith('project-fallback');
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /open project/i }));

    expect(mockPush).toHaveBeenCalledWith('/projects/project-fallback');
    expect(screen.getByText(/Created 12 nodes and 34 edges/)).toBeInTheDocument();
  });

  it('renders reliability summary cards and fallback summary text from reliability data', async () => {
    const completedWithReliability = buildCompletedJob({
      project_id: 'project-2',
      result: {
        project_id: 'project-2',
      },
      reliability_summary: reliabilitySummaryFixture,
    });
    mockGetImportStatus.mockResolvedValueOnce(completedWithReliability);

    render(<ImportProgress jobId="job-1" />);

    await waitFor(() => {
      expect(screen.getByText(/Resolved 40 entities and 22 relationships/)).toBeInTheDocument();
    });

    expect(screen.getByText(/90\.0% \(12 merges\)/)).toBeInTheDocument();
    expect(screen.getByText(/80\.0%/)).toBeInTheDocument();
    expect(screen.getByText(/100\s*->\s*40/)).toBeInTheDocument();
    expect(screen.getByText(/5 \(12\.0%\)/)).toBeInTheDocument();
    expect(screen.getByText(/3\/4 \(75\.0%\)/)).toBeInTheDocument();
    expect(screen.getByText(/1 \(2\.5%\)/)).toBeInTheDocument();
  });

  it('reads reliability summary from result payload when root summary is absent', async () => {
    const completedWithResultSummary = buildCompletedJob({
      project_id: 'project-3',
      result: {
        project_id: 'project-3',
        reliability_summary: reliabilitySummaryFixture,
      },
      reliability_summary: undefined,
    });
    mockGetImportStatus.mockResolvedValueOnce(completedWithResultSummary);

    render(<ImportProgress jobId="job-1" />);

    await waitFor(() => {
      expect(screen.getByText(/90\.0% \(12 merges\)/)).toBeInTheDocument();
    });
  });

  it('renders interrupted checkpoint details and resumes import successfully', async () => {
    mockGetImportStatus
      .mockResolvedValueOnce(buildInterruptedJob())
      .mockResolvedValueOnce({
        job_id: 'job-1',
        status: 'running',
        progress: 0.4,
        current_step: 'extract_entities',
        total_steps: 7,
        completed_steps: 3,
      });
    mockGetResumeInfo.mockResolvedValueOnce({
      job_id: 'job-1',
      status: 'interrupted',
      can_resume: true,
      checkpoint: {
        processed_count: 3,
        total_papers: 10,
        last_processed_index: 2,
        project_id: 'partial-project-1',
        stage: 'extract_entities',
      },
    });
    mockResumeImport.mockResolvedValueOnce({
      job_id: 'job-1',
      status: 'running',
      progress: 0.4,
      current_step: 'extract_entities',
      total_steps: 7,
      completed_steps: 3,
    });

    const onError = jest.fn();
    render(<ImportProgress jobId="job-1" onError={onError} />);

    await waitFor(() => {
      expect(screen.getByText(/Import Interrupted/i)).toBeInTheDocument();
    });

    expect(mockGetResumeInfo).toHaveBeenCalledWith('job-1');
    expect(onError).toHaveBeenCalledWith('Import interrupted by server restart');
    expect(screen.getByText(/3 \/ 10 papers/i)).toBeInTheDocument();
    expect(screen.getByText(/extract_entities/i)).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Partial Results/i }));
    expect(mockPush).toHaveBeenCalledWith('/projects/partial-project-1');

    await user.click(screen.getByRole('button', { name: /Resume Import/i }));

    await waitFor(() => {
      expect(mockResumeImport).toHaveBeenCalledWith('job-1');
    });
    await waitFor(() => {
      expect(screen.getByText(/Building Knowledge Graph/i)).toBeInTheDocument();
    });
  });

  it('shows resume error message when resume import fails', async () => {
    mockGetImportStatus.mockResolvedValueOnce(buildInterruptedJob());
    mockGetResumeInfo.mockResolvedValueOnce({
      job_id: 'job-1',
      status: 'interrupted',
      can_resume: true,
      checkpoint: {
        processed_count: 2,
        total_papers: 8,
        last_processed_index: 1,
        stage: 'import_papers',
      },
    });
    mockResumeImport.mockRejectedValueOnce(new Error('Resume API failed'));

    render(<ImportProgress jobId="job-1" />);

    await waitFor(() => {
      expect(screen.getByText(/Import Interrupted/i)).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Resume Import/i }));

    await waitFor(() => {
      expect(screen.getByText(/Resume API failed/i)).toBeInTheDocument();
    });
  });

  it('restarts status polling after resume success', async () => {
    jest.useFakeTimers();
    try {
      mockGetImportStatus
        .mockResolvedValueOnce(buildInterruptedJob())
        .mockResolvedValueOnce({
          job_id: 'job-1',
          status: 'running',
          progress: 0.5,
          current_step: 'build_relationships',
        })
        .mockResolvedValueOnce({
          job_id: 'job-1',
          status: 'completed',
          progress: 1,
          current_step: 'finalize',
          project_id: 'project-after-resume',
          result: { project_id: 'project-after-resume' },
        });

      mockGetResumeInfo.mockResolvedValueOnce({
        job_id: 'job-1',
        status: 'interrupted',
        can_resume: true,
        checkpoint: {
          processed_count: 4,
          total_papers: 10,
          last_processed_index: 3,
          stage: 'build_relationships',
        },
      });

      mockResumeImport.mockResolvedValueOnce({
        job_id: 'job-1',
        status: 'running',
        progress: 0.5,
        current_step: 'build_relationships',
      });

      const onComplete = jest.fn();
      render(<ImportProgress jobId="job-1" onComplete={onComplete} />);

      await waitFor(() => {
        expect(screen.getByText(/Import Interrupted/i)).toBeInTheDocument();
      });
      expect(mockGetImportStatus).toHaveBeenCalledTimes(1);

      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      await user.click(screen.getByRole('button', { name: /Resume Import/i }));

      await waitFor(() => {
        expect(mockGetImportStatus).toHaveBeenCalledTimes(2);
      });

      jest.advanceTimersByTime(2000);

      await waitFor(() => {
        expect(mockGetImportStatus).toHaveBeenCalledTimes(3);
      });
      await waitFor(() => {
        expect(onComplete).toHaveBeenCalledWith('project-after-resume');
      });
    } finally {
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
    }
  });

  it('stops polling timers on unmount', async () => {
    jest.useFakeTimers();
    try {
      mockGetImportStatus.mockResolvedValue({
        job_id: 'job-1',
        status: 'running',
        progress: 0.2,
        current_step: 'import_papers',
      });

      const { unmount } = render(<ImportProgress jobId="job-1" />);

      await waitFor(() => {
        expect(mockGetImportStatus).toHaveBeenCalledTimes(1);
      });

      unmount();

      jest.advanceTimersByTime(10000);
      await Promise.resolve();

      expect(mockGetImportStatus).toHaveBeenCalledTimes(1);
    } finally {
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
    }
  });
});
