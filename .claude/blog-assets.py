#!/usr/bin/env python3
"""블로그 초안의 도식/이미지를 실제 파일로 materialize (0-LLM, 결정론적).

soobeen-voice 에이전트가 초안 프로즈 + '빌드 섹션'(개념 다이어그램 SVG 소스 + 원본
이미지 인용)을 텍스트로 emit하면, 이 스크립트가 그 텍스트를 받아:
  1) SVG 소스 → 실제 .svg 파일 write + XML well-formed 검증(깨지면 loud fail)
  2) SVG → PNG 래스터화(Tistory 업로드 호환: cairosvg→rsvg-convert→Chrome→qlmanage)
  3) 본문의 ![](assets/…) 참조 경로를 실제 생성 포맷으로 정규화
  4) 원본 이미지 인용은 저작권 안전을 위해 기본 '출처 링크'로 변환(+SOURCES.md 기록),
     --fetch-sources 일 때만 실제 다운로드해 임베드
  5) 빌드 섹션을 떼어낸 '발행용 본문'을 출력

설계 — automation-safety 준수:
- stdlib(+선택적 Pillow)만 사용. LLM 판단 없음 — 파싱·검증·파일 IO만.
- 파일 생성은 **메인 세션(대화형)이 실행**한다. soobeen-voice(draft-only, Write/Edit 없음)는
  이 스크립트를 실행하지 않는다 — 초안 텍스트만 emit. cron에도 연결하지 않는다.
- silent-fail 금지: SVG 파싱 실패·미해결 참조는 nonzero exit로 loud 하게 알린다.

입력 초안 포맷:
  본문: ![캡션](assets/<slug>/NN-name.png)  ← 아무 확장자나 무방, 스크립트가 정규화
  빌드 섹션 시작 센티넬(이 줄부터 아래는 발행 본문에서 제거됨):
      <!-- BLOG-ASSETS BUILD (blog-assets.py가 이 아래를 떼어냄) -->
  개념 다이어그램:
      <!-- FIGURE: assets/<slug>/NN-name -->      (확장자 없는 relpath stem)
      ```svg
      <svg xmlns="http://www.w3.org/2000/svg" ...>...</svg>
      ```
  원본 이미지 인용:
      <!-- SOURCE-IMAGE: assets/<slug>/NN-name | <url> | <출처/라이선스 표기> -->

사용: blog-assets.py DRAFT.md [옵션]
  --outdir DIR        발행 본문+assets 출력 위치 (기본: DRAFT.md 옆)
  --in-place          DRAFT.md 자체를 발행 본문으로 덮어씀(assets는 그 디렉토리에)
  --raster {auto,none}  auto=SVG→PNG 래스터화(기본), none=SVG만 유지
  --scale N           래스터 device scale (기본 2 = 레티나)
  --fetch-sources     SOURCE-IMAGE URL을 실제 다운로드(기본: 링크 인용만, 저작권 안전)
  --check             검증만: 파싱+SVG well-formed+참조 해결 확인, 파일 미생성, 문제 시 nonzero
  -q / --quiet
종료코드: 0 ok · 2 usage · 3 SVG malformed · 4 미해결 참조
"""
import argparse, os, re, sys, shutil, subprocess, tempfile
from xml.dom import minidom

BUILD_SENTINEL_RE = re.compile(r"^<!--\s*BLOG-ASSETS BUILD\b.*?-->\s*$", re.M)
FIGURE_RE = re.compile(
    r"<!--\s*FIGURE:\s*(?P<stem>[^\s>]+)\s*-->\s*```svg\s*(?P<svg>.*?)```",
    re.S,
)
SOURCE_RE = re.compile(
    r"<!--\s*SOURCE-IMAGE:\s*(?P<stem>[^|]+?)\s*\|\s*(?P<url>[^|]+?)\s*(?:\|\s*(?P<note>.*?))?\s*-->",
    re.S,
)
# 본문 이미지 참조: ![cap](path)  — path 는 assets/ 로 시작하는 로컬 경로만 취급
IMG_REF_RE = re.compile(r"!\[(?P<cap>[^\]]*)\]\((?P<path>assets/[^)\s]+)\)")
RASTER_EXTS = (".png", ".svg", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


def log(msg, quiet=False):
    if not quiet:
        print(msg)


# ── 래스터라이저 (첫 번째로 되는 것 사용) ─────────────────────────────
def _svg_dims(svg_path):
    """SVG width/height(px) 추정. 없으면 viewBox, 그것도 없으면 (640,400)."""
    try:
        doc = minidom.parse(svg_path)
        el = doc.documentElement

        def num(v):
            m = re.match(r"^\s*([\d.]+)", v or "")
            return float(m.group(1)) if m else None

        w, h = num(el.getAttribute("width")), num(el.getAttribute("height"))
        if not (w and h):
            vb = el.getAttribute("viewBox").split()
            if len(vb) == 4:
                w, h = float(vb[2]), float(vb[3])
        return int(round(w or 640)), int(round(h or 400))
    except Exception:
        return 640, 400


def _rasterize(svg_path, png_path, scale):
    """SVG→PNG. 성공 시 png_path 반환, 전부 실패하면 None. 우선순위: 품질/무설정 순."""
    # 1) cairosvg (정확, 서브프로세스 없음)
    try:
        import cairosvg  # noqa
        cairosvg.svg2png(url=svg_path, write_to=png_path, scale=scale)
        return png_path if os.path.getsize(png_path) else None
    except Exception:
        pass
    # 2) rsvg-convert
    if shutil.which("rsvg-convert"):
        try:
            subprocess.run(["rsvg-convert", "-z", str(scale), "-o", png_path, svg_path],
                           check=True, capture_output=True)
            if os.path.exists(png_path) and os.path.getsize(png_path):
                return png_path
        except Exception:
            pass
    # 3) Chrome headless (종횡비 보존 + 레티나) — HTML 래퍼로 정확한 window-size 렌더
    chrome = _find_chrome()
    if chrome:
        try:
            w, h = _svg_dims(svg_path)
            with tempfile.TemporaryDirectory() as td:
                svg_copy = os.path.join(td, "f.svg")
                shutil.copy(svg_path, svg_copy)
                html = os.path.join(td, "wrap.html")
                with open(html, "w", encoding="utf-8") as f:
                    f.write('<!doctype html><meta charset="utf-8">'
                            '<body style="margin:0;padding:0">'
                            f'<img src="f.svg" width="{w}" height="{h}" style="display:block"></body>')
                subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                                f"--force-device-scale-factor={scale}",
                                "--default-background-color=FFFFFFFF",
                                f"--screenshot={png_path}", f"--window-size={w},{h}",
                                f"file://{html}"], check=True, capture_output=True, timeout=60)
            if os.path.exists(png_path) and os.path.getsize(png_path):
                return png_path
        except Exception:
            pass
    # 4) qlmanage (macOS 내장) — 정사각 패딩 → Pillow 있으면 종횡비대로 크롭
    if shutil.which("qlmanage"):
        try:
            w, h = _svg_dims(svg_path)
            size = int(round(max(w, h) * scale))
            with tempfile.TemporaryDirectory() as td:
                subprocess.run(["qlmanage", "-t", "-s", str(size), "-o", td, svg_path],
                               check=True, capture_output=True, timeout=60)
                thumb = os.path.join(td, os.path.basename(svg_path) + ".png")
                if os.path.exists(thumb):
                    _crop_topleft(thumb, png_path, int(round(w * scale)), int(round(h * scale)))
                    if os.path.exists(png_path) and os.path.getsize(png_path):
                        return png_path
        except Exception:
            pass
    return None


def _crop_topleft(src, dst, w, h):
    """qlmanage 정사각 출력을 좌상단 (w,h)로 크롭. Pillow 없으면 원본 복사."""
    try:
        from PIL import Image
        im = Image.open(src)
        w, h = min(w, im.width), min(h, im.height)
        im.crop((0, 0, w, h)).save(dst)
    except Exception:
        shutil.copy(src, dst)


def _find_chrome():
    for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium"):
        if os.path.exists(c):
            return c
    return shutil.which("google-chrome") or shutil.which("chromium")


# ── 파싱 / 검증 ───────────────────────────────────────────────────────
def split_build(text):
    """(발행 본문, 빌드 섹션). 센티넬 없으면 빌드 섹션은 ''."""
    m = BUILD_SENTINEL_RE.search(text)
    if not m:
        return text.rstrip() + "\n", ""
    return text[:m.start()].rstrip() + "\n", text[m.end():]


def stem_of(path):
    """assets/…/NN-name.ext → assets/…/NN-name (확장자 제거)."""
    for e in RASTER_EXTS:
        if path.lower().endswith(e):
            return path[: -len(e)]
    return path


def validate_svg(svg_text, stem):
    """well-formed 아니면 (False, 이유). <svg 루트 아니면도 거부."""
    try:
        doc = minidom.parseString(svg_text.strip().encode("utf-8"))
    except Exception as e:
        return False, f"{stem}: SVG XML 파싱 실패 — {e}"
    if doc.documentElement.tagName.lower() != "svg":
        return False, f"{stem}: 루트 엘리먼트가 <svg> 가 아님 ({doc.documentElement.tagName})"
    return True, ""


# ── 메인 ──────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description="블로그 초안 도식/이미지 materialize")
    ap.add_argument("draft", help="초안 markdown 경로")
    ap.add_argument("--outdir", help="출력 위치 (기본: 초안 옆)")
    ap.add_argument("--in-place", action="store_true", help="초안 파일을 발행 본문으로 덮어씀")
    ap.add_argument("--raster", choices=["auto", "none"], default="auto")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--fetch-sources", action="store_true", help="원본 이미지 실제 다운로드(기본: 인용만)")
    ap.add_argument("--check", action="store_true", help="검증만, 파일 미생성")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args(argv)

    if not os.path.isfile(a.draft):
        print(f"error: 초안 없음: {a.draft}", file=sys.stderr)
        return 2
    outdir = a.outdir or os.path.dirname(os.path.abspath(a.draft))
    text = open(a.draft, encoding="utf-8").read()
    body, build = split_build(text)

    figures = list(FIGURE_RE.finditer(build))
    sources = list(SOURCE_RE.finditer(build))

    # 1) SVG well-formed 선검증 (쓰기 전에 전부) — 하나라도 깨지면 loud fail
    problems = []
    for f in figures:
        ok, why = validate_svg(f.group("svg"), f.group("stem").strip())
        if not ok:
            problems.append(why)
    if problems:
        print("SVG 검증 실패 (파일 미생성):", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        return 3

    # 매핑: figure stem → materialized ext(.png or .svg) ; source stem → (url, note)
    fig_ext, warnings = {}, []
    source_map = {s.group("stem").strip(): (s.group("url").strip(),
                  (s.group("note") or "").strip()) for s in sources}

    if not a.check:
        os.makedirs(outdir, exist_ok=True)

    # 2) 다이어그램 write + 래스터화
    for f in figures:
        stem = f.group("stem").strip()
        svg_text = f.group("svg").strip()
        svg_rel = stem + ".svg"
        materialized = ".svg"
        if not a.check:
            svg_abs = os.path.join(outdir, svg_rel)
            os.makedirs(os.path.dirname(svg_abs), exist_ok=True)
            with open(svg_abs, "w", encoding="utf-8") as fh:
                fh.write(svg_text + "\n")
            if a.raster == "auto":
                png_abs = os.path.join(outdir, stem + ".png")
                if _rasterize(svg_abs, png_abs, a.scale):
                    materialized = ".png"
                else:
                    warnings.append(f"{stem}: 래스터라이저 없음 → SVG로 유지(.svg 참조). "
                                    "Tistory가 SVG 업로드를 거부하면 PNG로 변환 필요.")
        fig_ext[stem] = materialized

    # 3) 원본 이미지: 인용(기본) 또는 다운로드
    fetched = {}
    if a.fetch_sources:
        for stem, (url, note) in source_map.items():
            ext, ok = _fetch_image(url, os.path.join(outdir, stem), a.check)
            if ok:
                fetched[stem] = ext
            else:
                warnings.append(f"{stem}: 다운로드 실패 → 링크 인용으로 유지 ({url})")

    # 4) 본문 참조 정규화 + 미해결 검출
    unresolved = []

    def rewrite(m):
        cap, path = m.group("cap"), m.group("path")
        stem = stem_of(path)
        if stem in fig_ext:                              # 다이어그램
            return f"![{cap}]({stem + fig_ext[stem]})"
        if stem in fetched:                              # 다운로드된 원본
            return f"![{cap}]({stem + fetched[stem]})"
        if stem in source_map:                           # 인용(다운로드 안 함) → 링크로
            url, note = source_map[stem]
            tail = f" — {note}" if note else ""
            return f"> 📎 참고 그림: [{cap or '원본 자료'}]({url}) (출처 표기{tail}; 직접 업로드 권장)"
        # 선언 안 된 로컬 참조 → 실제 파일 있으면 ok, 없으면 미해결
        if os.path.exists(os.path.join(outdir, path)):
            return m.group(0)
        unresolved.append(path)
        return m.group(0)

    new_body = IMG_REF_RE.sub(rewrite, body)

    if unresolved:
        print("미해결 이미지 참조 (실제 파일 없음, FIGURE/SOURCE-IMAGE 선언도 없음):", file=sys.stderr)
        for u in sorted(set(unresolved)):
            print("  - " + u, file=sys.stderr)
        return 4

    if a.check:
        log(f"check ok: 다이어그램 {len(figures)}개 well-formed, "
            f"원본 인용 {len(source_map)}개, 미해결 참조 0", a.quiet)
        return 0

    # 5) SOURCES.md 인용 기록 (슬러그 디렉토리별)
    if source_map:
        for d in {os.path.dirname(s) for s in source_map}:
            sp = os.path.join(outdir, d, "SOURCES.md")
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            with open(sp, "w", encoding="utf-8") as fh:
                fh.write("# 원본 이미지 출처\n\n")
                for stem, (url, note) in source_map.items():
                    if os.path.dirname(stem) == d:
                        status = "다운로드됨" if stem in fetched else "인용(직접 업로드 권장)"
                        fh.write(f"- `{stem}` — [{url}]({url}) · {note or '표기 없음'} · {status}\n")

    # 6) 발행 본문 출력 (--in-place 아니면 입력 초안 덮어쓰기 방지)
    if a.in_place:
        out_path = a.draft
    else:
        out_path = os.path.join(outdir, os.path.basename(a.draft))
        if os.path.abspath(out_path) == os.path.abspath(a.draft):
            base, ext = os.path.splitext(os.path.basename(a.draft))
            out_path = os.path.join(outdir, base + ".blog" + ext)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(new_body if new_body.endswith("\n") else new_body + "\n")

    log(f"✓ 발행 본문: {out_path}", a.quiet)
    log(f"  다이어그램 {sum(1 for e in fig_ext.values() if e == '.png')}개 PNG"
        f" + {sum(1 for e in fig_ext.values() if e == '.svg')}개 SVG-only", a.quiet)
    log(f"  원본 이미지: 인용 {len(source_map) - len(fetched)}개 / 다운로드 {len(fetched)}개", a.quiet)
    for w in warnings:
        log("  ⚠ " + w, a.quiet)
    return 0


def _fetch_image(url, stem, check):
    """이미지 다운로드(content-type image/*, 10MB cap). (ext, ok) 반환."""
    if check:
        return "", False
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "blog-assets/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            ct = r.headers.get("Content-Type", "")
            if not ct.startswith("image/"):
                return "", False
            data = r.read(10 * 1024 * 1024 + 1)
            if len(data) > 10 * 1024 * 1024:
                return "", False
        ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
               "image/webp": ".webp", "image/svg+xml": ".svg"}.get(ct.split(";")[0].strip(), ".img")
        abs_path = stem + ext
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(data)
        return ext, True
    except Exception:
        return "", False


if __name__ == "__main__":
    sys.exit(main())
