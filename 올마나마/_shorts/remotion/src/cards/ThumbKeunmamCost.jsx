// 순대국편 썸네일 — 이거 얼마남아 6 (2026-07-30)
// 🔴 **브랜드 이름 금지**(2026-07-30 지시) — 일반 순대국 기준이다
// 🔴 레이아웃은 `ThumbTemplate.jsx` 공통. 여기선 훅 글자·음식 이미지만 정한다.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { BrandBall } from "../olma/BrandBall";
import { EP, cost, ratio } from "./card_keunmam";
import { TONE } from "./tone";
import { DISH3 } from "./props2";
import { GridBg, Ribbon } from "./SoftKit";
import { ThumbInner, ThumbLayout } from "./ThumbTemplate";

const won = (n) => n.toLocaleString("ko-KR");

export const 줄 = [
  { 글: "순대국 한 그릇", 크기: 88, 좌우: -8, 위아래: -78, 색: "검정", 폰트: "굵게" },
  { 글: "원가는", 크기: 150, 좌우: -108, 위아래: 82, 색: "코럴", 폰트: "굵게" },
];

export const 소품 = [
  { 그림: "food/s14_13_dot.png", x: 210, y: -284, 크기: 165, 회전: -3 },
  { 그림: "food/s14_21.png", x: 0, y: -542, 크기: 200, 회전: 0 },
];

export const 화살표 = [];
export const 쪽지 = [];

export const 리본글 = `${EP.series} ${EP.ep}`;

const COLORS = { 검정: "#111111", 진한갈색: TONE.ink, 코럴: TONE.point, 회갈색: TONE.sub, 금색: TONE.gold };
const FONTS = { 굵게: BLACK, 동글: JUA };

const HOOK = (
  <>
    {줄.map((s, i) => (
      <div
        key={i}
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: `translate(calc(-50% + ${s.좌우}px), calc(-50% + ${s.위아래}px))`,
          whiteSpace: "nowrap",
          lineHeight: 1.05,
          fontFamily: FONTS[s.폰트] || BLACK,
          fontSize: s.크기,
          color: COLORS[s.색] || TONE.ink,
        }}
      >
        {s.글}
      </div>
    ))}
  </>
);

const ARGS = { hook: HOOK, label: 리본글, food: DISH3.순대국밥, fit: false, 소품, 화살표, 쪽지,
  음식배율: 1,
  음식내림: 40,
  리본색: "#FFFFFF" };

export const ThumbKeunmamCost = () => <ThumbLayout {...ARGS} />;
export const ThumbCardKeunmamCost = () => <ThumbInner {...ARGS} />;

export const KeunmamCostIntro = () => (
  <AbsoluteFill style={{ background: TONE.bg }}>
    <Img
      src={staticFile("food/s12_01.png")}
      style={{
        position: "absolute", top: 660, left: "50%", transform: "translateX(-50%)",
        width: 720, filter: "drop-shadow(0 16px 34px rgba(180,120,90,.28))",
      }}
    />
    <div style={{ position: "absolute", top: 1145, left: "calc(50% - 225px)", transform: "translateX(-50%)" }}>
      <BrandBall brand="사장님" face="시치미" scale={1.0} blush />
    </div>
    <div style={{ position: "absolute", top: 1145, left: "calc(50% + 225px)", transform: "translateX(-50%)" }}>
      <BrandBall brand="올마" face="놀람" scale={1.28} blush />
    </div>
    <div
      style={{
        position: "absolute", top: 300, left: "50%", transform: "translateX(-50%)",
        background: "#fff", borderRadius: 34, padding: "26px 44px",
        fontFamily: JUA, fontSize: 72, color: TONE.ink, whiteSpace: "nowrap",
        boxShadow: "0 14px 36px rgba(180,120,100,.22)",
      }}
    >
      이 순대국 {won(EP.sell)}원인데
    </div>
  </AbsoluteFill>
);
