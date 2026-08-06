// 삼계탕편 판 데이터 (2026-08-03)
// 🔴 축은 **닭+티백 둘이 92%**. 나머지 넷을 다 더해도 480원.
import { EP, cost, ratio, chickenPct, rest } from "./card_samgye";

export const PAGES = [
  {
    kind: "rows",
    lead: "재료값을 더해보면",
    rows: [["삼계탕용 영계 한 마리", "4,280원", true]],
    box: `닭이 재료값의 ${chickenPct}%`,
  },
  {
    // 🔴 사장이 「한방 재료가 얼만데요!」로 발끈하는 지점. 티백 하나가 나머지 넷보다 두 배다
    kind: "rows",
    lead: "한방 티백 (인삼·황기·대추)",
    rows: [["삼계탕재료 100g", "1,100원", false]],
    box: "나머지 넷 다 합쳐 480원",
  },
  {
    kind: "rows",
    lead: "밤·마늘·쌀·대파",
    rows: [["당침당밤조림 · 깐마늘", "308원", false], ["쌀 · 대파", "172원", false]],
  },
  { kind: "reveal", sell: EP.sell, cost, ratio, box: `원가율 ${ratio}%` },
  {
    // 🔴 마무리를 시세 정보로 바꿨다(2026-08-03 대표 지시). 전국 평균 닭고기 6월
    //    kg당 6,650원, 작년 동월(5,568원) 대비 19.4%↑ — AI 살처분·폭염 여파.
    kind: "insight",
    big1: "닭고기 19% ↑",
    big2: "작년 이맘때보다",
    sub: "AI 여파 · 폭염에 보양식 수요까지 겹쳤다",
  },
];
