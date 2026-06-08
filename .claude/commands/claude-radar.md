---
description: Claude Code 활용 정보를 매일 수집해 추천 큐에 적재하고(collect), 큐를 검토해 동의 후 생성한다(review)
argument-hint: [collect | review]
---

# claude-radar: Claude 활용 정보 레이더

인자: `$ARGUMENTS` (빈 값/`collect` = 수집·추천, `review` = 검토·생성)

GeekNews·GitHub·Hacker News·Anthropic 공식·dev.to·npm 등에서 Claude Code 활용 관련 신규 정보를 모아, "우리 `.claude/` 프레임워크에 더하면 좋을 것(skill/agent/command/rule)"과 "`Claude/` KB에 박제할 지식"을 추천 큐에 쌓는다. **실제 생성·박제는 사용자 동의 후 `review` 모드에서만** 한다.

## 모드 판별
- 인자가 `review` → **검토·생성 모드**(§ B).
- 그 외(빈 값 또는 `collect`) → **수집·추천 모드**(§ A).

---

## A. 수집·추천 모드 (무인 cron이 호출 — 절대 `.claude/`·KB를 수정하지 않는다)

### A1. 수집
- `bash`로 `python3 .claude/radar-collect.py`를 실행한다. 결정론적 수집 엔진이 8개 소스를 긁어 seen ledger(`.claude/runtime/radar-seen.json`)로 중복을 제거하고 신규 항목을 JSON으로 출력한다(`new_items`, `counts`, `errors`, `baseline`).
- `baseline: true`이면 첫 실행이므로 **아무 것도 하지 말고** "레이더 기준선 기록 완료 — 다음 실행부터 신규 보고"만 보고하고 종료한다.
- `new_items`가 비어 있으면 "변경 없음"만 보고하고 종료한다(큐·파일 미변경).
- `errors`가 있으면 어떤 소스가 실패했는지 보고에 포함하되, 나머지 항목 처리는 계속한다.

### A2. 분류 (LLM 판단)
각 신규 항목을 다음 중 하나로 분류한다. `type_hint`는 참고일 뿐 — 제목·url·extra를 보고 직접 판단한다:
- **skill / agent / command / rule** — 우리 `.claude/`에 새로 만들거나 기존 것을 개선하면 가치 있는 활용 아이디어 (유용한 워크플로우 패턴, 새 hook 활용, 자주 하는 작업의 자동화 등).
- **kb-ingest** — Claude Code 사용법·개념 지식으로 `Claude/` KB에 박제할 가치가 있는 자료 (공식 기능 출시, 심층 글, 베스트 프랙티스).
- **drop** — 노이즈/무관/단순 홍보, 또는 **이미 우리 vault에 있는 것**. 큐에 넣지 않는다(이미 seen 처리되어 재출현하지 않음).

판단 기준: 우리 vault는 이미 `kb-*` 커맨드/에이전트/스킬과 Claude Code 공식 문서 한국어 KB(`Claude/`)를 갖췄다. **중복이거나 이미 가진 것**은 과감히 drop하고, 정말 새로운 활용 가치가 있는 것만 추천한다.

### A3. 큐 적재
- 추천(skill/agent/command/rule)과 kb-ingest 후보를 `.claude/runtime/radar-queue.md`의 **오늘 날짜 섹션**(`## YYYY-MM-DD`, 없으면 새로 만들어 맨 위에)에 append한다.
- 항목 포맷은 큐 파일 상단 주석의 템플릿을 **정확히** 따른다 — `### [pending] <type> · <제목>` 헤더 + `source`/`url`/`근거`/`제안` 불릿. status는 항상 `pending`으로 시작.
- 하루 추천이 8개를 넘으면 가치 높은 8개만 적재하되, 나머지는 **오늘 섹션 끝에 `<!-- overflow: N건 미적재 (이미 seen 처리되어 재출현하지 않음) -->` 주석**으로 남겨 누락을 추적 가능하게 한다(보고에도 언급). `radar-collect.py`는 출력한 전 항목을 seen에 기록하므로 적재하지 않은 항목은 다음 실행에 다시 나오지 않는다 — 무인 로그(`radar-cron.log`)는 gitignore되어 사실상 소실되므로 큐 주석이 유일한 추적 수단이다.

### A4. 보고
수집 수·신규 수·분류 분포(추천 N건, kb-ingest N건, drop N건)·소스 errors를 한 단락으로 요약한다. **여기서 멈춘다 — 생성·박제는 절대 하지 않는다.**

---

## B. 검토·생성 모드 (대화형 — 사용자 동의가 필수)

### B1. 큐 표시
- `.claude/runtime/radar-queue.md`의 `[pending]` 항목을 모두 읽어, 사용자에게 번호를 매겨 제시한다(유형·제목·근거·제안·url).

### B2. 동의
- 사용자가 만들거나 박제할 항목을 고르게 한다(`AskUserQuestion` 또는 자유 입력). **동의 없이는 어떤 파일도 만들지 않고, 어떤 KB 노트도 박제하지 않는다.**

### B3. 생성 (동의한 것만, 공식 생성 도구를 활용)
유형별로:
- **skill** → `Skill` 도구로 `skill-creator`를 호출해 생성한다(산출물: `.claude/skills/<name>/SKILL.md`). 손으로 SKILL.md를 직접 쓰지 말 것.
- **agent** → `.claude/agents/<name>.md`를 만든다. frontmatter 4필드(`name`/`description`/`tools`/`model`), 기존 `.claude/agents/kb-updater.md`·`kb-guide.md` 포맷을 따른다. description에 "언제 쓰는가 + 하지 않는 것(경계)"을 명시한다.
- **command** → `.claude/commands/<name>.md`를 만든다. frontmatter(`description`/`argument-hint`), 본문은 `$ARGUMENTS` + 단계 번호(`## 1.` …) 구조로 `kb-sync.md` 스타일을 따른다.
- **rule** → `.claude/rules/<name>-rules.md`를 만든다. **frontmatter 없는 순수 마크다운**(`# <Title>` 헤더로 시작 — skill/agent/command와 달리 frontmatter를 붙이지 않는다, `vault-rules.md`와 동일 형식). 영어 본문, canonical 섹션 패턴. 신규 rule은 `vault-rules.md`와 충돌 시 우선순위를 첫 단락에 명시한다.
- **kb-ingest** → 해당 url을 `/kb-ingest` 절차로 KB에 박제한다(스크럽 → 주제 판별 → 노트 생성/갱신 → 갱신 의무 3단계). 분량이 크면 `kb-updater` 서브에이전트(Agent tool, `subagent_type: kb-updater`)에 위임한다.

### B4. 큐 갱신
- 생성/박제를 마친 항목은 `[pending]`→`[done]`으로, 사용자가 거절한 항목은 `[dismissed]`로 상태만 바꾼다(텍스트 치환). 항목을 삭제하지 말고 이력을 남긴다.

### B5. 갱신 의무
- skill/agent/command/rule을 추가했으면 `.claude/runtime/hot.md`의 프레임워크 인벤토리 한 줄을 갱신한다(새 산출물 반영).
- KB 노트를 만들었으면 `.claude/rules/vault-rules.md`의 "Update duty (CANONICAL — 3 steps)"를 따른다(정본 참조 — 단계는 여기서 재명세하지 않는다).

### B6. 보고
무엇을 생성/박제/거절했는지, 큐에 남은 `pending` 수를 요약한다.

---

## 한계 (명시)
- 수집은 **공개·무인증 엔드포인트 + 키워드/topic 필터**에 의존한다. Reddit(봇 차단)·X·Discord·Smithery(429)는 제외됐다.
- seen ledger 기반 dedup이라, 한 번 본 repo/글은 큰 업데이트가 있어도 재추천하지 않는다(레이더의 목적은 "발견").
- 기존 페이지의 *내용* 변화는 추적하지 않는다 — 그건 `/kb-sync --deep`의 몫이며, 이 레이더(생태계/활용 신호)와 `kb-sync`(공식 문서 본문 동기화)는 입력 소스가 달라 역할이 겹치지 않는다.
