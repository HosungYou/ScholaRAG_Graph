/**
 * API client for ScholaRAG Graph backend
 *
 * Automatically includes Supabase access token in Authorization header
 * for authenticated API requests.
 */

import type {
  Project,
  GraphData,
  GraphEntity,
  GraphEdge,
  ChatResponse,
  ImportValidationResult,
  ImportJob,
  ImportResumeInfo,
  SearchResult,
  EntityType,
  GapAnalysisResult,
  StructuralGap,
  RelationshipEvidence,
} from '@/types';
import { getSession } from './supabase';

// API URL Configuration:
// 1. Use NEXT_PUBLIC_API_URL if explicitly set (recommended for production)
// 2. In production without env var: hardcode Render backend URL (avoids empty URL issues)
// 3. In development: use localhost:8000
// NOTE: Updated 2026-01-20 - Docker service (scholarag-graph-docker) replaced Python service
// FIX: 2026-01-20 - Force HTTPS to prevent Mixed Content errors in production
const getRawApiUrl = () => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
    return 'https://scholarag-graph-docker.onrender.com'; // Production: Render Docker backend
  }
  return 'http://localhost:8000'; // Development: direct to local backend
};

// Force HTTPS in production to prevent Mixed Content errors
// This handles cases where NEXT_PUBLIC_API_URL is accidentally set to HTTP
// BUG-016 Fix: Also enforce HTTPS during SSR (when window is undefined)
const enforceHttps = (url: string): string => {
  // Always force HTTPS for known production domains (works during SSR)
  // This is critical because window is undefined during Next.js SSR
  if (url.includes('onrender.com') || url.includes('vercel.app') || url.includes('render.com')) {
    return url.replace(/^http:\/\//, 'https://');
  }

  // Client-side: force HTTPS when page is loaded over HTTPS
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return url.replace(/^http:\/\//, 'https://');
  }

  return url;
};

export const API_URL = enforceHttps(getRawApiUrl());

// Debug logging for API configuration (only in browser)
if (typeof window !== 'undefined') {
  const rawUrl = getRawApiUrl();
  console.log('[API] Configuration:', {
    baseUrl: API_URL,
    rawUrl: rawUrl,
    httpsEnforced: rawUrl !== API_URL,
    hasEnvVar: !!process.env.NEXT_PUBLIC_API_URL,
    hostname: window.location.hostname,
    protocol: window.location.protocol,
  });
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Get authentication headers from Supabase session.
   * Returns Authorization header with Bearer token if session exists.
   */
  private async getAuthHeaders(): Promise<HeadersInit> {
    try {
      const session = await getSession();
      if (session?.access_token) {
        return {
          Authorization: `Bearer ${session.access_token}`,
        };
      }
    } catch (error) {
      console.warn('Failed to get auth session:', error);
    }
    return {};
  }

  /**
   * Make API request with automatic retry for transient errors (503).
   *
   * Render Starter plan has zero downtime (no cold starts), but may have
   * transient 503 errors due to DB connection pool exhaustion.
   * Fast retry with short delays handles these gracefully.
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retries: number = 3
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    // Get auth headers
    const authHeaders = await this.getAuthHeaders();

    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            ...authHeaders,
            ...options.headers,
          },
        });

        // Retry on 503 (Service Unavailable) - transient DB connection issues
        if (response.status === 503 && attempt < retries) {
          console.warn(`[API] 503 on ${endpoint}, retrying (${attempt}/${retries})...`);
          await this.delay(500 * attempt); // Fast backoff: 500ms, 1s, 1.5s
          continue;
        }

        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.detail || `API Error: ${response.status}`);
        }

        return response.json();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Retry on network errors or 503 (DB connection issues)
        if (attempt < retries && (
          lastError.message.includes('fetch') ||
          lastError.message.includes('network') ||
          lastError.message.includes('503') ||
          lastError.message.includes('Database temporarily')
        )) {
          console.warn(`[API] Error on ${endpoint}, retrying (${attempt}/${retries}):`, lastError.message);
          await this.delay(500 * attempt);
          continue;
        }

        throw lastError;
      }
    }

    throw lastError || new Error('Request failed after retries');
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Projects
  // IMPORTANT: Use trailing slash to avoid FastAPI redirect (causes Mixed Content on Render)
  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>('/api/projects/');
  }

  async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/api/projects/${id}`);
  }

  async createProject(data: { name: string; research_question?: string }): Promise<Project> {
    // IMPORTANT: Use trailing slash to avoid FastAPI redirect
    return this.request<Project>('/api/projects/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteProject(id: string): Promise<{ success: boolean }> {
    return this.request<{ success: boolean }>(`/api/projects/${id}`, {
      method: 'DELETE',
    });
  }

  // Graph
  async getNodes(
    projectId: string,
    params?: { entity_type?: EntityType; limit?: number }
  ): Promise<GraphEntity[]> {
    const searchParams = new URLSearchParams({ project_id: projectId });
    if (params?.entity_type) searchParams.set('entity_type', params.entity_type);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    return this.request<GraphEntity[]>(`/api/graph/nodes?${searchParams}`);
  }

  async getEdges(projectId: string) {
    return this.request<GraphData['edges']>(`/api/graph/edges?project_id=${projectId}`);
  }

  async getVisualizationData(projectId: string): Promise<GraphData> {
    return this.request<GraphData>(`/api/graph/visualization/${projectId}`);
  }

  async getSubgraph(nodeId: string, depth: number = 1): Promise<GraphData> {
    return this.request<GraphData>(`/api/graph/subgraph/${nodeId}?depth=${depth}`);
  }

  async searchNodes(query: string, entityTypes?: EntityType[]): Promise<SearchResult[]> {
    return this.request<SearchResult[]>('/api/graph/search', {
      method: 'POST',
      body: JSON.stringify({ query, entity_types: entityTypes }),
    });
  }

  // Chat
  async sendChatMessage(
    projectId: string,
    message: string,
    conversationId?: string
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/chat/query', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        message,
        conversation_id: conversationId,
      }),
    });
  }

  async getChatHistory(projectId: string) {
    return this.request<{ messages: ChatResponse[] }>(`/api/chat/history/${projectId}`);
  }

  async explainNode(nodeId: string, projectId: string): Promise<{ explanation: string }> {
    return this.request<{ explanation: string }>(
      `/api/chat/explain/${nodeId}?project_id=${projectId}`,
      {
        method: 'POST',
      }
    );
  }

  // Import
  async validateScholarag(folderPath: string): Promise<ImportValidationResult> {
    return this.request<ImportValidationResult>('/api/import/scholarag/validate', {
      method: 'POST',
      body: JSON.stringify({ folder_path: folderPath }),
    });
  }

  async importScholarag(
    folderPath: string,
    projectName?: string
  ): Promise<{ job_id: string }> {
    return this.request<{ job_id: string }>('/api/import/scholarag', {
      method: 'POST',
      body: JSON.stringify({
        folder_path: folderPath,
        project_name: projectName,
        extract_entities: true,
      }),
    });
  }

  async getImportStatus(jobId: string): Promise<ImportJob> {
    return this.request<ImportJob>(`/api/import/status/${jobId}`);
  }

  /**
   * Upload a single PDF file to create a Knowledge Graph.
   * Does not require a ScholaRAG project structure.
   */
  async uploadPDF(
    file: File,
    options?: {
      projectName?: string;
      researchQuestion?: string;
      extractConcepts?: boolean;
    }
  ): Promise<{ job_id: string; status: string; message: string; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);

    // Build URL with query parameters
    const params = new URLSearchParams();
    if (options?.projectName) params.set('project_name', options.projectName);
    if (options?.researchQuestion) params.set('research_question', options.researchQuestion);
    if (options?.extractConcepts !== undefined) {
      params.set('extract_concepts', String(options.extractConcepts));
    }

    const url = `${this.baseUrl}/api/import/pdf${params.toString() ? '?' + params.toString() : ''}`;

    // Get auth headers for file upload
    const authHeaders = await this.getAuthHeaders();

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: authHeaders,
      // Don't set Content-Type header - browser will set it with boundary for multipart
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Upload multiple PDF files to create a single Knowledge Graph project.
   */
  async uploadMultiplePDFs(
    files: File[],
    options?: {
      projectName?: string;
      researchQuestion?: string;
      extractConcepts?: boolean;
    }
  ): Promise<{ job_id: string; status: string; message: string; filename: string }> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    // Build URL with query parameters
    const params = new URLSearchParams();
    if (options?.projectName) params.set('project_name', options.projectName);
    if (options?.researchQuestion) params.set('research_question', options.researchQuestion);
    if (options?.extractConcepts !== undefined) {
      params.set('extract_concepts', String(options.extractConcepts));
    }

    const url = `${this.baseUrl}/api/import/pdf/multiple${params.toString() ? '?' + params.toString() : ''}`;

    // Get auth headers for file upload
    const authHeaders = await this.getAuthHeaders();

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: authHeaders,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Zotero Import
  /**
   * Validate Zotero export files before import.
   * Expects RDF file + optional PDF files.
   */
  async validateZotero(files: File[]): Promise<{
    valid: boolean;
    folder_path: string;
    rdf_file: string | null;
    items_count: number;
    pdfs_available: number;
    has_files_dir: boolean;
    errors: string[];
    warnings: string[];
  }> {
    const formData = new FormData();
    files.forEach((file) => {
      // Use webkitRelativePath if available (folder selection), otherwise use file.name
      const extendedFile = file as File & { webkitRelativePath?: string };
      const fileName = extendedFile.webkitRelativePath || file.name;
      formData.append('files', file, fileName);
    });

    const url = `${this.baseUrl}/api/import/zotero/validate`;

    // Get auth headers for file upload
    const authHeaders = await this.getAuthHeaders();

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: authHeaders,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Import Zotero RDF export with PDFs.
   * Upload files exported from Zotero with "Export Files" option.
   */
  async importZotero(
    files: File[],
    options?: {
      projectName?: string;
      researchQuestion?: string;
      extractConcepts?: boolean;
    }
  ): Promise<{
    job_id: string;
    status: string;
    message: string;
    items_count: number;
    project_id?: string;
  }> {
    const formData = new FormData();
    files.forEach((file) => {
      // Use webkitRelativePath if available (folder selection), otherwise use file.name
      const extendedFile = file as File & { webkitRelativePath?: string };
      const fileName = extendedFile.webkitRelativePath || file.name;
      formData.append('files', file, fileName);
    });

    // Build URL with query parameters
    const params = new URLSearchParams();
    if (options?.projectName) params.set('project_name', options.projectName);
    if (options?.researchQuestion) params.set('research_question', options.researchQuestion);
    if (options?.extractConcepts !== undefined) {
      params.set('extract_concepts', String(options.extractConcepts));
    }

    const url = `${this.baseUrl}/api/import/zotero${params.toString() ? '?' + params.toString() : ''}`;

    // Get auth headers for file upload
    const authHeaders = await this.getAuthHeaders();

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: authHeaders,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // ===========================================
  // BUG-028 Extension: Resume Interrupted Import
  // ===========================================

  /**
   * Get resume information for an interrupted import job.
   * Returns checkpoint details and whether the job can be resumed.
   */
  async getResumeInfo(jobId: string): Promise<ImportResumeInfo> {
    return this.request<ImportResumeInfo>(`/api/import/resume/${jobId}/info`);
  }

  /**
   * Resume an interrupted import job.
   * Note: For Zotero imports, files must be re-uploaded with the same checkpoint.
   */
  async resumeImport(jobId: string): Promise<ImportJob> {
    return this.request<ImportJob>(`/api/import/resume/${jobId}`, {
      method: 'POST',
    });
  }

  // Gap Detection
  async getGapAnalysis(projectId: string): Promise<GapAnalysisResult> {
    return this.request<GapAnalysisResult>(`/api/graph/gaps/${projectId}/analysis`);
  }

  async refreshGapAnalysis(projectId: string): Promise<GapAnalysisResult> {
    return this.request<GapAnalysisResult>(`/api/graph/gaps/${projectId}/refresh`, {
      method: 'POST',
    });
  }

  async getGapDetails(gapId: string): Promise<StructuralGap> {
    return this.request<StructuralGap>(`/api/graph/gaps/detail/${gapId}`);
  }

  async generateResearchQuestions(
    gapId: string,
    regenerate: boolean = false
  ): Promise<{ questions: string[] }> {
    return this.request<{ questions: string[] }>(
      `/api/graph/gaps/${gapId}/questions`,
      {
        method: 'POST',
        body: JSON.stringify({ regenerate }),
      }
    );
  }

  // Centrality Analysis
  async getCentrality(
    projectId: string,
    metric: 'betweenness' | 'degree' | 'eigenvector' = 'betweenness'
  ): Promise<{
    metric: string;
    centrality: Record<string, number>;
    top_bridges: Array<[string, number]>;
  }> {
    return this.request(`/api/graph/centrality/${projectId}?metric=${metric}`);
  }

  // Graph Metrics (Insight HUD)
  async getGraphMetrics(projectId: string): Promise<{
    modularity: number;
    diversity: number;
    density: number;
    avg_clustering: number;
    num_components: number;
    node_count: number;
    edge_count: number;
    cluster_count: number;
  }> {
    return this.request(`/api/graph/metrics/${projectId}`);
  }

  // Node Slicing
  async sliceGraph(
    projectId: string,
    removeTopN: number = 5,
    metric: 'betweenness' | 'degree' | 'eigenvector' = 'betweenness'
  ): Promise<{
    nodes: GraphEntity[];
    edges: GraphEdge[];
    removed_node_ids: string[];
    top_bridges: Array<{ id: string; name: string; score: number }>;
    original_count: number;
    filtered_count: number;
  }> {
    return this.request(`/api/graph/slice/${projectId}`, {
      method: 'POST',
      body: JSON.stringify({
        remove_top_n: removeTopN,
        metric,
      }),
    });
  }

  // K-means Clustering
  async recomputeClusters(
    projectId: string,
    clusterCount: number
  ): Promise<{
    clusters: Array<{
      cluster_id: number;
      concepts: string[];
      label: string;
      size: number;
      color: string;
    }>;
    optimal_k: number;
  }> {
    return this.request(`/api/graph/clusters/${projectId}`, {
      method: 'POST',
      body: JSON.stringify({ cluster_count: clusterCount }),
    });
  }

  // ============================================
  // Relationship Evidence (Contextual Edge Exploration)
  // ============================================

  /**
   * Fetch evidence chunks that support a specific relationship.
   * Used for contextual edge exploration - clicking an edge shows source text.
   */
  async fetchRelationshipEvidence(relationshipId: string): Promise<RelationshipEvidence> {
    return this.request<RelationshipEvidence>(
      `/api/graph/relationships/${relationshipId}/evidence`
    );
  }

  // ============================================
  // Temporal Graph (Graph Evolution)
  // ============================================

  /**
   * Fetch graph data filtered by year range for temporal visualization.
   */
  async getTemporalGraph(
    projectId: string,
    yearStart?: number,
    yearEnd?: number
  ): Promise<GraphData & { yearRange: { min: number; max: number } }> {
    const params = new URLSearchParams({ project_id: projectId });
    if (yearStart) params.set('year_start', yearStart.toString());
    if (yearEnd) params.set('year_end', yearEnd.toString());
    return this.request(`/api/graph/temporal?${params}`);
  }

  // ============================================
  // Bridge Hypothesis Generation
  // ============================================

  /**
   * Generate bridge hypotheses for a structural gap using AI.
   */
  async generateBridgeHypotheses(gapId: string): Promise<{
    hypotheses: Array<{
      title: string;
      description: string;
      methodology: string;
      connecting_concepts: string[];
      confidence: number;
    }>;
    bridge_type: 'theoretical' | 'methodological' | 'empirical';
    key_insight: string;
  }> {
    return this.request(`/api/graph/gaps/${gapId}/generate-bridge`, {
      method: 'POST',
    });
  }

  // ============================================
  // Diversity Analysis
  // ============================================

  /**
   * Get diversity metrics for a project's knowledge graph.
   */
  async getDiversityMetrics(projectId: string): Promise<{
    shannon_entropy: number;
    normalized_entropy: number;
    modularity: number;
    bias_score: number;
    diversity_rating: 'high' | 'medium' | 'low';
    cluster_sizes: number[];
    dominant_cluster_ratio: number;
    gini_coefficient: number;
  }> {
    return this.request(`/api/graph/diversity/${projectId}`);
  }

  // ============================================
  // Graph Comparison (Phase 5)
  // ============================================

  /**
   * Compare two project knowledge graphs.
   * Shows common entities, unique entities, and similarity metrics.
   */
  async compareGraphs(
    projectAId: string,
    projectBId: string
  ): Promise<{
    project_a_id: string;
    project_a_name: string;
    project_b_id: string;
    project_b_name: string;
    common_entities: number;
    unique_to_a: number;
    unique_to_b: number;
    common_entity_names: string[];
    jaccard_similarity: number;
    overlap_coefficient: number;
    nodes: Array<{
      id: string;
      name: string;
      entity_type: string;
      in_project_a: boolean;
      in_project_b: boolean;
      is_common: boolean;
    }>;
    edges: Array<{
      id: string;
      source: string;
      target: string;
      relationship_type: string;
      in_project_a: boolean;
      in_project_b: boolean;
      is_common: boolean;
    }>;
  }> {
    return this.request(`/api/graph/compare/${projectAId}/${projectBId}`);
  }
}

export const api = new ApiClient(API_URL);
