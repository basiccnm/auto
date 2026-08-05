# 아이콘 폰트 (자동 생성물 — 손대지 말 것)

`tabler-subset.woff2` · `tabler-subset.css` 는 **스크립트가 만든 파일**이다.
직접 고치면 다음 빌드에서 덮어써진다.

## 왜 서브셋인가
폰 앱은 오프라인이고 CSP가 외부 CDN을 막는다 → 폰트를 앱 안에 넣어야 한다.
그런데 Tabler 전체는 woff2 **857KB** + CSS 236KB다. 우리가 쓰는 건 **51개**뿐이라 잘라 넣는다.

| | 전체 | 우리 것 |
|---|---|---|
| woff2 | 857KB | **11KB** |
| css | 236KB | 3KB |

## 다시 만드는 법
아이콘을 **새로 쓰기 시작했으면** 반드시 다시 돌린다. 안 그러면 그 아이콘만 안 보인다.

```
cd app
node tools/build-icons.mjs
```

준비물(한 번만): `npm i @tabler/icons-webfont@3.24.0` · `pip install fonttools brotli`

스크립트가 `www/{app.js,index.html,style.css}`에서 `ti-…` 를 전부 긁어
그 글자만 남긴 폰트와 그 클래스만 있는 CSS를 만든다.
이름을 틀리게 적은 아이콘은 실행할 때 `⚠ 이름이 틀렸거나 없는 아이콘`으로 알려준다.

## 확인하는 법
브라우저 콘솔에서 — 쓰는 아이콘은 폭이 나오고, 안 넣은 아이콘은 0이다.

```js
const e = document.createElement("i"); e.className = "ti ti-bowl";
e.style.fontSize = "40px"; document.body.appendChild(e);
e.getBoundingClientRect().width;   // 40 = 정상, 0 = 폰트에 없음
```

출처: [@tabler/icons-webfont](https://tabler.io/icons) 3.24.0 (MIT)
