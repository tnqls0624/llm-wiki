---
description: 임의 자료(URL·파일·텍스트)를 스크럽 후 KB 노트로 박제한다
argument-hint: <URL 또는 파일 경로 또는 붙여넣은 텍스트>
---

# KB Ingest: 임의 자료를 KB 노트로 박제

대상: `$ARGUMENTS`

외부 자료를 KB에 통합한다. Claude Code 관련이면 `Claude/`에, 다른 주제면 새 주제 디렉토리에 노트를 만든다. KB 노트 형식은 frontmatter 3필드(`title`/`updated`/`sources`) + 한국어 본문 + `[[위키링크]]` 교차참조 + 말미 `## 원본 문서` URL 목록을 따른다.

## 1. 자료 수집
- 대상이 URL이면 본문을 가져온다(`curl -s <url>` 우선, 막히면 WebFetch/WebSearch). 파일 경로면 Read. 붙여넣은 텍스트면 그대로 사용한다.
- 노이즈(광고·네비게이션)는 버리고 핵심(개념·주장·절차·예시)만 남긴다.

## 2. 크리덴셜 스크럽 (필수)
- 외부 자료엔 토큰·키·비밀번호가 섞일 수 있다. **수집한 내용을 임시 파일로 쓴 뒤** `python3 .claude/scrub-secrets.py "<임시 파일>"`로 마스킹(`<REDACTED:...>`)한다.
- 마스킹된 항목이 있으면 보고에 명시하고, 실 토큰이면 사용자에게 제공자(GitHub 등) 폐기·교체를 권한다. (`secret-scan` PostToolUse 훅이 2차 안전망)

## 3. 주제 판별 → 노트 위치 결정
- **Claude Code 관련**(CLI·설정·훅·MCP·스킬·SDK 등): `Claude/`의 주제가 맞는 기존 노트에 새 섹션으로 통합한다. 그 노트 frontmatter `sources`에 출처를 추가한다(공식 슬러그가 아니면 URL/식별자를 적는다). 적합한 노트가 없고 분량이 충분하면 번호를 이어서 새 `Claude/NN 제목.md`를 만든다.
- **다른 주제**: 새 주제 디렉토리를 만든다 — `<주제>/`(예: `Rust/`)에 노트 `<주제>/NN 제목.md`를 두고, `Claude/` 패턴과 동일하게 **`<주제>/<주제>.md` MOC 허브**를 함께 만든다(MOC frontmatter `sources`는 빈 배열, 본문은 그 디렉토리 노트들의 카탈로그). 노트 본문은 `허브: [[<주제>]]`로 그 MOC를 가리킨다.

## 4. 노트 작성
- frontmatter 3필드 채우기: `title`, `updated`(오늘), `sources`(출처 슬러그/URL 배열).
- 본문은 한국어 사용법/요약 레퍼런스. 관련 KB 노트로 `[[위키링크]]` 교차참조를 건다(파일명만). 기존 내용과 모순되면 삭제하지 말고 `> [!warning] 모순` 콜아웃으로 표시.
- 말미에 `## 원본 문서` 섹션으로 출처 URL을 적는다.

## 5. 갱신 의무
- `.claude/rules/vault-rules.md`의 "Update duty (CANONICAL — 3 steps)"를 수행한다(정본 참조 — 단계·수치는 여기서 재명세하지 않는다). MOC는 만진 디렉토리의 허브(`Claude/Claude.md` 또는 새 주제의 `<주제>/<주제>.md`)를 갱신한다.
- **새 주제 디렉토리를 만들었다면** `hot.md`의 `## Vault state`에도 그 디렉토리를 추가한다(KB가 더 이상 `Claude/`만이 아님을 boot context에 반영).

## 6. 보고
무엇을 캡처했고(스크럽 결과 포함), 어느 노트/디렉토리에 박제했고, 어떤 교차링크·모순을 만들었는지 요약해 보고하라.
