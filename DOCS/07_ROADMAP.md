# 개발 로드맵

## 버전 계획

| 버전 | 목표 | 주요 기능 |
|------|------|-----------|
| **v0.1.0** | MVP 완성 | 기본 기능 동작 |
| **v0.2.0** | 안정화 | 테스트, 에러 핸들링 |
| **v0.3.0** | 기능 확장 | 고급 시각화, 분석 |
| **v1.0.0** | Production | 성능 최적화, 모니터링 |

---

## 단기 목표 (1주)

### v0.1.0 MVP 완성

```
[████████░░░░░░░░░░░░░░░░░] 35%
```

#### Week 1 Tasks

**Day 1-2: Database 연동**

| Task | 우선순위 | 예상 난이도 |
|------|----------|-------------|
| Render PostgreSQL 인스턴스 생성 | 최상 | 낮음 |
| pgvector 확장 활성화 | 최상 | 낮음 |
| 마이그레이션 스크립트 실행 | 최상 | 중간 |
| DATABASE_URL 환경 변수 설정 | 최상 | 낮음 |

```bash
# 실행 명령
psql $DATABASE_URL < migrations/001_base_tables.sql
psql $DATABASE_URL < migrations/002_extensions.sql
psql $DATABASE_URL < migrations/003_graph_tables.sql
```

**Day 3-4: Backend 완성**

| Task | 우선순위 | 예상 난이도 |
|------|----------|-------------|
| asyncpg 연결 풀 구현 | 최상 | 중간 |
| graph_store.py DB 메서드 구현 | 최상 | 높음 |
| Query Execution Agent 연동 | 상 | 중간 |

```python
# 핵심 구현 파일
backend/database.py       # asyncpg 연결 풀
backend/graph_store.py    # CRUD 메서드
backend/agents/query_execution_agent.py  # DB 연동
```

**Day 5-7: 통합 및 테스트**

| Task | 우선순위 | 예상 난이도 |
|------|----------|-------------|
| Frontend-Backend API 연동 확인 | 상 | 중간 |
| 데모 데이터 Import 테스트 | 상 | 낮음 |
| 기본 채팅 흐름 테스트 | 상 | 중간 |
| 버그 수정 | 상 | 가변 |

---

## 중기 목표 (1개월)

### v0.2.0 안정화

```
Phase 1: 테스트 코드 작성 (Week 2)
Phase 2: 에러 핸들링 강화 (Week 3)
Phase 3: 성능 기초 최적화 (Week 4)
```

#### 테스트 코드

| 영역 | 도구 | 목표 커버리지 |
|------|------|---------------|
| Backend 단위 테스트 | pytest | 70% |
| Frontend 테스트 | Jest | 60% |
| API 통합 테스트 | pytest + httpx | 80% |
| E2E 테스트 | Playwright | 주요 흐름 |

```python
# 테스트 구조
backend/tests/
├── test_agents/
│   ├── test_intent_agent.py
│   ├── test_concept_extraction_agent.py
│   └── test_orchestrator.py
├── test_routers/
│   ├── test_projects.py
│   ├── test_graph.py
│   └── test_chat.py
└── test_graph_store.py
```

#### 에러 핸들링

| 항목 | 내용 |
|------|------|
| API 예외 처리 | HTTPException + 상세 메시지 |
| DB 연결 실패 | 재시도 로직 |
| LLM API 실패 | Fallback 강화 |
| 클라이언트 에러 | Toast 알림 |

#### 성능 기초

| 항목 | 목표 |
|------|------|
| API 응답 시간 | < 2초 (p95) |
| 그래프 렌더링 | < 1초 (500 노드) |
| LLM 응답 | < 5초 |

---

## 장기 목표 (3개월)

### v0.3.0 기능 확장

#### 고급 시각화

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| Force-Directed 레이아웃 | d3-force 또는 elkjs 통합 | 상 |
| 클러스터링 | 동일 주제 그룹화 | 중 |
| 시간 기반 애니메이션 | 연도별 변화 시각화 | 중 |
| PNG/SVG 내보내기 | 그래프 이미지 저장 | 중 |

```typescript
// Force-Directed 레이아웃 예시
import { forceSimulation, forceLink, forceManyBody } from 'd3-force';

function forceDirectedLayout(nodes: Node[], edges: Edge[]): Node[] {
  const simulation = forceSimulation(nodes)
    .force('link', forceLink(edges).id(d => d.id))
    .force('charge', forceManyBody().strength(-300))
    .force('center', forceCenter(400, 300));

  simulation.tick(300);
  return nodes.map(node => ({
    ...node,
    position: { x: node.x, y: node.y },
  }));
}
```

#### 고급 분석

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 연구 트렌드 분석 | 시간별 키워드 변화 | 상 |
| 저자 네트워크 분석 | 공동 연구 패턴 | 중 |
| 인용 네트워크 분석 | 영향력 측정 | 중 |
| 자동 요약 | 논문 클러스터 요약 | 하 |

#### UX 개선

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| 응답 스트리밍 | SSE로 실시간 응답 | 상 |
| 다크 모드 | 테마 전환 | 중 |
| 키보드 단축키 | 효율적 탐색 | 중 |
| 다국어 지원 | 한국어/영어 | 하 |

---

### v1.0.0 Production

#### 성능 최적화

| 항목 | 목표 | 방법 |
|------|------|------|
| DB 쿼리 최적화 | < 100ms | 인덱스 튜닝, 쿼리 리팩토링 |
| 캐싱 | Hit rate 80%+ | Redis 또는 인메모리 |
| 번들 최적화 | < 200KB (초기) | 코드 스플리팅 |
| 이미지 최적화 | < 50KB | WebP, lazy loading |

#### 모니터링

| 도구 | 용도 |
|------|------|
| Sentry | 에러 추적 |
| Render Metrics | 서버 성능 |
| Vercel Analytics | 프론트엔드 성능 |
| Custom Logging | 사용자 행동 분석 |

#### 보안

| 항목 | 내용 |
|------|------|
| 인증 | JWT 또는 OAuth |
| Rate Limiting | API 호출 제한 |
| Input Validation | XSS, SQL Injection 방지 |
| HTTPS | 전송 암호화 |

---

## 마일스톤

### Milestone 1: MVP Demo (v0.1.0)

- [ ] 데이터베이스 연동 완료
- [ ] 기본 Import → 시각화 → 채팅 흐름 동작
- [ ] 데모 영상 제작

### Milestone 2: Beta Release (v0.2.0)

- [ ] 테스트 커버리지 70%+
- [ ] 주요 버그 수정
- [ ] 사용자 피드백 수집

### Milestone 3: Feature Complete (v0.3.0)

- [ ] Force-Directed 레이아웃
- [ ] 연구 트렌드 분석
- [ ] 응답 스트리밍

### Milestone 4: Production (v1.0.0)

- [ ] 성능 최적화 완료
- [ ] 모니터링 설정
- [ ] 문서화 완료
- [ ] 정식 출시

---

## 기술 부채 관리

### 현재 기술 부채

| 항목 | 영향도 | 해결 계획 |
|------|--------|-----------|
| Graph Store 인터페이스만 존재 | 높음 | v0.1.0에서 해결 |
| 테스트 코드 없음 | 중간 | v0.2.0에서 해결 |
| 에러 핸들링 미흡 | 중간 | v0.2.0에서 해결 |
| 하드코딩된 값들 | 낮음 | v0.3.0에서 해결 |

### 리팩토링 계획

```
v0.2.0:
- [ ] 중복 코드 제거
- [ ] 타입 안전성 강화
- [ ] 에러 타입 표준화

v0.3.0:
- [ ] 컴포넌트 구조 개선
- [ ] 상태 관리 최적화
- [ ] API 클라이언트 추상화
```

---

## 의존성 업데이트 계획

| 패키지 | 현재 | 목표 | 시기 |
|--------|------|------|------|
| React Flow | 11.10.0 | 최신 | v0.3.0 |
| FastAPI | 0.104+ | 최신 | v0.2.0 |
| asyncpg | 추가 필요 | 최신 | v0.1.0 |
| Next.js | 14.x | 15.x | v1.0.0 |

---

## 리소스 계획

### 예상 비용 (월간)

| 서비스 | 플랜 | 비용 |
|--------|------|------|
| Render PostgreSQL | Starter | $7 |
| Render Web Service | Starter | $7 |
| Vercel | Hobby | $0 |
| Anthropic API | Pay-as-you-go | ~$10-50 |
| **합계** | | **~$24-64** |

### Production 예상 비용

| 서비스 | 플랜 | 비용 |
|--------|------|------|
| Render PostgreSQL | Standard | $25 |
| Render Web Service | Standard | $25 |
| Vercel | Pro | $20 |
| Anthropic API | Pay-as-you-go | ~$50-200 |
| **합계** | | **~$120-270** |

---

## 참고 문서

- [06_PROGRESS_TRACKER.md](./06_PROGRESS_TRACKER.md) - 현재 진행 상황
- [00_OVERVIEW.md](./00_OVERVIEW.md) - 프로젝트 개요
- [AGENTiGraph Paper](https://arxiv.org/abs/2410.11531) - 참고 아키텍처
