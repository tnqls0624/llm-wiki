---
description: KB 산출물 품질을 골든셋으로 관측하고 리포트를 만든다 (판정하지 않는다)
argument-hint: [--type grounding|routing] [--seed] [--rotate N] [--reveal]
---

# KB Eval: 산출물 품질 관측

계약 테스트(306개)는 **메커니즘**만 본다 — 훅이 도는지, 가드가 실패를 내는지. 이 커맨드는 그 뒤에 남는 질문을 다룬다: **LLM이 쓴 내용이 맞는가.**

## 0. 이 도구는 판정하지 않는다 (가장 먼저 읽는다)

v1·v2·v3는 각각 독립 감사(12 에이전트 × 3회)에서 뚫렸다. 매번 지표를 고쳤고 매번 다른 입력으로 우회로가 열렸다. 공통 구조는 하나다: **게이트의 입력을 채점자가 전부 통제한다** — 원장·케이스 파일·큐·노트·플래그가 모두 같은 에이전트의 쓰기 범위 안이다. 그 조건에서 통과/실패를 선언하는 exit code는 거짓 안전감만 만든다.

> **exit code는 도구 상태다**: `0` 리포트 생성됨 · `1` 도구가 돌지 못함(입력 손상 등). **통과·실패가 아니다.**

**여전히 강제하는 것은 자료 위생뿐이다** — 원장에 들어가는 관찰이 형식적으로 말이 되는지. **강제하지 않는 것**: 채점자가 정답을 미리 보는 것, 원장·케이스 파일을 고치는 것, 주장 수를 발명하는 것, 유리한 케이스만 채점하는 것. 리포트가 그것을 **보여줄** 뿐이다.

### 그래서 채점자의 성실성이 전부다
- 이번 세션에서 `radar-queue.md`나 원장을 읽었으면 → **routing 채점을 직접 하지 말고** `general-purpose` 서브에이전트에 위임한다. 위임 프롬프트에 **큐 파일과 원장을 읽지 말라**고 명시한다.
- 채점 **전에** `--reveal`을 보지 않는다. 정답을 배우는 행위다.
- 유리한 케이스만 고르지 않는다. 막지는 않지만 리포트의 `coverage`가 드러낸다.

## 1. 케이스 확보

```bash
python3 .claude/kb-eval.py --seed
python3 .claude/kb-eval.py --seed --rotate 2     # 표본을 회전시킬 때
python3 .claude/kb-eval.py --list --type grounding
```

`--seed`는 **append-mostly**다: 기존 `case id`를 보존하고, 상한(grounding 6 · routing 12)에 못 미칠 때만 추가하고, 대상이 사라지면 삭제 대신 `retired`로 표시한다.

**`--rotate N`은 사람이 명시할 때만 돈다.** 상한에 도달하면 새로 쓴 노트가 표본에 들어오지 못하는데 — 검증이 가장 필요한 콘텐츠가 바로 그것이다 — 회전은 추이를 끊으므로 자동화하지 않는다. 리포트의 `not_covered`가 회전할 시점을 알려준다.

출력의 `notes`·`gold_distribution`·`duplicate_titles_dropped`·`not_covered`를 읽는다.

## 2. 채점 — 관찰만 보고한다

> **판단은 LLM, 산술은 코드.** `score`·`verdict`를 제출하면 거부된다(`Score`·`my_score` 같은 변형도). 알 수 없는 키도 거부된다 — 조용히 무시하면 네가 말한 것이 읽혔다고 오해하게 된다.

### grounding — 센다
노트를 `Read`로 읽고, `source_urls`의 원문을 가져와(공식 문서는 `curl -s https://code.claude.com/docs/<slug>.md`, 그 외는 `WebFetch`) 대조한다.

- 보는 것: 본문의 **사실 주장**(명령·플래그·설정키·환경변수·동작 설명)이 원문에 실재하는가.
- 보지 않는 것: 문체·분량·번역 품질.
- 죽은 링크는 세지 않고 `findings`에 적는다.

제출: `claims_checked` · `claims_grounded` · `contradictions` (**세 값 모두 정수로 명시** — 생략하면 "찾아보지 않았다"와 "없었다"가 원장에서 구분되지 않는다) + `findings[]`.

- `claims_checked`는 **3 이상**, `--list`가 준 **`max_claims` 이하**(본문 분량에서 계산).
- 셈이 모순되면 거부. **출처가 없는 노트는 채점 자체가 성립하지 않는다**(grounding의 정의가 '출처 원문에 실재하는가'이므로) — `skipped`로 낸다.

### routing — 결정한다
제목·종류만 보고 `queue` / `drop`을 판단한다. 제출: `decision` + `findings[]`.

### 채점 불가면 skipped
`{"case": "...", "skipped": "실질적인 사유"}`. **사유는 비어 있지 않은 문자열이어야 한다**(`false`·`0`·`""` 거부). `skipped`와 채점값을 함께 낼 수 없다.

## 3. 적재

```bash
python3 .claude/kb-eval.py --record /tmp/eval-results.json
```

형식 위반 하나에 **전체 거부**(부분 적재로 원장이 오염되지 않게). 결과 파일 2MiB 이하. 기록만 하고 판정은 없다.

## 4. 리포트

```bash
python3 .claude/kb-eval.py --report            # 사람이 읽는다
python3 .claude/kb-eval.py --report --reveal   # 케이스 id까지 (채점 후에만)
```

리포트가 나란히 보여주는 것:

| 신호 | 무엇을 드러내나 |
|---|---|
| `coverage` | 채점/skipped/코호트에 없는 활성 케이스 — 유리한 것만 골랐는지 |
| `accuracy` + `constant_strategy_would_score` | 정확도를 **가공하지 않고** 상수 전략 값과 나란히. 실제 정확도가 그 값 이하면 판단의 증거가 없다 |
| `class_recalls` · `graded_per_class` | 클래스별 성적과 표본 크기 |
| `accuracy_by_cohort` | routing 추이(코호트별) |
| `flagged` | grounding 기준 미달·모순·하락 |
| `age_days` | 마지막 채점이 언제였나 |
| `not_covered` | 표본 밖 노트·큐 라벨 수 |
| `concerns` | 위 신호에서 사람이 봐야 할 것들 |
| `limits` | 이 도구가 막지 못하는 것(매번 함께 출력) |

**`concerns`가 비어 있다고 "통과"가 아니다.** 신호가 없다는 뜻이고, 신호가 없는 이유가 "잘하고 있어서"인지 "안 봐서"인지는 `coverage`와 `age_days`가 말해준다.

## 5. 보고

- 코호트·커버리지·정확도(상수 전략 대비)·`concerns`를 사용자에게 그대로 전한다. 요약하면서 판정으로 바꾸지 않는다.
- `findings`에서 **반복되는 실패 패턴**을 지목한다. 여러 노트에서 같은 종류가 나오면 그건 노트 문제가 아니라 `/kb-sync`·`/kb-ingest` **프롬프트**의 문제다.

## 한계 (명시)

- **LLM-judge는 그 자체로 오류원이다.** 절대값보다 같은 케이스의 **추이**를 신뢰한다.
- **routing 골든셋은 사용자 결정 이력만큼만 자란다**(2026-08-29 기준 9 queue / 1 drop). 표본이 작고 치우쳐 있으면 클래스별 수치를 신뢰하기 어렵다 — 리포트가 그 사실을 `concerns`로 말한다. `[expired]`는 정답으로 쓰지 않는다(30일 미처리는 '거부'가 아니라 '처리 못 함'이며, 사용자가 내리지 않은 판단을 정답이라 우기는 셈이다).
- grounding은 출처 원문이 바뀌면 점수가 흔들린다 — `kb-source-hashes.py`의 구조 변경 감지와 함께 보면 원인 분리가 된다.
- **대화형·수동 실행 전용이다. cron에 걸지 않는다.**
