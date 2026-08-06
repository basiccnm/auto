// 이펙트 점검용 (임시) — 확정되면 지운다.
// 🔴 이펙트는 정지화면으로는 못 본다. 프레임을 넘겨가며 봐야 한다.
//    그래서 Still이 아니라 Composition으로 만든다.
import React from "react";
import { AbsoluteFill, Sequence } from "remotion";

import { Olma } from "../olma/Olma";
import { Nama } from "../olma/Nama";
import { PopEyes, Sparkles, ThumbCard, Volcano } from "../olma/BigFx";
import { Umbrella } from "../olma/Props";
import { BG, C } from "./config";
import { BLACK } from "./fonts";

const Label = ({ children }) => (
  <div
    style={{
      position: "absolute",
      top: 40,
      width: "100%",
      textAlign: "center",
      fontFamily: BLACK,
      fontSize: 54,
      color: C.ink,
    }}
  >
    {children}
  </div>
);

// 0~2초 반짝임 / 2~5초 썸네일카드 / 5~8초 눈알 / 8~13초 화산+우산
export const FxSheet = () => (
  <AbsoluteFill style={{ background: BG.hook }}>
    <Sequence from={0} durationInFrames={60} name="반짝임">
      <AbsoluteFill style={{ background: BG.hook }}>
        <Label>① 반짝임 (인사 장면)</Label>
        <Sparkles n={12} />
        <div style={{ position: "absolute", bottom: 300, left: "50%", translate: "-400px 0px" }}>
          <Olma face="씩" pose="기본" scale={1.0} />
        </div>
        <div style={{ position: "absolute", bottom: 300, left: "50%", translate: "-100px 0px" }}>
          <Nama face="씩" pose="기본" scale={1.0} glasses={0} />
        </div>
      </AbsoluteFill>
    </Sequence>

    <Sequence from={60} durationInFrames={90} name="썸네일카드">
      <AbsoluteFill style={{ background: BG.hook }}>
        <Label>② 썸네일 카드</Label>
        <ThumbCard at={6} top="교촌 허니콤보" main="원가 충격 공개" sub="올마나마?" />
      </AbsoluteFill>
    </Sequence>

    <Sequence from={150} durationInFrames={90} name="눈알">
      <AbsoluteFill style={{ background: BG.build }}>
        <Label>③ 눈알 튀어나옴</Label>
        <div style={{ position: "absolute", bottom: 400, left: "50%", translate: "-290px 0px" }}>
          <Olma face="헉" pose="깜짝" scale={1.4} />
          <PopEyes at={10} scale={1.4} />
        </div>
      </AbsoluteFill>
    </Sequence>

    <Sequence from={240} durationInFrames={150} name="화산+우산">
      <AbsoluteFill style={{ background: BG.climax }}>
        <Label>④ 화산 폭발 + 나마 우산</Label>
        {/* 🔴 분화구는 **올마 머리 정수리**에 와야 한다.
               올마가 bottom260·scale1.15에 있을 때 머리 중심은 화면상 x≈34% y≈59%다.
               분출은 거기서 위로 뻗으므로 y는 그보다 살짝 위(52%)에 둔다. */}
        {/* 분화구 = 올마 정수리. bottom260·scale1.15일 때 화면상 x≈34% y≈53% */}
        {/* 🔴 size 1.0은 화면 절반을 먹어 자막 자리가 없어졌다(2026-07-21). 0.62로 줄인다 */}
        <Volcano at={8} x="34%" y="56%" size={0.62} />
        <div style={{ position: "absolute", bottom: 260, left: "50%", translate: "-500px 0px" }}>
          <Olma face="극대노" pose="만세" scale={1.15} />
        </div>
        <div style={{ position: "absolute", bottom: 260, left: "50%", translate: "-140px 0px" }}>
          <Nama face="무표정" pose="가리킴위" scale={1.15} earmuffs glasses={0} />
        </div>
        {/* 🔴 우산은 손에 쥐여주면(holdR) 얼굴을 덮는다(2026-07-21).
               나마 **머리 위**에 따로 띄운다. 팔은 가리킴위로 들어 올려 잡은 것처럼 보이게. */}
        <div style={{ position: "absolute", bottom: 900, left: "50%", translate: "-60px 0px" }}>
          <Umbrella x={130} y={110} rot={-10} open={1} />
        </div>
      </AbsoluteFill>
    </Sequence>
  </AbsoluteFill>
);
