---
title: 04 RAG 지식베이스 검색 아키텍처 (Cerebras 사례)
updated: 2026-07-27
type: explanation
sources: [https://www.cerebras.ai/blog/how-we-built-our-knowledge-base, https://x.com/cerebras/status/2077822555159945507]
---

# 04 RAG 지식베이스 검색 아키텍처 (Cerebras 사례)

허브: [[AI-Infra]]

Cerebras가 사내 지식베이스(Cerebras Knowledge)를 구축한 방법을 정리한 케이스 스터디(2026-07-15, Isaac Tai·Daniel Kim·Mike Gao). 출시 3개월 만에 **하루 15,000+ 질의**를 받는 사내 최다 사용 도구가 됐고, 사람·자동화·에이전트가 함께 쓴다. 엔터프라이즈 RAG(검색 증강)를 실제 규모로 굴린 설계 결정과 트레이드오프가 담겨 있어, LLM 서빙([[01 LLM 서빙과 추론]]) 다음 층인 **검색/컨텍스트 공급** 인프라의 참고 사례다.

## 핵심 설계 원칙 — "meet data where it lives"

"모든 정보를 한 플랫폼에 모으자"는 single source of truth의 꿈은 실무에서 거의 실패한다. 정보는 편리한 곳에서 생성된다 — 문서의 제안 편집, Slack 스레드, GitHub 코드 참조, Jira 상태 메타데이터. 그래서 **기존 행동을 최소로 바꾸는** 방향, 즉 각 플랫폼에서 데이터를 직접 추출하는 쪽으로 설계했다.

지식베이스가 제공하는 3가지: ① 사내 데이터 수집·저장 플랫폼 ② 질의 플랫폼 ③ 인증·인가 + 감사·분석 레이어.

## 전체 파이프라인 (6단계)

```
SOURCES        Slack · Wiki · Code · Incidents
  ↓ DISTILLATION   LLM extractors (구조화 추출)
  ↓ EMBEDDINGS     pgvector · 3072-dim · HNSW
  ↓ RETRIEVAL      six lists in parallel (6개 검색기 병렬)
  ↓ FUSION+RERANK  RRF(k=60) → LLM rerank
  ↓ SYNTHESIS      answer + citations
```

## 코어 저장소 — 하나의 테이블, 소스당 커넥터 1개

중심은 **단일 Postgres 테이블**로 embeddings·raw summaries·metadata를 함께 보관한다. Slack 스레드든 netlist든 모든 소스가 같은 embeddings 테이블에 들어가고, 그 테이블의 무엇이든 같은 인터페이스로 즉시 질의된다.

- 각 데이터 소스는 **무엇을(data)·어떻게 연결(connect)·얼마나 자주 가져올지(fetch frequency)**를 정의한다.
- 결과 embedding 행은 출처(Slack/코드/문서/커스텀 DB)와 무관하게 동일 스키마: `document · embedding · metadata(source + timestamps)`.
- 다른 팀 개발자가 **커스텀 커넥터**를 붙일 수 있게 인터페이스를 의도적으로 단순화.

## Slack ingest — hybrid 검색이 핵심

가장 중요한 소스. 벡터 검색만으로는 부족했다(정보 밀도·길이 편차가 크고, 짧은 메시지가 cosine 유사도에서 긴 메시지를 이기며, 의미가 주변 대화에 의존). → **4개 신호를 동시에** 쓰는 hybrid:

| 신호 | 잡는 것 |
|---|---|
| **Full-text search (FTS)** | 정확 토큰 — 에러 문자열·플래그명·호스트명. 붙여넣은 에러는 lexical 정확 매치가 최선 증거, 어떤 의미 유사도도 이를 못 이겨야 함 |
| **Embedding search** | paraphrase — "restore hangs after manifest load" ↔ "checkpoint stalls on the NFS mount"처럼 어휘가 겹치지 않는 질문↔답 연결 |
| **IDF (역문서빈도)** | 희귀 토큰 신호를 필러와 분리 — "sounds good, thanks!"는 임베딩 공간에서 많은 질의와 가깝지만 term rarity 반영 시 0점 |
| **Age decay** | Slack 답변은 만료됨 — 동률이면 최신 스레드가 이김(6개월 전 답은 사라진 인프라를 말할 수 있음) |

어떤 스코어러도 단독으로 신뢰하지 않는다. 각 기법이 같은 코퍼스에 대한 자기 순위 뷰를 만들고, 질의 시점에 융합(→ Reranking).

**수집 (Socket Mode)**: Slack 봇을 Socket Mode로 실행 → 모든 메시지 이벤트를 persistent WebSocket으로 push 받아 Web API rate limit 없이 실시간 처리. 이벤트 도착 시 즉시 ack → stable event ID로 dedup → ingest 표시.

**스레드 단위 재수집**: ingest consumer는 새 메시지를 고립 저장하지 않고, 그 메시지가 속한 **스레드 전체(부모+모든 답글)를 Slack API에서 재fetch해 한 행으로** 쓴다. 답글 하나가 와도 부모·형제를 다시 당겨오므로 저장 내용·참여자·last-activity가 항상 완전한 대화를 반영. 채널마다 별도 data source라 freshness를 세밀 튜닝(바쁜 incident 채널은 더 자주).

**distillation**: raw 텍스트는 Postgres full-text(GIN) 인덱스로 즉시 keyword 검색 가능. 벡터 검색을 위해선 LLM이 스레드에서 구조화 추출 — `question(엔지니어가 실제로 검색할 한 줄) · summary · resolution · systems · code_refs`. **원문 transcript는 직접 임베딩하지 않고** 정규화된 문서를 임베딩(실험상 정규화 시 정확도가 유의미하게 상승, 메타데이터가 의미 매치에 신호 추가).

**bursting**: 긴 스레드의 중요 메시지가 스레드 요약에 안 담기는 문제 → **burst**(같은 저자의 연속 메시지)를 스레드 주제를 prepend한 채 개별 임베딩(Anthropic Contextual Retrieval 기법). 저신호 차단 위해 임계치 통과분만 임베딩: IDF ≥ 4.0 희귀 토큰 포함 · 결합 길이 ≥ 200자 · 메시지에 reaction(소셜 부스트) 중 가중 조합.

## Code repositories — CocoIndex + language-aware chunking

"grep is all you need" 논쟁 끝에(Claude Code 등 CLI 도구 부상으로 코드 임베딩이 반직관적으로 보였으나, Cursor의 대형 코드베이스 semantic search 결과를 참고해) 시도. 일부 repo는 40GB+ — 최신 유지 효율이 관건.

- **CocoIndex**(오픈소스 코드 임베딩 프레임워크) 채택. 언어별 regex 경계를 coarse→fine 순으로 분할: 클래스 등 상위 경계 먼저, 청크가 너무 크면 메서드→더 작은 블록으로 fallback. 한 파일이 file-level·function-level 등 여러 임베딩 생성.
- **증분 동기화**: 커밋마다 바뀐 청크만 재임베딩·재export(전체 재계산 X). 동기화 상태와 임베딩 저장소가 **같은 DB**에 살아 특히 잘 맞음.
- repo 온보딩을 팀이 직접 제출하는 설정 파일로(파일 경로 수준 allowlist/denylist).

## Custom data sources — plugin scripts

이미 자체 DB를 가진 팀은 데이터를 옮기지 않고 같은 질의 표면을 원함 → 커스텀 소스를 **plugin script**로 취급. 팀이 자기 시스템을 읽어 embeddings 테이블 모양의 행 + data source 엔트리를 emit하는 작은 Python 모듈을 PR로 제출. 같은 스키마로 공유 DB에 쓰기만 하면 나머지 스택은 변경 없이 동작.

## 질의 — planner → executor → synthesis

매 질의마다 **짧은 planning pass**로 LLM이 어느 도구·소스가 유효할지 결정. 주요 도구:
- `subsystem_index`: 파일별 LLM 요약 · `search`: Slack/wiki/code 통합 벡터 파이프라인(내부 병합·rerank) · `search_slack`: 직접 Slack 검색 · `search_code`: repo에 ripgrep · `recent_prs`: 관련 최근 PR · `who_knows`: 주제 전문가 탐색.
- planner는 인덱싱된 것의 compact 기술(어떤 프로젝트·소스가 있고 각 소스가 뭘 잘 답하는지)에 대해 동작 → executor가 병렬 fan-out → 공통 evidence 포맷으로 정규화 → 최종 synthesis LLM.

## Reranking — RRF + LLM rerank + context 확장

문서가 다른 질문에 답하면서 어휘만 겹쳐 상위에 뜨는 문제 방지:
1. **RRF(reciprocal rank fusion)**로 검색기들의 비호환 결과 리스트 결합: 각 문서에 리스트마다 `weight / (60 + rank)` 가산(default weight 1.0, smoothing 상수 k=60). smoothing이 **합의를 단일 강한 표보다 우선**시킴 — 여러 검색기에서 상위인 문서가 한 검색기에서만 1위인 문서를 이김.
2. 중복 청크를 소스 단위로 병합 → **파일당 기여 상한** → 다양성 있는 top 20.
3. 원 질의 + 후보를 작은 **reranker 모델**에 보내 0~10 점수 → top 10.
4. **context 확장**: 매칭된 wiki 섹션이면 인접 2개 섹션을 당겨와 chunking이 쪼갠 heading·전제·caveat 복원(외로운 문단 대신 완전한 스니펫).

## MCP vs Web UI — 같은 도구, 다른 오케스트레이터

- **MCP 통합**: 검색 building block을 "answer this question" 단일 엔드포인트 뒤에 숨기지 않고 **직접 도구로 노출**. 도구는 의도적으로 단순하고 **LLM-free에 가깝게**(클라이언트가 빠르고 싸게 질의). 입출력은 좁고 구조화·안정적. **Claude Code(또는 임의 MCP 에이전트)가 오케스트레이션 엔진** — 어떤 도구를 어떤 순서로 부르고 결과를 어떻게 최종 답/코드 수정으로 조립할지 결정. 검색 레이어 자체는 그 LLM 결정에 의존하지 않음. → [[10 MCP]]
- **Web UI**: 같은 도구가 매 질문마다 end-to-end로 도는 완전 파이프라인에 연결(planner → executor → synthesis를 UI 에이전트가 소유). 사용자에겐 "질문하면 답이 나온다"지만 내부는 MCP 클라이언트가 명시적으로 재현할 수 있는 같은 패턴.

## 조직화 — projects & scoped search

코퍼스가 커지자 "search everything everywhere"가 무용해짐(컴파일러 팀은 인프라 runbook을 원치 않음). → **project**(팀/이니셔티브에 관련된 Slack 채널·repo·DB·문서 공간의 명명된 번들)를 질의 스코프의 기본 단위로 도입. 가볍게 설계 — 같은 data source(공유 incident 채널 등)를 여러 project가 중복 없이 참조. 온보딩 시 기본 project를 골라 user profile에 저장 → 신입이 어느 채널/repo가 중요한지 배우기 전에 high-signal 답을 받음.

## 이 vault와의 연결 (Meta 관점)

이 아키텍처는 우리 vault가 [[00 LLM Wiki 아키텍처와 OKF 자기진단]]에서 **의도적으로 보류한 RAG 비-목표**의 실제 blueprint다. `vault-rules`의 재검토 조건("~100노트 초과 시 local opt-in **SQLite FTS5(BM25) + multilingual ONNX embedding + RRF** L2.5 fallback")은 Cerebras의 **FTS + embedding + IDF + RRF + rerank** hybrid와 정확히 같은 골격이다. 차이는 규모(하루 15k 질의·소스당 커넥터·pgvector HNSW vs 우리 ~50노트 MOC+wikilink). 즉 우리의 "지금은 오버킬" 판단은 유효하되, **넘어갈 때의 참조 설계**로 이 사례가 유용하다 — 특히 "정규화 후 임베딩(원문 X)", "RRF k=60 합의 우선", "context 확장으로 chunk 경계 복원"은 소규모에서도 이식 가능한 교훈.

> [!note] 규모 맥락
> Cerebras 사례의 수치·컴포넌트(pgvector 3072-dim HNSW, CocoIndex, Socket Mode 봇, project 스코핑)는 **엔터프라이즈 규모** 전제다. 우리 vault처럼 노트 수십 개 규모에 그대로 이식하면 cold-start 비용이 가치를 초과한다(vault-rules non-goal의 핵심 논거).

## 원본 문서

- [How We Built Our Knowledge Base — Cerebras (2026-07-15)](https://www.cerebras.ai/blog/how-we-built-our-knowledge-base)
- [Cerebras 발표 트윗](https://x.com/cerebras/status/2077822555159945507)
