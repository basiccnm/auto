// 순대국 원가편 — 이거 얼마남아 6 (2026-07-30)
//
// 🔴 **브랜드 이름을 쓰지 않는다**(2026-07-30 지시). 특정 브랜드가 뭘 넣는지 알 수 없어서다.
//    재료 구성은 공개 레시피 2개 대조, 단가는 식봄 도매(국내산).
// 🔴 이 편의 축은 **순대국인데 순대가 제일 싸다**는 것이다(머리고기 767 > 내장 644 > 육수 540 > 순대 425).
//
// ⚠️ **sfx 의 at(n,0) 은 대사 줄 번호(0부터)다.** LINES 가 13줄이므로 마지막은 at(12,0) 이다.
//    2026-07-30에 12줄 → 11줄로 줄이면서 at(11,0) 이 undefined 가 되어 스튜디오가 통째로 죽었다.
//    대사 줄 수를 바꾸면 **여기 인덱스도 같이 고칠 것.**
import React from "react";

import { EP } from "../cards/card_keunmam";
import { KeunmamPanel } from "../cards/KeunmamPage";
import { ThumbCardKeunmamCost } from "../cards/ThumbKeunmamCost";
import { LEAD, LINES } from "./lines_keunmam";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const KEUNMAM_SEC = talkSec(LINES, LEAD);

export const TalkKeunmam = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceK1"
    defaultBg="soft"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <KeunmamPanel i={p.page} top={200} pop={partPop} />}
        {p.site && <Site pop={bigIn} soft next={EP.next} site={EP.site} />}
      </>
    )}
    renderHook={() => <ThumbCardKeunmamCost />}
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.45, dur: 1.2 },
      { t: at(2, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },   // 머리고기·내장
      { t: at(4, 0), src: "tick.mp3", vol: 0.5, dur: 0.45 },   // 순대
      { t: at(9, 0), src: "coins.mp3", vol: 0.6, dur: 1.6 },   // ★ 정점 — 원가 공개
      { t: at(12, 0), src: "chime.mp3", vol: 0.9, dur: 1.8 },  // 마무리
    ]}
  />
);
