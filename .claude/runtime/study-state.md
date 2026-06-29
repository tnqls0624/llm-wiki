<!-- study-state v1 | block=1 | last_brief_date=2026-06-29 | repo_path=~/Desktop/Project/ai-infra-lab -->
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

# AI Infra 학습 진도 — 블록1 (Python/ML → PyTorch → FastAPI → Docker)

목표: **"PyTorch로 학습한 모델 → 저장 → FastAPI 추론 API → Docker 이미지"** 파이프라인을 자기 손으로 완성.
프로젝트: `ai-infra-lab` 단일 repo 단계 확장. K8s/GPU/분산학습/vLLM은 블록2(13~24주)로 미룸.

## W1 — 환경 + repo 척추
- [ ] [평일] D1: ai-infra-lab repo 생성 + 디렉토리 골격(training/serving/docker/notebooks/models/docs) 커밋, models/ gitignore
  - 🎯 개념: monorepo로 학습/서빙/인프라를 한 곳에 두는 이유, 대용량 모델 바이너리를 git에서 빼는 이유(.gitignore)
  - ✅ 완료: GitHub(private)에 골격이 push되고 origin 연결됨
  - ⚠️ 막히면: `gh auth status`로 로그인 확인, remote는 `git remote -v`
- [ ] [평일] D2: venv + PyTorch(CPU) 설치 + requirements.txt 커밋
  - 🎯 개념: 가상환경(venv)으로 의존성 격리하는 이유, PyTorch CPU 빌드, requirements로 버전 고정
  - 📖 자료: pytorch.org/get-started/locally (OS/CPU 설치 명령), 점프투파이썬 가상환경 절
  - ✅ 완료: `import torch` 무오류 + requirements.txt 커밋
  - ⚠️ 막히면: pip 느림→pytorch.org 인덱스 명령 사용, 휠 충돌→python 3.10~3.12 권장
- [ ] [평일] D3: `python -c "import torch; print(torch.__version__, torch.cuda.is_available())"` 성공, 결과 docs/log.md 기록
  - 🎯 개념: CUDA란 무엇이고 왜 회사/집 Mac에선 False인지(GPU 없음 = CPU 텐서). 블록2에서 EKS GPU로 바뀜
  - ✅ 완료: 버전 + False 출력 확인, docs/log.md에 기록
  - ⚠️ 막히면: False는 정상. import 에러면 venv 활성화 확인(`which python`)
- [ ] [평일] D4: 점프투파이썬에서 list/dict comprehension·f-string·타입힌트만 복습 + 짧은 예제 1개
  - 🎯 개념: comprehension(파이썬다운 반복), f-string(포매팅), 타입힌트(FastAPI/Pydantic 전제)
  - 📖 자료: 점프투파이썬(wikidocs.net/book/1) 해당 절만
  - ✅ 완료: 세 문법을 쓴 예제 .py 1개 커밋
- [ ] [평일] D5: 데코레이터 + `with` 컨텍스트매니저 확인 (FastAPI/PyTorch에서 쓰임)
  - 🎯 개념: 데코레이터(FastAPI 라우트 `@app.get`), with(파일·`torch.no_grad()` 자원 관리)
  - ✅ 완료: 데코레이터 1개 직접 작성 + with 예제 실행
- [ ] [주말] repo 골격 + venv + requirements.txt + README(목표·디렉토리 설명) 커밋, import 성공 기록 docs/
  - 🎯 개념: 한 주 배운 환경을 하나로 통합 — 클린 체크아웃에서 재현 가능한 상태 만들기
  - ✅ 완료: 새 터미널에서 venv 활성화 → import torch 성공, README에 디렉토리 설명

## W2 — numpy + 데이터 감각
- [ ] [평일] D1: numpy 배열 생성·인덱싱·`shape` (Tensor의 전신)
  - 🎯 개념: ndarray와 shape — PyTorch Tensor의 기반. 차원(axis) 개념
  - 📖 자료: 혼공머신 numpy 부분
  - ✅ 완료: 2D 배열 만들고 슬라이싱·shape 출력하는 노트북 셀
- [ ] [평일] D2: numpy broadcasting 규칙 직접 실험
  - 🎯 개념: broadcasting(shape 다른 배열 연산) — 딥러닝 텐서 연산의 핵심, shape mismatch 디버깅의 기초
  - ✅ 완료: (3,1)+(1,4) 같은 broadcasting 예제 1개 + 왜 되는지 한 줄 메모
- [ ] [평일] D3: 혼공머신 1~2장 읽기 (ML이 뭔지, 지도학습 개념) — 핵심 키워드만 메모
  - 🎯 개념: 지도학습(입력→정답 학습), 특성(feature)/타깃(target), 훈련/테스트 분리의 의미
  - 📖 자료: 『혼자 공부하는 머신러닝+딥러닝』 1~2장 (코랩)
  - ✅ 완료: 핵심 키워드 5개를 docs/log.md에 정리
- [ ] [평일] D4: pandas로 CSV 로드 → `train_test_split` 직접 해보기
  - 🎯 개념: 데이터를 train/test로 나누는 이유(일반화 측정), pandas DataFrame
  - ✅ 완료: CSV 로드 → split → 각 shape 출력
  - ⚠️ 막히면: 데이터 없으면 sklearn `load_iris()` 같은 내장 데이터셋 사용
- [ ] [평일] D5: (가벼운 날) split한 데이터 shape만 출력해 확인
  - 🎯 개념: 어제 한 split이 train/test 비율대로 나뉘었는지 눈으로 확인 — 복습/연속성
  - ✅ 완료: train/test shape 출력 후 커밋
- [ ] [주말] notebooks/01_data_basics.ipynb — 데이터 로드 → split → numpy 변환 한 흐름 정리
  - 🎯 개념: 한 주 배운 numpy/pandas/split을 하나의 재현 가능한 노트북으로 통합
  - ✅ 완료: 노트북이 위→아래 순서로 에러 없이 실행됨

## W3 — ML 기초 체화 (과적합·평가)
- [ ] [평일] D1: 혼공머신 3장 또는 분류 챕터 — 핵심 키워드 노트
  - 🎯 개념: 분류 vs 회귀, 모델이 "학습"한다는 게 코드 수준에서 무슨 뜻인지
  - 📖 자료: 혼공머신 해당 장
  - ✅ 완료: 키워드 메모 커밋
- [ ] [평일] D2: scikit-learn KNeighborsClassifier 또는 LogisticRegression 학습
  - 🎯 개념: `.fit()`/`.predict()` API — 모든 ML 라이브러리의 공통 패턴(PyTorch도 유사)
  - ✅ 완료: 분류기 학습 후 `.predict()`로 예측 1개 출력
- [ ] [평일] D3: 과적합/일반화 — train 정확도 vs test 정확도 직접 출력
  - 🎯 개념: 과적합(훈련엔 강하고 새 데이터엔 약함) — ML에서 가장 중요한 함정
  - ✅ 완료: train acc와 test acc를 나란히 출력해 차이 관찰
- [ ] [평일] D4: 평가지표 accuracy·confusion matrix 출력
  - 🎯 개념: accuracy의 한계, confusion matrix로 어디서 틀리는지 보기
  - ✅ 완료: confusion matrix 출력 + 한 줄 해석
- [ ] [평일] D5: 회고 — "ML = 데이터→학습→평가 루프" 한 문단 정리
  - 🎯 개념: 이번 주 전체를 한 문장으로 압축 — 다음 PyTorch 학습 루프의 멘탈 모델
  - ✅ 완료: docs/log.md에 한 문단 회고
- [ ] [주말] notebooks/02_ml_baseline.ipynb — 분류기 학습 + 평가지표 + 과적합 관찰 메모
  - 🎯 개념: scikit-learn 베이스라인 — 나중에 PyTorch 모델과 성능 비교할 기준선
  - ✅ 완료: 노트북에 학습→평가→과적합 관찰이 한 흐름으로

## W4 — PyTorch Tensor·autograd
- [ ] [평일] D1: Tensor 생성/연산, numpy ↔ tensor 변환
  - 🎯 개념: Tensor = numpy 배열 + GPU/autograd. `torch.from_numpy()`, `.numpy()`
  - 📖 자료: PyTorch 한국어 튜토리얼 60분 블리츠 "텐서"
  - ✅ 완료: numpy→tensor→numpy 왕복 변환 실행
- [ ] [평일] D2: `requires_grad=True` + `.backward()`로 gradient 확인
  - 🎯 개념: autograd(자동 미분) — 딥러닝 학습의 엔진. gradient가 뭔지
  - 📖 자료: 60분 블리츠 "autograd"
  - ✅ 완료: 간단한 식의 gradient를 `.grad`로 확인
- [ ] [평일] D3: 손실함수 직접 정의 → gradient 수동 확인
  - 🎯 개념: 손실(loss) = 예측과 정답의 차이. loss를 줄이는 게 학습
  - ✅ 완료: MSE 같은 손실 정의 후 backward로 grad 확인
- [ ] [평일] D4: 경사하강 1변수 직접 구현 (`w -= lr * w.grad`)
  - 🎯 개념: 경사하강(gradient descent) — 파라미터를 grad 반대로 조금씩 갱신. learning rate
  - ✅ 완료: 반복문으로 loss가 줄어드는 것 출력
  - ⚠️ 막히면: loss가 발산하면 lr를 1/10로
- [ ] [평일] D5: 60분 블리츠 "autograd" 페이지 교차 확인
  - 🎯 개념: 직접 구현한 것과 공식 설명을 대조해 개념 굳히기
  - ✅ 완료: 이해 안 됐던 부분 1개를 log.md에 질문/답으로 정리
- [ ] [주말] training/03_autograd_gd.py — 경사하강 직접 구현 스크립트 (W5 nn.Module 버전과 비교 기준선)
  - 🎯 개념: 손으로 만든 학습 루프 — W5에서 nn.Module로 같은 걸 만들어 "프레임워크가 뭘 자동화하는지" 체감
  - ✅ 완료: `python training/03_autograd_gd.py` 실행 시 loss 감소 출력

<!-- 다음 구간(W5~W12)은 W4 종료 후 /study-coach plan에서 일별 항목 + 학습 가이드로 상세화한다. 현재는 주차 헤더만. -->
## W5 — nn.Module + 학습 루프 (상세화 대기)
## W6 — DataLoader·검증 루프·정확도 (상세화 대기)
## W7 — 모델 저장/로딩 + 추론 스크립트 (상세화 대기)
## W8 — FastAPI 추론 서버 골격 (상세화 대기)
## W9 — 입력검증·startup 로딩·헬스체크 (상세화 대기)
## W10 — Dockerfile (multi-stage, CPU) (상세화 대기)
## W11 — 이미지 슬림화 + docker-compose (상세화 대기)
## W12 — 통합·문서화·회고 (상세화 대기)

---
## 검토 로그 (review가 append)
<!-- /study-coach review가 날짜별 채점·피드백을 여기 누적. 면접 회고의 원천. -->
