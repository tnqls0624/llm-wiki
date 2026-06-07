---
title: 24 Agent SDK — 고급과 레퍼런스
updated: 2026-06-07
sources: [agent-sdk/streaming-output, agent-sdk/streaming-vs-single-mode, agent-sdk/structured-outputs, agent-sdk/modifying-system-prompts, agent-sdk/observability, agent-sdk/cost-tracking, agent-sdk/hosting, agent-sdk/secure-deployment, agent-sdk/typescript, agent-sdk/typescript-v2-preview, agent-sdk/python]
---

# 24 Agent SDK — 고급과 레퍼런스

Agent SDK의 고급 주제(스트리밍, 구조화 출력, 시스템 프롬프트 커스터마이징, 관측성·비용 추적, 호스팅·보안 배포)와 TypeScript/Python API 레퍼런스를 다룬다. SDK의 기초 설치·인증·첫 쿼리는 [[22 Agent SDK — 시작]], 권한·세션·커스텀 도구·서브에이전트·MCP·훅 같은 핵심 기능은 [[23 Agent SDK — 핵심 기능]]을 참조. 허브: [[Claude]].

> [!note] 입력 모드 vs 출력 스트리밍 구분
> - **입력 모드**(메시지를 어떻게 보내는가): streaming input(권장) vs single message — 아래 [입력 모드](#입력-모드-streaming-vs-single)
> - **출력 스트리밍**(토큰을 실시간으로 받는가): `include_partial_messages` — 아래 [출력 스트리밍](#출력-스트리밍-실시간-토큰-수신)
> 둘은 독립적이다.

---

## 입력 모드: streaming vs single

SDK는 에이전트에 메시지를 보내는 두 가지 입력 모드를 제공한다.

| 모드 | 진입점 | 특징 | 용도 |
| :-- | :-- | :-- | :-- |
| **Streaming input** (기본·권장) | TS: `query()`에 `AsyncIterable<SDKUserMessage>` 전달 / PY: `ClaudeSDKClient` | 영속 세션, 인터럽트, 권한 요청 처리, 이미지 첨부, 메시지 큐잉, 멀티턴 컨텍스트 유지 | 대화형 앱, 장기 실행 에이전트 |
| **Single message** | `query()`에 `string` 전달 | 일회성. `continue`/`resume`로 상태 이어붙이기만 가능 | 람다 등 stateless 환경, one-shot 응답 |

### Single message의 제약

다음을 지원하지 **않는다**: 메시지 내 직접 이미지 첨부, 동적 메시지 큐잉, 실시간 인터럽트, 자연스러운 멀티턴 대화. 이런 기능이 필요하면 streaming input을 써야 한다.

### Streaming input 예시

TypeScript에서는 `query()`의 `prompt`에 `async function*` 제너레이터를 넘긴다. Python에서는 `ClaudeSDKClient`로 세션을 열고 `client.query(generator)` → `client.receive_response()`로 처리한다.

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock

async def message_generator():
    yield {"type": "user", "message": {"role": "user", "content": "Analyze this codebase"}}
    await asyncio.sleep(2)
    # 후속 메시지에 base64 이미지 첨부 가능
    yield {"type": "user", "message": {"role": "user", "content": [
        {"type": "text", "text": "Review this diagram"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}},
    ]}}

options = ClaudeAgentOptions(max_turns=10, allowed_tools=["Read", "Grep"])
async with ClaudeSDKClient(options) as client:
    await client.query(message_generator())
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
```

Single message에서 대화를 이어가려면 `continue: true`(TS) / `continue_conversation=True`(PY)를 사용한다. (세션·resume 상세는 [[23 Agent SDK — 핵심 기능]].)

---

## 출력 스트리밍: 실시간 토큰 수신

기본적으로 SDK는 Claude가 응답 생성을 끝낸 뒤 완성된 `AssistantMessage`만 yield한다. 토큰·도구 호출을 생성되는 즉시 받으려면 partial message 스트리밍을 켠다.

| 옵션 | TypeScript | Python |
| :-- | :-- | :-- |
| 부분 메시지 활성화 | `includePartialMessages: true` | `include_partial_messages=True` |
| 받는 메시지 타입 | `type: "stream_event"` (`SDKPartialAssistantMessage`) | `StreamEvent` (`from claude_agent_sdk.types import StreamEvent`) |

`StreamEvent`는 누적된 텍스트가 아니라 [Claude API의 raw 스트리밍 이벤트](https://platform.claude.com/docs/en/build-with-claude/streaming)를 감싼 객체다. 텍스트 델타를 직접 추출·누적해야 한다.

### StreamEvent 구조

```python
@dataclass
class StreamEvent:
    uuid: str
    session_id: str
    event: dict[str, Any]          # raw Claude API stream event
    parent_tool_use_id: str | None  # 서브에이전트 발생 시 부모 도구 ID
```

### 주요 이벤트 타입

| Event Type | 의미 |
| :-- | :-- |
| `message_start` | 새 메시지 시작 |
| `content_block_start` | 콘텐츠 블록(텍스트/tool_use) 시작 |
| `content_block_delta` | 콘텐츠 증분 업데이트 |
| `content_block_stop` | 콘텐츠 블록 종료 |
| `message_delta` | 메시지 수준 업데이트(stop reason, usage) |
| `message_stop` | 메시지 종료 |

### 텍스트 델타 추출 패턴

`content_block_delta` 이벤트에서 `delta.type`이 `text_delta`인 경우를 골라 `delta.text`를 읽는다.

```python
async for message in query(prompt="Explain how databases work",
                           options=ClaudeAgentOptions(include_partial_messages=True)):
    if isinstance(message, StreamEvent):
        event = message.event
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                print(delta.get("text", ""), end="", flush=True)
```

### 도구 호출 스트리밍

도구 호출도 증분으로 스트리밍된다. 세 이벤트로 추적한다.
- `content_block_start` (블록 타입이 `tool_use`): 도구 시작 → 이름 확인
- `content_block_delta` (`delta.type == "input_json_delta"`): `partial_json` 청크 누적
- `content_block_stop`: 도구 호출 입력 완성

### 메시지 흐름 순서

partial 활성화 시: `StreamEvent(message_start)` → `content_block_start`(text) → `content_block_delta`(text 청크들) → `content_block_stop` → `content_block_start`(tool_use) → `content_block_delta`(tool input) → ... → `message_stop` → 완성된 `AssistantMessage` → (도구 실행) → ... → `ResultMessage`. partial 비활성화 시에는 `SystemMessage`/`AssistantMessage`/`ResultMessage`와 compact boundary 메시지(`SDKCompactBoundaryMessage`(TS) / subtype `"compact_boundary"`인 `SystemMessage`(PY))만 받는다.

> [!warning] 알려진 제약
> 구조화 출력 JSON은 스트리밍 델타로 오지 않는다. 최종 `ResultMessage.structured_output`에만 들어온다. (아래 [구조화 출력](#구조화-출력-검증된-json) 참조.)

---

## 구조화 출력: 검증된 JSON

JSON Schema로 원하는 데이터 형태를 정의하면, 에이전트가 도구를 자유롭게 쓰면서도 마지막에 스키마에 맞는 검증된 JSON을 반환한다. SDK는 출력이 스키마와 어긋나면 재프롬프트하고, 재시도 한도 안에 검증에 실패하면 에러를 낸다.

| 옵션 | TypeScript | Python |
| :-- | :-- | :-- |
| 출력 포맷 지정 | `outputFormat: { type: "json_schema", schema }` | `output_format={"type": "json_schema", "schema": ...}` |
| 결과 읽기 | `message.structured_output` (result 메시지, `subtype === "success"`) | `message.structured_output` (`ResultMessage`) |

```typescript
const schema = {
  type: "object",
  properties: {
    company_name: { type: "string" },
    founded_year: { type: "number" },
  },
  required: ["company_name"],
};
for await (const message of query({
  prompt: "Research Anthropic and provide key company information",
  options: { outputFormat: { type: "json_schema", schema } },
})) {
  if (message.type === "result" && message.subtype === "success" && message.structured_output) {
    console.log(message.structured_output);
  }
}
```

### Zod / Pydantic 타입 안전 스키마

손으로 JSON Schema를 쓰는 대신 Zod(TS) / Pydantic(PY)으로 정의하면 JSON Schema를 자동 생성하고, 응답을 완전 타입화된 객체로 파싱할 수 있다.

| 작업 | TypeScript (Zod) | Python (Pydantic) |
| :-- | :-- | :-- |
| JSON Schema 생성 | `z.toJSONSchema(MySchema)` | `MyModel.model_json_schema()` |
| 런타임 검증·파싱 | `MySchema.safeParse(output)` | `MyModel.model_validate(output)` |

```python
class FeaturePlan(BaseModel):
    feature_name: str
    summary: str
    steps: list[Step]
    risks: list[str]

async for message in query(
    prompt="Plan how to add dark mode support to a React app.",
    options=ClaudeAgentOptions(output_format={"type": "json_schema", "schema": FeaturePlan.model_json_schema()}),
):
    if isinstance(message, ResultMessage) and message.structured_output:
        plan = FeaturePlan.model_validate(message.structured_output)
        print(plan.feature_name)
```

지원되는 JSON Schema 기능: 기본 타입(object/array/string/number/boolean/null), `enum`, `const`, `required`, 중첩 객체, `$ref`. 전체 한계는 [API structured outputs 문서](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations) 참조.

### 에러 처리

result 메시지의 `subtype`으로 성공/실패를 구분한다.

| Subtype | 의미 |
| :-- | :-- |
| `success` | 출력 생성·검증 성공 |
| `error_max_structured_output_retries` | 여러 시도 후에도 유효 출력 생성 실패 |

오류 회피 팁: 스키마를 집중적으로 유지(깊은 중첩·필수 필드 남발 금지), 작업에 맞춰 정보가 없을 수 있는 필드는 optional로, 모호하지 않은 명확한 프롬프트 사용. 단일 턴·도구 없는 구조화 출력이 필요하면 [API structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)를 직접 쓴다.

---

## 시스템 프롬프트 커스터마이징

시스템 프롬프트는 Claude의 행동·역량·응답 스타일을 정의한다. SDK의 세 가지 출발점:

| 출발점 | 설정 | 받는 것 |
| :-- | :-- | :-- |
| **Minimal default** | `systemPrompt` 미설정 | 도구 호출 지원만. 코딩 가이드·응답 스타일·프로젝트 컨텍스트 없음 (CLI의 `claude -p`와 다름) |
| **`claude_code` preset** | `{ type: "preset", preset: "claude_code" }` | CLI 전체 프롬프트: 도구 가이드, 코드 스타일, 응답 톤, 보안 규칙, 작업 디렉터리·환경 컨텍스트 |
| **Custom string** | `systemPrompt: "..."` | 당신이 쓴 것만. 도구 가이드·보안 지침은 직접 책임 |

> [!tip] 출발점 결정 기준
> "Claude Code와 얼마나 닮았나"가 핵심. 코딩 에이전트가 리포지터리에서 동작하고 사람이 스트리밍 출력을 보며 조종한다면 preset. 표면(surface)·정체성(identity)·권한 모델이 다르거나 비코딩 작업이면 custom string. CI에서 lint를 고치는 무인 코딩 자동화는 여전히 preset이 맞다.

### 네 가지 커스터마이징 방법

| 기능 | CLAUDE.md | Output Styles | preset + `append` | Custom `systemPrompt` |
| :-- | :-- | :-- | :-- | :-- |
| 영속성 | 프로젝트 파일 | 파일로 저장 | 세션 한정 | 세션 한정 |
| 재사용성 | 프로젝트 단위 | 프로젝트 간 | 코드 중복 | 코드 중복 |
| 기본 도구 | 보존 | 보존 | 보존 | 손실(직접 포함 필요) |
| 내장 안전 | 유지 | 유지 | 유지 | 직접 추가 |
| 환경 컨텍스트 | 자동 | 자동 | 자동 | 직접 제공 |
| 커스터마이징 수준 | 추가만 | 대체 또는 확장 | 추가만 | 완전 제어 |

### CLAUDE.md 로딩

CLAUDE.md 내용은 시스템 프롬프트가 아니라 **대화에 프로젝트 컨텍스트로 주입**되므로 어떤 systemPrompt 설정과도 함께 동작한다. setting source가 활성화되어야 로딩된다: `'project'` → `CLAUDE.md` 또는 `.claude/CLAUDE.md`, `'user'` → `~/.claude/CLAUDE.md`. 기본 `query()` 옵션은 둘 다 켜져 있으나, `settingSources`(TS)/`setting_sources`(PY)를 명시하면 필요한 소스를 직접 넣어야 한다. 빈 배열을 넘기면 로딩되지 않는다. (CLAUDE.md 작성법은 [[03 메모리와 컨텍스트]].)

### Output styles

마크다운 파일로 저장되는 페르소나. `~/.claude/output-styles/`(사용자) 또는 `.claude/output-styles/`(프로젝트)에 저장한다. frontmatter에 `keep-coding-instructions: true`를 넣으면 preset의 SW 엔지니어링 지침을 유지하고 그 위에 레이어한다(코드 리뷰어 등 코딩 작업에 유용). 활성화 경로: CLI `/config`, `.claude/settings.local.json`의 `outputStyle`, TS SDK는 inline `settings` 객체의 `outputStyle`(최상위 `Options` 필드 아님). **Python SDK에는 프로그램으로 output style을 고르는 옵션이 없다** — `append`나 custom string을 쓴다. output style 로딩에는 `settingSources`에 `'user'`/`'project'` 포함이 필요하다. (상세: [[12 출력 스타일과 상태줄]].)

### append로 preset 확장

```python
async for message in query(
    prompt="Help me write a Python function to calculate fibonacci",
    options=ClaudeAgentOptions(system_prompt={
        "type": "preset", "preset": "claude_code",
        "append": "Always include detailed docstrings and type hints in Python code.",
    }),
):
    ...
```

### 프롬프트 캐시 재사용 개선: `excludeDynamicSections`

기본적으로 같은 preset + 같은 `append`라도 작업 디렉터리가 다르면 캐시 엔트리를 공유하지 못한다. preset이 per-session 컨텍스트(cwd, git 여부, 플랫폼, 셸, OS 버전, auto-memory 경로)를 시스템 프롬프트에 박아 넣기 때문이다. `excludeDynamicSections: true`(TS) / `"exclude_dynamic_sections": True`(PY)를 켜면 이 컨텍스트가 첫 user 메시지로 옮겨가, 동일 구성이 머신·사용자 간 캐시를 공유한다.

> [!note] 버전·트레이드오프
> `@anthropic-ai/claude-agent-sdk` v0.2.98+ 또는 Python `claude-agent-sdk` v0.1.58+ 필요. preset 객체 형식에만 적용되고 문자열 systemPrompt에는 효과 없음. user 메시지의 지침은 시스템 프롬프트보다 가중치가 약간 낮으므로, 환경 컨텍스트 권위보다 교차 세션 캐시 재사용이 더 중요할 때 켠다. CLI 비대화 모드 등가 플래그는 `--exclude-dynamic-system-prompt-sections`([[02 CLI 레퍼런스]]).

(스킬·훅·권한도 시스템 프롬프트 밖에서 행동을 형성한다 → [[07 스킬]], [[09 훅]], [[05 권한]].)

---

## 관측성: OpenTelemetry

SDK는 Claude Code CLI를 자식 프로세스로 실행하고, CLI에 내장된 OTel 계측이 직접 컬렉터로 export한다. SDK 자체는 텔레메트리를 만들지 않고 환경변수만 CLI로 전달한다. OTLP를 받는 백엔드(Honeycomb, Datadog, Grafana, Langfuse, self-hosted collector)면 모두 가능.

### 환경변수로 설정하는 두 곳

- **프로세스 환경**(권장, 프로덕션): 셸/컨테이너/오케스트레이터에서 미리 export. 모든 `query()`가 코드 변경 없이 자동 적용.
- **per-call 옵션**: `ClaudeAgentOptions.env`(PY) / `options.env`(TS). PY는 상속 환경 위에 머지, **TS는 상속 환경을 완전히 대체하므로 `{ ...process.env, ... }`로 펼쳐야** PATH·API 키 유지.

### 세 가지 시그널

| Signal | 내용 | 활성화 |
| :-- | :-- | :-- |
| Metrics | 토큰·비용·세션·LoC·tool decision 카운터 | `OTEL_METRICS_EXPORTER` |
| Log events | 프롬프트·API 요청·API 에러·tool result 구조화 레코드 | `OTEL_LOGS_EXPORTER` |
| Traces | interaction·model request·tool call·hook 스팬 (beta) | `OTEL_TRACES_EXPORTER` + `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` |

### 표준 export 설정 (env)

```bash
CLAUDE_CODE_ENABLE_TELEMETRY=1
CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1     # traces(beta)에만 필요
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
OTEL_LOGS_EXPORTER=otlp
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_ENDPOINT=http://collector.example.com:4318
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer your-token
```

> [!warning] `console` exporter 금지
> SDK는 stdout을 메시지 채널로 쓴다. SDK를 통해 실행할 때 exporter 값으로 `console`을 설정하면 안 된다. 로컬 확인은 로컬 collector나 Jaeger 컨테이너로 `OTEL_EXPORTER_OTLP_ENDPOINT`를 향하게 한다.

### 단명 호출의 텔레메트리 플러시

CLI는 배치로 export한다(metrics 기본 60초, traces·logs 기본 5초). 짧은 작업은 데이터가 컬렉터에 도달하기 전 끝날 수 있으므로 간격을 줄인다.

```bash
OTEL_METRIC_EXPORT_INTERVAL=1000
OTEL_LOGS_EXPORT_INTERVAL=1000
OTEL_TRACES_EXPORT_INTERVAL=1000
```

### 트레이스 스팬 이름

| 스팬 | 범위 |
| :-- | :-- |
| `claude_code.interaction` | 에이전트 루프 한 턴(프롬프트 수신 ~ 응답 생성) |
| `claude_code.llm_request` | Claude API 호출 1건(모델·지연·토큰 속성) |
| `claude_code.tool` | 도구 호출 1건. 자식: `claude_code.tool.blocked_on_user`(권한 대기), `claude_code.tool.execution`(실행) |
| `claude_code.hook` | 훅 실행. `ENABLE_BETA_TRACING_DETAILED=1`+`BETA_TRACING_ENDPOINT` 추가 필요 |

`llm_request`/`tool`/`hook`은 `interaction`의 자식. Task 도구로 서브에이전트를 띄우면 그 스팬이 부모의 `claude_code.tool` 아래 중첩되어 위임 체인이 한 트레이스로 보인다. 스팬은 `session.id` 속성을 가지므로 백엔드에서 필터해 한 타임라인으로 본다.

### 앱 트레이스에 연결 / 태깅 / 엔드유저 귀속

- **트레이스 연결**: 앱에서 OTel 스팬이 활성인 채로 `query()`를 부르면 SDK가 `TRACEPARENT`/`TRACESTATE`를 자식 프로세스에 주입해 CLI의 interaction 스팬이 당신 스팬의 자식이 된다. `options.env`에 `TRACEPARENT`를 명시하면 자동 주입은 건너뛴다.
- **태깅**: `OTEL_SERVICE_NAME`(기본 `claude-code`)과 `OTEL_RESOURCE_ATTRIBUTES`로 서비스명·배포 메타데이터를 모든 스팬에 부착.
- **엔드유저 귀속**: 여러 사용자를 한 배포로 서비스할 때 `OTEL_RESOURCE_ATTRIBUTES`에 `enduser.id`/`tenant.id`를 per-call로 주입(값은 percent-encode 필수, 쉼표·공백·등호 예약). `tool_decision`·`tool_result`·`mcp_server_connection`·`permission_mode_changed` 이벤트가 per-user 감사 추적이 되어 SIEM으로 전달 가능.

### 민감 데이터 제어 (opt-in)

텔레메트리는 기본적으로 구조적(지속시간·모델명·도구명)이며 콘텐츠는 기록하지 않는다. 다음은 opt-in:

| 변수 | 추가 내용 |
| :-- | :-- |
| `OTEL_LOG_USER_PROMPTS=1` | 프롬프트 텍스트 |
| `OTEL_LOG_TOOL_DETAILS=1` | 도구 입력 인자(파일 경로·셸 명령·검색 패턴) |
| `OTEL_LOG_TOOL_CONTENT=1` | 도구 입출력 본문 전체(60KB 잘림, traces 필요) |
| `OTEL_LOG_RAW_API_BODIES` | Messages API 요청/응답 JSON 전체. `1`=인라인 60KB 잘림, `file:<dir>`=디스크에 비잘림 |

> 전체 메트릭·이벤트·속성 카탈로그는 [Monitoring 레퍼런스](https://code.claude.com/docs/en/monitoring-usage). 비용·토큰만 메시지 스트림에서 읽으려면 아래 [비용 추적](#비용-추적) 참조.

---

## 비용 추적

> [!warning] `total_cost_usd` / `costUSD`는 추정치
> 클라이언트 측 추정이지 권위 있는 청구 데이터가 아니다. SDK가 빌드 시 번들된 가격표로 로컬 계산하므로 가격 변경·모델 미인식·청구 규칙 시 실제 청구와 어긋날 수 있다. 개발 통찰·근사 예산 용도로만 쓰고, 엔드유저 청구나 금융 결정에 쓰지 말 것. 권위 데이터는 [Usage and Cost API](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api)나 Console.

### 사용량 스코프

| 단위 | 의미 |
| :-- | :-- |
| `query()` 호출 | SDK `query()` 1회 호출. 여러 step 포함 가능. 끝에 `result` 메시지 1개 생성 |
| Step | 호출 내 1회 요청/응답 사이클. assistant 메시지에 토큰 사용량 |
| Session | `resume`로 묶인 일련의 `query()` 호출. 각 호출이 독립적으로 비용 보고 |

### 필드명 (TS vs PY)

| 항목 | TypeScript | Python |
| :-- | :-- | :-- |
| 누적 추정 비용 | `message.total_cost_usd` (result) | `message.total_cost_usd` (`ResultMessage`) |
| step별 토큰 | `message.message.usage`, `message.message.id` | `message.usage`, `message.message_id` |
| 모델별 비용 | `message.modelUsage` (맵) | `message.model_usage` |
| 캐시 토큰 | `usage.cacheReadInputTokens`, `usage.cacheCreationInputTokens` | `usage["cache_read_input_tokens"]`, `usage["cache_creation_input_tokens"]` |

### 총비용 읽기

```python
async for message in query(prompt="Summarize this project"):
    if isinstance(message, ResultMessage):
        print(f"Total cost: ${message.total_cost_usd or 0}")
```

> [!warning] 병렬 도구 호출 중복 계산 주의
> 한 턴에서 여러 도구를 병렬 호출하면 메시지들이 같은 `id`와 동일 usage를 공유한다. **ID로 dedup**해야 토큰이 부풀려지지 않는다. 출력 토큰이 같은 ID에서 다르게 보이면 가장 높은 값(그룹 마지막 메시지)을 쓰고, 가능하면 result 메시지의 `total_cost_usd`를 신뢰한다.

`query()`마다 독립 `total_cost_usd`를 반환하므로 세션 누적이 필요하면 직접 합산한다. 성공·에러 result 모두 `usage`와 `total_cost_usd`를 포함하므로 subtype 무관하게 result에서 읽는다.

### 캐시 토큰과 1시간 TTL

SDK는 [프롬프트 캐싱](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)을 자동 사용한다. `cache_creation_input_tokens`(생성, 높은 요율)와 `cache_read_input_tokens`(읽기, 낮은 요율)를 별도 추적해 절감 효과를 본다. 기본 TTL은 5분(API 키·Bedrock·Vertex·Foundry). 짧은 세션이 5분 넘는 간격으로 반복되면 캐시가 만료되므로 `ENABLE_PROMPT_CACHING_1H` 환경변수로 1시간 TTL을 요청한다(쓰기 요율 더 높음 — 쓰기 비용↑ vs 읽기↑ 트레이드오프). Claude 구독 사용자는 이미 1시간 TTL 자동 적용. 비용 한도는 `maxBudgetUsd`(TS)/`max_budget_usd`(PY)로 추정치 기준 컷오프. (성능·비용 일반론은 [[19 비용과 성능]].)

---

## 호스팅 (자체 인프라)

SDK는 `claude` CLI 서브프로세스를 띄워 감독한다. 서브프로세스는 셸·작업 디렉터리·디스크의 세션 파일을 소유하므로, 호스팅은 stateless API 래퍼 호스팅과 다르다. 인프라 제어가 불필요하면 [Managed Agents](https://platform.claude.com/docs/en/managed-agents/overview)(Anthropic이 에이전트·샌드박스 운영) 고려.

### 서브프로세스 모델

`query()` 호출 1개 = 서브프로세스 1개. N 동시 세션 = N 서브프로세스. 기본적으로 모두 앱의 작업 디렉터리를 상속하므로, 세션마다 별도 파일시스템이 필요하면 호출마다 `cwd`를 넘긴다.

```python
query(prompt=prompt, options=ClaudeAgentOptions(cwd="/work/session-a"))
```

### 로컬 디스크에 사는 상태 (재시작 시 소실)

| 상태 | 기본 위치 |
| :-- | :-- |
| 세션 트랜스크립트 | `~/.claude/projects/` (또는 `CLAUDE_CONFIG_DIR`의 `projects/`) |
| `CLAUDE.md` 메모리 | user: `~/.claude/CLAUDE.md`, project: 세션 작업 디렉터리 |
| 작업 디렉터리 산출물 | 세션 작업 디렉터리 |

호스트 간 트랜스크립트 영속화는 `SessionStore` 어댑터로(세션 스토리지 상세는 핵심 기능 영역). 메모리 파일·산출물은 별도 전략(마운트 볼륨, 오브젝트 스토어 동기화).

### 세션 패턴

| 패턴 | 설명 | 용도 |
| :-- | :-- | :-- |
| Ephemeral | 작업마다 컨테이너 생성 후 완료 시 파기. one-shot 엔트리포인트 | 버그 수정, 영수증 추출, 번역, 미디어 변환 |
| Long-running | 영속 컨테이너에 여러 SDK 프로세스. HTTP/WS 엔드포인트 노출. TS는 `streamInput()`/`startup()`, PY는 `ClaudeSDKClient`로 세션 유지 | 이메일 트리아지, 사이트 빌더, Slack 봇 |
| Hybrid | `SessionStore`에서 hydrate하는 ephemeral 컨테이너. 유휴 시 다운 | 간헐적 PM, 장시간 리서치, 고객 지원 |
| Multi-agent | 한 컨테이너에 여러 SDK 서브프로세스. 에이전트별 cwd·설정 격리 | 멀티에이전트 시뮬레이션 |

### 런타임·리소스·네트워크

- **런타임**: Python 3.10+ 또는 Node.js 18+. 두 SDK 패키지가 플랫폼별 네이티브 Claude Code 바이너리를 번들하므로 별도 설치 불필요. 바이너리는 SDK 패키지 버전에 고정 — SDK 업데이트가 곧 CLI 업데이트(semver 준수).
- **리소스**: 신규 인스턴스 기준 에이전트당 1 GiB RAM, 5 GiB 디스크, 1 CPU가 합리적 출발점(바닥값이지 천장이 아님). 메모리는 세션 길이·도구 활동에 따라 증가.
- **네트워크**: `api.anthropic.com`(또는 Bedrock/Vertex 지역 엔드포인트)로 outbound HTTPS 필요. inbound는 컨테이너에 HTTP/WS 포트 노출(서브프로세스 자체는 네트워크를 듣지 않음).

### 스케일링 공식

```text
agents per host = (host RAM - overhead) / (per-session RAM ceiling)
```

per-session 천장은 대표 세션을 목표 길이·도구 부하로 돌려 peak RSS 측정. Long-running은 컨테이너 풀 + 로드밸런서에서 `sessionId` consistent hashing으로 세션을 한 컨테이너에 핀.

### 멀티테넌트 격리

공유 컨테이너에서 설정·`CLAUDE.md`가 테넌트 간 누출될 수 있다. 격리:
- `settingSources: []`(TS) / `setting_sources=[]`(PY) — 파일시스템 설정 미로딩
- `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` — auto memory는 settingSources와 무관하게 로딩되므로 별도 차단
- `CLAUDE_CONFIG_DIR`를 테넌트별 디렉터리로 — `~/.claude.json` 글로벌 설정 공유 방지
- 테넌트별 `cwd` 명시
- 프록시에서 테넌트별 egress 규칙

> [!note] 알려진 한계
> 상위 세션 타임아웃 없음 → `maxTurns`로 도구 라운드트립 제한. 장기 세션 메모리 증가 → 길이 제한·서브프로세스 주기적 재활용. 대규모 병렬 서브에이전트 fanout은 rate limit 우려 → 작은 배치로 분할. 서브에이전트별 벽시계 데드라인 없음 → 각 서브에이전트 `AgentDefinition`에 `maxTurns`, 백그라운드 서브에이전트만 `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` 스톨 워치독.

배포 코드(Docker/Modal/Kubernetes)는 [hosting cookbook](https://github.com/anthropics/claude-cookbooks/tree/main/claude_agent_sdk/hosting). (클라우드 프로바이더 일반론은 [[17 클라우드 프로바이더]].)

---

## 보안 배포

Claude Code·Agent SDK는 코드 실행·파일 접근·외부 서비스 상호작용이 가능하다. 전통 SW와 달리 컨텍스트·목표에 따라 행동을 동적 생성하므로, 처리하는 콘텐츠(파일·웹페이지·입력)에 행동이 영향받을 수 있다(**prompt injection**). 핵심 원칙은 일반 semi-trusted 코드 실행과 동일: **격리(isolation), 최소 권한(least privilege), 심층 방어(defense in depth)**.

### 내장 보안 기능

- **권한 시스템**: 모든 도구·bash 명령을 allow/block/prompt로 설정. glob 패턴 규칙. 조직 정책 가능 → [[05 권한]]
- **Bash 명령 파싱**: 실행 전 AST로 파싱해 권한 규칙 매칭. 깨끗이 파싱 안 되거나 allow 미매칭이면 명시 승인 필요. `eval` 등은 항상 승인. (샌드박스가 아닌 권한 게이트)
- **웹 검색 요약**: raw 콘텐츠 대신 요약을 컨텍스트에 넣어 웹 prompt injection 위험 감소
- **Sandbox mode**: bash 명령을 파일시스템·네트워크 제한 샌드박스에서 실행 → [[18 보안과 샌드박스]]

### 격리 기술 비교

| 기술 | 격리 강도 | 성능 오버헤드 | 복잡도 |
| :-- | :-- | :-- | :-- |
| Sandbox runtime | Good (보안 기본값) | Very low | Low |
| Containers (Docker) | 설정 의존 | Low | Medium |
| gVisor | Excellent (정확 설정 시) | Medium/High | Medium |
| VMs (Firecracker, QEMU) | Excellent (정확 설정 시) | High | Medium/High |

- **Sandbox runtime**: [`sandbox-runtime`](https://github.com/anthropic-experimental/sandbox-runtime)이 OS 레벨에서 파일시스템·네트워크 제한(Linux `bubblewrap`, macOS `sandbox-exec`/Seatbelt). 빌트인 프록시. `npm install @anthropic-ai/sandbox-runtime` 후 JSON allowlist 작성. 한계: 호스트 커널 공유, TLS 검사 없음(domain fronting 가능).
- **gVisor**: userspace에서 syscall 가로채기. `runsc` 런타임 설치 후 `docker run --runtime=runsc`. CPU 바운드 ~0%, 단순 syscall ~2배, 파일 I/O 집중은 10-200배 느림.
- **VM (Firecracker)**: 하드웨어 레벨 격리, microVM 부팅 <125ms. `vsock`으로 통신.

### 하드닝된 컨테이너 예시

```bash
docker run \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --security-opt seccomp=/path/to/seccomp-profile.json \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  --network none \
  --memory 2g --cpus 2 --pids-limit 100 \
  --user 1000:1000 \
  -v /path/to/code:/workspace:ro \
  -v /var/run/proxy.sock:/var/run/proxy.sock:ro \
  agent-image
```

| 옵션 | 목적 |
| :-- | :-- |
| `--cap-drop ALL` | `NET_ADMIN`·`SYS_ADMIN` 등 권한 상승 가능 capability 제거 |
| `--security-opt no-new-privileges` | setuid 바이너리로 권한 획득 방지 |
| `--read-only` | 루트 파일시스템 불변화 |
| `--tmpfs /tmp:...` | 컨테이너 중지 시 비워지는 쓰기 가능 임시 디렉터리 |
| `--network none` | 네트워크 인터페이스 완전 제거(아래 Unix 소켓으로만 통신) |
| `--pids-limit 100` | fork bomb 방지 |
| `-v ...:/workspace:ro` | 코드 읽기 전용 마운트. **`~/.ssh`·`~/.aws`·`~/.config` 같은 민감 디렉터리 마운트 금지** |

**Unix 소켓 아키텍처**: `--network none`이면 마운트된 Unix 소켓(호스트 프록시 연결)만이 외부 통로. prompt injection으로 에이전트가 손상돼도 프록시 허용 도메인으로만 통신 가능.

### 자격증명 관리: 프록시 패턴

권장 방식은 에이전트 보안 경계 **밖**에서 프록시가 outbound 요청에 자격증명을 주입하는 것. 에이전트는 자격증명 없이 요청, 프록시가 추가·전달. 이점: 에이전트가 실제 자격증명을 못 봄, 엔드포인트 allowlist 강제, 요청 감사 로깅, 한 곳에 집중 저장.

Claude API 라우팅 두 방법:

| 방법 | 환경변수 | 특징 |
| :-- | :-- | :-- |
| ANTHROPIC_BASE_URL | `export ANTHROPIC_BASE_URL="http://localhost:8080"` | sampling 요청만. 프록시가 plaintext HTTP 검사·수정 가능 |
| HTTP_PROXY/HTTPS_PROXY | `export HTTP_PROXY=... HTTPS_PROXY=...` | 시스템 전역. HTTPS는 CONNECT 터널이라 TLS 가로채기 없이는 내용 못 봄 |

프록시 구현체: [Envoy](https://www.envoyproxy.io/)(`credential_injector` 필터), [mitmproxy](https://mitmproxy.org/)(TLS 터미네이팅), [Squid](http://www.squid-cache.org/), [LiteLLM](https://github.com/BerriAI/litellm). 다른 서비스(git·npm·내부 API)는 ① 보안 경계 밖에서 인증하는 **custom tool/MCP 서버**, 또는 ② **TLS 터미네이팅 프록시**(프록시 CA 인증서를 trust store에 설치). Node.js `fetch()`는 기본적으로 `HTTP_PROXY`를 무시 → Node 24+에서 `NODE_USE_ENV_PROXY=1`.

### 파일시스템 제어

읽기 전용 마운트라도 자격증명 노출 위험: `.env`·`~/.git-credentials`·`~/.aws/credentials`·`~/.kube/config`·`.npmrc`·`*.pem`/`*.key` 등은 제외·sanitize. 필요한 소스만 복사하거나 `.dockerignore`식 필터링. 쓰기는 ephemeral은 `tmpfs`, 검토 후 영속은 overlay 파일시스템, 완전 영속은 전용 볼륨(민감 디렉터리와 분리). 클라우드는 private subnet + 방화벽으로 프록시 외 egress 차단 + 최소 IAM. (보안·샌드박스 일반론은 [[18 보안과 샌드박스]].)

---

## TypeScript SDK 레퍼런스 (핵심)

> 전체 시그니처·세부 타입은 [TypeScript SDK reference](https://code.claude.com/docs/en/agent-sdk/typescript)에 위임. 여기서는 주요 entry point만.

설치: `npm install @anthropic-ai/claude-agent-sdk`. 네이티브 Claude Code 바이너리를 optional dependency로 번들(예: `@anthropic-ai/claude-agent-sdk-darwin-arm64`). optional deps를 건너뛰면 `Native CLI binary for <platform> not found` 발생 → `pathToClaudeCodeExecutable`로 별도 설치 바이너리 지정. `bun build --compile` 단일 실행파일은 `extractFromBunfs()`로 바이너리를 추출해 경로 전달(SDK v0.3.144+).

### 주요 함수

| 함수 | 시그니처(요약) | 용도 |
| :-- | :-- | :-- |
| `query()` | `query({ prompt: string \| AsyncIterable<SDKUserMessage>, options?: Options }): Query` | 핵심. 메시지 스트림 async generator |
| `startup()` | `startup(params?: { options?, initializeTimeoutMs? }): Promise<WarmQuery>` | 서브프로세스 사전 워밍(spawn+initialize). 첫 호출 지연 제거 |
| `tool()` | `tool(name, description, inputSchema: ZodRawShape, handler, extras?)` | 타입 안전 MCP 도구 정의(Zod 3·4) |
| `createSdkMcpServer()` | `createSdkMcpServer({ name, version?, tools? })` | 같은 프로세스 내 in-process MCP 서버 |
| `listSessions()` / `getSessionMessages()` / `getSessionInfo()` | — | 과거 세션 목록·메시지·메타데이터 조회 |
| `renameSession()` / `tagSession()` | — | 세션 제목·태그 부여(최신 호출 우선) |
| `resolveSettings()` | `resolveSettings(options?): Promise<ResolvedSettings>` | *Alpha.* CLI를 띄우지 않고 유효 설정·소스 출처 해석 |

```typescript
import { startup } from "@anthropic-ai/claude-agent-sdk";
const warm = await startup({ options: { maxTurns: 3 } });   // 부팅 시 비용 선결제
for await (const message of warm.query("What files are here?")) { console.log(message); }
```

```typescript
import { tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
const searchTool = tool("search", "Search the web", { query: z.string() },
  async ({ query }) => ({ content: [{ type: "text", text: `Results for: ${query}` }] }),
  { annotations: { readOnlyHint: true, openWorldHint: true } });
```

### `Options` 주요 필드 (발췌)

전체 필드는 원본 표 참조. 자주 쓰는 것:

| 필드 | 타입 | 설명 |
| :-- | :-- | :-- |
| `allowedTools` / `disallowedTools` | `string[]` | 자동 승인 / 거부. allowedTools는 제한이 아님(미목록 도구는 permissionMode로 fall-through) |
| `tools` | `string[] \| { type:'preset', preset:'claude_code' }` | 도구 구성 |
| `systemPrompt` | `string \| { type:'preset', preset:'claude_code', append?, excludeDynamicSections? }` | 시스템 프롬프트 |
| `permissionMode` | `PermissionMode` | `'default'` 기본 |
| `canUseTool` | `CanUseTool` | 커스텀 권한 함수 |
| `maxTurns` / `maxBudgetUsd` | `number` | 에이전트 턴 / 비용(추정치) 상한 |
| `outputFormat` | `{ type:'json_schema', schema }` | 구조화 출력 |
| `includePartialMessages` | `boolean` | 출력 스트리밍 |
| `agents` | `Record<string, AgentDefinition>` | 서브에이전트 프로그램 정의 |
| `mcpServers` / `strictMcpConfig` | — | MCP 서버 구성 / 외부 소스 무시 |
| `settingSources` | `SettingSource[]` | 로딩할 파일시스템 설정(`[]`이면 비활성, managed policy는 무관) |
| `sessionStore` / `resume` / `forkSession` | — | 외부 저장 미러 / 재개 / 포크 |
| `env` | `Record<string,string>` | **상속 환경 대체** → `{ ...process.env, ... }` 필요 |
| `effort` / `thinking` | — | `'low'~'max'` 노력 수준 / thinking 설정(`maxThinkingTokens`는 deprecated) |

타임아웃·스톨 제어 env: `API_TIMEOUT_MS`(기본 600000), `CLAUDE_CODE_MAX_RETRIES`(기본 10), `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS`(백그라운드 서브에이전트), `CLAUDE_ENABLE_STREAM_WATCHDOG=1`+`CLAUDE_STREAM_IDLE_TIMEOUT_MS`.

### `Query` 객체 메서드 (발췌)

`query()`가 반환하는 `AsyncGenerator<SDKMessage, void>` 확장. streaming input 모드 전용 메서드 다수.

| 메서드 | 설명 |
| :-- | :-- |
| `interrupt()` | 쿼리 인터럽트(streaming input 전용) |
| `setPermissionMode()` / `setModel()` | 권한 모드 / 모델 변경(streaming input 전용) |
| `applyFlagSettings(settings)` | 런타임에 설정 머지. `model`·`permissions`·`hooks`·`agent` 등은 다음 턴 적용, 시스템 프롬프트는 효과 없음. `null`로 키 클리어. **TS 전용** |
| `streamInput(stream)` | 멀티턴용 입력 스트림 추가 |
| `rewindFiles(userMessageId, { dryRun? })` | 파일 체크포인트 복원(`enableFileCheckpointing: true` 필요) |
| `supportedCommands()`/`supportedModels()`/`supportedAgents()`/`mcpServerStatus()`/`accountInfo()` | 초기화 정보·역량 조회 |
| `setMcpServers()`/`reconnectMcpServer()`/`toggleMcpServer()` | MCP 서버 동적 관리 |
| `stopTask(taskId)` / `close()` | 백그라운드 태스크 중지 / 쿼리 종료 |

`WarmQuery`(startup 반환)는 `AsyncDisposable` — `await using`으로 자동 정리. `query(prompt)`는 WarmQuery당 1회만.

---

## Python SDK 레퍼런스 (핵심)

> 전체 시그니처·세부 타입은 [Python SDK reference](https://code.claude.com/docs/en/agent-sdk/python)에 위임.

### `query()` vs `ClaudeSDKClient`

| 기능 | `query()` | `ClaudeSDKClient` |
| :-- | :-- | :-- |
| 세션 | 기본 새 세션 | 같은 세션 재사용 |
| 대화 | 단일 교환 | 같은 컨텍스트 다중 교환 |
| 연결 | 자동 관리 | 수동 제어 |
| 인터럽트 | ❌ | ✅ |
| 대화 이어가기 | `continue_conversation`/`resume` 수동 | 자동 |
| 용도 | one-off 작업 | 연속 대화·인터랙티브 앱·응답 기반 로직 |

```python
async def query(*, prompt: str | AsyncIterable[dict[str, Any]],
                options: ClaudeAgentOptions | None = None,
                transport: Transport | None = None) -> AsyncIterator[Message]
```

```python
options = ClaudeAgentOptions(
    system_prompt="You are an expert Python developer",
    permission_mode="acceptEdits", cwd="/home/user/project")
async for message in query(prompt="Create a Python web server", options=options):
    print(message)
```

### `tool()` 데코레이터 / `create_sdk_mcp_server()`

```python
@tool("greet", "Greet a user", {"name": str})       # 단순 타입 매핑(권장)
async def greet(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}

calculator = create_sdk_mcp_server(name="calculator", version="2.0.0", tools=[add, multiply])
options = ClaudeAgentOptions(mcp_servers={"calc": calculator},
                             allowed_tools=["mcp__calc__add", "mcp__calc__multiply"])
```

`input_schema`는 단순 타입 매핑(`{"text": str, "count": int}`) 또는 JSON Schema dict. (커스텀 도구 상세는 [[23 Agent SDK — 핵심 기능]].)

### `ClaudeSDKClient` 주요 메서드

```python
async with ClaudeSDKClient(options=options) as client:   # async context manager
    await client.query("What's the capital of France?")
    async for message in client.receive_response():       # ResultMessage까지 수신
        ...
    await client.query("What's the population of that city?")  # 같은 세션 컨텍스트 유지
```

| 메서드 | 설명 |
| :-- | :-- |
| `connect(prompt?)` / `disconnect()` | 연결 / 해제 |
| `query(prompt, session_id="default")` | streaming 모드로 요청 전송 |
| `receive_messages()` / `receive_response()` | 전체 메시지 / ResultMessage까지 수신 |
| `interrupt()` | 인터럽트(streaming 전용) |
| `set_permission_mode()` / `set_model(None=reset)` | 권한 모드 / 모델 변경 |
| `rewind_files(user_message_id)` | 파일 체크포인트 복원(`enable_file_checkpointing=True`) |
| `get_mcp_status()` / `reconnect_mcp_server()` / `toggle_mcp_server()` | MCP 서버 관리 |
| `stop_task(task_id)` / `get_server_info()` | 백그라운드 태스크 중지 / 세션 정보 |

> [!warning] 인터럽트 후 버퍼 / break 주의
> `interrupt()`는 stop 신호를 보내지만 메시지 버퍼를 비우지 않는다. 인터럽트된 태스크의 메시지(`subtype="error_during_execution"`인 `ResultMessage` 포함)가 스트림에 남으므로, 새 쿼리 전에 `receive_response()`로 드레인해야 한다. 또한 메시지 순회 중 `break`로 조기 탈출하면 asyncio cleanup 문제가 생길 수 있으니 자연 종료하거나 플래그를 쓴다.

> [!note] dataclass vs TypedDict
> `@dataclass`(`ResultMessage`, `AgentDefinition`, `TextBlock` 등)는 런타임 객체로 속성 접근(`msg.result`). `TypedDict`(`ThinkingConfigEnabled`, `McpStdioServerConfig` 등)는 런타임에 plain dict이므로 키 접근(`config["budget_tokens"]`).

### `ClaudeAgentOptions` 주요 필드

TS `Options`와 1:1 대응하되 snake_case. 주요: `tools`, `allowed_tools`, `disallowed_tools`, `system_prompt`(str 또는 `{"type":"preset","preset":"claude_code","append":...}`), `mcp_servers`, `strict_mcp_config`, `permission_mode`, `continue_conversation`/`resume`/`fork_session`, `max_turns`/`max_budget_usd`, `model`/`fallback_model`, `output_format`, `can_use_tool`, `hooks`, `agents`, `setting_sources`, `skills`, `sandbox`, `plugins`, `include_partial_messages`, `thinking`/`effort`, `enable_file_checkpointing`, `session_store`/`session_store_flush`, `env`(상속 환경 위에 **머지**), `cwd`, `cli_path`.

> [!note] PY에 없는 것
> `applyFlagSettings()`(TS 전용), 프로그램으로 output style 선택 옵션(`append`/custom string 사용). 타임아웃 env는 TS와 동일하게 `env`로 전달.

---

## V2 세션 API (제거됨)

> [!warning] 더 이상 지원 안 됨
> TypeScript Agent SDK 0.3.142가 `unstable_v2_createSession`, `unstable_v2_resumeSession`, `unstable_v2_prompt`, `SDKSession`/`SDKSessionOptions` 타입을 제거했다. 마이그레이션: `query()` API + 세션 옵션 사용. 멀티턴은 `AsyncIterable<SDKUserMessage>` 전달, 저장 세션 재개는 `options.resume`. 0.2.x 이하 코드 유지보수용으로만 참조.

V2는 async generator·yield 조정 없이 매 턴을 별도 `send()`/`stream()` 사이클로 만든 실험적 세션 API였다. 마지막 V2 호환 릴리스 설치: `npm install @anthropic-ai/claude-agent-sdk@0.2`. API는 `createSession()`/`resumeSession()`, `session.send()`, `session.stream()` 세 개념으로 축소됐고 `await using`(TS 5.2+) 자동 정리를 지원했다. V2는 세션 포크(`forkSession`)와 일부 고급 streaming input 패턴을 지원하지 않았다.

```typescript
// (제거됨) 참고용
await using session = unstable_v2_createSession({ model: "claude-opus-4-7" });
await session.send("What is 5 + 3?");
for await (const msg of session.stream()) { /* ... */ }
```

---

## 원본 문서

- https://code.claude.com/docs/en/agent-sdk/streaming-output
- https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode
- https://code.claude.com/docs/en/agent-sdk/structured-outputs
- https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts
- https://code.claude.com/docs/en/agent-sdk/observability
- https://code.claude.com/docs/en/agent-sdk/cost-tracking
- https://code.claude.com/docs/en/agent-sdk/hosting
- https://code.claude.com/docs/en/agent-sdk/secure-deployment
- https://code.claude.com/docs/en/agent-sdk/typescript
- https://code.claude.com/docs/en/agent-sdk/typescript-v2-preview
- https://code.claude.com/docs/en/agent-sdk/python
