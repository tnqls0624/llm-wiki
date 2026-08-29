#!/bin/bash
# STRAY 가드 — 무인 cron 런이 허용 범위 밖 파일을 건드렸으면 커밋 경계 이전에 되돌린다.
# automation-safety의 'guard before the commit boundary' 불변식을 기계적으로 강제하는 2차 방어선.
# (1차는 커맨드 프롬프트 + allowlist.) 프롬프트 지시는 enforcement가 아니다 — 이 가드가 그 보강이다.
#
# 사용: bash stray-guard.sh <mode> [baseline-file]   (git repo 작업트리에서 cd 된 상태로 호출)
#   mode=runtime  : radar/study — .claude/runtime/ 만 허용, 그 밖 전부 STRAY (durable 생성 0)
#   mode=kb       : kb-sync — KB 노트(토픽 디렉터리)·.claude/runtime/ 은 허용,
#                   .claude/ 의 **메커니즘**(runtime 외)만 STRAY
#   mode=snapshot : 지금 dirty한 경로 목록을 stdout에 출력하고 종료(baseline 생성용, 아무것도 안 고침)
#
# **baseline-file**: 무인 런이 시작되기 *전부터* dirty했던 경로 목록(= 사람이 하던 작업).
# 그 경로들은 STRAY에서 제외한다. 없던 동안 실제 사고가 났다(2026-08-29): 09:30 study-coach cron이
# 사람이 편집 중이던 미커밋 `.claude/kb-eval.py`를 STRAY로 판정해 되돌렸고, 작업이 통째로 사라졌다.
# 무인 런의 책임 범위는 **그 런이 만든 변경**이지, 우연히 같은 시각에 열려 있던 사람의 작업이 아니다.
#
# STRAY 처리: 추적 파일은 `git checkout HEAD`로 원복, 미추적 신규 파일은 `rm`으로 삭제.
# 되돌린 경로 목록을 stdout에 출력(없으면 무출력). 항상 exit 0(정보성, 세션 흐름 비차단).
MODE="${1:-runtime}"
BASELINE="${2:-}"

# 경로 추출을 python에 맡긴다(2026-08-25 수정). 이전 판은 `--porcelain` 텍스트를 `sed 's/^...//'`
# 로 잘랐는데, git은 **공백·특수문자가 있는 경로를 따옴표로 감싼다** — `core.quotepath=false`는
# non-ASCII escape만 끄고 이 따옴표는 남긴다. 그래서 `"80 Tooling/04 설정.md"` 같은 항목은
# `^\.claude/` 매칭에서 탈락하거나, 통과해도 따옴표째로 `git checkout`/`rm` 에 넘겨져 조용히
# 아무 일도 하지 않았다. 이 vault의 KB 노트는 **전부 공백+한글**이라 사실상 상시 무력이었고,
# "STRAY reverted"를 출력하면서 실제로는 되돌리지 않는 거짓 성공이었다.
# `-z`(NUL 구분, 따옴표 없음)로 읽고 rename/copy의 **원본 경로까지** 목록에 넣는다 — 이전에는
# rename이 공백 유무와 무관하게 통째로 누락됐다.
_stray_paths() {
  git status --porcelain -z --untracked-files=all 2>/dev/null | python3 -c '
import sys
buf = sys.stdin.buffer.read().split(b"\0")
out, i = [], 0
while i < len(buf):
    e = buf[i]
    if not e:
        i += 1
        continue
    xy = e[:2].decode("ascii", "replace")
    out.append(e[3:].decode("utf-8", "surrogateescape"))
    if xy[0] in ("R", "C"):        # rename/copy 는 다음 NUL 필드가 원본 경로
        i += 1
        if i < len(buf) and buf[i]:
            out.append(buf[i].decode("utf-8", "surrogateescape"))
    i += 1
for p in out:
    print(p)
'
}

if [ "$MODE" = "snapshot" ]; then
  _stray_paths
  exit 0
fi

if [ "$MODE" = "kb" ]; then
  STRAY=$(_stray_paths | grep -E '^\.claude/' | grep -vE '^\.claude/runtime/' || true)
else
  STRAY=$(_stray_paths | grep -vE '^\.claude/runtime/' || true)
fi

# 런 시작 전부터 dirty했던 경로(=사람의 작업)를 제외한다. 정확 일치로만 뺀다.
if [ -n "$STRAY" ] && [ -n "$BASELINE" ] && [ -f "$BASELINE" ]; then
  STRAY=$(printf '%s\n' "$STRAY" | grep -vxF -f "$BASELINE" || true)
fi

[ -z "$STRAY" ] && exit 0

# 추적 판정은 **인덱스가 아니라 HEAD** 기준이다. `git ls-files --error-unmatch` 를 쓰던 동안
# `git mv` 로 옮겨진 파일의 원본 경로는 이미 인덱스에서 지워져 '미추적'으로 판정되고, 그 결과
# 존재하지 않는 경로에 `rm -f` 를 걸어 no-op — rename이 원복되지 않고 살아남았다.
printf '%s\n' "$STRAY" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  if git cat-file -e "HEAD:$f" 2>/dev/null; then
    git checkout HEAD -- "$f" 2>/dev/null   # HEAD에 있던 파일: 내용 + 인덱스 상태까지 원복
  else
    git rm -q -f --cached "$f" 2>/dev/null  # 인덱스에만 올라간 신규가 있으면 언스테이지
    rm -f "$f" 2>/dev/null                  # 워킹트리 신규 파일 삭제
  fi
done
printf 'STRAY reverted (mode=%s):\n%s\n' "$MODE" "$STRAY"
exit 0
