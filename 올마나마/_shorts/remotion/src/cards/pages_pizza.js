// 도미노 포테이토 피자 원가편 — 판(화면) 데이터 (2026-07-24)
//
// 🔴 kind 별로 판 모양이 다르다:
//    rows   = 재료 원가 쌓기 (이름·금액 목록)
//    reveal = 원가 공개 (판매가 vs 총원가 큰 숫자 대비)
//    insight= 인사이트 한 문장 (할인 강한 이유)
// 🔴 상시 자막 "원재료 기준 원가" 는 모든 판 하단에 자동으로 박힌다(PizzaPage에서).
import { EP, cost, ratio } from "./card_pizza";

const won = (n) => n.toLocaleString("ko-KR");

export const PAGES = [
  {
    // 0 — 치즈·도우가 절반
    kind: "rows",
    lead: "재료 원가",
    rows: [
      ["모차렐라 치즈", "1,306원", true],
      ["도우", "1,013원", true],
    ],
    box: "이 둘이 벌써 원가의 55%",
  },
  {
    // 1 — 나머지 재료 (베이컨 원산지 태그)
    kind: "rows",
    lead: "나머지 토핑",
    rows: [
      ["베이컨 (외국산)", "533원", false],
      ["감자", "372원", false],
      ["토마토소스", "311원", false],
      ["양파·버섯·옥수수·마요", "695원", false],
    ],
    box: "다 합쳐도 얼마 안 됨",
  },
  {
    // 2 — 원산지 (팩트 강조)
    kind: "insight",
    big1: "베이컨은",
    big2: "외국산 돼지고기",
    sub: "도미노 공식 원산지 표시",
  },
  {
    // 3 — 원가 공개 (정점)
    kind: "reveal",
    sell: EP.sell,
    cost: cost,
    ratio: ratio,
    box: "넉넉히 잡아도 원가율 15%",
  },
  {
    // 4 — 인사이트 (소비자 이득)
    kind: "insight",
    big1: "원가율 15%니까",
    big2: "만 원 깎아도 남아",
    sub: "그래서 피자는 늘 세일합니다",
  },
];
