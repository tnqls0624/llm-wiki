#!/usr/bin/env python3
"""kb-eval — LLM 산출물 품질 평가 하네스 (2026-08-25).

왜 필요(실측): 계약 테스트 231개는 전부 **메커니즘**을 검증한다 — 훅이 도는지, 가드가 rc=1을
내는지, 영수증이 남는지. 그런데 이 자동화의 실제 산출물은 LLM이 쓴 **내용**이다: kb-sync가
노트에 넣은 서술이 출처와 맞는지, radar 분류가 타당한지는 지금 아무도 검사하지 않는다.
2026-08 기준 생태계의 성장축도 여기다(raindrop-ai/workshop, ai-evals-course/evals-skills).

역할 분담(radar와 같은 형태): 이 스크립트는 **결정론적 부분만** — 케이스 시드·입력 조립·결과
검증·원장 적재·회귀 판정. 채점 자체는 LLM(`/kb-eval` 커맨드)이 하고, 결과는 `--record`로만
들어온다. 무인 런에서도 쓸 수 있도록 원장 쓰기는 스크립트 경로 하나로 고정한다.

케이스 타입:
  grounding — 노트의 사실 주장이 `source_urls` 원문에 실재하는가. kb-lint는 슬러그의 *존재*만
              보고 내용 정합은 못 본다. 여기서 잡는 것이 '그럴듯하지만 원문에 없는 서술'이다.
  routing   — radar의 적재/드롭 판단이 타당했는가. 정답 레이블이 이미 큐에 쌓여 있다
              (사용자가 review에서 내린 [done]/[dismissed] 결정) — 사람 판단이 곧 골든셋이다.

샘플링은 **결정론적**이다(노트명 sha256 정렬). 실행마다 케이스가 바뀌면 점수 추이가 무의미해진다.

사용:
  python3 .claude/kb-eval.py --seed                  # 케이스 파일 생성/갱신
  python3 .claude/kb-eval.py --list [--type T]       # 채점 입력 조립(LLM이 읽는다)
  python3 .claude/kb-eval.py --record results.json   # 채점 결과 검증 후 원장 적재
  python3 .claude/kb-eval.py --regress               # 직전 대비 하락·기준미달 → exit 1
  python3 .claude/kb-eval.py --summary               # 케이스별 최근 점수
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
GROUNDING_N = 6          # 노트 표본 크기. 늘리면 채점 토큰이 선형 증가 — 추이 감지엔 6개로 충분.
ROUTING_N = 10
DROP_TOL = 0.15          # 직전 대비 이만큼 떨어지면 회귀로 본다
MAX_FINDINGS = 10
MAX_FINDING_LEN = 300


def fail(msg, **extra):
    print(json.dumps({"ok": False, "error": msg, **extra}, ensure_ascii=False), file=sys.stderr)
    return 1


def read(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


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
        elif key and re.match(r"^\s+-\s+", ln):   # block-style YAML list
            fm[key] = (fm.get(key, "") + " " + ln.strip().lstrip("- ")).strip()
    return fm


def source_list(fm):
    raw = fm.get("source_urls", "")
    raw = raw.strip().strip("[]")
    return [s.strip().strip("'\"") for s in re.split(r"[,\s]+", raw) if s.strip()]


def stable_pick(items, n):
    """노트명 해시로 정렬해 상위 n개 — 실행마다 같은 표본이 나와야 점수 추이가 의미를 가진다."""
    return sorted(items, key=lambda s: hashlib.sha256(s.encode()).hexdigest())[:n]


def seed_cases():
    """vault 현재 상태에서 케이스를 (재)생성한다. 기존 케이스 id는 보존 — 추이가 끊기지 않게."""
    os.makedirs(EVALS_DIR, exist_ok=True)
    cases = []

    # grounding: source_urls가 실제로 있는 노트만 대상(MOC·빈 출처는 채점 불가)
    notes = []
    for d in TOPIC_DIRS:
        for p in sorted(glob.glob(os.path.join(REPO, d, "*.md"))):
            base = os.path.basename(p)
            if base[:-3] == d:            # MOC(파일명==디렉터리명)은 종합 허브 — 출처 정합 대상 아님
                continue
            fm = frontmatter(read(p))
            srcs = source_list(fm)
            if srcs:
                notes.append(os.path.relpath(p, REPO))
    for rel in stable_pick(notes, GROUNDING_N):
        cases.append({
            "id": "g-" + hashlib.sha256(rel.encode()).hexdigest()[:8],
            "type": "grounding",
            "note": rel,
            "min_score": 0.8,
            "rubric": ("노트 본문의 사실 주장(명령·플래그·설정키·동작 설명)이 source_urls 원문에 "
                       "실재하는지만 본다. 문체·분량·번역 품질은 채점 대상이 아니다. "
                       "원문에 없는 주장 1건 = 감점, 원문과 반대되는 주장 = 즉시 fail."),
        })

    # routing: 사용자가 review에서 내린 [done]/[dismissed] 결정이 정답 레이블
    q = read(QUEUE_PATH)
    labeled = []
    for m in re.finditer(r"^### \[(done|dismissed)\] (\S+) · (.+)$", q, re.M):
        labeled.append({"status": m.group(1), "kind": m.group(2), "title": m.group(3).strip()})
    for item in stable_pick([json.dumps(x, ensure_ascii=False, sort_keys=True) for x in labeled], ROUTING_N):
        it = json.loads(item)
        cases.append({
            "id": "r-" + hashlib.sha256(item.encode()).hexdigest()[:8],
            "type": "routing",
            "title": it["title"],
            "kind": it["kind"],
            "gold": "queue" if it["status"] == "done" else "drop",
            "min_score": 1.0,      # 이진 판단이라 부분점수가 없다
            "rubric": ("이 항목을 이 vault(Claude Code KB + AI-Infra 학습 프레임워크)의 추천 큐에 "
                       "올릴지(queue) 버릴지(drop)만 판단한다. 정답(gold)은 사용자가 실제로 내린 "
                       "결정이다. 맞으면 1.0, 틀리면 0.0."),
        })

    with open(CASES_PATH, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    kinds = {}
    for c in cases:
        kinds[c["type"]] = kinds.get(c["type"], 0) + 1
    print(json.dumps({"ok": True, "cases": len(cases), "by_type": kinds, "path": CASES_PATH},
                     ensure_ascii=False))
    return 0


def load_cases():
    out = []
    for ln in read(CASES_PATH).splitlines():
        ln = ln.strip()
        if ln:
            out.append(json.loads(ln))
    return out


def list_cases(ctype, limit):
    cases = [c for c in load_cases() if not ctype or c["type"] == ctype]
    if limit:
        cases = cases[:limit]
    if not cases:
        return fail("케이스 없음 — 먼저 --seed 를 실행하라")
    out = []
    for c in cases:
        item = dict(c)
        # 정답 누출 차단: routing의 gold(사용자가 내린 실제 결정)를 채점자에게 보여주면 평가가
        # 자기충족이 된다. 채점자는 decision만 제출하고, 채점은 --record가 gold와 대조해 한다.
        item.pop("gold", None)
        item.pop("min_score", None)   # 합격선도 숨긴다 — 점수를 합격선에 맞추는 유인을 없앤다
        if c["type"] == "grounding":
            body = read(os.path.join(REPO, c["note"]))
            fm = frontmatter(body)
            item["sources"] = source_list(fm)
            item["note_exists"] = bool(body)
            # 본문은 넘기지 않는다 — 채점자가 Read로 직접 읽어야 '원문 대조'가 실제로 일어난다.
            item["submit"] = "score(0~1) + verdict(pass|fail) + findings[]"
        else:
            item["submit"] = "decision(queue|drop) + findings[] — score는 스크립트가 gold와 대조해 매긴다"
        out.append(item)
    print(json.dumps({"ok": True, "count": len(out), "cases": out}, ensure_ascii=False, indent=1))
    return 0


def sanitize(s):
    s = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", str(s))
    return re.sub(r"\s+", " ", s).strip()[:MAX_FINDING_LEN]


def record(path):
    """LLM 채점 결과를 검증 후 원장에 append. 부분 적재 금지 — 하나라도 형식 위반이면 전체 거부."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        return fail("결과 파일 읽기/파싱 실패: %s" % e)
    known = {c["id"]: c for c in load_cases()}
    if not known:
        return fail("케이스 파일이 비어 있다 — --seed 먼저")
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return fail("results 배열이 없거나 비어 있다")
    rows, bad = [], []
    for r in results:
        cid = r.get("case")
        if cid not in known:
            bad.append("미등록 case: %s" % cid)
            continue
        case = known[cid]
        if case["type"] == "routing":
            # 채점 주체가 스크립트다 — 채점자는 결정만 낸다. 자기 점수를 매기게 하면
            # gold를 숨긴 의미가 사라진다(제출된 score는 무시하지 않고 아예 거부).
            decision = r.get("decision")
            if decision not in ("queue", "drop"):
                bad.append("%s: decision은 queue|drop (%s)" % (cid, decision))
                continue
            if "score" in r:
                bad.append("%s: routing 케이스는 score를 제출하지 않는다(gold 대조로 산출)" % cid)
                continue
            score = 1.0 if decision == case.get("gold") else 0.0
            verdict = "pass" if score == 1.0 else "fail"
        else:
            try:
                score = float(r.get("score"))
            except (TypeError, ValueError):
                bad.append("%s: score가 숫자가 아니다" % cid)
                continue
            if not 0.0 <= score <= 1.0:
                bad.append("%s: score 범위 위반(%s)" % (cid, score))
                continue
            verdict = r.get("verdict")
            if verdict not in ("pass", "fail"):
                bad.append("%s: verdict는 pass|fail (%s)" % (cid, verdict))
                continue
        findings = r.get("findings") or []
        if not isinstance(findings, list):
            bad.append("%s: findings는 배열" % cid)
            continue
        rows.append({
            "epoch": int(time.time()),
            "date": datetime.date.today().isoformat(),
            "case": cid,
            "type": known[cid]["type"],
            "score": round(score, 4),
            "verdict": verdict,
            "judge": sanitize(data.get("judge", "unknown")),
            "findings": [sanitize(x) for x in findings[:MAX_FINDINGS]],
        })
    if bad:
        return fail("결과 형식 위반 — 전체 거부", violations=bad[:8])
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    scored = [r["score"] for r in rows]
    with open(RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump({"epoch": int(time.time()), "recorded": len(rows),
                   "mean": round(sum(scored) / len(scored), 4)}, f)
    print(json.dumps({"ok": True, "recorded": len(rows),
                      "mean": round(sum(scored) / len(scored), 4),
                      "failed": [r["case"] for r in rows if r["verdict"] == "fail"]},
                     ensure_ascii=False))
    return 0


def ledger_rows():
    rows = []
    for ln in read(LEDGER_PATH).splitlines():
        ln = ln.strip()
        if ln:
            try:
                rows.append(json.loads(ln))
            except ValueError:
                continue
    return rows


def history():
    """case → 시간순 점수 목록."""
    h = {}
    for r in sorted(ledger_rows(), key=lambda x: x.get("epoch", 0)):
        h.setdefault(r["case"], []).append(r)
    return h


def regress(tol):
    """회귀 게이트: 기준 미달 또는 직전 대비 tol 이상 하락 → exit 1.

    신규 케이스는 baseline만 세우고 회귀로 보지 않는다(첫 실행이 항상 실패하면 게이트가 죽는다)."""
    cases = {c["id"]: c for c in load_cases()}
    h = history()
    if not h:
        print(json.dumps({"ok": True, "note": "원장이 비어 있다 — 회귀 판정할 이력 없음",
                          "regressions": []}, ensure_ascii=False))
        return 0
    regs, below = [], []
    for cid, runs in h.items():
        latest = runs[-1]
        floor = float(cases.get(cid, {}).get("min_score", 0.8))
        if latest["score"] < floor:
            below.append({"case": cid, "score": latest["score"], "min_score": floor})
        if len(runs) >= 2 and runs[-2]["score"] - latest["score"] >= tol:
            regs.append({"case": cid, "prev": runs[-2]["score"], "now": latest["score"]})
    out = {"ok": not (regs or below), "regressions": regs, "below_floor": below,
           "cases_with_history": len(h)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["ok"] else 1


def summary():
    h = history()
    if not h:
        print(json.dumps({"ok": True, "cases": 0, "note": "이력 없음"}, ensure_ascii=False))
        return 0
    rows = []
    for cid, runs in sorted(h.items()):
        rows.append({"case": cid, "type": runs[-1]["type"], "runs": len(runs),
                     "latest": runs[-1]["score"], "first": runs[0]["score"],
                     "last_date": runs[-1]["date"]})
    means = [r["latest"] for r in rows]
    print(json.dumps({"ok": True, "cases": len(rows),
                      "mean_latest": round(sum(means) / len(means), 4), "rows": rows},
                     ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser(description="kb-eval — LLM 산출물 품질 평가 하네스")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--seed", action="store_true", help="vault 현재 상태에서 케이스 파일 생성/갱신")
    g.add_argument("--list", action="store_true", help="채점 입력 조립(LLM이 읽는다)")
    g.add_argument("--record", metavar="FILE", help="LLM 채점 결과 검증 후 원장 적재")
    g.add_argument("--regress", action="store_true", help="하락·기준미달 검사(회귀 게이트, 실패 시 exit 1)")
    g.add_argument("--summary", action="store_true", help="케이스별 최근 점수")
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
