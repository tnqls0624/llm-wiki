요즘 AI 인프라 공부를 시작하면서 PyTorch 기초를 다지고 있습니다. 예제를 복붙하는 대신 MNIST 손글씨 숫자를 분류하는 학습 스크립트를 처음부터 직접 작성해봤습니다. 함수 뼈대만 있는 파일을 채워나가다 두 번 스스로 버그를 냈는데, 고치는 과정에서 Dataset과 DataLoader가 왜 분리돼 있는지, batch size가 실제로 뭘 바꾸는지가 훨씬 선명해졌습니다.

## Dataset과 DataLoader란?

MNIST는 손글씨 숫자 이미지 7만 장짜리 데이터셋이다. `torchvision.datasets.MNIST`로 내려받으면 나오는 `Dataset` 객체는 "전체 데이터 묶음 + 인덱스로 하나씩 꺼내는 방법"만 정의한 것이다. 실제 학습 루프가 쓰는 건 이걸 감싼 `DataLoader`다. 쉽게 말해 Dataset은 재료 창고, DataLoader는 정해진 양만큼 꺼내 순서대로 배달하는 역할이다. DataLoader가 배치 단위로 자르고 epoch마다 섞어(shuffle)준다.

> 🖼️ **[사진 1]** MNIST 손글씨 숫자 샘플 — 이 이미지 7만 장이 학습 재료다
> → 업로드: `1. mnist-examples.png`

이 구분을 몰랐을 때 실제로 버그를 냈다. `load_data` 함수의 반환문을 처음엔 이렇게 썼다.

```python
return tuple(train_ds, test_ds);
```

`tuple()`은 iterable 하나만 받는데 두 개를 넘겨서 TypeError가 났다. 콤마로 묶으면 되는 걸 `tuple()` 호출로 착각한 것이다. `return train_ds, test_ds;`로 고쳤는데, 이러면 여전히 `Dataset`을 그대로 반환하는 문제가 남는다. DataLoader로 감싸는 코드는 있었지만 이런 모양이었다.

```python
DataLoader(train_ds, batch_size=batch_size, shuffle=True);  # 변수에 담지 않고 버림
```

만들어놓고 쓰지 않은 죽은 코드였다. 학습 루프는 배치도 셔플도 안 된 원본 Dataset을 통째로 받고 있었다. 최종적으로는 이렇게 정리했다.

```python
train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)
return train_loader, test_loader
```

train은 매 epoch마다 순서를 섞어야 편향이 없고, test는 평가용이라 `shuffle=False`로 뒀다.

## 모델 구조 — 28x28 이미지를 숫자로 바꾸는 계산

모델은 `Flatten → Linear(784,128) → ReLU → Linear(128,10)` 순서로 쌓았다. Flatten이 28x28 이미지를 784차원 벡터로 펼치고, 첫 Linear가 784차원을 128개 출력으로 바꾼 뒤 ReLU로 비선형성을 넣고, 마지막 Linear가 숫자 0~9 클래스 점수 10개로 바꾼다.

이 `Linear` 계층의 계산이 y = wx + b다. 고등학교 때 배운 일차방정식과 구조가 같은데, 텐서 위에서는 x가 입력 데이터, w가 가중치(weight), b가 편향(bias, 항상 더해지는 값)이고, 스칼라가 아니라 행렬·벡터라는 점만 다르다. `Linear(784, 128)`은 784차원 x에 128x784 가중치 행렬 w를 곱하고 128차원 편향 b를 더해 128차원을 만든다.

## 학습 루프의 5단계

```python
opt.zero_grad()                        # ① 기울기 초기화
loss = loss_fn(model(x), y)            # ② forward + 손실 계산
loss.backward()                        # ③ backward
opt.step()                             # ④ 가중치 갱신
logger.info("loss=%.4f", loss.item())  # ⑤ 기록
```

① zero_grad는 이전 배치의 기울기를 지운다 — PyTorch는 기울기를 누적하는 구조라 안 지우면 계속 더해진다. ② forward + loss는 입력으로 예측값을 얻고 정답과 비교해 손실을 계산한다. ③ backward는 손실 기준으로 각 파라미터의 기울기를 역전파로 계산한다. ④ step은 그 기울기 방향으로 옵티마이저가 실제 가중치를 갱신한다. ⑤ 로그는 epoch 단위 손실을 기록해 학습이 진행되는지 확인한다. 이 5단계는 프레임워크가 뭐든 뼈대가 똑같다.

## batch size는 "속도"가 아니라 "갱신 횟수"를 정한다

MNIST 학습 데이터는 6만 장이고, 6만 장을 한 번 다 쓰는 게 1 epoch다. 한 번에 다 넣을 수 없으니 batch size만큼씩 잘라 여러 번(iteration) 나눠 넣는데, iteration 수는 전체 데이터 수를 batch size로 나눈 값이다.

`--batch-size 64`와 `256`으로 각각 돌려서 비교했다.

- batch 64: 60000 ÷ 64 ≈ **938회** 갱신
- batch 256: 60000 ÷ 256 ≈ **235회** 갱신

처리하는 데이터 총량(60000장)은 같아서 시간 차이는 크지 않았다. 대신 loss가 눈에 띄게 달랐다. batch가 작으면 가중치를 훨씬 자주(938번) 고쳐서 손실이 더 빠르게 떨어지고, batch가 클수록 갱신 기회(235번) 자체가 줄어든다. batch size는 연산 속도가 아니라 한 epoch 안에서 가중치를 몇 번 고칠지를 정하는 값이라는 걸 숫자로 확인한 셈이다.

> 🖼️ **[사진 2]** batch 64와 256으로 각각 돌렸을 때의 epoch별 loss 터미널 출력 — 갱신 횟수 차이가 loss 하강 속도로 드러난다
> → 업로드: `2. batch-loss-terminal.png`

## 모델은 왜 state_dict로 저장하는가

모델 객체 전체를 pickle로 통째로 저장할 수도 있지만, 이번엔 `state_dict`만 저장했다.

```python
torch.save(model.state_dict(), args.model_out)
m2 = SimpleNet()
m2.load_state_dict(torch.load(args.model_out))
```

`state_dict`는 계층 이름과 가중치·편향 값(텐서)만 담은 딕셔너리다. 모델 클래스 코드는 담지 않는다. 불러올 때는 같은 구조로 `SimpleNet()`을 새로 만들고 저장된 파라미터 값만 끼워 넣는다. 통째로 저장하면 클래스 정의가 pickle 안에 얽혀 들어가 코드가 조금만 바뀌어도 로드가 깨지는데, `state_dict`는 순수 데이터만 담아 클래스는 최신 소스에서, 값만 갈아 끼우는 구조라 더 안전하다. 새 인스턴스로 재로드하는 검증까지 돌렸고, 에러 없이 통과했다.

## 마무리

빈 함수를 채우면서 두 번 버그를 냈다. `tuple()` 오용, 그리고 DataLoader로 감싸놓고도 반환하지 않은 것. 둘 다 실행해서 에러를 보고 나서야 원인을 찾았는데, 그 덕에 Dataset/DataLoader 역할 차이와 batch size의 의미가 훨씬 선명하게 남았다.
