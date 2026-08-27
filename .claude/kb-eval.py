#!/usr/bin/env python3
"""kb-eval — LLM 산출물 품질 평가 하네스 (v3, 2026-08-26).

계약 테스트는 **메커니즘**만 본다. 이 하네스는 "LLM이 쓴 내용이 맞는가"를 보는 유일한 축이다.

## 이 도구가 강제하는 것 / 강제하지 못하는 것 (먼저 읽는다)

두 차례 독립 감사(각 12 에이전트)에서 v1·v2가 각각 뚫렸다. 배운 것은 버그 목록이 아니라
**경계**다: 채점자가 같은 파일시스템에서 같은 권한으로 도는 한, 정답 은닉도 원장 무결성도
성립하지 않는다. v2는 그 사실을 인정하지 않고 '게이트'를 자칭했다.

**강제한다(기계적):**
  · 코호트 — 한 번의 `--record` 는 해당 타입의 **활성 케이스 전량**이다. 부분 제출은 거부.
    v2는 부분 제출을 허용하면서 정확도는 제출 부분집합으로, baseline은 전체로 계산해서
    유리한 9건만 골라 답하면 통과했다.
  · 재굴림 — 같은 날 같은 타입의 두 번째 코호트는 `--force` 없이 거부. v2는 무제한 재제출을
    허용했고 `--record` 가 틀린 케이스 id를 알려줬으므로 2회차 만점이 보장됐다.
  · 정답 미노출 — `--record` 는 실패 **개수**만 낸다. 케이스별 결과는 `--reveal` 을 준 사람만 본다.
  · 지표 — routing은 **balanced accuracy**(클래스별 recall 평균)로 판정한다. 상수 전략은 표본
    크기·불균형과 무관하게 정확히 0.5가 되므로 0.5 초과 요구로 잡힌다. v2의 majority baseline은
    상수 전략이 *결정론적으로* 달성하는 값이라 동률에서만 걸렸고, 균형 표본이 커지면 오히려
    약해졌으며, 단일 클래스에서는 1.0이 되어 **완벽한 채점자도 영구 실패**했다.
  · grounding 앵커 — 노트 존재 필수, 본문 해시 필수, `claims_checked` 상한을 **본문 분량에서**
    계산한다. v2는 13자 노트에 100/100을 1.0으로 수락했다.
  · 판정 불가의 분리 — **종료 코드 3원화**(0 통과 / 1 실패 / **2 판정 불가**). v2는 이것들을
    조용한 통과(fail-open) 또는 영구 실패로 처리했고, v3 초판은 `undecidable`을 rc=0으로 내서
    **전량 skipped 제출이 '통과'가 됐다**(자체 감사 2026-08-27 재현 — 정답 지식이 전혀 필요 없는,
    체리피킹보다 나쁜 경로). 판정 못 한 것은 통과가 아니다.
  · 커버리지 — 코호트에서 실제 채점된 비율이 MIN_COVERAGE 미만이면 판정 불가. 코호트 완결성은
    개수가 아니라 채점된 비율로 본다.
  · 소수 클래스 표본 — BA가 기준을 넘어도 클래스별 채점 수가 MIN_CLASS_CASES 미만이면 통과를
    주장하지 않는다. 9q/1d에서 drop 하나만 맞히면 나머지 9개가 상수여도 BA=1.0이 된다(자체 감사
    재현). 상수 전략은 BA<=0.5로 이미 잡히므로 여기서 보류해도 게이트가 약해지지 않는다.
  · 시도한 축이 미판정이면 통과 없음 — grounding 통과를 이유로 rc=0을 내면 routing에 대해
    아무것도 말할 수 없는 상태가 '다 괜찮다'로 읽힌다.
  · 게이트가 `verdict` 를 읽는다 — v2는 모순이 기록된 fail을 rc=0으로 통과시켜 규칙이 장식이었다.

**강제하지 못한다(설계상 — 출력의 `enforcement_limits` 에도 함께 낸다):**
  · 채점자가 `runtime/radar-queue.md` 를 읽어 정답을 아는 것. 제목이 곧 조인 키다.
  · 채점자가 원장·케이스 파일을 직접 고치는 것.
  · grounding에서 채점자가 주장 수를 발명하는 것. 상한·최소치는 규모만 제한한다.
  → 이 도구는 **성실한 채점자의 품질 회귀를 잡는 장치**이고, 부정직한 채점자를 막는 장치가
    아니다. 후자가 필요하면 채점을 다른 권한 경계(격리 실행·별도 자격증명)로 옮겨야 한다.

사용:
  python3 .claude/kb-eval.py --seed
  python3 .claude/kb-eval.py --list [--type grounding|routing]
  python3 .claude/kb-eval.py --record results.json [--force]
  python3 .claude/kb-eval.py --regress [--reveal]
  python3 .claude/kb-eval.py --summary [--reveal]
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
import unicodedata

CLAUDE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(CLAUDE)
EVALS_DIR = os.path.join(CLAUDE, "evals")
CASES_PATH = os.path.join(EVALS_DIR, "cases.jsonl")
LEDGER_PATH = os.path.join(CLAUDE, "runtime", "eval-ledger.jsonl")
RECEIPT_PATH = os.path.join(CLAUDE, "runtime", "eval-last-run.json")
QUEUE_PATH = os.path.join(CLAUDE, "runtime", "radar-queue.md")

TOPIC_DIRS = ("20 Architecture", "30 AI Infrastructure", "80 Tooling")
GROUNDING_N = 6
ROUTING_N = 12
DROP_TOL = 0.15
GROUNDING_FLOOR = 0.8
MIN_CLAIMS = 3
BALANCED_FLOOR = 0.5          # 상수 전략의 balanced accuracy 값. 초과를 요구한다.
MIN_COVERAGE = 0.5            # 코호트에서 실제 채점된 비율의 하한. 미달이면 판정 불가.
MIN_CLASS_CASES = 2           # 통과를 주장하려면 각 클래스에 최소 이만큼 채점돼야 한다.
MAX_FINDINGS = 10
MAX_FINDING_LEN = 300
MAX_RESULT_BYTES = 2 << 20    # 결과 파일 상한 2MiB. v2는 524MB를 받아 1.27GB RSS를 썼다.
CLAIMS_PER_WORD = 0.2         # 본문 5단어당 주장 1개까지 — 발명된 큰 수를 막는 상한

GROUNDING_KEYS = {"case", "claims_checked", "claims_grounded", "contradictions", "findings", "skipped"}
ROUTING_KEYS = {"case", "decision", "findings", "skipped"}
# 점수/판정 계열을 넓게 막는다. v2는 정확히 두 키만 봐서 "Score"·"my_score"가 통과했다.
BANNED_KEY_RE = re.compile(r"(score|verdict|pass|fail)", re.I)
# 제어문자 + soft hyphen + zero-width/bidi/불가시. v2는 U+061C·U+2060·U+00AD·U+180E·U+3164·
# U+FFF9 를 통과시켜 자기 계약을 어겼다.
BAD_CHARS = re.compile("[\x00-\x08\x0b-\x1f\x7f­؜᠎​-‏"
                       "‪-‮⁠-⁤⁦-⁩ㅤ﻿￹-￻]")


def fail(msg, **extra):
    print(json.dumps({"ok": False, "error": msg, **extra}, ensure_ascii=False), file=sys.stderr)
    return 1


def read(p):
    """어떤 파일 손상도 traceback으로 새지 않게 한다(비UTF-8 바이트 포함)."""
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def sanitize(s):
    if not isinstance(s, str):
        s = json.dumps(s, ensure_ascii=False) if isinstance(s, (dict, list)) else str(s)
    return re.sub(r"\s+", " ", BAD_CHARS.sub("", s)).strip()[:MAX_FINDING_LEN]


def frontmatter(text):
    """(필드 dict, frontmatter 제외 본문)."""
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


def note_body(rel):
    """frontmatter를 **제외한** 본문. 해시 앵커의 대상.

    v2는 파일 전체를 해시해서, vault-rules가 모든 개정에 요구하는 `updated:` 범프만으로
    실제 회귀가 `rebaselined` 로 세탁됐다."""
    txt = read(os.path.join(REPO, rel))
    if not txt:
        return None
    _, body = frontmatter(txt)
    return body


def note_hash(rel):
    body = note_body(rel)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12] if body is not None else ""


def claims_cap(rel):
    body = note_body(rel)
    if body is None:
        return 0
    return max(MIN_CLAIMS, int(len(body.split()) * CLAIMS_PER_WORD))


def stable_id(prefix, key):
    return prefix + "-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]


def norm_title(s):
    """제목 매칭 키. macOS의 NFC/NFD 재기록과 NBSP로 매칭이 깨지던 것을 정규화로 흡수한다."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", sanitize(s)).replace(" ", " ")).strip()


# ── gold: 케이스 파일이 아니라 큐에서 읽는다 ─────────────────────────────

def queue_labels():
    """({정규화 제목: (queue|drop, kind)}, 충돌 제목 목록).

    상반된 결정이 붙은 같은 제목은 **버린다** — v2는 평범한 dict에 넣어 마지막 항목이 조용히
    이겼고, 정답이 임의가 되면 그 점수는 의미가 없다. 들여쓰기된 헤딩(큐 파일 자신의 템플릿
    주석 포함)은 `^###` 앵커로 제외되고, 제목에 개행이 섞이지 않게 `[^\\n]+` 로 받는다."""
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
    """스키마까지 검증한다 — v2는 필드 누락 행에서 raw KeyError 를 냈다."""
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
        if row["type"] == "grounding" and not row.get("note"):
            bad.append("line %d: grounding 인데 note 없음" % i)
            continue
        if row["type"] == "routing" and not row.get("title"):
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
        raise ValueError("cases.jsonl 중복 id — %s (한 케이스가 두 점수를 갖게 된다)" % dup[:3])
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
            if os.path.basename(p)[:-3] == d:      # MOC 제외
                continue
            rel = os.path.relpath(p, REPO)
            fm, _ = frontmatter(read(p))
            # 출처가 있고, **본문이 최소 주장 수를 담을 만큼 긴** 노트만 후보다.
            # 상한이 MIN_CLAIMS와 같아지면(아주 짧은 노트) 제출 가능한 값이 하나뿐이라 채점이
            # 형식적 통과로 굳는다 — 그런 케이스는 만들지 않는 것이 정직하다.
            if source_list(fm) and claims_cap(rel) > MIN_CLAIMS:
                out.append(rel)
    return out


def active_of(cases, t):
    return [c for c in cases if c["type"] == t and not c.get("retired")]


def seed_cases():
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
            c.pop("retired", None)
            c.pop("retired_reason", None)
        elif not c.get("retired"):
            c["retired"] = True
            c["retired_reason"] = ("노트가 없거나 source_urls를 잃음" if c["type"] == "grounding"
                                   else "큐에서 이 제목의 [done]/[dismissed] 결정을 찾을 수 없음")
            retired += 1

    # 캡은 **부활에도** 적용한다. v2는 add 경로만 검사해서 은퇴 케이스가 되살아나면 활성 케이스가
    # 상한을 영구히 넘었다(감사가 재현).
    for t, cap in (("grounding", GROUNDING_N), ("routing", ROUTING_N)):
        act = active_of(existing, t)
        for c in act[cap:]:
            c["retired"] = True
            c["retired_reason"] = "상한(%d) 초과로 보류 — 다른 케이스가 은퇴하면 다시 활성화된다" % cap

    added = 0
    ids = {c["id"] for c in existing}
    have = {c["note"] for c in active_of(existing, "grounding")}
    for rel in sorted(live_notes - have, key=lambda s: hashlib.sha256(s.encode()).hexdigest()):
        if len(active_of(existing, "grounding")) >= GROUNDING_N:
            break
        cid = stable_id("g", rel)
        if cid in ids:
            continue
        existing.append({"id": cid, "type": "grounding", "note": rel,
                         "min_score": GROUNDING_FLOOR,
                         "rubric": ("본문의 사실 주장(명령·플래그·설정키·동작 설명)이 source_urls "
                                    "원문에 실재하는지만 본다. 점수는 제출하지 않는다 — 검사한 "
                                    "주장 수/근거된 수/모순 수만 센다.")})
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
                         "rubric": ("이 항목을 이 vault의 추천 큐에 올릴지(queue) 버릴지(drop)만 "
                                    "판단한다. 점수는 제출하지 않는다 — 결정만 낸다.")})
        ids.add(cid)
        added += 1

    write_cases(existing)
    dist = gold_distribution(existing, labels)
    out = {"ok": True, "total": len(existing),
           "active": {t: len(active_of(existing, t)) for t in ("grounding", "routing")},
           "added": added, "retired_now": retired, "gold_stripped": migrated,
           "gold_distribution": dist, "duplicate_titles_dropped": dupes, "path": CASES_PATH}
    warn = []
    if dist["classes"] < 2:
        warn.append("routing 골든셋이 한 클래스뿐 — balanced accuracy를 계산할 수 없어 게이트가 "
                    "`undecidable`을 낸다(실패가 아니다). `/claude-radar review`에서 [dismissed] "
                    "결정이 쌓여야 이 축이 산다.")
    if dist["n"] and dist["n"] < 6:
        warn.append("routing 표본 %d개는 통계적으로 약하다 — 추이로만 읽는다." % dist["n"])
    if dupes:
        warn.append("같은 제목에 상반된 결정이 있어 %d건을 정답에서 제외했다." % len(dupes))
    if warn:
        out["warning"] = " / ".join(warn)
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
        item.pop("gold", None)           # 손으로 편집된 파일에도 방어한다
        if c["type"] == "grounding":
            body = note_body(c["note"])
            if body is None:
                item["unavailable"] = "노트를 읽을 수 없다 — skipped 로 제출하라"
            else:
                fm, _ = frontmatter(read(os.path.join(REPO, c["note"])))
                item["sources"] = source_list(fm)
                item["max_claims"] = claims_cap(c["note"])
                item["submit"] = ("claims_checked(<=max_claims) · claims_grounded · contradictions "
                                  "(정수) + findings[] / 채점 불가면 skipped:\"이유\"")
        else:
            item["submit"] = "decision(queue|drop) + findings[] / 채점 불가면 skipped:\"이유\""
        out.append(item)
    print(json.dumps({"ok": True, "count": len(out),
                      "cohort_rule": "이 타입의 활성 케이스 전량을 한 번에 제출한다 — 부분 제출은 거부된다",
                      "cases": out}, ensure_ascii=False, indent=1))
    return 0


# ── 채점 결과 → 점수 산출 → 원장 ────────────────────────────────────────

def record(path, force):
    try:
        if os.path.getsize(path) > MAX_RESULT_BYTES:
            return fail("결과 파일이 %d바이트를 넘는다 — 채점 결과가 그렇게 클 이유가 없다"
                        % MAX_RESULT_BYTES)
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

    # ── 코호트 검사: 제출된 타입의 활성 케이스 전량이 있어야 한다 ──
    types = {known[i]["type"] for i in ids}
    for t in sorted(types):
        need = {c["id"] for c in active_of(cases, t)}
        got = {i for i in ids if known[i]["type"] == t}
        if got - need:
            return fail("%s: 은퇴한 케이스가 포함됐다 — %s" % (t, sorted(got - need)[:3]))
        if need - got:
            return fail("%s 코호트 불완전: 활성 %d개 중 %d개만 제출됐다. 유리한 케이스만 골라 "
                        "제출하는 경로를 막기 위해 전량을 요구한다." % (t, len(need), len(got)),
                        missing_count=len(need - got))

    prev = ledger_rows()
    today = datetime.date.today().isoformat()
    for t in sorted(types):
        if not force and any(r.get("date") == today and r.get("type") == t for r in prev):
            return fail("%s 는 오늘 이미 채점됐다. 실패한 케이스를 알고 재제출하면 평가가 아니다 — "
                        "정말 다시 돌리려면 --force 를 준다." % t)

    labels, _ = queue_labels()
    # run id는 코호트의 정체성이다. 초 단위였을 때 같은 초의 두 채점이 **한 코호트로 병합**돼,
    # 판정 단위가 섞이고 이전 코호트와의 비교가 사라졌다(회귀 감지가 조용히 꺼짐).
    # 밀리초 + pid로 충돌을 없앤다.
    run = "%s-%d-%d" % (today, int(time.time() * 1000), os.getpid())
    rows, bad = [], []
    for r in results:
        cid = r["case"]
        case = known[cid]
        allowed = GROUNDING_KEYS if case["type"] == "grounding" else ROUTING_KEYS
        stray = set(r) - allowed
        if stray:
            # 조용히 무시하면 채점자는 자기가 말한 것이 읽혔다고 믿는다.
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
        if r.get("skipped"):
            rows.append(dict(base, skipped=sanitize(r["skipped"]), score=None, verdict="undecidable"))
            continue

        if case["type"] == "routing":
            if r.get("decision") not in ("queue", "drop"):
                bad.append("%s: decision 은 queue|drop (받은 값: %r)" % (cid, r.get("decision")))
                continue
            gold = gold_for(case, labels)
            if gold is None:
                bad.append("%s: 큐에서 정답을 찾을 수 없다 — skipped 로 제출하거나 --seed 로 은퇴시킨다" % cid)
                continue
            score = 1.0 if r["decision"] == gold else 0.0
            # gold를 원장에 남긴다 — v2는 남기지 않아 0.0의 귀속이 불가능했다. 정답 은닉은
            # 어차피 성립하지 않으므로(위 enforcement_limits), 사후 분석 가능성을 택한다.
            rows.append(dict(base, score=score, verdict="pass" if score else "fail",
                             decision=r["decision"], gold=gold))
        else:
            if note_body(case["note"]) is None:
                bad.append("%s: 노트를 읽을 수 없다 — skipped 로 제출한다(삭제된 노트에 점수를 줄 수 없다)" % cid)
                continue
            vals, broke = {}, False
            for k, dflt in (("claims_checked", None), ("claims_grounded", None), ("contradictions", 0)):
                v = r.get(k, dflt)
                if isinstance(v, bool) or not isinstance(v, int):
                    bad.append("%s: %s 는 정수여야 한다(받은 값: %r) — 실수·문자열·불린 금지" % (cid, k, v))
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
                bad.append("%s: claims_checked %d > 본문 분량이 허용하는 상한 %d — 이 노트에서 그만큼의 "
                           "사실 주장을 검사할 수 없다" % (cid, vals["claims_checked"], cap))
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
            verdict = "fail" if (vals["contradictions"] > 0 or score < floor) else "pass"
            rows.append(dict(base, score=round(score, 4), verdict=verdict, note_hash=nh, **vals))

    if bad:
        return fail("결과 형식 위반 — 전체 거부", violations=bad[:8])

    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump({"epoch": int(time.time()), "run": run, "recorded": len(rows),
                   "skipped": sum(1 for r in rows if r["score"] is None)}, f)
    # 어느 케이스가 틀렸는지는 내지 않는다 — v2는 그것을 출력해 2회차 만점을 보장했다.
    print(json.dumps({"ok": True, "run": run, "recorded": len(rows),
                      "skipped": sum(1 for r in rows if r["score"] is None),
                      "failed_count": sum(1 for r in rows if r["verdict"] == "fail"),
                      "note": "케이스별 결과는 --regress --reveal 로 사람이 확인한다"},
                     ensure_ascii=False))
    return 0


# ── 원장 · 게이트 ──────────────────────────────────────────────────────

def ledger_rows():
    rows, corrupt = [], 0
    for ln in read(LEDGER_PATH).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            corrupt += 1
            continue
        if isinstance(r, dict) and r.get("case") and r.get("type"):
            rows.append(r)
        else:
            corrupt += 1
    ledger_rows.corrupt = corrupt
    return rows


ledger_rows.corrupt = 0


def latest_cohort(rows, t):
    """타입 t의 **최신 run** 행들. latest-per-case가 아니다 — 코호트가 판정 단위다.

    v2는 케이스별 최신 행을 봤고, 그래서 실패한 케이스만 다시 제출해 게이트를 통과할 수 있었다."""
    runs = {}
    for r in rows:
        if r.get("type") == t:
            runs.setdefault(r.get("run", r.get("date", "?")), []).append(r)
    if not runs:
        return None, []
    # epoch 동률에서 순서가 흔들리지 않게 run 문자열을 2차 키로 쓴다.
    key = max(runs, key=lambda k: (max(x.get("epoch", 0) for x in runs[k]), str(k)))
    return key, runs[key]


def balanced_accuracy(rows):
    """클래스별 recall의 평균. 상수 전략은 표본 크기·불균형과 무관하게 정확히 0.5가 된다."""
    by = {}
    for r in rows:
        if r.get("gold") and r.get("score") is not None:
            by.setdefault(r["gold"], []).append(r["score"])
    if len(by) < 2:
        return None, {k: round(sum(v) / len(v), 3) for k, v in by.items()}
    recalls = {k: sum(v) / len(v) for k, v in by.items()}
    return round(sum(recalls.values()) / len(recalls), 4), {k: round(v, 3) for k, v in recalls.items()}


def regress(tol, reveal):
    try:
        cases = {c["id"]: c for c in load_cases()}
    except ValueError as e:
        return fail(str(e))
    if not 0 < tol <= 1:
        return fail("--drop 은 0 초과 1 이하여야 한다(받은 값: %s)" % tol)
    rows = ledger_rows()
    if not rows:
        # 이력이 없는 것도 '판정 불가'다. rc=0 + ok=true 였던 동안, 한 번도 채점하지 않은 상태가
        # '통과'로 읽혔다 — 전량 skipped와 같은 부류의 거짓 통과다.
        print(json.dumps({"ok": None, "verdict": "undecidable", "exit_code": 2,
                          "note": "원장이 비어 있다 — 채점 이력이 없다. 통과가 아니라 판정 불가다.",
                          "attempted_axes": [], "decided_axes": [], "unresolved_axes": []},
                         ensure_ascii=False))
        return 2

    problems, undecidable, info = [], [], {}
    decided = []          # 실제로 판정이 이뤄진 축
    attempted = []        # 코호트가 존재하는 축(=채점을 시도한 축). 이 중 미판정이 있으면 rc=2.

    def coverage_of(rws):
        graded = [x for x in rws if x.get("score") is not None]
        return graded, (len(graded) / len(rws) if rws else 0.0)

    grun, grows = latest_cohort(rows, "grounding")
    if grows:
        attempted.append("grounding")
        info["grounding_run"] = grun
        g_graded, g_cov = coverage_of(grows)
        info["grounding_coverage"] = {"graded": len(g_graded), "of": len(grows), "ratio": round(g_cov, 3)}
        if g_cov < MIN_COVERAGE:
            # 전량 skipped로 코호트를 '채우면' 아무것도 채점하지 않고 통과했다(v3 초판의 구멍,
            # 자체 감사에서 재현). 코호트 완결성은 **개수**가 아니라 **채점된 비율**로 봐야 한다.
            undecidable.append({"scope": "grounding", "why":
                                "채점된 비율 %.0f%% < %.0f%% — 코호트를 skipped로 채운 것은 채점이 아니다"
                                % (g_cov * 100, MIN_COVERAGE * 100)})
            grows = []
        else:
            decided.append("grounding")
    for r in grows:
        cid = r["case"]
        if cid not in cases or cases[cid].get("retired"):
            continue
        if r.get("score") is None:
            undecidable.append({"case": cid, "why": r.get("skipped", "skipped")})
            continue
        # v2의 게이트는 verdict를 읽지 않아, 모순이 기록된 fail이 rc=0으로 통과했다.
        if r.get("verdict") == "fail":
            problems.append({"case": cid, "kind": "fail", "detail":
                             "verdict=fail (contradictions=%s score=%s)"
                             % (r.get("contradictions"), r["score"])})
        # 이전 관측은 **다른 run**에서 찾는다. epoch 비교였을 때, 같은 초에 두 코호트가
        # 기록되면(--force 재채점이 정확히 그렇다) 이전 행이 하나도 잡히지 않아 회귀 감지가
        # 조용히 꺼졌다. 판정 단위가 코호트이므로 비교 단위도 코호트여야 한다.
        hist = [x for x in rows if x["case"] == cid and x.get("score") is not None
                and x.get("run") != r.get("run")]
        if hist:
            prev = max(hist, key=lambda x: (x.get("epoch", 0), str(x.get("run", ""))))
            if r.get("note_hash") and prev.get("note_hash") and r["note_hash"] != prev["note_hash"]:
                info.setdefault("rebaselined", []).append(cid)
            elif prev["score"] - r["score"] >= tol:
                problems.append({"case": cid, "kind": "drop",
                                 "detail": "%.3f -> %.3f" % (prev["score"], r["score"])})

    rrun, rrows = latest_cohort(rows, "routing")
    if rrows:
        attempted.append("routing")
        info["routing_run"] = rrun
        r_graded, r_cov = coverage_of(rrows)
        info["routing_coverage"] = {"graded": len(r_graded), "of": len(rrows), "ratio": round(r_cov, 3)}
        ba, recalls = balanced_accuracy(rrows)
        info["class_recalls"] = recalls
        per_class = {}
        for x in r_graded:
            if x.get("gold"):
                per_class[x["gold"]] = per_class.get(x["gold"], 0) + 1
        info["graded_per_class"] = per_class
        if r_cov < MIN_COVERAGE:
            undecidable.append({"scope": "routing", "why":
                                "채점된 비율 %.0f%% < %.0f%% — skipped로 코호트를 채운 것은 채점이 아니다"
                                % (r_cov * 100, MIN_COVERAGE * 100)})
        elif ba is None:
            undecidable.append({"scope": "routing", "why":
                                "정답이 한 클래스뿐 — balanced accuracy를 계산할 수 없다. "
                                "실패가 아니라 판정 불가다."})
        else:
            info["balanced_accuracy"] = ba
            if ba <= BALANCED_FLOOR:
                # 상수 전략은 표본 크기·불균형과 무관하게 정확히 이 값이다 → 확실한 실패.
                problems.append({"kind": "balanced_accuracy", "detail":
                                 "%.3f <= %.2f — 한 클래스만 답해도 이 값이 나온다(상수 전략의 값). "
                                 "채점자가 판단했다는 증거가 없다." % (ba, BALANCED_FLOOR)})
                decided.append("routing")
            elif min(per_class.values(), default=0) < MIN_CLASS_CASES:
                # BA > 0.5 이지만 **통과라고 말할 수는 없다**: 소수 클래스가 1건이면 그 1건의
                # 답이 BA를 0.5↔1.0으로 흔든다. 표본 10개인데 실질 판정이 1건에 달리는 상태다
                # (자체 감사에서 9q/1d로 재현). 상수 전략은 위에서 이미 잡히므로, 여기서 통과를
                # 보류하는 것이 게이트를 약화시키지 않는다.
                undecidable.append({"scope": "routing", "why":
                                    "balanced accuracy %.3f 는 기준을 넘지만 클래스별 채점 수가 %s — "
                                    "최소 %d건씩 필요하다. 소수 클래스가 1건이면 판정이 그 한 건에 "
                                    "좌우된다. `/claude-radar review`의 [dismissed] 결정이 쌓여야 "
                                    "이 축이 통과를 주장할 수 있다." % (ba, per_class, MIN_CLASS_CASES)})
            else:
                decided.append("routing")
    else:
        undecidable.append({"scope": "routing", "why": "채점 이력이 없다"})

    if ledger_rows.corrupt:
        info["corrupt_ledger_lines"] = ledger_rows.corrupt
        problems.append({"kind": "ledger", "detail":
                         "원장에 읽을 수 없는 줄이 %d개 있다 — 부분 이력으로 판정하지 않는다"
                         % ledger_rows.corrupt})

    # exit code 3원화. `undecidable`이 rc=0을 낳던 동안, 전량 skipped 코호트가 '통과'로 읽혔다 —
    # 아무것도 채점하지 않고 게이트를 통과하는 경로였다(자체 감사에서 재현). 판정하지 못한 것은
    # 통과가 아니다. 그렇다고 실패로 만들면 v2의 영구 실패 트랩이 돌아오므로 상태를 분리한다:
    #   rc=0 통과(실제로 판정했고 문제 없음) · rc=1 실패 · rc=2 판정 불가
    unresolved = [a for a in attempted if a not in decided]
    if problems:
        rc, verdict = 1, "fail"
    elif unresolved or not decided:
        # 채점을 **시도한** 축이 판정 불가로 남으면 통과라고 말하지 않는다. grounding이 통과했다는
        # 이유로 rc=0을 내면, routing에 대해 아무것도 말할 수 없는 상태가 '다 괜찮다'로 읽힌다.
        rc, verdict = 2, "undecidable"
    else:
        rc, verdict = 0, "pass"
    shown = problems if reveal else [{k: v for k, v in p.items() if k != "case"} for p in problems]
    shown_und = undecidable if reveal else [{k: v for k, v in u.items() if k != "case"}
                                           for u in undecidable]
    out = {"ok": (True if rc == 0 else (False if rc == 1 else None)),
           "verdict": verdict, "exit_code": rc,
           "decided_axes": decided, "attempted_axes": attempted, "unresolved_axes": unresolved,
           "problems": shown, "undecidable": shown_und, "info": info,
           "enforcement_limits": ["채점자가 radar-queue.md를 읽어 정답을 알 수 있다",
                                  "채점자가 원장·케이스 파일을 고칠 수 있다",
                                  "grounding 주장 수는 상한 안에서 채점자가 정한다"]}
    if rc == 2:
        out["hint"] = ("판정 불가는 통과가 아니다 — 위 undecidable 사유를 해소해야 이 게이트가 "
                       "의미를 갖는다(커버리지·클래스 표본).")
    elif not reveal and problems:
        out["hint"] = "케이스 id는 --reveal 로 본다(사람이 볼 때만)"
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return rc


def summary(reveal):
    try:
        load_cases()
    except ValueError as e:
        return fail(str(e))
    rows = ledger_rows()
    if not rows:
        print(json.dumps({"ok": True, "cases": 0, "note": "이력 없음"}, ensure_ascii=False))
        return 0
    out = {"ok": True, "runs": len({r.get("run") for r in rows}),
           "corrupt_ledger_lines": ledger_rows.corrupt}
    for t in ("grounding", "routing"):
        run, rs = latest_cohort(rows, t)
        if not rs:
            continue
        scored = [r["score"] for r in rs if r.get("score") is not None]
        blk = {"run": run, "n": len(rs), "skipped": len(rs) - len(scored),
               "mean": round(sum(scored) / len(scored), 4) if scored else None}
        if t == "routing":
            ba, recalls = balanced_accuracy(rs)
            blk["balanced_accuracy"] = ba
            blk["class_recalls"] = recalls
        if reveal:
            blk["cases"] = [{"case": r["case"], "score": r.get("score"),
                             "verdict": r.get("verdict")} for r in rs]
        out[t] = blk
    if not reveal:
        out["hint"] = "케이스별 점수는 --reveal 로 본다 — 채점 전에 보면 정답을 배운다"
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser(description="kb-eval — LLM 산출물 품질 평가 하네스 (v3)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--seed", action="store_true")
    g.add_argument("--list", action="store_true")
    g.add_argument("--record", metavar="FILE")
    g.add_argument("--regress", action="store_true")
    g.add_argument("--summary", action="store_true")
    ap.add_argument("--type", choices=("grounding", "routing"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--drop", type=float, default=DROP_TOL, help="회귀로 볼 하락 폭(0<x<=1)")
    ap.add_argument("--force", action="store_true", help="같은 날 재채점 허용(재굴림 — 신중히)")
    ap.add_argument("--reveal", action="store_true", help="케이스별 결과 노출(사람이 볼 때만)")
    args = ap.parse_args()
    try:
        if args.seed:
            return seed_cases()
        if args.list:
            return list_cases(args.type, args.limit)
        if args.record:
            return record(args.record, args.force)
        if args.regress:
            return regress(args.drop, args.reveal)
        return summary(args.reveal)
    except RecursionError:
        return fail("입력이 지나치게 중첩됐다")
    except KeyboardInterrupt:
        return fail("중단됨")


if __name__ == "__main__":
    sys.exit(main())
