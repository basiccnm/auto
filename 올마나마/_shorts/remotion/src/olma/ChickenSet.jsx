// 치킨 세트 — 박스 + 콜라 + 치킨무
//
// 🔴 접시에 담긴 치킨은 "배달 치킨"으로 안 읽힌다(2026-07-21 "박스에 담겨져 있고 옆에 콜라,
//    치킨무 플라스틱").  실제로 시켜 먹는 모습이라야 시청자가 자기 얘기로 받아들인다.
// 🔴 브랜드명은 config에서 받는다. 메뉴가 바뀌면 박스 로고도 따라간다.
import React from "react";
import { Drumstick } from "./Table";

const LINE = "#000";
const LW = 7;

// ── 치킨 박스 (뚜껑 열린 상태, 치킨이 담김)
// 🔴 박스 색은 config의 CFG.box에서 받는다(2026-07-21 지시).
//    브랜드마다 색이 같으면 "그 브랜드"로 안 읽힌다. 기본값은 예전 BBQ 빨강.
const BOX_DEFAULT = { body: "#E5352B", lid: "#D64B3F", logo: "#E5352B" };

export const ChickenBox = ({ brand = "BBQ", x = 0, y = 0, w = 460, box }) => {
  const c = { ...BOX_DEFAULT, ...(box || {}) };
  return (
  <g style={{ translate: `${x}px ${y}px` }}>
    {/* 열린 뚜껑 — 뒤로 젖혀져 있다 */}
    <path
      d={`M40 90 L${w - 40} 90 L${w - 76} -46 L76 -46 Z`}
      fill={c.lid}
      stroke={LINE}
      strokeWidth={LW}
      strokeLinejoin="round"
    />
    <text
      x={w / 2}
      y={26}
      textAnchor="middle"
      fontSize={62}
      fontWeight="900"
      fill="#fff"
      style={{ letterSpacing: 2 }}
    >
      {brand}
    </text>

    {/* 박스 안 치킨 — 박스보다 먼저 그려 담긴 것처럼 */}
    <g>
      <Drumstick x={w * 0.3} y={128} rot={-18} scale={0.72} />
      <Drumstick x={w * 0.7} y={130} rot={16} scale={0.7} />
      <Drumstick x={w * 0.5} y={106} rot={-2} scale={0.66} />
    </g>

    {/* 박스 앞면 */}
    <path
      d={`M14 150 L${w - 14} 150 L${w - 40} 300 L40 300 Z`}
      fill={c.body}
      stroke={LINE}
      strokeWidth={LW}
      strokeLinejoin="round"
    />
    {/* 박스 윗테두리 */}
    <path d={`M14 150 L${w - 14} 150`} stroke={LINE} strokeWidth={LW} strokeLinecap="round" />
    {/* 로고 띠 */}
    <rect x={w * 0.22} y={192} width={w * 0.56} height={62} rx={10} fill="#fff" stroke={LINE} strokeWidth={5} />
    <text x={w / 2} y={238} textAnchor="middle" fontSize={46} fontWeight="900" fill={c.logo}>
      {brand}
    </text>
  </g>
  );
};

// ── 콜라 페트병
export const Cola = ({ x = 0, y = 0, h = 300 }) => {
  const w = h * 0.34;
  return (
    <g style={{ translate: `${x}px ${y}px` }}>
      {/* 뚜껑 */}
      <rect x={w * 0.3} y={0} width={w * 0.4} height={26} rx={5} fill="#D64B3F" stroke={LINE} strokeWidth={LW - 1} />
      {/* 목 */}
      <path
        d={`M${w * 0.34} 24 L${w * 0.34} 44 Q${w * 0.34} 62 ${w * 0.16} 74
            L${w * 0.16} ${h - 16} Q${w * 0.16} ${h} ${w * 0.36} ${h}
            L${w * 0.64} ${h} Q${w * 0.84} ${h} ${w * 0.84} ${h - 16}
            L${w * 0.84} 74 Q${w * 0.66} 62 ${w * 0.66} 44 L${w * 0.66} 24 Z`}
        fill="#3A2A22"
        stroke={LINE}
        strokeWidth={LW}
        strokeLinejoin="round"
      />
      {/* 라벨 */}
      <rect x={w * 0.14} y={h * 0.42} width={w * 0.72} height={h * 0.26} fill="#E5352B" stroke={LINE} strokeWidth={5} />
      {/* 빛 반사 */}
      <rect x={w * 0.26} y={h * 0.16} width={7} height={h * 0.2} rx={4} fill="#fff" opacity={0.45} />
    </g>
  );
};

// ── 치킨무 플라스틱 통
export const Pickle = ({ x = 0, y = 0, w = 190 }) => {
  const h = w * 0.62;
  return (
    <g style={{ translate: `${x}px ${y}px` }}>
      {/* 통 */}
      <path
        d={`M6 14 L${w - 6} 14 L${w - 20} ${h} L20 ${h} Z`}
        fill="#F2F6F2"
        stroke={LINE}
        strokeWidth={LW}
        strokeLinejoin="round"
        opacity={0.95}
      />
      {/* 안에 든 무 — 하얀 네모들 */}
      {[
        [w * 0.28, h * 0.5],
        [w * 0.52, h * 0.44],
        [w * 0.72, h * 0.52],
        [w * 0.4, h * 0.7],
        [w * 0.62, h * 0.72],
      ].map(([cx, cy], i) => (
        <rect
          key={i}
          x={cx - 17}
          y={cy - 13}
          width={34}
          height={26}
          rx={5}
          fill="#FFFDF2"
          stroke={LINE}
          strokeWidth={4}
        />
      ))}
      {/* 뚜껑(투명) */}
      <ellipse cx={w / 2} cy={14} rx={w / 2 - 6} ry={13} fill="#DCEAF0" stroke={LINE} strokeWidth={LW} opacity={0.85} />
    </g>
  );
};

// ── 세트 전체 — 박스 가운데, 콜라 오른쪽, 치킨무 왼쪽
export const ChickenSet = ({ brand = "BBQ", width = 900, box }) => (
  <svg viewBox="0 0 900 400" width={width} xmlns="http://www.w3.org/2000/svg" style={{ overflow: "visible" }}>
    {/* 치킨무 — 왼쪽 앞 */}
    <Pickle x={30} y={230} w={190} />
    {/* 박스 — 가운데 */}
    <ChickenBox brand={brand} x={215} y={70} w={460} box={box} />
    {/* 콜라 — 오른쪽 */}
    <Cola x={700} y={62} h={300} />
  </svg>
);
