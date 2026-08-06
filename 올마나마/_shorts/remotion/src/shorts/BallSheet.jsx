// 볼 확인용 시안 (2026-07-22) — 확정되면 지운다.
//
// 🔴 등장인물은 **최대 4명**(올마·소비자·사장님·본사). 단 한 화면엔 **두 명까지**.
//    넷이 동시에 서면 얼굴이 작아져 표정이 안 보이고 누가 말하는지도 안 읽힌다.
//    올마가 상대를 바꿔가며 만나는 식이면 넷을 다 쓰면서 화면은 늘 둘이다.
import React from "react";
import { AbsoluteFill } from "remotion";

import { BrandBall } from "../olma/BrandBall";
import { Backdrop } from "../olma/Effects";
import { BG, C } from "./config";
import { BLACK, JUA } from "./fonts";

// 🔴 x는 화면 중앙에서의 거리. left+translate만 쓰면 요소 왼쪽 끝이 그 자리에 놓여 오른쪽이 잘린다.
const At = ({ children, x, y, style = {} }) => (
  <div style={{ position: "absolute", top: y, left: `calc(50% + ${x}px)`, transform: "translateX(-50%)", ...style }}>
    {children}
  </div>
);

const Cap = ({ children, x, y, size = 38, color = "#555" }) => (
  <At x={x} y={y} style={{ width: 300, textAlign: "center", fontFamily: JUA, fontSize: size, color }}>
    {children}
  </At>
);

const Title = ({ children, y, size = 66 }) => (
  <div
    style={{
      position: "absolute",
      top: y,
      width: "100%",
      textAlign: "center",
      fontFamily: BLACK,
      fontSize: size,
      letterSpacing: -3,
      color: C.ink,
    }}
  >
    {children}
  </div>
);

export const BallSheet = () => (
  <AbsoluteFill style={{ background: BG.hook }}>
    <Backdrop color={BG.hook} />

    <Title y={46} size={72}>등장인물 4명</Title>

    <At x={-390} y={160}><BrandBall brand="올마" face="웃음" scale={0.6} /></At>
    <At x={-130} y={160}><BrandBall brand="소비자" face="발끈" scale={0.6} /></At>
    <At x={130} y={160}><BrandBall brand="사장님" face="변명" scale={0.6} /></At>
    <At x={390} y={160}><BrandBall brand="교촌" face="시치미" scale={0.6} /></At>

    <Cap x={-390} y={400}>올마 · 진행</Cap>
    <Cap x={-130} y={400}>소비자</Cap>
    <Cap x={130} y={400}>사장님</Cap>
    <Cap x={390} y={400}>교촌 · 본사</Cap>

    {/* ── 올마 표정: 로고 얼굴 → 본편 얼굴 ── */}
    <Title y={510} size={56}>올마 — 오프닝은 로고 얼굴로</Title>

    <At x={-390} y={600}><BrandBall brand="올마" face="웃음" scale={0.56} /></At>
    <At x={-130} y={600}><BrandBall brand="올마" face="시치미" scale={0.56} /></At>
    <At x={130} y={600}><BrandBall brand="올마" face="놀람" scale={0.56} /></At>
    <At x={390} y={600}><BrandBall brand="올마" face="발끈" scale={0.56} /></At>

    <Cap x={-390} y={830} color="#8A6A00">웃음</Cap>
    <Cap x={-130} y={830}>시치미</Cap>
    <Cap x={130} y={830}>놀람</Cap>
    <Cap x={390} y={830}>발끈</Cap>

    <At x={-260} y={920}><BrandBall brand="올마" face="변명" scale={0.56} /></At>
    <At x={260} y={920}><BrandBall brand="올마" face="화남" scale={0.56} /></At>
    <Cap x={-260} y={1150}>변명</Cap>
    <Cap x={260} y={1150}>화남</Cap>

    {/* ── 실제 배치: 한 화면에 둘 ── */}
    <Title y={980} size={56}>한 화면엔 둘까지</Title>

    <At x={-200} y={1070}><BrandBall brand="올마" face="놀람" scale={0.66} /></At>
    <At x={200} y={1070}><BrandBall brand="교촌" face="시치미" scale={0.66} /></At>
    <Cap x={0} y={1350} size={42} color="#7A1410">올마 ↔ 본사 · 변명 구간</Cap>

    <At x={-200} y={1440}><BrandBall brand="올마" face="시치미" scale={0.66} /></At>
    <At x={200} y={1440}><BrandBall brand="사장님" face="변명" scale={0.66} /></At>
    <Cap x={0} y={1720} size={42} color="#14513A">올마 ↔ 사장님 · 하소연 구간</Cap>
  </AbsoluteFill>
);
