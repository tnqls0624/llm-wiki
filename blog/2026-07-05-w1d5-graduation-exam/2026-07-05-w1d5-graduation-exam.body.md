최근 AI 인프라 공부를 시작하면서 PyTorch로 MNIST 숫자 분류기를 학습시키는 CLI 스크립트를 만들었다. 데이터 로드부터 학습, 모델 저장까지 한 번에 돌아가서 "다 됐다"고 생각했는데, 리뷰에서 예외 처리는 코드만 읽어서 검증되는 게 아니라는 피드백을 받았다. 네트워크를 끊거나 디렉토리 권한을 없애는 식으로 실제 장애를 만들어보고, 그때 스크립트가 어떤 exit code로 끝나는지 확인해보라는 것이었다. 이 글에서는 그 과정에서 확인한 exit code의 의미, 라이브러리의 예외 재포장, silent fallback과 fail-fast의 차이를 정리한다.

## exit code란?

프로세스가 종료될 때 OS에 돌려주는 정수값이다. 관례상 0은 성공, 0이 아닌 값은 실패다. 쉘의 `$?`, CI 파이프라인의 스텝 성공/실패 판정, cron job 재시도, 쿠버네티스 컨테이너의 재시작 정책까지 전부 이 숫자 하나만 보고 동작을 결정한다. 로그에 에러 메시지가 잘 남아 있어도 exit code가 0이면 저 시스템들은 전부 "성공"으로 처리한다.

파이썬은 `sys.exit(code)`로 이 값을 넘긴다. 그런데 `sys.exit(None)`을 호출하면 exit code는 0이 된다. `return`만 쓰고 끝나는 함수의 반환값은 `None`이라서, 그걸 그대로 넘기면 실패한 로직인데도 프로세스는 성공으로 종료된다. 이 스크립트의 `main()`이 정확히 이 패턴이었다.

```python
if __name__ == "__main__":
    sys.exit(main())
```

`main()`은 `-> int` 시그니처인데, 예외 처리 분기 중 하나가 `return`만 쓰고 있었다. 문제인지 아닌지는 코드만 봐서는 확신이 안 됐다. 직접 장애를 만들어 확인해야 했다.

## 실험 1: Wi-Fi를 끄고 실행하기 — 라이브러리는 예외를 그대로 보여주지 않는다

`load_data()`는 `torchvision.datasets.MNIST`로 데이터를 내려받는데, 네트워크가 끊기면 어떤 예외가 올라올지 문서만 봐서는 확신이 없었다. Wi-Fi를 끄고 실행해봤다.

내부적으로 소켓 연결 실패(`socket.gaierror`)가 나고, 이게 `urllib`을 거치며 `urllib.error.URLError`로 바뀌고, 최종적으로 `torchvision`이 이걸 다시 `RuntimeError`로 감싸 던졌다. OS 수준 네트워크 예외가 라이브러리 세 겹을 거치며 타입이 계속 바뀐 것이다.

> 🖼️ **[사진 1]** Wi-Fi를 끄고 실행했을 때의 traceback — `socket.gaierror` → `URLError` → `RuntimeError`로 예외 타입이 바뀌어 올라온 실제 출력
> → 업로드: `1. wifi-off-traceback.png`

그런데 당시 `main()`의 예외 처리는 이랬다.

```python
except OSError as e:
    logger.error("파일/네트워크 I/O 실패: %s", e)
    return
```

`RuntimeError`를 잡는 분기가 없어서 그대로 unhandled exception으로 죽었다. "네트워크 예외니까 OSError로 잡히겠지"라는 가정이, 라이브러리가 재포장하는 순간 깨진 것이다. 라이브러리가 예외를 어떤 타입으로 감싸서 던지는지는 문서를 읽는 것만으로는 확신할 수 없고, 실제로 장애를 일으켜 traceback을 봐야 확인된다는 게 이 실험의 결론이다.

## 실험 2: models 디렉토리 권한을 없애기 — exit 0으로 끝나던 버그

`models/` 쓰기 권한을 없앤 채로 `torch.save()`를 실행했다. 권한 문제(`EACCES`)가 발생했는데, 이번에도 `torch.save` 내부에서 `RuntimeError`로 재포장돼 올라왔다.

문제는 위 `except OSError` 분기가 `return`만 쓰고 끝난다는 것이었다. `return`은 `None`을 돌려주고, `sys.exit(main())`은 결국 `sys.exit(None)` — exit code 0이다. 저장에 실패했는데 프로세스는 성공으로 종료된 것이다. CI였다면 파이프라인이 계속 초록불이었을 거고, cron이었다면 실패가 하루 종일 조용히 반복됐을 것이다.

> 🖼️ **[사진 2]** 저장 실패 직후 `echo $?`가 0을 찍은 터미널 — 로그엔 에러가 있는데 exit code는 성공인 상태
> → 업로드: `2. eacces-exit0-terminal.png`

수정은 `return`을 `return 1`로 바꾸고, 두 실험에서 확인한 재포장 사실을 반영해 잡는 예외 타입을 넓히는 것이었다.

```python
except (OSError, RuntimeError) as e:
    logger.error("파일/네트워크 I/O 실패: %s", e)
    return 1
```

## 실험 3: --device 플래그 — silent fallback과 fail-fast

`--device` 옵션의 첫 버전은 `--device cuda`를 줘도 GPU가 없으면 검사 없이 조용히 CPU로 넘어가는 구조였다. 겉으로는 잘 도는 것처럼 보이지만, GPU에서 돌리는 줄 알고 있던 작업이 실제로는 CPU에서 느리게 돌아가고 있어도 아무 신호가 없다. 요청한 조건이 충족되지 않았는데 다른 경로로 조용히 넘어가 실패를 감추는 이런 패턴을 silent fallback이라고 부른다. 인프라 코드에서는 위험한 패턴이다. 문제가 있어도 겉으로는 정상처럼 보여서, 나중에야 그것도 다른 사람이 먼저 눈치채게 되기 때문이다.

수정 과정에서 실수도 했다. `argparse` 쪽에 오타를 낸 채로 직접 실행해보지 않고 리뷰만 요청했다가, 실행 자체가 즉시 죽는 걸 놓쳤다. 코드를 고치면 항상 직접 돌려보고 넘겨야 한다는 걸 다시 확인했다.

최종 코드는 `cuda`를 요청했는데 실제로 쓸 수 없으면 그 자리에서 바로 예외를 던진다.

```python
if requested == "cuda" and not torch.cuda.is_available():
    raise ValueError("cuda 요청됐지만 이 환경엔 CUDA 없음")
```

이게 fail-fast다. 조건을 만족시킬 수 없으면 그 즉시 가장 이해하기 쉬운 형태로 실패시키는 방식이다. `main()`에서도 이 예외를 받아 exit code 1로 종료하도록 연결하고, `auto`/`cpu`/`cuda`와 GPU 있음/없음 조합을 전부 돌려 각각 기대한 exit code로 끝나는지 확인했다.

## 정리

결국 하나로 모인다. exit code는 쉘, CI, cron, 쿠버네티스가 성공과 실패를 구분하는 유일한 신호이고, 그 신호는 코드 안에서 조용히 뒤틀릴 수 있다 — `return`만 쓰고 끝나는 분기, 라이브러리가 예외를 다른 타입으로 감싸 던지는 동작, 검사 없이 다른 경로로 넘어가는 fallback 모두 같은 종류의 위험이다. 코드를 읽는 것만으로는 라이브러리가 예외를 어떻게 재포장하는지 알 수 없었고, Wi-Fi를 끄고 권한을 지워보는 식으로 직접 장애를 만들어야 확인이 됐다. 다음은 Linux 기본기 쪽인데, 여기서도 "실행해서 성공처럼 보인다"와 "실제로 의도한 대로 됐다"를 구분하는 습관을 계속 가져가려고 한다.
