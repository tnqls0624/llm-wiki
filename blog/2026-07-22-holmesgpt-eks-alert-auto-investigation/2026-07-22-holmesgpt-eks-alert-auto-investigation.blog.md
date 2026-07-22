# EKS 알람을 AI가 대신 조사하게 만들기 — HolmesGPT + Robusta 자동조사 파이프라인 구축기

## 준비할 이미지
1. `1. holmesgpt-pipeline-architecture.png` — alert 발생부터 Slack 한국어 보고까지 전체 파이프라인 아키텍처 다이어그램 (shot: 직접 캡처)
2. `2. slack-korean-investigation.png` — 실제 Slack에 게시된 한국어 AI 조사 보고 (shot: 직접 캡처, 민감정보 마스킹)

운영 중인 EKS 클러스터에서 Prometheus alert가 울릴 때마다 하는 일은 늘 비슷했다. 파드 상태 확인하고, 로그 뒤지고, 이벤트 보고, 메트릭 그래프 열고. alert 하나에 10~20분씩 쓰는 이 반복 작업을 AI에게 맡길 수 없을까 싶어서 HolmesGPT를 도입했다. 목표는 하나였다 — **alert가 울리면 사람이 보기 전에 AI가 먼저 클러스터를 조사하고, 한국어 보고서를 Slack에 올려놓는 것.** 결과적으로 파이프라인은 완성됐지만, 그 과정에서 업스트림 버그를 연달아 밟으며 수습하는 데 시간을 더 썼다. 이 글은 그 아키텍처와 삽질의 기록이다.

## HolmesGPT란?

- [HolmesGPT](https://github.com/robusta-dev/holmesgpt)는 Robusta에서 만든 오픈소스 **AI SRE 조사 엔진**이다. LLM에게 kubectl, Prometheus 질의 같은 도구를 쥐여주고, alert를 던지면 스스로 도구를 골라 클러스터를 조사한 뒤 근본 원인을 보고한다.
- 핵심은 **ReAct 패턴**이다. 정해진 스크립트를 따르는 게 아니라, LLM이 조회 결과를 보고 "다음엔 뭘 확인할지"를 스스로 결정한다. 파드 로그를 봤더니 DNS 에러가 있으면 서비스 목록을 조회하는 식이다.
- 쉽게 말해 신입 SRE에게 읽기 전용 kubectl 권한을 주고 "이 알람 원인 좀 조사해서 보고해줘"라고 시키는 것과 같다. 다만 이 신입은 30초 만에 보고서를 들고 온다.

혼자서는 alert를 받을 수 없으니 오케스트레이션 레이어가 필요한데, 같은 회사의 **Robusta OSS**를 썼다. Alertmanager 웹훅을 받아 playbook(Python 액션)을 실행하고 결과를 Slack에 보내주는 Kubernetes 이벤트 자동화 프레임워크다. SaaS 플랫폼 없이 오픈소스만으로 자체 호스팅했다.

## 전체 아키텍처

구성은 전부 GitOps(ArgoCD)로 배포했고, 흐름은 이렇다.

```
Prometheus alert 발생
  → Alertmanager (severity 필터링 후 웹훅 라우팅)
  → robusta-runner (커스텀 playbook 실행)
  → HolmesGPT /api/chat (LLM이 kubectl·Prometheus 도구로 실제 조사)
  → 한국어 4섹션 보고서 → Slack 게시
```

> 🖼️ **[사진 1]** alert 발생부터 Slack 한국어 보고까지 전체 파이프라인 아키텍처 다이어그램
> → 업로드: `1. holmesgpt-pipeline-architecture.png`

설계할 때 정한 원칙 두 가지가 있다.

- **AI는 read-only.** Holmes와 runner 모두 RBAC 계층에서 조회 권한만 갖는다. Robusta 차트가 기본으로 주는 ClusterRole에는 파드 삭제 같은 쓰기 권한이 포함돼 있어서, `overrideClusterRoles`로 get/list/watch만 남기고 전부 걷어냈다. Secret 조회도 의도적으로 뺐다.
- **영구 변경은 사람이 GitOps로만.** AI가 진단하고 조치를 "권장"까지는 하되, 실제 수정은 사람이 검토해서 Git에 커밋한다. 조사와 실행의 권한을 분리하는 게 신뢰의 핵심이라고 봤다.

LLM은 Gemini 2.5를 썼고, `modelList`에 pro와 flash 두 개를 등록해서 용도별로 라우팅했다(뒤에서 설명).

여기까지가 계획이었다. 배포하고 나서부터가 진짜 시작이었다.

## 사건 ① 내장 액션이 alert에서 그냥 죽는다

Robusta에는 `ask_holmes`라는 내장 액션이 있다. 문서만 보면 YAML 설정 몇 줄로 "alert 발생 → Holmes 조사"가 될 것 같다.

```yaml
customPlaybooks:
  - triggers:
      - on_prometheus_alert: {}
    actions:
      - ask_holmes: {}
```

그런데 alert가 올 때마다 runner가 `AttributeError`를 뱉었다. 소스를 열어보니 원인이 명확했다 — **내장 `ask_holmes`는 SaaS 플랫폼 UI의 콜백용으로 설계된 액션**이라, alert 이벤트에서 호출하면 조사 대상 리소스 정보(`context`)가 `None`인 채로 들어와 그대로 죽는다. YAML 설정만으로는 alert 자동조사가 불가능한 구조였다.

해결은 **커스텀 playbook**이었다. alert 객체에서 리소스·라벨·설명을 직접 추출해 조사 프롬프트를 구성하는 Python 액션을 하나 만들고, ConfigMap으로 마운트해서 `playbookRepos`로 로드했다. 조사 지침(한국어로 답할 것, 추측 금지, 4개 섹션 구조)도 이 프롬프트에 담았다.

```
## 🔎 장애 요약 — 무슨 일이 발생했는지 1~2문장
## 🧭 근본 원인 — 증거 기반. 확정 불가 시 '확정 불가' 명시
## 📋 판단 근거 — 실제 조회한 로그/이벤트/메트릭 인용
## 🛠 권장 조치 — 즉시 조치와 영구 조치(GitOps 수정) 구분
```

참고로 Holmes에 언어 설정 같은 건 따로 없다. 프롬프트에 "반드시 한국어로 답하라"를 넣는 게 정석이다.

## 사건 ② 패키지는 설치됐는데 로드가 안 된다

커스텀 playbook을 ConfigMap으로 마운트했더니 이번엔 pip 설치까지는 성공하는데 액션 등록이 안 됐다. 파고들어보니 Robusta의 config loader가 **패키지 이름을 `pyproject.toml`의 `[tool.poetry] name` 필드에서만 읽는다.** 요즘 표준인 PEP 621 `[project]` 섹션은 아예 보지 않는다.

빌드는 setuptools로 하면서 Robusta 파서용으로 poetry 섹션을 병기하는, 이상하지만 동작하는 pyproject.toml이 됐다.

```toml
[project]
name = "my_playbooks"        # 실제 빌드용 (setuptools)

[tool.poetry]
name = "my_playbooks"        # robusta config_loader 전용 메타데이터
```

하나 더 — ConfigMap을 subPath로 마운트하면 **ConfigMap을 갱신해도 기존 파드에 반영되지 않는다.** playbook을 수정할 때마다 runner를 rollout restart 해야 한다. 이건 Kubernetes subPath의 알려진 동작인데, 잊고 있으면 "분명히 고쳤는데 왜 그대로지"로 30분을 날리게 된다.

## 사건 ③ 404 — 차트와 이미지가 서로 다른 API를 말한다

이제 조사가 실행은 되는데, Holmes 호출이 전부 404로 떨어졌다. 원인은 허탈했다. **Robusta 차트에 묶여 배포되는 runner는 Holmes의 `/api/investigate` 엔드포인트를 호출하는데, 같은 차트가 배포하는 Holmes 이미지(0.36.0)에서는 그 엔드포인트가 제거되고 `/api/chat`만 남아 있었다.** 같은 Helm 차트 안에서 두 컴포넌트의 API 계약이 어긋나 있는 것이다.

커스텀 playbook에서 `/api/chat`을 직접 호출하는 걸로 우회했다. 다만 응답 타입이 달라서 한 번 더 손이 갔다 — Slack sender가 렌더링할 수 있는 결과 블록 타입이 정해져 있어서, chat 응답을 그 타입으로 변환해 넣어야 Slack까지 도달한다.

이 사건의 교훈은 명확하다. **오픈소스 조합 도입에서 "차트 버전과 이미지 버전이 서로 검증된 조합인지"는 문서가 아니라 소스로 확인해야 한다.**

## 사건 ④ 조사 보고서가 Slack에서 증발한다

파이프라인이 돌기 시작하자 이번엔 Slack 쪽에서 문제가 연쇄로 터졌다. 이게 이번 구축에서 가장 실무적인 교훈이었는데, **조사가 성공해도 전달이 실패하면 아무 일도 없던 것과 같다.**

- **3,000자 한도.** Slack section block의 텍스트 한도는 3,000자다. 문제는 초과하면 잘리는 게 아니라 `invalid_attachments` 에러로 **메시지 전체가 거부**된다는 것. 즉 AI가 열심히 쓴 긴 보고서일수록 통째로 증발한다. 본문을 2,800자에서 자르고 전문은 스레드에 파일로 첨부하는 방어 로직을 넣었다.
- **도구 호출 증거 첨부 실패.** Holmes는 조사에 사용한 도구 호출 결과(어떤 kubectl 명령, 어떤 PromQL을 실행했는지)를 함께 반환하고, 이걸 스레드에 파일로 올려주면 "AI가 뭘 보고 이런 결론을 냈는지" 검증할 수 있다. 그런데 chat API의 도구 결과는 dict로 오는 경우가 있어 파일 업로드 API가 거부한다 — 문자열로 직렬화해서 해결.
- **봇 스코프.** 파일 업로드에는 `files:write` 스코프가 따로 필요하다. 본문 게시(`chat:write`)만 있으면 보고서는 올라가는데 첨부만 조용히 실패한다.
- **첨부 개수 한도.** 스코프를 넣고 나니 이번엔 도구 호출이 21건인 조사에서 첨부 파일 **링크 목록 메시지**가 다시 3,000자를 넘겨 터졌다. 첨부는 10개까지만, 설명은 80자로 절단.

결과물은 이렇게 생겼다. alert 알림 아래에 한국어 조사 보고가 붙고, 스레드에 증거 파일이 달린다.

> 🖼️ **[사진 2]** 실제 Slack에 게시된 한국어 AI 조사 보고 (4섹션 구조 + 스레드 증거 첨부)
> → 업로드: `2. slack-korean-investigation.png`

## 운영 튜닝 — 파이프라인이 도는 것과 쓸 만한 것은 다르다

E2E가 돌고 나서 하루 운영해보니, 이번엔 비용과 소음이 문제였다. 다른 팀들의 공개 사례([에스티씨랩의 HolmesGPT 도입기](https://www.stclab.com/blog/holmesgpt-cncf-tools-kubernetes-alerts-auto-dignosing), [AB180의 alert 표준화](https://engineering.ab180.co/stories/standardizing-alert-system-with-iac))를 참고해서 네 가지를 손봤다.

**① alert 필터링.** 처음엔 모든 alert를 조사시켰는데, info급 alert까지 LLM 조사가 도는 건 낭비다. Alertmanager 라우팅에서 `severity =~ "warning|critical"`만 통과시키고, `repeat_interval`을 12시간으로 늘려 지속 발화 alert의 재조사를 하루 2회로 제한했다. resolved 통지도 껐다 — 조사가 붙지 않는 순수 소음이었다.

**② 워크로드 단위 중복 억제.** CronJob이 3번 실패하면 Job마다 alert가 3개 뜨고, 조사도 3번 돈다. 내용은 사실상 같은데. Job 이름의 타임스탬프 접미사와 파드 해시를 정규식으로 벗겨 **워크로드 단위 fingerprint**를 만들고, 같은 fingerprint는 30분간 재조사하지 않게 했다. 에스티씨랩 사례에서 하루 40건 raw alert가 12건 조사로 줄었다는 그 패턴이다.

**③ 모델 라우팅 + 승격 재시도.** critical은 Gemini 2.5 Pro(정확도), warning 이하는 Flash(비용)로 라우팅했다. 그런데 Flash가 가끔 빈 응답을 반환하고, 그러면 Holmes 서버가 응답 검증에서 500을 뱉는 업스트림 버그가 있다. 실패 시 Pro로 한 번 승격 재시도하는 로직을 넣었는데, 배포 당일 실전에서 바로 작동했다 — Flash 실패 → Pro 재시도 → 보고 성공.

**④ 런북.** 이번 튜닝에서 체감 효과가 가장 컸다. alert 이름별로 "무엇을 조사하고 무엇은 하지 말 것"을 짧게 정리해 프롬프트에 주입한다.

```
"KubeCPUOvercommit": (
    "노드별 CPU requests 합계와 allocatable 비교만 수행한다. "
    "개별 파드 로그 조사는 불필요. requests는 "
    "kube_pod_container_resource_requests{resource=\"cpu\"}를 쓴다"
    "(구식 _cpu_cores 접미사 메트릭은 존재하지 않음)."
),
```

마지막 줄이 실전에서 나온 것이다. Slack 스레드의 증거 파일을 열어보니 LLM이 kube-state-metrics v1 시절 메트릭 이름(`..._cpu_cores`)을 추측해 질의했다가 빈 결과를 받고 도구 호출을 낭비하고 있었다. 런북에 정확한 v2 메트릭 이름을 박아주면 첫 쿼리부터 맞는다. **증거 첨부를 보고 → 런북을 보강하고 → 도구 호출이 줄어드는** 이 루프가 운영의 핵심이라는 에스티씨랩의 "모델보다 런북이 먼저" 원칙에 크게 공감하게 됐다.

## 첫 실전 성과 — 한 번도 성공한 적 없던 백업

파이프라인이 처음으로 밥값을 한 사례가 있다. PostgreSQL 백업 CronJob 실패 alert가 계속 울려서 AI 조사를 붙였더니, 판단 근거에 "DNS 미해석"이 잡혔다. 따라가보니 백업 잡이 바라보는 DB 호스트가 존재하지 않는 네임스페이스를 가리키고 있었고(네임스페이스 통합 때 미반영), 고치고 나니 이번엔 접속 유저도 틀려 있었다. 둘 다 고치고 나서야 알게 된 사실 — **이 백업은 배포된 이래 한 번도 성공한 적이 없었다.** alert는 매일 울렸지만 아무도 파고들지 않았던 것이다.

AI가 원인을 "확정"해준 건 아니다. 하지만 조사 보고서가 방향을 잡아줬고, 사람은 검증과 수정에만 집중하면 됐다. 조사는 AI, 판단과 변경은 사람 — 처음 정한 원칙이 실제로 작동하는 걸 확인한 순간이었다.

## 정리

이번 구축에서 확인한 것 네 가지.

1. **오픈소스 조합의 API 계약은 소스로 검증해야 한다.** 같은 Helm 차트 안에서도 컴포넌트끼리 다른 API를 말할 수 있다(`/api/investigate` 404 사건).
2. **전달 계층이 신뢰성의 절반이다.** 조사가 아무리 잘 돼도 Slack 3,000자 한도, 봇 스코프, 타입 불일치 중 하나에 걸리면 보고서는 증발한다. "성공 로그"가 아니라 "사용자에게 도달했는지"를 검증해야 한다.
3. **모델보다 런북, 필터링이 먼저다.** LLM 교체보다 조사 범위를 좁혀주는 런북 한 줄, severity 필터 한 줄이 품질과 비용에 더 크게 작용했다.
4. **read-only 원칙은 도입 장벽을 낮춘다.** AI에게 조회 권한만 주고 변경은 GitOps로 분리하니, "AI가 클러스터를 건드리면 어쩌지"라는 걱정 없이 도입을 밀 수 있었다.

다음 단계는 조사 결과를 바탕으로 AI가 수정 MR 초안까지 만들어주는 반자동 조치 루프다. 물론 머지 버튼은 계속 사람 몫이다.

**참고 자료**
- [HolmesGPT (GitHub)](https://github.com/robusta-dev/holmesgpt) · [Robusta OSS](https://github.com/robusta-dev/robusta)
- [에스티씨랩 — HolmesGPT와 CNCF 도구로 Kubernetes 알림 자동 진단](https://www.stclab.com/blog/holmesgpt-cncf-tools-kubernetes-alerts-auto-dignosing)
- [AB180 — IaC로 alert 시스템 표준화하기](https://engineering.ab180.co/stories/standardizing-alert-system-with-iac)
