// 플립북 낙서 — 카드 위 여백에 넣는 손그림 애니메이션 (2026-07-24)
//
// 🔴 왜: 카드가 정지 이미지라 영상으로 만들면 심심하다.
//    공책 귀퉁이에 그려 넘기던 플립북처럼, 위 여백에서 졸라맨이 움직인다.
//
// 🔴 진짜 플립북처럼 보이려면 **부드럽게 보간하면 안 된다.**
//    프레임을 뚝뚝 끊어 바꿔야 손으로 넘긴 느낌이 난다 → Math.floor로 프레임 선택.
// 🔴 선은 흰색 반투명. 남색 배경 위에서 분필·볼펜 낙서처럼 보인다.
//    너무 진하면 카드보다 눈에 띄어 주객이 전도된다.
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";

const INK = "rgba(255,255,255,0.55)";

// 공통 선 스타일 — 손그림이니 끝을 둥글게, 굵기는 살짝 굵게
const S = {
  stroke: INK,
  strokeWidth: 7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  fill: "none",
};

// ── 화내기 — 팔을 위아래로 휘두른다 ────────────────────────
// 🔴 팔만 흔들면 단조로워서 몸도 들썩이게 했다(dy를 크게, 다리도 벌린다)
const ANGRY = [
  { armL: "M70 96 L28 52", armR: "M130 96 L172 52", dy: -8, legs: "M100 140 L72 186 M100 140 L128 186" },
  { armL: "M70 96 L24 126", armR: "M130 96 L176 126", dy: 8, legs: "M100 140 L64 182 M100 140 L136 182" },
  { armL: "M70 96 L34 66", armR: "M130 96 L166 66", dy: -3, legs: "M100 140 L76 186 M100 140 L124 186" },
];

const Angry = ({ f }) => {
  const p = ANGRY[f % ANGRY.length];
  return (
    <g transform={`translate(0,${p.dy})`}>
      <circle cx="100" cy="46" r="26" {...S} />
      {/* 성난 눈썹 */}
      <path d="M84 38 L94 44 M116 38 L106 44" {...S} strokeWidth={6} />
      <path d="M90 56 q10 -6 20 0" {...S} strokeWidth={6} />
      <path d="M100 72 L100 140" {...S} />
      <path d={p.armL} {...S} />
      <path d={p.armR} {...S} />
      <path d={p.legs} {...S} />
      {/* 뿜는 김 */}
      <path d="M138 26 q10 -12 2 -22 M156 34 q12 -10 6 -22" {...S} strokeWidth={5} />
    </g>
  );
};

// ── 계산 — 허리 숙여 계산기를 두드린다 ─────────────────────
// 🔴 두 프레임 차이가 거의 없어 안 움직여 보였다 — 팔을 크게 들었다 내린다
const CALC = [
  { arm: "M100 104 L150 84", dy: -4 },
  { arm: "M100 104 L138 134", dy: 4 },
  { arm: "M100 104 L146 98", dy: 0 },
];

const Calc = ({ f }) => {
  const p = CALC[f % CALC.length];
  return (
    <g transform={`translate(0,${p.dy})`}>
      <circle cx="92" cy="50" r="26" {...S} />
      <path d="M92 76 L100 140" {...S} />
      <path d="M100 104 L62 96" {...S} />
      <path d={p.arm} {...S} />
      <path d="M100 140 L78 186 M100 140 L122 186" {...S} />
      {/* 계산기 */}
      <rect x="128" y="118" width="46" height="60" rx="6" {...S} strokeWidth={6} />
      <path d="M136 132 h30 M136 148 h30 M136 162 h30" {...S} strokeWidth={4} />
    </g>
  );
};

// ── 놀람 — 뒤로 자빠진다 ──────────────────────────────────
const SHOCK = [
  { rot: 0, dy: 0 },
  { rot: -12, dy: 6 },
  { rot: -26, dy: 16 },
  { rot: -12, dy: 6 },
];

const Shock = ({ f }) => {
  const p = SHOCK[f % SHOCK.length];
  return (
    <g transform={`translate(0,${p.dy}) rotate(${p.rot} 100 180)`}>
      <circle cx="100" cy="46" r="26" {...S} />
      {/* 크게 뜬 눈·벌린 입 */}
      <circle cx="91" cy="42" r="4" {...S} strokeWidth={5} />
      <circle cx="109" cy="42" r="4" {...S} strokeWidth={5} />
      <ellipse cx="100" cy="58" rx="7" ry="9" {...S} strokeWidth={5} />
      <path d="M100 72 L100 140" {...S} />
      <path d="M100 96 L58 70 M100 96 L142 70" {...S} />
      <path d="M100 140 L76 186 M100 140 L124 186" {...S} />
      {/* 놀람 표시 */}
      <path d="M150 22 L156 44 M150 52 L150 54" {...S} strokeWidth={6} />
    </g>
  );
};

export const KINDS = { 화내기: Angry, 계산: Calc, 놀람: Shock };
export const FRAMES = { 화내기: ANGRY.length, 계산: CALC.length, 놀람: SHOCK.length };

// 점검 시트용 — 프레임 번호를 직접 넣어 그린다
export const DoodleFrame = ({ kind = "화내기", f = 0, width = 200 }) => {
  const K = KINDS[kind] || Angry;
  return (
    <svg width={width} height={width * 1.1} viewBox="0 0 200 220" style={{ overflow: "visible" }}>
      <K f={f} />
    </svg>
  );
};

/**
 * @param kind  "화내기" | "계산" | "놀람"
 * @param fps   플립 속도(초당 프레임 교체 수). 8이면 공책 넘기는 속도쯤
 */
export const Doodle = ({ kind = "화내기", width = 200, fps = 8 }) => {
  const frame = useCurrentFrame();
  const { fps: videoFps } = useVideoConfig();
  // 🔴 floor로 끊어야 플립북이 된다. 보간하면 매끈해져서 손그림 느낌이 죽는다
  const f = Math.floor((frame / videoFps) * fps);
  const Kind = KINDS[kind] || Angry;
  return (
    <svg width={width} height={width * 1.1} viewBox="0 0 200 220" style={{ overflow: "visible" }}>
      <Kind f={f} />
    </svg>
  );
};
