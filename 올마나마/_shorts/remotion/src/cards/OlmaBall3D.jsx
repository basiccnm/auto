// 올마볼 3D — 카드뉴스용 (2026-07-24)
//
// 🔴 시안(_shorts/bg/Gemini_Generated_Image_2a4rfc...png)의 3D 볼을 **코드로 다시 그린** 것.
//    정본 v2 §2 "AI 생성 이미지 자산 0개, 전부 코드 렌더" 방침을 따른다.
//    이미지를 잘라 쓰면 표정마다 이미지가 새로 필요하다 — 코드면 파라미터로 무한 확장.
//
// 🔴 3D처럼 보이게 하는 건 결국 네 가지다. 하나라도 빠지면 평면으로 보인다.
//      ① 몸통 라디얼 그라데이션 — 광원이 좌상단
//      ② 정반사 하이라이트 — 좌상단에 흰 타원 두 개(큰 것 + 작은 것)
//      ③ 림라이트 — 우하단 가장자리에 옅은 밝은 테. 배경과 분리시킨다
//      ④ 바닥 그림자 — 눌린 타원. 없으면 공중에 뜬다
//
// 🔴 검정 외곽선을 쓰지 않는다. 쇼츠용 폴란드볼(BrandBall.jsx)과 다른 점이 이것.
//    선을 두르는 순간 2D 스티커가 된다.
import React from "react";

// 🔴 색(2026-07-24 지시) — 처음엔 #FFE066~#F0A500이었는데 "노란색으로 보이지 않는다".
//    밝은 쪽이 크림색에 가까워 물 빠진 느낌이었다. 채도를 올려 노랑을 살린다.
//    다만 너무 진하면 주황이 되므로 hi는 아직 밝게 남긴다.
const Y = {
  hi: "#FFD53D", // 광원 쪽
  mid: "#FDB90A",
  lo: "#E89100", // 그늘
  deep: "#CE7D00", // 팔·다리 그늘
};
const INK = "#3D2B12"; // 눈동자·입. 검정보다 갈색이 부드럽다

// ── 표정 ────────────────────────────────────────────────────
// eye: 눈 모양 / mouth: 입 path / brow: 눈썹(없으면 생략)
// 🔴 입 위치(2026-07-24 지시) — 처음엔 y=128 언저리에 뒀더니 "너무 올라와 있다".
//    눈 아래(y≈104)와 너무 붙어 얼굴이 답답했다. y=140~146으로 내려 여백을 준다.
export const FACES = {
  기본: { mouth: "M86 142 q14 12 28 0" },
  // 🔴 2026-07-24 지시: 더 내리고(140→146) 옆으로 길게(폭 36→52)
  웃음: { mouth: "M74 146 q26 22 52 0" },
  놀람: { mouthEllipse: [100, 146, 11, 15], eyeScale: 1.1 },
  화남: {
    mouth: "M84 150 q16 -11 32 0",
    brow: [
      "M60 80 L90 95", // 좌 — 안쪽으로 내려온다
      "M140 80 L110 95",
    ],
  },
  // 🔴 시무룩과 진땀이 입만 거의 같아 구분이 안 됐다(2026-07-24 지적). 성격을 갈랐다.
  //    시무룩 = 눈을 반쯤 감고 아래를 본다. 기운 없음
  //    진땀   = 눈을 크게 뜨고 입이 지그재그로 떨린다. 당황·불안
  //    시무룩 = 눈동자만 아래로 내린다(2026-07-24 지시). 눈꺼풀·눈썹 안 씀
  시무룩: { mouth: "M84 152 q16 -11 32 0", pupilDy: 8 },
  //    눈치 = 입·팔은 기본과 같게 두고(2026-07-24 지시) **눈동자만** 옆위로 굴린다.
  //    딴 데 흘끗 보는 눈 하나로 눈치 보는 게 읽힌다. 원래 "으쓱"이었는데 이름을 바꿨다
  눈치: { mouth: "M86 142 q14 12 28 0", pupilDx: 8, pupilDy: -4 },
  //    계산 = 눈을 대각선 위로. 머릿속으로 셈하는 눈이다(2026-07-24 지시)
  계산: { mouth: "M88 144 h24", pupilDy: -6, pupilDx: 6 },
  진땀: {
    // 지그재그 입 — 파르르 떠는 느낌
    mouth: "M80 148 q8 -9 16 0 t16 0 t16 0",
    eyeScale: 1.06,
    sweat: true,
  },
};

// ── 소품 ────────────────────────────────────────────────────
const ChefHat = () => (
  <g transform="translate(0,-6)">
    <path
      d="M56 44 q-26 -4 -26 -30 q0 -24 28 -24 q4 -21 32 -21 q18 -18 40 0 q28 0 30 21 q28 0 28 24 q0 26 -26 30 z"
      fill="url(#hatG)"
    />
    <rect x="54" y="40" width="92" height="18" rx="8" fill="#E8EAF0" />
  </g>
);

const Calc = () => (
  <g transform="translate(126,150) rotate(-12)">
    <rect x="0" y="0" width="52" height="66" rx="8" fill="#2F3542" />
    <rect x="6" y="6" width="40" height="16" rx="4" fill="#9BE7A0" />
    {[0, 1, 2].map((r) =>
      [0, 1, 2].map((c) => (
        <rect key={r + "-" + c} x={7 + c * 13} y={28 + r * 12} width="9" height="8" rx="2" fill="#5A6272" />
      ))
    )}
  </g>
);

export const OlmaBall3D = ({
  face = "기본",
  prop = null, // "요리사모자" | "계산기"
  size = 420,
  shadow = true,
}) => {
  const F = FACES[face] || FACES.기본;
  const es = F.eyeScale || 1;
  const dx = F.pupilDx || 0; // 눈동자 좌우 — 대각선 시선용
  const dy = F.pupilDy || 0; // 눈동자 상하

  return (
    <svg width={size} height={size * 1.12} viewBox="0 0 200 224" style={{ overflow: "visible" }}>
      <defs>
        {/* ① 몸통 — 광원이 좌상단(35%,28%) */}
        <radialGradient id="bodyG" cx="35%" cy="28%" r="78%">
          <stop offset="0%" stopColor={Y.hi} />
          <stop offset="45%" stopColor={Y.mid} />
          <stop offset="100%" stopColor={Y.lo} />
        </radialGradient>
        {/* ③ 림라이트 — 우하단만 밝게 */}
        {/* 🔴 림라이트를 0.85로 세게 줬더니 노랑이 하얗게 떴다 — 0.5로 낮춘다 */}
        <radialGradient id="rimG" cx="72%" cy="80%" r="52%">
          <stop offset="65%" stopColor="#FFFFFF" stopOpacity="0" />
          <stop offset="100%" stopColor="#FFDE7A" stopOpacity="0.5" />
        </radialGradient>
        <linearGradient id="limbG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={Y.mid} />
          <stop offset="100%" stopColor={Y.deep} />
        </linearGradient>
        <radialGradient id="hatG" cx="40%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="100%" stopColor="#DFE3EC" />
        </radialGradient>
        <radialGradient id="shadowG" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#000" stopOpacity="0.34" />
          <stop offset="100%" stopColor="#000" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* ④ 바닥 그림자 — 제일 먼저 깔아야 뒤로 간다 */}
      {shadow && <ellipse cx="100" cy="206" rx="62" ry="13" fill="url(#shadowG)" />}

      {/* 다리 — 몸통보다 뒤 */}
      <ellipse cx="80" cy="192" rx="17" ry="11" fill="url(#limbG)" />
      <ellipse cx="122" cy="192" rx="17" ry="11" fill="url(#limbG)" />

      {/* 팔 — 통통한 캡슐. 손은 끝에 동그라미
          🔴 2026-07-24 지시: 팔이 몸통에서 떨어져 떠 있었다.
             몸통(중심 100,110 · 반지름 76)의 **안쪽에서 시작**해야 붙어 보인다.
             그래서 x를 몸통 쪽으로 당기고(14→30, 152→136) 길이를 늘렸다.
             몸통보다 먼저 그려서 이음매가 몸통에 덮이게 한다 — 이게 핵심 */}
      {/* 🔴 팔은 전 표정 공통으로 고정한다(2026-07-24 지시).
          으쓱일 때 벌려봤는데 캐릭터가 흔들려 보여서 되돌렸다 */}
      <g fill="url(#limbG)">
        <rect x="30" y="122" width="44" height="16" rx="8" transform="rotate(26 52 130)" />
        <circle cx="26" cy="152" r="13" />
        <rect x="126" y="122" width="44" height="16" rx="8" transform="rotate(-26 148 130)" />
        <circle cx="174" cy="152" r="13" />
      </g>

      {/* 몸통 */}
      <circle cx="100" cy="110" r="76" fill="url(#bodyG)" />
      <circle cx="100" cy="110" r="76" fill="url(#rimG)" />

      {/* ② 정반사 — 이 두 개가 광택을 만든다 */}
      <ellipse cx="66" cy="62" rx="26" ry="18" fill="#fff" opacity="0.42" transform="rotate(-24 66 62)" />
      <ellipse cx="52" cy="86" rx="9" ry="6" fill="#fff" opacity="0.28" transform="rotate(-24 52 86)" />

      {prop === "요리사모자" && <ChefHat />}

      {/* 눈 — 흰자 + 눈동자 + 반짝
          🔴 2026-07-24 지시: 눈 사이를 벌리고(76/124 → 72/128) 눈동자를 줄였다(12 → 9).
             붙어 있고 눈동자가 크면 얼굴이 답답하고 아기 같아진다 */}
      <g>
        <ellipse cx="72" cy="104" rx={20 * es} ry={22 * es} fill="#fff" />
        <ellipse cx="128" cy="104" rx={20 * es} ry={22 * es} fill="#fff" />
        <ellipse cx={74 + dx} cy={107 + dy} rx={9 * es} ry={10.5 * es} fill={INK} />
        <ellipse cx={130 + dx} cy={107 + dy} rx={9 * es} ry={10.5 * es} fill={INK} />
        <circle cx={70 + dx} cy={102 + dy} r={3.2 * es} fill="#fff" />
        <circle cx={126 + dx} cy={102 + dy} r={3.2 * es} fill="#fff" />
        <circle cx={78 + dx} cy={111 + dy} r={1.8 * es} fill="#fff" opacity="0.8" />
        <circle cx={134 + dx} cy={111 + dy} r={1.8 * es} fill="#fff" opacity="0.8" />
      </g>

      {/* 눈썹 */}
      {F.brow &&
        F.brow.map((d, i) => (
          <path key={i} d={d} stroke={INK} strokeWidth="9" strokeLinecap="round" fill="none" />
        ))}

      {/* 입 */}
      {F.mouthEllipse ? (
        <ellipse
          cx={F.mouthEllipse[0]}
          cy={F.mouthEllipse[1]}
          rx={F.mouthEllipse[2]}
          ry={F.mouthEllipse[3]}
          fill={INK}
        />
      ) : (
        <path d={F.mouth} stroke={INK} strokeWidth="7" strokeLinecap="round" fill="none" />
      )}

      {/* 진땀 — 🔴 처음엔 머리 위(150,76)에 뒀더니 뭔지 모를 표시로 보였다.
          관자놀이에서 뺨을 타고 흐르게 내린다. 두 방울이라야 "진땀"으로 읽힌다 */}
      {F.sweat && (
        <g fill="#7FC4F0">
          <path d="M150 96 q9 15 0 22 q-9 -7 0 -22z" opacity="0.95" />
          <path d="M162 122 q7 12 0 17 q-7 -5 0 -17z" opacity="0.85" />
        </g>
      )}

      {prop === "계산기" && <Calc />}
    </svg>
  );
};
