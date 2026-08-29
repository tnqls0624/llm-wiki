#!/bin/bash
# claude-radar cron wrapper — launchd가 매일 09:30(로컬) + 로그인 시(RunAtLoad) 실행.
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

# ── due 판정 (anacron, 매일 09:30) ───────────────────────────────
# 직전 예정 슬롯의 epoch 계산 (plist의 StartCalendarInterval Hour/Minute과 일치 유지!)
# 2026-08-23(아키텍처 P0-5): 일 1회 -> 주 1회(수 09:33). 근거 — 처리가 병목이지 수집이 아니고
# (모든 수집 표면에 미처리 잔량 실측), 26일 침묵 실패를 아무도 눈치 못 챈 것이 일 1회 과잉의 증거.
# 정지 감시는 session-context 데드맨 배너(ledger 9일 무갱신)가 별도로 담당한다.
# 슬롯 시각은 plist StartCalendarInterval(Weekday 3, 09:33)과 반드시 일치해야 한다.
SLOT_EPOCH="$(python3 - <<'PYEOF'
import datetime as d
now = d.datetime.now()
slot = now.replace(hour=9, minute=33, second=0, microsecond=0)
days_back = (now.weekday() - 2) % 7          # 2 = 수요일
slot -= d.timedelta(days=days_back)
if slot > now:                                # 오늘이 수요일인데 09:33 전이면 지난주 슬롯이 직전
    slot -= d.timedelta(days=7)
print(int(slot.timestamp()))
PYEOF
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

# 무인 런 **시작 시점의 dirty 목록**을 남긴다(2026-08-29). 이 목록에 있던 경로는 사람이 하던
# 작업이므로 stray-guard가 건드리지 않는다. 없던 동안 실제 사고가 났다: 09:30 study-coach cron이
# 편집 중이던 미커밋 `.claude/kb-eval.py`를 STRAY로 되돌려 작업이 통째로 사라졌다.
# 무인 런의 책임 범위는 그 런이 만든 변경이지, 같은 시각에 열려 있던 사람의 작업이 아니다.
STRAY_BASELINE="$VAULT/.claude/runtime/.stray-baseline.$$"
bash "$VAULT/.claude/stray-guard.sh" snapshot > "$STRAY_BASELINE" 2>/dev/null || true
trap 'rm -f "$LOCK" "$STRAY_BASELINE"' EXIT

# 실패 서명 측정용 기준선(2026-08-23 추가). collect의 유일한 산출물은 radar-queue.md 인데,
# harness가 이 경로를 'sensitive file'로 분류해 무인 런의 Edit/Write를 거부하면서도
# seen 원장(allowlist된 radar-collect.py가 직접 씀)은 계속 자라 26일간 exit=0으로 침묵했다.
# "큐 무변경" 자체는 정상일 수 있다(신규 0건) — 실패는 "seen은 늘었는데 큐는 그대로"다.
QUEUE="$VAULT/.claude/runtime/radar-queue.md"
SEEN="$VAULT/.claude/runtime/radar-seen.json"
_seen_count() { python3 -c "import json,sys;print(len(json.load(open(sys.argv[1])).get('seen',{})))" "$1" 2>/dev/null || echo -1; }
SEEN_BEFORE="$(_seen_count "$SEEN")"
QUEUE_BEFORE="$(stat -f%m "$QUEUE" 2>/dev/null || echo 0)"
RUN_START_EPOCH="$(date +%s)"

# 구조화 실행 원장(2026-08-25) — 26일 침묵을 사후에 세어야 했던 경험의 응답. span 1건 = 실행 1건.
SPAN="$(python3 "$VAULT/.claude/span.py" start claude-radar 2>/dev/null || true)"

{
  echo "=== [$(date '+%F %T')] claude-radar collect start ==="
  # sonnet: 수집·분류·추천은 중간 티어로 충분(비용 레버). collect 모드는 큐+seen만 변경.
  # python3 allowlist는 radar-collect.py로 고정(임의 `python3 -c` 실행 표면 차단). 큐 적재는 Read/Write/Edit.
  "$CLAUDE_BIN" -p "/claude-radar collect — 신규가 없으면 아무 파일도 만들지 말고 '변경 없음'만 보고하고 종료하라." \
    --model sonnet \
    --permission-mode acceptEdits \
    --allowedTools "Bash(python3 .claude/radar-collect.py:*),Read,Write,Edit,Glob,Grep,WebFetch" \
    2>&1
  rc=$?
  echo "=== [$(date '+%F %T')] exit=$rc ==="

  # 안전 불변식의 기계적 강제(2차 방어선): collect는 .claude/runtime/ 만 변경해야 한다.
  # 프롬프트 오판으로 큐 밖(skill/agent/KB 등)을 건드렸으면 auto-commit/push 전에 되돌린다 —
  # 동의 없는 생성물이 조용히 커밋·push되지 않게. (1차 방어선은 command §A + allowlist)
  # 가드 로직은 stray-guard.sh로 추출(kb-sync와 공유 + 계약 테스트 대상). runtime 모드 = .claude/runtime/만 허용.
  bash "$VAULT/.claude/stray-guard.sh" runtime "$STRAY_BASELINE"

  # 산출물 가드 v2 (2026-08-23): 완주 영수증 계약.
  # v1(seen 증가 + 큐 무변경 = 실패)은 첫 실전에서 "신규 전부 정당 드롭" 정상 케이스를
  # 실패로 오판했다(거짓 양성). 이제 LLM은 분류를 마치면 --finish <queued> <dropped>로
  # 영수증을 남겨야 하고, 가드는 ① 신규가 있었는데 영수증이 없으면 실패(분류 미완주 —
  # 26일 침묵과 같은 부류) ② queued>0인데 큐 mtime 무변경이면 실패(적재 유실)만 본다.
  SEEN_AFTER="$(_seen_count "$SEEN")"
  QUEUE_AFTER="$(stat -f%m "$QUEUE" 2>/dev/null || echo 0)"
  RECEIPT="$VAULT/.claude/runtime/radar-last-collect.json"
  NEW_N=$((SEEN_AFTER - SEEN_BEFORE))
  if [ "$SEEN_BEFORE" -ge 0 ] && [ "$NEW_N" -gt 0 ]; then
    RCP_EPOCH="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('epoch',0))" "$RECEIPT" 2>/dev/null || echo 0)"
    RCP_QUEUED="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('queued',-1))" "$RECEIPT" 2>/dev/null || echo -1)"
    if [ "$RCP_EPOCH" -lt "${RUN_START_EPOCH:-0}" ]; then
      echo "⚠ 분류 미완주: 신규 ${NEW_N}건이 seen에 기록됐는데 이번 실행의 --finish 영수증이 없다."
      echo "  LLM 세션이 분류를 끝내지 못했거나 --finish 호출을 누락. 신규 항목은 재추천되지 않으므로 로그에서 수동 확인 필요."
      rc=1
    elif [ "$RCP_QUEUED" -gt 0 ] && [ "$QUEUE_AFTER" = "$QUEUE_BEFORE" ]; then
      echo "⚠ 적재 유실: 영수증은 queued=${RCP_QUEUED}인데 radar-queue.md 무변경 — --append-queue 경로 확인 필요."
      rc=1
    fi
  fi

  # 성공 시에만 스탬프 갱신 — 실패하면 다음 로그인/슬롯에서 재시도됨
  [ "$rc" -eq 0 ] && date +%s > "$STAMP"

  # span 종료 — 영수증 가드가 rc를 바꾼 뒤에 닫는다.
  if [ -n "$SPAN" ]; then
    SPAN_ST=error; [ "$rc" -eq 0 ] && SPAN_ST=ok
    python3 "$VAULT/.claude/span.py" end "$SPAN" --status "$SPAN_ST" \
      --attr "rc=$rc" --attr "new=${NEW_N:-0}" --attr "queued=${RCP_QUEUED:-0}" >/dev/null || true
    # stdout만 버린다 — stderr는 로그로 흘러야 orphan(계측 버그) 경고가 보인다(fail-loud 유지).
  fi

  # 무인 런의 커밋·push를 훅에 의존하지 않고 직접 수행 (2026-08-25).
  # 근거(실측): headless 런에서 SessionEnd 훅이 `Hook cancelled`로 33회 취소됐다(radar 27·kb-sync 6).
  # Stop 훅의 turn 커밋은 살아있어 로컬 커밋은 됐지만 push는 SessionEnd 전용이라 누락돼 왔다 —
  # 멀티맥 vault에서 push 누락은 다른 Mac이 낡은 상태로 다음 런을 도는 것을 뜻한다.
  # auto-commit.py를 재사용하므로 발산 감지·sync-status 마커가 중복 구현되지 않는다(멱등).
  echo '{"hook_event_name":"SessionEnd"}' | CLAUDE_PROJECT_DIR="$VAULT" python3 "$VAULT/.claude/hooks/auto-commit.py" >/dev/null 2>&1 || true
} >> "$LOG" 2>&1

# 로그 로테이션: 512KB 초과 시 뒤쪽 절반만 유지
if [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 524288 ]; then
  tail -c 262144 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
