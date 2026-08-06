// 엽기떡볶이 엽기로제 원가 — 이거 얼마남아 3 (2026-07-26)
//
// 🔴 **도매(매장 매입) 기준**이다. DB menus.store_cost / menu_ingredients.wholesale_cost 와 같다.
//    소매로 바꾸지 않는다 — 영상과 사이트가 다른 숫자를 보이면 안 된다.
//
// 🔴 이 편의 발견: **떡볶이인데 떡보다 소스가 2.4배 비싸다.**
//    떡볶이 분말 1,540원 vs 밀떡 648원. 이게 훅이고 인사이트다.
//
// 🔴 메뉴를 바꾸려면 여기 EP 만 갈아끼우면 된다(마라떡볶이 16,000/4,066 · 오리지널 14,000/3,704).
export const EP = {
  series: "이거 얼마남아",
  ep: 3,
  brand: "엽기떡볶이",
  title: "엽기로제",
  cond: "2~3인분 · 무옵션",
  site: "olmanama.com",

  sell: 16000,

  // DB menu_ingredients.wholesale_cost 그대로 (합 4,244)
  items: [
    ["떡볶이 분말", 1540],
    ["밀떡", 648],
    ["휘핑크림", 540],
    ["모차렐라 치즈", 499],
    ["사각 어묵", 385],
    ["봉어묵", 296],
    ["비엔나 소시지", 256],
    ["대파", 52],
    ["양배추", 28],
  ],
};

export const cost = EP.items.reduce((a, [, c]) => a + c, 0); // 4,244
export const ratio = Math.round((cost / EP.sell) * 100); // 27

// 소스 + 떡이 재료값의 몇 %인가 (스토리용)
export const bigTwo = EP.items[0][1] + EP.items[1][1]; // 2,188
export const bigTwoPct = Math.round((bigTwo / cost) * 100); // 52

export { TONE } from "./tone";
