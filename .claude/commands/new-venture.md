---
description: 새 비즈니스 프로젝트를 Projects/ 아래 스캐폴드하고, 1회차 회의(리서치→비판→종합)를 돌려 부트스트랩 4대 잣대 통과 여부에 대한 첫 권고를 낸다
argument-hint: <아이디어 한 줄>
---

# new-venture: 새 사업 시작 + 1회차 회의

아이디어: `$ARGUMENTS`

가장 비싼 실수(잘못된 도메인에 진입)를 **시작점에서** 막는 커맨드다. 디렉토리 골격을 만들고, 곧바로 직원 에이전트들을 소집해 "이 아이디어가 부트스트랩 4대 잣대(① 6개월 내 수요신호 ② 자본 ~0 ③ 창업자 역량이 해자 ④ 에이전트 자동화)를 통과하는가"를 검증한다. **채택은 사람이 결정한다 — 이 커맨드는 권고까지다.**

## 1. 스캐폴드 생성
- 아이디어에서 짧은 영문 kebab-case slug를 정한다(예: `geo-citation-report`). 이미 `Projects/<slug>/`가 있으면 사용자에게 알리고 멈춘다(덮어쓰기 금지).
- `Projects/<slug>/` 아래 골격을 만든다 — 각 파일은 헤더 + "(미작성)" 플레이스홀더로 시작:
  - `plan.md` (문제정의·가설·MVP·마일스톤 — product-pm이 채움)
  - `decisions.md` (ADR 로그 — 회의 결과만, 사람 결정 후)
  - `progress.md` (주차별 진척 — /weekly-review가 append)
  - `growth.md` (채널 실험 — growth-marketer)
  - `ops.md` (비용·운영 — ops-finance)
  - `research/` 디렉토리(첫 리서치 노트가 여기 들어감)
- `Projects/Projects.md` MOC의 "활성" 표에 `[[<slug>]] — 한 줄 요약` 줄을 추가한다.

## 2. 1회차 회의 (fan-out → 비판 → 종합)
- **사풍 주입**: 직원을 호출하기 전 `Projects/_company/charter.md`(창업자 프로필·자산·부트스트랩 4대 잣대·운영 원칙)를 읽어, 각 직원 프롬프트에 그 맥락을 포함한다 — 직원이 "이 창업자가 누구고 뭘 가졌는지" 위에서 일하도록.
- **리서치**: `market-researcher` 서브에이전트(Agent tool, `subagent_type: market-researcher`)에 아이디어를 넘겨 수요·경쟁·타깃·진입점·가장 강한 반증을 조사하고 `Projects/<slug>/research/`에 박제하게 한다.
- **비판**: 리서치 결과를 `red-team-critic`(`subagent_type: red-team-critic`)에 넘겨 4대 잣대로 채점하고 킬샷·빌드 전 검증 실험을 받는다.
- **종합**: 리서치 + 비판을 묶어, 채택/조건부/탈락 권고와 근거를 한 화면에 정리한다. (선택: `founder-chief-of-staff`에 종합 판단을 맡길 수 있다.)

## 3. 사람 결정 (durable 기록 게이트)
- `AskUserQuestion`으로 창업자에게 선택지를 제시한다: **채택(다음 실험 진행) / 조건부(이 검증부터) / 보류 / 폐기**.
- 창업자가 고른 결정**만** `Projects/<slug>/decisions.md`에 ADR 형식으로 기록한다: `## YYYY-MM-DD — <결정>` + 맥락·선택지·결정·근거. **동의 없이 decisions.md를 쓰지 않는다**(automation-safety: durable 변경은 사람 동의 후).
- 채택/조건부면 `product-pm`에 plan.md(가설 + 다음 1개 실험)를 작성하게 한다.

## 4. 보고
스캐폴드 경로 · 회의 핵심(수요/반증/권고) · 사람이 내린 결정 · 다음 1개 실험을 요약한다.
