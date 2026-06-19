# obsidian_sync

Claude Code 지식 베이스 + 포터블 자동화 프레임워크를 담은 Obsidian vault.

- **토픽 디렉토리** — 한국어 KB 콘텐츠. 각 `<Topic>/`는 노트 + `<Topic>/<Topic>.md` MOC 허브. 현재: `Claude/`(Claude Code 공식문서, 26) · `AI-Infra/`(6) · `Infra/`(10) · `Meta/`(vault 자기진단).
- **`.claude/`** — 커맨드·에이전트·스킬·룰·훅·cron으로 이뤄진 프레임워크(메커니즘). 다른 vault로 복사 가능.

전체 사용법은 [`README.md`](README.md), AI 운영 규칙 정본은 [`.claude/rules/vault-rules.md`](.claude/rules/vault-rules.md)와 [`.claude/rules/automation-safety-rules.md`](.claude/rules/automation-safety-rules.md)에 있다(둘 다 매 세션 자동 로드).

## 변경 동기화 의무 (CANONICAL)

**무언가를 추가하거나 수정하면, 그것을 기록하는 문서를 같은 변경 안에서 반드시 함께 갱신한다.** 코드·콘텐츠와 그것을 설명하는 문서가 갈라지면 안 된다. 변경을 끝내기 전에 아래 표를 확인한다.

| 무엇을 바꿨나 | 함께 갱신할 파일 |
|---|---|
| 새/변경 command·agent·skill·rule·hook·script (`.claude/`) | ① `README.md` 인벤토리 표 ② `.claude/runtime/hot.md` Framework 줄 ③ **새 메커니즘이면** `.claude/tests/test_mechanisms.py`에 계약 테스트 추가 |
| KB 노트 (`Claude/` 등 토픽 디렉토리) | `vault-rules.md`의 **Update duty (3 steps)**: `updated` bump → MOC 반영 → `hot.md` 한 줄 |
| **새 토픽 디렉토리 추가** (`<Topic>/`) | ① `<Topic>/<Topic>.md` MOC 생성(`type: moc`, `sources: []`) ② `README.md` 인벤토리 ③ `hot.md` Content 줄에 토픽+한 줄 설명 ④ `radar` 라우팅이 필요하면 `radar-collect.py` source-tag + `vault-rules.md` 라우팅 문장 ⑤ 인접 토픽으로의 cross-link 최소 1개(사일로 방지) |
| frontmatter 스키마 (`type` 등 필드·enum) | `.claude/kb-required-fields.txt` + `.claude/kb-allowed-types.txt`(정본) → `vault-rules.md` Note format → `kb-lint.py`·`kb-lint-check.py` 검증 → `test_mechanisms.py` (모두 같은 변경 안에서) |
| cron·자동화 스케줄/동작 | `README.md` + `hot.md` (안전 불변식은 `automation-safety-rules.md`) |
| `settings.json` (훅·권한 등록) | `hot.md` Framework 줄의 hooks·이벤트 수 |

세부 단계는 여기서 재명세하지 않는다 — `.claude/rules/`(vault-rules·automation-safety)를 정본으로 따른다. 규칙끼리 충돌하면 **이 `CLAUDE.md`가 우선**이며, 불일치를 발견하면 묵시적으로 수렴하지 말고 사용자에게 보고한다.

## 변경 후 검증
- 프레임워크 변경 → `bash .claude/tests/run-tests.sh` 통과 확인.
- KB 변경 → `python3 .claude/kb-lint.py` (필요 시 `--online`) 통과 확인.

> 이 문서는 매 세션 자동 로드된다(프로젝트 메모리). 간결하게 유지한다 — 상세는 위 링크 문서로 위임한다.
