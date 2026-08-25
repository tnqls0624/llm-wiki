---
description: LLM 산출물 품질을 골든셋으로 채점하고 회귀를 잡는다 (계약 테스트가 못 보는 축)
argument-hint: [--type grounding|routing] [--seed]
---

# KB Eval: 산출물 품질 평가

계약 테스트(277개)는 **메커니즘**만 본다 — 훅이 도는지, 가드가 `rc=1`을 내는지, 영수증이 남는지. 이 커맨드는 그것들이 전부 통과한 뒤에도 남는 질문을 다룬다: **LLM이 쓴 내용이 맞는가.**

엔진은 `.claude/kb-eval.py`(0-LLM, 결정론적)다. 역할이 엄격히 갈린다:

> **판단은 LLM, 산술은 코드.** 너는 관찰한 **수**만 보고한다. `score`도 `verdict`도 제출하지 않는다 — 제출하면 거부된다. 점수는 스크립트가 계산한다.

초판은 이 선이 없어서 실패했다. judge가 자기 점수를 매기니 앵커가 없었고, **노트가 삭제된 케이스에 1.0/pass가 그대로 수락**됐다. 점수를 만드는 주체와 채점받는 주체가 같으면 그건 평가가 아니다.

## 0. 채점자 오염 규칙 (먼저 읽는다)

**정답을 본 컨텍스트는 채점할 수 없다.** routing의 정답은 사용자가 `/claude-radar review`에서 내린 `[done]`/`[dismissed]` 결정이며, `runtime/radar-queue.md`에 그대로 적혀 있다.

- 이번 세션에서 `radar-queue.md`를 읽었거나 큐 상태를 요약한 적이 있으면 → **routing 채점을 직접 하지 말고** `general-purpose` 서브에이전트에 위임한다(격리 컨텍스트). 위임 프롬프트에 **큐 파일을 읽지 말라**고 명시한다.
- `grounding`은 정답 레이블이 없다(원문 대조 자체가 판정). 메인 세션 채점도 가능하지만 노트가 크면 위임이 낫다.
- 케이스 파일(`.claude/evals/cases.jsonl`)에는 **정답이 없다** — 저장하지 않는다. 정답은 `--record` 시점에 스크립트가 큐에서 도출한다. 그러니 "케이스 파일을 열어 정답을 찾는" 경로 자체가 없다. 대신 큐를 열어보는 것이 곧 오염이다.

## 1. 케이스 확보

```bash
python3 .claude/kb-eval.py --seed          # 케이스 생성/갱신
python3 .claude/kb-eval.py --list --type grounding
```

`--seed`는 **append-mostly**다: 기존 `case id`를 보존하고, 활성 케이스가 상한에 못 미칠 때만 추가하고, 대상이 사라진 케이스는 삭제하지 않고 `retired`로 표시한다. 재추첨하지 않으므로 점수 추이가 끊기지 않는다. (초판은 매번 전체를 다시 뽑아 id가 흔들렸고, 원장의 과거 점수가 고아가 됐다.)

`--seed` 출력의 `warning`과 `routing_balance`를 **반드시 읽는다.** 골든셋이 한쪽으로 치우쳤으면 그 사실이 곧 평가의 한계다.

## 2. 채점

### grounding — 세기만 한다
케이스마다: 노트를 `Read`로 읽고, `source_urls`의 각 슬러그 원문을 가져와(공식 문서는 `curl -s https://code.claude.com/docs/<slug>.md`, 그 외는 `WebFetch`) 대조한다.

- 보는 것: 본문의 **사실 주장**(명령·플래그·설정키·환경변수·동작 설명)이 원문에 실재하는가.
- 보지 않는 것: 문체·분량·번역 품질·구성.
- 출처가 죽은 링크면 그 항목은 세지 않고 `findings`에 적는다 — 링크 사망을 내용 오류로 채점하면 점수가 링크 수명을 따라 흔들린다.

제출: `claims_checked`(검사한 주장 수) · `claims_grounded`(원문에서 확인된 수) · `contradictions`(원문과 **반대**되는 주장 수) · `findings[]`.

- `claims_checked`가 **3 미만이면 거부**된다 — 안 보고 통과할 수 없다.
- `claims_grounded > claims_checked` 같은 모순된 셈은 거부된다.
- `contradictions > 0`이면 비율과 무관하게 `fail`이다.
- `findings`에는 문제가 된 주장을 **인용**해 남긴다("~라고 썼는데 원문에는 없음"). 근거 없는 총평은 쓸모없다.

### routing — 결정만 한다
케이스마다 제목·종류만 보고, 이 vault(Claude Code KB + AI-Infra 학습 프레임워크)에 **큐로 올릴지(queue) 버릴지(drop)** 판단한다.

제출: `decision`(queue|drop) + `findings[]`(판단 근거 한 줄).

## 3. 적재

결과를 `/tmp`에 쓰고 스크립트로 넘긴다(원장 직접 편집 금지).

```json
{"judge": "opus-5", "results": [
  {"case": "g-xxxxxxxx", "claims_checked": 12, "claims_grounded": 11, "contradictions": 0,
   "findings": ["'--foo' 플래그를 썼는데 원문에는 '--bar'만 있음"]},
  {"case": "r-xxxxxxxx", "decision": "drop", "findings": ["Go 전용 도구 — 이 vault와 접점 없음"]}
]}
```

```bash
python3 .claude/kb-eval.py --record /tmp/eval-results.json
```

하나라도 형식을 어기면 **전체가 거부된다**(부분 적재로 원장이 오염되지 않게). 결과 수는 활성 케이스 수를 넘을 수 없고, 같은 케이스를 두 번 제출할 수 없다(가짜 회귀 방지).

## 4. 회귀 판정

```bash
python3 .claude/kb-eval.py --regress    # 실패 시 exit 1
python3 .claude/kb-eval.py --summary
```

게이트가 보는 것 셋:
1. **grounding floor 미달** (기본 0.8) — grounding 전용이다.
2. **grounding 직전 대비 0.15 이상 하락** — 단, 노트 내용 해시가 바뀌었으면 회귀가 아니라 `rebaselined`로 분류한다(다른 텍스트를 비교하지 않는다).
3. **routing이 majority baseline 이하** — 이게 핵심이다. 골든셋이 9 queue / 1 drop이면 **항상 "queue"만 답하는 채점자가 0.90**을 받는다. 그 점수는 통과가 아니다. baseline을 넘지 못하면 "채점자가 판단했다는 증거가 없다"로 실패 처리한다.

신규 케이스는 baseline만 세우고 회귀로 보지 않는다. 은퇴 케이스와 고아 행(원장에만 있는 id)은 게이트를 막지 않는다.

## 5. 보고

- 케이스 수 · 평균 · `fail` 목록 · 회귀 여부 · **`routing_balance`와 baseline 판정**.
- `findings`에서 **반복되는 실패 패턴**을 지목한다. 한 노트의 오류는 그 노트 문제지만, 여러 노트에서 같은 종류가 나오면 그건 `/kb-sync`·`/kb-ingest` **프롬프트**의 문제다 — 그 경우 커맨드 수정을 제안한다.

## 한계 (명시)

- **LLM-judge는 그 자체로 오류원이다.** 점수의 절대값보다 같은 케이스의 **추이**를 신뢰한다.
- **routing 골든셋은 사용자 결정 이력만큼만 자란다** (2026-08-25 기준 9 queue / 1 drop, baseline 0.90). 이 불균형이 지금 이 하네스의 가장 큰 약점이다 — baseline 게이트는 무의미한 점수를 *탐지*할 뿐, 표본을 늘려주지는 않는다. `[expired]` 항목은 정답으로 쓰지 않는다(30일 미처리는 '거부'가 아니라 '처리 못 함'이며, 사용자가 내리지 않은 판단을 정답이라 우기는 셈이다).
- grounding은 출처 원문이 바뀌면 점수가 흔들린다 — `kb-source-hashes.py`의 구조 변경 감지와 함께 보면 원인 분리가 된다.
- 이 커맨드는 **대화형·수동 실행 전용**이다. cron에 걸지 않는다 — 채점 자체가 LLM 비용이고, 무인 채점 실패는 또 하나의 조용한 실패 경로가 된다.
