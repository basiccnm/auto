// 재료 그림 — 원가 장면에서 하나씩 떨어지는 것들
//
// 🔴 글씨만 있으면 "아무것도 안 하는" 화면이 된다(2026-07-21 지적).
//    재료마다 **그림 + 그 재료다운 사고**가 있어야 5초를 버틴다.
// 🔴 68편 내내 돌려 쓰는 자산이다. 메뉴가 바뀌면 여기 아이콘만 추가하면 된다.
// 🔴 이모지 금지 — 렌더 환경 폰트에 따라 별표로 깨진다. 전부 SVG로 그린다.
import React from "react";
import { interpolate, random, useCurrentFrame, Easing } from "remotion";

import { Drumstick } from "./Table";

const LINE = "#000";
const LW = 7;
const E = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };

// ── ① 닭 정육(윙·봉) — 덩어리로 쿵
export const MeatChunk = ({ w = 420 }) => (
  <svg viewBox="0 0 420 300" width={w} style={{ overflow: "visible" }}>
    {/* 스티로폼 트레이 */}
    <path d="M30 210 L390 210 L370 280 L50 280 Z" fill="#F2F2F2" stroke={LINE} strokeWidth={LW} strokeLinejoin="round" />
    <path d="M30 210 L390 210" stroke={LINE} strokeWidth={LW} strokeLinecap="round" />
    {/* 고기 덩어리 — 봉·윙이 쌓임 */}
    <g>
      <Drumstick x={120} y={150} rot={-24} scale={0.9} />
      <Drumstick x={250} y={155} rot={20} scale={0.88} />
      <Drumstick x={186} y={110} rot={-4} scale={0.82} />
    </g>
    {/* 무게 라벨 */}
    <rect x={140} y={228} width={140} height={40} rx={8} fill="#fff" stroke={LINE} strokeWidth={5} />
    <text x={210} y={258} textAnchor="middle" fontSize={30} fontWeight="900" fill={LINE}>
      1kg
    </text>
  </svg>
);

// ── ② 치킨 브레딩믹스 — 가루 봉지. 터지면서 가루가 뿜어져 나온다
export const FlourBag = ({ w = 300, burst = 0 }) => (
  <svg viewBox="0 0 300 360" width={w} style={{ overflow: "visible" }}>
    {/* 봉지 */}
    <path
      d="M40 60 L260 60 L250 340 L50 340 Z"
      fill="#EFE3C8"
      stroke={LINE}
      strokeWidth={LW}
      strokeLinejoin="round"
    />
    {/* 접힌 윗부분 */}
    <path d="M40 60 L60 20 L240 20 L260 60 Z" fill="#DCCBA6" stroke={LINE} strokeWidth={LW} strokeLinejoin="round" />
    {/* 라벨 */}
    <rect x={72} y={140} width={156} height={92} rx={12} fill="#fff" stroke={LINE} strokeWidth={5} />
    <text x={150} y={180} textAnchor="middle" fontSize={30} fontWeight="900" fill="#B3121B">
      브레딩
    </text>
    <text x={150} y={214} textAnchor="middle" fontSize={26} fontWeight="900" fill={LINE}>
      180g
    </text>
    {/* 터져 나오는 가루 */}
    {burst > 0 &&
      Array.from({ length: 14 }, (_, i) => {
        const a = (i / 14) * Math.PI * 2;
        const d = 40 + burst * 150 * (0.5 + random(`fb${i}`));
        return (
          <circle
            key={i}
            cx={150 + Math.cos(a) * d}
            cy={40 + Math.sin(a) * d * 0.7}
            r={8 + random(`fr${i}`) * 12}
            fill="#F6EEDC"
            stroke={LINE}
            strokeWidth={3}
            opacity={1 - burst}
          />
        );
      })}
  </svg>
);

// ── ③ 식용유 — 기름통 + 끓는 기름방울
export const OilCan = ({ w = 260, boil = 0 }) => (
  <svg viewBox="0 0 260 380" width={w} style={{ overflow: "visible" }}>
    {/* 통 */}
    <rect x={40} y={90} width={180} height={250} rx={18} fill="#FFD24A" stroke={LINE} strokeWidth={LW} />
    {/* 목 + 뚜껑 */}
    <rect x={104} y={40} width={52} height={56} rx={8} fill="#FFD24A" stroke={LINE} strokeWidth={LW} />
    <rect x={94} y={18} width={72} height={30} rx={8} fill="#C8102E" stroke={LINE} strokeWidth={LW} />
    {/* 라벨 */}
    <rect x={66} y={160} width={128} height={104} rx={12} fill="#fff" stroke={LINE} strokeWidth={5} />
    <text x={130} y={200} textAnchor="middle" fontSize={30} fontWeight="900" fill="#B3121B">
      식용유
    </text>
    <text x={130} y={240} textAnchor="middle" fontSize={26} fontWeight="900" fill={LINE}>
      142ml
    </text>
    {/* 끓어오르는 기름방울 */}
    {boil > 0 &&
      Array.from({ length: 9 }, (_, i) => {
        const p = (boil + random(`ob${i}`)) % 1;
        return (
          <circle
            key={i}
            cx={60 + random(`ox${i}`) * 140}
            cy={90 - p * 120}
            r={7 + random(`or${i}`) * 9}
            fill="#FFE9A8"
            stroke={LINE}
            strokeWidth={3}
            opacity={1 - p}
          />
        );
      })}
  </svg>
);

// ── ④ 허니 간장소스 — 통 + 붓. 이 편의 주인공
export const SauceTub = ({ w = 320, spill = 0 }) => (
  <svg viewBox="0 0 320 360" width={w} style={{ overflow: "visible" }}>
    {/* 통 */}
    <path d="M50 110 L270 110 L250 330 L70 330 Z" fill="#6B3A16" stroke={LINE} strokeWidth={LW} strokeLinejoin="round" />
    {/* 뚜껑 */}
    <rect x={38} y={78} width={244} height={40} rx={10} fill="#8A4C1E" stroke={LINE} strokeWidth={LW} />
    {/* 라벨 */}
    <rect x={84} y={160} width={152} height={104} rx={12} fill="#fff" stroke={LINE} strokeWidth={5} />
    <text x={160} y={198} textAnchor="middle" fontSize={28} fontWeight="900" fill="#6B3A16">
      허니 간장
    </text>
    <text x={160} y={238} textAnchor="middle" fontSize={26} fontWeight="900" fill={LINE}>
      200g
    </text>
    {/* 쏟아지는 소스 */}
    {spill > 0 && (
      <path
        d={`M270 130 q40 ${40 * spill} 20 ${160 * spill}`}
        fill="none"
        stroke="#8A4C1E"
        strokeWidth={22 * spill}
        strokeLinecap="round"
        opacity={0.95}
      />
    )}
  </svg>
);

// ── 붓 — "붓으로 하나하나 발라서"의 그 붓
export const Brush = ({ w = 200, angle = 0 }) => (
  <svg viewBox="0 0 200 320" width={w} style={{ overflow: "visible", rotate: `${angle}deg` }}>
    {/* 손잡이 */}
    <rect x={82} y={10} width={36} height={180} rx={14} fill="#C8955A" stroke={LINE} strokeWidth={LW} />
    {/* 금속 물림쇠 */}
    <rect x={74} y={186} width={52} height={34} rx={6} fill="#BDC3C7" stroke={LINE} strokeWidth={5} />
    {/* 붓털 — 소스가 묻어 갈색 */}
    <path d="M76 218 L124 218 L136 300 L64 300 Z" fill="#6B3A16" stroke={LINE} strokeWidth={LW} strokeLinejoin="round" />
  </svg>
);

// ── ⑤ 치킨무 — 통 + 튀는 국물
export const PickleTub = ({ w = 280, splash = 0 }) => (
  <svg viewBox="0 0 280 260" width={w} style={{ overflow: "visible" }}>
    <path d="M30 60 L250 60 L230 230 L50 230 Z" fill="#EAF4F7" stroke={LINE} strokeWidth={LW} strokeLinejoin="round" opacity={0.95} />
    <ellipse cx={140} cy={60} rx={110} ry={22} fill="#DCEAF0" stroke={LINE} strokeWidth={LW} />
    {/* 무 조각들 */}
    {[
      [92, 110],
      [150, 96],
      [186, 130],
      [110, 156],
      [166, 168],
    ].map(([x, y], i) => (
      <rect key={i} x={x} y={y} width={44} height={40} rx={7} fill="#fff" stroke={LINE} strokeWidth={5} />
    ))}
    {/* 튀는 국물 */}
    {splash > 0 &&
      Array.from({ length: 8 }, (_, i) => {
        const a = -Math.PI / 2 + (i - 4) * 0.28;
        const d = splash * 150;
        return (
          <ellipse
            key={i}
            cx={140 + Math.cos(a) * d}
            cy={60 + Math.sin(a) * d}
            rx={9}
            ry={13}
            fill="#DCEAF0"
            stroke={LINE}
            strokeWidth={3}
            opacity={1 - splash}
          />
        );
      })}
  </svg>
);

// 재료 인덱스 → 그림. config의 items 순서와 1:1.
// 🔴 진행도(0~1)를 받아 저마다 다른 사고를 친다.
export const IngredientArt = ({ i, p = 0 }) => {
  switch (i) {
    case 0:
      return <MeatChunk />;
    case 1:
      return <FlourBag burst={interpolate(p, [0.1, 0.6], [0, 1], E)} />;
    case 2:
      return <OilCan boil={p} />;
    case 3:
      return <SauceTub spill={interpolate(p, [0.15, 0.5], [0, 1], E)} />;
    case 4:
      return <PickleTub splash={interpolate(p, [0.1, 0.55], [0, 1], E)} />;
    default:
      return null;
  }
};
