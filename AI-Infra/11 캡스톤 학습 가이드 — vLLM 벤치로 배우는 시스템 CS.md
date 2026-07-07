---
title: 11 캡스톤 학습 가이드 — vLLM 벤치로 배우는 시스템 CS
updated: 2026-06-09
sources:
  - https://docs.vllm.ai/en/stable/
  - https://arxiv.org/abs/2309.06180
type: tutorial
---

# 캡스톤 학습 가이드: vLLM 벤치 = 시스템 CS 실전

허브: [[AI-Infra]] · 실행 절차: [[10 핸즈온 vLLM 스팟 서빙 벤치마크]] · 개념: [[01 LLM 서빙과 추론]]

> **이 노트의 목적**: 캡스톤을 "스크립트 복붙"이 아니라 **"왜 이렇게 동작하는지 CS 기초로 이해하며 진행"**하게 만든다. 실행 레포는 `~/Desktop/Project/vllm-spot-bench`. [[10 핸즈온 vLLM 스팟 서빙 벤치마크]]이 *무엇을 치는가*라면, 이 노트는 *왜 그런가 + CS 토대 + 실무 팁 + 면접 포인트*다.
>
> 핵심 명제: **vLLM 서빙은 학부 CS(운영체제·네트워크·시스템·자료구조)의 GPU 버전이다.** 이걸 연결해 배우면 "툴 사용법"이 아니라 "시스템 엔지니어링"을 익힌다 — 그게 면접에서 신입과 당신을 가른다.

## 학습 로드맵 (캡스톤 단계 ↔ CS 토픽)
각 단계를 진행할 때 이 노트의 해당 모듈을 함께 읽고, **이해 체크 질문에 스스로 답해본 뒤** 다음으로 간다.

| 단계 | 캡스톤에서 하는 것 | 밑에 깔린 CS 기초 | 실무/면접 핵심 |
|---|---|---|---|
| **M1 서빙 + KV캐시** | OpenAI 호환 API 띄우기 | **OS 가상메모리 페이징**, REST/소켓, 공간-시간 트레이드오프 | PagedAttention이 푼 문제, gpu-mem-util, OOM |
| **M2 Continuous batching** | 동시 요청 처리 | **OS 스케줄링**, 큐잉, throughput↔latency 트레이드오프 | 정적 vs 연속 배칭, SLA, 선점 |
| **M3 부하테스트 (p99)** | TTFT/throughput/p99 측정 | **큐잉 이론·Little's Law**, tail latency, 동시성≠병렬성 | p99가 평균보다 중요한 이유, coordinated omission |
| **M4 비용** | $/1M tokens 산출 | 자원 활용률(utilization), amortization | 셀프호스팅 손익분기 vs API, 스팟 중단 |
| **M5 양자화** | FP16/INT4 비교 | **부동소수점 표현(IEEE754)**, 정밀도-메모리-속도 트레이드오프 | 양자화가 품질에 주는 영향, 언제 쓰나 |

> 아래는 **M1을 깊이** 다룬다. M2~M5는 해당 단계를 실제로 진행할 때 같은 형식(do→CS→실무→면접→이해체크)으로 이어 쓴다. "진행하면서 학습"이라 한꺼번에 다 만들지 않는다 — 그래야 손과 머리가 같이 간다.

---

## 모듈 1 — 서빙과 KV 캐시: PagedAttention은 OS 페이징이다

### 🎯 하는 것 (do)
```bash
bash serve.sh                 # vllm serve … --gpu-memory-utilization 0.90
curl localhost:8000/health    # 200 OK
curl localhost:8000/v1/models # 서빙 중인 모델
curl localhost:8000/metrics   # Prometheus 메트릭 (KV캐시 사용률 등)
```

### 🧠 밑에 깔린 CS
**(1) OpenAI 호환 API = 그냥 REST 서버다.** vLLM이 포트 8000에 소켓을 바인드하고 HTTP로 JSON을 주고받는다. 당신이 백엔드에서 만든 API 서버와 **구조가 똑같다.** 다른 건 핸들러 안에서 GPU가 도는 것뿐. → "LLM 서빙"이라는 말에 겁먹을 필요 없다. 익숙한 REST 위에 추론이 얹힌 것.

**(2) KV 캐시 = 공간-시간 트레이드오프(CS의 가장 기본 원리).** LLM은 토큰을 하나씩 생성하는데, 매 토큰마다 *이전 모든 토큰*의 Key·Value 벡터가 필요하다. 매번 재계산하면 시퀀스 길이 n에 대해 O(n²) — 느리다. 그래서 한 번 계산한 K·V를 **메모리에 캐싱**해 O(n)으로 줄인다. 전형적인 "메모리를 써서 연산을 줄인다". 문제는 이 캐시가 **GPU 메모리를 엄청 먹는다**는 것(8B 모델에서 요청당 수백 MB~GB).

**(3) PagedAttention = OS 가상메모리 페이징을 KV 캐시에 적용한 것.** ← 이게 이 모듈의 핵심. 운영체제 수업에서 배운 바로 그것이다.
- **문제**: KV 캐시를 "연속된 큰 메모리 한 덩어리"로 잡으면 두 가지가 터진다 — ① 요청마다 *최대 길이*만큼 미리 할당해야 해서 짧은 요청도 메모리를 낭비(internal fragmentation), ② 길이가 제각각인 요청들이 들고 나면 메모리에 구멍이 생김(external fragmentation). OS가 프로세스 메모리를 연속으로 주려다 겪는 단편화 문제와 **완전히 동일**하다.
- **해법(OS의 그것)**: OS는 물리 메모리를 고정 크기 **페이지**로 쪼개고, 프로세스에 필요할 때만 페이지를 매핑한다(페이지 테이블). vLLM도 똑같이 KV 캐시를 고정 크기 **블록**으로 쪼개고, 시퀀스가 자랄 때만 블록을 할당하며 **블록 테이블**로 추적한다. → 단편화 거의 0, 메모리 활용률 급상승 → **같은 GPU로 훨씬 많은 동시 요청 처리.**
- 한 줄 요약(면접용): *"PagedAttention은 OS의 가상메모리 페이징을 KV 캐시에 적용해, 연속 할당의 단편화를 없애고 메모리 활용률을 끌어올린 기법이다."*

### 🔧 실무 팁
- `--gpu-memory-utilization 0.90`: GPU 메모리의 90%를 (모델 가중치 + KV 캐시 블록)에 쓰겠다는 뜻. **높일수록 동시에 들고 있을 수 있는 토큰(=처리량)이 늘지만**, OS·다른 프로세스 여유가 줄어 너무 높이면 OOM. 0.85~0.92가 흔한 시작점.
- **OOM이 나면** 순서대로: `--max-model-len` 축소(컨텍스트 짧게) → `--quantization awq`(가중치를 줄여 KV 캐시 공간 확보) → 더 작은 모델/큰 GPU.
- `/metrics`의 `vllm:gpu_cache_usage_perc`를 봐라. **KV 캐시가 100%에 닿으면** 새 요청이 대기(큐잉)하거나 선점된다 = M2·M3에서 TTFT가 무너지는 직접 원인. 관측성은 백엔드의 Prometheus 메트릭과 동일한 습관.
- `/health`·`/metrics`는 백엔드의 헬스체크·메트릭 엔드포인트와 1:1. K8s에 올릴 때(02 노트) readiness/liveness probe로 그대로 쓰인다.

### 🎤 면접 포인트
- *"KV 캐시가 뭔가요? 왜 필요하죠?"* → 자기회귀 생성에서 이전 토큰 K·V 재계산을 피하는 캐시, O(n²)→O(n) 공간-시간 트레이드오프.
- *"PagedAttention이 기존 방식 대비 무엇을 개선했나요?"* → 위 한 줄 요약. "OS 페이징과 같은 아이디어"라고 답하면 CS 기본기가 드러난다.
- *"동시 사용자를 늘렸더니 OOM이 났습니다. 어떻게 진단·해결하죠?"* → gpu_cache_usage 메트릭 확인 → util/max-len/양자화 트레이드오프 설명.

### ✅ 이해 체크 (스스로 답하고 실제로 확인)
1. `--max-model-len`을 8192→4096으로 반토막 내면, 동시에 처리 가능한 요청 수는 늘까 줄까? **왜?** (힌트: 요청당 KV 캐시 블록 수)
2. `nvidia-smi`를 띄워둔 채 `--gpu-memory-utilization`을 0.5와 0.9로 각각 서빙해보라. GPU 메모리 점유와 `/metrics`의 cache usage가 어떻게 달라지나?
3. PagedAttention의 "블록 테이블"은 OS의 무엇에 대응하나? (답: 페이지 테이블)

> 이 세 질문에 막힘없이 답할 수 있으면 M1 통과. 막히면 [[01 LLM 서빙과 추론]]과 PagedAttention 논문(아래 출처)을 보강해서 다시.

---

## 다음 (M2~M5)
M1을 손으로 돌리고 이해 체크를 통과하면, M2(continuous batching = 스케줄링)부터 같은 형식으로 이어 쓴다. 각 모듈은 캡스톤의 실제 단계와 동기화되므로, **진행 = 학습**이 된다. 진척은 [[10 핸즈온 vLLM 스팟 서빙 벤치마크]]의 완료 기준 체크리스트로 추적.

## 원본 문서
- vLLM Docs: https://docs.vllm.ai/en/stable/
- PagedAttention 논문 (Kwon et al., 2023, "Efficient Memory Management for Large Language Model Serving"): https://arxiv.org/abs/2309.06180
