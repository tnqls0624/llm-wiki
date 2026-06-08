---
title: 10 핸즈온 vLLM 스팟 서빙 벤치마크
updated: 2026-06-08
sources:
  - https://docs.vllm.ai/en/stable/
  - https://docs.runpod.io/serverless/vllm/overview
  - https://aws.amazon.com/ec2/spot/
---

# 핸즈온: 스팟 GPU vLLM 서빙 + 벤치마크

허브: [[AI-Infra]] · 개념: [[01 LLM 서빙과 추론]] · 마일스톤: [[00 로드맵]]의 0-3개월

**목표 산출물**: 스팟 GPU에 vLLM으로 8B 모델을 OpenAI 호환 API로 서빙하고, 부하테스트로 throughput·TTFT·p99을 측정한 GitHub 리포(README에 벤치 표). = 0-3개월 첫 체크리스트 항목.

**왜 이게 첫 산출물인가**: 백엔드의 "API 서버 + 부하테스트 + p99" 경험을 LLM에 그대로 적용 → 가장 빠르게 "엔드투엔드 한 바퀴"를 돌고, 면접에서 가장 설득력 있는 산출물(측정 표/곡선)을 얻는다.

## 0. GPU 없이 로컬 워밍업 (30분, 선택)
GPU 빌리기 전 개념·API를 무료로 체감:
```bash
pip install vllm
vllm serve Qwen/Qwen2.5-1.5B-Instruct --max-model-len 4096   # 작은 모델은 CPU/Apple Silicon도 가능
curl http://localhost:8000/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"Qwen/Qwen2.5-1.5B-Instruct","messages":[{"role":"user","content":"hi"}]}'
```
→ OpenAI 호환 API가 곧 익숙한 백엔드 서비스임을 확인.

## 1. 스팟 GPU 확보 (비용 최소)
| 경로 | 비용 | 세팅 | 추천 상황 |
|---|---|---|---|
| Vast.ai RTX 4090 | $0.25~0.35/hr | 쉬움(도커) | 가장 싸게 첫 벤치 |
| RunPod (pod/serverless) | RTX4090 ~$0.34, A100 ~$0.89/hr | 쉬움(vLLM 템플릿) | scale-to-zero |
| **AWS g5.xlarge**(A10G 24GB) 스팟 | ~$0.3~0.5/hr | 중간(AMI+드라이버) | **AWS 트랙 정합** |

AWS 트랙이 목표이므로 **g5.xlarge 스팟** 권장(빠른 첫 실험만 Vast.ai/RunPod로 마찰 줄이기). A10G 24GB → 8B FP16(~16GB) 여유.

> ⚠ **첫 30분에 비용 안전부터**: AWS Budgets 알람($10 등) + 작업 후 즉시 `terminate` 또는 유휴 auto-stop. 추론만 하므로 체크포인트는 불필요하나, **끝나면 반드시 종료 확인**.

## 2. vLLM 서빙
g5.xlarge(AWS Deep Learning AMI = 드라이버 포함) 기준:
```bash
pip install vllm
huggingface-cli login          # 게이트 모델(Llama 등) 접근 시
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --port 8000
```
- VRAM 부족 시: `--quantization awq` + AWQ 모델(`...-AWQ`) 또는 `--max-model-len` 축소.
- `/health`·`/metrics`(Prometheus) 확인 — 백엔드의 헬스체크·메트릭 노출과 동일.

## 3. 부하테스트 (throughput·TTFT·p99)
```bash
# (a) vLLM 내장 — 처리량·지연
vllm bench serve --model meta-llama/Llama-3.1-8B-Instruct \
  --host localhost --port 8000 --num-prompts 200 --request-rate 10

# (b) k6 — 동시성 스윕(백엔드 친숙). load.js 에서 VU 1·5·10·20 으로 올림
k6 run --vus 10 --duration 60s bench/load.js
```
> 핵심 관찰: **동시성을 올리면 throughput은 오르다 TTFT가 무너지는 지점** — 이 곡선이 면접 산출물.

## 4. 측정·기록
- TTFT(time-to-first-token) · TPOT(inter-token) · throughput(tokens/s, req/s) · GPU util(`nvidia-smi`/DCGM) · **$/1M tokens**.
- `$/1M tokens = (스팟 시간당 $) ÷ (시간당 처리 토큰 ÷ 1e6)`.

## 5. 리포 구조 (포트폴리오)
```
vllm-spot-bench/
├── README.md             # 벤치 표 + 환경(GPU·모델·양자화) + "동시성 vs TTFT" 그래프
├── serve.sh              # vllm serve 명령(파라미터 주석)
├── bench/{load.js, run_bench.sh}
├── metrics/cost_per_token.py
├── infra/                # (선택) g5 스팟 기동 스크립트 또는 Terraform
└── results/              # 측정 CSV/그래프
```
README에 **백엔드 서사**를 명시: "PagedAttention=메모리 풀, continuous batching=요청 배치 큐 — 백엔드 throughput 최적화의 GPU 버전". 이 한 줄이 신입 ML 지원자와의 차별화.

## 6. 다음 단계 (이 리포를 키운다)
- SGLang으로 같은 모델 재측정 → RAG(공유 prefix) vs 일반 챗 비교 → [[00 로드맵]] 3-9개월 벤치 블로그.
- 양자화 FP16/AWQ-INT4/FP8 비용-품질 곡선 추가.
- KServe+KEDA로 K8s에 올려 scale-to-zero → [[02 쿠버네티스 GPU 오케스트레이션]].

## 완료 기준 (체크포인트)
- [ ] OpenAI 호환 `/v1/chat/completions` 200 응답
- [ ] 동시성 스윕 throughput·TTFT·p99 표
- [ ] `$/1M tokens` 산출
- [ ] README에 벤치 표 + 백엔드 서사
- [ ] 작업 후 인스턴스 종료 확인 + 총비용 기록

## 원본 문서
- vLLM (Quickstart·Serving·Benchmarks): https://docs.vllm.ai/en/stable/
- RunPod vLLM: https://docs.runpod.io/serverless/vllm/overview
- AWS EC2 Spot: https://aws.amazon.com/ec2/spot/
