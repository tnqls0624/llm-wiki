---
title: 02 쿠버네티스 GPU 오케스트레이션
updated: 2026-06-08
type: explanation
sources:
  - https://kserve.github.io/website/
  - https://keda.sh/docs/
  - https://kueue.sigs.k8s.io/
  - https://docs.aws.amazon.com/eks/latest/best-practices/karpenter.html
  - https://awslabs.github.io/ai-on-eks/
---

# 쿠버네티스 GPU 오케스트레이션

허브: [[AI-Infra]] · 함께: [[01 LLM 서빙과 추론]](여기 올릴 추론 워크로드)·[[03 MLOps 파이프라인과 관측성]](배포 후 관측·드리프트) · 토대(Infra): [[06 컨테이너 내부 구조]](cgroups·namespaces·GPU 주입)

K8s는 2026년 "AI 워크로드의 기본 컨트롤 플레인"으로 수렴했다(CNCF). Docker·CI/CD·무중단 배포 경험이 직결되며, 새로 배울 것은 **GPU 스케줄링 계층**과 **선언적 모델 서빙 CR**이다. "맛본 수준" K8s를 GPU-aware 운영 수준으로 끌어올리는 게 이 직무의 핵심 차별점.

## GPU 스케줄링
- **NVIDIA GPU Operator** — 드라이버·device plugin·MIG·DCGM 모니터링 일괄 관리. 시작점.
- **device plugin → DRA** — 2026년 Dynamic Resource Allocation으로 전환 중(CNCF). 버전보다 원리에 투자.
- **Kueue** — GPU fair-share·quota·gang scheduling의 사실상 표준. 팀별 ClusterQueue로 활용률↑.
- **Volcano / KAI Scheduler** — gang scheduling(분산 학습 all-or-nothing).
- **Karpenter** — GPU 노드 just-in-time 프로비저닝 + 스팟 + consolidation. EKS 기본 오토스케일러(Auto Mode 내장).

## 모델 서빙 (선언적)
- **KServe**(CNCF) — `InferenceService`/`LLMInferenceService` CR로 추론 엔진을 K8s 네이티브(scale-to-zero·카나리·트래픽 분할·멀티모델)로 감쌈. **RawDeployment 모드부터** 시작(Knative부터 가면 복잡도 폭증).
- **KEDA** — HPA의 0-스케일 한계를 보완. vLLM 네이티브 메트릭(queue depth·KV cache util) 기반 scale-to-zero.
- **llm-d**(2025말) — vLLM 위 prefill/decode 분리·KV 오프로딩·크로스노드 텐서 병렬로 70B+ 멀티노드 서빙. prefix-cache aware routing으로 TTFT 2배·throughput 3배 사례.

## GitOps · IaC
- **ArgoCD** — 모델·서빙 매니페스트를 선언적으로. ⚠ KServe가 자기 리소스를 mutate하므로 `ignoreDifferences` 미설정 시 영원히 OutOfSync.
- **Terraform** — EKS + GPU 노드그룹 + Karpenter NodePool + IRSA + VPC를 코드화. `terraform apply` 한 번으로 서는 추론 클러스터 = 채용 어필의 중심.

## 흔한 함정
- **GPU nodeSelector/리소스 요청 누락** → CPU 노드에 떨어져 조용히 느린 CPU 추론으로 폴백(에러도 안 남).
- **ArgoCD OutOfSync 영구화** → `ignoreDifferences` 설정.
- **스팟 GPU 비용 폭탄** → Karpenter consolidation·TTL·노드 종료 핸들러로 학습 끝나면 즉시 정리.
- **Knative부터 시작** → RawDeployment로 핵심 패턴 먼저.
- **모델을 그냥 Deployment로** → `InferenceService` CR 추상화가 플랫폼 사고의 핵심.

## AWS 경로
EKS로 통일. `terraform-aws-modules/eks` + Karpenter NodePool(g5/g6 스팟·consolidation). **EKS Auto Mode**는 데이터플레인까지 관리(TCO 절감 크나, 학습 단계엔 셀프매니지드 Karpenter로 내부 동작 먼저 이해 후 비교). IRSA로 파드별 최소권한 S3 모델 접근(백엔드 IAM 경험 직결). 메인 실습 정답지: **`awslabs/ai-on-eks`** 블루프린트(Karpenter+vLLM+KServe+Ray를 Terraform으로).

## 자격증
- **CKA** — 플랫폼 엔지니어 단일 최고 신호(핸즈온). KServe/KEDA/llm-d가 모두 K8s 위에서 도므로 토대.

## 사이드 프로젝트
- 홈랩 단일 GPU + k3s + NVIDIA GPU Operator로 device plugin 실습
- EKS(Karpenter GPU 스팟)에 KServe(vLLM) + ArgoCD GitOps + DCGM 대시보드, 전부 Terraform IaC
- Kueue ClusterQueue로 가짜 팀 2개 GPU quota·gang scheduling → 활용률 before/after 측정
- 공개 Terraform 모듈 `eks-ai-platform`(apply 한 번에 EKS+Karpenter+KServe+ArgoCD)

## 원본 문서
- KServe: https://kserve.github.io/website/
- KEDA: https://keda.sh/docs/
- Kueue: https://kueue.sigs.k8s.io/
- Karpenter (EKS best practices): https://docs.aws.amazon.com/eks/latest/best-practices/karpenter.html
- AI on EKS (awslabs): https://awslabs.github.io/ai-on-eks/
- NVIDIA GPU Operator: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/index.html
- CNCF "great migration to K8s"(2026-03): https://www.cncf.io/blog/2026/03/05/the-great-migration-why-every-ai-platform-is-converging-on-kubernetes/
