/**
 * Core entity types for ScholaRAG Graph
 */

// Entity Types
export type EntityType = 'Paper' | 'Author' | 'Concept' | 'Method' | 'Finding';

// Relationship Types
export type RelationshipType =
  | 'AUTHORED_BY'
  | 'CITES'
  | 'DISCUSSES_CONCEPT'
  | 'USES_METHOD'
  | 'SUPPORTS'
  | 'CONTRADICTS'
  | 'RELATED_TO';

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
  paper_id: string;
  title: string;
  authors?: string[];
  year?: number;
  relevance_score?: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  highlighted_nodes: string[];
  highlighted_edges: string[];
  conversation_id: string;
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
