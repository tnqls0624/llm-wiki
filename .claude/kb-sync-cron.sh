#!/bin/bash
# kb-sync cron wrapper — launchd가 월·목 09:07(로컬) + 로그인 시(RunAtLoad) 실행.
# claude headless(-p)로 /kb-sync를 돌려 공식 문서 변경분을 KB에 반영한다.
# 커밋·push는 SessionEnd auto-commit 훅이 처리(fetch-guarded).
# 사용: kb-sync-cron.sh [--check|--force]
#   --check = claude 호출 없이 환경만 검증
#   --force = due 판정 건너뛰고 즉시 실행
#
# anacron 패턴: 전원 꺼짐으로 슬롯을 놓친 경우를 위해 매 호출마다
# "직전 예정 슬롯 > 마지막 성공 실행" 이면 실행, 아니면 no-op.
# (RunAtLoad가 로그인마다 부르지만 due가 아니면 즉시 종료 — 비용 0)
#
# 포터블: 모든 경로는 스크립트 위치에서 역산 — 홈 디렉토리/머신이 달라도 동작.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="$(dirname "$SCRIPT_DIR")"            # .claude/ 의 부모 = vault 루트
LOG="$VAULT/.claude/runtime/kb-sync-cron.log"
STAMP="$VAULT/.claude/runtime/kb-sync-last-run"   # 마지막 성공 실행 epoch
LOCK="${TMPDIR:-/tmp}/kb-sync-$(id -u)-$(basename "$VAULT").lock"  # vault별 분리(다중 vault 안전)

# claude CLI 탐지 — launchd는 PATH가 최소라 명시 fallback 필요
CLAUDE_BIN="$(command -v claude 2>/dev/null)"
for c in "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
  [ -n "$CLAUDE_BIN" ] && break
  [ -x "$c" ] && CLAUDE_BIN="$c"
done

if [ "$1" = "--check" ]; then
  [ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { echo "[check] FAIL: claude CLI not found (PATH/fallbacks)"; exit 1; }
  [ -f "$VAULT/.claude/commands/kb-sync.md" ] || { echo "[check] FAIL: /kb-sync command missing in $VAULT"; exit 1; }
  echo "[check] ok: vault=$VAULT claude=$CLAUDE_BIN ($("$CLAUDE_BIN" --version 2>/dev/null | head -1))"
  exit 0
fi

[ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { echo "[$(date '+%F %T')] FAIL: claude CLI not found" >> "$LOG"; exit 1; }

# ── due 판정 (anacron) ──────────────────────────────────────────
# 직전 예정 슬롯(월/목 09:07, plist의 StartCalendarInterval과 일치 유지!)의 epoch 계산
SLOT_EPOCH="$(python3 - <<'PY'
import datetime as d
now = d.datetime.now()
slots = []
for back in range(8):  # 최근 8일이면 월/목 슬롯이 반드시 포함됨
    day = now - d.timedelta(days=back)
    if day.weekday() in (0, 3):  # Mon=0, Thu=3
        s = day.replace(hour=9, minute=7, second=0, microsecond=0)
        if s <= now:
            slots.append(s)
print(int(max(slots).timestamp()))
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

# 중복 실행 방지 (이전 런이 아직 돌고 있으면 스킵)
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "[$(date '+%F %T')] skip: already running (pid $(cat "$LOCK"))" >> "$LOG"
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

cd "$VAULT" || exit 0

{
  echo "=== [$(date '+%F %T')] kb-sync run start ==="
  # sonnet: 주기 diff 반영은 중간 티어로 충분(비용 레버). acceptEdits + 최소 도구 allowlist로 무인 실행.
  # allowlist 정밀화(least-authority): curl은 공식 docs 호스트로, python3는 정확 스크립트로 고정 —
  # 임의 `python3 -c`·임의 curl POST(데이터 유출 표면)를 무인 런에서 차단(radar collect와 권한 위생 통일).
  "$CLAUDE_BIN" -p "/kb-sync — 변경이 없으면 아무 파일도 만들지 말고 '변경 없음'만 보고하고 종료하라." \
    --model sonnet \
    --permission-mode acceptEdits \
    --allowedTools "Bash(curl -s https://code.claude.com/docs/*),Bash(python3 .claude/kb-lint.py:*),Bash(python3 .claude/kb-source-hashes.py:*),Read,Write,Edit,Glob,Grep" \
    2>&1
  rc=$?
  echo "=== [$(date '+%F %T')] exit=$rc ==="

  # 안전 불변식의 기계적 강제(2차 방어선): kb-sync는 KB 노트(토픽 디렉터리)와 .claude/runtime/ 을
  # durable하게 쓰는 것이 설계 의도다. 그러나 .claude/ 의 **메커니즘**(skills/agents/commands/rules/
  # hooks/scripts/tests 등 runtime 외)을 자기수정하는 것은 범위 밖 — 프롬프트 오판으로 훅/룰을 고쳐
  # auto-commit/push로 다른 머신에 전파되지 않게, 커밋 경계 이전에 되돌린다. KB 쓰기는 허용하므로
  # radar처럼 전부 되돌리지 않고 '.claude/ 메커니즘 경로'만 STRAY 처리한다(kb 모드 = 블랙리스트).
  bash "$VAULT/.claude/stray-guard.sh" kb

  # 성공 시에만 스탬프 갱신 — 실패하면 다음 로그인/슬롯에서 재시도됨
  [ "$rc" -eq 0 ] && date +%s > "$STAMP"
} >> "$LOG" 2>&1

# 로그 로테이션: 512KB 초과 시 뒤쪽 절반만 유지
if [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 524288 ]; then
  tail -c 262144 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
