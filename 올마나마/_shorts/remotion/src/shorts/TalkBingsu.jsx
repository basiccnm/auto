// 설빙 애플망고치즈설빙 원가편 — 이거 얼마남아 2 (2026-07-25)
//
// 🔴 **첫 여성향 편.** 올마=여자(핑크, 진행) / 나마=남자(노랑, 사장님).
//    배경은 이미지 대신 파스텔 격자(bg:"soft"), 판은 흰 카드 + 코럴.
import React from "react";

import { EP } from "../cards/card_bingsu";
import { BingsuPanel } from "../cards/BingsuPage";
import { ThumbCardBingsu } from "../cards/ThumbBingsu";
import { LEAD, LINES } from "./lines_bingsu";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const BINGSU_SEC = talkSec(LINES, LEAD);

export const TalkBingsu = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceB1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <BingsuPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft site={EP.site} ask={"궁금한 메뉴 있으면\n댓글 남겨주세요!"} />}
      </>
    )}
    renderHook={() => <ThumbCardBingsu />}
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(5, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(7, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },
      { t: at(11, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },
    ]}
  />
);
