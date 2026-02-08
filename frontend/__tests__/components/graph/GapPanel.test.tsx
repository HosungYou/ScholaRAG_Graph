export {};

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { GapPanel } from '@/components/graph/GapPanel';
import type { ConceptCluster, StructuralGap } from '@/types';

const mockGetGapRecommendations = jest.fn();
const mockShowToast = jest.fn();

jest.mock('@/lib/api', () => ({
  api: {
    getGapRecommendations: (...args: unknown[]) => mockGetGapRecommendations(...args),
    generateBridgeHypotheses: jest.fn(),
    createBridge: jest.fn(),
  },
}));

jest.mock('@/components/ui/Toast', () => ({
  useToast: () => ({ showToast: mockShowToast }),
}));

const gapsFixture: StructuralGap[] = [
  {
    id: 'gap-1',
    cluster_a_id: 0,
    cluster_b_id: 1,
    cluster_a_concepts: ['c1'],
    cluster_b_concepts: ['c2'],
    cluster_a_names: ['Trust'],
    cluster_b_names: ['Fairness'],
    gap_strength: 0.62,
    bridge_candidates: [],
    research_questions: [],
  },
];

const clustersFixture: ConceptCluster[] = [
  {
    cluster_id: 0,
    concepts: ['c1'],
    concept_names: ['Trust'],
    size: 1,
    density: 0.4,
    label: 'Trust',
  },
  {
    cluster_id: 1,
    concepts: ['c2'],
    concept_names: ['Fairness'],
    size: 1,
    density: 0.5,
    label: 'Fairness',
  },
];

function renderGapPanel() {
  return render(
    <GapPanel
      projectId="project-1"
      gaps={gapsFixture}
      clusters={clustersFixture}
      nodes={[]}
      onGapSelect={jest.fn()}
      onHighlightNodes={jest.fn()}
      onClearHighlights={jest.fn()}
    />
  );
}

describe('GapPanel retry countdown', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.useRealTimers();
    consoleErrorSpy.mockRestore();
  });

  it('starts countdown on 429 and auto-retries recommendations when countdown reaches zero', async () => {
    const rateLimitError = Object.assign(new Error('Rate limited'), {
      status: 429,
      retryAfterSeconds: 3,
    });

    mockGetGapRecommendations
      .mockRejectedValueOnce(rateLimitError)
      .mockResolvedValueOnce({
        gap_id: 'gap-1',
        query_used: 'bridge trust fairness',
        papers: [
          {
            title: 'A paper',
            year: 2024,
            citation_count: 12,
            url: 'https://example.com/paper',
            abstract_snippet: 'snippet',
          },
        ],
      });

    renderGapPanel();

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Find related papers' }));
    });

    await waitFor(() => {
      expect(mockGetGapRecommendations).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(screen.getByText('Retry in 3s')).toBeInTheDocument();
    });

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(screen.getByText('Retry in 2s')).toBeInTheDocument();

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(screen.getByText('Retry in 1s')).toBeInTheDocument();

    await act(async () => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockGetGapRecommendations).toHaveBeenCalledTimes(2);
    });

    expect(mockShowToast).toHaveBeenCalledWith(
      'Semantic Scholar rate limited. Auto-retrying in 3s...',
      'error'
    );
    expect(mockShowToast).toHaveBeenCalledWith('Papers loaded successfully', 'success');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Find related papers' })).not.toBeDisabled();
    });
  });

  it('does not emit nested button DOM warnings on render', () => {
    renderGapPanel();

    const nestingWarnings = consoleErrorSpy.mock.calls.filter((call) =>
      String(call[0]).includes('validateDOMNesting')
    );
    expect(nestingWarnings).toHaveLength(0);
  });
});
