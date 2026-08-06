// 오프닝 인사 — 모든 편 공통 (2026-07-21 대표님 지시)
//
// 🔴 매 편 **같은 자리·같은 문구**로 들어간다. 채널 시그니처다.
//    "치킨값 욕하는 영상"으로 오해받아 자영업자 악플이 달리는 걸 앞에서 막는다.
//
// 🔴 정지 화면이면 쇼츠 첫 2초에 그냥 넘긴다.
//    그래서 올마가 **꾸벅 인사하는 움직임**을 넣었다. 움직임이 시선을 잡는다.
//
// 🔴 2초를 넘기지 말 것. 훅이 늦어지면 그만큼 이탈한다.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing } from "remotion";

import { Olma } from "../olma/Olma";
import { Nama } from "../olma/Nama";
import { Backdrop } from "../olma/Effects";
import { BG, C } from "./config";
import { BLACK, JUA } from "./fonts";

// 문구는 여기서만 고친다. config가 아니라 여기 두는 이유 —
// 메뉴가 바뀌어도 이 인사는 안 바뀌기 때문(68편 공통).
export const GREET = {
  top: "소상공인 여러분 힘내세요",
  bottom: "그냥 궁금해서 만들었습니다",
};

export const Greet = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 꾸벅 — 0.25초 숙이고 0.35초 들기. 상체만 기울인다(lean).
  const bowIn = Math.round(fps * 0.25);
  const bowOut = Math.round(fps * 0.6);
  const lean = interpolate(f, [0, bowIn, bowOut], [0, 26, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });
  // 머리는 조금 더 깊게 — 이래야 '꾸벅'으로 읽힌다
  const head = interpolate(f, [0, bowIn, bowOut], [0, 14, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });

  // 나마 — 3프레임 늦게 숙인다. 동시에 움직이면 기계처럼 보인다
  const D = 3;
  const lean2 = interpolate(f, [D, bowIn + D, bowOut + D], [0, 26, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });
  const head2 = interpolate(f, [D, bowIn + D, bowOut + D], [0, 14, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });

  // 자막은 위·아래가 살짝 시차를 두고 올라온다
  const up = (delay) =>
    interpolate(f, [delay, delay + 6], [30, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.quad),
    });
  const fade = (delay) =>
    interpolate(f, [delay, delay + 6], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  return (
    <AbsoluteFill style={{ background: BG.hook, overflow: "hidden" }}>
      <Backdrop color={BG.hook} />

      {/* 윗줄 — 존중의 말. 흰 판 위에 올려야 배경 패턴에 안 묻힌다 */}
      <div
        style={{
          position: "absolute",
          top: 470,
          width: "100%",
          textAlign: "center",
          translate: `0px ${up(2)}px`,
          opacity: fade(2),
        }}
      >
        <span
          style={{
            display: "inline-block",
            fontFamily: BLACK,
            fontSize: 92,
            letterSpacing: -4,
            color: "#fff",
            background: C.ink,
            borderRadius: 20,
            padding: "16px 44px 24px",
          }}
        >
          {GREET.top}
        </span>
      </div>

      {/* 아랫줄 — 의도 설명. 조금 작고 부드럽게 */}
      <div
        style={{
          position: "absolute",
          top: 640,
          width: "100%",
          textAlign: "center",
          translate: `0px ${up(9)}px`,
          opacity: fade(9),
        }}
      >
        <span
          style={{
            display: "inline-block",
            fontFamily: JUA,
            fontSize: 62,
            color: "#333",
            background: "#fff",
            border: `6px solid ${C.ink}`,
            borderRadius: 18,
            padding: "12px 34px 18px",
          }}
        >
          {GREET.bottom}
        </span>
      </div>

      {/* 🔴 둘 다 나와 꾸벅 인사한다(2026-07-21 지시). 혼자면 화면이 허전했다.
             나마가 아주 살짝 늦게 숙인다 — 동시에 움직이면 기계 같다. */}
      {/* 🔴 Olma의 viewBox는 -90부터라 컴포넌트 폭(667)의 가운데가 몸통이 아니다.
             둘을 화면 정중앙에 두려면 각각 -430 / -240 만큼 밀어야 한다(2026-07-21 오른쪽 쏠림 수정). */}
      {/* 🔴 간격 주의 — 붙이면 나마 양갈래가 올마 얼굴을 파고든다(2026-07-21).
             둘 사이를 300px 벌린다. */}
      <div style={{ position: "absolute", bottom: 210, left: "50%", translate: "-490px 0px" }}>
        <Olma face="씩" pose="기본" scale={1.05} lean={lean} head={head} />
      </div>
      <div style={{ position: "absolute", bottom: 210, left: "50%", translate: "-190px 0px" }}>
        <Nama face="씩" pose="기본" scale={1.05} lean={lean2} head={head2} />
      </div>
    </AbsoluteFill>
  );
};
