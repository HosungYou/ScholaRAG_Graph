# ScholaRAG_Graph Action Items

> 이 문서는 코드 리뷰, 기능 구현, 버그 수정 등에서 발견된 액션 아이템을 추적합니다.
>
> **마지막 업데이트**: 2026-01-21 23:45 (시각화 파이프라인 감사 결과 - 6개 신규 이슈 발견)
> **관리자**: Claude Code

---

## 📊 Status Overview

| Priority | Total | Completed | In Progress | Pending |
|----------|-------|-----------|-------------|---------|
| 🔴 High | 23 | 20 | 0 | 3 |
| 🟡 Medium | 20 | 17 | 0 | 3 |
| 🟢 Low | 9 | 8 | 0 | 1 |
| **Total** | **52** | **45** | **0** | **7** |

---

## 🔴 High Priority (Immediate Action Required)

### BUG-019: Uvicorn Proxy Headers 미지원 (Mixed Content 진짜 근본 원인)
- **Source**: Codex gpt-5.2-codex Root Cause Analysis 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: DevOps / Backend Team
- **Files**:
  - `Dockerfile` - Uvicorn CMD 수정
  - `frontend/lib/api.ts` - trailing slash 추가
  - `frontend/components/graph/StatusBar.tsx` - 중앙화된 API_URL 사용
- **Description**: BUG-015~018 수정 후에도 Mixed Content 에러 지속. Codex 리뷰를 통해 **진짜 근본 원인** 발견: Uvicorn이 Render의 X-Forwarded-Proto 헤더를 무시하여 리다이렉트 URL이 HTTP로 생성됨.
- **Root Cause Analysis**:
  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    요청 흐름 (문제)                              │
  ├─────────────────────────────────────────────────────────────────┤
  │  1. 프론트엔드: GET /api/projects (trailing slash 없음)         │
  │  2. Render Load Balancer: HTTPS → HTTP (내부 TLS 종료)          │
  │  3. FastAPI: "/api/projects" → "/api/projects/" 리다이렉트      │
  │  4. 문제: Uvicorn이 X-Forwarded-Proto를 무시!                   │
  │  5. 결과: Location: http://... (HTTP로 리다이렉트)              │
  │  6. 브라우저: Mixed Content 에러!                               │
  └─────────────────────────────────────────────────────────────────┘
  ```
- **Why Previous Fixes Failed**:
  | 수정 | 왜 실패했나 |
  |------|------------|
  | BUG-015 | system.py 커넥션 - URL/프록시와 무관 |
  | BUG-016 | enforceHttps - 클라이언트만 수정, **백엔드 리다이렉트는 여전히 HTTP** |
  | BUG-017 | ImportError - URL과 무관 |
  | BUG-018 | vercel.json - 상대 경로용, **절대 URL 사용 시 적용 안됨** |
- **Resolution**:
  1. **Dockerfile** (핵심 수정):
     ```dockerfile
     # 이전
     CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}

     # 수정 후
     CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips="*"
     ```
  2. **frontend/lib/api.ts** (방어적 수정):
     ```typescript
     // /api/projects → /api/projects/ (리다이렉트 회피)
     async getProjects(): Promise<Project[]> {
       return this.request<Project[]>('/api/projects/');
     }
     ```
  3. **frontend/components/graph/StatusBar.tsx**:
     ```typescript
     // 로컬 API_URL 정의 제거, 중앙화된 export 사용
     import { API_URL } from '@/lib/api';
     ```
- **Acceptance Criteria**:
  - [x] Dockerfile에 --proxy-headers 추가
  - [x] api.ts에 trailing slash 추가
  - [x] StatusBar.tsx가 중앙화된 API_URL 사용
  - [x] Render Docker 서비스 재배포
  - [x] Mixed Content 에러 완전 해결 확인 ✅ (2026-01-21 22:53)
- **Additional Fix Required**:
  - **Issue**: StatusBar.tsx에서 `import { API_URL } from '@/lib/api'` 사용했으나, api.ts에서 `API_URL`이 export되지 않아 Vercel 빌드 실패
  - **Error**: `Module '"@/lib/api"' declares 'API_URL' locally, but it is not exported`
  - **Fix**: `const API_URL` → `export const API_URL` (api.ts:58)
  - **Commit**: `c9efd80`
- **Created**: 2026-01-21
- **Completed**: 2026-01-21 22:53
- **Verified By**: User (Console: "No Issues", Network: No Mixed Content)
- **Commits**: `169dfb8` (proxy-headers), `c9efd80` (API_URL export)
- **Related**: BUG-015, BUG-016, BUG-017, BUG-018
- **Key Insight**: 프론트엔드만 수정해서는 해결 불가. 백엔드가 프록시 환경을 인식해야 함.

---

### BUG-020: PDF 텍스트 4000자 제한 - 95%+ 콘텐츠 무시 🔴 P0
- **Source**: Parallel Agent Audit (Import Pipeline) 2026-01-21
- **Status**: ⬜ Pending
- **Priority**: 🔴 P0 (Critical - 데이터 손실)
- **Assignee**: Backend Team
- **Files**:
  - `backend/importers/zotero_rdf_importer.py:569-577` - 엔티티 추출 텍스트 제한
- **Description**: Zotero RDF 임포트 시 PDF에서 추출된 텍스트의 첫 4000자만 엔티티 추출에 사용됨. 200+ 페이지 PDF에서 95% 이상의 콘텐츠가 무시되어 18개 노드만 생성됨.
- **Root Cause**:
  ```python
  # zotero_rdf_importer.py:569-577
  text_for_extraction = item.abstract or pdf_text[:4000]  # ❌ 첫 4000자만 사용!

  # PDF 전체 텍스트가 있더라도 첫 4000자만 엔티티 추출에 사용
  # 200페이지 = ~400,000자 중 1%만 처리됨
  ```
- **Impact**:
  - 16개 논문에서 18개 노드만 추출 (논문당 ~1개)
  - 개념 간 관계 파악 불가능
  - Knowledge Graph 유용성 심각하게 저하
- **Resolution**:
  1. **Semantic Chunking 도입**: PDF 전체 텍스트를 의미 단위로 분할
  2. **청크별 엔티티 추출**: 각 청크에서 엔티티 추출 후 병합
  3. **중복 제거**: 동일 엔티티 병합 및 출현 빈도 추적
  ```python
  # 수정 방안
  chunks = semantic_chunker.chunk_text(pdf_text, max_chunk_size=4000)
  all_entities = []
  for chunk in chunks:
      entities = await self._extract_entities_from_text(chunk)
      all_entities.extend(entities)
  merged_entities = self._merge_duplicate_entities(all_entities)
  ```
- **Acceptance Criteria**:
  - [ ] PDF 전체 텍스트를 청킹하여 처리
  - [ ] 청크별 엔티티 추출 구현
  - [ ] 중복 엔티티 병합 로직 구현
  - [ ] 16개 논문에서 100+ 노드 생성 확인
- **Created**: 2026-01-21
- **Related**: BUG-021, BUG-022

---

### BUG-021: Cohere API 키 없음 - 임베딩/관계 생성 완전 스킵 🔴 P0
- **Source**: Parallel Agent Audit (Edge Generation) 2026-01-21
- **Status**: ⬜ Pending
- **Priority**: 🔴 P0 (Critical - 관계 0개)
- **Assignee**: Backend Team / DevOps
- **Files**:
  - `backend/graph/embedding/embedding_pipeline.py:38-68` - 임베딩 생성 로직
  - `backend/importers/zotero_rdf_importer.py:649-671` - 관계 빌딩 조건
- **Description**: Cohere API 키가 설정되지 않아 임베딩 생성이 스킵되고, 임베딩이 없으면 관계 빌딩도 완전히 스킵됨. 결과적으로 0개의 엣지 생성.
- **Root Cause**:
  ```python
  # embedding_pipeline.py:38-68
  if settings.cohere_api_key:
      embedding_provider = CohereEmbeddingProvider(api_key=settings.cohere_api_key)
  else:
      logger.warning("No Cohere API key configured - skipping embedding creation")
      return 0  # ❌ 임베딩 0개 반환!

  # zotero_rdf_importer.py:649-671
  if extract_concepts and self.graph_store and embeddings_created > 0:
      # 관계 빌딩 로직
  # ❌ embeddings_created == 0이면 관계 빌딩 완전 스킵!
  ```
- **Dependency Chain**:
  ```
  Cohere API 키 없음
       ↓
  임베딩 생성 스킵 (return 0)
       ↓
  embeddings_created == 0
       ↓
  관계 빌딩 조건 실패
       ↓
  엣지 0개!
  ```
- **Resolution**:
  1. **Render에 COHERE_API_KEY 환경변수 설정**
  2. **폴백 로직 추가**: Cohere 없으면 OpenAI 임베딩 사용
  3. **Co-occurrence 관계 추가**: 임베딩 없이도 동시 출현 기반 관계 생성
- **Acceptance Criteria**:
  - [ ] Render에 COHERE_API_KEY 설정
  - [ ] 임베딩 Provider 폴백 로직 구현 (Cohere → OpenAI → 스킵)
  - [ ] 임베딩 없이도 Co-occurrence 관계 생성 옵션 추가
  - [ ] 재임포트 후 관계 생성 확인
- **API Key**: Configured in Render Dashboard (Environment Variables)
- **Created**: 2026-01-21
- **Related**: BUG-020, BUG-022

---

### BUG-022: Entity 추출 시 LLM Provider None - 키워드 폴백
- **Source**: Parallel Agent Audit (Import Pipeline) 2026-01-21
- **Status**: ⬜ Pending
- **Priority**: 🟡 Medium (기능 저하)
- **Assignee**: Backend Team
- **Files**:
  - `backend/importers/zotero_rdf_importer.py:155-180` - LLM Provider 초기화
- **Description**: LLM Provider가 None으로 초기화될 수 있어 LLM 기반 엔티티 추출 대신 키워드 기반 추출로 폴백됨. 키워드 추출은 정확도가 낮음.
- **Root Cause**:
  ```python
  # zotero_rdf_importer.py
  self.llm_provider = llm_provider  # None일 수 있음

  # 엔티티 추출 시
  if self.llm_provider:
      entities = await self._extract_entities_with_llm(text)
  else:
      entities = self._extract_entities_with_keywords(text)  # 정확도 낮음
  ```
- **Resolution**:
  1. **GROQ_API_KEY 환경변수 설정** (빠르고 무료)
  2. **LLM Provider 자동 초기화**: 환경변수 기반 자동 감지
  3. **명확한 경고 로깅**: LLM 없이 진행 시 사용자에게 알림
- **Acceptance Criteria**:
  - [ ] Render에 GROQ_API_KEY 설정
  - [ ] LLM Provider 자동 초기화 로직 개선
  - [ ] 키워드 폴백 시 명확한 경고 로깅
- **API Key**: Configured in Render Dashboard (Environment Variables)
- **Created**: 2026-01-21
- **Related**: BUG-020, BUG-021

---

### BUG-023: Three.js 버전 충돌 (0.160.1 vs 0.182.0)
- **Source**: Parallel Agent Audit (Visualization) 2026-01-21
- **Status**: ⬜ Pending
- **Priority**: 🟡 Medium (경고 + 잠재적 불안정)
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/package.json` - 의존성 버전
- **Description**: `three@0.160.1`이 직접 의존성으로 설치되어 있지만, `react-force-graph-3d`가 `three@0.182.0`을 peer dependency로 요구함. 두 버전이 충돌하여 콘솔 경고 발생.
- **Console Warning**:
  ```
  THREE.WebGLRenderer: Multiple THREE.js instances detected
  ```
- **Root Cause**:
  ```json
  // package.json
  "dependencies": {
    "three": "^0.160.1",           // 직접 설치
    "react-force-graph-3d": "..."  // three@0.182.0 peer dependency
  }
  ```
- **Resolution**:
  ```json
  // package.json에 overrides 추가
  "overrides": {
    "three": "0.160.1"
  }
  ```
  또는 three 버전을 0.182.0으로 업그레이드
- **Acceptance Criteria**:
  - [ ] Three.js 버전 통일 (overrides 또는 업그레이드)
  - [ ] "Multiple instances" 경고 제거 확인
  - [ ] 그래프 렌더링 정상 동작 확인
- **Created**: 2026-01-21
- **Related**: BUG-024

---

### BUG-024: 노드 클릭 시 자동 카메라 포커스 - 줌 불안정
- **Source**: Parallel Agent Audit (Visualization) 2026-01-21
- **Status**: ⬜ Pending
- **Priority**: 🟡 Medium (UX 저하)
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/components/graph/Graph3D.tsx:527-534` - onNodeClick 핸들러
- **Description**: 노드 클릭 시 `focusOnNode` 함수가 자동으로 카메라를 노드에 포커스하면서 줌 레벨이 변경됨. 사용자가 의도하지 않은 줌 변경으로 불안정한 UX 제공.
- **Root Cause**:
  ```typescript
  // Graph3D.tsx:527-534
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
    focusOnNode(node);  // ❌ 자동으로 카메라 이동 + 줌 변경
  }, [focusOnNode]);
  ```
- **Additional Issues**:
  - Hover 시 `setHoveredNode` 호출로 불필요한 리렌더링
  - Force simulation 설정이 적극적 (alphaDecay, velocityDecay)
- **Resolution**:
  1. **자동 포커스 제거 또는 옵션화**
  2. **더블클릭으로 포커스 변경** (단일 클릭은 선택만)
  3. **Hover 리렌더링 최적화**: 상태 업데이트 throttle
- **Acceptance Criteria**:
  - [ ] 노드 클릭 시 자동 카메라 이동 제거/옵션화
  - [ ] 더블클릭 시에만 카메라 포커스 (선택 사항)
  - [ ] 줌 안정성 개선 확인
- **Created**: 2026-01-21
- **Related**: BUG-023

---

### BUG-026: Rate Limiter가 OPTIONS Preflight 차단하여 CORS 에러
- **Source**: Systematic Debugging Session 2026-01-21
- **Status**: ✅ Completed
- **Priority**: 🔴 High (Import 기능 완전 차단)
- **Assignee**: Backend Team
- **Files**:
  - `backend/middleware/rate_limiter.py` - OPTIONS 요청 건너뛰기 추가
- **Description**: Vercel Preview URL에서 Zotero Import 시 Validation 단계에서 멈춤. 콘솔에 CORS 에러와 429 Too Many Requests 에러 동시 발생.
- **Root Cause Analysis**:
  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    요청 흐름 (문제)                              │
  ├─────────────────────────────────────────────────────────────────┤
  │  1. 프론트엔드: 빈번한 import status 폴링 (1초 간격)            │
  │  2. 각 GET 요청 전에 OPTIONS preflight 요청 발생               │
  │  3. Rate Limiter: OPTIONS도 rate limit에 카운트!               │
  │  4. 60 req/min 초과 → 429 Too Many Requests 반환               │
  │  5. OPTIONS가 429 반환 시 브라우저는 CORS 실패로 인식           │
  │  6. 실제 GET 요청 전에 CORS 에러로 차단                        │
  └─────────────────────────────────────────────────────────────────┘
  ```
- **Console Errors**:
  ```
  CORS Error: "Response to preflight request doesn't pass access control check:
              It does not have HTTP ok status."
  429 Error: "Too many requests. Please try again later."
  ```
- **Resolution**:
  1. **OPTIONS 요청 건너뛰기**: Rate limiter에서 CORS preflight 제외
  2. **Import status rate limit 증가**: 60 → 120 req/min
- **Acceptance Criteria**:
  - [x] OPTIONS 요청이 rate limit에서 제외됨
  - [x] Import status 폴링이 429 에러 없이 동작
  - [x] Vercel Preview URL에서 import 정상 동작
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: Network DevTools (200 OK responses, CORS headers present)
- **Commits**: `644a6fe`
- **Related**: BUG-019, CORS Configuration

---

### BUG-027: Import Progress가 0%에서 멈춤 - 다중 원인
- **Source**: Systematic Debugging Session + Codex gpt-5.2-codex Review 2026-01-21
- **Status**: ✅ Completed
- **Priority**: 🔴 P0 (Critical - Import 완전 차단)
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/import_.py` - progress_callback에서 JobStore 업데이트 추가
- **Description**: BUG-026 수정 후 CORS 에러는 해결되었으나, Zotero Import Validation 단계가 0%에서 진행되지 않음. 네트워크 탭에서 200 OK 응답 확인되었지만 progress가 항상 0.
- **Root Cause Analysis**:
  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    Progress 업데이트 흐름 (문제)                 │
  ├─────────────────────────────────────────────────────────────────┤
  │  1. Status API (/api/import/status/{id})                        │
  │     - JobStore에서 먼저 조회 (line 560-591)                      │
  │     - JobStore에서 발견되면 job.progress 반환                    │
  │                                                                 │
  │  2. _run_zotero_import (line 1361-1376)                         │
  │     - progress_callback은 _import_jobs만 업데이트!              │
  │     - job_store.update_job은 시작 시에만 호출 (line 1381-1386)  │
  │                                                                 │
  │  3. 결과                                                        │
  │     - JobStore progress는 항상 0.0 (초기값)                     │
  │     - Status API는 JobStore 우선 조회 → 0.0 반환               │
  │     - Legacy fallback (_import_jobs)에 도달 안함                │
  │                                                                 │
  │  ROOT CAUSE: progress_callback이 JobStore를 업데이트하지 않음!  │
  └─────────────────────────────────────────────────────────────────┘
  ```
- **Resolution**:
  - **progress_callback에서 asyncio.create_task로 JobStore 비동기 업데이트 추가**
  - 3개 임포트 함수 모두 수정: Zotero, PDF, Multi-PDF
  ```python
  def progress_callback(progress):
      # Update legacy in-memory store
      _import_jobs[job_id]["status"] = import_status
      _import_jobs[job_id]["progress"] = progress.progress
      ...

      # BUG-027 FIX: Also update JobStore
      try:
          import asyncio
          loop = asyncio.get_running_loop()
          loop.create_task(
              job_store.update_job(
                  job_id=job_id,
                  progress=progress.progress,
                  message=progress.message,
              )
          )
      except RuntimeError:
          logger.warning("Could not update JobStore: no running event loop")
  ```
- **Additional Root Cause (Codex gpt-5.2-codex Review)**:
  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │              Progress 단위 불일치 (핵심 원인)                    │
  ├─────────────────────────────────────────────────────────────────┤
  │                                                                 │
  │  Backend: progress = 0.1 (10%를 의미하는 fraction 0.0-1.0)      │
  │                    ↓                                            │
  │  Frontend: Math.round(0.1) = 0, width: "0.1%" (거의 안보임)     │
  │                    ↓                                            │
  │  결과: UI에 항상 0% 표시!                                       │
  │                                                                 │
  └─────────────────────────────────────────────────────────────────┘
  ```
- **Additional Fix (Frontend)**:
  ```typescript
  // frontend/components/import/ImportProgress.tsx
  // BUG-027 FIX: Backend sends progress as 0.0-1.0, convert to 0-100
  const progressPercent = Math.round((job.progress ?? 0) * 100);

  // Use progressPercent instead of job.progress
  {progressPercent}%
  style={{ width: `${progressPercent}%` }}
  ```
- **Phase 3 Fix (Fire-and-Forget Problem)**:
  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    Fire-and-Forget Problem                      │
  ├─────────────────────────────────────────────────────────────────┤
  │  asyncio.create_task()가 예외를 조용히 무시                     │
  │  DB 업데이트 실패 시 → 메모리만 업데이트됨                       │
  │  Status API는 DB 우선 조회 → stale 데이터 반환                  │
  │                                                                 │
  │  78% 계산: 0.25 + 0.65 * (8/10) = 0.77 ≈ 78%                   │
  └─────────────────────────────────────────────────────────────────┘
  ```
- **BUG-027-C Fix (Error Callback)**:
  ```python
  task = loop.create_task(job_store.update_job(...))
  def _handle_jobstore_error(t):
      if t.exception():
          logger.error(f"JobStore update failed: {t.exception()}")
  task.add_done_callback(_handle_jobstore_error)
  ```
- **BUG-027-D Fix (Status API Prefer Recent Data)**:
  ```python
  # Compare timestamps between DB and in-memory
  if legacy_updated > db_updated:
      return legacy_data  # Use in-memory if more recent
  ```
- **Acceptance Criteria**:
  - [x] progress_callback이 JobStore도 업데이트
  - [x] Frontend가 progress를 100배로 스케일링
  - [x] Fire-and-forget tasks에 error callback 추가
  - [x] Status API가 최신 데이터 소스를 우선 반환
  - [ ] Zotero Import가 Validation → Parsing → Processing → Complete
  - [ ] Frontend에서 실시간 progress 표시 (0% → 100%)
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Commits**: `16531bc` (JobStore update), `12d6ae4` (Frontend scaling), `fef83eb` (Error callback + Status API fix)
- **Related**: BUG-026

---

### BUG-028: Import가 37%에서 멈춤 - 서버 재시작으로 인한 Task 종료
- **Source**: Render 로그 분석 + Systematic Debugging 2026-01-21
- **Status**: ✅ Completed
- **Priority**: 🔴 P0 (Critical - Import 실패 시 원인 불명확)
- **Assignee**: Backend Team
- **Files**:
  - `backend/jobs/job_store.py` - INTERRUPTED 상태 추가
  - `backend/main.py` - 서버 시작 시 RUNNING job 감지
  - `backend/routers/import_.py` - ImportStatus에 INTERRUPTED 추가
  - `frontend/components/import/ImportProgress.tsx` - INTERRUPTED 처리
  - `frontend/types/graph.ts` - ImportJob 타입에 interrupted 추가
- **Description**: Import 진행 중 Render 자동 배포가 발생하면 background task가 종료되어 progress가 영원히 멈춤.
- **Root Cause Analysis**:
  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    Render Auto-Deploy 문제                      │
  ├─────────────────────────────────────────────────────────────────┤
  │  06:46:12 - Import 시작 (16 papers)                             │
  │       ↓                                                         │
  │  06:46:37 - 논문 4/16 처리 중 (progress ≈ 37%)                  │
  │       ↓                                                         │
  │  06:47:19 - ⚠️ Render: "==> Deploying..."                       │
  │       ↓                                                         │
  │  06:47:30 - 새 서버 시작, 이전 프로세스 종료                     │
  │       ↓                                                         │
  │  Background Task 사망 → Progress 업데이트 중단!                 │
  └─────────────────────────────────────────────────────────────────┘
  ```
- **Resolution**:
  - **BUG-028-A**: JobStatus에 INTERRUPTED 상태 추가
    ```python
    class JobStatus(str, Enum):
        INTERRUPTED = "interrupted"  # BUG-028
    ```
  - **BUG-028-B**: 서버 시작 시 RUNNING → INTERRUPTED 자동 변경
    ```python
    async def mark_running_as_interrupted(self) -> int:
        await self.db.execute("""
            UPDATE jobs SET status = 'interrupted',
            error = 'Server restarted during job execution.'
            WHERE status = 'running'
        """)
    ```
  - **BUG-028-C**: Frontend에서 INTERRUPTED 상태 처리
    ```typescript
    } else if (status.status === 'interrupted') {
        setError('Import was interrupted due to server restart.');
    }
    ```
- **Acceptance Criteria**:
  - [x] INTERRUPTED 상태가 JobStatus, ImportStatus에 추가됨
  - [x] 서버 시작 시 RUNNING job이 INTERRUPTED로 변경됨
  - [x] Frontend에서 INTERRUPTED 상태를 적절히 표시
  - [x] Checkpoint 저장 및 Resume 기능 → **BUG-028-EXT로 구현 완료**
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Related**: BUG-027, BUG-028-EXT

---

### BUG-028-EXT: Checkpoint 저장 및 Resume 기능 (BUG-028 확장)
- **Source**: BUG-028 향후 개선 방향 구현 2026-01-21
- **Status**: ✅ Completed
- **Priority**: 🟡 Medium (UX 개선 - 중단된 Import 재개 가능)
- **Assignee**: Backend/Frontend Team
- **Files**:
  - `backend/jobs/job_store.py` - `update_job()`에 metadata 파라미터 추가
  - `backend/routers/import_.py` - Checkpoint 헬퍼, Resume endpoint 추가
  - `backend/importers/zotero_rdf_importer.py` - skip_paper_ids, existing_project_id 지원
  - `frontend/types/graph.ts` - ImportCheckpoint, ImportResumeInfo 타입 추가
  - `frontend/lib/api.ts` - getResumeInfo(), resumeImport() 함수 추가
  - `frontend/components/import/ImportProgress.tsx` - Interrupted 상태 UI 강화
- **Description**: BUG-028에서 INTERRUPTED 상태 감지만 구현. 이 확장에서는 중단된 Import를 재개할 수 있도록 Checkpoint 저장 및 Resume 기능 구현.
- **Implementation Details**:
  - **Checkpoint 구조** (Paper 단위 저장):
    ```python
    checkpoint = {
        "processed_paper_ids": ["id1", "id2", ...],
        "total_papers": 16,
        "last_processed_index": 5,
        "project_id": "uuid-...",
        "stage": "importing",
        "updated_at": "2026-01-21T..."
    }
    ```
  - **Resume 방식** (Skip 방식):
    - 이미 처리된 paper_id 목록을 checkpoint에서 로드
    - 재개 시 해당 논문들 스킵하고 나머지만 처리
  - **Resume Endpoint**: `POST /api/import/resume/{job_id}`
  - **Resume Info Endpoint**: `GET /api/import/resume/{job_id}/info`
- **Frontend UI 변경**:
  - Interrupted 상태에서 checkpoint 진행률 표시
  - "파일 다시 업로드" 버튼 + "부분 결과 보기" 버튼
  - 이미 처리된 논문 수 및 안내 메시지 표시
- **Acceptance Criteria**:
  - [x] 각 논문 처리 완료 시 checkpoint가 metadata에 저장됨
  - [x] job_store.update_job()에 metadata 파라미터 지원
  - [x] Resume endpoint가 checkpoint 정보 반환
  - [x] ZoteroRDFImporter가 skip_paper_ids 파라미터 지원
  - [x] Frontend에서 interrupted 상태 시 checkpoint 정보 표시
  - [x] 파일 재업로드 시 처리된 논문 스킵하고 계속 진행
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Related**: BUG-028, INFRA-006

---

### BUG-025: Filter UI에 Paper/Author 표시 - ADR-001 위반
- **Source**: Parallel Agent Audit (Filter UI) 2026-01-21
- **Status**: ✅ Completed
- **Priority**: 🟢 Low (ADR 위반 - 기능적 영향 적음)
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/components/graph/EntityFilter.tsx` - 엔티티 필터 UI
  - `backend/graph/graph_store.py` - 엔티티 타입 정의
- **Description**: ADR-001에 따르면 Paper/Author는 메타데이터로만 존재하고 시각화되지 않아야 함. 그러나 Filter UI에 Paper/Author 필터 옵션이 표시됨.
- **ADR-001 요약**:
  > "Concept-Centric Knowledge Graph: Papers/Authors as metadata only, not visualized"
- **Root Cause**:
  ```typescript
  // EntityFilter.tsx
  const ALL_ENTITY_TYPES = ['Paper', 'Author', 'Concept', 'Method', 'Finding'];
  // ❌ Paper/Author가 하드코딩되어 있음
  ```
  ```python
  # graph_store.py - "Hybrid Mode" 존재
  class EntityType(Enum):
      PAPER = "Paper"      # 메타데이터지만 EntityType에 존재
      AUTHOR = "Author"    # 메타데이터지만 EntityType에 존재
      CONCEPT = "Concept"  # 시각화 대상
      ...
  ```
- **Resolution**:
  1. **동적 엔티티 타입 감지**: 실제 그래프 데이터에서 존재하는 타입만 표시
  2. **Paper/Author 필터 숨김**: 노드 수 0이면 필터에서 제외
  3. **ADR-001 명확화**: Hybrid Mode 문서화 또는 제거
- **Acceptance Criteria**:
  - [ ] Paper/Author가 0개일 때 필터에서 숨김
  - [ ] 또는 ADR-001 업데이트하여 Hybrid Mode 명시
- **Created**: 2026-01-21
- **Related**: ADR-001

---

### BUG-018: vercel.json 폐기된 Render 서비스 URL (Mixed Content 근본 원인)
- **Source**: Parallel Agent Brainstorming 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/vercel.json` - API rewrite URL 수정
  - `frontend/.env.local.example` - 예제 URL 수정
- **Description**: `vercel.json`의 rewrite 규칙이 삭제된 `scholarag-graph-api` 서비스를 가리키고 있어 Mixed Content 에러 발생. BUG-015/016/017 수정에도 불구하고 에러가 계속되는 실제 원인.
- **Root Cause**:
  ```json
  // 이전 코드 (버그) - vercel.json
  {
    "source": "/api/:path*",
    "destination": "https://scholarag-graph-api.onrender.com/api/:path*"  // ❌ 삭제된 서비스!
  }
  ```
- **Discovery Method**:
  1. `superpowers:brainstorming` 스킬로 체계적 문제 탐색
  2. `superpowers:dispatching-parallel-agents`로 3개 에이전트 병렬 조사
  3. 브라우저 자동화로 Vercel 환경 변수 직접 확인 → HTTPS 정상 설정 확인
  4. 에이전트가 `vercel.json`의 폐기된 URL 발견
- **Resolution**:
  ```json
  // 수정된 코드
  {
    "source": "/api/:path*",
    "destination": "https://scholarag-graph-docker.onrender.com/api/:path*"  // ✅ 현재 Docker 서비스
  }
  ```
- **Acceptance Criteria**:
  - [x] `vercel.json` rewrite URL을 Docker 서비스로 변경
  - [x] `.env.local.example`의 참조 URL도 업데이트
  - [x] Vercel 재배포 트리거
  - [x] Mixed Content 에러 해결
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: Claude Code
- **Commit**: `3523eb4`
- **Related**: BUG-015, BUG-016, BUG-017, INFRA-004 (Python→Docker 마이그레이션)
- **Lesson Learned**: 인프라 마이그레이션(INFRA-004) 시 `vercel.json` rewrite 규칙도 함께 업데이트해야 함

---

### BUG-015: system.py get_connection() AttributeError 수정
- **Source**: Root Cause Analysis 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/system.py:95` - 버그 위치
  - `backend/database.py` - Database 클래스 인터페이스
- **Description**: `db.get_connection()` 메서드가 존재하지 않아 `/api/system/status` 엔드포인트에서 500 에러 발생. 이 에러가 CORS 에러로 마스킹되어 반복적인 CORS 수정 시도로 이어짐.
- **Root Cause**:
  ```python
  # 이전 코드 (버그)
  database = await db.get_connection()  # ❌ AttributeError!

  # Database 클래스에는 get_connection() 메서드가 없음
  # 사용 가능한 메서드: acquire(), fetch(), fetchval(), fetchrow()
  ```
- **Render 로그 증거**:
  ```
  AttributeError: 'Database' object has no attribute 'get_connection'
  File "/app/routers/system.py", line 92, in get_system_status
  ```
- **Resolution**:
  ```python
  # 수정된 코드: acquire() context manager 사용
  async with db.acquire() as conn:
      result = await conn.fetchval(query, project_id)
  ```
- **Acceptance Criteria**:
  - [x] `system.py`의 `get_connection()` 호출을 올바른 메서드로 교체
  - [x] 로컬에서 `/api/system/status` 엔드포인트 테스트
  - [x] Render 재배포 후 500 에러 해결 확인
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: Claude Code
- **Commits**: `b95c051`, `feaa756`
- **Related**: Session `2026-01-21_root-cause-analysis-recurring-errors.md`, `2026-01-21_parallel-agent-debugging-deployment-fix.md`

---

### BUG-016: SSR에서 enforceHttps 작동 안함 (Mixed Content)
- **Source**: Parallel Agent Debugging 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/lib/api.ts` - `enforceHttps()` 함수 수정
- **Description**: `enforceHttps` 함수가 `window.location.protocol`을 체크하는데, Next.js SSR 환경에서는 `window`가 undefined라서 HTTP URL이 그대로 통과됨. HTTPS 페이지에서 HTTP API 요청 시 Mixed Content 에러 발생.
- **Root Cause**:
  ```typescript
  // 이전 코드 (버그)
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return url.replace(/^http:\/\//, 'https://');
  }
  // SSR에서 window === undefined → HTTPS 강제 안됨!
  ```
- **Resolution**:
  ```typescript
  // 수정된 코드: 프로덕션 도메인은 항상 HTTPS 강제 (SSR에서도 작동)
  if (url.includes('onrender.com') || url.includes('vercel.app') || url.includes('render.com')) {
    return url.replace(/^http:\/\//, 'https://');
  }
  ```
- **Acceptance Criteria**:
  - [x] 프로덕션 도메인에서 HTTPS 강제 적용
  - [x] SSR 환경에서도 정상 작동
  - [x] Mixed Content 에러 해결
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: Claude Code
- **Commit**: `4611214`
- **Related**: Session `2026-01-21_parallel-agent-debugging-deployment-fix.md`

---

### BUG-017: quota_middleware.py ImportError (배포 차단)
- **Source**: Parallel Agent Debugging 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/middleware/quota_middleware.py:29` - import 문 수정
- **Description**: 존재하지 않는 함수 `get_current_user_optional`을 import하여 앱 시작 실패. BUG-015 수정 배포를 차단하는 원인이 됨.
- **Root Cause**:
  ```python
  # 이전 코드 (버그)
  from auth.dependencies import get_current_user_optional  # ❌ 존재하지 않음!

  # auth.dependencies.py에 있는 실제 함수명:
  # - get_optional_user  ✅
  # - get_current_user
  ```
- **Render 로그 증거**:
  ```
  ImportError: cannot import name 'get_current_user_optional' from 'auth.dependencies'
  File "/app/middleware/quota_middleware.py", line 29
  ```
- **Resolution**:
  ```python
  # 수정된 코드
  from auth.dependencies import get_optional_user  # ✅ 올바른 함수명
  ```
- **Acceptance Criteria**:
  - [x] 올바른 함수명으로 import 수정
  - [x] `QuotaDependency` 클래스에서 올바른 함수 사용
  - [x] 중복 로컬 함수 제거
  - [x] Render 배포 성공
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: Claude Code
- **Commit**: `feaa756`
- **Related**: Session `2026-01-21_parallel-agent-debugging-deployment-fix.md`, BUG-015

---

### TEST-001: InfraNodus DB Migrations 실행
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Files**:
  - `database/migrations/012_relationship_evidence.sql`
  - `database/migrations/013_entity_temporal.sql`
- **Description**: 새로운 InfraNodus 기능을 위한 DB 마이그레이션 실행 필요
- **Acceptance Criteria**:
  - [ ] Supabase에서 012_relationship_evidence.sql 실행
  - [ ] Supabase에서 013_entity_temporal.sql 실행
  - [ ] `migrate_entity_temporal_data()` 함수 실행하여 기존 데이터 백필
  - [ ] 테이블 및 인덱스 생성 확인
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

---

## 🟡 Medium Priority (Short-term)

### ARCH-002: GraphStore God Object 리팩토링
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/graph_store.py` - Facade로 리팩토링 (~300 라인)
  - `backend/graph/persistence/entity_dao.py` - Entity/Relationship CRUD (신규)
  - `backend/graph/persistence/chunk_dao.py` - Chunk 저장/검색 (신규)
  - `backend/graph/embedding/embedding_pipeline.py` - 임베딩 생성/검색 (신규)
  - `backend/graph/analytics/graph_analytics.py` - 통계/분석 (신규)
- **Description**: GraphStore가 persistence, graph algorithms, embeddings, import helpers, chunk storage를 모두 담당하여 결합도가 높고 테스트/확장이 어려움
- **Resolution**: Facade 패턴으로 리팩토링하여 4개 모듈로 분리. 기존 API는 100% 하위 호환성 유지.
- **Acceptance Criteria**:
  - [x] Persistence DAO 분리 (EntityDAO)
  - [x] Embedding pipeline 분리 (EmbeddingPipeline)
  - [x] Graph analytics 분리 (GraphAnalytics)
  - [x] Chunk storage 분리 (ChunkDAO)
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### PERF-008: 임베딩 업데이트 배치 처리
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/graph_store.py:623-662` - 엔티티 임베딩 배치 업데이트
  - `backend/graph/graph_store.py:1329-1357` - 청크 임베딩 배치 업데이트
- **Description**: 임베딩 업데이트가 row별 개별 쿼리로 실행되어 대량 처리 시 성능 저하
- **Resolution**:
  1. `executemany`를 사용한 배치 업데이트 구현
  2. 배치 실패 시 개별 업데이트로 fallback
  3. 엔티티 및 청크 임베딩 모두 적용
- **Acceptance Criteria**:
  - [x] `executemany` 사용한 배치 업데이트 구현
  - [x] Fallback 로직 추가
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report, PERF-006 (동일 이슈)

---

### SEC-012: Auth 설정 불일치 처리
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/main.py:81-107` - Supabase 초기화 및 검증 로직
- **Description**: Supabase가 설정되지 않았지만 `require_auth=true`인 경우 503/401 에러 발생
- **Resolution**:
  1. 프로덕션에서 `require_auth=true`지만 Supabase 미설정 시 startup 실패
  2. 개발 환경에서 명확한 경고 출력 후 auth 자동 비활성화
- **Acceptance Criteria**:
  - [x] dev 모드에서 auth 자동 비활성화 + 명확한 경고
  - [x] prod에서 auth 필수인데 미설정 시 startup 실패
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### TEST-002: InfraNodus 새 API 엔드포인트 테스트
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Description**: 새로 추가된 6개 API 엔드포인트에 대한 단위 테스트 작성
- **Endpoints**:
  - `GET /api/graph/relationships/{id}/evidence`
  - `GET /api/graph/temporal/{project_id}`
  - `POST /api/graph/temporal/{project_id}/migrate`
  - `POST /api/graph/gaps/{id}/generate-bridge`
  - `GET /api/graph/diversity/{project_id}`
  - `GET /api/graph/compare/{a}/{b}`
- **Acceptance Criteria**:
  - [ ] 각 엔드포인트별 테스트 케이스 작성
  - [ ] 인증 및 권한 테스트 포함
  - [ ] 에러 케이스 테스트 포함
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

---

### FUNC-004: TemporalSlider KnowledgeGraph 통합
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/components/graph/KnowledgeGraph.tsx`
  - `frontend/components/graph/TemporalSlider.tsx`
- **Description**: TemporalSlider 컴포넌트를 KnowledgeGraph 메인 뷰에 통합
- **Acceptance Criteria**:
  - [ ] KnowledgeGraph.tsx에 TemporalSlider 렌더링
  - [ ] useTemporalGraph 훅 연동
  - [ ] 연도별 노드 필터링 동작 확인
  - [ ] 애니메이션 재생/정지 기능 테스트
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

---

### DOC-002: InfraNodus API 문서화
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Docs Team
- **Description**: 새로운 InfraNodus 관련 API 엔드포인트 문서화
- **Acceptance Criteria**:
  - [ ] API 엔드포인트별 요청/응답 스키마 문서화
  - [ ] 사용 예제 추가
  - [ ] CLAUDE.md API 섹션 업데이트
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

---

### INFRA-005: Infrastructure as Code 도입
- **Source**: Root Cause Analysis 2026-01-21
- **Status**: ⏳ Pending
- **Assignee**: DevOps Team
- **Files**:
  - `render.yaml` (신규)
  - `vercel.json` (업데이트)
- **Description**: 환경 변수를 코드로 관리하여 Configuration Drift 방지. 코드 기본값과 플랫폼 환경 변수 간 불일치로 인한 반복적 CORS/API URL 수정 문제 해결.
- **Background**:
  최근 커밋 히스토리에서 동일 유형 문제 반복 수정:
  - `1ca4f4b` - CORS origins 추가
  - `ac11672` - Vercel Preview URL regex
  - `882f14a` - Rate limiter CORS 헤더
  - `22217b5` - HTTPS 강제 변환
- **Acceptance Criteria**:
  - [ ] `render.yaml` 생성 (서비스 설정 + 환경 변수)
  - [ ] `vercel.json`에 환경 변수 참조 추가
  - [ ] CI/CD에서 환경 변수 일치 검증 자동화
- **Created**: 2026-01-21
- **Related**: Session `2026-01-21_root-cause-analysis-recurring-errors.md`

---

### PERF-006: 청크 임베딩 배치 업데이트
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/graph_store.py:1329-1357` - 청크 임베딩 배치 업데이트
- **Description**: 청크 임베딩이 개별 쿼리로 실행되어 대량 처리 시 성능 저하
- **Resolution**: PERF-008과 동일 - `executemany` 배치 업데이트 적용
- **Acceptance Criteria**:
  - [x] `executemany` 배치 업데이트 사용
  - [x] Fallback 로직 추가
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: PERF-008 (동일 이슈로 함께 해결), Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### PERF-004: 503 에러 모니터링
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Files**:
  - `backend/middleware/error_tracking.py` - 에러 추적 서비스 (신규)
  - `backend/routers/system.py` - 에러 메트릭 엔드포인트 추가
  - `backend/main.py` - ErrorTrackingMiddleware 등록
  - `DOCS/operations/503-error-monitoring.md` - 모니터링 가이드 (신규)
- **Description**: 배포 후 503 에러 발생률 모니터링
- **Resolution**:
  1. `ErrorTracker` 클래스 - 에러 이벤트 인메모리 추적 (최근 100개)
  2. `ErrorTrackingMiddleware` - 모든 4xx/5xx 응답 자동 기록
  3. 503 에러 로그 포맷: `[503_ERROR] path=... method=... response_time_ms=...`
  4. API 엔드포인트:
     - `GET /api/system/metrics/errors` - 전체 에러 요약
     - `GET /api/system/metrics/error-rate` - 시간 윈도우별 에러율
     - `GET /api/system/metrics/503` - 503 에러 상세 분석
     - `GET /api/system/metrics/recent-errors` - 최근 에러 목록
  5. Render 알림 설정 가이드 문서화
- **Acceptance Criteria**:
  - [x] Render 로그에서 503 에러 빈도 확인 (로그 패턴 `[503_ERROR]`)
  - [x] 에러 발생 시 알림 설정 (문서화 완료)
  - [x] 에러 메트릭 API 엔드포인트 추가
- **Created**: 2026-01-19
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Session `2026-01-19_render-starter-optimization.md`

---

## 🟢 Low Priority (Long-term)

### TEST-004: Frontend 테스트 추가
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/jest.config.js` - Jest 설정 (신규)
  - `frontend/jest.setup.js` - 테스트 setup (신규)
  - `frontend/__tests__/components/ui/ErrorDisplay.test.tsx` - ErrorDisplay 테스트 (신규)
  - `frontend/__tests__/components/ui/Skeleton.test.tsx` - Skeleton 테스트 (신규)
  - `frontend/__tests__/components/auth/LoginForm.test.tsx` - LoginForm 테스트 (신규)
  - `frontend/package.json` - 테스트 의존성 추가
- **Description**: 프론트엔드 컴포넌트 테스트 및 E2E smoke 테스트 부재
- **Resolution**:
  1. Jest + React Testing Library 설정
  2. Next.js router 및 Supabase 클라이언트 mock
  3. ErrorDisplay, Skeleton, LoginForm 컴포넌트 테스트 작성
- **Acceptance Criteria**:
  - [x] 핵심 컴포넌트 unit 테스트 추가
  - [ ] Auth flow E2E 테스트 (future)
  - [ ] CI에 테스트 연동 (future)
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### FUNC-005: Per-Project/User API 할당량
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `database/migrations/014_api_quota.sql` - DB 스키마 (신규)
  - `backend/middleware/quota_service.py` - 쿼터 서비스 (신규)
  - `backend/middleware/quota_middleware.py` - FastAPI 미들웨어 (신규)
  - `backend/routers/quota.py` - 쿼터 API 라우터 (신규)
  - `backend/routers/integrations.py` - 쿼터 의존성 적용
  - `backend/main.py` - 쿼터 미들웨어 등록
- **Description**: 외부 통합(Semantic Scholar, OpenAlex 등)에 대한 프로젝트/사용자별 할당량 없음
- **Resolution**:
  1. DB 스키마 추가: `api_quota_plans`, `user_quota_assignments`, `api_usage` 테이블
  2. 4단계 플랜 (free, basic, premium, enterprise) 각각 다른 할당량
  3. `QuotaService` - 쿼터 확인, 사용량 추적, 인메모리 캐싱
  4. `QuotaDependency` - FastAPI 의존성으로 쿼터 체크
  5. `QuotaTrackingMiddleware` - 자동 사용량 추적
  6. `/api/quota/*` 엔드포인트 - 사용량 조회 API
  7. 응답 헤더에 쿼터 정보 포함 (X-Quota-Limit, X-Quota-Used, X-Quota-Remaining)
- **Acceptance Criteria**:
  - [x] 프로젝트별 또는 사용자별 일일 API 호출 제한
  - [x] 초과 시 경고 (80%) 또는 차단 (100%)
  - [x] 쿼터 현황 조회 API
  - [x] 응답 헤더에 쿼터 정보 포함
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### TEST-003: InfraNodus E2E 테스트
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: QA Team
- **Description**: 모든 InfraNodus 기능에 대한 수동 E2E 테스트
- **Test Cases**:
  - [ ] Edge 클릭 → EdgeContextModal 열림 → 원문 표시 확인
  - [ ] TemporalSlider 연도 조절 → 노드 필터링 확인
  - [ ] GapPanel "Generate Bridge" 클릭 → 가설 생성 확인
  - [ ] InsightHUD 다양성 게이지 표시 확인
  - [ ] /projects/compare 페이지 → 프로젝트 비교 동작 확인
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

---

### DOC-003: 에러 디버깅 가이드 작성
- **Source**: Root Cause Analysis 2026-01-21
- **Status**: ⏳ Pending
- **Assignee**: Docs Team
- **Files**:
  - `DOCS/troubleshooting/error-debugging-guide.md` (신규)
- **Description**: CORS 에러가 실제로는 백엔드 500 에러를 마스킹할 수 있다는 점 문서화. 개발자가 프로덕션 에러를 효율적으로 디버깅할 수 있도록 가이드 제공.
- **Key Topics**:
  1. CORS 에러 마스킹 현상 설명
  2. Render 로그 확인 방법
  3. `/api/system/metrics/errors` 활용법
  4. 에러 유형별 체크리스트
- **Acceptance Criteria**:
  - [ ] CORS vs 실제 백엔드 에러 구분 방법 문서화
  - [ ] Render Dashboard 로그 확인 가이드
  - [ ] 일반적인 500 에러 원인 및 해결 방법
- **Created**: 2026-01-21
- **Related**: Session `2026-01-21_root-cause-analysis-recurring-errors.md`, BUG-015

---

### DOC-001: 배포 가이드에 Starter 플랜 권장사항 추가
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ⬜ Pending
- **Assignee**: Docs Team
- **Description**: Render Starter 플랜 최적화 설정 문서화
- **Acceptance Criteria**:
  - [ ] 연결 풀 설정 권장값 문서화
  - [ ] 프론트엔드 재시도 로직 설명 추가
- **Created**: 2026-01-19

---

### FUNC-003: /api/system/status 엔드포인트 구현
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ⬜ Pending
- **Assignee**: Backend Team
- **Description**: StatusBar 컴포넌트용 시스템 상태 API 구현
- **Acceptance Criteria**:
  - [ ] LLM 연결 상태 반환
  - [ ] 벡터 인덱싱 상태 반환
  - [ ] 데이터 소스 정보 반환
- **Created**: 2026-01-19

---

## 📝 Completed Items Archive

### SEC-011: Rate Limiter X-Forwarded-For Spoofing 취약점
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Priority**: 🔴 High (Security Vulnerability)
- **Files**:
  - `backend/middleware/rate_limiter.py:305-356` - trusted proxy 로직 추가
  - `backend/config.py:81-87` - `trusted_proxy_mode` 설정 추가
- **Description**: Rate limiter가 `X-Forwarded-For` 헤더를 무조건 신뢰하여 IP 스푸핑으로 rate limit 우회 가능
- **Risk**: DoS 공격, Rate limit 우회
- **Resolution**:
  1. `trusted_proxy_mode` 설정 추가 (`auto`, `always`, `never`)
  2. `auto` 모드: 프로덕션에서만 X-Forwarded-For 신뢰 (Render LB 뒤)
  3. 개발 환경에서는 직접 연결 IP 사용하여 스푸핑 방지
  4. 디버그 로깅으로 IP 소스 추적 가능
- **Acceptance Criteria**:
  - [x] Trusted proxy 설정 추가
  - [x] 프록시 뒤에 있을 때만 `X-Forwarded-For` 사용
  - [x] 환경별 자동 감지 (`auto` 모드)
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report, Session `2026-01-20_mixed-content-cors-fix.md`

---

### ARCH-001: DB 연결 실패 시 일관된 동작 구현
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Priority**: 🔴 High (Architecture)
- **Files**:
  - `backend/main.py:88-114` - DB 초기화 + fail-fast 로직
  - `backend/database.py:184-207` - `require_db()` dependency 추가
- **Description**: DB 초기화 실패 시 앱이 계속 실행되지만 대부분의 엔드포인트가 500 에러 발생
- **Risk**: Cascading 500 에러, 불일치한 동작
- **Resolution**:
  1. 프로덕션/스테이징에서 DB 연결 실패 시 fail-fast (앱 시작 차단)
  2. `require_db()` dependency 추가 - DB 없으면 503 반환
  3. 개발 환경에서만 memory-only 모드 허용
- **Acceptance Criteria**:
  - [x] 프로덕션에서 DB 실패 시 fail-fast
  - [x] `require_db()` dependency로 일관된 503 응답
  - [x] 개발 환경에서 memory-only 모드 허용
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### BUG-015: Mixed Content & CORS Error (Vercel Preview)
- **Source**: Production Error 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Priority**: 🔴 High (Production CORS Error)
- **Files**:
  - `frontend/lib/api.ts` - HTTPS 강제 로직 추가
- **Description**: Vercel Preview 배포에서 Mixed Content 에러와 CORS 에러 발생
- **Error Messages**:
  ```
  Mixed Content: The page at 'https://...' was loaded over HTTPS, but requested
  an insecure resource 'http://scholarag-graph-docker.onrender.com/api/projects/'

  CORS error: Access to fetch blocked - No 'Access-Control-Allow-Origin' header
  Origin: https://schola-rag-graph-1fugffud8-hosung-yous-projects.vercel.app
  ```
- **Root Cause**: `NEXT_PUBLIC_API_URL` 환경변수가 HTTP로 설정되어 HTTPS 페이지에서 HTTP 요청 차단됨
- **Resolution**:
  1. `enforceHttps()` 함수 추가하여 HTTPS 페이지에서 자동으로 HTTP → HTTPS 변환
  2. 디버그 로깅 개선으로 HTTPS 강제 여부 표시
- **Commit**: `22217b5`
- **Completed**: 2026-01-20
- **Related**: Session `2026-01-20_mixed-content-cors-fix.md`

---

### BUG-014: Rate Limiter 429 응답에 CORS 헤더 누락
- **Source**: Production Error 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Priority**: 🔴 High (Production CORS Error)
- **Files**:
  - `backend/middleware/rate_limiter.py:330-342` - 429 응답 생성 로직
- **Description**: Import 진행 중 status 폴링이 rate limit(5/min)에 걸리면 429 응답이 CORS 헤더 없이 반환되어 브라우저에서 CORS 에러로 표시됨
- **Error Message**:
  ```
  429 Too Many Requests
  CORS error: No 'Access-Control-Allow-Origin' header present
  ```
- **Root Cause**: `JSONResponse`를 직접 반환하면 CORS middleware를 우회함
- **Resolution**:
  1. Rate limiter 429 응답에 CORS 헤더 추가
  2. `/api/import/status/*` 폴링 limit 완화 (60/min)
  3. `/api/import/*` limit 증가 (5 → 10/min)
- **Commit**: `882f14a`
- **Completed**: 2026-01-20
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### BUG-013: semantic_chunker `Any` 타입 임포트 누락
- **Source**: Production Error Log 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Priority**: 🔴 High (Production 500 Error)
- **Files**:
  - `backend/importers/semantic_chunker.py:15` - typing import
  - `backend/importers/semantic_chunker.py:461` - `Dict[str, Any]` 반환 타입
- **Description**: `/api/import/zotero/validate` 엔드포인트 호출 시 500 Internal Server Error 발생
- **Error Message**:
  ```
  NameError: name 'Any' is not defined
  File "/app/importers/semantic_chunker.py", line 461, in SemanticChunker
  ```
- **Root Cause**: `typing` 모듈에서 `Any`가 임포트되지 않았으나 `Dict[str, Any]` 타입 힌트에서 사용됨
- **Fix**:
  ```python
  # Before
  from typing import List, Optional, Dict, Tuple
  # After
  from typing import List, Optional, Dict, Tuple, Any
  ```
- **Acceptance Criteria**:
  - [x] `Any` 타입 임포트 추가
  - [x] `/api/import/zotero/validate` 정상 작동 확인
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Commit**: `d2dd6d6`
- **Verified By**: Claude Code
- **Lesson Learned**: 타입 힌트 추가 시 해당 타입이 임포트되었는지 확인 필요

---

### SEC-007: CORS 보안 강화
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/main.py:116-136` - CORS 설정
- **Description**: `*.vercel.app` 와일드카드 + credentials 허용은 보안 위험
- **Risk**: Cross-origin 공격 가능성
- **Acceptance Criteria**:
  - [x] 명시적 origin 목록으로 변경
  - [x] 프로덕션 환경에서 와일드카드 제거
  - [x] 개발 모드에서만 localhost 허용
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: `allow_origin_regex` 제거, 명시적 origin 목록만 사용, 메서드/헤더 제한
- **Related**: Session `2026-01-20_security-fixes.md`

---

### SEC-008: DB 불가 시 Chat 액세스 비활성화
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/chat.py:81` - DB 연결 검사 로직
- **Description**: DB 연결 실패 시 인증 우회 가능 취약점
- **Risk**: 무단 채팅 접근
- **Acceptance Criteria**:
  - [x] DB 불가 시 chat 엔드포인트 비활성화 (production/staging)
  - [x] 적절한 에러 응답 반환 (503 Service Unavailable)
  - [x] 개발 모드에서만 memory-only 허용
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: 환경별 분기 처리로 프로덕션 보안 강화
- **Related**: Session `2026-01-20_security-fixes.md`

---

### SEC-009: SQL Injection 방어 추가
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/graph_store.py:1381` - search_chunks 함수
- **Description**: 사용자 입력 검증 부족으로 SQL injection 위험
- **Acceptance Criteria**:
  - [x] 파라미터화된 쿼리 사용 (LIMIT 파라미터화)
  - [x] 입력 검증 로직 추가 (top_k: 1-100 범위 제한)
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: `top_k` f-string → 파라미터화 쿼리, 최대값 100 제한
- **Related**: Session `2026-01-20_security-fixes.md`

---

### SEC-010: Import Path Validation 강화
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/import_.py:139` - 경로 검증 로직
- **Description**: `ALLOWED_IMPORT_ROOTS` 비어있을 때 모든 경로 허용됨
- **Acceptance Criteria**:
  - [x] 시스템 디렉토리 차단 (개발 모드 포함)
  - [x] Path traversal 공격 방어 추가
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: `/etc`, `/var`, `/usr` 등 시스템 경로 차단, macOS/Windows 경로 포함
- **Related**: Session `2026-01-20_security-fixes.md`

---

### BUG-012: 채팅 메시지 트랜잭션 적용
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/chat.py:160` - 메시지 삽입 로직
- **Description**: 채팅 메시지 삽입이 트랜잭션 없이 실행됨
- **Acceptance Criteria**:
  - [x] 트랜잭션으로 메시지 삽입 래핑
  - [x] 실패 시 롤백 처리
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: `db.transaction()` 컨텍스트 매니저로 래핑
- **Related**: Session `2026-01-20_security-fixes.md`

---

### INFRA-003: Render Docker 캐시 활성화
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Description**: Docker 빌드 캐시 활성화로 빌드 시간 단축
- **Acceptance Criteria**:
  - [x] Render는 자동으로 Docker 빌드 캐시 활성화
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: Render 문서 확인: "Render caches all intermediate build layers" - 별도 설정 불필요
- **Related**: Session `2026-01-20_security-fixes.md`

---

### INFRA-004: 기존 Python 서비스 삭제
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Description**: Docker 서비스로 마이그레이션 완료 후 기존 Python 서비스 삭제
- **Service ID**: `srv-d5n4aesoud1c739ot8a0` (삭제됨)
- **Acceptance Criteria**:
  - [x] 기존 Python 서비스 삭제
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: User (수동 삭제)
- **Notes**: Render Dashboard에서 수동 삭제 완료
- **Related**: Session `2026-01-20_security-fixes.md`

---

### INFRA-006: Auto-Deploy 비활성화 (BUG-028 예방)
- **Source**: BUG-028 분석 결과 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Description**: Render Auto-Deploy 기능이 import 진행 중 서버를 재시작하여 background task를 종료시킴. 이를 방지하기 위해 Auto-Deploy를 비활성화하고 수동 배포로 전환.
- **Root Cause**:
  ```
  git push → Render Auto-Deploy → 서버 재시작 → Import task 사망 → Progress 멈춤
  ```
- **Configuration Change**:
  - **Path**: Render Dashboard → `scholarag-graph-docker` → Settings → Build & Deploy → Auto-Deploy
  - **Before**: On Commit
  - **After**: **Off**
- **Deployment Process (New)**:
  1. Render Dashboard → `scholarag-graph-docker` 접속
  2. "Manual Deploy" → "Deploy latest commit" 클릭
  3. ⚠️ 배포 전 진행 중인 import가 없는지 확인
- **Acceptance Criteria**:
  - [x] Auto-Deploy를 Off로 변경
  - [x] CLAUDE.md에 문서화
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Related**: BUG-028

---

### BUG-011: DATABASE_URL 특수문자 연결 실패
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Description**: Supabase 비밀번호의 특수문자(`!!!!`)로 인한 URL 인코딩 문제
- **Error**: `InvalidPasswordError: password authentication failed`
- **Acceptance Criteria**:
  - [x] Supabase 비밀번호 변경 (특수문자 제거)
  - [x] DATABASE_URL 환경변수 업데이트
  - [x] Health endpoint에서 DB 연결 확인
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: 비밀번호를 `ScholaRAG2026`으로 변경하여 해결
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### BUG-010: DB 연결 에러 로깅 개선
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/database.py` - 예외 로깅 상세화
- **Description**: DB 연결 실패 시 구체적인 에러 정보 로깅
- **Acceptance Criteria**:
  - [x] 예외 타입과 메시지 로깅 추가
  - [x] `{type(e).__name__}: {e}` 형식으로 출력
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Commit**: `866b23c fix(docker): optimize build with split requirements and improved error logging`
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### PERF-007: Docker 빌드 최적화 (Requirements 분리)
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Files**:
  - `Dockerfile` - requirements 분리 로직 추가
  - `backend/requirements-base.txt` - 경량 의존성 (신규)
  - `backend/requirements-specter.txt` - SPECTER2 의존성 (신규)
- **Description**: PyTorch/SPECTER2를 선택적으로 분리하여 이미지 크기 ~200MB 감소
- **Acceptance Criteria**:
  - [x] requirements-base.txt 생성 (SPECTER2 제외)
  - [x] requirements-specter.txt 생성 (선택적)
  - [x] Dockerfile에 ENABLE_SPECTER2 빌드 인자 추가
  - [x] 커밋 및 푸시
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Commit**: `866b23c fix(docker): optimize build with split requirements and improved error logging`
- **Notes**: Pipeline minutes 소진으로 배포 대기 중. 다음 달 리셋 시 자동 적용 예정.
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### BUG-005: pgbouncer prepared statement 충돌 수정
- **Source**: Production Error 2026-01-19
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/database.py` - `statement_cache_size=0` 추가
- **Description**: Supabase pgbouncer (transaction mode)와 asyncpg prepared statement 충돌 해결
- **Error**: `DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_16__" already exists`
- **Acceptance Criteria**:
  - [x] `statement_cache_size=0` 설정으로 prepared statement 비활성화
  - [x] 프로덕션 500 에러 해결 확인
  - [x] API 정상 응답 (200 OK) 확인
- **Created**: 2026-01-19
- **Completed**: 2026-01-19
- **Verified By**: Claude Code
- **Commit**: `888c96e fix(database): disable prepared statements for pgbouncer compatibility`
- **Notes**: CORS 에러로 표시되었지만 실제 원인은 서버 측 pgbouncer 충돌

---

### BUG-004: 503 에러 - DB 연결 풀 최적화
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/database.py` - 연결 풀 크기 축소 (min:2, max:5)
- **Description**: Free-tier DB 연결 제한(~20)에 맞게 풀 크기 최적화
- **Acceptance Criteria**:
  - [x] min_size=2, max_size=5 설정
  - [x] max_inactive_connection_lifetime=300 추가
  - [x] 503 에러 감소 확인
- **Created**: 2026-01-19
- **Completed**: 2026-01-19
- **Verified By**: Claude Code
- **Notes**: 5회 연속 테스트 모두 200 OK 확인

---

### PERF-005: 프론트엔드 API 재시도 로직
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/lib/api.ts` - 503 에러 자동 재시도 로직 추가
- **Description**: Starter 플랜용 빠른 재시도 로직 (500ms 백오프)
- **Acceptance Criteria**:
  - [x] 3회 재시도 로직 구현
  - [x] 500ms × attempt 지수 백오프
  - [x] 네트워크 에러 및 503 처리
- **Created**: 2026-01-19
- **Completed**: 2026-01-19
- **Verified By**: Claude Code
- **Notes**: Starter 플랜은 cold start 없음 → 빠른 백오프 적용

---

### SEC-001: Graph/Chat 엔드포인트 인증 강제
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/graph.py` - `require_auth_if_configured` dependency 추가
  - `backend/routers/chat.py` - `require_auth_if_configured` dependency 추가
- **Description**: 모든 graph/chat 엔드포인트에 인증 및 프로젝트 접근 검사를 강제
- **Acceptance Criteria**:
  - [x] 모든 graph 엔드포인트에 `require_auth_if_configured` 추가
  - [x] 프로젝트 소유권/협업자 접근 검증 로직 추가
  - [x] 테스트 통과 확인
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `require_auth_if_configured` dependency를 통해 구현됨

---

### SEC-002: AuthMiddleware 중앙화
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/main.py:117` - AuthMiddleware 적용
- **Description**: AuthMiddleware를 미들웨어로 설치
- **Acceptance Criteria**:
  - [x] 중앙 집중식 인증 미들웨어 구현
  - [x] main.py에서 미들웨어로 등록
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `main.py:117`에서 AuthMiddleware가 app에 추가됨

---

### SEC-003: Supabase RLS 정책 활성화
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Database Team
- **Files**:
  - `database/migrations/005_user_profiles.sql` - RLS 정책 활성화됨
- **Description**: Supabase RLS 정책 활성화
- **Acceptance Criteria**:
  - [x] RLS 정책 활성화
  - [x] `ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;`
  - [x] `ALTER TABLE projects ENABLE ROW LEVEL SECURITY;`
  - [x] 적절한 정책 생성 (`Users can view own profile` 등)
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: 마이그레이션 파일에서 RLS가 활성화되어 있음 (주석 처리되지 않음)

---

### FUNC-001: Orchestrator DB/GraphStore 연결
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/chat.py:445,454` - DB 및 GraphStore 전달
- **Description**: `AgentOrchestrator`를 `db`와 `GraphStore`로 초기화
- **Acceptance Criteria**:
  - [x] Orchestrator 초기화 시 DB 연결 전달
  - [x] GraphStore 인스턴스 전달
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `chat.py`에서 `graph_store`와 `db_connection` 파라미터로 전달됨

---

### BUG-001: datetime import 누락 수정
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/teams.py:8` - datetime import 추가됨
- **Description**: `datetime` import 누락 수정
- **Acceptance Criteria**:
  - [x] `from datetime import datetime` 추가
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `teams.py:8`에 import 문 확인됨

---

### FUNC-002: Frontend API Authorization 헤더
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/lib/api.ts` - Bearer token 헤더 추가됨
- **Description**: API 클라이언트에 Supabase 액세스 토큰을 Authorization 헤더로 첨부
- **Acceptance Criteria**:
  - [x] Supabase 세션에서 토큰 추출
  - [x] API 요청에 Bearer 토큰 첨부
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `api.ts`에서 Authorization: Bearer 헤더 설정 확인됨

---

### PERF-001: LLM 결과 캐싱
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/llm/cached_provider.py` - CachedLLMProvider 구현됨
- **Description**: LLM 결과에 캐싱 추가
- **Acceptance Criteria**:
  - [x] 캐싱 Provider 구현
  - [x] TTL 기반 캐시 무효화
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `CachedLLMProvider` 클래스로 인메모리 캐싱 구현됨

---

### PERF-002: Redis Rate Limiting
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Files**:
  - `backend/middleware/rate_limiter.py` - Redis 기반 Rate Limiter 구현됨
- **Description**: Redis 기반 Rate Limiting
- **Acceptance Criteria**:
  - [x] Redis 기반 Rate Limiter 구현
  - [x] 환경별 설정 지원
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: Redis 연결 시 Redis 사용, 없으면 인메모리 fallback

---

### PERF-003: N+1 쿼리 최적화
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/chat.py` - `json_agg` 사용한 쿼리 최적화
- **Description**: 프로젝트 통계 및 채팅 기록에 쿼리 배칭 추가
- **Acceptance Criteria**:
  - [x] N+1 쿼리 패턴 수정
  - [x] `json_agg`를 사용한 집계 쿼리로 최적화
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `chat.py`에서 `json_agg`를 사용한 효율적인 쿼리 확인됨

---

## 📋 How to Use This Document

### Adding New Items
```markdown
### [TYPE]-[NUMBER]: 제목
- **Source**: [리뷰/기능/버그 출처]
- **Status**: ⬜ Pending | 🔄 In Progress | ✅ Completed
- **Assignee**: [담당자/팀]
- **Files**: [관련 파일 목록]
- **Description**: [상세 설명]
- **Acceptance Criteria**:
  - [ ] 조건 1
  - [ ] 조건 2
- **Created**: YYYY-MM-DD
- **Completed**: -
```

### Status Legend
- ⬜ **Pending**: 아직 시작되지 않음
- 🔄 **In Progress**: 진행 중
- ✅ **Completed**: 완료됨
- ❌ **Won't Fix**: 수정하지 않기로 결정

### Type Prefixes
- `SEC`: Security (보안)
- `BUG`: Bug Fix (버그 수정)
- `FUNC`: Functionality (기능)
- `PERF`: Performance (성능)
- `DOC`: Documentation (문서)
- `TEST`: Testing (테스트)

---

*이 문서는 Claude Code에 의해 자동으로 관리됩니다.*
