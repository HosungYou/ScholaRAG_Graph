/**
 * Core entity types for ScholaRAG Graph
 */

// Entity Types (Hybrid Mode: Paper/Author + Concept-Centric)
export type EntityType =
  | 'Paper'      // Hybrid Mode - Paper node
  | 'Author'     // Hybrid Mode - Author node
  | 'Concept'    // Primary - Core concept
  | 'Method'     // Primary - Research methodology
  | 'Finding'    // Primary - Research finding
  | 'Problem'    // Secondary - Research problem
  | 'Dataset'    // Secondary - Dataset
  | 'Metric'     // Secondary - Measurement metric
  | 'Innovation' // Secondary - Innovation/contribution
  | 'Limitation'; // Secondary - Limitation

// Relationship Types (Updated for Concept-Centric Design)
export type RelationshipType =
  | 'AUTHORED_BY'
  | 'CITES'
  | 'DISCUSSES_CONCEPT'
  | 'USES_METHOD'
  | 'SUPPORTS'
  | 'CONTRADICTS'
  | 'RELATED_TO'
  | 'CO_OCCURS_WITH'
  | 'PREREQUISITE_OF'
  | 'BRIDGES_GAP'
  | 'APPLIES_TO'
  | 'ADDRESSES';

// Property types
export interface PaperProperties {
  title?: string;
  abstract?: string;
  year?: number;
  doi?: string;
  arxiv_id?: string;
  authors?: string[];
  citation_count?: number;
  source?: string;
  pdf_path?: string;
  url?: string;
  [key: string]: unknown;
}

export interface AuthorProperties {
  affiliation?: string;
  orcid?: string;
  email?: string;
  paper_count?: number;
  [key: string]: unknown;
}

export interface ConceptProperties {
  description?: string;
  domain?: string;
  paper_count?: number;
  synonyms?: string[];
  [key: string]: unknown;
}

export interface MethodProperties {
  description?: string;
  type?: 'quantitative' | 'qualitative' | 'mixed';
  paper_count?: number;
  [key: string]: unknown;
}

export interface FindingProperties {
  statement?: string;
  effect_size?: string;
  significance?: string;
  confidence?: number;
  paper_count?: number;
  [key: string]: unknown;
}

// Base Entity interface
export interface GraphEntity {
  id: string;
  entity_type: EntityType;
  name: string;
  properties: PaperProperties | AuthorProperties | ConceptProperties | MethodProperties | FindingProperties;
  created_at?: string;
  updated_at?: string;
}

// Edge/Relationship
export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: RelationshipType;
  properties?: Record<string, unknown>;
  weight?: number;
}

// Graph Data
export interface GraphData {
  nodes: GraphEntity[];
  edges: GraphEdge[];
}

// Project
export interface Project {
  id: string;
  name: string;
  research_question?: string | null;
  description?: string | null;
  source_path?: string | null;
  created_at: string;
  updated_at?: string;
  stats?: ProjectStats;
}

export interface ProjectStats {
  total_nodes?: number;
  total_edges?: number;
  total_papers?: number;
  total_authors?: number;
  total_concepts?: number;
  total_methods?: number;
  total_findings?: number;
}

// Chat
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations?: Citation[];
  highlighted_nodes?: string[];
  highlighted_edges?: string[];
}

export interface Citation {
  id: string;
  label: string;
  entity_type?: string;
  // Extended fields (optional, for rich display)
  paper_id?: string;
  title?: string;
  authors?: string[];
  year?: number;
  relevance_score?: number;
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  intent?: string;
  citations: Citation[];
  highlighted_nodes: string[];
  highlighted_edges: string[];
  suggested_follow_ups?: string[];
  agent_trace?: Record<string, unknown>;
}

// Import
export interface ImportValidationResult {
  valid: boolean;
  folder_path: string;
  config_found: boolean;
  scholarag_metadata_found: boolean;
  papers_csv_found: boolean;
  papers_count: number;
  pdfs_count: number;
  chroma_db_found: boolean;
  errors: string[];
  warnings: string[];
}

// BUG-028 Extension: Checkpoint for resume support
export interface ImportCheckpoint {
  processed_paper_ids: string[];
  total_papers: number;
  last_processed_index: number;
  project_id?: string;
  stage?: string;
  updated_at?: string;
}

export interface ImportJob {
  job_id: string;
  // BUG-028: Added 'interrupted' status for jobs killed by server restart
  status:
    | 'pending'
    | 'running'
    | 'validating'
    | 'extracting'
    | 'processing'
    | 'building_graph'
    | 'completed'
    | 'failed'
    | 'interrupted';
  progress: number;
  current_step?: string;
  total_steps?: number;
  completed_steps?: number;
  message?: string;
  error?: string;
  project_id?: string;
  stats?: Record<string, unknown>;
  reliability_summary?: ImportReliabilitySummary;
  result?: {
    project_id?: string;
    nodes_created?: number;
    edges_created?: number;
    reliability_summary?: ImportReliabilitySummary;
    stats?: Record<string, unknown>;
  };
  // BUG-028 Extension: Checkpoint for resume support
  checkpoint?: ImportCheckpoint;
  // UI-002: Additional fields for job list display
  created_at?: string;
  updated_at?: string;
  metadata?: {
    project_name?: string;
    research_question?: string;
    checkpoint?: ImportCheckpoint;
    [key: string]: unknown;
  };
}

export interface ImportReliabilitySummary {
  raw_entities_extracted: number;
  entities_after_resolution: number;
  merges_applied: number;
  canonicalization_rate: number;
  llm_pairs_reviewed: number;
  llm_pairs_confirmed: number;
  llm_confirmation_accept_rate: number;
  potential_false_merge_count: number;
  potential_false_merge_ratio: number;
  potential_false_merge_samples: Array<{
    entity_type: string;
    context_bucket: string;
    left: string;
    right: string;
    similarity: number;
  }>;
  relationships_created: number;
  evidence_backed_relationships: number;
  provenance_coverage: number;
  low_trust_edges: number;
  low_trust_edge_ratio: number;
}

// BUG-028 Extension: Resume info response
export interface ImportResumeInfo {
  job_id: string;
  status: string;
  can_resume: boolean;
  checkpoint?: {
    processed_count: number;
    total_papers: number;
    last_processed_index: number;
    project_id?: string;
    stage?: string;
    updated_at?: string;
  };
  error?: string;
  message?: string;
}

// Search
export interface SearchResult {
  id: string;
  entity_type: EntityType;
  name: string;
  properties?: Record<string, unknown>;
  score?: number;
}

// React Flow types
export interface CustomNodeData {
  label: string;
  entityType: EntityType;
  properties?: Record<string, unknown>;
  isHighlighted?: boolean;
}

// Gap Detection Types (InfraNodus-style)
export interface ConceptCluster {
  cluster_id: number;
  concepts: string[];
  concept_names: string[];
  centroid?: number[];
  size: number;
  density: number;
  label?: string;
  color?: string;  // Cluster color for visualization
}

// Potential Edge for Ghost Edge visualization (InfraNodus-style)
export interface PotentialEdge {
  source_id: string;
  target_id: string;
  similarity: number;
  gap_id: string;
  source_name?: string;
  target_name?: string;
}

export interface StructuralGap {
  id: string;
  cluster_a_id: number;
  cluster_b_id: number;
  cluster_a_concepts: string[];
  cluster_b_concepts: string[];
  cluster_a_names: string[];
  cluster_b_names: string[];
  gap_strength: number;
  bridge_candidates: string[];
  research_questions: string[];
  potential_edges?: PotentialEdge[];  // Ghost edges for visualization
  created_at?: string;
}

export interface CentralityMetrics {
  concept_id: string;
  concept_name: string;
  degree_centrality: number;
  betweenness_centrality: number;
  pagerank: number;
  cluster_id?: number;
}

export interface GapAnalysisResult {
  clusters: ConceptCluster[];
  gaps: StructuralGap[];
  centrality_metrics: CentralityMetrics[];
  total_concepts: number;
  total_relationships: number;
}

export interface GapReproBridgeRelationship {
  relationship_id: string;
  source_name: string;
  target_name: string;
  confidence: number;
  hypothesis_title?: string | null;
  ai_generated: boolean;
}

export interface GapReproRecommendationTrace {
  status: 'success' | 'rate_limited' | 'timeout' | 'failed' | string;
  query_used: string;
  retry_after_seconds?: number | null;
  error?: string | null;
  papers: Array<{
    title: string;
    year: number | null;
    citation_count: number;
    url: string | null;
    abstract_snippet: string;
  }>;
}

export interface GapReproReport {
  project_id: string;
  gap_id: string;
  generated_at: string;
  gap_strength: number;
  cluster_a_names: string[];
  cluster_b_names: string[];
  bridge_candidates: string[];
  research_questions: string[];
  bridge_relationships: GapReproBridgeRelationship[];
  recommendation: GapReproRecommendationTrace;
}

// Extended Entity Type for Concept-Centric Design
export type ConceptCentricEntityType =
  | 'Concept'
  | 'Method'
  | 'Finding'
  | 'Problem'
  | 'Dataset'
  | 'Metric'
  | 'Innovation'
  | 'Limitation';

// Concept-Centric Node Properties
export interface ConceptCentricProperties {
  definition?: string;
  domain?: string;
  source_paper_ids?: string[];
  centrality_degree?: number;
  centrality_betweenness?: number;
  centrality_pagerank?: number;
  cluster_id?: number;
  is_gap_bridge?: boolean;
  paper_count?: number;
  confidence?: number;
  [key: string]: unknown;
}

// View Mode Types (InfraNodus-style visualization modes)
// - '3d': Full 3D force-directed graph
// - 'topic': 2D cluster block visualization
// - 'gaps': Gap-focused visualization with bridge highlighting
export type ViewMode = '3d' | 'topic' | 'gaps' | 'temporal';

// Gaps View Configuration
export interface GapsViewConfig {
  selectedGapId: string | null;
  showAllGaps: boolean;
  highlightBridges: boolean;
  dimInactiveNodes: boolean;
  inactiveOpacity: number;  // 0.15 - 0.25
  bridgeGlowIntensity: number;
}

export interface TopicNode {
  id: string;
  clusterId: number;
  label: string;
  size: number;           // Number of concepts in cluster
  color: string;          // Cluster color
  x?: number;             // Position (set by D3)
  y?: number;
  fx?: number | null;     // Fixed position
  fy?: number | null;
  conceptIds: string[];   // IDs of concepts in this cluster
  conceptNames: string[]; // Names of concepts
  density: number;        // Cluster density
}

export interface TopicLink {
  id: string;
  source: string | TopicNode;
  target: string | TopicNode;
  type: 'connection' | 'gap';  // Regular connection or structural gap
  weight: number;              // Connection strength or gap strength
  gapId?: string;              // If type is 'gap', reference to StructuralGap
  connectionCount?: number;    // Number of edges between clusters
}

export interface TopicViewData {
  nodes: TopicNode[];
  links: TopicLink[];
}

// ============================================
// Relationship Evidence Types (Contextual Edge Exploration)
// ============================================

export interface EvidenceChunk {
  evidence_id: string;
  chunk_id: string;
  text: string;
  section_type: string;
  paper_id?: string;
  paper_title?: string;
  paper_authors?: string;
  paper_year?: number;
  relevance_score: number;
  context_snippet?: string;
}

export interface RelationshipEvidence {
  relationship_id: string;
  source_name: string;
  target_name: string;
  relationship_type: string;
  evidence_chunks: EvidenceChunk[];
  total_evidence: number;
  error_code?: string | null;  // "table_missing", "permission_denied", "query_failed"
  ai_explanation?: string;  // v0.11.0: AI-generated explanation when no text evidence found
}

// ============================================
// Bridge Hypothesis Types (AI Bridge Generation)
// ============================================

export interface BridgeHypothesis {
  title: string;
  description: string;
  methodology: string;
  connecting_concepts: string[];
  confidence: number;
}

export interface BridgeGenerationResult {
  hypotheses: BridgeHypothesis[];
  bridge_type: 'theoretical' | 'methodological' | 'empirical';
  key_insight: string;
}

// ============================================
// Diversity Metrics Types
// ============================================

export interface DiversityMetrics {
  shannon_entropy: number;
  modularity: number;
  bias_score: number;
  diversity_rating: 'high' | 'medium' | 'low' | 'focused';  // v0.6.0: Added 'focused'
  cluster_sizes: number[];
}

// ============================================
// Temporal Graph Types
// ============================================

export interface TemporalGraphData extends GraphData {
  yearRange: {
    min: number;
    max: number;
  };
}
