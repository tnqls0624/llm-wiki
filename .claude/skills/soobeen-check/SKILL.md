---
name: soobeen-check
description: 개인화 학습 세션 마감 체크. 사용자가 "마감 체크", "오늘 끝", "오늘 여기까지" 등 학습 세션 종료를 선언하면 감시 목록 ①~⑦(soobeen-profile)을 실제 산출물(git status·diff·log.md)과 대조해 통과/미달 표를 반환한다. ai-infra-lab은 읽기 전용 — 수정·커밋은 사용자가 직접. 대화형 전용 — 무인 cron 연결 금지.
---

# soobeen-check — 세션 마감 체크

`.claude/rules/soobeen-profile.md`의 감시 목록을 산출물과 기계적으로 대조한다. 채점하지 않는다(채점은 `/study-coach review`의 몫) — 커밋 전에 스스로 잡을 수 있는 것을 잡는 프리플라이트다.

## 0. 대상
- repo: `study-state.md` 메타의 `repo_path`(기본 `~/Desktop/Project/ai-infra-lab`), `.claude/runtime/study-local.conf`가 있으면 override.
- **ai-infra-lab은 읽기 전용** — `git status/diff/log`와 Read만. 이 스킬은 어떤 파일도 수정·커밋하지 않는다(vault 포함 — 보고만).

## 1. 증거 수집
- `git -C <repo> status --porcelain` — 미커밋 잔존 확인
- `git -C <repo> log --format='%h|%B' -8` — 오늘 커밋 + 메시지 본문(펜스·제목 검사)
- 오늘 커밋 범위의 `git diff -- '*.py'` — 코드 표면 검사
- `<repo>/docs/log.md` 오늘 항목 · `.claude/runtime/study-today.md`(오늘 완료 기준) · `study-state.md` 검토 로그 최근 항목(verbatim 대조용)

## 2. 감시 목록 대조 (각각 통과/미달/해당없음 + 한 줄 근거)

| # | 체크 | 미달 판정 |
|---|---|---|
| ① 서술 | log.md 오늘 항목에 "배운 것"이 **자기 말**로 있나 | "실행했다"뿐이거나, 문장이 study-today.md·검토 로그·코치 발화와 동일(verbatim) |
| ② 커밋 | worktree clean + 오늘 산출물이 커밋에 존재 | 미커밋 변경 잔존(채점은 커밋 기준 — 두 Mac 동기화 전제) |
| ③ 실패 기록 | 세션 중 실패가 "발생한 문제" 칸에 있나 | 칸이 "없음"인데 본문·출력에 실패 흔적(실패한 명령·에러·안 된 것) 있음 |
| ④ 코드 표면 | 오늘 diff의 .py | 줄 끝 세미콜론, 죽은 주석(`# raise NotImplementedError` 등), 미사용 import |
| ⑤ 계획 | "다음에 할 것"을 본인이 썼나 | "너가 적어줘"류 위임 |
| ⑥ 커밋 위생 | 오늘 커밋 메시지 | 코드펜스(백틱 3개) 잔재, "WXDY: 학습" 꼴 무정보 제목 |
| ⑦ fail-silent | 오늘 diff의 except/폴백 분기 | 실패가 exit code·로그로 드러나지 않음(bare return, silent fallback) |

## 3. 출력
표 다음에, 미달 항목마다 **5분 내 실행 가능한 다음 스텝** 1개. 반드시 **빈칸/키워드 템플릿**으로 — 완성 문장을 주면 복붙된다(soobeen-profile 코칭 원칙).
- ① 미달 예: log.md에 `새로 안 것: 1) ___ (왜 그런가: ___)` 채워 넣기 — 먼저 기억으로 쓰고 자료와 대조.
- ② 미달 예: `git add <파일> && git commit` 남음. 메시지 키워드: `<스코프>: <무엇을> — <왜>`.

모두 통과면 "마감 완료 — 기록+커밋이 한 동작으로 끝났다" 한 줄로 끝낸다. 통과를 부풀리지 않는다(정직한 보류 — 애매하면 미달로).
