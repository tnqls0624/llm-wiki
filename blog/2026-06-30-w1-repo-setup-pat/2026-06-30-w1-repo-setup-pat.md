# 레포 하나 세팅하며 만난 인증정보, git, 가상환경, CUDA 이야기

## 준비할 이미지
1. `1. github-pat-settings.png` — GitHub PAT 발급 화면 (web: GitHub 공식 문서 그림 — 수집됨)
2. `2. git-commit-tree-blob.png` — git commit→tree→blob 오브젝트 모델 도해 (web: Pro Git 공식 그림 — 수집됨)

AI 인프라를 공부해보기로 하고 개인 학습용 레포(ai-infra-lab)를 새로 만들었습니다. training, serving, gateway, docker, kubernetes 같은 디렉토리 골격을 잡고 첫 push까지 끝냈을 때는 "이 정도면 세팅 끝"이라고 생각했는데, 그 뒤로 며칠 사이에 예상 못한 문제를 네 번이나 만났습니다. GitHub 인증 토큰이 원격 저장소 URL에 그대로 노출된 사고, git이 빈 디렉토리를 다루는 방식, 파이썬 가상환경을 커밋에서 빼야 하는 이유, 그리고 GPU 없는 맥에서 PyTorch의 CUDA 체크가 False로 나오는 이유까지. 이번 글에서는 레포 하나를 세팅하면서 실제로 겪은 문제들과 그 원인을 정리합니다.

## GitHub 인증 토큰(PAT)이 원격 URL에 그대로 노출된 사고

PAT(Personal Access Token)는 GitHub이 발급하는 문자열 형태의 인증정보로, HTTPS로 git 작업(push, pull, clone)을 할 때 비밀번호 대신 쓰는 토큰입니다.

- OAuth 앱 권한처럼 scope(repo, workflow 등)를 지정해서 발급한다.
- 유출되면 그 scope 안에서 공격자가 내 계정처럼 행동할 수 있다 — 비밀번호와 다를 게 없는 민감정보다.

> 🖼️ **[사진 1]** GitHub 설정에서 PAT를 발급하는 화면 — 토큰이 "비밀번호 대신 쓰는 인증정보"라는 걸 보여주는 공식 문서 그림
> → 업로드: `1. github-pat-settings.png`

레포를 만들고 push할 때 인증을 편하게 하려고 토큰을 origin URL에 바로 넣었습니다. `git remote -v`로 확인해보니 이런 모양이었습니다.

```
origin  https://<token>@github.com/<user>/ai-infra-lab.git (fetch)
```

URL 안에 인증정보가 평문으로 그대로 들어가 있는 상태입니다. 이게 왜 위험한지 정리하면:

- 셸 히스토리 파일(`~/.zsh_history` 등)에 명령어가 그대로 남는다.
- `git remote -v` 한 번만 쳐도 누구나 볼 수 있고, 터미널 스크롤백이나 화면 공유에도 그대로 노출된다.
- 로그나 CI 출력에 remote URL이 찍히면 거기에도 토큰이 같이 찍힌다.

바로 URL에서 토큰을 뺐습니다.

```
git remote set-url origin https://github.com/<user>/ai-infra-lab.git
```

그리고 인증 방식 자체를 바꿨습니다. `gh` CLI로 로그인하면 토큰이 macOS Keychain 같은 OS 자격증명 저장소에 암호화된 채로 저장되고, git이 인증이 필요할 때마다 credential helper를 통해 꺼내 씁니다. URL에 넣는 방식과의 차이는 명확합니다 — helper를 쓰면 토큰이 히스토리나 로그에 평문으로 찍힐 일이 없습니다. 노출됐던 토큰은 GitHub에서 폐기하고 새로 발급받을 계획입니다.

## git은 빈 디렉토리를 추적하지 않는다

레포를 만들 때 `training/`, `serving/`, `gateway/`, `docker/`, `kubernetes/`, `mlflow/` 등 12개 디렉토리 골격을 먼저 잡았습니다. 커밋 메시지에는 "디렉토리 골격 커밋"이라고 썼는데, 나중에 diff를 다시 보니 실제로 바뀐 파일은 `.gitignore` 한 줄과 `README.md` 한 줄뿐이었습니다.

git은 파일(정확히는 blob) 단위로 추적하는 시스템이라, 내용이 하나도 없는 디렉토리는 트리에 기록조차 되지 않습니다. 폴더를 로컬에 만들어놔도 안이 비어 있으면 git 입장에서는 존재하지 않는 것과 같습니다. 안에 파일이 하나라도 생기는 순간부터 그 경로가 커밋에 포함됩니다. 그래서 자리만 미리 잡아두고 싶은 빈 디렉토리에는 `.gitkeep`처럼 내용 없는 파일을 하나 넣어 강제로 추적시키는 방법을 쓰기도 합니다.

> 🖼️ **[사진 2]** git이 커밋을 저장하는 구조(commit → tree → blob) — 파일(blob)이 없으면 트리에 기록될 것도 없다는 걸 보여주는 도해
> → 업로드: `2. git-commit-tree-blob.png`

## 가상환경(venv)과 requirements.txt로 재현성 확보하기

다음은 PyTorch 설치였습니다. `venv`는 파이썬 표준 라이브러리에 포함된 도구로, 프로젝트마다 독립된 패키지 설치 공간을 만들어줍니다. 전역 파이썬에 패키지를 그냥 설치하면 프로젝트마다 필요한 버전이 달라질 때 서로 충돌하기 쉬운데, venv로 격리하면 이 문제가 없습니다.

```
python -m venv .venv
pip install torch torchvision
```

torch 2.12.1, torchvision 0.27.1을 설치하고 numpy, scikit-learn, jupyter까지 넣은 뒤 버전을 고정했습니다.

```
pip freeze > requirements.txt
```

113줄짜리 `requirements.txt`가 나왔습니다. 그런데 커밋하기 전에 `git status`를 보니 `.venv/`가 통째로 untracked 상태로 잡혀 있었습니다. 그대로 `git add .`를 했다면 가상환경 전체가 레포에 올라갈 뻔한 상황이었습니다. 이게 왜 문제인지 정리하면:

- `.venv` 안에는 OS·아키텍처에 종속된 컴파일된 바이너리가 들어 있어서 다른 머신에서 그대로 재사용할 수 없다.
- torch 같은 패키지가 포함되면 용량이 커서 레포 자체가 무거워진다.
- `requirements.txt` 하나만 있으면 어디서든 `pip install -r requirements.txt`로 같은 패키지 목록을 재현할 수 있으니, `.venv` 자체를 커밋할 이유가 없다.

`.gitignore`에 세 줄을 추가해서 막았습니다.

```
.venv/
__pycache__/
*.pyc
```

## torch.cuda.is_available()이 False인 게 정상인 이유

`import torch`는 에러 없이 됐는데, `torch.cuda.is_available()`을 찍어보니 False가 나왔습니다. 처음엔 설치가 잘못됐나 싶었는데 생각해보면 당연한 결과였습니다.

- CUDA는 NVIDIA GPU에서 연산을 돌리기 위한 NVIDIA의 병렬 컴퓨팅 플랫폼이자 드라이버 스택이다.
- PyTorch는 설치 시점에 CPU 전용 빌드와 CUDA 지원 빌드를 따로 배포한다. CUDA 빌드는 NVIDIA GPU와 드라이버가 있는 머신에서만 의미가 있다.
- 지금 쓰는 맥에는 NVIDIA GPU가 없어서 CPU 빌드를 설치했고, `is_available()`이 False로 나오는 게 정확한 상태다. 오히려 이 환경에서 True가 나왔다면 그게 이상한 신호였을 것.
- 나중에 GPU가 붙은 서버나 클라우드 인스턴스로 옮겨서 CUDA 빌드를 설치하면 그때는 True로 바뀔 예정이다.

## 마무리

레포 하나를 세팅하는 짧은 기간에 인증정보 관리, git의 추적 단위, 의존성 재현성, 하드웨어 빌드 차이까지 짚게 됐습니다. 코드를 한 줄도 쓰기 전에 정리해야 할 게 이만큼 있다는 걸 이번에 알았습니다. 다음 글에서는 실제로 학습 코드를 작성하면서 만난 문제들을 정리해보겠습니다.

<!-- BLOG-IMAGES (blog-collect.py가 이 아래를 떼어냄) -->
<!-- IMG: 1 | github-pat-settings | web | GitHub 설정의 PAT 발급 화면 | https://docs.github.com/assets/images/help/settings/personal-access-tokens.png | GitHub Docs, CC BY 4.0 -->
<!-- IMG: 2 | git-commit-tree-blob | web | git commit→tree→blob 오브젝트 모델 도해 | https://git-scm.com/book/en/v2/images/commit-and-tree.png | Pro Git (git-scm.com), CC BY-NC-SA 3.0 -->
