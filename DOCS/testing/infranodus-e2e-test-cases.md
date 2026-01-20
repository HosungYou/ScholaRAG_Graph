# InfraNodus E2E Test Cases

> **Version**: 0.4.0
> **Created**: 2026-01-20
> **Status**: Ready for Manual Testing

이 문서는 InfraNodus 통합 기능의 End-to-End 테스트 케이스를 정의합니다.

---

## Prerequisites

- [ ] 프로젝트에 최소 20개 이상의 노드가 있어야 함
- [ ] 시간 데이터가 있는 엔티티가 포함되어야 함 (publication_year 등)
- [ ] 구조적 갭이 감지된 상태여야 함
- [ ] 인증된 사용자로 로그인되어 있어야 함

---

## Test Suite 1: Contextual Edge Exploration (Phase 1)

### TC-1.1: Edge 클릭 → Modal 열기

**Steps:**
1. 프로젝트의 Knowledge Graph 페이지 접근
2. 그래프에서 임의의 Edge(연결선) 클릭
3. EdgeContextModal이 열리는지 확인

**Expected Results:**
- [ ] Modal이 화면 중앙에 나타남
- [ ] Source 노드 이름이 표시됨
- [ ] Target 노드 이름이 표시됨
- [ ] Relationship 타입이 표시됨

### TC-1.2: Evidence 목록 표시

**Steps:**
1. TC-1.1 수행 후 Modal 내용 확인
2. Evidence 목록이 로드되는지 확인

**Expected Results:**
- [ ] Evidence 항목들이 리스트로 표시됨
- [ ] 각 Evidence에 Paper 제목이 표시됨
- [ ] 각 Evidence에 연도가 표시됨
- [ ] 각 Evidence에 관련도 점수가 표시됨
- [ ] Context snippet이 표시됨

### TC-1.3: Modal 닫기

**Steps:**
1. Modal 외부 영역 클릭 또는 X 버튼 클릭
2. Modal이 닫히는지 확인

**Expected Results:**
- [ ] Modal이 즉시 닫힘
- [ ] 그래프 상태가 유지됨

---

## Test Suite 2: Temporal Graph Evolution (Phase 2)

### TC-2.1: Temporal Slider 토글

**Steps:**
1. Knowledge Graph 페이지 접근
2. 상단 툴바의 Clock 아이콘(⏰) 클릭
3. TemporalSlider가 나타나는지 확인

**Expected Results:**
- [ ] TemporalSlider가 화면 하단 중앙에 나타남
- [ ] 현재 연도가 표시됨
- [ ] 연도 범위(min-max)가 올바르게 표시됨
- [ ] 재생/일시정지 버튼이 있음

### TC-2.2: 연도별 노드 필터링

**Steps:**
1. TemporalSlider 활성화
2. 슬라이더를 과거 연도로 이동
3. 그래프의 노드 수 변화 확인

**Expected Results:**
- [ ] 슬라이더 이동 시 노드 수가 변화함
- [ ] 선택된 연도 이후에 등장한 노드는 숨겨짐
- [ ] Edge도 함께 필터링됨 (양쪽 노드가 없으면 숨김)
- [ ] 노드/엣지 카운트가 업데이트됨

### TC-2.3: 애니메이션 재생/정지

**Steps:**
1. TemporalSlider의 재생 버튼(▶) 클릭
2. 애니메이션 작동 확인
3. 일시정지 버튼(⏸) 클릭

**Expected Results:**
- [ ] 재생 시 연도가 자동으로 증가함
- [ ] 그래프가 실시간으로 업데이트됨
- [ ] 일시정지 시 애니메이션이 즉시 멈춤
- [ ] 최대 연도 도달 시 처음으로 루프함

### TC-2.4: 애니메이션 속도 조절

**Steps:**
1. 속도 버튼(1x) 클릭
2. 다른 속도(0.5x, 2x, 4x) 선택
3. 애니메이션 재생

**Expected Results:**
- [ ] 선택한 속도가 UI에 표시됨
- [ ] 실제 애니메이션 속도가 변경됨
- [ ] 0.5x: 느림, 4x: 빠름

### TC-2.5: Skip to Start/End

**Steps:**
1. Skip to End(⏭) 버튼 클릭
2. Skip to Start(⏮) 버튼 클릭

**Expected Results:**
- [ ] ⏭ 클릭 시 최대 연도로 이동
- [ ] ⏮ 클릭 시 최소 연도로 이동
- [ ] 그래프가 즉시 업데이트됨

### TC-2.6: Histogram 표시

**Steps:**
1. TemporalSlider의 히스토그램 영역 확인
2. 마우스를 특정 막대 위에 올림

**Expected Results:**
- [ ] 연도별 노드 수가 막대 그래프로 표시됨
- [ ] 현재 연도까지의 막대는 색상이 채워짐
- [ ] 툴팁에 해당 연도의 노드 수가 표시됨

---

## Test Suite 3: AI Bridge Generation (Phase 3)

### TC-3.1: GapPanel에서 Bridge 생성

**Steps:**
1. GapPanel 열기 (✨ 버튼)
2. 구조적 갭 항목에서 "Generate Bridge Ideas" 버튼 클릭
3. 결과 확인

**Expected Results:**
- [ ] 로딩 인디케이터가 표시됨
- [ ] 생성된 가설(hypothesis)이 카드로 표시됨
- [ ] 각 가설에 confidence 점수가 표시됨
- [ ] Supporting evidence가 표시됨

### TC-3.2: Bridge Hypothesis 상세 보기

**Steps:**
1. 생성된 Bridge Hypothesis 카드 클릭
2. 상세 정보 확인

**Expected Results:**
- [ ] 가설 전문이 표시됨
- [ ] 추천 검색어가 표시됨
- [ ] 관련 논문 목록이 표시됨

---

## Test Suite 4: Diversity Index (Phase 4)

### TC-4.1: InsightHUD 다양성 게이지

**Steps:**
1. Knowledge Graph 페이지 접근
2. InsightHUD의 Diversity 섹션 확인

**Expected Results:**
- [ ] 다양성 게이지가 표시됨
- [ ] Shannon Entropy 값이 표시됨
- [ ] Gini Coefficient 값이 표시됨
- [ ] Diversity Rating(Excellent/Good/Fair/Poor)이 표시됨

### TC-4.2: 다양성 상세 정보

**Steps:**
1. Diversity 게이지 클릭 또는 확장 버튼 클릭
2. 상세 정보 확인

**Expected Results:**
- [ ] Cluster 분포가 표시됨
- [ ] Entity type 분포가 표시됨
- [ ] Bias 분석 결과가 표시됨
- [ ] 권장사항이 표시됨

---

## Test Suite 5: Graph Comparison Mode (Phase 5)

### TC-5.1: 비교 페이지 접근

**Steps:**
1. `/projects/compare` 페이지 접근
2. 두 개의 프로젝트 선택

**Expected Results:**
- [ ] 프로젝트 선택 UI가 표시됨
- [ ] 사용자의 프로젝트 목록이 로드됨
- [ ] 두 프로젝트를 선택할 수 있음

### TC-5.2: 비교 결과 표시

**Steps:**
1. 두 프로젝트 선택 후 "Compare" 클릭
2. 비교 결과 확인

**Expected Results:**
- [ ] Jaccard Similarity가 표시됨
- [ ] Overlap Coefficient가 표시됨
- [ ] Venn 다이어그램이 표시됨
- [ ] 공유 엔티티 목록이 표시됨

### TC-5.3: Venn 다이어그램 상호작용

**Steps:**
1. Venn 다이어그램의 영역(A only, B only, intersection) 클릭
2. 해당 영역의 상세 정보 확인

**Expected Results:**
- [ ] 클릭한 영역이 하이라이트됨
- [ ] 해당 영역의 엔티티 목록이 표시됨
- [ ] 엔티티 개수가 표시됨

---

## Test Suite 6: Cross-Feature Integration

### TC-6.1: Temporal + Gap Detection

**Steps:**
1. TemporalSlider를 과거 연도로 설정
2. GapPanel 열기
3. 갭 분석 결과 확인

**Expected Results:**
- [ ] 해당 연도 기준의 갭이 표시됨
- [ ] 미래 노드가 제외된 상태에서 갭 계산됨

### TC-6.2: Edge Click + Temporal

**Steps:**
1. TemporalSlider 활성화
2. 과거 연도로 설정
3. Edge 클릭

**Expected Results:**
- [ ] Modal에 해당 시점까지의 Evidence만 표시됨
- [ ] 미래 논문의 Evidence는 제외됨

---

## Bug Report Template

테스트 중 발견된 버그는 아래 형식으로 보고:

```markdown
## Bug Report

**Test Case**: TC-X.X
**Date**: YYYY-MM-DD
**Tester**: [Name]

### Description
[버그 설명]

### Steps to Reproduce
1. ...
2. ...
3. ...

### Expected Result
[기대 결과]

### Actual Result
[실제 결과]

### Screenshots
[스크린샷 첨부]

### Environment
- Browser: Chrome/Firefox/Safari
- OS: macOS/Windows/Linux
- Screen Size: 1920x1080
```

---

## Test Completion Checklist

| Suite | Total | Passed | Failed | Blocked |
|-------|-------|--------|--------|---------|
| 1. Edge Exploration | 3 | - | - | - |
| 2. Temporal Evolution | 6 | - | - | - |
| 3. Bridge Generation | 2 | - | - | - |
| 4. Diversity Index | 2 | - | - | - |
| 5. Graph Comparison | 3 | - | - | - |
| 6. Integration | 2 | - | - | - |
| **Total** | **18** | - | - | - |

**Test Sign-off**:
- [ ] All critical tests passed
- [ ] No critical/high severity bugs open
- [ ] Performance acceptable

**Tested by**: _______________
**Date**: _______________
