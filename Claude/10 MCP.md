---
title: 10 MCP
updated: 2026-06-07
type: reference
sources: [mcp, mcp-quickstart, managed-mcp]
---

# 10 MCP

MCP(Model Context Protocol)는 Claude Code를 외부 도구·데이터 소스에 연결하는 오픈 소스 표준이다. MCP 서버는 Claude Code에 도구, 데이터베이스, API에 대한 접근을 제공한다. 이슈 트래커나 모니터링 대시보드에서 데이터를 채팅으로 복사·붙여넣기 하고 있다면, 서버를 연결해 Claude가 그 시스템을 직접 읽고 동작하도록 만드는 신호다.

이 노트는 세 페이지를 통합한다. 처음 연결한다면 "빠른 시작" 섹션의 단계별 흐름부터 따라가고, 전체 옵션은 "전체 레퍼런스" 섹션을, 조직 단위 통제는 "관리형 MCP 구성"을 참고하라. 허브: [[Claude]]. 관련: [[02 CLI 레퍼런스]](`claude mcp` 명령), [[04 설정]](settings.json `env`/`permissions`), [[05 권한]](도구 허용/거부), [[11 플러그인]](플러그인 번들 서버), [[18 보안과 샌드박스]](prompt injection 위협 모델), [[09 훅]](Elicitation 훅), [[19 비용과 성능]](컨텍스트 윈도 비용).

---

## MCP로 할 수 있는 일

서버를 연결하면 Claude Code에 다음과 같은 작업을 요청할 수 있다.

- **이슈 트래커 기능 구현**: "Add the feature described in JIRA issue ENG-4521 and create a PR on GitHub."
- **모니터링 데이터 분석**: "Check Sentry and Statsig to check the usage of the feature described in ENG-4521."
- **데이터베이스 질의**: "Find emails of 10 random users who used feature ENG-4521, based on our PostgreSQL database."
- **디자인 통합**: "Update our standard email template based on the new Figma designs that were posted in Slack."
- **워크플로우 자동화**: "Create Gmail drafts inviting these 10 users to a feedback session about the new feature."
- **외부 이벤트 반응**: MCP 서버는 *채널(channel)* 역할도 할 수 있어, Telegram/Discord/웹훅 이벤트를 세션으로 푸시해 Claude가 자리를 비운 동안에도 반응하게 한다.

### MCP 서버 찾기·만들기

- **Anthropic Directory**(`https://claude.ai/directory`)에서 검토된 커넥터를 탐색한다. Directory 커넥터는 Claude Code와 동일한 MCP 인프라를 쓰므로, 거기 등재된 원격 서버는 `claude mcp add`로 그대로 추가할 수 있다.
- 직접 서버를 만들려면 MCP 서버 가이드(`modelcontextprotocol.io/docs/develop/build-server`)와 Claude 커넥터 빌딩 문서를 참고한다.
- Claude에게 서버 스캐폴딩을 맡길 수도 있다(공식 `mcp-server-dev` 플러그인). [[11 플러그인]] 참고.

```
# 빌드 플러그인 설치 (마켓플레이스 미발견 시 먼저 추가)
/plugin marketplace add anthropics/claude-plugins-official
/plugin install mcp-server-dev@claude-plugins-official
/reload-plugins

# 빌드 스킬 실행 → remote HTTP 또는 local stdio 서버를 스캐폴딩
/mcp-server-dev:build-mcp-server
```

> [!warning] 신뢰
> 각 서버를 연결하기 전에 신뢰할 수 있는지 확인하라. 외부 콘텐츠를 가져오는 서버는 prompt injection 위험에 노출시킬 수 있다([[18 보안과 샌드박스]]).

---

## 빠른 시작 — 서버 한 개 연결하기

`mcp-quickstart` 페이지의 end-to-end 흐름이다. 모든 서버는 동일한 절차를 따른다: **추가 → 상태 확인 → 사용 → (선택)정리**.

### 시작 전 준비

- Claude Code가 설치·인증되어 있어야 한다([[01 시작하기]]).
- 프로젝트 디렉터리에서 터미널을 연다(빈 디렉터리도 가능).

### 단계별 (인증 불필요한 호스티드 서버 예시)

예시 서버는 Claude Code 문서 MCP 서버(전문 검색 제공, 인증 불필요)다.

```bash
# 1. 추가 — claude 세션 안이 아니라 터미널에서 실행
claude mcp add --transport http claude-code-docs https://code.claude.com/docs/mcp

# 2. 연결 상태 확인
claude mcp list

# 3. 세션 시작 후 서버를 이름으로 지목해 사용
claude
# (프롬프트 안에서)
#   Use the claude-code-docs server to look up what MCP_TIMEOUT does

# 4. (선택) 정리
claude mcp remove claude-code-docs
```

명령 각 부분 해설:
- `claude mcp add`: 서버를 Claude Code에 등록한다.
- `--transport http`: 로컬 프로세스가 아니라 URL에 호스팅된 서버.
- `claude-code-docs`: 직접 정하는 이름(라벨). Claude 출력의 도구 라벨과 `claude mcp remove` 같은 명령에서 이 이름을 쓴다.
- 마지막 인자는 서버 URL이다.

추가 시 `Added HTTP MCP server ... to local config`처럼 출력된다. `local config`는 *현재 프로젝트에 한해, 나에게만* 등록됐다는 뜻이다. 모든 프로젝트에서 쓰려면 user 스코프로 추가한다.

> [!note] 프롬프트에서 서버를 굳이 지목하지 않아도 Claude가 알아서 적절한 도구를 고른다. 빠른 시작에서 이름을 명시하는 이유는 데모가 web fetch 등 다른 도구가 아니라 새 서버를 거치도록 보장하기 위해서다. 첫 호출 시 도구 사용 권한을 묻는다 — 승인해야 진행된다.

### `claude mcp list` 상태 표시

| Status | 의미 |
|--------|------|
| `✓ Connected` | 사용 준비 완료 |
| `! Needs authentication` | 서버는 도달 가능하나 브라우저 사인인 또는 `--header` 토큰이 필요 |
| `✗ Failed to connect` | 서버가 응답하지 않음 (Troubleshooting 참고) |
| `✗ Connection error` | 연결 시도가 에러를 던짐 |
| `⏸ Pending approval` | 승인 대기 중인 project 스코프 서버 |

### 설정 파일 위치 (디스크상)

`claude mcp add`는 `--scope`에 따라 세 스코프 중 하나(파일 두 개)에 기록한다. 직접 편집할 필요는 없지만 디버깅·버전 관리에 유용하다.

| Scope | File | 사용 가능 범위 |
|-------|------|----------------|
| `local` | `~/.claude.json`, 이 프로젝트 엔트리 아래 | 나만, 이 프로젝트만 (기본값) |
| `project` | 프로젝트 루트의 `.mcp.json` | 프로젝트를 클론하는 모두 |
| `user` | `~/.claude.json`, 최상위 `mcpServers` 키 아래 | 나만, 모든 프로젝트 |

- Windows에서 `~/.claude.json`은 `%USERPROFILE%\.claude.json`(보통 `C:\Users\YourName\.claude.json`)으로 해석된다.
- `CLAUDE_CONFIG_DIR`를 설정했다면 그 디렉터리 안의 `.claude.json`을 읽는다([[04 설정]]).
- `claude mcp get <name>`으로 어느 스코프에 정의됐는지 확인한다.

### 스코프 변경

스코프는 추가 시점에 고정된다. 변경하려면 제거 후 새 스코프로 다시 추가한다.

```bash
# 기존 local 엔트리 제거 (정의를 하나로 정리)
claude mcp remove claude-code-docs --scope local

# 모든 프로젝트에서 쓰기 (user)
claude mcp add --scope user --transport http claude-code-docs https://code.claude.com/docs/mcp

# 팀과 공유 (project → .mcp.json에 기록, 버전관리에 커밋)
claude mcp add --scope project --transport http claude-code-docs https://code.claude.com/docs/mcp
```

`project` 스코프로 추가 후 `.mcp.json`을 커밋하면, 레포를 클론한 팀원은 승인 프롬프트를 거쳐 동일하게 연결된다.

### 다른 형태 서버 예시

**로컬 stdio 서버** (Claude Code가 서브프로세스로 시작). 브라우저·파일시스템·DB 소켓 등 로컬 자원 접근에 적합. Playwright 서버 예시(Node.js 18+ 필요):

```bash
claude mcp add playwright -- npx -y @playwright/mcp@latest
# 확인: npx 패키지 다운로드 중에는 잠깐 Failed to connect로 보일 수 있으니 다시 확인
claude mcp list
# 사용:  Use playwright to open https://example.com and tell me the page title
```

- 호스티드 예시와 차이: `--transport` 플래그 없음(로컬은 기본 `stdio`), `--` 뒤가 서버 실행 명령, `-y`는 npx 프롬프트 없이 설치.
- 다른 브라우저는 `@playwright/mcp@latest` 뒤에 `--browser firefox` 같은 식으로 추가.

**사인인이 필요한 서버**(OAuth, 예: Sentry/Linear/Notion):

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
# list에서는 ! Needs authentication 으로 표시됨
# 세션 안에서 /mcp → sentry 선택 → Enter → Authenticate → 브라우저 사인인
```

정적 토큰을 쓰는 서버는 추가 시점에 `--header "Authorization: Bearer <token>"`로 토큰을 넘긴다(아래 GitHub 예시).

### 다른 표면(surface)에서 연결

| 표면 | 방법 |
|------|------|
| Claude Code 데스크톱 앱 | Connectors UI ([[14 IDE와 데스크톱]]) |
| Claude Desktop 채팅 앱 | 별도 앱. macOS/WSL에서 `claude mcp add-from-claude-desktop`로 `claude_desktop_config.json` 복사 |
| VS Code | "Connect to external tools with MCP" ([[14 IDE와 데스크톱]]) |
| Claude Code on the web | 레포의 `.mcp.json`을 읽음 ([[15 웹과 모바일]]) |
| Claude.ai | `claude.ai/customize/connectors`에 추가한 커넥터가 동일 계정 로그인 시 CLI에서 자동 로드 |

---

## 전체 레퍼런스 — 설치 방식 (transport별)

`mcp` 페이지의 정식 레퍼런스. 서버는 여러 방식으로 구성한다.

### Option 1: 원격 HTTP 서버 (권장)

클라우드 서비스에 가장 널리 지원되는 transport.

```bash
# 기본 문법
claude mcp add --transport http <name> <url>

# 예: Notion
claude mcp add --transport http notion https://mcp.notion.com/mcp

# Bearer 토큰 예
claude mcp add --transport http secure-api https://api.example.com/mcp \
  --header "Authorization: Bearer your-token"
```

JSON(`.mcp.json`, `~/.claude.json`, `claude mcp add-json`) 구성 시 `type` 필드는 `streamable-http`를 `http`의 별칭으로 받는다. MCP 명세가 이 transport를 `streamable-http`로 부르므로, 서버 문서에서 복사한 구성을 수정 없이 쓸 수 있다.

### Option 2: 원격 SSE 서버 (deprecated)

> [!warning] SSE(Server-Sent Events) transport는 deprecated다. 가능하면 HTTP를 써라.

```bash
claude mcp add --transport sse <name> <url>
claude mcp add --transport sse asana https://mcp.asana.com/sse
claude mcp add --transport sse private-api https://api.company.com/sse \
  --header "X-API-Key: your-key-here"
```

### Option 3: 로컬 stdio 서버

로컬 프로세스로 실행. 시스템 직접 접근·커스텀 스크립트에 이상적.

```bash
# 기본 문법
claude mcp add [options] <name> -- <command> [args...]

# 예: Airtable 서버
claude mcp add --env AIRTABLE_API_KEY=YOUR_KEY --transport stdio airtable \
  -- npx -y airtable-mcp-server
```

- Claude Code는 spawn한 서버 환경에 `CLAUDE_PROJECT_DIR`(프로젝트 루트)를 설정한다. 서버 안에서 `process.env.CLAUDE_PROJECT_DIR`(Node) / `os.environ["CLAUDE_PROJECT_DIR"]`(Python)로 읽거나, MCP `roots/list` 요청으로 Claude Code 실행 디렉터리를 얻을 수 있다. 이 변수는 *서버 환경*에만 설정되므로, project/user 스코프 `.mcp.json`의 `command`/`args`에서 `${VAR}` 확장으로 참조하려면 `${CLAUDE_PROJECT_DIR:-.}` 같은 기본값이 필요하다. (플러그인 제공 구성은 `${CLAUDE_PROJECT_DIR}`를 직접 치환하므로 기본값 불필요.)

> [!important] stdio 서버 인자는 `--`로 구분
> `--`(이중 대시)는 Claude 자신의 옵션(`--transport`, `--env`, `--scope`)과 서버를 실행하는 명령·인자를 분리한다. `--` 뒤는 그대로 서버에 전달된다.
> - `claude mcp add --transport stdio myserver -- npx server` → `npx server` 실행
> - `claude mcp add --env KEY=value --transport stdio myserver -- python server.py --port 8080` → 환경에 `KEY=value`를 둔 채 `python server.py --port 8080` 실행
> `--`가 없으면 Claude Code가 서버의 `--port` 같은 플래그를 자기 옵션으로 파싱하려 한다.
> `--env`는 여러 `KEY=value`를 받는다. 서버 이름이 `--env` 바로 뒤에 오면 CLI가 이름을 또 다른 쌍으로 읽어 거부하므로, `--env`와 서버 이름 사이에 다른 옵션을 최소 하나 둬라.

### Option 4: 원격 WebSocket 서버

영속적 양방향 연결을 유지하므로, Claude에 프롬프트 없이 이벤트를 푸시하는 원격 서버에 적합. 서버가 요청에만 응답한다면 HTTP를 써라(HTTP는 OAuth와 `--transport` 플래그를 지원, WebSocket은 둘 다 미지원).

```bash
claude mcp add-json events-server \
  '{"type":"ws","url":"wss://mcp.example.com/socket","headers":{"Authorization":"Bearer YOUR_TOKEN"}}'
```

`type: "ws"` 엔트리는 `http`와 동일한 `url`, `headers`, `headersHelper`, `timeout`, `alwaysLoad` 필드를 받는다. 인증은 헤더 전용 — 정적 토큰을 `headers`에 넣거나 `headersHelper`로 연결 시점에 생성한다. `claude mcp add --transport` 플래그는 `ws`를 받지 않는다.

---

## 서버 관리

```bash
# 모든 서버 나열
claude mcp list
# 특정 서버 상세
claude mcp get github
# 서버 제거
claude mcp remove github
# (Claude Code 안에서) 서버 상태 확인
/mcp
```

- `.mcp.json`의 승인 대기 project 서버는 `claude mcp list`에서 `⏸ Pending approval`로 보인다. `claude`를 대화형으로 실행해 검토·승인한다. `claude mcp get <name>`은 대기 서버를 `⏸ Pending approval`, 거부된 서버를 `✗ Rejected`로 표시한다.
- `/mcp` 패널은 연결된 서버 옆에 도구 개수를 보여주고, tools 능력을 광고하지만 노출 도구가 없는 서버를 표시한다.
- 요청에 아직 백그라운드 연결 중인 서버 도구가 필요하면, Claude는 그 서버를 기다린다. tool search 활성(기본) 시 대기는 `ToolSearch` 호출 안에서 일어난다. tool search 없는 구성(Vertex AI, 커스텀 `ANTHROPIC_BASE_URL`, `ENABLE_TOOL_SEARCH=false`)에서는 `WaitForMcpServers` 도구를 쓴다.
- 서버 이름 `workspace`는 내부 예약어다. 같은 이름의 서버를 정의하면 로드 시 건너뛰고 rename을 요청하는 경고를 띄운다.

### 동적 도구 업데이트 / 자동 재연결

- **`list_changed` 알림**: MCP 서버가 도구·프롬프트·리소스를 동적으로 갱신하면 Claude Code가 재연결 없이 자동으로 능력을 새로고침한다.
- **자동 재연결**: HTTP/SSE 서버가 세션 중 끊기면 exponential backoff로 자동 재연결한다(최대 5회, 1초 시작·매번 2배). 진행 중에는 `/mcp`에서 pending으로 보이고, 5회 실패 후 failed로 표시되며 `/mcp`에서 수동 재시도 가능. **stdio 서버는 로컬 프로세스라 자동 재연결되지 않는다.** 시작 시 초기 연결 실패에도 동일 backoff 적용 — v2.1.121부터 5xx·connection refused·timeout 같은 일시 오류는 최대 3회 재시도하고, 인증/not-found 오류는 구성 변경이 필요하므로 재시도하지 않는다.

### 채널로 메시지 푸시

MCP 서버는 CI 결과, 모니터링 알림, 채팅 메시지 등 외부 이벤트를 세션으로 직접 푸시할 수 있다. 서버가 `claude/channel` 능력을 선언하고, 시작 시 `--channels` 플래그로 opt-in 한다. ([[13 자동화와 스케줄링]] 연관)

### 타임아웃·출력·환경변수 팁

> [!tip] 주요 환경변수·플래그
> - `--scope` 저장 위치: `local`(기본, 현 프로젝트·나만; 구버전 `project`), `project`(`.mcp.json`로 팀 공유), `user`(모든 프로젝트·나만; 구버전 `global`)
> - `--env KEY=value`로 환경변수 설정
> - `MCP_TIMEOUT`: 서버 *시작* 타임아웃 (예: `MCP_TIMEOUT=10000 claude` → 10초)
> - 서버별 도구 실행 타임아웃: `.mcp.json` 엔트리에 `"timeout"`(ms, 예 `"timeout": 600000` = 10분). 그 서버에 한해 `MCP_TOOL_TIMEOUT`을 덮어씀
> - `MAX_MCP_OUTPUT_TOKENS`: 출력 토큰 한도 (기본 25,000, 10,000 초과 시 경고)
> - `/mcp`로 OAuth 2.0 인증 수행

- 서버별 `timeout`은 도구 호출당 하드 벽시계 한도이며 서버의 진행 알림으로 연장되지 않는다. 1000 미만 값은 무시되어 `MCP_TOOL_TIMEOUT`(미설정 시 약 28시간 기본값)으로 폴스루한다(v2.1.162 이전에는 1초로 내림). HTTP/SSE는 요청당 첫 바이트 budget에 60초 최소값이 있다.

---

## 플러그인 제공 MCP 서버

[[11 플러그인]]은 MCP 서버를 번들로 묶어, 플러그인이 켜질 때 도구·통합을 자동 제공한다. 플러그인 MCP 서버는 사용자 구성 서버와 동일하게 동작한다.

- 플러그인은 플러그인 루트의 `.mcp.json` 또는 `plugin.json` 인라인으로 MCP 서버를 정의한다.
- 플러그인이 켜지면 그 MCP 서버가 자동 시작된다. 세션 중 enable/disable 하면 `/reload-plugins`로 연결/해제한다.
- 플러그인 도구는 수동 구성 MCP 도구와 나란히 나타난다. 플러그인 서버는 플러그인 설치로 관리되며 `/mcp` 명령으로 관리하지 않는다.

플러그인 루트 `.mcp.json` 예:

```json
{
  "mcpServers": {
    "database-tools": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": { "DB_URL": "${DB_URL}" }
    }
  }
}
```

`plugin.json` 인라인 예:

```json
{
  "name": "my-plugin",
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--port", "8080"]
    }
  }
}
```

환경변수: `${CLAUDE_PLUGIN_ROOT}`(번들 파일), `${CLAUDE_PLUGIN_DATA}`(플러그인 업데이트를 견디는 영속 상태), `${CLAUDE_PROJECT_DIR}`(안정적 프로젝트 루트). stdio/SSE/HTTP/WebSocket 모두 지원(서버별로 다를 수 있음). 플러그인 서버는 `/mcp` 목록에 플러그인 출처 표시와 함께 나타난다.

---

## MCP 설치 스코프

서버는 세 스코프로 구성된다. 스코프는 서버가 어느 프로젝트에 로드되는지와 팀 공유 여부를 통제한다. 관리자는 enterprise 레벨(managed configuration)로도 배포할 수 있다.

| Scope | Loads in | 팀 공유 | 저장 위치 |
|-------|----------|---------|-----------|
| Local | 현재 프로젝트만 | 아니오 | `~/.claude.json` |
| Project | 현재 프로젝트만 | 예, 버전관리로 | 프로젝트 루트 `.mcp.json` |
| User | 모든 프로젝트 | 아니오 | `~/.claude.json` |

> [!note] MCP "local scope" 용어는 일반 local 설정과 다르다. MCP local 스코프 서버는 `~/.claude.json`(홈)에 저장되고, 일반 local 설정은 `.claude/settings.local.json`(프로젝트)을 쓴다. [[04 설정]] 참고.

### Local 스코프 (기본)

추가한 프로젝트에서만 로드되고 나에게만 비공개. 개인 개발 서버, 실험 구성, 버전관리에 넣고 싶지 않은 자격증명에 적합.

```bash
claude mcp add --transport http stripe https://mcp.stripe.com
claude mcp add --transport http stripe --scope local https://mcp.stripe.com  # 명시
```

`/path/to/your/project`에서 실행한 결과(`~/.claude.json`):

```json
{
  "projects": {
    "/path/to/your/project": {
      "mcpServers": {
        "stripe": { "type": "http", "url": "https://mcp.stripe.com" }
      }
    }
  }
}
```

### Project 스코프

`.mcp.json`을 프로젝트 루트에 저장해 팀 협업을 가능케 한다. 버전관리에 체크인하도록 설계됨.

```bash
claude mcp add --transport http paypal --scope project https://mcp.paypal.com/mcp
```

```json
{
  "mcpServers": {
    "shared-server": { "command": "/path/to/server", "args": [], "env": {} }
  }
}
```

보안상 `.mcp.json` 서버 사용 전 승인을 요구한다. 승인 선택을 초기화하려면 `claude mcp reset-project-choices`.

### User 스코프

`~/.claude.json`에 저장, 모든 프로젝트에서 사용 가능하되 내 계정 비공개. 개인 유틸리티·개발 도구에 적합.

```bash
claude mcp add --transport http hubspot --scope user https://mcp.hubspot.com/anthropic
```

### 스코프 계층과 우선순위

같은 서버가 여러 곳에 정의되면 Claude Code는 한 번만 연결하고, 최상위 우선순위 소스의 정의를 쓴다. 필드는 스코프 간 병합되지 않고 그 소스의 엔트리 전체를 쓴다.

1. Local
2. Project
3. User
4. 플러그인 제공 서버
5. claude.ai 커넥터

세 스코프는 *이름*으로 중복을 판단한다. 플러그인·커넥터는 *엔드포인트*(같은 URL/command)로 중복을 판단한다.

### `.mcp.json` 환경변수 확장

기계별 경로·민감 값을 분리하면서 구성을 공유할 수 있다.

- `${VAR}` — 환경변수 `VAR` 값으로 확장
- `${VAR:-default}` — `VAR`가 있으면 그 값, 없으면 `default`

확장 위치: `command`, `args`, `env`, `url`(HTTP), `headers`(HTTP 인증).

```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": { "Authorization": "Bearer ${API_KEY}" }
    }
  }
}
```

필수 환경변수가 미설정이고 기본값도 없으면 구성 파싱에 실패한다.

---

## 실전 예시

### Sentry로 에러 모니터링

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
# /mcp 로 Sentry 계정 인증 후:
#   What are the most common errors in the last 24 hours?
#   Show me the stack trace for error ID abc123
#   Which deployment introduced these new errors?
```

### GitHub로 코드 리뷰

GitHub 원격 MCP는 personal access token을 헤더로 인증한다. fine-grained 토큰을 발급한 뒤:

```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/ \
  --header "Authorization: Bearer YOUR_GITHUB_PAT"
#   Review PR #456 and suggest improvements
#   Create a new issue for the bug we just found
#   Show me all open PRs assigned to me
```

### PostgreSQL 데이터베이스 질의

```bash
claude mcp add --transport stdio db -- npx -y @bytebase/dbhub \
  --dsn "postgresql://readonly:<YOUR_PASSWORD>@prod.db.com:5432/analytics"
#   What's our total revenue this month?
#   Show me the schema for the orders table
#   Find customers who haven't made a purchase in 90 days
```

---

## 원격 서버 인증 (OAuth 2.0)

많은 클라우드 MCP 서버가 인증을 요구한다. Claude Code는 보안 연결에 OAuth 2.0을 지원한다.

- 서버가 `401 Unauthorized` 또는 `403 Forbidden`을 응답하면 인증 필요로 표시되어 `/mcp`에서 OAuth 플로우를 완료할 수 있다. `WWW-Authenticate` 헤더로 인증 서버를 가리키는 커스텀 서버도 동일한 자동 발견을 받는다.
- `headers.Authorization`을 설정했는데 서버가 그 헤더를 거부하면 OAuth로 폴백하지 않고 연결 실패로 보고한다. 토큰 유효성을 확인하거나 헤더를 제거해 OAuth를 쓰라.

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
# 세션 안에서:  /mcp  → 브라우저 로그인
```

> [!tip] 인증 팁
> - 토큰은 안전하게 저장·자동 갱신된다. `/mcp` 메뉴 "Clear authentication"으로 취소
> - 브라우저가 자동으로 안 열리면 제공된 URL을 직접 연다
> - 인증 후 리다이렉트가 연결 오류로 실패하면, 브라우저 주소창의 전체 callback URL을 Claude Code의 URL 프롬프트에 붙여넣는다
> - OAuth는 HTTP 서버에서 동작

### 고정 OAuth callback 포트

일부 서버는 미리 등록된 redirect URI를 요구한다. 기본은 랜덤 포트지만 `--callback-port`로 `http://localhost:PORT/callback` 형식에 맞춰 고정한다.

```bash
claude mcp add --transport http \
  --callback-port 8080 \
  my-server https://mcp.example.com/mcp
```

`--callback-port`는 단독(dynamic client registration) 또는 `--client-id`와 함께(pre-configured credentials) 쓸 수 있다.

### 사전 구성 OAuth 자격증명

Dynamic Client Registration을 지원하지 않는 서버(에러: "Incompatible auth server: does not support dynamic client registration")는 사전 구성 자격증명이 필요하다. Claude Code는 CIMD(Client ID Metadata Document)도 자동 발견한다. 자동 발견 실패 시 서버 개발자 포털에서 OAuth 앱을 등록해 client ID/secret을 받는다.

```bash
# claude mcp add — --client-secret은 마스킹 입력으로 프롬프트
claude mcp add --transport http \
  --client-id your-client-id --client-secret --callback-port 8080 \
  my-server https://mcp.example.com/mcp

# claude mcp add-json — oauth 객체 포함
claude mcp add-json my-server \
  '{"type":"http","url":"https://mcp.example.com/mcp","oauth":{"clientId":"your-client-id","callbackPort":8080}}' \
  --client-secret

# add-json (callback 포트만, dynamic registration)
claude mcp add-json my-server \
  '{"type":"http","url":"https://mcp.example.com/mcp","oauth":{"callbackPort":8080}}'

# CI / 환경변수로 secret 전달 (인터랙티브 프롬프트 생략)
MCP_CLIENT_SECRET=your-secret claude mcp add --transport http \
  --client-id your-client-id --client-secret --callback-port 8080 \
  my-server https://mcp.example.com/mcp
```

> [!tip]
> - client secret은 시스템 keychain(macOS) 또는 자격증명 파일에 안전 저장 — config에 안 들어감
> - secret 없는 public OAuth client는 `--client-id`만 사용
> - 이 플래그들은 HTTP/SSE에만 적용, stdio엔 무효
> - `claude mcp get <name>`으로 OAuth 자격증명 구성 여부 확인

### OAuth 메타데이터 발견 재정의

기본 발견 체인을 우회해 특정 인증 서버 메타데이터 URL을 가리킨다. 표준 엔드포인트가 에러를 내거나 내부 프록시로 라우팅할 때 `authServerMetadataUrl`을 설정한다. 기본 발견 순서: RFC 9728 `/.well-known/oauth-protected-resource` → RFC 8414 `/.well-known/oauth-authorization-server`.

```json
{
  "mcpServers": {
    "my-server": {
      "type": "http",
      "url": "https://mcp.example.com/mcp",
      "oauth": {
        "authServerMetadataUrl": "https://auth.example.com/.well-known/openid-configuration"
      }
    }
  }
}
```

URL은 `https://` 필수. `authServerMetadataUrl`은 v2.1.64+ 필요. 메타데이터의 `scopes_supported`가 업스트림 광고 scope를 덮어쓴다.

### OAuth scope 제한

`oauth.scopes`로 인증 플로우에서 요청할 scope를 고정한다. 업스트림이 원하는 것보다 많은 scope를 광고할 때 보안팀 승인 부분집합으로 제한하는 지원 방식. 값은 RFC 6749 §3.3의 `scope` 형식과 같은 공백 구분 단일 문자열.

```json
{
  "mcpServers": {
    "slack": {
      "type": "http",
      "url": "https://mcp.slack.com/mcp",
      "oauth": { "scopes": "channels:read chat:write search:read" }
    }
  }
}
```

- `oauth.scopes`는 `authServerMetadataUrl`과 `/.well-known` 발견 scope 모두에 우선. 미설정 시 서버가 scope를 결정.
- 인증 서버가 `scopes_supported`에 `offline_access`를 광고하면, 새 브라우저 사인인 없이 토큰 갱신이 가능하도록 고정 scope에 덧붙인다.
- 도구 호출에서 403 `insufficient_scope`가 나오면 같은 고정 scope로 재인증한다. 필요 도구가 핀 밖 scope를 요구하면 `oauth.scopes`를 넓혀라.

### 커스텀 인증 — 동적 헤더 (`headersHelper`)

OAuth가 아닌 인증(Kerberos, 단기 토큰, 내부 SSO)에는 `headersHelper`로 연결 시점에 헤더를 생성한다. Claude Code가 명령을 실행해 출력을 연결 헤더에 병합한다.

```json
{
  "mcpServers": {
    "internal-api": {
      "type": "http",
      "url": "https://mcp.internal.example.com",
      "headersHelper": "/opt/bin/get-mcp-auth-headers.sh"
    }
  }
}
```

인라인 명령도 가능:

```json
{
  "mcpServers": {
    "internal-api": {
      "type": "http",
      "url": "https://mcp.internal.example.com",
      "headersHelper": "echo '{\"Authorization\": \"Bearer '\"$(get-token)\"'\"}'"
    }
  }
}
```

**요구사항**: 명령은 문자열 key-value JSON 객체를 stdout에 써야 한다. 셸에서 10초 타임아웃으로 실행. 동적 헤더는 같은 이름의 정적 `headers`를 덮어쓴다. helper는 매 연결(세션 시작·재연결)마다 새로 실행되며 캐싱이 없으니 토큰 재사용은 스크립트 책임이다.

helper 실행 시 설정되는 환경변수:

| Variable | Value |
|----------|-------|
| `CLAUDE_CODE_MCP_SERVER_NAME` | MCP 서버 이름 |
| `CLAUDE_CODE_MCP_SERVER_URL` | MCP 서버 URL |

> [!note] `headersHelper`는 임의 셸 명령을 실행한다. project/local 스코프에 정의되면 workspace 신뢰 다이얼로그 수락 후에만 실행된다.

---

## JSON 구성으로 서버 추가

```bash
# 기본 문법
claude mcp add-json <name> '<json>'

# HTTP 서버
claude mcp add-json weather-api '{"type":"http","url":"https://api.weather.com/mcp","headers":{"Authorization":"Bearer token"}}'

# stdio 서버
claude mcp add-json local-weather '{"type":"stdio","command":"/path/to/weather-cli","args":["--api-key","abc123"],"env":{"CACHE_DIR":"/tmp"}}'

# 사전 구성 OAuth 자격증명 HTTP 서버
claude mcp add-json my-server '{"type":"http","url":"https://mcp.example.com/mcp","oauth":{"clientId":"your-client-id","callbackPort":8080}}' --client-secret

# 확인
claude mcp get weather-api
```

JSON은 셸에서 제대로 이스케이프하고 MCP 서버 구성 스키마를 따라야 한다. `--scope user`로 user 구성에 추가 가능.

## Claude Desktop에서 서버 가져오기

```bash
claude mcp add-from-claude-desktop   # 인터랙티브 선택 다이얼로그
claude mcp list                      # 확인
```

macOS·WSL에서만 동작하며 표준 위치의 Claude Desktop 구성 파일을 읽는다. `--scope user` 지원. 이름이 겹치면 숫자 접미사(`server_1`)가 붙는다.

## Claude.ai 커넥터 사용

Claude.ai 계정으로 Claude Code에 로그인했다면, Claude.ai에 추가한 MCP 서버가 자동으로 사용 가능하다.

- `claude.ai/customize/connectors`에서 서버 추가(Team/Enterprise는 admin만). 인증 완료 후 Claude Code `/mcp` 목록에 Claude.ai 출처 표시와 함께 나타난다.
- v2.1.161부터 한 번도 사인인하지 않은 커넥터는 섹션 끝의 `Show unused connectors` 행 뒤로 접힌다. 이전에 사인인한 커넥터는 재인증이 필요해도 계속 보인다.
- Claude.ai 커넥터는 활성 [[05 권한]] 아닌 *인증 방식*이 Claude.ai 구독일 때만 가져온다. `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `apiKeyHelper`, Bedrock/Vertex 등이 활성이면(이전에 `/login` 했더라도) 로드되지 않는다. `/status`로 활성 인증 방식을 확인하고, 해당 변수를 unset 하거나 `apiKeyHelper`를 제거한 뒤 `/login`으로 Claude.ai 계정을 선택하라.
- Claude Code에 추가한 서버가 같은 URL의 claude.ai 커넥터보다 우선한다. 이 경우 `/mcp`는 커넥터를 hidden으로 표시한다.
- Microsoft 365, Gmail, Google Calendar 등 일부 Anthropic 호스티드 커넥터는 로컬 OAuth를 지원하지 않는다(업스트림 IdP가 claude.ai 등록 redirect URL만 수락). v2.1.162부터 `/mcp`에서 이들 인증 시 claude.ai의 Settings → Connectors에서 연결하라는 안내가 뜬다.

```bash
# Claude Code에서 claude.ai MCP 서버 비활성화
ENABLE_CLAUDEAI_MCP_SERVERS=false claude
```

## Claude Code를 MCP 서버로 사용

Claude Code 자체를 다른 앱이 연결하는 MCP 서버로 쓸 수 있다.

```bash
claude mcp serve   # stdio MCP 서버로 시작
```

Claude Desktop의 `claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "claude-code": {
      "type": "stdio",
      "command": "claude",
      "args": ["mcp", "serve"],
      "env": {}
    }
  }
}
```

> [!warning] 실행 경로
> `command`는 Claude Code 실행 파일을 가리켜야 한다. PATH에 없으면 `which claude`로 전체 경로를 찾아 `"command": "/full/path/to/claude"`로 지정. 잘못된 경로면 `spawn claude ENOENT` 에러가 난다.

이 서버는 Claude Code의 View, Edit, LS 등 도구를 노출한다([[06 내장 도구 레퍼런스]]). 개별 도구 호출의 사용자 확인 구현은 *연결한 클라이언트* 책임이다.

---

## MCP 출력 한도와 경고

큰 출력의 토큰 사용을 관리해 대화 컨텍스트가 압도되지 않게 한다.

- **경고 임계값**: 어떤 MCP 도구 출력이 10,000 토큰을 초과하면 경고 표시
- **조정 가능 한도**: `MAX_MCP_OUTPUT_TOKENS` 환경변수로 최대치 조정
- **기본 한도**: 25,000 토큰
- **적용 범위**: 환경변수는 자체 한도를 선언하지 않은 도구에 적용. `anthropic/maxResultSizeChars`를 설정한 도구는 텍스트 콘텐츠에 그 값을 쓴다(`MAX_MCP_OUTPUT_TOKENS`와 무관). 이미지 데이터 반환 도구는 여전히 `MAX_MCP_OUTPUT_TOKENS` 적용.

```bash
export MAX_MCP_OUTPUT_TOKENS=50000
claude
```

대용량 데이터셋·DB 질의, 상세 리포트 생성, 방대한 로그 처리 서버에 특히 유용하다. [[19 비용과 성능]] 연관.

### 특정 도구 한도 올리기 (서버 작성자용)

MCP 서버를 만든다면, 개별 도구가 기본 디스크 영속 임계값보다 큰 결과를 반환하도록 `tools/list` 응답 엔트리의 `_meta["anthropic/maxResultSizeChars"]`를 설정할 수 있다. Claude Code가 그 도구 임계값을 주석 값까지(하드 상한 500,000자) 올린다.

```json
{
  "name": "get_schema",
  "description": "Returns the full database schema",
  "_meta": { "anthropic/maxResultSizeChars": 200000 }
}
```

DB 스키마, 전체 파일 트리처럼 본질적으로 크지만 필요한 출력에 유용하다. 주석 없이 기본 임계값을 넘는 결과는 디스크에 영속되고 대화엔 파일 참조로 대체된다. 텍스트 콘텐츠에는 `MAX_MCP_OUTPUT_TOKENS`와 독립적으로 적용되지만, 이미지 반환 도구엔 효과가 없어 환경변수 상향만이 유일한 방법이다.

---

## MCP elicitation 응답

MCP 서버는 작업 중 구조화된 입력을 요청할 수 있다(elicitation). 서버가 스스로 얻을 수 없는 정보가 필요하면 Claude Code가 인터랙티브 다이얼로그를 띄우고 응답을 서버에 전달한다. 사용자 측 구성은 불필요 — 서버 요청 시 자동으로 나타난다.

- **Form mode**: 서버가 정의한 폼 필드(예: username/password) 다이얼로그를 채워 제출
- **URL mode**: 인증·승인용 브라우저 URL을 열고 완료 후 CLI에서 확인

다이얼로그 없이 자동 응답하려면 [[09 훅]]의 `Elicitation` 훅을 쓴다.

## MCP 리소스 사용 (@ 멘션)

MCP 서버는 파일처럼 @ 멘션으로 참조하는 리소스를 노출할 수 있다.

```text
# 프롬프트에 @ 입력 → 연결된 모든 서버의 리소스가 자동완성에 표시
Can you analyze @github:issue://123 and suggest a fix?
Please review the API documentation at @docs:file://api/authentication
# 여러 리소스 동시 참조
Compare @postgres:schema://users with @docs:file://database/user-model
```

형식은 `@server:protocol://resource/path`. 리소스는 참조 시 자동으로 fetch되어 attachment로 포함된다. 경로는 @ 멘션 자동완성에서 fuzzy 검색된다. 서버가 지원하면 Claude Code가 리소스 나열·읽기 도구를 자동 제공한다. 텍스트, JSON, 구조화 데이터 등 모든 콘텐츠 타입을 담을 수 있다.

## MCP 프롬프트를 명령으로 사용

MCP 서버는 Claude Code에서 명령으로 쓰이는 프롬프트를 노출할 수 있다.

```text
# / 입력 → MCP 프롬프트가 /mcp__servername__promptname 형식으로 표시
/mcp__github__list_prs
# 인자는 명령 뒤에 공백 구분
/mcp__github__pr_review 456
/mcp__jira__create_issue "Bug in login flow" high
```

프롬프트는 연결된 서버에서 동적 발견되고, 인자는 정의된 파라미터로 파싱되며, 결과는 대화에 직접 주입된다. 서버·프롬프트 이름은 정규화된다(공백 → 언더스코어).

---

## MCP Tool Search로 스케일링

Tool search는 도구 정의를 Claude가 필요로 할 때까지 미뤄 MCP 컨텍스트 사용을 낮게 유지한다. 세션 시작 시 도구 이름과 서버 지시문만 로드되므로, MCP 서버를 더 추가해도 컨텍스트 윈도 영향이 최소다.

### 동작 방식

기본 활성. MCP 도구는 미리 로드되지 않고 deferred 되며, Claude가 작업에 필요할 때 search 도구로 발견한다. 실제 사용하는 도구만 컨텍스트에 들어간다. 사용자 입장에선 이전과 동일하게 동작한다. 임계값 기반 로딩을 원하면 `ENABLE_TOOL_SEARCH=auto`로 컨텍스트의 10% 안에 맞는 스키마는 미리 로드하고 초과분만 미룬다.

### 서버 작성자용

Tool Search가 켜지면 *server instructions* 필드가 더 유용하다([[07 스킬]]과 유사하게 Claude가 언제 도구를 검색할지 이해하도록 돕는다). 도구 카테고리, 검색해야 할 시점, 핵심 능력을 명확히 적어라. Claude Code는 도구 설명과 server instructions를 각 2KB에서 truncate 하니 간결하게, 핵심을 앞에 둬라.

### 구성 — `ENABLE_TOOL_SEARCH`

기본 활성이나 Vertex AI에서는 기본 비활성, `ANTHROPIC_BASE_URL`이 non-first-party 호스트면 비활성(대부분의 프록시가 `tool_reference` 블록을 전달 안 함). 폴백을 덮으려면 명시적으로 설정. `tool_reference` 지원 모델 필요: Sonnet 4+ 또는 Opus 4+(Haiku 미지원; Vertex AI는 Sonnet 4.5+/Opus 4.5+).

| Value | Behavior |
|-------|----------|
| (unset) | 모든 MCP 도구 deferred·온디맨드 로드. Vertex AI나 non-first-party `ANTHROPIC_BASE_URL`에서는 upfront 로딩으로 폴백 |
| `true` | 모든 도구 deferred. Vertex AI·프록시에서도 beta 헤더 전송. Vertex Sonnet 4.5/Opus 4.5 미만 모델이나 `tool_reference` 미지원 프록시에서는 요청 실패 |
| `auto` | 임계값 모드: 컨텍스트의 10% 안에 맞으면 upfront, 아니면 deferred |
| `auto:N` | 커스텀 퍼센트 임계값 모드 (N=0~100, 예 `auto:5`) |
| `false` | 모든 도구 upfront 로드, deferral 없음 |

```bash
ENABLE_TOOL_SEARCH=auto:5 claude   # 커스텀 5% 임계값
ENABLE_TOOL_SEARCH=false claude    # tool search 완전 비활성
```

settings.json의 `env` 필드에도 설정 가능([[04 설정]]). `ToolSearch` 도구만 비활성화하려면([[05 권한]]):

```json
{ "permissions": { "deny": ["ToolSearch"] } }
```

### 특정 서버 deferral 제외 (`alwaysLoad`)

서버 도구가 검색 단계 없이 항상 보여야 하면 `alwaysLoad: true`를 설정한다. 그 서버의 모든 도구가 `ENABLE_TOOL_SEARCH` 설정과 무관하게 세션 시작 시 컨텍스트에 로드된다. 매 턴 필요한 소수 도구에만 쓰라(upfront 도구는 대화에 쓸 컨텍스트를 잠식).

```json
{
  "mcpServers": {
    "core-tools": {
      "type": "http",
      "url": "https://mcp.example.com/mcp",
      "alwaysLoad": true
    }
  }
}
```

`alwaysLoad`는 모든 서버 타입에서 가능, v2.1.121+ 필요. 서버가 도구 `_meta`에 `"anthropic/alwaysLoad": true`를 넣어 개별 도구만 always-loaded로 표시할 수도 있다. `alwaysLoad: true`는 서버 연결까지 시작을 차단한다(표준 5초 connect 타임아웃 상한). 첫 프롬프트 구성 시 도구가 있어야 하므로, MCP 시작이 기본적으로 non-blocking인데도 적용된다. 다른 서버는 백그라운드 연결을 계속한다.

---

## 관리형 MCP 구성 (조직 통제)

`managed-mcp` 페이지. 기본적으로 Claude Code 사용자는 누구나 원하는 MCP 서버를 연결할 수 있다. Anthropic은 Directory 등재 전 listing criteria로 커넥터를 검토하지만, 어떤 MCP 서버도 보안 감사·관리하지 않는다. 관리자는 조직에서 실행 가능한 서버를 고정 승인 세트 배포부터 MCP 완전 비활성화까지 제한할 수 있다. [[18 보안과 샌드박스]]는 MCP 위협 모델과 승인 전 서버 평가법을 다룬다.

### 패턴 고르기

| Pattern | 동작 | 구성 |
|---------|------|------|
| **Disable MCP** | 어디서도 서버 미로드 | `managed-mcp.json` 빈 서버 맵 |
| **Fixed deployment** | 모든 사용자 동일 서버, 추가 불가 | `managed-mcp.json`에 원하는 서버 |
| **Approved catalog** | 승인 목록 게시, 사용자가 골라 추가, 그 외 차단 | `allowedMcpServers` + `allowManagedMcpServersOnly: true` |
| **Plugin servers only** | 서버는 플러그인에서만, 사용자 추가 불가 | `strictPluginOnlyCustomization`에 `mcp` 포함 ([[11 플러그인]]) |
| **Soft allowlist** | 사용자가 자기 설정에서 넓힐 수 있는 allowlist | `allowedMcpServers`만 (`allowManagedMcpServersOnly` 없이) |
| **Denylist only** | 알려진 불량 서버 차단, 나머지 허용 | `deniedMcpServers` |
| **No restrictions** | 사용자가 무엇이든 추가 | 관리형 MCP 구성 미배포 |

> [!note] Claude Code엔 사용자가 탐색·설치하는 내장 MCP 레지스트리가 없다. approved-catalog 패턴은 승인 목록과 `claude mcp add` 명령을 내부 위키 등에 공유하거나, 서버를 플러그인으로 묶어 managed plugin marketplace로 배포해 `/plugin`에서 탐색·설치하게 한다.

### `managed-mcp.json`으로 배타적 통제

`managed-mcp.json`을 배포하면 Claude Code는 그 파일이 정의한 서버만 로드한다. 사용자는 다른 MCP 서버(플러그인 제공 서버 포함)를 추가·수정·사용할 수 없다. 이 파일은 claude.ai 커넥터도 기본 억제한다(아래 예외 설정 제외).

추가 필터:
- `allowedMcpServers`/`deniedMcpServers`는 관리형 서버에도 적용 — 통과 못한 관리형 서버는 미로드.
- 사용자 자신의 `deniedMcpServers`가 병합되므로, 사용자는 자신에 한해 관리형 서버를 차단할 수 있다.

`managed-mcp.json`은 독립 파일이라 server-managed settings로 전달 불가. 관리자 권한으로 시스템 경로에 쓸 수 있는 프로세스(Jamf/구성 프로파일(macOS), Group Policy/Intune(Windows), Linux 플릿 관리 등)로 배포한다.

| Platform | Path |
|----------|------|
| macOS | `/Library/Application Support/ClaudeCode/managed-mcp.json` |
| Linux·WSL | `/etc/claude-code/managed-mcp.json` |
| Windows | `C:\Program Files\ClaudeCode\managed-mcp.json` |

프로젝트 `.mcp.json`과 동일한 형식:

```json
{
  "mcpServers": {
    "github": { "type": "http", "url": "https://api.githubcopilot.com/mcp/" },
    "sentry": { "type": "http", "url": "https://mcp.sentry.dev/mcp" },
    "company-internal": {
      "type": "stdio",
      "command": "/usr/local/bin/company-mcp-server",
      "args": ["--config", "/etc/company/mcp-config.json"],
      "env": { "COMPANY_API_URL": "https://internal.example.com" }
    }
  }
}
```

#### 사용자별 자격증명으로 인증

머신의 누구나 이 파일을 읽을 수 있으니 `env` 블록에 API 키·자격증명을 저장하지 마라. 대신:
- `${VAR}` 확장으로 각 사용자 환경에서 secret을 읽음
- OAuth 또는 사용자별 헤더로 각자 인증
- `headersHelper`로 연결 시점에 자격증명 생성

#### 구성 검증

```bash
# 1. managed-mcp.json의 서버만 보여야 함. 사용자 서버가 보이면 파일이 안 읽힘 → 경로·권한 확인
claude mcp list

# 2. 추가 시도는 enterprise 정책 에러로 거부됨 (URL은 실제 서버일 필요 없음)
claude mcp add --transport http test https://example.com/mcp
#   → Cannot add MCP server: enterprise MCP configuration is active and has exclusive control over MCP servers
```

#### MCP 완전 비활성화

```json
{ "mcpServers": {} }
```

빈 서버 맵을 배포하면 모든 서버 차단. `/mcp`엔 서버가 안 보이고, `claude mcp add`는 위 enterprise 정책 에러를 낸다. 이전에 구성한 서버는 다음 세션부터 정책 때문이라는 경고 없이 로드를 멈춘다.

#### claude.ai 커넥터를 관리형 세트와 함께 허용

`managed-mcp.json`은 기본적으로 claude.ai 커넥터(관리자가 admin console에서 조직용으로 구성한 것 포함)를 억제한다. 함께 로드하려면 managed settings source에 `"allowAllClaudeAiMcps": true`를 설정(v2.1.149+ 필요). 이 설정으로 `managed-mcp.json`이 없을 때와 동일한 claude.ai 커넥터를 로드한다. allowlist/denylist는 여전히 적용되므로 `deniedMcpServers`로 특정 커넥터 차단 가능. 플러그인 제공 서버는 계속 억제된다. 이 설정은 admin 통제 정책 티어(server-managed settings, MDM plist/HKLM 레지스트리, 시스템 `managed-settings.json`)에서만 읽힌다 — 사용자/프로젝트 설정에 두면 무효.

### allowlist·denylist 기반 통제

allowlist/denylist는 구성된 서버 중 어느 것이 로드되는지 필터링한다. 레지스트리가 아니다 — 서버는 사용자·플러그인·`managed-mcp.json`이 먼저 추가해야 적용된다. 서버를 사용자에게 *배포*하려면 `managed-mcp.json`을 써라.

allowlist를 authoritative하게 하려면 managed settings source에 `allowedMcpServers`와 `allowManagedMcpServersOnly: true`를 함께 둔다. `allowManagedMcpServersOnly` 없이는 모든 설정 소스(사용자 `~/.claude/settings.json` 포함)의 allowlist가 병합되어 사용자가 넓힐 수 있다. denylist는 소스 무관 항상 병합.

> [!note] `allowManagedMcpServersOnly`는 permission rules만 잠그는 `allowManagedPermissionRulesOnly`와 별개다([[05 권한]]). 후자 플래그를 켜도 MCP allowlist는 강제되지 않는다.

#### URL·command·name으로 서버 매칭

| Key | Matches | 용도 |
|-----|---------|------|
| `serverUrl` | 원격 서버 URL, 정확 또는 `*` 와일드카드 | HTTP·SSE 서버 |
| `serverCommand` | stdio 서버를 시작하는 정확한 명령·인자 | Stdio 서버 |
| `serverName` | 사용자 지정 라벨. 정확 매치만(와일드카드 미확장) | 양쪽 모두, 단 아래 경고 |

`allowedMcpServers` 미설정과 빈 배열은 다르다:

| Setting | Unset(기본) | Empty `[]` | Populated |
|---------|------------|-----------|-----------|
| `allowedMcpServers` | 모든 서버 허용 | 어떤 서버도 불허 | 매칭 서버만 허용 |
| `deniedMcpServers` | 차단 없음 | 차단 없음 | 매칭 서버 차단 |

> [!warning] `serverName`만 쓴 allowlist는 보안 통제가 아니다. 이름은 `claude mcp add`나 config 편집 시 사용자가 붙이는 라벨이라 누구든 서버를 `github`라 부를 수 있다. 실제 실행 서버를 강제하려면 `serverCommand`나 `serverUrl` 엔트리를 추가하라.

#### 서버 평가 순서

서버(`managed-mcp.json` 포함) 로드 전 세 검사를 순서대로 수행:
1. **리스트 병합**: 모든 소스의 allowlist/denylist를 각각 하나로 합침. `allowManagedMcpServersOnly`가 true면 관리형 allowlist만 유지(denylist는 항상 모든 소스 병합).
2. **denylist 검사**: URL/command/name 중 하나라도 denylist에 매칭되면 차단. denylist 매치를 덮는 것은 없음.
3. **allowlist 검사**: `allowedMcpServers`가 어디에도 없으면 denylist 통과 서버는 모두 로드. 설정됐으면 서버 타입별로:

| Server type | 허용 조건 |
|-------------|-----------|
| Remote (HTTP/SSE) | `serverUrl` 엔트리 매치. allowlist에 `serverUrl` 엔트리가 하나도 없을 때만 `serverName` 매치가 인정됨 |
| Stdio | `serverCommand` 엔트리 매치. `serverCommand` 엔트리가 하나도 없을 때만 `serverName` 매치 인정 |

매칭 규칙:
- **Command는 정확 매치** — 모든 인자가 순서대로. `["npx","-y","server"]`는 `["npx","server"]`나 `["npx","-y","server","--flag"]`와 불일치.
- **URL은 `*` 와일드카드** 지원(scheme 포함 어디서나). 호스트명 매치는 대소문자 무시·trailing FQDN 점 무시(예 `https://Mcp.Example.com/*`가 `https://mcp.example.com/api` 매치), 경로는 대소문자 구분.

| Pattern | 허용 |
|---------|------|
| `https://mcp.example.com/*` | 특정 도메인의 모든 경로 |
| `https://mcp.example.com` | 역시 모든 경로(경로 없는 패턴은 모든 경로 매치) |
| `https://*.example.com/*` | `example.com`의 모든 서브도메인 |
| `http://localhost:*/*` | localhost의 모든 포트 |
| `*://mcp.example.com/*` | 특정 도메인으로의 모든 scheme |

#### 예시 구성 (하드 allowlist + denylist)

```json
{
  "allowedMcpServers": [
    { "serverUrl": "https://api.githubcopilot.com/*" },
    { "serverUrl": "https://mcp.sentry.dev/*" },
    { "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."] },
    { "serverCommand": ["python", "/usr/local/bin/approved-server.py"] },
    { "serverUrl": "https://mcp.example.com/*" },
    { "serverUrl": "https://*.internal.example.com/*" }
  ],
  "deniedMcpServers": [
    { "serverName": "dangerous-server" },
    { "serverCommand": ["npx", "-y", "unapproved-package"] },
    { "serverUrl": "https://*.untrusted.example.com/*" }
  ]
}
```

- 첫 `serverUrl` 엔트리가 생기면 모든 원격 서버는 URL 패턴에 매치해야 함 → 사용자가 허용된 이름을 붙여 미등재 원격 서버를 통과시킬 수 없음.
- 첫 `serverCommand` 엔트리도 stdio 서버에 같은 효과 → 모든 로컬 서버가 등재 명령과 정확히 매치해야 함.
- denylist의 `serverName` 엔트리는 항상 적용 → `dangerous-server`라는 이름의 서버는 URL/command 무관하게 차단.
- 이 allowlist의 `serverName` 엔트리는 두 transport 모두 더 엄격한 엔트리가 이미 있으므로 아무것도 매치하지 못함.

#### allowlist를 managed settings로만 제한

```json
{
  "allowManagedMcpServersOnly": true,
  "allowedMcpServers": [
    { "serverUrl": "https://api.githubcopilot.com/*" },
    { "serverUrl": "https://*.internal.example.com/*" }
  ]
}
```

`allowManagedMcpServersOnly: true`면 user/project/local 설정의 allowlist는 무시된다. denylist는 여전히 모든 소스에서 병합되어 사용자가 자신에 한해 항상 서버를 차단할 수 있다.

### 제한이 사용자에게 보이는 방식

| Restriction | 사용자가 보는 것 |
|-------------|------------------|
| `managed-mcp.json` 존재 + `claude mcp add` | `Cannot add MCP server: enterprise MCP configuration is active and has exclusive control over MCP servers` |
| denylist 서버 + `claude mcp add` | `Cannot add MCP server "<name>": server is explicitly blocked by enterprise policy` |
| allowlist에 없음 + `claude mcp add` | `Cannot add MCP server "<name>": not allowed by enterprise policy` |
| 기존 구성 서버가 이제 정책으로 차단됨 | `/mcp`·`claude mcp list`에서 경고 없이 조용히 사라짐 |

마지막 경우 사용자는 정책이 이유라는 신호를 못 받으니, 새 제한을 롤아웃할 때 어떤 서버가 차단되는지 알려라.

### MCP 사용량 모니터링

OpenTelemetry export 구성 시 Claude Code는 사용자가 호출하는 MCP 서버·도구를 기록할 수 있다. `OTEL_LOG_TOOL_DETAILS=1`로 도구 이벤트에 MCP 서버·도구 이름을 포함시킨 뒤 collector에서 집계한다. ([[16 CI-CD와 팀 통합]] 연관)

### 구성 요약

| Surface | 통제 대상 | 위치 | 전달 방법 |
|---------|-----------|------|-----------|
| `managed-mcp.json` | 고정 서버 세트, 배타적 통제 | 시스템 경로(macOS/Linux/Windows) | MDM·GPO·플릿 관리·관리자 권한 프로세스. server-managed settings로 불가 |
| `allowedMcpServers` | 허용 서버 allowlist | 임의 설정 파일; `allowManagedMcpServersOnly` 없으면 모든 소스 병합 | 강제하려면 managed settings source |
| `deniedMcpServers` | 차단 서버 denylist | 임의 설정 파일; 모든 소스 병합 | allowedMcpServers와 동일 |
| `allowManagedMcpServersOnly` | allowlist를 managed 소스로만 잠금 | managed settings source만(그 외 무효) | allowedMcpServers와 동일 |
| `allowAllClaudeAiMcps` | `managed-mcp.json`과 함께 claude.ai 커넥터 로드 | managed settings source만(그 외 무효) | allowedMcpServers와 동일 |

---

## 트러블슈팅

세션 안 `/mcp` 또는 셸 `claude mcp list`로 상태를 확인한 뒤 증상별로 대응한다.

- **`/mcp shows No MCP servers configured`**: 현재 디렉터리에 서버를 못 찾음. ① 다른 프로젝트에서 `claude mcp add` 했을 가능성(local 서버는 프로젝트에 묶임) → 현재 프로젝트에서 다시 추가하거나 `--scope user`로 추가. ② 잘못된 경로의 config 편집 → 올바른 파일은 `~/.claude.json`과 `<project>/.mcp.json`뿐. `~/.claude/config/mcp.json` 등은 읽지 않음.
- **`Failed to connect` / `Connection error`**: 서버가 시작 안 됐거나 URL이 응답 안 함. 브라우저 사인인 대신 토큰을 기대하는 HTTP 서버에서도 나타남.
  - HTTP: `curl -I https://mcp.sentry.dev/mcp`로 도달성 확인(PowerShell은 `curl.exe`). `404`/`405`=서버 작동(많은 MCP 엔드포인트는 POST만 응답), `401`/`403`=인증 필요, 무응답=URL·네트워크 확인.
  - stdio: 구성된 명령을 터미널에서 직접 실행. 시작 후 입력 대기=서버 정상 → `claude mcp get <name>`의 명령과 비교(다르면 `--` 구분자 누락 가능성, 제거 후 `--` 넣어 재추가). 명령 에러=메시지가 누락(Node.js·브라우저 등)을 알려줌.
- **`Connection timed out at startup`**: 기본 30초 시작 타임아웃 초과. stdio 첫 실행은 npx 다운로드로 느릴 수 있음. `MCP_TIMEOUT=60000 claude`(PowerShell: `$env:MCP_TIMEOUT = "60000"; claude`).
- **`Server already exists`**: 같은 이름·스코프에 이미 존재. 기존 엔트리 제거(`claude mcp remove <name>`) 또는 다른 이름 사용. 여러 스코프에 있으면 `--scope`로 지정(예 `--scope local`).
- **`Server connects but no tools appear`**: `/mcp`에서 서버 선택. 도구 목록이 비면 보통 API 키 같은 필수 환경변수 누락 → `--env KEY=value` 또는 `.mcp.json` `env`로 전달.
- **`Changes to .mcp.json don't take effect`**: Claude Code는 세션 시작 시 `.mcp.json`을 읽음 → 편집 후 세션 재시작. 안 나타나면 `/mcp`에서 parse 경고 확인(잘못된 엔트리는 건너뛰고 문제 필드 표시). 이전에 거부했다면 `claude mcp reset-project-choices`.
- **`OAuth sign-in fails or browser doesn't open`**: `/mcp` → 서버 선택 → `Authenticate` 재시도. 브라우저가 안 열리면 터미널 URL을 직접 연다.

---

## 원본 문서

- [mcp](https://code.claude.com/docs/en/mcp)
- [mcp-quickstart](https://code.claude.com/docs/en/mcp-quickstart)
- [managed-mcp](https://code.claude.com/docs/en/managed-mcp)
