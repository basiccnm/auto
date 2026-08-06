// 블랙알리오 치킨편 판 데이터 (2026-08-03)
// 🔴 축은 **소스 1,350원이 나머지 셋(1,174원)보다 비싸다**는 것.
import { EP, cost, ratio, chickenPct, rest } from "./card_puradak";

export const PAGES = [
  {
    kind: "rows",
    lead: "재료값을 더해보면",
    rows: [["생닭 한 마리", "6,000원", true]],
    box: `닭이 재료값의 ${chickenPct}%`,
  },
  {
    // 🔴 사장이 「시그니처 소스」로 자랑하는 지점. 뒤에서 1,174원으로 뒤집힌다
    kind: "rows",
    lead: "블랙알리오소스",
    rows: [["소스 180g", "1,350원", false]],
    box: `나머지 셋 다 합쳐 ${rest}원`,
  },
  {
    kind: "rows",
    lead: "파우더·치킨무·식용유",
    rows: [["치킨파우더 200g", "470원", false], ["치킨무 · 식용유", "704원", false]],
  },
  { kind: "reveal", sell: EP.sell, cost, ratio, box: `원가율 ${ratio}%` },
  {
    // 🔴 마무리를 시세 정보로 바꿨다(2026-08-03 대표 지시). 07-27→08-03 재조회로
    //    확인한 값 — 같은 상품이 일주일 새 4,800→6,000원(+25%).
    kind: "insight",
    big1: "닭값 4,800원",
    big2: "→ 6,000원",
    sub: "일주일 새 25% 올랐다",
  },
];
