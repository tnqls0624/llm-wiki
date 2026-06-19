---
title: 16 CI-CD와 팀 통합
updated: 2026-06-07
type: reference
sources: [github-actions, github-enterprise-server, gitlab-ci-cd, code-review, slack]
---

# 16 CI-CD와 팀 통합

Claude Code를 팀의 협업 인프라(GitHub/GitLab CI, 자체 호스팅 GHES, 자동 코드 리뷰, Slack)에 통합하는 레퍼런스다. 핵심 관문은 두 가지다. (1) **CI에서 Claude를 직접 실행**하는 방식 — `anthropics/claude-code-action`(GitHub Actions), `.gitlab-ci.yml` 잡(GitLab) — 은 자기 러너에서 돌고 자기 비용으로 청구된다. (2) **Anthropic이 운영하는 매니지드 서비스** — Code Review, Slack 통합 — 은 Anthropic 인프라에서 돌고 토큰 사용량 기준으로 청구된다. 어느 경로든 `CLAUDE.md`가 프로젝트 표준을 주입하는 공통 메커니즘이다. 메모리/컨텍스트는 [[03 메모리와 컨텍스트]], 권한 모델은 [[05 권한]], 클라우드 프로바이더 인증은 [[17 클라우드 프로바이더]], 웹/원격 세션은 [[15 웹과 모바일]]을 참고하라.

> [!info] 모델 기본값
> Claude Code GitHub Actions의 기본 모델은 **Sonnet**이다. Opus 4.8을 쓰려면 `claude_args: --model claude-opus-4-8`로 지정한다.

---

## GitHub Actions — `@claude` 자동화

`anthropics/claude-code-action`은 PR/이슈에서 `@claude` 멘션으로 Claude를 호출하거나, 프롬프트를 주어 즉시 실행시키는 GitHub Action이다. 코드는 GitHub 러너에 머무르며(secure by default), `CLAUDE.md` 가이드라인을 따른다. 이 Action은 [[22 Agent SDK — 시작]] 위에 구축되어 있어, SDK로 더 커스텀한 자동화도 만들 수 있다.

- 트리거 없이 모든 PR에 자동 리뷰만 원한다면 이 페이지 아래의 [Code Review](#code-review--매니지드-자동-pr-리뷰) 매니지드 서비스를 쓰는 게 낫다.
- 저장소: https://github.com/anthropics/claude-code-action

### Quick setup vs Manual setup

| 방식 | 절차 | 비고 |
|------|------|------|
| Quick setup | 터미널에서 `claude` 실행 후 `/install-github-app` | GitHub App + 시크릿을 가이드대로 설치. **저장소 admin 권한 필요**. **직접 Claude API 사용자 전용** (Bedrock/Vertex는 수동 설정) |
| Manual setup | (1) GitHub App 설치 https://github.com/apps/claude (2) `ANTHROPIC_API_KEY`를 저장소 시크릿에 추가 (3) `examples/claude.yml`을 `.github/workflows/`로 복사 | `/install-github-app`이 실패하거나 수동을 선호할 때 |

GitHub App이 요구하는 저장소 권한: **Contents (Read & write)**, **Issues (Read & write)**, **Pull requests (Read & write)**. 설정 후 이슈/PR 댓글에서 `@claude`로 멘션해 테스트한다(`/claude` 아님).

### v1.0 마이그레이션 (베타 → GA)

v1.0은 워크플로 파일 수정이 필요한 breaking change를 포함한다. 베타 사용자는 다음 4가지를 반드시 바꿔야 한다.

1. 액션 버전: `@beta` → `@v1`
2. `mode: "tag"` / `mode: "agent"` 삭제 (이제 자동 감지)
3. `direct_prompt` → `prompt`
4. `max_turns`, `model`, `custom_instructions` 등 CLI 옵션을 `claude_args`로 이동

| 구 베타 입력 | 신 v1.0 입력 |
|---|---|
| `mode` | *(삭제 — 자동 감지)* |
| `direct_prompt` | `prompt` |
| `override_prompt` | `prompt` + GitHub 변수 |
| `custom_instructions` | `claude_args: --append-system-prompt` |
| `max_turns` | `claude_args: --max-turns` |
| `model` | `claude_args: --model` |
| `allowed_tools` | `claude_args: --allowedTools` |
| `disallowed_tools` | `claude_args: --disallowedTools` |
| `claude_env` | `settings` JSON 형식 |

Before/After 예시:

```yaml
# Beta
- uses: anthropics/claude-code-action@beta
  with:
    mode: "tag"
    direct_prompt: "Review this PR for security issues"
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    custom_instructions: "Follow our coding standards"
    max_turns: "10"
    model: "claude-sonnet-4-6"

# GA (v1.0)
- uses: anthropics/claude-code-action@v1
  with:
    prompt: "Review this PR for security issues"
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    claude_args: |
      --append-system-prompt "Follow our coding standards"
      --max-turns 10
      --model claude-sonnet-4-6
```

v1.0은 설정에 따라 **interactive 모드**(`@claude` 멘션 응답)와 **automation 모드**(프롬프트로 즉시 실행)를 자동 감지한다.

### Action 파라미터 레퍼런스

| 파라미터 | 설명 | 필수 |
|---|---|---|
| `prompt` | Claude에게 줄 지시 (평문 또는 [skill](#skill-호출) 이름) | No* |
| `claude_args` | Claude Code CLI 인자 패스스루 | No |
| `plugin_marketplaces` | 줄바꿈 구분 플러그인 마켓플레이스 Git URL 목록 | No |
| `plugins` | 실행 전 설치할 플러그인 이름 목록 (줄바꿈 구분) | No |
| `anthropic_api_key` | Claude API 키 | Yes** |
| `github_token` | API 접근용 GitHub 토큰 | No |
| `trigger_phrase` | 커스텀 트리거 문구 (기본값 `@claude`) | No |
| `use_bedrock` | Claude API 대신 Amazon Bedrock 사용 | No |
| `use_vertex` | Claude API 대신 Google Vertex AI 사용 | No |

\* 이슈/PR 댓글에서 prompt 생략 시 트리거 문구에 반응. \*\* 직접 Claude API에서만 필수, Bedrock/Vertex는 불필요.

`claude_args`로 넘기는 주요 CLI 인자 (전체는 [[02 CLI 레퍼런스]]):

| 인자 | 설명 |
|---|---|
| `--max-turns` | 최대 대화 턴 수 (기본값 10) |
| `--model` | 사용할 모델 (예: `claude-sonnet-4-6`) |
| `--mcp-config` | MCP 설정 경로 ([[10 MCP]]) |
| `--allowedTools` | 허용 도구 콤마 구분 목록 (`--allowed-tools` 별칭도 동작) |
| `--debug` | 디버그 출력 활성화 |

```yaml
claude_args: "--max-turns 5 --model claude-sonnet-4-6 --mcp-config /path/to/config.json"
```

### 워크플로 예시

**기본 워크플로 (`@claude` 멘션 응답):**

```yaml
name: Claude Code
on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
jobs:
  claude:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          # Responds to @claude mentions in comments
```

**Skill 호출** — `prompt`는 [[07 스킬]] 호출도 받는다. 저장소의 `.claude/skills/`에 있는 스킬은 `actions/checkout`을 먼저 돌린 뒤 `/skill-name`을 넘기고, 플러그인 패키지된 스킬은 `plugin_marketplaces`/`plugins`로 설치한 뒤 네임스페이스 형식 `/plugin-name:skill-name`을 넘긴다.

```yaml
name: Code Review
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          plugin_marketplaces: "https://github.com/anthropics/claude-code.git"
          plugins: "code-review@claude-code-plugins"
          prompt: "/code-review:code-review ${{ github.repository }}/pull/${{ github.event.pull_request.number }}"
```

**스케줄 기반 커스텀 자동화** ([[13 자동화와 스케줄링]] 참고):

```yaml
name: Daily Report
on:
  schedule:
    - cron: "0 9 * * *"
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Generate a summary of yesterday's commits and open issues"
          claude_args: "--model opus"
```

**댓글 안에서 흔한 사용 패턴:**

```text
@claude implement this feature based on the issue description
@claude how should I implement user authentication for this endpoint?
@claude fix the TypeError in the user dashboard component
```

### Bedrock / Vertex AI 인증 (엔터프라이즈)

엔터프라이즈에서는 자체 클라우드 인프라로 Claude Code Action을 돌려 데이터 거주지·청구를 통제할 수 있다. 인증 모델 자체는 [[17 클라우드 프로바이더]]를 참고하고, 여기서는 GitHub Actions 관점의 핵심만 정리한다.

권장 흐름은 **자체 GitHub App을 만들어** OIDC로 인증하는 것이다(정적 키 없음). 자체 App을 만들면 `actions/create-github-app-token` 액션으로 워크플로 안에서 토큰을 생성한다. 자체 App을 원치 않으면 공식 Anthropic App(https://github.com/apps/claude)을 쓴다.

필요한 시크릿:

| 프로바이더 | 시크릿 |
|---|---|
| Claude API | `ANTHROPIC_API_KEY` (+ 자체 App 시 `APP_ID`, `APP_PRIVATE_KEY`) |
| Amazon Bedrock | `AWS_ROLE_TO_ASSUME` (+ `APP_ID`, `APP_PRIVATE_KEY`) |
| Google Vertex AI | `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT` (+ `APP_ID`, `APP_PRIVATE_KEY`) |

- **Bedrock**: GitHub을 OIDC IdP(`https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`)로 등록 → `AmazonBedrockFullAccess` IAM Role 생성 → trust policy를 해당 저장소로 제한. OIDC는 정적 키보다 안전하다(임시·자동 로테이션). 모델 ID는 리전 프리픽스를 포함(`us.anthropic.claude-sonnet-4-6`).
- **Vertex AI**: IAM Credentials / STS / Vertex AI API 활성화 → Workload Identity Pool + GitHub OIDC provider → `Vertex AI User` 롤만 가진 전용 서비스 계정 → IAM 바인딩으로 풀이 SA를 임퍼소네이트. WIF는 다운로드 키가 불필요하다. project ID는 인증 단계에서 자동 추출된다.

**Bedrock 워크플로 (요지):** `actions/checkout` → `actions/create-github-app-token@v2` → `aws-actions/configure-aws-credentials@v4`(role-to-assume) → `claude-code-action@v1`에 `use_bedrock: "true"`. `id-token: write` 권한과 `AWS_REGION` env 필요.

```yaml
      - uses: anthropics/claude-code-action@v1
        with:
          github_token: ${{ steps.app-token.outputs.token }}
          use_bedrock: "true"
          claude_args: '--model us.anthropic.claude-sonnet-4-6 --max-turns 10'
```

**Vertex AI 워크플로 (요지):** `google-github-actions/auth@v2`(workload_identity_provider + service_account) 후 `use_vertex: "true"`. 관련 env: `ANTHROPIC_VERTEX_PROJECT_ID`, `CLOUD_ML_REGION`, `VERTEX_REGION_CLAUDE_4_5_SONNET`.

```yaml
      - uses: anthropics/claude-code-action@v1
        with:
          github_token: ${{ steps.app-token.outputs.token }}
          trigger_phrase: "@claude"
          use_vertex: "true"
          claude_args: '--model claude-sonnet-4-5@20250929 --max-turns 10'
        env:
          ANTHROPIC_VERTEX_PROJECT_ID: ${{ steps.auth.outputs.project_id }}
          CLOUD_ML_REGION: us-east5
          VERTEX_REGION_CLAUDE_4_5_SONNET: us-east5
```

### 베스트 프랙티스 · 비용 · 트러블슈팅

- **`CLAUDE.md`**: 저장소 루트에 두어 코드 스타일·리뷰 기준·프로젝트 규칙을 정의 ([[03 메모리와 컨텍스트]]). 간결하게 유지.
- **보안**: API 키를 절대 커밋하지 말고 항상 GitHub Secrets(`${{ secrets.ANTHROPIC_API_KEY }}`)로 참조. 액션 권한은 최소화하고, Claude 제안은 머지 전 검토. (전반적 보안은 [[18 보안과 샌드박스]])
- **비용** ([[19 비용과 성능]] 참고): GitHub 러너 분(minutes) + Claude API 토큰 두 축으로 발생. 절감 팁 — 구체적인 `@claude` 명령으로 불필요한 호출 줄이기, `--max-turns` 설정, 워크플로 타임아웃 설정, GitHub concurrency 제어로 병렬 실행 제한.

| 증상 | 점검 |
|---|---|
| `@claude`에 무응답 | GitHub App 설치 확인, 워크플로 활성화, 시크릿에 API 키, 댓글에 `@claude`(`/claude` 아님) |
| Claude 커밋에 CI 미실행 | Actions user가 아닌 GitHub App/커스텀 App 사용, 워크플로 트리거 이벤트 포함, App 권한에 CI 트리거 포함 |
| 인증 에러 | API 키 유효성·권한 확인, Bedrock/Vertex는 자격증명 구성과 시크릿 이름 확인 |

---

## GitHub Enterprise Server (GHES)

GHES 지원은 github.com 대신 **자체 관리 GitHub 인스턴스**의 저장소로 Claude Code를 쓰게 한다. **Team·Enterprise 플랜 전용.** admin이 GHES 인스턴스를 한 번 연결하면, 개발자는 저장소별 설정 없이 웹 세션·자동 코드 리뷰·내부 마켓플레이스 플러그인을 쓸 수 있다.

### GHES 기능 지원 매트릭스

| 기능 | 지원 | 비고 |
|---|---|---|
| Claude Code on the web | ✅ | admin이 한 번 연결, `claude --remote` 또는 claude.ai/code 사용 |
| Code Review | ✅ | github.com과 동일한 자동 PR 리뷰 |
| Claude Security | ✅ | Enterprise 플랜 공개 베타, claude.ai/security |
| Teleport sessions | ✅ | `--teleport`로 웹↔터미널 세션 이동 |
| Plugin marketplaces | ✅ | `owner/repo` 약칭 대신 전체 git URL 사용 |
| Contribution metrics | ✅ | 웹훅으로 analytics 대시보드 전달 |
| GitHub Actions | ✅ | 워크플로 수동 설정 필요, `/install-github-app`은 github.com 전용 |
| GitHub MCP server | ❌ | GHES 인스턴스에서 동작하지 않음 |

> [!warning] GitHub MCP 서버 미지원
> GHES에서는 GitHub MCP 서버가 동작하지 않는다. 대신 `gh` CLI를 GHES 호스트로 설정해 쓴다: `gh auth login --hostname github.example.com`. 그러면 세션에서 Claude가 `gh` 명령을 쓸 수 있다. (MCP 일반은 [[10 MCP]])

### Admin 설정

admin이 Claude 조직 admin 권한과 GHES 인스턴스에 GitHub App 생성 권한을 갖고 한 번 연결한다. 가이드 설정은 GitHub App manifest를 생성해 GHES로 리다이렉트하여 원클릭 생성을 유도한다(리다이렉트가 막히면 manual setup).

1. **claude.ai/admin-settings/claude-code** → GitHub Enterprise Server 섹션
2. **Connect** → 표시명 + GHES 호스트명(예: `github.example.com`) 입력. 자체 서명/사설 CA면 CA 인증서를 선택 입력란에 붙여넣기
3. **Continue to GitHub Enterprise** → GHES로 리다이렉트, manifest 검토 후 **Create GitHub App** → 자격증명 자동 저장
4. GHES의 GitHub App 페이지에서 대상 저장소/조직에 App 설치 (서브셋으로 시작해 나중에 추가 가능)
5. admin-settings로 돌아와 Code Review, Claude Security, contribution metrics 활성화

**GitHub App 권한** (manifest가 자동 구성):

| 권한 | 접근 | 용도 |
|---|---|---|
| Contents | Read & write | 저장소 클론·브랜치 푸시 |
| Pull requests | Read & write | PR 생성·리뷰 댓글 게시 |
| Issues | Read & write | 이슈 멘션 응답 |
| Checks | Read & write | Code Review check run 게시 |
| Actions | Read | auto-fix용 CI 상태 읽기 |
| Repository hooks | Read & write | contribution metrics 웹훅 수신 |
| Metadata | Read | 모든 App에 GitHub 필수 |

구독 이벤트: `pull_request`, `issue_comment`, `pull_request_review_comment`, `pull_request_review`, `check_run`.

- **Manual setup**: 리다이렉트가 막히면 Connect 대신 **Add manually**. GHES에 App을 직접 만들고 위 권한·이벤트를 설정한 뒤 호스트명, OAuth client ID/secret, App ID, client ID/secret, webhook secret, private key를 입력.
- **네트워크 요건**: GHES 인스턴스가 Anthropic 인프라에서 도달 가능해야 한다(클론·리뷰 댓글 게시). 방화벽 뒤라면 [Anthropic API IP 주소](https://platform.claude.com/docs/en/api/ip-addresses)를 allowlist. ([[18 보안과 샌드박스]])

### 개발자 워크플로

admin 연결 후 개발자는 추가 설정이 없다. Claude Code가 작업 디렉터리의 git remote에서 GHES 호스트명을 **자동 감지**한다.

```bash
git clone git@github.example.com:platform/api-service.git
cd api-service
# Claude가 git remote에서 GHES 호스트를 감지해 세션을 조직 인스턴스로 라우팅
claude --remote "Add retry logic to the payment webhook handler"
```

세션은 Anthropic 인프라에서 돌며 GHES에서 클론하고 브랜치로 변경을 푸시한다. 진행 상황은 `/tasks` 또는 claude.ai/code에서 모니터링. 전체 원격 세션 워크플로(diff 리뷰, auto-fix, routines)는 [[15 웹과 모바일]] 참고.

- **Teleport**: `claude --teleport`로 웹 세션을 로컬 터미널로 끌어온다. 같은 GHES 저장소 체크아웃인지 검증 후 브랜치를 fetch하고 세션 히스토리를 로드한다.

### GHES 플러그인 마켓플레이스

GHES에 마켓플레이스를 호스팅해 내부 도구를 조직에 배포한다 ([[11 플러그인]]). 구조는 github.com과 동일, 참조 방식만 다르다. `owner/repo` 약칭은 항상 github.com으로 해석되므로 **전체 git URL**을 쓴다.

```bash
/plugin marketplace add git@github.example.com:platform/claude-plugins.git
/plugin marketplace add https://github.example.com/platform/claude-plugins.git
```

[[04 설정]]의 managed settings로 마켓플레이스 소스를 제한하는 조직은, 저장소를 일일이 나열하지 않고 `hostPattern` 소스 타입으로 GHES 인스턴스 전체를 허용할 수 있다.

```json
{
  "strictKnownMarketplaces": [
    {
      "source": "hostPattern",
      "hostPattern": "^github\\.example\\.com$"
    }
  ]
}
```

수동 설정 없이 마켓플레이스가 보이도록 사전 등록도 가능하다.

```json
{
  "extraKnownMarketplaces": {
    "internal-tools": {
      "source": {
        "source": "git",
        "url": "git@github.example.com:platform/claude-plugins.git"
      }
    }
  }
}
```

### GHES 제약 · 트러블슈팅

- `/install-github-app`은 GHES 미지원 → admin setup 플로우 사용. GHES에서 GitHub Actions 워크플로를 원하면 [example workflow](https://github.com/anthropics/claude-code-action/blob/main/examples/claude.yml)를 수동 적응.
- GitHub MCP 서버 미지원 → `gh` CLI 사용.

| 증상 | 점검 |
|---|---|
| 웹 세션 클론 실패 | admin이 GHES 설정 완료했는지, App이 해당 저장소에 설치됐는지, 등록 호스트명이 git remote와 일치하는지 |
| 마켓플레이스 add 정책 에러 | 조직이 마켓플레이스 소스 제한 중 → admin에게 `hostPattern` 추가 요청 |
| GHES 인스턴스 미도달 | 방화벽이 Anthropic API IP 인바운드 허용하는지 확인 |

---

## GitLab CI/CD

GitLab 통합은 `.gitlab-ci.yml`에 잡 하나 + masked 변수 하나로 Claude를 CI/CD 잡에서 돌린다. **현재 beta**이며 **GitLab이 유지보수**한다(지원: GitLab 이슈 573776). [[22 Agent SDK — 시작]] 위에 구축. 자기 GitLab 러너에서 돌고, 브랜치 보호·승인 규칙이 그대로 적용된다.

### 동작 방식 (3단계)

1. **이벤트 기반 오케스트레이션**: GitLab이 트리거(예: 이슈/MR/리뷰 스레드의 `@claude` 멘션)를 수신 → 잡이 스레드·저장소에서 컨텍스트 수집 → 프롬프트 구성 → Claude Code 실행
2. **프로바이더 추상화**: Claude API(SaaS) / Amazon Bedrock(IAM, cross-region) / Google Vertex AI(GCP-native, WIF) 선택
3. **샌드박스 실행**: 각 상호작용이 엄격한 네트워크·파일시스템 규칙을 가진 컨테이너에서 실행. 워크스페이스 스코프 권한으로 쓰기를 제한. 모든 변경이 MR로 흘러 리뷰어가 diff를 보고 승인 규칙이 적용됨.

할 수 있는 일: 이슈/댓글에서 MR 생성·갱신, 성능 회귀 분석·최적화 제안, 브랜치에 기능 구현 후 MR, 테스트/댓글이 짚은 버그 수정, 후속 댓글에 반복 대응.

### Quick setup

1. **Settings → CI/CD → Variables**에서 `ANTHROPIC_API_KEY`를 masked(필요시 protected)로 추가
2. `.gitlab-ci.yml`에 Claude 잡 추가

```yaml
stages:
  - ai

claude:
  stage: ai
  image: node:24-alpine3.21
  rules:
    - if: '$CI_PIPELINE_SOURCE == "web"'
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
  variables:
    GIT_STRATEGY: fetch
  before_script:
    - apk update
    - apk add --no-cache git curl bash
    - curl -fsSL https://claude.ai/install.sh | bash
  script:
    - /bin/gitlab-mcp-server || true
    - echo "$AI_FLOW_INPUT for $AI_FLOW_CONTEXT on $AI_FLOW_EVENT"
    - >
      claude
      -p "${AI_FLOW_INPUT:-'Review this MR and implement the requested changes'}"
      --permission-mode acceptEdits
      --allowedTools "Bash Read Edit Write mcp__gitlab"
      --debug
```

추가 후 **CI/CD → Pipelines**에서 수동 실행하거나 MR에서 트리거해 테스트. `--permission-mode acceptEdits`와 `--allowedTools`는 [[05 권한]]·[[06 내장 도구 레퍼런스]]를 참고.

### Manual setup (프로덕션 권장)

1. **프로바이더 접근 구성**: Claude API는 `ANTHROPIC_API_KEY` masked 변수 / Bedrock은 GitLab→AWS OIDC + Bedrock IAM Role / Vertex는 GitLab→GCP Workload Identity Federation
2. **GitLab API 작업용 자격증명**: 기본 `CI_JOB_TOKEN`, 또는 `api` 스코프 Project Access Token을 `GITLAB_ACCESS_TOKEN`(masked)으로
3. `.gitlab-ci.yml`에 잡 추가
4. **(선택) 멘션 트리거**: "Comments (notes)" 프로젝트 웹훅을 이벤트 리스너에 추가 → 댓글에 `@claude` 포함 시 리스너가 `AI_FLOW_INPUT`/`AI_FLOW_CONTEXT` 변수와 함께 파이프라인 트리거 API 호출

### AI_FLOW_* 변수와 사용 패턴

- `AI_FLOW_INPUT`: 사용자 입력(프롬프트). 잡에서 `-p "${AI_FLOW_INPUT:-'기본 프롬프트'}"`로 폴백 지정
- `AI_FLOW_CONTEXT`: 컨텍스트(MR/이슈 등)
- `AI_FLOW_EVENT`: 이벤트 종류

이슈/MR 댓글에서:

```text
@claude implement this feature based on the issue description
@claude suggest a concrete approach to cache the results of this API call
@claude fix the TypeError in the user dashboard component
```

### Bedrock / Vertex AI 잡 (OIDC / WIF)

키 저장 없이 OIDC/WIF로 임시 자격증명을 교환한다. 인증 모델 자체는 [[17 클라우드 프로바이더]] 참고.

**Bedrock** — 필요 변수 `AWS_ROLE_TO_ASSUME`(role ARN), `AWS_REGION`. before_script에서 GitLab OIDC 토큰(`CI_JOB_JWT_V2`)을 `aws sts assume-role-with-web-identity`로 교환:

```yaml
claude-bedrock:
  stage: ai
  image: node:24-alpine3.21
  rules:
    - if: '$CI_PIPELINE_SOURCE == "web"'
  before_script:
    - apk add --no-cache bash curl jq git python3 py3-pip
    - pip install --no-cache-dir awscli
    - curl -fsSL https://claude.ai/install.sh | bash
    - export AWS_WEB_IDENTITY_TOKEN_FILE="${CI_JOB_JWT_FILE:-/tmp/oidc_token}"
    - if [ -n "${CI_JOB_JWT_V2}" ]; then printf "%s" "$CI_JOB_JWT_V2" > "$AWS_WEB_IDENTITY_TOKEN_FILE"; fi
    - >
      aws sts assume-role-with-web-identity
      --role-arn "$AWS_ROLE_TO_ASSUME"
      --role-session-name "gitlab-claude-$(date +%s)"
      --web-identity-token "file://$AWS_WEB_IDENTITY_TOKEN_FILE"
      --duration-seconds 3600 > /tmp/aws_creds.json
    - export AWS_ACCESS_KEY_ID="$(jq -r .Credentials.AccessKeyId /tmp/aws_creds.json)"
    - export AWS_SECRET_ACCESS_KEY="$(jq -r .Credentials.SecretAccessKey /tmp/aws_creds.json)"
    - export AWS_SESSION_TOKEN="$(jq -r .Credentials.SessionToken /tmp/aws_creds.json)"
  script:
    - /bin/gitlab-mcp-server || true
    - >
      claude
      -p "${AI_FLOW_INPUT:-'Implement the requested changes and open an MR'}"
      --permission-mode acceptEdits
      --allowedTools "Bash Read Edit Write mcp__gitlab"
      --debug
  variables:
    AWS_REGION: "us-west-2"
```

Bedrock 모델 ID는 리전 프리픽스 포함(`us.anthropic.claude-sonnet-4-6`).

**Vertex AI** — 필요 변수 `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `CLOUD_ML_REGION`(예: `us-east5`). `gcloud auth login --cred-file`에 external_account 자격증명을 넘겨 WIF로 인증:

```yaml
claude-vertex:
  stage: ai
  image: gcr.io/google.com/cloudsdktool/google-cloud-cli:slim
  rules:
    - if: '$CI_PIPELINE_SOURCE == "web"'
  before_script:
    - apt-get update && apt-get install -y git && apt-get clean
    - curl -fsSL https://claude.ai/install.sh | bash
    - >
      gcloud auth login --cred-file=<(cat <<EOF
      {
        "type": "external_account",
        "audience": "${GCP_WORKLOAD_IDENTITY_PROVIDER}",
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
        "service_account_impersonation_url": "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${GCP_SERVICE_ACCOUNT}:generateAccessToken",
        "token_url": "https://sts.googleapis.com/v1/token"
      }
      EOF
      )
    - gcloud config set project "$(gcloud projects list --format='value(projectId)' --filter="name:${CI_PROJECT_NAMESPACE}" | head -n1)" || true
  script:
    - /bin/gitlab-mcp-server || true
    - >
      CLOUD_ML_REGION="${CLOUD_ML_REGION:-us-east5}"
      claude
      -p "${AI_FLOW_INPUT:-'Review and update code as requested'}"
      --permission-mode acceptEdits
      --allowedTools "Bash Read Edit Write mcp__gitlab"
      --debug
  variables:
    CLOUD_ML_REGION: "us-east5"
```

WIF에서는 서비스 계정 키 저장이 불필요. 저장소별 trust condition과 최소 권한 SA를 쓴다.

### GitLab 고급 파라미터 · 거버넌스 · 트러블슈팅

자주 쓰는 입력 (정확한 플래그는 버전마다 다를 수 있으니 잡에서 `claude --help`):

| 입력 | 설명 |
|---|---|
| `prompt` / `prompt_file` | 인라인(`-p`) 또는 파일로 지시 |
| `max_turns` | 왕복 반복 횟수 제한 |
| `timeout_minutes` | 총 실행 시간 제한 |
| `ANTHROPIC_API_KEY` | Claude API 필수 (Bedrock/Vertex는 미사용) |
| 프로바이더 env | `AWS_REGION`, Vertex용 project/region 변수 |

거버넌스: 각 잡은 제한된 네트워크의 격리 컨테이너에서 실행 / 변경은 MR로 흘러 모든 diff가 보임 / 브랜치 보호·승인 규칙이 AI 코드에도 적용 / 워크스페이스 스코프 권한으로 쓰기 제한 / BYO 프로바이더 자격증명으로 비용 통제. ([[18 보안과 샌드박스]])

비용: GitLab 러너 시간 + API 토큰. 절감 — 구체적 명령, `max_turns`·타임아웃 설정, concurrency 제한, 러너의 npm/패키지 캐싱.

| 증상 | 점검 |
|---|---|
| `@claude` 무응답 | 파이프라인 트리거 확인, CI/CD 변수 존재, 댓글에 `@claude`(`/claude` 아님)·멘션 트리거 구성 |
| 댓글/MR 작성 불가 | `CI_JOB_TOKEN` 권한 또는 `api` 스코프 PAT, `mcp__gitlab` 도구가 `--allowedTools`에 포함, MR 컨텍스트 또는 `AI_FLOW_*` 변수 충분한지 |
| 인증 에러 | API 키 유효성 / Bedrock·Vertex는 OIDC·WIF 구성·role 임퍼소네이션·시크릿 이름·리전·모델 가용성 |

---

## Code Review — 매니지드 자동 PR 리뷰

Code Review는 Anthropic이 운영하는 매니지드 서비스로, GitHub PR을 분석해 문제가 있는 코드 라인에 **인라인 댓글**로 결과를 게시한다. 전문화된 다중 에이전트가 변경을 전체 코드베이스 맥락에서 검사해 로직 오류·보안 취약점·깨진 엣지 케이스·미묘한 회귀를 찾는다. **Team·Enterprise 구독 한정 research preview**이며, **Zero Data Retention 조직은 사용 불가**.

핵심: 결과는 심각도 태그가 붙지만 **PR을 승인하거나 차단하지 않아** 기존 리뷰 워크플로를 해치지 않는다. `CLAUDE.md`/`REVIEW.md`로 무엇을 flag할지 튜닝한다. 자기 CI에서 직접 돌리려면 위 GitHub Actions/GitLab CI/CD 절을, 자체 호스팅이면 GHES 절을 본다. 로컬 터미널에서 GitHub App 없이 diff만 리뷰하려면 아래 [`/code-review` 명령](#code-review-명령--로컬-diff-리뷰)을 본다.

### 리뷰 동작 방식

admin이 조직에 활성화하면, PR이 열릴 때·매 push마다·수동 요청 시(저장소 설정에 따라) 리뷰가 트리거된다. `@claude review` 댓글은 모드와 무관하게 리뷰를 시작한다.

리뷰가 돌면 여러 에이전트가 Anthropic 인프라에서 diff와 주변 코드를 **병렬** 분석한다. 각 에이전트가 다른 종류의 이슈를 찾고, **검증 단계**가 후보를 실제 코드 동작과 대조해 false positive를 거른다. 결과는 중복 제거·심각도 정렬되어 해당 라인에 인라인 댓글로, 리뷰 본문에 요약으로 게시된다. 이슈가 없으면 check run을 "no issues detected"로 갱신한다. **평균 20분** 소요, PR 크기·복잡도에 비례해 비용 증가.

### 심각도 레벨

| 마커 | 심각도 | 의미 |
|---|---|---|
| 🔴 | Important | 머지 전 고쳐야 할 버그 |
| 🟡 | Nit | 사소한 이슈, 고치면 좋지만 비차단 |
| 🟣 | Pre-existing | 코드베이스에 이미 있던 버그(이 PR이 유발하지 않음) |

각 결과에는 접을 수 있는 확장 추론 섹션이 있어 왜 flag했고 어떻게 검증했는지 볼 수 있다.

### 결과에 평가·답글하기

각 리뷰 댓글에는 👍/👎가 이미 붙어 GitHub UI에서 원클릭 평가가 가능하다. 👍는 유용함, 👎는 틀렸거나 노이즈. Anthropic은 PR 머지 후 반응 카운트를 모아 리뷰어를 튜닝한다(재리뷰 트리거 아님, PR 변경 없음).

> [!warning] 인라인 댓글 답글은 무동작
> 인라인 댓글에 답글을 달아도 Claude가 응답하거나 PR을 갱신하지 않는다. 결과에 대응하려면 코드를 고쳐 push하라. push-트리거 리뷰 구독 PR이면 다음 실행이 고쳐진 이슈의 스레드를 resolve한다. push 없이 새 리뷰를 원하면 **top-level PR 댓글**로 `@claude review once`.

### Check run 출력 (머지 게이팅)

인라인 댓글 외에, 매 리뷰가 **Claude Code Review** check run을 채운다. **Details** 링크에서 심각도 정렬된 전체 결과 요약을 본다. 각 결과는 **Files changed** 탭에 annotation으로도 표시(Important=빨강, Nit=노랑, Pre-existing=회색). annotation과 심각도 표는 인라인 댓글과 독립적으로 기록되어, GitHub이 이동한 라인의 인라인 댓글을 거부해도 남는다.

check run은 항상 **neutral** 결론으로 끝나 브랜치 보호로 머지를 차단하지 않는다. 결과로 머지를 게이팅하려면 자기 CI에서 check run 출력의 심각도 집계를 읽는다. Details 텍스트 마지막 줄은 `gh`+jq로 파싱 가능한 머신 판독 코멘트다.

```bash
gh api repos/OWNER/REPO/check-runs/CHECK_RUN_ID \
  --jq '.output.text | split("bughunter-severity: ")[1] | split(" -->")[0] | fromjson'
```

반환 예: `{"normal": 2, "nit": 1, "pre_existing": 0}`. `normal` 키가 Important 개수이고, 0이 아니면 머지 전 고칠 버그가 최소 하나 있다는 뜻.

기본적으로 Code Review는 **correctness**(프로덕션을 깨는 버그)에 집중하며 포매팅 취향이나 테스트 커버리지 누락은 보지 않는다. 가이던스 파일로 검사 범위를 넓힐 수 있다.

### Code Review 설정

admin이 조직에 한 번 활성화하고 포함할 저장소를 고른다. Claude 조직 admin 권한 + GitHub 조직에 App 설치 권한 필요.

1. **claude.ai/admin-settings/claude-code** → Code Review 섹션
2. **Setup** → GitHub App 설치 플로우
3. Claude GitHub App 설치 (권한: Contents read&write, Issues read&write, Pull requests read&write). Code Review는 contents read + pull requests write를 사용하고, 넓은 권한 집합은 나중에 GitHub Actions 활성화도 지원
4. 저장소 선택 (안 보이면 설치 시 App 접근을 줬는지 확인, 나중에 추가 가능)
5. **Review Behavior** 드롭다운으로 저장소별 리뷰 시점 설정

| 트리거 모드 | 동작 |
|---|---|
| Once after PR creation | PR이 열리거나 ready로 표시될 때 1회 |
| After every push | PR 브랜치 매 push마다 — 새 이슈 포착 + 고친 이슈 스레드 자동 resolve (가장 많이 실행, 비용 최대) |
| Manual | 누군가 `@claude review`/`@claude review once` 댓글 시에만. `@claude review`는 이후 push에도 구독시킴 |

설정 후 테스트 PR을 연다. 자동 트리거면 몇 분 안에 **Claude Code Review** check run 등장. Manual이면 `@claude review` 댓글. 저장소 테이블은 최근 활동 기준 리뷰당 평균 비용도 보여주며, 행 액션 메뉴로 저장소별 on/off·제거.

### 수동 트리거

| 명령 | 동작 |
|---|---|
| `@claude review` | 리뷰 시작 + 이후 push-트리거 리뷰 구독 |
| `@claude review once` | 1회 리뷰만, 향후 push 구독 안 함 |

`@claude review once`는 잦은 push의 장기 PR이나 일회성 second opinion에 유용(리뷰 동작 변경 없음). 트리거 조건:

- **top-level PR 댓글**로 게시 (diff 라인 인라인 댓글 아님)
- 명령을 댓글 맨 앞에 두고, one-shot이면 같은 줄에 `once`
- 저장소에 owner/member/collaborator 접근 권한 필요
- PR이 열려 있어야 함

자동 트리거와 달리 수동 트리거는 **draft PR에서도 실행**된다. 이미 리뷰 중이면 요청은 완료까지 큐잉.

### 리뷰 커스터마이즈 — CLAUDE.md vs REVIEW.md

Code Review는 두 파일을 읽어 flag 대상을 결정하며, 영향력 강도가 다르다.

- **`CLAUDE.md`**: 모든 Claude Code 작업에 쓰이는 공유 프로젝트 지시. 리뷰는 이를 프로젝트 컨텍스트로 읽고, **새로 도입된 위반을 nit**으로 flag. 양방향 — PR이 `CLAUDE.md` 진술을 outdated하게 만들면 문서 갱신 필요도 flag. 디렉터리 계층 모든 레벨의 `CLAUDE.md`를 읽어 하위 디렉터리 규칙은 그 경로 파일에만 적용 ([[03 메모리와 컨텍스트]]).
- **`REVIEW.md`**: 저장소 루트의 **리뷰 전용** 지시. 리뷰 파이프라인 모든 에이전트의 시스템 프롬프트에 **최우선 지시 블록**으로 주입되어 기본 가이던스를 능가. verbatim으로 붙여지므로 `@` import 구문은 확장 안 되고 참조 파일도 안 읽힘 — 규칙을 파일에 직접 적는다.

`REVIEW.md`에서 튜닝할 수 있는 것:

| 항목 | 설명 |
|---|---|
| Severity | 🔴 Important의 정의를 저장소에 맞게 재정의(docs/config/prototype는 좁게, `CLAUDE.md` 위반을 Important로 격상도 가능) |
| Nit volume | 1회 리뷰의 🟡 Nit 댓글 수 캡 (예: "최대 5개, 나머지는 요약에 개수로") |
| Skip rules | 결과를 안 낼 경로·브랜치 패턴·카테고리(생성 코드, lockfile, vendored 의존성, 머신 브랜치, CI가 이미 강제하는 lint/spellcheck) |
| Repo-specific checks | 매 PR 검사 규칙(예: "새 API 라우트는 통합 테스트 필수") — 최우선 주입이라 긴 CLAUDE.md보다 안정적으로 적용 |
| Verification bar | 결과 게시 전 증거 요구(예: "동작 주장은 naming 추론이 아닌 file:line 인용 필요") |
| Re-review convergence | 재리뷰 시 행동(예: "첫 리뷰 후 새 nit 억제, Important만") |
| Summary shape | 본문 첫 줄에 한 줄 집계(`2 factual, 4 style`), 문제 없으면 "no factual issues" 선두 |

`REVIEW.md` 예시 (백엔드 서비스):

```markdown
# Review instructions

## What Important means here

Reserve Important for findings that would break behavior, leak data,
or block a rollback: incorrect logic, unscoped database queries, PII
in logs or error messages, and migrations that aren't backward
compatible. Style, naming, and refactoring suggestions are Nit at
most.

## Cap the nits

Report at most five Nits per review. If you found more, say "plus N
similar items" in the summary instead of posting them inline. If
everything you found is a Nit, lead the summary with "No blocking
issues."

## Do not report

- Anything CI already enforces: lint, formatting, type errors
- Generated files under `src/gen/` and any `*.lock` file
- Test-only code that intentionally violates production rules

## Always check

- New API routes have an integration test
- Log lines don't include email addresses, user IDs, or request bodies
- Database queries are scoped to the caller's tenant
```

> [!tip] 길이의 비용
> 긴 `REVIEW.md`는 중요한 규칙을 희석한다. 리뷰 동작을 바꾸는 지시만 담고, 일반 프로젝트 컨텍스트는 `CLAUDE.md`에 둔다.

### 사용량·비용

**claude.ai/analytics/code-review** 대시보드: PRs reviewed(일별), Cost weekly(주별 지출), Feedback(개발자 대응으로 auto-resolve된 댓글 수), Repository breakdown(저장소별). 대시보드 비용은 모니터링용 추정치, 정확한 청구는 Anthropic 청구서 기준.

**가격**: 토큰 사용량 기준, 리뷰당 평균 **$15-25** (PR 크기·코드베이스 복잡도·검증 필요 이슈 수에 비례). **usage credits로 별도 청구**되며 플랜 포함 사용량에 카운트되지 않음. 트리거가 총비용에 영향: Once=PR당 1회, After every push=push마다(횟수만큼 배수), Manual=댓글 시에만. 어느 모드든 `@claude review`는 이후 push마다 비용 발생, `@claude review once`는 구독 안 함. Bedrock/Vertex를 다른 기능에 쓰더라도 Code Review 비용은 Anthropic 청구서에 표시. 월 지출 캡은 **claude.ai/admin-settings/usage**에서 설정. ([[19 비용과 성능]])

### Code Review 트러블슈팅

리뷰는 best-effort다. 실패해도 PR을 차단하지 않지만 자동 재시도도 안 한다.

- **실패/타임아웃 재실행**: check run이 **Code review encountered an error** 또는 **Code review timed out** 제목으로 끝남(결론은 여전히 neutral). 재실행하려면 `@claude review once` 댓글, 또는 구독 중이면 새 커밋 push. **GitHub Checks 탭의 Re-run 버튼은 Code Review를 재트리거하지 않음.**
- **spend-cap 메시지**: 월 지출 캡 도달 시 PR에 스킵 안내 댓글 1개. 다음 청구 주기 시작 시 또는 admin이 캡 상향 시 재개.
- **인라인 댓글이 안 보이는 결과 찾기**: check run **Details**(전체 결과 표), **Files changed** annotation(diff 라인 부착), 리뷰 본문 **Additional findings**(리뷰 중 push해 라인이 사라진 경우).

### `/code-review` 명령 — 로컬 diff 리뷰

GitHub App 없이 터미널에서 diff를 리뷰하려면 Claude Code 세션에서 `/code-review`를 실행한다 ([[02 CLI 레퍼런스]], [[20 베스트 프랙티스와 워크플로우]]). 현재 diff의 correctness 버그와 (min-version 2.1.151+) reuse·simplification·efficiency 정리를 보고한다.

| 사용 | 효과 |
|---|---|
| `/code-review` | 현재 diff 리뷰(현재 effort 사용) |
| `/code-review --comment` | 결과를 인라인 PR 댓글로 게시 |
| `/code-review --fix` | 리뷰 후 결과를 워킹 트리에 적용 |
| `/code-review high` ~ `max` | effort 상향 — 넓은 커버리지, 불확실한 결과 포함 가능 (low/medium은 적고 고신뢰) |
| `/code-review <path \| PR ref>` | 특정 대상 리뷰 |
| `/code-review ultra --fix` | 클라우드의 더 깊은 ultrareview 실행 후 결과를 워킹 트리에 적용 |

effort 레벨은 [[19 비용과 성능]]의 effort 조정과 연동. 명령 이름 변천: v2.1.147 전엔 `/simplify`(기본 fix 적용). v2.1.154부터 `/simplify`는 버그 탐색 없는 cleanup-only 리뷰로 fix 적용. 버그 탐색을 스크립트했다면 `/code-review --fix`로 전환(동작 불변).

---

## Slack 통합

Claude Code in Slack은 Slack 워크스페이스에서 코딩 작업을 위임한다. `@Claude`를 코딩 작업과 함께 멘션하면 의도를 자동 감지해 **Claude Code on the web 세션**을 생성한다 ([[15 웹과 모바일]]). 기존 Claude for Slack 앱 위에 코딩 요청 지능형 라우팅을 추가한 형태다.

사용 사례: 버그 조사·수정(채널 보고 즉시), 빠른 코드 리뷰·수정, 협업 디버깅(스레드 컨텍스트 활용), 병렬 작업(Slack에서 킥오프 후 완료 알림).

### 사전 요건

| 요건 | 상세 |
|---|---|
| Claude Plan | Pro, Max, Team, Enterprise (premium seats 또는 Chat + Claude Code seats) |
| Claude Code on the web | claude.ai/code 접근 활성화 필요 |
| GitHub Account | Claude Code on the web에 연결, 최소 1개 저장소 인증 |
| Slack Authentication | Claude 앱으로 Slack 계정을 Claude 계정에 링크 |

### 설정

1. **앱 설치**: 워크스페이스 admin이 Slack App Marketplace(https://slack.com/marketplace/A08SF47R6P4)에서 "Add to Slack"
2. **계정 연결**: Slack의 Claude 앱 → App Home 탭 → "Connect" → 브라우저 인증
3. **웹 구성**: claude.ai/code에 같은 계정으로 로그인, GitHub 연결, 최소 1개 저장소 인증
4. **라우팅 모드 선택** (App Home의 **Routing Mode**):

| 모드 | 동작 |
|---|---|
| Code only | 모든 @멘션을 Claude Code 세션으로. 개발 전용 팀에 적합 |
| Code + Chat | 메시지별로 코딩↔Chat 지능형 라우팅. 단일 @Claude 엔트리포인트를 원하는 팀에 적합 |

Code + Chat에서 Chat으로 갔는데 코딩을 원했다면 **"Retry as Code"**, 반대도 가능.

5. **채널 추가**: 설치 후 자동 추가 안 됨. 채널에서 `/invite @Claude`로 초대. **추가된 채널의 @멘션에만 응답.**

### 동작 방식

- **자동 감지**: @Claude 멘션 시 메시지를 분석해 코딩 작업이면 웹으로 라우팅. 명시적으로 코딩 작업으로 지정도 가능.
- **컨텍스트 수집**: 스레드 멘션이면 스레드 전체 메시지를, 채널 직접 멘션이면 최근 채널 메시지를 컨텍스트로 수집해 저장소 선택·접근 방향에 활용.

> [!note] 채널 전용
> Claude Code in Slack은 채널(공개/비공개)에서만 동작하고 **DM에서는 동작하지 않는다.**

> [!warning] 신뢰된 대화에서만
> @Claude 호출 시 대화 컨텍스트 접근 권한이 주어진다. Claude는 컨텍스트의 다른 메시지 지시를 따를 수 있으므로 **신뢰된 Slack 대화에서만** 사용하라. ([[18 보안과 샌드박스]])

**세션 플로우**: (1) @멘션 코딩 요청 → (2) 의도 감지 → (3) claude.ai/code에 세션 생성 → (4) 스레드에 진행 상태 게시 → (5) 완료 시 @멘션 + 요약 + 액션 버튼 → (6) "View Session"으로 전체 transcript, "Create PR"로 PR.

### UI 요소 · 메시지 액션

- **App Home**: 연결 상태 표시, Claude 계정 연결/해제
- **메시지 액션**: **View Session**(브라우저에서 전체 세션, 계속/추가 요청), **Create PR**(세션 변경으로 PR 생성), **Retry as Code**(Chat 응답을 코딩 세션으로 재시도), **Change Repo**(잘못 고른 저장소 변경)
- **저장소 선택**: 컨텍스트 기반 자동 선택, 모호하면 드롭다운 표시

### 접근·권한

| 사용자 레벨 | 요건 |
|---|---|
| Claude Code Sessions | 각 사용자가 자기 Claude 계정으로 실행 |
| Usage & Rate Limits | 세션은 개인 플랜 한도에 카운트 |
| Repository Access | 본인이 개인 연결한 저장소만 접근 |
| Session History | claude.ai/code 히스토리에 표시 |

| 워크스페이스 레벨 | 설명 |
|---|---|
| App installation | 워크스페이스 admin이 앱 설치 결정 |
| Enterprise Grid distribution | Enterprise Grid는 조직 admin이 워크스페이스별 접근 제어 |
| App removal | 앱 제거 시 해당 워크스페이스 전 사용자 접근 즉시 회수 |

**채널 기반 접근 제어**: 자동 추가 안 됨 → `/invite @Claude` 필요. 채널 멤버십이 접근을 통제하여, 워크스페이스 권한 너머 추가 접근 계층 제공(공개/비공개 채널 모두 지원).

**가시성**: Slack에는 상태 업데이트·완료 요약·액션 버튼이, 웹에는 전체 대화 히스토리·코드 변경·파일 작업·세션 계속/PR 생성이 있다. Enterprise·Team 계정은 Slack에서 만든 세션이 조직에 자동 가시화([[15 웹과 모바일]]의 세션 공유 참고).

### Slack 베스트 프랙티스 · 한계 · 트러블슈팅

효과적 요청: 구체적으로(파일·함수·에러명), 컨텍스트 제공(저장소·프로젝트), 성공 정의("done"이 뭔지 — 테스트? 문서? PR?), 스레드 활용. **Slack을 쓸 때**: 컨텍스트가 이미 Slack 토론에 있을 때, 비동기 킥오프, 팀 가시성 필요 시. **웹 직접**: 파일 업로드, 실시간 상호작용, 더 길고 복잡한 작업.

**현재 한계**: GitHub 저장소만 지원 / 세션당 PR 1개 / 개인 플랜 rate limit 적용 / 웹 접근 필수(없으면 표준 Chat 응답만).

| 증상 | 점검 |
|---|---|
| 세션 미시작 | App Home 계정 연결, 웹 접근 활성화, GitHub 저장소 1개 이상 연결 |
| 저장소 안 보임 | claude.ai/code에서 저장소 연결, GitHub 권한, GitHub 재연결 |
| 잘못된 저장소 | "Change Repo" 버튼, 요청에 저장소명 포함 |
| 인증 에러 | 계정 재연결, 올바른 계정 로그인, 플랜에 Claude Code 포함 확인 |
| 세션 만료 | 세션은 웹 히스토리에 남음, claude.ai/code에서 계속/참조 |

---

## 통합 경로 비교

| 통합 | 실행 위치 | 청구 | 트리거 | 주 용도 |
|---|---|---|---|---|
| GitHub Actions | 자기 GitHub 러너 | GitHub 분 + API 토큰 | `@claude` 멘션 / 프롬프트 / 스케줄 | 커스텀 자동화, 자기 CI |
| GitLab CI/CD (beta) | 자기 GitLab 러너 | 러너 분 + API 토큰 | `@claude` 멘션 / MR 이벤트 / 수동·web | 커스텀 자동화, MR 워크플로 |
| Code Review (preview) | Anthropic 인프라 | usage credits(리뷰당 $15-25) | PR open / push / `@claude review` | 매니지드 자동 PR 리뷰 |
| GHES | Anthropic 인프라(웹 세션·리뷰) | 플랜·기능별 | admin 연결 후 자동 | 자체 호스팅 GitHub |
| Slack | Anthropic 인프라(웹 세션) | 개인 플랜 한도 | `@Claude` 멘션 | 채널에서 작업 위임 |

---

## 원본 문서

- [github-actions](https://code.claude.com/docs/en/github-actions)
- [github-enterprise-server](https://code.claude.com/docs/en/github-enterprise-server)
- [gitlab-ci-cd](https://code.claude.com/docs/en/gitlab-ci-cd)
- [code-review](https://code.claude.com/docs/en/code-review)
- [slack](https://code.claude.com/docs/en/slack)

관련 허브: [[Claude]]
