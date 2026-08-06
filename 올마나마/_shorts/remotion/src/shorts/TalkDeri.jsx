// 롯데리아 데리버거 원가편 — 이거 얼마남아 8 (2026-08-02)
//
// 🔴 이 편의 축은 **제일 싼데 제일 안 남는다.**
//    데리버거 3,800원 34% / 불고기 5,100원 26% / 새우 5,100원 31%.
//    번(450원)이 어느 버거나 똑같이 들어가서 그렇다 — 7번에 복선, 15번에 회수.
//
// 🔴 지금까지 편과 다른 점 둘 (2026-08-01 대표 지시)
//    ① **절정을 뒤로** — 16줄 중 12번(75%)에서 원가를 깐다. 지코바편은 8/12(67%)였다.
//    ② **사이트 홍보를 정점 바로 앞에** — 10~11번. 원가를 기다리는 순간이라 넘기지 못한다.
//
// 🔴 사장님 목소리는 이 편만 **Andrew**(`사장님3`, -15Hz). 김밥편은 Remy 였다.
import React from "react";

import { EP } from "../cards/card_deri";
import { DeriPanel } from "../cards/DeriPage";
import { ThumbCardDeriCost } from "../cards/ThumbDeriCost";
import { LEAD, LINES } from "./lines_deri";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const DERI_SEC = talkSec(LINES, LEAD);

export const TalkDeri = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceD1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <DeriPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft next={EP.next} site={EP.site} />}
      </>
    )}
    renderHook={() => <ThumbCardDeriCost />}
    // 🔴 효과음 인덱스는 **0부터**다. 대사 번호 -1 을 쓴다.
    //    5 = 「빵값 보면 놀랄걸」(작은 반전) · 11 = 원가 공개(정점)
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
