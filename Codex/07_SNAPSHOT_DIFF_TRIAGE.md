# Snapshot Diff Triage Procedure

## 목표

스냅샷 diff 발생 시 `허용 가능한 변경`과 `회귀`를 빠르게 분리하고, 의사결정을 로그로 남긴다.

## 트리아지 단계

1. `make test-frontend-core` 실행으로 diff 재현
2. 변경 파일을 4개 축으로 분류
   - 데이터 매핑 변경
   - 컴포넌트 레이아웃 변경
   - 카피/문구 변경
   - 테스트 목(mock) 변경
3. 아래 기준으로 판정
   - `Accept`: 제품 의도 변경 + 관련 기능 테스트 통과
   - `Fix`: 의도 없는 구조/신뢰성 신호 손실
   - `Split`: 의도 변경과 비의도 변경이 섞여 있는 경우 분리 커밋
4. 판정 근거를 `Codex/02_EXECUTION_LOG.md`에 기록
5. `Accept`일 때만 스냅샷 갱신 확정

## PR 라벨 매핑 (CI Gate)

- `Accept` 판정: `snapshot:accept`
- `Fix` 판정: `snapshot:fix`
- `Split` 판정: `snapshot:split`

## 회귀 판정 규칙

- 즉시 회귀로 판정
  - low-trust/근거/정규화 관련 UI 신호가 사라짐
  - Import 상태 전이(completed/interrupted) 핵심 문구 누락
  - Graph 뷰 모드 제어 UI가 누락됨
- 조건부 회귀
  - 시각 구조 변경은 의도 문서/설계서(SDD)와 일치할 때만 허용
  - mock 계약 필드 제거는 API 타입 변경 근거가 있을 때만 허용

## 실행 명령

```bash
make test-frontend-core
make test-all-core
```

## 기록 템플릿

```md
### [시간] Snapshot Triage
- 대상: <test file>
- 분류: <data-mapping | layout | copy | mock>
- 판정: <Accept | Fix | Split>
- 근거: <1-3줄>
- 후속 조치: <테스트/코드/문서>
```
