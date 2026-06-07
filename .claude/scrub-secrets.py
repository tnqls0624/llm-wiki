#!/usr/bin/env python3
"""scrub-secrets — 텍스트/파일에서 credential 패턴을 탐지·마스킹.

왜: ingest가 외부 자료를 sources/(불변)에 박제하기 전에 토큰/키가 영구 노출되는 것을 막는다.
sources/는 한 번 캡처하면 수정 금지(protect-sources 훅) → secret이 박히면 git 히스토리까지 영구.
import 가능(find_secrets/scrub) + CLI. PostToolUse 훅 hooks/secret-scan.py가 이 코어를 재사용.

보수적 설계: prefix가 명확한 **고신뢰 패턴만** 마스킹하고, 코드 예제의 placeholder
(YOUR_KEY·sk-xxx·<token> 등)는 제외해 오탐을 최소화한다. 일반 `api_key=...` 같은
저신뢰 패턴은 다루지 않는다(외부 지식 자료엔 정상적 예제가 흔하므로).

CLI:
  python3 scrub-secrets.py <file>...        # 인플레이스 마스킹 + 리포트(발견 시 exit 1)
  python3 scrub-secrets.py --check <file>   # 탐지만(수정 안 함), 발견 시 exit 1
  echo "..." | python3 scrub-secrets.py      # stdin → 마스킹본 stdout
"""
import re, sys

# (name, regex, group) — group=0 전체 매칭 마스킹, >0 해당 캡처그룹만(예: URL의 password)
SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"), 0),
    ("github-pat", re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), 0),
    ("github-fine-pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b"), 0),
    ("github-oauth", re.compile(r"\bgh[ousr]_[A-Za-z0-9]{36}\b"), 0),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), 0),
    ("openai-key", re.compile(r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{20,}"), 0),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), 0),
    ("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}"), 0),
    ("stripe-key", re.compile(r"\b[sr]k_live_[0-9a-zA-Z]{24,}\b"), 0),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), 0),
    ("url-password", re.compile(r"://[^/\s:@]+:([^/\s:@]{3,})@"), 1),
]

# 명백한 더미/예시 — 이게 매칭 전체에 있으면 실 secret 아님으로 보고 건너뛴다(오탐 방지)
PLACEHOLDER = re.compile(
    r"(?i)(x{4,}|y{4,}|z{4,}|your[_-]|example|sample|redacted|placeholder|dummy|"
    r"\.\.\.|<[^>]*>|abc123|0{6,}|123456|test[_-]?(?:key|token|secret)|my[_-]?(?:key|token|secret))")


def _is_placeholder(s):
    return bool(PLACEHOLDER.search(s))


def find_secrets(text):
    """실제 secret으로 보이는 매칭만 반환: [(name, secret_str, start, end)] (겹침 미제거)."""
    found = []
    for name, rx, grp in SECRET_PATTERNS:
        for m in rx.finditer(text):
            if grp > m.re.groups:
                continue
            s = m.group(grp)
            if not s or _is_placeholder(m.group(0)):
                continue
            found.append((name, s, m.start(grp), m.end(grp)))
    return found


def scrub(text):
    """secret을 <REDACTED:name>으로 치환. (scrubbed, [(name, preview)]) 반환."""
    hits = find_secrets(text)
    if not hits:
        return text, []
    # 겹치는 매칭 제거(예: sk-ant-가 openai 패턴에도 잡히는 경우) — 시작 위치순, 먼저 잡은 영역 우선
    hits.sort(key=lambda x: (x[2], -x[3]))
    dedup, last_end = [], -1
    for h in hits:
        if h[2] >= last_end:
            dedup.append(h)
            last_end = h[3]
    report = []
    for name, s, a, b in sorted(dedup, key=lambda x: x[2], reverse=True):  # 뒤에서부터(인덱스 보존)
        preview = s[:4] + "…" if len(s) > 4 else "…"
        text = text[:a] + f"<REDACTED:{name}>" + text[b:]
        report.append((name, preview))
    return text, list(reversed(report))


def _main(argv):
    check = "--check" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:  # stdin 모드
        scrubbed, rep = scrub(sys.stdin.read())
        if not check:
            sys.stdout.write(scrubbed)
        for n, p in rep:
            sys.stderr.write(f"secret: {n} ({p})\n")
        return 1 if rep else 0
    rc = 0
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                data = f.read()
        except Exception:
            continue
        scrubbed, rep = scrub(data)
        if rep:
            rc = 1
            sys.stderr.write(f"⚠ {fp}: credential {len(rep)}건 발견 — "
                             + ", ".join(f"{n}({p})" for n, p in rep) + "\n")
            if not check:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(scrubbed)
                sys.stderr.write("  → <REDACTED:...>로 마스킹 완료. 원본의 실 토큰은 제공자에서 폐기·교체 권장.\n")
    return rc


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
