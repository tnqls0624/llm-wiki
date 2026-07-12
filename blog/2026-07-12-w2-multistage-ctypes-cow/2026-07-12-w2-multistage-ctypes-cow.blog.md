# 단일 스테이지를 멀티스테이지로

지난 글에서는 CUDA 베이스 이미지 위에 `train_mnist.py`를 얹는 Dockerfile을 완성했다. 빌드 에러 4개를 순서대로 잡고 나니 이미지는 잘 도는데, 문제는 크기였다. `docker images`로 확인한 크기가 3.22GB. 이번 글의 목표는 그 이미지를 멀티스테이지로 다이어트시키는 것이었는데, 실제로는 다이어트보다 사고를 치고 수습하는 데 시간을 더 썼다. 그 과정에서 venv COPY가 실제로 뭘 옮기고 뭘 못 옮기는지, 그리고 "빌드했다"와 "검증했다"가 왜 다른 말인지를 몸으로 확인했다.

## 멀티스테이지란 — venv를 통째로 옮기는 전략

단일 스테이지 Dockerfile은 `apt-get install`로 빌드 도구를 깔고, `pip install`로 torch를 설치하고, 그 상태 그대로 실행까지 간다. 문제는 빌드에만 필요한 도구(pip, python3-venv 등)가 최종 이미지에도 그대로 남는다는 것이다. 컨테이너가 실제로 실행될 때는 패키지 설치가 이미 끝나 있으니 이 도구들은 짐일 뿐이다.

**멀티스테이지 빌드란?**
- Dockerfile 안에 `FROM ... AS <이름>`으로 여러 스테이지를 두고, 뒤 스테이지가 `COPY --from=<이름>`으로 앞 스테이지의 산출물만 골라 가져오는 방식이다.
- 빌드 도구(gcc, pip, venv 생성기 등)는 앞 스테이지(`builder`)에만 남고, 최종 이미지(`runner`)에는 실행에 필요한 결과물만 들어간다.
- 쉽게 말해 요리로 치면 재료 손질(칼·도마·껍질)은 주방에만 남기고, 완성된 요리만 그릇에 담아 내보내는 것과 같다.

내가 고른 패턴은 **builder에서 venv를 하나 만들어 그 안에 torch/torchvision을 설치하고, runner는 그 venv 디렉터리 `/opt/venv`를 통째로 `COPY` 한 번에 옮기는 방식**이다. 패키지 하나하나를 다시 설치하는 대신 이미 만들어진 site-packages 묶음을 그대로 복사하는 셈이라 깔끔하다고 생각했는데, 여기서 첫 번째 사고가 났다.

> 🖼️ **[사진 1]** builder 스테이지에서 venv를 만들고, runner 스테이지가 `COPY --from=builder`로 그 결과물만 가져오는 구조도
> → 업로드: `1. multi-stage-build.png`

## 사건 ① ctypes가 사라졌다

멀티스테이지로 바꾼 첫 Dockerfile은 `docker build`까지는 멀쩡히 통과했다. 그런데 `docker run`으로 컨테이너를 띄우자 `import torch` 한 줄에서 바로 죽었다.

```
ModuleNotFoundError: No module named 'ctypes'
```

torch가 없다는 것도 아니고 ctypes라니, 처음엔 뭐가 문제인지 감이 안 왔다. 원인은 runner 스테이지에 설치한 파이썬이 `python3-minimal`이었다는 것이다.

**venv와 stdlib의 관계**
- venv(가상환경)는 `pip install`로 받은 패키지(site-packages)만 자기 디렉터리 안에 담는다.
- ctypes 같은 표준 라이브러리(stdlib)는 venv 안에 들어 있는 게 아니라, venv가 참조하는 **시스템 파이썬**이 갖고 있다.
- `python3-minimal`은 인터프리터 최소 구성이라 stdlib 대부분이 빠져 있고, ctypes 같은 모듈은 `libpython3.10-stdlib`(full `python3` 패키지가 끌고 오는 것) 쪽에 들어 있다.

즉 venv를 통째로 `COPY`해도 따라오는 건 site-packages(torch, torchvision)뿐이고, ctypes 같은 stdlib은 runner 이미지 자체의 시스템 파이썬 몫이라 별도로 갖춰야 했다. runner의 apt 설치 대상을 `python3-minimal`에서 full `python3`로 바꾸자 문제가 사라졌다.

> 🖼️ **[사진 2]** venv를 COPY한 뒤 `import torch`가 ctypes를 못 찾고 죽는 실제 에러 화면
> → 업로드: `2. ctypes-modulenotfounderror.png`



## 크기 실측 — 레이어 단위로 뜯어보기

사고를 수습하고 나서 원래 목표였던 크기 비교를 했다.

| 구분 | 크기 |
|---|---|
| 단일 스테이지 (`mnist-train:latest`) | 3.22GB |
| 멀티스테이지 (`mnist-train:multistage`) | 2.90GB |
| 차이 | −320MB (−9.9%) |

`docker history`로 레이어를 쪼개보면 이 320MB가 어디서 나왔는지 보인다.

- **줄어든 곳**: apt 레이어 345MB → 32.3MB. runtime 스테이지에서 pip·venv 생성 도구와 그 의존성을 뺀 효과가 절감분의 거의 전부다.
- **안 줄어든 곳**: torch venv 레이어 779MB → 772MB로 사실상 그대로다.

이 두 번째 숫자가 이번 실습에서 가장 중요한 발견이었다. **멀티스테이지가 이미지 크기를 항상 줄여주는 건 아니다.** 실행에 실제로 필요한 라이브러리(torch 자체)는 빌드 도구가 아니라서 어느 스테이지로 옮기든 그대로 남는다. 멀티스테이지가 걷어내는 건 어디까지나 "빌드에만 쓰고 실행엔 안 쓰는" 도구들이다.

남은 약 2.1GB는 `nvidia/cuda:12.4.1-runtime` 베이스 이미지 자체의 몫이다. CPU 전용으로만 쓸 거면 `python:3.11-slim` 베이스로 바꿔 1GB 아래로도 내려갈 수 있지만, Block 2에서 GPU로 전환할 계획이 있어 CUDA 베이스는 그대로 유지하기로 했다.

```dockerfile
# =========================
# 1. Dependency builder
# =========================
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        torch==2.12.1 torchvision==0.27.1 \
        --index-url https://download.pytorch.org/whl/cpu

# =========================
# 2. Runtime
# =========================
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS runner

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:${PATH}"
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY python/W1/D5/train_mnist.py ./train_mnist.py

CMD ["python", "train_mnist.py", "--epochs", "1"]
```

(지면상 `ENV DEBIAN_FRONTEND` 등 일부 설정 줄은 생략한 축약본 — 전체는 repo의 `docker/Dockerfile` 참고)

## `-v` 마운트와 `docker diff` — CoW를 눈으로 보기

지난 글에서 컨테이너 안에서 만든 데이터(MNIST 다운로드, 저장된 모델)가 `--rm`과 함께 사라지는 걸 확인했었다. 이번엔 그걸 `-v` 마운트로 실제로 막아보고, 그 전후를 `docker diff`로 대조했다.

```bash
docker run --rm \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/models:/app/models" \
  mnist-train:multistage
```

**Copy-on-Write(CoW)란?**
- 컨테이너는 이미지의 읽기 전용 레이어들 위에 쓰기 가능한 레이어 한 장을 얹어서 실행된다.
- 컨테이너 안에서 파일을 새로 만들거나 바꾸면 이 쓰기 레이어에 쌓이고, `--rm`으로 컨테이너를 지우면 이 레이어도 함께 사라진다.
- `-v` 마운트는 이 쓰기 레이어를 거치지 않고 호스트 디렉터리에 직접 쓰도록 우회로를 뚫어주는 것이다.

`docker diff`로 두 경우를 대조하면 이 우회가 실제로 일어났는지 확인할 수 있다. diff 기호는 `A`(추가) · `C`(변경) · `D`(삭제)이고, 디렉터리는 그 안에 자식 엔트리가 생기면 부모 디렉터리 자체도 `C`로 표시된다.

- **마운트 없이 실행**: `/app/data` 밑 MNIST 파일 8개와 `/app/models/mnist.pt`가 전부 `A`로 잡힌다. 이 파일들은 전부 쓰기 레이어에 쌓인 것이고, `--rm`과 함께 소멸한다.
- **마운트해서 실행**: `A /app/data`, `A /app/models`라는 빈 마운트 지점 디렉터리만 남고, 그 안의 파일 내용은 diff에 0줄이다. 실제 쓰기는 CoW 레이어를 거치지 않고 호스트로 바로 갔다는 뜻이다.
- 다만 `/tmp/perf-1.map`, `/tmp/torchinductor_root`는 마운트 여부와 무관하게 양쪽 다 `A`로 남았다. PyTorch 런타임이 남기는 흔적인데, `docker diff`는 특정 경로가 아니라 프로세스가 건드린 파일 전부를 잡는다는 걸 보여준다.

> 🖼️ **[사진 3]** `-v` 마운트 유무에 따른 `docker diff` 결과 비교 — 마운트 없으면 데이터 전부 `A`, 마운트하면 빈 디렉터리만 `A`
> → 업로드: `3. docker-diff-cow.png`

호스트에 남은 `models/mnist.pt`의 수정 시각을 컨테이너 로그에 찍힌 저장 시각과 맞춰보니 초 단위로 일치했다. 컨테이너가 마운트를 통해 호스트에 직접 쓰고 있다는 증거다. 부수적으로, 호스트의 `data/` 디렉터리를 재사용하니 MNIST를 다시 받을 필요가 없어져 다운로드 포함 13초 걸리던 실행이 캐시 상태에서는 3.5초로 줄었다.

## 부수 관찰 두 가지

- **^C가 파이썬에 직접 꽂힌다**: 학습 도중 Ctrl+C를 누르면 컨테이너 안 python이 곧바로 `KeyboardInterrupt`로 종료된다. CMD를 exec form(`["python", ...]`)으로 써서 python 자체가 PID 1이기 때문에 SIGINT가 셸을 거치지 않고 바로 전달된 것이다. shell form이었다면 `sh`가 PID 1이 되어 시그널이 여기서 막혔을 것이다. 지난 글에서 확인한 "컨테이너의 PID 1 = 내가 띄운 프로세스"가 시그널 처리에도 그대로 이어진다는 걸 확인한 셈이다.
- **로그의 loss는 평균이 아니다**: 실행할 때마다 로그에 찍히는 loss 값이 0.057, 0.445, 0.183처럼 매번 달랐다. 처음엔 이상하다고 생각했는데, 이 값은 한 epoch 전체의 평균이 아니라 **마지막 배치 하나의 loss**였다. 배치 단위로 값이 출렁이는 걸 그대로 찍고 있으니 실행마다 다른 게 정상이다.

## 정리

이번 실습에서 새로 확인한 것들.

1. venv를 `COPY`해도 따라오는 건 site-packages뿐이다. ctypes 같은 stdlib은 시스템 파이썬(full `python3`) 몫이라 runner 스테이지에도 별도로 갖춰야 한다.
2. 멀티스테이지가 이미지 크기를 항상 줄여주는 건 아니다 — 걷어낼 수 있는 건 빌드 전용 도구뿐이고, 실행에 실제로 필요한 라이브러리(이번 경우 torch venv 레이어)는 그대로 남는다.
3. "빌드가 성공했다"와 "이미지 안에 내가 원하는 게 들어 있다"는 다른 말이다. `docker run <이미지> python -c "..."`로 아티팩트 내부를 직접 열어보는 게 진짜 검증이다.
4. `-v` 마운트는 컨테이너의 Copy-on-Write 레이어를 우회해 호스트에 직접 쓴다. `docker diff`의 `A`/`C`/`D` 기록으로 그 경계를 눈으로 확인할 수 있다.
5. exec form CMD는 컨테이너 안 프로세스를 PID 1로 만들어 시그널을 직접 받게 한다 — 이게 볼륨·캐시뿐 아니라 종료 방식까지 관통하는 원리였다.

다음은 named volume과 bind mount를 나란히 비교해보고, Block 1 게이트인 GPU 접근 방식 결정 문서를 쓸 차례다.
