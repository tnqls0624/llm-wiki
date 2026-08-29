#!/bin/bash
# study-coach cron wrapper — launchd가 매일 09:30(로컬) + 로그인 시(RunAtLoad) 실행.
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

# ── due 판정 (anacron, 매일 09:30) ───────────────────────────────
# 직전 예정 슬롯의 epoch (plist의 StartCalendarInterval Hour/Minute과 일치 유지!)
SLOT_EPOCH="$(python3 - <<'PY'
import datetime as d
now = d.datetime.now()
slot = now.replace(hour=9, minute=30, second=0, microsecond=0)
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

# 무인 런 **시작 시점의 dirty 목록**을 남긴다(2026-08-29). 이 목록에 있던 경로는 사람이 하던
# 작업이므로 stray-guard가 건드리지 않는다. 없던 동안 실제 사고가 났다: 09:30 study-coach cron이
# 편집 중이던 미커밋 `.claude/kb-eval.py`를 STRAY로 되돌려 작업이 통째로 사라졌다.
# 무인 런의 책임 범위는 그 런이 만든 변경이지, 같은 시각에 열려 있던 사람의 작업이 아니다.
STRAY_BASELINE="$VAULT/.claude/runtime/.stray-baseline.$$"
bash "$VAULT/.claude/stray-guard.sh" snapshot > "$STRAY_BASELINE" 2>/dev/null || true
trap 'rm -f "$LOCK" "$STRAY_BASELINE"' EXIT

# 구조화 실행 원장(2026-08-25). 이 루프는 게이트로 스킵되는 날이 정상이라 로그만으로는
# '침묵'과 '사망'을 못 가른다 — span의 gate attr이 그 둘을 기계 판독 가능하게 만든다.
SPAN="$(python3 "$VAULT/.claude/span.py" start study-coach 2>/dev/null || true)"

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

  # ── 커밋 게이트 (2026-08-23, 아키텍처 P0-3) ─────────────────────────
  # "커밋이 진도의 단위"를 cron에 이식: 마지막 검토 이후 ai-infra-lab에 신규 커밋이 없으면
  # LLM 채점을 스킵한다(브리핑은 아래 fallback이 항상 보장). 무커밋일 = 무비용·무알림 —
  # 공백일은 버스트 리듬의 정상 상태이며, 매일 알림은 죄책감 부채를 만든다(브리핑 DB에서 실증).
  # repo 경로 해석은 study-brief.py와 동일 규칙: state 메타 repo_path + study-local.conf override.
  REPO_PATH="$(grep -o 'repo_path=[^ |]*' "$VAULT/.claude/runtime/study-state.md" 2>/dev/null | head -1 | cut -d= -f2)"
  [ -f "$VAULT/.claude/runtime/study-local.conf" ] && \
    OVERRIDE="$(grep -o 'repo_path=.*' "$VAULT/.claude/runtime/study-local.conf" 2>/dev/null | head -1 | cut -d= -f2)" && \
    [ -n "$OVERRIDE" ] && REPO_PATH="$OVERRIDE"
  REPO_PATH="${REPO_PATH/#\~/$HOME}"
  SKIP_REVIEW=""
  if [ -d "$REPO_PATH/.git" ]; then
    # 다른 Mac의 산출물을 먼저 당겨온다 — READ-ONLY 불변식은 "내용을 만들지 않는다"이지
    # pull 금지가 아니다(기존 /study-coach review 절차의 첫 스텝과 동일).
    if ! git -C "$REPO_PATH" pull --ff-only 2>&1; then
      # fail-loud: stale 채점은 fail-silent 재발이다(감시 ⑦). 채점 스킵 + rc=1로 재시도 유도.
      echo "⚠ ai-infra-lab pull 실패(발산/네트워크) — stale 채점 금지, 오늘 LLM 리뷰 스킵. 수동 해소 필요."
      SKIP_REVIEW="pull-failed"
    else
      LASTREV="$(grep -oE '^### [0-9]{4}-[0-9]{2}-[0-9]{2}' "$VAULT/.claude/runtime/study-state.md" 2>/dev/null | tail -1 | cut -d' ' -f2)"
      [ -z "$LASTREV" ] && LASTREV="1970-01-01"
      NEWC="$(git -C "$REPO_PATH" log --since="$LASTREV 23:59:59" --oneline 2>/dev/null | wc -l | tr -d ' ')"
      if [ "$NEWC" -eq 0 ]; then
        echo "commit gate: $LASTREV 이후 신규 커밋 0 — LLM 채점 스킵(브리핑만). 무커밋일은 정상 침묵."
        SKIP_REVIEW="no-commits"
      else
        echo "commit gate: 신규 커밋 ${NEWC}건 — 채점 진행."
      fi
    fi
  else
    echo "⚠ ai-infra-lab 없음($REPO_PATH) — 이 Mac은 브리핑 전용, LLM 채점 스킵."
    SKIP_REVIEW="no-repo"
  fi

  if [ -n "$SKIP_REVIEW" ]; then
    rc=0
    [ "$SKIP_REVIEW" = "pull-failed" ] && rc=1   # 스탬프 미갱신 → 다음 로그인/슬롯 재시도
  else
  # sonnet: 검토·채점은 중간 티어로 충분(automation-safety: 무인은 cheapest tier).
  # allowlist: study-brief.py 실행 + git(ai-infra-lab 읽기/pull) + runtime 파일 쓰기.
  "$CLAUDE_BIN" -p "/study-coach review — 어제 새 산출물이 없으면 진도를 바꾸지 말고 오늘 브리핑만 생성하라." \
    --model sonnet \
    --permission-mode acceptEdits \
    --allowedTools "Bash(python3 .claude/study-brief.py:*),Bash(git:*),Read,Write,Edit,Glob,Grep" \
    2>&1
  rc=$?
  fi
  echo "=== [$(date '+%F %T')] exit=$rc gate=${SKIP_REVIEW:-review-ran} ==="

  # 2차 방어선: review는 .claude/runtime/ 만 변경해야 한다. 프롬프트 오판으로 KB/메커니즘을 건드렸으면
  # auto-commit/push 전에 되돌린다(동의 없는 생성물 차단). ai-infra-lab은 별도 repo라 vault git status에 안 잡힘.
  bash "$VAULT/.claude/stray-guard.sh" runtime "$STRAY_BASELINE"

  # 완주 영수증 (2026-08-25): 채점이 실제로 돌았다면(게이트 통과) study-state.md에 오늘 날짜
  # 리뷰 로그가 남아야 한다 — 그게 이 루프의 유일한 durable 산출물이다.
  # 근거: radar 26일 침묵·kb-sync duty-③ 누락과 같은 부류. "LLM이 돌았고 exit=0"은 완주의 증거가
  # 아니다. 게이트로 스킵된 날(no-commits/no-repo/pull-failed)은 대상 아님(정상 침묵).
  if [ -z "$SKIP_REVIEW" ] && [ "$rc" -eq 0 ]; then
    if ! grep -qE "^### $(date +%F)" "$VAULT/.claude/runtime/study-state.md" 2>/dev/null; then
      echo "⚠ 채점 미완주: 게이트를 통과해 LLM 리뷰가 돌았는데 study-state.md에 오늘 리뷰 로그가 없다."
      echo "  채점 결과 유실 — 체크박스·진도가 미반영일 수 있다. /study-coach review 재실행 필요."
      rc=1
    fi
  fi

  # LLM 리뷰가 어떤 이유로든(사용 한도·네트워크) 오늘 브리핑을 못 냈으면 0-LLM 엔진으로 직접 보장.
  # study-brief.py --brief-only는 last_brief_date를 안 건드려, 한도 리셋 후 재시도가 채점을 재수행할 수 있다.
  # rc 무관하게 "오늘 날짜 브리핑 존재?"로 게이트 → 실패 케이스에서만 발동(성공 시 중복 overwrite 없음).
  if ! grep -q "date=$(date +%F)" "$TODAY_FILE" 2>/dev/null; then
    python3 "$VAULT/.claude/study-brief.py" --brief-only && echo "(fallback: study-brief.py로 오늘 브리핑 생성 — LLM 리뷰 실패/스킵)"
  fi

  # macOS 알림 (2026-08-23 개정): 무커밋일은 무알림 — 매일 알림은 죄책감 부채를 만든다(아키텍처 §5).
  # 알림 조건: 채점이 실제로 돌았거나(review-ran), 사용자 행동이 필요한 실패(pull-failed)만.
  # no-commits/no-repo 침묵은 정상 상태이고, 루프 사망 감시는 session-context 데드맨 배너가 담당.
  if [ "$SKIP_REVIEW" = "pull-failed" ]; then
    osascript -e "display notification \"ai-infra-lab pull 실패 — 발산 수동 해소 필요\" with title \"⚠ study-coach\" sound name \"Basso\"" 2>/dev/null || true
  elif [ -z "$SKIP_REVIEW" ] && grep -q "date=$(date +%F)" "$TODAY_FILE" 2>/dev/null; then
    NOTE="$(grep -m1 '^\*\*W' "$TODAY_FILE" 2>/dev/null | sed 's/\*\*//g' | cut -c1-110)"
    [ -z "$NOTE" ] && NOTE="오늘의 학습 브리핑이 준비됐어요"
    osascript -e "display notification \"${NOTE//\"/\\\"}\" with title \"📚 AI Infra 학습\" sound name \"Glass\"" 2>/dev/null || true
  fi

  # span 종료 — 완주 가드가 rc를 바꾼 뒤에 닫는다. gate attr이 '정상 침묵'과 '실패'를 구분한다.
  if [ -n "$SPAN" ]; then
    SPAN_ST=error; [ "$rc" -eq 0 ] && SPAN_ST=ok
    python3 "$VAULT/.claude/span.py" end "$SPAN" --status "$SPAN_ST" \
      --attr "rc=$rc" --attr "gate=${SKIP_REVIEW:-review-ran}" >/dev/null || true
    # stdout만 버린다 — stderr는 로그로 흘러야 orphan(계측 버그) 경고가 보인다(fail-loud 유지).
  fi

  # 무인 런의 커밋·push를 훅에 의존하지 않고 직접 수행 (2026-08-25).
  # 근거(실측): headless 런에서 SessionEnd 훅이 `Hook cancelled`로 33회 취소됐다(radar 27·kb-sync 6).
  # Stop 훅의 turn 커밋은 살아있어 로컬 커밋은 됐지만 push는 SessionEnd 전용이라 누락돼 왔다 —
  # 멀티맥 vault에서 push 누락은 다른 Mac이 낡은 study-state로 다음 런을 도는 것을 뜻한다.
  # auto-commit.py를 재사용하므로 발산 감지·sync-status 마커가 중복 구현되지 않는다(멱등).
  echo '{"hook_event_name":"SessionEnd"}' | CLAUDE_PROJECT_DIR="$VAULT" python3 "$VAULT/.claude/hooks/auto-commit.py" >/dev/null 2>&1 || true

  [ "$rc" -eq 0 ] && date +%s > "$STAMP"
} >> "$LOG" 2>&1

if [ "$(stat -f%z "$LOG" 2>/dev/null || echo 0)" -gt 524288 ]; then
  tail -c 262144 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
