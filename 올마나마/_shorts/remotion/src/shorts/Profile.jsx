// 채널 프로필 이미지 — 올마 얼굴
//
// 🔴 프로필은 어디서든 **원형으로 잘린다**(유튜브·인스타·틱톡 전부).
//    네 모서리는 안 보인다고 봐야 하므로, 얼굴을 가운데에 두고 사방에 여유를 준다.
// 🔴 아주 작게(32px) 표시되는 자리도 있다. 눈·입만 크게 남기고 잔선은 뺀다.
import React from "react";
import { AbsoluteFill } from "remotion";
import { OLMA, MOUTHS } from "../olma/Olma";
import { C } from "./config";

export const Profile = ({ face = "씩", bg = C.yellow }) => {
  const mouth = MOUTHS[face] || MOUTHS["씩"];
  return (
    <AbsoluteFill style={{ background: bg, alignItems: "center", justifyContent: "center" }}>
      <svg viewBox="0 0 400 400" width={1080} height={1080} xmlns="http://www.w3.org/2000/svg">
        {/* 얼굴 — 원형 크롭 안에 꽉 차되 테두리가 안 잘리게 r=150 */}
        <circle cx={200} cy={200} r={150} fill={OLMA.head} stroke={OLMA.line} strokeWidth={14} />
        {/* 눈 — 작게 표시될 걸 감안해 크게 */}
        <ellipse cx={152} cy={178} rx={17} ry={17} fill={OLMA.line} />
        <ellipse cx={248} cy={178} rx={17} ry={17} fill={OLMA.line} />
        {/* 입 — 400x400 좌표계로 옮겨 그린다 */}
        <g style={{ transformBox: "view-box", transformOrigin: "200px 200px", translate: "0px 52px", scale: 1.5 }}>
          <path d={mouth} fill="none" stroke={OLMA.line} strokeWidth={9} strokeLinecap="round" />
        </g>
      </svg>
    </AbsoluteFill>
  );
};
