#!/usr/bin/env python3
"""SessionStart hook — 위키 부팅 컨텍스트 주입.
hot.md(.claude/runtime/, AI 런타임 캐시·영어)의 INJECT 마커 블록만 주입한다
(고정 헤더 → prompt cache 친화·완결). 마커가 없으면 앞 2000자 fallback.
hot.md가 없으면 index.md 발췌. 컨텍스트 계층화(L1 hot → L2 index)의 진입점."""
import json, sys, os, re, datetime

root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
try:
    data = json.load(sys.stdin)
    # CLAUDE_PROJECT_DIR(설정 hook이 전달)을 우선 — cwd가 vault 밖이면 빈 컨텍스트가 주입됨
    if not os.environ.get("CLAUDE_PROJECT_DIR"):
        root = (data or {}).get("cwd") or root
except Exception:
    pass

def read(p, n=None):
    try:
        with open(p, encoding="utf-8") as f:
            s = f.read()
        return s[:n] if n else s
    except Exception:
        return ""

def injected(text):
    # INJECT:START..END 사이의 고정 헤더만 주입 → prompt cache 친화·데이터 완결.
    # 휘발성 'Recent sessions'는 마커 밖이라 주입되지 않음(매 세션 캐시 churn 방지).
    m = re.search(r"<!--\s*INJECT:START.*?-->(.*?)<!--\s*INJECT:END\s*-->", text, re.S)
    return m.group(1).strip() if m else text[:2000].strip()

hot = os.path.join(root, ".claude", "runtime", "hot.md")
idx = os.path.join(root, "index.md")
parts = []

if os.path.exists(hot):
    parts.append("## 최근 컨텍스트 (hot.md L1)\n" + injected(read(hot)))
elif os.path.exists(idx):
    parts.append("## LLM Wiki 인덱스 (index.md 발췌)\n" + read(idx, 1500))
    parts.append("\n(hot.md 미도입 — 로드맵 1단계. 도입 시 세션 부팅이 더 가벼워집니다.)")
else:
    parts.append("LLM Wiki vault이지만 index.md/hot.md가 없습니다. ingest로 시작하세요.")

# auto-commit이 push 발산 시 남긴 경고를 부팅 시 최상단에 표면화(성공 push 시 자동 제거).
sync = read(os.path.join(root, ".claude", "runtime", "sync-status.txt")).strip()
if sync:
    parts.insert(0, "## ⚠ Git 동기화 경고\n" + sync + "(해결 후 다음 push 성공 시 사라집니다.)")

# 주간 review-queue.md '신뢰되지만 잊힌' 버킷에서 1개를 ISO주차로 회전해 부팅 컨텍스트 끝에 덧붙인다.
# ISO주차로만 회전 → 같은 주 안에선 동일(캐시 churn 주 1회). additionalContext는 한 문자열이라
# 캐시 prefix 분리는 Claude Code breakpoint 배치에 달렸고 훅이 보장하진 않음(tail-append가 최소영향).
# WIKI_NO_RECALL=1로 끔. 실패는 무시.
if os.environ.get("WIKI_NO_RECALL") != "1":
    try:
        body = read(os.path.join(root, "review-queue.md"))
        bucket = re.search(r"^##\s*신뢰되지만 잊힌.*?(?=^##\s|\Z)", body, re.M | re.S)
        picks = re.findall(r"^### \[\[([^\]]+)\]\]\s*\n([^\n]*)", bucket.group(0), re.M) if bucket else []
        if picks:
            slug, summ = picks[datetime.date.today().isocalendar()[1] % len(picks)]
            summ = summ.strip()
            if summ.startswith("- 점수 근거") or summ == "(요약 없음)":
                summ = ""    # 방어: empty-summary 페이지의 점수근거 라인 오캡처 차단
            blurb = (" — " + summ) if summ else ""
            parts.append("## 오늘의 재방문\n[[" + slug.strip() + "]]" + blurb
                         + "\n이번 주 잘 안 들춘 고가치 페이지. 지금 작업과 엮이면 /wiki-query로 끌어쓰고 결론은 /save. (무시 가능 · 끄려면 WIKI_NO_RECALL=1)")
    except Exception:
        pass

ctx = "\n".join(parts).strip()
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))
