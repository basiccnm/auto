// 빙수편 판 데이터 (2026-07-25)
// 🔴 여성향 톤 — 흰 카드 + 코럴 강조. 재료는 큰 덩어리로만(빙수는 공개 배합이 없다)
// 🔴 숫자는 **도매(매장 매입) 기준**이다(2026-07-25). 소매로 바꾸면 여기 전부 다시 써야 한다.
import { EP, cost, ratio } from "./card_bingsu";

export const PAGES = [
  {
    kind: "rows",
    lead: "재료값을 더해보면",
    rows: [["큐브치즈", "1,496원", true], ["우유", "1,200원", true]],
    box: "이 둘이 벌써 59%",
  },
  {
    kind: "rows",
    lead: "나머지 재료",
    rows: [
      ["망고퓨레", "915원", false],
      ["냉동망고", "558원", false],
      ["연유", "189원", false],
      ["바닐라 아이스크림", "176원", false],
    ],
  },
  { kind: "reveal", sell: EP.sell, cost, ratio, box: "원가율 31%" },
  {
    kind: "insight",
    big1: "빙수는",
    big2: "나눠 먹는 게 남아요",
    sub: "1인분 값으로 둘이 먹으면 절반",
  },
];
