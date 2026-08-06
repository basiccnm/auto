// 나마 — 올마의 짝. 여성 캐릭터 (2026-07-21)
//
// 🔴 표정·포즈 이름은 올마와 **똑같이** 쓴다(POSES·MOUTHS를 그대로 import).
//    그래야 장면 코드에서 <Olma>를 <Nama>로 바꾸기만 하면 되고, 68편 내내 안 꼬인다.
//
// 🔴 올마와 다른 점은 네 가지뿐이다. 이것만으로 실루엣이 갈린다:
//    ① 단발 머리 (제일 큰 구분 — 멀리서도 보인다)
//    ② 분홍 몸통 (올마는 파랑)
//    ③ 속눈썹
//    ④ 가슴 글자 N (올마는 O)
import React from "react";

import { MOUTHS, OLMA, POSES } from "./Olma";
import { EarMuffs, Glasses } from "./Props";

export const NAMA = {
  head: "#F7EFA8", // 얼굴은 올마와 같게 — 같은 종족으로 보여야 짝이 된다
  body: "#F5A9C0", // 분홍
  hair: "#5A3A22", // 짙은 갈색
  line: "#000",
  lw: 7,
};

const ANGRY_FACES = ["화남", "절규", "극대노"];
const RED_FACES = ["극대노"];

// ── 머리 모양 ────────────────────────────────────────────────
// 🔴 첫 단발은 "너무 별로"였다(2026-07-21). 얼굴을 덮어 표정이 죽고 덩어리가 무거웠다.
//    그래서 ① 앞머리는 이마 **위쪽만** 덮고 ② 뒷머리는 얼굴 옆으로만 보이게 한다.
//    모양은 hair prop으로 갈아끼운다. 확정되면 기본값 하나만 남긴다.
const HAIR = {
  // 단발 — 턱선에서 안으로 말린 기본형
  bob: {
    back: "M100 172 q0 -104 100 -104 q100 0 100 104 q0 66 -14 96 q-10 -30 -16 -60 l0 -60 l-140 0 l0 60 q-6 30 -16 60 q-14 -30 -14 -96 z",
    front: "M104 150 q6 -86 96 -86 q90 0 96 86 q-30 -40 -66 -44 q-10 16 -30 16 q-34 0 -52 -14 q-26 12 -44 42 z",
  },
  // 포니테일 — 뒤로 묶어 옆으로 뻗친다. 실루엣이 제일 확실하다
  pony: {
    back: "M112 160 q0 -96 88 -96 q88 0 88 96 q0 22 -4 40 l-168 0 q-4 -18 -4 -40 z M286 150 q52 6 66 58 q12 46 -14 76 q-16 -46 -34 -66 q-14 -14 -26 -18 z",
    front: "M108 148 q8 -84 92 -84 q84 0 92 84 q-32 -40 -70 -42 q-12 18 -34 18 q-30 0 -46 -16 q-22 14 -34 40 z",
  },
  // 양갈래 — 귀 옆으로 두 갈래. 제일 만화 같다
  twin: {
    back: "M108 162 q0 -98 92 -98 q92 0 92 98 q0 20 -4 36 l-176 0 q-4 -16 -4 -36 z M86 172 q-34 10 -36 56 q-2 40 22 58 q10 -44 26 -66 z M314 172 q34 10 36 56 q2 40 -22 58 q-10 -44 -26 -66 z",
    front: "M106 150 q6 -86 94 -86 q88 0 94 86 q-30 -42 -68 -44 q-12 18 -32 18 q-32 0 -48 -16 q-24 14 -40 42 z",
  },
};

const Hair = ({ hair = "bob", part }) => {
  const set = HAIR[hair] || HAIR.bob;
  return (
    <path d={set[part]} fill={NAMA.hair} stroke={NAMA.line} strokeWidth={NAMA.lw} strokeLinejoin="round" />
  );
};

// 팔 — 올마와 같은 규칙. 손에 쥔 물건은 팔 안에서 그려야 안 어긋난다
const Arm = ({ side, deg, hold }) => {
  const x = side === "L" ? 152 : 248;
  const d = side === "L" ? -1 : 1;
  const hx = x + d * 15,
    hy = 374;
  return (
    <g style={{ transformBox: "view-box", transformOrigin: `${x}px 268px`, rotate: `${deg}deg` }}>
      <path
        d={`M${x} 268 q${d * 22} 55 ${d * 14} 96`}
        fill="none"
        stroke={NAMA.line}
        strokeWidth={NAMA.lw}
        strokeLinecap="round"
      />
      {hold && (
        <g style={{ transformBox: "view-box", transformOrigin: `${hx}px ${hy}px`, rotate: `${-deg * 0.8}deg` }}>
          {hold(hx, hy)}
        </g>
      )}
      <ellipse cx={hx} cy={hy} rx={16} ry={20} fill={NAMA.body} stroke={NAMA.line} strokeWidth={NAMA.lw} />
      <ellipse cx={hx - d * 12} cy={hy - 6} rx={7} ry={10} fill={NAMA.body} stroke={NAMA.line} strokeWidth={5} />
      <ellipse cx={hx - d * 3} cy={hy - 7} rx={6} ry={7} fill="#fff" opacity={0.45} />
    </g>
  );
};

const Leg = ({ x, deg, side = 1 }) => (
  <g style={{ transformBox: "view-box", transformOrigin: `${x}px 400px`, rotate: `${deg}deg` }}>
    <path d={`M${x} 400 v96`} stroke={NAMA.line} strokeWidth={NAMA.lw} strokeLinecap="round" />
    <ellipse
      cx={x + side * 9}
      cy={506}
      rx={26}
      ry={17}
      fill={NAMA.body}
      stroke={NAMA.line}
      strokeWidth={NAMA.lw}
      style={{ transformBox: "view-box", transformOrigin: `${x}px 506px`, rotate: `${side * 12}deg` }}
    />
    <ellipse cx={x + side * 6} cy={500} rx={11} ry={6} fill="#fff" opacity={0.42} />
  </g>
);

export const Nama = ({
  face = "무표정",
  pose = "기본",
  scale = 1,
  tilt = 0,
  bounce = 0,
  armL = null,
  armR = null,
  walk = 0,
  phase = 0,
  head = 0,
  lean = 0,
  holdR = null,
  holdL = null,
  chew = 0,
  hair = "twin", // 2026-07-21 확정: 양갈래. (bob | pony | twin)
  // 🔴 몸통 없이 머리만 (2026-07-22). 올마와 같은 옵션 — 자세한 주의사항은 Olma.jsx 참고.
  headOnly = false,
  // 🔴 소품은 머리 그룹 안에서 그린다. 고개를 까닥이면 같이 움직여야 한다.
  glasses = null, // null=안 씀 / 0=똑바로 / -18=삐뚤어짐(부딪힌 뒤)
  earmuffs = false, // 화산 폭발 대비
  style = {},
}) => {
  const p = POSES[pose] || POSES["기본"];
  const swing = Math.sin(phase) * 26 * walk;
  const L = armL === null ? p.L + swing : armL;
  const R = armR === null ? p.R + swing : armR;
  const mouth = MOUTHS[face] || MOUTHS["무표정"];
  const bigEye = face === "놀람" || face === "헉";
  const isAngry = ANGRY_FACES.includes(face);
  const isRed = RED_FACES.includes(face);
  const isBliss = face === "황홀" || face === "감음";

  return (
    <svg
      viewBox={headOnly ? "40 20 320 320" : "-90 -60 580 680"}
      width={(headOnly ? 320 : 580) * scale}
      height={(headOnly ? 320 : 680) * scale}
      xmlns="http://www.w3.org/2000/svg"
      style={{ overflow: "visible", ...style }}
    >
      <g
        style={{
          transformBox: "view-box",
          transformOrigin: "200px 500px",
          translate: `0px ${bounce}px`,
          rotate: `${tilt}deg`,
        }}
      >
        {!headOnly && (
          <>
            {/* 바닥 그림자 */}
            <ellipse cx={200} cy={508} rx={78 - Math.min(Math.abs(bounce), 20) * 1.2} ry={13} fill="#000" opacity={0.13} />

            <Leg x={184} deg={Math.sin(phase) * 30 * walk} side={-1} />
            <Leg x={216} deg={-Math.sin(phase) * 30 * walk} side={1} />
          </>
        )}

        <g style={{ transformBox: "view-box", transformOrigin: "200px 400px", rotate: `${lean}deg` }}>
          {/* 몸통 — 🔴 올마는 직사각형, 나마는 아래가 살짝 퍼진 사다리꼴(원피스).
              실루엣으로 구분되게 하는 두 번째 장치다. */}
          {!headOnly && (
            <>
              <path
                d="M154 252 h92 q26 0 26 26 v96 q0 28 -18 28 h-108 q-18 0 -18 -28 v-96 q0 -26 26 -26 z"
                fill={NAMA.body}
                stroke={NAMA.line}
                strokeWidth={NAMA.lw}
                strokeLinejoin="round"
              />
              <path d="M166 268 q10 -8 22 -6 v112 q-14 4 -22 -4 z" fill="#fff" opacity={0.32} />

              {/* 가슴 글자 N — 올마의 O와 짝. 폰트에 안 기대고 선으로 그린다 */}
              <path
                d="M186 348 v-36 l28 36 v-36"
                fill="none"
                stroke={NAMA.line}
                strokeWidth={9}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </>
          )}

          <g style={{ transformBox: "view-box", transformOrigin: "200px 252px", rotate: `${head}deg` }}>
            {/* 🔴 뒷머리 — 얼굴보다 **먼저** 그려 뒤로 보낸다. */}
            <Hair hair={hair} part="back" />

            {/* 얼굴 */}
            <circle
              cx={200}
              cy={163}
              r={98}
              fill={isRed ? "#FF8A7A" : NAMA.head}
              stroke={NAMA.line}
              strokeWidth={NAMA.lw}
            />

            {/* 앞머리 — 얼굴 위에 그린다. 🔴 눈썹을 가리면 표정이 죽으니 이마 위쪽만 덮는다 */}
            <Hair hair={hair} part="front" />

            {/* 볼터치 */}
            <ellipse cx={140} cy={196} rx={20} ry={12} fill="#FF8A7A" opacity={isRed ? 0.75 : 0.5} />
            <ellipse cx={260} cy={196} rx={20} ry={12} fill="#FF8A7A" opacity={isRed ? 0.75 : 0.5} />

            {/* 눈썹 — 올마보다 가늘고 둥글게 */}
            {!isBliss && (
              <>
                <path
                  d={isAngry ? "M146 126 l38 18" : "M148 126 q20 -9 38 -2"}
                  fill="none"
                  stroke={NAMA.line}
                  strokeWidth={7}
                  strokeLinecap="round"
                />
                <path
                  d={isAngry ? "M254 126 l-38 18" : "M252 126 q-20 -9 -38 -2"}
                  fill="none"
                  stroke={NAMA.line}
                  strokeWidth={7}
                  strokeLinecap="round"
                />
              </>
            )}

            {/* 눈 + 속눈썹 — 🔴 속눈썹이 여성 캐릭터임을 가장 빨리 알린다 */}
            {isBliss ? (
              <>
                <path d="M148 152 q20 -22 40 0" fill="none" stroke={NAMA.line} strokeWidth={8} strokeLinecap="round" />
                <path d="M212 152 q20 -22 40 0" fill="none" stroke={NAMA.line} strokeWidth={8} strokeLinecap="round" />
              </>
            ) : isAngry ? (
              <>
                <path d="M146 142 l38 16 l-20 14 z" fill={NAMA.line} strokeLinejoin="round" />
                <path d="M254 142 l-38 16 l20 14 z" fill={NAMA.line} strokeLinejoin="round" />
              </>
            ) : (
              <>
                <ellipse cx={168} cy={152} rx={bigEye ? 15 : 11} ry={bigEye ? 16 : 12} fill={NAMA.line} />
                <ellipse cx={232} cy={152} rx={bigEye ? 15 : 11} ry={bigEye ? 16 : 12} fill={NAMA.line} />
                <circle cx={172} cy={147} r={bigEye ? 5 : 3.6} fill="#fff" />
                <circle cx={236} cy={147} r={bigEye ? 5 : 3.6} fill="#fff" />
                {/* 속눈썹 — 눈 바깥쪽 위로 세 가닥 */}
                <path d="M152 140 l-10 -8 M160 136 l-6 -10" stroke={NAMA.line} strokeWidth={5} strokeLinecap="round" />
                <path d="M248 140 l10 -8 M240 136 l6 -10" stroke={NAMA.line} strokeWidth={5} strokeLinecap="round" />
              </>
            )}

            <path
              style={
                chew
                  ? { transformBox: "view-box", transformOrigin: "200px 196px", scale: `1 ${1 + Math.sin(chew) * 0.45}` }
                  : undefined
              }
              d={mouth}
              fill={face === "극대노" || face === "절규" || face === "헉" || face === "놀람" ? "#fff" : "none"}
              stroke={NAMA.line}
              strokeWidth={6}
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* 소품 — 눈·입 위에 얹는다 */}
            {glasses !== null && <Glasses tilt={glasses} />}
            {earmuffs && <EarMuffs />}
          </g>

          {!headOnly && (
            <>
              <Arm side="L" deg={L} hold={holdL} />
              <Arm side="R" deg={R} hold={holdR} />
            </>
          )}
        </g>
      </g>
    </svg>
  );
};
