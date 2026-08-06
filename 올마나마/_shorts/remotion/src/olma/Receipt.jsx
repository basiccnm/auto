// 영수증 — 훅에서 올마 얼굴로 날아와 찰싹 붙는 소품
//
// 🔴 실사 이미지 안 쓴다. 올마·식탁과 같은 그림체(두꺼운 검은 선)로 그려야 톤이 안 깨진다.
// 🔴 아랫단은 톱니(지그재그) — 이게 있어야 한눈에 "영수증"으로 읽힌다.
import React from "react";
import { BLACK, JUA } from "../shorts/fonts";
import { OLMA, MOUTHS } from "./Olma";

const LINE = "#000";

// 올마 얼굴 로고 — 영수증 맨 아래 도장처럼 찍는다
const OlmaMark = ({ cx, cy, r }) => (
  <g>
    <circle cx={cx} cy={cy} r={r} fill={OLMA.head} stroke={LINE} strokeWidth={r * 0.13} />
    <circle cx={cx - r * 0.32} cy={cy - r * 0.12} r={r * 0.12} fill={LINE} />
    <circle cx={cx + r * 0.32} cy={cy - r * 0.12} r={r * 0.12} fill={LINE} />
    <path
      d={`M${cx - r * 0.3} ${cy + r * 0.24} q${r * 0.3} ${r * 0.3} ${r * 0.6} 0`}
      fill="none"
      stroke={LINE}
      strokeWidth={r * 0.1}
      strokeLinecap="round"
    />
  </g>
);

// 🔴 종이를 **한 덩어리 path**로 그린다. 위아래 모두 핑킹가위 자국(톱니)(2026-07-21 지시).
//    예전처럼 사각형 + 아래 톱니를 따로 겹치면 이음매가 지저분하게 보인다.
const paper = (x0, y0, w, h, step = 26, tooth = 16) => {
  const n = Math.floor(w / step);
  const s = w / n; // 폭에 딱 맞게 나눈다 (자투리 없이)
  let d = `M${x0} ${y0}`;
  for (let i = 0; i < n; i++) d += ` l${s / 2} ${-tooth} l${s / 2} ${tooth}`; // 위쪽 톱니
  d += ` L${x0 + w} ${y0 + h}`;
  for (let i = 0; i < n; i++) d += ` l${-s / 2} ${tooth} l${-s / 2} ${-tooth}`; // 아래쪽 톱니
  return d + " Z";
};

export const Receipt = ({ brand = "BBQ", menu = "황금올리브", price = 23000, width = 460, hook = "" }) => {
  // 🔴 아래에 훅 문구가 들어가므로 세로로 길게(2026-07-21)
  const W = 520, H = 660;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={width} xmlns="http://www.w3.org/2000/svg" style={{ overflow: "visible" }}>
      {/* 종이 — 위아래 핑킹가위 자국 */}
      <path
        d={paper(12, 34, W - 24, H - 68)}
        fill="#FFFDF5"
        stroke={LINE}
        strokeWidth={8}
        strokeLinejoin="round"
      />

      {/* 🔴 이 화면이 그대로 썸네일이 된다(2026-07-21).
          영수증 안이 비면 허술해 보이므로 **글자를 키워 안쪽을 꽉 채운다.** */}
      <text x={W / 2} y={106} textAnchor="middle" fontFamily={BLACK} fontSize={54} fill={LINE}>
        {brand}
      </text>
      <text x={W / 2} y={186} textAnchor="middle" fontFamily={BLACK} fontSize={80} fill={LINE} letterSpacing={-3}>
        {menu}
      </text>

      <line x1={40} y1={238} x2={W - 40} y2={238} stroke={LINE} strokeWidth={5} strokeDasharray="16 13" />

      {/* 합계 — "원"은 숫자 바로 옆에. 바코드는 뺐다(시선만 뺏음) */}
      <text x={W / 2} y={318} textAnchor="middle" fontFamily={BLACK} fontSize={92} fill="#E5352B" letterSpacing={-3}>
        {price.toLocaleString()}
        <tspan fontSize={48} fill={LINE}> 원</tspan>
      </text>

      <line x1={40} y1={374} x2={W - 40} y2={374} stroke={LINE} strokeWidth={5} strokeDasharray="16 13" />

      {/* 훅 — 채널 시그니처. 🔴 짧을수록 크게 쓸 수 있다(2026-07-21).
          위에 금액이 있으니 "이거 팔아"가 없어도 뜻이 통한다. 매 편 같은 자리에 박아 각인시킨다.
          종이 폭(520)을 넘으면 화면 밖으로 삐져나가니 여백 안에 들어오는 크기로. */}
      {/* 🔴 흰 종이 위 검정 글씨는 밋밋하다. 형광펜을 칠한 것처럼 만들면
          "영수증 보다가 표시해둔" 느낌이 나서 스토리도 맞고 눈에도 확 띈다(2026-07-21). */}
      {hook && (
        <>
          {/* 형광펜 — 글자 아래쪽 절반만 덮는다(실제로 형광펜 그은 느낌) */}
          <rect x={64} y={434} width={W - 128} height={54} fill="#FFD400" rx={6} />
          <text
            x={W / 2}
            y={478}
            textAnchor="middle"
            fontFamily={BLACK}
            fontSize={104}
            fill={LINE}
            letterSpacing={-5}
          >
            {hook}
          </text>
        </>
      )}

      {/* 브랜드 마크 — 영수증 맨 아래 도장처럼. 사이트 주소를 같이 박아 유입을 만든다.
          🔴 로고+주소를 한 덩어리로 보고 가운데 정렬한다(2026-07-21). */}
      <OlmaMark cx={W / 2 - 148} cy={566} r={24} />
      <text x={W / 2 + 30} y={578} textAnchor="middle" fontFamily={BLACK} fontSize={34} fill={LINE} letterSpacing={-1}>
        olmanama.com
      </text>
    </svg>
  );
};
