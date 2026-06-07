#!/usr/bin/env python3
"""PostToolUse hook — 방금 Write/Edit한 파일에 credential이 박제됐는지 즉시 경고(비차단).

sources/는 불변이라 토큰이 박히면 영구 노출 → scrub-secrets로 ingest 단계에서 예방하되,
놓친 것을 2차로 탐지(capture·wiki-lint-check와 같은 즉시-피드백 루프). 발견 시 exit 2 + stderr.
자동 수정은 안 한다(오탐 시 원본 훼손 방지) — 사람이 scrub-secrets로 처리. scrub-secrets.py 코어 재사용.
어떤 실패도 세션을 막지 않는다 — 항상 exit 0/2."""
import json, sys, os, importlib.util

TEXT_EXT = (".md", ".txt", ".json", ".yaml", ".yml", ".py", ".sh",
            ".js", ".ts", ".env", ".cfg", ".ini", ".toml")

fp = ""
try:
    data = json.load(sys.stdin)
    ti = data.get("tool_input") or {}
    fp = ti.get("file_path") or ti.get("path") or ""
except Exception:
    sys.exit(0)

if not fp or not fp.lower().endswith(TEXT_EXT) or not os.path.isfile(fp):
    sys.exit(0)

# 자기경고 방지: 테스트 픽스처(.claude/tests/)와 secret 도구 자신은 패턴을 *데이터로* 보유.
# 이들을 검사하면 편집할 때마다 가짜 경고(nag loop)가 뜬다.
_norm = fp.replace("\\", "/")
if "/.claude/tests/" in _norm or os.path.basename(fp) in ("scrub-secrets.py", "secret-scan.py"):
    sys.exit(0)

try:
    with open(fp, encoding="utf-8") as f:
        text = f.read()
except Exception:
    sys.exit(0)

# scrub-secrets 코어 로드: hooks/secret-scan.py → ../scrub-secrets.py
core = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scrub-secrets.py")
try:
    spec = importlib.util.spec_from_file_location("scrub_secrets", core)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    hits = mod.find_secrets(text)
except Exception:
    sys.exit(0)  # 코어 부재/오류 시 조용히 통과(세션 비차단)

if hits:
    names = ", ".join(sorted({n for n, _, _, _ in hits}))
    sys.stderr.write(
        f"⚠ credential 의심 — {fp}\n"
        f"  {len(hits)}건 ({names})\n"
        f"  실 토큰이면: `python3 .claude/scrub-secrets.py \"{fp}\"`로 마스킹 후 제공자(GitHub 등)에서 폐기·교체.\n"
        f"  sources/는 불변이라 커밋 전 처리 필수. (오탐이면 무시)\n"
    )
    sys.exit(2)  # PostToolUse: stderr를 Claude에 피드백(비차단 경고)

sys.exit(0)
