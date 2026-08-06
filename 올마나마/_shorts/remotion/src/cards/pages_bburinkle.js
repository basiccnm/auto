// 뿌링클편 판 데이터 (2026-07-27)
// 🔴 여성향 톤 — 흰 카드 + 코럴 강조. 글씨는 검정(파스텔 금지).
// 🔴 숫자는 **도매(매장 매입) 기준**이다.
// 🔴 이 편의 축: 생닭이 재료값의 70%. 판 ①이 그걸 바로 보여준다.
import { EP, cost, ratio, chickenPct } from "./card_bburinkle";

export const PAGES = [
  {
    kind: "rows",
    lead: "재료값을 더해보면",
    rows: [["생닭 한 마리", "4,980원", true], ["튀김파우더", "915원", true]],
    box: `닭 한 마리가 재료값의 ${chickenPct}%`,
  },
  {
    kind: "rows",
    lead: "나머지 재료",
    rows: [
      ["식용유", "421원", false],
      ["치킨무", "353원", false],
      ["뿌링클 시즈닝", "350원", false],
      ["디핑소스", "144원", false],
    ],
  },
  { kind: "reveal", sell: EP.sell, cost, ratio, box: `원가율 ${ratio}%` },
  {
    kind: "insight",
    big1: "치킨 원가는",
    big2: "닭값이 전부예요",
    sub: "나머지 다 합쳐도 2,183원",
  },
];
