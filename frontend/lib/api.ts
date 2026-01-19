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
  ChatResponse,
  ImportValidationResult,
  ImportJob,
  SearchResult,
  EntityType,
  GapAnalysisResult,
  StructuralGap,
} from '@/types';
import { getSession } from './supabase';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    // Get auth headers
    const authHeaders = await this.getAuthHeaders();

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Projects
  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>('/api/projects');
  }

  async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/api/projects/${id}`);
  }

  async createProject(data: { name: string; research_question?: string }): Promise<Project> {
    return this.request<Project>('/api/projects', {
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
}

export const api = new ApiClient(API_URL);
