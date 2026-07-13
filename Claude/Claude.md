---
title: Claude Code 사용법
updated: 2026-07-13
type: moc
---

# Claude Code 사용법

이 노트는 Claude Code 공식 문서(code.claude.com/docs) 전체 페이지를 27개 노트로 종합한 지식 베이스의 중심 허브(MOC)다. 설치부터 CLI·설정·권한·확장(스킬·훅·MCP·플러그인·서브에이전트)·자동화·팀 통합·운영(보안·비용)·Agent SDK·레퍼런스까지 Claude Code의 모든 사용법을 다룬다. 명령어·플래그·설정 키·환경변수는 원문 영어 그대로, 맥락·트레이드오프·주의사항은 한국어로 정리했으며, 각 노트는 본문에서 `허브: [[Claude]]`로 이곳을 가리킨다. 아래 **용도별 학습 경로**로 목적에 맞는 노트를 순서대로 따라가거나, **전체 지도**에서 주제군별로 원하는 노트를 바로 찾아갈 수 있다.

## 용도별 학습 경로

목적에 맞는 경로를 따라 노트를 순서대로 읽으면 된다. 경로는 누적적이다 — 입문을 마친 뒤 일상 사용으로, 다시 자동화나 팀 도입으로 확장하는 것을 권장한다.

### 입문 (처음 시작하는 경우)
1. [[01 시작하기]] — 설치·로그인·첫 세션·동작 원리
2. [[02 CLI 레퍼런스]] — 명령어와 대화형 모드 조작
3. [[03 메모리와 컨텍스트]] — 메모리(CLAUDE.md)와 컨텍스트 윈도우 이해
4. [[20 베스트 프랙티스와 워크플로우]] — Explore→Plan→Code 실전 워크플로우

### 일상 사용 (매일 코딩에 쓰는 경우)
1. [[06 내장 도구 레퍼런스]] — 도구와 슬래시 커맨드 활용
2. [[05 권한]] — 권한 규칙·모드로 마찰 줄이기
3. [[14 IDE와 데스크톱]] — VS Code/JetBrains/데스크톱 통합
4. [[20 베스트 프랙티스와 워크플로우]] — 워크플로우 레시피와 프롬프트 라이브러리
5. [[12 출력 스타일과 상태줄]] — UX 커스터마이징
6. [[25 트러블슈팅]] — 막힐 때 진단·복구

### 자동화·CI (스크립트·파이프라인으로 돌리는 경우)
1. [[13 자동화와 스케줄링]] — headless 실행·스케줄링·채널
2. [[09 훅]] — 수명주기 훅으로 동작 자동화
3. [[07 스킬]] — 재사용 가능한 절차를 스킬로
4. [[16 CI-CD와 팀 통합]] — GitHub Actions·GitLab CI/CD·Slack
5. [[19 비용과 성능]] — 토큰·비용 통제와 모니터링

### 팀·엔터프라이즈 도입 (조직 차원에서 굴리는 경우)
1. [[04 설정]] — 설정 스코프·우선순위·조직 배포
2. [[05 권한]] — managed settings와 권한 거버넌스
3. [[17 클라우드 프로바이더]] — Bedrock/Vertex AI/Foundry 배포
4. [[27 게이트웨이]] — Claude apps gateway 자체 호스팅 또는 서드파티 LLM 게이트웨이로 인증·비용·감사를 중앙화
5. [[18 보안과 샌드박스]] — 보안 모델·격리·데이터 정책
6. [[19 비용과 성능]] — 팀 rate limit·OpenTelemetry·애널리틱스
7. [[11 플러그인]] — 마켓플레이스로 조직 표준 배포
8. [[26 변경 이력과 용어집]] — 챔피언 킷·커뮤니케이션 킷으로 도입 추진

### Agent SDK 개발 (Claude Code를 코드에 임베드하는 경우)
1. [[22 Agent SDK — 시작]] — 설치·query()·에이전트 루프
2. [[23 Agent SDK — 핵심 기능]] — 권한·세션·훅·MCP·커스텀 도구
3. [[24 Agent SDK — 고급과 레퍼런스]] — 스트리밍·관측성·호스팅·언어별 API 레퍼런스
4. [[09 훅]] / [[10 MCP]] / [[07 스킬]] — SDK가 통합하는 기반 기능 심화

## 전체 지도

27개 노트를 주제군으로 묶어 각 노트당 한 줄 요약과 함께 나열한다.

### 시작·CLI
- [[01 시작하기]] — 설치·업데이트·제거(바이너리 서명 검증), 로그인·인증, 에이전틱 루프·세션·컨텍스트·권한 모드, Quickstart 8단계, 확장 기능 선택 기준까지의 입문 종합 노트.
- [[02 CLI 레퍼런스]] — CLI 명령어·플래그 전체, 대화형 모드 단축키·vim 모드, keybindings.json 커스터마이징, 터미널 설정, 풀스크린 렌더링, 음성 받아쓰기.

### 설정·권한
- [[03 메모리와 컨텍스트]] — CLAUDE.md 계층·auto memory, 컨텍스트 윈도우 동작·/compact 생존표, 세션 재개·체크포인팅(/rewind), 모노레포 스코핑, .claude 디렉터리 레퍼런스.
- [[04 설정]] — settings.json 키·스코프 우선순위·sandbox, 환경변수 전체, 모델 구성(별칭·effort·1M 컨텍스트), auto mode 분류기, 설정 디버깅과 조직 배포.
- [[05 권한]] — allow/ask/deny 규칙 문법과 deny-first 평가, 도구별 규칙, 여섯 권한 모드(default/acceptEdits/plan/auto/dontAsk/bypassPermissions), 보호 경로·managed settings.

### 확장 (스킬·훅·MCP·플러그인·서브에이전트)
- [[06 내장 도구 레퍼런스]] — 내장 도구 42종과 슬래시 커맨드 전체, 도구 권한 규칙 포맷(ToolName(specifier)), 도구별 동작·제약, 워크플로우 단계별 커맨드 활용.
- [[07 스킬]] — SKILL.md frontmatter 전체, 동적 컨텍스트 주입(!`cmd`), context:fork 서브에이전트 실행, 호출 제어(skillOverrides), 콘텐츠 생명주기와 토큰 예산.
- [[08 서브에이전트와 에이전트 팀]] — 4가지 병렬 실행 방식(서브에이전트·agent view·에이전트 팀·다이내믹 워크플로우)의 정의·조율·선택 기준과 fork·worktree 격리; Anthropic API Claude Managed Agents 공개 베타(webhooks·멀티에이전트 세션·샌드박스).
- [[09 훅]] — 28개 훅 이벤트와 5가지 핸들러 타입, matcher/if 필터·종료 코드·JSON 출력 제어, 자동 포맷·파일 보호 등 실전 패턴, 보안 고려사항.
- [[10 MCP]] — MCP 서버 추가·관리, 4가지 transport·설치 스코프, 원격 OAuth 인증, Tool Search, managed-mcp.json·allowlist/denylist 조직 통제.
- [[11 플러그인]] — 플러그인 생성(매니페스트·컴포넌트), 마켓플레이스 발견/설치, plugin.json·marketplace.json 스키마, CLI 명령, 의존성 제약·관리형 제한.
- [[12 출력 스타일과 상태줄]] — 시스템 프롬프트를 바꾸는 출력 스타일(내장/커스텀)과 stdin JSON으로 컨텍스트·비용·git을 렌더링하는 statusLine 스크립트.

### 자동화·통합
- [[13 자동화와 스케줄링]] — headless 실행(claude -p, --bare), 세션 스코프 /loop·cron, 클라우드 Routines·Desktop scheduled tasks, Channels 이벤트 푸시, Remote Control·딥링크.
- [[14 IDE와 데스크톱]] — VS Code/Cursor 확장, JetBrains 플러그인, 데스크톱 GUI(병렬 세션·worktree·PR 모니터링), .claude/launch.json, Enterprise managed settings.
- [[15 웹과 모바일]] — claude.ai/code 클라우드 세션·GitHub 연결, 클라우드 환경 구성·네트워크 access level, --remote/--teleport 세션 이동, Auto-fix PR, 모바일 앱.
- [[16 CI-CD와 팀 통합]] — GitHub Actions(claude-code-action v1)·GitLab CI/CD, 매니지드 Code Review, GHES 연결, Slack 라우팅 모드, Bedrock/Vertex OIDC 인증.

### 운영 (보안·비용)
- [[18 보안과 샌드박스]] — 권한 기반 보안 아키텍처·프롬프트 인젝션 방어, 샌드박스 격리 스펙트럼(/sandbox·dev container·VM), security-guidance 플러그인, 데이터·텔레메트리·BAA 정책.
- [[19 비용과 성능]] — 비용 추적(/usage)·토큰 절감, 프롬프트 캐싱 동작, fast mode, OpenTelemetry 모니터링·SIEM 감사, 팀 애널리틱스 대시보드.
- [[17 클라우드 프로바이더]] — AWS Bedrock·Claude Platform on AWS·Vertex AI·Microsoft Foundry 배포, 환경변수·IAM/RBAC·모델 핀, 서드파티 LLM 게이트웨이 환경변수 설정(LiteLLM), 기업 네트워크 설정.
- [[27 게이트웨이]] — Claude apps gateway(자체 셀프호스팅, `claude gateway` 서브커맨드) 퀵스타트·gateway.yaml 레퍼런스·배포(K8s/Cloud Run/GCP 예시)·지출 한도 Admin API, 서드파티 게이트웨이 프로토콜 계약·개발자 접속·조직 롤아웃 5단계.

### Agent SDK
- [[22 Agent SDK — 시작]] — 설치·인증·query() 진입점, 내장 도구·권한 모드, 에이전트 루프(턴·메시지·컴팩션), settingSources 통합, claude-code-sdk→claude-agent-sdk 마이그레이션.
- [[23 Agent SDK — 핵심 기능]] — 권한 평가·모드, 세션 영속화(SessionStore), 훅, MCP·in-process 커스텀 도구, 서브에이전트, 사용자 입력 처리, 파일 체크포인트.
- [[24 Agent SDK — 고급과 레퍼런스]] — 입력/출력 스트리밍, 구조화 출력, 시스템 프롬프트 커스터마이징, 관측성·비용 추적, 자체 호스팅·보안 배포, TypeScript/Python API 레퍼런스.

### 레퍼런스
- [[20 베스트 프랙티스와 워크플로우]] — 컨텍스트 관리·검증 루프, Explore→Plan→Code, SDLC 5단계 프롬프트 라이브러리, git worktree 격리, ultraplan/ultrareview, /goal 자동 진행; harness vs 프롬프트 레이어 진단법, 디자인·프로토타이핑 워크플로우(Jane Street 사례).
- [[21 브라우저와 컴퓨터 사용]] — Chrome 통합(--chrome)으로 웹 앱 테스트·디버깅, computer-use MCP로 macOS 네이티브 GUI 제어, 권한·안전 가드레일·도구 우선순위.
- [[25 트러블슈팅]] — 성능·검색·설치·로그인·런타임 에러 진단·복구, 증상별 라우팅 표, 자동 재시도 튜닝, /doctor·/rewind·/compact 등 핵심 진단 명령.
- [[26 변경 이력과 용어집]] — 용어집 전체, 최근 3개월 changelog, 주간 What's New(w13~w28), 팀 도입용 챔피언 킷·커뮤니케이션 킷.
