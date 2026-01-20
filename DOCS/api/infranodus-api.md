# InfraNodus API Documentation

> **Version**: 0.4.0
> **Added**: 2026-01-20 (InfraNodus Integration)

This document describes the new API endpoints added for InfraNodus-style knowledge graph analysis features.

---

## Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph/relationships/{id}/evidence` | GET | Get evidence for a relationship |
| `/api/graph/temporal/{project_id}` | GET | Get temporal graph data |
| `/api/graph/temporal/{project_id}/migrate` | POST | Trigger temporal data migration |
| `/api/graph/gaps/{id}/generate-bridge` | POST | Generate AI bridge hypotheses |
| `/api/graph/diversity/{project_id}` | GET | Get diversity metrics |
| `/api/graph/compare/{project_a}/{project_b}` | GET | Compare two projects |

---

## Endpoints

### 1. Relationship Evidence

**GET** `/api/graph/relationships/{relationship_id}/evidence`

Get evidence chunks that support a specific relationship in the knowledge graph.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `relationship_id` | UUID | The relationship ID |

#### Response (200 OK)

```json
{
  "relationship_id": "uuid",
  "evidence": [
    {
      "evidence_id": "uuid",
      "chunk_id": "uuid",
      "chunk_text": "Full text of the evidence chunk...",
      "section_type": "methodology",
      "paper_id": "uuid",
      "paper_title": "Paper Title",
      "paper_authors": "Author A, Author B",
      "paper_year": 2024,
      "relevance_score": 0.85,
      "context_snippet": "...short context excerpt..."
    }
  ],
  "total_evidence": 3
}
```

#### Errors

| Status | Description |
|--------|-------------|
| 401 | Unauthorized - Missing or invalid auth token |
| 404 | Relationship not found |

---

### 2. Temporal Graph Data

**GET** `/api/graph/temporal/{project_id}`

Get temporal statistics and year-filtered graph data for visualization.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | UUID | The project ID |

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `year` | int | null | Filter entities visible by this year |

#### Response (200 OK)

```json
{
  "project_id": "uuid",
  "temporal_stats": {
    "min_year": 2015,
    "max_year": 2024,
    "year_count": 10,
    "entities_with_year": 150,
    "total_entities": 200
  },
  "nodes_by_year": {
    "2015": 5,
    "2016": 12,
    "2017": 18,
    "...": "..."
  }
}
```

---

### 3. Temporal Data Migration

**POST** `/api/graph/temporal/{project_id}/migrate`

Trigger backfill of temporal data from paper metadata to entities.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | UUID | The project ID |

#### Response (202 Accepted)

```json
{
  "message": "Temporal data migration started",
  "entities_updated": 45,
  "relationships_updated": 120
}
```

---

### 4. Generate Bridge Hypotheses

**POST** `/api/graph/gaps/{gap_id}/generate-bridge`

Generate AI-powered bridge hypotheses for a structural gap.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `gap_id` | UUID | The structural gap ID |

#### Request Body (Optional)

```json
{
  "context": "Additional context for hypothesis generation",
  "max_hypotheses": 3
}
```

#### Response (200 OK)

```json
{
  "gap_id": "uuid",
  "hypotheses": [
    {
      "id": "uuid",
      "hypothesis": "Concept A may relate to Concept B through mechanism X because...",
      "confidence": 0.75,
      "reasoning": "Based on overlapping methodologies in papers P1 and P2...",
      "supporting_papers": [
        {
          "paper_id": "uuid",
          "title": "Paper Title",
          "relevance": 0.82
        }
      ],
      "suggested_search_queries": [
        "\"concept A\" AND \"concept B\" AND mechanism",
        "concept A relationship concept B"
      ]
    }
  ],
  "generated_at": "2026-01-20T12:00:00Z"
}
```

---

### 5. Diversity Metrics

**GET** `/api/graph/diversity/{project_id}`

Get diversity analysis metrics for a project's knowledge graph.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | UUID | The project ID |

#### Response (200 OK)

```json
{
  "project_id": "uuid",
  "diversity_metrics": {
    "shannon_entropy": 2.45,
    "normalized_entropy": 0.78,
    "gini_coefficient": 0.35,
    "diversity_rating": "Good"
  },
  "cluster_distribution": {
    "cluster_count": 5,
    "largest_cluster_size": 45,
    "smallest_cluster_size": 8,
    "sizes": [45, 32, 28, 15, 8]
  },
  "entity_type_distribution": {
    "Concept": 85,
    "Method": 45,
    "Finding": 32,
    "Problem": 12
  },
  "bias_analysis": {
    "bias_score": 0.15,
    "dominant_type": "Concept",
    "recommendations": [
      "Consider adding more Method entities for balance",
      "Problem entities are underrepresented"
    ]
  }
}
```

#### Diversity Rating Scale

| Rating | Shannon Entropy | Gini Coefficient |
|--------|-----------------|------------------|
| Excellent | > 3.0 | < 0.2 |
| Good | 2.0 - 3.0 | 0.2 - 0.4 |
| Fair | 1.0 - 2.0 | 0.4 - 0.6 |
| Poor | < 1.0 | > 0.6 |

---

### 6. Project Comparison

**GET** `/api/graph/compare/{project_a}/{project_b}`

Compare two projects' knowledge graphs using similarity metrics.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_a` | UUID | First project ID |
| `project_b` | UUID | Second project ID |

#### Response (200 OK)

```json
{
  "project_a": {
    "id": "uuid",
    "name": "Project A",
    "entity_count": 150,
    "relationship_count": 320
  },
  "project_b": {
    "id": "uuid",
    "name": "Project B",
    "entity_count": 180,
    "relationship_count": 290
  },
  "comparison": {
    "jaccard_similarity": 0.42,
    "overlap_coefficient": 0.65,
    "cosine_similarity": 0.58
  },
  "overlap": {
    "shared_entities": 63,
    "shared_entity_names": ["AI", "Machine Learning", "Education", "..."],
    "unique_to_a": 87,
    "unique_to_b": 117
  },
  "venn_data": {
    "a_only": ["Reinforcement Learning", "Neural Networks"],
    "b_only": ["Natural Language Processing", "Transformers"],
    "intersection": ["Machine Learning", "Deep Learning", "AI"]
  }
}
```

#### Similarity Metrics

| Metric | Formula | Range |
|--------|---------|-------|
| Jaccard Similarity | \|A ∩ B\| / \|A ∪ B\| | 0-1 |
| Overlap Coefficient | \|A ∩ B\| / min(\|A\|, \|B\|) | 0-1 |
| Cosine Similarity | Embedding vector similarity | 0-1 |

---

## Authentication

All endpoints require authentication via Bearer token:

```
Authorization: Bearer <supabase_access_token>
```

---

## Rate Limits

| Endpoint | Rate Limit |
|----------|------------|
| Evidence endpoints | 60/min |
| Generation endpoints | 10/min |
| Other endpoints | 30/min |

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid auth token |
| `FORBIDDEN` | 403 | No access to requested resource |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request parameters |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Usage Examples

### cURL

```bash
# Get relationship evidence
curl -X GET "https://scholarag-graph-docker.onrender.com/api/graph/relationships/{id}/evidence" \
  -H "Authorization: Bearer $TOKEN"

# Get diversity metrics
curl -X GET "https://scholarag-graph-docker.onrender.com/api/graph/diversity/{project_id}" \
  -H "Authorization: Bearer $TOKEN"

# Generate bridge hypotheses
curl -X POST "https://scholarag-graph-docker.onrender.com/api/graph/gaps/{gap_id}/generate-bridge" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"context": "Focus on educational technology"}'
```

### TypeScript

```typescript
import { api } from '@/lib/api';

// Get temporal data
const temporalData = await api.getTemporalGraph(projectId);

// Compare projects
const comparison = await api.compareProjects(projectA, projectB);

// Generate bridge hypotheses
const bridges = await api.generateBridgeHypotheses(gapId, {
  context: 'Educational technology focus',
  max_hypotheses: 3
});
```
