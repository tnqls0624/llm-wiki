---
description: AI Infra 학습 코치 — 어제 산출물을 LLM이 검토·채점하고(review) 오늘 할 것을 브리핑한다(brief)
argument-hint: [review | brief | plan]
---

# study-coach: AI Infra 학습 코치

인자: `$ARGUMENTS` (빈 값/`review` = 검토+브리핑, `brief` = 오늘 브리핑만, `plan` = 다음 구간 상세화)

진도 정본은 `.claude/runtime/study-state.md`(git 추적 → 회사/집 두 Mac이 push/pull로 공유). 검토 대상은 별도 repo `ai-infra-lab`(경로는 study-state 메타 `repo_path` + `.claude/runtime/study-local.conf` override). 무인 아침 cron(`study-coach-cron.sh`)이 `review`를 headless로 호출한다.

## 모드 판별
- `brief` → **브리핑 전용**(§ B). `plan` → **구간 상세화**(§ C). 그 외(빈 값/`review`) → **검토+브리핑**(§ A).

---

## A. 검토 + 브리핑 모드 (무인 cron + 수동 공용 — LLM이 검사)

> **안전 경계(필수 준수):** 쓰기는 `.claude/runtime/`(study-state.md·study-today.md)에만 한다. **ai-infra-lab repo는 읽기 전용**(`git log`/`git diff`/파일 Read만 — commit·push·수정 금지). `.claude/`의 메커니즘(skills/agents/commands/rules/hooks/scripts/tests)과 KB 토픽 디렉토리는 **절대 건드리지 않는다** — 위반 시 cron의 stray-guard가 커밋 전에 되돌린다.

### A1. 검토 대상 파악
- `.claude/runtime/study-state.md`를 읽어 메타(`repo_path`, `last_brief_date`)와 미완료 항목(`- [ ]`)을 파악한다.
- repo 경로 확인: `study-local.conf`에 `repo_path=`가 있으면 그것을, 없으면 메타의 `repo_path`(기본 `~/ai-infra-lab`)를 쓴다.
- repo 디렉토리가 **없으면**(아직 학습 시작 전): 검토를 건너뛰고 "아직 ai-infra-lab 없음 — 첫 항목부터 시작" 안내 후 § A4(브리핑)로 간다.

### A2. 어제 산출물 수집 (읽기 전용)
- `git -C <repo> pull --ff-only` 로 다른 Mac에서 한 작업을 먼저 당겨온다(실패해도 무시하고 로컬 기준으로 진행 — 보고에 언급).
- 마지막 검토 이후의 변화를 본다: `git -C <repo> log --since="2 days ago" --stat`, 필요하면 `git -C <repo> diff HEAD~N`. 노트북·스크립트·`docs/log.md`·README 등 실제 산출물을 Read로 확인한다.
- **커밋·변경이 없으면**: "어제 새 산출물 없음"으로 기록하고 진도는 그대로 둔 채 § A4로 간다(억지로 체크하지 않는다).

### A3. 채점 + 진도 갱신 (study-state.md = runtime, 쓰기 허용)
실제 산출물을 study-state의 미완료 항목과 대조해 **LLM이 판단**한다:
- **완료 기준을 실제로 충족한 항목**만 `- [ ]` → `- [x]`로 바꾼다. "파일만 있고 동작 안 함"은 체크하지 않는다(이 vault의 완료 기준 = 동작하는 결과물).
- 애매하면 체크하지 말고 검토 로그에 "확인 필요" 사유를 남긴다.
- study-state.md 하단 `## 검토 로그`에 **날짜 섹션**(`### YYYY-MM-DD`)을 append한다:
  - **잘한 점** / **부족하거나 고칠 점**(베스트 프랙티스 관점) / **다음에 주의할 것** 3줄.
  - 코드 품질 피드백은 구체적으로(예: "`model.eval()` 누락 — 추론 시 dropout이 켜진 채 실행됨").

### A4. 오늘 브리핑 생성
- `bash`로 `python3 .claude/study-brief.py --force` 를 실행한다(갱신된 state 기준으로 오늘 요일에 맞는 다음 항목을 `study-today.md`에 씀). 0-LLM 결정론적이라 항목 선택은 체크박스 순서를 그대로 따른다.
- 그런 다음 `study-today.md` 상단에 § A3의 **검토 한 줄 요약**(예: "어제: W1 D2 완료 ✅ / requirements.txt에 버전 핀 누락 주의")을 prepend해, 아침에 한 화면에서 "어제 피드백 + 오늘 할 것"이 보이게 한다.

### A5. 보고
검토한 커밋 수 · 새로 체크한 항목 · 핵심 피드백 1~2개 · 오늘 할 항목을 한 단락으로 요약한다. (무인 cron 호출이면 osascript 알림은 wrapper가 처리하므로 stdout 요약만.)

---

## B. 브리핑 전용 모드 (`brief` — LLM 없이 오늘 항목만)
- `bash`로 `python3 .claude/study-brief.py --force` 를 실행하고 결과(`study-today.md`)를 사용자에게 보여준다. 검토·채점은 하지 않는다. 빠른 "오늘 뭐 하지?" 확인용.

---

## C. 구간 상세화 모드 (`plan` — 대화형)
- study-state.md에서 `상세화 대기`로 표시된 다음 주차 구간(예: W5~W8)을 사용자와 함께 일별 항목(`- [ ] [평일] D1: …` / `- [ ] [주말] …`)으로 채운다.
- persona의 11단계 형식(진단→목표→개념→자료→주차계획→평일→주말→완료기준→GitHub산출물→오류→다음조건)을 따르되, 한 번에 4주 분량만 상세화한다.
- 완료한 항목은 제외하고 다음 구간만 추가한다(이전 계획 반복 금지).

---

## 갱신 의무 / 한계
- 이 커맨드가 study-state.md의 **항목 구조·일별 계획을 바꿨으면**(C 모드) `.claude/runtime/hot.md`의 study-coach 줄에 반영한다. 단순 체크/검토 로그 append(A 모드)는 runtime 데이터 변경이라 추가 동기화 불필요.
- 검토는 **마지막 검토 이후 커밋된 산출물**만 본다 — 커밋하지 않은 로컬 작업은 보이지 않는다(두 Mac 동기화도 커밋 기준). "커밋하는 습관"이 이 시스템의 전제다.
- 무인 검토는 진도를 **자동 체크**한다 — 오판이 있으면 아침에 study-today를 보고 study-state에서 직접 정정하면 된다(git이라 되돌리기 안전).
