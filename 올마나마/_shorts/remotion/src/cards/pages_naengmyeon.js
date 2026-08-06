// 물냉면편 판 데이터 (2026-08-03, 재료 정정 2026-08-05, 순서 재구성 2026-08-05)
// 🔴 축이 바뀌었다 — **육수 680원이 재료값의 37%로 단독 1위.** "물"냉면인데
//    물(육수)이 제일 비싸다는 게 새 반전(`card_naengmyeon.js` 주석 참고).
// 🔴 **순서 재구성**(대표 지적 — *"양지를 뒤로 빼야지"*) — 육수가 주인공이라
//    오프닝으로 올리고, 이제 제일 싼 축인 소고기는 냉면사리와 묶어 반전 자리로.
import { EP, cost, ratio, brothPct, rest } from "./card_naengmyeon";

export const PAGES = [
  {
    kind: "rows",
    lead: "재료값을 더해보면",
    rows: [["냉면육수 500ml", "680원", true]],
    box: `육수가 재료값의 ${brothPct}%`,
  },
  {
    kind: "rows",
    lead: "냉면사리·소고기양지",
    rows: [["냉면사리 200g", "397원", false], ["소고기양지 25g", "376원", false]],
  },
  {
    kind: "rows",
    lead: "계란·오이·무",
    rows: [["계란 1개", "282원", false], ["오이 50g", "90원", false], ["무 50g", "27원", false]],
    box: `셋 다 합쳐 ${rest}원`,
  },
  { kind: "reveal", sell: EP.sell, cost, ratio, box: `원가율 ${ratio}%` },
  {
    kind: "insight",
    big1: "냉면육수 680원",
    big2: "냉면사리 397원",
    sub: "물냉면인데 육수가 제일 비싸요",
  },
];
