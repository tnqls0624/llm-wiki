# Dockerfile 빌드 에러 4개를 넘고 나서, 레이어 캐시를 직접 돌려봤다

## 준비할 이미지
1. `1. docker-build-cache-invalidation.png` — 캐시가 바뀐 레이어부터 아래로 전부 무효화되는 구조도 (web: Docker 공식 문서 빌드 캐시 그림)

지난 글에서 이미지·컨테이너·볼륨을 자료 없이 기억으로만 정리해봤고, 그러다 스스로도 확신이 안 서는 지점 세 개를 남겼다. 그중 두 번째가 레이어 캐시였다. "변경된 부분이 기존 레이어에 쌓인다"고 적어놓긴 했는데, 이게 레이어 하나가 계속 수정되는 건지, 아니면 그때그때 새 레이어가 생기는 건지 말로는 설명이 안 됐다. 이번 글은 그 확신 없는 지점을 실제로 Dockerfile을 쓰고 `docker build`를 여러 번 돌려가며 확인한 기록이다. 나머지 두 개 — 컨테이너 실행이 정말 이미지를 "복사"하는 것인지, 볼륨이라고 알고 있던 것이 정확히 무엇을 가리키는지 — 는 아직 손을 못 댔고, 이 글 끝에 다음 확인 목록으로 남겨둔다.

목표는 단순했다. 앞서 만든 MNIST 학습 스크립트(`train_mnist.py`)를 CUDA 베이스 이미지에 태워서 `docker build`와 `docker run`이 끝까지 통과하게 만드는 것. 지금 쓰는 맥에는 NVIDIA GPU가 없어서 일단 CPU로 빌드·실행만 검증하기로 했다. 15줄 안팎짜리 Dockerfile 하나 쓰는 데 빌드 에러를 4번 순서대로 만났고, 그 과정에서 빌드 컨텍스트와 레이어 캐시가 실제로 어떻게 움직이는지 볼 수 있었다.

## 빌드 컨텍스트란

Dockerfile을 쓰기 전에 짚고 넘어가야 하는 개념이 하나 있다.

- **빌드 컨텍스트**: `docker build` 명령에 넘기는 디렉토리. `COPY`나 `ADD`는 이 디렉토리 안에 있는 파일만 이미지에 넣을 수 있다.

쉽게 말해 `docker build`를 실행하는 순간, 도커 데몬은 지정한 디렉토리 전체를 압축해서 넘겨받는다. 그 바깥에 아무리 필요한 파일이 있어도 `COPY`는 그걸 볼 방법이 없다. 이 전제를 모르고 시작했다가 아래 두 번째 에러를 그대로 맞았다.

## 빌드 에러 4개 (순서대로)

**① `RUN apt install && pip install`을 한 줄에 합쳐서 실패**

베이스 이미지(`nvidia/cuda:12.4.1-runtime-ubuntu22.04`)에는 패키지 목록도, 파이썬도, pip도 없는 상태다. `apt-get update` 없이 설치를 시도했고, 설치할 패키지 이름도 안 썼고, pip은 아직 설치되지도 않아서 `command not found`가 났다. 세 가지 실수가 한 줄에 겹쳐 있었던 셈이다. 고친 형태:

```dockerfile
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*
```

마지막 `rm -rf /var/lib/apt/lists/*`는 apt가 받아둔 패키지 목록 캐시를 지워서 레이어 용량을 줄이는 관례다. 고치면서 `apt` 대신 `apt-get`을 쓴 것도 이유가 있다 — `apt`는 스크립트에서 쓰면 "unstable CLI" 경고를 내는, 사람용 명령이기 때문이다.

**② `COPY requirements.txt .` → 파일을 못 찾음**

파일은 분명 리포 루트에 있는데 `COPY`가 못 찾았다. 원인은 위에서 정리한 빌드 컨텍스트였다. Dockerfile이 `docker/` 안에 있어서 그 디렉토리를 컨텍스트로 넘기고 있었고, 컨텍스트 바깥의 루트 `requirements.txt`는 애초에 전송조차 안 된 파일이었다. 해결은 컨텍스트를 리포 루트로 주고, Dockerfile 위치만 `-f`로 따로 지정하는 것.

```bash
docker build -f docker/Dockerfile -t mnist-train .
```

**③ pip이 scikit-learn을 못 찾음**

PyTorch CPU 휠을 받으려고 `--index-url https://download.pytorch.org/whl/cpu`를 붙였는데, 이 인덱스에는 torch 계열 패키지만 있다. requirements.txt에 있던 scikit-learn, jupyterlab은 여기 없으니 못 찾는 게 당연했다. 그런데 다시 보니 `train_mnist.py`가 import 하는 건 torch, torchvision뿐이었다. 로컬에서 개발할 때 쓰는 의존성(주피터 등)과 컨테이너가 실행 시점에 실제로 필요로 하는 의존성은 다른 것이었다 — 이미지에는 실행에 필요한 최소만 넣으면 됐다.

```dockerfile
RUN pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

CPU 휠을 고른 이유도 따로 있다. 기본 `pip install torch`는 CUDA용 휠(약 2.5GB)을 받는다. 지금은 CPU로 빌드·실행만 검증하는 단계라 200MB대의 CPU 휠로 가볍게 유지했다.

**④ `CMD "echo start!"` → not found**

빌드는 통과했는데 `docker run`에서 죽었다. 문자열 하나로 통째로 넘긴 CMD는 셸이 따옴표 포함 전체를 명령어 이름 하나로 해석해버린다. 올바른 형태는 JSON 배열로 쓰는 exec form이다.

```dockerfile
CMD ["python3", "train_mnist.py", "--epochs", "1"]
```

shell form으로 쓰면 `/bin/sh -c`를 거쳐서 셸이 컨테이너의 첫 프로세스가 되고, exec form으로 쓰면 python이 직접 첫 프로세스가 된다. 예전 글에서 컨테이너 안 첫 프로세스가 곧 내가 띄운 프로세스라는 걸 확인한 적이 있는데, CMD 형식이 바로 그 프로세스를 결정하는 자리였다.

## .dockerignore — 1GB가 136B로

컨텍스트를 리포 루트로 바꾸자 다른 문제가 생겼다. 리포에는 `.venv/`(991MB)와 데이터셋(63MB)이 있어서 매 빌드마다 약 1GB를 도커 데몬으로 전송하게 된 것이다. `.dockerignore`에 아래 목록을 추가하고 다시 빌드했다.

```
.venv/
data/
models/
.git/
.obsidian/
__pycache__/
*.pyc
```

```
=> => transferring context: 136B
```

1GB급이던 전송량이 136바이트로 줄었다. `.gitignore`가 커밋에 안 실을 파일을 정하는 거라면, `.dockerignore`는 빌드 컨텍스트로 전송할 파일을 정하는 셈이다.

## 실행 — 드라이버 경고와 사라진 모델

`docker run --rm`으로 돌리자 CUDA 배너와 함께 경고가 떴다.

```
WARNING: The NVIDIA Driver was not detected.  GPU functionality will not be available.
...
INFO train_mnist: device=cpu (cuda available: False)
INFO train_mnist: epoch 0 done, loss=0.0898
INFO train_mnist: 모델 저장/재로드 검증 완료: models/mnist.pt
```

경고의 의미가 오늘 확인한 것 중 제일 중요했다. 이미지 안에는 CUDA **런타임**만 있고, **드라이버**는 호스트 것을 빌려 쓴다. GPU가 있는 호스트에서 `--gpus all`을 붙이면 NVIDIA Container Toolkit이 호스트 드라이버를 컨테이너에 주입해주는 구조다. 지금 쓰는 맥에는 NVIDIA 드라이버가 없으니 경고가 뜨는 게 오히려 정상이고, 스크립트는 의도대로 CPU 1 epoch을 끝까지 완주했다(loss=0.0898, 모델 저장/재로드 검증까지 통과).

한 가지 더 확인한 게 있다. MNIST 데이터 다운로드도, 학습된 모델(`models/mnist.pt`)도 전부 컨테이너 **안에서** 만들어졌고, `--rm`으로 컨테이너가 종료되는 순간 함께 사라졌다. 지난 글에서 컨테이너가 지워지면 데이터도 같이 사라지니 볼륨으로 분리해야 한다고 말로만 적어뒀던 걸, 이번엔 직접 겪은 셈이다.

## 레이어 캐시 실측 — 확신 없던 지점을 확인하다

여기부터가 지난 글에서 남긴 확신 없는 두 번째 지점을 검증한 부분이다. 아무것도 안 바꾸고 재빌드하면 레이어 전부가 캐시를 타면서 빌드가 1.5초 만에 끝났다. 그다음 `train_mnist.py`에 주석 한 줄만 추가하고 다시 빌드했다.

```
=> CACHED [3/5] RUN apt-get update && apt-get install -y python3 python3-pip ...
=> CACHED [4/5] RUN pip3 install --no-cache-dir torch torchvision ...
=> [5/5] COPY python/train_mnist.py .
```

apt 레이어와 pip 레이어는 그대로 `CACHED`로 남았고, `COPY` 레이어만 다시 실행됐다. 도커는 `COPY` 대상 파일을 내용 체크섬으로 비교하기 때문에, 주석 한 줄이라도 바뀌면 그 레이어부터 무효화된다. 이미지 해시도 `aa98f3`에서 `b537d6`으로 바뀌었다 — 즉 레이어 자체가 수정되는 게 아니라, 바뀐 레이어를 새로 만들고 그걸 얹은 "새 이미지"가 하나 더 생기는 것이었다. "변경된 부분이 기존 레이어에 쌓인다"고 적었던 지난 글의 문장이 헷갈렸던 이유가 여기서 풀렸다 — 쌓이는 건 레이어 자체가 아니라, 그 위에 새로 만들어지는 레이어다.

> 🖼️ **[사진 1]** 캐시가 바뀐 레이어부터 아래로 전부 무효화되는 구조 — 위쪽 레이어를 고치면 그 아래 레이어(예: pip 설치처럼 무거운 것)까지 전부 다시 실행된다
> → 업로드: `1. docker-build-cache-invalidation.png`

여기서 반대 방향이 더 중요한 교훈이었다. 만약 apt 설치 줄을 고쳤다면 그 **아래에 있는** pip 레이어(제일 무겁고 느린 레이어)까지 전부 다시 실행됐을 거다. 캐시는 바뀐 명령부터 그 아래로 전부 깨진다. 그래서 지금 Dockerfile은 비싸고 잘 안 바뀌는 명령(apt, pip 설치)을 위에, 자주 바뀌는 소스 코드(`COPY`)를 맨 아래에 둔 순서로 되어 있다.

```dockerfile
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

WORKDIR /app

RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY python/train_mnist.py .

CMD ["python3", "train_mnist.py", "--epochs", "1"]
```

## 다음 확인 목록

지난 글에서 남긴 확신 없는 지점 세 개 중 하나를 처리했으니 남은 건 두 개다.

1. 컨테이너를 띄우는 게 정확히 "복사"인지 — `docker diff`, `docker history`로 컨테이너를 띄운 전후에 실제로 뭐가 생기는지 찍어봐야 한다.
2. 지금 알고 있는 볼륨(호스트 디렉토리 마운트)이 도커가 말하는 volume 전체인지, 그중 한 방식(bind mount)일 뿐인지 — `docker volume create` + `-v` 마운트로 컨테이너를 지웠다 다시 띄워서 데이터가 남는지 직접 확인해볼 차례다. 마침 오늘 `--rm`으로 데이터가 사라지는 걸 봤으니, 다음엔 그 데이터를 볼륨으로 분리해서 살아남게 만들어볼 계획이다.

## 정리

이번에 새로 확인한 것 세 가지.

1. `COPY`는 빌드 컨텍스트 바깥을 절대 볼 수 없다 — 컨텍스트는 루트로 주고 Dockerfile 위치는 `-f`로 분리 지정하고, `.dockerignore`로 전송량을 지킨다(1GB → 136B).
2. 이미지에는 CUDA 런타임만 있고 드라이버는 호스트 것을 빌려 쓴다 — "Driver was not detected" 경고는 이 구조를 그대로 보여준다.
3. 레이어 캐시는 레이어 자체가 수정되는 게 아니라, 바뀐 지점부터 아래로 전부 무효화되면서 새 레이어를 얹은 새 이미지가 생긴다. 그래서 비싸고 안 바뀌는 명령은 위에, 자주 바뀌는 소스는 맨 아래에 쓴다.

말로 정리했던 지식과 명령어로 찍어본 결과가 어긋나지 않는다는 걸 확인하고 나니, 다음엔 남은 두 가지(복사/CoW, 볼륨의 정확한 정체)도 같은 방식으로 확인해보고 싶어졌다.

<!-- BLOG-IMAGES (blog-collect.py가 이 아래를 떼어냄) -->
<!-- IMG: 1 | docker-build-cache-invalidation | web | Docker 빌드 캐시가 바뀐 레이어부터 아래로 무효화되는 구조를 보여주는 공식 문서 다이어그램 | https://raw.githubusercontent.com/docker/docs/main/content/manuals/build/images/cache-stack-invalidated.png | Docker 공식 문서 저장소(docker/docs, build cache), 저작권 Docker Inc., 출처 표기 후 인용 -->
