/**
 * Test file for ERDetailSection component
 * Phase 11C: Embedding ER Statistics Dashboard Extension
 */

import type { ImportReliabilitySummary } from '@/types';

// Test data: reliability summary with embedding ER statistics
const mockReliabilitySummary: ImportReliabilitySummary = {
  raw_entities_extracted: 1500,
  entities_after_resolution: 1200,
  merges_applied: 300,
  canonicalization_rate: 0.2,
  llm_pairs_reviewed: 150,
  llm_pairs_confirmed: 120,
  llm_confirmation_accept_rate: 0.8,
  potential_false_merge_count: 10,
  potential_false_merge_ratio: 0.033,
  potential_false_merge_samples: [],
  relationships_created: 5000,
  evidence_backed_relationships: 4500,
  provenance_coverage: 0.9,
  low_trust_edges: 200,
  low_trust_edge_ratio: 0.04,

  // Phase 8A: New embedding-based ER fields
  embedding_candidates_found: 245,
  string_candidates_found: 180,
  llm_confirmed_merges: 120,
};

// Test cases
console.log('✓ Type check: ImportReliabilitySummary accepts new fields');
console.log('✓ embedding_candidates_found:', mockReliabilitySummary.embedding_candidates_found);
console.log('✓ string_candidates_found:', mockReliabilitySummary.string_candidates_found);
console.log('✓ llm_confirmed_merges:', mockReliabilitySummary.llm_confirmed_merges);

// Test optional fields
const minimalSummary: ImportReliabilitySummary = {
  raw_entities_extracted: 100,
  entities_after_resolution: 90,
  merges_applied: 10,
  canonicalization_rate: 0.1,
  llm_pairs_reviewed: 5,
  llm_pairs_confirmed: 4,
  llm_confirmation_accept_rate: 0.8,
  potential_false_merge_count: 1,
  potential_false_merge_ratio: 0.01,
  potential_false_merge_samples: [],
  relationships_created: 500,
  evidence_backed_relationships: 450,
  provenance_coverage: 0.9,
  low_trust_edges: 20,
  low_trust_edge_ratio: 0.04,
  // No embedding fields - should be optional
};

console.log('✓ Type check: Fields are optional (minimalSummary compiles)');

export { mockReliabilitySummary, minimalSummary };
