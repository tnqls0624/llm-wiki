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
import urllib.request

LLMS_TXT_URL = "https://code.claude.com/docs/llms.txt"
FALLBACK_REQUIRED = ["title", "updated", "sources"]
EXCLUDE_DIR_NAMES = {".claude", ".codex", ".obsidian", ".git", ".agents", ".trash"}
MIN_BODY_CHARS = 50
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


def load_required_fields(root):
    """kb-required-fields.txt 런타임 로드. 없거나 비면 fallback."""
    path = os.path.join(root, ".claude", "kb-required-fields.txt")
    try:
        with open(path, encoding="utf-8") as f:
            fields = [
                ln.strip()
                for ln in f
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
        if fields:
            return fields
    except Exception:
        pass
    return list(FALLBACK_REQUIRED)


def parse_frontmatter(content):
    """단순 정규식 frontmatter 파서 (yaml 모듈 의존 금지).
    ^---\n...\n--- 블록을 잡아 'key: value' 한 줄 매핑으로 푼다.
    sources: [a, b] 인라인 배열은 리스트로 파싱."""
    m = re.match(r"^---\n(.*?)\n---", content, re.S)
    if not m:
        return None, {}
    block = m.group(1)
    fm = {}
    for line in block.splitlines():
        fmatch = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not fmatch:
            continue
        key = fmatch.group(1)
        raw = fmatch.group(2).strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            items = [x.strip().strip("'\"") for x in inner.split(",")] if inner else []
            fm[key] = [x for x in items if x]
        else:
            fm[key] = raw.strip("'\"")
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


def lint_note(path, root, required, page_names):
    """단일 노트 검사 → 문제 문자열 리스트."""
    issues = []
    try:
        raw = open(path, encoding="utf-8").read()
    except Exception as e:
        return ["읽기 실패: %s" % e]

    # d. 빈 노트
    stripped = raw.strip()
    if len(stripped) == 0:
        return ["0-byte/빈 노트"]
    if len(stripped) < MIN_BODY_CHARS:
        issues.append("사실상 빈 노트 (<%d자, 실제 %d자)" % (MIN_BODY_CHARS, len(stripped)))

    # a/b. 프론트매터
    block, fm = parse_frontmatter(raw)
    if block is None:
        issues.append("프론트매터(---) 블록 없음")
    else:
        is_moc = fm.get("type") == "moc"
        for field in required:
            # MOC는 원본 슬러그가 없으므로 sources 면제
            if field == "sources" and is_moc:
                continue
            if field not in fm:
                issues.append("프론트매터 필수 필드 누락: %s" % field)
        if "updated" in fm and not DATE_RE.match(str(fm["updated"])):
            issues.append("updated 형식 오류 (YYYY-MM-DD 아님): %s" % fm["updated"])

    # e. 코드펜스 홀수
    if count_fences(raw) % 2 != 0:
        issues.append("코드펜스(```) 미닫힘 — 펜스 개수 홀수")

    # c. 끊긴 위키링크
    no_fence, no_inline = strip_code(raw)
    for target in extract_links(no_inline):
        if target not in page_names:
            issues.append("끊긴 위키링크: [[%s]]" % target)

    # 중복 제거(순서 보존)
    return list(dict.fromkeys(issues))


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
            kb_slugs.update(s for s in src if s)
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


def main():
    args = sys.argv[1:]
    online = "--online" in args
    as_json = "--json" in args

    root = find_vault_root()
    required = load_required_fields(root)
    notes = collect_notes(root)
    page_names = {os.path.splitext(os.path.basename(p))[0] for p in notes}

    results = {}  # rel_path -> [issues]
    total_issues = 0
    for path in notes:
        issues = lint_note(path, root, required, page_names)
        if issues:
            rel = os.path.relpath(path, root)
            results[rel] = issues
            total_issues += len(issues)

    online_info = check_online(root, notes) if online else None

    has_problems = total_issues > 0  # online 비교는 exit code 미반영

    if as_json:
        out = {
            "vault_root": root,
            "notes_scanned": len(notes),
            "required_fields": required,
            "files_with_issues": results,
            "issue_count": total_issues,
            "ok": not has_problems,
        }
        if online_info is not None:
            out["online"] = online_info
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
