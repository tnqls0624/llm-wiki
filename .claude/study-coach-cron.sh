#!/bin/bash
# study-coach cron wrapper — launchd가 매일 08:07(로컬) + 로그인 시(RunAtLoad) 실행.
# claude headless(-p)로 "/study-coach review"를 돌려 ① 어제 ai-infra-lab 산출물을 LLM이 검토·채점하고
# ② study-state.md(진도) 갱신 + study-today.md(오늘 브리핑)를 작성한다.
# 쓰기는 .claude/runtime/ 만 — ai-infra-lab은 읽기 전용, .claude 메커니즘/KB는 stray-guard가 되돌린다.
# 커밋·push는 SessionEnd auto-commit 훅이 처리(fetch-guarded).
# 사용: study-coach-cron.sh [--check|--force]
#   --check = claude 호출 없이 환경만 검증
#   --force = due 판정 건너뛰고 즉시 실행
#
# anacron 패턴(radar/kb-sync와 동일): "직전 예정 슬롯 > 마지막 성공 실행"이면 실행, 아니면 no-op.
# 멀티 머신: 시작 시 vault를 git pull(ff-only)해 다른 Mac의 진도를 당겨온 뒤 검토한다.
# 포터블: 모든 경로는 스크립트 위치에서 역산.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="$(dirname "$SCRIPT_DIR")"
LOG="$VAULT/.claude/runtime/study-cron.log"
STAMP="$VAULT/.claude/runtime/study-last-run"
TODAY_FILE="$VAULT/.claude/runtime/study-today.md"
LOCK="${TMPDIR:-/tmp}/study-coach-$(id -u)-$(basename "$VAULT").lock"

CLAUDE_BIN="$(command -v claude 2>/dev/null)"
for c in "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
  [ -n "$CLAUDE_BIN" ] && break
  [ -x "$c" ] && CLAUDE_BIN="$c"
done

if [ "$1" = "--check" ]; then
  [ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { echo "[check] FAIL: claude CLI not found (PATH/fallbacks)"; exit 1; }
  [ -f "$VAULT/.claude/commands/study-coach.md" ] || { echo "[check] FAIL: /study-coach command missing in $VAULT"; exit 1; }
  [ -f "$VAULT/.claude/study-brief.py" ] || { echo "[check] FAIL: study-brief.py missing in $VAULT"; exit 1; }
  python3 "$VAULT/.claude/study-brief.py" --check >/dev/null 2>&1 || { echo "[check] FAIL: study-brief.py errored"; exit 1; }
  echo "[check] ok: vault=$VAULT claude=$CLAUDE_BIN ($("$CLAUDE_BIN" --version 2>/dev/null | head -1))"
  exit 0
fi

[ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { echo "[$(date '+%F %T')] FAIL: claude CLI not found" >> "$LOG"; exit 1; }

# ── due 판정 (anacron, 매일 08:07) ───────────────────────────────
# 직전 예정 슬롯의 epoch (plist의 StartCalendarInterval Hour/Minute과 일치 유지!)
SLOT_EPOCH="$(python3 - <<'PY'
import datetime as d
now = d.datetime.now()
slot = now.replace(hour=8, minute=7, second=0, microsecond=0)
if slot > now:
    slot -= d.timedelta(days=1)
print(int(slot.timestamp()))
PY
)"
if [ "$1" != "--force" ]; then
  if [ ! -f "$STAMP" ]; then
    date +%s > "$STAMP"
    echo "[$(date '+%F %T')] init: baseline stamp written, no run" >> "$LOG"
    exit 0
  fi
  LAST="$(cat "$STAMP" 2>/dev/null || echo 0)"
  if [ "$LAST" -ge "$SLOT_EPOCH" ]; then
    exit 0
  fi
fi

if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "[$(date '+%F %T')] skip: already running (pid $(cat "$LOCK"))" >> "$LOG"
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

cd "$VAULT" || exit 0

{
  echo "=== [$(date '+%F %T')] study-coach review start ==="
  # 멀티 머신: 다른 Mac의 진도를 먼저 당겨온다(ff-only → 로컬 미커밋 있으면 안전하게 skip).
  git pull --ff-only 2>&1 || echo "(vault pull skipped — 로컬 변경 있거나 충돌; 로컬 state로 진행)"

  # 멀티맥 중복 방지: study-state의 last_brief_date가 오늘이면(다른 Mac이 이미 검토·브리핑함)
  # claude를 호출하지 않는다 — anacron stamp는 기기별이라 두 Mac이 각자 due가 되지만,
  # last_brief_date(추적되는 공유 state)가 2차 멱등 키 역할을 한다.
  LB="$(grep -o 'last_brief_date=[0-9-]*' "$VAULT/.claude/runtime/study-state.md" 2>/dev/null | head -1 | cut -d= -f2)"
  if [ "$1" != "--force" ] && [ "$LB" = "$(date +%F)" ]; then
    echo "already briefed today ($LB) — skip claude (다른 Mac 또는 이전 실행이 처리)"
    date +%s > "$STAMP"
    exit 0
  fi

  # sonnet: 검토·채점은 중간 티어로 충분(automation-safety: 무인은 cheapest tier).
  # allowlist: study-brief.py 실행 + git(ai-infra-lab 읽기/pull) + runtime 파일 쓰기.
  "$CLAUDE_BIN" -p "/study-coach review — 어제 새 산출물이 없으면 진도를 바꾸지 말고 오늘 브리핑만 생성하라." \
    --model sonnet \
    --permission-mode acceptEdits \
    --allowedTools "Bash(python3 .claude/study-brief.py:*),Bash(git:*),Read,Write,Edit,Glob,Grep" \
    2>&1
  rc=$?
  echo "=== [$(date '+%F %T')] exit=$rc ==="

  # 2차 방어선: review는 .claude/runtime/ 만 변경해야 한다. 프롬프트 오판으로 KB/메커니즘을 건드렸으면
  # auto-commit/push 전에 되돌린다(동의 없는 생성물 차단). ai-infra-lab은 별도 repo라 vault git status에 안 잡힘.
  bash "$VAULT/.claude/stray-guard.sh" runtime

  # macOS 알림: 오늘 브리핑 한 줄(brief.py --notify-line은 멱등이라 이미 생성됨 → state에서 다시 못 뽑음)을
  # study-today.md 본문 "오늘 할 것" 라인에서 추출해 표시. GUI 세션(launchd Aqua)이라 알림 노출됨.
  if [ "$rc" -eq 0 ] && [ -f "$TODAY_FILE" ]; then
    NOTE="$(grep -m1 '^\*\*W' "$TODAY_FILE" 2>/dev/null | sed 's/\*\*//g' | cut -c1-110)"
    [ -z "$NOTE" ] && NOTE="오늘의 학습 브리핑이 준비됐어요"
    osascript -e "display notification \"${NOTE//\"/\\\"}\" with title \"📚 AI Infra 학습\" sound name \"Glass\"" 2>/dev/null || true
  fi

  [ "$rc" -eq 0 ] && date +%s > "$STAMP"
} >> "$LOG" 2>&1

if [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 524288 ]; then
  tail -c 262144 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
