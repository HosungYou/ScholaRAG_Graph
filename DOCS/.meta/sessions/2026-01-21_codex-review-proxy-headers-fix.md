# Session Log: Codex Review - BUG-019 Proxy Headers Fix

> **Session ID**: 2026-01-21_codex-review-proxy-headers-fix
> **Date**: 2026-01-21
> **Agent**: Claude Code (Opus 4.5) + Codex CLI (gpt-5.2-codex)
> **Type**: Root Cause Analysis / Critical Bug Fix
> **Duration**: ~45 minutes
> **Skills Used**: `/review` (code-reviewer skill), `superpowers:systematic-debugging`

---

## Context

### User Request
BUG-015~018 수정에도 불구하고 동일한 Mixed Content 에러가 계속 발생. 다른 접근법/방법론을 통해 근본 원인 파악 요청. `/review` 커맨드로 코드 리뷰 실행.

### Screenshots Provided
1. **프로젝트 뷰**: Mixed Content 에러 - `http://scholarag-graph-docker.onrender.com/api/projects/`
2. **프로젝트 목록**: "Failed to load projects" + 다수의 API 재시도 에러

### Key Observation
에러 URL이 `http://scholarag-graph-docker.onrender.com` - **HTTP**임에도 불구하고:
- 환경변수는 HTTPS로 설정됨 (이전 브라우저 자동화로 확인)
- `enforceHttps()` 함수가 api.ts에 존재
- vercel.json도 HTTPS URL 사용

→ **이전과는 다른 접근이 필요**

---

## Methodology: Codex CLI Review

### Tool Selection
- **Codex CLI** (`codex exec -m gpt-5.2-codex`)
- 전체 코드베이스를 분석하여 숨겨진 근본 원인 탐색

### Review Prompt
```
Conduct a comprehensive code review focused on the RECURRING BUG:
- Mixed Content Error persists after BUG-015/016/017/018 fixes
- Find ALL places where API URLs are constructed
- Check if enforceHttps() is actually being called
- Verify environment variable usage
- Check for build-time vs runtime URL resolution
- Look for any HTTP hardcoding
```

---

## Root Cause Discovery

### Codex Analysis Results

**Executive Summary** (Codex):
> The mixed‑content error is caused by FastAPI redirecting `/api/projects` → `/api/projects/` using the **wrong scheme (http)** because the backend doesn't trust proxy headers behind Render's TLS termination.

### The REAL Root Cause

```
┌─────────────────────────────────────────────────────────────────┐
│                    요청 흐름 분석                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 프론트엔드: GET /api/projects (trailing slash 없음)         │
│                                                                 │
│  2. Render Load Balancer                                        │
│     - 클라이언트 ↔ LB: HTTPS                                    │
│     - LB ↔ 컨테이너: HTTP (TLS termination)                     │
│     - X-Forwarded-Proto: https 헤더 추가                        │
│                                                                 │
│  3. Uvicorn                                                     │
│     - --proxy-headers 옵션 없음!                                │
│     - X-Forwarded-Proto 헤더 무시                               │
│     - scope["scheme"] = "http" 로 인식                          │
│                                                                 │
│  4. FastAPI Router                                              │
│     - @router.get("/") 정의 (trailing slash 필요)               │
│     - /api/projects → /api/projects/ 리다이렉트 발생            │
│     - Location: http://scholarag-graph-docker.onrender.com/...  │
│                                                                 │
│  5. 브라우저                                                     │
│     - HTTPS 페이지에서 HTTP 리소스 요청                         │
│     - Mixed Content 에러!                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why Previous Fixes Failed

| Bug Fix | Why It Failed |
|---------|---------------|
| **BUG-015** (system.py) | DB 커넥션 문제 - URL/프록시와 완전 무관 |
| **BUG-016** (enforceHttps SSR) | 클라이언트 base URL만 수정. **백엔드 리다이렉트 URL은 여전히 HTTP** |
| **BUG-017** (ImportError) | 모듈 임포트 에러 - URL과 무관 |
| **BUG-018** (vercel.json) | 상대 경로 `/api/*` 용. **절대 URL 사용 시 적용 안됨** |

### Key Insight
> **프론트엔드만 수정해서는 해결 불가. 백엔드가 프록시 환경을 인식해야 함.**

---

## Resolution

### BUG-019: Uvicorn Proxy Headers 지원

#### 1. Dockerfile (핵심 수정)
```dockerfile
# 이전 (버그)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}

# 수정 후
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips="*"
```

**설명**:
- `--proxy-headers`: X-Forwarded-Proto, X-Forwarded-For 헤더 신뢰
- `--forwarded-allow-ips="*"`: 모든 프록시(Render LB) 신뢰

#### 2. frontend/lib/api.ts (방어적 수정)
```typescript
// 이전
async getProjects(): Promise<Project[]> {
  return this.request<Project[]>('/api/projects');
}

// 수정 후 - trailing slash로 리다이렉트 회피
async getProjects(): Promise<Project[]> {
  return this.request<Project[]>('/api/projects/');
}
```

#### 3. frontend/components/graph/StatusBar.tsx
```typescript
// 이전 - 로컬 정의 (enforceHttps 우회)
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// 수정 후 - 중앙화된 API_URL 사용
import { API_URL } from '@/lib/api';
```

---

## Commits

| Commit | Description |
|--------|-------------|
| `169dfb8` | fix(BUG-019): add proxy headers support for HTTPS redirects |
| `e09c7d6` | docs: add BUG-019 to action-items with root cause analysis from Codex |

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Tools Used | Codex CLI (gpt-5.2-codex), Claude Code |
| Review Type | Root Cause Analysis |
| Bugs Fixed | 1 (BUG-019 - 진짜 근본 원인) |
| Commits Made | 2 |
| Files Modified | 4 (Dockerfile, api.ts, StatusBar.tsx, action-items.md) |
| Tokens Used (Codex) | 76,167 |

---

## Key Learnings

### 1. TLS Termination과 Proxy Headers
클라우드 환경(Render, AWS ELB, Cloudflare 등)에서는 Load Balancer가 TLS를 종료하고 백엔드에 HTTP로 전달함. 백엔드는 반드시 `X-Forwarded-Proto` 헤더를 신뢰하도록 설정해야 함.

### 2. 증상 vs 근본 원인
- **증상**: Mixed Content 에러, CORS 에러
- **시도한 수정**: 프론트엔드 URL 수정, CORS 설정, vercel.json
- **근본 원인**: 백엔드 Uvicorn이 프록시 환경을 인식하지 못함

### 3. 다른 접근법의 가치
동일한 방법론(프론트엔드 수정)을 반복하지 않고, **Codex 리뷰**를 통해 전체 시스템을 분석하여 숨겨진 근본 원인 발견.

### 4. Trailing Slash와 FastAPI
FastAPI에서 `@router.get("/")` 정의 시, trailing slash 없는 요청은 자동 리다이렉트됨. 프록시 환경에서 이 리다이렉트가 HTTP URL을 생성하면 Mixed Content 발생.

---

## Related Documents

- `DOCS/project-management/action-items.md` - BUG-019 추가
- `DOCS/.meta/sessions/2026-01-21_brainstorming-vercel-url-fix.md` - 이전 세션
- `Dockerfile` - 핵심 수정 파일
- `frontend/lib/api.ts` - 방어적 수정
- `frontend/components/graph/StatusBar.tsx` - enforceHttps 우회 수정

---

## Verification Pending

- [ ] Render Docker 서비스 수동 재배포
- [ ] Mixed Content 에러 완전 해결 확인
- [ ] /api/projects 정상 응답 확인
