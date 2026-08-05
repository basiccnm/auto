// 브랜드 홈페이지에서 **숨은 탭까지** 메뉴를 뽑는다. 2026-07-28
//
// 🔴 왜 «가격도 이름도 없다» 고 오판했나 (버거킹 실제 사고)
//    `innerText` 는 **보이는 글자만** 준다. 탭이 여러 개인 사이트는 안 눌린 탭이
//    `display:none` 이라 innerText 가 61자로 나왔고 «홈페이지에 메뉴가 없다» 고 봤다.
//    그런데 DOM 에는 **219장이 다 들어 있었다.**
//    → **`textContent` 로 읽으면 탭을 누를 필요조차 없다.**
//
// 대표 정리(2026-07-28): *"메뉴는 별도, 금액은 따로다. 둘이 연결돼서 매장에서 보여지는 것"*
//    · 메뉴(이름·구성·이미지) = 브랜드 홈페이지
//    · 가격                  = 매장이 붙은 주문 화면(앱)
//    · 연결 고리             = 메뉴명
//
// 쓰는 법: 브라우저로 메뉴 페이지를 연 뒤 실행 → «이름\t구성\t이미지» 를 받아
//          `scripts/brand_webview_apply.py` 로 넣는다.

(() => {
  // 카드 컨테이너는 사이트마다 다르다 — 흔한 것부터 훑고, 없으면 이미지 기준으로 올라간다.
  const SEL = ['.menu_card', '.prd_item', '.goods_item', 'li.menu', '.menu-item', '.product'];
  let cards = [];
  for (const s of SEL) {
    cards = [...document.querySelectorAll(s)];
    if (cards.length >= 5) break;
  }
  if (cards.length < 5) {
    const seenBox = new Set();
    cards = [];
    document.querySelectorAll('img').forEach((im) => {
      const box = im.closest('li') || im.closest('article') || im.parentElement?.parentElement;
      if (box && !seenBox.has(box)) { seenBox.add(box); cards.push(box); }
    });
  }

  const NAME_SEL = ['.tit', '.name', '.prd_name', '.goods_name', 'h3', 'h4', 'strong'];
  const DESC_SEL = ['.set_info', '.desc', '.summary', 'p'];
  const pick = (box, sels) => {
    for (const s of sels) {
      const e = box.querySelector(s);
      // 🔴 innerText 가 아니라 textContent — 숨은 탭도 읽어야 한다
      const t = e && (e.textContent || '').replace(/\s+/g, ' ').trim();
      if (t) return t;
    }
    return '';
  };

  const seen = new Set(), out = [];
  for (const c of cards) {
    const nm = pick(c, NAME_SEL);
    if (!nm || nm.length > 40 || seen.has(nm)) continue;
    seen.add(nm);
    const desc = pick(c, DESC_SEL);
    const img = c.querySelector('img');
    out.push([nm, desc === nm ? '' : desc, img ? img.getAttribute('src') || '' : ''].join('\t'));
  }
  return out.join('\n');
})();
