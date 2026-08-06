// 순대국편 판 데이터 (2026-07-30) — 🔴 브랜드 이름 금지, 일반 순대국 기준
// 🔴 이 편의 축은 **순대국인데 순대가 제일 싸다**는 것이다.
//    머리고기 767 · 내장 644 · 순대 425.
// 🔴 양파는 뺐다 — 순대국에 안 들어간다. 쌀(밥)은 넣는다.
import { EP, cost, ratio, meatPct } from "./card_keunmam";

export const PAGES = [
  {
    kind: "rows",
    lead: "건더기부터 더해보면",
    rows: [["머리고기 65g", "767원", true], ["내장 65g", "644원", false], ["순대 5개", "425원", false]],
    box: `건더기 210g 이 재료값의 ${meatPct}%`,
  },
  {
    kind: "rows",
    lead: "나머지 재료",
    rows: [["사골육수 40g", "540원", true], ["쌀 100g", "240원", false], ["깍두기", "164원", false], ["채소·양념", "214원", false]],
  },
  { kind: "reveal", sell: EP.sell, cost, ratio, box: `원가율 ${ratio}%` },
  {
    kind: "insight",
    big1: "순대국인데",
    big2: "순대가 제일 싸다",
    sub: "머리고기 767 · 내장 644 · 순대 425",
  },
];
