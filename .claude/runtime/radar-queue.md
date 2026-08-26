# claude-radar 추천 큐

<!-- 무인 collect(/claude-radar collect)가 신규 추천을 아래 날짜 섹션에 append한다.
     대화형 review(/claude-radar review)가 [pending] → [done]/[dismissed]로 상태만 바꾼다(이력 보존, 항목 삭제 금지).
     session-context 훅이 '### [done]' 개수를 세어 세션 시작 시 노출한다.

     항목 템플릿 — 이 형식을 정확히 지킬 것(훅이 '### [done]'을 카운트):

     ### [done] <skill|agent|command|rule|kb-ingest> · <제목>
     - **source**: <소스명>
     - **url**: <원본 링크>
     - **근거**: <왜 주목할 가치가 있는지 한 줄>
     - **제안**: <무엇을 어떻게 만들지/박제할지>
-->

## 2026-08-26

### [pending] kb-ingest · claude-code v2.1.246 릴리스 노트
- **source**: anthropics/claude-code releases
- **url**: https://github.com/anthropics/claude-code/releases/tag/v2.1.246
- **근거**: 서브커맨드 앞에 와일드카드가 오는 Bash allow rule에 대한 startup 경고, `/permissions` Auto mode 탭, 턴 완료 시간 표시 등 실사용에 영향 주는 변경 — `80 Tooling/`의 권한·설정 관련 노트와 직결.
- **제안**: `80 Tooling/` 권한/설정 레퍼런스 노트(예: `30 설정 레퍼런스` 또는 관련 훅·권한 노트)에 반영 여부 검토. `/kb-sync`와 역할 겹침 주의 — 릴리스 노트 단위 변경이라 이 큐가 더 빠름.

### [pending] kb-ingest · Your Claude Code Hooks Are Costing You Minutes a Day
- **source**: dev.to #claudecode
- **url**: https://dev.to/bokuwalily/your-claude-code-hooks-are-costing-you-minutes-a-day-heres-how-i-measured-it-4im4
- **근거**: 우리 vault는 hook-heavy(session-context, kb-lint-check, stray-guard, Stop/SessionEnd auto-commit 등) — hook 누적 지연 측정 방법론은 직접 참고 가치가 있음.
- **제안**: 원문 확인 후 `80 Tooling/31 하네스 엔지니어링`에 "hook 성능 측정" 절 추가할 가치가 있는지 판단. 실측 결과가 유의미하면 우리 hook들에도 같은 측정을 적용해볼 것.

### [pending] kb-ingest · 52 Days, 2,340 Rows, Every Cost Logged as Zero: The Stop Hook Trap
- **source**: dev.to #claudecode
- **url**: https://dev.to/bokuwalily/52-days-2340-rows-every-cost-logged-as-zero-the-stop-hook-trap-3bn3
- **근거**: 우리의 무인 auto-commit이 Stop hook에 의존한다(automation-safety-rules "Anything an unattended run leaves in the tree is auto-committed"). Stop hook의 조용한 실패 모드는 우리 파이프라인의 실제 리스크와 직결.
- **제안**: 원문 확인 후 fail-silent 패턴이 우리 Stop/SessionEnd hook에도 있는지 점검. 재현되면 `test_mechanisms.py`에 계약 테스트 추가하거나 rule로 문서화.

### [pending] kb-ingest · Four Traps in MCP Health Checking: What Broke My Overnight Batches
- **source**: dev.to #claudecode
- **url**: https://dev.to/bokuwalily/four-traps-in-mcp-health-checking-what-broke-my-overnight-batches-1187
- **근거**: 다수 MCP 서버(claude.ai connectors 등)를 연결해 쓰는데 헬스체크 메커니즘이 없음 — 실패 패턴 지식이 갭을 메울 수 있음.
- **제안**: 원문 확인 후 `80 Tooling/`에 MCP 운영 관련 노트가 있으면 보강, 없으면 신규 노트 검토.

### [pending] kb-ingest · What I Learned Letting an AI Agent Security-Review 300 Pull Requests
- **source**: dev.to #claudecode
- **url**: https://dev.to/yureki_lab/what-i-learned-letting-an-ai-agent-security-review-300-pull-requests-1io1
- **근거**: `security-review` skill을 이미 보유 — 대규모 실전 운용 경험(오탐률·놓친 케이스 등)은 우리 skill 튜닝에 참고 가치.
- **제안**: 원문 확인 후 `80 Tooling/`에 보안 리뷰 운용 팁 노트로 반영할지, 혹은 `security-review` skill 자체 개선 아이디어로 review에서 논의.

### [pending] rule · forge-harness — 커밋 전 AI 코드 게이트 하네스
- **source**: GeekNews
- **url**: https://news.hada.io/topic?id=32868
- **근거**: "AI가 쓴 코드를 커밋 전에 막는" 오픈소스 게이트 하네스 — 우리도 이미 stray-guard.sh(무인 변경 원복)·kb-lint-check(PostToolUse) 같은 게이트를 갖고 있어 설계 비교 가치가 있음.
- **제안**: review에서 원문 확인 후, 우리 게이트 메커니즘과 겹치지 않는 새 패턴(예: 커밋 전 최종 차단선)이 있으면 rule/hook으로 흡수. 이미 커버된 범위면 dismissed.

## 2026-08-24

### [pending] kb-sync · 00 LLM Wiki 아키텍처와 OKF 자기진단: 출처 구조 변경(https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

### [pending] kb-sync · 01 시작하기: 출처 구조 변경(how-claude-code-works) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

### [pending] kb-sync · 04 설정: 출처 구조 변경(auto-mode-config, debug-your-config, env-vars) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

### [pending] kb-sync · 06 내장 도구 레퍼런스: 출처 구조 변경(commands) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

### [pending] kb-sync · 11 플러그인: 출처 구조 변경(plugins-reference) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

### [pending] kb-sync · 14 IDE와 데스크톱: 출처 구조 변경(vs-code) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

### [pending] kb-sync · 25 트러블슈팅: 출처 구조 변경(errors) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

### [pending] kb-sync · 26 변경 이력과 용어집: 출처 구조 변경(whats-new/index) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

### [pending] kb-sync · 27 게이트웨이: 출처 구조 변경(claude-apps-gateway) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

### [pending] kb-sync · 29 자체 호스팅 환경: 출처 구조 변경(self-hosted-environments-configuration) — /kb-sync --deep
- **근거**: 2026-08-24 kb-sync §6b 2층 검출(구조 12/프로즈 41 중 구조분). 베이스라인 08-22→08-24 skel diff로 복구 적재.

## 2026-08-23

### [pending] kb-ingest · Munder Difflin — 나를 복제한 직원들로 사무실을 운영하는 에이전트 하네스
- **source**: GeekNews
- **url**: https://news.hada.io/topic?id=32788
- **근거**: 제목상 자기 복제 에이전트로 조직(사무실)을 운영하는 멀티에이전트 하네스 사례로 보임 — 우리 vault의 workflow/orchestration 패턴과 인접. WebFetch 권한 미승인으로 원문 미확인(제목·source만 근거) — review 시 원문 확인 후 채택 여부 판단 필요.
- **제안**: review에서 원문 열람 후 `80 Tooling/`에 박제할 가치(멀티에이전트 오케스트레이션 사례) 있는지 판단. 가치 없으면 dismissed 처리.

## 2026-07-27

### [done] kb-ingest · Claude Code로 대규모 코드 마이그레이션을 수행한 방법
- **source**: GeekNews
- **url**: https://news.hada.io/topic?id=31855
- **근거**: Claude Code를 대규모 코드베이스 마이그레이션에 실전 적용한 워크플로우 글(한국어). `Claude/` KB의 활용 패턴/서브에이전트·워크플로우 노트에 박제할 사용법 지식.
- **제안**: `/kb-ingest`로 `Claude/`에 박제(마이그레이션 워크플로우 사례). 기존 워크플로우/서브에이전트 노트에 사례 섹션으로 붙일지 별도 노트로 낼지는 분량 보고 판단.

### [dismissed] kb-ingest · obsidian-llm-wiki — markdown vault → 6-persona MCP team
- **source**: GitHub topic:mcp-server+topic:claude-code (★24)
- **url**: https://github.com/2233admin/obsidian-llm-wiki
- **근거**: 우리 vault(obsidian_sync = Claude Code KB + 포터블 프레임워크)와 **정면으로 인접한** 프로젝트 — markdown vault를 6-페르소나 MCP 팀으로 컴파일해 Claude Code·Codex·OpenCode·Gemini CLI에서 headless로 공용. 우리가 `EXTENSIBILITY.md`/vault-rules non-goal에서 **의도적으로 보류한** "타 에이전트 interop(AGENTS.md)"을 실제로 구현한 레퍼런스라 그 결정 재검토 근거가 됨.
- **제안**: `Claude/`(또는 Meta/ 자기진단) 레퍼런스로 박제 — 6-persona MCP 방식 vs 우리 MOC+wikilink 방식 대조. 즉시 채택이 아니라 "관찰·비교"용. review에서 위치(Claude vs Meta) 확정.

## 2026-06-08

### [done] kb-ingest · claude-code 최신 릴리스 신기능 (v2.1.160–166)
- **source**: anthropics/claude-code releases
- **url**: https://github.com/anthropics/claude-code/releases
- **근거**: fallbackModel(166), requiredMinimum/MaximumVersion managed settings(163), `claude agents --json`의 waitingFor(162), OTEL metric labels(161), shell startup 파일 쓰기 전 prompt(160) — 공식 신기능 5종이 `Claude/` KB의 설정·관리 노트에 아직 미반영.
- **제안**: KB 설정/관리 노트에 신기능 섹션 추가(`/kb-sync --deep` 또는 `/kb-ingest`).

### [done] kb-ingest · Anthropic Managed Agents + Multiagent sessions (공식)
- **source**: Anthropic release notes
- **url**: https://platform.claude.com/docs/en/release-notes/overview
- **근거**: Managed Agents 공개베타·webhooks(5/29), Multiagent sessions(5/6). 우리가 Workflow·서브에이전트를 적극 쓰는데 공식 멀티에이전트 기능이 KB에 없음.
- **제안**: 멀티에이전트/Managed Agents 개념을 KB 노트로 박제.

### [done] command · skill 토큰 풋프린트 점검 (영감: "Skills cost tokens even when they don't fire")
- **source**: dev.to #claudecode
- **url**: https://dev.to/kenimo49/claude-code-skills-cost-tokens-even-when-they-dont-fire-i-measured-5-skills-across-7-hours-the-8jo
- **근거**: skill은 트리거 안 해도 description이 컨텍스트 토큰 비용을 발생시킨다. 우리 vault는 kb-assistant 등 다수 skill을 보유 → 누적 비용 점검 가치.
- **제안**: 우리 skill들의 description 토큰 풋프린트를 집계하는 경량 `/skill-audit` command, 또는 인사이트만 KB 박제.

### [done] kb-ingest · "the agent bug lives in the harness"
- **source**: dev.to #claudecode
- **url**: https://dev.to/mjmirza/the-agent-bug-you-keep-blaming-on-the-prompt-lives-in-the-harness-2hkb
- **근거**: 에이전트 버그의 근원이 프롬프트가 아니라 harness라는 관점 — KB의 [[agent-harness-taxonomy]]와 직접 연결.
- **제안**: harness 노트에 섹션 추가 또는 별도 ingest.

### [done] kb-ingest · "I design with Claude more than Figma now" (Jane Street)
- **source**: Hacker News (267pt/237cm)
- **url**: https://blog.janestreet.com/i-design-with-claude-code-more-than-figma-now-index/
- **근거**: HN 고점수의 고품질 실전 워크플로우 글 — 디자인/프로토타이핑에 Claude Code 활용.
- **제안**: 활용 사례로 KB 박제.

### [done] watch · claude-code-plugins-plus-skills 마켓플레이스
- **source**: GitHub topic:claude-code+anthropic (★2,328)
- **url**: https://github.com/jeremylongshore/claude-code-plugins-plus-skills
- **근거**: 425 plugins / 2,810 skills / 200 agents 오픈소스 마켓플레이스 — 향후 skill/agent 발굴 소스.
- **제안**: 북마크(관찰). 필요 시 개별 skill을 평가 후 도입.

### [done] rule · 자연어 가드레일 생성 패턴 (영감: oh-my-harness)
- **source**: GitHub topic:claude-code+anthropic (★12)
- **url**: https://github.com/kyu1204/oh-my-harness
- **근거**: 자연어로 CLAUDE.md/rules 가드레일을 생성·강제하는 접근 — 우리 vault-rules.md 관리에 참고.
- **제안**: 패턴 검토 후, 유용하면 rule 작성 가이드에 반영.

### [done] kb-ingest · "cut AI engineering costs by 62%"
- **source**: dev.to #claudecode (8rxn)
- **url**: https://dev.to/gaurav_vij137/i-kept-using-claude-code-added-one-thing-to-it-cut-ai-engineering-costs-by-62-52ke
- **근거**: Claude Code 비용 최적화 실전 — 우리가 cron에 sonnet 티어를 쓰는 비용 전략과 연결.
- **제안**: 비용 최적화 인사이트를 KB 박제.

<!-- overflow: 52건 미적재 (이미 seen 처리되어 재출현하지 않음) — 첫 수집이라 과거 backlog/기존 인기 repo 다수. 정상 운영(매일)에선 하루 소수만 신규. -->

