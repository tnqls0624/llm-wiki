---
name: blog-publish
description: blog/<slug>/ 초안을 Tistory 글쓰기 에디터에 반자동으로 올린다. 사용자가 "블로그 올려줘", "티스토리에 올려줘", "이 글 올려줘", "블로그 발행 준비" 등을 말하면 aside-browser(`aside repl`)로 제목·본문을 마크다운 모드에 입력하고 이미지 자리에 위치 마커를 남긴 뒤 **임시저장까지만** 한다. 이미지 첨부와 최종 발행(공개)은 사용자가 직접 — 자동화하지 않는다. 대화형 전용 — 무인 cron 연결 금지.
---

# blog-publish — Tistory 반자동 게시 (임시저장까지)

`blog-collect.py`가 만든 발행 본문(`blog/<slug>/<slug>.blog.md`)을 Tistory 글쓰기 에디터에 넣고 **임시저장**한다. 여기까지가 이 스킬의 전부다. **이미지 첨부·최종 발행은 사용자 몫**이며 자동화하지 않는다(automation-safety: 발행은 사용자 승인 후).

브라우저 계층은 **aside-browser**다(2026-08-22 이관). claude-in-chrome은 비활성화됐으므로 그 경로를 되살리려 하지 말 것 — 이 vault의 브라우저 자동화는 Aside로 통일한다.

## 경계 (불변식 — 넘지 않는다)
- **임시저장까지만.** "완료"/"발행"/"공개" 버튼은 **누르지 않는다.** 검토·발행은 사용자가 직접.
- **이미지는 첨부하지 않는다.** Tistory 이미지 업로드는 OS 네이티브 파일 선택창을 거쳐 브라우저 자동화로 파일을 주입할 수 없다. 드래그-드롭·붙여넣기 이벤트도 에디터가 처리하지 않는다(검증됨 2026-07-08). `window.confirm`/파일 선택 API를 우회하는 JS 주입은 **하지 않는다**(보안 약화 — 자동 승인 분류기가 차단하며, 그게 옳다). 본문에는 이미지가 들어갈 자리에 **텍스트 위치 마커**만 남기고, 첨부는 사용자가 에디터에서 수행한다.
- **대화형 전용.** 이 스킬은 어떤 cron 래퍼에도 연결하지 않는다. 브라우저·로그인 세션은 사용자 것이다.
- **확인 대화상자를 자동 승인하지 않는다.** `page.on('dialog', …)` 자동 수락 핸들러를 **등록하지 말 것**. 모드 변경 확인창이 뜨면 사용자에게 Aside 브라우저 창에서 직접 눌러달라고 요청한다.

## 입력
- `blog/<slug>/<slug>.blog.md` (발행 본문). 없으면 먼저 `python3 .claude/blog-collect.py blog/<slug>/<slug>.md` 로 만든다.
- 본문의 `[사진 N]` 플레이스홀더와 `blog/<slug>/SOURCES.md`의 상태(다운로드됨/대기)를 읽어 **어떤 이미지가 준비됐고 어떤 게 아직 없는지** 파악한다. 대기(`shot`) 이미지가 있으면 그대로 마커로 남기고 마지막에 대기 목록을 보고한다.

## 절차 (aside repl)

`aside repl`은 Playwright 호환 API + `fs`·`page.evaluate(fn, arg)`를 준다. **본문을 인자로 직접 넘길 수 있으므로 예전의 로컬 HTTP 서버 + CORS `fetch()` 우회는 불필요하다.** TTY에서 `aside repl`을 띄워 아래를 단계별로 실행한다(각 액션 후 새 `snapshot`).

**1. 탭 확보.** 이미 Tistory 글쓰기 탭이 열려 있을 수 있으니 먼저 조회한다.
```js
const openTabs = await listBrowserTabs();
console.log(openTabs.map(t => ({ targetId: t.targetId, active: t.active, url: t.url })));
```
`/manage/newpost/` 탭이 있으면 `attachBrowserTab(targetId)`, 없으면 `openTab('https://<블로그>.tistory.com/manage/newpost/')`. 로그인은 사용자 Aside 세션을 그대로 쓴다.

**2. 마크다운 모드로 전환.** 새 글은 매번 **기본모드**로 열린다. 우상단 모드 드롭다운 → 마크다운.
```js
const s1 = await snapshot(page, { interactive: true });
console.log(s1.tree);
```
ref로 드롭다운·마크다운 항목을 클릭한다. "작성 모드를 변경하시겠습니까?" 확인창이 뜨면(간헐적) **자동 승인하지 말고** 사용자에게 요청한다. 전환 후 툴바가 마크다운(제목1/코드 등)으로 바뀐 것을 `annotatedScreenshot(page)`로 확인한다.

**3. 본문 주입 — 합성 타이핑 대신 정확 주입** (2026-07-08 검증: `type` 계열은 한글 자모를 간헐적으로 깨뜨린다 — 쉘→쉐, 끊기면→끕기면).
```js
const raw = await fs.readFile('blog/<slug>/<slug>.blog.md', 'utf8');
// 제목 줄과 "## 준비할 이미지" 블록을 떼어낸 본문만 남긴다
const title = raw.match(/^#\s+(.*)$/m)[1].trim();
const body  = raw.replace(/^#\s+.*$/m, '').split('## 준비할 이미지')[0].trim();

const injected = await page.evaluate((b) => {
  // 페이지에 CodeMirror가 2개다 (검증 2026-07-10):
  //   .cm-s-tistory-html (숨김) + .cm-s-tistory-markdown (표시)
  // document.querySelector('.CodeMirror') 는 숨겨진 HTML 쪽을 잡는다 — 반드시 markdown 인스턴스.
  const el = document.querySelector('.CodeMirror.cm-s-tistory-markdown');
  if (!el || !el.CodeMirror) return { ok: false };
  el.CodeMirror.setValue(b);
  return { ok: true, height: el.offsetHeight, len: el.CodeMirror.getValue().length };
}, body);
console.log(injected);   // height 가 수백 px로 커졌는지 = 화면 렌더 확인
```
`[사진 N]` 콜아웃은 그대로 둔다 — Tistory가 `\[사진 N\]`으로 자동 이스케이프해도 렌더는 정상이다.

**4. 제목 주입 — 반드시 실제 입력 이벤트.** JS `.value = …` 직접 대입은 화면에만 보이고 Tistory 앱 상태에 등록되지 않아 **저장 시 빈 제목으로 날아간다**(검증됨).
```js
await page.locator('#post-title-inp').click();
await page.keyboard.insertText(title);   // insertText = 키 이벤트 없이 실제 input 이벤트 → 한글 안전
const got = await page.locator('#post-title-inp').inputValue();
console.log({ title, got, match: got.trim() === title });
```
`insertText`가 안 먹으면 `page.locator('#post-title-inp').fill(title)`로 재시도한다. `keyboard.type()`은 키 이벤트를 하나씩 보내 한글이 깨질 수 있으므로 쓰지 않는다.

**5. 본문 대조.** `el.CodeMirror.getValue()`를 원본과 비교한다. Tistory의 `\[ \]` 이스케이프·trailing space·리스트 마커 간격 정규화는 무시한다.

**6. 임시저장.** 하단 임시저장 클릭 → "작성 중인 글이 저장되었습니다" 배너 + 임시저장 카운트 증가를 새 `snapshot`의 `diff`와 스크린샷으로 확인한다. (드롭다운 `임시저장` 배지를 누르면 저장된 초안 목록이 떠서 특정 초안을 다시 불러올 수 있다.)

**7. 여기서 멈춘다.** 발행하지 않는다.

## 출력 (사용자에게 보고)
- **발행 상태 기록(2026-08-23)**: 임시저장 성공 직후 `blog/<slug>/SOURCES.md` **맨 위에** `> 발행상태: temp-saved <YYYY-MM-DD>` 한 줄을 추가/갱신한다(이미 있으면 그 줄만 교체). 사용자가 발행을 마쳤다고 알려주면 `> 발행상태: published <YYYY-MM-DD> <URL>`로 갱신 — 초안 9개의 발행 여부 기록이 0이던 문제의 소유처는 이 파일이다.
- 임시저장 성공 여부 + 스크린샷.
- **남은 수동 작업 목록**: 각 `[사진 N]` 마커별로 (a) 첨부할 파일 절대경로(`blog/<slug>/N. 파일명.png`), (b) 아직 캡처 안 된 `shot` 이미지가 있으면 무엇을 찍어야 하는지.
- 마지막 안내: 사용자가 각 마커 자리에서 툴바 사진 버튼으로 파일 첨부 → 마커 줄 삭제 → 검토 후 발행.

## 참고
- 이미지 수집·발행 본문 생성은 `blog-collect.py`(메인 세션), 초안 작성은 `soobeen-voice` 에이전트 몫. 이 스킬은 "완성된 발행 본문을 에디터에 올리는" 마지막 단계만 담당한다.
- 브라우저 자동화가 2~3회 반복 실패하면 중단하고 사용자에게 상황을 보고한다. Aside 쪽 실패 신호: `listBrowserTabs()`가 빈 배열(브라우저 미실행), `snapshot`에 로그인 화면(세션 만료), `page.evaluate`가 `{ok:false}`(에디터 미로드 또는 셀렉터 변경).
- `aside repl`은 프로세스가 죽으면 세션도 사라진다. 한 번의 REPL 세션 안에서 1~7단계를 마치고, 변수는 `const s1`, `const s2`처럼 새 이름을 쓴다(top-level 바인딩이 세션 내에서 유지된다).
