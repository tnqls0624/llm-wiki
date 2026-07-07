#!/usr/bin/env python3
"""블로그 초안의 웹 참조 이미지를 다운로드해 blog/<slug>/ 에 번호 파일로 저장 (0-LLM, 결정론적).

soobeen-voice 에이전트가 초안 본문에 `[사진 N]` 번호 플레이스홀더를 두고, 맨 끝
'이미지 계획' 빌드 섹션에 각 사진의 메타를 emit하면, 이 스크립트가:
  1) 본문 `[사진 N]` ↔ 계획 번호 1:1 대응 검증(어긋나면 loud fail, exit 4)
  2) kind=web + URL 인 항목을 다운로드해 <outdir>/`N. name.ext` 로 저장
     (content-type image/* + 10MB cap + http/https + 사설·로컬 호스트 차단)
  3) SOURCES.md 에 번호·파일명·종류·출처·라이선스·상태 기록(저작권 판단 근거)
  4) 빌드 섹션을 떼어낸 '발행용 본문' 출력
  5) kind=shot(직접 촬영) / URL 없는 web 는 '대기'로 보고(정상 — 사용자 몫)

설계 — automation-safety 준수:
- stdlib만. LLM 판단 없음. 어떤 이미지가 맞는지 '검색'은 메인 세션(대화형)이 하고,
  이 스크립트는 결정된 URL을 받아 다운로드·검증·정리만 한다.
- 파일 생성은 메인 세션이 실행. soobeen-voice(draft-only, Write 없음)는 실행하지 않는다. cron 연결 금지.
- silent-fail 금지: 플레이스홀더/계획 불일치는 nonzero exit. 다운로드 실패·차단 URL은 loud warning + SOURCES.md 기록.
- 저작권: 다운로드분의 출처·라이선스를 SOURCES.md에 남겨 사용자가 재게시 여부를 판단하게 한다.

입력 초안 포맷:
  본문:  > 🖼️ **[사진 N]** 캡션 / > → 업로드: `N. name.png`   ← [사진 N] 만 검증에 씀
  빌드 섹션 시작 센티넬(이 줄부터 아래는 발행 본문에서 제거됨):
      <!-- BLOG-IMAGES (blog-collect.py가 이 아래를 떼어냄) -->
  이미지 계획 한 줄씩 (필드 구분 `|`, URL·출처는 web 에서만, 메인 세션이 검색 후 채움):
      <!-- IMG: N | name | web  | 설명 | https://…/fig.png | 출처, 라이선스 -->
      <!-- IMG: N | name | shot | 설명 -->

사용: blog-collect.py DRAFT.md [옵션]
  --outdir DIR        저장 위치 (기본: <vault>/blog/<초안파일stem>/)
  --in-place          초안 파일을 발행 본문으로 덮어씀(이미지·SOURCES는 outdir에)
  --check             검증만: 파싱 + 플레이스홀더 대응 확인, 네트워크·파일 IO 없음
  --allow-local-hosts SSRF 가드 해제(테스트 전용 — 로컬 http 서버 대상)
  --timeout SEC       다운로드 타임아웃 (기본 20)
  -q / --quiet
종료코드: 0 ok · 2 usage · 4 플레이스홀더/계획 불일치
"""
import argparse, ipaddress, os, re, socket, sys
from urllib.parse import urlparse

BUILD_SENTINEL_RE = re.compile(r"^<!--\s*BLOG-IMAGES\b.*?-->\s*$", re.M)
IMG_RE = re.compile(r"<!--\s*IMG:\s*(?P<inner>.+?)\s*-->", re.S)
PLACEHOLDER_RE = re.compile(r"\[\s*사진\s*(?P<n>\d+)\s*\]")
CT_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg",
          "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg",
          "image/bmp": ".bmp"}
MAX_BYTES = 10 * 1024 * 1024


def log(msg, quiet=False):
    if not quiet:
        print(msg)


def find_vault_root():
    """이 스크립트는 <vault>/.claude/blog-collect.py 에 산다 → 부모의 부모가 vault root."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


# ── 파싱 ──────────────────────────────────────────────────────────────
def split_build(text):
    """(발행 본문, 빌드 섹션). 센티넬 없으면 빌드 섹션은 ''."""
    m = BUILD_SENTINEL_RE.search(text)
    if not m:
        return text.rstrip() + "\n", ""
    return text[:m.start()].rstrip() + "\n", text[m.end():]


def parse_plan(build):
    """빌드 섹션 → [{n,name,kind,desc,url,note}] (번호 오름차순). 파싱 못 한 줄은 problems에."""
    plan, problems = [], []
    for m in IMG_RE.finditer(build):
        parts = [p.strip() for p in m.group("inner").split("|")]
        if len(parts) < 3:
            problems.append(f"IMG 줄 필드 부족(최소 N|name|kind): {m.group('inner')!r}")
            continue
        n_raw, name, kind = parts[0], parts[1], parts[2].lower()
        if not n_raw.isdigit():
            problems.append(f"IMG 번호가 숫자 아님: {n_raw!r}")
            continue
        if kind not in ("web", "shot"):
            problems.append(f"IMG kind 는 web|shot 여야: {kind!r} (#{n_raw})")
            continue
        plan.append({
            "n": int(n_raw), "name": name, "kind": kind,
            "desc": parts[3] if len(parts) > 3 else "",
            "url": parts[4] if len(parts) > 4 and parts[4] else "",
            "note": parts[5] if len(parts) > 5 else "",
        })
    plan.sort(key=lambda x: x["n"])
    return plan, problems


def check_correspondence(body, plan):
    """본문 [사진 N] 과 계획 번호가 1..K 로 빈틈없이 1:1 대응하는지. 문제 목록 반환(빈 = ok)."""
    problems = []
    body_nums = sorted({int(m.group("n")) for m in PLACEHOLDER_RE.finditer(body)})
    plan_nums = [p["n"] for p in plan]
    if len(plan_nums) != len(set(plan_nums)):
        dup = sorted({n for n in plan_nums if plan_nums.count(n) > 1})
        problems.append(f"계획에 중복 번호: {dup}")
    plan_set = set(plan_nums)
    if plan_set:
        expected = set(range(1, max(plan_set) + 1))
        missing = sorted(expected - plan_set)
        if missing:
            problems.append(f"계획 번호가 1부터 연속이 아님 — 빠진 번호: {missing}")
    for n in body_nums:
        if n not in plan_set:
            problems.append(f"본문 [사진 {n}] 에 대응하는 IMG 계획 줄이 없음")
    for n in sorted(plan_set):
        if n not in body_nums:
            problems.append(f"IMG 계획 #{n} 이 본문 [사진 {n}] 로 등장하지 않음(고아 계획)")
    return problems


# ── 다운로드 (SSRF 가드 + 검증) ───────────────────────────────────────
def safe_url(url, allow_local=False):
    """(ok, 이유). http/https + 공인 호스트만 허용(defense-in-depth; URL은 메인 세션 검색분)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return False, "http/https 스킴 아님"
    host = p.hostname
    if not host:
        return False, "호스트 없음"
    if allow_local:
        return True, ""
    if host == "localhost" or host.endswith(".local"):
        return False, "로컬 호스트"
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception as e:
        return False, f"DNS 해석 실패({e})"
    for res in infos:
        try:
            ip = ipaddress.ip_address(res[4][0])
        except ValueError:
            continue
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False, f"사설·로컬 IP({ip})"
    return True, ""


def download(url, dest_stem, timeout, allow_local=False):
    """이미지 다운로드 → dest_stem+ext 저장. (ext, err) — err None 이면 성공."""
    ok, why = safe_url(url, allow_local)
    if not ok:
        return None, f"차단된 URL — {why}"
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "blog-collect/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if not ct.startswith("image/"):
                return None, f"이미지 아님(Content-Type={ct or '없음'})"
            data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return None, f"10MB 초과"
        if not data:
            return None, "빈 응답"
        ext = CT_EXT.get(ct, ".img")
        os.makedirs(os.path.dirname(dest_stem), exist_ok=True)
        with open(dest_stem + ext, "wb") as f:
            f.write(data)
        return ext, None
    except Exception as e:
        return None, f"다운로드 실패({e})"


# ── SOURCES.md ─────────────────────────────────────────────────────────
def write_sources(outdir, rows):
    """rows: [{n,name,kind,url,note,status,file}] → SOURCES.md (저작권 판단 근거)."""
    sp = os.path.join(outdir, "SOURCES.md")
    with open(sp, "w", encoding="utf-8") as fh:
        fh.write("# 이미지 출처 · 라이선스\n\n")
        fh.write("> 웹 수집 이미지는 저작권이 있을 수 있음 — 재게시 전 아래 출처·라이선스를 확인하세요.\n\n")
        for r in sorted(rows, key=lambda x: x["n"]):
            src = f"[{r['url']}]({r['url']})" if r["url"] else "—"
            note = r["note"] or ("직접 촬영" if r["kind"] == "shot" else "표기 없음")
            fh.write(f"- **[사진 {r['n']}]** `{r['file']}` · {r['kind']} · {r['status']}\n")
            fh.write(f"  - 출처: {src}\n  - 라이선스/표기: {note}\n")
    return sp


# ── 메인 ──────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description="블로그 초안 웹 이미지 수집·저장")
    ap.add_argument("draft", help="초안 markdown 경로")
    ap.add_argument("--outdir", help="저장 위치 (기본: <vault>/blog/<초안stem>/)")
    ap.add_argument("--in-place", action="store_true", help="초안을 발행 본문으로 덮어씀")
    ap.add_argument("--check", action="store_true", help="검증만(네트워크·파일 IO 없음)")
    ap.add_argument("--allow-local-hosts", action="store_true", help="SSRF 가드 해제(테스트 전용)")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args(argv)

    if not os.path.isfile(a.draft):
        print(f"error: 초안 없음: {a.draft}", file=sys.stderr)
        return 2
    stem = os.path.splitext(os.path.basename(a.draft))[0]
    outdir = a.outdir or os.path.join(find_vault_root(), "blog", stem)

    text = open(a.draft, encoding="utf-8").read()
    body, build = split_build(text)
    plan, parse_problems = parse_plan(build)

    # 1) 구조 검증 — 파싱 실패 or 플레이스홀더/계획 불일치 → loud fail
    problems = parse_problems + check_correspondence(body, plan)
    if problems:
        print("이미지 계획 검증 실패 (파일 미생성):", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        return 4

    if a.check:
        webs = [p for p in plan if p["kind"] == "web"]
        shots = [p for p in plan if p["kind"] == "shot"]
        log(f"check ok: 계획 {len(plan)}개 (web {len(webs)} / shot {len(shots)}), "
            f"본문 플레이스홀더 대응 OK", a.quiet)
        return 0

    os.makedirs(outdir, exist_ok=True)

    # 2) 다운로드 + 상태 집계
    rows, warnings, n_dl, n_pending = [], [], 0, 0
    for p in plan:
        fname_base = f"{p['n']}. {p['name']}"
        dest_stem = os.path.join(outdir, fname_base)
        if p["kind"] == "web" and p["url"]:
            ext, err = download(p["url"], dest_stem, a.timeout, a.allow_local_hosts)
            if err:
                warnings.append(f"[사진 {p['n']}] {p['url']} → {err} (대기로 기록)")
                rows.append({**p, "status": f"다운로드 실패({err})", "file": fname_base + ".png"})
                n_pending += 1
            else:
                n_dl += 1
                rows.append({**p, "status": "다운로드됨", "file": fname_base + ext})
        else:  # shot 또는 URL 없는 web → 사용자가 직접 준비
            reason = "직접 촬영" if p["kind"] == "shot" else "URL 미지정(검색 필요)"
            rows.append({**p, "status": f"대기({reason})", "file": fname_base + ".png"})
            n_pending += 1

    # 3) SOURCES.md
    write_sources(outdir, rows)

    # 4) 발행 본문 출력(빌드 섹션 제거)
    if a.in_place:
        out_path = a.draft
    else:
        out_path = os.path.join(outdir, stem + ".blog.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(body if body.endswith("\n") else body + "\n")

    log(f"✓ 저장 위치: {outdir}", a.quiet)
    log(f"  다운로드 {n_dl}개 · 대기(직접 준비) {n_pending}개 · 발행 본문: {out_path}", a.quiet)
    if n_pending:
        log("  ▸ 대기 목록(직접 촬영/업로드 필요):", a.quiet)
        for r in rows:
            if r["status"].startswith("대기") or r["status"].startswith("다운로드 실패"):
                log(f"    - [사진 {r['n']}] {r['file']} — {r['desc'] or r['name']}", a.quiet)
    for w in warnings:
        log("  ⚠ " + w, a.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
