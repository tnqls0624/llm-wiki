#!/usr/bin/env bash
# run-tests.sh — 메커니즘 회귀 테스트 러너. 표준 라이브러리(unittest)만 사용, 의존성 0(+git).
# 격리 임시 vault에서 새 KB 체계의 훅/스크립트(session-context · auto-commit · secret-scan ·
# scrub-secrets · kb-lint · kb-lint-check)를 실제 호출해 계약을 검증한다.
# 실행: bash .claude/tests/run-tests.sh   (vault 어디서든)
# 종료코드: 0=전부 통과, 비0=실패(수동·CI 공용). 왜 필요한지는 test_mechanisms.py 참조.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/test_mechanisms.py"
