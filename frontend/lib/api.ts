/**
 * API client for ScholaRAG Graph backend
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
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
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
}

export const api = new ApiClient(API_URL);
