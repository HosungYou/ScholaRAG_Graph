# ScholaRAG_Graph Test Suite Documentation
## Zotero Hybrid Import Testing Strategy

---

## Overview

This directory contains the comprehensive test suite for the ScholaRAG_Graph_Review project, with special focus on the new **Zotero Hybrid Import** feature. The test suite follows a three-tier architecture (Unit → Integration → E2E) and provides 80%+ code coverage.

---

## Quick Start

```bash
# Repository root 기준 표준 경로 (권장)
make verify-env
make test-backend-core

# backend 디렉터리에서 직접 실행 시
./venv/bin/pytest -q tests

# Coverage
./venv/bin/pytest --cov=importers --cov=integrations --cov-report=html

# Open coverage report
open htmlcov/index.html
```

---

## Documentation Files

| Document | Purpose | Audience |
|----------|---------|----------|
| **`DOCS/testing/TDD.md`** | Project-wide test design baseline (SDD-TDD traceability, quality gates) | Developers, reviewers |
| **ZOTERO_HYBRID_IMPORT_TEST_DESIGN.md** | Comprehensive test design with fixtures, unit/integration/e2e tests, CI/CD config | Developers implementing tests |
| **TEST_ARCHITECTURE_DIAGRAM.md** | Visual diagrams of test structure, flow, dependencies | All team members (overview) |
| **IMPLEMENTATION_GUIDE.md** | Step-by-step setup instructions, checklist, troubleshooting | Developers setting up tests |
| **README.md** (this file) | Quick reference and navigation | Everyone |

---

## Test Suite Structure

```
tests/
├── README.md                              # This file
├── ZOTERO_HYBRID_IMPORT_TEST_DESIGN.md   # Full test design (58KB)
├── TEST_ARCHITECTURE_DIAGRAM.md          # Visual diagrams (27KB)
├── IMPLEMENTATION_GUIDE.md               # Setup guide (12KB)
├── conftest.py                           # Global pytest fixtures
├── pytest.ini                            # Pytest configuration
│
├── fixtures/                             # Reusable test data
│   ├── __init__.py
│   ├── zotero_fixtures.py               # Mock Zotero data generators
│   └── pdf_fixtures.py                  # Mock PDF content
│
├── mocks/                                # Mock HTTP responses
│   ├── __init__.py
│   ├── mock_zotero_responses.py         # Zotero API mocks
│   └── mock_pdf_files.py                # PDF file mocks
│
├── unit/                                 # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_zotero_local_client.py      # ZoteroLocalClient tests
│   ├── test_hybrid_importer.py          # HybridZoteroImporter phases
│   └── test_merge_logic.py              # Merge algorithms
│
├── integration/                          # Integration tests (real services)
│   ├── __init__.py
│   ├── test_zotero_desktop_integration.py  # Real Zotero Desktop
│   ├── test_database_integration.py        # Real PostgreSQL + pgvector
│   └── test_end_to_end_pipeline.py         # Full pipeline
│
└── e2e/                                  # End-to-end tests (full API)
    ├── __init__.py
    ├── test_api_endpoints.py            # Zotero import API routes
    └── test_full_import_workflow.py     # Complete user workflow
```

---

## Existing Tests (Pre-Zotero)

| Test File | Coverage |
|-----------|----------|
| `test_gap_detector.py` | Gap detection algorithms |
| `test_integrations.py` | Semantic Scholar, OpenAlex, Zotero API clients |
| `test_auth.py` | Authentication/authorization |
| `test_entity_extractor.py` | Entity extraction with LLMs |
| `test_api_integration.py` | API endpoint contracts |
| `test_agents.py` | AGENTiGraph 6-agent pipeline |
| `test_api_contracts.py` | API schema validation |

---

## New Tests (Zotero Hybrid Import)

### Unit Tests (50+ tests, ~30 sec)

**test_zotero_local_client.py** - Tests Zotero Desktop API communication
- Connection tests (success, timeout, refused)
- Collection fetching
- Item retrieval and filtering
- PDF attachment handling

**test_hybrid_importer.py** - Tests each phase of hybrid import
- Phase 1: Zotero metadata fetch
- Phase 2: PDF extraction
- Phase 3: Data merging
- Phase 4: Entity extraction (LLM)
- Phase 5: Graph construction

**test_merge_logic.py** - Tests merge algorithms
- Title normalization and matching
- Abstract conflict resolution (prefer longer)
- Author name variations
- Merge strategies (prefer_zotero, prefer_pdf, smart_merge)

### Integration Tests (15 tests, ~2 min)

**test_zotero_desktop_integration.py** - Tests with real Zotero Desktop
- Real collection fetching
- Real PDF file access
- Full import workflow

**test_database_integration.py** - Tests with real PostgreSQL
- GraphStore CRUD operations
- Node/edge persistence
- Deduplication logic

**test_end_to_end_pipeline.py** - Tests complete pipeline
- Full pipeline with mocked data
- Error recovery scenarios

### E2E Tests (5 tests, ~5 min)

**test_api_endpoints.py** - Tests API routes
- `GET /api/import/zotero/status`
- `GET /api/import/zotero/collections`
- `POST /api/import/zotero/import`
- `GET /api/import/status/{job_id}`

**test_full_import_workflow.py** - Tests user workflows
- Complete import lifecycle
- Job status polling
- Concurrent imports

---

## Running Tests

### Local Development

```bash
# Fast unit tests only (run frequently)
pytest tests/unit/ -v

# Unit tests with coverage
pytest tests/unit/ --cov=importers --cov-report=term-missing

# Integration tests (requires services)
docker-compose up -d postgres
pytest tests/integration/ -v -m "not requires_zotero"
docker-compose down

# E2E tests (requires backend running)
uvicorn main:app --port 8000 &
pytest tests/e2e/ -v
pkill -f uvicorn

# Manual Zotero Desktop tests
# 1. Open Zotero Desktop
# 2. Enable "Allow other applications" in Preferences
pytest -m "requires_zotero" -v
```

### v0.10.2 Stability Regression (Recommended)

```bash
# 1) Syntax check for lifecycle/import stabilization changes
python3 -m py_compile backend/main.py backend/routers/import_.py

# 2) Importer regression tests
pytest -q backend/tests/test_importer.py

# 3) Frontend changed-file lint
cd frontend
npm run -s lint -- --file components/import/ImportProgress.tsx --file components/graph/StatusBar.tsx --file components/graph/Graph3D.tsx
```

### CI/CD (GitHub Actions)

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request

Pipeline stages:
1. **Unit Tests** (~30 sec) - Must pass to continue
2. **Integration Tests** (~2 min) - Must pass to continue
3. **E2E Tests** (~5 min) - Must pass to merge PR

---

## Test Markers

Use pytest markers to run specific test categories:

```bash
# Run only unit tests (fast)
pytest -m "unit" -v

# Run without Zotero Desktop
pytest -m "not requires_zotero" -v

# Run integration tests only
pytest -m "integration" -v

# Run E2E tests only
pytest -m "e2e" -v

# Skip slow tests
pytest -m "not slow" -v
```

Available markers:
- `unit` - Fast, isolated unit tests
- `integration` - Tests requiring real services
- `e2e` - Full workflow tests
- `slow` - Tests taking >30 seconds
- `requires_zotero` - Needs Zotero Desktop running
- `requires_pdf` - Needs PDF processing libraries
- `contract` - API contract validation

---

## Coverage Targets

| Module | Target | Current |
|--------|--------|---------|
| `integrations/zotero_local.py` | 85% | 🆕 NEW |
| `importers/hybrid_zotero_importer.py` | 90% | 🆕 NEW |
| Merge logic | 95% | 🆕 NEW |
| API routes (Zotero) | 80% | 🆕 NEW |
| **Overall** | **80%** | TBD |

Generate coverage report:
```bash
pytest --cov=importers --cov=integrations --cov-report=html
open htmlcov/index.html
```

---

## Key Fixtures

### Global Fixtures (conftest.py)

- `app` - FastAPI app instance
- `async_client` - AsyncClient for API testing
- `mock_db` - Mocked database connection
- `sample_project` - Sample project data
- `sample_node` - Sample graph node
- `sample_edge` - Sample graph edge

### Zotero Fixtures

- `sample_zotero_collection` - Mock collection data
- `sample_zotero_items` - Mock paper items (2 items)
- `sample_zotero_attachments` - Mock PDF attachments
- `large_zotero_collection` - 100+ items for performance testing
- `mock_zotero_local_client` - Mocked ZoteroLocalClient
- `temp_pdf_directory` - Temporary directory for test PDFs
- `sample_pdf_content` - Mock extracted PDF text
- `mock_graph_store` - Mocked GraphStore
- `mock_llm_provider` - Mocked LLM API
- `hybrid_import_config` - Import configuration
- `merge_test_scenarios` - Data merge test cases
- `phase_test_checkpoints` - Expected phase benchmarks

---

## Performance Benchmarks

| Operation | Target Duration | Max Papers |
|-----------|----------------|------------|
| Fetch 100 items | < 5 sec | 100 |
| Extract 50 PDFs | < 2 min | 50 |
| Merge 100 papers | < 10 sec | 100 |
| Extract entities (50) | < 2 min* | 50 |
| Build graph (100) | < 15 sec | 100 |
| **Full pipeline (100)** | **< 5 min** | **100** |

*With mocked LLM (real LLM takes ~10-15 min due to API rate limits)

---

## Troubleshooting

### Import Errors
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Async Test Failures
```bash
pip install pytest-asyncio
# Ensure pytest.ini has: asyncio_mode = auto
```

### Database Connection Fails
```bash
# Start PostgreSQL
brew services start postgresql

# Or Docker:
docker-compose up -d postgres

# Verify:
psql -h localhost -U test -d scholarag_test -c "SELECT 1;"
```

### Zotero Tests Skipped
This is expected if Zotero Desktop is not running.
To run these tests:
1. Open Zotero Desktop
2. Go to Edit → Preferences → Advanced
3. Enable "Allow other applications on this computer to communicate with Zotero"
4. Run: `pytest -m "requires_zotero" -v`

---

## Adding New Tests

### 1. Identify Test Type
- **Unit Test**: Tests single function/class in isolation
- **Integration Test**: Tests multiple components together
- **E2E Test**: Tests complete user workflow

### 2. Create Test File
```bash
# Unit test
touch tests/unit/test_my_feature.py

# Integration test
touch tests/integration/test_my_integration.py

# E2E test
touch tests/e2e/test_my_workflow.py
```

### 3. Follow Naming Conventions
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Fixtures: descriptive names (no `test_` prefix)

### 4. Use Existing Fixtures
```python
import pytest

@pytest.mark.asyncio
async def test_my_feature(async_client, mock_db, sample_project):
    # Your test code
    pass
```

### 5. Add Markers
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_fast_unit():
    pass

@pytest.mark.integration
@pytest.mark.requires_zotero
async def test_with_zotero():
    pass
```

---

## CI/CD Integration

### GitHub Actions Workflow

File: `.github/workflows/backend-tests.yml`

**Jobs:**
1. **unit-tests** - Runs unit tests on every commit
2. **integration-tests** - Runs after unit tests pass
3. **e2e-tests** - Runs after integration tests pass

**Services:**
- PostgreSQL (pgvector/pgvector:pg16)

**Artifacts:**
- Coverage report (uploaded to Codecov)
- Test results (JUnit XML)

### Branch Protection Rules

Recommended settings:
- ✅ Require status checks to pass
- ✅ Require branches to be up to date
- ✅ Unit Tests (required)
- ✅ Integration Tests (required)
- ✅ E2E Tests (required)

---

## Next Steps

1. **Implement Phase 1** (Environment Setup)
   - Install test dependencies
   - Update pytest.ini
   - Create directory structure

2. **Implement Phase 2** (Fixtures)
   - Extend conftest.py
   - Create zotero_fixtures.py
   - Create mock responses

3. **Implement Phase 3-4** (Unit Tests)
   - test_zotero_local_client.py
   - test_hybrid_importer.py
   - test_merge_logic.py

4. **Implement Phase 5** (Integration Tests)
   - test_zotero_desktop_integration.py
   - test_database_integration.py
   - test_end_to_end_pipeline.py

5. **Implement Phase 6** (E2E Tests)
   - test_api_endpoints.py
   - test_full_import_workflow.py

6. **Implement Phase 7** (CI/CD)
   - Create GitHub Actions workflow
   - Configure Codecov
   - Set branch protection rules

**Estimated Implementation Time:** 7 days (1 developer)

---

## Resources

- **Full Test Design**: [ZOTERO_HYBRID_IMPORT_TEST_DESIGN.md](./ZOTERO_HYBRID_IMPORT_TEST_DESIGN.md)
- **Architecture Diagrams**: [TEST_ARCHITECTURE_DIAGRAM.md](./TEST_ARCHITECTURE_DIAGRAM.md)
- **Implementation Guide**: [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
- **pytest Documentation**: https://docs.pytest.org
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io
- **Coverage.py**: https://coverage.readthedocs.io

---

## Contact

For questions or support:
- Review existing test patterns in `tests/test_integrations.py`
- Check pytest documentation for specific features
- Consult the implementation guide for setup issues

**Last Updated:** January 15, 2026
**Version:** 1.0.0
**Status:** ✅ Design Complete, 🚧 Implementation Pending
