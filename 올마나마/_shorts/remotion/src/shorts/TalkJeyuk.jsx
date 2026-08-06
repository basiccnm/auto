// 깻잎제육 반상 원가편 — 이거 얼마남아 9 (2026-08-03)
//
// 🔴 **레시피편과 짝이다.** 마지막이 "다음은 초간단 제육볶음 레시피" 예고 →
//    다음 편으로 제육볶음 레시피편이 올라간다. 「제육볶음레시피」 월 134,730 회가 노림수다.
// 🔴 이 편의 축은 **반찬 네 가지가 다 합쳐 273원**이라는 것.
//    계란후라이 하나(282원)가 반찬 전부보다 비싸다.
//    ⛔ 반찬이 부실하다고 말하지 않는다. 숫자만 보이고 판단은 보는 사람 몫이다.
// 🔴 판매가 10,500원은 **공식 API**(api.bonif.co.kr, BF104) 확인값이다.
//    우리 DB 에 있던 「제육볶음 반상 8,900원」은 공식에 없다 — 단종된 옛 메뉴다.
import React from "react";

import { EP } from "../cards/card_jeyuk";
import { JeyukPanel } from "../cards/JeyukPage";
import { ThumbCardJeyukCost } from "../cards/ThumbJeyukCost";
import { LEAD, LINES } from "./lines_jeyuk";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const JEYUK_SEC = talkSec(LINES, LEAD);

export const TalkJeyuk = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceJ1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <JeyukPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft next={EP.next} site={EP.site} />}
      </>
    )}
    renderHook={() => <ThumbCardJeyukCost />}
    // 🔴 인덱스는 **0부터**. 12줄이라 마지막이 11이다(지코바편과 같은 자리).
    //    2=고기 51% · 5=밥·계란 · 7=원가공개(coins) · 11=마무리(chime)
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(3, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(6, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(7, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },
      { t: at(11, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },
    ]}
  />
);
