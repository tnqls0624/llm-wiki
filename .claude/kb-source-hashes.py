#!/usr/bin/env python3
"""kb-sync 보조 — 출처(sources) 원문의 콘텐츠 해시를 추적해 '같은 슬러그 안의 본문 변경'을 잡는다.
stdlib only. kb-sync.md가 자인한 한계(슬러그 레벨 diff만 — 같은 슬러그 내용 변경 미감지)를 메운다.

동작:
  1. 전 KB 노트에서 sources 항목을 모은다(kb-lint.parse_frontmatter 재사용).
  2. 각 항목을 raw URL로 변환(슬러그 → code.claude.com/docs/en/<slug>.md, http(s)면 그대로).
  3. GET fetch → sha256. 이전 해시(runtime/source-hashes.json)와 비교.
  4. 변경/신규/사라진 항목을 출력. --update면 해시 스냅샷을 저장.

**안전**: 이 스크립트는 KB 노트를 수정하지 않는다 — 변경 '감지'까지만(automation-safety least-authority).
실제 노트 반영은 사용자가 `/kb-sync --deep <노트>`로 결정(collect↔review 분리). cron 한정(외부 egress).

CLI: python3 .claude/kb-source-hashes.py [--update] [--json]
exit 0(항상 — 정보성). 네트워크 실패한 항목은 errors로 보고하되 exit code 미반영.
"""
import sys
import os
import re
import json
import hashlib
import importlib.util
import urllib.request
import urllib.error

DOCS_RAW = "https://code.claude.com/docs/en/%s.md"
HASH_STORE = "source-hashes.json"  # .claude/runtime/ 아래


def _load_kblint():
    """kb-lint.py(하이픈 파일명 → importlib)를 로드해 parse_frontmatter/collect_notes 재사용."""
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("kblint", os.path.join(here, "kb-lint.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def source_to_url(item):
    """sources 항목 → 완전 raw URL. http(s)면 그대로, 아니면 Claude 공식문서 슬러그로 간주."""
    item = item.strip()
    if item.startswith("http://") or item.startswith("https://"):
        return item
    return DOCS_RAW % item


def diff_hashes(old, new):
    """이전/현재 해시 맵 비교 → (changed, added, removed). 순수 함수(테스트 대상)."""
    old = old or {}
    new = new or {}
    changed = sorted(k for k in new if k in old and old[k] != new[k])
    added = sorted(k for k in new if k not in old)
    removed = sorted(k for k in old if k not in new)
    return changed, added, removed


def collect_sources(root, kblint):
    """전 KB 노트의 sources 합집합. 항목 → 그 항목을 sources에 가진 노트 basename 목록."""
    src_to_notes = {}
    for path in kblint.collect_notes(root):
        try:
            raw = open(path, encoding="utf-8").read()
        except Exception:
            continue
        _, fm = kblint.parse_frontmatter(raw)
        src = fm.get("sources")
        if isinstance(src, list):
            for s in src:
                if s:
                    src_to_notes.setdefault(s, []).append(os.path.basename(path))
    return src_to_notes


def fetch_hash(url, timeout=20):
    """raw 본문 GET → sha256 hexdigest. 실패 시 None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kb-source-hashes"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return hashlib.sha256(resp.read()).hexdigest()
    except Exception:
        return None


def main():
    args = sys.argv[1:]
    do_update = "--update" in args
    as_json = "--json" in args

    kblint = _load_kblint()
    root = kblint.find_vault_root()
    store_path = os.path.join(root, ".claude", "runtime", HASH_STORE)

    try:
        with open(store_path, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = {}

    src_to_notes = collect_sources(root, kblint)
    new, errors = {}, []
    for item in sorted(src_to_notes):
        url = source_to_url(item)
        h = fetch_hash(url)
        if h is None:
            errors.append({"source": item, "url": url, "notes": src_to_notes[item]})
            continue
        new[item] = h

    # 네트워크로 못 받은 항목은 이전 해시를 보존(누락을 'removed'로 오인하지 않게).
    merged = dict(old)
    merged.update(new)
    for e in errors:
        merged.setdefault(e["source"], old.get(e["source"], ""))

    changed, added, removed = diff_hashes(old, new) if old else ([], sorted(new), [])

    if do_update:
        os.makedirs(os.path.dirname(store_path), exist_ok=True)
        with open(store_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2, sort_keys=True)

    suspect = [{"source": s, "url": source_to_url(s), "notes": src_to_notes.get(s, [])} for s in changed]

    if as_json:
        print(json.dumps({
            "checked": len(new), "baseline": not old,
            "changed": suspect, "added": added, "removed": removed,
            "errors": errors, "updated": do_update,
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    lines = ["kb-source-hashes — 출처 원문 콘텐츠 해시 점검 (정보성)"]
    if not old:
        lines.append("  최초 실행(baseline) — %d개 항목 해시 기록%s." % (len(new), " 저장됨" if do_update else " (미저장: --update 필요)"))
    else:
        lines.append("  점검 %d개 · 내용 변경 의심 %d개 · 신규 %d개 · 사라짐 %d개"
                     % (len(new), len(changed), len(added), len(removed)))
        if suspect:
            lines.append("  ⚠ 본문 변경 의심(=/kb-sync --deep 대상):")
            for s in suspect:
                lines.append("    ~ %s  ←  %s" % (s["source"], ", ".join(s["notes"])))
    if errors:
        lines.append("  네트워크 실패 %d개(무시, 이전 해시 보존):" % len(errors))
        for e in errors[:10]:
            lines.append("    ? %s" % e["source"])
    print("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
