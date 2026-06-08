#!/usr/bin/env python3
"""PostToolUse 훅 — KB 콘텐츠 노트 편집 직후 경량 점검(즉시 피드백).
편집된 '단일 파일'만 빠르게 검사한다:
  1) 프론트매터 필수 필드 누락(.claude/kb-required-fields.txt 런타임 로드)
  2) 끊긴 [[위키링크]] (vault 전체 .md 파일명 대비; 코드펜스/인라인코드 제거 후 검사)
  3) 코드펜스(```) 짝 불균형
이슈가 있으면 exit 2 + stderr로 Claude에 경고(자동 수정은 안 함). 정상이면 조용히 exit 0.
모든 예외는 silent-fail(exit 0). stdlib only."""
import json, sys, os, re, glob

fp = ""
try:
    data = json.load(sys.stdin)
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path") or ti.get("path") or ""
except Exception:
    sys.exit(0)

norm = fp.replace("\\", "/")

# 대상 필터 1: .md 파일이며 메커니즘 디렉터리(.claude/.agents/.codex/.obsidian/.space/.git)가
# 아닌 콘텐츠 노트만. 제외 집합은 배치 린터 kb-lint.py의 EXCLUDE_DIR_NAMES와 일치시킨다
# (.agents 는 .claude 와 마찬가지로 메커니즘 — 스킬/에이전트 정의 SKILL.md, frontmatter가 name/description).
if not fp or not norm.endswith(".md"):
    sys.exit(0)
if any(seg in norm for seg in ("/.claude/", "/.agents/", "/.codex/", "/.obsidian/", "/.space/", "/.git/", "/.trash/")):
    sys.exit(0)
if not os.path.isfile(fp):
    sys.exit(0)

# vault root 역산: CLAUDE_PROJECT_DIR env 우선, 없으면 파일의 부모를 거슬러 .git 디렉터리 탐색.
# cwd에 의존하지 않아 Bash cwd가 vault 밖으로 이동해도 견고하다(빈 glob 오탐 방지).
def find_vault_root(path):
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent

vault_root = find_vault_root(fp)
if not vault_root:
    sys.exit(0)  # root 역산 실패 시 — 빈 glob 오탐 방지

# 대상 필터 2: 편집된 파일이 vault root 아래여야 한다(밖이면 스킵).
abs_fp = os.path.abspath(fp)
root_prefix = os.path.abspath(vault_root) + os.sep
if not abs_fp.startswith(root_prefix):
    sys.exit(0)

# 대상 필터 3: 루트 직속 .md(README.md·CLAUDE.md 등 프로젝트 메타 문서)는 KB 노트가 아니므로 제외.
# KB 노트는 항상 <Topic>/ 서브디렉터리 안에 있다(vault-rules: topic dir 패턴). 배치 린터 kb-lint.py 와 일치.
if os.path.dirname(abs_fp) == os.path.abspath(vault_root):
    sys.exit(0)

try:
    with open(fp, encoding="utf-8") as f:
        content = f.read()
except Exception:
    sys.exit(0)

warnings = []

# 1) 프론트매터 필수 필드
m = re.match(r"^---\n(.*?)\n---", content, re.S)
if not m:
    warnings.append("프론트매터(---) 블록 없음")
else:
    fm = m.group(1)
    required = ("title", "updated", "sources")
    try:
        with open(os.path.join(vault_root, ".claude", "kb-required-fields.txt"), encoding="utf-8") as sf:
            loaded = [ln.strip() for ln in sf if ln.strip() and not ln.lstrip().startswith("#")]
        if loaded:
            required = loaded
    except Exception:
        pass
    # type: moc 노트는 sources 면제 — MOC는 원본을 가리키지 않는 허브.
    # 배치 린터 kb-lint.py(is_moc 로직)와 동일하게 맞춘다.
    tm = re.search(r"^type:\s*(.+)$", fm, re.M)
    is_moc = bool(tm) and tm.group(1).strip().strip("'\"") == "moc"
    for field in required:
        if field == "sources" and is_moc:
            continue
        if not re.search(rf"^{re.escape(field)}:", fm, re.M):
            warnings.append(f"프론트매터 필수 필드 누락: {field}")

# 2) 끊긴 [[위키링크]] — 코드펜스(```...```)·인라인코드(`...`) 제거 후 검사(코드 속 [[..]] 오탐 방지).
stripped = re.sub(r"```.*?```", "", content, flags=re.S)
stripped = re.sub(r"`[^`\n]*`", "", stripped)
# vault 전체 .md 파일명(확장자 제거) 집합. 메커니즘 디렉터리는 제외.
pages = set()
for p in glob.glob(os.path.join(vault_root, "**", "*.md"), recursive=True):
    pn = p.replace("\\", "/")
    if any(seg in pn for seg in ("/.claude/", "/.agents/", "/.codex/", "/.obsidian/", "/.space/", "/.git/", "/.trash/")):
        continue
    pages.add(os.path.splitext(os.path.basename(p))[0])
for raw in re.findall(r"\[\[([^\]]+)\]\]", stripped):
    target = raw.split("|")[0].split("#")[0].strip()
    if target and target not in pages:
        warnings.append(f"끊긴 위키링크: [[{target}]]")

# 3) 코드펜스 균형 — 줄 시작의 ``` 펜스 개수가 홀수면 닫히지 않은 것.
fences = re.findall(r"^\s*```", content, re.M)
if len(fences) % 2 != 0:
    warnings.append("코드펜스(```) 짝 불균형 — 닫히지 않은 블록 가능성")

if warnings:
    rel = os.path.relpath(abs_fp, vault_root)
    sys.stderr.write(
        "⚠️ KB 노트 점검 — " + rel + ":\n  - " + "\n  - ".join(dict.fromkeys(warnings)) + "\n"
    )
    sys.exit(2)  # PostToolUse: stderr를 Claude에 피드백(비차단 경고)

sys.exit(0)
