/**
 * Tests for useGraphStore - gap analysis auto-refresh logic
 * v0.10.0: Verifies v0.9.0 auto-refresh when no gaps but clusters exist
 */

// Mock the API module before importing the store
const mockGetGapAnalysis = jest.fn();
const mockRefreshGapAnalysis = jest.fn();

jest.mock('@/lib/api', () => ({
  __esModule: true,
  api: {
    getGapAnalysis: (...args: unknown[]) => mockGetGapAnalysis(...args),
    refreshGapAnalysis: (...args: unknown[]) => mockRefreshGapAnalysis(...args),
  },
  default: {
    getGapAnalysis: (...args: unknown[]) => mockGetGapAnalysis(...args),
    refreshGapAnalysis: (...args: unknown[]) => mockRefreshGapAnalysis(...args),
  },
}));

describe('useGraphStore - Gap Analysis', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchGapAnalysis auto-refresh', () => {
    it('should not refresh when gaps exist', async () => {
      const analysisWithGaps = {
        clusters: [{ cluster_id: 0 }, { cluster_id: 1 }],
        gaps: [{ id: 'gap-1', cluster_a_id: 0, cluster_b_id: 1 }],
        centrality_metrics: [],
      };
      mockGetGapAnalysis.mockResolvedValue(analysisWithGaps);

      // Import store dynamically to get fresh instance
      const { useGraphStore } = await import('@/hooks/useGraphStore');
      const store = useGraphStore.getState();
      await store.fetchGapAnalysis('test-project-id');

      expect(mockGetGapAnalysis).toHaveBeenCalledWith('test-project-id');
      expect(mockRefreshGapAnalysis).not.toHaveBeenCalled();
    });

    it('should auto-refresh when no gaps but multiple clusters exist', async () => {
      // First call: no gaps but clusters exist
      const analysisNoGaps = {
        clusters: [{ cluster_id: 0 }, { cluster_id: 1 }, { cluster_id: 2 }],
        gaps: [],
        centrality_metrics: [],
      };
      // Refresh returns gaps
      const analysisRefreshed = {
        clusters: [{ cluster_id: 0 }, { cluster_id: 1 }, { cluster_id: 2 }],
        gaps: [{ id: 'gap-1', cluster_a_id: 0, cluster_b_id: 1 }],
        centrality_metrics: [{ concept_id: 'c1', betweenness_centrality: 0.5 }],
      };
      mockGetGapAnalysis.mockResolvedValue(analysisNoGaps);
      mockRefreshGapAnalysis.mockResolvedValue(analysisRefreshed);

      const { useGraphStore } = await import('@/hooks/useGraphStore');
      const store = useGraphStore.getState();
      await store.fetchGapAnalysis('test-project-id');

      // Should trigger refresh because gaps=0 && clusters>1
      expect(mockRefreshGapAnalysis).toHaveBeenCalledWith('test-project-id');
    });

    it('should not refresh when only one cluster exists', async () => {
      const analysisSingleCluster = {
        clusters: [{ cluster_id: 0 }],
        gaps: [],
        centrality_metrics: [],
      };
      mockGetGapAnalysis.mockResolvedValue(analysisSingleCluster);

      const { useGraphStore } = await import('@/hooks/useGraphStore');
      const store = useGraphStore.getState();
      await store.fetchGapAnalysis('test-project-id');

      // Single cluster: no refresh needed
      expect(mockRefreshGapAnalysis).not.toHaveBeenCalled();
    });

    it('should handle refresh failure gracefully', async () => {
      const analysisNoGaps = {
        clusters: [{ cluster_id: 0 }, { cluster_id: 1 }],
        gaps: [],
        centrality_metrics: [],
      };
      mockGetGapAnalysis.mockResolvedValue(analysisNoGaps);
      mockRefreshGapAnalysis.mockRejectedValue(new Error('Network error'));

      const { useGraphStore } = await import('@/hooks/useGraphStore');
      const store = useGraphStore.getState();

      // Should not throw even if refresh fails
      await expect(store.fetchGapAnalysis('test-project-id')).resolves.not.toThrow();
    });
  });
});

describe('useGraphStore - View Mode Recommendation', () => {
  it('should recommend gaps mode for gap intent', async () => {
    const { useGraphStore } = await import('@/hooks/useGraphStore');
    const store = useGraphStore.getState();
    expect(store.getRecommendedViewMode('analyze_gaps')).toBe('gaps');
  });

  it('should apply temporal mode for timeline intent', async () => {
    const { useGraphStore } = await import('@/hooks/useGraphStore');
    const store = useGraphStore.getState();

    store.applyRecommendedViewMode('timeline');
    expect(useGraphStore.getState().viewMode).toBe('temporal');
  });

  it('should fallback to 3d for unknown intent', async () => {
    const { useGraphStore } = await import('@/hooks/useGraphStore');
    const store = useGraphStore.getState();
    expect(store.getRecommendedViewMode('unclassified_intent')).toBe('3d');
  });
});
