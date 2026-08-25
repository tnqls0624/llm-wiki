---
description: LLM 산출물 품질을 골든셋으로 채점하고 회귀를 잡는다 (계약 테스트가 못 보는 축)
argument-hint: [--type grounding|routing] [--seed] [--reveal]
---

# KB Eval: 산출물 품질 평가

계약 테스트(292개)는 **메커니즘**만 본다 — 훅이 도는지, 가드가 `rc=1`을 내는지. 이 커맨드는 그 뒤에 남는 질문을 다룬다: **LLM이 쓴 내용이 맞는가.**

## 0. 이 도구가 막는 것과 막지 못하는 것 (가장 먼저 읽는다)

v1·v2는 각각 독립 감사(12 에이전트)에서 뚫렸다. v3는 그 경계를 인정하고 설계됐다.

> **강제한다**: 코호트 전량 제출 · 같은 날 재굴림 차단 · 정답 미노출 · balanced accuracy · grounding 앵커(노트 존재·본문 해시·주장 수 상한) · 판정 불가의 분리 · 게이트가 `verdict`를 읽음
>
> **강제하지 못한다**: 채점자가 `radar-queue.md`를 읽어 정답을 아는 것 · 채점자가 원장·케이스 파일을 고치는 것 · grounding 주장 수를 상한 안에서 발명하는 것

**그래서 이 도구는 성실한 채점자의 품질 회귀를 잡는 장치이고, 부정직한 채점자를 막는 장치가 아니다.** `--regress` 출력의 `enforcement_limits`가 매번 이 사실을 함께 낸다. 결과는 "신뢰하되 검증 불가"로 읽는다.

### 채점자 오염 규칙
routing의 정답은 사용자가 `/claude-radar review`에서 내린 `[done]`/`[dismissed]` 결정이고 `runtime/radar-queue.md`에 그대로 있다. 제목이 곧 조인 키다.

- 이번 세션에서 `radar-queue.md`를 읽었거나 큐를 요약한 적이 있으면 → **routing 채점을 직접 하지 말고** `general-purpose` 서브에이전트에 위임한다. 위임 프롬프트에 **큐 파일과 원장을 읽지 말라**고 명시한다.
- 채점 **전에** `--reveal`이나 `--summary --reveal`을 보지 않는다. 그건 정답을 배우는 행위다.
- `grounding`은 정답 레이블이 없다(원문 대조 자체가 판정).

## 1. 케이스 확보

```bash
python3 .claude/kb-eval.py --seed
python3 .claude/kb-eval.py --list --type grounding
```

`--seed`는 **append-mostly**다: 기존 `case id`를 보존하고, 상한(grounding 6 · routing 12)에 못 미칠 때만 추가하고, 대상이 사라지면 삭제 대신 `retired`로 표시한다. 상한은 **부활에도** 적용된다. 본문이 최소 주장 수를 담을 수 없을 만큼 짧은 노트는 애초에 케이스가 되지 않는다.

`--seed` 출력의 `warning`·`gold_distribution`·`duplicate_titles_dropped`를 **반드시 읽는다.**

## 2. 채점 — 관찰만 보고한다

> **판단은 LLM, 산술은 코드.** `score`·`verdict`를 제출하면 거부된다(`Score`·`my_score` 같은 변형도). 알 수 없는 키도 거부된다 — 조용히 무시하면 네가 말한 것이 읽혔다고 오해하게 된다.

### grounding — 센다
노트를 `Read`로 읽고, `source_urls`의 원문을 가져와(공식 문서는 `curl -s https://code.claude.com/docs/<slug>.md`, 그 외는 `WebFetch`) 대조한다.

- 보는 것: 본문의 **사실 주장**(명령·플래그·설정키·환경변수·동작 설명)이 원문에 실재하는가.
- 보지 않는 것: 문체·분량·번역 품질.
- 죽은 링크는 세지 않고 `findings`에 적는다 — 링크 수명이 점수를 흔들면 안 된다.

제출: `claims_checked` · `claims_grounded` · `contradictions` (**정수만** — 실수·문자열·불린 거부) + `findings[]`.

- `claims_checked`는 **3 이상**, 그리고 `--list`가 준 **`max_claims` 이하**여야 한다(본문 분량에서 계산됨).
- 셈이 모순되면(`grounded > checked` 등) 거부.
- `contradictions > 0`이면 비율과 무관하게 `fail`이고, **게이트가 이를 읽는다**.

### routing — 결정한다
제목·종류만 보고 `queue`(큐에 올림) / `drop`(버림)을 판단한다.

제출: `decision` + `findings[]`(근거 한 줄).

### 채점 불가면 skipped
출처가 전멸했거나 노트를 읽을 수 없으면 `{"case": "...", "skipped": "이유"}`로 낸다. 코호트 전량 요구를 만족하면서 채점 불가를 표현하는 유일한 방법이다. 삭제된 노트에 점수를 주는 것은 거부된다.

## 3. 적재 — 코호트 단위

```bash
python3 .claude/kb-eval.py --record /tmp/eval-results.json
```

**한 번의 `--record`는 그 타입의 활성 케이스 전량이다.** 부분 제출은 거부된다 — v2는 유리한 케이스만 골라 제출하면 통과했다. 타입은 나눠 낼 수 있다(grounding 코호트와 routing 코호트를 따로).

- **같은 날 같은 타입의 두 번째 코호트는 거부된다.** 정말 다시 돌려야 하면 `--force`. v2는 무제한 재제출을 허용했고 `--record`가 틀린 케이스를 알려줬으므로 2회차 만점이 보장됐다.
- 출력은 `failed_count`만 낸다 — **어느 케이스가 틀렸는지는 알려주지 않는다.**
- 형식 위반 하나에 **전체 거부**. 결과 파일은 2MiB 이하.

## 4. 회귀 판정

```bash
python3 .claude/kb-eval.py --regress            # 실패 시 exit 1
python3 .claude/kb-eval.py --regress --reveal   # 사람이 원인을 볼 때
python3 .claude/kb-eval.py --summary [--reveal]
```

게이트가 보는 것:

1. **grounding `verdict=fail`** — floor(0.8) 미달 또는 모순 1건 이상.
2. **grounding 하락** — 직전 **코호트** 대비 0.15 이상. 단 **본문 해시**가 바뀌었으면 `rebaselined`(다른 텍스트를 비교하지 않는다). 해시는 frontmatter를 제외하므로 `updated:` 범프로 회귀가 세탁되지 않는다.
3. **routing balanced accuracy ≤ 0.5** — 클래스별 recall의 평균이다. **상수 전략(항상 한 클래스)은 표본 크기·불균형과 무관하게 정확히 0.5**가 되므로 초과를 요구하면 잡힌다. v2의 majority baseline은 상수 전략이 결정론적으로 달성하는 값이라 동률에서만 걸렸고, 균형 표본이 커지면 오히려 약해졌으며, 단일 클래스에서는 1.0이 되어 완벽한 채점자도 영구 실패했다.
4. **원장 손상** — 읽을 수 없는 줄이 있으면 부분 이력으로 판정하지 않는다.

**판정 불가(`undecidable`)는 실패도 통과도 아니다**: 정답이 한 클래스뿐, 큐에서 라벨 소실, `skipped` 제출. 게이트는 이것을 실패로 만들지 않고 그대로 보고한다.

은퇴 케이스와 고아 행(원장에만 있는 id)은 게이트를 막지 않는다.

## 5. 보고

- 코호트(`run`) · `failed_count` · `balanced_accuracy`와 `class_recalls` · `undecidable` · `enforcement_limits`.
- `findings`에서 **반복되는 실패 패턴**을 지목한다. 여러 노트에서 같은 종류가 나오면 그건 노트 문제가 아니라 `/kb-sync`·`/kb-ingest` **프롬프트**의 문제다 — 커맨드 수정을 제안한다.

## 한계 (명시)

- **LLM-judge는 그 자체로 오류원이다.** 절대값보다 같은 케이스의 **추이**를 신뢰한다.
- **routing 골든셋은 사용자 결정 이력만큼만 자란다** (2026-08-26 기준 9 queue / 1 drop). balanced accuracy는 불균형에 강하지만, 표본이 10개면 통계적으로 약하다 — `[dismissed]` 결정이 쌓여야 이 축이 힘을 얻는다. `[expired]`는 정답으로 쓰지 않는다(30일 미처리는 '거부'가 아니라 '처리 못 함'이며, 사용자가 내리지 않은 판단을 정답이라 우기는 셈이다).
- grounding은 출처 원문이 바뀌면 점수가 흔들린다 — `kb-source-hashes.py`의 구조 변경 감지와 함께 보면 원인 분리가 된다.
- **대화형·수동 실행 전용이다. cron에 걸지 않는다** — 채점이 LLM 비용이고, 무인 채점 실패는 또 하나의 조용한 실패 경로가 된다.
