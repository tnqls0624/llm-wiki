---
title: 22 Agent SDK — 시작
updated: 2026-06-07
sources: [agent-sdk/overview, agent-sdk/quickstart, agent-sdk/agent-loop, agent-sdk/claude-code-features, agent-sdk/migration-guide]
---

# 22 Agent SDK — 시작

허브: [[Claude]] · 다음 권: [[23 Agent SDK — 핵심 기능]] · [[24 Agent SDK — 고급과 레퍼런스]]

Claude Agent SDK는 [[01 시작하기|Claude Code]]를 구동하는 것과 **동일한 도구, 에이전트 루프, 컨텍스트 관리**를 Python / TypeScript 라이브러리로 제공한다. 즉 Claude Code의 능력을 CLI가 아닌 **내 코드 안에서 프로그래밍 가능하게** 박아넣어 자율 AI 에이전트를 만드는 것이 목적이다. 이 노트는 SDK를 처음 시작하는 데 필요한 5개 페이지(개요 · 퀵스타트 · 에이전트 루프 · Claude Code 기능 통합 · 마이그레이션)를 종합한다.

> [!note] 구독 플랜 사용량 변경 (2026-06-15부터)
> 구독 플랜에서 Agent SDK 및 `claude -p` 사용량은 인터랙티브 사용 한도와 **분리된** 별도의 월간 Agent SDK 크레딧에서 차감된다. 자세한 내용은 Anthropic 지원 문서 참고.

> [!warning] 인증 정책
> 별도 승인이 없는 한 Anthropic은 서드파티 개발자가 자사 제품(Agent SDK 기반 에이전트 포함)에 claude.ai 로그인이나 rate limit을 제공하는 것을 허용하지 않는다. 반드시 **API 키 기반 인증**을 사용하라.

---

## 1. 개요 — Agent SDK란 무엇인가 (overview)

SDK는 파일 읽기·명령 실행·코드 편집을 위한 **내장 도구(built-in tools)**를 포함하므로, 도구 실행 로직을 직접 구현하지 않아도 에이전트가 즉시 동작한다. 가장 기본적인 진입점은 `query()` 함수다.

```python Python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="Find and fix the bug in auth.py",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Edit", "Bash"]),
    ):
        print(message)  # Claude가 파일을 읽고 버그를 찾아 편집한다

asyncio.run(main())
```

```typescript TypeScript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Find and fix the bug in auth.ts",
  options: { allowedTools: ["Read", "Edit", "Bash"] }
})) {
  console.log(message);
}
```

### 설치와 API 키

| 작업 | TypeScript | Python |
|------|-----------|--------|
| 설치 | `npm install @anthropic-ai/claude-agent-sdk` | `pip install claude-agent-sdk` |
| 런타임 요구 | Node.js 18+ | Python 3.10+ |
| 바이너리 | 네이티브 Claude Code 바이너리를 optional dependency로 **번들** (별도 설치 불필요) | — |

Python에서 `No matching distribution found for claude-agent-sdk` 오류가 나면 인터프리터가 3.10 미만이라는 뜻이다. `python3 --version`(macOS/Linux) 또는 `py --version`(Windows)으로 확인하라.

API 키는 [Console](https://platform.claude.com/)에서 발급받아 환경변수로 설정한다.

```bash
export ANTHROPIC_API_KEY=your-api-key
```

서드파티 API 프로바이더 인증도 지원한다 (자세한 셋업은 [[17 클라우드 프로바이더]] 참고):

| 프로바이더 | 환경변수 |
|-----------|---------|
| Amazon Bedrock | `CLAUDE_CODE_USE_BEDROCK=1` + AWS 자격증명 |
| Claude Platform on AWS | `CLAUDE_CODE_USE_ANTHROPIC_AWS=1`, `ANTHROPIC_AWS_WORKSPACE_ID` + AWS 자격증명 |
| Google Vertex AI | `CLAUDE_CODE_USE_VERTEX=1` + Google Cloud 자격증명 |
| Microsoft Azure | `CLAUDE_CODE_USE_FOUNDRY=1` + Azure 자격증명 |

### 첫 에이전트 실행

```python Python
async for message in query(
    prompt="What files are in this directory?",
    options=ClaudeAgentOptions(allowed_tools=["Bash", "Glob"]),
):
    if hasattr(message, "result"):
        print(message.result)
```

### 핵심 능력 (Capabilities)

Claude Code를 강력하게 만드는 모든 기능이 SDK에서 그대로 쓸 수 있다.

| 능력 | 요지 | SDK 옵션 / 표면 | 상세 노트 |
|------|------|---------------|----------|
| **Built-in tools** | 파일·명령·코드 검색이 기본 제공 | `allowed_tools` / `allowedTools` | [[06 내장 도구 레퍼런스]] |
| **Hooks** | 에이전트 라이프사이클 특정 지점에서 커스텀 코드 실행(검증·로깅·차단·변형) | `hooks` 파라미터 + `HookMatcher` | [[09 훅]] |
| **Subagents** | 전문 하위 에이전트를 스폰해 집중 작업 위임 | `agents` + `allowedTools: ["Agent"]` | [[08 서브에이전트와 에이전트 팀]] |
| **MCP** | 외부 시스템(DB·브라우저·API) 연결 | `mcp_servers` / `mcpServers` | [[10 MCP]] |
| **Permissions** | 어떤 도구를 언제 쓸지 정밀 제어 | `allowed_tools`, `permission_mode` 등 | [[05 권한]] |
| **Sessions** | 여러 교환에 걸쳐 컨텍스트 유지·재개·포크 | `resume`, `session_id` | [[03 메모리와 컨텍스트]] |

**Hooks 예시 (모든 파일 변경을 감사 로그로):**

```python Python
import asyncio
from datetime import datetime
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher

async def log_file_change(input_data, tool_use_id, context):
    file_path = input_data.get("tool_input", {}).get("file_path", "unknown")
    with open("./audit.log", "a") as f:
        f.write(f"{datetime.now()}: modified {file_path}\n")
    return {}

async def main():
    async for message in query(
        prompt="Refactor utils.py to improve readability",
        options=ClaudeAgentOptions(
            permission_mode="acceptEdits",
            hooks={
                "PostToolUse": [
                    HookMatcher(matcher="Edit|Write", hooks=[log_file_change])
                ]
            },
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)

asyncio.run(main())
```

**Subagents 예시:** 서브에이전트는 `Agent` 도구를 통해 호출되므로 자동 승인을 원하면 `allowedTools`에 `"Agent"`를 포함해야 한다. 서브에이전트 컨텍스트 내부에서 나온 메시지는 `parent_tool_use_id` 필드를 가지므로 어느 서브에이전트 실행에 속하는지 추적할 수 있다.

```python Python
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

async for message in query(
    prompt="Use the code-reviewer agent to review this codebase",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Agent"],
        agents={
            "code-reviewer": AgentDefinition(
                description="Expert code reviewer for quality and security reviews.",
                prompt="Analyze code quality and suggest improvements.",
                tools=["Read", "Glob", "Grep"],
            )
        },
    ),
):
    ...
```

**MCP 예시 (Playwright 브라우저 자동화 연결):** 브라우저/컴퓨터 사용 관련은 [[21 브라우저와 컴퓨터 사용]] 참고.

```python Python
async for message in query(
    prompt="Open example.com and describe what you see",
    options=ClaudeAgentOptions(
        mcp_servers={
            "playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]}
        }
    ),
):
    ...
```

**Sessions 예시:** 첫 쿼리에서 세션 ID를 캡처해 두 번째 쿼리에서 `resume`으로 전체 컨텍스트를 이어받는다.

```python Python
session_id = None
async for message in query(
    prompt="Read the authentication module",
    options=ClaudeAgentOptions(allowed_tools=["Read", "Glob"]),
):
    if isinstance(message, SystemMessage) and message.subtype == "init":
        session_id = message.data["session_id"]

async for message in query(
    prompt="Now find all places that call it",
    options=ClaudeAgentOptions(resume=session_id),
):
    if isinstance(message, ResultMessage):
        print(message.result)
```

### Agent SDK를 다른 Claude 도구와 비교

Anthropic은 Claude로 빌드하는 여러 방법을 제공한다. SDK의 위치를 이해하는 것이 도구 선택의 핵심이다.

**vs Client SDK** — Anthropic Client SDK는 직접 API 접근으로, 도구 실행 루프를 **직접 구현**해야 한다. Agent SDK는 Claude가 도구 실행을 **자율적으로 처리**한다.

```python
# Client SDK: 도구 루프를 직접 구현
response = client.messages.create(...)
while response.stop_reason == "tool_use":
    result = your_tool_executor(response.tool_use)
    response = client.messages.create(tool_result=result, **params)

# Agent SDK: Claude가 도구를 자율 처리
async for message in query(prompt="Fix the bug in auth.py"):
    print(message)
```

**vs Claude Code CLI** — 같은 능력, 다른 인터페이스. 많은 팀이 둘 다 쓴다(일상 개발은 CLI, 프로덕션은 SDK). 워크플로우는 양쪽에서 그대로 변환된다. 관련 CLI 비교는 [[02 CLI 레퍼런스]] · CI/CD 통합은 [[16 CI-CD와 팀 통합]].

| Use case | 추천 |
|----------|------|
| Interactive development | CLI |
| CI/CD pipelines | SDK |
| Custom applications | SDK |
| One-off tasks | CLI |
| Production automation | SDK |

**vs Managed Agents** — Managed Agents는 호스팅된 REST API(Anthropic이 에이전트와 샌드박스를 운영). Agent SDK는 **내 프로세스 안에서** 에이전트 루프를 돌리는 라이브러리.

| | Agent SDK | Managed Agents |
|---|-----------|----------------|
| **실행 위치** | 내 프로세스, 내 인프라 | Anthropic 관리 인프라 |
| **인터페이스** | Python/TypeScript 라이브러리 | REST API |
| **작업 대상** | 내 인프라의 파일 | 세션당 관리형 샌드박스 |
| **세션 상태** | 내 파일시스템의 JSONL | Anthropic 호스팅 이벤트 로그 |
| **커스텀 도구** | 인프로세스 Python/TS 함수 | Claude가 트리거 → 내가 실행·반환 |
| **적합** | 로컬 프로토타이핑, 파일시스템·서비스 직접 작업 | 샌드박스/세션 인프라 운영 없는 프로덕션, 장기·비동기 세션 |

전형적 경로: Agent SDK로 로컬 프로토타이핑 → Managed Agents로 프로덕션 이전.

### 브랜딩 가이드라인

파트너가 Claude 브랜딩을 사용하는 것은 선택사항이다.
- **허용:** "Claude Agent"(드롭다운 메뉴 권장), "Claude"(이미 "Agents" 라벨이 붙은 메뉴 내), "{YourAgentName} Powered by Claude"
- **불가:** "Claude Code" / "Claude Code Agent", Claude Code 스타일의 ASCII 아트나 시각 요소 모방

라이선스는 Anthropic Commercial Terms of Service를 따른다.

---

## 2. 퀵스타트 — 버그 수정 에이전트 만들기 (quickstart)

5분 만에 코드를 읽고 버그를 찾아 자동으로 고치는 에이전트를 만드는 실습이다.

### 셋업

전제조건: Node.js 18+ 또는 Python 3.10+, Anthropic 계정.

```bash
mkdir my-agent
cd my-agent
```

SDK는 어느 폴더에서 실행하든 그 디렉터리와 하위 디렉터리의 파일에 기본 접근한다.

설치 옵션:

```bash
# TypeScript
npm install @anthropic-ai/claude-agent-sdk

# Python (uv) — 가상환경 자동 처리
uv init
uv add claude-agent-sdk

# Python (pip) — macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
pip install claude-agent-sdk

# Python (pip) — Windows
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install claude-agent-sdk
```

> Windows PowerShell이 `Activate.ps1`을 execution policy 오류로 막으면 먼저 `Set-ExecutionPolicy -Scope Process RemoteSigned` 실행.

API 키는 프로젝트 디렉터리에 `.env` 파일로 둔다.

```bash
ANTHROPIC_API_KEY=your-api-key
```

### 버그가 있는 파일 만들기

`utils.py`:

```python
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

def get_user_name(user):
    return user["name"].upper()
```

버그 2개: `calculate_average([])`는 0으로 나누기 크래시, `get_user_name(None)`은 TypeError 크래시.

### 에이전트 작성과 실행

```python agent.py
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

async def main():
    async for message in query(
        prompt="Review utils.py for bugs that would cause crashes. Fix any issues you find.",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Glob"],  # 이 도구들 자동 승인
            permission_mode="acceptEdits",            # 파일 편집 자동 승인
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)              # Claude의 추론
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")   # 호출 중인 도구
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")      # 최종 결과

asyncio.run(main())
```

실행:

```bash
npx tsx agent.ts   # TypeScript
uv run agent.py    # Python (uv)
python agent.py    # Python (pip, 가상환경 활성화 상태)
```

코드의 세 핵심 부분:
1. **`query`** — 에이전트 루프를 만드는 진입점. async iterator를 반환하므로 `async for`로 메시지를 스트리밍한다.
2. **`prompt`** — Claude에게 시킬 일. 어떤 도구를 쓸지는 Claude가 스스로 판단.
3. **`options`** — 에이전트 설정. 여기선 `allowedTools`로 도구를 사전 승인하고 `permissionMode: "acceptEdits"`로 편집을 자동 승인.

`async for` 루프는 Claude가 생각하고 → 도구 호출하고 → 결과 관찰하고 → 다음을 결정하는 동안 계속 돈다. SDK가 오케스트레이션(도구 실행, 컨텍스트 관리, 재시도)을 처리하므로 사용자는 스트림만 소비하면 된다. 루프는 Claude가 작업을 끝내거나 에러가 나면 종료된다.

> [!note] 스트리밍 vs 싱글턴
> 위 예시는 실시간 진행 표시를 위해 스트리밍을 쓴다. 라이브 출력이 불필요한 배경 작업·CI 파이프라인이라면 모든 메시지를 한 번에 수집할 수도 있다(streaming-vs-single-mode — [[24 Agent SDK — 고급과 레퍼런스]]).

### 에이전트 커스터마이즈

```python
# 웹 검색 추가
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Glob", "WebSearch"], permission_mode="acceptEdits"
)

# 커스텀 시스템 프롬프트
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Glob"],
    permission_mode="acceptEdits",
    system_prompt="You are a senior Python developer. Always follow PEP 8 style guidelines.",
)

# 터미널 명령 실행 (Bash) — "Write unit tests for utils.py, run them, and fix any failures" 같은 프롬프트 가능
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Edit", "Glob", "Bash"], permission_mode="acceptEdits"
)
```

### 핵심 개념 — 도구 조합과 권한 모드

**도구 조합**으로 에이전트가 할 수 있는 일이 결정된다:

| Tools | 에이전트 능력 |
|-------|-------------|
| `Read`, `Glob`, `Grep` | 읽기 전용 분석 |
| `Read`, `Edit`, `Glob` | 분석 + 코드 수정 |
| `Read`, `Edit`, `Bash`, `Glob`, `Grep` | 완전 자동화 |

**권한 모드(permission mode)**로 사람 감독 수준을 조절한다 (전체 규칙은 [[05 권한]]):

| Mode | 동작 | Use case |
|------|------|----------|
| `acceptEdits` | 파일 편집·일반 파일시스템 명령 자동 승인, 나머지는 질문 | 신뢰하는 개발 워크플로우 |
| `dontAsk` | `allowedTools`에 없는 건 전부 거부 | 잠긴(locked-down) 헤드리스 에이전트 |
| `auto` (TS 전용) | 모델 분류기가 각 도구 호출을 승인/거부 | 안전 가드레일을 가진 자율 에이전트 |
| `bypassPermissions` | 모든 도구를 질문 없이 실행 | 샌드박스 CI, 완전 신뢰 환경 |
| `default` | 승인 처리를 위한 `canUseTool` 콜백 필요 | 커스텀 승인 플로우 |

### 퀵스타트 트러블슈팅

- "API key not found": `.env`나 셸 환경에 `ANTHROPIC_API_KEY`가 설정됐는지 확인 (전체 가이드는 [[25 트러블슈팅]]).
- **`thinking.type.enabled` is not supported for this model**: Claude Opus 4.7은 `thinking.type.enabled`를 `thinking.type.adaptive`로 대체했다. 구버전 SDK는 `claude-opus-4-7` 선택 시 400 에러를 낸다. **Agent SDK v0.2.111 이상으로 업그레이드**하면 해결.

---

## 3. 에이전트 루프의 동작 원리 (agent-loop)

SDK는 Claude Code를 구동하는 것과 **동일한 실행 루프**를 내 애플리케이션에 임베드한다. CLI 설치가 필요 없는 독립 패키지다.

### 루프 한눈에 보기

모든 에이전트 세션은 같은 사이클을 따른다:

1. **프롬프트 수신** — 프롬프트 + 시스템 프롬프트 + 도구 정의 + 대화 이력을 받는다. SDK는 세션 메타데이터를 담은 `subtype="init"`의 `SystemMessage`를 yield.
2. **평가와 응답** — 현재 상태를 평가해 진행 방식 결정. 텍스트 응답·도구 호출 요청·둘 다 가능. SDK는 텍스트와 도구 호출을 담은 `AssistantMessage`를 yield.
3. **도구 실행** — 요청된 각 도구를 실행하고 결과를 수집해 Claude에게 다시 전달. [[09 훅]]으로 도구 실행 전에 가로채기/변형/차단 가능.
4. **반복** — 2·3을 반복. 한 사이클이 한 **턴(turn)**. 도구 호출이 없는 응답이 나올 때까지 계속.
5. **결과 반환** — 도구 호출 없는 최종 `AssistantMessage` → 최종 텍스트·토큰 사용량·비용·세션 ID를 담은 `ResultMessage`.

간단한 질문("여기 어떤 파일 있어?")은 1~2턴, 복잡한 작업("auth 모듈 리팩터하고 테스트 업데이트해")은 수십 번의 도구 호출이 여러 턴에 걸쳐 연쇄된다.

### 턴과 메시지

한 **턴**은 루프 안의 한 번의 왕복이다: Claude가 도구 호출을 포함한 출력 생성 → SDK가 도구 실행 → 결과를 Claude에 자동 전달. 이 과정에서는 **사용자 코드로 제어가 넘어오지 않는다**. 도구 호출 없는 출력이 나올 때까지 턴이 계속된다.

예시 — "Fix the failing tests in auth.ts":
- **Turn 1:** `Bash`로 `npm test` (3개 실패) → `AssistantMessage` + 출력 담은 `UserMessage`
- **Turn 2:** `auth.ts`·`auth.test.ts`를 `Read`
- **Turn 3:** `Edit`로 수정 후 `Bash`로 재실행 → 전부 통과
- **Final turn:** 도구 호출 없는 텍스트 응답 → 최종 `AssistantMessage` + `ResultMessage`

(총 4턴: 도구 호출 3턴 + 최종 텍스트 1턴)

`max_turns` / `maxTurns`로 루프를 제한할 수 있고 **도구 사용 턴만** 카운트한다. `max_budget_usd` / `maxBudgetUsd`로 지출 임계값 기반 제한도 가능. 제한이 없으면 Claude가 스스로 끝낼 때까지 도는데, 잘 정의된 작업엔 괜찮지만 "이 코드베이스 개선해" 같은 열린 프롬프트는 오래 돌 수 있다. **프로덕션 에이전트는 예산 설정이 좋은 기본값.**

### 메시지 타입 (5개 핵심)

| 타입 | 언제 | 핵심 |
|------|------|------|
| `SystemMessage` | 세션 라이프사이클 이벤트 | `subtype="init"`(첫 메시지, 세션 메타데이터), `"compact_boundary"`(컴팩션 후). TS에서 compact boundary는 별도 `SDKCompactBoundaryMessage` 타입 |
| `AssistantMessage` | 각 Claude 응답 후(최종 텍스트 포함) | 텍스트 블록 + 도구 호출 블록 |
| `UserMessage` | 각 도구 실행 후 | Claude에 돌려보내는 도구 결과 (스트림 중 사용자 입력도 포함) |
| `StreamEvent` | partial messages 활성화 시에만 | 원시 API 스트리밍 이벤트(텍스트 델타, 도구 입력 청크) |
| `ResultMessage` | 루프 종료 표시 | 최종 텍스트·토큰 사용량·비용·세션 ID. `subtype`로 성공/제한 도달 판단 |

> [!warning] ResultMessage 후에도 스트림은 끝까지 소비
> `prompt_suggestion` 같은 소수의 후행 시스템 이벤트가 `ResultMessage` 뒤에 도착할 수 있다. 결과에서 `break` 하지 말고 스트림을 끝까지 iterate 하라.

TS SDK는 추가 관찰성 이벤트(hook 이벤트, 도구 진행, rate limit, task 알림)도 yield하지만 루프 구동에 필수는 아니다.

**메시지 타입 체크 방법:**
- **Python:** `claude_agent_sdk`에서 import한 클래스로 `isinstance()` 체크 (`isinstance(message, ResultMessage)`)
- **TypeScript:** `type` 문자열 필드 체크 (`message.type === "result"`). `AssistantMessage`·`UserMessage`는 원시 API 메시지를 `.message` 필드로 감싸므로 컨텐츠 블록은 `message.message.content` (`message.content` 아님)

### 도구 실행

#### 내장 도구 (built-in tools)

SDK는 Claude Code와 같은 도구를 포함한다 (각 도구 동작은 [[06 내장 도구 레퍼런스]]):

| 카테고리 | 도구 | 역할 |
|---------|------|------|
| **File operations** | `Read`, `Edit`, `Write` | 파일 읽기·수정·생성 |
| **Search** | `Glob`, `Grep` | 패턴으로 파일 찾기, regex로 내용 검색 |
| **Execution** | `Bash` | 셸 명령·스크립트·git |
| **Web** | `WebSearch`, `WebFetch` | 웹 검색, 페이지 fetch·파싱 |
| **Discovery** | `ToolSearch` | 모든 도구를 미리 로드하지 않고 on-demand로 동적 발견·로드 |
| **Orchestration** | `Agent`, `Skill`, `AskUserQuestion`, `TaskCreate`, `TaskUpdate` | 서브에이전트 스폰, 스킬 호출, 사용자에 질문, 태스크 추적 |

추가로: [[10 MCP]] 서버로 외부 서비스 연결, custom tool handler로 커스텀 도구 정의, setting source로 프로젝트 [[07 스킬]] 로드.

#### 도구 권한

Claude는 작업에 따라 어떤 도구를 부를지 결정하지만, **실행 허용 여부는 사용자가 제어**한다. 세 옵션이 함께 작동한다:

- **`allowed_tools` / `allowedTools`** — 나열된 도구 자동 승인. 나열 안 된 도구도 사용 가능하지만 권한 필요.
- **`disallowed_tools` / `disallowedTools`** — 나열된 도구를 다른 설정과 무관하게 차단.
- **`permission_mode` / `permissionMode`** — allow/deny 규칙에 안 걸리는 도구를 어떻게 처리할지 제어.

개별 도구를 `"Bash(npm *)"` 같은 규칙으로 스코핑할 수도 있다. 도구가 거부되면 Claude는 거부 메시지를 도구 결과로 받고 보통 다른 접근을 시도하거나 진행 불가를 보고한다.

#### 병렬 도구 실행

한 턴에 여러 도구를 요청하면 도구 종류에 따라 동시/순차 실행된다. **읽기 전용 도구**(`Read`, `Glob`, `Grep`, read-only로 표시된 MCP 도구)는 동시 실행 가능. **상태 변경 도구**(`Edit`, `Write`, `Bash`)는 충돌 방지를 위해 순차 실행. 커스텀 도구는 기본 순차이며, annotation에 `readOnlyHint`(MCP SDK 필드명, TS·Python 공통)를 설정하면 병렬 활성화.

### 루프 제어 옵션

모두 `ClaudeAgentOptions`(Python) / `Options`(TS)의 필드다.

#### 턴과 예산

| 옵션 | 제어 | 기본 |
|------|------|------|
| `max_turns` / `maxTurns` | 최대 도구 사용 왕복 횟수 | 무제한 |
| `max_budget_usd` / `maxBudgetUsd` | 중단 전 최대 비용 | 무제한 |

한도 도달 시 `ResultMessage`의 subtype이 `error_max_turns` 또는 `error_max_budget_usd`가 된다. 비용 관련은 [[19 비용과 성능]].

#### Effort 레벨

`effort` 옵션은 Claude가 적용하는 추론량을 제어한다. 낮을수록 턴당 토큰이 적고 비용 절감. 모든 모델이 지원하진 않는다.

| Level | 동작 | 적합 |
|-------|------|------|
| `"low"` | 최소 추론, 빠른 응답 | 파일 조회, 디렉터리 나열 |
| `"medium"` | 균형 | 일상 편집, 표준 작업 |
| `"high"` | 철저한 분석 | 리팩터, 디버깅 |
| `"xhigh"` | 확장 추론 깊이 | 코딩·에이전트 작업; Opus 4.7 권장 |
| `"max"` | 최대 추론 깊이 | 깊은 분석이 필요한 다단계 문제 |

`effort` 미설정 시 Python SDK는 모델 기본값을 따르고, **TypeScript SDK는 `"high"`로 기본 설정**된다.

> [!note] effort vs extended thinking
> `effort`는 각 응답 내의 추론 깊이를 latency·토큰 비용과 맞바꾼다. [Extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)은 출력에 보이는 사고 사슬 블록을 만드는 **별개 기능**이다. 둘은 독립적이라 `effort: "low"` + extended thinking, 또는 `effort: "max"` + thinking 미사용 조합도 가능.

`effort`는 `query()` 옵션에서 세션 전체로, 또는 `AgentDefinition`의 `effort` 필드로 서브에이전트별로 세션 레벨을 오버라이드할 수 있다.

#### Permission mode (전체 표)

| Mode | 동작 |
|------|------|
| `"default"` | allow 규칙에 안 걸리는 도구는 승인 콜백 트리거; 콜백 없으면 거부 |
| `"acceptEdits"` | 파일 편집·일반 파일시스템 명령(`mkdir`, `touch`, `mv`, `cp` 등) 자동 승인; 그 외 Bash는 default 규칙 |
| `"plan"` | 읽기 전용 도구만 실행; Claude가 탐색하고 소스 편집 없이 계획 생성 |
| `"dontAsk"` | 절대 묻지 않음. 권한 규칙으로 사전 승인된 도구만 실행, 나머지 거부 |
| `"auto"` (TS 전용) | 모델 분류기가 각 도구 호출 승인/거부 |
| `"bypassPermissions"` | 모든 허용 도구를 묻지 않고 실행. Unix에서 root 실행 시 사용 불가. 격리 환경에서만 사용 |

인터랙티브 앱은 `"default"` + 승인 콜백, 개발 머신 자율 에이전트는 `"acceptEdits"`, CI·컨테이너 등 격리 환경에만 `"bypassPermissions"`.

#### Model

`model` 미설정 시 인증 방식·구독에 따른 Claude Code 기본값 사용. `model="claude-sonnet-4-6"`처럼 명시해 특정 모델을 고정하거나 더 작은 모델로 빠르고 저렴한 에이전트 구성 가능.

### 컨텍스트 윈도우

컨텍스트 윈도우는 세션 동안 Claude가 사용할 수 있는 정보 총량이다. **턴 사이에 리셋되지 않고 누적**된다: 시스템 프롬프트, 도구 정의, 대화 이력, 도구 입력·출력. 턴 간 동일하게 유지되는 내용(시스템 프롬프트, 도구 정의, CLAUDE.md)은 자동 [prompt cache](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)되어 반복 prefix의 비용·latency를 줄인다. 자세한 컨텍스트 관리는 [[03 메모리와 컨텍스트]].

**무엇이 컨텍스트를 소비하나:**

| 출처 | 로드 시점 | 영향 |
|------|----------|------|
| 시스템 프롬프트 | 매 요청 | 작은 고정 비용 |
| CLAUDE.md | 세션 시작(`settingSources` 통해) | 매 요청에 전체 포함되나 prompt-cache로 첫 요청만 full cost |
| 도구 정의 | 매 요청; MCP 스키마는 기본 deferred | 내장 도구 스키마는 매 요청 로드. tool search가 MCP 스키마를 기본 지연 로드 |
| 대화 이력 | 턴마다 누적 | 프롬프트·응답·도구 입출력으로 증가 |
| 스킬 설명 | 세션 시작(setting source) | 짧은 요약만; 전체는 호출 시 로드 |

큰 도구 출력(큰 파일 읽기, verbose 명령)은 한 턴에 수천 토큰을 쓸 수 있고, 컨텍스트는 누적되므로 도구 호출이 많은 긴 세션은 훨씬 더 많은 컨텍스트를 쌓는다.

#### 자동 컴팩션 (automatic compaction)

컨텍스트가 한계에 가까워지면 SDK가 대화를 자동 압축한다: 오래된 이력을 요약해 공간을 비우고 최근 교환·핵심 결정은 유지. 이때 `type: "system"` + `subtype: "compact_boundary"` 메시지를 yield(Python은 `SystemMessage`, TS는 별도 `SDKCompactBoundaryMessage`).

컴팩션은 오래된 메시지를 요약으로 대체하므로 **초기 프롬프트의 구체적 지시가 보존되지 않을 수 있다**. 지속 규칙은 초기 프롬프트가 아니라 CLAUDE.md(매 요청 재주입)에 넣어라.

컴팩션 커스터마이즈:
- **CLAUDE.md 요약 지시:** 컴팩터가 CLAUDE.md를 다른 컨텍스트처럼 읽으므로, 요약 시 보존할 것을 적은 섹션을 둘 수 있다(헤더는 자유 형식, 의도로 매칭).
- **`PreCompact` 훅:** 컴팩션 전 커스텀 로직 실행(예: 전체 트랜스크립트 보관). `trigger` 필드(`manual`/`auto`) 수신.
- **수동 컴팩션:** 프롬프트 문자열로 `/compact`를 보내 온디맨드 트리거(SDK 입력으로 처리).

```markdown CLAUDE.md
# Summary instructions

When summarizing this conversation, always preserve:
- The current task objective and acceptance criteria
- File paths that have been read or modified
- Test results and error messages
- Decisions made and the reasoning behind them
```

#### 컨텍스트 효율 유지 전략

- **서브에이전트로 하위 작업 분리** — 각 서브에이전트는 새 대화로 시작(부모 턴을 보지 않음), 최종 응답만 도구 결과로 부모에 반환. 메인 컨텍스트는 전체 트랜스크립트가 아니라 요약만큼만 증가. (자세히 [[08 서브에이전트와 에이전트 팀]])
- **도구를 선별적으로** — 모든 도구 정의가 컨텍스트를 차지. `AgentDefinition`의 `tools` 필드로 서브에이전트를 최소 집합으로 스코핑.
- **MCP 서버 비용 주의** — MCP tool search가 기본으로 스키마를 지연 로드하지만, off거나 Vertex AI거나 비-퍼스트파티 `ANTHROPIC_BASE_URL` 뒤면 각 MCP 서버가 모든 도구 스키마를 매 요청에 추가.
- **일상 작업엔 낮은 effort** — 파일 읽기·디렉터리 나열만 하는 에이전트는 `"low"`로.

### 세션과 연속성

SDK 상호작용마다 세션이 생성/연속된다. `ResultMessage.session_id`(양쪽 SDK)에서 세션 ID를 캡처해 나중에 재개. TS SDK는 init `SystemMessage`의 직접 필드로도 노출, Python은 `SystemMessage.data`에 중첩.

재개하면 이전 턴의 전체 컨텍스트(읽은 파일·수행한 분석·취한 행동)가 복원된다. 세션을 **포크(fork)**해 원본을 수정하지 않고 다른 접근으로 분기할 수도 있다. (전체 가이드: sessions — [[24 Agent SDK — 고급과 레퍼런스]] / 개념은 [[03 메모리와 컨텍스트]])

> [!note] Python의 ClaudeSDKClient
> Python에서 `ClaudeSDKClient`는 여러 호출에 걸쳐 세션 ID를 자동 처리한다.

### 결과 처리 (handle the result)

루프 종료 시 `ResultMessage`가 무슨 일이 있었는지 알려준다. `subtype`(양쪽 SDK)이 종료 상태 확인의 1차 수단:

| Result subtype | 의미 | `result` 필드 |
|----------------|------|:------------:|
| `success` | 정상 완료 | 있음 |
| `error_max_turns` | `maxTurns` 한도 도달 | 없음 |
| `error_max_budget_usd` | `maxBudgetUsd` 한도 도달 | 없음 |
| `error_during_execution` | 루프 중 에러(API 실패, 요청 취소 등) | 없음 |
| `error_max_structured_output_retries` | structured output 검증이 재시도 한도 후 실패 | 없음 |

`result` 필드(최종 텍스트)는 `success`에서만 존재하므로 **항상 subtype 먼저 확인**. 모든 subtype은 `total_cost_usd`·`usage`·`num_turns`·`session_id`를 가져 에러 후에도 비용 추적·재개 가능. Python에서 `total_cost_usd`·`usage`는 optional 타입이라 일부 에러 경로에서 `None`일 수 있으니 포맷 전 가드.

`stop_reason` 필드(TS `string | null`, Python `str | None`)는 최종 턴에서 모델이 멈춘 이유: `end_turn`(정상), `max_tokens`(출력 토큰 한도), `refusal`(요청 거절). refusal 감지는 `stop_reason == "refusal"` 체크.

### 종합 예시 — 실패 테스트 수정 에이전트

이 페이지의 핵심 개념을 한 에이전트로 결합: 자동 승인 도구 + 프로젝트 설정 + 턴·effort 안전 한도, 그리고 세션 ID 캡처와 결과·비용 처리.

```python Python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async def run_agent():
    session_id = None
    async for message in query(
        prompt="Find and fix the bug causing test failures in the auth module",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Bash", "Glob", "Grep"],  # 여기 나열하면 자동 승인
            setting_sources=["project"],   # 현재 디렉터리에서 CLAUDE.md, skills, hooks 로드
            max_turns=30,                  # 폭주 세션 방지
            effort="high",                 # 복잡한 디버깅에 철저한 추론
        ),
    ):
        if isinstance(message, ResultMessage):
            session_id = message.session_id
            if message.subtype == "success":
                print(f"Done: {message.result}")
            elif message.subtype == "error_max_turns":
                print(f"Hit turn limit. Resume session {session_id} to continue.")
            elif message.subtype == "error_max_budget_usd":
                print("Hit budget limit.")
            else:
                print(f"Stopped: {message.subtype}")
            if message.total_cost_usd is not None:
                print(f"Cost: ${message.total_cost_usd:.4f}")

asyncio.run(run_agent())
```

### 훅 (루프 안에서의 위치)

[[09 훅]]은 루프 특정 지점에서 발화하는 콜백이다. 자주 쓰는 것:

| Hook | 발화 시점 | 용도 |
|------|----------|------|
| `PreToolUse` | 도구 실행 전 | 입력 검증, 위험 명령 차단 |
| `PostToolUse` | 도구 반환 후 | 출력 감사, 부수 효과 트리거 |
| `UserPromptSubmit` | 프롬프트 전송 시 | 프롬프트에 추가 컨텍스트 주입 |
| `Stop` | 에이전트 종료 시 | 결과 검증, 세션 상태 저장 |
| `SubagentStart` / `SubagentStop` | 서브에이전트 스폰/완료 | 병렬 작업 결과 추적·집계 |
| `PreCompact` | 컨텍스트 컴팩션 전 | 요약 전 전체 트랜스크립트 보관 |

훅은 에이전트 컨텍스트 윈도우가 아니라 **애플리케이션 프로세스에서 실행**되므로 컨텍스트를 소비하지 않는다. `PreToolUse` 훅이 도구 호출을 거부하면 실행이 막히고 Claude는 거부 메시지를 받는다. 위 6개 이벤트는 양쪽 SDK 지원, TS SDK는 추가 이벤트 지원.

---

## 4. SDK에서 Claude Code 기능 쓰기 (claude-code-features)

Agent SDK는 Claude Code와 같은 기반 위에 있으므로 동일한 **파일시스템 기반 기능**(프로젝트 지시 CLAUDE.md·rules, 스킬, 훅 등)을 쓸 수 있다.

`settingSources`를 생략하면 `query()`는 CLI와 같은 파일시스템 설정(user·project·local 설정, CLAUDE.md, `.claude/`의 skills·agents·commands)을 읽는다. 격리하려면 `settingSources: []`를 넘겨 프로그래밍으로 구성한 것만 쓰게 한다. **단, managed policy 설정과 글로벌 `~/.claude.json`은 이 옵션과 무관하게 읽힌다.**

### settingSources로 파일시스템 설정 제어

`setting_sources`(Python) / `settingSources`(TS)는 어떤 파일시스템 설정을 로드할지 제어한다. 명시 리스트로 특정 소스만 opt-in, 빈 배열로 user·project·local 비활성화.

```python Python
async for message in query(
    prompt="Help me refactor the auth module",
    options=ClaudeAgentOptions(
        setting_sources=["user", "project"],  # ~/.claude/ + ./.claude/
        allowed_tools=["Read", "Edit", "Bash"],
    ),
):
    ...
```

각 소스가 로드하는 것 (`<cwd>`는 `cwd` 옵션으로 넘긴 작업 디렉터리, 미설정 시 프로세스 현재 디렉터리):

| Source | 로드 대상 | 위치 |
|--------|----------|------|
| `"project"` | 프로젝트 CLAUDE.md, `.claude/rules/*.md`, 프로젝트 skills·hooks, 프로젝트 `settings.json` | `settings.json`·hooks는 `<cwd>/.claude/`; CLAUDE.md·rules는 `<cwd>`와 모든 부모 디렉터리; skills는 `<cwd>`와 리포지토리 루트까지의 모든 부모 |
| `"user"` | 유저 CLAUDE.md, `~/.claude/rules/*.md`, 유저 skills·설정 | `~/.claude/` |
| `"local"` | CLAUDE.local.md, `.claude/settings.local.json` | `settings.local.json`은 `<cwd>/.claude/`; CLAUDE.local.md는 `<cwd>`와 모든 부모 |

`settingSources` 생략 = `["user", "project", "local"]`. `cwd` 옵션이 프로젝트 레벨 입력을 찾는 위치를 결정한다: CLAUDE.md·rules는 `<cwd>`와 모든 부모에서, skills는 `<cwd>`와 리포 루트까지 부모에서, 프로젝트 `settings.json`·hooks는 **`<cwd>/.claude/`에서만**(부모 fallback 없음) 로드.

#### settingSources가 제어하지 않는 것

| 입력 | 동작 | 비활성화 방법 |
|------|------|--------------|
| Managed policy 설정 | 호스트에 있으면 항상 로드 | managed 설정 파일 제거 |
| `~/.claude.json` 글로벌 config | 항상 읽힘 | `env`의 `CLAUDE_CONFIG_DIR`로 재배치 |
| `~/.claude/projects/<project>/memory/`의 auto memory | 기본으로 시스템 프롬프트에 로드 | settings에 `autoMemoryEnabled: false`, 또는 `env`에 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` |
| claude.ai MCP 커넥터 | 활성 인증이 claude.ai 구독이면 로드. `mcpServers: {}`로는 억제 안 됨 | `strictMcpConfig: true`, 또는 `env`에 `ENABLE_CLAUDEAI_MCP_SERVERS=false` |

> [!warning] 멀티테넌트 격리
> 기본 `query()` 옵션을 멀티테넌트 격리에 의존하지 마라. 위 입력들이 `settingSources`와 무관하게 읽히므로 SDK 프로세스가 호스트 레벨 config와 디렉터리별 메모리를 주울 수 있다. 멀티테넌트 배포는 테넌트마다 별도 파일시스템에서 실행하고 `settingSources: []` + `env`에 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`을 설정하라. (보안 배포는 [[18 보안과 샌드박스]])

### 프로젝트 지시 (CLAUDE.md와 rules)

`CLAUDE.md`와 `.claude/rules/*.md`는 코딩 컨벤션·빌드 명령·아키텍처 결정 등 프로젝트의 지속 컨텍스트를 준다. `settingSources`에 `"project"`가 포함되면 세션 시작 시 컨텍스트에 로드되어, 매 프롬프트에 반복하지 않아도 컨벤션을 따른다. (CLAUDE.md 구조화는 [[03 메모리와 컨텍스트]])

**CLAUDE.md 로드 위치:**

| 레벨 | 위치 | 로드 시점 |
|------|------|----------|
| Project (root) | `<cwd>/CLAUDE.md` 또는 `<cwd>/.claude/CLAUDE.md` | `"project"` 포함 시 |
| Project rules | `<cwd>/.claude/rules/*.md` 및 모든 부모의 `.claude/rules/*.md` | `"project"` 포함 시 |
| Project (parent dirs) | `cwd` 상위 디렉터리들의 CLAUDE.md | `"project"` 포함, 세션 시작 |
| Project (child dirs) | `cwd` 하위 디렉터리들의 CLAUDE.md | `"project"` 포함, 해당 서브트리 파일 읽을 때 온디맨드 |
| Local | `<cwd>/CLAUDE.local.md` 및 모든 부모 | `"local"` 포함 시 |
| User | `~/.claude/CLAUDE.md` | `"user"` 포함 시 |
| User rules | `~/.claude/rules/*.md` | `"user"` 포함 시 |

모든 레벨은 **누적(additive)**: project와 user CLAUDE.md가 둘 다 있으면 둘 다 본다. 레벨 간 강한 우선순위 규칙은 없으니 충돌하는 규칙을 피하거나 더 구체적인 파일에 우선순위를 명시하라("이 프로젝트 지시는 충돌하는 유저 레벨 기본값을 오버라이드한다").

> [!tip] CLAUDE.md 없이 컨텍스트 주입
> `systemPrompt`로 직접 컨텍스트를 주입할 수도 있다(modifying-system-prompts — [[23 Agent SDK — 핵심 기능]]). 인터랙티브 Claude Code 세션과 SDK 에이전트가 같은 컨텍스트를 공유하길 원할 때 CLAUDE.md를 쓴다.

### 스킬 (Skills)

스킬은 전문 지식과 호출 가능한 워크플로우를 주는 마크다운 파일이다. 매 세션 로드되는 CLAUDE.md와 달리 **온디맨드 로드**: 시작 시 스킬 설명만 받고 관련될 때 전체 내용을 로드. (전체는 [[07 스킬]])

스킬은 `settingSources`를 통해 파일시스템에서 발견된다. `query()`의 `skills` 옵션을 생략하면 발견된 user·project 스킬이 활성화되고 Skill 도구가 사용 가능(CLI 동작과 일치). 제어하려면 `skills`를 `"all"`, 스킬명 리스트, 또는 `[]`(전부 비활성)로 전달. `skills` 설정 시 SDK가 Skill 도구를 `allowedTools`에 자동 추가. 명시적 `tools` 리스트도 넘기면 그 리스트에 `"Skill"`을 포함해야 Claude가 스킬을 호출할 수 있다.

```python Python
async for message in query(
    prompt="Review this PR using our code review checklist",
    options=ClaudeAgentOptions(
        setting_sources=["user", "project"],
        skills="all",
        allowed_tools=["Read", "Grep", "Glob"],
    ),
):
    ...
```

> [!note] 스킬은 파일시스템 아티팩트로만
> 스킬은 `.claude/skills/<name>/SKILL.md`로 생성해야 한다. SDK에는 스킬을 프로그래밍으로 등록하는 API가 없다.

### 훅 (두 방식 병행)

SDK는 훅을 두 방식으로 정의하며 나란히 실행된다:

- **파일시스템 훅:** `settings.json`에 정의된 셸 명령. `settingSources`가 관련 소스를 포함할 때 로드. 인터랙티브 Claude Code 세션과 같은 훅.
- **프로그래밍 훅:** `query()`에 직접 전달하는 콜백 함수. 애플리케이션 프로세스에서 실행되며 구조화된 결정을 반환.

둘 다 같은 훅 라이프사이클에 실행된다. 프로젝트 `.claude/settings.json`에 이미 훅이 있고 `settingSources: ["project"]`를 설정하면 그 훅들이 추가 설정 없이 SDK에서 자동 실행된다.

훅 콜백은 도구 입력을 받고 결정 dict를 반환한다. `{}` 반환은 도구 진행 허용. 차단하려면 `permissionDecision: "deny"`와 `permissionDecisionReason`을 가진 `hookSpecificOutput` 객체를 반환(이유가 Claude에 도구 결과로 전달). `PreToolUse`의 top-level `decision`·`reason` 필드는 deprecated.

```python Python
async def audit_bash(input_data, tool_use_id, context):
    command = input_data.get("tool_input", {}).get("command", "")
    if "rm -rf" in command:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Destructive command blocked",
            }
        }
    return {}  # 빈 dict: 도구 진행 허용

async for message in query(
    prompt="Refactor the auth module",
    options=ClaudeAgentOptions(
        setting_sources=["project"],  # .claude/settings.json 훅 로드
        hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[audit_bash])]},
    ),
):
    ...
```

```typescript TypeScript
const auditBash = async (input: HookInput): Promise<HookJSONOutput> => {
  if (input.hook_event_name !== "PreToolUse") return {};
  const toolInput = input.tool_input as { command?: string };
  if (toolInput.command?.includes("rm -rf")) {
    return {
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: "Destructive command blocked",
      },
    };
  }
  return {};
};
```

**언제 어느 훅 타입:**

| 타입 | 적합 |
|------|------|
| **파일시스템** (`settings.json`) | CLI와 SDK 세션 간 훅 공유. `"command"`(셸 스크립트), `"http"`(엔드포인트 POST), `"mcp_tool"`(MCP 서버 도구 호출), `"prompt"`(LLM이 프롬프트 평가), `"agent"`(검증 에이전트 스폰) 지원. 메인 에이전트와 모든 서브에이전트에서 발화 |
| **프로그래밍** (`query()` 콜백) | 앱 특화 로직, 구조화된 결정, 인프로세스 통합. 서브에이전트 안에서도 발화하며 콜백이 `agent_id`·`agent_type`를 받아 구분 |

> [!note] TS 추가 훅 이벤트
> TypeScript SDK는 Python을 넘어 `SessionStart`, `SessionEnd`, `TeammateIdle`, `TaskCompleted` 등 추가 이벤트를 지원한다.

### 어떤 기능을 쓸까

| 하고 싶은 것 | 사용 | SDK 표면 |
|-------------|------|----------|
| 에이전트가 항상 따르는 프로젝트 컨벤션 | CLAUDE.md | `settingSources: ["project"]`가 자동 로드 |
| 관련될 때 로드하는 참조 자료 | Skills | `settingSources` + `skills` |
| 재사용 워크플로우(deploy·review·release) | User-invocable skills | `settingSources` + `skills` |
| 격리된 하위 작업을 새 컨텍스트에 위임 | Subagents | `agents` + `allowedTools: ["Agent"]` |
| 공유 태스크 리스트로 여러 Claude Code 인스턴스 조율 | Agent teams | SDK 옵션으로 직접 구성 안 됨. 한 세션이 팀 리드 역할을 하는 **CLI 기능** |
| 도구 호출에 결정적 로직(감사·차단·변형) | Hooks | `hooks` 콜백, 또는 `settingSources`로 로드한 셸 스크립트 |
| 외부 서비스에 구조화된 도구 접근 | MCP | `mcpServers` |

> [!tip] Subagents vs Agent teams
> 서브에이전트는 일시적·격리적(새 대화, 단일 작업, 요약을 부모에 반환). Agent teams는 태스크 리스트를 공유하고 서로 직접 메시지하는 여러 독립 Claude Code 인스턴스를 조율하는 **CLI 기능**이다. ([[08 서브에이전트와 에이전트 팀]])

활성화하는 모든 기능은 컨텍스트 윈도우에 더해진다. 기능별 비용은 [[19 비용과 성능]] 참고.

---

## 5. Claude Agent SDK로 마이그레이션 (migration-guide)

기존 **Claude Code SDK**가 **Claude Agent SDK**로 이름이 바뀌고 문서가 재구성됐다. 코딩 작업을 넘어 모든 종류의 AI 에이전트를 만드는 더 넓은 역량을 반영한 변경이다.

### 무엇이 바뀌었나

| 측면 | 이전(Old) | 이후(New) |
|------|----------|----------|
| 패키지명 (TS/JS) | `@anthropic-ai/claude-code` | `@anthropic-ai/claude-agent-sdk` |
| Python 패키지 | `claude-code-sdk` | `claude-agent-sdk` |
| 문서 위치 | Claude Code docs | API Guide → Agent SDK 섹션 |

### 마이그레이션 단계

**TypeScript/JavaScript:**

```bash
npm uninstall @anthropic-ai/claude-code
npm install @anthropic-ai/claude-agent-sdk
```

```typescript
// Before
import { query, tool, createSdkMcpServer } from "@anthropic-ai/claude-code";
// After
import { query, tool, createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";
```

`package.json` 의존성도 `@anthropic-ai/claude-code: ^0.0.42` → `@anthropic-ai/claude-agent-sdk: ^0.2.0`로. 그게 전부 — 다른 코드 변경 불필요.

**Python:**

```bash
pip uninstall claude-code-sdk
pip install claude-agent-sdk
```

```python
# Before
from claude_code_sdk import query, ClaudeCodeOptions
options = ClaudeCodeOptions(model="claude-opus-4-7")
# After
from claude_agent_sdk import query, ClaudeAgentOptions
options = ClaudeAgentOptions(model="claude-opus-4-7")
```

### Breaking changes (v0.1.0)

> [!warning] v0.1.0 호환성 깨짐
> 격리와 명시적 설정을 개선하기 위해 Claude Agent SDK v0.1.0은 Claude Code SDK에서 넘어오는 사용자에게 breaking change를 도입했다. 마이그레이션 전 이 섹션을 주의 깊게 검토하라.

**1. Python: `ClaudeCodeOptions` → `ClaudeAgentOptions`** — 타입명이 "Claude Agent SDK" 브랜딩과 일관되도록 변경.

**2. 시스템 프롬프트가 더 이상 기본값 아님** — SDK가 Claude Code의 시스템 프롬프트를 기본으로 쓰지 않는다. 이전 동작을 원하면 preset을 명시:

```typescript
// 이전 동작 = Claude Code preset
const result = query({
  prompt: "Hello",
  options: { systemPrompt: { type: "preset", preset: "claude_code" } }
});
// 또는 커스텀
const result = query({
  prompt: "Hello",
  options: { systemPrompt: "You are a helpful coding assistant" }
});
```

```python
async for message in query(
    prompt="Hello",
    options=ClaudeAgentOptions(
        system_prompt={"type": "preset", "preset": "claude_code"}
    ),
):
    print(message)
```

→ SDK 앱에 더 나은 제어·격리 제공. Claude Code의 CLI 중심 지시를 상속하지 않고 커스텀 동작 에이전트를 만들 수 있다.

**3. Settings sources 기본값** — v0.1.0에서 잠깐 바뀌었다가 되돌려졌으므로 마이그레이션 조치 불필요. **현재 동작:** `settingSources` 생략 시 user·project·local 파일시스템 설정을 로드(CLI와 일치). 파일시스템 설정과 격리하려면 빈 배열을 넘긴다.

```python
options=ClaudeAgentOptions(setting_sources=[])          # 파일시스템 설정 미로드
options=ClaudeAgentOptions(setting_sources=["project"]) # 프로젝트만
```

> [!note] 버전 주의
> Python SDK 0.1.59 이하는 빈 리스트를 옵션 생략과 동일하게 취급했으니 `setting_sources=[]`에 의존하기 전 업그레이드하라. CI/CD·배포 앱·테스트 환경·멀티테넌트 시스템에서 로컬 커스터마이즈가 새지 않도록 격리가 특히 중요하다.

### 왜 이름을 바꿨나

Claude Code SDK는 원래 코딩 작업용이었지만 모든 종류의 AI 에이전트를 만드는 강력한 프레임워크로 진화했다. "Claude Agent SDK"라는 새 이름이 다음을 더 잘 반영한다:
- 비즈니스 에이전트(법률 어시스턴트, 금융 어드바이저, 고객 지원)
- 전문 코딩 에이전트(SRE 봇, 보안 리뷰어, 코드 리뷰 에이전트)
- 도구 사용·MCP 통합을 활용한 도메인 무관 커스텀 에이전트

### 마이그레이션 도움말

문제 발생 시 — TS는 import가 모두 `@anthropic-ai/claude-agent-sdk`로 갱신됐는지, `package.json`이 새 패키지명인지, `npm install` 실행했는지 확인. Python은 import가 `claude_agent_sdk`인지, `requirements.txt`/`pyproject.toml`이 새 패키지명인지, `pip install claude-agent-sdk` 실행했는지 확인. (일반 트러블슈팅 [[25 트러블슈팅]], 버전 변경 이력 [[26 변경 이력과 용어집]])

---

## 다음 단계

- 핵심 기능(스트리밍, 시스템 프롬프트, custom tools, 사용자 입력/승인 등): [[23 Agent SDK — 핵심 기능]]
- 고급 주제와 Python/TypeScript API 레퍼런스, 호스팅·세션·보안 배포: [[24 Agent SDK — 고급과 레퍼런스]]
- 예제 에이전트: anthropics/claude-agent-sdk-demos (이메일 어시스턴트, 리서치 에이전트 등)

## 원본 문서

- https://code.claude.com/docs/en/agent-sdk/overview
- https://code.claude.com/docs/en/agent-sdk/quickstart
- https://code.claude.com/docs/en/agent-sdk/agent-loop
- https://code.claude.com/docs/en/agent-sdk/claude-code-features
- https://code.claude.com/docs/en/agent-sdk/migration-guide
