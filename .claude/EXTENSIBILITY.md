# 확장 가이드 — 새 요소를 추가할 때 손볼 곳

`.claude/`는 이식 가능한 프레임워크 패키지다(→ `rules/vault-rules.md`). 새 커맨드·에이전트·훅·스크립트를 추가하거나 다른 vault로 옮길 때 **어디를 고쳐야 하는지**를 한곳에 모은 체크리스트다. 산재된 책임을 명시화해 누락·드리프트를 막는다.

> 원칙: 각 항목은 **정본(source of truth) 파일**을 가리킨다. 정본만 고치고 나머지는 참조로 둔다(중복 카운트/재서술 금지 — vault-rules의 update duty가 정본).

## 현재 메커니즘 인벤토리
드리프트 방지를 위해 카운트를 한곳에만 둔다 — 메커니즘을 추가/제거하면 이 표와 `.claude/runtime/hot.md`만 갱신한다.

| 종류 | 개수 | 항목 |
|------|------|------|
| commands | 5 | `.claude/commands/*.md` |
| agents | 2 | `.claude/agents/*.md` |
| skills | 1 | `.claude/skills/<name>/SKILL.md` |
| hooks | 4 | `session-context`(SessionStart) · `auto-commit`(Stop+SessionEnd) · `secret-scan`(PostToolUse) · `kb-lint-check`(PostToolUse) |
| scripts | 2 | `kb-lint.py`(머신 린트) · `scrub-secrets.py`(크리덴셜 마스킹 core+CLI) |
| tests | 1 | `.claude/tests/test_mechanisms.py` (러너: `bash .claude/tests/run-tests.sh`) |

## 공통 절차 — 무엇을 추가하든
1. **파일 위치 컨벤션**: 메커니즘은 `.claude/` 아래, 종류별 디렉터리에 둔다(commands/agents/hooks/skills/tests). 지식은 절대 여기 두지 않는다 — 토픽 디렉터리(`Claude/` 등)로.
2. **계약 테스트**: `.claude/tests/test_mechanisms.py`에 격리-vault 케이스를 함께 추가한다(계약 = 무엇을 보장하는가). 모든 훅·스크립트는 silent-fail(exit 0) 설계라 깨져도 세션이 조용히 진행 → 테스트가 없으면 회귀를 못 잡는다.
3. **인벤토리·hot.md 갱신**: 위 인벤토리 표의 카운트/항목과 `.claude/runtime/hot.md`의 카운트 줄을 맞춘다(정본 두 곳, vault-rules의 navigation 줄도 카운트를 언급하면 함께).

## 새 command 추가
1. `.claude/commands/<name>.md` 생성 — frontmatter `description`·`argument-hint`, 본문은 한국어 절차.
2. 갱신 의무가 있는 커맨드면 본문에서 절차를 재서술하지 말고 `rules/vault-rules.md`의 "Update duty (CANONICAL — 3 steps)"를 **참조**한다.
3. 자연어로도 부르려면 `skills/<name>/SKILL.md` 라우팅 표에 의도→커맨드 매핑을 추가한다.
4. 인벤토리 표의 commands 개수와 `hot.md`를 갱신한다(→ 공통 절차 3).

## 새 subagent 추가
1. `.claude/agents/<name>.md` 생성 — frontmatter: `name` · `description`(자동 위임 트리거의 유일 근거이니 "use when"을 명확히) · `tools`(최소권한) · `model`(난이도별 티어).
2. 절차가 기존 커맨드와 겹치면 **재서술하지 말고 정본 커맨드를 참조**한다.
3. 위임된 에이전트는 격리 컨텍스트 안에서 update duty의 1·2단계(`updated` bump, MOC 반영)까지만 한다 — `hot.md`(3단계)는 메인 세션이 에이전트 복귀 후 소유한다. 에이전트는 `hot.md`를 건드리지 않는다.
4. 인벤토리 표의 agents 개수와 `hot.md`를 갱신한다.

## 새 hook 추가
1. `.claude/hooks/<name>.py` 작성. 기존 훅 파일(`session-context.py`·`secret-scan.py` 등)을 Read해 포터블 규약을 따른다:
   - stdin으로 JSON 수신(`tool_input.file_path` 등).
   - `CLAUDE_PROJECT_DIR` env 우선 + `file_path` 역산/`cwd` fallback으로 cwd-robust.
   - 모든 예외는 silent-fail(exit 0). 경고는 stderr 출력 + exit 2(PostToolUse 컨벤션 — 기존 `kb-lint-check.py` 참조).
   - stdlib only, 절대경로 하드코딩 금지.
2. **settings.json 배선**: `.claude/settings.json`의 `hooks`에 이벤트·matcher를 등록한다(커맨드 경로는 `python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.py"`). 같은 이벤트/matcher에 여러 훅을 stack하면 **배열 순서가 계약일 수 있다**(예: PostToolUse는 `kb-lint-check`→`secret-scan`) — 순서 의존은 훅 docstring에 명시하고 위치를 보존한다.
3. **계약 테스트**: `test_mechanisms.py`에 격리-vault 케이스를 추가한다(→ 공통 절차 2). silent-fail이라 테스트 없이는 회귀 무감지.
4. 인벤토리 표의 hooks 개수·항목과 `hot.md`를 갱신한다.

## 새 bash/python 스크립트 추가
1. `.claude/`(또는 적절한 하위 디렉터리)에 두고, 훅과 동일한 포터블 규약(`$CLAUDE_PROJECT_DIR`/`$0` 기준, 절대경로 하드코딩 금지)을 따른다.
2. `test_mechanisms.py`에 계약 테스트를 추가한다.
3. 인벤토리 표의 scripts 항목과 `hot.md`를 갱신한다.

## path-scoped 규칙 추가 (특정 경로 편집 시에만 로드)
- `.claude/rules/<name>.md` frontmatter에 `paths: ["<glob>"]`를 둔다. Claude Code 공식 기능. `paths`가 없으면 매 세션 무조건 로드, 있으면 매칭 파일 작업 시에만 로드된다. 예: KB 노트 전용 규칙이면 `paths: ["Claude/**/*.md"]`.

## 다른 vault/기기로 이식
1. `.claude/`를 통째로 복사한다(데이터인 토픽 디렉터리는 새 vault 것을 사용).
2. 절대경로 하드코딩이 없어야 한다 — 훅·스크립트 모두 `$CLAUDE_PROJECT_DIR`/`$0` 기준.
3. git이 없으면 `git init`(`auto-commit` 훅이 세션마다 fetch-guarded 커밋·push).

## `.codex/` 어댑터 — STALE, 동기화 보류
- `.codex/`·`.agents/`·`AGENTS.md`(Codex 런타임 어댑터)는 **구 wiki 체계 기준으로 작성되어 현재 stale**하다. 새 KB 체계(`Claude/` + 3필드 프론트매터 + 3단계 update duty)를 반영하지 않는다.
- **재구축 전까지 동기화하지 마라.** 새 커맨드/에이전트/훅을 추가할 때 `.codex/` 어댑터를 함께 갱신하지 않는다 — 어댑터가 이미 정합이 깨져 있어 부분 갱신은 혼란만 키운다.
- 어댑터를 새 체계로 재구축할 때 이 절을 정본으로 다시 작성한다(빌드 스크립트로 `.claude/`에서 생성하는 방식이면 drift가 원천 차단된다 — 권장).
