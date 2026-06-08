---
title: 01 LLM 서빙과 추론
updated: 2026-06-08
sources:
  - https://docs.vllm.ai/en/stable/
  - https://docs.sglang.ai/
  - https://kserve.github.io/website/docs/model-serving/generative-inference/autoscaling
  - https://www.spheron.network/blog/vllm-vs-tensorrt-llm-vs-sglang-benchmarks/
---

# LLM 서빙과 추론 인프라

허브: [[AI-Infra]]

6년차 백엔드 자산이 **가장 강하게 전이**되는 영역. 추론 엔진은 본질적으로 "고처리량·저지연 stateful 서비스"이고, PagedAttention=메모리 풀, continuous batching=요청 배치 큐, KV cache=캐시 계층의 GPU 버전이다. API·p99·로드밸런싱·캐시 운영 직관이 그대로 옮겨간다.

## 추론 엔진 (2026 3강)
- **vLLM** — 사실상 표준(디폴트). V1 엔진, OpenAI 호환 API. NVIDIA/AMD/AWS Neuron 지원 → 스팟 쇼핑 유연. RunPod 엔드포인트의 ~40%가 vLLM 기반.
- **SGLang** — RadixAttention으로 공유 prefix(RAG·멀티턴·few-shot) KV 캐시를 radix tree로 재사용. 8B에서 vLLM 대비 ~29% 우위, 70B+는 3~5%로 좁아짐.
- **TensorRT-LLM** — 최고 throughput(10~13% 우위)이나 모델당 ~28분 컴파일 + NVIDIA 락인. v1.0+ PyTorch 백엔드로 컴파일 회피 가능.
- **TGI** — 2025-12 유지보수 모드. **새로 배우지 말 것**(HuggingFace도 vLLM 권장).

> 엔진은 워크로드별 선택 — 백엔드의 DB/캐시 선택 의사결정과 동형.

## GPU 메모리 기초
총 VRAM = 모델 가중치(70~75%) + KV 캐시(컨텍스트 길이 비례, 15~20%) + 런타임 오버헤드(CUDA 컨텍스트·할당자 0.5~2GB).
- 가중치 ≈ 파라미터 × bytes/param (FP16=2, INT8=1, INT4=0.5) × 1.2
- KV 캐시 = 2 × layers × hidden × seq_len × batch × dtype
- **decode 단계는 memory-bandwidth-bound** — 이 직관이 용량 계획·비용 산정·OOM 디버깅의 출발점.

## 최적화 (같은 GPU로 10~50배)
- **양자화**: AWQ INT4(activation-aware, 같은 비트폭서 GPTQ보다 품질↑) · GPTQ(Marlin 커널 2.5배↑) · FP8(Hopper 기본, 30%+↑ 거의 무손실)
- **연속 배칭(continuous batching)**: static 대비 10~20배 throughput
- **PagedAttention**: 메모리 단편화 제거
- **prefix caching**: 공유 프롬프트 재사용
- **speculative decoding**: 작은 draft 모델(n-gram/EAGLE)로 디코딩 가속
> 양자화는 공짜 점심이 아니다 — 품질 저하를 perplexity/태스크 정확도로 정량 측정해 비용-품질 곡선으로 다룰 것.

## 측정 (개발자 ↔ 인프라 엔지니어를 가르는 핵심)
TTFT(time-to-first-token) · TPOT/ITL(inter-token latency) · throughput(tokens/s, req/s) · GPU util · **$/1M tokens**. 백엔드의 p99·부하테스트·SLO 경험이 가장 직접 전이 — 메트릭 이름만 LLM 특화로 바뀐다. `vllm bench serve`/locust/k6로 동시성 스윕 → "throughput을 올리면 TTFT가 무너지는 지점"을 그래프로.

## 사이드 학습 (GPU 없이 시작)
1. CPU/작은 모델(Qwen2.5-0.5B/1.5B)로 vLLM 원리·OpenAI 호환 API 서비스화
2. 스팟 GPU(Vast.ai RTX 4090 $0.25~0.35/hr · RunPod) — 벤치마크 단계에만 시간당 임대
3. Modal($30 크레딧)/RunPod 서버리스 scale-to-zero — 저트래픽 cents/day
4. AWS 통제력 단계: **Bedrock**(매니지드) → **SageMaker** async endpoint(MinCapacity=0) → **EKS+vLLM**(최대 통제·학습효과)

> ⚠ SageMaker **Serverless Inference는 GPU 미지원** — scale-to-zero GPU는 async endpoint(MinCapacity=0)나 Modal/RunPod로.

## 사이드 프로젝트 (포트폴리오)
- vLLM vs SGLang을 RAG(공유 prefix 많음) vs 일반 챗에서 throughput·TTFT 벤치 → 표/블로그 (엔진 선택 의사결정 증명)
- FP16 / AWQ-INT4 / FP8 양자화 "비용-품질 파레토 곡선"
- kind/스팟 GPU에 KServe + KEDA scale-to-zero 추론 플랫폼 (KV cache util·queue depth·TTFT 대시보드)
- Bedrock vs SageMaker vs EKS-자체호스팅 비용 손익분기 분석

## 원본 문서
- vLLM: https://docs.vllm.ai/en/stable/
- SGLang: https://docs.sglang.ai/
- KServe Generative Inference Autoscaling: https://kserve.github.io/website/docs/model-serving/generative-inference/autoscaling
- 엔진 벤치(2026, 교차검증 권장): https://www.spheron.network/blog/vllm-vs-tensorrt-llm-vs-sglang-benchmarks/
- AWS — vLLM on SageMaker/Bedrock: https://aws.amazon.com/blogs/machine-learning/efficiently-serve-dozens-of-fine-tuned-models-with-vllm-on-amazon-sagemaker-ai-and-amazon-bedrock/
