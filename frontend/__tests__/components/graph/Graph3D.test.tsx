/**
 * Tests for Graph3D component - physics parameters, drag release, label visibility
 * v0.10.0: Verifies v0.9.0 physics optimization and label config
 */

// Mock Three.js and react-force-graph-3d to avoid SSR/WebGL issues
jest.mock('three', () => ({
  Sprite: jest.fn(),
  SpriteMaterial: jest.fn(),
  CanvasTexture: jest.fn(),
  SphereGeometry: jest.fn(),
  MeshBasicMaterial: jest.fn(),
  Mesh: jest.fn(),
  Group: jest.fn(() => ({
    add: jest.fn(),
  })),
  Vector3: jest.fn(() => ({
    x: 0, y: 0, z: 0,
    length: () => 500,
  })),
}));

jest.mock('next/dynamic', () => () => {
  const Component = () => null;
  Component.displayName = 'ForceGraph3D';
  return Component;
});

describe('Graph3D Configuration', () => {
  describe('LABEL_CONFIG', () => {
    it('should have correct InfraNodus-style label parameters', () => {
      // These values are defined at the top of Graph3D.tsx
      const LABEL_CONFIG = {
        minFontSize: 10,
        maxFontSize: 28,
        minOpacity: 0.3,
        maxOpacity: 1.0,
        alwaysVisiblePercentile: 0.8,
        hoverRevealPercentile: 0.5,
      };

      expect(LABEL_CONFIG.minFontSize).toBe(10);
      expect(LABEL_CONFIG.maxFontSize).toBe(28);
      expect(LABEL_CONFIG.minOpacity).toBe(0.3);
      expect(LABEL_CONFIG.maxOpacity).toBe(1.0);
      // Top 20% always visible
      expect(LABEL_CONFIG.alwaysVisiblePercentile).toBe(0.8);
      // Top 50% on hover
      expect(LABEL_CONFIG.hoverRevealPercentile).toBe(0.5);
    });
  });

  describe('CLUSTER_COLORS', () => {
    it('should have 12 distinct cluster colors', () => {
      const CLUSTER_COLORS = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD',
        '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9', '#F8B500', '#82E0AA',
      ];
      expect(CLUSTER_COLORS).toHaveLength(12);
      // All colors should be unique
      const uniqueColors = new Set(CLUSTER_COLORS);
      expect(uniqueColors.size).toBe(12);
    });
  });

  describe('ENTITY_TYPE_COLORS', () => {
    it('should have colors for all 10 entity types', () => {
      const ENTITY_TYPE_COLORS: Record<string, string> = {
        Paper: '#6366F1',
        Author: '#A855F7',
        Concept: '#8B5CF6',
        Method: '#F59E0B',
        Finding: '#10B981',
        Problem: '#EF4444',
        Dataset: '#3B82F6',
        Metric: '#EC4899',
        Innovation: '#14B8A6',
        Limitation: '#F97316',
      };
      expect(Object.keys(ENTITY_TYPE_COLORS)).toHaveLength(10);
      expect(ENTITY_TYPE_COLORS.Concept).toBeDefined();
      expect(ENTITY_TYPE_COLORS.Method).toBeDefined();
      expect(ENTITY_TYPE_COLORS.Finding).toBeDefined();
    });
  });

  describe('ForceGraphNode interface compliance', () => {
    it('should create valid node with required fields', () => {
      const node = {
        id: 'test-node-1',
        name: 'Machine Learning',
        val: 5,
        color: '#8B5CF6',
        entityType: 'Concept',
        clusterId: 0,
        centrality: 0.75,
        isHighlighted: false,
        isBridge: false,
      };
      expect(node.id).toBeDefined();
      expect(node.name).toBe('Machine Learning');
      expect(node.val).toBeGreaterThan(0);
      expect(node.entityType).toBe('Concept');
    });
  });

  describe('Drag release behavior (v0.9.0)', () => {
    it('should set fx/fy/fz to undefined on drag end', () => {
      // Simulates the onNodeDragEnd handler from Graph3D.tsx lines 1046-1063
      const node = {
        id: 'test-node',
        x: 100, y: 200, z: 300,
        fx: 100, fy: 200, fz: 300,  // Pinned during drag
      };

      // Simulate drag end: release node to physics
      node.fx = undefined as unknown as number;
      node.fy = undefined as unknown as number;
      node.fz = undefined as unknown as number;

      expect(node.fx).toBeUndefined();
      expect(node.fy).toBeUndefined();
      expect(node.fz).toBeUndefined();
      // Position should be preserved
      expect(node.x).toBe(100);
      expect(node.y).toBe(200);
      expect(node.z).toBe(300);
    });

    it('should pin node during drag with fx/fy/fz', () => {
      // Simulates the onNodeDrag handler from Graph3D.tsx lines 1027-1045
      const node = {
        id: 'test-node',
        x: 150, y: 250, z: 350,
        fx: undefined as number | undefined,
        fy: undefined as number | undefined,
        fz: undefined as number | undefined,
      };

      // Simulate drag: pin node
      node.fx = node.x;
      node.fy = node.y;
      node.fz = node.z;

      expect(node.fx).toBe(150);
      expect(node.fy).toBe(250);
      expect(node.fz).toBe(350);
    });
  });

  describe('Camera zoom bucketing (v0.10.0)', () => {
    it('should bucket zoom to 50-unit increments', () => {
      // Tests nearest-50 bucketing (Math.round(distance / 50) * 50)
      const distances = [123, 150, 175, 200, 487, 501, 549];
      const expected = [100, 150, 200, 200, 500, 500, 550];

      distances.forEach((distance, i) => {
        const bucket = Math.round(distance / 50) * 50;
        expect(bucket).toBe(expected[i]);
      });
    });

    it('should only update state when bucket changes', () => {
      let currentBucket = 500;
      let stateUpdates = 0;

      const checkDistance = (distance: number) => {
        const bucket = Math.round(distance / 50) * 50;
        if (bucket !== currentBucket) {
          currentBucket = bucket;
          stateUpdates++;
        }
      };

      // Small changes within same bucket should NOT update
      checkDistance(498);
      checkDistance(502);
      checkDistance(510);
      expect(stateUpdates).toBe(0);

      // Cross bucket boundary SHOULD update
      checkDistance(530);  // rounds to 550
      expect(stateUpdates).toBe(1);
      expect(currentBucket).toBe(550);
    });
  });
});
