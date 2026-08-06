// 배달 1편 본편 — 옵션 꼼수(앵커링), 약 48초 (2026-07-24)
//
// 🔴 마라탕 2·3편과 **같은 엔진·같은 문법**이다(talk_engine.jsx).
//    이 파일은 화면(판)만 지정한다. 대사는 lines_anchor.js, 숫자는 pages_anchor.js.
//
// 🔴 판은 카드뉴스와 **같은 컴포넌트**(AnchorPanel)를 쓴다. 인스타 카드와 쇼츠가
//    한 소스에서 나오는 게 이 편의 핵심이다 — 문구를 두 벌로 두면 반드시 어긋난다.
//
// 🔴 쇼츠에선 showBox=false. 판이 길어지면 말풍선(y820)과 겹친다.
//    판 top 200 + 최대 높이 588 = 788 에서 끝나야 안전하다.
import React from "react";

import { EP } from "../cards/card_anchor";
import { AnchorPanel } from "../cards/AnchorPage";
import { ThumbCard } from "../cards/ThumbAnchor";
import { LEAD, LINES } from "./lines_anchor";
import { Site, TalkEngine, talkSec } from "./talk_engine";

export const ANCHOR_SEC = talkSec(LINES, LEAD);

export const TalkAnchor = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voiceD1"
    defaultBg="store01"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.page != null && <AnchorPanel i={p.page} top={200} pop={partPop} showBox={false} showSite={false} />}
        {/* 🔴 ask를 안 넘기면 "마라탕 궁금한 거…"가 나온다. 여긴 배달편이다 */}
        {p.site && <Site pop={bigIn} site={EP.site} ask={"배달 궁금한 거 있으면\n쇼츠로 알려드려요!"} />}
      </>
    )}
    renderHook={() => <ThumbCard />}
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.5, dur: 1.2 },
      // 판이 바뀌는 순간마다 틱 — 장이 넘어간 걸 귀로도 알린다
      { t: at(2, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 }, // 문제
      { t: at(4, 0), src: "tick.mp3", vol: 0.6, dur: 0.45 }, // 옵션값
      { t: at(6, 0), src: "coins.mp3", vol: 0.65, dur: 1.6 }, // 결제액 = 정점
      { t: at(8, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 }, // 이유
      { t: at(11, 0), src: "chime.mp3", vol: 1.0, dur: 1.8 }, // 회수
    ]}
  />
);
