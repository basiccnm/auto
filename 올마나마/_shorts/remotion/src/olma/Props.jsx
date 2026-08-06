// 소품 — 올마·나마가 손에 들거나 몸에 붙이는 것들 (2026-07-21)
//
// 🔴 68편 내내 돌려 쓰는 자산이다. 메뉴가 바뀌어도 이것들은 그대로다.
// 🔴 이모지 금지 — 렌더 환경 폰트에 따라 별표로 깨진다. 전부 SVG로 그린다.
// 🔴 손에 쥐는 소품은 Olma/Nama의 holdR·holdL로 넘긴다.
//    그래야 팔이 회전해도 안 어긋난다(밖에서 좌표로 맞추면 매번 틀어진다).
//    holdR은 (hx, hy)를 받는 함수다 → (x,y) => <Calculator x={x} y={y} />
import React from "react";

const LINE = "#000";
const LW = 6;

// 손에 쥐는 소품 공통 — 손 좌표를 받아 그 자리에 놓는다
const Held = ({ x, y, w, h, vb, children, dx = 0, dy = 0, rot = 0 }) => (
  <g style={{ translate: `${x - w / 2 + dx}px ${y - h / 2 + dy}px` }}>
    <svg viewBox={vb} width={w} height={h} style={{ overflow: "visible", rotate: `${rot}deg` }}>
      {children}
    </svg>
  </g>
);

// ── 안경 — 나마 얼굴에 붙인다. tilt를 주면 삐뚤어진다(부딪힌 뒤)
export const Glasses = ({ tilt = 0 }) => (
  <g style={{ transformBox: "view-box", transformOrigin: "200px 152px", rotate: `${tilt}deg` }}>
    <circle cx={168} cy={152} r={34} fill="#fff" opacity={0.35} stroke={LINE} strokeWidth={LW} />
    <circle cx={232} cy={152} r={34} fill="#fff" opacity={0.35} stroke={LINE} strokeWidth={LW} />
    <path d="M202 150 h-4 M198 150 q4 -6 8 0" stroke={LINE} strokeWidth={LW} fill="none" />
    <path d="M134 148 l-24 -8 M266 148 l24 -8" stroke={LINE} strokeWidth={LW} strokeLinecap="round" />
    {/* 렌즈 반사 */}
    <path d="M152 138 l14 -8" stroke="#fff" strokeWidth={7} strokeLinecap="round" opacity={0.9} />
    <path d="M216 138 l14 -8" stroke="#fff" strokeWidth={7} strokeLinecap="round" opacity={0.9} />
  </g>
);

// ── 자(Ruler) — 올마 손등 때리는 것
export const Ruler = ({ x = 0, y = 0, rot = 0 }) => (
  <Held x={x} y={y} w={190} h={40} vb="0 0 190 40" rot={rot}>
    <rect x={2} y={8} width={186} height={24} rx={5} fill="#FFD24A" stroke={LINE} strokeWidth={5} />
    {[30, 60, 90, 120, 150].map((v) => (
      <path key={v} d={`M${v} 8 v10`} stroke={LINE} strokeWidth={4} />
    ))}
  </Held>
);

// ── 계산기 — 나마의 상징. 팩트 폭격기
export const Calculator = ({ x = 0, y = 0, rot = 0, lit = false }) => (
  <Held x={x} y={y} w={130} h={170} vb="0 0 130 170" rot={rot}>
    <rect x={4} y={4} width={122} height={162} rx={14} fill="#4A4A4A" stroke={LINE} strokeWidth={LW} />
    {/* 액정 */}
    <rect x={18} y={18} width={94} height={38} rx={6} fill={lit ? "#B6F5A0" : "#CFE8D8"} stroke={LINE} strokeWidth={4} />
    {/* 버튼 */}
    {[0, 1, 2, 3].map((r) =>
      [0, 1, 2].map((c) => (
        <rect
          key={`${r}${c}`}
          x={20 + c * 32}
          y={68 + r * 24}
          width={24}
          height={17}
          rx={4}
          fill={r === 3 && c === 2 ? "#E5352B" : "#DDD"}
          stroke={LINE}
          strokeWidth={3}
        />
      ))
    )}
  </Held>
);

// ── 단가표 표지판 — 올마 얼굴에 붙이는 팩트
export const PriceBoard = ({ x = 0, y = 0, rot = -6, line1 = "수입산", line2 = "냉장" }) => (
  <Held x={x} y={y} w={230} h={150} vb="0 0 230 150" rot={rot}>
    <rect x={4} y={4} width={222} height={112} rx={10} fill="#fff" stroke={LINE} strokeWidth={LW} />
    <path d="M115 116 v30" stroke={LINE} strokeWidth={8} strokeLinecap="round" />
    <text x={115} y={50} textAnchor="middle" fontSize={34} fontWeight="900" fill="#B3121B">
      {line1}
    </text>
    <text x={115} y={92} textAnchor="middle" fontSize={34} fontWeight="900" fill={LINE}>
      {line2}
    </text>
  </Held>
);

// ── 돋보기
export const Magnifier = ({ x = 0, y = 0, rot = 0 }) => (
  <Held x={x} y={y} w={140} h={160} vb="0 0 140 160" rot={rot}>
    <circle cx={62} cy={58} r={46} fill="#DCEAF0" opacity={0.6} stroke={LINE} strokeWidth={LW} />
    <path d="M95 92 l34 46" stroke={LINE} strokeWidth={14} strokeLinecap="round" />
    <path d="M44 40 l16 -10" stroke="#fff" strokeWidth={8} strokeLinecap="round" opacity={0.9} />
  </Held>
);

// ── 도장 — "그냥 밀가루" 이마에 쾅
export const StampTool = ({ x = 0, y = 0, rot = 0 }) => (
  <Held x={x} y={y} w={120} h={150} vb="0 0 120 150" rot={rot}>
    <rect x={40} y={4} width={40} height={54} rx={10} fill="#8A4C1E" stroke={LINE} strokeWidth={LW} />
    <rect x={16} y={56} width={88} height={30} rx={8} fill="#C8955A" stroke={LINE} strokeWidth={LW} />
    <rect x={24} y={86} width={72} height={40} rx={6} fill="#E5352B" stroke={LINE} strokeWidth={LW} />
  </Held>
);

// ── 꿀벌 인형 — 허니소스 놀리기용
// 🔴 줄무늬가 몸 밖으로 삐져나가고 크기도 작았다(2026-07-21).
//    줄무늬를 clipPath로 몸 안에 가두고, 전체를 키운다.
export const BeeToy = ({ x = 0, y = 0, rot = 0 }) => (
  <Held x={x} y={y} w={200} h={170} vb="0 0 200 170" rot={rot}>
    <defs>
      <clipPath id="beebody">
        <ellipse cx={100} cy={104} rx={62} ry={44} />
      </clipPath>
    </defs>
    {/* 날개 */}
    <ellipse cx={72} cy={44} rx={32} ry={20} fill="#DCEAF0" stroke={LINE} strokeWidth={5} opacity={0.92} />
    <ellipse cx={128} cy={44} rx={32} ry={20} fill="#DCEAF0" stroke={LINE} strokeWidth={5} opacity={0.92} />
    {/* 몸 */}
    <ellipse cx={100} cy={104} rx={62} ry={44} fill="#FFD24A" stroke={LINE} strokeWidth={LW} />
    <g clipPath="url(#beebody)">
      <path d="M84 56 v96 M118 56 v96" stroke={LINE} strokeWidth={14} />
    </g>
    {/* 눈 + 더듬이 */}
    <circle cx={56} cy={96} r={6} fill={LINE} />
    <path d="M78 62 l-10 -18 M104 60 l6 -20" stroke={LINE} strokeWidth={5} strokeLinecap="round" />
  </Held>
);

// ── 이쑤시개 (치킨무 한 조각 꽂힌)
// 🔴 무 조각이 너무 작아 뭘 찍었는지 안 보였다(2026-07-21). 크게 키운다.
export const Toothpick = ({ x = 0, y = 0, rot = 0 }) => (
  <Held x={x} y={y} w={120} h={180} vb="0 0 120 180" rot={rot}>
    <path d="M60 8 v92" stroke="#C8955A" strokeWidth={8} strokeLinecap="round" />
    {/* 치킨무 한 조각 — 네모나고 두툼하게 */}
    <rect x={16} y={92} width={88} height={68} rx={10} fill="#fff" stroke={LINE} strokeWidth={LW} />
    <path d="M30 112 h60 M30 134 h60" stroke="#CFE0E6" strokeWidth={6} strokeLinecap="round" />
  </Held>
);

// ── 귀마개 — 화산 폭발 대비. 머리에 붙인다
export const EarMuffs = () => (
  <g>
    <path d="M120 130 q80 -54 160 0" fill="none" stroke={LINE} strokeWidth={12} strokeLinecap="round" />
    <ellipse cx={116} cy={152} rx={26} ry={32} fill="#E5352B" stroke={LINE} strokeWidth={LW} />
    <ellipse cx={284} cy={152} rx={26} ry={32} fill="#E5352B" stroke={LINE} strokeWidth={LW} />
  </g>
);

// ── 우산 — 화산재 막기. open 0~1로 펴진다
// 🔴 1차는 곡선 두 개를 이어 붙여 **박쥐 날개**처럼 갈라져 보였다(2026-07-21).
//    지붕은 **반원 돔(arc) 한 번**으로 그리고, 아래 가장자리만 물결로 판다.
export const Umbrella = ({ x = 0, y = 0, rot = 0, open = 1 }) => {
  const rx = 20 + 100 * open; // 펴질수록 넓어진다
  const ry = 16 + 62 * open; //  높이도 같이
  const L0 = 130 - rx;
  const R0 = 130 + rx;
  const s = (rx * 2) / 4; // 물결 4칸
  return (
    <Held x={x} y={y} w={280} h={230} vb="0 0 280 230" rot={rot}>
      <path
        d={
          `M${L0} 100 A${rx} ${ry} 0 0 1 ${R0} 100 ` +
          `q${-s / 2} ${20 * open} ${-s} 0 ` +
          `q${-s / 2} ${20 * open} ${-s} 0 ` +
          `q${-s / 2} ${20 * open} ${-s} 0 ` +
          `q${-s / 2} ${20 * open} ${-s} 0 z`
        }
        fill="#E5352B"
        stroke={LINE}
        strokeWidth={LW}
        strokeLinejoin="round"
      />
      {/* 살 — 돔 한가운데를 가르는 선 두 개. 우산처럼 보이게 하는 핵심 */}
      <path d={`M130 ${100 - ry} v${ry + 4}`} stroke={LINE} strokeWidth={4} opacity={0.45} />
      <path d={`M${130 - rx / 2} ${100 - ry * 0.72} L130 104`} stroke={LINE} strokeWidth={4} opacity={0.45} />
      <path d={`M${130 + rx / 2} ${100 - ry * 0.72} L130 104`} stroke={LINE} strokeWidth={4} opacity={0.45} />
      {/* 대 + 손잡이 */}
      <path d="M130 104 v92 q0 22 -22 22" fill="none" stroke={LINE} strokeWidth={10} strokeLinecap="round" />
      <circle cx={130} cy={100 - ry} r={7} fill={LINE} />
    </Held>
  );
};

// ── 지휘봉 — 나마가 올마를 가리킬 때
export const Pointer = ({ x = 0, y = 0, rot = 0 }) => (
  <Held x={x} y={y} w={200} h={40} vb="0 0 200 40" rot={rot}>
    <path d="M10 20 h160" stroke={LINE} strokeWidth={8} strokeLinecap="round" />
    <circle cx={182} cy={20} r={12} fill="#E5352B" stroke={LINE} strokeWidth={5} />
    <rect x={2} y={12} width={22} height={16} rx={5} fill="#4A4A4A" stroke={LINE} strokeWidth={4} />
  </Held>
);

// ── 표지판 — "댓글로 알려줘"
export const SignBoard = ({ x = 0, y = 0, rot = -5, text = "댓글로 알려줘" }) => (
  <Held x={x} y={y} w={300} h={180} vb="0 0 300 180" rot={rot}>
    <rect x={4} y={4} width={292} height={110} rx={14} fill="#FFD400" stroke={LINE} strokeWidth={LW} />
    <path d="M150 114 v58" stroke={LINE} strokeWidth={10} strokeLinecap="round" />
    <text x={150} y={72} textAnchor="middle" fontSize={38} fontWeight="900" fill={LINE}>
      {text}
    </text>
  </Held>
);
