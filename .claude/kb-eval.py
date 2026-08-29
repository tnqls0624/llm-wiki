#!/usr/bin/env python3
"""kb-eval — KB 산출물 품질 **관측** 도구 (v4, 2026-08-29).

## 이 도구는 판정하지 않는다

v1·v2·v3는 각각 독립 감사(12 에이전트 × 3회)에서 뚫렸다. 매번 지표를 고쳤고, 매번 다른 입력으로
우회로가 열렸다. 세 번의 공통 구조는 하나다: **게이트의 입력을 채점자가 전부 통제한다.**
원장·케이스 파일·큐·노트·플래그가 모두 같은 에이전트의 쓰기 범위 안에 있다. 그 조건에서
'통과/실패'를 선언하는 exit code는 거짓 안전감만 만든다.

기록으로 남기는 실패 사례(4라운드에서 반복하지 않기 위해):
  · v1 — 채점자가 자기 `score`를 제출: 앵커가 없어 **삭제된 노트에 1.0/pass**가 수락됐다.
  · v2 — majority baseline: 상수 전략이 그 값을 *결정론적으로* 달성해 동률에서만 걸렸고,
    균형 표본이 커지면 오히려 약해졌으며, 단일 클래스에서 1.0이 되어 완벽한 채점자도 영구 실패.
    부분 제출을 허용하면서 정확도는 부분집합, baseline은 전체로 계산해 **유리한 9/10만 답하면 통과**.
    `--record`가 틀린 케이스를 알려줘 2회차 만점이 보장됐다.
  · v3 — balanced accuracy: 상수 전략은 잡았지만 **불균형에서 27% 정확도를 통과시키고 82%를
    실패시켰다**(소수 클래스에 1/2 가중치). 코호트 전량 요구는 `skipped` 표적 사용으로
    체리피킹이 그대로 복원됐고, 축을 아예 제출하지 않으면 통과라 **침묵이 정직보다 유리**했으며,
    한 번 통과한 코호트가 신선도 경계 없이 영구 크레딧을 줬다.

그래서 v4는 **관측 도구**다. 통과/실패를 선언하지 않고, 사람이 읽을 리포트를 만든다.
exit code는 판정이 아니라 도구 상태다: `0` 리포트 생성됨 · `1` 도구가 돌지 못함(입력 손상 등).

여전히 강제하는 것은 **자료 위생**뿐이다 — 원장에 들어가는 관찰이 형식적으로 말이 되는지
(정수인지, 셈이 모순되지 않는지, 대상 노트가 실재하고 출처가 있는지, 경로가 repo 안인지).

강제하지 않는 것: 채점자가 정답을 미리 보는 것, 원장·케이스 파일을 고치는 것, 주장 수를
발명하는 것, 유리한 케이스만 채점하는 것. 리포트는 그런 신호를 **보여줄** 뿐 막지 않는다 —
`coverage`, `constant_strategy_would_score`, `age_days`, `concerns` 가 그 용도다.

사용:
  python3 .claude/kb-eval.py --seed [--rotate N]
  python3 .claude/kb-eval.py --list [--type grounding|routing]
  python3 .claude/kb-eval.py --record results.json
  python3 .claude/kb-eval.py --report [--reveal]
"""
import argparse
import datetime
import glob
import hashlib
import json
import math
import os
import re
import sys
import time
import unicodedata

CLAUDE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(CLAUDE)
REPO_REAL = os.path.realpath(REPO)
EVALS_DIR = os.path.join(CLAUDE, "evals")
CASES_PATH = os.path.join(EVALS_DIR, "cases.jsonl")
LEDGER_PATH = os.path.join(CLAUDE, "runtime", "eval-ledger.jsonl")
RECEIPT_PATH = os.path.join(CLAUDE, "runtime", "eval-last-run.json")
QUEUE_PATH = os.path.join(CLAUDE, "runtime", "radar-queue.md")

TOPIC_DIRS = ("20 Architecture", "30 AI Infrastructure", "80 Tooling")
GROUNDING_N = 6
ROUTING_N = 12
GROUNDING_FLOOR = 0.8         # 리포트가 '기준 미달'로 **표시**하는 선. 차단하지 않는다.
DROP_TOL = 0.15               # 리포트가 '하락'으로 표시하는 폭
MIN_CLAIMS = 3
STALE_DAYS = 30
MAX_FINDINGS = 10
MAX_FINDING_LEN = 300
MAX_RESULT_BYTES = 2 << 20
MAX_LEDGER_ROWS = 20000
CLAIMS_PER_WORD = 0.2

GROUNDING_KEYS = {"case", "claims_checked", "claims_grounded", "contradictions", "findings", "skipped"}
ROUTING_KEYS = {"case", "decision", "findings", "skipped"}
BANNED_KEY_RE = re.compile(r"(score|verdict|pass|fail)", re.I)
BAD_CHARS = re.compile("[\x00-\x08\x0b-\x1f\x7f­؜᠎​-‏"
                       "‪-‮⁠-⁤⁦-⁩ㅤ﻿￹-￻]")


def fail(msg, **extra):
    """도구가 돌지 못했다. 판정 실패가 아니다."""
    print(json.dumps({"ok": False, "tool_error": msg, **extra}, ensure_ascii=False), file=sys.stderr)
    return 1


def read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def sanitize(s):
    if not isinstance(s, str):
        s = json.dumps(s, ensure_ascii=False) if isinstance(s, (dict, list)) else str(s)
    return re.sub(r"\s+", " ", BAD_CHARS.sub("", s)).strip()[:MAX_FINDING_LEN]


def safe_note_path(rel):
    """repo 안으로 봉인된 절대경로. 밖을 가리키면 None.

    `note` 는 케이스 파일에서 오고 그 파일은 편집 가능하다. 봉인이 없던 동안
    `../../etc/passwd` 같은 값이 그대로 읽혀 '노트 존재' 앵커를 만족시켰다(감사 지적)."""
    if not isinstance(rel, str) or not rel:
        return None
    p = os.path.realpath(os.path.join(REPO, rel))
    if p != REPO_REAL and not p.startswith(REPO_REAL + os.sep):
        return None
    return p


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    fm, key = {}, None
    for ln in m.group(1).splitlines():
        km = re.match(r"^(\w+):\s*(.*)$", ln)
        if km:
            key = km.group(1)
            fm[key] = km.group(2).strip()
        elif key and re.match(r"^\s*-\s+", ln):
            fm[key] = (fm.get(key, "") + " " + ln.strip().lstrip("- ")).strip()
    return fm, text[m.end():]


def source_list(fm):
    raw = (fm.get("source_urls", "") or "").strip().strip("[]")
    return [s.strip().strip("'\"") for s in re.split(r"[,\s]+", raw) if s.strip()]


def note_parts(rel):
    """(sources, body) — 경로가 봉인 밖이거나 읽을 수 없으면 (None, None)."""
    p = safe_note_path(rel)
    if not p:
        return None, None
    txt = read(p)
    if not txt.strip():
        return None, None
    fm, body = frontmatter(txt)
    return source_list(fm), body


def note_hash(rel):
    _, body = note_parts(rel)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12] if body else ""


def claims_cap(rel):
    _, body = note_parts(rel)
    return max(MIN_CLAIMS, int(len(body.split()) * CLAIMS_PER_WORD)) if body else 0


def stable_id(prefix, key):
    return prefix + "-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]


def norm_title(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", sanitize(s)).replace(" ", " ")).strip()


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


# ── gold ──────────────────────────────────────────────────────────────

def queue_labels():
    out, dupes = {}, set()
    for m in re.finditer(r"^###[ \t]*\[(done|dismissed)\][ \t]*([^\s·]+)[ \t]*·[ \t]*([^\n]+)$",
                         read(QUEUE_PATH), re.M):
        t = norm_title(m.group(3))
        if not t:
            continue
        status = "queue" if m.group(1) == "done" else "drop"
        if t in out:
            if out[t][0] != status:
                dupes.add(t)
            continue
        out[t] = (status, m.group(2))
    for t in dupes:
        out.pop(t, None)
    return out, sorted(dupes)


def gold_for(case, labels):
    hit = labels.get(norm_title(case.get("title", "")))
    return hit[0] if hit else None


# ── 케이스 파일 ────────────────────────────────────────────────────────

def load_cases():
    rows, bad = [], []
    for i, ln in enumerate(read(CASES_PATH).splitlines(), 1):
        ln = ln.strip()
        if not ln:
            continue
        try:
            row = json.loads(ln)
        except ValueError as e:
            bad.append("line %d: %s" % (i, e))
            continue
        if not isinstance(row, dict) or not row.get("id") or row.get("type") not in ("grounding", "routing"):
            bad.append("line %d: id/type 누락 또는 형식 위반" % i)
            continue
        if row["type"] == "grounding":
            if not row.get("note"):
                bad.append("line %d: grounding 인데 note 없음" % i)
                continue
            if not safe_note_path(row["note"]):
                bad.append("line %d: note 경로가 repo 밖을 가리킨다 — %r" % (i, row["note"]))
                continue
            ms = row.get("min_score", GROUNDING_FLOOR)
            # NaN 은 json.loads 가 받아들이고 모든 비교를 False로 만든다 → floor가 조용히 꺼졌다.
            if not is_num(ms) or not 0 < float(ms) <= 1:
                bad.append("line %d: min_score 가 (0,1] 범위의 유한한 수가 아니다 — %r" % (i, ms))
                continue
        elif not row.get("title"):
            bad.append("line %d: routing 인데 title 없음" % i)
            continue
        rows.append(row)
    if bad:
        raise ValueError("cases.jsonl 검증 실패 — " + "; ".join(bad[:3]))
    seen, dup = set(), []
    for r in rows:
        if r["id"] in seen:
            dup.append(r["id"])
        seen.add(r["id"])
    if dup:
        raise ValueError("cases.jsonl 중복 id — %s" % dup[:3])
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
            if os.path.basename(p)[:-3] == d:
                continue
            rel = os.path.relpath(p, REPO)
            srcs, body = note_parts(rel)
            if srcs and body and max(MIN_CLAIMS, int(len(body.split()) * CLAIMS_PER_WORD)) > MIN_CLAIMS:
                out.append(rel)
    return out


def active_of(cases, t):
    return [c for c in cases if c["type"] == t and not c.get("retired")]


def seed_cases(rotate):
    """케이스 갱신. 기본은 append-mostly(추이 우선), `--rotate N` 이면 오래된 N개를 교체한다.

    상한에 도달하면 새로 쓴 노트가 영영 표본에 들어오지 못했다(감사 지적: '검증이 가장 필요한
    콘텐츠가 영구 제외'). 회전은 추이를 끊으므로 자동으로 하지 않고 **사람이 명시**한다."""
    try:
        existing = load_cases()
    except ValueError as e:
        return fail(str(e))
    live_notes = set(grounding_candidates())
    labels, dupes = queue_labels()
    live_titles = set(labels)

    migrated = 0
    for c in existing:
        if c.pop("gold", None) is not None:
            migrated += 1
        if c["type"] == "routing":
            c.pop("min_score", None)

    retired = 0
    for c in existing:
        alive = (c["note"] in live_notes) if c["type"] == "grounding" \
            else (norm_title(c["title"]) in live_titles)
        if alive:
            if str(c.get("retired_reason", "")).startswith("상한"):
                continue
            c.pop("retired", None)
            c.pop("retired_reason", None)
        elif not c.get("retired"):
            c["retired"] = True
            c["retired_reason"] = ("노트가 없거나 source_urls/본문을 잃음" if c["type"] == "grounding"
                                   else "큐에서 이 제목의 [done]/[dismissed] 결정을 찾을 수 없음")
            retired += 1

    rotated = []
    if rotate:
        last_seen = {}
        for r in ledger_rows():
            last_seen[r["case"]] = max(last_seen.get(r["case"], 0), r.get("epoch", 0))
        for t in ("grounding", "routing"):
            act = sorted(active_of(existing, t), key=lambda c: last_seen.get(c["id"], 0))
            for c in act[:rotate]:
                c["retired"] = True
                c["retired_reason"] = "회전(--rotate)으로 표본에서 내보냄"
                rotated.append(c["id"])

    benched = 0
    for t, cap in (("grounding", GROUNDING_N), ("routing", ROUTING_N)):
        for c in active_of(existing, t)[cap:]:
            c["retired"] = True
            c["retired_reason"] = "상한(%d) 초과로 보류" % cap
            benched += 1

    added = 0
    ids = {c["id"] for c in existing}
    have = {c["note"] for c in active_of(existing, "grounding")}
    for rel in sorted(live_notes - have, key=lambda s: hashlib.sha256(s.encode()).hexdigest()):
        if len(active_of(existing, "grounding")) >= GROUNDING_N:
            break
        cid = stable_id("g", rel)
        if cid in ids:
            continue
        existing.append({"id": cid, "type": "grounding", "note": rel, "min_score": GROUNDING_FLOOR,
                         "rubric": ("본문의 사실 주장이 source_urls 원문에 실재하는지만 본다. "
                                    "점수는 제출하지 않는다 — 검사한 주장 수/근거된 수/모순 수만 센다.")})
        ids.add(cid)
        added += 1

    have_t = {norm_title(c["title"]) for c in active_of(existing, "routing")}
    for title in sorted(live_titles - have_t, key=lambda s: hashlib.sha256(s.encode()).hexdigest()):
        if len(active_of(existing, "routing")) >= ROUTING_N:
            break
        cid = stable_id("r", title)
        if cid in ids:
            continue
        existing.append({"id": cid, "type": "routing", "title": title, "kind": labels[title][1],
                         "rubric": "큐에 올릴지(queue) 버릴지(drop)만 판단한다. 결정만 낸다."})
        ids.add(cid)
        added += 1

    write_cases(existing)
    dist = gold_distribution(existing, labels)
    uncovered_notes = len(live_notes - {c["note"] for c in active_of(existing, "grounding")})
    uncovered_titles = len(live_titles - {norm_title(c["title"]) for c in active_of(existing, "routing")})
    out = {"ok": True, "total": len(existing),
           "active": {t: len(active_of(existing, t)) for t in ("grounding", "routing")},
           "added": added, "retired_now": retired, "benched_over_cap": benched,
           "rotated_out": rotated, "gold_stripped": migrated,
           "gold_distribution": dist, "duplicate_titles_dropped": dupes,
           "not_covered": {"notes": uncovered_notes, "queue_labels": uncovered_titles},
           "path": CASES_PATH}
    notes = []
    if dist["classes"] == 0:
        notes.append("routing 정답이 하나도 없다 — 큐에 [done]/[dismissed] 결정이 없다.")
    elif dist["classes"] < 2:
        notes.append("routing 정답이 한 클래스뿐 — 클래스별 비교가 불가능하다.")
    if uncovered_notes:
        notes.append("표본에 못 들어간 노트 %d개 — 새로 쓴 내용을 넣으려면 `--rotate N`." % uncovered_notes)
    if dupes:
        notes.append("같은 제목에 상반된 결정이 있어 %d건을 정답에서 제외했다." % len(dupes))
    if notes:
        out["notes"] = notes
    print(json.dumps(out, ensure_ascii=False))
    return 0


def gold_distribution(cases, labels):
    golds = [gold_for(c, labels) for c in active_of(cases, "routing")]
    golds = [g for g in golds if g]
    counts = {"queue": golds.count("queue"), "drop": golds.count("drop")}
    return {"counts": counts, "n": len(golds), "classes": sum(1 for v in counts.values() if v)}


# ── 채점 입력 ─────────────────────────────────────────────────────────

def list_cases(ctype, limit):
    try:
        cases = load_cases()
    except ValueError as e:
        return fail(str(e))
    sel = [c for c in cases if not c.get("retired") and (not ctype or c["type"] == ctype)]
    if limit:
        sel = sel[:limit]
    if not sel:
        return fail("활성 케이스 없음 — 먼저 --seed 를 실행하라")
    out = []
    for c in sel:
        item = dict(c)
        item.pop("min_score", None)
        item.pop("gold", None)
        if c["type"] == "grounding":
            srcs, body = note_parts(c["note"])
            if not body:
                item["unavailable"] = "노트를 읽을 수 없다 — skipped 로 제출하라"
            elif not srcs:
                item["unavailable"] = "source_urls 가 없다 — 대조할 원문이 없으므로 skipped 로 제출하라"
            else:
                item["sources"] = srcs
                item["max_claims"] = claims_cap(c["note"])
                item["submit"] = ("claims_checked(<=max_claims) · claims_grounded · contradictions "
                                  "(정수) + findings[] / 채점 불가면 skipped:\"사유\"")
        else:
            item["submit"] = "decision(queue|drop) + findings[] / 채점 불가면 skipped:\"사유\""
        out.append(item)
    print(json.dumps({"ok": True, "count": len(out),
                      "note": "이 도구는 판정하지 않는다 — 리포트를 만든다. 유리한 케이스만 골라 "
                              "채점하면 리포트의 coverage 가 그것을 드러낸다.",
                      "cases": out}, ensure_ascii=False, indent=1))
    return 0


# ── 채점 결과 → 원장 (자료 위생 검증만) ─────────────────────────────────

def record(path):
    try:
        if os.path.getsize(path) > MAX_RESULT_BYTES:
            return fail("결과 파일이 %d바이트를 넘는다" % MAX_RESULT_BYTES)
    except OSError as e:
        return fail("결과 파일 확인 실패: %s" % e)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, RecursionError) as e:
        return fail("결과 파일 읽기/파싱 실패: %s" % e)
    if not isinstance(data, dict):
        return fail("최상위는 results 배열을 담은 객체여야 한다")
    try:
        cases = load_cases()
    except ValueError as e:
        return fail(str(e))
    known = {c["id"]: c for c in cases}
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return fail("results 배열이 없거나 비어 있다")
    if any(not isinstance(r, dict) for r in results):
        return fail("results 의 모든 항목은 객체여야 한다")
    ids = [r.get("case") for r in results]
    if len(ids) != len(set(ids)):
        return fail("같은 case가 두 번 제출됐다")
    unknown = [i for i in ids if i not in known]
    if unknown:
        return fail("미등록 case: %s" % unknown[:3])
    retired = [i for i in ids if known[i].get("retired")]
    if retired:
        return fail("은퇴한 케이스는 채점 대상이 아니다: %s" % retired[:3])

    labels, _ = queue_labels()
    today = datetime.date.today().isoformat()
    run = "%s-%d-%d" % (today, int(time.time() * 1000), os.getpid())
    rows, bad = [], []
    for r in results:
        cid = r["case"]
        case = known[cid]
        allowed = GROUNDING_KEYS if case["type"] == "grounding" else ROUTING_KEYS
        stray = set(r) - allowed
        if stray:
            banned = [k for k in stray if BANNED_KEY_RE.search(k)]
            bad.append("%s: 허용되지 않은 키 %s%s" % (cid, sorted(stray)[:4],
                       " — 점수/판정은 제출하지 않는다" if banned else ""))
            continue
        findings = r.get("findings") or []
        if not isinstance(findings, list):
            bad.append("%s: findings 는 배열" % cid)
            continue
        base = {"epoch": int(time.time()), "date": today, "run": run, "case": cid,
                "type": case["type"], "judge": sanitize(data.get("judge", "unknown")),
                "findings": [sanitize(x) for x in findings[:MAX_FINDINGS]]}

        if "skipped" in r:
            # **문자열만** 받는다 — sanitize 가 `False`/`0` 을 "False"/"0" 이라는 그럴듯한
            # '사유'로 바꿔놓던 경로를 막는다(자체 감사에서 재현).
            if not isinstance(r["skipped"], str) or not sanitize(r["skipped"]):
                bad.append("%s: skipped 는 실질적인 사유 **문자열**이어야 한다(받은 값: %r)"
                           % (cid, r["skipped"]))
                continue
            others = set(r) - {"case", "skipped", "findings"}
            if others:
                bad.append("%s: skipped 와 %s 를 함께 낼 수 없다 — 채점했는지 안 했는지가 모호해진다"
                           % (cid, sorted(others)))
                continue
            rows.append(dict(base, skipped=sanitize(r["skipped"]), score=None, verdict="skipped"))
            continue

        if case["type"] == "routing":
            if r.get("decision") not in ("queue", "drop"):
                bad.append("%s: decision 은 queue|drop (받은 값: %r)" % (cid, r.get("decision")))
                continue
            gold = gold_for(case, labels)
            if gold is None:
                bad.append("%s: 큐에서 정답을 찾을 수 없다 — skipped 로 제출한다" % cid)
                continue
            score = 1.0 if r["decision"] == gold else 0.0
            rows.append(dict(base, score=score, verdict="hit" if score else "miss",
                             decision=r["decision"], gold=gold))
        else:
            srcs, body = note_parts(case["note"])
            if not body:
                bad.append("%s: 노트를 읽을 수 없다 — skipped 로 제출한다" % cid)
                continue
            if not srcs:
                # grounding의 정의가 '출처 원문에 실재하는가'이므로 출처가 없으면 채점이 성립하지
                # 않는다. 이 앵커가 없던 동안 source_urls를 지운 노트가 1.0을 받았다.
                bad.append("%s: source_urls 가 없다 — 대조할 원문이 없으므로 skipped 로 제출한다" % cid)
                continue
            vals, broke = {}, False
            for k in ("claims_checked", "claims_grounded", "contradictions"):
                v = r.get(k)
                if isinstance(v, bool) or not isinstance(v, int):
                    bad.append("%s: %s 는 정수여야 한다(받은 값: %r). contradictions 도 명시한다 — "
                               "생략하면 '찾아보지 않았다'와 '없었다'가 구분되지 않는다" % (cid, k, v))
                    broke = True
                    break
                vals[k] = v
            if broke:
                continue
            cap = claims_cap(case["note"])
            if vals["claims_checked"] < MIN_CLAIMS:
                bad.append("%s: 검사한 주장이 %d개 < 최소 %d" % (cid, vals["claims_checked"], MIN_CLAIMS))
                continue
            if vals["claims_checked"] > cap:
                bad.append("%s: claims_checked %d > 본문 분량이 허용하는 상한 %d"
                           % (cid, vals["claims_checked"], cap))
                continue
            if not 0 <= vals["claims_grounded"] <= vals["claims_checked"] \
                    or not 0 <= vals["contradictions"] <= vals["claims_checked"]:
                bad.append("%s: 셈이 모순됐다 %s" % (cid, vals))
                continue
            nh = note_hash(case["note"])
            if not nh:
                bad.append("%s: 본문 해시를 만들 수 없다" % cid)
                continue
            score = vals["claims_grounded"] / vals["claims_checked"]
            floor = float(case.get("min_score", GROUNDING_FLOOR))
            rows.append(dict(base, score=round(score, 4), note_hash=nh,
                             verdict=("contradiction" if vals["contradictions"] > 0 else
                                      "below_floor" if score < floor else "ok"),
                             **vals))

    if bad:
        return fail("결과 형식 위반 — 전체 거부", violations=bad[:8])

    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump({"epoch": int(time.time()), "run": run, "recorded": len(rows)}, f)
    print(json.dumps({"ok": True, "run": run, "recorded": len(rows),
                      "skipped": sum(1 for r in rows if r["score"] is None),
                      "note": "기록만 했다 — 판정은 없다. `--report` 로 사람이 읽는다."},
                     ensure_ascii=False))
    return 0


# ── 원장 · 리포트 ──────────────────────────────────────────────────────

def ledger_rows():
    rows, corrupt = [], 0
    for ln in read(LEDGER_PATH).splitlines()[-MAX_LEDGER_ROWS:]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            corrupt += 1
            continue
        # 타입까지 본다 — score/epoch/run 이 엉뚱한 타입이면 나중에 raw traceback 이 났다.
        if (isinstance(r, dict) and isinstance(r.get("case"), str) and isinstance(r.get("type"), str)
                and isinstance(r.get("epoch"), int) and isinstance(r.get("run"), str)
                and (r.get("score") is None or is_num(r.get("score")))):
            rows.append(r)
        else:
            corrupt += 1
    ledger_rows.corrupt = corrupt
    return rows


ledger_rows.corrupt = 0


def latest_cohort(rows, t):
    runs = {}
    for r in rows:
        if r.get("type") == t:
            runs.setdefault(r["run"], []).append(r)
    if not runs:
        return None, []
    key = max(runs, key=lambda k: (max(x["epoch"] for x in runs[k]), str(k)))
    return key, runs[key]


def days_since(epoch):
    return round((time.time() - epoch) / 86400.0, 1)


def report(reveal):
    """사람이 읽는 리포트. 판정하지 않는다 — 신호를 나란히 보여준다."""
    try:
        cases = {c["id"]: c for c in load_cases()}
    except ValueError as e:
        return fail(str(e))
    rows = ledger_rows()
    out = {
        "ok": True,
        "generated": datetime.date.today().isoformat(),
        "disclaimer": ("이 도구는 통과/실패를 판정하지 않는다. 채점자가 원장·케이스 파일·큐·노트를 "
                       "모두 쓸 수 있으므로 게이트는 성립하지 않는다(v1~v3가 세 차례 감사에서 각각 "
                       "뚫린 이유). 아래 신호를 사람이 읽고 판단한다."),
        "limits": ["채점자가 radar-queue.md·원장을 읽어 정답을 알 수 있다",
                   "채점자가 원장·케이스 파일·노트를 고칠 수 있다",
                   "grounding 주장 수는 상한 안에서 채점자가 정한다",
                   "유리한 케이스만 채점해도 막지 않는다 — coverage 로 드러낼 뿐이다"],
    }
    if ledger_rows.corrupt:
        out["corrupt_ledger_lines"] = ledger_rows.corrupt
    if not rows:
        out["note"] = "채점 이력이 없다."
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    concerns = []
    active_ids = {t: {c["id"] for c in active_of(list(cases.values()), t)}
                  for t in ("grounding", "routing")}

    for t in ("grounding", "routing"):
        run, rs = latest_cohort(rows, t)
        if not rs:
            concerns.append("%s: 채점 이력이 없다." % t)
            continue
        graded = [r for r in rs if r.get("score") is not None]
        skipped = [r for r in rs if r.get("score") is None]
        age = days_since(max(r["epoch"] for r in rs))
        missing = active_ids[t] - {r["case"] for r in rs}
        blk = {"cohort": run, "age_days": age,
               "coverage": {"graded": len(graded), "skipped": len(skipped), "in_cohort": len(rs),
                            "active_cases": len(active_ids[t]),
                            "active_not_in_cohort": len(missing)},
               "skipped_reasons": [r.get("skipped", "") for r in skipped][:10]}
        if age > STALE_DAYS:
            concerns.append("%s: 마지막 채점이 %.0f일 전이다 — 리포트가 낡았다." % (t, age))
        if missing:
            concerns.append("%s: 활성 케이스 %d개가 이 코호트에 없다 — 표본이 바뀌었거나 일부만 냈다."
                            % (t, len(missing)))
        if skipped:
            concerns.append("%s: %d/%d 를 채점하지 않았다(skipped). 사유를 확인하라."
                            % (t, len(skipped), len(rs)))

        if t == "routing":
            by_gold = {}
            for r in graded:
                if r.get("gold"):
                    by_gold.setdefault(r["gold"], []).append(r["score"])
            blk["accuracy"] = round(sum(r["score"] for r in graded) / len(graded), 4) if graded else None
            blk["class_recalls"] = {k: round(sum(v) / len(v), 3) for k, v in by_gold.items()}
            blk["graded_per_class"] = {k: len(v) for k, v in by_gold.items()}
            if by_gold:
                big = max(len(v) for v in by_gold.values())
                blk["constant_strategy_would_score"] = {
                    "accuracy": round(big / len(graded), 4),
                    "note": "다수 클래스만 답할 때의 정확도. 실제 정확도가 이 값 이하면 판단의 증거가 없다."}
                if blk["accuracy"] is not None and \
                        blk["accuracy"] <= blk["constant_strategy_would_score"]["accuracy"]:
                    concerns.append("routing: 정확도 %.3f 가 상수 전략 값 %.3f 이하다."
                                    % (blk["accuracy"], blk["constant_strategy_would_score"]["accuracy"]))
                if min((len(v) for v in by_gold.values()), default=0) < 2:
                    concerns.append("routing: 클래스별 채점 수가 %s — 표본이 작아 클래스별 수치를 "
                                    "신뢰하기 어렵다." % blk["graded_per_class"])
                if len(by_gold) < 2:
                    concerns.append("routing: 정답이 한 클래스뿐이라 클래스별 비교가 불가능하다.")
            hist = {}
            for r in rows:
                if r["type"] == "routing" and r.get("score") is not None:
                    hist.setdefault(r["run"], []).append(r["score"])
            series = sorted(((k, round(sum(v) / len(v), 4)) for k, v in hist.items()), key=lambda kv: kv[0])
            blk["accuracy_by_cohort"] = series[-5:]
            if len(series) >= 2 and series[-2][1] - series[-1][1] >= DROP_TOL:
                concerns.append("routing: 정확도가 %.3f → %.3f 로 떨어졌다." % (series[-2][1], series[-1][1]))
        else:
            flagged = []
            for r in graded:
                cid = r["case"]
                if r.get("verdict") in ("contradiction", "below_floor"):
                    flagged.append({"case": cid, "verdict": r["verdict"], "score": r["score"],
                                    "contradictions": r.get("contradictions")})
                prev = [x for x in rows if x["case"] == cid and x.get("score") is not None
                        and x["run"] != r["run"]]
                if prev:
                    p = max(prev, key=lambda x: (x["epoch"], x["run"]))
                    if r.get("note_hash") and p.get("note_hash") and r["note_hash"] != p["note_hash"]:
                        blk.setdefault("rebaselined", []).append(cid if reveal else "(hidden)")
                    elif p["score"] - r["score"] >= DROP_TOL:
                        flagged.append({"case": cid, "verdict": "drop",
                                        "detail": "%.3f -> %.3f" % (p["score"], r["score"])})
            blk["mean"] = round(sum(r["score"] for r in graded) / len(graded), 4) if graded else None
            blk["flagged"] = flagged if reveal else [
                {k: v for k, v in f.items() if k != "case"} for f in flagged]
            if flagged:
                concerns.append("grounding: 확인이 필요한 항목 %d건(기준 미달·모순·하락)." % len(flagged))
        out[t] = blk

    labels, _ = queue_labels()
    live_notes = set(grounding_candidates())
    out["not_covered"] = {
        "notes_without_case": len(live_notes - {c.get("note") for c in cases.values()
                                                if c["type"] == "grounding" and not c.get("retired")}),
        "queue_labels_without_case": len(set(labels) - {norm_title(c.get("title", ""))
                                                        for c in cases.values()
                                                        if c["type"] == "routing" and not c.get("retired")}),
    }
    if out["not_covered"]["notes_without_case"]:
        concerns.append("표본에 없는 노트 %d개 — 새로 쓴 내용은 검증되지 않는다(`--seed --rotate N`)."
                        % out["not_covered"]["notes_without_case"])
    if ledger_rows.corrupt:
        concerns.append("원장에 읽을 수 없는 줄 %d개 — 이력이 불완전하다." % ledger_rows.corrupt)
    out["concerns"] = concerns
    if not reveal:
        out["hint"] = "케이스 id는 --reveal 로 본다 — 채점 전에 보면 정답을 배운다."
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser(description="kb-eval — KB 산출물 품질 관측 도구 (v4, 판정하지 않는다)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--seed", action="store_true")
    g.add_argument("--list", action="store_true")
    g.add_argument("--record", metavar="FILE")
    g.add_argument("--report", action="store_true")
    ap.add_argument("--type", choices=("grounding", "routing"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--rotate", type=int, default=0, help="--seed 시 오래된 케이스 N개를 표본에서 교체")
    ap.add_argument("--reveal", action="store_true", help="케이스 id 노출(사람이 볼 때만)")
    args = ap.parse_args()
    if args.rotate < 0:
        return fail("--rotate 는 0 이상이어야 한다")
    try:
        if args.seed:
            return seed_cases(args.rotate)
        if args.list:
            return list_cases(args.type, args.limit)
        if args.record:
            return record(args.record)
        return report(args.reveal)
    except RecursionError:
        return fail("입력이 지나치게 중첩됐다")
    except KeyboardInterrupt:
        return fail("중단됨")
    except Exception as e:                      # 도구가 죽어도 JSON 계약은 지킨다
        return fail("예상치 못한 오류: %s: %s" % (type(e).__name__, e))


if __name__ == "__main__":
    sys.exit(main())
