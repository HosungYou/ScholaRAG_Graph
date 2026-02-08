export {};

import { render, waitFor } from '@testing-library/react';
import { ImportProgress } from '@/components/import/ImportProgress';

const mockGetImportStatus = jest.fn();
const mockGetResumeInfo = jest.fn();
const mockResumeImport = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    back: jest.fn(),
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

describe('ImportProgress snapshots', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('matches completed state snapshot with reliability cards', async () => {
    mockGetImportStatus.mockResolvedValueOnce({
      job_id: 'job-1',
      status: 'completed',
      progress: 1,
      current_step: 'finalize',
      project_id: 'project-1',
      result: {
        project_id: 'project-1',
        nodes_created: 12,
        edges_created: 34,
      },
      reliability_summary: {
        raw_entities_extracted: 100,
        entities_after_resolution: 40,
        merges_applied: 12,
        canonicalization_rate: 0.9,
        llm_pairs_reviewed: 4,
        llm_pairs_confirmed: 3,
        llm_confirmation_accept_rate: 0.75,
        potential_false_merge_count: 1,
        potential_false_merge_ratio: 0.025,
        potential_false_merge_samples: [],
        relationships_created: 22,
        evidence_backed_relationships: 18,
        provenance_coverage: 0.8,
        low_trust_edges: 5,
        low_trust_edge_ratio: 0.12,
      },
    });

    const { container } = render(<ImportProgress jobId="job-1" />);

    await waitFor(() => {
      expect(container.textContent).toContain('Import Complete!');
    });

    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches interrupted state snapshot with checkpoint details', async () => {
    mockGetImportStatus.mockResolvedValueOnce({
      job_id: 'job-1',
      status: 'interrupted',
      progress: 0.3,
      current_step: 'extract_entities',
      error: 'Import interrupted by server restart',
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

    const { container } = render(<ImportProgress jobId="job-1" />);

    await waitFor(() => {
      expect(container.textContent).toContain('Import Interrupted');
    });

    expect(container.firstChild).toMatchSnapshot();
  });
});
