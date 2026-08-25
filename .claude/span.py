#!/usr/bin/env python3
"""span — 무인 루프의 구조화 실행 원장 (2026-08-25).

왜 필요(실측): cron 로그는 자유 텍스트 + `exit=N`이다. 그래서 답할 수 없는 질문이 쌓였다 —
어느 단계에서 죽었나, 언제부터 느려졌나, 이 루프의 성공률은 얼마인가, 지난주 대비 산출량이
줄었나. 실제로 radar는 26일간 exit=0으로 침묵했고 kb-sync는 duty-③만 빠뜨린 채 성공으로
보고했다. 영수증(radar-last-collect / hot-last-append / eval-last-run)도 세 곳에 흩어져
"마지막 실행"의 단일 소스가 없다.

설계는 earendil-works/pi 의 pi-telemetry 계약을 우리 규모로 축약했다 — span(시작·끝이 있는
작업 1건) + attributes(그 작업에 붙는 명명된 사실) + status(ok|error). 익스포터·백엔드·전역
current-span 상태는 없다: 원장은 JSONL 한 파일이고, 상위 span은 인자로 명시한다. 우리 루프는
단일 레벨이라 트리 추적을 위한 복잡도를 지불할 이유가 없다.

파일 하나만 쓴다(`runtime/spans.jsonl`, append-only). 무인 런에서도 쓸 수 있는 이유는
radar `--append-queue`·`hot-append.py`와 같다 — 스크립트 경로는 harness의 sensitive 차단을
받지 않는다.

사용(shell 계측):
  SPAN="$(python3 .claude/span.py start kb-sync)"
  ... 작업 ...
  python3 .claude/span.py end "$SPAN" --status ok --attr notes=3 --attr gate=review-ran

  python3 .claude/span.py summary [--days 30]      # 루프별 성공률·지속시간·마지막 실행
  python3 .claude/span.py check kb-sync --max-age-days 9   # 마지막 성공이 오래됐으면 exit 1
"""
import argparse
import datetime
import json
import os
import re
import sys
import time

CLAUDE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(CLAUDE, "runtime", "spans.jsonl")
MAX_LINES = 5000          # 초과 시 뒤쪽 절반만 유지(cron 로그 회전과 같은 정책)
MAX_ATTRS = 12
MAX_VAL_LEN = 200


def fail(msg):
    print("span: %s" % msg, file=sys.stderr)
    return 1


def sanitize(s):
    s = re.sub(r"[\x00-\x1f\x7f]", " ", str(s))
    return re.sub(r"\s+", " ", s).strip()[:MAX_VAL_LEN]


def parse_attrs(pairs):
    """`k=v` 목록 → dict. 숫자로 보이면 숫자로 저장한다(추이 계산에 쓰이므로)."""
    out = {}
    for p in (pairs or [])[:MAX_ATTRS]:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        k = re.sub(r"[^A-Za-z0-9_.]", "", k)[:40]
        if not k:
            continue
        v = sanitize(v)
        try:
            out[k] = int(v)
        except ValueError:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def append(row):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    rotate()


def rotate():
    try:
        with open(LEDGER, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return
    if len(lines) <= MAX_LINES:
        return
    keep = lines[len(lines) // 2:]
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(keep)
    os.replace(tmp, LEDGER)


def rows():
    out = []
    try:
        with open(LEDGER, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    continue      # 손상 줄은 건너뛴다 — 원장 하나가 루프를 죽이면 안 된다
    except OSError:
        pass
    return out


def cmd_start(args):
    name = re.sub(r"[^A-Za-z0-9_.-]", "", args.name)[:40]
    if not name:
        return fail("span 이름이 비었다")
    epoch = int(time.time())
    sid = "%s-%d-%d" % (name, epoch, os.getpid())
    append({"id": sid, "name": name, "phase": "start", "epoch": epoch,
            "date": datetime.date.today().isoformat(),
            "parent": args.parent or "", "attrs": parse_attrs(args.attr)})
    print(sid)     # shell이 캡처해 end 로 넘긴다
    return 0


def cmd_end(args):
    sid = sanitize(args.id)
    if not sid:
        return fail("span id가 비었다")
    start = None
    for r in rows():
        if r.get("id") == sid and r.get("phase") == "start":
            start = r
    if start is None:
        # fail-loud: 짝 없는 end 는 계측 버그다. 원장에는 남기되(유실 방지) 경고로 알린다.
        print("span: 짝이 되는 start를 찾지 못했다 (%s) — 계측 확인 필요" % sid, file=sys.stderr)
    epoch = int(time.time())
    dur = (epoch - start["epoch"]) if start else None
    append({"id": sid, "name": start["name"] if start else sid.split("-")[0],
            "phase": "end", "epoch": epoch,
            "date": datetime.date.today().isoformat(),
            "status": args.status, "duration_s": dur,
            "orphan": start is None, "attrs": parse_attrs(args.attr)})
    return 0


def cmd_summary(args):
    cutoff = int(time.time()) - args.days * 86400
    ends = [r for r in rows() if r.get("phase") == "end" and r.get("epoch", 0) >= cutoff]
    if not ends:
        print(json.dumps({"ok": True, "days": args.days, "loops": {},
                          "note": "이 기간에 종료된 span이 없다"}, ensure_ascii=False))
        return 0
    by = {}
    for r in ends:
        by.setdefault(r.get("name", "?"), []).append(r)
    loops = {}
    for name, rs in sorted(by.items()):
        rs.sort(key=lambda x: x.get("epoch", 0))
        durs = sorted(x["duration_s"] for x in rs if isinstance(x.get("duration_s"), int))
        ok = sum(1 for x in rs if x.get("status") == "ok")
        loops[name] = {
            "runs": len(rs),
            "ok": ok,
            "error": len(rs) - ok,
            "success_rate": round(ok / len(rs), 3),
            "median_duration_s": durs[len(durs) // 2] if durs else None,
            "max_duration_s": durs[-1] if durs else None,
            "last_run": rs[-1].get("date"),
            "last_status": rs[-1].get("status"),
            "last_attrs": rs[-1].get("attrs", {}),
            "orphans": sum(1 for x in rs if x.get("orphan")),
        }
    print(json.dumps({"ok": True, "days": args.days, "loops": loops}, ensure_ascii=False, indent=1))
    return 0


def cmd_check(args):
    """데드맨 보조: 마지막 **성공** span이 임계보다 오래됐으면 exit 1.

    기존 session-context 데드맨은 산출물 파일의 날짜를 본다(학습 로그·seen ledger·노트 updated).
    이건 '루프가 돌았는가' 자체를 본다 — 산출물이 없는 정상 무소음(no-commits 게이트)과
    루프 사망을 구분하려면 두 신호가 다 필요하다."""
    name = re.sub(r"[^A-Za-z0-9_.-]", "", args.name)[:40]
    oks = [r for r in rows()
           if r.get("phase") == "end" and r.get("name") == name and r.get("status") == "ok"]
    if not oks:
        print(json.dumps({"ok": False, "name": name, "reason": "성공 기록이 없다"},
                         ensure_ascii=False))
        return 1
    last = max(x.get("epoch", 0) for x in oks)
    age_days = (int(time.time()) - last) / 86400.0
    stale = age_days > args.max_age_days
    print(json.dumps({"ok": not stale, "name": name, "age_days": round(age_days, 2),
                      "max_age_days": args.max_age_days}, ensure_ascii=False))
    return 1 if stale else 0


def main():
    ap = argparse.ArgumentParser(description="무인 루프 실행 원장(span/attrs/status)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="span 시작 — id를 stdout에 출력")
    s.add_argument("name")
    s.add_argument("--parent", default="", help="상위 span id(선택)")
    s.add_argument("--attr", action="append", help="k=v (반복 가능)")
    s.set_defaults(func=cmd_start)

    e = sub.add_parser("end", help="span 종료")
    e.add_argument("id")
    e.add_argument("--status", choices=("ok", "error"), required=True)
    e.add_argument("--attr", action="append", help="k=v (반복 가능)")
    e.set_defaults(func=cmd_end)

    m = sub.add_parser("summary", help="루프별 성공률·지속시간 추이")
    m.add_argument("--days", type=int, default=30)
    m.set_defaults(func=cmd_summary)

    c = sub.add_parser("check", help="마지막 성공이 오래됐으면 exit 1")
    c.add_argument("name")
    c.add_argument("--max-age-days", type=float, default=9.0)
    c.set_defaults(func=cmd_check)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
