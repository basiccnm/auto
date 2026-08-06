// 카드뉴스 영상 — 6장을 순서대로 넘긴다 (2026-07-24)
//
// 🔴 속도(2026-07-24 지시): "약간 빠른 것 같은데" 정도로 넘긴다.
//    쇼츠는 다 읽히려고 만드는 게 아니라 **"뭐였지?" 하고 되감게** 만드는 것.
//    그래서 훅·마무리는 짧게, 숫자 카드만 조금 더 준다.
// 🔴 전환은 0.15초 크로스페이드. 더 길면 늘어지고, 없으면 뚝뚝 끊긴다.
// 🔴 카드 레이아웃은 mode="video" — 상단 여백을 줄여 글씨를 더 키운 판(4:5 크롭 대비 불필요)
import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";

import { CARDS } from "./card_anchor";
import { CardNews } from "./CardNews";
import { DoodleStory } from "./DoodleStory";

export const VFPS = 30;

// 장당 초 — 정보량에 비례. ⓪표지가 앞에 붙었다(2026-07-24). 합계 12.2초
// 🔴 표지는 1.0초 — 썸네일이자 훅. 목록에서 이 화면이 얼굴이 된다
const SEC = [1.0, 1.6, 1.8, 2.4, 2.4, 1.8, 1.2];
const FADE = 0.15;

export const CARD_VIDEO_SEC = SEC.reduce((a, b) => a + b, 0);

const Fade = ({ children, dur }) => {
  const f = useCurrentFrame();
  const fade = FADE * VFPS;
  const op = interpolate(f, [0, fade, dur - fade, dur], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ opacity: op }}>{children}</AbsoluteFill>;
};

export const CardVideo = () => {
  let at = 0;
  return (
    <AbsoluteFill style={{ background: "#182F6E" }}>
      {CARDS.map((c, i) => {
        const dur = Math.round(SEC[i] * VFPS);
        const from = at;
        at += dur;
        return (
          <Sequence key={c.id} from={from} durationInFrames={dur}>
            <Fade dur={dur}>
              <CardNews i={i} mode="video" />
            </Fade>
          </Sequence>
        );
      })}

      {/* 🔴 낙서 스토리는 카드 위에 **한 번만** 깐다(2026-07-24).
          Sequence 안에 넣으면 카드마다 리셋돼서 이야기가 안 이어진다.
          하단 여백(틱톡 UI가 가리는 480px 위쪽)에 무대를 만든다 */}
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <div style={{ position: "absolute", bottom: 250, left: "50%", transform: "translateX(-50%)" }}>
          <DoodleStory width={980} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
