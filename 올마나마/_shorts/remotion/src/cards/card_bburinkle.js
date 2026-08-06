// bhc 뿌링클 원가 — 이거 얼마남아 4 (2026-07-27)
//
// 🔴 **도매(매장 매입) 기준.** DB menus.store_cost / menu_ingredients.wholesale_cost 와 같다.
//
// 🔴 이 편의 축: **생닭 한 마리가 재료값의 70%.** 나머지 다 합쳐도 2,183원이다.
//    치킨 원가는 결국 닭값이라는 게 숫자로 나온다.
//
// 🔴 다음 편(집에서 뿌링클 초간단 레시피)으로 이어진다 — 마무리에서 예고한다.
//    원가를 보고 "비싸네" 한 사람에게 다음 날 해결책을 주는 구조다.
export const EP = {
  series: "이거 얼마남아",
  ep: 4,
  brand: "bhc",
  title: "뿌링클",
  cond: "한 마리 · 무옵션",
  site: "olmanama.com",
  next: "초간단 뿌링클 레시피",

  sell: 21000,

  // DB menu_ingredients.wholesale_cost 그대로 (합 7,163)
  items: [
    ["생닭 한 마리", 4980],
    ["튀김파우더", 915],
    ["식용유", 421],
    ["치킨무", 353],
    ["뿌링클 시즈닝", 350],
    ["디핑소스", 144],
  ],
};

export const cost = EP.items.reduce((a, [, c]) => a + c, 0); // 7,163
export const ratio = Math.round((cost / EP.sell) * 100); // 34

// 생닭이 재료값의 몇 %인가 (이 편의 스토리)
export const chickenPct = Math.round((EP.items[0][1] / cost) * 100); // 70

export { TONE } from "./tone";
