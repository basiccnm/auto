// 지코바편 판 데이터 (2026-07-28)
// 🔴 이 편의 축은 **원산지**다. 순살이 1,000원 비싼데 닭값은 600원 싸다 —
//    뼈 있는 건 국산, 순살은 브라질산이라서다(2025-04 원산지 적발 뒤 전면 전환, 회사 발표).
import { EP, cost, ratio, chickenPct } from "./card_zicoba";

export const PAGES = [
  {
    kind: "rows",
    lead: "재료값을 더해보면",
    rows: [["닭다리살 800g", "4,200원", true], ["양념 소스 300g", "960원", true]],
    box: `닭값이 재료값의 ${chickenPct}%`,
  },
  {
    kind: "rows",
    lead: "나머지 재료",
    rows: [["치킨무", "353원", false], ["구이용 밀떡", "160원", false]],
  },
  { kind: "reveal", sell: EP.sell, cost, ratio, box: `원가율 ${ratio}%` },
  {
    kind: "insight",
    big1: "순살은 수입산",
    big2: "뼈 있는 건 국산",
    sub: "순살이 1,000원 비싼데 닭값은 600원 싸다",
  },
];
