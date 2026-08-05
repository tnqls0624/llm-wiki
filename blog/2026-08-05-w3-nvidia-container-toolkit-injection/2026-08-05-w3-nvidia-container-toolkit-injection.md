# GPU 컨테이너, 요청과 주입은 다른 주체다 — `--gpus all` 실행 체인과 3주째 막혀 있던 문서 하나

## 준비할 이미지
1. `1. nvidia-container-toolkit-arch.png` — NVIDIA Container Toolkit 공식 아키텍처 다이어그램(런타임/hook/CLI 구성) (web: NVIDIA 공식 문서)
2. `2. aws-g4dn-instance-spec.png` — AWS g4dn.xlarge(T4 16GB, Turing) 인스턴스 스펙 공식 페이지 (shot: 직접 캡처 — 선택 사항, 없어도 본문은 성립)

7월 중순에 CUDA 컨테이너를 띄웠을 때 뜨는 `NVIDIA Driver was not detected` 경고가 정확히 어느 계층의 부재를 뜻하는지 스택을 그려가며 정리했다. 결론은 "커널 드라이버 모듈은 호스트에 남고, 사용자 공간 드라이버 라이브러리와 `/dev/nvidia*`는 NVIDIA Container Toolkit이 컨테이너에 연결해준다"는 것이었다. 그런데 그 정리에는 구멍이 하나 있었다 — "언제" 연결되는지, 즉 `docker run --gpus all`을 치는 순간부터 컨테이너 안에서 `nvidia-smi`가 뜨는 순간까지 실제로 어떤 순서로 일이 벌어지는지가 빠져 있었다. 이번 글은 그 빈칸을 채운 기록이다. 그리고 그 사이에 있었던, 조금 민망하지만 솔직하게 남겨야 할 이야기도 하나 있다. 그 정리 이후 20일 동안 커밋이 하나도 없었는데, 원인이 의지 부족이 아니라 파일 하나가 텅 비어 있었기 때문이었다는 것이다.

## 먼저 짚은 것 — 커널 드라이버는 호스트, 그 위는 Toolkit의 몫

그때 정리한 결론만 짧게 복기하면 이렇다.

- 컨테이너는 호스트 Linux 커널을 그대로 공유한다. 그래서 `nvidia`, `nvidia_uvm` 같은 **커널 드라이버 모듈은 호스트에만** 로드된다. 컨테이너가 자기 몫의 커널 모듈을 따로 갖는 구조가 아니다.
- 반면 컨테이너 안의 CUDA 프로그램이 그 커널 드라이버를 호출하려면 **사용자 공간 드라이버 라이브러리**(`libcuda.so`, NVML 등)와 **GPU 장치 파일**(`/dev/nvidia0`, `/dev/nvidiactl` 등)이 컨테이너 안에서 보여야 한다. 이건 이미지에 미리 구워 넣는 게 아니라, NVIDIA Container Toolkit이 컨테이너를 실행하는 시점에 연결해주는 것이다.
- CUDA Toolkit(`nvcc`, 헤더, 컴파일러)과 NVIDIA Driver는 서로 다른 소프트웨어다. 이미지 안에 CUDA Toolkit이 있어도 드라이버가 연결 안 되면 GPU 연산은 안 된다.

이 정리를 하기 전에는 "드라이버는 전부 호스트에만 있고 컨테이너에는 아무 요소도 안 들어온다"고 생각했었는데, 그 표현은 틀렸다. 커널 모듈은 호스트에 고정이지만, 그 위의 사용자 공간 인터페이스는 필요할 때마다 컨테이너 경계를 넘어 들어온다. 이번 글의 주제는 바로 그 "필요할 때"가 정확히 언제이고, 누가 그 일을 하느냐다.

## `--gpus all`은 설치 명령이 아니라 GPU 장치 "요청"이다

처음엔 `--gpus all`을 "GPU 드라이버를 컨테이너에 설치하는 옵션"처럼 생각하고 있었다. 그런데 공식 문서와 아키텍처를 다시 보니 이 플래그가 하는 일은 훨씬 좁다. **`--gpus all`은 GPU를 설치하라는 명령이 아니라, "이 컨테이너에 GPU 장치를 붙여 달라"는 요청(request)일 뿐이다.** 그 요청을 실제로 들어주는 건 다른 컴포넌트다.

**Device Request란?**
- Docker 클라이언트가 `--gpus` 플래그를 해석해서 만드는 내부 구조체다. "어떤 GPU를 몇 개, 어떤 capability로 달라"는 요청 내용이 여기 담긴다.
- 이 시점에는 아직 아무 것도 컨테이너 안에 들어오지 않는다. 요청서를 작성했을 뿐이다.

전체 흐름을 순서대로 적으면 이렇다.

```text
docker run --gpus all <image>
        │
        ▼
Docker가 Device Request 생성          ← "GPU 달라"는 요청만 만들어짐
        │
        ▼
nvidia-container-runtime               ← OCI 런타임 실행 전, 요청을 가로챔
        │
        ▼
OCI runtime hook (prestart)            ← 컨테이너 생성 스펙에 훅을 끼워 넣음
        │
        ▼
nvidia-container-cli / libnvidia-container
        │                               ← 실제로 GPU 장치·드라이버 라이브러리를
        │                                  마운트 목록에 추가
        ▼
runc가 컨테이너를 exec 하기 직전        ← 여기서 주입이 "완료"된다
        │
        ▼
컨테이너 안 프로세스 시작 (/dev/nvidia*, libcuda.so 사용 가능)
```

> 🖼️ **[사진 1]** NVIDIA Container Toolkit 공식 아키텍처 다이어그램 — 런타임(runtime)·hook·CLI가 어떻게 이어지는지
> → 업로드: `1. nvidia-container-toolkit-arch.png`

**OCI hook이란?**
- OCI(Open Container Initiative) 런타임 스펙은 컨테이너를 실제로 띄우기 전후에 외부 프로그램을 끼워 넣을 수 있는 지점(hook)을 정의해둔다.
- NVIDIA Container Toolkit은 이 중 `prestart` hook에 자기 프로그램을 등록해둔다. 그래서 `runc`가 컨테이너를 만드는 과정 중간에 "잠깐, GPU 장치와 라이브러리부터 마운트하고 가자"고 끼어들 수 있다.
- 쉽게 말해 택배가 문 앞에 도착하기(컨테이너 실행) 직전에 검수원(hook)이 한 번 상자를 열어 빠진 물건(GPU 장치·드라이버 라이브러리)을 채워 넣는 것과 같다.

이 흐름에서 중요한 건 **"요청은 클라이언트(Docker)가 만들고, 주입은 런타임(Toolkit)이 한다"는 역할 분리**다. `--gpus all`을 붙이는 순간 GPU가 뿅 하고 나타나는 게 아니라, 그 사이에 nvidia-container-runtime → OCI hook → nvidia-container-cli로 이어지는 체인이 한 번 돈다. 그리고 이 체인이 끝나는 지점은 **runc가 컨테이너 프로세스를 exec하기 바로 직전**이다. 컨테이너 안 애플리케이션이 처음 실행되는 순간에는 이미 `/dev/nvidia*`와 드라이버 라이브러리가 마운트되어 있는 상태라는 뜻이다.

여기서 자연스럽게 따라오는 결론이 하나 있다. 컨테이너 안에서 `nvidia-smi`를 돌리면 Driver Version이 하나 찍히는데, **이 값은 컨테이너 안에 따로 설치된 드라이버 버전이 아니라 호스트 드라이버 버전 그대로다.** Toolkit이 주입하는 건 이미 호스트에 로드되어 있는 드라이버의 사용자 공간 인터페이스이지, 별도의 드라이버를 컨테이너용으로 새로 설치하는 게 아니기 때문이다. 그래서 같은 호스트 위에서 여러 컨테이너를 띄워도 안에서 보이는 Driver Version은 전부 같다.

## 다음 세션에 확인할 것 — 검증 스크립트를 미리 설계해뒀다

여기까지는 전부 문서와 아키텍처를 대조해서 정리한 내용이고, 실제로 손으로 돌려서 확인한 건 하나도 없다. GPU가 없는 맥에서는 애초에 검증이 불가능하고, 마침 이 글을 쓰는 시점엔 Docker 데몬조차 켜져 있지 않아서 로컬에서 가능한 최소한의 확인(`docker create --gpus all`이 클라이언트 단에서 뭘 남기는지 보는 정도)도 못 했다. 그래서 이번엔 GPU가 붙은 서버에 접속하자마자 돌릴 검증 스크립트를 미리 짜두는 것으로 마무리했다.

VM은 시간당 과금이라 접속 후 헤매는 시간 자체가 비용이다. 그래서 스크립트는 지금까지 정리한 층 구조를 그대로 따라가게 짰다.

1. **호스트 계층** — `nvidia-smi`, `lsmod | grep nvidia`, `/dev/nvidia*` 존재 확인. 여기가 실패하면 아래는 전부 의미가 없으니 제일 먼저 본다.
2. **Toolkit 계층** — `nvidia-ctk --version`, `/etc/docker/daemon.json`, `docker info`로 런타임 등록 여부 확인.
3. **요청 계층** — `docker create --gpus all`로 컨테이너를 **실행하지 않고 생성만** 한 뒤 `docker inspect`로 `DeviceRequests`를 들여다본다. 이 글의 핵심 가설을 검증하는 지점이다. 아직 실행 전인데도 요청 내용이 이미 기록되어 있다면 "요청과 주입은 분리된 단계"라는 게 실측으로 확인되는 것이다.
4. **주입 계층** — 같은 이미지를 **GPU 요청 없이 한 번, `--gpus all`로 한 번** 실행해서 `/dev/nvidia*`와 `nvidia-smi` 출력을 나란히 비교한다. 이 대조가 스크립트에서 가장 마음에 드는 부분인데, 이미지는 완전히 동일하고 런타임 옵션 하나만 다르기 때문에 결과 차이가 나면 그 차이의 원인은 이미지가 아니라 런타임이라고 못박을 수 있다.
5. **라이브러리 계층** — 컨테이너 안에서 `libcuda.so`(드라이버가 주입한 것)와 `libcudart.so`(이미지에 원래 포함된 CUDA Runtime)를 따로 찾아본다. 드라이버 계층과 CUDA Toolkit 계층이 서로 다른 층이라는 걸 파일 위치로 직접 확인하는 단계다.
6. **프레임워크 계층** — PyTorch가 있는 이미지라면 `torch` import까지 도달하는지 본다.

```bash
./verify-gpu-container.sh 2>&1 | tee gpu-verify-$(date +%Y%m%d-%H%M).log
```

스크립트에는 `set -e`를 일부러 넣지 않았다. 실패하는 명령의 에러 메시지 자체가 이번 실습에서 보고 싶은 자료이기 때문이다. 예를 들어 `--gpus` 옵션을 런타임이 못 알아들으면 어떤 에러 문구가 나오는지가, 명령이 성공하는 것 못지않게 중요한 정보다. 다만 이 스크립트는 로컬에서 부분적으로라도 먼저 돌려보고 갔어야 한다는 걸 알고 있다 — GPU가 없어도 3번(요청 계층)과 4번의 "GPU 미요청" 절반은 로컬에서도 실행이 되는 부분이라, 다음 세션에 GPU VM으로 넘어가기 전에 그 부분부터 확인해두려고 한다. 어쨌든 지금 상태를 정직하게 말하면, **개념은 정리됐지만 실측은 0건이고, 다음 세션에 실제 GPU VM에서 이 스크립트로 검증할 예정**이다.

## 3주간 이론만 읽었던 진짜 이유 — 막혀 있던 건 문서 한 장이었다

여기서부터는 조금 다른 이야기다. 이번 CUDA/드라이버 스택 정리를 처음 시작한 게 7월 16일이었는데, 이 글을 쓰는 지금까지 딱 20일이 걸렸다. 그 사이 커밋이 하나도 없었다. 처음엔 "요새 좀 늘어졌나" 싶었는데, 다시 들여다보니 원인은 게으름이 아니라 훨씬 구체적이었다.

GPU 실습을 시작하려면 어떤 클라우드에, 어떤 인스턴스로, 얼마 예산으로 들어갈지를 정리하는 결정 문서를 먼저 채워야 다음 단계(실제 GPU 서버에서의 실습)로 넘어갈 수 있게 로드맵을 짜뒀었다. 그런데 이 결정 문서 파일 자체는 이미 저장소에 커밋되어 있었다 — 다만 **내용이 전부 공란인 채로.** 파일 존재 여부만 보면 "작업했다"처럼 보이지만, 실제로는 다음 단계로 넘어가기 위한 조건이 하나도 충족되지 않은 상태였다. 그러니 20일 동안 할 수 있는 건 이미 아는 개념을 다른 각도로 다시 정리하는 것뿐이었고, 그게 "이론만 읽는" 상태로 보였던 것이다.

이번에 그 문서를 실제로 채우면서 몇 가지를 확정했다.

- **인스턴스**: AWS EC2 `g4dn.xlarge` — NVIDIA T4 16GB, Turing 아키텍처(`sm_75`). 처음엔 `t3.large`를 골랐다가, 이게 GPU가 아예 없는 범용 인스턴스라는 걸 뒤늦게 확인했다. AWS에서 Turing 이상 GPU가 붙은 계열은 `g4dn`/`g5`/`g6`이고, `p3`(V100, Volta 아키텍처)는 최신 CUDA 지원이 이미 끊겨서 후보에서 뺐다.
- **비용**: g4dn.xlarge 온디맨드 기준 시간당 약 $0.63(서울 리전). 실습 예상 사용 시간을 15~25시간으로 잡으면 총 $10~16 정도다. 컨테이너 대여형 서비스는 root 권한을 못 주는 경우가 많아서, 드라이버를 직접 설치해보는 실습 자체가 불가능해 제외했다.
- **AMI**: 드라이버가 이미 깔려 있는 이미지 대신, 드라이버가 없는 순수 Ubuntu 24.04로 시작해서 드라이버 설치부터 직접 해보기로 했다. 스택을 이해하는 게 목적이면 이미 다 세팅된 이미지를 쓰는 게 오히려 손해라고 판단했다.
- **주의할 것**: 신규 계정은 이런 GPU 인스턴스 종류의 vCPU 쿼터가 기본 0으로 잡혀 있는 경우가 많아서, 증설 승인부터 제일 먼저 신청해두기로 했다. 승인에 시간이 걸릴 수 있어서 실습 시작보다 먼저 처리해야 한다.

> 🖼️ **[사진 2]** AWS g4dn.xlarge 인스턴스 스펙 — T4 16GB, Turing 아키텍처인 것을 확인한 공식 페이지
> → 업로드: `2. aws-g4dn-instance-spec.png`

이 문서를 채우고 나서야 왜 3주 동안 진도가 이론에서만 맴돌았는지가 명확해졌다. 원인을 "의지가 부족했다"로 규정했으면 다음에도 똑같이 막혔을 거고, 반대로 "20일이나 쉬었으니 괜찮다"고 넘겼으면 이 문서가 왜 비어 있었는지 다시 안 봤을 것이다. 실제로 도움이 된 건 둘 다 아니고, **막혀 있는 지점이 정확히 어디인지 찾는 것**이었다. 이번 경우엔 그게 텅 빈 결정 문서 한 장이었다.

## 정리

이번에 확인한 것들을 한 문장씩으로 정리하면.

1. `--gpus all`은 GPU를 컨테이너에 설치하는 옵션이 아니라 GPU 장치를 요청하는 옵션이다. **요청은 Docker 클라이언트가 만들고, 그 요청을 실제 장치·라이브러리 마운트로 바꾸는 주입은 nvidia-container-runtime과 OCI hook, nvidia-container-cli가 이어받아서 처리하며, 이 작업은 runc가 컨테이너를 exec하기 직전에 끝난다.**
2. 컨테이너 안에서 보이는 `nvidia-smi`의 Driver Version은 호스트 드라이버 버전 그대로다. Toolkit은 새 드라이버를 넣는 게 아니라 이미 호스트에 있는 드라이버의 인터페이스를 연결할 뿐이기 때문이다.
3. 진도가 이론에서 멈춰 있을 때 원인이 항상 태도의 문제인 건 아니다. 이번엔 다음 단계로 넘어가기 위한 조건 문서 하나가 비어 있던 게 전부였고, 그 문서를 채우는 데는 오래 걸리지 않았다. 막힌 지점을 정확히 찾는 것 자체가 진도라는 걸 이번에 확인했다.

다음 글은 실제 GPU 서버에 접속해서 이 검증 스크립트를 돌린 결과 — 특히 Device Request가 실행 전에 이미 기록되어 있는지, 같은 이미지인데 `--gpus all` 유무로 `/dev/nvidia*`가 정말 갈리는지를 눈으로 확인한 기록이 될 것 같다.

**참고 자료**
- [NVIDIA Container Toolkit — Architecture Overview](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/arch-overview.html)
- [NVIDIA Container Toolkit — Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [NVIDIA CUDA Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/index.html)

<!-- BLOG-IMAGES (blog-collect.py가 이 아래를 떼어냄) -->
<!-- IMG: 1 | nvidia-container-toolkit-arch | web | NVIDIA Container Toolkit 공식 아키텍처 다이어그램(runtime/hook/CLI 구성) | https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/_images/runtime-architecture.png | NVIDIA Container Toolkit 공식 문서(arch-overview) · © NVIDIA — 출처 표기 후 인용 -->
<!-- IMG: 2 | aws-g4dn-instance-spec | shot | AWS g4dn.xlarge(T4 16GB, Turing) 인스턴스 스펙 공식 문서 페이지 캡처 (선택 — 없으면 마커 줄만 삭제) -->
