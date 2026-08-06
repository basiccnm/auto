// 낙서 스토리 — 12초 내내 이어지는 한 편 (2026-07-24)
//
// 🔴 앞서 만든 Doodle은 카드마다 따로 도는 짧은 루프였다.
//    이건 **처음부터 끝까지 하나로 이어지는 이야기**다(2026-07-24 지시).
//    카드가 넘어가도 낙서는 계속 진행돼서, 눈이 심심할 틈이 없다.
//
// 🔴 스토리(카드 내용과 맞춘 A집 vs B집 대결):
//      0~2초   양쪽 끝에서 둘이 등장해 가운데로 걸어온다
//      2~5초   마주 보고 신경전 (서로 삿대질)
//      5~8초   치고받고 싸운다 (제일 격렬)
//      8~10초  왼쪽(A집)이 나가떨어진다
//      10~12초 오른쪽(B집)이 승리 세리머니
//
// 🔴 플립북 느낌을 살리려면 **부드럽게 보간하면 안 된다.**
//    초당 8프레임으로 끊어 그린다(Math.floor).
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";

const INK = "rgba(255,255,255,0.5)";
const S = {
  stroke: INK,
  strokeWidth: 6,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  fill: "none",
};

// 졸라맨 하나 — 위치·팔각도·기울기만 받는다
const Man = ({ x, y = 0, rot = 0, armL, armR, legs, face = "기본", flip = false }) => (
  <g transform={`translate(${x},${y}) rotate(${rot} 0 90) scale(${flip ? -1 : 1},1)`}>
    <circle cx="0" cy="0" r="18" {...S} />
    {face === "화남" && <path d="M-11 -7 L-3 -2 M11 -7 L3 -2" {...S} strokeWidth={5} />}
    {face === "화남" && <path d="M-7 9 q7 -5 14 0" {...S} strokeWidth={5} />}
    {face === "기본" && <path d="M-7 6 q7 5 14 0" {...S} strokeWidth={5} />}
    {face === "뻗음" && <path d="M-9 -4 L-3 2 M-3 -4 L-9 2 M3 -4 L9 2 M9 -4 L3 2" {...S} strokeWidth={4} />}
    <path d="M0 18 L0 90" {...S} />
    <path d={armL} {...S} />
    <path d={armR} {...S} />
    <path d={legs} {...S} />
  </g>
);

const STAND = { armL: "M0 40 L-26 62", armR: "M0 40 L26 62", legs: "M0 90 L-18 128 M0 90 L18 128" };
const WALK = [
  { armL: "M0 40 L-28 56", armR: "M0 40 L22 66", legs: "M0 90 L-24 126 M0 90 L14 130" },
  { armL: "M0 40 L-22 66", armR: "M0 40 L28 56", legs: "M0 90 L-14 130 M0 90 L24 126" },
];
const POINT = { armL: "M0 40 L-24 60", armR: "M0 36 L44 30", legs: "M0 90 L-18 128 M0 90 L18 128" };
const PUNCH = [
  { armL: "M0 40 L-24 60", armR: "M0 34 L52 22", legs: "M0 90 L-22 128 M0 90 L16 128" },
  { armL: "M0 36 L-40 26", armR: "M0 44 L28 66", legs: "M0 90 L-14 128 M0 90 L22 128" },
];
const CHEER = [
  { armL: "M0 38 L-30 4", armR: "M0 38 L30 4", legs: "M0 90 L-20 128 M0 90 L20 128" },
  { armL: "M0 38 L-26 -6", armR: "M0 38 L26 -6", legs: "M0 90 L-14 124 M0 90 L14 124" },
];

// 쓰러진 자세
const DOWN = { armL: "M0 40 L-34 30", armR: "M0 40 L30 40", legs: "M0 90 L-24 96 M0 90 L24 84" };

export const DoodleStory = ({ width = 980, flipFps = 8 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps; // 초
  const f = Math.floor(t * flipFps); // 플립 프레임 번호

  // 무대 좌표: 왼쪽 -190 ~ 오른쪽 190
  let L, R;

  if (t < 2) {
    // ① 등장 — 양쪽 끝에서 걸어온다
    const p = t / 2;
    const w = WALK[f % 2];
    L = { x: -330 + p * 150, ...w, face: "기본" };
    R = { x: 330 - p * 150, ...w, face: "기본", flip: true };
  } else if (t < 5) {
    // ② 신경전 — 삿대질
    const p = (t - 2) / 3;
    const bob = (f % 2) * 4;
    L = { x: -180 + p * 30, y: bob, ...POINT, face: "화남" };
    R = { x: 180 - p * 30, y: -bob, ...POINT, face: "화남", flip: true };
  } else if (t < 8) {
    // ③ 난투 — 제일 격렬. 몸이 앞뒤로 튄다
    const k = f % 2;
    const jab = k ? 18 : -6;
    L = { x: -150 + jab, y: k ? -6 : 6, ...PUNCH[k], face: "화남" };
    R = { x: 150 - jab, y: k ? 6 : -6, ...PUNCH[1 - k], face: "화남", flip: true };
  } else if (t < 10) {
    // ④ A집 KO — 왼쪽이 뒤로 나가떨어진다
    const p = Math.min((t - 8) / 1.2, 1);
    L = { x: -150 - p * 130, y: p * 40, rot: -70 * p, ...DOWN, face: "뻗음" };
    R = { x: 150, ...STAND, face: "기본", flip: true };
  } else {
    // ⑤ B집 승리 — 만세
    const c = CHEER[f % 2];
    L = { x: -280, y: 40, rot: -70, ...DOWN, face: "뻗음" };
    R = { x: 120, ...c, face: "기본" };
  }

  return (
    <svg
      width={width}
      height={width * 0.28}
      viewBox="-400 -40 800 220"
      style={{ overflow: "visible" }}
    >
      <Man {...L} />
      <Man {...R} />
      {/* 바닥선 — 무대처럼 */}
      <path d="M-380 132 L380 132" {...S} strokeWidth={4} opacity={0.5} />
      {/* 난투 중엔 충돌 별표 */}
      {t >= 5 && t < 8 && f % 2 === 0 && (
        <g transform="translate(0,20)">
          <path d="M-16 -16 L16 16 M16 -16 L-16 16 M0 -22 L0 22 M-22 0 L22 0" {...S} strokeWidth={5} />
        </g>
      )}
    </svg>
  );
};
