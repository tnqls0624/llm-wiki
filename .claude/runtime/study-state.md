<!-- study-state v1 | block=0 | last_brief_date=2026-07-12 | repo_path=~/Desktop/Project/ai-infra-lab -->
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
**현재**: 🎉 Block 0 완료(2026-07-05). **[Block 1 진행]** — 🎉 W2 전체 완료(2026-07-12, 멀티스테이지 `docker build`/`run` 완주 + 크기·CoW 실측). 다음: **W3 상세화 필요** — `/study-coach plan`으로 일별 항목을 채워야 브리핑이 나온다.
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
- [x] [평일] D5: `train_mnist.py` **S2 — load_data() 구현** (MNIST 다운로드 → DataLoader)
  - 🎯 개념: Dataset/DataLoader = 학습 데이터 공급 파이프라인, transform(ToTensor: 이미지→0~1 텐서)
  - 📖 자료: `python/train_mnist.py`의 S2 docstring 힌트 3단계 (그대로 따라가면 됨)
  - ✅ 완료: `python python/train_mnist.py` 실행 시 data/ 다운로드 후 "S3" 안내가 뜨고, 구현 커밋됨
  - ⚠️ 막히면: import 에러 → venv 활성화(`which python`) 확인. 다운로드 실패 → 네트워크 확인 후 재실행
- [x] [주말] `train_mnist.py` **S3 — SimpleNet(nn.Module) 구현** + S1 코드 정독
  - 🎯 개념: nn.Module 클래스와 super().__init__(), Flatten→Linear→ReLU→Linear 구조. S1의 argparse/logging이 왜 인프라 도구의 골격인지
  - ✅ 완료: 실행 시 "S4" 안내가 뜨고 커밋됨 + log.md에 argparse/logging 요점 3줄

## W2 — Block 0 완료 → Block 1 진입
- [x] [평일] D1: `train_mnist.py` **S4 — train() 학습 루프 구현**
  - 🎯 개념: 학습 루프 5박자(zero_grad→forward/loss→backward→step→log), 데이터도 `.to(device)` 해야 하는 이유
  - 📖 자료: S4 docstring 힌트 (루프 골격 그대로 제공됨)
  - ✅ 완료: `--epochs 1` 학습이 돌고 loss가 로그에 찍힘, 커밋
- [x] [평일] D2: **S5 — 모델 저장/재로드 + 예외처리** → 🎉 Block 0 완료 기준 충족
  - 🎯 개념: state_dict 저장/로드, try/except로 "무엇이 왜 실패했는지" 구분하는 인프라 코드 기본기
  - ✅ 완료: models/mnist.pt 저장→재로드 성공, 전체 파이프라인 무오류 실행, 커밋
- [x] [평일] D3: Linux 기본 — `docker run -it ubuntu`에서 top/권한/패키지/journalctl 감잡기 (Docker Desktop/OrbStack 설치 겸)
  - 🎯 개념: 서버의 기본 화면 — 프로세스(top), 권한(chmod/sudo), 로그(journalctl). macOS와 뭐가 다른가
  - ✅ 완료: 컨테이너 안에서 명령 실행해보고 새로 안 것 3개를 log.md에 기록
- [x] [평일] D4: Block 0 회고(버퍼 잔여 기록) + Block 1 시작 — Docker 이미지/레이어/볼륨 개념
  - 🎯 개념: 이미지 vs 컨테이너, 레이어 캐시, 데이터는 볼륨으로 분리하는 이유
  - ✅ 완료: log.md에 `[Block 1 시작]` 표기 + 개념 요약
- [x] [평일] D5: Dockerfile 초안 — CUDA 베이스 이미지에 train_mnist.py 탑재 (CPU 경로)
  - 🎯 개념: 베이스 이미지 선택(nvidia/cuda vs NGC PyTorch), COPY/RUN/CMD
  - ✅ 완료: `docker build`가 통과하는 Dockerfile 커밋 (docker/)
- [x] [주말] Dockerfile 완성 — 멀티스테이지 + .dockerignore + 컨테이너로 학습 실행 검증
  - 🎯 개념: 멀티스테이지로 이미지 슬림화, .dockerignore로 빌드 컨텍스트 정리, 시크릿 커밋 금지 규칙
  - ✅ 완료: `docker run`으로 train_mnist.py가 컨테이너 안에서 돌고 커밋됨

<!-- 다음 구간은 해당 블록 진입 직전에 /study-coach plan 또는 ROADMAP.md 주차 마일스톤 기준으로 일별 상세화한다. -->
## W3 — Block 1: NVIDIA Container Toolkit 원리 + NGC (상세화 2026-07-12)
- [ ] [평일] D1: NVIDIA 스택 지도 — 드라이버 vs CUDA 툴킷 vs 컨테이너 런타임 (retrieval-first)
  - 🎯 개념: 호스트 커널 드라이버 / CUDA 런타임·툴킷 / 컨테이너의 경계. W2에서 목격한 "NVIDIA Driver was not detected" 경고가 정확히 어느 층의 부재인가
  - 📖 자료: **먼저 무자료로** log.md에 스택 그림+설명 → 그다음 NVIDIA Container Toolkit 공식 아키텍처 문서와 대조
  - ✅ 완료: log.md에 자기 말 스택 지도 + 대조에서 틀렸던 부분 수정 기록
- [ ] [평일] D2: NVIDIA Container Toolkit 동작 원리 — `--gpus all`이 하는 일
  - 🎯 개념: nvidia-container-runtime이 컨테이너 시작 시점에 드라이버 라이브러리·`/dev/nvidia*`를 주입하는 구조(runc hook). "이미지에 드라이버를 안 굽는" 이유가 여기서 완성됨
  - ✅ 완료: log.md에 주입 흐름 요약 + Block 2 D1에서 실측할 체크리스트 3개
- [ ] [평일] D3: CPU Mac에서 가능한 실측 — 컨테이너 안 드라이버 부재 확인
  - 📖 자료: `docker run --rm mnist-train:multistage sh -c "ls /dev | grep -i nvidia; ldconfig -p | grep -i cuda"` → 이어서 `--gpus all` 시도 시 에러 관찰
  - ✅ 완료: 출력과 에러를 log.md "발생한 문제/확인" 칸에 기록 — **에러가 나는 게 정상인 실험**
- [ ] [평일] D4: NGC 카탈로그 + 이미지 태그 체계
  - 🎯 개념: nvidia/cuda의 base/runtime/devel 3티어 차이, NGC PyTorch 년.월 태그 체계, 각각 언제 쓰나
  - ✅ 완료: "내 Dockerfile은 왜 runtime 티어로 충분한가 + devel이 필요해지는 경우"를 log.md에 자기 말로
- [ ] [평일] D5: 시크릿 규칙 확립 — NGC API key (W1 D1 PAT 사건 재발 방지)
  - 🎯 개념: nvcr.io 로그인은 `$oauthtoken` + API key. 키는 환경변수/키체인으로만 — 커밋·Dockerfile 하드코딩 금지 규칙화
  - ✅ 완료: NGC 계정+API key 발급, `docker login nvcr.io` 성공, 시크릿 규칙 3줄을 docs/notes 또는 log.md에 커밋(키 값 자체는 어디에도 안 남김)
- [ ] [주말] cuda 이미지 3티어 실측 — base vs runtime vs devel
  - 🎯 개념: 티어별 크기·내용물 차이를 수치로 — W2 크기 실측의 연장선
  - 📖 자료: `docker pull nvidia/cuda:12.4.1-{base,runtime,devel}-ubuntu22.04` → `docker images`·`docker history`·컨테이너 안 `nvcc --version`(devel만 성공)·`ldconfig -p | grep cuda` 대조
  - ✅ 완료: 비교표+관찰을 `docs/notes/block1-cuda-image-tiers.md`로 커밋 (다운로드 ~5GB)
  - ⚠️ 막히면: 디스크 부족 → 실측 후 `docker rmi <태그>`로 개별 정리 (`prune -a` 금지 — 7-12 전체 소실 사건 참고)

## W4 — Block 1: GPU 실습 환경 결정 — gpu-access-decision.md 커밋 게이트 (상세화 2026-07-12)
- [ ] [평일] D1: 요구사항 정리 — Block 2~3 실습이 GPU 환경에 요구하는 것
  - 🎯 개념: root 있는 단일 GPU VM이어야 하는 이유(드라이버 설치 실습), Turing 이상이어야 하는 이유(CUDA 13.x의 Volta 이하 제거), RunPod/Vast 컨테이너 대여 불가 이유
  - ✅ 완료: 요구사항 체크리스트를 자기 말로 log.md에 — ROADMAP 주의사항과 대조
- [ ] [평일] D2: 후보 조사 ① — Lambda / AWS(g4dn·g5·g6)
  - ✅ 완료: 인스턴스 타입·GPU 모델·시급·리전·스팟 여부 비교표 log.md 기록
- [ ] [평일] D3: 후보 조사 ② + 예산 산정
  - 🎯 개념: 온디맨드 vs 스팟 트레이드오프(회수 리스크), 총 15~25h × 시급 = 예산($50~100 목표)
  - ✅ 완료: 후보 3곳 이상 비교표 완성 + 예산 상한 결정
- [ ] [평일] D4: 결정 — `docs/notes/gpu-access-decision.md` 커밋 (🎉 Block 1 게이트)
  - ✅ 완료: 프로바이더·인스턴스 타입·GPU 모델·시급·예산 상한·스팟 회수 대응이 적힌 결정 문서 커밋. **이 커밋 없이 Block 2 진입 금지**
- [ ] [평일] D5: 계정·쿼터 선처리 + Block 1 회고
  - 🎯 개념: GPU 인스턴스 쿼터 승인은 며칠 걸릴 수 있음 — Block 2 첫날 막히지 않게 지금 신청
  - ✅ 완료: 계정·결제·쿼터 신청 상태 log.md 기록 + Block 1 회고(`[Block 2 준비]` 표기)
- [ ] [주말] 스모크 테스트 — 결정한 환경에서 인스턴스 1회 기동 (실비용 ~$5, 2026-07-12 사용자 승인)
  - 🎯 개념: 결정이 실제로 뜨는지 Block 2 전에 확인 — 기동→ssh→`nvidia-smi`→**즉시 종료**
  - ✅ 완료: nvidia-smi 출력(드라이버·CUDA 버전·GPU 모델)을 log.md에 기록 + 인스턴스 종료·과금 중단 확인
  - ⚠️ 막히면: 쿼터 거부/대기 → D5 신청 티켓 상태 확인, 길어지면 대체 프로바이더 스위치 판단
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

### 2026-07-05 — W1 D5 + 주말 + W2 D1·D2 ✅ (S2~S5 완주 → 🎉 Block 0 완료)
- 잘한 점: 하루 세션에서 S2(load_data)만 예정이었으나 **S3~S5까지 완주**해 train_mnist.py 전 파이프라인을 `--epochs 1`로 실행 검증. DataLoader vs Dataset 반환 버그를 스스로 발견·수정했고, batch 64 vs 256 실험으로 "총 연산량은 같고 업데이트 횟수(938 vs 235)가 loss에 영향"을 직접 관찰 — 복붙이 아닌 CS 이해 목표에 정확히 부합. y=wx+b 선형대수 직관까지 병행 학습.
- 고칠 점(구체):
  1) **`main()` 종료 코드 버그** — `except OSError` 브랜치가 bare `return`(→ None)이라 `sys.exit(None)`=exit 0. 즉 I/O 실패인데 성공(0)으로 종료됨. 인프라 코드는 실패를 **exit code로** 알려야 함 → `return 1`. `NotImplementedError` 브랜치도 마찬가지, `-> int` 시그니처와도 불일치.
  2) **세미콜론** — D4 리뷰에서 지적한 습관이 S2~S5 전반에 다시 등장(`tf = ...;`). Python은 불필요 — 커밋 전 제거 습관.
  3) `torch.load(path)` → 최신 PyTorch는 `weights_only=True` 권장(pickle 역직렬화 보안 경고 회피). state_dict 로드엔 안전한 옵션.
  4) 죽은 주석(`# raise NotImplementedError(...)`) 잔존 — 구현 끝나면 삭제.
- 다음 주의: test_loader를 만들지만 정확도 평가는 없음(Block 0 범위상 무방). W2 D3부터는 코드가 아니라 Linux/Docker 감각 — `docker run -it ubuntu`에서 top/권한/journalctl을 직접 만져보고 log.md에 "새로 안 것 3개" 남기기가 완료 기준. 병행 중인 수학(함수/이차함수/지수로그)은 좋은 방향.

### 2026-07-05 (저녁 재검토)
- 새 커밋 1개: `697a024` docs/log.md W1 D5 회고(세션 마감 4형식 준수) — 아침 검토에 이미 반영된 내용의 커밋화. 코드 변경 없음 → 체크 변동 없음.
- 세션 관찰: **졸업 시험 예측 1번을 실전 수행** — 네트워크 차단 후 실행해 torchvision이 밑바닥 OSError(URLError←gaierror)를 `RuntimeError`로 재포장해 던지는 것을 traceback으로 직접 확인(`except OSError` 미포착 → unhandled로 exit 1). "라이브러리 예외 계약은 목격으로 안다"를 체득한 좋은 실험. batch 의미(938 vs 235 = 60,000÷batch_size)와 `return 1`→`sys.exit(main())` 종료 흐름도 세션에서 확립.
- 다음 주의: **exit code 수정(`return 1`)·`--device` 플래그·예측 2·3번이 아직 미커밋** — 월요일 워밍업으로 커밋하면 다음 검토에서 채점. 이후 D3(Linux 기본, `docker run -it ubuntu`) 진입.
- (심야 추가) 졸업 시험 진행: 예측 2번(models/ 권한 → torch.save의 EACCES→RuntimeError 재포장 + exit 0 버그 목격 → `return 1` 수정으로 exit=1 확인) 완료. **③ --device 완료 — 단 2회 실패 후 코치 제공 코드로 마감**(1차: 검사 없음+silent fallback / 2차: `pick_device.add_argument` 오타로 전 실행 즉사 — 셀프 실행 없이 리뷰 요청한 게 핵심 교훈). 인수 매트릭스 0/0/1/2 전부 통과. 냅킨 계산(101,770개·7B=28/14GB·13B fp16 26GB)은 공동 풀이. **재시험 2건 예약: 냅킨 3문 + pick_device 무힌트 재구현.** 잔여: ④ 예측 3번(.to(device) 함정, 예측 먼저) + 커밋(사용자 진행 중).

### 2026-07-06 — 새 커밋 2개 검토, 체크 없음 (W2 D3 부분 진행)
- 잘한 점: ① `8761381` exit code 숙제 이행 — 심야 검토 예고대로 `NotImplementedError`/`OSError` 브랜치를 `return 1`로 수정했고, `except (OSError, RuntimeError)` 확장은 "torchvision이 OSError를 RuntimeError로 재포장" 실험 결과를 근거로 연결한 정확한 수정(체크박스는 W2 D2 후속이라 변동 없음). ② `f8ce89f` W2 D3 착수 — `lscpu`·`top`·`free -m`·`df -h` 실행, 특히 "load average 최대치 ≈ 코어 수(11)" 통찰은 직접 관찰로 얻은 진짜 학습.
- 부족하거나 고칠 점: ① **W2 D3 미체크 유지(확인 필요)** — (a) 컨테이너(`docker run -it ubuntu`) 안에서 실행했는지 log.md에 명시 없음 (b) 항목이 요구한 권한(chmod/sudo)·패키지(apt)·journalctl 미다룸 (c) "새로 안 것 3개" 형식 미충족(확실한 통찰은 load average 1개), 로그가 "다음에 할 것: 너가 적어줘"로 미완. notes 3파일 변경은 빈 줄 포매팅뿐. ② 세미콜론 습관이 수정 커밋에도 잔존(`logger.error(...);`) — **3번째 지적**, 커밋 전 자기 리뷰 체크리스트에 넣을 것.
- 다음에 주의할 것: D3 마감 조건 — 컨테이너 **안에서** whoami/chmod/`apt update && apt install`/journalctl을 직접 실행(plain ubuntu 컨테이너엔 systemd가 없어 journalctl이 실패하는데, 그 실패 자체가 "컨테이너 ≠ 완전한 서버" 학습 포인트) 후 "새로 안 것 3개"를 log.md에 번호 목록으로 기록하면 체크. 그다음 D4(Block 0 회고 + 이미지/레이어/볼륨 개념) 진입.

### 2026-07-06 (밤 재검토) — 새 커밋 없음, 미커밋 log.md에서 D3 조작 실습 확인
- 확인: docs/log.md **미커밋 수정**에서 저녁 피드백 즉시 이행 — 프롬프트 `root@1e001715902c:/#`가 **컨테이너 안 실행을 확정**(아침 '확인 필요' (a) 해소). chmod 400→600 실험(ls -l 출력 증거 포함), `apt update && apt install`, whoami/id, journalctl 시도→실패 목격, vmstat 1까지 — D3의 조작 요구사항 전부 수행됨.
- 남은 것 2가지(체크는 보류): ① **"새로 안 것 3개"를 번호 목록으로 기록** — 지금은 명령 나열이라 "배운 것"이 없음. 특히 journalctl이 "왜" 실패했는지(PID 1=bash, systemd 부재 → 컨테이너 ≠ 완전한 서버)를 자기 말로 쓰는 게 핵심. ② **커밋** — 채점은 커밋 기준(두 Mac 동기화 전제). 둘 다 되면 다음 검토에서 체크.
- 다음에 주의할 것: log.md의 "발생한 문제: 없음"인데 journalctl 실패는 문제였다 — 실패를 '발생한 문제/해결' 칸에 쓰는 습관이 트러블슈팅 기록의 시작(면접 소재도 여기서 나옴). "다음에 할 것: 너가 적어줘"는 study-today.md 브리핑이 그 답.

### 2026-07-06 (심야) — 커밋 1개(`9e3c988`), W2 D3 체크 보류 유지
- 잘한 점: 밤 재검토 피드백의 ②(커밋)를 즉시 이행 — 하루에 검토→이행 루프를 세 번 돈 반응 속도가 이 시스템의 이상적인 사용 패턴. 컨테이너 실습 자체는 완결(조작 요구사항 전부 + chmod 출력 증거).
- 부족하거나 고칠 점: ①("새로 안 것 3개" 번호 목록)이 이번 커밋에도 없음 — 내용이 아까 본 미커밋 수정과 동일. 경계가 애매한 건 사실(load average 통찰은 명확히 서술됨, journalctl·chmod는 사실/증거만 있고 "배운 것" 서술이 없음)이나, "실행했다"와 "이해했다"의 구분이 이 트랙의 핵심 원칙이라 체크 보류. 특히 journalctl은 "실패했다"만 있고 **왜**(PID 1=bash, systemd 부재)가 없음 — 이걸 자기 말로 쓰는 순간이 학습이 완성되는 지점.
- 다음에 주의할 것: D3 마감 = log.md에 `새로 안 것: 1) … 2) … 3) …` 5분 서술 + 커밋(3번째 동일 지적 — 이번이 마지막이 되게). D4도 "log.md에 [Block 1 시작] 표기 + 개념 요약"이라 같은 근육을 씀. "발생한 문제: 없음" 칸 습관도 재차 강조.

### 2026-07-06 (심야 2차) — 새 커밋 없음, 미커밋 log.md에 '새로 안 것 3개' 추가 확인 → **커밋만 하면 D3 체크 확정**
- 판정: 미커밋 docs/log.md에 새로 안 것 3개(최소 이미지·journalctl 실패 이유·chmod 권한 비트)가 추가됨 — **내용은 완료 기준 충족으로 판정 완료**. 채점은 커밋 기준이므로 보류 — **다음 검토(무인 cron 포함)는 이 커밋이 확인되면 추가 판단 없이 D3을 체크할 것.**
- 짚을 점: 추가된 3줄이 코치가 준 힌트 문장 그대로(verbatim) — 사실관계가 본인 실험과 일치하고 코치가 완성 문장을 준 책임도 있어 이번엔 수용. 단 이 서술의 목적은 회상 연습(retrieval) — D4의 "[Block 1 시작] 개념 요약"부터는 **먼저 기억으로 쓰고 나서** 자료와 대조할 것.
- 다음에 주의할 것: 커밋 습관 — 산출물을 만들고도 커밋을 빼먹으면 이 시스템(두 Mac 동기화·무인 채점)에는 존재하지 않는 작업이 된다. 세션 마감 = 기록 + **커밋**까지가 한 동작.

### 2026-07-06 (심야 3차) — W2 D3 ✅ (`f16a571`)
- 채점: 심야 2차 판정대로 커밋 확인 즉시 체크. 완료 기준 전부 충족 — 컨테이너 안 실행(증거: `root@1e00…` 프롬프트), 조작 실습(chmod·apt·whoami/id·journalctl 실패 목격·vmstat), 새로 안 것 3개 log.md 기록 + 커밋.
- 총평: 하루에 검토→이행 루프 5회 — 관찰(lscpu/top/free/df)에서 시작해 피드백마다 빠짐없이 메꿔 마감까지 감. 이 반응 루프 자체가 시스템이 의도한 사용법. 아쉬운 점은 기존 지적 반복: 서술 3줄 verbatim 복붙(수용됨, 다음부턴 기억→대조), "발생한 문제: 없음" 칸 미활용(journalctl 실패가 거기 들어갈 내용).
- 다음: W2 D4 = Block 0 회고 + **[Block 1 시작]** — Docker 이미지 vs 컨테이너·레이어 캐시·볼륨 개념을 log.md에 요약(먼저 기억으로 쓰고 자료와 대조). Infra/06 컨테이너 내부 노트가 좋은 대조 자료.

### 2026-07-09 — W2 D4 ✅ (`c31cbcb`) + TIL 4편 소급 반영
- 잘한 점: ① D4 채점 — Docker 이미지/컨테이너/볼륨 개념을 **먼저 기억으로**("아는것을 적어봄") 자기 말로 서술. 7-06 verbatim 지적 이후 retrieval-first 처방이 처음으로 실전 이행됨. cgroups(자원)/namespace(격리) 구분 정확, 특히 온프레미스 레이어-diff 배포 실무 사례("발생한 문제/해결" 칸 활용)는 개념↔경험 연결의 모범 — 면접 소재감. ② 7-07 저녁 TIL 4편 커밋(`d75d332`·`fe5a227`·`cc3d1e7`) — 학습→블로그 아웃풋 루프 가동(검토 공백일 산출물 소급 반영; 7-07·7-08 무인 검토 로그 없음). ③ 학습 인프라 자가 개선(`d710b87`·`a4ffbf2`): ai-infra-lab CLAUDE.md가 study-today.md 심볼릭 링크를 @참조 — 브리핑이 학습 세션에 자동 주입되는 구조를 스스로 설계(링크·타깃 동작 확인됨).
- 부족하거나 고칠 점(기술 정밀도 — 내일 실습에서 검증): 1) "베이스 이미지를 복사하여 실행" → 실제로는 복사가 아니라 read-only 레이어들 위에 얇은 쓰기 레이어 하나를 얹는 **CoW(copy-on-write)**. `docker diff`/`docker history`로 실측 가능. 2) 레이어는 **불변(immutable)** — 변경이 "기존 레이어에 쌓이는" 게 아니라 새 레이어로 위에 쌓임. 캐시 무효화는 Dockerfile 명령 순서 기준(한 줄 바뀌면 그 아래 전부 재빌드) — D5에서 직접 체감할 것. 3) 볼륨 서술이 bind mount(호스트 디렉토리 마운트)에 가까움 — named volume(도커 관리 영역)과 구분. retrieval의 후반부(자료와 **대조**)는 아직 — 본인이 적은 내일 계획(volume 생존 실험·docker history)이 정확히 그 대조다.
- 다음에 주의할 것: 고객사명이 든 실무 사례는 private repo(log.md)까지만 — 공개 TIL/블로그로 옮길 땐 스크럽(soobeen-voice가 걸러주지만 본인도 인지). D5 완료 기준 = `docker build` 통과하는 Dockerfile 커밋(`docker/`), CUDA 베이스 이미지 선택(nvidia/cuda vs NGC PyTorch)이 첫 결정 지점.

### 2026-07-12 — W2 D5 ✅ (`4a9b603`~`15c3204`, 7-11 토 10커밋) / 주말 항목은 멀티스테이지만 남음
- 잘한 점: ① D5 초과 달성 — `docker build` 통과(기준)를 넘어 `docker run`으로 컨테이너 안 1 epoch 학습 완주(loss=0.0898, 저장/재로드까지). ② **빌드 에러 4종을 "발생한 문제" 칸에 원인까지 기록** — 7-06 세 차례 지적된 실패 미기록 습관(감시 ③)이 이번 세션에서 정확히 교정됨. ③ 캐시 무효화 실측(주석 1줄→재빌드→apt/pip CACHED·이미지 해시 변경 관찰)으로 D4 정밀도 피드백 ②를 실험으로 검증 — retrieval의 후반부(자료와 대조)를 실측으로 수행. ④ "다음에 할 것"을 정밀도 ①③ 넘버링에 연결해 스스로 구체화(감시 ⑤ 해소 지속). TIL 5편도 자기 말 서술 + 금융권 사례 고객사명 스크럽 준수.
- 부족하거나 고칠 점: ① **주말 항목 보류 — 멀티스테이지만 미구현**(.dockerignore·실행 검증은 D5에서 선취). 현 Dockerfile은 런타임 의존성만 설치해 슬림화 여지가 작지만 학습 목표는 메커니즘 — builder 스테이지에서 pip install 후 site-packages만 COPY하고 `docker images`로 크기 전후를 실측하면 체감됨. ② 컨테이너의 `pip3 install torch torchvision`이 **버전 무핀** — 이미지는 매 빌드마다 최신을 받아 로컬 venv(실측 torch 2.12.1/torchvision 0.27.1)와 갈라질 수 있음(재현성). 로컬 실측 버전 기준 `torch==2.12.1` 식 핀 권장. (정정: requirements.txt는 7-02에 의도적 무핀 큐레이션으로 정리됨 — "== 고정"은 6-30 상태 기준의 옛 정보였음.) ③ `f0384eb`가 CMD shell form 실패 기록을 삭제 — 실패 기록을 지울 땐 "확인해보니 X여서 제거" 사유를 커밋 본문이나 log.md에 남길 것(트러블슈팅 이력의 신뢰성).
- 다음에 주의할 것: 주말 마감 조건 = 멀티스테이지 변환 + 재빌드·재실행 통과 + 커밋(하나 남음). 본인이 적은 계획(`-v` 마운트로 data/models 분리·`docker diff` CoW 확인)은 정밀도 ①③ 검증이라 같은 세션에서 병행하기 좋음. Block 1 게이트 (b) gpu-access-decision.md는 W4 항목 — 서두를 필요 없음.

### 2026-07-12 (오후, 대화형) — 멀티스테이지 초안 리뷰: 빌드 통과 but 실행 불가 (미커밋)
- 확인: 미커밋 docker/Dockerfile이 멀티스테이지(builder venv → runner COPY)로 변환됨 — venv-copy 패턴 정석, `--no-install-recommends`·`libgomp1`·`ca-certificates`·`PYTHONUNBUFFERED=1` 등 의존성 사고 좋음. 코치가 빌드 검증: `docker build` 통과, 크기 3.22GB→2.71GB(-510MB) 실측.
- **불합격 사유(코치 실측)**: `docker run … python -c "import torch"` → **`ModuleNotFoundError: No module named 'ctypes'`**. 원인 = runner의 `python3-minimal`은 인터프리터 최소본만 — ctypes 등 stdlib 대부분은 `libpython3.10-stdlib`(full `python3`가 끌고 옴)에 있고, **venv 복사로는 안 따라옴**(venv는 site-packages만 담고 stdlib은 시스템 것을 참조). "빌드 통과 ≠ 동작" — 7-05 교훈 그대로.
- 추가 지적: 핀 값 `torch==2.5.1/torchvision==0.20.1`이 로컬 실측(2.12.1/0.27.1)과 불일치 — 외부 예제 조합으로 의심(무검토 붙여넣기 패턴). 로컬 기준으로 핀 교체 필요. 마감 조건 = ① runner python 패키지 수정 ② 핀 교체 ③ 재빌드+`docker run` 1 epoch 완주(본인 실행) ④ log.md 실측 기록 ⑤ 커밋 — 다음 검토에서 확인되면 주말 항목 체크.

### 2026-07-12 (오후 2차) — W2 주말 ✅ (`2d82b38`~`9ccca23` 4커밋) → 🎉 W2 완료
- 채점: 마감 조건 ①~⑤ 전부 이행 확인 — 멀티스테이지 Dockerfile+핀(2.12.1/0.27.1) 커밋, 컨테이너 학습 실행(13s/3.5s, loss 3회 관찰), 크기·CoW 실측 기록, working tree clean → 체크. 중간에 "저장 전 빌드로 옛 이미지(2.5.1) 실행"을 시각 대조로 잡아냈고, 이후 이미지 내부를 직접 열어 확인하는 검증("아티팩트 쪽을 확인한다")을 본인이 재현함. "커밋했다" 선언 후 커밋 0개였던 해프닝 1회(감시 ② — git log로 확인하는 습관 재강조 후 즉시 이행).
- 잘한 점: ① **크기 실측의 해상도** — 3.22→2.90GB(-320MB)를 레이어 단위로 분해(apt 345→32.3MB가 절감의 거의 전부, torch venv 779→772MB 동일)해 "실행 라이브러리는 멀티스테이지로 못 줄인다"를 수치로 결론. CUDA 베이스 유지 결정도 근거(Block 2 GPU 전환)와 함께 기록. ② `-v` 마운트+`docker diff`로 CoW 우회 실측(D4 정밀도 ①③ 마감) — mtime 초 단위 대조, 마운트 시 diff 0줄. ③ 부수 관찰 2건(^C가 exec form PID 1에 직접 전달됨, 로그 loss는 에포크 평균이 아닌 마지막 배치 값) — 실험 설계 강점 그대로.
- 부족하거나 고칠 점: **"발생한 문제" 칸 오용 재발(감시 ③)** — 오늘 실제 문제 2건(runner `python3-minimal`의 ctypes ModuleNotFoundError, 저장 전 빌드로 옛 이미지 실행)이 log.md에 없고, 그 칸을 멀티스테이지 일반론(AI 설명체 "~해보자/~않아" verbatim 대량 복붙)이 차지. "오늘 한 것" 첫 줄도 브리핑 🎯 문구 그대로. 자기 실측 파트(2·3절)는 살아있는데 이론 서술이 복붙 — retrieval-first 전반부(먼저 기억으로) 생략.
- 다음에 주의할 것: W3~가 상세화 대기 — `/study-coach plan`을 돌려야 내일 브리핑이 나온다. named volume 비교(정밀도 ③ 나머지)·gpu-access-decision.md(W4 게이트)는 본인 계획에 이미 있음. ctypes·옛 이미지 사건 2줄을 log.md "발생한 문제" 칸에 추가하는 5분 커밋 권장 — 오늘 최고의 면접 소재.

### 2026-07-12 (오후 3차) — 발생한 문제 2불릿, 사용자 명시 요청으로 코치가 log.md에 직접 기입 (미커밋)
- 빈칸 템플릿 제안을 거절하고 코치 직접 기입을 2회 명시 요청 → 읽기 전용 원칙의 대화형 예외로 **편집만** 수행, 커밋은 사용자 몫으로 남김. 해당 2불릿(ctypes 실패·저장 전 빌드)은 **코치 작성** — 향후 채점에서 본인 서술(retrieval)로 계산하지 않는다.
- 감시 ① 누적: 이번 세션에서 자기 말 서술 회피가 2건(발생한 문제 칸을 이론 복붙으로 채움 + 이번 기입 위임). 다음 세션 워밍업으로 retrieval 재시험 권장: "venv 디렉토리에는 무엇이 들어있고 stdlib은 어디서 오나"를 무자료로 설명시키기(기존 재시험 2건 — 냅킨 3문·pick_device 무힌트 — 과 함께 대기열 3건).

### 2026-07-12 (저녁) — 새 커밋 없음 · TIL 6편 파이프라인 완료 · 다음 = W3 plan
- 검토: `9c545da` 이후 새 커밋 없음, working tree clean — 채점 변동 없음(W2는 오후에 완료 확정). 저녁 작업은 블로그 파이프라인: TIL 6편 임시저장(soobindairy.tistory.com) + 이미지 3장 준비 완료([사진 1] 코치 자체 제작 다이어그램 / [사진 2]·[사진 3] 본인 캡처 — ctypes 재현 시 스테이지 혼동 1회·`python3--minimal` 오타 1회를 스스로 수습). 재현용 컨테이너·이미지 뒷정리까지 확인됨.
- 관찰: 캡처 재현 중 `docker system prune -a`(추정)로 전체 이미지·빌드 캐시 소실 → 커밋된 Dockerfile에서 풀 재빌드로 복구(코치 실행). "이미지는 소스에서 재생 가능한 산출물, prune -a와 rmi <태그>의 차이"가 덤 학습 — 다음 세션에서 log.md에 남길 가치 있음(오늘은 미기록, 커밋 없었으므로 강제 아님).
- 다음에 주의할 것: **W3(NVIDIA Container Toolkit + NGC)가 상세화 대기** — 일별 체크리스트가 없어 내일 아침 브리핑이 비어 나온다. `/study-coach plan`으로 W3~W4(Block 1 잔여) 상세화가 최우선. 블로그는 발행 전 최종 검토만 남음(발행은 본인).
