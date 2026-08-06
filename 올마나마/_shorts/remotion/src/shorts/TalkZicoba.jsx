// 지코바 순살양념구이 원가편 — 이거 얼마남아 5 (2026-07-28)
//
// 🔴 **레시피편과 짝이다.** 마지막이 "다음은 초간단 지코바 레시피" 예고 →
//    다음 편으로 shop/ShopZicoba 가 올라간다.
// 🔴 이 편의 축은 **원산지**다. 순살이 1,000원 비싼데 닭값은 600원 싸다 —
//    뼈는 국산, 순살은 브라질산이라서다(2025-04 원산지 적발 뒤 전면 전환, 회사 발표).
//    ⛔ 브라질산이 나쁘다고 말하지 않는다. 사실만 전하고 판단은 보는 사람 몫이다.
import React from "react";

import { EP } from "../cards/card_zicoba";
import { ZicobaPanel } from "../cards/ZicobaPage";
import { ThumbCardZicobaCost } from "../cards/ThumbZicobaCost";
import { LEAD, LINES } from "./lines_zicoba";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const ZICOBA_SEC = talkSec(LINES, LEAD);

export const TalkZicoba = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceZ1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <ZicobaPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft next={EP.next} site={EP.site} />}
      </>
    )}
    renderHook={() => <ThumbCardZicobaCost />}
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(5, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },
      { t: at(7, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },
      { t: at(11, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },
    ]}
  />
);
