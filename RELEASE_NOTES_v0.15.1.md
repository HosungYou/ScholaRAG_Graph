# Release Notes v0.15.1

> **Version**: 0.15.1 | **Date**: 2026-02-09
> **Track**: Infrastructure Maintenance
> **Previous**: v0.15.0

---

## Overview

Infrastructure maintenance release focused on resolving Supabase Free Plan quota exceedance (671 MB / 500 MB limit) and applying the pending Migration 021 for cross-paper entity linking. Also migrated the Render backend from Transaction Pooler to Session Pooler for improved prepared statement support.

---

## Infrastructure Changes

### INFRA-008: January Test Data Cleanup
- Deleted 26 test projects from January 2026 (Zotero Import 2026-01-19 ~ 2026-01-21)
- Removed ~1,043,953 rows across 9 tables in FK dependency order
- Preserved 4 active February 2026 projects

**Deleted data breakdown:**

| Table | Rows Deleted |
|-------|-------------|
| relationships | 995,787 |
| entities | 42,905 |
| semantic_chunks | 4,779 |
| paper_metadata | 375 |
| messages | 34 |
| projects | 26 |
| structural_gaps | 21 |
| conversations | 16 |
| concept_clusters | 10 |

### INFRA-009: VACUUM FULL Space Recovery
- Executed `VACUUM FULL` on 3 largest tables to reclaim dead tuple space
- **Database size: 671 MB → 181 MB (490 MB recovered, 73% reduction)**
- Back within Supabase Free Plan 500 MB limit

| Table | Before | After | Recovered |
|-------|--------|-------|-----------|
| relationships | 404 MB | 8.4 MB | 395.6 MB |
| semantic_chunks | 174 MB | 127 MB | 47 MB |
| entities | 65 MB | 31 MB | 34 MB |

### INFRA-010: Migration 021 Applied
- `SAME_AS` enum value added to `relationship_type` (18th value)
- `idx_entities_name_type` partial index created (Method, Dataset, Concept)
- `idx_relationships_same_as` partial index created (SAME_AS type)
- Required for v0.15.0 cross-paper entity linking feature

### INFRA-011: Database Connection Mode Change
- **Before**: Transaction Pooler (`aws-0-us-west-2.pooler.supabase.com:6543`)
- **After**: Session Pooler (`aws-0-us-west-2.pooler.supabase.com:5432`)
- **Reason**: Session Pooler supports prepared statements and DDL operations
- Render deployment auto-triggered

### INFRA-012: Supabase MCP Configuration
- Added `.mcp.json` to project root (`/Volumes/External SSD/Projects/`)
- Enables Supabase MCP tools for future database operations from any working directory

---

## Database Migrations

| Migration | Description | Status |
|-----------|-------------|--------|
| `021_cross_paper_links.sql` | SAME_AS relationship type + indexes | ✅ Applied |

---

## Technical Stats

| Metric | Value |
|--------|-------|
| Database rows deleted | ~1,043,953 |
| Disk space recovered | 490 MB |
| Final database size | 181 MB |
| Indexes created | 2 |
| Enum values added | 1 |
| Breaking changes | None |
| New env vars | None |
| Deployment triggered | 1 (Render auto-deploy) |

---

## Migration Guide

No application code changes required. This is an infrastructure-only release.

**For developers:**
- Database connection now uses Session Pooler (port 5432) instead of Transaction Pooler (port 6543)
- If connecting locally, update your `DATABASE_URL` to use port 5432

---

## Known Limitations

- `VACUUM FULL` warnings for system tables (pg_authid, pg_subscription, etc.) are normal on Supabase — these are restricted to superuser
- `semantic_chunks` HNSW index rebuild warning during VACUUM FULL — cosmetic only, index was rebuilt successfully
