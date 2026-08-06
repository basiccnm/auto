// bhc 뿌링클 원가편 — 이거 얼마남아 4 (2026-07-27)
//
// 🔴 **레시피편과 짝이다.** 이 편 마지막이 "내일은 집에서 뿌링클" 예고 →
//    다음 날 shop/combo_bburinkle 편이 올라간다. 소재 하나로 이틀을 쓴다.
// 🔴 여성향 톤. 올마=여자(핑크, 진행) / 사장님=남자(노랑).
import React from "react";

import { EP } from "../cards/card_bburinkle";
import { BburinklePanel } from "../cards/BburinklePage";
import { ThumbCardBburinkle } from "../cards/ThumbBburinkle";
import { LEAD, LINES } from "./lines_bburinkle";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const BBURINKLE_SEC = talkSec(LINES, LEAD);

export const TalkBburinkle = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceBB1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <BburinklePanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft next={EP.next} site={EP.site} />}
      </>
    )}
    renderHook={() => <ThumbCardBburinkle />}
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(5, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(7, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },
      { t: at(11, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },
    ]}
  />
);
