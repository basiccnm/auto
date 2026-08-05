// 앱 웹뷰 사이트에서 **탭을 눌러가며** 메뉴판 전체를 뽑는다. 2026-07-28
//
// 🔴 왜 브라우저 JS 인가
//    Nuxt·Next 같은 SPA 는 탭 전환이 **클라이언트 라우팅**이라
//    헤드리스 `--dump-dom` 으로는 **첫 탭만** 받는다(설빙 146개 중 13개만 나왔다).
//    탭을 실제로 눌러야 하므로 브라우저에서 돌린다.
//
// 쓰는 법: 브라우저로 대상 페이지를 연 뒤 이 코드를 실행하고,
//          결과(이름\t가격)를 `scripts/brand_webview_apply.py` 로 넘긴다.
//
// ⛔ 주소를 추측하지 않는다. 앱 APK 의 `assets/app.config` 등에 적힌 `WEBVIEW_URL` 만 쓴다.
//    설빙: "WEBVIEW_URL": "https://sapp.sulbing.com"  →  /menu

(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // 탭 이름은 브랜드마다 다르다 — 화면에서 «잎 노드 + 짧은 글자» 를 후보로 본다.
  const TAB_HINT = window.__TABS__ || [];
  const tabs = [...document.querySelectorAll('*')].filter(
    (e) => !e.children.length && TAB_HINT.includes(e.textContent.trim())
  );

  const price = {}, order = [];
  const grab = () => {
    const W = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const L = [];
    while (W.nextNode()) {
      const v = W.currentNode.nodeValue.trim();
      if (v) L.push(v);
    }
    for (let i = 0; i < L.length; i++) {
      const m = L[i].match(/^([0-9]{1,3}(?:,[0-9]{3})+)\s*원$/);
      if (!m) continue;
      // 가격 바로 위 3줄 안에서 이름을 찾는다. NEW·BEST 뱃지는 건너뛴다.
      for (let j = i - 1; j >= Math.max(0, i - 3); j--) {
        const nm = L[j];
        if (/^(NEW|BEST|HOT|품절)$/.test(nm) || /원$/.test(nm)) continue;
        if (nm.length > 1 && nm.length < 34) {
          if (!(nm in price)) { price[nm] = +m[1].replace(/,/g, ''); order.push(nm); }
          break;
        }
      }
    }
  };

  grab();                                   // 첫 탭
  for (const t of tabs) { t.click(); await sleep(1400); grab(); }

  return order.map((n) => n + '\t' + price[n]).join('\n');
})();
