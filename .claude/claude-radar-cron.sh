#!/bin/bash
# claude-radar cron wrapper — launchd가 매일 09:17(로컬) + 로그인 시(RunAtLoad) 실행.
# claude headless(-p)로 "/claude-radar collect"를 돌려 Claude 활용 정보를 수집·추천 큐에 적재한다.
# 무인 단계는 큐(.claude/runtime/)와 seen ledger만 변경 — .claude/·KB 생성은 하지 않는다(동의 후 review 몫).
# 커밋·push는 SessionEnd auto-commit 훅이 처리(fetch-guarded).
# 사용: claude-radar-cron.sh [--check|--force]
#   --check = claude 호출 없이 환경만 검증
#   --force = due 판정 건너뛰고 즉시 실행
#
# anacron 패턴: 전원 꺼짐으로 슬롯을 놓친 경우를 위해 매 호출마다
# "직전 예정 슬롯 > 마지막 성공 실행"이면 실행, 아니면 no-op(비용 0).
# 포터블: 모든 경로는 스크립트 위치에서 역산.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="$(dirname "$SCRIPT_DIR")"                       # .claude/ 의 부모 = vault 루트
LOG="$VAULT/.claude/runtime/radar-cron.log"
STAMP="$VAULT/.claude/runtime/radar-last-run"          # 마지막 성공 실행 epoch
LOCK="${TMPDIR:-/tmp}/claude-radar-$(id -u)-$(basename "$VAULT").lock"  # vault별 분리

# claude CLI 탐지 — launchd는 PATH가 최소라 명시 fallback 필요
CLAUDE_BIN="$(command -v claude 2>/dev/null)"
for c in "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
  [ -n "$CLAUDE_BIN" ] && break
  [ -x "$c" ] && CLAUDE_BIN="$c"
done

if [ "$1" = "--check" ]; then
  [ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { echo "[check] FAIL: claude CLI not found (PATH/fallbacks)"; exit 1; }
  [ -f "$VAULT/.claude/commands/claude-radar.md" ] || { echo "[check] FAIL: /claude-radar command missing in $VAULT"; exit 1; }
  [ -f "$VAULT/.claude/radar-collect.py" ] || { echo "[check] FAIL: radar-collect.py missing in $VAULT"; exit 1; }
  python3 "$VAULT/.claude/radar-collect.py" --dry-run --no-baseline >/dev/null 2>&1 || { echo "[check] FAIL: radar-collect.py errored"; exit 1; }
  echo "[check] ok: vault=$VAULT claude=$CLAUDE_BIN ($("$CLAUDE_BIN" --version 2>/dev/null | head -1))"
  exit 0
fi

[ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { echo "[$(date '+%F %T')] FAIL: claude CLI not found" >> "$LOG"; exit 1; }

# ── due 판정 (anacron, 매일 09:17) ───────────────────────────────
# 직전 예정 슬롯의 epoch 계산 (plist의 StartCalendarInterval Hour/Minute과 일치 유지!)
SLOT_EPOCH="$(python3 - <<'PY'
import datetime as d
now = d.datetime.now()
slot = now.replace(hour=9, minute=17, second=0, microsecond=0)
if slot > now:            # 오늘 슬롯이 아직 안 왔으면 어제 슬롯이 직전
    slot -= d.timedelta(days=1)
print(int(slot.timestamp()))
PY
)"
if [ "$1" != "--force" ]; then
  if [ ! -f "$STAMP" ]; then
    # 설치 직후: 현재를 기준선으로 기록만 하고 종료 (설치 시점 폭주 방지)
    date +%s > "$STAMP"
    echo "[$(date '+%F %T')] init: baseline stamp written, no run" >> "$LOG"
    exit 0
  fi
  LAST="$(cat "$STAMP" 2>/dev/null || echo 0)"
  if [ "$LAST" -ge "$SLOT_EPOCH" ]; then
    exit 0  # 직전 슬롯 이미 소화 — no-op (RunAtLoad 로그인 호출의 평상시 경로)
  fi
fi

# 중복 실행 방지
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "[$(date '+%F %T')] skip: already running (pid $(cat "$LOCK"))" >> "$LOG"
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

cd "$VAULT" || exit 0

{
  echo "=== [$(date '+%F %T')] claude-radar collect start ==="
  # sonnet: 수집·분류·추천은 중간 티어로 충분(비용 레버). collect 모드는 큐+seen만 변경.
  # python3 allowlist는 radar-collect.py로 고정(임의 `python3 -c` 실행 표면 차단). 큐 적재는 Read/Write/Edit.
  "$CLAUDE_BIN" -p "/claude-radar collect — 신규가 없으면 아무 파일도 만들지 말고 '변경 없음'만 보고하고 종료하라." \
    --model sonnet \
    --permission-mode acceptEdits \
    --allowedTools "Bash(python3 .claude/radar-collect.py:*),Read,Write,Edit,Glob,Grep" \
    2>&1
  rc=$?
  echo "=== [$(date '+%F %T')] exit=$rc ==="

  # 안전 불변식의 기계적 강제(2차 방어선): collect는 .claude/runtime/ 만 변경해야 한다.
  # 프롬프트 오판으로 큐 밖(skill/agent/KB 등)을 건드렸으면 auto-commit/push 전에 되돌린다 —
  # 동의 없는 생성물이 조용히 커밋·push되지 않게. (1차 방어선은 command §A + allowlist)
  STRAY=$(git -c core.quotepath=false status --porcelain --untracked-files=all 2>/dev/null \
            | sed 's/^...//' | grep -vE '^\.claude/runtime/' || true)
  if [ -n "$STRAY" ]; then
    echo "WARN: collect touched files outside .claude/runtime/ — reverting (safety invariant):"
    printf '%s\n' "$STRAY"
    printf '%s\n' "$STRAY" | while IFS= read -r f; do
      [ -z "$f" ] && continue
      if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
        git checkout -- "$f" 2>/dev/null      # 추적 파일: 원복
      else
        rm -f "$f" 2>/dev/null                 # 미추적 신규 파일: 삭제
      fi
    done
  fi

  # 성공 시에만 스탬프 갱신 — 실패하면 다음 로그인/슬롯에서 재시도됨
  [ "$rc" -eq 0 ] && date +%s > "$STAMP"
} >> "$LOG" 2>&1

# 로그 로테이션: 512KB 초과 시 뒤쪽 절반만 유지
if [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 524288 ]; then
  tail -c 262144 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
