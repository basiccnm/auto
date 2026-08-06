// 블랙알리오 치킨편 썸네일 — 이거 얼마남아 11 (2026-08-03)
//
// 🔴 **레이아웃은 여기 없다. `ThumbTemplate.jsx` 가 갖고 있다.**
//    카드 크기·리본 위치는 전 편 공통 상수(THUMB)라 이 파일에서 못 바꾼다.
//    여기서 정하는 건 **훅 글자 3줄과 음식 이미지 경로**뿐이다.
//    → "음식만 내려/키워" 같은 지시에 카드·리본이 따라 움직이던 사고를 막는다.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { BrandBall } from "../olma/BrandBall";
import { EP, cost, ratio } from "./card_puradak";
import { TONE } from "./tone";
import { DISH4 } from "./props2";
import { GridBg, Ribbon } from "./SoftKit";
import { ThumbInner, ThumbLayout } from "./ThumbTemplate";

const won = (n) => n.toLocaleString("ko-KR");


// ╔══════════════════════════════════════════════════════════╗
// ║  🎚 조정판 — 줄을 넣고 빼고 옮긴다                        ║
// ║  마우스로 맞추려면: out/qa/조정.html 을 열어서 끌어다 놓고 ║
// ║  거기 나오는 코드를 아래 `줄` 에 통째로 붙여넣으면 된다.   ║
// ╚══════════════════════════════════════════════════════════╝
//   좌우   : 카드 가운데 기준. 양수 = 오른쪽
//   위아래 : 카드 세로 가운데 기준. 음수 = 위
//   색     : 진한갈색 · 코럴 · 회갈색 · 금색
//   폰트   : 굵게(Black Han Sans) · 동글(Jua)
export const 줄 = [
  { 글: "블랙알리오 치킨", 크기: 96, 좌우: -8, 위아래: -78, 색: "검정", 폰트: "굵게" },
  { 글: "원가는", 크기: 150, 좌우: -108, 위아래: 82, 색: "코럴", 폰트: "굵게" },
];

export const 소품 = [
  { 그림: "food/s14_13_dot.png", x: 210, y: -284, 크기: 165, 회전: -3 },
  // 초록 체크 — 카드 윗변 한가운데에 걸치게. 카드 top=418 → 무대중심 기준 y=-542
  { 그림: "food/s14_21.png", x: 0, y: -542, 크기: 200, 회전: 0 },
];

export const 화살표 = [];

// 예전에 한 번 올렸던 메뉴다 — 본 사람이 헷갈리지 않게 표시(2026-07-27 지시).
// 🔴 **흰 카드 바깥 위쪽**이다. 카드 안에 넣으면 잘린다. 카드 윗변이 y = -542
export const 쪽지 = [];

export const 리본글 = `${EP.series} ${EP.ep}`;

const COLORS = { 검정: "#111111", 진한갈색: TONE.ink, 코럴: TONE.point, 회갈색: TONE.sub, 금색: TONE.gold };
const FONTS = { 굵게: BLACK, 동글: JUA };

// 🔴 줄마다 **절대좌표**다. 흐름으로 쌓으면 한 줄을 키울 때 아래 줄이 같이 밀려서
//    편집기에서 "왜 다른 것도 같이 변하냐"가 된다(2026-07-25).
//    좌표계는 편집기(편집기.html)와 동일 — 카드 한가운데가 (0,0)
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

const ARGS = { hook: HOOK, label: 리본글, food: DISH4.간장닭, fit: false, 소품, 화살표, 쪽지,
  음식배율: 1, // 누끼 기준 자동정렬로 바뀌어 미세조정 불필요
  음식내림: 40, // 🔴 음식만 내린다. 카드·리본·소품은 안 움직인다(2026-07-27 지시)
  // 리본 글씨는 흰색(2026-07-25 지시)
  리본색: "#FFFFFF" };

// 썸네일 Still (배경 포함)
export const ThumbPuradakCost = () => <ThumbLayout {...ARGS} />;

// 🔴 쇼츠 첫 장면(훅)용 — **배경 없이 알맹이만.** talk_engine 이 배경을 이미 깔았다.
//    썸네일과 같은 부품을 쓰므로 둘이 절대 어긋나지 않는다.
export const ThumbCardPuradakCost = () => <ThumbInner {...ARGS} />;

// ── 인트로 장면 — 캐릭터 등장 ────────────────────────────────
export const PuradakCostIntro = () => (
  <AbsoluteFill style={{ background: TONE.bg }}>
    <Img
      src={staticFile("food/s12_01.png")}
      style={{
        position: "absolute", top: 660, left: "50%", transform: "translateX(-50%)",
        width: 720, filter: "drop-shadow(0 16px 34px rgba(180,120,90,.28))",
      }}
    />
    {/* 🔴 자리 스왑(2026-07-25) — 사장님 왼쪽, 올마 오른쪽. 말하는 쪽이 오른쪽에 크게 */}
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
      이 엽떡 {won(EP.sell)}원인데
    </div>
  </AbsoluteFill>
);
