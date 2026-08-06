// 엽기떡볶이 엽기로제 원가편 — 이거 얼마남아 3 (2026-07-26)
//
// 🔴 **여성향 톤 3편.** 올마=여자(핑크, 진행) / 나마=남자(노랑, 사장님).
//    배경은 이미지 대신 파스텔 격자(bg:"soft"), 판은 흰 카드 + 코럴.
import React from "react";

import { EP } from "../cards/card_yeopgi";
import { YeopgiPanel } from "../cards/YeopgiPage";
import { ThumbCardYeopgi } from "../cards/ThumbYeopgi";
import { LEAD, LINES } from "./lines_yeopgi";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const YEOPGI_SEC = talkSec(LINES, LEAD);

export const TalkYeopgi = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceY1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <YeopgiPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft site={EP.site} ask={"궁금한 메뉴 있으면\n댓글 남겨주세요!"} />}
      </>
    )}
    renderHook={() => <ThumbCardYeopgi />}
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(5, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(7, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },
      { t: at(11, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },
    ]}
  />
);
