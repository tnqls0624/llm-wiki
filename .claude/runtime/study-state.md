<!-- study-state v1 | block=0 | last_brief_date=2026-06-30 | repo_path=~/Desktop/Project/ai-infra-lab -->
<!--
  AI Infra 학습 진도 정본. git 추적됨 → 두 Mac(회사/집)이 push/pull로 공유.
  study-brief.py(무인 cron)가 이 파일을 읽어 요일별 다음 미완료 항목 + 그 아래 들여쓴 학습 가이드를
  study-today.md로 뽑고, /study-coach review(대화형)가 산출물 검토 후 `- [ ]`→`- [x]` 체크하고
  last_brief_date/검토로그를 갱신한다.
  메타는 위 한 줄 주석에서 파싱: last_brief_date(멱등 키), repo_path(검토 대상 ai-infra-lab 경로).
  repo_path가 머신마다 다르면 .claude/runtime/study-local.conf(gitignore)에 `repo_path=...` 한 줄로 override.
  항목 태그: [평일] = 20~40분, [주말] = 2~3시간 통합 실습. 체크는 review에서만.
  각 항목 아래 2칸 들여쓴 불릿(🎯개념 📖자료 ✅완료 ⚠️막히면)이 그날 브리핑에 함께 출력된다.
-->

# AI Infra 학습 진도 — 인프라 빌더 트랙 (Block 0~6)

**정본 커리큘럼**: `ai-infra-lab/ROADMAP.md` (2026-07-02 v3 확정 — 학습 우선, 블랙웰 특화는 부록 A/B).
**현재**: Block 0 (기초 최소화) — 통합 산출물 `python/train_mnist.py`를 S2→S5 순서로 증분 완성 중.
**주차↔블록**: W1~2=Block 0 · W3~4=Block 1(컨테이너) · W5~7=Block 2(GPU/CUDA) · W8~10=Block 3(서버·네트워크) · W11~12=Block 4(K8s) · W13~16=Block 5(서빙&학습) · W17~19=Block 6(관측성) + 버퍼 3주.

## W1 — 환경 + repo 척추 + 로드맵 확정 [Block 0]
- [x] [평일] D1: ai-infra-lab repo 생성 + 디렉토리 골격(training/serving/docker/notebooks/models/docs) 커밋, models/ gitignore
  - 🎯 개념: monorepo로 학습/서빙/인프라를 한 곳에 두는 이유, 대용량 모델 바이너리를 git에서 빼는 이유(.gitignore)
  - ✅ 완료: GitHub(private)에 골격이 push되고 origin 연결됨
- [x] [평일] D2: venv + PyTorch(CPU) 설치 + requirements.txt 커밋
  - 🎯 개념: 가상환경(venv)으로 의존성 격리하는 이유, PyTorch CPU 빌드, requirements로 버전 고정
  - ✅ 완료: `import torch` 무오류 + requirements.txt 커밋
- [x] [평일] D3: `python -c "import torch; print(torch.__version__, torch.cuda.is_available())"` 성공, 결과 docs/log.md 기록
  - 🎯 개념: CUDA란 무엇이고 왜 CPU Mac에선 False인지. GPU 실습은 Block 2에서 클라우드 GPU VM으로
  - ✅ 완료: 버전 + False 출력 확인, docs/log.md에 기록
- [x] [평일] D4: 파이썬 문법 예제(f-string·타입힌트) — `python/W1D4/practice.py` 커밋
  - 참고: ROADMAP v3 전환으로 문법 드릴 방식 종결 — comprehension 등 나머지는 train_mnist.py 작성 중 자연 습득
- [ ] [평일] D5: `train_mnist.py` **S2 — load_data() 구현** (MNIST 다운로드 → DataLoader)
  - 🎯 개념: Dataset/DataLoader = 학습 데이터 공급 파이프라인, transform(ToTensor: 이미지→0~1 텐서)
  - 📖 자료: `python/train_mnist.py`의 S2 docstring 힌트 3단계 (그대로 따라가면 됨)
  - ✅ 완료: `python python/train_mnist.py` 실행 시 data/ 다운로드 후 "S3" 안내가 뜨고, 구현 커밋됨
  - ⚠️ 막히면: import 에러 → venv 활성화(`which python`) 확인. 다운로드 실패 → 네트워크 확인 후 재실행
- [ ] [주말] `train_mnist.py` **S3 — SimpleNet(nn.Module) 구현** + S1 코드 정독
  - 🎯 개념: nn.Module 클래스와 super().__init__(), Flatten→Linear→ReLU→Linear 구조. S1의 argparse/logging이 왜 인프라 도구의 골격인지
  - ✅ 완료: 실행 시 "S4" 안내가 뜨고 커밋됨 + log.md에 argparse/logging 요점 3줄

## W2 — Block 0 완료 → Block 1 진입
- [ ] [평일] D1: `train_mnist.py` **S4 — train() 학습 루프 구현**
  - 🎯 개념: 학습 루프 5박자(zero_grad→forward/loss→backward→step→log), 데이터도 `.to(device)` 해야 하는 이유
  - 📖 자료: S4 docstring 힌트 (루프 골격 그대로 제공됨)
  - ✅ 완료: `--epochs 1` 학습이 돌고 loss가 로그에 찍힘, 커밋
- [ ] [평일] D2: **S5 — 모델 저장/재로드 + 예외처리** → 🎉 Block 0 완료 기준 충족
  - 🎯 개념: state_dict 저장/로드, try/except로 "무엇이 왜 실패했는지" 구분하는 인프라 코드 기본기
  - ✅ 완료: models/mnist.pt 저장→재로드 성공, 전체 파이프라인 무오류 실행, 커밋
- [ ] [평일] D3: Linux 기본 — `docker run -it ubuntu`에서 top/권한/패키지/journalctl 감잡기 (Docker Desktop/OrbStack 설치 겸)
  - 🎯 개념: 서버의 기본 화면 — 프로세스(top), 권한(chmod/sudo), 로그(journalctl). macOS와 뭐가 다른가
  - ✅ 완료: 컨테이너 안에서 명령 실행해보고 새로 안 것 3개를 log.md에 기록
- [ ] [평일] D4: Block 0 회고(버퍼 잔여 기록) + Block 1 시작 — Docker 이미지/레이어/볼륨 개념
  - 🎯 개념: 이미지 vs 컨테이너, 레이어 캐시, 데이터는 볼륨으로 분리하는 이유
  - ✅ 완료: log.md에 `[Block 1 시작]` 표기 + 개념 요약
- [ ] [평일] D5: Dockerfile 초안 — CUDA 베이스 이미지에 train_mnist.py 탑재 (CPU 경로)
  - 🎯 개념: 베이스 이미지 선택(nvidia/cuda vs NGC PyTorch), COPY/RUN/CMD
  - ✅ 완료: `docker build`가 통과하는 Dockerfile 커밋 (docker/)
- [ ] [주말] Dockerfile 완성 — 멀티스테이지 + .dockerignore + 컨테이너로 학습 실행 검증
  - 🎯 개념: 멀티스테이지로 이미지 슬림화, .dockerignore로 빌드 컨텍스트 정리, 시크릿 커밋 금지 규칙
  - ✅ 완료: `docker run`으로 train_mnist.py가 컨테이너 안에서 돌고 커밋됨

<!-- 다음 구간은 해당 블록 진입 직전에 /study-coach plan 또는 ROADMAP.md 주차 마일스톤 기준으로 일별 상세화한다. -->
## W3 — Block 1: NVIDIA Container Toolkit 원리 + NGC (상세화 대기)
## W4 — Block 1: GPU 실습 환경 결정 — gpu-access-decision.md 커밋 게이트 (상세화 대기)
## W5 — Block 2: 스택 확인 랩 — 드라이버/CUDA/호환성 매트릭스 (상세화 대기)
## W6 — Block 2: 함정 재현 랩 — no kernel image 재현→해결 (상세화 대기)
## W7 — Block 2: OOM 랩 — VRAM과 모델 크기 (상세화 대기)
## W8 — Block 3: Linux 서버 실무 — systemd/드라이버 설치 갈림길 (상세화 대기)
## W9 — Block 3: GPU 서버 아키텍처 — NVLink/NUMA/스토리지 (상세화 대기)
## W10 — Block 3: 토폴로지 읽기 — topo -m/nccl-tests (상세화 대기)
## W11 — Block 4: kind로 K8s 개념 + Helm (상세화 대기)
## W12 — Block 4: GPU Operator + GPU Pod (상세화 대기)
## W13 — Block 5: vLLM 서빙 + 벤치마크 (상세화 대기)
## W14 — Block 5: TRT-LLM 프리빌트 + 서빙 인증 1겹 (상세화 대기)
## W15 — Block 5: DDP 토이 + 체크포인트 재개 (상세화 대기)
## W16 — Block 5: MLflow 1런 + 트랙 회고 (상세화 대기)
## W17 — Block 6: DCGM→Prometheus→Grafana 대시보드 (상세화 대기)
## W18 — Block 6: 알림·장애 플레이북·패치 위생 (상세화 대기)
## W19 — Block 6: 백업 개념 + 캡스톤 ops 핸드북 (상세화 대기)

---
## 검토 로그 (review가 append)
<!-- /study-coach review가 날짜별 채점·피드백을 여기 누적. 면접 회고의 원천. -->

### 2026-06-29 — W1 D1 ✅
- 잘한 점: 디렉토리 골격 12개 + `models/` gitignore + GitHub(private) push 완료. git remote URL의 토큰 노출을 스스로 발견해 정리하고 log.md에 기록한 건 인프라 엔지니어다운 대응.
- 고칠 점: README가 한 줄뿐 → 주말 항목에서 목표·디렉토리 설명 채우기. `.gitignore`에 `.venv/`·`__pycache__/`·`*.pyc` 추가 권장(D2 venv 대비). 빈 디렉토리는 git이 추적 안 함 — 파일 생기면 자동 포함되니 지금은 무방.
- 다음 주의: 토큰을 URL에 평문 저장하는 방식은 노출이 지속됨 → 노출된 토큰 폐기 + 새 토큰 사용 권장.

### 2026-06-30 — W1 D2 ✅
- 잘한 점: torch 2.12.1 + torchvision 설치, requirements.txt로 버전 `==` 고정, `.gitignore`에 `.venv/`·`__pycache__/`·`*.pyc` 추가(어제 피드백 즉시 반영). `import torch` 무오류 + cuda False 확인.
- 고칠 점: docs/log.md에 D2 회고가 빠짐(D1만 있음) — 세션 마감 4줄 남기는 습관 유지. requirements.txt가 전체 freeze(113줄)라 직접 의존(torch/numpy/scikit/jupyter)과 전이 의존이 섞임 — 지금은 무방, 나중에 직접 의존만 분리(requirements.in 등)하면 재현·감사 쉬움.
- 다음 주의: cuda False가 정상(CPU). D3은 이를 명시 확인하고 docs/log.md에 기록하는 단계 — 사실상 거의 됐으니 기록만 남기면 빠르게 완료.

### 2026-06-30 — W1 D3 ✅
- 잘한 점: `import torch 2.12.1 / cuda False`를 log.md에 명확히 기록. GPU 없는 CPU=정상이라는 점을 연결해 이해한 게 좋음. README도 작성해 W1 주말 항목(디렉토리 설명)을 일부 선취.
- 고칠 점: D2·D3을 한 로그 항목에 묶음 — 진도 추적엔 무방하나 앞으로 항목별 분리하면 회고가 또렷.
- 다음 주의: D4는 **코드 산출물(예제 .py)이 처음 생기는 항목** — `training/` 또는 `notebooks/`에 두고 커밋.

### 2026-07-01 — 새 산출물 없음
- 마지막 검토(6-30) 이후 ai-infra-lab에 새 커밋 없음(마지막 커밋 6-30 13:50 README). 진도 그대로 W1 D3까지 유지 — 억지 체크 안 함.
- 상태: tracked 파일은 `.gitignore`·`README.md`·`docs/log.md`·`requirements.txt` 4개. `training/`·`notebooks/`에 아직 `.py`/`.ipynb` 산출물 없음 → D4가 첫 코드 커밋 지점.
- 다음 주의: D4(comprehension·f-string·타입힌트 예제 .py 1개)를 커밋해야 진도가 나간다.

### 2026-07-02 — W1 D4 ✅ + 커리큘럼 v3 전환
- D4 채점: `python/W1D4/practice.py` 커밋 — f-string·타입힌트 사용(기준 3개 중 2개). comprehension 미사용이나 로드맵 전환으로 문법 드릴 종결 — 이후 train_mnist.py 작성 중 자연 습득. 코드 품질 메모: 불필요한 세미콜론, 미사용 import(`from numpy import number`), f-string 안 `$`는 리터럴 출력 — S2 구현 때 정리 습관 들일 것.
- 대형 변화: **ROADMAP.md v3 확정**(7블록 인프라 빌더 트랙, 학습 우선 — 블랙웰 특화는 부록 A/B) + `python/train_mnist.py` 스캐폴드 커밋(S1 완성, S2~S5 TODO). 이 study-state를 v3 구조(W1~19 ↔ Block 0~6)로 재편 — 완료 이력(D1~D4)과 검토 로그는 보존.
- 운영 메모: 09:30 자동 리뷰가 세션 한도(resets 14:10)로 실패 → 16:53 --force 재실행으로 복구. 폴백 브리핑(study-brief.py)은 정상 동작했음.
- 다음: W1 D5 = train_mnist.py **S2(load_data) 구현** — S2 docstring 힌트 3단계 참고. 집에서 진행 예정(양 repo pull 잊지 말 것).
