---
description: 공식 문서(llms.txt)의 변경분을 슬러그 diff로 잡아 KB에 반영한다
argument-hint: [--deep <노트번호>]
---

# KB Sync: 공식 문서 변경분을 KB에 반영

인자: `$ARGUMENTS`

KB(`Claude/` 26개 노트 + `Claude/Claude.md` MOC)를 공식 문서 최신 상태와 맞춘다. 기준은 각 노트 frontmatter의 `sources` 슬러그 배열이다.

## 1. 공식 문서 슬러그 수집
- `curl -s https://code.claude.com/docs/llms.txt`로 인덱스를 가져온다. 거기서 문서 슬러그를 **전수 추출**한다(각 페이지 raw는 `https://code.claude.com/docs/en/<slug>.md`).

## 2. KB와 diff (슬러그 레벨)
- `Claude/*.md` 모든 노트의 frontmatter `sources`를 읽어 **합집합**을 만든다(MOC는 빈 배열이므로 제외).
- 공식 슬러그 집합과 비교한다:
  - **신규 슬러그** = 공식에 있으나 KB `sources` 합집합에 없음.
  - **사라진 슬러그** = KB `sources`에 있으나 공식 인덱스에 없음.

## 3. 반영
- **신규 슬러그**: `curl`로 raw markdown을 fetch → 주제를 판별 → 주제가 맞는 기존 노트에 새 섹션으로 추가하고 그 노트 `sources`에 슬러그를 더한다. 어느 기존 노트에도 맞지 않으면 **새 노트**를 만든다(파일명은 기존 번호를 이어서 `Claude/NN 제목.md`, frontmatter 3필드 `title`/`updated`/`sources`, 본문 말미에 `## 원본 문서` URL 목록, 허브 링크 `허브: [[Claude]]`).
- **사라진 슬러그**: 해당 슬러그를 다루던 노트 섹션에 `> [!warning] deprecated` 콜아웃으로 표시한다(내용은 삭제하지 말고 폐기 사실만 명시).
- **whats-new 주간 페이지**(예: `whats-new-wNN`): 별도 노트를 만들지 말고 **`26 변경 이력과 용어집`에 누적**한다(주간 What's New 섹션에 이어 붙임).

## 4. 위임 (신규 페이지가 많을 때)
- 새로 만들어야 할 **노트가 5개를 초과**하면 직접 처리하지 말고 `kb-updater` 서브에이전트에 위임한다(Agent tool, `subagent_type: kb-updater`). 신규 슬러그 목록과 raw URL을 넘기고, 에이전트가 갱신 의무 3단계 중 노트 측 단계(`updated`·MOC)를 자기 컨텍스트에서 처리하게 한다. 에이전트 반환 후 **메인 세션이 `hot.md` 단계를 마무리**한다.

## 5. 갱신 의무
- 노트를 만들거나 바꿨으면 `.claude/rules/vault-rules.md`의 "Update duty (CANONICAL — 3 steps)"를 수행한다(정본 참조 — 단계·수치는 여기서 재명세하지 않는다). MOC는 `Claude/Claude.md`를 갱신한다.

## 6. 검증 (마무리)
- `bash`로 `python3 .claude/kb-lint.py --online`을 실행해 KB가 공식 인덱스와 정합한지 확인한다. 남은 문제가 있으면 고치고 재실행해 0을 확인한다.

## 한계 (명시)
- 이 흐름은 **슬러그 레벨 diff만** 한다 — 기존 페이지의 *내용* 변경(같은 슬러그인데 본문이 갱신됨)은 감지하지 못한다.
- `--deep <노트번호>` 인자를 받으면: 해당 노트의 `sources` 슬러그들을 모두 재fetch해 노트 본문과 대조하고, 달라진 부분을 갱신한다(내용 레벨 동기화).

## 7. 보고
신규/사라진 슬러그 개수, 어떤 노트를 만들고 고쳤는지, (위임했다면) kb-updater 결과, lint 결과를 요약해 보고하라.
