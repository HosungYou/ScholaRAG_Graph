/**
 * Core entity types for ScholaRAG Graph
 */

// Entity Types (Hybrid Mode: Paper/Author + Concept-Centric)
export type EntityType =
  | 'Paper'      // Hybrid Mode - 논문 노드
  | 'Author'     // Hybrid Mode - 저자 노드
  | 'Concept'    // Primary - 핵심 개념
  | 'Method'     // Primary - 연구 방법론
  | 'Finding'    // Primary - 연구 결과
  | 'Problem'    // Secondary - 연구 문제
  | 'Dataset'    // Secondary - 데이터셋
  | 'Metric'     // Secondary - 측정 지표
  | 'Innovation' // Secondary - 혁신/기여
  | 'Limitation'; // Secondary - 한계점

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

export interface ImportJob {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  current_step?: string;
  total_steps?: number;
  completed_steps?: number;
  error?: string;
  result?: {
    project_id: string;
    nodes_created: number;
    edges_created: number;
  };
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
