# 이미지 출처 · 라이선스

> 웹 수집 이미지는 저작권이 있을 수 있음 — 재게시 전 아래 출처·라이선스를 확인하세요.

- **[사진 1]** `1. multi-stage-build.png` · web · 미수집 (blog-collect.py 실행 대기)
  - 후보: Docker 공식 문서 multi-stage builds 개념도 (docker/docs)
- **[사진 2]** `2. ctypes-modulenotfounderror.png` · shot · 사용자 직접 촬영 대기
  - 재현: `python3-minimal` 상태의 이전 이미지가 없으므로, Dockerfile에서 `python3`→`python3-minimal`로 잠시 되돌려 재빌드하면 동일 에러 재현 가능
- **[사진 3]** `3. docker-diff-cow.png` · shot · 사용자 직접 촬영 대기
  - 재현: `--rm` 없이 실행 후 `docker diff <컨테이너>` — 마운트 유무 2회 대조

## 본문 사실 출처 (provenance)
- `ai-infra-lab/docs/log.md` — `## 2026-07-12 (일)` 섹션 (커밋 `b7cc92a`·`ca7197b`·`9ccca23`·`9c545da`)
- `ai-infra-lab/docker/Dockerfile` — 커밋 `2d82b38` (본문 코드는 축약본)
- `obsidian_sync/.claude/runtime/study-state.md` — `### 2026-07-12` 검토 로그 3건
- 크기 수치(3.22→2.90GB, apt 345→32.3MB, torch venv 779→772MB)는 log.md의 본인 실측값
