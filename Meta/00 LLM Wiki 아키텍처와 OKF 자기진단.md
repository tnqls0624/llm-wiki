---
title: 00 LLM Wiki 아키텍처와 OKF 자기진단
updated: 2026-06-19
type: explanation
sources:
  - https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
  - https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/
  - https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
  - https://llmstxt.org/
  - https://agents.md/
  - https://neo4j.com/blog/genai/what-is-graphrag/
  - https://zettelkasten.de/atomicity/guide/
---

# LLM Wiki 아키텍처와 OKF 자기진단

허브: [[Meta]]

이 vault가 "LLM wiki"로서 어떤 표준 계보에 속하고, 무엇을 잘하며 무엇을 의도적으로 안 하는지 박제한 메타 노트. 2026-06-19, 구글 **Open Knowledge Format(OKF) v0.1** 발표([news.hada.io](https://news.hada.io/topic?id=30622))를 계기로 30+ 소스를 리서치해 10개 차원으로 vault를 자기진단한 결과다. 향후 `/claude-radar review`·구조 변경의 **기준점**으로 삼는다 — "이미 내린 결정"을 재논의하지 않기 위해.

## 결정적 사실: 이 vault가 곧 OKF가 형식화하려는 패턴이다
구글은 OKF의 표준화 대상 사례로 **"코딩 에이전트에 연결된 Obsidian vault"와 "CLAUDE.md"를 직접 지목**했다. OKF는 Andrej Karpathy의 2026-04 "LLM Wiki" 아이디어를 포터블 포맷으로 형식화한 것이고, 이 vault(Obsidian + Claude Code + CLAUDE.md + frontmatter + wikilink + MOC)는 그 패턴의 **살아있는 인스턴스**다. 즉 OKF는 "외부에서 가져올 표준"이 아니라 "우리 패턴이 표준화된 것"이며, OKF와의 차이가 곧 호환 갭 목록이다.

## 표준 계보 (리서치 종합)
- **OKF v0.1** (Google): bundle = YAML frontmatter 마크다운 파일 디렉토리, **파일=개념(파일경로=정체성)**, 마크다운 링크 그래프, **유일 필수 필드 `type`**, 설계 3원칙(최소규정 / 생산자-소비자 독립 / 플랫폼 아닌 포맷). 한계: 구조만 표준화하고 **의미는 표준화 안 함**("just a folder" 비판 — type 어휘·링크 의미 무통제), 레퍼런스 파서가 스펙과 모순(미성숙).
- **Karpathy LLM Wiki**: 3계층(raw 원문 / wiki LLM-생성 / 스키마=CLAUDE.md) + Ingest·Query·Lint 운영 루프. 핵심 = **원자성**("10,000단어 catch-all보다 focused 1,000단어 10개"), **상단 한 줄 요약 = 로드 게이트**, RAG와 달리 **지식이 복리로 누적**(LLM이 0비용으로 북키핑). "문서의 1차 독자는 사람이 아니라 모델."
- **llms.txt** (Howard): H1 + blockquote 요약 + H2 섹션별 링크+설명 + 생략 가능 Optional. = MOC 허브 구조와 동형.
- **AGENTS.md** (Linux Foundation): 사람용 README와 분리된 에이전트 진입점, 트리 근접성 우선, **짧을수록 우월**(README 중복은 성공률↓·비용 +23%).
- **GraphRAG/PKM**: 수작업 MOC = community-summary의 0토큰 대체물, wikilink = 그래프 엣지. 단 **과분절(atomicity zealotry) 경계** — 멀티홉 추론을 강제해 토큰·오류↑. 원자성은 규칙이 아니라 트레이드오프.
- **시맨틱웹 교훈**: RDF/OWL이 실패한 건 표현력이 아니라 **운영비용**(수작업 어노테이션·온톨로지 합의). 마크다운+frontmatter+wikilink가 옳은 altitude.

## 10차원 자기진단 판정
| 차원 | 판정 | 요지 |
|---|---|---|
| AI 에이전트 소비성 (hot.md INJECT + MOC 레이어링) | **strong** | progressive-disclosure 3계층이 교과서적. INJECT-only 주입으로 캐시 churn 방지 |
| 자동화/안전 (collect↔review, STRAY 가드, fetch-guard) | **strong** | 무인 자동화 안전이 업계 모범 수준 |
| 메타데이터/frontmatter | adequate→**개선** | `type` 필드 도입(아래) |
| 그래프/링크 (wikilink, 사일로) | adequate→**개선** | AI-Infra 사일로 cross-link 보강 |
| 콘텐츠 원자성 | adequate | 대형 종합노트는 의도된 설계(1-read 답변성) — 분할 금지 |
| 검색/리트리벌 (MOC-first, RAG 부재) | adequate | 45노트 규모에선 MOC+wikilink로 충분 |
| 표준 정합/포터블 | adequate→**개선** | type 도입 + 문서 드리프트 정리 |
| 신선도/품질 유지 | adequate→**개선** | 결정론 신선도 경고·해시 감지 추가 |
| 확장성/멀티토픽 | adequate→**개선** | L1.5 토픽 라우터 + 토픽 추가 체크리스트 |
| 검증/평가 (콘텐츠 사실성 eval) | **gap** | 메커니즘 테스트는 충실하나 콘텐츠 eval은 결정론 lint로 부분 보강 |

**아키텍처 총평**: 1인 운영 + Claude Code 1차 소비 용도에 **매우 적합**. 골격은 바꿀 게 아니라 지킬 것 — 시급한 건 새 추상화가 아니라 (a) 실측 버그 수정 (b) 멀티토픽 라우팅 일반화 (c) 사일로 cross-link.

## 채택한 결정 (2026-06-19)
- ✅ **`type` 닫힌 enum 도입**: `reference|explanation|how-to|tutorial|moc`. OKF 유일 필수 필드 + Diátaxis 축. 정본 `.claude/kb-allowed-types.txt`, `kb-lint`가 enum 드리프트 차단. (OKF의 "어휘 무통제" 약점을 lint 강제로 보완 — vault = OKF 컨테이너 + 자체 검증 레이어.)
- ✅ **결정론 신선도/품질**: `kb-lint`에 age 경고·MOC 백링크·거버넌스 메트릭, `kb-source-hashes.py`로 "같은 슬러그 본문 변경" 감지(review 큐 적재, 자동수정 금지), `--links` 외부 URL 점검.
- ✅ **멀티토픽 라우팅**: L1 hot.md → **L1.5 토픽 라우터** → L2 `<Topic>/<Topic>.md` → L3. 토픽 추가 체크리스트를 CLAUDE.md 변경동기화 표에 박제.
- ✅ **안전 비대칭 해소**: STRAY 가드를 `stray-guard.sh`로 추출(radar+kb-sync 공유) + 계약 테스트.

## 의도적 non-goal (안 하기로 한 것 = 강점)
> [!note] 재논의 차단
> 아래는 45노트 규모에서 **콜드스타트 비용 > 효용**이라 의도적으로 배제한다. 정본은 `.claude/rules/vault-rules.md`의 "Explicit non-goals".
- **임베딩/벡터검색/RAG**: 수작업 MOC+wikilink가 이미 GraphRAG community-summary 자산. 트리거(100+노트 AND "이름 모르는 개념 의미검색" 빈발) 전엔 코드 변경 0.
- **RDF/JSON-LD/온톨로지**: 시맨틱웹의 운영비용 함정.
- **typed-relation frontmatter**(related/up/part-of): 본문 wikilink가 이미 담당 — double-entry 부채. `type`만 추가.
- **OKF export 스크립트·AGENTS.md**: 외부 발행/타에이전트 협업 수요 실재 시까지 보류. vault는 source-of-truth, wikilink→md-link는 export 경계 관심사.

## OKF 호환성 요약
- **정렬**: 디렉토리=번들, `<Topic>/<Topic>.md`=index.md 역할, markdown+YAML frontmatter, provenance(sources/`## 원본 문서`), mechanism/content 분리 = 생산자-소비자 독립.
- **의도적 비호환**: Obsidian `[[wikilink]]`(OKF는 표준 md-link만, visualizer 비파싱) — 1차 소비자가 Claude Code(파일시스템 직접 read)인 한 GraphRAG/Karpathy 소비에 더 풍부한 신호라 vault 내부 유지가 옳다. OKF 호환은 export 경계의 관심사.
- **저비용 첫 단추(완료)**: `type` 도입. 이후 export 시 `updated→timestamp`, `sources→resource` 매핑 어댑터만 추가하면 단방향 OKF 번들 산출 가능.

## 원본 문서
- OKF v0.1 SPEC: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
- How the OKF can improve data sharing (Google Cloud): https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/
- Karpathy LLM Wiki gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- llms.txt: https://llmstxt.org/
- AGENTS.md: https://agents.md/
- What is GraphRAG? (Neo4j): https://neo4j.com/blog/genai/what-is-graphrag/
- Zettelkasten Atomicity Guide: https://zettelkasten.de/atomicity/guide/
- 원 토픽(GeekNews): https://news.hada.io/topic?id=30622
