# obsidian_sync — Claude Code KB & 자동화 프레임워크

Obsidian vault 하나에 **두 가지**가 들어 있다:

1. **`Claude/` — 지식 베이스(콘텐츠)**: Claude Code 공식 문서(code.claude.com/docs, 145페이지)를 한국어로 종합한 26개 노트 + `Claude/Claude.md` MOC 허브.
2. **`.claude/` — 포터블 프레임워크 패키지(메커니즘)**: KB를 묻고·갱신·점검·박제하고, Claude 생태계를 매일 자동 수집하는 커스텀 커맨드·에이전트·스킬·룰·훅·cron. 다른 vault로 그대로 복사 가능.

> 이 README는 **Claude Code 기본 기능이 아닌, 이 프로젝트가 추가한 것**의 사용법만 정리한다. 기본 CLI 사용법은 `Claude/` KB를 참고한다.

핵심 원칙(메커니즘 vs 콘텐츠 분리, 갱신 의무 등)의 정본은 `.claude/rules/vault-rules.md`이며 매 세션 자동 로드된다.

---

## 📁 디렉토리 구조

```
obsidian_sync/
├── Claude/                      # 콘텐츠: Claude Code 공식문서 KB (26 노트 + MOC)
│   ├── 01 시작하기.md … 26 변경 이력과 용어집.md
│   └── Claude.md                # MOC 허브 (학습 경로 + 전체 지도)
├── .claude/                     # 메커니즘: 포터블 프레임워크
│   ├── commands/                # 슬래시 커맨드 7개
│   ├── agents/                  # 서브에이전트 2개
│   ├── skills/                  # 스킬 (kb-assistant)
│   ├── rules/                   # 자동 로드 룰 2개
│   ├── hooks/                   # 이벤트 훅 4개
│   ├── tests/                   # 계약 테스트 (51 케이스)
│   ├── runtime/                 # 휘발성 상태 (hot.md, 큐, ledger, 로그)
│   ├── *.py / *.sh              # 스크립트 + cron 래퍼/설치기
│   └── settings.json            # 훅 등록
└── README.md
```

---

## ⌨️ 슬래시 커맨드 (7개)

세션에서 `/<이름>`으로 호출한다. KB 관련 5개 + 생태계 자동화 2개.

| 커맨드 | 인자 | 용도 |
|---|---|---|
| `/kb-query` | `<질문>` | Claude Code 사용법 질문을 KB에서 찾아 답하고, **새로운 통찰만** 노트에 남긴다 |
| `/kb-ingest` | `<URL·파일·텍스트>` | 외부 자료를 크리덴셜 스크럽 후 KB 노트로 박제 |
| `/kb-save` | `[제목/범위]` | 이번 세션의 대화·탐색 결과를 KB 노트로 박제 |
| `/kb-sync` | `[--deep <노트번호>]` | 공식 문서(llms.txt) 변경분을 슬러그 diff로 잡아 KB에 반영 |
| `/kb-lint` | `[--online]` | KB 무결성 점검(+`--online`은 공식 인덱스와 비교) 후 직접 수정 |
| `/claude-radar` | `[collect\|review]` | Claude 생태계 정보 수집·추천(collect) / 큐 검토·동의 후 생성(review) |
| `/skill-audit` | `[--global] [--plugins]` | 설치된 skill의 description 토큰 풋프린트(매 세션 상시 비용) 점검 |

### 자주 쓰는 흐름
```bash
/kb-query 훅 어떻게 설정해?          # KB에서 답 찾기
/kb-ingest https://example.com/글    # 외부 글을 KB에 박제
/kb-sync                             # 공식 문서 최신화(주 1회 권장)
/kb-lint --online                    # 커버리지 검증
/claude-radar review                 # 오늘 쌓인 생태계 추천 검토
/skill-audit --plugins               # skill 상시 토큰 비용 점검
```

---

## 📡 claude-radar — 매일 Claude 생태계 레이더 (핵심 자동화)

GeekNews·GitHub·Hacker News·Anthropic 공식·dev.to·npm 등 **10개 채널**에서 Claude Code 활용 정보(새 skill·agent·MCP·기능·패턴)를 매일 자동 수집해, "우리 프레임워크에 더하면 좋을 것"과 "KB에 박제할 지식"을 추천한다.

### 동작 (2단계 — "동의 후 추가"를 구조로 보장)
```
[무인]  매일 09:17 (launchd cron)
        → radar-collect.py 가 10개 채널 수집 → seen ledger 로 중복 제거
        → /claude-radar collect 이 분류·추천 → runtime/radar-queue.md 에 적재
        ⚠ 무인 단계는 큐+ledger만 변경 — skill/agent/KB를 절대 생성하지 않는다.

[대화형] 다음 세션 시작 → 큐 대기 항목 자동 노출 (SessionStart 훅)
        → /claude-radar review → 항목 검토 → 동의한 것만 생성·박제
          · skill   → skill-creator
          · agent/command/rule → .claude/ 아래 파일 생성
          · kb-ingest → /kb-ingest 로 KB 박제
```

### 안전 설계
- **collect ↔ review 분리**: 무인 수집은 추천만 쌓고, 실제 생성은 사용자 동의가 있는 대화형 세션에서만.
- **3중 방어선**: ① 커맨드 지시 ② cron allowlist를 `radar-collect.py`로 고정 ③ cron 사후 `git checkout` 가드(`runtime/` 밖 변경 자동 원복).
- **프롬프트 인젝션 차단**: 외부 제목을 수집 단계에서 정제 + 부팅 컨텍스트 주입 시 백틱·"신뢰 불가" 프리앰블로 중립화.

상세 가드레일은 `.claude/rules/automation-safety-rules.md` 참조.

---

## 🤖 서브에이전트 (2개)

격리 컨텍스트에서 도는 위임용 에이전트. `Agent` 도구의 `subagent_type`으로 호출되거나, 커맨드가 무거운 작업을 위임한다. 둘 다 비용 레버로 **sonnet**.

| 에이전트 | 도구 | 용도 |
|---|---|---|
| `kb-guide` | Read·Grep·Glob (**읽기 전용**) | 여러 KB 노트에 흩어진 답을 격리 컨텍스트에서 모아 답변 + 근거 노트명만 반환 (메인 컨텍스트 오염 방지) |
| `kb-updater` | Read·Write·Edit·Glob·Grep·Bash·WebFetch | 공식 문서 변경 반영·다중 노트 동시 갱신 등 무거운 KB 쓰기. 갱신 의무 ①(updated)·②(MOC)는 자기가 수행하되 **hot.md는 건드리지 않는다**(메인 세션 몫) |

---

## 🧠 스킬 (1개)

| 스킬 | 용도 |
|---|---|
| `kb-assistant` | 사용자의 KB 관련 의도("훅 어떻게 설정해", "문서 최신화", "이 글 정리해줘")를 감지해 올바른 kb-* 커맨드로 **라우팅** |

> 플러그인 marketplace로 설치된 다른 스킬(`data:*`, `figma:*`, `claude-mem:*` 등)은 이 프로젝트가 만든 것이 아니다. `/skill-audit --plugins`로 상시 비용을 점검할 수 있다.

---

## 📐 룰 (2개 · 매 세션 자동 로드)

`.claude/rules/*.md`는 세션 시작 시 자동으로 컨텍스트에 주입된다. 충돌 시 `vault-rules.md`가 우선.

| 룰 | 내용 |
|---|---|
| `vault-rules.md` | **핵심 운영 규칙 정본** — 구조(메커니즘/콘텐츠 분리), 노트 형식, 갱신 의무 3단계, 네비게이션 계층, lint, claude-radar |
| `automation-safety-rules.md` | **무인/위임 자동화 가드레일** — 최소 권한, 신뢰 불가 입력 중립화, 다층 방어, 검증(테스트), 비용 |

---

## 🪝 훅 (4 스크립트 / 4 이벤트)

`settings.json`에 등록되어 Claude Code 이벤트에 자동 실행된다.

| 이벤트 | 훅 | 동작 |
|---|---|---|
| SessionStart | `session-context.py` | `hot.md`(L1 부팅 캐시) 주입 + radar 큐 대기 추천 노출 + sync 경고 표면화 |
| PostToolUse (Write/Edit) | `kb-lint-check.py` → `secret-scan.py` | 저장한 파일을 즉시 린트 + 크리덴셜 누출 경고 |
| Stop + SessionEnd | `auto-commit.py` | 변경사항 자동 커밋 + fetch-guarded push(멀티 머신 안전) |

---

## 🛠️ 스크립트 & 자동화

### 스크립트
| 파일 | 용도 |
|---|---|
| `kb-lint.py` | 전 vault 기계 린트(frontmatter·날짜·위키링크). `--online`은 공식 llms.txt와 슬러그 비교 |
| `scrub-secrets.py` | 크리덴셜 탐지·마스킹 코어(GitHub PAT·AWS·OpenAI·Anthropic 등). ingest 시 1차 방어 |
| `radar-collect.py` | claude-radar 수집 엔진(0-LLM, 결정론적). 10개 채널 → dedup → JSON |

### cron 자동화 (launchd)
| 작업 | 스케줄 | 설치 |
|---|---|---|
| `kb-sync` | 월·목 09:07 | `bash .claude/install-kb-sync-cron.sh` |
| `claude-radar` | 매일 09:17 | `bash .claude/install-claude-radar-cron.sh` |

- 둘 다 **anacron 패턴**(전원 꺼짐으로 놓친 슬롯을 로그인 시 보충) + 락 + 로그 로테이션.
- 헤드리스 실행이라 **sonnet** 티어 사용(비용 레버).
- 제거: `launchctl bootout "gui/$(id -u)/com.$(id -un).<작업명>"` + plist 삭제.

---

## ✅ 테스트

```bash
bash .claude/tests/run-tests.sh      # 51개 계약 테스트 (표준 라이브러리만, 의존성 0)
```

격리 임시 vault에서 모든 훅·스크립트를 실제 호출해 계약을 검증한다(silent-fail 회귀 방지). 새 메커니즘을 추가하면 `test_mechanisms.py`에 케이스를 더하는 것이 규칙이다.

---

## 🚚 다른 머신으로 옮기기

`.claude/`는 포터블하게 설계됐다(모든 경로를 스크립트 위치에서 역산). 새 머신에서:

```bash
git clone <repo> && cd obsidian_sync
bash .claude/install-kb-sync-cron.sh        # cron 재등록 (plist는 설치 시점 절대경로로 생성)
bash .claude/install-claude-radar-cron.sh
bash .claude/tests/run-tests.sh             # 동작 검증
```

> `.claude/runtime/`의 cron 로그·anacron stamp는 기기별이라 `.gitignore`로 제외된다. 큐(`radar-queue.md`)와 dedup ledger(`radar-seen.json`)는 공유 콘텐츠라 추적된다.
