---
description: LLM 산출물 품질을 골든셋으로 채점하고 회귀를 잡는다 (계약 테스트가 못 보는 축)
argument-hint: [--type grounding|routing] [--seed]
---

# KB Eval: 산출물 품질 평가

계약 테스트(231개)는 **메커니즘**만 본다 — 훅이 도는지, 가드가 `rc=1`을 내는지, 영수증이 남는지. 이 커맨드는 그것들이 전부 통과한 뒤에도 남는 질문을 다룬다: **LLM이 쓴 내용이 맞는가.**

엔진은 `.claude/kb-eval.py`(0-LLM, 결정론적)이고 이 커맨드는 채점자다. 역할이 갈린다 — 케이스 시드·입력 조립·결과 검증·원장 적재·회귀 판정은 스크립트, 판단은 LLM.

## 0. 채점자 오염 규칙 (먼저 읽는다)

**정답을 본 컨텍스트는 채점할 수 없다.** `routing` 케이스의 정답(`gold`)은 사용자가 `/claude-radar review`에서 내린 `[done]`/`[dismissed]` 결정이고, 그건 `runtime/radar-queue.md`에 그대로 적혀 있다.

- 이번 세션에서 `radar-queue.md`를 읽었거나 큐 상태를 요약한 적이 있으면 → **routing 채점을 직접 하지 말고** `general-purpose` 서브에이전트에 위임한다(격리 컨텍스트). 위임 프롬프트에 큐 파일을 읽지 말라고 명시한다.
- `grounding`은 정답 레이블이 없으므로(원문 대조 자체가 판정) 메인 세션 채점도 가능하다. 다만 노트가 크고 출처가 여럿이면 컨텍스트 절약을 위해 위임이 낫다.
- `--list`는 이미 `gold`와 `min_score`를 지운 상태로 내려온다. 그 두 값을 케이스 파일에서 직접 찾아보는 행위 자체가 채점 무효화다.

## 1. 케이스 확보

```bash
python3 .claude/kb-eval.py --seed          # vault 현재 상태에서 케이스 재생성(필요할 때만)
python3 .claude/kb-eval.py --list --type grounding
```

`--seed`는 표본을 **결정론적으로**(노트명 sha256 정렬) 고른다 — 실행마다 케이스가 바뀌면 점수 추이가 의미를 잃는다. 노트가 추가돼 표본이 변하는 건 정상이지만, 점수 비교는 같은 `case id` 안에서만 유효하다.

## 2. 채점

### grounding
케이스마다: 노트를 `Read`로 읽고, `source_urls`의 각 슬러그 원문을 가져와(공식 문서는 `curl -s https://code.claude.com/docs/<slug>.md`, 그 외는 `WebFetch`) 대조한다.

- 보는 것: 본문의 **사실 주장**(명령·플래그·설정키·환경변수·동작 설명)이 원문에 실재하는가.
- 보지 않는 것: 문체·분량·번역 품질·구성. 그건 lint와 사람의 몫이다.
- 원문에 없는 주장 1건 = 감점, 원문과 **반대되는** 주장 = 즉시 `fail`.
- `findings`에는 문제가 된 주장을 **인용**해 남긴다("~라고 썼는데 원문에는 없음"). 근거 없는 총평은 쓸모없다.
- 출처가 죽은 링크면 그 항목은 채점에서 제외하고 `findings`에 적는다 — 링크 사망을 내용 오류로 채점하면 점수가 링크 수명을 따라 흔들린다.

제출: `score`(0~1, 검증된 주장 비율) + `verdict`(pass|fail) + `findings[]`.

### routing
케이스마다 제목·종류만 보고, 이 vault(Claude Code KB + AI-Infra 학습 프레임워크)에 **큐로 올릴지(queue) 버릴지(drop)** 판단한다.

제출: `decision`(queue|drop) + `findings[]`(판단 근거 한 줄). **`score`를 제출하면 거부된다** — 채점은 스크립트가 `gold`와 대조해 한다. 자기 점수를 매기게 하면 `gold`를 숨긴 의미가 사라진다.

## 3. 적재

결과를 `/tmp`에 쓰고 스크립트로 넘긴다(원장 직접 편집 금지 — `runtime/`은 무인 런에서 harness가 막고, 형식 검증도 스크립트에만 있다).

```json
{"judge": "opus-5", "results": [
  {"case": "g-xxxxxxxx", "score": 0.92, "verdict": "pass", "findings": ["..."]},
  {"case": "r-xxxxxxxx", "decision": "drop", "findings": ["..."]}
]}
```

```bash
python3 .claude/kb-eval.py --record /tmp/eval-results.json
```

하나라도 형식을 어기면 **전체가 거부된다**(부분 적재로 원장이 오염되지 않게). `violations`를 보고 고쳐 재시도한다.

## 4. 회귀 판정

```bash
python3 .claude/kb-eval.py --regress    # 기준 미달 또는 직전 대비 0.15↓ → exit 1
python3 .claude/kb-eval.py --summary    # 케이스별 최근 점수·실행 횟수
```

신규 케이스는 baseline만 세우고 회귀로 보지 않는다 — 첫 실행이 항상 실패하면 게이트가 죽는다.

## 5. 보고

- 케이스 수 · 평균 점수 · `fail` 목록 · 회귀 여부.
- `findings`에서 **반복되는 실패 패턴**을 지목한다. 한 노트의 오류는 그 노트 문제지만, 여러 노트에서 같은 종류가 나오면 그건 `/kb-sync`·`/kb-ingest` 프롬프트의 문제다 — 그 경우 커맨드 수정을 제안한다.
- 점수가 떨어졌으면 원인 케이스와 직전 점수를 함께 제시한다. "품질이 나빠졌다"만으로는 아무것도 고칠 수 없다.

## 한계 (명시)

- **LLM-judge는 그 자체로 오류원이다.** 점수의 절대값보다 같은 케이스의 **추이**를 신뢰한다.
- grounding은 출처 원문이 바뀌면 점수가 흔들린다 — `kb-source-hashes.py`가 구조 변경을 잡는 시점과 함께 보면 원인 분리가 된다.
- routing 골든셋은 사용자 결정 이력만큼만 자란다(2026-08-25 기준 10건). 적은 표본에서 나온 점수를 과신하지 않는다.
- 이 커맨드는 **대화형·수동 실행 전용**이다. cron에 걸지 않는다 — 채점 자체가 LLM 비용이고, 무인 채점 실패는 또 하나의 조용한 실패 경로가 된다.
