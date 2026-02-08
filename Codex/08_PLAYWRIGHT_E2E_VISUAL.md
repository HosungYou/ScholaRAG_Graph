# Playwright E2E + Visual Regression Guide

## 목적

코어 기능을 유지하면서 프론트 핵심 흐름(그래프 상호작용/갭 패널/임포트 상태)의 브라우저 회귀를 자동 검증한다.

## 테스트 구성

1. 상호작용 회귀
   - 파일: `frontend/e2e/graph-interactions.spec.ts`
   - 시나리오:
     - pin/unpin (drag 시뮬레이션)
     - camera reset
     - gap focus

2. 시각 회귀
   - 파일: `frontend/e2e/visual-regression.spec.ts`
   - baseline:
     - `gap-panel-expanded.png`
     - `import-progress-completed.png`
     - `import-progress-interrupted.png`
     - `graph3d-shell.png`
     - `knowledge-graph3d-shell.png`

3. QA 라우트
   - 경로: `frontend/app/qa/e2e/page.tsx`
   - 목적: 백엔드 의존성 없이 결정론적 fixture를 렌더링
   - 시나리오 파라미터:
     - `?scenario=knowledge`
     - `?scenario=graph3d`
     - `?scenario=gap-panel`
     - `?scenario=import-completed`
     - `?scenario=import-interrupted`

## 실행 명령

```bash
make test-frontend-e2e
make test-frontend-visual
```

## baseline 갱신

```bash
cd frontend
npx playwright test -c playwright.config.ts e2e/visual-regression.spec.ts --update-snapshots
```

## CI 연동

1. PR triage gate: `.github/workflows/ci.yml` `snapshot-triage` 잡
2. PR E2E/Visual gate: `.github/workflows/ci.yml` `frontend-e2e-visual` 잡
3. PR 템플릿 체크리스트: `.github/pull_request_template.md`
