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

