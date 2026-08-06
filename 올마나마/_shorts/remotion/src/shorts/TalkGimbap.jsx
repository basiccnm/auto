// 돈까스 김밥 원가편 — 이거 얼마남아 7 (2026-08-01)
//
// 🔴 이 편의 축은 **1등이 돈까스가 아니다.** 계란 418 > 돈까스 408.
//    10원 차이지만 «돈까스김밥» 이라는 이름을 달고 계란이 1위인 게 이야깃거리다.
//
// 🔴 지금까지 편과 다른 점 둘 (2026-08-01 대표 지시)
//    ① **절정을 뒤로** — 16줄 중 12번(75%)에서 원가를 깐다. 지코바편은 8/12(67%)였다.
//    ② **사이트 홍보를 정점 바로 앞에** — 10~11번. 원가를 기다리는 순간이라 넘기지 못한다.
//
// 🔴 사장님 목소리는 이 편만 **Remy**(`사장님2`). 편마다 브랜드가 다르니 사람도 다르다.
import React from "react";

import { EP } from "../cards/card_gimbap";
import { GimbapPanel } from "../cards/GimbapPage";
import { ThumbCardGimbapCost } from "../cards/ThumbGimbapCost";
import { LEAD, LINES } from "./lines_gimbap";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const GIMBAP_SEC = talkSec(LINES, LEAD);

export const TalkGimbap = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceG1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <GimbapPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft next={EP.next} site={EP.site} />}
      </>
    )}
    renderHook={() => <ThumbCardGimbapCost />}
    // 🔴 효과음 인덱스는 **0부터**다. 대사 번호 -1 을 쓴다.
    //    5 = 「1등이 돈까스가 아니야」(작은 반전) · 11 = 원가 공개(정점)
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(5, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(9, 0), src: "tick.mp3", vol: 0.4, dur: 0.45 },
      { t: at(11, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },
      { t: at(15, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },
    ]}
  />
);
