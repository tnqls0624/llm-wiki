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

# 영수증 신선도 기준선(2026-08-25). 낡은 영수증을 이번 실행 것으로 오인하면 가드가 무의미해진다.
RUN_START_EPOCH="$(date +%s)"

# 구조화 실행 원장(2026-08-25). cron 로그의 자유 텍스트로는 "어느 단계에서 죽었나 / 언제부터
# 느려졌나 / 이 루프 성공률이 얼마나"를 답할 수 없다. span 하나 = 이 실행 1건.
SPAN="$(python3 "$VAULT/.claude/span.py" start kb-sync 2>/dev/null || true)"

{
  echo "=== [$(date '+%F %T')] kb-sync run start ==="
  # sonnet: 주기 diff 반영은 중간 티어로 충분(비용 레버). acceptEdits + 최소 도구 allowlist로 무인 실행.
  # allowlist 정밀화(least-authority): curl은 공식 docs 호스트로, python3는 정확 스크립트로 고정 —
  # 임의 `python3 -c`·임의 curl POST(데이터 유출 표면)를 무인 런에서 차단(radar collect와 권한 위생 통일).
  "$CLAUDE_BIN" -p "/kb-sync — 변경이 없으면 아무 파일도 만들지 말고 '변경 없음'만 보고하고 종료하라." \
    --model sonnet \
    --permission-mode acceptEdits \
    --allowedTools "Bash(curl -s https://code.claude.com/docs/*),Bash(python3 .claude/kb-lint.py:*),Bash(python3 .claude/kb-source-hashes.py:*),Bash(python3 .claude/radar-collect.py:*),Bash(python3 .claude/hot-append.py:*),Read,Write,Edit,Glob,Grep" \
    2>&1
  rc=$?
  echo "=== [$(date '+%F %T')] exit=$rc ==="

  # 안전 불변식의 기계적 강제(2차 방어선): kb-sync는 KB 노트(토픽 디렉터리)와 .claude/runtime/ 을
  # durable하게 쓰는 것이 설계 의도다. 그러나 .claude/ 의 **메커니즘**(skills/agents/commands/rules/
  # hooks/scripts/tests 등 runtime 외)을 자기수정하는 것은 범위 밖 — 프롬프트 오판으로 훅/룰을 고쳐
  # auto-commit/push로 다른 머신에 전파되지 않게, 커밋 경계 이전에 되돌린다. KB 쓰기는 허용하므로
  # radar처럼 전부 되돌리지 않고 '.claude/ 메커니즘 경로'만 STRAY 처리한다(kb 모드 = 블랙리스트).
  bash "$VAULT/.claude/stray-guard.sh" kb

  # 산출물 가드: 갱신 의무 ③(hot.md 한 줄) 완주 영수증 (2026-08-25).
  # 근거(실측): 08-24 무인 런은 §6b 처리를 끝내고도 hot.md Edit이 sensitive-file로 두 번 거부돼
  # duty-③만 미완료로 끝났는데 exit=0이었다 — radar 26일 침묵과 같은 부류(거짓 성공).
  # hot-append.py가 allowlist된 쓰기 경로가 된 이상 "못 썼다"는 변명이 없다 → 계약으로 만든다.
  # KB를 실제로 건드린 실행에만 적용한다(변경 없음 종료는 duty 대상이 아니다). 세션 중 Stop 훅이
  # 이미 커밋했을 수 있으므로 커밋된 변경과 미커밋 변경을 모두 센다.
  # `-c core.quotepath=false` 는 필수다(2026-08-25 실측으로 발견한 버그 수정). 기본 설정에서 git은
  # non-ASCII 경로를 `"80 Tooling/31 \355\225\230....md"` 로 escape하고 **따옴표로 감싼다** — 그러면
  # KB_RE의 `^(20|30|80)` 와 `\.md$` 가 둘 다 빗나가, 이 vault의 KB 노트(전부 한글 파일명)를 하나도
  # 세지 못한다. 즉 세션 중 Stop 훅이 이미 커밋한 통상 경로에서 KB_TOUCHED가 0이 되어 가드가 영구히
  # 침묵했다 — 고치려던 '거짓 성공'을 가드 자신이 재생산하는 형태였다. `tr -d '"'` 는 2차 방어선.
  KB_RE='^(20|30|80) .*\.md$'
  KB_COMMITTED="$(git -C "$VAULT" -c core.quotepath=false log --since="@$RUN_START_EPOCH" --name-only --pretty=format: 2>/dev/null | tr -d '"' | grep -cE "$KB_RE" || true)"
  KB_DIRTY="$(git -C "$VAULT" -c core.quotepath=false status --porcelain 2>/dev/null | sed 's/^...//' | tr -d '"' | grep -cE "$KB_RE" || true)"
  KB_TOUCHED=$(( ${KB_COMMITTED:-0} + ${KB_DIRTY:-0} ))
  if [ "$KB_TOUCHED" -gt 0 ]; then
    HOT_RCPT="$VAULT/.claude/runtime/hot-last-append.json"
    HOT_EPOCH="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('epoch',0))" "$HOT_RCPT" 2>/dev/null || echo 0)"
    if [ "${HOT_EPOCH:-0}" -lt "$RUN_START_EPOCH" ]; then
      echo "⚠ duty-③ 미완주: KB 파일 ${KB_TOUCHED}건을 건드렸는데 이번 실행의 hot.md 영수증이 없다."
      echo "  hot-append.py --line 호출 누락 — hot.md가 안 갱신되면 다음 세션 L1 부팅 컨텍스트가 이 변경을 모른다."
      rc=1
    fi
  fi

  # span 종료 — rc가 최종 확정된 뒤에 닫는다(가드가 rc를 바꿀 수 있으므로 순서가 중요).
  if [ -n "$SPAN" ]; then
    SPAN_ST=error; [ "$rc" -eq 0 ] && SPAN_ST=ok
    python3 "$VAULT/.claude/span.py" end "$SPAN" --status "$SPAN_ST" \
      --attr "rc=$rc" --attr "kb_touched=${KB_TOUCHED:-0}" >/dev/null || true
    # stdout만 버린다 — stderr는 블록의 >>"$LOG"로 흘러야 orphan(계측 버그) 경고가 로그에 남는다.
    # `2>&1 >/dev/null`로 함께 버리면 span.py의 fail-loud 설계가 정확히 무인 환경에서만 무력해진다.
  fi

  # 무인 런의 커밋·push를 훅에 의존하지 않고 직접 수행 (2026-08-25).
  # 근거(실측): headless 런에서 SessionEnd 훅이 `Hook cancelled`로 33회 취소됐다(radar 27·kb-sync 6).
  # Stop 훅의 turn 커밋은 살아있어 로컬 커밋은 됐지만 push는 SessionEnd 전용이라 누락돼 왔다 —
  # 멀티맥 vault에서 push 누락은 다른 Mac이 낡은 상태로 다음 런을 도는 것을 뜻한다.
  # auto-commit.py를 그대로 재사용하므로 발산 감지·sync-status 마커가 중복 구현되지 않는다(멱등).
  echo '{"hook_event_name":"SessionEnd"}' | CLAUDE_PROJECT_DIR="$VAULT" python3 "$VAULT/.claude/hooks/auto-commit.py" >/dev/null 2>&1 || true

  # 성공 시에만 스탬프 갱신 — 실패하면 다음 로그인/슬롯에서 재시도됨
  [ "$rc" -eq 0 ] && date +%s > "$STAMP"
} >> "$LOG" 2>&1

# 로그 로테이션: 512KB 초과 시 뒤쪽 절반만 유지
if [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 524288 ]; then
  tail -c 262144 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
