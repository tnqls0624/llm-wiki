---
description: 중대·되돌리기 어려운 결정에 회의를 소집한다 — 관련 직원 에이전트 병렬 의견수렴 → 비판가가 깸 → 종합 → 사람 결정 → decisions.md 기록
argument-hint: <프로젝트 slug> | <안건>
---

# council: 중대 결정 회의

안건: `$ARGUMENTS` (형식: `<프로젝트 slug> | <결정할 안건>`)

되돌리기 비싼 결정(아이디어 채택, MVP 스코프, 피벗, 프로젝트 중단)에만 쓴다. 일상 작업(리서치 한 건, 카피 초안)은 회의 없이 해당 직원에게 바로 위임하라 — 이 커맨드는 과설계 방지를 위해 "비싼 결정" 전용이다. **결정은 사람이 한다 — 회의는 권고까지.**

## 1. 안건·맥락 로드
- `$ARGUMENTS`에서 프로젝트 slug와 안건을 분리한다. `Projects/<slug>/`의 `plan.md`·`decisions.md`·`progress.md`·`research/`를 읽어 현재 상태·과거 결정·열린 질문을 파악한다.
- (선택) `founder-chief-of-staff`(`subagent_type: founder-chief-of-staff`)에 "이 안건에 누구를 부를지" 라우팅 판단을 받는다.

## 2. 의견 수렴 (병렬 fan-out)
- 안건에 관련된 직원 에이전트들을 **병렬로** Task 호출한다(`Agent` tool 다중 호출 — 이 vault의 'N authors ∥' 패턴). 안건별 통상 조합:
  - 도메인/아이디어 채택 → `market-researcher` + `product-pm` + `ops-finance`
  - MVP 스코프 → `product-pm` + `builder` + `growth-marketer`
  - 피벗/중단 → `market-researcher` + `ops-finance` + `product-pm`
- 각 직원은 격리 컨텍스트에서 자기 관점의 입장문(권고 + 근거)을 반환한다.

## 3. 비판 (단일 패스)
- 모인 입장문을 묶어 `red-team-critic`(`subagent_type: red-team-critic`)에 **한 번에** 넘긴다. 비판가는 부트스트랩 4대 잣대로 각 안을 채점하고 가장 약한 고리·킬샷·빌드 전 검증 실험을 드러낸다.
- **핵심**: 의견수렴 → 비판이 분리된 단계라, 한 모델이 자기 안을 자기가 검증하는 편향을 구조로 차단한다(collect↔review 분리와 같은 사상).

## 4. 종합 + 사람 결정 (durable 기록 게이트)
- 입장문 + 비판을 종합해 단일 권고(채택/조건부/보류/중단)와 근거를 한 화면에 정리한다.
- `AskUserQuestion`으로 창업자에게 선택지를 제시하고, **고른 결정만** `Projects/<slug>/decisions.md`에 ADR로 append한다: `## YYYY-MM-DD — <결정>` + 맥락·선택지(요약)·결정·근거. **동의 없이 decisions.md를 쓰지 않는다.**

## 5. 보고
참석 직원 · 핵심 의견 충돌 · 비판가 킬샷 · 사람이 내린 결정 · 다음 행동을 요약한다.
