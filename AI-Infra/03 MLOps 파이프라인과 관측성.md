---
title: 03 MLOps 파이프라인과 관측성
updated: 2026-06-08
sources:
  - https://mlflow.org/docs/latest/
  - https://docs.flyte.org/
  - https://opentelemetry.io/blog/2026/genai-observability/
  - https://github.com/evidentlyai/evidently
  - https://madewithml.com/
---

# MLOps 파이프라인과 관측성

허브: [[AI-Infra]]

MLOps는 본질적으로 **"데이터+모델 버전까지 포함한 CI/CD"** 다. 백엔드의 아티팩트 버저닝·릴리스 파이프라인·롤백·관측성 경험이 1:1 전이된다 — "Git=설정, S3=모델 blob, ArgoCD=조정"의 분리 원칙을 체득하는 게 백엔드→플랫폼 사고 전환점.

## 파이프라인 · 레지스트리
- **MLflow 3** — 실험 추적 + 모델 레지스트리. "S3=artifact, RDB=메타" 분리가 백엔드 자산과 직결. GenAI(LoggedModel·Prompt Registry·OTel 트레이싱)로 확장.
- **Flyte** — 2026 그린필드 ML 파이프라인 1순위(강타입·K8s-native). 도구 하나에 베팅한다면 이것.
- **Kubeflow / Airflow** — Kubeflow Pipelines/Trainer V2(분산 PyTorch 추상화), Airflow는 데이터 수집→전처리→학습→평가 DAG.
- **DVC / Feast** — 데이터·모델 버저닝 / feature store.

> 도구 수집 금지 — Flyte 하나를 깊게. 나머지는 어휘·통합지점만.

## 관측성 (백엔드 최대 전이 자산)
- **OpenTelemetry GenAI Semantic Conventions**(2026 표준) — 토큰 사용량·비용·에이전트 스텝·벡터DB 쿼리를 표준 속성으로. 기존 Prometheus/Grafana 경험의 LLM 확장.
- **DCGM exporter** — GPU util·HBM·온도 메트릭.
- **Evidently / Arize Phoenix / Langfuse** — OTel이 못 보는 출력 품질·드리프트 평가 레이어. Evidently는 OSS(예산 0원).
> "inference pod이 화요일 새벽 4시 OOM 던질 때 온콜 도는 사람"이 MLOps 엔지니어의 정의 — SRE 자산이 빛나는 지점.

## CI/CD for ML
백엔드 배포 파이프라인을 ML 버전으로 포팅: GitHub Actions로 `register → build image → deploy to EKS → smoke test → canary → promote`. KServe `InferenceService`로 선언적 서빙 + 자동 카나리·롤백.

## 모델 모니터링
데이터/예측 드리프트(입력 분포 변화), 성능 저하, 환각. Evidently + Prometheus + Grafana 라이브 대시보드. 기존 SLO/알림 설계를 LLM SLO(예: TTFT p95 < 500ms)로 재정의.

## AWS 경로
**SageMaker Pipelines**(관리형, EC2 Spot 학습) ‖ **Kubeflow/Flyte on EKS**(K8s-native 이식성). `SageMaker Components for Kubeflow Pipelines`로 하이브리드(K8s 오케스트레이션 + SageMaker 관리형 학습)가 다수 AWS 패턴. 스토리지: FSx for Lustre(핫) · EFS(공유) · S3(아티팩트).

## 자격증
- **AWS MLA-C01**(ML Engineer Associate) — 데이터준비28%·모델개발26%·배포오케스트레이션22%·모니터링/보안24%로 MLOps 직무에 정확히 부합. ⚠ 구 ML Specialty는 2026-03-31 은퇴 → MLA-C01.

## 사이드 프로젝트
- MLflow + Airflow/Flyte로 데이터 수집→학습→평가→레지스트리→배포 end-to-end DAG (기존 CI/CD 재활용)
- Evidently + Grafana 드리프트 라이브 대시보드(입력 분포를 일부러 흔들어 알람 트리거)
- 스팟 노드 중단 → S3 체크포인팅 자동 복구 파이프라인(fault-tolerance 증명)
- 동일 워크로드를 Flyte(EKS) vs SageMaker Pipelines로 양쪽 구현 → 비용·이식성·운영부담 비교

## 원본 문서
- MLflow: https://mlflow.org/docs/latest/
- Flyte: https://docs.flyte.org/
- OTel GenAI Observability(2026): https://opentelemetry.io/blog/2026/genai-observability/
- Evidently: https://github.com/evidentlyai/evidently
- Made With ML: https://madewithml.com/
- aws-samples EKS+Terraform+Kubeflow: https://github.com/aws-samples/amazon-eks-machine-learning-with-terraform-and-kubeflow
