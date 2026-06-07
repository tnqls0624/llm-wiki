---
title: 02 CLI 레퍼런스
updated: 2026-06-07
sources: [cli-reference, interactive-mode, keybindings, terminal-config, fullscreen, voice-dictation]
---

# 02 CLI 레퍼런스

Claude Code의 커맨드라인 인터페이스, 대화형 세션 단축키, 키바인딩 커스터마이징, 터미널 설정, 풀스크린 렌더링, 음성 받아쓰기에 대한 종합 레퍼런스다. 명령어·플래그·키·설정 키는 원문 그대로 유지하고 설명은 한국어로 정리했다. 허브는 [[Claude]], 시작은 [[01 시작하기]] 참고.

---

## CLI 명령어 (commands)

`claude`로 세션을 시작하거나, 콘텐츠를 파이프로 넘기거나, 대화를 재개하거나, 업데이트를 관리할 수 있다. 서브커맨드를 오타로 입력하면(`claude udpate`) Claude Code가 가장 가까운 매치를 제안(`Did you mean claude update?`)하고 세션을 시작하지 않고 종료한다.

### 세션·SDK·업데이트

| Command | Description | Example |
| :--- | :--- | :--- |
| `claude` | 대화형 세션 시작 | `claude` |
| `claude "query"` | 초기 프롬프트와 함께 대화형 세션 시작 | `claude "explain this project"` |
| `claude -p "query"` | SDK로 쿼리 후 종료 (print mode) | `claude -p "explain this function"` |
| `cat file \| claude -p "query"` | 파이프된 콘텐츠 처리 | `cat logs.txt \| claude -p "explain"` |
| `claude -c` | 현재 디렉터리의 가장 최근 대화 이어가기 | `claude -c` |
| `claude -c -p "query"` | SDK로 대화 이어가기 | `claude -c -p "Check for type errors"` |
| `claude -r "<session>" "query"` | ID 또는 이름으로 세션 재개 | `claude -r "auth-refactor" "Finish this PR"` |
| `claude update` | 최신 버전으로 업데이트 | `claude update` |
| `claude install [version]` | 네이티브 바이너리 설치/재설치. `2.1.118` 같은 버전, `stable`, `latest` 허용 | `claude install stable` |

### 인증 (auth)

| Command | Description | Example |
| :--- | :--- | :--- |
| `claude auth login` | Anthropic 계정 로그인. `--email`로 이메일 사전 입력, `--sso`로 SSO 강제, `--console`로 구독 대신 Console(API 과금) 로그인 | `claude auth login --console` |
| `claude auth logout` | 계정 로그아웃 | `claude auth logout` |
| `claude auth status` | 인증 상태를 JSON으로 출력. `--text`는 사람이 읽는 형식. 로그인 시 종료코드 0, 미로그인 시 1 | `claude auth status` |
| `claude setup-token` | CI·스크립트용 장수명 OAuth 토큰 생성. 저장하지 않고 터미널에 출력. 구독 필요 | `claude setup-token` |

### 백그라운드 세션·에이전트 뷰

이 명령어들은 [[08 서브에이전트와 에이전트 팀]]의 병렬 백그라운드 세션 관리와 연결된다.

| Command | Description | Example |
| :--- | :--- | :--- |
| `claude agents` | agent view를 열어 병렬 백그라운드 세션 모니터링/디스패치. `--cwd <path>`로 필터, `--json`으로 스크립팅용 JSON 배열 출력. `--permission-mode`, `--model`, `--effort`, `--agent`로 디스패치 기본값 설정 | `claude agents --json` |
| `claude attach <id>` | 이 터미널에서 백그라운드 세션에 연결 | `claude attach 7c5dcf5d` |
| `claude logs <id>` | 백그라운드 세션의 최근 출력 출력 | `claude logs 7c5dcf5d` |
| `claude respawn <id>` | 대화를 유지한 채 백그라운드 세션 재시작. `--all`로 전체 재시작(예: 바이너리 업데이트 반영) | `claude respawn 7c5dcf5d` |
| `claude stop <id>` | 백그라운드 세션 중지 (`claude kill`도 가능) | `claude stop 7c5dcf5d` |
| `claude rm <id>` | 목록에서 백그라운드 세션 제거 (transcript는 로컬에 남아 `--resume` 가능) | `claude rm 7c5dcf5d` |
| `claude daemon status` | 백그라운드 세션 supervisor 상태·버전·소켓 디렉터리·워커 수 진단 출력. 미실행 시 종료코드 1 | `claude daemon status` |
| `claude daemon stop --any` | supervisor와 호스팅 세션 중지. `--keep-workers`로 세션 유지, `--any`로 on-demand supervisor 중지 확인 | `claude daemon stop --any --keep-workers` |

### 기타 관리·통합 명령어

| Command | Description | Example |
| :--- | :--- | :--- |
| `claude mcp` | MCP 서버 설정 (자세히는 [[10 MCP]]) | — |
| `claude plugin` | 플러그인 관리 (별칭 `claude plugins`, 자세히는 [[11 플러그인]]) | `claude plugin install code-review@claude-plugins-official` |
| `claude auto-mode defaults` | 내장 auto mode 분류 규칙을 JSON으로 출력 (`claude auto-mode config`로 적용된 설정 확인). 권한은 [[05 권한]] | `claude auto-mode defaults > rules.json` |
| `claude project purge [path]` | 프로젝트의 로컬 상태 전부 삭제(transcript, task list, debug log, 편집 이력, 프롬프트 이력, `~/.claude.json` 항목). 플래그: `--dry-run`(미리보기), `-y`/`--yes`(확인 생략), `-i`/`--interactive`(항목별 확인), `--all`(모든 프로젝트) | `claude project purge ~/work/repo --dry-run` |
| `claude remote-control` | Remote Control 서버 시작(서버 모드, 로컬 대화형 세션 없음). [[15 웹과 모바일]] 참고 | `claude remote-control --name "My Project"` |
| `claude ultrareview [target]` | ultrareview 비대화형 실행. 성공 0/실패 1, `--json`으로 raw payload, `--timeout <minutes>`로 기본 30분 변경 | `claude ultrareview 1234 --json` |

---

## CLI 플래그 (flags)

`claude --help`는 모든 플래그를 나열하지 않으므로, `--help`에 없다고 해서 그 플래그를 못 쓰는 것은 아니다. 아래는 전체 플래그 목록이다.

| Flag | Description | Example |
| :--- | :--- | :--- |
| `--add-dir` | Claude가 읽고 편집할 추가 작업 디렉터리. 파일 접근만 부여하고 `.claude/` 설정은 대부분 미발견. 영속화하려면 settings의 `permissions.additionalDirectories` 사용 | `claude --add-dir ../apps ../lib` |
| `--agent` | 현재 세션의 에이전트 지정(`agent` 설정 오버라이드) | `claude --agent my-custom-agent` |
| `--agents` | JSON으로 커스텀 서브에이전트 동적 정의. subagent frontmatter 필드명 + `prompt` 필드 | `claude --agents '{"reviewer":{"description":"Reviews code","prompt":"You are a code reviewer"}}'` |
| `--allow-dangerously-skip-permissions` | `bypassPermissions`를 `Shift+Tab` 모드 사이클에 추가하되 그 모드로 시작하지는 않음 | `claude --permission-mode plan --allow-dangerously-skip-permissions` |
| `--allowedTools` | 프롬프트 없이 실행되는 도구. 패턴 매칭은 permission rule syntax 참고. 사용 가능한 도구 제한은 `--tools` | `"Bash(git log *)" "Bash(git diff *)" "Read"` |
| `--append-system-prompt` | 기본 시스템 프롬프트 끝에 텍스트 추가 | `claude --append-system-prompt "Always use TypeScript"` |
| `--append-system-prompt-file` | 파일에서 추가 시스템 프롬프트 로드 후 기본 프롬프트에 append | `claude --append-system-prompt-file ./extra-rules.txt` |
| `--bare` | 최소 모드: hooks·skills·plugins·MCP·auto memory·CLAUDE.md 자동 탐색 생략으로 스크립트 호출 가속. Bash·파일 읽기·편집만 사용. `CLAUDE_CODE_SIMPLE` 설정 | `claude --bare -p "query"` |
| `--betas` | API 요청에 포함할 beta 헤더 (API key 사용자 전용) | `claude --betas interleaved-thinking` |
| `--bg` | 세션을 백그라운드 에이전트로 시작하고 즉시 반환. `--exec`로 셸 명령 백그라운드 잡, `--agent`로 특정 서브에이전트 실행 | `claude --bg "investigate the flaky test"` |
| `--channels` | (Research preview) channel 알림을 들을 MCP 서버. `plugin:<name>@<marketplace>` 공백 구분. Claude.ai 인증 필요 | `claude --channels plugin:my-notifier@my-marketplace` |
| `--chrome` | Chrome 브라우저 통합 활성화 (자세히는 [[21 브라우저와 컴퓨터 사용]]) | `claude --chrome` |
| `--continue`, `-c` | 현재 디렉터리의 가장 최근 대화 로드 | `claude --continue` |
| `--dangerously-load-development-channels` | 승인 allowlist 밖 channel을 로컬 개발용으로 활성화. 확인 프롬프트 | `claude --dangerously-load-development-channels server:webhook` |
| `--dangerously-skip-permissions` | 권한 프롬프트 건너뛰기. `--permission-mode bypassPermissions`와 동등 ([[05 권한]], [[18 보안과 샌드박스]]) | `claude --dangerously-skip-permissions` |
| `--debug` | 디버그 모드(카테고리 필터 가능, 예 `"api,hooks"` 또는 `"!statsig,!file"`) | `claude --debug "api,mcp"` |
| `--debug-file <path>` | 디버그 로그를 특정 파일에 기록. 암묵적으로 디버그 모드 활성화. `CLAUDE_CODE_DEBUG_LOGS_DIR`보다 우선 | `claude --debug-file /tmp/claude-debug.log` |
| `--disable-slash-commands` | 이 세션의 모든 skills·commands 비활성화 | `claude --disable-slash-commands` |
| `--disallowedTools` | deny 규칙. 맨이름은 도구를 컨텍스트에서 제거, `Bash(rm *)` 같은 스코프 규칙은 도구는 두고 매칭만 거부 | `"Bash(git log *)" "Bash(git diff *)" "Edit"` |
| `--effort` | 현재 세션 effort level: `low`,`medium`,`high`,`xhigh`,`max` (모델별 가용 레벨 상이). `effortLevel` 오버라이드, 비영속 ([[19 비용과 성능]]) | `claude --effort high` |
| `--enable-auto-mode` | v2.1.111에서 제거됨. auto mode는 기본으로 `Shift+Tab` 사이클에 포함, `--permission-mode auto` 사용 | `claude --permission-mode auto` |
| `--exclude-dynamic-system-prompt-sections` | 머신별 섹션(작업 디렉터리·환경·메모리 경로·git 플래그)을 첫 user 메시지로 이동해 멀티유저 prompt-cache 재사용 개선. 기본 시스템 프롬프트에서만, `-p`와 함께 | `claude -p --exclude-dynamic-system-prompt-sections "query"` |
| `--exec` | Claude 세션 대신 PTY 백그라운드 잡으로 셸 명령 실행. `--bg`와 함께 | `claude --bg --exec 'pytest -x'` |
| `--fallback-model` | 기본 모델 과부하/불가 시 지정 모델로 자동 폴백. print mode·백그라운드 세션에서만 적용, 대화형은 무시 | `claude -p --fallback-model sonnet "query"` |
| `--fork-session` | 재개 시 원본 재사용 대신 새 세션 ID 생성 (`--resume`/`--continue`와) | `claude --resume abc123 --fork-session` |
| `--from-pr` | 특정 PR에 연결된 세션 재개. PR 번호, GitHub/GitHub Enterprise/GitLab MR/Bitbucket PR URL 허용 | `claude --from-pr 123` |
| `--ide` | 유효한 IDE가 정확히 하나면 시작 시 자동 연결 ([[14 IDE와 데스크톱]]) | `claude --ide` |
| `--init` | 세션 전에 `init` matcher로 Setup hooks 실행 (print mode 전용, [[09 훅]]) | `claude -p --init "query"` |
| `--init-only` | Setup과 `SessionStart` hooks만 실행 후 대화 없이 종료 | `claude --init-only` |
| `--include-hook-events` | 모든 hook 라이프사이클 이벤트를 출력 스트림에 포함. `--output-format stream-json` 필요 | `claude -p --output-format stream-json --verbose --include-hook-events "query"` |
| `--include-partial-messages` | 부분 스트리밍 이벤트 포함. `--print`와 `--output-format stream-json` 필요 | `claude -p --output-format stream-json --verbose --include-partial-messages "query"` |
| `--input-format` | print mode 입력 형식 (`text`, `stream-json`) | `claude -p --output-format json --input-format stream-json` |
| `--json-schema` | 워크플로 완료 후 JSON Schema에 맞는 검증된 JSON 출력 (print mode 전용) | `claude -p --json-schema '{"type":"object","properties":{...}}' "query"` |
| `--maintenance` | 세션 전에 `maintenance` matcher로 Setup hooks 실행 (print mode 전용) | `claude -p --maintenance "query"` |
| `--max-budget-usd` | 중지 전 API 호출 최대 지출액 (print mode 전용, [[19 비용과 성능]]) | `claude -p --max-budget-usd 5.00 "query"` |
| `--max-turns` | agentic 턴 수 제한 (print mode 전용). 한계 도달 시 에러 종료. 기본 무제한 | `claude -p --max-turns 3 "query"` |
| `--mcp-config` | JSON 파일/문자열에서 MCP 서버 로드 (공백 구분, [[10 MCP]]) | `claude --mcp-config ./mcp.json` |
| `--model` | 현재 세션 모델 (`sonnet`/`opus` 별칭 또는 풀네임). `model` 설정과 `ANTHROPIC_MODEL` 오버라이드 | `claude --model claude-sonnet-4-6` |
| `--name`, `-n` | 세션 표시 이름 설정. `/resume`과 터미널 제목에 표시. `claude --resume <name>`으로 재개. `/rename`으로 중간 변경 | `claude -n "my-feature-work"` |
| `--no-chrome` | 이 세션의 Chrome 통합 비활성화 | `claude --no-chrome` |
| `--no-session-persistence` | 세션을 디스크에 저장하지 않아 재개 불가 (print mode 전용). `CLAUDE_CODE_SKIP_PROMPT_HISTORY`는 모든 모드에서 동일 | `claude -p --no-session-persistence "query"` |
| `--output-format` | print mode 출력 형식 (`text`, `json`, `stream-json`) | `claude -p "query" --output-format json` |
| `--permission-mode` | 시작 권한 모드: `default`,`acceptEdits`,`plan`,`auto`,`dontAsk`,`bypassPermissions`. settings의 `defaultMode` 오버라이드 | `claude --permission-mode plan` |
| `--permission-prompt-tool` | 비대화형 모드에서 권한 프롬프트를 처리할 MCP 도구 지정 | `claude -p --permission-prompt-tool mcp_auth_tool "query"` |
| `--plugin-dir` | 디렉터리/`.zip`에서 이 세션만 플러그인 로드. 여러 개는 플래그 반복 | `claude --plugin-dir ./my-plugin` |
| `--plugin-url` | URL에서 플러그인 `.zip` 가져오기 (이 세션만). 플래그 반복 또는 공백 구분 | `claude --plugin-url https://example.com/plugin.zip` |
| `--print`, `-p` | 대화형 없이 응답 출력 (프로그래밍 사용은 [[22 Agent SDK — 시작]]) | `claude -p "query"` |
| `--prompt-suggestions` | 매 턴 후 예측된 다음 프롬프트를 `prompt_suggestion` 메시지로 emit. `--print`,`--output-format stream-json`,`--verbose` 필요 | `claude -p --prompt-suggestions --output-format stream-json --verbose "query"` |
| `--remote` | claude.ai에 새 web 세션 생성 ([[15 웹과 모바일]]) | `claude --remote "Fix the login bug"` |
| `--remote-control`, `--rc` | Remote Control 활성화된 대화형 세션 시작 (claude.ai/Claude 앱에서도 제어). 선택적 이름 인자 | `claude --remote-control "My Project"` |
| `--remote-control-session-name-prefix <prefix>` | Remote Control 자동 생성 세션명 접두사. 기본은 호스트명. `CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX`와 동일 | `claude remote-control --remote-control-session-name-prefix dev-box` |
| `--replay-user-messages` | stdin의 user 메시지를 stdout으로 재방출(ack). `--input-format`·`--output-format` 모두 `stream-json` 필요 | `claude -p --input-format stream-json --output-format stream-json --verbose --replay-user-messages` |
| `--resume`, `-r` | ID/이름으로 특정 세션 재개 또는 대화형 picker. v2.1.144부터 백그라운드 세션은 `bg` 표시 | `claude --resume auth-refactor` |
| `--session-id` | 특정 세션 ID 사용 (유효한 UUID) | `claude --session-id "550e8400-e29b-41d4-a716-446655440000"` |
| `--setting-sources` | 로드할 설정 소스 (`user`,`project`,`local`, 쉼표 구분) ([[04 설정]]) | `claude --setting-sources user,project` |
| `--settings` | settings JSON 파일 경로 또는 인라인 JSON. 여기 키는 이 세션 동안 `settings.json` 동일 키를 오버라이드 | `claude --settings ./settings.json` |
| `--strict-mcp-config` | `--mcp-config`의 MCP 서버만 사용, 그 외 모든 MCP 설정 무시 | `claude --strict-mcp-config --mcp-config ./mcp.json` |
| `--system-prompt` | 전체 시스템 프롬프트를 커스텀 텍스트로 교체 | `claude --system-prompt "You are a Python expert"` |
| `--system-prompt-file` | 파일에서 시스템 프롬프트 로드해 기본 프롬프트 교체 | `claude --system-prompt-file ./custom-prompt.txt` |
| `--teleport` | web 세션을 로컬 터미널에서 재개 | `claude --teleport` |
| `--teammate-mode` | agent team teammate 표시 방식: `auto`(기본),`in-process`,`tmux`. `teammateMode` 오버라이드 ([[08 서브에이전트와 에이전트 팀]]) | `claude --teammate-mode in-process` |
| `--tmux` | worktree용 tmux 세션 생성. `--worktree` 필요. iTerm2 네이티브 pane 사용, `--tmux=classic`은 전통 tmux | `claude -w feature-auth --tmux` |
| `--tools` | Claude가 쓸 내장 도구 제한. `""`=전부 비활성, `"default"`=전부, `"Bash,Edit,Read"`=지정 ([[06 내장 도구 레퍼런스]]) | `claude --tools "Bash,Edit,Read"` |
| `--verbose` | verbose 로깅, 턴별 전체 출력. `viewMode` 오버라이드 | `claude --verbose` |
| `--version`, `-v` | 버전 번호 출력 | `claude -v` |
| `--worktree`, `-w` | `<repo>/.claude/worktrees/<name>`의 격리된 git worktree에서 시작. 이름 생략 시 자동. `#<번호>`나 GitHub PR URL로 그 PR을 fetch | `claude -w feature-auth` |

### 시스템 프롬프트 플래그 4종

시스템 프롬프트 커스터마이징 플래그 4종은 대화형/비대화형 모두에서 동작한다.

| Flag | Behavior | Example |
| :--- | :--- | :--- |
| `--system-prompt` | 기본 프롬프트 전체 교체 | `claude --system-prompt "You are a Python expert"` |
| `--system-prompt-file` | 파일 내용으로 교체 | `claude --system-prompt-file ./prompts/review.txt` |
| `--append-system-prompt` | 기본 프롬프트에 append | `claude --append-system-prompt "Always use TypeScript"` |
| `--append-system-prompt-file` | 파일 내용을 기본 프롬프트에 append | `claude --append-system-prompt-file ./style-rules.txt` |

선택 기준 — `--system-prompt`와 `--system-prompt-file`은 상호 배타적이며, append 플래그는 둘 중 어느 교체 플래그와도 조합 가능하다. **append**는 Claude가 코딩 어시스턴트 정체성을 유지한 채 추가 규칙만 따르게 할 때 쓴다(기본 도구 가이드·안전 지침·코딩 규칙 보존). **교체**는 표면·정체성·권한 모델이 Claude Code와 다를 때(예: 사람이 보지 않는 파이프라인의 비코딩 에이전트) 쓰며, 기본 프롬프트 전체(도구 가이드·안전 지침 포함)가 사라지므로 필요한 것은 직접 챙겨야 한다. 이 플래그는 해당 호출에만 적용된다. 영속적 페르소나는 [[12 출력 스타일과 상태줄]]의 output styles, 프로젝트 규칙은 [[03 메모리와 컨텍스트]]의 CLAUDE.md를 쓴다.

---

## 키보드 단축키 (대화형 모드)

단축키는 플랫폼·터미널마다 다를 수 있다. 풀스크린 렌더링에서는 transcript viewer에서 `?`로 단축키 목록을 본다.

> [!note] macOS에서 Option/Alt 단축키
> `Alt+B`, `Alt+F`, `Alt+Y`, `Alt+M`, `Alt+P` 등은 터미널에서 Option을 Meta로 설정해야 동작한다.
> - **iTerm2**: Settings → Profiles → Keys → General → Left/Right Option key를 "Esc+"
> - **Apple Terminal**: Settings → Profiles → Keyboard → "Use Option as Meta Key" 체크
> - **VS Code**: 설정에 `"terminal.integrated.macOptionIsMeta": true`
>
> 자세한 내용은 아래 "터미널 설정" 섹션 참고.

### 일반 제어 (General controls)

| Shortcut | Description | Context |
| :--- | :--- | :--- |
| `Ctrl+C` | 중단 또는 입력 지우기 | 실행 중 작업 인터럽트. 실행 중인 게 없으면 1회 누름은 입력 비우기, 2회 누름은 Claude Code 종료 |
| `Ctrl+X Ctrl+K` | 이 세션의 모든 백그라운드 서브에이전트 종료 | 3초 내 두 번 눌러 확인 ([[08 서브에이전트와 에이전트 팀]]) |
| `Ctrl+D` | Claude Code 세션 종료 | EOF 신호 |
| `Ctrl+G` 또는 `Ctrl+X Ctrl+E` | 기본 텍스트 에디터에서 열기 | 프롬프트/응답을 외부 에디터에서 편집. `Ctrl+X Ctrl+E`는 readline 네이티브 바인딩. `/config`에서 "Show last response in external editor"를 켜면 Claude의 이전 응답이 `#` 주석으로 앞에 붙고 저장 시 제거됨 |
| `Ctrl+L` | 화면 다시 그리기 | 전체 redraw. 입력·대화 이력 유지. 화면이 깨졌을 때 복구용 |
| `Ctrl+O` | transcript viewer 토글 | 상세 도구 사용·실행 표시. 기본 한 줄로 접히는 MCP 호출("Called slack 3 times")도 펼침 |
| `Ctrl+R` | 명령 이력 역방향 검색 | 이전 명령 대화형 검색 |
| `Ctrl+V` 또는 `Cmd+V`(iTerm2) 또는 `Alt+V`(Windows/WSL) | 클립보드 이미지 붙여넣기 | 커서 위치에 `[Image #N]` chip 삽입. WSL은 둘 다 바인딩, `Ctrl+V`를 터미널이 가로채면 `Alt+V` 사용 |
| `Ctrl+B` | 실행 중 작업 백그라운드화 | bash 명령·에이전트 백그라운드화. Tmux 사용자는 두 번 |
| `Ctrl+T` | task list 토글 | 터미널 상태 영역의 task list 표시/숨김 |
| `Left/Right arrows` | 대화상자 탭 순환 | 권한 대화상자·메뉴 탭 이동 |
| `Up/Down arrows` 또는 `Ctrl+P`/`Ctrl+N` | 커서 이동 또는 명령 이력 탐색 | 멀티라인 입력에서 먼저 프롬프트 내 커서 이동, 위/아래 끝에서 다시 누르면 이력 탐색 |
| `Esc` | Claude 중단 | 현재 응답/도구 호출을 턴 중간에 멈추고 리다이렉트. 지금까지 작업은 유지 |
| `Esc` + `Esc` | 입력 초안 지우기 또는 rewind | 입력에 텍스트가 있으면 더블 `Esc`로 지우고 초안을 이력에 저장(`Up`으로 복구). 입력이 비었으면 rewind 메뉴(체크포인트 복원) |
| `Shift+Tab` 또는 `Alt+M`(일부 설정) | 권한 모드 순환 | `default`,`acceptEdits`,`plan` 및 활성화한 모드(`auto`,`bypassPermissions`) 순환 ([[05 권한]]) |
| `Option+P`(macOS) 또는 `Alt+P`(Win/Linux) | 모델 전환 | 프롬프트를 지우지 않고 모델 전환 |
| `Option+T`(macOS) 또는 `Alt+T`(Win/Linux) | 확장 사고(extended thinking) 토글 | v2.1.132부터 macOS에서 Option-as-Meta 설정 없이 동작 |
| `Option+O`(macOS) 또는 `Alt+O`(Win/Linux) | fast mode 토글 | fast mode 켜기/끄기 |

### 텍스트 편집 (Text editing)

| Shortcut | Description | Context |
| :--- | :--- | :--- |
| `Ctrl+A` | 현재 줄 처음으로 커서 이동 | 멀티라인에서 현재 논리 줄의 처음으로 |
| `Ctrl+E` | 현재 줄 끝으로 커서 이동 | 멀티라인에서 현재 논리 줄의 끝으로 |
| `Ctrl+K` | 줄 끝까지 삭제 | 삭제 텍스트를 붙여넣기용으로 저장 |
| `Ctrl+U` | 커서부터 줄 시작까지 삭제 | 저장됨. 멀티라인에서 반복 시 줄 넘어 지움. macOS에서 iTerm2·Terminal.app은 `Cmd+Backspace`를 이 단축키에 매핑 |
| `Ctrl+W` | 이전 단어 삭제 | 저장됨. Windows에서 `Ctrl+Backspace`도 이전 단어 삭제 |
| `Ctrl+Y` | 삭제 텍스트 붙여넣기 | `Ctrl+K`/`Ctrl+U`/`Ctrl+W`로 삭제한 텍스트 붙여넣기 |
| `Alt+Y` (`Ctrl+Y` 후) | 붙여넣기 이력 순환 | 붙여넣기 후 이전 삭제 텍스트 순환. macOS는 Option-as-Meta 필요 |
| `Alt+B` | 단어 단위 뒤로 이동 | macOS는 Option-as-Meta 필요 |
| `Alt+F` | 단어 단위 앞으로 이동 | macOS는 Option-as-Meta 필요 |

### 테마와 디스플레이 / 멀티라인 입력

| Shortcut | Description | Context |
| :--- | :--- | :--- |
| `Ctrl+T` | 코드블록 구문 강조 토글 | `/theme` picker 메뉴 안에서만 동작. Claude 응답의 코드 색상 제어 |

멀티라인 입력 방법:

| Method | Shortcut | Context |
| :--- | :--- | :--- |
| Quick escape | `\` + `Enter` | 모든 터미널에서 동작 |
| Option key | `Option+Enter` | macOS에서 Option-as-Meta 활성화 후 |
| Shift+Enter | `Shift+Enter` | iTerm2, WezTerm, Ghostty, Kitty, Warp, Apple Terminal, Windows Terminal에서 네이티브 |
| Control sequence | `Ctrl+J` | 설정 없이 모든 터미널에서 동작 |
| Paste mode | 직접 붙여넣기 | 코드블록·로그용 |

> [!tip] VS Code, Cursor, Devin Desktop, Alacritty, Zed에서는 `/terminal-setup`을 실행해 Shift+Enter 바인딩을 설치한다.

### 빠른 명령 / 음성 입력

| Shortcut | Description | Notes |
| :--- | :--- | :--- |
| `/` (맨앞) | command 또는 skill | 아래 "명령어" 및 [[07 스킬]] |
| `!` (맨앞) | shell mode | 명령을 직접 실행하고 출력을 세션에 추가 |
| `@` | 파일 경로 멘션 | 파일 경로 자동완성 트리거 |
| `Space` 홀드/탭 | 음성 받아쓰기 | voice dictation 활성화 필요. 홀드로 녹음, `/voice tap`으로 탭-토글. 재바인딩 가능 (아래 "음성 받아쓰기") |

### Transcript viewer

`Ctrl+O`로 transcript viewer를 열면 사용 가능한 단축키다. 풀스크린 렌더링에서 `?`로 전체 단축키 패널을 본다. `Ctrl+E`는 `transcript:toggleShowAll`로 재바인딩 가능.

| Shortcut | Description |
| :--- | :--- |
| `?` | 단축키 도움말 패널 토글 (풀스크린 렌더링 필요) |
| `{` / `}` | 이전/다음 user 프롬프트로 점프 (vim 단락 모션, 풀스크린 필요) |
| `Ctrl+E` | 전체 콘텐츠 표시 토글 |
| `[` | 전체 대화를 터미널 네이티브 스크롤백에 기록해 `Cmd+F`·tmux copy mode 등으로 검색 가능 (풀스크린 필요) |
| `v` | 대화를 임시 파일에 쓰고 `$VISUAL`/`$EDITOR`로 열기 (풀스크린 필요) |
| `q`, `Ctrl+C`, `Esc` | transcript view 종료. 셋 다 `transcript:exit`로 재바인딩 가능 |

---

## 명령어와 vim 에디터 모드

`/`를 입력하면 사용 가능한 모든 command가 보이고, `/` 뒤에 글자를 입력해 필터링한다. `/` 메뉴는 내장 command, 번들·사용자 작성 [[07 스킬]], [[11 플러그인]]·[[10 MCP]]가 기여한 command를 모두 보여준다. 전체 command 목록은 별도 commands 레퍼런스 참고.

### Vim 에디터 모드

`/config` → Editor mode로 vim 스타일 편집을 활성화한다. (활성화는 아래 "터미널 설정"에서도 다룸. 설정 키 `editorMode`는 [[04 설정]].)

**모드 전환**

| Command | Action | From mode |
| :--- | :--- | :--- |
| `Esc` | NORMAL 모드 진입 | INSERT, VISUAL |
| `i` / `I` | 커서 앞 / 줄 시작에 삽입 | NORMAL |
| `a` / `A` | 커서 뒤 / 줄 끝에 삽입 | NORMAL |
| `o` / `O` | 아래 / 위에 줄 열기 | NORMAL |
| `v` / `V` | 문자 단위 / 줄 단위 visual 선택 시작 | NORMAL |

**탐색 (NORMAL)**

| Command | Action |
| :--- | :--- |
| `h`/`j`/`k`/`l` | 좌/하/상/우 이동 |
| `Space` | 우 이동 |
| `w` / `e` / `b` | 다음 단어 / 단어 끝 / 이전 단어 |
| `0` / `$` / `^` | 줄 시작 / 줄 끝 / 첫 비공백 문자 |
| `gg` / `G` | 입력 시작 / 입력 끝 |
| `f{char}` / `F{char}` | 다음 / 이전 문자 occurrence로 점프 |
| `t{char}` / `T{char}` | 다음 / 이전 문자 직전·직후로 점프 |
| `;` / `,` | 마지막 f/F/t/T 모션 반복 / 역방향 반복 |
| `/` | 역방향 이력 검색 (`Ctrl+R`과 동일) |

> [!note] vim NORMAL 모드에서 커서가 입력 처음/끝에 있어 더 못 움직이면 `j`/`k`와 화살표 키가 명령 이력을 탐색한다.

**편집 (NORMAL)**

| Command | Action |
| :--- | :--- |
| `x` / `dd` / `D` | 문자 삭제 / 줄 삭제 / 줄 끝까지 삭제 |
| `dw`/`de`/`db` | 단어/끝까지/뒤로 삭제 |
| `cc` / `C` | 줄 변경 / 줄 끝까지 변경 |
| `cw`/`ce`/`cb` | 단어/끝까지/뒤로 변경 |
| `yy`/`Y` / `yw`/`ye`/`yb` | 줄 yank / 단어·끝·뒤 yank |
| `p` / `P` | 커서 뒤 / 앞 붙여넣기 |
| `>>` / `<<` | 들여쓰기 / 내어쓰기 |
| `J` / `u` / `.` | 줄 합치기 / undo / 마지막 변경 반복 |

**텍스트 객체 (NORMAL)** — `d`,`c`,`y` 같은 operator와 함께 동작:

| Command | Action |
| :--- | :--- |
| `iw`/`aw` | 단어 inner/around |
| `iW`/`aW` | WORD(공백 구분) inner/around |
| `i"`/`a"`, `i'`/`a'` | 큰/작은따옴표 inner/around |
| `i(`/`a(`, `i[`/`a[`, `i{`/`a{` | 괄호/대괄호/중괄호 inner/around |

**Visual 모드** — `v`(문자) / `V`(줄) 선택. 모션이 선택을 확장하고 operator가 직접 작용:

| Command | Action |
| :--- | :--- |
| `d`/`x` / `y` / `c`/`s` | 선택 삭제 / yank / 변경 |
| `p` | 선택을 register 내용으로 교체 |
| `r{char}` | 선택된 모든 문자를 `{char}`로 교체 |
| `~`/`u`/`U` | 선택 토글/소문자/대문자 |
| `>`/`<` / `J` | 선택 줄 들여/내어쓰기 / 합치기 |
| `o` | 커서와 anchor 교환 |
| `v`/`V` | 문자↔줄 단위 토글 또는 종료 |

> [!warning] `Ctrl+V` 블록 단위 visual 모드는 지원되지 않는다.

---

## 명령 이력·셸 모드·세션 기능 (대화형 모드)

### 명령 이력과 Ctrl+R 역방향 검색

- 입력 이력은 작업 디렉터리별로 저장된다. `/clear`로 새 세션을 시작하면 이력이 리셋되지만 이전 대화는 보존돼 재개 가능하다.
- 같은 프롬프트를 연속 두 번 제출하면 이력 항목 1개로 기록된다.
- history expansion(`!`)은 기본 비활성화.

`Ctrl+R` 흐름: ① `Ctrl+R`로 검색 시작 → ② 검색어 입력(매치는 강조) → ③ `Ctrl+R` 재차로 더 오래된 매치 순환 → ④ `Ctrl+S`로 scope 순환(this session → this project → all projects, 기본은 all projects) → ⑤ `Tab`/`Esc`로 매치 수락 후 편집 또는 `Enter`로 즉시 실행 → ⑥ `Ctrl+C` 또는 빈 검색에서 `Backspace`로 취소.

### 백그라운드 bash와 `!` 셸 모드

Claude Code는 bash 명령을 백그라운드로 실행해 긴 프로세스 중에도 작업을 계속할 수 있다. 백그라운드화 방법은 ① Claude에게 백그라운드 실행을 프롬프트하거나 ② Bash 도구 호출 중 `Ctrl+B`를 누르는 것이다(tmux 사용자는 prefix 키 때문에 두 번).

주요 특성: 출력은 파일에 기록돼 Claude가 Read 도구로 회수, 각 작업은 고유 ID, 종료 시 자동 정리, 출력이 5GB 초과 시 자동 종료(stderr에 사유 기록). 전체 비활성화는 `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`. 흔히 백그라운드화하는 명령: 빌드 도구(webpack/vite/make), 패키지 매니저(npm/yarn/pnpm), 테스트 러너(jest/pytest), 개발 서버, 장기 프로세스(docker/terraform).

`!` 접두사로 셸 명령을 Claude를 거치지 않고 직접 실행한다.

```bash
! npm test
! git status
! ls -la
```

셸 모드는 명령과 출력을 대화 컨텍스트에 추가, 실시간 진행 표시, `Ctrl+B` 백그라운드화 지원, Claude의 해석·승인 불필요, **Tab** 히스토리 자동완성(이 프로젝트의 이전 `!` 명령), 빈 프롬프트에서 `Escape`/`Backspace`/`Ctrl+U`로 종료. `!`로 시작하는 텍스트를 빈 프롬프트에 붙여넣으면 자동으로 셸 모드 진입.

### 프롬프트 제안 (prompt suggestions)

세션을 처음 열면 git 이력 기반의 회색 예시 명령이 입력창에 뜬다. Claude 응답 후에도 대화 이력 기반 제안이 이어진다. **Tab** 또는 **Right arrow**로 입력에 넣고 **Enter**로 제출, 타이핑 시작 시 dismiss. 제안은 부모 대화의 prompt cache를 재사용하는 백그라운드 요청이라 추가 비용이 미미하고, cache가 cold면 생성을 건너뛴다. 첫 턴 후·plan mode에서 자동 생략, print mode에서는 기본 off(`--prompt-suggestions` + `--output-format stream-json --verbose`로 `prompt_suggestion` emit).

전체 비활성화:

```bash
export CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false
```

### 곁다리 질문 `/btw`

`/btw`는 대화 이력에 추가하지 않고 현재 작업에 대한 빠른 질문을 한다. 현재 대화 전체를 보지만 **도구 접근은 없다**(이미 컨텍스트에 있는 것만 답함). Claude가 작업 중에도 실행 가능하며 메인 턴을 방해하지 않는다. 질문/답변은 ephemeral(닫을 수 있는 overlay에 표시, 이력에 들어가지 않음).

```
/btw what was the name of that config file again?
```

overlay 키:

| Key | Action |
| :--- | :--- |
| `Space`, `Enter`, `Escape` | 답변 닫고 프롬프트 복귀 |
| `Up`/`Down` | 답변 스크롤 |
| `c` | 답변을 raw Markdown으로 클립보드 복사 |
| `f` | 새 세션으로 fork (부모 대화 + Q&A를 실제 transcript로 상속, 풀 도구 접근). 로컬 세션 전용 |
| `x` | 위에 표시된 이전 `/btw` 교환 목록 지우기 |

`/btw`는 [[08 서브에이전트와 에이전트 팀]]의 서브에이전트와 정반대다 — 곁다리는 전체 대화를 보지만 도구가 없고, 서브에이전트는 풀 도구를 갖되 빈 컨텍스트로 시작한다.

### Task list / Session recap / PR review status

- **Task list**: 복잡한 다단계 작업 시 Claude가 진행 추적용 task list를 생성. `Ctrl+T`로 토글(최대 5개 표시). 전체 보기/지우기는 "show me all tasks"/"clear all tasks". 컨텍스트 압축에도 지속. 세션 간 공유는 `CLAUDE_CODE_TASK_LIST_ID=my-project claude`(`~/.claude/tasks/`의 명명 디렉터리).
- **Session recap**: 자리를 비웠다 돌아오면 한 줄 요약 표시. 마지막 턴 후 3분 경과·터미널 unfocus·최소 3턴일 때 백그라운드 생성, 연속 두 번은 안 함. `/recap`으로 온디맨드 생성. `/config`에서 끌 수 있음. 모든 plan·provider에서 기본 on, 비대화형에서는 항상 생략.
- **PR review status**: open PR이 있는 브랜치 작업 시 footer에 클릭 가능한 PR 링크("PR #446") 표시. 밑줄 색: 초록=approved, 노랑=pending, 빨강=changes requested, 회색=draft. merge/close 시 사라짐. `Cmd+click`(Mac)/`Ctrl+click`(Win/Linux)로 브라우저 열기. 60초마다 + `gh pr`/`git push` 직후 새로고침. `gh` CLI 설치·인증 필요. (CI 통합은 [[16 CI-CD와 팀 통합]])

---

## 키바인딩 커스터마이징 (keybindings)

> [!note] 커스텀 키바인딩은 Claude Code v2.1.18 이상 필요. `claude --version`으로 확인.

`/keybindings`를 실행하면 `~/.claude/keybindings.json`을 생성/열 수 있다. 파일 변경은 재시작 없이 자동 감지·적용된다.

### 설정 파일 구조

설정 파일은 `bindings` 배열을 가진 객체다. 각 블록은 context와 keystroke→action 맵을 지정한다.

| Field | Description |
| :--- | :--- |
| `$schema` | (선택) 에디터 자동완성용 JSON Schema URL |
| `$docs` | (선택) 문서 URL |
| `bindings` | context별 binding 블록 배열 |

`Ctrl+E`를 Chat 컨텍스트의 외부 에디터 열기에 바인딩하고 `Ctrl+U`를 해제하는 예시:

```json
{
  "$schema": "https://www.schemastore.org/claude-code-keybindings.json",
  "$docs": "https://code.claude.com/docs/en/keybindings",
  "bindings": [
    {
      "context": "Chat",
      "bindings": {
        "ctrl+e": "chat:externalEditor",
        "ctrl+u": null
      }
    }
  ]
}
```

### Contexts (컨텍스트 목록)

각 binding 블록은 적용 context를 지정한다.

| Context | Description |
| :--- | :--- |
| `Global` | 앱 전역 |
| `Chat` | 메인 채팅 입력 영역 |
| `Autocomplete` | 자동완성 메뉴 열림 |
| `Settings` | 설정 메뉴 |
| `Confirmation` | 권한·확인 대화상자 |
| `Tabs` | 탭 네비게이션 컴포넌트 |
| `Help` | 도움말 메뉴 표시 |
| `Transcript` | transcript viewer |
| `HistorySearch` | 이력 검색 모드(Ctrl+R) |
| `Task` | 백그라운드 task 실행 중 |
| `ThemePicker` | 테마 picker 대화상자 |
| `Attachments` | select 대화상자의 이미지 첨부 네비게이션 |
| `Footer` | footer indicator 네비게이션(tasks, teams, diff) |
| `MessageSelector` | rewind·summarize 대화상자 메시지 선택 |
| `DiffDialog` | diff viewer 네비게이션 |
| `ModelPicker` | 모델 picker effort level |
| `Select` | 일반 select/list 컴포넌트 |
| `Plugin` | 플러그인 대화상자(browse, discover, manage) |
| `Scroll` | 풀스크린 모드의 대화 스크롤·텍스트 선택 |
| `Doctor` | `/doctor` 진단 화면 |

### 사용 가능한 액션 (actions)

액션은 `namespace:action` 형식이다(예: `chat:submit`, `app:toggleTodos`).

**App (`Global`)**

| Action | Default | Description |
| :--- | :--- | :--- |
| `app:interrupt` | Ctrl+C | 현재 작업 취소 |
| `app:exit` | Ctrl+D | Claude Code 종료 |
| `app:redraw` | (unbound) | 터미널 강제 redraw |
| `app:toggleTodos` | Ctrl+T | task list 토글 |
| `app:toggleTranscript` | Ctrl+O | verbose transcript 토글 |

**History**

| Action | Default | Description |
| :--- | :--- | :--- |
| `history:search` | Ctrl+R | 이력 검색 열기 |
| `history:previous` | Up | 이전 이력 항목 |
| `history:next` | Down | 다음 이력 항목 |

**Chat**

| Action | Default | Description |
| :--- | :--- | :--- |
| `chat:cancel` | Escape | 현재 입력 취소 |
| `chat:clearInput` | Ctrl+L | 전체 redraw(입력 보존). 풀스크린에서 2초 내 두 번 누르면 `/clear` |
| `chat:clearScreen` | Cmd+K | 풀스크린에서 2초 내 두 번 누르면 `/clear` |
| `chat:killAgents` | Ctrl+X Ctrl+K | 이 세션의 모든 백그라운드 서브에이전트 종료 |
| `chat:cycleMode` | Shift+Tab\* | 권한 모드 순환 |
| `chat:modelPicker` | Meta+P | 모델 picker 열기 |
| `chat:fastMode` | Meta+O | fast mode 토글 |
| `chat:thinkingToggle` | Meta+T | 확장 사고 토글 |
| `chat:submit` | Enter | 메시지 제출 |
| `chat:newline` | Ctrl+J | 제출 없이 줄바꿈 삽입 |
| `chat:undo` | Ctrl+\_, Ctrl+Shift+- | 마지막 액션 undo |
| `chat:externalEditor` | Ctrl+G, Ctrl+X Ctrl+E | 외부 에디터에서 열기 |
| `chat:stash` | Ctrl+S | 현재 프롬프트 stash |
| `chat:imagePaste` | Ctrl+V (Win/WSL은 Alt+V) | 클립보드 이미지 붙여넣기. WSL은 둘 다 바인딩 |

\* VT 모드 없는 Windows(Node <24.2.0/<22.17.0, Bun <1.2.23)에서는 기본 Meta+M.

**Autocomplete**

| Action | Default | Description |
| :--- | :--- | :--- |
| `autocomplete:accept` | Tab | 제안 수락 |
| `autocomplete:dismiss` | Escape | 메뉴 닫기 |
| `autocomplete:previous` / `autocomplete:next` | Up / Down | 이전/다음 제안 |

**Confirmation**

| Action | Default | Description |
| :--- | :--- | :--- |
| `confirm:yes` | Y, Enter | 액션 확인 |
| `confirm:no` | N, Escape | 액션 거부 |
| `confirm:previous` / `confirm:next` | Up / Down | 이전/다음 옵션 |
| `confirm:nextField` | Tab | 다음 필드 |
| `confirm:previousField` | (unbound) | 이전 필드 |
| `confirm:toggle` | Space | 선택 토글 |
| `confirm:cycleMode` | Shift+Tab | 권한 모드 순환 |
| `confirm:toggleExplanation` | Ctrl+E | 권한 설명 토글 |

**Permission (`Confirmation`)**

| Action | Default | Description |
| :--- | :--- | :--- |
| `permission:toggleDebug` | (unbound) | 권한 디버그 정보 토글. 이전 기본값 Ctrl+D는 `app:exit`와 충돌해 v2.1.146에서 제거 |

**Transcript**

| Action | Default | Description |
| :--- | :--- | :--- |
| `transcript:toggleShowAll` | Ctrl+E | 전체 콘텐츠 표시 토글 |
| `transcript:exit` | q, Ctrl+C, Escape | transcript view 종료 |

**HistorySearch**

| Action | Default | Description |
| :--- | :--- | :--- |
| `historySearch:next` | Ctrl+R | 다음 매치 |
| `historySearch:accept` | Escape, Tab | 선택 수락 |
| `historySearch:cancel` | Ctrl+C | 검색 취소 |
| `historySearch:execute` | Enter | 선택 명령 실행 |
| `historySearch:cycleScope` | Ctrl+S | scope 순환(session, project, everywhere) |

**Task / Theme / Help**

| Action | Default | Description |
| :--- | :--- | :--- |
| `task:background` | Ctrl+B | 현재 task 백그라운드화 |
| `theme:toggleSyntaxHighlighting` | Ctrl+T | 구문 강조 토글 (`ThemePicker`) |
| `help:dismiss` | Escape | 도움말 메뉴 닫기 (`Help`) |

**Tabs / Attachments / Footer**

| Action | Default | Description |
| :--- | :--- | :--- |
| `tabs:next` / `tabs:previous` | Tab, Right / Shift+Tab, Left | 다음/이전 탭 |
| `attachments:next` / `attachments:previous` | Right / Left | 다음/이전 첨부 |
| `attachments:remove` | Backspace, Delete | 선택 첨부 제거 |
| `attachments:exit` | Down, Escape | 첨부 네비게이션 종료 |
| `footer:next` / `footer:previous` | Right / Left | 다음/이전 footer 항목 |
| `footer:up` / `footer:down` | Up / Down | footer 위/아래 (위에서 deselect) |
| `footer:openSelected` | Enter | 선택 footer 항목 열기 |
| `footer:clearSelection` | Escape | footer 선택 해제 |

**MessageSelector**

| Action | Default | Description |
| :--- | :--- | :--- |
| `messageSelector:up` | Up, K, Ctrl+P | 위로 |
| `messageSelector:down` | Down, J, Ctrl+N | 아래로 |
| `messageSelector:top` | Ctrl+Up, Shift+Up, Meta+Up, Shift+K | 맨 위로 |
| `messageSelector:bottom` | Ctrl+Down, Shift+Down, Meta+Down, Shift+J | 맨 아래로 |
| `messageSelector:select` | Enter | 메시지 선택 |

**DiffDialog**

| Action | Default | Description |
| :--- | :--- | :--- |
| `diff:dismiss` | Escape | diff viewer 닫기 |
| `diff:previousSource` / `diff:nextSource` | Left / Right | 이전/다음 diff 소스 |
| `diff:previousFile` | Up, K | 이전 파일 / 디테일에서 한 줄 위 스크롤 |
| `diff:nextFile` | Down, J | 다음 파일 / 디테일에서 한 줄 아래 스크롤 |
| `diff:viewDetails` | Enter | diff 디테일 보기 |
| `diff:back` | (context-specific) | diff viewer에서 뒤로 |

diff 디테일 뷰는 pager 스타일 키를 표준 scroll 액션에 바인딩한다(`scroll:pageUp`=PageUp, `scroll:pageDown`=PageDown, `scroll:fullPageUp`=Shift+Space/B, `scroll:fullPageDown`=Space, `scroll:top`=G/Home, `scroll:bottom`=Shift+G/End). 이는 `DiffDialog` 컨텍스트의 일부로 디테일 뷰에서만 적용된다.

**ModelPicker / Select**

| Action | Default | Description |
| :--- | :--- | :--- |
| `modelPicker:decreaseEffort` / `modelPicker:increaseEffort` | Left / Right | effort level 감소/증가 |
| `modelPicker:thisSessionOnly` | s | 강조된 모델을 이 세션에만 적용 |
| `select:next` | Down, J, Ctrl+N | 다음 옵션 |
| `select:previous` | Up, K, Ctrl+P | 이전 옵션 |
| `select:accept` / `select:cancel` | Enter / Escape | 선택 수락 / 취소 |

**Plugin / Settings / Doctor**

| Action | Default | Description |
| :--- | :--- | :--- |
| `plugin:toggle` | Space | 플러그인 선택 토글 |
| `plugin:install` | I | 선택 플러그인 설치 |
| `plugin:favorite` | F | 플러그인 즐겨찾기(Installed 탭 상단 정렬) |
| `settings:search` | / | 검색 모드 진입 |
| `settings:retry` | R | usage 데이터 재로드 (에러 시) |
| `settings:close` | Enter | 변경 저장 후 닫기. Escape는 변경 폐기 |
| `doctor:fix` | F | 진단 보고서를 Claude에 보내 수정. 이슈 발견 시에만 활성 |

**Voice (`Chat`, voice dictation 활성화 시)**

| Action | Default | Description |
| :--- | :--- | :--- |
| `voice:pushToTalk` | Space | 프롬프트 받아쓰기. `/voice` 모드에 따라 hold 또는 tap |

**Scroll (`Scroll`, 풀스크린 렌더링 시)**

| Action | Default | Description |
| :--- | :--- | :--- |
| `scroll:lineUp` / `scroll:lineDown` | (unbound) | 한 줄 위/아래 스크롤. 마우스 휠이 트리거 |
| `scroll:pageUp` / `scroll:pageDown` | PageUp / PageDown | viewport 절반 위/아래 |
| `scroll:top` | Ctrl+Home | 대화 시작으로 |
| `scroll:bottom` | Ctrl+End | 최신 메시지로 + auto-follow 재개 |
| `scroll:halfPageUp` / `scroll:halfPageDown` | (unbound) | 절반 위/아래(vi 스타일 재바인딩용) |
| `scroll:fullPageUp` / `scroll:fullPageDown` | (unbound) | 전체 viewport 위/아래 |
| `selection:copy` | Ctrl+Shift+C / Cmd+C | 선택 텍스트 클립보드 복사 |
| `selection:clear` | (unbound) | 활성 선택 해제 |
| `selection:extendLeft` / `extendRight` | Shift+Left / Shift+Right | 선택을 한 칸 좌/우 확장 |
| `selection:extendUp` / `extendDown` | Shift+Up / Shift+Down | 한 행 위/아래 확장(가장자리에서 스크롤) |
| `selection:extendLineStart` / `extendLineEnd` | Shift+Home / Shift+End | 줄 시작/끝까지 확장 |

### Keystroke 문법

**Modifiers** (`+`로 연결):

- `ctrl`/`control` — Control 키
- `shift` — Shift 키
- `alt`/`opt`/`option`/`meta` — Windows·Linux의 Alt, macOS의 Option
- `cmd`/`command`/`super`/`win` — macOS Command, Windows Windows 키, Linux Super 키

`cmd` 그룹은 Super modifier를 보고하는 터미널(Kitty 키보드 프로토콜, xterm `modifyOtherKeys` 모드)에서만 감지된다. 대부분의 터미널은 보내지 않으므로 어디서나 동작하려면 `ctrl`이나 `meta`를 쓴다.

```text
ctrl+k          Ctrl + K
shift+tab       Shift + Tab
meta+p          macOS는 Option + P, 그 외는 Alt + P
ctrl+shift+c    여러 modifier
```

**대문자**: 단독 대문자는 Shift를 함의한다(`K` = `shift+k`). 단, modifier가 붙은 대문자(`ctrl+K`)는 양식상일 뿐 Shift를 함의하지 않아 `ctrl+k`와 같다.

**Chords**: 공백으로 구분된 keystroke 시퀀스. `ctrl+k ctrl+s` = Ctrl+K 누르고 떼고 Ctrl+S.

**특수 키**: `escape`/`esc`, `enter`/`return`, `tab`, `space`, `up`/`down`/`left`/`right`, `backspace`/`delete`.

### 기본 단축키 해제와 chord prefix

액션을 `null`로 설정하면 기본 단축키를 해제한다.

```json
{ "bindings": [ { "context": "Chat", "bindings": { "ctrl+s": null } } ] }
```

특정 prefix를 공유하는 chord를 모두 해제하면 그 prefix를 단일 키 바인딩으로 쓸 수 있다.

```json
{
  "bindings": [
    {
      "context": "Chat",
      "bindings": {
        "ctrl+x ctrl+k": null,
        "ctrl+x ctrl+e": null,
        "ctrl+x": "chat:newline"
      }
    }
  ]
}
```

일부 chord만 해제하면 prefix를 눌렀을 때 남은 binding을 위한 chord-wait 모드로 여전히 진입한다.

### 재바인딩 불가·터미널 충돌·vim 상호작용·검증

**재바인딩 불가 (Reserved)**

| Shortcut | Reason |
| :--- | :--- |
| Ctrl+C | 하드코딩된 interrupt/cancel |
| Ctrl+D | 하드코딩된 exit |
| Ctrl+M | 터미널에서 Enter와 동일(둘 다 CR 전송) |
| Caps Lock | 터미널 앱에 전달되지 않음 |

**터미널 멀티플렉서 충돌**

| Shortcut | Conflict |
| :--- | :--- |
| Ctrl+B | tmux prefix (두 번 눌러 전송) |
| Ctrl+A | GNU screen prefix |
| Ctrl+Z | Unix 프로세스 suspend (SIGTSTP) |

**Vim 모드 상호작용** — vim 모드(`/config` → Editor mode)와 keybindings는 독립 동작한다. vim 모드는 입력 레벨(커서·모드·모션), keybindings는 컴포넌트 레벨(toggle todos, submit 등)을 처리한다. vim에서 Escape는 INSERT→NORMAL 전환이지 `chat:cancel`을 트리거하지 않는다. 대부분의 Ctrl+키는 vim을 통과해 keybinding 시스템으로 간다. vim NORMAL에서 `?`는 도움말, `/`는 이력 검색(Ctrl+R과 동일)이다.

**검증** — Claude Code는 parse 에러, 잘못된 context 이름, reserved 충돌, 멀티플렉서 충돌, 동일 context 중복 바인딩에 경고한다. `/doctor`로 경고를 확인한다. (진단 도구는 [[25 트러블슈팅]])

---

## 터미널 설정 (terminal-config)

Claude Code는 설정 없이 어떤 터미널에서도 동작한다. 이 섹션은 특정 동작이 기대와 다를 때만 필요하다. 여기서 다루는 건 터미널이 Claude Code에 올바른 신호를 보내게 하는 것이고, Claude Code가 어떤 키에 반응할지 바꾸려면 위 "키바인딩 커스터마이징"을 본다.

### 멀티라인 프롬프트 입력

Enter는 제출, 줄바꿈은 `Ctrl+J` 또는 `\` 후 Enter(모든 터미널에서 설정 없이 동작). 대부분 터미널에서 Shift+Enter도 되지만 emulator마다 다르다.

| Terminal | Shift+Enter for newline |
| :--- | :--- |
| Ghostty, Kitty, iTerm2, WezTerm, Warp, Apple Terminal, Windows Terminal | 설정 없이 동작 |
| VS Code, Cursor, Devin Desktop, Alacritty, Zed | `/terminal-setup`을 한 번 실행 |
| gnome-terminal, JetBrains IDE(PyCharm, Android Studio 등) | 불가능; Ctrl+J 또는 `\` 후 Enter 사용 |

`/terminal-setup`은 VS Code·Cursor·Devin Desktop·Alacritty·Zed의 설정 파일에 Shift+Enter 등 바인딩을 기록한다(기존 바인딩 유지). tmux/screen 안이 아닌 호스트 터미널에서 직접 실행해야 한다. VS Code·Cursor·Devin Desktop에서는 `terminal.integrated.gpuAcceleration`을 `"off"`(통합 터미널 텍스트 깨짐 방지), `terminal.integrated.mouseWheelScrollSensitivity`(풀스크린 부드러운 스크롤)도 함께 설정한다. GPU 변경 되돌리려면 `"auto"`로 복구 후 창 reload. tmux 안에서는 외부 터미널이 지원해도 아래 tmux 설정이 추가로 필요하다. 줄바꿈을 다른 키에 바인딩하거나 Enter↔Shift+Enter 동작을 바꾸려면 keybindings 파일에서 `chat:newline`·`chat:submit`을 매핑한다.

### macOS Option 키 단축키 활성화

Option+Enter(줄바꿈), Option+P(모델 전환) 등 일부 단축키는 Option 키를 쓴다. macOS 대부분 터미널은 기본으로 Option을 modifier로 보내지 않아 활성화 전까지 동작하지 않는다. 설정 라벨은 보통 "Use Option as Meta Key"다(Meta는 지금의 Option/Alt의 역사적 Unix 이름).

- **Apple Terminal**: Settings → Profiles → Keyboard → "Use Option as Meta Key" 체크. 첫 실행 시 "Option+Enter for newlines and visual bell" 프롬프트를 수락했다면 이미 됨(그 프롬프트가 `/terminal-setup`을 실행해 Option-as-Meta 활성화 + 오디오 벨을 visual flash로 전환).
- **iTerm2**: Settings → Profiles → Keys → General → Left/Right Option key를 "Esc+". iTerm2에서 `/terminal-setup` 실행 시 "Applications in terminal may access clipboard"도 켜져 `/copy`가 시스템 클립보드에 쓸 수 있게 됨(tmux 안에서도 iTerm2 감지). 변경 적용은 iTerm2 재시작.
- **VS Code**: 설정에 `"terminal.integrated.macOptionIsMeta": true` 추가.
- Ghostty·Kitty 등은 설정 파일에서 Option-as-Alt/Option-as-Meta 설정을 찾는다.

### 터미널 벨·알림

Claude가 작업을 마치거나 권한 프롬프트에서 멈추면 notification 이벤트를 발생시킨다. 기본적으로 데스크톱 알림은 Ghostty·Kitty·iTerm2에서만 전송한다. 다른 터미널은 `preferredNotifChannel`을 `"terminal_bell"`로 설정해 벨을 울리거나 Notification hook을 구성한다. SSH 너머에서도 데스크톱 알림은 로컬 머신에 도달한다. Ghostty·Kitty는 OS 알림 센터로 자동 전달, iTerm2는 forwarding 활성화 필요(Settings → Profiles → Terminal → "Notification Center Alerts" 체크 → "Filter Alerts"에서 "Send escape sequence-generated alerts" 활성화). 알림이 안 보이면 OS 설정의 터미널 알림 권한 확인, tmux 안이면 passthrough 활성화.

**Notification hook으로 사운드 재생** — 어떤 터미널에서도 [[09 훅]]의 Notification hook으로 사운드/커스텀 명령을 실행할 수 있다. hook은 내장 알림을 대체하지 않고 함께 실행되므로, 데스크톱 알림을 못 받는 Warp·VS Code 통합 터미널도 hook이나 `terminal_bell`을 쓸 수 있다.

```json ~/.claude/settings.json
{
  "hooks": {
    "Notification": [
      {
        "hooks": [{ "type": "command", "command": "afplay /System/Library/Sounds/Glass.aiff" }]
      }
    ]
  }
}
```

### tmux 설정

tmux 안에서는 기본적으로 두 가지가 깨진다: Shift+Enter가 줄바꿈 대신 제출되고, 데스크톱 알림·progress bar가 외부 터미널에 도달하지 못한다. `~/.tmux.conf`에 추가 후 `tmux source-file ~/.tmux.conf`로 적용:

```bash ~/.tmux.conf
set -g allow-passthrough on
set -s extended-keys on
set -as terminal-features 'xterm*:extkeys'
```

`allow-passthrough`는 알림·progress가 외부 터미널에 도달하게 하고, `extended-keys` 두 줄은 tmux가 Shift+Enter와 Enter를 구별하게 한다.

### 컬러 테마 맞추기

`/theme` 명령 또는 `/config`의 테마 picker로 터미널에 맞는 Claude Code 테마를 고른다. auto 옵션은 터미널의 밝음/어둠 배경을 감지해 OS 외관 변경을 따른다. Claude Code는 터미널 자체 색 구성을 제어하지 않는다(터미널 앱이 설정). 하단 인터페이스 커스터마이징은 [[12 출력 스타일과 상태줄]]의 custom status line 참고.

**커스텀 테마** (v2.1.118 이상): `/theme`는 내장 preset 외에 정의한 커스텀 테마와 플러그인 기여 테마를 나열한다. 목록 끝의 **New custom theme…**로 대화형 생성(이름 지정 후 color token 선택). 강조된 커스텀 테마에서 `Ctrl+E`로 편집. 각 테마는 `~/.claude/themes/`의 JSON 파일이고, `.json` 제외 파일명이 slug, 선택 시 `custom:<slug>`가 테마 선호로 저장된다.

| Field | Type | Description |
| :--- | :--- | :--- |
| `name` | string | `/theme`에 표시될 라벨. 기본은 파일명 slug |
| `base` | string | 시작 preset: `dark`, `light`, `dark-daltonized`, `light-daltonized`, `dark-ansi`, `light-ansi`. 기본 `dark` |
| `overrides` | object | color token명→색상값 맵. 미지정 token은 base preset으로 fall through |

색상값은 `#rrggbb`, `#rgb`, `rgb(r,g,b)`, `ansi256(n)`, `ansi:<name>`(16 표준 ANSI 이름, 예 `red`·`cyanBright`)을 허용한다. 알 수 없는 token·잘못된 값은 무시되므로 오타가 렌더링을 깨지 않는다.

```json ~/.claude/themes/dracula.json
{
  "name": "Dracula",
  "base": "dark",
  "overrides": {
    "claude": "#bd93f9",
    "error": "#ff5555",
    "success": "#50fa7b"
  }
}
```

Claude Code는 `~/.claude/themes/`를 watch해 파일 변경 시 재시작 없이 적용한다. override 가능한 주요 color token 그룹: **텍스트·accent**(`claude`=브랜드 accent/spinner, `text`, `inverseText`, `inactive`, `subtle`, `suggestion`, `permission`, `remember`), **상태**(`success`, `error`, `warning`, `merged`), **입력박스·모드 indicator**(`promptBorder`, `planMode`, `autoAccept`, `bashBorder`, `ide`, `fastMode`), **diff 렌더링**(`diffAdded`, `diffRemoved`, `diffAddedDimmed`, `diffRemovedDimmed`, `diffAddedWord`, `diffRemovedWord`), **풀스크린 전용**(`userMessageBackground`, `userMessageBackgroundHover`, `messageActionsBackground`, `bashMessageBackgroundColor`, `memoryBackgroundColor`, `selectionBg`), **usage meter·라벨**(`rate_limit_fill`, `rate_limit_empty`, `briefLabelYou`, `briefLabelClaude`). 여러 token은 spinner gradient용 shimmer 변형 쌍(`claudeShimmer` 등)을 갖고, 서브에이전트는 `<color>_FOR_SUBAGENTS_ONLY`(red/blue/green/yellow/purple/orange/pink/cyan 8색), `ultrathink`·`ultraplan` 키워드는 `rainbow_<color>`·`rainbow_<color>_shimmer`(7색) gradient로 렌더된다.

### 풀스크린 렌더링 전환 / 대용량 붙여넣기

- **풀스크린 전환**: 화면이 깜빡이거나 스크롤 위치가 튀면 풀스크린 렌더링 모드로 전환한다(아래 "풀스크린 렌더링" 섹션). `/tui fullscreen`으로 현재 세션에서 전환(대화 유지), 기본값으로 만들려면 시작 전 `CLAUDE_CODE_NO_FLICKER` 환경변수 설정.

```bash
CLAUDE_CODE_NO_FLICKER=1 claude
```
```powershell
$env:CLAUDE_CODE_NO_FLICKER = "1"; claude
```
```json ~/.claude/settings.json
{ "env": { "CLAUDE_CODE_NO_FLICKER": "1" } }
```

- **대용량 붙여넣기**: 10,000자 초과를 붙여넣으면 입력을 `[Pasted text]` placeholder로 접지만 제출 시 전체 내용이 전송된다. VS Code 통합 터미널은 매우 큰 붙여넣기에서 문자를 drop할 수 있으니 파일 기반 워크플로(파일로 쓰고 Claude에게 읽게 함)를 선호한다.

### Vim 키바인딩으로 프롬프트 편집

`/config` → Editor mode 또는 `~/.claude/settings.json`의 `editorMode`를 `"vim"`으로 설정해 활성화한다(끄려면 `normal`). vim 모드는 NORMAL·VISUAL 모션·operator의 부분집합(`hjkl`, `v`/`V`, `d`/`c`/`y` + 텍스트 객체)을 지원한다. 전체 키 표는 위 "Vim 에디터 모드" 참고. vim 모션은 keybindings 파일로 remap할 수 없다. INSERT 모드에서 Enter는 여전히 제출하므로(표준 Vim과 다름), 줄바꿈은 NORMAL에서 `o`/`O` 또는 Ctrl+J를 쓴다.

---

## 풀스크린 렌더링 (fullscreen)

> [!note] 풀스크린 렌더링은 opt-in research preview이며 v2.1.89 이상 필요. `/tui fullscreen`으로 현재 대화에서 전환, v2.1.110 이전에는 `CLAUDE_CODE_NO_FLICKER=1` 설정. 동작은 피드백에 따라 변할 수 있다.

풀스크린 렌더링은 깜빡임을 없애고 긴 대화에서 메모리를 평탄하게 유지하며 마우스 지원을 추가하는 대안 렌더링 경로다. `vim`이나 `htop`처럼 터미널의 alternate screen buffer에 인터페이스를 그리고 현재 보이는 메시지만 렌더링한다. VS Code 통합 터미널, tmux, iTerm2처럼 렌더링 처리량이 병목인 emulator에서 차이가 가장 크다.

> [!note] "fullscreen"은 `vim`처럼 터미널 그리기 표면을 점유한다는 의미일 뿐, 터미널 창을 최대화하는 것과 무관하며 어떤 창 크기에서도 동작한다.

### 활성화

`/tui fullscreen`을 실행하면 CLI가 `tui` 설정을 저장하고 대화를 유지한 채 풀스크린으로 재실행한다. `/tui`(인자 없음)는 활성 렌더러를 출력한다. `CLAUDE_CODE_NO_FLICKER=1 claude`로도 가능하며 둘은 등가다. `/tui` 명령은 재실행 프로세스에서 `CLAUDE_CODE_NO_FLICKER`를 clear해 작성한 설정이 적용되게 한다.

### 무엇이 달라지나

입력박스가 출력 스트리밍에도 화면 하단에 고정된다(입력이 가만히 있으면 풀스크린 활성). 보이는 메시지만 render tree에 유지돼 대화 길이와 무관하게 메모리가 일정하다. 대화가 native scrollback 대신 alternate screen buffer에 있어 몇 가지가 다르게 동작한다.

| Before | Now | Details |
| :--- | :--- | :--- |
| `Cmd+f`/tmux search로 텍스트 찾기 | `Ctrl+o`로 transcript 모드 후 `/`로 검색 또는 `[`로 scrollback에 기록 | 검색·리뷰 |
| 터미널 네이티브 클릭드래그 선택·복사 | in-app 선택, 마우스 release 시 자동 복사 | 마우스 사용 |
| `Cmd`-클릭으로 URL 열기 | URL 클릭 | 마우스 사용 |

### 마우스 사용

풀스크린은 마우스 이벤트를 캡처해 Claude Code 내부에서 처리한다: 프롬프트 입력 클릭으로 커서 위치, `/`·`@` 목록 제안 클릭으로 수락, 접힌 도구 결과 클릭으로 펼침/접힘, URL·파일 경로 클릭으로 열기(파일 경로는 기본 앱, `http(s)`는 브라우저). VS Code 등 xterm.js 기반 터미널에서는 `Cmd`-클릭을 계속 쓴다(중복 열림 방지를 위해 터미널 link handler에 위임). 클릭드래그로 선택(더블클릭=단어, 트리플클릭=줄), 마우스 휠로 스크롤.

선택 텍스트는 마우스 release 시 자동 복사된다. `/config`의 "Copy on select"를 끄면 `Ctrl+Shift+c`로 수동 복사(kitty 프로토콜 지원 터미널은 `Cmd+c`도). 선택이 활성이면 `Ctrl+c`는 취소 대신 복사한다. 선택 활성 시 `Shift`+화살표로 키보드 확장(`Shift+↑`/`↓`는 가장자리에서 viewport 스크롤, `Shift+Home`/`End`는 줄 시작/끝까지).

### 대화 스크롤

| Shortcut | Action |
| :--- | :--- |
| `PgUp` / `PgDn` | 절반 화면 위/아래 스크롤 |
| `Ctrl+Home` | 대화 시작으로 점프 |
| `Ctrl+End` | 최신 메시지로 점프 + auto-follow 재개 |
| Mouse wheel | 몇 줄씩 스크롤 |

전용 `PgUp`/`PgDn`/`Home`/`End` 키가 없는 키보드(MacBook 등)는 `Fn`+화살표(`Fn+↑`=PgUp, `Fn+↓`=PgDn, `Fn+←`=Home, `Fn+→`=End, 따라서 `Ctrl+Fn+→`가 맨아래 점프). 이 액션들은 재바인딩 가능(위 "Scroll" 액션 참고).

**Auto-follow**: 위로 스크롤하면 auto-follow가 멈춰 새 출력이 끌어내리지 않는다. `Ctrl+End` 또는 맨아래 스크롤로 재개. 완전히 끄려면 `/config`에서 Auto-scroll을 off(권한 프롬프트 등은 이 설정과 무관하게 스크롤됨).

**마우스 휠**: 터미널이 마우스 이벤트를 Claude Code에 전달해야 한다. iTerm2는 per-profile 설정(Settings → Profiles → Terminal → "Enable mouse reporting"). 휠이 느리면 터미널이 notch당 1 이벤트만 보내는 것일 수 있다. `CLAUDE_CODE_SCROLL_SPEED`로 배수 설정(1~20, `3`이 vim 기본과 일치).

```bash
export CLAUDE_CODE_SCROLL_SPEED=3
```

`/scroll-speed`로 대화형 조절(`←`/`→` 조절, `r` 리셋, `Enter` 저장; `~/.claude/settings.json`에 영속). JetBrains IDE 터미널은 자체 스크롤 처리를 적용하고 `CLAUDE_CODE_SCROLL_SPEED`를 무시하며, 2025.2의 스크롤 휠 버그를 런타임 감지·완화한다(2025.3+ 권장).

### 검색·리뷰와 대화 비우기

`Ctrl+o`로 일반 프롬프트와 transcript 모드를 토글한다. `/focus`는 마지막 프롬프트, 도구 호출 한 줄 요약(edit diffstat), 최종 응답만 보여주는 조용한 뷰다(세션 간 영속, 다시 실행하면 off). transcript 모드의 `less` 스타일 네비게이션·검색:

| Key | Action |
| :--- | :--- |
| `/` | 검색 열기 (타이핑으로 찾기, `Enter` 수락, `Esc` 취소·스크롤 복원) |
| `n` / `N` | 다음/이전 매치 |
| `j` / `k` 또는 `↑` / `↓` | 한 줄 스크롤 |
| `g` / `G` 또는 `Home` / `End` | 맨 위/아래 점프 |
| `Ctrl+u` / `Ctrl+d` | 절반 페이지 스크롤 |
| `Ctrl+b` / `Ctrl+f` 또는 `Space` / `b` | 전체 페이지 스크롤 |
| `Ctrl+o`, `Esc`, `q` | transcript 모드 종료 |

대화가 alternate buffer에 있어 터미널 `Cmd+f`·tmux search가 못 보므로, `Ctrl+o`로 transcript 모드 진입 후 **`[`**로 전체 대화를 native scrollback에 기록(도구 출력 펼친 채; `Cmd+f`·tmux copy mode로 검색 가능) 또는 **`v`**로 임시 파일에 쓰고 `$VISUAL`/`$EDITOR`로 연다.

**대화 비우기**: `Ctrl+L`을 2초 내 두 번 누르면 `/clear`(1회=redraw+힌트, 2회=clear). macOS는 `Cmd+K` 더블도 `/clear`.

### tmux와 함께 / 네이티브 텍스트 선택 유지 / Research preview

**tmux 주의 3가지**: ① 마우스 휠 스크롤은 tmux 마우스 모드 필요 — `~/.tmux.conf`에 `set -g mouse on` 추가(키보드 `PgUp`/`PgDn`은 무관). ② iTerm2의 tmux 통합 모드(`tmux -CC`)와 비호환(통합 모드에서 alternate buffer·마우스 추적 오동작, 활성화 금지; `-CC` 없는 일반 tmux는 정상). ③ tmux는 synchronized output 미지원이라 redraw 시 깜빡임이 더 보일 수 있음(특히 SSH; 심하면 tmux 밖 별도 탭에서 실행).

**네이티브 선택 유지**: 마우스 캡처가 켜지면 터미널 네이티브 copy-on-select가 멈춘다. Claude Code는 선택을 시스템 클립보드에 쓰는데, 로컬 세션은 네이티브 도구(macOS `pbcopy`, Linux Wayland `wl-copy`/X11 `xclip`·`xsel`, Windows·WSL PowerShell `Set-Clipboard`)를 쓰고, tmux 안에서는 tmux paste buffer에도, SSH에서는 OSC 52로 fallback한다(복사 후 사용 경로를 toast로 표시). 일부 터미널은 OSC 52를 차단하므로 iTerm2는 Settings → General → Selection → "Applications in terminal may access clipboard" 활성화(또는 `/terminal-setup`). 일회성 네이티브 선택 키: Terminal.app `Fn`, iTerm2 `Option`, VS Code·Cursor·Devin Desktop `Shift`(macOS는 설정 시 `Option`), 그 외 `Shift`. 항상 네이티브 선택을 쓰려면 `CLAUDE_CODE_DISABLE_MOUSE=1`로 마우스 캡처를 opt-out(flicker-free 렌더링·평탄 메모리는 유지, click-to-position·click-to-expand·URL 클릭·휠 스크롤은 잃음).

```bash
CLAUDE_CODE_NO_FLICKER=1 CLAUDE_CODE_DISABLE_MOUSE=1 claude
```

**Research preview**: 흔한 emulator에서 테스트됐으나 드문 터미널·특이 구성에서 렌더링 이슈가 있을 수 있다. 문제는 `/feedback` 또는 GitHub 이슈로 보고(emulator명·버전 포함). 끄려면 `/tui default` 또는 `CLAUDE_CODE_NO_FLICKER` unset. 저장된 `tui` 설정과 무관하게 classic 렌더러를 강제하려면 `CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1`. agent view·`claude attach`로 연 백그라운드 세션은 항상 풀스크린 렌더링을 쓰며 `tui` 설정·`CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN`이 적용되지 않는다.

---

## 음성 받아쓰기 (voice dictation)

타이핑 대신 프롬프트를 말로 입력한다. 음성은 입력창에 실시간 transcribe되어 한 메시지 안에서 음성과 타이핑을 섞을 수 있다. `/voice`로 활성화 후 키를 누른 채 말하거나(hold) 한 번 탭해 시작·다시 탭해 전송(tap)한다.

> [!note] 음성 받아쓰기는 v2.1.69 이상, tap 모드는 v2.1.116 이상 필요.

### 요구사항

음성은 녹음 오디오를 Anthropic 서버로 스트리밍해 transcribe하며 로컬 처리가 아니다. **Claude.ai 계정 인증** 시에만 사용 가능하고, API key 직접 사용·Amazon Bedrock·Google Vertex AI·Microsoft Foundry에서는 불가하다([[17 클라우드 프로바이더]]). 조직에 HIPAA 컴플라이언스가 켜진 경우도 불가. transcription은 Claude 메시지·토큰을 소비하지 않고 `/usage` 한도에 포함되지 않는다. 로컬 마이크 접근이 필요해 [[15 웹과 모바일]]의 web이나 SSH 세션에서는 불가(WSL은 WSLg 필요). 오디오 녹음은 macOS·Linux·Windows의 내장 네이티브 모듈을 쓰고, Linux에서 모듈 로드 실패 시 ALSA의 `arecord` 또는 SoX의 `rec`로 fallback한다. VS Code 확장도 같은 Claude.ai 계정 요구로 지원하나 VS Code Remote(SSH·Dev Container·Codespaces)에서는 불가([[14 IDE와 데스크톱]]).

### 활성화

`/voice`로 활성화한다(첫 활성화 시 마이크 체크, macOS는 시스템 마이크 권한 프롬프트).

```
/voice
Voice mode enabled (hold). Hold Space to record. Dictation language: en (/config to change).
```

| Command | Effect |
| :--- | :--- |
| `/voice` | on/off 토글, 현재 모드 유지 |
| `/voice hold` | hold 모드로 활성화 |
| `/voice tap` | tap 모드로 활성화 |
| `/voice off` | 비활성화 |

세션 간 영속화는 [[04 설정]]의 user settings 파일에 직접:

```json
{
  "voice": {
    "enabled": true,
    "mode": "tap"
  }
}
```

활성화 중 프롬프트가 비면 footer에 `hold Space to speak` 힌트가 뜬다(현재 `voice:pushToTalk` 바인딩 반영, custom status line이 있으면 안 뜸). transcription은 코딩 어휘에 튜닝돼 `regex`·`OAuth`·`JSON`·`localhost` 등을 인식하고, 현재 프로젝트명·git 브랜치명이 인식 힌트로 자동 추가된다.

### Hold 모드 (push-to-talk, 기본)

`Space`를 누른 채 녹음하고 떼면 멈춘다(push-to-talk). Claude Code는 터미널의 빠른 key-repeat 이벤트를 보고 hold를 감지하므로 짧은 warmup이 있다(footer `keep holding…` → 활성화 시 live waveform). warmup 중 처음 한두 개 repeat 문자가 입력됐다가 자동 제거되며, 단일 `Space` 탭은 그냥 공백을 친다. transcript는 커서 위치에 삽입되고 커서는 끝에 남아 타이핑·받아쓰기를 섞을 수 있다.

```
> refactor the auth middleware to ▮
  # hold Space, speak "use the new token validation helper"
> refactor the auth middleware to use the new token validation helper▮
```

기본은 키를 떼면 transcript를 삽입하고 `Enter`를 기다린다. `voice` 설정 객체에 `"autoSubmit": true`를 두면 transcript가 3단어 이상일 때 자동 전송한다.

> [!tip] warmup을 건너뛰려면 `/voice tap`(tap 모드) 또는 `meta+k` 같은 modifier 조합으로 재바인딩한다(첫 keypress에 즉시 녹음 시작).

### Tap 모드

`/voice tap`으로 활성화. 입력이 빈 상태에서 `Space`를 탭하면 녹음 시작(live waveform), 다시 탭하면 멈추고 transcript가 3단어 이상이면 자동 전송한다(짧으면 삽입만, 오타 탭으로 stray word 방지). 첫 탭은 입력이 빌 때만 녹음을 시작하므로 메시지 작성 중 공백은 정상 입력된다. 둘째 탭은 입력 내용과 무관하게 멈춘다. 15초 무음 또는 총 2분 후 자동 정지.

### 받아쓰기 언어

받아쓰기는 Claude 응답 언어를 제어하는 동일한 `language` 설정을 쓴다. 비어 있으면 영어 기본(VS Code 확장은 비었을 때 `accessibility.voice.speechLanguage`를 먼저 본 뒤 영어). 지원 언어: Czech `cs`, Danish `da`, Dutch `nl`, English `en`, French `fr`, German `de`, Greek `el`, Hindi `hi`, Indonesian `id`, Italian `it`, Japanese `ja`, **Korean `ko`**, Norwegian `no`, Polish `pl`, Portuguese `pt`, Russian `ru`, Spanish `es`, Swedish `sv`, Turkish `tr`, Ukrainian `uk`.

`/config` 또는 설정에서 지정하며 BCP 47 코드 또는 언어명 모두 가능:

```json
{ "language": "japanese" }
```

지원 목록에 없으면 활성화 시 경고하고 영어로 fallback한다(Claude 텍스트 응답은 영향 없음).

### 받아쓰기 키 재바인딩

받아쓰기 키는 `Chat` 컨텍스트의 `voice:pushToTalk`에 바인딩되고 기본은 `Space`다(hold·tap 모두 동일 바인딩). `~/.claude/keybindings.json`에서 재바인딩한다.

```json
{
  "bindings": [
    {
      "context": "Chat",
      "bindings": {
        "meta+k": "voice:pushToTalk",
        "space": null
      }
    }
  ]
}
```

`voice:pushToTalk`은 한 번에 한 키만 쓰며 커스텀 키는 기본 `Space`를 대체하므로 `"space": null`은 명확성을 위한 것이고 생략해도 동작은 같다. hold 모드에서는 `v` 같은 단순 글자 키를 피한다(hold 감지가 key-repeat에 의존해 warmup 중 글자가 입력됨). `Space`나 `meta+k` 같은 modifier 조합을 쓴다. tap 모드는 warmup이 없어 대부분 키가 동작한다. `Caps Lock` 등 일부 키는 바인딩 불가(위 "재바인딩 불가" 참고).

### 트러블슈팅

- **`Voice mode requires a Claude.ai account`**: API key/서드파티 provider로 인증됨. `/login`으로 Claude.ai 로그인.
- **`Microphone access is denied`**: 시스템 설정에서 터미널에 마이크 권한 부여. macOS는 System Settings → Privacy & Security → Microphone, Windows는 Settings → Privacy & security → Microphone에서 desktop 앱 허용 후 `/voice` 재실행.
- **`No audio recording tool found` (Linux)**: 네이티브 모듈 로드 실패·fallback 미설치. 에러 메시지의 명령으로 SoX 설치(예 `sudo apt-get install sox`).
- **`Voice mode could not find a working audio recorder in WSL`**: WSLg는 PulseAudio로 라우팅하므로 SoX의 PulseAudio 백엔드 명시 설치 필요 — `sudo apt install sox libsox-fmt-pulse`.
- **`Voice input is failing repeatedly and has been paused`**: 연속 시작 실패로 일시 중지(헤드리스 서버·오디오 패스스루 없는 원격 셸·권한 거부 등). 작동 입력 장치 확인·근본 원인 수정 후 재시도.
- **hold 모드에서 `Space`를 눌러도 아무 일 없음**: 공백이 계속 쌓이면 음성이 꺼진 것(`/voice hold`). 한두 공백 후 멈추면 켜졌으나 hold 감지 미작동(OS에서 key-repeat 비활성). `/voice tap`으로 전환.
- **tap 모드에서 `Space`가 공백만 침**: 첫 탭은 입력이 빌 때만 녹음 시작. 입력 비우거나 `/voice tap` 확인.
- **`No audio detected from microphone`**: 녹음됐으나 무음. 올바른 기본 입력 장치·입력 레벨 확인.
- **`No speech detected`**: 오디오는 도달했으나 단어 미인식. 마이크에 가까이·소음 줄이기·언어 일치 확인.
- **transcription이 깨지거나 잘못된 언어**: 기본 영어. 다른 언어는 `/config`에서 먼저 설정.

**macOS Microphone 설정에 터미널이 안 보일 때**: 권한 상태를 리셋한다. ① `tccutil reset Microphone <bundle-id>` 실행(`com.apple.Terminal` 또는 `com.googlecode.iterm2`; 다른 터미널은 `osascript -e 'id of app "AppName"'`로 식별자 조회). bundle ID 없이 실행하면 모든 앱의 마이크 접근이 취소되니 주의. ② `Cmd+Q`로 터미널 완전 종료 후 재실행. ③ Claude Code 시작 후 `/voice` 실행, macOS 권한 프롬프트 허용.

추가 문제는 [[25 트러블슈팅]] 참고.

---

## 원본 문서

- [cli-reference](https://code.claude.com/docs/en/cli-reference)
- [interactive-mode](https://code.claude.com/docs/en/interactive-mode)
- [keybindings](https://code.claude.com/docs/en/keybindings)
- [terminal-config](https://code.claude.com/docs/en/terminal-config)
- [fullscreen](https://code.claude.com/docs/en/fullscreen)
- [voice-dictation](https://code.claude.com/docs/en/voice-dictation)
