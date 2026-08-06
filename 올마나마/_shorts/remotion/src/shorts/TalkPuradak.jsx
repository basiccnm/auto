// 블랙알리오 치킨 원가편 — 이거 얼마남아 10 (2026-08-03)
//
// 🔴 이 편의 축은 **소스 1,350원이 나머지 셋(파우더·치킨무·식용유 1,174원)보다 비싸다**는 것.
// 🔴 판매가 21,900원은 공식 메뉴가(브랜드 = 푸라닭치킨). 재료는 menu_ingredients 기준.
import React from "react";

import { EP } from "../cards/card_puradak";
import { PuradakPanel } from "../cards/PuradakPage";
import { ThumbCardPuradakCost } from "../cards/ThumbPuradakCost";
import { LEAD, LINES } from "./lines_puradak";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const PURADAK_SEC = talkSec(LINES, LEAD);

export const TalkPuradak = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceP1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <PuradakPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft next={EP.next} site={EP.site} />}
      </>
    )}
    renderHook={() => <ThumbCardPuradakCost />}
    // 인덱스는 0부터. 14줄 — 2=닭 · 5=소스1,350 · 10=원가공개(coins) · 13=마무리(chime)
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(5, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(10, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },
      { t: at(13, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },
    ]}
  />
);
