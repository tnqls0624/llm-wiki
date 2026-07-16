---
title: 14 IDE와 데스크톱
updated: 2026-07-16
type: reference
sources: [vs-code, jetbrains, desktop, desktop-quickstart, platforms, desktop-linux, desktop-wsl]
---

# 14 IDE와 데스크톱

Claude Code를 터미널 밖에서 — VS Code/Cursor 확장, JetBrains 플러그인, 그리고 독립 데스크톱 앱(GUI)에서 — 사용하는 방법을 정리한다. 모든 표면(surface)은 동일한 엔진을 공유하며 CLAUDE.md·MCP·설정 파일을 같이 읽는다. 어떤 표면을 고를지에 대한 비교는 맨 아래 [[#플랫폼과 통합 (어디서 실행할지 고르기)]] 참고. 허브는 [[Claude]].

> [!info] 관련 노트
> CLI 자체는 [[02 CLI 레퍼런스]], 설정 파일은 [[04 설정]], 권한 모드는 [[05 권한]], MCP는 [[10 MCP]], 플러그인은 [[11 플러그인]], 웹·모바일은 [[15 웹과 모바일]], 컴퓨터 사용/Chrome은 [[21 브라우저와 컴퓨터 사용]], 샌드박스/보안은 [[18 보안과 샌드박스]]에서 다룬다.

---

## VS Code 확장

VS Code 확장은 Claude Code의 **네이티브 그래픽 인터페이스**를 IDE에 직접 통합한 것이다. VS Code에서 Claude Code를 쓰는 권장 방식이다. 인라인 diff, @-mention, 플랜 리뷰, 키보드 단축키를 제공하며, 확장 안에 **CLI도 포함**되어 통합 터미널에서 고급 기능을 쓸 수 있다.

확장의 주요 능력: Claude의 플랜을 수락 전에 검토·편집, 편집을 자동 수락, 선택 영역에서 특정 줄 범위로 파일을 @-mention, 대화 기록 접근, 여러 대화를 탭/창으로 동시 열기.

### 사전 요구사항 및 설치

| 항목 | 요구사항 |
|------|----------|
| VS Code 버전 | 1.98.0 이상 |
| 계정 | Anthropic 계정(첫 실행 시 로그인). Bedrock/Vertex 등 서드파티는 별도 설정 |

설치 방법:
- VS Code: `Cmd+Shift+X` (Mac) / `Ctrl+Shift+X` (Win/Linux)로 Extensions 뷰를 열고 "Claude Code" 검색 후 **Install**.
- 직접 링크: `vscode:extension/anthropic.claude-code` (Cursor는 `cursor:extension/anthropic.claude-code`).
- Cursor, Devin Desktop, Kiro 등 VS Code 포크에도 설치된다. [Open VSX registry](https://open-vsx.org/extension/Anthropic/claude-code)에서 설치 가능. 설치가 안 되는 에디터라면 통합 터미널에서 `claude` 실행.
- 설치 후 안 보이면 VS Code 재시작 또는 Command Palette에서 **Developer: Reload Window**.

### 시작하기 — Spark 아이콘과 패널 열기

VS Code 곳곳에서 **Spark 아이콘**이 Claude Code를 가리킨다. 패널을 여는 방법:

| 방법 | 위치/단축키 | 비고 |
|------|------------|------|
| Editor Toolbar | 에디터 우상단 Spark 아이콘 | 파일이 열려 있어야 보임 |
| Activity Bar | 좌측 사이드바 Spark 아이콘 | 항상 보임. 세션 목록 표시 |
| Command Palette | `Cmd+Shift+P` / `Ctrl+Shift+P` → "Claude Code" | "Open in New Tab" 등 선택 |
| Status Bar | 우하단 **✱ Claude Code** 클릭 | 파일이 없어도 동작 |

첫 패널 진입 시 로그인 화면이 뜬다. **Not logged in · Please run /login**이 나오면 로그인 화면이 자동 재오픈된다. `ANTHROPIC_API_KEY`를 셸에 설정했는데도 로그인 프롬프트가 뜨면, VS Code가 셸 환경을 상속받지 못한 것 — 터미널에서 `code .`로 실행하거나 Claude 계정으로 로그인. Command Palette의 **Claude Code: Open Walkthrough**로 기본 가이드 투어를 볼 수 있다.

### 프롬프트 박스 기능

- **권한 모드(Permission modes)**: 프롬프트 박스 하단 모드 표시기를 클릭해 전환. normal(매 액션마다 허가), Plan(변경 전 플랜을 마크다운 문서로 열어 인라인 코멘트로 피드백), auto-accept(허가 없이 편집). 기본값은 설정 `claudeCode.initialPermissionMode`로 지정. → [[05 권한]]
- **커맨드 메뉴**: `/` 입력 또는 클릭으로 열기. 파일 첨부, 모델 전환, extended thinking 토글, `/usage`(플랜 사용량), `/remote-control`(Remote Control 세션) 등. Customize 섹션에서 MCP·hooks·memory·permissions·plugins 접근. 터미널 아이콘이 붙은 항목은 통합 터미널에서 열림.
- **컨텍스트 표시기**: 컨텍스트 윈도우 사용량 표시. 필요 시 자동 compact 또는 `/compact` 수동 실행.
- **Extended thinking**: 복잡한 문제에 추론 시간을 더 씀. `/` 메뉴로 토글. 추론은 접힌 블록으로 표시되고 클릭하면 펼쳐짐. `Ctrl+O`로 세션 내 모든 thinking 블록 펼치기/접기. → [[03 메모리와 컨텍스트]]
- **다중 줄 입력**: `Shift+Enter`로 전송 없이 줄바꿈. 질문 다이얼로그의 "Other" 자유 입력에서도 동작.

#### 파일·폴더 참조 (@-mention)

`@`를 입력하면 파일/폴더 이름으로 컨텍스트를 추가. 퍼지 매칭 지원 — 부분 이름으로 찾을 수 있다.

```text
> Explain the logic in @auth      (퍼지: auth.js, AuthService.ts 등 매칭)
> What's in @src/components/       (폴더는 끝에 슬래시)
```

- 큰 PDF는 특정 페이지·범위(예: 1-10페이지, 3페이지 이후)만 읽도록 요청 가능.
- 에디터에서 텍스트를 선택하면 Claude가 자동으로 본다. `Option+K` (Mac) / `Alt+K` (Win/Linux)로 파일 경로+줄 번호 @-mention 삽입(예: `@app.ts#5-10`). 선택 표시기를 클릭해 Claude가 선택 영역을 보는지 토글(eye-slash = 숨김).
- `Shift`를 누른 채 파일을 프롬프트 박스로 드래그하면 첨부로 추가.

#### 과거 대화 재개

패널 상단 **Session history** 버튼으로 대화 기록 접근. 키워드 검색 또는 시간별(Today, Yesterday, Last 7 days) 브라우징. 새 세션은 첫 메시지 기반 AI 제목을 받는다. 세션 위에 호버하면 rename/remove. → 세션 관리는 [[01 시작하기]] 참고.

**Claude.ai 원격 세션 재개**: [[15 웹과 모바일]]의 웹 세션을 VS Code에서 재개할 수 있다. **Claude.ai Subscription** 로그인 필요(Anthropic Console 아님). Session history → **Remote** 탭에서 선택해 로컬로 다운로드. 단, GitHub 저장소로 시작한 웹 세션만 Remote 탭에 표시되며, 변경은 claude.ai로 동기화되지 않는다.

### 워크플로우 커스터마이즈

#### 패널 위치 선택

패널 탭/타이틀바를 드래그해 이동:
- **Secondary sidebar**(우측): 코딩하면서 Claude 계속 보기.
- **Primary sidebar**(좌측, Explorer/Search 아이콘들).
- **Editor area**: 파일 옆 탭으로 열기. 곁다리 작업에 유용.

#### 다중 대화 실행

Command Palette의 **Open in New Tab** / **Open in New Window**로 추가 대화 시작. 각 대화는 자체 기록·컨텍스트 유지. 탭 사용 시 spark 아이콘의 색 점: 파랑=권한 요청 대기, 주황=숨겨진 탭에서 Claude 작업 완료.

#### 터미널 모드 전환

기본은 그래픽 채팅 패널. CLI 스타일 인터페이스를 원하면 [Use Terminal 설정](vscode://settings/claudeCode.useTerminal) 체크, 또는 설정 → Extensions → Claude Code → **Use Terminal**.

### 플러그인 관리 (`/plugins`)

VS Code 확장은 [[11 플러그인]] 설치·관리 GUI를 포함한다. 프롬프트 박스에 `/plugins` 입력으로 **Manage plugins** 인터페이스 열기.

- **Plugins 탭**: 설치된 플러그인(토글 스위치), 마켓플레이스의 사용 가능한 플러그인. 검색 필터. **Install** 클릭.
- 설치 스코프 선택: **Install for you**(user, 모든 프로젝트) / **Install for this project**(project, 협업자 공유) / **Install locally**(local, 본인·이 저장소만).
- **Marketplaces 탭**: GitHub repo/URL/로컬 경로로 마켓플레이스 추가, refresh 아이콘으로 갱신, trash 아이콘으로 제거. 변경 후 재시작 배너 표시.
- VS Code 플러그인 관리는 내부적으로 동일한 CLI 명령을 쓰므로, 확장에서 설정한 플러그인·마켓플레이스는 CLI에서도 사용 가능(역방향도 동일).

### Chrome으로 브라우저 작업 자동화 (`@browser`)

웹 앱 테스트, 콘솔 로그 디버깅, 브라우저 워크플로우 자동화. [Claude in Chrome 확장](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn) **1.0.36 이상** 필요.

```text
@browser go to localhost:3000 and check the console for errors
```

Claude는 브라우저 작업용 새 탭을 열고 로그인 상태를 공유한다. 자세한 내용은 [[21 브라우저와 컴퓨터 사용]].

### VS Code 명령과 단축키

Command Palette에서 "Claude Code"를 검색해 모든 확장 명령 확인. 일부 단축키는 어느 패널이 포커스인지에 따라 다르다(에디터 포커스 vs Claude 포커스). `Cmd+Esc` / `Ctrl+Esc`로 둘 사이 토글. **확장의 모든 내장 Claude Code 명령이 다 있는 건 아님** — CLI 비교 참고.

| Command | Shortcut | Description |
|---------|----------|-------------|
| Focus Input | `Cmd+Esc` / `Ctrl+Esc` | 에디터 ↔ Claude 포커스 토글 |
| Open in Side Bar | - | 좌측 사이드바에 열기 |
| Open in Terminal | - | 터미널 모드로 열기 |
| Open in New Tab | `Cmd+Shift+Esc` / `Ctrl+Shift+Esc` | 새 대화를 에디터 탭으로 |
| Open in New Window | - | 새 대화를 별도 창으로 |
| New Conversation | `Cmd+N` / `Ctrl+N` | 새 대화. Claude 포커스 + `enableNewConversationShortcut: true` 필요 |
| Reopen Closed Session | `Cmd+Shift+T` / `Ctrl+Shift+T` | 최근 닫은 Claude 탭 재오픈. `enableReopenClosedSessionShortcut`로 비활성화 |
| Insert @-Mention Reference | `Option+K` / `Alt+K` | 현재 파일+선택 참조 삽입(에디터 포커스 필요) |
| Show Logs | - | 확장 디버그 로그 |
| Logout | - | Anthropic 계정 로그아웃 |

#### 외부 도구에서 VS Code 탭 띄우기 (URI 핸들러)

확장은 `vscode://anthropic.claude-code/open` URI 핸들러를 등록한다. 셸 alias, 브라우저 북마클릿, 스크립트에서 URL을 열어 Claude Code 탭을 띄울 수 있다. VS Code가 안 떠 있으면 먼저 실행, 떠 있으면 포커스된 창에서 열림.

```bash
# macOS
open "vscode://anthropic.claude-code/open"
# Linux
xdg-open "vscode://anthropic.claude-code/open"
```
```powershell
# Windows PowerShell
Start-Process "vscode://anthropic.claude-code/open"
```
```cmd
:: cmd.exe — start의 첫 따옴표 인자는 창 제목이므로 빈 제목을 먼저 넘김
start "" "vscode://anthropic.claude-code/open"
```

선택적 쿼리 파라미터:

| Parameter | Description |
|-----------|-------------|
| `prompt` | 프롬프트 박스에 미리 채울 텍스트. URL 인코딩 필요. 자동 전송은 안 됨 |
| `session` | 새 대화 대신 재개할 세션 ID. 현재 VS Code에 열린 워크스페이스 소속이어야 함. 못 찾으면 새 대화. 이미 탭에 열려 있으면 포커스 |

```text
vscode://anthropic.claude-code/open?prompt=review%20my%20changes
```

VS Code 탭이 아니라 터미널 세션을 띄우려면 CLI의 `claude-cli://` 핸들러 사용(deep-links).

### 설정 구성

확장에는 두 종류의 설정이 있다:
- **Extension 설정**(VS Code 내): 확장 동작 제어. `Cmd+,` / `Ctrl+,` → Extensions → Claude Code. 또는 `/` → **General Config**.
- **Claude Code 설정**(`~/.claude/settings.json`): 확장과 CLI가 **공유**. allowed commands, env vars, hooks, MCP 등. → [[04 설정]]

> [!tip] 스키마 자동완성
> `settings.json`에 `"$schema": "https://json.schemastore.org/claude-code-settings.json"`을 추가하면 VS Code에서 모든 설정에 대한 자동완성·인라인 검증이 활성화된다.

#### Extension 설정 키 전체

| Setting | Default | Description |
|---------|---------|-------------|
| `useTerminal` | `false` | 그래픽 패널 대신 터미널 모드로 실행 |
| `initialPermissionMode` | `default` | 새 대화 승인 프롬프트: `default`, `plan`, `acceptEdits`, `bypassPermissions` |
| `preferredLocation` | `panel` | 열리는 위치: `sidebar`(우측) 또는 `panel`(새 탭) |
| `autosave` | `true` | Claude가 읽기/쓰기 전 파일 자동 저장 |
| `useCtrlEnterToSend` | `false` | Enter 대신 Ctrl/Cmd+Enter로 전송 |
| `enableNewConversationShortcut` | `false` | Cmd/Ctrl+N으로 새 대화 활성화 |
| `enableReopenClosedSessionShortcut` | `true` | Cmd/Ctrl+Shift+T로 최근 닫은 탭 재오픈 |
| `hideOnboarding` | `false` | 온보딩 체크리스트 숨김 |
| `respectGitIgnore` | `true` | 파일 검색에서 .gitignore 패턴 제외 |
| `usePythonEnvironment` | `true` | 워크스페이스 Python 환경 활성화(Python 확장 필요) |
| `environmentVariables` | `[]` | Claude 프로세스 env. 공유 설정은 Claude Code 설정을 쓸 것 |
| `disableLoginPrompt` | `false` | 인증 프롬프트 건너뛰기(서드파티 프로바이더 셋업용) |
| `allowDangerouslySkipPermissions` | `false` | 모드 선택기에 Bypass permissions 추가. 인터넷 없는 샌드박스에서만 사용 |
| `claudeProcessWrapper` | - | Claude 프로세스 실행 실행파일. 번들 바이너리 경로가 인자로 전달됨. 빌드에 바이너리가 없으면 별도 설치한 `claude` 바이너리를 지정 |

### VS Code 확장 vs CLI

일부 기능은 CLI에서만 가능. CLI 전용 기능이 필요하면 통합 터미널에서 `claude` 실행.

| Feature | CLI | VS Code Extension |
|---------|-----|-------------------|
| Commands and skills | All | Subset (`/`로 확인) |
| MCP server config | Yes | Partial (CLI로 추가; `/mcp`로 관리) |
| Checkpoints | Yes | Yes |
| `!` bash shortcut | Yes | No |
| Tab completion | Yes | No |

#### Checkpoints로 되감기

확장은 체크포인트를 지원한다. 메시지 위에 호버해 rewind 버튼 → 세 옵션:
- **Fork conversation from here**: 코드 변경은 유지한 채 이 메시지에서 새 대화 분기.
- **Rewind code to here**: 대화 기록은 유지하고 파일 변경만 이 지점으로 되돌림.
- **Fork conversation and rewind code**: 새 분기 + 파일 되돌림.

#### CLI를 VS Code 안에서 / 확장 ↔ CLI 전환

- 통합 터미널(`` Ctrl+` `` / `` Cmd+` ``)에서 `claude` 실행 → diff 뷰·진단 공유 등 IDE 통합 자동.
- 외부 터미널이면 Claude Code 안에서 `/ide`로 VS Code 연결.
- 확장과 CLI는 **동일한 대화 기록 공유**. 확장 대화를 터미널에서 이어가려면 `claude --resume`.
- **터미널 출력 참조**: 프롬프트에서 `@terminal:name`(터미널 제목)으로 명령 출력·에러·로그를 복붙 없이 Claude에 전달.
- **백그라운드 프로세스**: 장기 실행 명령은 status bar에 진행 표시. 단 CLI 대비 가시성 제한 — 더 잘 보려면 명령을 통합 터미널에서 직접 실행.

#### MCP 연결

통합 터미널에서 `claude mcp add`로 추가. 예: GitHub 원격 MCP 서버([PAT](https://github.com/settings/personal-access-tokens)를 헤더로):

```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/ \
  --header "Authorization: Bearer YOUR_GITHUB_PAT"
```

VS Code 안에서 관리하려면 `/mcp` — 서버 활성/비활성, 재연결, OAuth 관리. → [[10 MCP]]

### git 작업 / 워크트리

Claude가 변경 스테이징, 커밋 메시지 작성, PR 생성, 브랜치 작업 수행:

```text
> commit my changes with a descriptive message
> create a pr for this feature
> summarize the changes I've made to the auth module
```

`--worktree` (`-w`) 플래그로 격리된 워크트리(독립 파일·브랜치, git 기록 공유)에서 시작. 병렬 작업 시 인스턴스 간 간섭 방지.

```bash
claude --worktree feature-auth
```

워크트리 상세는 [[02 CLI 레퍼런스]] 및 [[13 자동화와 스케줄링]] 흐름과 함께 본다.

### 서드파티 프로바이더

기본은 Anthropic API 직결. Amazon Bedrock / Google Vertex AI / Microsoft Foundry를 쓰려면:
1. [Disable Login Prompt 설정](vscode://settings/claudeCode.disableLoginPrompt) 체크.
2. 프로바이더 셋업 가이드(`~/.claude/settings.json` 구성 → 확장·CLI 공유). → [[17 클라우드 프로바이더]]

### 보안과 프라이버시 / 내장 IDE MCP 서버

코드는 비공개로 유지되며 모델 학습에 쓰이지 않는다. auto-edit 권한이 켜져 있으면 Claude가 `settings.json`·`tasks.json` 등 VS Code가 자동 실행할 수 있는 설정 파일을 수정할 수 있어, 신뢰 불가 코드 작업 시 [VS Code Restricted Mode](https://code.visualstudio.com/docs/editor/workspace-trust#_restricted-mode) 사용·수동 승인·신중한 리뷰를 권장. → [[18 보안과 샌드박스]]

**내장 `ide` MCP 서버**: 확장 활성화 시 로컬 MCP 서버가 돌고 CLI가 자동 연결된다. 이를 통해 CLI가 네이티브 diff 뷰어를 열고, `@`-mention용 선택 영역을 읽고, Jupyter 셀 실행을 요청한다. `ide`로 명명되며 설정할 게 없어 `/mcp`에서 숨겨지지만, `PreToolUse` 훅으로 MCP 도구를 allowlist 하는 조직은 존재를 알아야 한다.

- **선택·열린 파일 컨텍스트**: 연결된 동안 CLI가 현재 에디터 선택과 활성 파일 경로를 매 프롬프트에 포함. 트랜스크립트에 `⧉ Selected N lines from <file>` 표시. `.env` 같은 민감 파일은 그 경로에 [`Read` deny rule](/en/permissions#read-and-edit)을 추가하면 선택 텍스트·열린 파일 알림 모두 차단됨. → [[05 권한]]
- **전송·인증**: `127.0.0.1` 랜덤 high port에 바인딩, 외부 도달 불가. 활성화마다 새 랜덤 토큰 생성, `~/.claude/ide/` 아래 `0600` 락 파일(`0700` 디렉터리)에 기록.
- **모델에 노출되는 도구**: 서버는 ~12개 도구를 호스팅하지만 모델에는 2개만 보임(나머지는 CLI UI용 내부 RPC로 필터링).

| Tool name (훅이 보는 이름) | 하는 일 | Writes? |
|---|---|---|
| `mcp__ide__getDiagnostics` | 언어 서버 진단(Problems 패널의 에러·경고) 반환. 단일 파일 스코프 가능 | No |
| `mcp__ide__executeCode` | 활성 Jupyter 노트북 커널에서 Python 실행. 항상 확인 절차 | Yes |

> [!warning] Jupyter 실행은 항상 먼저 묻는다
> `mcp__ide__executeCode`는 무음 실행 불가. 매 호출 시 코드를 활성 노트북 끝에 새 셀로 삽입하고 Quick Pick으로 **Execute** / **Cancel**을 묻는다. 취소/`Esc`면 에러 반환. 활성 노트북 없음, Jupyter 확장(`ms-toolsai.jupyter`) 미설치, 커널이 Python이 아니면 거부. 이 Quick Pick은 `PreToolUse` 훅과 별개 — allowlist는 *제안*을 허용할 뿐, *실제 실행*은 Quick Pick이 결정.

### VS Code 문제 해결 (요약)

- **확장 설치 안 됨**: VS Code 1.98.0+ 확인, 확장 설치 권한 확인, [Marketplace](https://marketplace.visualstudio.com/items?itemName=anthropic.claude-code)에서 직접 설치.
- **Spark 아이콘 안 보임**: 파일 열기(폴더만으론 부족), 버전 확인, Reload Window, 충돌 AI 확장(Cline/Continue) 비활성화, workspace trust 확인. 대안으로 Status Bar의 ✱ Claude Code.
- **macOS에서 Cmd+Esc 무반응**: macOS Tahoe+의 시스템 Game Overlay 단축키가 가로챔. System Settings → Keyboard → Keyboard Shortcuts → Game Controllers에서 Game Overlay 체크 해제. 또는 `Cmd+K Cmd+S` Keyboard Shortcuts 에디터에서 `Claude Code: Focus input` 재바인딩.
- **응답 없음**: 인터넷 확인, 새 대화, 터미널에서 `claude` 실행해 상세 에러 확인.

### 확장 제거 (저장소까지 삭제)

Extensions 뷰에서 Uninstall 후, 데이터·설정까지 지우려면:
```bash
# macOS
rm -rf ~/Library/"Application Support"/Code/User/globalStorage/anthropic.claude-code
# Linux
rm -rf ~/.config/Code/User/globalStorage/anthropic.claude-code
```
```powershell
# Windows PowerShell
Remove-Item -Recurse -Force "$env:APPDATA\Code\User\globalStorage\anthropic.claude-code"
```

---

## JetBrains IDE

Claude Code는 전용 플러그인으로 JetBrains IDE에 통합되어 인터랙티브 diff 뷰, 선택 컨텍스트 공유 등을 제공한다.

### 지원 IDE 및 기능

지원: IntelliJ IDEA, PyCharm, Android Studio, WebStorm, PhpStorm, GoLand 등 대부분의 JetBrains IDE.

| 기능 | 설명 |
|------|------|
| Quick launch | `Cmd+Esc` (Mac) / `Ctrl+Esc` (Win/Linux)로 에디터에서 바로 열기, 또는 Claude Code 버튼 클릭 |
| Diff viewing | 코드 변경을 터미널 대신 IDE diff 뷰어에 표시 |
| Selection context | 현재 선택/탭을 자동으로 Claude와 공유. [`Read` deny rule](/en/permissions#read-and-edit)로 매칭 파일 차단 |
| File reference shortcuts | `Cmd+Option+K` (Mac) / `Alt+Ctrl+K` (Win/Linux)로 `@src/auth.ts#L1-99` 같은 파일 참조 삽입 |
| Diagnostic sharing | lint·syntax 에러 등 IDE 진단을 작업 중 자동 공유 |

### 설치

[Claude Code 플러그인](https://plugins.jetbrains.com/plugin/27310-claude-code-beta-)을 JetBrains 마켓플레이스에서 설치하고 IDE 재시작. Claude Code 자체가 없으면 먼저 [[01 시작하기]]로 설치. 플러그인 설치 후 적용을 위해 IDE를 **완전히 재시작**해야 할 수 있다(때로 여러 번).

### 사용

- **IDE 내부에서**: IDE 통합 터미널에서 `claude` 실행하면 모든 통합 기능 활성.
- **외부 터미널에서**: 외부 터미널에서 `/ide` 명령으로 JetBrains IDE에 연결.

```bash
claude
```
```text
/ide
```

Claude가 IDE와 같은 파일에 접근하게 하려면 IDE 프로젝트 루트와 같은 디렉터리에서 Claude Code를 시작.

### 설정

**Claude Code 설정**으로 IDE 통합 구성: `claude` → `/config` → diff tool을 `auto`(IDE 표시) 또는 `terminal`(터미널 유지)로 설정.

**플러그인 설정**(**Settings → Tools → Claude Code [Beta]**):

| 항목 | 설명 |
|------|------|
| Claude command | Claude 실행 커스텀 명령. 예: `claude`, `/usr/local/bin/claude`, `npx @anthropic-ai/claude-code` |
| Suppress notification for Claude command not found | 명령 못 찾음 알림 건너뛰기 |
| Enable using Option+Enter for multi-line prompts | macOS 전용. Option+Enter로 줄바꿈. Option 키가 예기치 않게 캡처되면 비활성화. 터미널 재시작 필요 |
| Enable automatic updates | 플러그인 업데이트 자동 확인·설치(재시작 시 적용) |

> [!tip] WSL 사용자
> Claude command를 `wsl -d Ubuntu -- bash -lic "claude"`로 설정(`Ubuntu`는 배포판 이름으로 교체).

**ESC 키 구성**: JetBrains 터미널에서 ESC가 Claude Code 작업을 중단하지 못하면 **Settings → Tools → Terminal**에서 "Move focus to the editor with Escape" 체크 해제, 또는 "Configure terminal keybindings"에서 "Switch focus to Editor" 단축키 삭제 후 적용.

### 특수 구성

#### 원격 개발 (Remote Development)

> [!warning] 플러그인은 원격 호스트에 설치
> JetBrains Remote Development 사용 시 플러그인을 **Settings → Plugin (Host)**로 원격 호스트에 설치해야 한다. 로컬 클라이언트가 아님.

#### WSL 구성

WSL2 + JetBrains IDE에서 "No available IDEs detected"가 뜨면, 원인은 보통 WSL2의 NAT 네트워킹 또는 Windows 방화벽이 WSL2와 Windows 호스트의 IDE 간 연결을 차단하는 것(WSL1은 영향 없음).

**방법 1 — 방화벽 규칙(권장, 기존 네트워킹 유지)**:
```bash
# WSL 셸에서 IP/서브넷 확인 (예: 172.21.x.x → 172.21.0.0/16)
hostname -I
```
```powershell
# 관리자 PowerShell — 서브넷을 본인 것에 맞춰 조정
New-NetFirewallRule -DisplayName "Allow WSL2 Internal Traffic" -Direction Inbound -Protocol TCP -Action Allow -RemoteAddress 172.21.0.0/16 -LocalAddress 172.21.0.0/16
```
이후 IDE와 Claude Code를 닫고 다시 열어 규칙 적용.

**방법 2 — mirrored 네트워킹**(Windows 11 22H2+ 필요. Windows 10은 방법 1):
```ini
# Windows 사용자 디렉터리의 .wslconfig
[wsl2]
networkingMode=mirrored
```
이후 PowerShell에서 `wsl --shutdown`으로 WSL 재시작.

### JetBrains 문제 해결 / 보안

- **플러그인 작동 안 함**: 프로젝트 루트에서 실행 중인지 확인, 플러그인 활성 확인, IDE 완전 재시작(여러 번), Remote Development면 원격 호스트 설치 확인.
- **IDE 미감지("No available IDEs detected")**: 플러그인 설치·활성 확인, IDE 완전 재시작, 통합 터미널에서 실행 확인, WSL이면 위 WSL 구성.
- **Command not found**: `claude --version`으로 설치 확인, 플러그인 설정에서 Claude 명령 경로 구성, WSL은 WSL 명령 포맷 사용.
- **보안**: auto-edit 권한 시 IDE가 자동 실행할 수 있는 설정 파일을 수정해 bash 실행 권한 프롬프트를 우회할 위험이 있다. 수동 승인 모드 사용, 신뢰 프롬프트만 사용, Claude가 수정 가능한 파일 인지를 권장. → [[18 보안과 샌드박스]]
- IDE 외부의 설치·로그인 문제는 [[25 트러블슈팅]].

---

## 데스크톱 앱 시작하기 (Quickstart)

데스크톱 앱은 Claude Code를 GUI로 제공하며, 여러 세션을 나란히 실행하도록 설계됐다: 병렬 작업용 사이드바, 드래그앤드롭 레이아웃(통합 터미널·파일 에디터), 시각적 diff 리뷰, 라이브 앱 미리보기, GitHub PR 모니터링(auto-merge), 스케줄 작업. **터미널 불필요**.

### 다운로드와 요구사항

| 플랫폼 | 다운로드 |
|--------|----------|
| macOS | [Universal 빌드](https://claude.ai/api/desktop/darwin/universal/dmg/latest/redirect?utm_source=claude_code&utm_medium=docs) (Intel + Apple Silicon) |
| Windows x64 | [setup 인스톨러](https://claude.ai/api/desktop/win32/x64/setup/latest/redirect?utm_source=claude_code&utm_medium=docs) |
| Windows ARM64 | [ARM64 인스톨러](https://claude.ai/api/desktop/win32/arm64/setup/latest/redirect?utm_source=claude_code&utm_medium=docs) |
| Linux (베타) | Ubuntu 22.04+ / Debian 12+, x86_64·arm64. apt 저장소로 설치 — 아래 [Linux 베타](#linux-베타-desktop-linux) 참고 |

- **구독 필요**: Pro, Max, Team, 또는 Enterprise.
- **Windows 첫 실행 시 [Git for Windows](https://git-scm.com/downloads/win) 필요** — 설치 후 앱 재시작.
- 데스크톱 앱에 Claude Code가 포함되어 Node.js·CLI 별도 설치 불필요. 터미널에서 `claude`를 쓰려면 CLI를 별도 설치([[01 시작하기]]).

### Linux 베타 (desktop-linux)

Ubuntu·Debian 계열에서 macOS·Windows와 동일한 Chat·Cowork·Code 세 탭을 제공한다(요구사항은 Ubuntu 22.04+ 또는 Debian 12+, x86_64/arm64 — 조건을 만족하는 다른 Debian 계열도 동작할 수 있으나 공식 테스트 대상은 아님).

**설치**(apt 저장소 등록 — 이후 업데이트가 일반 시스템 패키지 업데이트로 도착):

```bash
sudo curl -fsSLo /usr/share/keyrings/claude-desktop-archive-keyring.asc https://downloads.claude.ai/claude-desktop/key.asc
echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/claude-desktop-archive-keyring.asc] https://downloads.claude.ai/claude-desktop/apt/stable stable main" | sudo tee /etc/apt/sources.list.d/claude-desktop.list
sudo apt update && sudo apt install claude-desktop
```

앱 런처에서 **Claude** 실행 또는 터미널에서 `claude-desktop`. 로그인은 macOS/Windows와 동일(구독 또는 조직 SSO) — **Console API 키로 직접 로그인 불가**, API 키 인증은 CLI를 쓴다. 저장소 없이 [claude.com/download](https://claude.com/download)의 `.deb`를 직접 설치할 수도 있으나(`sudo apt install ./claude-desktop_*.deb`) 이 경로는 apt 업데이트를 안 받는다.

**업데이트**: `sudo apt update && sudo apt upgrade` (앱 자체 자동 업데이트 없음). **제거**: `sudo apt remove claude-desktop` (저장소 등록도 했다면 `/etc/apt/sources.list.d/claude-desktop.list` 별도 삭제).

**Linux 베타에 아직 없는 것**: [Computer use](#claude에게-컴퓨터-사용-허용-computer-use)(앱·화면 제어), 음성 받아쓰기([[02 CLI 레퍼런스]]의 CLI로 대체), 네이티브 Wayland에서의 Quick Entry 전역 단축키(데스크톱 환경의 GlobalShortcuts portal 필요, X11은 동작), Fedora/RHEL 지원. 이 기능들이 필요하면 같은 엔진을 쓰는 CLI를 사용.

### Windows에서 WSL 세션 (desktop-wsl)

Windows의 Code 탭은 세션을 Windows 자체가 아니라 **WSL 2 배포판 안에서** 실행할 수 있다. Claude Code 프로세스·도구·git이 모두 배포판 내부에서 그 Linux 툴체인과 네이티브 Linux 경로로 실행되므로, 프로젝트가 실제로 타깃하는 환경과 일치한다. 저장소가 배포판 파일시스템 안에 있으면 이 방식을 쓴다 — Windows에서 그 파일에 접근하면 네트워크 파일시스템을 경유해 느리고 파일 감시(file watching)도 깨진다.

**요구사항**: [WSL 2](https://learn.microsoft.com/windows/wsl/install)가 설치된 Windows 10/11(WSL 1 불가), 설치된 배포판 1개 이상(예 Ubuntu), 배포판 내부에 `git` 설치.

**세션 시작**: ① 새 세션 시작 후 환경 선택기를 열면 설치된 WSL 2 배포판들이 **WSL** 섹션에 나타난다 → 하나 선택. ② 세션은 배포판 홈 디렉터리에서 시작하므로 폴더 선택기로 프로젝트 폴더를 고른다(탐색은 배포판 내부에서 `/home/you/project` 같은 Linux 경로로 이뤄짐). ③ 배포판+폴더 조합마다 최초 1회 워크스페이스 신뢰 다이얼로그가 뜬다 — 한 배포판에서 신뢰한 폴더가 다른 배포판이나 Windows 쪽 동일 경로에는 적용되지 않는다. `\\wsl.localhost\...` 폴더를 일반 폴더 선택기에서 직접 열어도 해당 배포판 안에서 다시 열린다. 배포판별 최근 폴더가 선택기에 표시돼 재연결이 한 번의 클릭으로 된다.

**동작하는 것**: 병렬 세션, side chat, 시각적 diff 리뷰, 브랜치·PR 상태, 워크트리 — 모두 배포판 내부의 git·툴체인 기반. **Open in editor**는 [Remote - WSL](https://code.visualstudio.com/docs/remote/wsl)로 연결된 VS Code를 연다. **아직 없는 것**: 통합 터미널, 커넥터·플러그인, session forking, 파일 브라우저 pane, 컴포저 `@` 파일 제안.

**관리형 디바이스**: 조직이 관리하는 디바이스에서는 WSL 세션이 막힐 수 있다("device is managed" 메시지) — admin-setup의 [설정 전달 방식](https://code.claude.com/docs/en/admin-setup#decide-how-settings-reach-devices) 참고.

### 세 개의 탭

데스크톱 앱에는 세 탭이 있다:

| 탭 | 용도 |
|----|------|
| **Chat** | 파일 접근 없는 일반 대화(claude.ai와 유사) |
| **Cowork** | 자체 환경의 클라우드 VM에서 작업하는 자율 백그라운드 에이전트. Dispatch·장기 에이전트 작업 |
| **Code** | 로컬 파일에 직접 접근하는 인터랙티브 코딩 어시스턴트. 변경을 실시간 검토·승인 |

이 노트는 주로 **Code** 탭을 다룬다.

### 첫 세션 (설치 → 실행)

1. **설치·로그인**: 인스톨러 실행, macOS는 Applications, Windows는 시작 메뉴에서 실행 후 Anthropic 계정 로그인.
2. **Code 탭 열기**: 상단 중앙 **Code**. 업그레이드 요구 시 유료 플랜 구독. 403 에러는 인증 트러블슈팅 참고.
3. **환경·폴더 선택**: **Local**(내 머신, 파일 직접 접근) 선택 후 **Select folder**. 또는 **Remote**(클라우드, 앱 닫아도 계속), **SSH**(원격 머신). Windows 로컬 세션은 Git 필수.
4. **모델 선택**: send 버튼 옆 드롭다운(Opus/Sonnet/Haiku). 나중에 변경 가능.
5. **할 일 지시**: 예) `Find a TODO comment and fix it`, `Add tests for the main function`, `Create a CLAUDE.md with instructions for this codebase`.
6. **변경 검토·수락**: 기본 Ask permissions 모드 — diff 뷰 + Accept/Reject 버튼 + 실시간 업데이트. 수락 전엔 파일이 수정되지 않음.

> [!tip] 처음에는
> 잘 아는 작은 프로젝트로 시작하면 Claude Code가 무엇을 할 수 있는지 가장 빠르게 파악할 수 있다.

다음에 시도할 것들: 중단·조정(stop 버튼/입력 후 Enter), `@filename`·첨부·드래그앤드롭으로 컨텍스트 제공, `/` 또는 +→Slash commands로 스킬 사용([[07 스킬]]), diff 뷰 리뷰·코멘트, 권한 모드 조정([[05 권한]]), 플러그인 추가([[11 플러그인]]), 패널 배치, 앱 미리보기, PR 추적, 스케줄 작업([[13 자동화와 스케줄링]]), 병렬 세션·side chat·클라우드 전송.

---

## 데스크톱 앱 레퍼런스 (Code 탭)

### 세션 시작 — 4가지 사전 구성

Code 탭에서 각 대화는 자체 채팅 기록·프로젝트 폴더·코드 변경을 가진 **세션(session)**이다. 사이드바에서 여러 세션을 병렬 실행한다. 첫 메시지 전에 프롬프트 영역에서 4가지 구성:

- **Environment**: **Local**(내 머신) / **Remote**(Anthropic 클라우드) / **SSH**(내가 관리하는 원격 머신).
- **Project folder**: 작업 폴더·저장소. 원격은 여러 저장소 추가 가능.
- **Model**: send 버튼 옆 드롭다운. 세션 중 변경 가능.
- **Permission mode**: 자율 수준. 세션 중 변경 가능.

`Enter`로 시작.

### 프롬프트 박스와 컨텍스트

- 입력 후 `Enter`로 전송. **중단·조정**: stop 버튼으로 즉시 중단, 또는 교정 입력 후 `Enter`로 실행 중지 없이 전송 — Claude는 현재 액션이 끝나면 교정을 읽고 다음 단계 전에 조정.
- 프롬프트 박스 옆 **+** 버튼: 파일 첨부, 스킬, 커넥터, 플러그인.
- **@mention files**: `@`+파일명으로 컨텍스트 추가(원격 세션은 불가).
- **Attach files**: 이미지·PDF 등 첨부 버튼 또는 드래그앤드롭. 버그 스크린샷·디자인 목업·참고 문서에 유용.

### 권한 모드 (Permission modes)

세션 중 send 버튼 옆 모드 선택기로 전환. Ask permissions로 시작해 익숙해지면 Auto accept edits나 Plan으로 이동 권장. 상세는 [[05 권한]].

| Mode | Settings key | 동작 |
|------|--------------|------|
| **Ask permissions** | `default` | 파일 편집·명령 실행 전 질문. diff를 보고 각 변경 수락/거부. 신규 사용자 권장 |
| **Auto accept edits** | `acceptEdits` | 파일 편집 + `mkdir`/`touch`/`mv` 등 흔한 파일시스템 명령 자동 수락. 다른 터미널 명령은 여전히 질문 |
| **Plan mode** | `plan` | 파일 읽고 명령 실행해 탐색, 소스 편집 없이 플랜 제안. 복잡한 작업에서 접근을 먼저 검토 |
| **Auto** | `auto` | 백그라운드 안전 검사(요청과의 정합성 검증)와 함께 모든 액션 실행. 프롬프트 감소 + 감독 유지. Settings → Claude Code에서 활성화 |
| **Bypass permissions** | `bypassPermissions` | 권한 프롬프트 없이 실행(CLI의 `--dangerously-skip-permissions` 등가). Settings에서 "Allow bypass permissions mode" 활성화. 샌드박스 컨테이너/VM에서만. Enterprise 관리자가 비활성화 가능 |

- `dontAsk` 모드는 [[02 CLI 레퍼런스]] / [[05 권한]]의 CLI에서만 가능.
- **Auto 모드 가용성**: 리서치 프리뷰, Anthropic API의 모든 사용자에게 제공, **Claude Opus 4.6 이상 또는 Sonnet 4.6** 필요. Vertex AI로 라우팅하는 Enterprise는 `CLAUDE_CODE_ENABLE_AUTO_MODE` 설정 전엔 off이며 거기선 Opus 4.7/4.8만 지원.
- **원격 세션**: Auto accept edits·Plan mode 지원. Ask permissions는 원격이 기본 자동 수락이라 불가, Bypass는 환경이 이미 샌드박스라 불가.
- Enterprise 관리자는 가용 권한 모드를 제한 가능(아래 enterprise 구성).

> [!tip] 베스트 프랙티스
> 복잡한 작업은 Plan 모드로 시작해 접근을 그린 뒤, 플랜 승인 후 Auto accept edits나 Ask permissions로 실행. → [[20 베스트 프랙티스와 워크플로우]]

### 앱 미리보기 (Preview)

Claude가 dev 서버를 띄우고 임베디드 브라우저로 자체 변경을 검증한다. 프론트엔드뿐 아니라 백엔드 서버도 — API 엔드포인트 테스트, 서버 로그 보기, 발견한 이슈 반복 수정. 대부분 파일 편집 후 자동으로 서버 시작. 정적 HTML/PDF/이미지/비디오도 채팅에서 경로 클릭으로 미리보기 가능. 기본적으로 매 편집 후 자동 검증(auto-verify).

Preview 패널에서: 임베디드 브라우저로 직접 상호작용, Claude가 스크린샷·DOM 검사·클릭·폼 입력으로 자체 검증하는 것 관찰, **Preview** 드롭다운으로 서버 시작/중지, **Persist sessions**로 쿠키·로컬스토리지 유지(재로그인 불필요), 서버 구성 편집·전체 중지.

커스텀 dev 명령은 `.claude/launch.json` 편집(아래 [[#미리보기 서버 구성 (.claude/launch.json)]]). Settings → Claude Code에서 Persist preview sessions off로 세션 데이터 정리, Preview off로 전체 비활성화.

### diff 뷰로 변경 검토

변경 후 `+12 -1` 같은 diff 통계 표시기 클릭 → diff 뷰어(좌측 파일 목록, 우측 변경). 특정 줄 클릭으로 코멘트 박스 → 피드백 입력 후 `Enter`. 여러 줄 코멘트를 한 번에 제출:
- **macOS**: `Cmd+Enter`
- **Windows**: `Ctrl+Enter`

Claude가 코멘트를 읽고 변경하면 새 diff로 표시.

#### 코드 리뷰 (Review code)

diff 뷰 우상단 **Review code**로 커밋 전 Claude에게 변경 평가 요청. 고신호 이슈(컴파일 에러, 명확한 로직 에러, 보안 취약점, 명백한 버그)에 집중하며, 스타일·포맷·기존 이슈·린터가 잡을 것은 표시하지 않는다. → [[20 베스트 프랙티스와 워크플로우]]

#### PR 상태 모니터링

PR 오픈 후 세션에 CI 상태 바 표시. Claude Code가 [GitHub CLI](https://cli.github.com/)로 체크 결과를 폴링하고 실패를 표면화.
- **Auto-fix**: 활성화 시 실패 출력을 읽고 반복하며 자동 수정 시도.
- **Auto-merge**: 모든 체크 통과 시 PR 병합(squash). GitHub 저장소 설정에서 auto-merge가 활성화돼 있어야 함.

CI 종료 시 데스크톱 알림. PR 병합/종료 시 세션 자동 보관은 Settings → Claude Code의 auto-archive. **PR 모니터링은 `gh`(GitHub CLI) 설치·인증 필요** — 없으면 첫 PR 생성 시 설치 안내. → [[16 CI-CD와 팀 통합]]

### 워크스페이스 배치 (panes)

Code 탭은 배치 가능한 panes 중심: chat, diff, preview, terminal, file, plan, tasks, subagent. 헤더 드래그로 이동, 가장자리 드래그로 리사이즈. **Cmd+\\**(macOS) / **Ctrl+\\**(Windows)로 포커스된 pane 닫기. 추가 pane은 세션 툴바 **Views** 메뉴.

> [!note] 버전 요구
> pane 레이아웃·터미널·파일 에디터·뷰 모드는 Claude Desktop **v1.2581.0 이상** 필요. macOS는 **Claude → Check for Updates**, Windows는 **Help → Check for Updates**.

#### 통합 터미널

세션 옆에서 명령 실행. **Views** 메뉴 또는 **Ctrl+\`**(macOS·Windows). 세션 작업 디렉터리에서 열리고 Claude와 동일 환경 공유 — `npm test`, `git status`가 Claude가 편집 중인 파일을 본다. 두 번째 탭은 터미널 pane 헤더의 **+** 또는 폴더 우클릭 **Open in terminal**. **로컬 세션 전용**.

#### 파일 열기·편집

채팅/diff에서 파일 경로 클릭 → file pane. HTML/PDF/이미지/비디오는 preview pane으로. 스팟 편집 후 **Save**. 디스크에서 변경됐으면 경고 후 override/discard. **Discard**로 되돌리기, pane 헤더 경로 클릭으로 절대 경로 복사. file pane은 **로컬·SSH 세션**에서 가능(원격은 Claude에게 변경 요청).

#### 다른 앱에서 파일 열기 (우클릭 메뉴)

채팅/diff/file pane에서 파일 경로 우클릭:
- **Attach as context**: 다음 프롬프트에 파일 추가
- **Open in**: VS Code, Cursor, Zed 등 설치된 에디터에서 열기
- **Show in Finder**(macOS) / **Show in Explorer**(Windows): 폴더 열기
- **Copy path**: 절대 경로 복사

#### 뷰 모드 전환

채팅 트랜스크립트 상세 수준 제어. send 버튼 옆 **Transcript view** 드롭다운 또는 **Ctrl+O**(macOS·Windows)로 순환.

| Mode | 표시 내용 |
|------|-----------|
| **Normal** | 도구 호출을 요약으로 접고, 전체 텍스트 응답 |
| **Verbose** | 모든 도구 호출·파일 읽기·중간 단계 |
| **Summary** | Claude의 최종 응답과 변경만 |

디버깅엔 Verbose, 여러 세션 결과 빠르게 스캔엔 Summary.

#### 키보드 단축키

**Cmd+/**(macOS) / **Ctrl+/**(Windows)로 Code 탭 단축키 전체 보기. Windows는 아래 **Cmd** 대신 **Ctrl**. 세션 순환·터미널 토글·뷰 모드 토글은 모든 플랫폼에서 **Ctrl**.

| Shortcut | Action |
|----------|--------|
| `Cmd` `/` | 단축키 표시 |
| `Cmd` `N` | 새 세션 |
| `Cmd` `W` | 세션 닫기 |
| `Ctrl` `Tab` / `Ctrl` `Shift` `Tab` | 다음/이전 세션 |
| `Cmd` `Shift` `]` / `Cmd` `Shift` `[` | 다음/이전 세션 |
| `Esc` | Claude 응답 중지 |
| `Cmd` `Shift` `D` | diff pane 토글 |
| `Cmd` `Shift` `P` | preview pane 토글 |
| `Cmd` `Shift` `S` | preview에서 요소 선택 |
| `Ctrl` `` ` `` | terminal pane 토글 |
| `Cmd` `\` | 포커스된 pane 닫기 |
| `Cmd` `;` | side chat 열기 |
| `Ctrl` `O` | 뷰 모드 순환 |
| `Cmd` `Shift` `M` | 권한 모드 메뉴 |
| `Cmd` `Shift` `I` | 모델 메뉴 |
| `Cmd` `Shift` `E` | effort 메뉴 |
| `1`–`9` | 열린 메뉴에서 항목 선택 |

이 단축키는 Code 탭에만 적용된다. 터미널 인터랙티브 모드 단축키(`Shift+Tab`으로 모드 순환 등)는 데스크톱에 적용 안 됨.

#### 사용량 확인

모델 picker 옆 usage ring 클릭으로 현재 컨텍스트 윈도우 사용량과 기간 플랜 사용량 확인. 컨텍스트는 세션별, 플랜 사용량은 모든 Claude Code 표면에서 공유. → [[19 비용과 성능]]

### Claude에게 컴퓨터 사용 허용 (Computer use)

Claude가 앱을 열고 화면을 제어해 GUI에서만 되는 작업(네이티브 앱 테스트, 모바일 시뮬레이터, CLI 없는 데스크톱 도구)을 수행. 상세는 [[21 브라우저와 컴퓨터 사용]].

> [!note] 가용성
> macOS·Windows의 리서치 프리뷰, **Pro 또는 Max** 플랜 필요(Team/Enterprise 불가). 데스크톱 앱이 실행 중이어야 함. 기본 off.

> [!warning] 신뢰 경계
> [샌드박스 Bash 도구]([[18 보안과 샌드박스]])와 달리 컴퓨터 사용은 실제 데스크톱에서 승인한 것에 접근한다. Claude가 액션마다 검사하고 화면 내용의 prompt injection 가능성을 표시하지만 신뢰 경계가 다르다.

**언제 적용되나**: Claude는 가장 정밀한 도구를 먼저 시도 — 서비스 커넥터 있으면 커넥터, 셸 명령이면 Bash, 브라우저 작업이고 Claude in Chrome 셋업돼 있으면 그것, 아무것도 없으면 컴퓨터 사용(가장 넓고 느림).

**활성화** (Settings > General의 Desktop app):
1. 데스크톱 앱 최신화·재시작.
2. **Computer use** 토글 on. Windows는 즉시 적용.
3. macOS는 두 권한 부여: **Accessibility**(클릭·타입·스크롤), **Screen Recording**(화면 보기).

**앱 권한 티어** (앱 카테고리별 고정, 변경 불가):

| Tier | Claude가 할 수 있는 것 | 적용 대상 |
|------|----------------------|-----------|
| View only | 스크린샷으로 보기만 | 브라우저, 트레이딩 플랫폼 |
| Click only | 클릭·스크롤(타입·단축키 불가) | 터미널, IDE |
| Full control | 클릭·타입·드래그·단축키 | 그 외 전부 |

처음 앱 사용 시 세션에 프롬프트 — **Allow for this session** / **Deny**. 승인은 현재 세션 동안(Dispatch-spawned 세션은 30분). 터미널·Finder/File Explorer·System Settings 같은 광범위 앱은 추가 경고 표시. Settings > General에서 **Denied apps**(프롬프트 없이 거부), **Unhide apps when Claude finishes**(작업 중 숨긴 창 복원) 구성.

### 세션 관리

#### 병렬 세션 (Git 격리)

**+ New session**(사이드바) 또는 **Cmd+N**/**Ctrl+N**으로 병렬 작업. **Ctrl+Tab**/**Ctrl+Shift+Tab**으로 순환. Git 저장소면 각 세션이 [Git worktree]로 프로젝트의 격리 사본을 받아, 커밋 전까지 세션 간 변경이 섞이지 않는다.

두 세션 동시 보기: **Cmd**(macOS)/**Ctrl**(Windows)+사이드바 세션 클릭 → 두 번째 pane. 분할 중 다른 세션 클릭은 포커스된 pane을 교체. **Cmd+\\**/**Ctrl+\\**로 포커스 pane 닫고 단일 세션 복귀.

- 워크트리 기본 위치: `<project-root>/.claude/worktrees/`. Settings → Claude Code의 "Worktree location"으로 변경 가능. 브랜치 prefix도 설정 가능.
- 워크트리 제거: 사이드바 세션 호버 → archive 아이콘.
- **Auto-archive after PR merge or close**(Settings → Claude Code): PR 병합/종료 시 세션 자동 보관(완료된 로컬 세션만).
- gitignore된 파일(`.env`)을 새 워크트리에 포함하려면 프로젝트 루트에 `.worktreeinclude` 파일 생성.

> [!note] Git 필수
> 세션 격리는 [Git](https://git-scm.com/downloads) 필요. 대부분 Mac은 기본 포함(`git --version`으로 확인). Windows는 Code 탭 동작에 Git 필수.

사이드바 상단 컨트롤로 상태·프로젝트·환경별 필터·그룹화. 세션 이름 변경은 활성 세션 툴바 제목 클릭. 컨텍스트가 차면 자동 요약 후 계속, `/compact`로 조기 요약 가능. → [[03 메모리와 컨텍스트]]. Code 세션이 작업을 끝냈는데 보고 있지 않으면 OS 알림 전송.

#### Side chat (`/btw`)

세션 컨텍스트를 쓰되 메인 대화에 더하지 않는 곁다리 질문. 코드 이해·가정 확인·아이디어 탐색을 메인 세션을 벗어나지 않고. **Cmd+;**(macOS)/**Ctrl+;**(Windows) 또는 `/btw`. 메인 스레드의 그 시점까지 모든 것을 읽을 수 있다. **로컬·SSH 세션**에서 가능.

#### 백그라운드 작업 (tasks pane)

현재 세션 내 백그라운드 작업(subagents, 백그라운드 셸 명령, 동적 워크플로우) 표시. **Views** 메뉴 또는 드래그. 항목 클릭으로 subagent pane에서 출력 보기·중지. 다른 세션은 사이드바. → [[08 서브에이전트와 에이전트 팀]]

#### 장기 작업 원격 실행 (Remote)

대규모 리팩터·테스트·마이그레이션 등은 세션 시작 시 **Remote** 선택. Anthropic 클라우드에서 돌며 앱을 닫거나 컴퓨터를 꺼도 계속된다. [claude.ai/code](https://claude.ai/code)나 iOS 앱에서 모니터링. 원격은 다중 저장소 지원 — repo pill 옆 **+**로 추가 저장소(각 자체 브랜치 선택기). → [[15 웹과 모바일]]

#### 다른 표면에서 이어가기 (Continue in)

세션 툴바 우하단 VS Code 아이콘의 **Continue in** 메뉴:
- **Claude Code on the Web**: 로컬 세션을 원격으로 전송. 데스크톱이 브랜치를 push하고 대화 요약을 생성, 전체 컨텍스트로 새 원격 세션 생성. 깨끗한 working tree 필요, SSH 세션 불가.
- **Your IDE**: 현재 작업 디렉터리에서 지원 IDE로 프로젝트 열기.

#### Dispatch에서 온 세션

[Dispatch](https://support.claude.com/en/articles/13947068)는 Cowork 탭의 영속 대화다. 작업을 메시지하면 처리 방법을 결정한다. 작업이 Code 세션이 되는 두 경로: 직접 요청("open a Claude Code session and fix the login bug"), 또는 Dispatch가 개발 작업으로 판단해 자체 spawn. 버그 수정·의존성 업데이트·테스트·PR이 Code로 라우팅; 리서치·문서·스프레드시트는 Cowork에 남음. Code 탭 사이드바에 **Dispatch** 배지로 표시, 완료/승인 필요 시 폰에 푸시 알림. 컴퓨터 사용이 켜져 있으면 Dispatch-spawned 세션도 사용 가능(앱 승인 30분 후 만료·재프롬프트). **Pro/Max 필요**(Team/Enterprise 불가).

### Claude Code 확장 (Extend)

사이드바 **Customize**에서 커넥터·스킬·플러그인 한곳 관리.

#### 외부 도구 연결 (Connectors)

로컬·SSH 세션은 **+** → **Connectors**로 Google Calendar, Slack, GitHub, Linear, Notion 등 추가. 세션 전·중 추가 가능. 원격 세션은 **+** 불가(단, routines가 생성 시점에 커넥터 구성). 관리·연결 해제는 Settings → Connectors 또는 Connectors 메뉴의 **Manage connectors**.

커넥터는 그래픽 셋업 플로우를 가진 [[10 MCP]] 서버다. 목록에 없는 통합은 설정 파일로 MCP 서버를 수동 추가하거나 커스텀 커넥터 생성.

#### 스킬 사용 (Use skills)

[[07 스킬]]은 능력을 확장. 관련 시 자동 로드되거나, `/` 입력 또는 **+** → **Slash commands**로 직접 호출. 내장 명령, 커스텀 스킬, 프로젝트 스킬, 설치된 플러그인 스킬 포함. 선택하면 입력 필드에 하이라이트되고, 뒤에 작업을 적어 전송.

#### 플러그인 설치 (Install plugins)

[[11 플러그인]]은 스킬·에이전트·훅·MCP·LSP 구성을 추가하는 재사용 패키지. 터미널 없이 데스크톱에서 설치. 로컬·SSH 세션은 **+** → **Plugins**로 설치된 플러그인 보기, **Add plugin**으로 브라우저(공식 Anthropic 마켓플레이스 포함), **Manage plugins**로 활성/비활성/제거. user/project/local 스코프. 조직 중앙 관리 플러그인은 CLI와 동일하게 사용 가능. **원격 세션은 플러그인 불가.**

#### 미리보기 서버 구성 (.claude/launch.json)

Claude가 dev 서버 셋업을 자동 감지해 세션 시작 시 선택한 폴더 루트의 `.claude/launch.json`에 저장. Preview가 이 폴더를 작업 디렉터리로 쓰므로 부모 폴더 선택 시 자체 dev 서버를 가진 하위 폴더는 자동 감지 안 됨(해당 폴더에서 세션 시작하거나 수동 추가). 커스터마이즈는 파일 직접 편집 또는 Preview 드롭다운 **Edit configuration**. JSON with comments 지원.

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "my-app",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "port": 3000
    }
  ]
}
```

**auto-verify**: `autoVerify` 활성 시 편집 후 자동 검증(스크린샷·에러 확인·동작 확인). 기본 on. 프로젝트별 비활성화는 `"autoVerify": false` 또는 Preview 드롭다운 토글.

```json
{
  "version": "0.0.1",
  "autoVerify": false,
  "configurations": [...]
}
```

**구성 필드** (`configurations` 배열의 각 항목):

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | 서버 고유 식별자 |
| `runtimeExecutable` | string | 실행 명령(`npm`, `yarn`, `node` 등) |
| `runtimeArgs` | string[] | `runtimeExecutable`에 넘길 인자(예: `["run", "dev"]`) |
| `port` | number | 서버 포트. 기본 3000 |
| `cwd` | string | 프로젝트 루트 기준 작업 디렉터리. 기본 루트. `${workspaceFolder}`로 루트 명시 |
| `env` | object | 추가 env(예: `{ "NODE_ENV": "development" }`). repo에 커밋되므로 비밀값 금지 — 비밀은 로컬 환경 에디터에 |
| `autoPort` | boolean | 포트 충돌 처리(아래) |
| `program` | string | `node`로 실행할 스크립트 |
| `args` | string[] | `program`에 넘길 인자(`program` 설정 시만) |

- **`program` vs `runtimeExecutable`**: 패키지 매니저로 dev 서버 띄우면 `runtimeExecutable`+`runtimeArgs`(예: `npm run dev`). `node`로 단독 스크립트면 `program`(예: `"program": "server.js"` → `node server.js`), 추가 플래그는 `args`.
- **`autoPort`**: `true`(자유 포트 자동 선택, 대부분 적합), `false`(에러로 실패 — OAuth 콜백·CORS allowlist 등 정확한 포트 필요 시), 미설정(Claude가 정확한 포트 필요한지 물어보고 답 저장). 다른 포트를 고르면 `PORT` 환경변수로 전달.

예시 — 다중 서버(모노레포 frontend + API):
```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "frontend",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "cwd": "apps/web",
      "port": 3000,
      "autoPort": true
    },
    {
      "name": "api",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "start"],
      "cwd": "server",
      "port": 8080,
      "env": { "NODE_ENV": "development" },
      "autoPort": false
    }
  ]
}
```

### 환경 구성 (Local / Remote / SSH)

세션 시작 시 고른 환경이 Claude의 실행 위치와 연결 방식을 결정한다.

#### 로컬 세션 (Local)

데스크톱 앱은 전체 셸 환경을 항상 상속하지 않는다. macOS에서 Dock/Finder로 실행 시 `~/.zshrc`/`~/.bashrc`를 읽어 `PATH`와 고정된 Claude Code 변수 집합만 추출하고, 그 외 export 변수는 안 잡힌다. Windows는 user/system env는 상속하지만 PowerShell 프로필은 안 읽는다.

로컬 세션·dev 서버 env 설정: 프롬프트 박스 환경 드롭다운 → **Local** 호버 → 기어 아이콘 → 로컬 환경 에디터. 여기 저장한 변수는 머신에 암호화 저장되며 모든 로컬 세션·preview 서버에 적용. `~/.claude/settings.json`의 `env` 키에도 추가 가능하나 그것은 Claude 세션에만 도달(dev 서버 X). → [[04 설정]], 변수 전체 목록은 env-vars.

[Extended thinking]([[03 메모리와 컨텍스트]])은 기본 활성. 끄려면 로컬 환경 에디터에서 `MAX_THINKING_TOKENS=0`. adaptive reasoning 모델은 다른 `MAX_THINKING_TOKENS` 값을 무시(adaptive가 thinking 깊이 제어). Opus 4.6·Sonnet 4.6은 `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`로 고정 budget 사용; Opus 4.7+는 항상 adaptive로 고정 budget 모드 없음.

#### 원격 세션 (Remote)

앱을 닫아도 백그라운드에서 계속. 사용량은 구독 플랜 한도에 포함, 별도 compute 과금 없음. 환경 드롭다운 → **Add environment**로 네트워크 접근 수준·env가 다른 커스텀 클라우드 환경 생성. → [[15 웹과 모바일]], [[19 비용과 성능]]

#### SSH 세션

데스크톱 앱을 인터페이스로 쓰면서 원격 머신(클라우드 VM, dev 컨테이너, 특수 하드웨어 서버)에서 Claude Code 실행. 환경 드롭다운 → **+ Add SSH connection** 다이얼로그:

| 필드 | 설명 |
|------|------|
| Name | 연결 라벨 |
| SSH Host | `user@hostname` 또는 `~/.ssh/config`의 호스트 |
| SSH Port | 기본 22, SSH config 포트 사용 가능 |
| Identity File | 개인 키 경로(예: `~/.ssh/id_rsa`). 비우면 기본 키/SSH config |

원격 머신은 Linux 또는 macOS. 첫 연결 시 데스크톱이 자동으로 Claude Code 설치. 연결 후 권한 모드·커넥터·플러그인·MCP 서버 지원.

**팀용 SSH 사전 구성** (관리자): [managed settings](/en/settings#settings-precedence) 파일에 `sshConfigs` 추가. 각 사용자 환경 드롭다운에 자동 표시되고 managed로 표시되어 선택만 가능(편집·삭제 불가).

```json
{
  "sshConfigs": [
    {
      "id": "shared-dev-vm",
      "name": "Shared Dev VM",
      "sshHost": "user@dev.example.com",
      "sshPort": 22,
      "sshIdentityFile": "~/.ssh/id_ed25519",
      "startDirectory": "~/projects"
    }
  ]
}
```
각 항목은 `id`, `name`, `sshHost` 필수; `sshPort`, `sshIdentityFile`, `startDirectory`는 선택. 사용자도 자신의 `~/.claude/settings.json`에 `sshConfigs` 추가 가능(다이얼로그로 추가한 연결이 저장되는 곳).

**SSH 호스트 제한** (관리자): managed settings에 `sshHostAllowlist` 추가. 설정 시 패턴에 매칭되는 resolved hostname만 연결 가능. 빈 배열이면 SSH 세션 전체 비활성화.

```json
{ "sshHostAllowlist": ["*.devboxes.example.com", "bastion.example.com"] }
```
패턴은 대소문자 무시. `*`=모든 호스트, `*.example.com`=example.com과 모든 서브도메인, 그 외 정확 매치. 검사는 `~/.ssh/config` 해석(`ssh -G`) 후 hostname 대상이라 `Host` alias·`ProxyCommand`/`ProxyJump`도 resolved `HostName`이 매칭되면 허용. **managed settings에서만** 읽으며 user/project는 무시. **데스크톱 앱만** 준수 — CLI·IDE 확장은 안 읽고, Bash 도구로 실행하는 `ssh` 명령도 제한 안 함. 네트워크 egress가 아닌 데스크톱 연결 대상을 통제하므로 하드 경계가 필요하면 조직 네트워크/제로트러스트 통제와 병행. → [[18 보안과 샌드박스]]

### Enterprise 구성

Team/Enterprise 플랜은 admin 콘솔 컨트롤·managed settings·디바이스 관리 정책으로 데스크톱 동작 관리.

**Admin 콘솔 컨트롤** ([admin settings console](https://claude.ai/admin-settings/claude-code)):
- **Code in the desktop**: 조직 사용자의 데스크톱 Claude Code 접근 제어
- **Code in the web**: 웹 세션 활성/비활성
- **Remote Control**: Remote Control 활성/비활성
- **Disable Bypass permissions mode**: bypass 권한 모드 활성화 방지

**Managed settings** (project·user 설정을 override, Desktop이 CLI 세션 spawn 시 적용):

| Key | 설명 |
|-----|------|
| `permissions.disableBypassPermissionsMode` | `"disable"`로 Bypass permissions 모드 활성화 방지 |
| `disableAutoMode` | `"disable"`로 Auto 모드 방지(선택기에서 제거). `permissions` 아래에도 가능 |
| `autoMode` | auto 모드 classifier가 신뢰/차단할 것 커스터마이즈 |
| `sshConfigs` | SSH 연결 사전 구성(사용자 편집·삭제 불가) |
| `sshHostAllowlist` | SSH 세션을 패턴 매칭 호스트로 제한. 빈 배열은 전체 비활성화. managed에서만 |
| `managedMcpServers` | 서드파티 배포의 모든 사용자에게 MCP 서버 push. `"http"`/`"sse"`/`"stdio"` transport, 선택적 `toolPolicy` 맵으로 도구 제한. 3P 데스크톱 배포 전용 |

디스크에 배포된 managed settings 파일은 Desktop 세션에 적용. 원격 push된 managed settings는 현재 CLI·IDE 세션에만 도달하므로, Desktop 배포는 MDM으로 파일 배포 또는 admin 콘솔 컨트롤 사용. `disableBypassPermissionsMode`·`disableAutoMode`는 user/project 설정에서도 동작하지만 managed에 두면 override 방지. `autoMode`는 user/`.claude/settings.local.json`/managed에서 읽고 체크인된 `.claude/settings.json`에선 안 읽음(clone된 repo가 classifier 룰 주입 불가). 전체 managed-only 설정(`allowManagedPermissionRulesOnly`, `allowManagedHooksOnly` 포함)은 [[05 권한]]·[[18 보안과 샌드박스]].

**디바이스 관리 정책** (MDM/그룹 정책): Claude Code 기능 활성/비활성, auto-update 제어, 커스텀 배포 URL.
- macOS: `com.anthropic.Claude` preference 도메인(Jamf, Kandji 등)
- Windows: 레지스트리 `SOFTWARE\Policies\Claude`

**인증·SSO**: Enterprise는 전 사용자 SSO 강제 가능(SAML/OIDC). **데이터 처리**: 로컬 세션은 로컬, 원격은 Anthropic 클라우드 처리. → [[18 보안과 샌드박스]]

**배포**: macOS는 `.dmg`로 MDM(Jamf/Kandji), Windows는 MSIX 패키지 또는 `.exe`(사일런트 설치). 프록시·방화벽·LLM 게이트웨이는 network-config. → [[16 CI-CD와 팀 통합]], [[17 클라우드 프로바이더]]

### CLI에서 넘어오기 (Desktop vs CLI)

데스크톱은 CLI와 **동일 엔진**을 GUI로 돌린다. 같은 머신·같은 프로젝트에서 둘을 동시에 실행 가능(각자 세션 기록은 분리, 설정·프로젝트 메모리는 CLAUDE.md로 공유).

CLI 세션을 데스크톱으로 이동: 터미널에서 **`/desktop`** → 세션 저장 후 데스크톱 앱에서 열고 CLI 종료. macOS·Windows에서 Claude 구독 로그인 시 가능(API 키 인증, Bedrock/Vertex/Foundry는 불가).

> [!tip] Desktop vs CLI
> 한 창에서 병렬 세션 관리·panes 나란히 배치·시각적 변경 검토는 **Desktop**. 스크립팅·자동화·터미널 워크플로우는 **CLI**.

#### CLI 플래그 등가물

| CLI | Desktop 등가물 |
|-----|---------------|
| `--model sonnet` | send 버튼 옆 Model 드롭다운 |
| `--resume`, `--continue` | 사이드바 세션 클릭 |
| `--permission-mode` | send 버튼 옆 Mode 선택기 |
| `--dangerously-skip-permissions` | Bypass permissions 모드(Settings → Claude Code) |
| `--add-dir` | 원격 세션에서 **+** 버튼으로 다중 repo |
| `--allowedTools`, `--disallowedTools` | 세션별 등가물 없음. 설정 파일의 권한 룰은 적용됨 |
| `--verbose` | Transcript view 드롭다운의 Verbose 모드 |
| `--print`, `--output-format` | 없음. Desktop은 인터랙티브 전용 |
| `ANTHROPIC_MODEL` env | Model 드롭다운 |
| `MAX_THINKING_TOKENS` env | 로컬 환경 에디터 |

#### 공유 설정

Desktop과 CLI는 같은 설정 파일을 읽는다: 프로젝트의 `CLAUDE.md`·`CLAUDE.local.md`([[03 메모리와 컨텍스트]]), `~/.claude.json`·`.mcp.json`의 MCP 서버([[10 MCP]]), 설정의 hooks([[09 훅]])·skills([[07 스킬]]), `~/.claude.json`·`~/.claude/settings.json`의 설정([[04 설정]]), Sonnet/Opus/Haiku 모델.

> [!note] Claude Desktop 채팅 앱의 MCP 서버
> Desktop 앱은 `claude_desktop_config.json`의 MCP 서버를 `~/.claude.json`·`.mcp.json`과 함께 Code 탭 세션에 로드한다. 독립 CLI는 `claude_desktop_config.json`을 안 읽음 — macOS·WSL에서 `claude mcp add-from-claude-desktop`으로 복사. → [[10 MCP]]

#### 기능 비교 (CLI vs Desktop)

| Feature | CLI | Desktop |
|---------|-----|---------|
| Permission modes | `dontAsk` 포함 모든 모드 | Ask/Auto accept edits/Plan/Auto/Bypass(Settings) |
| Third-party providers | Bedrock, Vertex, Foundry | 기본 Anthropic API. Enterprise는 Vertex·gateway 구성 가능 |
| MCP servers | 설정 파일 | Connectors UI(로컬·SSH) 또는 설정 파일 |
| Plugins | `/plugin` 명령 | 플러그인 매니저 UI |
| @mention files | 텍스트 기반 | 자동완성, 로컬·SSH만 |
| File attachments | 없음 | 이미지, PDF |
| Session isolation | `--worktree` 플래그 | 자동 워크트리 |
| Multiple sessions | 별도 터미널 | 사이드바 탭 |
| Recurring tasks | Cron, CI 파이프라인 | 스케줄 작업 |
| Computer use | macOS에서 `/mcp`로 활성화 | macOS·Windows에서 앱·화면 제어 |
| Dispatch integration | 없음 | 사이드바 Dispatch 세션 |
| Scripting/automation | `--print`, Agent SDK | 없음 |

#### Desktop에 없는 것

다음은 CLI 또는 VS Code 확장에서만:
- **서드파티 프로바이더**: Desktop은 기본 Anthropic API. Enterprise는 Vertex·gateway만 managed settings로. Bedrock·Foundry는 CLI. → [[17 클라우드 프로바이더]]
- **Linux**: 데스크톱 앱은 macOS·Windows만. Linux는 CLI.
- **인라인 코드 제안**: Desktop은 autocomplete 스타일 제안 없음(대화·명시적 변경으로 동작).
- **Agent teams**: 서로 메시지하는 병렬 세션은 [[08 서브에이전트와 에이전트 팀]]의 CLI. 한 세션 내 멀티 에이전트는 동적 워크플로우(Desktop 동작).
- **터미널 다이얼로그 명령**: `/permissions`, `/config`, `/agents`, `/doctor` 등 터미널 인터랙티브 패널을 여는 명령은 Code 탭에서 `isn't available in this environment` 응답. 설정 파일 직접 편집 또는 독립 CLI 사용.

### 데스크톱 문제 해결

런타임 API 에러(`API Error: 500`, `529 Overloaded`, `429`, `Prompt is too long`)는 CLI·desktop·web 공통이며 [[25 트러블슈팅]]의 Error 레퍼런스 참고.

- **버전 확인**: macOS는 **Claude → About Claude**, Windows는 **Help → About**. 버전 번호 클릭으로 복사.
- **403/인증 에러**: ① 앱 메뉴에서 로그아웃·재로그인(가장 흔한 해결), ② 유료 구독(Pro/Max/Team/Enterprise) 확인, ③ CLI는 되는데 Desktop이 안 되면 앱을 완전 종료 후 재오픈·재로그인, ④ 인터넷·프록시 확인.
- **빈/멈춘 화면**: 재시작, 대기 중 업데이트 확인(실행 시 auto-update), Windows는 Event Viewer → Windows Logs → Application 크래시 로그.
- **"Failed to load session"**: 폴더 부재, Git LFS 미설치, 파일 권한 가능 — 다른 폴더 선택 또는 재시작.
- **설치 도구 못 찾음**(`npm`·`node` 등): 일반 터미널에서 동작 확인, 셸 프로필 PATH 설정 확인, 앱 재시작으로 env 재로드.
- **Git/Git LFS 에러**: Windows는 [Git for Windows](https://git-scm.com/downloads/win) 설치·재시작. "Git LFS is required..."면 [git-lfs.com](https://git-lfs.com/)에서 설치 후 `git lfs install`·재시작.
- **Windows MCP 미동작**: 설정 확인, 앱 재시작, Task Manager에서 서버 프로세스 확인, 서버 로그 검토.
- **앱 종료 안 됨**: macOS는 Cmd+Q, 안 되면 Cmd+Option+Esc Force Quit. Windows는 Ctrl+Shift+Esc Task Manager.
- **Windows 이슈**: 설치 후 PATH 미반영이면 새 터미널 열기. concurrent installation 에러면 관리자 권한으로 인스톨러 실행.
- **"Branch doesn't exist yet" (CLI 오픈 시)**: 원격 세션이 로컬에 없는 브랜치를 만들 수 있다. 세션 툴바 브랜치명 복사 후:
```bash
git fetch origin <branch-name>
git checkout <branch-name>
```
- **여전히 막히면**: [GitHub Issues](https://github.com/anthropics/claude-code/issues), [지원 센터](https://support.claude.com/). 버그 신고 시 앱 버전·OS·정확한 에러·로그(macOS는 Console.app, Windows는 Event Viewer) 포함.

---

## 플랫폼과 통합 (어디서 실행할지 고르기)

Claude Code는 모든 표면에서 동일 엔진을 돌리지만 각 표면은 다른 작업 방식에 맞춰져 있다. 설정·프로젝트 메모리·MCP 서버는 로컬 표면들 간에 공유되며, 같은 프로젝트에서 표면을 섞어 쓸 수 있다.

### 어디서 실행할까 (플랫폼 비교)

| Platform | 적합한 경우 | 제공 |
|----------|-------------|------|
| **CLI** | 터미널 워크플로우, 스크립팅, 원격 서버 | 전체 기능, Agent SDK, macOS computer use(Pro/Max), 서드파티 프로바이더 |
| **Desktop** | 시각적 검토, 병렬 세션, 관리형 셋업 | diff 뷰어, 앱 미리보기, computer use·Dispatch(Pro/Max) |
| **VS Code** | 터미널 전환 없이 VS Code 안에서 | 인라인 diff, 통합 터미널, 파일 컨텍스트 |
| **JetBrains** | IntelliJ/PyCharm/WebStorm 등 안에서 | diff 뷰어, 선택 공유, 터미널 세션 |
| **Web** | 많은 조정이 필요 없는 장기 작업, 오프라인에도 계속할 작업 | Anthropic 관리 클라우드, 연결 끊겨도 계속 |
| **Mobile** | 컴퓨터에서 떨어져 작업 시작·모니터링 | iOS/Android 앱의 클라우드 세션, 로컬 세션용 Remote Control, Desktop으로 Dispatch(Pro/Max) |

CLI가 터미널 네이티브 작업에 가장 완전(스크립팅·Agent SDK는 CLI 전용). 서드파티 프로바이더는 VS Code에서도 동작. Enterprise Desktop은 Vertex AI·gateway 지원; Bedrock/Foundry는 CLI나 VS Code. Web은 클라우드에서 돌아 연결 끊겨도 계속. Mobile은 그 클라우드 세션 또는 Remote Control로의 로컬 세션의 얇은 클라이언트이며, Dispatch로 Desktop에 작업 전송 가능. → [[15 웹과 모바일]], [[22 Agent SDK — 시작]]

### 도구 연결 (Integrations)

| Integration | 하는 일 | 용도 |
|-------------|---------|------|
| Chrome | 로그인된 세션으로 브라우저 제어 | 웹 앱 테스트, 폼 입력, API 없는 사이트 자동화 |
| GitHub Actions | CI 파이프라인에서 Claude 실행 | 자동 PR 리뷰, 이슈 트리아지, 스케줄 유지보수 |
| GitLab CI/CD | GitLab용 GitHub Actions 등가 | GitLab CI 자동화 |
| Code Review | 모든 PR 자동 리뷰 | 사람 리뷰 전 버그 포착 |
| Slack | 채널의 `@Claude` 멘션 응답 | 팀 챗의 버그 리포트를 PR로 |

목록에 없는 통합은 [[10 MCP]]·커넥터로 Linear, Notion, Google Drive, 내부 API 등 거의 무엇이든 연결. → [[21 브라우저와 컴퓨터 사용]], [[16 CI-CD와 팀 통합]]

### 터미널에서 떨어져 작업하기

|  | 트리거 | Claude 실행 위치 | 셋업 | 적합 |
|--|--------|-----------------|------|------|
| **Dispatch** | Claude 모바일 앱에서 작업 메시지 | 내 머신(Desktop) | 모바일 앱을 Desktop과 페어링 | 떨어져 있을 때 위임, 최소 셋업 |
| **Remote Control** | claude.ai/code나 모바일 앱에서 실행 중 세션 조종 | 내 머신(CLI/VS Code) | `claude remote-control` 실행 | 다른 기기에서 진행 중 작업 조종 |
| **Channels** | Telegram/Discord 등 챗 앱이나 자체 서버의 push 이벤트 | 내 머신(CLI) | channel 플러그인 설치/직접 구축 | CI 실패·챗 메시지 등 외부 이벤트 반응 |
| **Slack** | 팀 채널에서 `@Claude` 멘션 | Anthropic 클라우드 | Slack 앱 설치 + 웹 활성화 | 팀 챗의 PR·리뷰 |
| **Scheduled tasks** | 스케줄 설정 | CLI / Desktop / 클라우드 | 빈도 선택 | 일일 리뷰 등 반복 자동화 |

어디서 시작할지 모르겠으면 CLI를 설치해 프로젝트 디렉터리에서 실행하거나, 터미널 없이 쓰려면 Desktop. → [[13 자동화와 스케줄링]], [[15 웹과 모바일]]

---

## 원본 문서

- [vs-code](https://code.claude.com/docs/en/vs-code)
- [jetbrains](https://code.claude.com/docs/en/jetbrains)
- [desktop](https://code.claude.com/docs/en/desktop)
- [desktop-quickstart](https://code.claude.com/docs/en/desktop-quickstart)
- [platforms](https://code.claude.com/docs/en/platforms)
- [desktop-linux](https://code.claude.com/docs/en/desktop-linux)
- [desktop-wsl](https://code.claude.com/docs/en/desktop-wsl)
