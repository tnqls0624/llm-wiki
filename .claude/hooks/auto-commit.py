#!/usr/bin/env python3
"""Stop/SessionEnd hook — turn·세션 종료 시 vault 변경분을 git에 자동커밋.
Stop은 매 turn 커밋만, SessionEnd는 누락분 flush + 원격 push(origin). 매 turn push는
느려서 세션 종료 시 1회만 한다. .git 없으면 no-op, 변경 없으면 커밋 skip(push는 시도).
push 실패(충돌·네트워크)해도 세션을 막지 않는다(다음 종료에 재시도). 항상 exit 0."""
import json, sys, os, subprocess, datetime, re

# CLAUDE_PROJECT_DIR(설정 hook이 `$CLAUDE_PROJECT_DIR`로 항상 전달)을 신뢰한다.
# stdin의 cwd로 덮어쓰면, Bash cwd가 vault 밖의 다른 git repo일 때
# 그 repo에 vault 변경을 커밋하는 오염이 생긴다.
root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
data = {}
try:
    data = json.load(sys.stdin) or {}
    if not os.environ.get("CLAUDE_PROJECT_DIR"):
        root = data.get("cwd") or root
    # 재진입 방지: 이미 Stop hook 처리 중이면 즉시 종료
    if data.get("stop_hook_active"):
        sys.exit(0)
except Exception:
    pass


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=root,
        capture_output=True, text=True, timeout=30,
    )


def sync_push():
    """SessionEnd push — blind push 대신 fetch로 발산을 먼저 감지(멀티맥 안전).
    behind==0 → fast-forward 안전 push. ahead==0(따라잡기만) → ff-only merge(충돌 불가).
    양쪽 다 앞선 발산이면 무인 merge/rebase는 위험 → push 보류 + 마커로 다음 세션 부팅에 경고
    (session-context 훅이 sync-status.txt를 표면화). 성공 시 마커 제거."""
    status = os.path.join(root, ".claude", "runtime", "sync-status.txt")

    def clear():
        try:
            os.remove(status)
        except OSError:
            pass

    # upstream 미설정(첫 push 등)이면 기존대로 한 번 시도
    if git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").returncode != 0:
        git("push")
        return
    git("fetch", "--quiet")
    counts = git("rev-list", "--count", "--left-right", "@{u}...HEAD")
    behind = ahead = 0
    if counts.returncode == 0 and counts.stdout.split():
        try:
            behind, ahead = (int(x) for x in counts.stdout.split()[:2])
        except Exception:
            behind = ahead = 0
    if behind == 0:
        git("push"); clear()                         # fast-forward 안전
    elif ahead == 0:
        git("merge", "--ff-only", "@{u}"); clear()   # 따라잡기만 — 충돌 불가
    else:                                            # 발산 — 무인 처리 금지, 사람에게 알림
        try:
            os.makedirs(os.path.dirname(status), exist_ok=True)
            with open(status, "w", encoding="utf-8") as f:
                f.write(f"⚠ git 발산: 로컬 {ahead} ahead · 원격 {behind} behind. "
                        f"자동 push 보류됨 — `git pull --rebase` 후 충돌 해결 필요.\n")
        except OSError:
            pass


try:
    if not os.path.isdir(os.path.join(root, ".git")):
        sys.exit(0)  # git repo 아님 — 조용히 종료
    # vault 마커 확인 — root가 엉뚱한 repo면 커밋하지 않는다(오염 방지).
    # 루트 CLAUDE.md는 이 vault엔 없을 수 있으므로(vault-rules: 미래 슬롯, 현재 부재) `.claude/`
    # 프레임워크 디렉터리도 마커로 인정한다 — 둘 중 하나라도 있으면 이 vault다.
    # (CLAUDE.md 단독 마커였을 때 리셋 후 커밋이 영구 no-op 되던 버그 수정, 2026-06-08.)
    if not (os.path.isfile(os.path.join(root, "CLAUDE.md")) or os.path.isdir(os.path.join(root, ".claude"))):
        sys.exit(0)

    # identity 없는 환경(fresh/CI)에서도 commit이 silent-fail 하지 않게 fallback.
    # setdefault라 operator의 기존 user.name/email이 있으면 그대로 보존된다.
    if git("var", "GIT_COMMITTER_IDENT").returncode != 0:
        os.environ.setdefault("GIT_AUTHOR_NAME", "Claude Auto")
        os.environ.setdefault("GIT_AUTHOR_EMAIL", "claude-auto@local")
        os.environ.setdefault("GIT_COMMITTER_NAME", "Claude Auto")
        os.environ.setdefault("GIT_COMMITTER_EMAIL", "claude-auto@local")

    git("add", "-A")
    # 정크 가드: 점 2개 이상으로 시작하는 파일명(예: '....md')의 신규 추가/수정만 커밋에서 제외.
    # 삭제(D)는 통과시킨다 — 안 그러면 정크 '삭제'까지 unstage되어 정크가 영영 안 지워진다
    # (2026-05-31: ....md 삭제가 18h 동안 커밋 안 되던 버그 수정).
    for line in git("diff", "--cached", "--name-status").stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or parts[0].startswith("D"):
            continue  # 삭제는 그대로 커밋 — 정크 제거를 막지 않는다
        f = parts[-1]
        if re.match(r"^\.{2,}[a-z0-9]*$", os.path.basename(f).lower()):
            git("reset", "-q", "--", f)
    # 스테이징된 변경이 있으면 커밋(없으면 커밋만 skip)
    if git("diff", "--cached", "--quiet").returncode != 0:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        git("commit", "-m", f"auto: {stamp} Claude 세션", "--no-verify")

    # SessionEnd(세션 종료) 때만 원격 push — 매 turn push는 느리고 과하다.
    # fetch로 발산을 먼저 감지해 blind push 충돌을 피한다(강제 push 안 함, 네트워크 실패는 무시).
    if data.get("hook_event_name") == "SessionEnd":
        sync_push()
except Exception:
    pass  # 어떤 실패도 세션을 막지 않는다

sys.exit(0)
