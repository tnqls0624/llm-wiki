---
title: 23 Agent SDK — 핵심 기능
updated: 2026-06-07
type: reference
sources: [agent-sdk/permissions, agent-sdk/sessions, agent-sdk/session-storage, agent-sdk/hooks, agent-sdk/mcp, agent-sdk/custom-tools, agent-sdk/subagents, agent-sdk/skills, agent-sdk/slash-commands, agent-sdk/plugins, agent-sdk/user-input, agent-sdk/todo-tracking, agent-sdk/tool-search, agent-sdk/file-checkpointing]
---

# 23 Agent SDK — 핵심 기능

Claude Agent SDK로 에이전트를 만들 때 필요한 **핵심 기능 레퍼런스**다. 권한 제어, 세션 영속화, 훅, MCP, 커스텀 도구, 서브에이전트, 스킬/명령/플러그인, 사용자 입력 처리, 할 일 추적, 도구 검색, 파일 체크포인트까지 다룬다. SDK 진입(설치·`query()` 기초)은 [[22 Agent SDK — 시작]], 전체 옵션/타입 레퍼런스는 [[24 Agent SDK — 고급과 레퍼런스]]를 참조하라. CLI/대화형 사용은 [[05 권한]] [[06 내장 도구 레퍼런스]] [[07 스킬]] [[08 서브에이전트와 에이전트 팀]] [[09 훅]] [[10 MCP]] [[11 플러그인]]에 정리돼 있고, 이 노트는 그것들을 **SDK 코드에서 프로그래밍적으로 다루는 관점**이다. 허브는 [[Claude]].

> 코드 예시의 식별자(옵션 키, 함수명, 도구명)는 원문 그대로 영어로 유지한다. Python은 보통 `snake_case`, TypeScript는 `camelCase`를 쓰며, 같은 개념이 두 SDK에서 이름만 다른 경우가 많으니 표를 함께 참고하라.

---

## 권한 제어 (permissions)

에이전트가 도구를 어떻게 쓸지를 **permission mode + allow/deny 규칙 + 훅 + `canUseTool` 콜백**의 조합으로 통제한다. 이 페이지는 모드와 규칙을 다루고, 런타임 대화형 승인 흐름은 아래 [사용자 입력](#사용자-입력-처리-user-input)에서 다룬다.

### 권한 평가 순서 (절대 순서)

도구 요청이 들어오면 SDK는 다음 순서로 평가한다. 이 순서를 이해하는 게 권한 설계의 핵심이다.

1. **Hooks** — 먼저 [훅](#훅-hooks)을 실행. 훅이 곧바로 deny할 수 있다. 단, 훅이 `allow`를 반환해도 아래 deny/ask 규칙은 그대로 평가된다.
2. **Deny 규칙** — `disallowed_tools` + `settings.json`의 deny 규칙. 매칭되면 `bypassPermissions` 모드에서도 차단된다. `Bash` 같은 **맨이름(bare-name) deny는 평가 전에 도구를 Claude의 컨텍스트에서 제거**하므로, 이 단계에서는 `Bash(rm *)` 같은 스코프 규칙만 검사된다.
3. **Permission mode** — 활성 모드 적용. `bypassPermissions`는 여기까지 온 걸 모두 승인, `acceptEdits`는 파일 작업을 승인, 나머지는 통과.
4. **Allow 규칙** — `allowed_tools` + settings.json allow 규칙. 매칭되면 승인.
5. **`canUseTool` 콜백** — 위에서 해결 안 된 것은 콜백으로 결정 요청. `dontAsk` 모드에서는 이 단계를 건너뛰고 **거부**한다.

### Allow / Deny 규칙

`allowed_tools`(TS: `allowedTools`)와 `disallowed_tools`(TS: `disallowedTools`)는 위 흐름의 allow/deny 리스트에 항목을 추가한다. allow는 승인에만 영향(없는 도구도 여전히 존재하며 모드로 통과), deny는 도구명이냐 스코프 패턴이냐에 따라 동작이 다르다.

| 옵션 | 효과 |
|---|---|
| `allowed_tools=["Read", "Grep"]` | `Read`/`Grep` 자동 승인. 미기재 도구는 그대로 존재하며 mode/`canUseTool`로 통과 |
| `disallowed_tools=["Bash"]` | `Bash` 도구 정의가 요청에서 **제거**됨. Claude가 도구를 보지도 못함 |
| `disallowed_tools=["Bash(rm *)"]` | `Bash`는 살아있고, `rm *` 매칭 호출만 모든 모드(`bypassPermissions` 포함)에서 거부 |

잠긴(locked-down) 에이전트는 `allowedTools` + `permissionMode: "dontAsk"` 조합이 정석이다. 기재한 도구만 승인, 나머지는 프롬프트 없이 즉시 거부.

```typescript
const options = {
  allowedTools: ["Read", "Glob", "Grep"],
  permissionMode: "dontAsk"
};
```

> [!warning] `allowed_tools`는 `bypassPermissions`를 제약하지 못한다
> `allowed_tools`는 기재한 도구를 사전승인할 뿐이다. 미기재 도구는 어떤 allow 규칙에도 안 걸리고 모드로 통과하는데, `bypassPermissions`는 거기서 전부 승인한다. 즉 `allowed_tools=["Read"]` + `bypassPermissions`여도 `Bash`/`Write`/`Edit`까지 모두 승인된다. `bypassPermissions`를 쓰되 특정 도구를 막으려면 `disallowed_tools`를 써라.

`.claude/settings.json`에 allow/deny/ask 규칙을 선언적으로 둘 수도 있다. 이 규칙은 `project` setting source가 활성일 때 읽힌다(기본 `query()`는 활성). `setting_sources`를 명시했다면 `"project"`를 포함해야 적용된다. 규칙 문법은 [[04 설정]]·[[05 권한]] 참조.

### 권한 모드 (permission modes)

| 모드 | 설명 | 도구 동작 |
|---|---|---|
| `default` | 표준 | 자동 승인 없음. 미매칭 도구는 `canUseTool` 콜백 트리거 |
| `dontAsk` | 프롬프트 대신 거부 | 사전승인 안 된 건 거부. `canUseTool` 호출 안 됨 |
| `acceptEdits` | 파일 편집 자동 수락 | 파일 편집 + 파일시스템 명령(`mkdir`, `rm`, `mv` 등) 자동 승인 |
| `bypassPermissions` | 모든 권한 검사 우회 | 모든 도구가 프롬프트 없이 실행 (주의) |
| `plan` | 계획 모드 | 읽기 전용 도구만. 소스 편집 없이 분석·계획 |
| `auto` (TS 전용) | 모델 분류 승인 | 모델 분류기가 각 호출을 승인/거부 |

> [!warning] 서브에이전트 상속
> 부모가 `bypassPermissions`/`acceptEdits`/`auto`를 쓰면 **모든 서브에이전트가 그 모드를 상속하며 서브에이전트별로 재정의 불가**다. 서브에이전트는 부모와 다른 시스템 프롬프트로 더 느슨하게 동작할 수 있어, `bypassPermissions` 상속은 승인 프롬프트 없는 완전 자율 시스템 접근을 부여하는 셈이다.

#### 모드 설정 (쿼리 시작 / 스트리밍 중 동적 변경)

쿼리 시작 시 `permission_mode`(Py) / `permissionMode`(TS)로 지정한다. 스트리밍 중에는 `set_permission_mode()`(Py) / `setPermissionMode()`(TS)로 즉시 변경 가능 — 처음엔 빡빡하게 시작하고 신뢰가 쌓이면 `acceptEdits`로 완화하는 패턴에 유용.

```python
async with ClaudeSDKClient(options=ClaudeAgentOptions(permission_mode="default")) as client:
    await client.query("Help me refactor this code")
    await client.set_permission_mode("acceptEdits")  # 세션 중 변경
    async for message in client.receive_response():
        ...
```

- **`acceptEdits`**: 파일 편집(Edit, Write) + 파일시스템 명령(`mkdir touch rm rmdir mv cp sed`) 자동 승인. 단, 작업 디렉터리 또는 `additionalDirectories` 안쪽 경로에만 적용. 바깥 경로·보호 경로는 여전히 프롬프트.
- **`dontAsk`**: 모든 프롬프트를 거부로 전환. 헤드리스 에이전트에서 고정된 도구 표면을 강제하고 싶을 때.
- **`bypassPermissions`**: 전부 자동 승인. 단 deny 규칙·명시적 ask 규칙·훅은 모드 검사 전에 평가되어 여전히 차단 가능.
- **`plan`**: 읽기 전용. 탐색·계획만 하고 소스 수정 안 함. 계획 확정 전 `AskUserQuestion`으로 요구사항을 명확히 할 수 있다.

---

## 세션 (sessions)

세션은 SDK가 작업하며 누적하는 **대화 이력**(프롬프트·모든 도구 호출/결과·응답)이다. 디스크에 자동 기록되어 나중에 돌아올 수 있다. 세션은 **대화를 영속화하는 것이지 파일시스템 스냅샷이 아니다** — 파일 변경을 되돌리려면 [파일 체크포인트](#파일-체크포인트-file-checkpointing)를 써라.

### 무엇을 쓸지 고르기

| 만드는 것 | 사용 |
|---|---|
| 일회성 작업 (단일 프롬프트, 후속 없음) | 추가 작업 불필요. `query()` 한 번 |
| 한 프로세스 내 멀티턴 채팅 | `ClaudeSDKClient`(Py) 또는 `continue: true`(TS). ID 관리 불필요 |
| 프로세스 재시작 후 이어가기 | `continue_conversation=True`(Py) / `continue: true`(TS). 디렉터리 최신 세션 재개 |
| 특정 과거 세션 재개 (최신 아님) | 세션 ID 캡처 후 `resume`에 전달 |
| 원본 유지하며 다른 접근 시도 | fork |
| 디스크에 아무것도 안 쓰는 stateless (TS 전용) | `persistSession: false`. 메모리에만 존재. Python은 항상 디스크 영속 |

**Continue vs Resume vs Fork**: continue는 현재 디렉터리의 최신 세션을 찾는다(추적 불필요). resume은 특정 세션 ID를 받는다(멀티유저 앱 등 다수 세션일 때 필요). fork는 원본 이력의 사본으로 시작하는 새 세션을 만든다 — 원본은 그대로 유지되어 두 갈래를 독립적으로 재개 가능.

### 자동 세션 관리

- **Python `ClaudeSDKClient`**: 세션 ID를 내부 처리. 같은 client 인스턴스의 매 `client.query()`가 같은 세션을 자동 이어간다. async context manager로 쓰거나 `connect()`/`disconnect()` 수동 호출.
- **TypeScript `continue: true`**: 세션 보유 객체가 없으므로 각 후속 `query()`에 `continue: true`를 넘기면 디스크 최신 세션을 재개.

> 실험적 V2 세션 API(`createSession()` + send/stream)는 TypeScript Agent SDK 0.3.142에서 제거됨. `query()` + 이 페이지의 세션 옵션을 쓰라.

### 세션 ID 캡처 / Resume / Fork

세션 ID는 결과 메시지의 `session_id` 필드에서 읽는다(`ResultMessage`(Py) / `SDKResultMessage`(TS), 성공/에러 무관하게 존재). TS는 init `SystemMessage`의 직접 필드로도 일찍 얻을 수 있고, Python은 `SystemMessage.data` 안에 중첩된다.

```python
# resume — 특정 세션 ID로 이어가기 (이전 분석 컨텍스트 보유)
async for message in query(
    prompt="Now implement the refactoring you suggested",
    options=ClaudeAgentOptions(resume=session_id,
        allowed_tools=["Read", "Edit", "Write", "Glob", "Grep"]),
):
    ...
```

```python
# fork — 분기 (forked_id가 새 ID, 원본 session_id는 불변)
async for message in query(
    prompt="Instead of JWT, implement OAuth2 for the auth module",
    options=ClaudeAgentOptions(resume=session_id, fork_session=True),  # TS: forkSession: true
):
    if isinstance(message, ResultMessage):
        forked_id = message.session_id
```

> [!tip] resume이 빈 세션을 돌려줄 때
> 가장 흔한 원인은 `cwd` 불일치. 세션은 `~/.claude/projects/<encoded-cwd>/*.jsonl`에 저장되며 `<encoded-cwd>`는 절대 작업 디렉터리의 모든 비영숫자 문자를 `-`로 치환한 것(`/Users/me/proj` → `-Users-me-proj`). 다른 디렉터리에서 resume하면 SDK가 엉뚱한 곳을 본다. 세션 파일이 현재 머신에 존재해야 함도 필수.

### 호스트 간 재개

세션 파일은 생성한 머신에 로컬이다. 다른 호스트(CI 워커, 임시 컨테이너, 서버리스)에서 재개하려면 (1) `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`을 동일 경로로 옮기거나(`cwd` 일치 필수), (2) 결과만 애플리케이션 상태로 캡처해 새 세션 프롬프트에 넣는다(더 견고). 공유 스토리지로 미러링하려면 [세션 스토리지](#세션-스토리지-session-storage)의 `SessionStore` 어댑터를 사용.

세션 열거/조회/변경 함수: `list_sessions()`/`listSessions()`, `get_session_messages()`/`getSessionMessages()`, `get_session_info()`/`getSessionInfo()`, `rename_session()`/`renameSession()`, `tag_session()`/`tagSession()`.

---

## 세션 스토리지 (session-storage)

기본적으로 SDK는 세션 transcript를 로컬 `~/.claude/projects/`의 JSONL로 쓴다. `SessionStore` 어댑터로 이를 S3·Redis·DB 등 자체 백엔드에 **미러링**하면, 한 호스트에서 만든 세션을 다른 호스트에서 재개할 수 있다. 멀티호스트 배포, 내구성(임시 컨테이너 대비), 컴플라이언스/감사(자체 보존·암호화·접근통제)에 유용.

### `SessionStore` 인터페이스

필수 메서드 `append`·`load`, 선택 메서드 3개로 구성된다.

```typescript
type SessionKey = { projectKey: string; sessionId: string; subpath?: string };

type SessionStore = {
  append(key: SessionKey, entries: SessionStoreEntry[]): Promise<void>;   // 필수
  load(key: SessionKey): Promise<SessionStoreEntry[] | null>;             // 필수
  listSessions?(projectKey: string): Promise<Array<{ sessionId: string; mtime: number }>>;
  delete?(key: SessionKey): Promise<void>;
  listSubkeys?(key: { projectKey: string; sessionId: string }): Promise<string[]>;
};
```

| 메서드 | 필수 | 호출 시점 |
|---|---|---|
| `append` | 예 | 로컬에 transcript 배치가 쓰인 직후. 엔트리는 JSON-safe 객체 |
| `load` | 예 | `resume` 시 서브프로세스 spawn 직전 1회. 모르는 세션이면 `null` 반환 |
| `listSessions` | 아니오 | `listSessions({sessionStore})` 및 `continue: true`. 미구현 시 throw |
| `delete` | 아니오 | `deleteSession({sessionStore})`. main 키 삭제는 모든 subkey로 cascade해야 함. 미구현 시 no-op(append-only 백엔드에 적합) |
| `listSubkeys` | 아니오 | resume 시 서브에이전트 transcript 발견용. 미구현 시 main transcript만 복원 |

`SessionKey`는 transcript 하나를 가리킨다. `projectKey`는 작업 디렉터리의 안정·파일시스템 안전 인코딩, `sessionId`는 세션 UUID, `subpath`는 서브에이전트/사이드카 파일일 때 설정(예: `subagents/agent-<id>`, 불투명 키 접미사로 취급).

### 빠른 시작 (`InMemorySessionStore`)

개발·테스트용 `InMemorySessionStore`가 내장돼 있다. 같은 store 인스턴스를 두 `query()`에 넘기고 두 번째에 `resume`을 주면 로컬 FS 대신 store에서 transcript를 로드한다.

```python
from claude_agent_sdk import query, ClaudeAgentOptions, InMemorySessionStore, ResultMessage
store = InMemorySessionStore()
# 1번째: session_store=store 로 미러링하며 session_id 캡처
# 2번째: ClaudeAgentOptions(session_store=store, resume=session_id) 로 재개
```

### 자체 어댑터 / 검증

`append`·`load`만 구현하면 기본 동작, 선택 메서드를 추가하면 그만큼 기능이 켜진다. `append`에 들어오는 엔트리는 `SessionStoreEntry`(불투명 JSON-safe)로, 순서대로 영속화하고 `load`에서 같은 순서로 반환해야 한다. **deep-equal이면 충분**하고 byte-equal 직렬화는 불필요(Postgres `jsonb`처럼 키 순서를 바꿔도 OK).

레퍼런스 어댑터는 TS 저장소 `examples/session-stores/`에 있다(npm 미배포, `src/`를 복사):

| 어댑터 | 백엔드 클라이언트 | 저장 모델 |
|---|---|---|
| `S3SessionStore` | `@aws-sdk/client-s3` | `append()`마다 JSONL part 파일 1개; `load()`가 list·sort·concat |
| `RedisSessionStore` | `ioredis` | transcript당 `RPUSH`/`LRANGE` 리스트 + 정렬셋 세션 인덱스 |
| `PostgresSessionStore` | `pg` | `jsonb` 테이블 엔트리당 1행, `BIGSERIAL` 정렬 |

검증: TS는 `examples/session-stores/shared/conformance.ts`를 복사, Python은 `from claude_agent_sdk.testing import run_session_store_conformance` 후 `await run_session_store_conformance(MyStore)`.

### 동작 노트 (중요)

- **Dual-write**: store는 대체가 아니라 미러. 서브프로세스가 항상 로컬 디스크에 먼저 쓰고 SDK가 각 배치를 `append()`로 포워딩. 로컬 사본을 임시로 하려면 `options.env`에서 `CLAUDE_CONFIG_DIR`을 temp로. **`sessionStore`는 `persistSession: false`와 조합 불가**(throw), **`enableFileCheckpointing`과도 조합 불가**(체크포인트 백업 blob은 로컬에만 기록되고 미러 안 됨).
- **미러 쓰기는 best-effort**: `append()` 실패/타임아웃 시 에러 로깅 + `{type:"system", subtype:"mirror_error"}` 메시지 emit, 쿼리는 계속. 재시도 없음 → store 데이터 손실 감지하려면 `mirror_error` 모니터링.
- **`getSessionMessages`는 post-compaction 체인 반환**: auto-compaction 후 이전 턴이 요약으로 대체되어, store에 raw 503 엔트리가 있어도 18 메시지만 반환될 수 있다. 전체 raw는 `store.load(key)` 직접 호출.
- **`forkSession`은 byte 복사 아님**: 소스를 읽어 모든 `sessionId`·메시지 UUID를 다시 쓴 뒤 새 키로 append.
- **서브에이전트 transcript**: `subpath: "subagents/agent-<id>"`로 미러. `listSubagents`/resume이 `listSubkeys` 필요.
- **보존(retention)**: SDK는 store에서 자동 삭제하지 않음. TTL·S3 라이프사이클·스케줄 정리는 어댑터 책임. 로컬은 `cleanupPeriodDays` 설정으로 독립 정리.

---

## 훅 (hooks)

훅은 에이전트 이벤트(도구 호출, 세션 시작, 실행 중단 등)에 반응해 사용자 코드를 실행하는 콜백이다. 위험한 작업 차단, 감사 로깅, 입출력 변환, 인간 승인 요구, 세션 라이프사이클 추적에 쓴다. 동작 흐름: 이벤트 발생 → SDK가 등록 훅 수집 → matcher로 필터 → 콜백 실행(이벤트 상세 수신) → 콜백이 결정 객체 반환(allow/deny/modify/inject).

### 사용 가능한 훅

| 이벤트 | Py | TS | 트리거 |
|---|---|---|---|
| `PreToolUse` | 예 | 예 | 도구 호출 요청 (차단/수정 가능) |
| `PostToolUse` | 예 | 예 | 도구 실행 결과 |
| `PostToolUseFailure` | 예 | 예 | 도구 실행 실패 |
| `PostToolBatch` | 아니오 | 예 | 도구 배치 전체 resolve, 다음 모델 호출 전 배치당 1회 |
| `UserPromptSubmit` | 예 | 예 | 사용자 프롬프트 제출 (컨텍스트 주입) |
| `MessageDisplay` | 아니오 | 예 | 텍스트 어시스턴트 메시지 완료, 메시지당 1회 (transcript 변경 없이 표시 텍스트만 가공) |
| `Stop` | 예 | 예 | 에이전트 실행 정지 |
| `SubagentStart` / `SubagentStop` | 예 | 예 | 서브에이전트 시작/완료 |
| `PreCompact` | 예 | 예 | 대화 compaction 요청 (요약 전 아카이브) |
| `PermissionRequest` | 예 | 예 | 권한 다이얼로그가 뜰 상황 (커스텀 권한 처리) |
| `SessionStart` / `SessionEnd` | 아니오 | 예 | 세션 초기화/종료 |
| `Notification` | 예 | 예 | 에이전트 상태 메시지 (Slack/PagerDuty 전달) |
| `Setup` | 아니오 | 예 | 세션 셋업/유지보수 |
| `TeammateIdle` / `TaskCompleted` / `ConfigChange` / `WorktreeCreate` / `WorktreeRemove` | 아니오 | 예 | (TS 전용) |

### 설정과 matcher

```python
options = ClaudeAgentOptions(
    hooks={"PreToolUse": [HookMatcher(matcher="Write|Edit", hooks=[my_callback])]}
)
```

`hooks`는 이벤트명을 키로, matcher 배열을 값으로 갖는다. matcher 비교 규칙(settings 파일과 동일):

- 문자·숫자·`_`·`|`만 포함 → **정확 문자열** 비교(`|`로 대안 구분). `Write|Edit`는 그 둘만.
- `*`/빈 문자열/생략 → 모든 발생 매칭.
- 그 외 문자 포함 → **정규식**. `^mcp__`는 모든 MCP 도구. `mcp__memory`는 정확 비교라 아무것도 안 맞음 → `mcp__memory__.*`를 써야 함.

| 옵션 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `matcher` | string | undefined | 이벤트 필터 필드 대상 패턴. 도구 훅은 **도구명만** 매칭(파일 경로 등 인자 아님) |
| `hooks` | HookCallback[] | — | 필수. 콜백 함수 배열 |
| `timeout` | number | 60 | 초 단위 타임아웃 |

> MCP 도구명: `mcp__<server>__<action>`. 서버명은 `mcpServers` 설정 키에서 옴.

### 콜백 입출력

콜백은 3개 인자를 받는다: **입력 데이터**(타입별 형태. 공통 `session_id`/`cwd`/`hook_event_name`, 서브에이전트 안에서는 `agent_id`/`agent_type`), **tool use ID**(Pre/PostToolUse 상관), **context**(TS는 `signal: AbortSignal`, Py는 예약).

반환 객체:
- **Top-level**: `systemMessage`(사용자에게 메시지 표시), `continue`(Py `continue_`, 이후 실행 여부).
- **`hookSpecificOutput`**: 현재 작업 제어. `PreToolUse`는 `permissionDecision`(`"allow"`/`"deny"`/`"ask"`/`"defer"`)·`permissionDecisionReason`·`updatedInput`. `"defer"`는 쿼리를 끝내고 나중에 재개. `PostToolUse`는 `additionalContext`(도구 결과에 정보 추가) 또는 `updatedToolOutput`(Claude가 보기 전 출력 교체, 모든 도구·양 SDK). `{}` 반환 = 변경 없이 허용.

> 우선순위: **deny > defer > ask > allow**. 어떤 훅이든 deny 반환하면 다른 훅과 무관하게 차단.

### 비동기 출력 (side-effect 전용)

로깅·웹훅처럼 에이전트 동작에 영향 안 주는 부수효과는 즉시 반환해 에이전트를 기다리게 하지 않는다.

```python
async def async_hook(input_data, tool_use_id, context):
    asyncio.create_task(send_to_logging_service(input_data))
    return {"async_": True, "asyncTimeout": 30000}   # TS: { async: true, asyncTimeout: 30000 }
```

### 패턴 예시

- **입력 수정**: `updatedInput`를 `hookSpecificOutput` 안에 넣고 `permissionDecision: "allow"`(또는 `"ask"`)도 함께. `"defer"`에선 무시됨. 원본 `tool_input`을 mutate하지 말고 새 객체 반환.
- **컨텍스트 추가 + 차단**: `permissionDecision: "deny"` + `permissionDecisionReason`(모델용) + `systemMessage`(사용자용).
- **읽기 전용 자동 승인**: `Read`/`Glob`/`Grep`에 `permissionDecision: "allow"`.
- **다중 훅 등록**: 한 이벤트에 매칭되는 모든 훅이 **병렬** 실행. 권한은 최대 제한 우선(하나라도 deny면 차단). 완료 순서 비결정적 → 각 훅은 독립적으로 작성.
- **다중도구 matcher**: `Write|Edit|Delete`(정확 리스트), `^mcp__`(정규식), matcher 생략(전부).
- **HTTP 요청/Slack 전달**: 훅 안에서 에러를 catch(전파 시 에이전트 중단 가능). `Notification` 훅은 `permission_prompt`/`idle_prompt`/`auth_success`/`elicitation_*` 등에 발화하며 `message`/`title` 필드 포함.

### 흔한 문제 해결

- **훅 미발화**: 이벤트명 대소문자(`PreToolUse`), matcher가 도구명과 정확 매칭, 올바른 이벤트 타입 아래. `max_turns` 도달 시 세션이 먼저 끝나 훅이 안 뜰 수 있음.
- **matcher 필터 안 됨**: matcher는 **도구명만** 매칭. 파일 경로는 콜백 안에서 `tool_input.file_path` 검사.
- **수정 입력 미적용**: `updatedInput`가 `hookSpecificOutput` 안에 있고 `hookEventName`/`permissionDecision: "allow"` 포함됐는지.
- **Python에 세션 훅 없음**: `SessionStart`/`SessionEnd`는 TS SDK 콜백으로만 등록 가능. Python은 settings 파일의 셸 명령 훅으로만(예: `setting_sources=["project"]`로 `.claude/settings.json` 로드).
- **서브에이전트 권한 반복/재귀 루프**: 서브에이전트는 부모 권한을 자동 상속하지 않음 → `PreToolUse` 훅으로 자동 승인하거나 권한 규칙. `UserPromptSubmit` 훅이 서브에이전트를 spawn하면 무한 루프 가능 → 서브에이전트 표시 체크·세션 상태 추적·top-level 한정.
- **`systemMessage` 미표시**: 기본적으로 SDK가 훅 출력을 메시지 스트림에 안 보냄 → `includeHookEvents`(Py `include_hook_events`) 설정. 모델에 전달하려면 `additionalContext`.

---

## MCP (mcp)

[Model Context Protocol](https://modelcontextprotocol.io)은 에이전트를 외부 도구·데이터에 연결하는 개방 표준이다. DB 조회, Slack/GitHub 같은 API 통합을 커스텀 도구 구현 없이 할 수 있다. MCP 서버는 로컬 프로세스, HTTP 연결, 또는 SDK 애플리케이션 내부 실행이 가능하다.

### 서버 추가

코드의 `mcpServers` 옵션 또는 프로젝트 루트의 `.mcp.json`(`project` setting source 활성 시 로드)으로 설정.

```typescript
options: {
  mcpServers: {
    "claude-code-docs": { type: "http", url: "https://code.claude.com/docs/mcp" }
  },
  allowedTools: ["mcp__claude-code-docs__*"]   // 와일드카드로 서버 전체 허용
}
```

```json
// .mcp.json
{ "mcpServers": { "filesystem": {
  "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/projects"]
}}}
```

### MCP 도구 허용

MCP 도구는 사용 전 명시적 권한이 필요하다. 명명 규칙: **`mcp__<server-name>__<tool-name>`** (서버 `github`의 `list_issues` → `mcp__github__list_issues`). `allowedTools`로 사전승인하며 와일드카드(`mcp__github__*`) 가능.

> [!note] MCP 접근은 모드보다 `allowedTools`를 선호
> `permissionMode: "acceptEdits"`는 MCP 도구를 자동 승인하지 **않는다**(파일 편집·파일시스템 Bash만). `bypassPermissions`는 MCP를 승인하지만 다른 안전 프롬프트도 다 끄므로 과하다. `allowedTools` 와일드카드는 원하는 MCP 서버만 정확히 허용.

서버가 주는 도구는 `system` init 메시지의 `mcp_servers`(또는 `message.mcp_servers`)로 확인.

### 전송 타입 (transport)

- **stdio**: 로컬 프로세스, stdin/stdout. 문서가 **실행 명령**(`npx ...`)을 주면 이걸 사용. `command`/`args`/`env`로 구성.
- **HTTP/SSE**: 클라우드 호스팅·원격 API. 문서가 **URL**을 주면 사용. `type: "sse"` 또는 `type: "http"`(streamable HTTP), `url`, `headers`. JSON 설정에서는 `"streamable-http"`가 `"http"`의 alias이나 프로그래밍 `mcpServers` 옵션은 `"http"`만 받음.
- **SDK MCP 서버**: 별도 프로세스 없이 코드 내 정의 → [커스텀 도구](#커스텀-도구-custom-tools).

### 인증

`env` 필드로 자격증명 전달(stdio). HTTP/SSE는 `headers`에 `Authorization: Bearer ...`. `.mcp.json`의 `${GITHUB_TOKEN}` 문법은 런타임에 환경변수 확장. OAuth2는 SDK가 자동 처리하지 않으나, 앱에서 플로우 완료 후 access token을 헤더로 전달 가능.

### 도구 검색 통합 / 에러 처리

MCP 도구가 많으면 정의가 컨텍스트를 잠식 → [도구 검색](#도구-검색-tool-search)이 기본 활성. `system`/`init` 메시지의 각 서버 `status` 필드로 연결 실패를 사전 감지(`status !== "connected"`). 결과 메시지 `subtype === "error_during_execution"`로 실행 실패 감지.

흔한 실패 원인: 환경변수 누락, 서버 미설치(`npx` 패키지/Node PATH), 잘못된 연결 문자열, 네트워크 문제. MCP SDK 기본 연결 타임아웃 60초.

---

## 커스텀 도구 (custom-tools)

SDK의 **in-process MCP 서버**로 자체 함수를 정의하면 Claude가 DB·외부 API·도메인 로직을 호출할 수 있다. 별도 프로세스가 아니라 애플리케이션 안에서 실행된다.

### 빠른 참조

| 하고 싶은 것 | 방법 |
|---|---|
| 도구 정의 | `@tool`(Py) / `tool()`(TS) — name·description·schema·handler |
| Claude에 등록 | `create_sdk_mcp_server`/`createSdkMcpServer`로 감싸 `mcpServers`에 전달 |
| 사전 승인 | allowed tools에 추가 |
| 내장 도구 제거 | `tools` 배열에 원하는 내장만 나열 |
| 병렬 호출 허용 | side-effect 없는 도구에 `readOnlyHint: true` |
| 루프 중단 없이 에러 처리 | throw 대신 `isError: true` 반환 |
| 이미지/파일 반환 | content 배열에 `image`/`resource` 블록 |
| 기계가독 JSON 반환 | `structuredContent` 설정 |
| 다수 도구로 스케일 | [도구 검색](#도구-검색-tool-search) |

### 도구 정의 (4부분)

- **Name**: 고유 식별자.
- **Description**: 무엇을 하는지(Claude가 호출 시점 판단).
- **Input schema**: TS는 항상 [Zod 스키마](https://zod.dev/)(handler `args` 자동 타입). Py는 `{"latitude": float}` 같은 dict(SDK가 JSON Schema로 변환) 또는 전체 JSON Schema dict(enum·범위·옵션·중첩 필요 시).
- **Handler**: async 함수. 반환은 `content`(필수, `"text"`/`"image"`/`"resource"` 블록 배열) + `structuredContent`(선택) + `isError`(선택).

```python
@tool("get_temperature", "Get the current temperature at a location",
      {"latitude": float, "longitude": float})
async def get_temperature(args):
    ...  # httpx로 fetch
    return {"content": [{"type": "text", "text": f"Temperature: {t}°F"}]}

weather_server = create_sdk_mcp_server(name="weather", version="1.0.0", tools=[get_temperature])
```

```typescript
const getTemperature = tool(
  "get_temperature", "Get the current temperature at a location",
  { latitude: z.number().describe("Latitude"), longitude: z.number().describe("Longitude") },
  async (args) => ({ content: [{ type: "text", text: `Temperature: ${t}°F` }] })
);
const weatherServer = createSdkMcpServer({ name: "weather", version: "1.0.0", tools: [getTemperature] });
```

> 옵션 파라미터: TS는 Zod 필드에 `.default()`. Py는 dict 스키마가 모든 키를 필수로 보므로 스키마에서 빼고 description에 언급한 뒤 handler에서 `args.get()`으로 읽음.

### 호출 / 다중 도구

`mcpServers`의 키가 `mcp__{server_name}__{tool_name}`의 `{server_name}`이 된다. `allowedTools`에 그 이름(또는 와일드카드 `mcp__weather__*`)을 나열해 프롬프트 없이 실행. 모든 도구는 매 턴 컨텍스트를 소비하므로 수십 개면 [도구 검색](#도구-검색-tool-search)을 고려.

### 도구 어노테이션 (annotations)

`tool()` 5번째 인자(TS) / `@tool`의 `annotations` 키워드(Py). 모두 Boolean 힌트이며 **메타데이터일 뿐 강제력 없음**(handler가 실제로 그렇게 동작하게 유지해야 함).

| 필드 | 기본 | 의미 |
|---|---|---|
| `readOnlyHint` | false | 환경 미변경. 다른 읽기 전용 도구와 **병렬 호출** 가능 여부 제어 |
| `destructiveHint` | true | 파괴적 업데이트 가능 (정보용) |
| `idempotentHint` | false | 동일 인자 반복 호출이 추가 효과 없음 (정보용) |
| `openWorldHint` | true | 프로세스 외부 시스템 접근 (정보용) |

### 도구 접근 제어 (availability vs permission)

`tools`/bare-name `disallowedTools`는 **availability**(Claude 컨텍스트에 보이는지) 변경, `allowedTools`/scoped `disallowedTools`는 **permission**(시도된 호출 승인 여부)만 변경.

| 옵션 | 레이어 | 효과 |
|---|---|---|
| `tools: ["Read", "Grep"]` | Availability | 나열한 내장만 컨텍스트에. MCP 도구는 영향 없음 |
| `tools: []` | Availability | 모든 내장 제거. MCP 도구만 사용 가능 |
| allowed tools | Permission | 나열 도구는 프롬프트 없이. 미나열도 권한 흐름 통과 |
| disallowed tools | 둘 다 | bare 이름은 컨텍스트 제거, scoped(`Bash(rm *)`)는 보이되 매칭만 거부 |

### 에러 처리 / 이미지·리소스 / 구조화 데이터

- **에러**: handler가 **uncaught 예외를 throw하면 에이전트 루프 중단**(query 실패). catch 후 `isError: true`(Py `"is_error": True`) 반환하면 루프 계속(Claude가 에러를 데이터로 보고 재시도/대안 가능).
- **이미지**: `content`에 `image` 블록. `data`는 raw base64(접두사 없음), `mimeType` 필수. URL 이미지는 handler에서 fetch 후 base64 인코딩.
- **리소스**: `resource` 블록. `resource.uri`는 라벨(SDK가 읽지 않음), 실제 내용은 `text`/`blob`에 인라인.
- **구조화 데이터**: `structuredContent`(content 배열과 별개 JSON 객체). 설정 시 Claude는 JSON + image/resource 블록만 받고 **text 블록은 전달 안 됨**(중복 가정). 단, **Python `@tool`은 `content`·`is_error`만 포워딩** → `structuredContent` 필요하면 standalone MCP 서버를 써라.
- **enum 스키마**: TS `z.enum([...])`, Py는 dict 스키마가 enum 미지원이라 전체 JSON Schema dict 필요.

---

## 서브에이전트 (subagents)

서브에이전트는 메인 에이전트가 spawn하는 별도 인스턴스다. 컨텍스트 격리, 병렬 실행, 전문 지시 적용에 쓴다. 생성 3가지: 프로그래밍적(`agents` 파라미터, SDK 권장), 파일시스템(`.claude/agents/`의 마크다운, [[08 서브에이전트와 에이전트 팀]] 참조), 내장 `general-purpose`(정의 없이 Agent 도구로 호출).

> Claude는 각 서브에이전트의 `description`으로 호출 여부를 판단한다. 명확한 description을 쓰고, `allowedTools`에 **`Agent`를 포함**해야 호출이 프롬프트 없이 자동 승인된다.

### 이점

- **컨텍스트 격리**: 각 서브에이전트는 새 대화에서 실행. 중간 도구 호출/결과는 내부에 남고 **최종 메시지만** 부모에 반환(부모 컨텍스트 절약).
- **병렬화**: 독립 하위작업을 동시 실행(가장 느린 것 시간으로 완료).
- **전문 지시/지식**: 맞춤 시스템 프롬프트.
- **도구 제한**: `tools`로 권한 축소(`doc-reviewer`를 Read/Grep만).

### `AgentDefinition` 설정

```python
agents={
  "code-reviewer": AgentDefinition(
    description="Expert code review specialist. Use for quality, security reviews.",
    prompt="You are a code review specialist...",
    tools=["Read", "Grep", "Glob"],   # 생략 시 모든 도구 상속
    model="sonnet",                    # 'sonnet'/'opus'/'haiku'/'inherit'/full ID
  ),
}
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `description` | 예 | 언제 쓸지 자연어 설명 |
| `prompt` | 예 | 역할·동작 정의 시스템 프롬프트 |
| `tools` | 아니오 | 허용 도구명 배열. 생략 시 전부 상속 |
| `disallowedTools` | 아니오 | 제거할 도구명 |
| `model` | 아니오 | 모델 오버라이드 (alias/`inherit`/full ID) |
| `skills` | 아니오 | 시작 시 컨텍스트에 preload할 스킬명. 미나열도 Skill 도구로 호출 가능 |
| `memory` | 아니오 | `'user'`/`'project'`/`'local'` |
| `mcpServers` | 아니오 | 이 에이전트용 MCP 서버(이름/인라인) |
| `initialPrompt` | 아니오 | main thread 에이전트로 실행 시 첫 user 턴 자동 제출 |
| `maxTurns` | 아니오 | 정지 전 최대 agentic 턴 |
| `background` | 아니오 | 비차단 백그라운드 태스크로 실행 |
| `effort` | 아니오 | `'low'`/`'medium'`/`'high'`/`'xhigh'`/`'max'`/number |
| `permissionMode` | 아니오 | 이 에이전트 내 권한 모드 |

> 서브에이전트는 자기 서브에이전트를 spawn할 수 없다. 서브에이전트 `tools`에 `Agent`를 넣지 마라. Python SDK는 이 필드명에 camelCase 사용(wire format).

### 무엇을 상속하나

서브에이전트 컨텍스트는 fresh지만 비어있지 않다. **부모→서브에이전트 유일 채널은 Agent 도구의 프롬프트 문자열** → 필요한 파일 경로·에러·결정을 그 프롬프트에 직접 담아라.

| 받음 | 못 받음 |
|---|---|
| 자기 시스템 프롬프트 + Agent 도구 프롬프트 | 부모 대화 이력/도구 결과 |
| 프로젝트 CLAUDE.md (`settingSources`로 로드) | preload 스킬 내용(`AgentDefinition.skills`에 없으면) |
| 도구 정의(부모 상속 또는 `tools` 부분집합) | 부모 시스템 프롬프트 |

### 호출 / 탐지 / 재개

- **자동**: `description` 기반. **명시**: 프롬프트에 이름 언급("Use the code-reviewer agent to..."). **동적**: factory 함수로 런타임 조건에 따라 `AgentDefinition` 생성(엄격 리뷰엔 `opus`).
- **탐지**: Agent 도구의 `tool_use` 블록. `block.name`이 `"Agent"`(v2.1.63부터, 이전 `"Task"` — 호환 위해 둘 다 체크). 서브에이전트 내부 메시지는 `parent_tool_use_id` 필드 보유. TS는 `message.message.content`, Py는 `message.content`로 접근.
- **재개**: Agent 도구 결과에 `agentId: <id>` 텍스트 포함. (1) 첫 쿼리서 `session_id` 캡처, (2) 결과 텍스트서 `agentId` 파싱, (3) 둘째 쿼리에 `resume: sessionId` + 프롬프트에 agent ID 포함(같은 `agents` 정의 전달). 내장 `Explore`/`Plan`은 one-shot이라 trailer 생략 → 재개엔 커스텀/`general-purpose` 사용. 서브에이전트 transcript는 메인 compaction과 무관하게 별도 파일로 영속, `cleanupPeriodDays`(기본 30일)로 정리.

### 도구 조합 / 스케일업

| 용도 | 도구 |
|---|---|
| 읽기 전용 분석 | `Read`, `Grep`, `Glob` |
| 테스트 실행 | `Bash`, `Read`, `Grep` |
| 코드 수정 | `Read`, `Edit`, `Write`, `Grep`, `Glob` |
| 전체 접근 | 전부 (`tools` 생략) |

턴당 수십~수백 에이전트를 조율하려면 `Workflow` 도구(TS Agent SDK v0.3.149+, `allowedTools`에 `Workflow` 포함)로 오케스트레이션을 대화 컨텍스트 밖 스크립트로 옮긴다.

> Windows: 매우 긴 프롬프트의 서브에이전트는 명령줄 길이 제한(8191자)으로 실패 가능 → 짧게 유지하거나 파일시스템 정의.

---

## 스킬 (skills)

Agent Skills는 Claude가 상황에 맞게 **자율 호출**하는 전문 능력으로, 지시·설명·선택 리소스를 담은 `SKILL.md` 파일로 패키징된다(개념·작성법은 [[07 스킬]]).

### SDK에서의 동작

스킬은 **파일시스템 아티팩트로만** 정의된다(서브에이전트와 달리 프로그래밍 등록 API 없음). `settingSources`/`setting_sources`가 지배하는 위치에서 로드되고, 시작 시 메타데이터 발견, 트리거 시 전체 내용 로드, 모델이 자율 호출, `skills` 옵션으로 필터.

```python
options = ClaudeAgentOptions(
    cwd="/path/to/project",
    setting_sources=["user", "project"],  # 파일시스템서 스킬 로드
    skills="all",                          # 발견된 모든 스킬 활성
    allowed_tools=["Read", "Write", "Bash"],
)
```

- `skills` 생략 시 발견된 스킬 활성 + Skill 도구 사용 가능(CLI 동작과 동일).
- `"all"`(전부), `["pdf", "docx"]`(특정 이름. `SKILL.md`의 `name` 또는 디렉터리명, 플러그인은 `plugin:skill`), `[]`(전부 비활성).
- `skills` 설정 시 SDK가 `allowedTools`에 **Skill 도구를 자동 추가**. `tools` 리스트를 명시했다면 `"Skill"`을 직접 포함해야 함.

> `skills` 옵션은 **컨텍스트 필터이지 샌드박스가 아니다**. 미나열 스킬은 모델에게 숨겨지고 Skill 도구가 거부하지만, 파일은 디스크에 남아 Read·Bash로 접근 가능.

### 위치 / 생성 / 도구 제한

- **Project** `.claude/skills/`(`project` 소스), **User** `~/.claude/skills/`(`user` 소스), **Plugin** 스킬.
- 디렉터리 + `SKILL.md`(YAML frontmatter + Markdown). `description`이 호출 시점을 결정.
- **`SKILL.md`의 `allowed-tools` frontmatter는 CLI에서만 동작, SDK에선 무시.** SDK는 메인 `allowedTools` 옵션으로 제어(+ `canUseTool` 없으면 미나열 거부, `dontAsk`로 강제).

### 문제 해결

- **스킬 안 보임**: `setting_sources`에 `user`/`project` 포함했는지(`setting_sources=[]`면 미로드). `cwd`가 `.claude/skills/`를 포함하는 디렉터리(또는 상위, 같은 repo) 가리키는지. `ls .claude/skills/*/SKILL.md`로 확인.
- **스킬 안 쓰임**: `skills` 리스트에 이름 포함됐는지(`[]`면 전부 비활성), description이 구체적인지.

---

## 슬래시 명령 (slash-commands)

`/`로 시작하는 명령으로 세션을 제어한다(compaction, 컨텍스트 사용량 조회, 커스텀 명령 등). **대화형 터미널 없이 동작하는 명령만** SDK로 dispatch 가능하며, `system/init` 메시지가 세션의 가용 명령을 나열한다.

### 발견 / 전송

```typescript
if (message.type === "system" && message.subtype === "init") {
  console.log("Available slash commands:", message.slash_commands);
  // 예: ["clear", "compact", "context", "usage"]
}
```

명령은 프롬프트 문자열에 그냥 포함해 전송: `query({ prompt: "/compact", options: { maxTurns: 1 } })`.

### 내장 명령

- **`/compact`**: 오래된 메시지를 요약해 이력 축소. `system`/`compact_boundary` 메시지에 `compact_metadata.pre_tokens`·`trigger`.
- **`/clear`**: 컨텍스트를 빈 상태로 리셋(이전 대화는 디스크에 남아 `resume`으로 복귀). [스트리밍 입력 모드](#스트리밍-입력)에서 유용. 일회성 `query()`는 이미 빈 컨텍스트로 시작하므로 효과 없음 → 새 `query()`를 시작. (SDK의 `/clear`는 Claude Code v2.1.117+ 필요.)

### 커스텀 명령

마크다운 파일로 정의(서브에이전트와 유사).

> [!note] 레거시 vs 권장
> `.claude/commands/`는 **레거시** 포맷이다. 권장은 `.claude/skills/<name>/SKILL.md`로, 동일한 `/name` 슬래시 호출 + Claude 자율 호출까지 지원한다([스킬](#스킬-skills) 참조). CLI는 둘 다 계속 지원.

- **위치**: Project `.claude/commands/`, Personal `~/.claude/commands/`.
- **포맷**: 파일명(`.md` 제외)이 명령명. 내용이 동작. 선택적 YAML frontmatter.
- **Frontmatter 필드**: `allowed-tools`, `description`, `model`(예: `claude-opus-4-7`), `argument-hint`.
- **인자/플레이스홀더**: `$0`/`$1`(위치), `$ARGUMENTS`(전체). 예: `/fix-issue 123 high` → `$0="123"`, `$1="high"`.
- **Bash 실행**: `` !`git status` `` 형태로 출력 포함.
- **파일 참조**: `@package.json`처럼 `@` 접두사로 내용 포함.
- **네임스페이싱**: 하위 디렉터리(`frontend/component.md` → `/component`, description에 `project:frontend` 표시. 명령명 자체엔 영향 없음).

커스텀 명령은 파일시스템에 정의되면 SDK에서 자동 사용 가능하며 `slash_commands` 리스트에 내장 명령과 함께 나타난다.

---

## 플러그인 (plugins)

플러그인은 스킬·에이전트·훅·MCP 서버를 묶어 프로젝트 간 공유하는 패키지다(구조·생성은 [[11 플러그인]]). SDK로 **로컬 디렉터리에서 프로그래밍적으로 로드**한다.

### 로딩

`type`은 `"local"`만 허용된다. 마켓플레이스/원격 배포 플러그인은 먼저 다운로드해 로컬 경로를 준다.

```python
options=ClaudeAgentOptions(plugins=[
    {"type": "local", "path": "./my-plugin"},
    {"type": "local", "path": "/absolute/path/to/another-plugin"},
])
```

- **경로**: 상대(cwd 기준) 또는 절대. 경로는 플러그인 **루트**(=`skills/`·`agents/`·`hooks/`·`commands/`(레거시)·`.claude-plugin/`의 부모)를 가리켜야 함.
- CLI 설치 플러그인(`/plugin install ...`)도 설치 경로(`~/.claude/plugins/`)를 주면 SDK에서 사용 가능.

### 확인 / 사용 / 구조

성공 로드 시 `system`/`init`에 나타남: `message.plugins`(예: `[{name, path}]`), `message.skills`(예: `["my-plugin:greet"]` — 플러그인명 접두사), `message.slash_commands`(같은 접두사). 플러그인 스킬 직접 호출: `/plugin-name:skill-name`.

```text
my-plugin/
├── .claude-plugin/plugin.json   # 매니페스트 (선택, 없으면 자동 발견)
├── skills/my-skill/SKILL.md      # 자율/`/skill-name` 호출
├── commands/custom-cmd.md        # 레거시 (skills/ 권장)
├── agents/specialist.md
├── hooks/hooks.json
└── .mcp.json                     # MCP 서버 정의
```

> `commands/`는 레거시. 새 플러그인은 `skills/` 사용(둘 다 호환 유지).

**문제 해결**: init에 안 보이면 경로가 루트 가리키는지·`plugin.json` JSON 유효한지·권한 읽기 가능한지. 스킬 안 되면 네임스페이스(`/plugin-name:skill-name`) 사용·init `skills`에 올바른 네임스페이스로 나타나는지·각 스킬이 `skills/my-skill/SKILL.md`인지. 상대 경로 문제는 cwd 확인 또는 절대 경로.

---

## 사용자 입력 처리 (user-input)

작업 중 Claude가 **도구 사용 권한**(파일 삭제·명령 실행)이나 **명확화 질문**(`AskUserQuestion` 도구)으로 사용자에게 확인할 때, 둘 다 `canUseTool` 콜백을 트리거하고 콜백이 반환할 때까지 실행을 일시정지한다. (일반 대화 턴과 다름.) 콜백은 무한정 pending 가능하며, 너무 오래 걸릴 응답은 [`defer` 훅 결정](#훅-hooks)으로 프로세스를 종료했다 나중에 재개.

```python
options = ClaudeAgentOptions(can_use_tool=handle_tool_request)   # TS: { canUseTool: handleToolRequest }
```

> 프롬프트 없이 자동 허용/거부는 [훅](#훅-hooks)을 써라(훅이 `canUseTool`보다 먼저 실행). `PermissionRequest` 훅으로 외부 알림(Slack/이메일/푸시)도 가능.

### 도구 승인 요청 처리

콜백은 3개 인자: `toolName`, `input`(도구별 파라미터), `options`(TS)/`context`(Py, optional `suggestions`+취소 signal). 반환:

| 응답 | Python | TypeScript |
|---|---|---|
| 허용 | `PermissionResultAllow(updated_input=...)` | `{ behavior: "allow", updatedInput }` |
| 거부 | `PermissionResultDeny(message=...)` | `{ behavior: "deny", message }` |

흔한 도구별 `input` 필드: `Bash`(`command`/`description`/`timeout`), `Write`(`file_path`/`content`), `Edit`(`file_path`/`old_string`/`new_string`), `Read`(`file_path`/`offset`/`limit`).

> [!note] Python 필수 우회
> Python의 `can_use_tool`은 [스트리밍 모드](#스트리밍-입력)와 `{"continue_": True}`를 반환하는 `PreToolUse` 더미 훅이 필요하다. 이 훅 없으면 권한 콜백 호출 전에 스트림이 닫힌다.

응답 방식 6가지: **승인**(input 그대로), **변경 승인**(input 수정 후 실행, Claude는 변경을 모름 — 경로 sanitize·제약 추가), **승인+기억**(`context.suggestions`의 `PermissionUpdate`를 `updatedPermissions`(Py `updated_permissions`)로 echo. `localSettings` destination은 `.claude/settings.local.json`에 규칙 기록 → 향후 세션 프롬프트 생략. Py는 SDK 0.1.80+), **거부**(이유 메시지), **대안 제시**(거부 + 가이드), **완전 전환**([스트리밍 입력](#스트리밍-입력)으로 새 지시).

### 명확화 질문 처리 (`AskUserQuestion`)

여러 유효 접근이 있을 때 Claude가 `AskUserQuestion`을 호출 → `canUseTool`이 `toolName === "AskUserQuestion"`으로 트리거. (`plan` 모드에서 특히 흔함.) `tools` 배열을 제한했다면 `AskUserQuestion`을 포함해야 함. **질문·옵션은 Claude가 생성**하고, 앱은 표시·선택 반환만 한다(자체 질문 추가 불가).

질문 입력(`questions` 배열) 각 항목:

| 필드 | 설명 |
|---|---|
| `question` | 표시할 전체 질문 텍스트 |
| `header` | 짧은 라벨 (최대 12자) |
| `options` | 2~4개 선택지, 각 `label`+`description` (TS는 선택적 `preview`) |
| `multiSelect` | true면 다중 선택 |

응답: `answers` 객체(키=`question` 텍스트, 값=선택한 `label`. 다중 선택은 라벨 배열 또는 `", "` 조인). **원본 `questions` 배열을 그대로 함께 전달**(도구 처리에 필수). 자유 텍스트는 "Other" 선택지를 추가해 사용자 텍스트를 값으로(단어 "Other"가 아님). 선택적 `response` 필드는 사용자가 질문 카드를 dismiss하고 일반 답을 칠 때만(설정 시 Claude는 "The user responded: …"를 받음).

```python
return PermissionResultAllow(updated_input={
    "questions": input_data.get("questions", []),
    "answers": {
        "How should I format the output?": "Summary",
        "Which sections should I include?": ["Introduction", "Conclusion"],
    },
})
```

#### 옵션 프리뷰 (TypeScript)

`toolConfig.askUserQuestion.previewFormat`으로 각 옵션에 `preview` 필드 추가(시각 mockup). `unset`(기본, 필드 없음), `"markdown"`(ASCII 아트·코드블록), `"html"`(스타일된 `<div>`. SDK가 `<script>`/`<style>`/`<!DOCTYPE>`를 콜백 전에 거부). 세션 전체에 적용되며 Claude가 시각 비교가 도움될 때만 포함(렌더 전 `undefined` 체크).

### 한계 / 기타 입력 방식

- **한계**: `AskUserQuestion`은 Agent 도구로 spawn된 서브에이전트에선 사용 불가. 호출당 1~4 질문, 질문당 2~4 옵션.
- **스트리밍 입력**: 작업 중 인터럽트, 추가 컨텍스트 제공, 채팅 UI. 단일 연결로 여러 프롬프트 전송([22 Agent SDK — 시작]의 streaming-vs-single 참조).
- **커스텀 도구**: 구조화 입력(폼·위저드), 외부 승인 시스템 통합, 도메인 특화 상호작용 → [커스텀 도구](#커스텀-도구-custom-tools).

---

## 할 일 추적 (todo-tracking)

복잡한 워크플로우를 구조화하고 진행 상황을 사용자에게 표시한다. SDK가 자동으로 todo를 만드는 경우: 3개 이상 동작의 복잡 작업, 사용자 제공 작업 리스트, 진행 추적이 이로운 비단순 작업, 명시 요청.

라이프사이클: `pending`(생성) → `in_progress`(시작) → `completed`(완료) → 그룹 전체 완료 시 제거.

> [!note] TodoWrite → Task tools 마이그레이션
> TypeScript Agent SDK 0.3.142 / Claude Code v2.1.142부터 세션은 `TodoWrite` 대신 구조화 Task 도구(`TaskCreate`·`TaskUpdate`·`TaskGet`·`TaskList`)를 사용한다. 아래 첫 예시들은 `CLAUDE_CODE_ENABLE_TASKS=0`을 설정해 미마이그레이션 세션의 `TodoWrite`를 계속 보여준다.

### TodoWrite 모니터링 (레거시)

도구 호출 업데이트는 메시지 스트림에 반영된다. `block.name === "TodoWrite"`인 `tool_use` 블록의 `block.input.todos`를 검사. 각 todo는 `{ content, status, activeForm }`이며 `status`는 `completed`/`in_progress`/`pending`. `in_progress`일 때 `activeForm`을 표시하는 게 자연스럽다.

```typescript
options: { maxTurns: 15, env: { ...process.env, CLAUDE_CODE_ENABLE_TASKS: "0" } }
// block.name === "TodoWrite" 이면 block.input.todos 순회
```

### Task tools로 마이그레이션

`TodoWrite` 단일 호출이 `TaskCreate`(항목 추가)와 `TaskUpdate`(`taskId`로 항목 패치)로 분리된다. `TaskList`/`TaskGet`으로 현재 리스트 읽기. 모니터링 코드는 여전히 `tool_use` 블록을 보지만, 매번 전체 리스트를 교체하는 대신 **task ID 키 맵**을 유지한다.

| TodoWrite | Task tools |
|---|---|
| 한 호출이 전체 `todos` 배열 재작성 | `TaskCreate`가 1개 추가, `TaskUpdate`가 `taskId`로 1개 패치 |
| `block.name === "TodoWrite"` 매칭 | `"TaskCreate"` 또는 `"TaskUpdate"` 매칭 |
| 항목 형태 `{ content, status, activeForm }` | `TaskCreate`: `{ subject, description, activeForm?, metadata? }`. `TaskUpdate`: `{ taskId, status?, subject?, description?, activeForm?, addBlocks?, addBlockedBy?, owner?, metadata? }`. `status`=`pending`/`in_progress`/`completed`, `status: "deleted"`로 삭제 |
| `block.input.todos` 직접 렌더 | 호출 간 누적, 또는 `TaskList` 결과 스냅샷 |

> 배정된 task ID는 `TaskCreate` **입력에 없고**, 매칭 `tool_result`의 `{ task: { id, subject } }`로 돌아온다 → 결과 블록에서 캡처해 맵 키로. (v2.1.142+ 기본이라 `options.env` 변경 불필요.)

```python
# Task tools 모니터링 (기본 동작)
if block.name == "TaskCreate":
    print(f"+ {block.input['subject']}")
elif block.name == "TaskUpdate" and block.input.get("status"):
    print(f"  {block.input['taskId']} -> {block.input['status']}")
```

---

## 도구 검색 (tool-search)

수백~수천 개 도구로 스케일할 때, 모든 도구 정의를 미리 로드하지 않고 **카탈로그를 검색해 필요한 것만 on-demand 로드**한다. 두 문제를 해결: 컨텍스트 효율(50개 도구가 10~20K 토큰), 도구 선택 정확도(30~50개 초과 시 저하).

### 동작 방식

활성 시 도구 정의가 컨텍스트에서 보류되고, 에이전트는 가용 도구 요약을 받아 필요할 때 검색한다. 가장 관련 높은 **3~5개**가 컨텍스트에 로드되어 이후 턴에 유지(긴 대화로 compaction되면 제거될 수 있고 다시 검색). 첫 발견 시 검색 round-trip 1회 추가되나 큰 도구셋엔 매 턴 작은 컨텍스트로 상쇄. **~10개 미만이면 upfront 로드가 보통 더 빠름.**

> 모델 지원: Claude Sonnet 4+ 또는 Opus 4+. **Haiku 미지원.**

### 설정 (`ENABLE_TOOL_SEARCH`)

기본 활성. 단 Vertex AI(Sonnet 4.5+/Opus 4.5+에서만 지원)와 `ANTHROPIC_BASE_URL`이 비-first-party 호스트일 때(프록시가 `tool_reference` 블록을 미전달) 기본 비활성. `query()`의 `env` 옵션으로 오버라이드:

| 값 | 동작 |
|---|---|
| (unset) | 켜짐. Vertex AI/비-first-party `ANTHROPIC_BASE_URL`에선 upfront 로드로 fallback |
| `true` | 항상 켜짐. Vertex AI·프록시에도 beta 헤더 전송(미지원 환경은 요청 실패) |
| `auto` | 모든 도구 정의 토큰 합이 컨텍스트 윈도의 10% 초과 시 활성 |
| `auto:N` | `auto`의 커스텀 퍼센트. `auto:5`는 5% 초과 시 활성(낮을수록 일찍) |
| `false` | 꺼짐. 매 턴 모든 정의 로드 |

```python
options = ClaudeAgentOptions(
    mcp_servers={"enterprise-tools": {"type": "http", "url": "https://tools.example.com/mcp"}},
    allowed_tools=["mcp__enterprise-tools__*"],
    env={"ENABLE_TOOL_SEARCH": "auto:5"},
)
```

원격 MCP·[커스텀 SDK 도구](#커스텀-도구-custom-tools) 모두에 적용. `auto`의 임계값은 전 서버 정의 합산 크기 기준.

### 발견 최적화 / 한계

검색은 도구 이름·설명에 질의를 매칭한다. `search_slack_messages`가 `query_slack`보다 넓게, 키워드 풍부한 설명("Search Slack messages by keyword, channel, or date range")이 generic("Query Slack")보다 잘 매칭. 시스템 프롬프트에 도구 카테고리 목록(`You can search for tools to interact with Slack, GitHub, and Jira.`)을 두면 도움.

**한계**: 카탈로그 최대 10,000 도구, 검색당 3~5개 반환, Haiku 미지원.

---

## 파일 체크포인트 (file-checkpointing)

세션 중 Write·Edit·NotebookEdit 도구로 한 파일 변경을 추적해 임의 시점으로 되돌린다(undo, 대안 탐색, 에러 복구).

> [!warning] Bash 변경은 추적 안 됨
> Write/Edit/NotebookEdit 도구를 통한 변경만 추적. `echo > file.txt`·`sed -i` 같은 Bash 명령 변경은 캡처 안 됨.

> 파일 rewind는 **디스크 파일만** 복원하고 **대화는 되돌리지 않는다**. `rewind_files()`/`rewindFiles()` 후에도 대화 이력·컨텍스트는 그대로.

추적 대상: 세션 중 생성된 파일, 수정된 파일, 수정 파일의 원본 내용. rewind 시 생성 파일은 삭제, 수정 파일은 그 시점 내용으로 복원.

### 구현 (3단계)

| 옵션 | Python | TypeScript | 설명 |
|---|---|---|---|
| 체크포인트 활성 | `enable_file_checkpointing=True` | `enableFileCheckpointing: true` | 변경 추적 |
| UUID 수신 | `extra_args={"replay-user-messages": None}` | `extraArgs: { 'replay-user-messages': null }` | 스트림서 user 메시지 UUID 수신에 필수 |

```python
options = ClaudeAgentOptions(
    enable_file_checkpointing=True,
    permission_mode="acceptEdits",
    extra_args={"replay-user-messages": None},
)
checkpoint_id = None; session_id = None
async with ClaudeSDKClient(options) as client:
    await client.query("Refactor the authentication module")
    async for message in client.receive_response():
        if isinstance(message, UserMessage) and message.uuid and not checkpoint_id:
            checkpoint_id = message.uuid           # 첫 user 메시지 UUID = 원본 복원점
        if isinstance(message, ResultMessage) and not session_id:
            session_id = message.session_id

# 나중에 rewind: 빈 프롬프트로 세션 재개 후 호출
if checkpoint_id and session_id:
    async with ClaudeSDKClient(
        ClaudeAgentOptions(enable_file_checkpointing=True, resume=session_id)) as client:
        await client.query("")   # 빈 프롬프트로 연결 오픈
        async for message in client.receive_response():
            await client.rewind_files(checkpoint_id)
            break
```

- 첫 user 메시지 UUID로 rewind하면 모든 파일이 원본 상태로. 중간 상태로 가려면 여러 체크포인트 저장.
- 세션 ID 캡처는 스트림 완료 후 rewind할 때만 필요. 스트림 처리 중 즉시 rewind하면 불필요.
- CLI rewind: `claude -p --resume <session-id> --rewind-files <checkpoint-uuid>`.

### 패턴

- **위험 작업 전 체크포인트**: 매 에이전트 턴 전 최신 UUID만 유지(덮어쓰기). 문제 발생 시 마지막 안전 상태로 rewind 후 break.
- **다중 복원점**: 모든 UUID를 메타데이터(설명·타임스탬프)와 함께 배열에 저장 → 세션 후 특정 시점으로 rewind(예: turn 1 리팩터 유지, turn 2 테스트만 undo).

### 한계 / 문제 해결

| 한계 | 설명 |
|---|---|
| Write/Edit/NotebookEdit만 | Bash 변경 미추적 |
| 같은 세션 | 체크포인트는 생성 세션에 묶임 |
| 파일 내용만 | 디렉터리 생성/이동/삭제는 rewind로 안 됨 |
| 로컬 파일 | 원격·네트워크 파일 미추적 |

- **옵션 미인식**: SDK 구버전 → `pip install --upgrade claude-agent-sdk` / `npm install @anthropic-ai/claude-agent-sdk@latest`.
- **user 메시지에 UUID 없음**: `replay-user-messages` 미설정.
- **"No file checkpoint found"**: 원본 세션에 체크포인트 미활성, 또는 세션 미완료 상태에서 resume·rewind 시도.
- **"ProcessTransport is not ready for writing"**: 스트림 순회 완료 후 `rewindFiles()` 호출(연결 닫힘) → 빈 프롬프트로 재개 후 새 쿼리에 rewind 호출.

---

## 원본 문서

- [agent-sdk/permissions](https://code.claude.com/docs/en/agent-sdk/permissions)
- [agent-sdk/sessions](https://code.claude.com/docs/en/agent-sdk/sessions)
- [agent-sdk/session-storage](https://code.claude.com/docs/en/agent-sdk/session-storage)
- [agent-sdk/hooks](https://code.claude.com/docs/en/agent-sdk/hooks)
- [agent-sdk/mcp](https://code.claude.com/docs/en/agent-sdk/mcp)
- [agent-sdk/custom-tools](https://code.claude.com/docs/en/agent-sdk/custom-tools)
- [agent-sdk/subagents](https://code.claude.com/docs/en/agent-sdk/subagents)
- [agent-sdk/skills](https://code.claude.com/docs/en/agent-sdk/skills)
- [agent-sdk/slash-commands](https://code.claude.com/docs/en/agent-sdk/slash-commands)
- [agent-sdk/plugins](https://code.claude.com/docs/en/agent-sdk/plugins)
- [agent-sdk/user-input](https://code.claude.com/docs/en/agent-sdk/user-input)
- [agent-sdk/todo-tracking](https://code.claude.com/docs/en/agent-sdk/todo-tracking)
- [agent-sdk/tool-search](https://code.claude.com/docs/en/agent-sdk/tool-search)
- [agent-sdk/file-checkpointing](https://code.claude.com/docs/en/agent-sdk/file-checkpointing)
