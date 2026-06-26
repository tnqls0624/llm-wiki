<!-- study-state v1 | block=1 | last_brief_date=2026-06-26 | repo_path=~/ai-infra-lab -->
<!--
  AI Infra 학습 진도 정본. git 추적됨 → 두 Mac(회사/집)이 push/pull로 공유.
  study-brief.py(무인 cron)가 이 파일을 읽어 요일별 다음 미완료 항목을 study-today.md로 뽑고,
  /study-coach review(대화형)가 산출물 검토 후 `- [ ]`→`- [x]` 체크하고 last_brief_date/메모를 갱신한다.
  메타는 위 한 줄 주석에서 파싱: last_brief_date(멱등 키), repo_path(검토 대상 ai-infra-lab 경로).
  repo_path가 머신마다 다르면 .claude/runtime/study-local.conf(gitignore)에 `repo_path=...` 한 줄로 override.
  항목 태그: [평일] = 20~40분, [주말] = 2~3시간 통합 실습. 체크는 review에서만.
-->

# AI Infra 학습 진도 — 블록1 (Python/ML → PyTorch → FastAPI → Docker)

목표: **"PyTorch로 학습한 모델 → 저장 → FastAPI 추론 API → Docker 이미지"** 파이프라인을 자기 손으로 완성.
프로젝트: `ai-infra-lab` 단일 repo 단계 확장. K8s/GPU/분산학습/vLLM은 블록2(13~24주)로 미룸.

## W1 — 환경 + repo 척추
- [ ] [평일] D1: ai-infra-lab repo 생성 + 디렉토리 골격(training/serving/docker/notebooks/models/docs) 커밋, models/ gitignore
- [ ] [평일] D2: `python -m venv .venv` + `pip install torch torchvision numpy scikit-learn jupyter` + requirements.txt 커밋
- [ ] [평일] D3: `python -c "import torch; print(torch.__version__, torch.cuda.is_available())"` 성공, 결과 docs/log.md 기록
- [ ] [평일] D4: 점프투파이썬에서 list/dict comprehension·f-string·타입힌트만 복습 + 짧은 예제 1개
- [ ] [평일] D5: 데코레이터 + `with` 컨텍스트매니저 확인 (FastAPI/PyTorch에서 쓰임)
- [ ] [주말] repo 골격 + venv + requirements.txt + README(목표·디렉토리 설명) 커밋, import 성공 기록 docs/

## W2 — numpy + 데이터 감각
- [ ] [평일] D1: numpy 배열 생성·인덱싱·`shape` (Tensor의 전신)
- [ ] [평일] D2: numpy broadcasting 규칙 직접 실험
- [ ] [평일] D3: 혼공머신 1~2장 읽기 (ML이 뭔지, 지도학습 개념) — 핵심 키워드만 메모
- [ ] [평일] D4: pandas로 CSV 로드 → `train_test_split` 직접 해보기
- [ ] [평일] D5: (가벼운 날) split한 데이터 shape만 출력해 확인
- [ ] [주말] notebooks/01_data_basics.ipynb — 데이터 로드 → split → numpy 변환 한 흐름 정리

## W3 — ML 기초 체화 (과적합·평가)
- [ ] [평일] D1: 혼공머신 3장 또는 분류 챕터 — 핵심 키워드 노트
- [ ] [평일] D2: scikit-learn KNeighborsClassifier 또는 LogisticRegression 학습
- [ ] [평일] D3: 과적합/일반화 — train 정확도 vs test 정확도 차이 직접 출력
- [ ] [평일] D4: 평가지표 accuracy·confusion matrix 출력
- [ ] [평일] D5: 회고 — "ML = 데이터→학습→평가 루프" 한 문단 정리
- [ ] [주말] notebooks/02_ml_baseline.ipynb — 분류기 학습 + 평가지표 + 과적합 관찰 메모

## W4 — PyTorch Tensor·autograd
- [ ] [평일] D1: Tensor 생성/연산, numpy ↔ tensor 변환
- [ ] [평일] D2: `requires_grad=True` + `.backward()`로 gradient 확인
- [ ] [평일] D3: 손실함수 직접 정의 → gradient 수동 확인
- [ ] [평일] D4: 경사하강 1변수 직접 구현 (`w -= lr * w.grad`)
- [ ] [평일] D5: 60분 블리츠 "autograd" 페이지 교차 확인
- [ ] [주말] training/03_autograd_gd.py — 경사하강 직접 구현 스크립트 (W5 nn.Module 버전과 비교 기준선)

<!-- 다음 구간(W5~W12)은 W4 종료 후 /study-coach review에서 일별로 상세화한다. 현재는 주차 헤더만. -->
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
