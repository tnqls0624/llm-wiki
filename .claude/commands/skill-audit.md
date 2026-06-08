---
description: 설치된 skill들의 description 토큰 풋프린트를 집계해 매 세션 상시 비용을 점검한다
argument-hint: [--global] [--plugins]
---

# skill-audit: skill description 토큰 풋프린트 점검

인자: `$ARGUMENTS` (`--global`=글로벌 `~/.claude/skills/` 포함, `--plugins`=플러그인 marketplace skill도 포함)

skill의 `description`은 **트리거 여부와 무관하게** 매 세션 시스템 프롬프트에 상시 로드된다(출처: dev.to "Skills cost tokens even when they don't fire" — 5개 skill 7시간 측정). skill이 늘수록 이 상시 비용이 누적되므로 주기적으로 점검해 다이어트 후보를 찾는다.

## 1. skill 수집
- 프로젝트 skill: `.claude/skills/*/SKILL.md`를 Glob으로 찾는다. `--global`이면 `~/.claude/skills/*/SKILL.md`도, `--plugins`면 `~/.claude/plugins/**/SKILL.md`도 포함한다.
- 각 SKILL.md의 frontmatter에서 `name`과 `description`을 추출한다.
- **대량일 때(플러그인은 수백 개)는 개별 Read 대신 python 한 번으로 일괄 파싱하라** — glob으로 경로를 모아 각 파일 앞부분의 frontmatter `description`/`name`만 정규식으로 뽑고 글자수를 센다(토큰 환산은 §2).

## 2. 토큰 추정
- 각 `description`의 길이를 추정한다 — 보수적으로 **글자수 ÷ 3** (영어 ~4자/토큰, 한국어 ~2자/토큰의 중간). `name`도 합산한다.
- SKILL.md **본문**은 트리거될 때만 로드되므로 description과 분리해 별도 표기한다(상시 비용 = description, 발동 비용 = 본문).

## 3. 보고
- description 추정 토큰 **내림차순 표**(skill명 · 추정 토큰 · 글자수). proj/global/plugin scope를 함께 표기한다.
- **상시 로드 총합**(모든 description 합)을 보고한다 — 이것이 "skill을 한 번도 안 써도 매 세션 내는 비용".
- `--plugins`일 때는 skill 수가 많으므로 **marketplace/플러그인별 그룹 집계**(플러그인명 · skill 수 · 토큰 합)를 추가하고 비용 큰 플러그인을 상위에 보인다 — 안 쓰는 플러그인 비활성화가 가장 큰 절감 레버다.
- ~70토큰(약 200자)을 크게 넘는 description은 **다이어트 후보**로 표시하고, 트리거 정확도(언제 발동하는지)를 해치지 않는 선에서 압축안을 제안한다(로컬 skill만 수정 가능 — 플러그인은 비활성화로 대응).

## 한계 (명시)
- 토큰 수는 추정치다(정확한 토크나이저 미사용) — 상대 비교·이상치 탐지용으로 충분하다.
- description 외 SKILL.md 본문·번들 파일의 발동 시 비용은 별도이며 이 점검 범위가 아니다.
- `--plugins` 스캔은 `~/.claude/plugins/` 전체를 보므로 **버전 중복·비활성 플러그인이 섞여 과대추정될 수 있다** — 실제 세션에 로드되는 활성 목록은 `/plugin`으로 확인한다. 그룹 집계는 "어느 플러그인이 비싼가"의 상대 비교용이다.
