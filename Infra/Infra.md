---
title: Infra
updated: 2026-06-10
sources: []
---

# 인프라 엔지니어 CS·리눅스·커널 학습 허브

인프라 엔지니어가 알아야 할 CS 기초·리눅스 커맨드·커널 지식의 한국어 학습 KB. `Claude/`·`AI-Infra/`와 동일 패턴(노트 + MOC + lint)을 따른다. [[AI-Infra]](GPU 서빙·K8s)의 **토대 레이어** — 컨테이너도 GPU 서버도 결국 리눅스 위에서 돈다.

## 먼저 읽을 것
- **[[00 인프라 학습 로드맵]]** — 읽기 순서 · 학습 방법론(읽기→관찰→장애 연결→면접 점검) · 8주 플랜 · 면접 질문 매핑 · 셀프 체크리스트.

## 개념 체인 (순서대로)
- **[[01 프로세스와 스레드]]** — task_struct · fork CoW · 좀비/D state · 스케줄링(CFS→EEVDF) · 시그널과 graceful shutdown.
- **[[02 메모리 관리]]** — 가상 메모리 · 페이지 캐시 · RSS/PSS · swap · OOM killer · hugepages · NUMA.
- **[[03 파일시스템과 스토리지]]** — VFS 3계층 · 링크 · ext4/XFS · I/O 경로와 스케줄러 · LVM · RAID · 디스크 풀 대응.
- **[[04 리눅스 네트워킹]]** — 패킷 수신 경로 · TCP 상태(TIME_WAIT/CLOSE_WAIT) · backlog · DNS · conntrack · ss/tcpdump 디버깅.
- **[[05 커널과 시스템 콜]]** — syscall과 vDSO · strace · epoll · 인터럽트 · sysctl · /proc · rlimits · 부팅 · eBPF.
- **[[06 컨테이너 내부 구조]]** — namespaces · cgroups · overlayfs · runc — CPU throttling · OOMKilled · PID 1 · GPU 주입까지.

## 사전 (수시 참조)
- **[[07 실무 리눅스 커맨드]]** — find·grep·awk·ss·lsof 등 현장 필수 커맨드를 복붙 예시와 안전 수칙으로 정리한 실전 사전.
- **[[08 성능 분석과 트러블슈팅]]** — USE 방법론 · 60초 체크리스트 · perf · eBPF 도구 · 실전 장애 플레이북 5종.

## 자료
- **[[99 인프라 학습 리소스]]** — 단계별 엄선 자원(OSTEP·TLPI·Systems Performance·jvns·LWN) · VM 장애 주입 훈련 · 자격증 전략.

## 학습 루프 (이 KB를 쓰는 법)
```
읽기   01→06 개념 체인을 순서대로, 07·08은 사전처럼
관찰   읽은 개념을 터미널에서 직접 재현 (/proc, ss, vmstat …)
질의   /kb-query·kb-guide → 박제한 개념을 격리 컨텍스트로 복습
박제   /kb-ingest → 가치 있는 외부 자료를 이 디렉토리에 노트로
```

## 핵심 명제
인프라 역량의 본질은 커맨드 암기가 아니라 **"커널이 왜 그렇게 동작하는지"를 알고 증상에서 원인으로 내려가는 능력**이다. 개념(01~06) 없이 도구(07~08)만 알면 스트리트라이트 안티패턴에 빠진다. 이 KB를 마치면 [[AI-Infra]]의 GPU·K8s 레이어가 "리눅스의 응용"으로 읽힌다.
