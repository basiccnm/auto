// 도미노 포테이토 피자 원가편 본편 — 원가 시리즈 1 (2026-07-24)
//
// 🔴 마라탕·배달편과 같은 엔진(talk_engine). 이 파일은 화면(판)만 지정한다.
//    대사 lines_pizza.js · 숫자 card_pizza.js · 판 PizzaPage.jsx
// 🔴 판은 인스타 카드와 같은 컴포넌트(PizzaPanel)를 쓴다 — 한 소스에서 쇼츠·카드 둘 다 나온다.
import React from "react";

import { EP } from "../cards/card_pizza";
import { PizzaPanel } from "../cards/PizzaPage";
import { ThumbCard } from "../cards/ThumbPizza";
import { LEAD, LINES } from "./lines_pizza";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const PIZZA_SEC = talkSec(LINES, LEAD);

export const TalkPizza = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceP1"
    defaultBg="pizza01"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <PizzaPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} site={EP.site} ask={"피자·치킨 원가 더 궁금하면\n올마나마에서 확인하세요"} />}
      </>
    )}
    renderHook={() => <ThumbCard />}
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.5, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 }, // 재료 쌓기 시작
      { t: at(3, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(7, 0), src: "coins.mp3", vol: 0.65, dur: 1.6 }, // 원가 공개 = 정점
      { t: at(8, 0), src: "boom.mp3", vol: 0.55, dur: 1.0 }, // 사장 버럭 (fire.mp3 없어서 boom으로)
      { t: at(11, 0), src: "chime.mp3", vol: 1.0, dur: 1.8 }, // 마무리
    ]}
  />
);
