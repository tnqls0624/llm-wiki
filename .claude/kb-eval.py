#!/usr/bin/env python3
"""kb-eval — LLM 산출물 품질 평가 하네스 (2026-08-25, 같은 날 재설계).

왜 필요: 계약 테스트 277개는 전부 **메커니즘**을 본다 — 훅이 도는지, 가드가 rc=1을 내는지.
그런데 이 자동화의 산출물은 LLM이 쓴 **내용**이다. kb-sync가 노트에 넣은 서술이 출처와 맞는지,
radar 분류가 타당한지는 계약 테스트가 영원히 답하지 못한다.

## 재설계 배경 (초판의 설계 결함, 독립 감사에서 전부 재현됨)

초판은 "LLM이 점수를 매기고 스크립트가 적재한다"였다. 그 구조 자체가 틀렸다:
  · judge가 `score`/`verdict`를 직접 제출하니 **앵커가 없었다** — 노트가 삭제된 케이스에도
    1.0/pass가 그대로 수락됐다. 점수를 만드는 주체와 채점되는 주체가 같으면 평가가 아니다.
  · gold를 케이스 파일에 넣고 `--list`에서만 가렸다. 2지선다를 해시로 숨길 수 없고
    (case id로 2번 추측), 파일 자체가 git 추적이라 정답 요약표를 배포한 셈이었다.
  · routing 골든셋이 9 queue / 1 drop이라, **항상 "queue"만 답하는 채점자가 0.90**을 받았다.
    나쁜 judge를 탐지할 수 없는 평가였다.
  · `--seed`가 매번 재추첨해서 case id가 흔들렸다(집합이 커지면 표본이 바뀐다). 원장에 남은
    과거 점수는 orphan이 되고, `--regress`는 그 orphan 때문에 exit 1에 고정될 수 있었다.

## 재설계 원칙

1. **판단은 LLM, 산술은 코드.** judge는 관찰한 *수*만 보고한다(검사한 주장 수, 근거된 수,
   모순 수 / 또는 queue|drop 결정). score는 스크립트가 계산한다. judge가 score를 제출하면 거부.
2. **정답은 한 곳에만 있다.** routing gold는 케이스 파일에 저장하지 않고, `--record` 시점에
   `radar-queue.md`(사용자 결정의 원천)에서 제목으로 도출한다. 정답 요약표를 만들지 않는다.
3. **다수 클래스 기준선을 게이트에 넣는다.** 불균형 골든셋에서 나온 높은 점수는 통과가 아니다.
   routing 정확도가 majority baseline 이하면 회귀로 본다.
4. **케이스는 append-mostly.** 기존 id는 보존하고, 대상이 사라지면 삭제가 아니라 `retired`.
   재추첨하지 않으므로 추이가 끊기지 않고, 원장의 orphan도 게이트를 막지 않는다.
5. **버전 앵커.** grounding 원장 행에 노트 내용 해시를 남긴다. 노트가 재작성되면 하락을
   회귀가 아니라 `rebaselined`로 처리한다 — 무관한 두 텍스트를 비교하지 않는다.

사용:
  python3 .claude/kb-eval.py --seed                  # 케이스 생성/갱신(기존 id 보존)
  python3 .claude/kb-eval.py --list [--type T]       # 채점 입력 조립(judge가 읽는다)
  python3 .claude/kb-eval.py --record results.json   # 관찰 검증 → 점수 산출 → 원장 적재
  python3 .claude/kb-eval.py --regress               # 하락·기준미달·baseline미달 → exit 1
  python3 .claude/kb-eval.py --summary               # 케이스별 추이
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys
import time

CLAUDE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(CLAUDE)
EVALS_DIR = os.path.join(CLAUDE, "evals")
CASES_PATH = os.path.join(EVALS_DIR, "cases.jsonl")
LEDGER_PATH = os.path.join(CLAUDE, "runtime", "eval-ledger.jsonl")
RECEIPT_PATH = os.path.join(CLAUDE, "runtime", "eval-last-run.json")
QUEUE_PATH = os.path.join(CLAUDE, "runtime", "radar-queue.md")

TOPIC_DIRS = ("20 Architecture", "30 AI Infrastructure", "80 Tooling")
GROUNDING_N = 6           # grounding 표본 상한. 채점 토큰이 선형 증가하므로 추이 감지에 충분한 크기.
ROUTING_N = 12
DROP_TOL = 0.15           # 직전 대비 이만큼 떨어지면 회귀
GROUNDING_FLOOR = 0.8
MIN_CLAIMS = 3            # 이보다 적게 검사한 grounding 결과는 거부(안 보고 통과 방지)
MAX_FINDINGS = 10
MAX_FINDING_LEN = 300
# 제어문자 + zero-width + bidi 제어. 후자는 원장을 읽는 사람에게 보이는 글자를 조작할 수 있다.
BAD_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f​-‏‪-‮⁦-⁩﻿]")


def fail(msg, **extra):
    print(json.dumps({"ok": False, "error": msg, **extra}, ensure_ascii=False), file=sys.stderr)
    return 1


def read(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def sanitize(s):
    return re.sub(r"\s+", " ", BAD_CHARS.sub("", str(s))).strip()[:MAX_FINDING_LEN]


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm, key = {}, None
    for ln in m.group(1).splitlines():
        km = re.match(r"^(\w+):\s*(.*)$", ln)
        if km:
            key = km.group(1)
            fm[key] = km.group(2).strip()
        elif key and re.match(r"^\s*-\s+", ln):
            # 들여쓰기 0의 블록 리스트(`source_urls:` 다음 줄이 `- x`)도 받는다.
            # `^\s+-` 였던 동안 그런 노트는 출처 0개로 읽혀 grounding 표본에서 조용히 빠졌다.
            fm[key] = (fm.get(key, "") + " " + ln.strip().lstrip("- ")).strip()
    return fm


def source_list(fm):
    raw = (fm.get("source_urls", "") or "").strip().strip("[]")
    return [s.strip().strip("'\"") for s in re.split(r"[,\s]+", raw) if s.strip()]


def note_hash(rel):
    """노트 본문의 내용 지문. 원장의 버전 앵커 — 노트가 재작성되면 추이 비교를 끊는다."""
    body = read(os.path.join(REPO, rel))
    if not body:
        return ""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


def stable_id(prefix, key):
    return prefix + "-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]


# ── routing gold: 케이스 파일이 아니라 큐에서 읽는다 ──────────────────────

def queue_labels():
    """radar-queue.md의 사용자 결정 → {제목: queue|drop}.

    `[expired]`는 포함하지 않는다 — 30일 미처리는 '거부'가 아니라 '처리 못 함'이고, 그것을
    drop 정답으로 쓰면 사용자가 내리지 않은 판단을 정답이라 우기게 된다. 대신 골든셋 불균형은
    majority baseline으로 다룬다."""
    out = {}
    for m in re.finditer(r"^###\s*\[(done|dismissed)\]\s*(\S+)\s*·\s*(.+)$", read(QUEUE_PATH), re.M):
        out[sanitize(m.group(3))] = ("queue" if m.group(1) == "done" else "drop", m.group(2))
    return out


def gold_for(case, labels):
    """케이스의 정답을 큐에서 도출. 큐에서 사라졌으면 None(채점 불가)."""
    hit = labels.get(case.get("title", ""))
    return hit[0] if hit else None


# ── 케이스 파일: append-mostly + retire ─────────────────────────────────

def load_cases(strict=True):
    """케이스 로드. 깨진 줄은 raw traceback이 아니라 명시적 실패로 알린다."""
    rows, bad = [], []
    for i, ln in enumerate(read(CASES_PATH).splitlines(), 1):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except ValueError as e:
            bad.append("line %d: %s" % (i, e))
    if bad and strict:
        raise ValueError("cases.jsonl 파싱 실패 — " + "; ".join(bad[:3]))
    return rows


def write_cases(cases):
    os.makedirs(EVALS_DIR, exist_ok=True)
    tmp = CASES_PATH + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    os.replace(tmp, CASES_PATH)


def grounding_candidates():
    out = []
    for d in TOPIC_DIRS:
        for p in sorted(glob.glob(os.path.join(REPO, d, "*.md"))):
            base = os.path.basename(p)
            if base[:-3] == d:          # MOC(파일명==디렉터리명)은 종합 허브 — 출처 정합 대상 아님
                continue
            rel = os.path.relpath(p, REPO)
            if source_list(frontmatter(read(p))):
                out.append(rel)
    return out


def seed_cases():
    """케이스를 갱신한다. **기존 id를 보존하고, 부족분만 추가하고, 사라진 대상은 은퇴시킨다.**

    초판은 매번 전체를 해시 정렬해 상위 N개를 다시 뽑았다 — 집합이 하나만 커져도 표본이
    바뀌어 case id가 흔들리고, 원장의 과거 점수가 orphan이 됐다. 추이를 재는 도구가
    추이를 끊는 구조였다. 지금은 append-mostly다."""
    existing = load_cases()
    by_id = {c["id"]: c for c in existing}

    live_notes = set(grounding_candidates())
    labels = queue_labels()
    live_titles = set(labels)

    # ⓪ 마이그레이션: 초판이 케이스 파일에 저장했던 `gold`를 제거한다. 정답은 이제 큐에서만
    # 읽으므로 여기 남아 있으면 git 추적 파일에 정답 요약표를 계속 배포하는 셈이다.
    migrated = 0
    for c in existing:
        if c.pop("gold", None) is not None:
            migrated += 1
        if c["type"] == "routing":
            c.pop("min_score", None)   # routing은 이진 — 개별 floor가 아니라 baseline으로 판정한다

    # ① 기존 케이스: 대상이 살아있으면 유지, 사라졌으면 retire(삭제하지 않는다 — 이력 보존)
    retired = 0
    for c in existing:
        alive = (c["note"] in live_notes) if c["type"] == "grounding" else (c["title"] in live_titles)
        if alive:
            if c.pop("retired", None):
                c.pop("retired_reason", None)      # 되살아난 경우 은퇴 해제
        elif not c.get("retired"):
            c["retired"] = True
            c["retired_reason"] = "대상이 vault/큐에서 사라짐"
            retired += 1

    # ② 부족분만 신규 추가. 활성 케이스가 상한에 못 미칠 때만.
    def active(t):
        return [c for c in by_id.values() if c["type"] == t and not c.get("retired")]

    added = 0
    have = {c["note"] for c in active("grounding")}
    for rel in sorted(live_notes - have, key=lambda s: hashlib.sha256(s.encode()).hexdigest()):
        if len(active("grounding")) >= GROUNDING_N:
            break
        cid = stable_id("g", rel)
        by_id[cid] = {"id": cid, "type": "grounding", "note": rel,
                      "min_score": GROUNDING_FLOOR,
                      "rubric": ("노트 본문의 사실 주장(명령·플래그·설정키·동작 설명)이 source_urls "
                                 "원문에 실재하는지만 본다. 문체·분량·번역 품질은 대상이 아니다. "
                                 "점수는 제출하지 않는다 — 검사한 주장 수/근거된 수/모순 수만 센다.")}
        existing.append(by_id[cid])
        added += 1

    have_t = {c["title"] for c in active("routing")}
    for title in sorted(live_titles - have_t, key=lambda s: hashlib.sha256(s.encode()).hexdigest()):
        if len(active("routing")) >= ROUTING_N:
            break
        cid = stable_id("r", title)
        by_id[cid] = {"id": cid, "type": "routing", "title": title, "kind": labels[title][1],
                      "rubric": ("이 항목을 이 vault(Claude Code KB + AI-Infra 학습 프레임워크)의 "
                                 "추천 큐에 올릴지(queue) 버릴지(drop)만 판단한다. 점수는 제출하지 "
                                 "않는다 — 결정만 낸다.")}
        existing.append(by_id[cid])
        added += 1
        # 주의: gold는 저장하지 않는다. --record 가 큐에서 도출한다(정답의 단일 출처).

    write_cases(existing)

    # ③ 불균형 경고: 다수 클래스만 답해도 나오는 점수를 미리 알려준다.
    bal = routing_balance(existing, labels)
    out = {"ok": True, "total": len(existing),
           "active": {t: len(active(t)) for t in ("grounding", "routing")},
           "added": added, "retired_now": retired, "gold_stripped": migrated,
           "routing_balance": bal, "path": CASES_PATH}
    if bal and bal["majority_baseline"] is not None and bal["majority_baseline"] > 0.6:
        out["warning"] = ("routing 골든셋이 %s로 치우쳤다 — 다수 클래스만 답해도 %.2f가 나온다. "
                          "게이트는 이 baseline 초과를 요구하지만, 표본을 키우는 것이 근본 해결이다."
                          % (bal["counts"], bal["majority_baseline"]))
    print(json.dumps(out, ensure_ascii=False))
    return 0


def routing_balance(cases, labels):
    """활성 routing 케이스의 정답 분포와 majority baseline."""
    golds = [gold_for(c, labels) for c in cases
             if c["type"] == "routing" and not c.get("retired")]
    golds = [g for g in golds if g]
    if not golds:
        return {"counts": {}, "n": 0, "majority_baseline": None}
    counts = {"queue": golds.count("queue"), "drop": golds.count("drop")}
    return {"counts": counts, "n": len(golds),
            "majority_baseline": round(max(counts.values()) / len(golds), 3)}


# ── 채점 입력 조립 ────────────────────────────────────────────────────

def list_cases(ctype, limit):
    try:
        cases = load_cases()
    except ValueError as e:
        return fail(str(e))
    cases = [c for c in cases if not c.get("retired") and (not ctype or c["type"] == ctype)]
    if limit:
        cases = cases[:limit]
    if not cases:
        return fail("활성 케이스 없음 — 먼저 --seed 를 실행하라")
    out = []
    for c in cases:
        item = dict(c)
        item.pop("min_score", None)   # 합격선을 알면 점수를 합격선에 맞추려는 유인이 생긴다
        if c["type"] == "grounding":
            body = read(os.path.join(REPO, c["note"]))
            if not body:
                continue              # 노트가 사라진 케이스는 채점 대상에서 뺀다(--seed가 은퇴시킨다)
            item["sources"] = source_list(frontmatter(body))
            item["submit"] = ("claims_checked, claims_grounded, contradictions (정수) + findings[]. "
                              "score/verdict 는 제출하지 않는다 — 스크립트가 산술한다.")
        else:
            item["submit"] = ("decision(queue|drop) + findings[]. score/verdict 는 제출하지 않는다 — "
                              "정답은 radar-queue.md의 사용자 결정이고 대조는 스크립트가 한다.")
        out.append(item)
    print(json.dumps({"ok": True, "count": len(out), "cases": out}, ensure_ascii=False, indent=1))
    return 0


# ── 채점 결과 검증 → 점수 산출 → 원장 적재 ──────────────────────────────

def record(path):
    """관찰을 검증하고 **점수는 여기서 계산한다**. 형식 위반이 하나라도 있으면 전체 거부."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        return fail("결과 파일 읽기/파싱 실패: %s" % e)
    try:
        cases = load_cases()
    except ValueError as e:
        return fail(str(e))
    known = {c["id"]: c for c in cases}
    active = {cid for cid, c in known.items() if not c.get("retired")}
    if not active:
        return fail("활성 케이스가 없다 — --seed 먼저")
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return fail("results 배열이 없거나 비어 있다")
    if len(results) > len(active):
        # 상한이 없던 동안 감사가 20000행 63.7MB를 git 추적 원장에 써넣었다.
        return fail("결과 %d개 > 활성 케이스 %d개 — 케이스당 하나만 제출한다"
                    % (len(results), len(active)))

    labels = queue_labels()
    rows, bad, seen = [], [], set()
    for r in results:
        cid = r.get("case")
        if cid not in known:
            bad.append("미등록 case: %s" % cid)
            continue
        if cid in seen:
            # 중복 id는 같은 케이스에 두 점수를 남겨 가짜 회귀를 만든다.
            bad.append("%s: 같은 case가 두 번 제출됐다" % cid)
            continue
        seen.add(cid)
        case = known[cid]
        if case.get("retired"):
            bad.append("%s: 은퇴한 케이스(대상이 사라짐)는 채점하지 않는다" % cid)
            continue
        if "score" in r or "verdict" in r:
            bad.append("%s: score/verdict 를 제출하지 않는다 — 관찰만 낸다(점수는 스크립트가 산술)" % cid)
            continue
        findings = r.get("findings") or []
        if not isinstance(findings, list):
            bad.append("%s: findings 는 배열" % cid)
            continue

        extra = {}
        if case["type"] == "routing":
            decision = r.get("decision")
            if decision not in ("queue", "drop"):
                bad.append("%s: decision 은 queue|drop (받은 값: %s)" % (cid, decision))
                continue
            gold = gold_for(case, labels)
            if gold is None:
                bad.append("%s: 큐에서 정답을 찾을 수 없다(제목이 바뀌었나?) — --seed 로 은퇴 처리" % cid)
                continue
            score = 1.0 if decision == gold else 0.0
            verdict = "pass" if score == 1.0 else "fail"
            extra = {"decision": decision}
        else:
            try:
                checked = int(r.get("claims_checked"))
                grounded = int(r.get("claims_grounded"))
                contra = int(r.get("contradictions", 0))
            except (TypeError, ValueError):
                bad.append("%s: claims_checked/claims_grounded/contradictions 는 정수여야" % cid)
                continue
            if checked < MIN_CLAIMS:
                bad.append("%s: 검사한 주장이 %d개 < 최소 %d — 안 보고 통과할 수 없다"
                           % (cid, checked, MIN_CLAIMS))
                continue
            if not 0 <= grounded <= checked or contra < 0 or contra > checked:
                bad.append("%s: 셈이 모순됐다(checked=%s grounded=%s contradictions=%s)"
                           % (cid, checked, grounded, contra))
                continue
            score = round(grounded / checked, 4)
            # 원문과 반대되는 주장은 비율과 무관하게 실패다.
            verdict = "fail" if (contra > 0 or score < float(case.get("min_score", GROUNDING_FLOOR))) else "pass"
            extra = {"claims_checked": checked, "claims_grounded": grounded,
                     "contradictions": contra, "note_hash": note_hash(case["note"])}

        row = {"epoch": int(time.time()), "date": datetime.date.today().isoformat(),
               "case": cid, "type": case["type"], "score": score, "verdict": verdict,
               "judge": sanitize(data.get("judge", "unknown")),
               "findings": [sanitize(x) for x in findings[:MAX_FINDINGS]]}
        row.update(extra)
        rows.append(row)

    if bad:
        return fail("결과 형식 위반 — 전체 거부", violations=bad[:8])

    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    scored = [r["score"] for r in rows]
    bal = routing_balance(cases, labels)
    with open(RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump({"epoch": int(time.time()), "recorded": len(rows),
                   "mean": round(sum(scored) / len(scored), 4)}, f)
    print(json.dumps({"ok": True, "recorded": len(rows),
                      "mean": round(sum(scored) / len(scored), 4),
                      "failed": [r["case"] for r in rows if r["verdict"] == "fail"],
                      "routing_balance": bal}, ensure_ascii=False))
    return 0


# ── 원장 읽기 · 회귀 게이트 ────────────────────────────────────────────

def ledger_rows():
    rows = []
    for ln in read(LEDGER_PATH).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except ValueError:
            continue          # 손상 줄 하나가 게이트를 죽이면 안 된다
    return rows


def history():
    h = {}
    for r in sorted(ledger_rows(), key=lambda x: x.get("epoch", 0)):
        h.setdefault(r["case"], []).append(r)
    return h


def regress(tol):
    """게이트. 세 가지를 본다 — 기준 미달 / 직전 대비 하락 / **routing이 baseline 이하**.

    baseline 검사가 이 게이트의 핵심이다. 골든셋이 9 queue / 1 drop이면 항상 "queue"만 답하는
    채점자가 0.90을 받는다 — 초판은 그것을 통과로 인정했다. 다수 클래스만 답해서 얻을 수 있는
    점수는 통과가 아니다.

    orphan(원장에는 있으나 케이스 파일에서 사라진 id)은 **무시한다**. 초판에서는 재추첨으로
    생긴 orphan이 게이트를 exit 1에 고정시킬 수 있었다."""
    try:
        cases = {c["id"]: c for c in load_cases()}
    except ValueError as e:
        return fail(str(e))
    h = history()
    if not h:
        print(json.dumps({"ok": True, "note": "원장이 비어 있다 — 판정할 이력 없음",
                          "regressions": [], "below_floor": []}, ensure_ascii=False))
        return 0

    regs, below, rebased, orphans = [], [], [], []
    for cid, runs in h.items():
        case = cases.get(cid)
        if case is None:
            orphans.append(cid)
            continue
        if case.get("retired"):
            continue
        latest = runs[-1]
        # floor·개별 하락 검사는 **grounding 전용**이다. routing은 케이스당 0 또는 1이므로
        # 개별 floor를 적용하면 오답 1건이 곧 게이트 실패가 되고, 0↔1 진동은 매 실행 '회귀'로
        # 잡힌다. routing의 품질 지표는 개별 점수가 아니라 아래 baseline 대비 전체 정확도다.
        if case["type"] != "grounding":
            continue
        floor = float(case.get("min_score", GROUNDING_FLOOR))
        if latest["score"] < floor:
            below.append({"case": cid, "score": latest["score"], "min_score": floor})
        if len(runs) >= 2:
            prev = runs[-2]
            # 버전 앵커: 노트가 재작성됐으면 하락을 회귀라 부르지 않는다(다른 텍스트다).
            if (latest.get("note_hash") and prev.get("note_hash")
                    and latest["note_hash"] != prev["note_hash"]):
                rebased.append({"case": cid, "prev": prev["score"], "now": latest["score"]})
            elif prev["score"] - latest["score"] >= tol:
                regs.append({"case": cid, "prev": prev["score"], "now": latest["score"]})

    # routing baseline 검사
    labels = queue_labels()
    bal = routing_balance(list(cases.values()), labels)
    rt = [runs[-1] for cid, runs in h.items()
          if cases.get(cid, {}).get("type") == "routing" and not cases[cid].get("retired")]
    baseline_fail = None
    if rt and bal.get("majority_baseline") is not None:
        acc = round(sum(r["score"] for r in rt) / len(rt), 3)
        if acc <= bal["majority_baseline"]:
            baseline_fail = {"routing_accuracy": acc, "majority_baseline": bal["majority_baseline"],
                             "why": "다수 클래스만 답해도 이 점수가 나온다 — 채점자가 판단했다는 증거가 없다"}

    ok = not (regs or below or baseline_fail)
    print(json.dumps({"ok": ok, "regressions": regs, "below_floor": below,
                      "rebaselined": rebased, "orphans_ignored": orphans,
                      "baseline_check": baseline_fail or "pass",
                      "routing_balance": bal, "cases_with_history": len(h)},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


def summary():
    try:
        cases = {c["id"]: c for c in load_cases()}
    except ValueError as e:
        return fail(str(e))
    h = history()
    if not h:
        print(json.dumps({"ok": True, "cases": 0, "note": "이력 없음"}, ensure_ascii=False))
        return 0
    rows = []
    for cid, runs in sorted(h.items()):
        c = cases.get(cid, {})
        rows.append({"case": cid, "type": runs[-1]["type"], "runs": len(runs),
                     "latest": runs[-1]["score"], "first": runs[0]["score"],
                     "last_date": runs[-1]["date"],
                     "state": "orphan" if not c else ("retired" if c.get("retired") else "active")})
    live = [r["latest"] for r in rows if r["state"] == "active"]
    print(json.dumps({"ok": True, "cases": len(rows),
                      "mean_latest_active": round(sum(live) / len(live), 4) if live else None,
                      "routing_balance": routing_balance(list(cases.values()), queue_labels()),
                      "rows": rows}, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser(description="kb-eval — LLM 산출물 품질 평가 하네스")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--seed", action="store_true", help="케이스 생성/갱신(기존 id 보존, 사라진 대상은 은퇴)")
    g.add_argument("--list", action="store_true", help="채점 입력 조립(judge가 읽는다)")
    g.add_argument("--record", metavar="FILE", help="관찰 검증 → 점수 산출 → 원장 적재")
    g.add_argument("--regress", action="store_true", help="하락·기준미달·baseline미달 검사(실패 시 exit 1)")
    g.add_argument("--summary", action="store_true", help="케이스별 추이")
    ap.add_argument("--type", choices=("grounding", "routing"), help="--list 필터")
    ap.add_argument("--limit", type=int, default=0, help="--list 개수 제한")
    ap.add_argument("--drop", type=float, default=DROP_TOL, help="회귀로 볼 점수 하락 폭")
    args = ap.parse_args()

    if args.seed:
        return seed_cases()
    if args.list:
        return list_cases(args.type, args.limit)
    if args.record:
        return record(args.record)
    if args.regress:
        return regress(args.drop)
    return summary()


if __name__ == "__main__":
    sys.exit(main())
