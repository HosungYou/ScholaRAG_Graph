# Frontend 서비스 스펙 (Vercel/Next.js)

## 서비스 개요

| 항목 | 내용 |
|------|------|
| **역할** | 사용자 인터페이스, 그래프 시각화, 챗봇 UI |
| **프레임워크** | Next.js 14 (App Router) |
| **배포 플랫폼** | Vercel |
| **URL** | https://scholarag-graph.vercel.app |

---

## 기술 스택

```json
{
  "next": "14.1.0",
  "react": "^18.2.0",
  "reactflow": "^11.10.0",
  "@tanstack/react-query": "^5.17.0",
  "zustand": "^4.5.0",
  "tailwindcss": "^3.4.1",
  "typescript": "^5.3.3",
  "lucide-react": "^0.312.0"
}
```

---

## 디렉토리 구조

```
frontend/
├── app/
│   ├── layout.tsx           # 루트 레이아웃
│   ├── page.tsx             # 랜딩 페이지
│   ├── providers.tsx        # Client-side 프로바이더
│   ├── globals.css          # 전역 스타일
│   ├── projects/
│   │   ├── page.tsx         # 프로젝트 목록
│   │   └── [id]/
│   │       └── page.tsx     # 프로젝트 상세 (Dual-Mode)
│   └── import/
│       └── page.tsx         # ScholaRAG Import UI
├── components/
│   ├── graph/
│   │   ├── KnowledgeGraph.tsx   # React Flow 메인 컴포넌트
│   │   ├── CustomNode.tsx       # 커스텀 노드 렌더러
│   │   ├── FilterPanel.tsx      # 필터링 패널
│   │   ├── SearchBar.tsx        # 검색 바
│   │   └── NodeDetails.tsx      # 노드 상세 패널
│   └── chat/
│       └── ChatInterface.tsx    # 채팅 인터페이스
├── hooks/
│   └── useGraphStore.tsx        # Zustand 그래프 스토어
├── lib/
│   └── utils.ts                 # 유틸리티 함수
└── vercel.json                  # Vercel 배포 설정
```

---

## 페이지별 스펙

### 1. 랜딩 페이지 (`/`)

| 항목 | 상태 | 설명 |
|------|------|------|
| Hero 섹션 | ✅ 완료 | 프로젝트 소개 |
| Feature 카드 | ✅ 완료 | 3가지 핵심 기능 |
| CTA 버튼 | ✅ 완료 | Import 시작 |
| 네비게이션 | ✅ 완료 | 헤더 메뉴 |

### 2. 프로젝트 목록 (`/projects`)

| 항목 | 상태 | 설명 |
|------|------|------|
| 프로젝트 카드 | ⚠️ 부분 | UI 완료, API 연동 필요 |
| 생성 버튼 | ⚠️ 부분 | UI 완료, API 연동 필요 |
| 검색/필터 | ❌ 미구현 | 추후 개발 |

### 3. 프로젝트 상세 (`/projects/[id]`)

| 항목 | 상태 | 설명 |
|------|------|------|
| Dual-Mode 토글 | ✅ 완료 | Chat/Split/Explore 모드 |
| Graph 패널 | ✅ 완료 | React Flow 통합 |
| Chat 패널 | ✅ 완료 | ChatInterface 컴포넌트 |
| API 연동 | ⚠️ 부분 | 엔드포인트 연결 필요 |

### 4. Import 페이지 (`/import`)

| 항목 | 상태 | 설명 |
|------|------|------|
| 폴더 선택 UI | ⚠️ 부분 | 기본 구조 |
| 진행률 표시 | ❌ 미구현 | WebSocket 연동 필요 |
| 결과 미리보기 | ❌ 미구현 | 추후 개발 |

---

## 컴포넌트 상세

### KnowledgeGraph.tsx

```typescript
interface KnowledgeGraphProps {
  nodes: Node[];
  edges: Edge[];
  onNodeClick?: (node: Node) => void;
  highlightedNodes?: string[];
  highlightedEdges?: string[];
}
```

| 기능 | 상태 | 설명 |
|------|------|------|
| 노드 렌더링 | ✅ 완료 | 5가지 엔티티 타입 |
| 엣지 렌더링 | ✅ 완료 | 관계 시각화 |
| 줌/패닝 | ✅ 완료 | React Flow 내장 |
| 미니맵 | ✅ 완료 | 전체 보기 |
| 하이라이트 | ✅ 완료 | 선택/검색 결과 강조 |
| 레이아웃 | ⚠️ 부분 | 그리드 + 랜덤 (Force-directed 필요) |

### FilterPanel.tsx

```typescript
interface FilterPanelProps {
  entityTypes: string[];
  selectedTypes: string[];
  onTypeChange: (types: string[]) => void;
  yearRange?: [number, number];
  onYearRangeChange?: (range: [number, number]) => void;
}
```

| 기능 | 상태 |
|------|------|
| 엔티티 타입 필터 | ✅ 완료 |
| 연도 범위 필터 | ✅ 완료 |
| All/None 토글 | ✅ 완료 |

### ChatInterface.tsx

```typescript
interface ChatInterfaceProps {
  projectId: string;
  onSendMessage: (message: string) => Promise<ChatResponse>;
  onCitationClick?: (citation: string) => void;
  initialMessages?: Message[];
}
```

| 기능 | 상태 |
|------|------|
| 메시지 표시 | ✅ 완료 |
| 입력 필드 | ✅ 완료 |
| 추천 질문 | ✅ 완료 |
| 인용 클릭 | ✅ 완료 |
| 로딩 상태 | ✅ 완료 |
| 복사 기능 | ✅ 완료 |

---

## 상태 관리 (Zustand)

### useGraphStore

```typescript
interface GraphStore {
  nodes: Node[];
  edges: Edge[];
  selectedNode: Node | null;
  highlightedNodes: string[];
  highlightedEdges: string[];
  filters: {
    entityTypes: string[];
    yearRange: [number, number];
  };
  // Actions
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  selectNode: (node: Node | null) => void;
  setHighlights: (nodes: string[], edges: string[]) => void;
  updateFilters: (filters: Partial<Filters>) => void;
}
```

| 항목 | 상태 |
|------|------|
| 스토어 정의 | ✅ 완료 |
| 노드/엣지 관리 | ✅ 완료 |
| 필터 상태 | ✅ 완료 |
| API 연동 | ⚠️ 부분 |

---

## 환경 변수

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000        # 로컬
NEXT_PUBLIC_API_URL=https://scholarag-graph-api.onrender.com  # 프로덕션
```

---

## Vercel 배포 설정

```json
// vercel.json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "env": {
    "NEXT_PUBLIC_API_URL": "@api_url"
  },
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://scholarag-graph-api.onrender.com/api/:path*"
    }
  ]
}
```

---

## 구현 진행률

### 전체: 85%

```
[██████████████████░░░░░░] 85%
```

| 카테고리 | 진행률 | 상태 |
|----------|--------|------|
| 페이지 구조 | 100% | ✅ |
| 컴포넌트 | 95% | ✅ |
| 스타일링 | 90% | ✅ |
| 상태 관리 | 80% | ⚠️ |
| API 연동 | 50% | ⚠️ |
| 테스트 | 0% | ❌ |

---

## 향후 요구사항

### 우선순위 높음
- [ ] API 엔드포인트 완전 연동
- [ ] 에러 핸들링 강화
- [ ] 로딩 스켈레톤 추가

### 우선순위 중간
- [ ] Force-directed 레이아웃 알고리즘
- [ ] 그래프 내보내기 (PNG/SVG)
- [ ] 다크 모드

### 우선순위 낮음
- [ ] E2E 테스트 (Playwright)
- [ ] 접근성 개선
- [ ] PWA 지원

---

## 의존성

| 서비스 | 의존 관계 |
|--------|----------|
| Backend API | 모든 데이터 CRUD |
| LLM Provider | 챗봇 응답 (Backend 경유) |
