# Release Notes — v0.13.0: Paper Citation Network

**Date**: 2026-02-07

## Overview

v0.13.0 adds an on-demand **Paper Citation Network** view. Users click "Build Citation Network" to fetch inter-paper citation data from Semantic Scholar, then explore a Litmaps-style scatter plot (X = publication year, Y = citation count on log scale).

## New Features

### Citation Network Builder (`backend/graph/citation_builder.py`)
- **On-demand construction**: No database persistence — in-memory cache with 1-hour TTL
- **2-phase build**: Phase 1 matches local papers via DOI on Semantic Scholar; Phase 2 fetches references for matched papers
- **Rate-limit safety**: 1 req/sec throttle with API key (`S2_API_KEY` env var)
- **Global build semaphore**: Only 1 concurrent build across all projects via `asyncio.Semaphore(1)`
- **DOI normalization**: Strips `https://doi.org/`, `doi:`, `DOI:` prefixes; lowercases
- **Large project guard**: `MAX_PAPERS_FOR_BUILD = 100` cap

### API Endpoints (`backend/routers/graph.py`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/graph/citation/{project_id}/build` | POST | Start background citation network build |
| `/api/graph/citation/{project_id}/status` | GET | Poll build progress (phase + progress/total) |
| `/api/graph/citation/{project_id}/network` | GET | Retrieve cached citation network |

All endpoints include `verify_project_access` for authentication.

### Citation View (`frontend/components/graph/CitationView.tsx`)
- **Litmaps-style D3.js scatter plot**: X = year, Y = citation count (log scale)
- **Visual encoding**: Teal circles = local papers, light blue = referenced papers
- **Interactive**: Hover tooltip (title, year, citations, DOI), click opens DOI/Semantic Scholar
- **2-phase progress bar**: Shows "Matching papers..." then "Fetching references..."
- **Build/Rebuild UI**: Empty state with build button, error state with retry

### Knowledge Graph Integration (`KnowledgeGraph3D.tsx`)
- New "Citations" tab with `GitBranch` icon in view mode toolbar
- Gap panel hidden in citations mode
- View mode badge hidden in citations mode

## Environment Variables

```env
S2_API_KEY=<your_semantic_scholar_api_key>
```

## Known Limitations

- **In-memory cache only**: Server restart clears cached networks — users must rebuild
- **DOI-only matching**: Papers without DOIs are skipped during Phase 1
- **Max 100 papers**: Large projects are capped at 100 papers for build
- **1 req/sec rate limit**: Builds for 100 papers take ~3-4 minutes (matching + references)
- **No edge directionality in scatter**: Citation edges shown as undirected lines

## View Mode Count

ScholaRAG_Graph now supports **4 view modes**: 3D, Topic, Gaps, Citations.
