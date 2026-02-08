export {};

import React from 'react';
import { render } from '@testing-library/react';
import { Graph3D } from '@/components/graph/Graph3D';
import type { GraphEntity, GraphEdge, PotentialEdge, ConceptCluster, CentralityMetrics } from '@/types';

jest.mock('next/dynamic', () => {
  const React = require('react');

  return () => React.forwardRef((props: any, ref: React.Ref<unknown>) => {
    React.useImperativeHandle(ref, () => ({
      camera: () => ({ position: { length: () => 500 } }),
      cameraPosition: jest.fn(),
      graphData: () => props.graphData,
      scene: () => null,
      renderer: () => null,
    }));

    const data = props.graphData || { nodes: [], links: [] };

    const normalized = {
      nodes: data.nodes.map((node: any) => ({
        id: node.id,
        entityType: node.entityType,
        clusterId: node.clusterId,
        color: node.color,
        val: node.val,
      })),
      links: data.links.map((link: any) => ({
        id: link.id,
        source: typeof link.source === 'string' ? link.source : link.source?.id,
        target: typeof link.target === 'string' ? link.target : link.target?.id,
        relationshipType: link.relationshipType,
        isLowTrust: link.isLowTrust,
        isGhost: link.isGhost,
        weight: link.weight,
        confidence: link.confidence,
      })),
    };

    return (
      <pre data-testid="force-graph-mock">
        {JSON.stringify(normalized, null, 2)}
      </pre>
    );
  });
});

describe('Graph3D snapshots', () => {
  const nodesFixture: GraphEntity[] = [
    {
      id: 'n-1',
      entity_type: 'Concept',
      name: 'Transfer Learning',
      properties: { cluster_id: 0 },
    },
    {
      id: 'n-2',
      entity_type: 'Method',
      name: 'Fine-tuning',
      properties: { cluster_id: 1 },
    },
  ];

  const edgesFixture: GraphEdge[] = [
    {
      id: 'e-1',
      source: 'n-1',
      target: 'n-2',
      relationship_type: 'APPLIES_TO',
      weight: 0.52,
      properties: { confidence: 0.45 },
    },
  ];

  const clustersFixture: ConceptCluster[] = [
    {
      cluster_id: 0,
      concepts: ['n-1'],
      concept_names: ['Transfer Learning'],
      size: 1,
      density: 0.5,
      label: 'Transfer',
    },
    {
      cluster_id: 1,
      concepts: ['n-2'],
      concept_names: ['Fine-tuning'],
      size: 1,
      density: 0.6,
      label: 'Method',
    },
  ];

  const centralityFixture: CentralityMetrics[] = [
    {
      concept_id: 'n-1',
      concept_name: 'Transfer Learning',
      degree_centrality: 0.4,
      betweenness_centrality: 0.3,
      pagerank: 0.2,
      cluster_id: 0,
    },
    {
      concept_id: 'n-2',
      concept_name: 'Fine-tuning',
      degree_centrality: 0.6,
      betweenness_centrality: 0.5,
      pagerank: 0.4,
      cluster_id: 1,
    },
  ];

  it('matches canonical graph mapping snapshot with low-trust edge', () => {
    const { getByTestId } = render(
      <Graph3D
        nodes={nodesFixture}
        edges={edgesFixture}
        clusters={clustersFixture}
        centralityMetrics={centralityFixture}
        highlightedNodes={['n-1']}
        highlightedEdges={['e-1']}
      />
    );

    expect(getByTestId('force-graph-mock')).toMatchSnapshot();
  });

  it('matches ghost-edge enabled snapshot', () => {
    const potentialEdgesFixture: PotentialEdge[] = [
      {
        source_id: 'n-1',
        target_id: 'n-2',
        similarity: 0.81,
        gap_id: 'gap-1',
        source_name: 'Transfer Learning',
        target_name: 'Fine-tuning',
      },
    ];

    const { getByTestId } = render(
      <Graph3D
        nodes={nodesFixture}
        edges={edgesFixture}
        clusters={clustersFixture}
        centralityMetrics={centralityFixture}
        showGhostEdges
        potentialEdges={potentialEdgesFixture}
      />
    );

    expect(getByTestId('force-graph-mock')).toMatchSnapshot();
  });
});
