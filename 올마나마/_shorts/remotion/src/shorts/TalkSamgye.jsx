// 삼계탕 원가편 — 이거 얼마남아 11 (2026-08-03)
//
// 🔴 이 편의 축은 **닭+한방 티백 둘이 92%**라는 것. 나머지 넷을 다 더해도 480원.
//    브랜드가 없어 「국내산 영계만 씁니다」는 삼계탕집 일반을 대변하는 톤이다.
// 🔴 판매가 18,000원은 한국소비자원 참가격(2026-05 서울 평균 18,150원) 근거.
import React from "react";

import { EP } from "../cards/card_samgye";
import { SamgyePanel } from "../cards/SamgyePage";
import { ThumbCardSamgyeCost } from "../cards/ThumbSamgyeCost";
import { LEAD, LINES } from "./lines_samgye";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const SAMGYE_SEC = talkSec(LINES, LEAD);

export const TalkSamgye = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceS1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <SamgyePanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft next={EP.next} site={EP.site} />}
      </>
    )}
    renderHook={() => <ThumbCardSamgyeCost />}
    // 인덱스는 0부터. 14줄 — 2=닭73% · 5=티백1,100 · 10=원가공개(coins) · 13=마무리(chime)
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(5, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(10, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },
      { t: at(13, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },
    ]}
  />
);
