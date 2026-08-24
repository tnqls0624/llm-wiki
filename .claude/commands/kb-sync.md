---
description: 공식 문서(llms.txt)의 변경분을 슬러그 diff로 잡아 KB에 반영한다
argument-hint: [--deep <노트번호>]
---

# KB Sync: 공식 문서 변경분을 KB에 반영

인자: `$ARGUMENTS`

KB(`80 Tooling/` 공식문서 노트 29개 + `80 Tooling/80 Tooling.md` MOC)를 공식 문서 최신 상태와 맞춘다. 기준은 각 노트 frontmatter의 `source_urls` 슬러그 배열이다.

## 1. 공식 문서 슬러그 수집
- `curl -s https://code.claude.com/docs/llms.txt`로 인덱스를 가져온다. 거기서 문서 슬러그를 **전수 추출**한다(각 페이지 raw는 `https://code.claude.com/docs/en/<slug>.md`).

## 2. KB와 diff (슬러그 레벨)
- `80 Tooling/*.md` 모든 노트의 frontmatter `source_urls`를 읽어 **합집합**을 만든다(MOC는 빈 배열이므로 제외).
- 공식 슬러그 집합과 비교한다:
  - **신규 슬러그** = 공식에 있으나 KB `source_urls` 합집합에 없음.
  - **사라진 슬러그** = KB `source_urls`에 있으나 공식 인덱스에 없음.

## 3. 반영
- **신규 슬러그**: `curl`로 raw markdown을 fetch → 주제를 판별 → 주제가 맞는 기존 노트에 새 섹션으로 추가하고 그 노트 `source_urls`에 슬러그를 더한다. 어느 기존 노트에도 맞지 않으면 **새 노트**를 만든다(파일명은 기존 번호를 이어서 `80 Tooling/NN 제목.md`, frontmatter §12 11필드 — 정본 `.claude/kb-required-fields.txt`, `type`은 보통 `playbook`(허용값 `.claude/kb-allowed-types.txt`), 본문 말미에 `## 원본 문서` URL 목록, 허브 링크 `허브: [[80 Tooling]]`).
- **사라진 슬러그**: 해당 슬러그를 다루던 노트 섹션에 `> [!warning] deprecated` 콜아웃으로 표시한다(내용은 삭제하지 말고 폐기 사실만 명시).
- **whats-new 주간 페이지**(예: `whats-new-wNN`): 별도 노트를 만들지 말고 **`26 변경 이력과 용어집`에 누적**한다(주간 What's New 섹션에 이어 붙임).

## 4. 위임 (신규 페이지가 많을 때)
- 새로 만들어야 할 **노트가 5개를 초과**하면 직접 처리하지 말고 `kb-updater` 서브에이전트에 위임한다(Agent tool, `subagent_type: kb-updater`). 신규 슬러그 목록과 raw URL을 넘기고, 에이전트가 갱신 의무 3단계 중 노트 측 단계(`updated`·MOC)를 자기 컨텍스트에서 처리하게 한다. 에이전트 반환 후 **메인 세션이 `hot.md` 단계를 마무리**한다.

## 5. 갱신 의무
- 노트를 만들거나 바꿨으면 `.claude/rules/vault-rules.md`의 "Update duty (CANONICAL — 3 steps)"를 수행한다(정본 참조 — 단계·수치는 여기서 재명세하지 않는다). MOC는 `80 Tooling/80 Tooling.md`를 갱신한다.

## 6. 검증 (마무리)
- `bash`로 `python3 .claude/kb-lint.py --online`을 실행해 KB가 공식 인덱스와 정합한지 확인한다. 남은 문제가 있으면 고치고 재실행해 0을 확인한다.

## 6b. 콘텐츠 드리프트 감지 (같은 슬러그 내용 변경)
- `python3 .claude/kb-source-hashes.py --json`을 실행한다. 출처 원문을 `runtime/source-hashes.json`과 비교해 **본문이 바뀐 슬러그**(슬러그는 그대로인데 공식문서 내용만 갱신된 경우)를 결정론적으로 잡는다.
- 변경은 **두 층으로 보고된다**(2026-08-22 도입). 이 구분이 이 단계의 핵심이다:
  - `changed_structural` — 구조 지문(헤딩 + 백틱 식별자 집합)이 달라짐. 섹션이나 설정키·플래그가 생기거나 사라졌다는 뜻 → **종합 노트가 낡았을 가능성이 높다.**
  - `changed_prose_only` — 원문 바이트만 달라짐(표현·오타·링크 재작성). 노트 반영은 보통 불필요.
  - `changed_unknown` — 이전 스냅샷이 구 포맷이라 구조 비교 불가. 구조 변경이라 단정하지 않는다.
- **큐에는 `changed_structural` 만 적재한다.** `changed` 전체를 적재하지 마라 — 이 문서 사이트는 변경 속도가 커서 `changed` 가 매 실행 출처의 60~80%를 차지한다(2026-08-22 실측: 07-27→08-10 206/251 · 08-10→08-20 187/253 · 08-20→08-22 149/254, 그리고 스냅샷 갱신 직후 수 분 만에 12건이 다시 full 변경으로 잡혔는데 그 12건 전부가 프로즈만이었다). 전체를 적재하면 큐가 노이즈로 죽는다.
- 적재 형식: **노트 단위로 집계**해 `### [pending] kb-sync · <노트>: 출처 구조 변경(<슬러그들>) — /kb-sync --deep` 항목들을 **임시 파일에 쓰고 `python3 .claude/radar-collect.py --append-queue <파일>`로 적재**한다(2026-08-24 확립 — radar-queue.md는 harness가 sensitive로 분류해 직접 Edit이 거부된다; 회당 상한 8이므로 초과분은 나눠 호출). **노트를 직접 고치지 말 것**(자동 무효화 금지 — 사용자가 review에서 `--deep`로 결정. collect↔review 분리).
- 마지막에 `python3 .claude/kb-source-hashes.py --update`로 스냅샷을 갱신한다(다음 실행의 기준선). 스냅샷 값은 `{full, skel}` 형태다.
- 참고: `errors`(fetch 차단)로 나온 항목은 이전 해시가 보존되므로 `removed` 로 오인되지 않는다(2026-08-22 버그 수정 — 그 전엔 외부 블로그 URL 2건이 매 실행 `removed` 로 보고됐다). `removed` 는 이제 "어떤 노트도 더 이상 이 출처를 참조하지 않음"만 뜻한다.

## 한계 (명시)
- §1~3의 흐름은 **슬러그 레벨 diff만** 한다 — 기존 페이지의 *내용* 변경은 §6b의 해시 감지가 보완한다(노트 자동 수정은 안 하고 review 큐에만 적재).
- `--deep <노트번호>` 인자를 받으면: 해당 노트의 `source_urls` 슬러그들을 모두 재fetch해 노트 본문과 대조하고, 달라진 부분을 갱신한다(내용 레벨 동기화). §6b가 큐에 올린 노트가 주 대상.

## 7. 보고
신규/사라진 슬러그 개수, 어떤 노트를 만들고 고쳤는지, (위임했다면) kb-updater 결과, lint 결과를 요약해 보고하라.
