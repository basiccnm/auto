// 데리버거편 판 데이터 (2026-08-02 · 재업)
//
// 🔴 이 편의 축은 **1988년부터 38년, 900원 → 3,800원**. 값은 4배인데 크기는 제일 작다.
//    ⚠️ 그 이야기를 **절정 앞**에 둔다(판 2·3). 뒤에 붙이면 이미 나간 뒤다(대표 지적).
//
// 🔴 **g 을 쓰지 않는다.** 우리는 롯데리아 배합·중량을 모른다. 공식 총중량 134g 에 맞춰
//    식봄 최저가로 구성했을 때의 값이다. 그램을 적으면 «롯데리아가 이만큼 넣는다» 가 된다.
//
// 🔴 판 순서 = 대사의 `page:` 인덱스. lines_deri.js 와 어긋나면 화면이 헛돈다.
//    0 패티 / 1 나머지 재료 / 2 38년 역사 / 3 크기 / 4 원가공개
import { EP, cost, ratio, since, years, firstPrice } from "./card_deri";

export const PAGES = [
  {
    kind: "rows",
    lead: "제일 비싼 것부터",
    rows: [["패티", "487원", true]],
  },
  {
    // 🔴 다섯 개 **전부 금액을 붙인다**(대표 지시). 뭉개면 원가를 다루는 채널이 대충 말하는 꼴이다
    kind: "rows",
    lead: "나머지 재료",
    rows: [["빵", "450원", false], ["양상추", "59원", false],
           ["소스", "38원", false], ["양파", "6원", false]],
  },
  {
    kind: "rows",
    lead: `${since}년부터 ${years}년`,
    rows: [["그때", `${firstPrice.toLocaleString("ko-KR")}원`, false],
           ["지금", `${EP.sell.toLocaleString("ko-KR")}원`, true]],
    box: "38년 만에 4배",
  },
  {
    kind: "insight",
    big1: "값은 4배인데",
    big2: "크기는 제일 작다",
    sub: "롯데리아 버거 중 가장 작은 버거",
  },
  { kind: "reveal", sell: EP.sell, cost, ratio, box: `원가율 ${ratio}%` },
];
