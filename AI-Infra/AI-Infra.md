---
title: AI-Infra
updated: 2026-06-08
type: moc
sources: []
---

# AI 인프라 엔지니어 학습 허브

6년차 백엔드 → AI 인프라 엔지니어(LLM 서빙·MLOps·플랫폼/K8s) 전환을 위한 한국어 학습 KB. `Claude/` KB와 동일 패턴(노트 + MOC + lint)을 따른다. 매일 `/claude-radar`가 생태계를 추적하고, 가치 있는 자료는 `/kb-ingest`로 이 디렉토리에 박제한다.

## 선행 지식 (Infra 토대)
GPU 서버도 컨테이너도 결국 리눅스 위에서 돈다 — [[Infra]] KB가 이 KB의 토대 레이어다. 특히 [[02 메모리 관리]](KV cache·PagedAttention의 바탕), [[06 컨테이너 내부 구조]](cgroups·GPU 디바이스 주입), [[08 성능 분석과 트러블슈팅]](서빙 p99 디버깅)을 먼저 알면 아래 3영역이 "리눅스의 응용"으로 읽힌다.

## 먼저 읽을 것
- **[[00 로드맵]]** — 전이 자산 매핑 · 4단계(0-3 / 3-9 / 9-18 / 18-36개월) · 체크리스트 · 함정 · AWS 트랙 · 한국 시장 · 학습 OS 사용법.

## 집중 3영역
- **[[01 LLM 서빙과 추론]]** — vLLM/SGLang/TensorRT-LLM, GPU 메모리, 양자화·배칭·캐싱, TTFT/throughput 측정, GPU 없이 시작하는 법.
- **[[02 쿠버네티스 GPU 오케스트레이션]]** — KServe·KEDA·Kueue·Karpenter, GPU 스케줄링(device plugin→DRA), GitOps, Terraform EKS.
- **[[03 MLOps 파이프라인과 관측성]]** — MLflow·Flyte/Airflow, OpenTelemetry GenAI·드리프트, CI/CD for ML.

## 핸즈온
- **[[10 핸즈온 vLLM 스팟 서빙 벤치마크]]** — 0-3개월 첫 산출물 step-by-step (스팟 GPU 확보·vLLM 서빙·부하테스트·리포 구조·비용 안전).

## 자료
- **[[99 학습 리소스와 추적 소스]]** — 공식 docs·강의·랩·자격증 + `claude-radar`에 등록한 매일 추적 소스.

## 학습 루프 (이 KB를 쓰는 법)
```
수집  /claude-radar     → 매일 AI 인프라 신규를 큐로 받음
박제  /kb-ingest        → 가치 있는 자료를 이 디렉토리에 노트로
질의  /kb-query·kb-guide → 박제한 개념을 격리 컨텍스트로 복습
추적  [[00 로드맵]]      → 마일스톤 체크리스트로 진척 관리
```

## 핵심 명제
백엔드 6년차 자산의 **~80%(분산시스템·API·운영·CI/CD·관측성·비용)가 그대로 전이**된다. 새로 채울 것은 GPU/서빙/토큰경제라는 얇은 레이어. 채용을 가르는 건 자격증이 아니라 **"프로덕션처럼 보이는 단일 캡스톤"** 이다.
