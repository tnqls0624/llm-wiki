#!/usr/bin/env python3
"""claude-radar 수집 엔진 (0-LLM, 결정론적).

여러 공개 소스에서 'Claude Code 활용' 관련 신규 항목을 긁어와
seen ledger(.claude/runtime/radar-seen.json)로 중복을 제거하고
신규 항목만 JSON으로 stdout에 출력한다. /claude-radar 커맨드(collect 모드)가
이 출력을 받아 LLM 판단으로 분류·추천을 만들고 큐에 적재한다.

설계:
- stdlib만 사용(urllib/json/xml/re/datetime) — cron wrapper allowlist는 Bash(python3:*) 뿐.
- 각 소스는 독립 try/except — 한 소스 실패가 전체를 막지 않는다(errors[]에 기록).
- 출력과 동시에 seen ledger를 갱신(출력된 모든 key를 '봤음'으로 마킹) → 다음 실행에서 재출현 차단.
  --dry-run 이면 ledger를 건드리지 않는다(테스트/미리보기).
- 첫 실행(ledger 부재) = baseline: 현재 항목을 전부 seen에 기록만 하고 new_items는 비운다
  (kb-sync-cron의 baseline 사상과 동일 — 도입 시점 폭주 방지). 둘째 날부터 진짜 신규만.
- ledger는 prune: PRUNE_DAYS 초과분 제거, 그래도 PRUNE_MAX 초과면 최신 것만 유지.

검증된 소스(2026-06-08, 모두 curl/urllib + stdlib 파싱 가능):
  HN(Algolia) · GitHub releases.atom · GitHub topic search · awesome curation commits.atom
  · GeekNews rss/news · Anthropic platform release-notes · dev.to API · npm registry search
"""
import argparse, json, os, re, sys, time, datetime
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))            # .claude/
SEEN_PATH = os.path.join(ROOT, "runtime", "radar-seen.json")
ATOM = {"a": "http://www.w3.org/2005/Atom"}
# 일부 소스(dev.to)가 'bot' UA를 Cloudflare로 차단 → 일반 브라우저 UA 사용.
# 모두 공개 read 엔드포인트이고 하루 1회 호출이라 rate limit/ToS 무해.
UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Version/17.0 Safari/605.1.15")}
PRUNE_DAYS = 120
PRUNE_MAX = 3000
PER_SOURCE_CAP = 8     # 한 소스가 날짜순 정렬을 독식하지 못하게(다양성 보장)
ERRORS = []

# Claude Code 활용 신호 / 노이즈 필터 (제목+url 대상)
SIGNAL = re.compile(
    r"claude.?code|claude-code|mcp.server|mcp.tool|\bmcp\b|subagent|sub-agent|"
    r"slash.command|\.claude/|claude\.md|anthropic.sdk|claude.desktop|claude.api|"
    r"claude.skill|claude.agent|claude.plugin|agent.sdk",
    re.I,
)
NOISE = re.compile(
    r"s&p 500|spending problem|lawsuit|\bIPO\b|funding round|series [a-e]\b|"
    r"datacenter|water (use|utility)|valuation|stock",
    re.I,
)
# Anthropic release-notes overview.md 는 Claude Platform 전체를 다루므로 CC 관련 섹션만 추린다.
CC_CHANGELOG_RE = re.compile(r"claude code|claude\.com/docs|subagent|slash|/plugin|hook|skill", re.I)


def today():
    return datetime.date.today().isoformat()


def clean_text(s):
    """제어문자·개행을 공백으로, 연속 공백 축약 — 큐 헤더 위조/프롬프트 인젝션 라인 방지.
    외부 수집 텍스트(제목·설명)는 다운스트림에서 큐 헤더 → 부팅 컨텍스트로 흐르므로 출력 전 정제한다."""
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", s or "")).strip()


def iso_date(s):
    """'2026-06-08' 또는 'May 6, 2026' → 'YYYY-MM-DD'. 실패 시 ''(정렬 키를 ISO로 통일)."""
    s = (s or "").strip()
    m = re.search(r"20\d\d-\d\d-\d\d", s)
    if m:
        return m.group(0)
    m = re.search(r"([A-Za-z]+)\s+(\d+),?\s+(20\d\d)", s)
    if m:
        for fmt in ("%B %d %Y", "%b %d %Y"):
            try:
                return datetime.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", fmt).date().isoformat()
            except ValueError:
                pass
    return ""


def http_get(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 — 소스 하나의 실패를 격리
        ERRORS.append(f"GET {url[:70]}: {e}")
        return None


def http_json(url, timeout=15):
    raw = http_get(url, timeout)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception as e:  # noqa: BLE001
        ERRORS.append(f"JSON {url[:70]}: {e}")
        return None


def _atom_entries(raw):
    try:
        root = ET.fromstring(raw)
    except Exception as e:  # noqa: BLE001
        ERRORS.append(f"ATOM parse: {e}")
        return []
    return root.findall("a:entry", ATOM)


def _text(entry, tag):
    return (entry.findtext(f"a:{tag}", default="", namespaces=ATOM) or "").strip()


def _link(entry, fallback=""):
    el = entry.find("a:link", ATOM)
    return el.get("href") if el is not None and el.get("href") else fallback


# ── 소스별 수집 ────────────────────────────────────────────────

def fetch_hn(since_ts):
    items = []
    endpoints = [
        # 1) 최근 윈도우 Claude Code story (시간 역순)
        (f"https://hn.algolia.com/api/v1/search_by_date?query=Claude%20Code&tags=story"
         f"&numericFilters=created_at_i%3E{since_ts}&hitsPerPage=40", False),
        # 2) relevance 보강 — 점수 높은 항목만 (윈도우 밖 고관련도 포착)
        ("https://hn.algolia.com/api/v1/search?query=Anthropic%20Claude%20Code"
         "&tags=story&hitsPerPage=20", True),
    ]
    for url, relevance in endpoints:
        d = http_json(url)
        if not d:
            continue
        for h in d.get("hits", []):
            title = h.get("title") or ""
            oid = h.get("objectID")
            u = h.get("url") or f"https://news.ycombinator.com/item?id={oid}"
            if not SIGNAL.search(title + " " + u) or NOISE.search(title):
                continue
            pts = h.get("points", 0) or 0
            if relevance and pts < 10:
                continue
            items.append({
                "key": f"hn:{oid}",
                "type_hint": "watch",
                "source": "Hacker News",
                "title": title[:200],
                "url": u,
                "date": (h.get("created_at") or "")[:10],
                "extra": f"{pts}pt/{h.get('num_comments', 0)}cm",
            })
    return items


def fetch_gh_releases():
    raw = http_get("https://github.com/anthropics/claude-code/releases.atom")
    if not raw:
        return []
    items = []
    for e in _atom_entries(raw)[:8]:
        title = _text(e, "title")
        content = re.sub(r"<[^>]+>", " ", _text(e, "content"))
        items.append({
            "key": f"ghrel:{title}",
            "type_hint": "kb-ingest",
            "source": "anthropics/claude-code releases",
            "title": f"claude-code {title}",
            "url": _link(e, "https://github.com/anthropics/claude-code/releases"),
            "date": _text(e, "updated")[:10],
            "extra": re.sub(r"\s+", " ", content).strip()[:320],
        })
    return items


def fetch_gh_repos():
    items = []
    # 이중 topic + stars 필터로 노이즈 차단(검증: claude-skill 2385, mcp-server+claude-code 2227)
    queries = [
        ("topic:claude-skill", "skill"),
        ("topic:mcp-server+topic:claude-code", "watch"),
        ("topic:claude-code+topic:anthropic+stars:>10", "watch"),
    ]
    for q, hint in queries:
        url = (f"https://api.github.com/search/repositories?q={q}"
               f"&sort=updated&order=desc&per_page=15")
        d = http_json(url)
        if not d:
            continue
        for r in d.get("items", []):
            name = r.get("full_name")
            if not name:                       # 부분 응답/스키마 변동 항목이 소스 전체를 날리지 않게
                continue
            stars = r.get("stargazers_count", 0) or 0
            if stars < 5:
                continue
            desc = r.get("description") or ""
            items.append({
                "key": f"gh:{name}",
                "type_hint": hint,
                "source": f"GitHub {q}",
                "title": name,
                "url": r.get("html_url", ""),
                "date": (r.get("updated_at") or "")[:10],
                "extra": f"★{stars} · {desc[:130]}",
            })
    return items


def fetch_awesome():
    feeds = [
        ("hesreallyhim/awesome-claude-code",
         "https://github.com/hesreallyhim/awesome-claude-code/commits/main.atom"),
        ("VoltAgent/awesome-claude-code-subagents",
         "https://github.com/VoltAgent/awesome-claude-code-subagents/commits/main.atom"),
    ]
    items = []
    add = re.compile(r"\b(add|new|create|introduc|feat|support)", re.I)
    for repo, url in feeds:
        raw = http_get(url)
        if not raw:
            continue
        for e in _atom_entries(raw)[:10]:
            title = _text(e, "title")
            if not add.search(title):  # merge/chore/docs 커밋 노이즈 제거
                continue
            eid = _text(e, "id")
            sha = eid.split("/")[-1][:10] if eid else title[:10]
            items.append({
                "key": f"ghc:{repo}:{sha}",
                "type_hint": "watch",
                "source": f"awesome curation: {repo}",
                "title": title[:200],
                "url": _link(e, url),
                "date": _text(e, "updated")[:10],
                "extra": "큐레이션 신규 항목 추가",
            })
    return items


def fetch_geeknews():
    raw = http_get("https://news.hada.io/rss/news")
    if not raw:
        return []
    kw = ["claude code", "claude-code", "anthropic", "model context protocol",
          " mcp ", "claude desktop", "claude api", "subagent", "slash command",
          "claude skill", "claude agent"]
    items = []
    for e in _atom_entries(raw):
        title = _text(e, "title")
        content = _text(e, "content")
        blob = f" {title} {content} ".lower()
        if not any(k in blob for k in kw):
            continue
        if NOISE.search(f"{title} {content}"):   # fetch_hn과 동일하게 펀딩/주가 노이즈 차단('anthropic' 부분일치 오탐)
            continue
        link = _link(e)
        items.append({
            "key": f"gn:{link}",
            "type_hint": "kb-ingest",
            "source": "GeekNews",
            "title": title[:200],
            "url": link,
            "date": _text(e, "updated")[:10],
            "extra": "",
        })
    return items


def fetch_anthropic_changelog():
    raw = http_get("https://platform.claude.com/docs/en/release-notes/overview.md")
    if not raw:
        return []
    items = []
    secs = re.split(r"(?m)^#{2,3}\s+", raw)
    # 필터를 cap보다 먼저 적용 — overview.md는 Platform 전체 변경로그라, 상위를 비-CC 항목이
    # 점유하면 고정 윈도우(secs[:N])가 CC 릴리스 노트를 영구 배제한다(누락 버그). 먼저 거르고 나서 cap.
    matched = [s for s in secs[1:] if s.strip() and CC_CHANGELOG_RE.search(s)]
    for s in matched[:12]:
        head = s.splitlines()[0].strip()
        # head 가 날짜뿐인 경우가 많으므로(### May 6, 2026) 본문 첫 구절을 붙여 제목 보강
        body_preview = re.sub(r"[\[\]*`]", "", re.sub(r"\s+", " ", s[len(head):])).strip()[:110]
        title = (f"{head} — {body_preview}".strip(" —"))[:170]
        items.append({
            "key": f"acl:{head[:48]}",
            "type_hint": "kb-ingest",
            "source": "Anthropic release notes",
            "title": title,
            "url": "https://platform.claude.com/docs/en/release-notes/overview",
            "date": iso_date(head),            # 'May 6, 2026' → ISO 로 통일(문자열 정렬 왜곡 방지)
            "extra": re.sub(r"\s+", " ", s).strip()[:300],
        })
    return items


def fetch_devto():
    d = http_json("https://dev.to/api/articles?tag=claudecode&per_page=15&top=7")
    if not isinstance(d, list):
        return []
    items = []
    for a in d:
        rx = a.get("public_reactions_count", 0) or 0
        rt = a.get("reading_time_minutes", 0) or 0
        if rx < 3 and rt < 3:  # 실질 콘텐츠만
            continue
        items.append({
            "key": f"devto:{a.get('id')}",
            "type_hint": "kb-ingest",
            "source": "dev.to #claudecode",
            "title": (a.get("title") or "")[:200],
            "url": a.get("url", ""),
            "date": (a.get("published_at") or "")[:10],
            "extra": f"{rx}rxn · {rt}min",
        })
    return items


def fetch_npm():
    items = []
    for text in ("claude-code mcp", "claude-code skill", "claude-code agent"):
        q = urllib.parse.quote(text)
        d = http_json(f"https://registry.npmjs.org/-/v1/search?text={q}&size=8&popularity=1.0")
        if not d:
            continue
        for o in d.get("objects", []):
            p = o.get("package", {}) or {}
            name = p.get("name")
            if not name:
                continue
            items.append({
                "key": f"npm:{name}",
                "type_hint": "watch",
                "source": "npm registry",
                "title": name,
                "url": (p.get("links", {}) or {}).get("npm", ""),
                "date": (p.get("date") or "")[:10],
                "extra": (p.get("description") or "")[:130],
            })
    return items


# ── ledger ─────────────────────────────────────────────────────

def load_seen():
    """(seen_dict, status) — status: 'absent'|'ok'|'corrupt'.
    파일 부재는 정상 첫 실행(absent → baseline). 존재하나 파싱 실패/비-dict는 corrupt:
    조용히 {}로 강등하면 baseline 판정을 우회해 그날 수집분 전체가 신규로 흘러가고(surge),
    save_seen이 손상 파일을 덮어써 dedup 이력이 영구 소실된다. 호출부가 구분하도록 신호한다."""
    if not os.path.exists(SEEN_PATH):
        return {}, "absent"
    try:
        with open(SEEN_PATH, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("seen"), dict):
            return d["seen"], "ok"
        return {}, "corrupt"
    except Exception:  # noqa: BLE001
        return {}, "corrupt"


def prune(seen):
    cutoff = (datetime.date.today() - datetime.timedelta(days=PRUNE_DAYS)).isoformat()
    pruned = {k: v for k, v in seen.items() if (v or "") >= cutoff}
    if len(pruned) > PRUNE_MAX:
        newest = sorted(pruned.items(), key=lambda kv: kv[1] or "", reverse=True)[:PRUNE_MAX]
        pruned = dict(newest)
    return pruned


def save_seen(seen):
    os.makedirs(os.path.dirname(SEEN_PATH), exist_ok=True)
    tmp = SEEN_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "claude-radar dedup ledger — key→first-seen date. Managed by radar-collect.py; do not hand-edit.",
            "updated": datetime.datetime.now().isoformat(timespec="seconds"),
            "seen": seen,
        }, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SEEN_PATH)


# ── main ───────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="claude-radar 결정론적 수집 엔진")
    ap.add_argument("--dry-run", action="store_true", help="seen ledger를 갱신하지 않음(미리보기/테스트)")
    ap.add_argument("--max-items", type=int, default=60, help="LLM에 넘길 신규 항목 상한")
    ap.add_argument("--window-hours", type=int, default=48, help="HN 등 시간 윈도우(시간)")
    ap.add_argument("--no-baseline", action="store_true", help="첫 실행도 baseline 없이 신규로 처리")
    args = ap.parse_args()

    seen, seen_status = load_seen()
    if seen_status == "corrupt":
        ERRORS.append(f"seen ledger corrupt at {SEEN_PATH} — treating as baseline (surge/overwrite guard)")
    since_ts = int(time.time()) - args.window_hours * 3600

    collected = []
    sources = [
        lambda: fetch_hn(since_ts), fetch_gh_releases, fetch_gh_repos, fetch_awesome,
        fetch_geeknews, fetch_anthropic_changelog, fetch_devto, fetch_npm,
    ]
    for fn in sources:
        try:
            collected += fn() or []
        except Exception as e:  # noqa: BLE001
            ERRORS.append(f"{getattr(fn, '__name__', 'source')}: {e}")

    # 이번 실행 내 중복 제거(key 기준, 먼저 본 것 우선)
    uniq = {}
    for it in collected:
        uniq.setdefault(it["key"], it)

    # absent(첫 실행)도 corrupt(손상)도 baseline 처리 — 현재 항목을 seen에 기록만, 신규는 비움.
    baseline = (seen_status in ("absent", "corrupt")) and not args.no_baseline
    if baseline:
        for k in uniq:
            seen[k] = today()
        if not args.dry_run:
            save_seen(prune(seen))
        note = ("seen ledger 손상 감지 — 재기준선 기록(이력 소실 방지)." if seen_status == "corrupt"
                else "첫 실행 baseline — 현재 항목을 seen에 기록만 함. 다음 실행부터 신규를 보고.")
        print(json.dumps({
            "baseline": True,
            "new_items": [],
            "counts": {"collected": len(uniq), "new": 0},
            "errors": ERRORS,
            "note": note,
        }, ensure_ascii=False, indent=2))
        return

    fresh = [it for k, it in uniq.items() if k not in seen]
    fresh.sort(key=lambda x: x.get("date", "") or "", reverse=True)
    # 소스별 쿼터로 다양성 보장 후 상한 적용
    capped, per = [], {}
    for it in fresh:
        s = it["source"]
        if per.get(s, 0) >= PER_SOURCE_CAP:
            continue
        per[s] = per.get(s, 0) + 1
        capped.append(it)
    fresh = capped[:args.max_items]

    for it in fresh:                       # 외부 수집 텍스트 정제(큐 헤더 위조/프롬프트 인젝션 방지)
        it["title"] = clean_text(it.get("title", ""))[:200]
        it["extra"] = clean_text(it.get("extra", ""))[:320]

    if not args.dry_run:
        for it in fresh:
            seen[it["key"]] = today()
        save_seen(prune(seen))

    print(json.dumps({
        "baseline": False,
        "new_items": fresh,
        "counts": {"collected": len(uniq), "new": len(fresh)},
        "errors": ERRORS,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
