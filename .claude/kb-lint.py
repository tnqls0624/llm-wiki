#!/usr/bin/env python3
"""KB(Claude Code 지식 베이스) 기계 검증 — stdlib only, LLM 없이 돌리는 1차 게이트.

검사 대상: vault 루트 아래 콘텐츠 노트 전부 (.claude/ .codex/ .obsidian/ .git/ .agents/ 및
모든 .space/ 디렉터리 제외한 **/*.md). .agents/ 는 .claude/ 와 마찬가지로 메커니즘
(스킬 정의 SKILL.md, frontmatter가 name/description) — KB 콘텐츠가 아니므로 제외한다.

검사 항목:
  a. 프론트매터 필수 필드 — .claude/kb-required-fields.txt 를 런타임에 읽고
     (없으면 하드코딩 fallback [title, updated, sources]) 각 노트에 존재하는지.
     단 type: moc 노트는 sources 면제(MOC는 원본을 가리키지 않는 허브).
  b. updated 형식 YYYY-MM-DD.
  c. 끊긴 [[위키링크]] — 코드펜스/인라인코드 제거 후 추출, [[타깃#앵커]]·[[타깃|별칭]] 처리,
     [[#...]] 같은-문서 앵커는 스킵, 타깃이 vault 내 .md 파일명(확장자 제외)과 일치하는지.
  d. 0-byte / 사실상 빈(<50자) 노트.
  e. 코드펜스(```) 홀수 — 닫히지 않음.
  f. --online: 공식 문서 인덱스(llms.txt)와 KB의 sources 슬러그 집합 비교.
     네트워크 실패는 경고만, exit code 미반영.

CLI: python3 .claude/kb-lint.py [--online] [--json]
출력: 사람용 한국어 요약(파일별 문제 + 통계). --json이면 JSON.
exit 0(문제 없음) / 1(문제 있음). --online 의 인덱스 비교 결과는 정보성이라 exit code에 미반영.
"""
import sys
import os
import re
import json
import datetime
import urllib.request
import urllib.error

LLMS_TXT_URL = "https://code.claude.com/docs/llms.txt"
FALLBACK_REQUIRED = ["title", "updated", "sources", "type"]
FALLBACK_TYPES = ["reference", "explanation", "how-to", "tutorial", "moc"]
EXCLUDE_DIR_NAMES = {".claude", ".codex", ".obsidian", ".git", ".agents", ".trash"}
MIN_BODY_CHARS = 50
AGE_WARN_DAYS = 90  # updated가 이보다 오래되면 stale 후보(정보성 — exit code 미반영)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def find_vault_root():
    """이 스크립트는 <vault>/.claude/kb-lint.py 에 산다 → 부모의 부모가 vault root."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


def is_excluded(rel_parts):
    """경로 조각 중 하나라도 제외 디렉터리거나 .space/ 면 제외."""
    for part in rel_parts:
        if part in EXCLUDE_DIR_NAMES:
            return True
        if part.endswith(".space"):
            return True
    return False


def collect_notes(root):
    """vault 아래 콘텐츠 .md 전부 (제외 디렉터리 + 루트 직속 메타 문서 빼고)."""
    notes = []
    root_abs = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        # 디렉터리 가지치기 — 제외 디렉터리는 내려가지 않는다.
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIR_NAMES and not d.endswith(".space")
        ]
        # 루트 직속 .md(README.md·CLAUDE.md 등 프로젝트 메타 문서)는 KB 노트가 아니다.
        # KB 노트는 항상 <Topic>/ 서브디렉터리 안에 있다(vault-rules: topic dir 패턴).
        if os.path.abspath(dirpath) == root_abs:
            continue
        for fn in filenames:
            if fn.endswith(".md"):
                notes.append(os.path.join(dirpath, fn))
    return sorted(notes)


def _load_list_file(root, filename, fallback):
    """`.claude/<filename>` 을 한 줄 한 항목으로 읽는다(# 주석·빈 줄 무시). 없거나 비면 fallback."""
    path = os.path.join(root, ".claude", filename)
    try:
        with open(path, encoding="utf-8") as f:
            items = [
                ln.strip()
                for ln in f
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
        if items:
            return items
    except Exception:
        pass
    return list(fallback)


def load_required_fields(root):
    """kb-required-fields.txt 런타임 로드. 없거나 비면 fallback."""
    return _load_list_file(root, "kb-required-fields.txt", FALLBACK_REQUIRED)


def load_allowed_types(root):
    """kb-allowed-types.txt 런타임 로드(닫힌 enum). 없거나 비면 fallback."""
    return _load_list_file(root, "kb-allowed-types.txt", FALLBACK_TYPES)


def parse_frontmatter(content):
    """단순 정규식 frontmatter 파서 (yaml 모듈 의존 금지).
    ^---\n...\n--- 블록을 잡아 'key: value' 한 줄 매핑으로 푼다.
    리스트는 두 형태 모두 지원:
      - 인라인:  sources: [a, b]
      - 블록형:  sources:\n  - a\n  - b   ← 다음 줄들이 '  - item' 패턴이면 리스트로 누적.
    블록형 한 패턴만 처리한다 — 중첩 매핑/멀티라인 스칼라(|, >)는 다루지 않는다(stdlib-only 단순성 유지)."""
    m = re.match(r"^---\n(.*?)\n---", content, re.S)
    if not m:
        return None, {}
    block = m.group(1)
    fm = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        fmatch = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not fmatch:
            i += 1
            continue
        key = fmatch.group(1)
        raw = fmatch.group(2).strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            items = [x.strip().strip("'\"") for x in inner.split(",")] if inner else []
            fm[key] = [x for x in items if x]
            i += 1
        elif raw == "":
            # 값이 비었으면 후속 줄이 블록형 리스트('  - item')인지 본다.
            collected = []
            j = i + 1
            while j < len(lines):
                im = re.match(r"^\s+-\s+(.*)$", lines[j])
                if not im:
                    break
                item = im.group(1).strip().strip("'\"")
                if item:
                    collected.append(item)
                j += 1
            fm[key] = collected  # 빈 리스트면 [] (block 없음과 동일 — 키만 존재)
            i = j if collected else i + 1
        else:
            fm[key] = raw.strip("'\"")
            i += 1
    return block, fm


def strip_code(content):
    """코드펜스(```...```)와 인라인코드(`...`)를 제거 — 그 안의 [[ ]] 류를
    링크로 오인하지 않기 위해. 펜스를 먼저, 인라인을 나중에 제거한다."""
    no_fence = re.sub(r"```.*?```", "", content, flags=re.S)
    no_inline = re.sub(r"`[^`\n]*`", "", no_fence)
    return no_fence, no_inline


def count_fences(content):
    """줄 시작의 ``` 펜스 개수 (홀수면 미닫힘)."""
    return len(re.findall(r"^\s*```", content, flags=re.M))


def extract_links(text_without_code):
    """[[타깃]] 추출 → 별칭(|)·앵커(#) 제거한 타깃 목록.
    [[#앵커]] 같은-문서 링크는 None 으로 표시해 호출부에서 스킵."""
    targets = []
    for raw in re.findall(r"\[\[([^\]]+)\]\]", text_without_code):
        body = raw.strip()
        if body.startswith("#"):
            continue  # 같은-문서 앵커
        target = body.split("|")[0].split("#")[0].strip()
        if target:
            targets.append(target)
    return targets


def lint_note(path, root, required, page_names, allowed_types):
    """단일 노트 검사 → (issues, meta).
    issues = 치명적 문제(exit code 반영). meta = 정보성 집계용 dict(updated/is_moc/has_conflict 등)."""
    issues = []
    meta = {"updated": None, "is_moc": False, "has_conflict": False, "has_type": False}
    try:
        raw = open(path, encoding="utf-8").read()
    except Exception as e:
        return ["읽기 실패: %s" % e], meta

    # d. 빈 노트
    stripped = raw.strip()
    if len(stripped) == 0:
        return ["0-byte/빈 노트"], meta
    if len(stripped) < MIN_BODY_CHARS:
        issues.append("사실상 빈 노트 (<%d자, 실제 %d자)" % (MIN_BODY_CHARS, len(stripped)))

    # a/b. 프론트매터
    block, fm = parse_frontmatter(raw)
    is_moc = fm.get("type") == "moc"
    meta["is_moc"] = is_moc
    meta["has_type"] = "type" in fm
    meta["updated"] = fm.get("updated")
    if block is None:
        issues.append("프론트매터(---) 블록 없음")
    else:
        for field in required:
            # MOC는 원본 슬러그가 없으므로 sources 면제
            if field == "sources" and is_moc:
                continue
            if field not in fm:
                issues.append("프론트매터 필수 필드 누락: %s" % field)
        if "updated" in fm and not DATE_RE.match(str(fm["updated"])):
            issues.append("updated 형식 오류 (YYYY-MM-DD 아님): %s" % fm["updated"])
        # type 닫힌 enum 검증 — 허용값 밖이면 어휘 드리프트로 간주.
        if "type" in fm and fm["type"] not in allowed_types:
            issues.append("type 값이 허용 enum 밖: %r (허용: %s)"
                          % (fm["type"], ", ".join(allowed_types)))

    # e. 코드펜스 홀수
    if count_fences(raw) % 2 != 0:
        issues.append("코드펜스(```) 미닫힘 — 펜스 개수 홀수")

    # c. 끊긴 위키링크
    no_fence, no_inline = strip_code(raw)
    links = extract_links(no_inline)
    for target in links:
        if target not in page_names:
            issues.append("끊긴 위키링크: [[%s]]" % target)

    # MOC 백링크 — 노트가 자기 토픽 MOC(<Topic>/<Topic>.md)를 역참조하는지(update duty ② 기계 강제).
    # 부모 디렉터리명 == MOC basename. MOC 자신과 MOC 없는 디렉터리는 면제.
    parent = os.path.basename(os.path.dirname(path))
    note_name = os.path.splitext(os.path.basename(path))[0]
    if parent in page_names and note_name != parent and not is_moc and parent not in links:
        issues.append("토픽 MOC 백링크 누락: [[%s]] (update duty ②)" % parent)

    # 모순 콜아웃 보유 여부(거버넌스 메트릭 — Conflict Rate).
    meta["has_conflict"] = bool(re.search(r">\s*\[!warning\]\s*모순", raw))

    # 중복 제거(순서 보존)
    return list(dict.fromkeys(issues)), meta


def check_links(notes, timeout=8):
    """각 노트 '## 원본 문서' 섹션의 http(s) URL을 HEAD로 생존 점검. (dead, checked_count).
    정보성 — exit code 미반영. cron 한정 권고(외부 egress). 403/405/429는 봇/메서드 차단으로 보고 생존 간주."""
    url_re = re.compile(r'https?://[^\s)>\]"]+')
    urls = {}  # url -> [note basenames]
    for path in notes:
        try:
            raw = open(path, encoding="utf-8").read()
        except Exception:
            continue
        m = re.search(r'^##\s*원본 문서\s*$(.*)', raw, re.M | re.S)
        section = m.group(1) if m else ""
        for u in url_re.findall(section):
            u = u.rstrip('.,;')
            urls.setdefault(u, []).append(os.path.basename(path))
    dead = []
    for u in sorted(urls):
        try:
            req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "kb-lint"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                code = resp.getcode()
            if code and code >= 400:
                dead.append({"url": u, "status": code, "notes": urls[u]})
        except urllib.error.HTTPError as e:
            if e.code not in (403, 405, 429) and e.code >= 400:
                dead.append({"url": u, "status": e.code, "notes": urls[u]})
        except Exception as e:
            dead.append({"url": u, "status": str(e)[:50], "notes": urls[u]})
    return dead, len(urls)


def extract_index_slugs(text):
    """llms.txt 에서 docs 슬러그 전수 추출.
    링크 형태: https://code.claude.com/docs/en/<slug>(.md)?  또는  /docs/en/<slug>.
    <slug> 는 슬래시 포함 가능(whats-new/2026-w13 등). 앵커·쿼리 제거."""
    slugs = set()
    pat = re.compile(r"/docs/(?:en/)?([A-Za-z0-9][A-Za-z0-9/_-]*?)(?:\.md)?(?=[)\s\"'#?]|$)")
    for m in pat.finditer(text):
        slug = m.group(1)
        # llms.txt 자체나 루트성 토큰 제외
        if slug in ("en", "llms", "llms-full"):
            continue
        slugs.add(slug)
    return slugs


def check_online(root, notes):
    """공식 인덱스 슬러그 ↔ KB sources 슬러그 비교. (info, network_failed)."""
    info = {"new_in_docs": [], "missing_from_index": [], "network_error": None}
    # KB sources 합집합 (Claude/*.md 만 sources 를 가짐; 그래도 전 노트에서 모은다)
    kb_slugs = set()
    for path in notes:
        try:
            raw = open(path, encoding="utf-8").read()
        except Exception:
            continue
        _, fm = parse_frontmatter(raw)
        src = fm.get("sources")
        if isinstance(src, list):
            # 공식 docs 슬러그만 비교 대상 — 외부 URL(http(s), 예: AI-Infra/Infra의 vLLM·AWS 문서)은
            # code.claude.com 인덱스에 없는 게 당연하므로 제외(missing_from_index 노이즈 방지).
            kb_slugs.update(s for s in src if s and not s.startswith("http"))
    try:
        req = urllib.request.Request(LLMS_TXT_URL, headers={"User-Agent": "kb-lint"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", "replace")
    except Exception as e:
        info["network_error"] = str(e)
        return info
    index_slugs = extract_index_slugs(text)
    if not index_slugs:
        info["network_error"] = "인덱스에서 슬러그를 추출하지 못함(형식 변경 가능성)"
        return info
    # 공식 문서에 새로 생긴 슬러그(인덱스엔 있으나 KB엔 없음)
    info["new_in_docs"] = sorted(index_slugs - kb_slugs)
    # KB엔 있으나 인덱스에서 사라진 슬러그
    info["missing_from_index"] = sorted(kb_slugs - index_slugs)
    info["index_count"] = len(index_slugs)
    info["kb_count"] = len(kb_slugs)
    return info


def compute_governance(metas, today):
    """정보성 거버넌스 메트릭 집계(exit code 미반영). today=오늘 날짜(테스트 주입 가능)."""
    stale = []  # (rel, age_days)
    for rel, m in metas.items():
        u = m.get("updated")
        if not u or not DATE_RE.match(str(u)):
            continue
        try:
            age = (today - datetime.date.fromisoformat(str(u))).days
        except ValueError:
            continue
        if age > AGE_WARN_DAYS:
            stale.append((rel, age))
    stale.sort(key=lambda x: -x[1])
    return {
        "total": len(metas),
        "with_type": sum(1 for m in metas.values() if m.get("has_type")),
        "conflicts": sorted(rel for rel, m in metas.items() if m.get("has_conflict")),
        "stale": stale,
        "age_threshold_days": AGE_WARN_DAYS,
    }


def main():
    args = sys.argv[1:]
    online = "--online" in args
    as_json = "--json" in args
    do_links = "--links" in args

    root = find_vault_root()
    required = load_required_fields(root)
    allowed_types = load_allowed_types(root)
    notes = collect_notes(root)
    page_names = {os.path.splitext(os.path.basename(p))[0] for p in notes}

    results = {}  # rel_path -> [issues]
    metas = {}    # rel_path -> meta(정보성)
    total_issues = 0
    for path in notes:
        issues, meta = lint_note(path, root, required, page_names, allowed_types)
        rel = os.path.relpath(path, root)
        metas[rel] = meta
        if issues:
            results[rel] = issues
            total_issues += len(issues)

    online_info = check_online(root, notes) if online else None
    gov = compute_governance(metas, datetime.date.today())
    links_info = check_links(notes) if do_links else None

    has_problems = total_issues > 0  # online·age·links·governance는 exit code 미반영

    if as_json:
        out = {
            "vault_root": root,
            "notes_scanned": len(notes),
            "required_fields": required,
            "allowed_types": allowed_types,
            "files_with_issues": results,
            "issue_count": total_issues,
            "ok": not has_problems,
            "governance": {
                "total": gov["total"],
                "with_type": gov["with_type"],
                "conflicts": gov["conflicts"],
                "stale": [{"note": r, "age_days": a} for r, a in gov["stale"]],
                "age_threshold_days": gov["age_threshold_days"],
            },
        }
        if online_info is not None:
            out["online"] = online_info
        if links_info is not None:
            dead, checked = links_info
            out["links"] = {"checked": checked, "dead": dead}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.exit(1 if has_problems else 0)

    # 사람용 한국어 요약
    lines = []
    lines.append("KB 린트 — 검사 노트 %d개 (vault: %s)" % (len(notes), root))
    lines.append("필수 필드: %s" % ", ".join(required))
    lines.append("")
    if results:
        lines.append("문제가 있는 파일 %d개, 총 %d건:" % (len(results), total_issues))
        for rel in sorted(results):
            lines.append("")
            lines.append("  %s" % rel)
            for iss in results[rel]:
                lines.append("    - %s" % iss)
    else:
        lines.append("문제 없음 — 모든 노트 통과.")

    # 거버넌스 메트릭(정보성, exit code 미반영) — hot.md 한 줄 보고용 한 줄 요약 포함.
    lines.append("")
    lines.append("── 거버넌스 (정보성) ──")
    lines.append("  type 보유 %d/%d · 모순 콜아웃 %d개 · 신선도(>%dd) %d개"
                 % (gov["with_type"], gov["total"], len(gov["conflicts"]),
                    gov["age_threshold_days"], len(gov["stale"])))
    if gov["stale"]:
        lines.append("  stale 후보(updated 오래된 순):")
        for rel, age in gov["stale"][:10]:
            lines.append("    - %s (%d일)" % (rel, age))
        if len(gov["stale"]) > 10:
            lines.append("    …외 %d개" % (len(gov["stale"]) - 10))

    if links_info is not None:
        dead, checked = links_info
        lines.append("")
        lines.append("── 외부 URL 점검 (--links, 정보성, exit code 미반영) ──")
        lines.append("  점검 %d개 URL ↔ 죽은 링크 %d개" % (checked, len(dead)))
        for d in dead:
            lines.append("    ✗ [%s] %s  ←  %s"
                         % (d["status"], d["url"], ", ".join(d["notes"])))

    if online_info is not None:
        lines.append("")
        lines.append("── 공식 문서 인덱스 대조 (--online, 정보성, exit code 미반영) ──")
        if online_info.get("network_error"):
            lines.append("  네트워크/파싱 실패(무시): %s" % online_info["network_error"])
        else:
            lines.append("  인덱스 슬러그 %d개 ↔ KB sources %d개"
                         % (online_info.get("index_count", 0), online_info.get("kb_count", 0)))
            new = online_info["new_in_docs"]
            missing = online_info["missing_from_index"]
            if new:
                lines.append("  공식 문서에 새로 생긴(또는 KB 미수록) 슬러그 %d개:" % len(new))
                for s in new:
                    lines.append("    + %s" % s)
            else:
                lines.append("  공식 문서에 새로 생긴 슬러그 없음.")
            if missing:
                lines.append("  KB에는 있으나 인덱스에서 사라진 슬러그 %d개:" % len(missing))
                for s in missing:
                    lines.append("    - %s" % s)
            else:
                lines.append("  KB sources 중 인덱스에서 사라진 슬러그 없음.")

    print("\n".join(lines))
    sys.exit(1 if has_problems else 0)


if __name__ == "__main__":
    main()
