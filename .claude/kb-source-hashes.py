#!/usr/bin/env python3
"""kb-sync 보조 — 출처(sources) 원문의 콘텐츠 해시를 추적해 '같은 슬러그 안의 본문 변경'을 잡는다.
stdlib only. kb-sync.md가 자인한 한계(슬러그 레벨 diff만 — 같은 슬러그 내용 변경 미감지)를 메운다.

동작:
  1. 전 KB 노트에서 sources 항목을 모은다(kb-lint.parse_frontmatter 재사용).
  2. 각 항목을 raw URL로 변환(슬러그 → code.claude.com/docs/en/<slug>.md, http(s)면 그대로).
  3. GET fetch → 항목별로 해시 2개를 낸다:
       full — 원문 전체 sha256 (어떤 글자 하나만 바뀌어도 달라진다)
       skel — 구조 지문 sha256: 헤딩 + 백틱 식별자(설정키·플래그·환경변수)의 정렬된 집합
  4. 이전 스냅샷과 비교해 변경을 **두 층으로 나눈다**:
       structural — skel 이 달라짐. 섹션이나 식별자가 생기고/사라짐 → 종합 노트가 낡았을 가능성 높음.
       prose      — full 만 달라짐. 표현·오타·링크 재작성 → 노트 내용에는 보통 영향 없음.
     2026-08-22 측정: 이 문서 사이트는 2~14일 구간마다 출처의 60~80%가 full 변경으로 잡혀
     단일 층 검출기가 매 실행 발화했다(07-27→08-10 206/251, 08-10→08-20 187/253, 08-20→08-22 149/254).
     계층화는 그 안에서 실제로 볼 것을 골라내기 위한 것이다.
  5. --update면 스냅샷을 저장한다.

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


HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)
IDENT_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.\-]{2,})`")


def skeleton(text):
    """구조 지문 — 헤딩 + 백틱 식별자의 정렬된 집합을 sha256.
    프로즈 수정·링크 재작성·오타 교정에는 불변이고, 섹션/설정키/플래그가 생기거나 사라지면 변한다.
    순수 함수(테스트 대상)."""
    heads = {h.strip() for h in HEADING_RE.findall(text)}
    idents = {i for i in IDENT_RE.findall(text)}
    payload = "\n".join(sorted(heads)) + "\n--\n" + "\n".join(sorted(idents))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _entry(v):
    """스냅샷 값을 {full, skel} 로 정규화. 구 포맷(문자열=full만)도 읽는다."""
    if isinstance(v, dict):
        return {"full": v.get("full"), "skel": v.get("skel")}
    return {"full": v, "skel": None}


def classify_changes(old, new, changed):
    """changed 항목을 structural / prose / unknown 으로 분류. 순수 함수(테스트 대상).
    unknown = 이전 스냅샷이 구 포맷(skel 부재)이라 구조 비교가 불가능한 항목.
    보수적으로 structural 이라 주장하지 않는다."""
    structural, prose, unknown = [], [], []
    for k in changed:
        o, n = _entry((old or {}).get(k)), _entry((new or {}).get(k))
        if o["skel"] is None or n["skel"] is None:
            unknown.append(k)
        elif o["skel"] != n["skel"]:
            structural.append(k)
        else:
            prose.append(k)
    return sorted(structural), sorted(prose), sorted(unknown)


def diff_hashes(old, new):
    """이전/현재 해시 맵 비교 → (changed, added, removed). 순수 함수(테스트 대상)."""
    old = old or {}
    new = new or {}
    changed = sorted(k for k in new if k in old and old[k] != new[k])
    added = sorted(k for k in new if k not in old)
    removed = sorted(k for k in old if k not in new)
    return changed, added, removed


def collect_sources(root, kblint):
    """전 KB 노트의 source_urls 합집합. 항목 → 그 항목을 source_urls에 가진 노트 basename 목록."""
    src_to_notes = {}
    for path in kblint.collect_notes(root):
        try:
            raw = open(path, encoding="utf-8").read()
        except Exception:
            continue
        _, fm = kblint.parse_frontmatter(raw)
        src = fm.get("source_urls")
        if isinstance(src, list):
            for s in src:
                if s:
                    src_to_notes.setdefault(s, []).append(os.path.basename(path))
    return src_to_notes


def fetch_hash(url, timeout=20):
    """raw 본문 GET → {"full": sha256, "skel": sha256}. 실패 시 None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kb-source-hashes"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return {"full": hashlib.sha256(raw).hexdigest(),
                "skel": skeleton(raw.decode("utf-8", "replace"))}
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

    # 2026-08-22 버그 수정: 위 보존이 merged(쓰기 경로)에만 반영돼 있어서, fetch 실패 항목이
    # diff 입력(new)에서 빠지며 매번 'removed'로 보고됐다(외부 블로그 URL 2건이 그 사례).
    # 주석이 선언한 의도가 구현되지 않았던 것 — diff 입력에도 같은 보존을 적용한다.
    # 이제 removed 는 "어떤 노트도 더 이상 이 출처를 참조하지 않음"만 의미한다.
    current = dict(new)
    for e in errors:
        if e["source"] in old:
            current[e["source"]] = old[e["source"]]

    changed, added, removed = diff_hashes(old, current) if old else ([], sorted(current), [])
    structural, prose, unknown = classify_changes(old, current, changed)

    if do_update:
        os.makedirs(os.path.dirname(store_path), exist_ok=True)
        with open(store_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2, sort_keys=True)

    def _items(keys):
        return [{"source": s, "url": source_to_url(s), "notes": src_to_notes.get(s, [])} for s in keys]

    suspect = _items(changed)

    if as_json:
        print(json.dumps({
            "checked": len(new), "baseline": not old,
            # changed = structural + prose + unknown 합집합(하위 호환 유지).
            # 리뷰 대상은 changed_structural 이다 — changed 전체가 아니다.
            "changed": suspect, "added": added, "removed": removed,
            "changed_structural": _items(structural),
            "changed_prose_only": _items(prose),
            "changed_unknown": _items(unknown),
            "errors": errors, "updated": do_update,
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    lines = ["kb-source-hashes — 출처 원문 콘텐츠 해시 점검 (정보성)"]
    if not old:
        lines.append("  최초 실행(baseline) — %d개 항목 해시 기록%s." % (len(new), " 저장됨" if do_update else " (미저장: --update 필요)"))
    else:
        lines.append("  점검 %d개 · 변경 %d개(구조 %d / 프로즈만 %d / 판정불가 %d) · 신규 %d개 · 사라짐 %d개"
                     % (len(new), len(changed), len(structural), len(prose), len(unknown),
                        len(added), len(removed)))
        if structural:
            lines.append("  ⚠ 구조 변경 — 섹션/식별자가 생기거나 사라짐 (=/kb-sync --deep 대상):")
            for s in _items(structural):
                lines.append("    ~ %s  ←  %s" % (s["source"], ", ".join(s["notes"])))
        if prose:
            lines.append("  · 프로즈만 변경 %d개 — 표현·링크 재작성. 노트 반영 보통 불필요(생략)." % len(prose))
        if unknown:
            lines.append("  · 판정불가 %d개 — 이전 스냅샷이 구 포맷(skel 없음). --update 후 다음 실행부터 분류됨." % len(unknown))
    if errors:
        lines.append("  네트워크 실패 %d개(무시, 이전 해시 보존):" % len(errors))
        for e in errors[:10]:
            lines.append("    ? %s" % e["source"])
    print("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
