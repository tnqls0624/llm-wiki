#!/bin/bash
# STRAY 가드 — 무인 cron 런이 허용 범위 밖 파일을 건드렸으면 커밋 경계 이전에 되돌린다.
# automation-safety의 'guard before the commit boundary' 불변식을 기계적으로 강제하는 2차 방어선.
# (1차는 커맨드 프롬프트 + allowlist.) 프롬프트 지시는 enforcement가 아니다 — 이 가드가 그 보강이다.
#
# 사용: bash stray-guard.sh <mode>    (반드시 git repo의 작업트리에서, cd 된 상태로 호출)
#   mode=runtime : radar collect — .claude/runtime/ 만 허용, 그 밖 전부 STRAY (durable 생성 0)
#   mode=kb      : kb-sync — KB 노트(토픽 디렉터리)·.claude/runtime/ 은 허용,
#                  .claude/ 의 **메커니즘**(skills/agents/commands/rules/hooks/scripts/tests 등 runtime 외)만 STRAY
#
# STRAY 처리: 추적 파일은 `git checkout`으로 원복, 미추적 신규 파일은 `rm`으로 삭제.
# 되돌린 경로 목록을 stdout에 출력(없으면 무출력). 항상 exit 0(정보성, 세션 흐름 비차단).
MODE="${1:-runtime}"

if [ "$MODE" = "kb" ]; then
  STRAY=$(git -c core.quotepath=false status --porcelain --untracked-files=all 2>/dev/null \
            | sed 's/^...//' | grep -E '^\.claude/' | grep -vE '^\.claude/runtime/' || true)
else
  STRAY=$(git -c core.quotepath=false status --porcelain --untracked-files=all 2>/dev/null \
            | sed 's/^...//' | grep -vE '^\.claude/runtime/' || true)
fi

[ -z "$STRAY" ] && exit 0

printf '%s\n' "$STRAY" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    git checkout -- "$f" 2>/dev/null      # 추적 파일: 원복
  else
    rm -f "$f" 2>/dev/null                 # 미추적 신규 파일: 삭제
  fi
done
printf 'STRAY reverted (mode=%s):\n%s\n' "$MODE" "$STRAY"
exit 0
