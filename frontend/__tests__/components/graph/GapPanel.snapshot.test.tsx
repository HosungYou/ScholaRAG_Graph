export {};

import { fireEvent, render, waitFor } from '@testing-library/react';
import { GapPanel } from '@/components/graph/GapPanel';
import type { ConceptCluster, StructuralGap } from '@/types';

const mockGetGapRecommendations = jest.fn();

jest.mock('@/lib/api', () => ({
  api: {
    getGapRecommendations: (...args: unknown[]) => mockGetGapRecommendations(...args),
    generateBridgeHypotheses: jest.fn(),
    createBridge: jest.fn(),
  },
}));

jest.mock('@/components/ui/Toast', () => ({
  useToast: () => ({ showToast: jest.fn() }),
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
    bridge_candidates: ['bridge-1'],
    research_questions: ['How does trust influence fairness outcomes?'],
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

describe('GapPanel snapshots', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetGapRecommendations.mockResolvedValue({
      gap_id: 'gap-1',
      query_used: 'trust fairness bridge',
      papers: [],
    });
  });

  it('matches collapsed list view snapshot', () => {
    const { container } = render(
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

    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches expanded gap detail snapshot', async () => {
    const { container, getByRole } = render(
      <GapPanel
        projectId="project-1"
        gaps={gapsFixture}
        clusters={clustersFixture}
        nodes={[
          {
            id: 'bridge-1',
            entity_type: 'Concept',
            name: 'Calibration',
            properties: {},
          },
        ]}
        onGapSelect={jest.fn()}
        onHighlightNodes={jest.fn()}
        onClearHighlights={jest.fn()}
      />
    );

    fireEvent.click(getByRole('button', { name: /Trust Fairness 62%/i }));

    await waitFor(() => {
      expect(container.textContent).toContain('AI Research Questions');
    });

    expect(container.firstChild).toMatchSnapshot();
  });
});
