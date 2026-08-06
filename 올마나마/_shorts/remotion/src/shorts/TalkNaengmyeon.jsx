// 물냉면 원가편 — 이거 얼마남아 13 (2026-08-03)
//
// 🔴 이 편의 축은 **원가율 12% — 시리즈 최저**. 소고기(육수용 25g)·메밀면·계란이
//    376/330/282원으로 거의 비슷비슷하다. 브랜드가 없어 「육수를 이틀 우려요」는
//    냉면집 일반 톤이다.
// 🔴 판매가 9,000원 — 대표 확정. 참가격 서울 평균(12,615원)보다 낮게 잡았다.
import React from "react";

import { EP } from "../cards/card_naengmyeon";
import { NaengmyeonPanel } from "../cards/NaengmyeonPage";
import { ThumbCardNaengmyeonCost } from "../cards/ThumbNaengmyeonCost";
import { LEAD, LINES } from "./lines_naengmyeon";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const NAENGMYEON_SEC = talkSec(LINES, LEAD);

export const TalkNaengmyeon = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceN1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <NaengmyeonPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft next={EP.next} site={EP.site} />}
      </>
    )}
    renderHook={() => <ThumbCardNaengmyeonCost />}
    // 인덱스는 0부터. 14줄 — 2=소고기양지 · 5=메밀면계란612 · 10=원가공개(coins) · 13=마무리(chime)
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(5, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(10, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },
      { t: at(13, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },
    ]}
  />
);
