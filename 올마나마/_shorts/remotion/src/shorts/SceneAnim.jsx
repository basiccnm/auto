// 만담 한 판 — 말하는 쪽이 커지고 튄다 (2026-07-22)
//
// 🔴 다 같은 크기로 서 있으면 누가 말하는지 안 보이고 화면이 죽는다(2026-07-22 지시).
//    말하는 쪽 = 크게 + 통통, 듣는 쪽 = 작게 + 가만히. 시선이 저절로 따라간다.
// 🔴 CSS transition 금지 — 렌더에서 프레임이 어긋난다. 전부 spring/interpolate로 계산한다.
// 🔴 크기 변화는 **말이 시작되는 프레임**에 맞춰야 한다. 어긋나면 더빙이 안 맞는 느낌이 난다.
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

import { BrandBall } from "../olma/BrandBall";
import { JUA } from "./fonts";

// 대사 — who(누가) · text(뭐라고) · sec(몇 초짜리). voice/out 의 mp3 길이와 맞춘다.
const BEATS = [
  { who: "올마", face: "시치미", text: "교촌 허니콤보.", sec: 1.9 },
  { who: "소비자", face: "발끈", text: "비싸!", sec: 1.2 },
  { who: "교촌", face: "시치미", text: "붓으로 발랐거든요.", sec: 1.7 },
  { who: "올마", face: "놀람", text: "그럼 재료값 까볼까.", sec: 2.1 },
];

// 화면상 자리 — 올마는 늘 왼쪽. 상대만 오른쪽에서 바뀐다
const SLOT = { 올마: -270, 소비자: 270, 교촌: 270, 사장님: 270 };

const BIG = 1.24; // 말하는 쪽
const SMALL = 0.92; // 듣는 쪽

const Bubble = ({ children, x, y, pop }) => (
  <div
    style={{
      position: "absolute",
      top: y,
      left: `calc(50% + ${x}px)`,
      transform: `translateX(-50%) scale(${pop})`,
      transformOrigin: "50% 100%",
      opacity: Math.min(pop * 1.6, 1),
    }}
  >
    <div
      style={{
        position: "relative",
        background: "#fff",
        border: "9px solid #000",
        borderRadius: 28,
        padding: "16px 30px 22px",
        fontFamily: JUA,
        fontSize: 62,
        color: "#111",
        whiteSpace: "nowrap",
      }}
    >
      {children}
      <div
        style={{
          position: "absolute",
          bottom: -36,
          left: "50%",
          marginLeft: -22,
          width: 0,
          height: 0,
          borderLeft: "22px solid transparent",
          borderRight: "22px solid transparent",
          borderTop: "36px solid #000",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: -21,
          left: "50%",
          marginLeft: -13,
          width: 0,
          height: 0,
          borderLeft: "13px solid transparent",
          borderRight: "13px solid transparent",
          borderTop: "23px solid #fff",
        }}
      />
    </div>
  </div>
);

export const SceneAnim = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 지금 몇 번째 대사인가
  let acc = 0;
  let idx = 0;
  let start = 0;
  for (let i = 0; i < BEATS.length; i++) {
    const end = acc + BEATS[i].sec * fps;
    if (f < end) {
      idx = i;
      start = acc;
      break;
    }
    acc = end;
    idx = i;
    start = acc - BEATS[i].sec * fps;
  }
  const beat = BEATS[idx];
  const local = f - start;

  // 말풍선 — 튀어나오듯 등장
  const pop = spring({ fps, frame: local, config: { damping: 11, stiffness: 220, mass: 0.6 } });

  // 말하는 쪽 — 말 시작에 한 번 크게 튀었다가 제자리로
  const bounce = interpolate(
    spring({ fps, frame: local, config: { damping: 9, stiffness: 260, mass: 0.5 } }),
    [0, 1],
    [0.86, 1],
  );
  // 🔴 살아 있어 보이려면 말하는 동안 미세하게 계속 흔들려야 한다. 멈추면 그림이 된다.
  const idleWobble = 1 + Math.sin(local / 4.5) * 0.018;

  // 화면에 둘. 올마는 늘 있고, 상대는 그 대사의 상대역
  const partner = beat.who === "올마" ? (BEATS[idx + 1] || BEATS[idx - 1] || {}).who || "교촌" : beat.who;
  const cast = ["올마", partner === "올마" ? "교촌" : partner];

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Img src={staticFile("bg/store03.png")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,.5) 0%, rgba(0,0,0,0) 24%, rgba(0,0,0,0) 46%, rgba(0,0,0,.6) 100%)",
        }}
      />

      {cast.map((who) => {
        const talking = who === beat.who;
        const s = (talking ? BIG * bounce * idleWobble : SMALL) * 1.0;
        return (
          <div
            key={who}
            style={{
              position: "absolute",
              top: 1180,
              left: `calc(50% + ${SLOT[who]}px)`,
              transform: "translateX(-50%)",
              // 🔴 아래쪽을 기준으로 커져야 바닥에 붙어 있는 것처럼 보인다.
              //    가운데 기준이면 커질 때 발이 뜬다.
              transformOrigin: "50% 100%",
              zIndex: talking ? 2 : 1,
            }}
          >
            <div style={{ transform: `scale(${s})`, transformOrigin: "50% 100%" }}>
              <BrandBall brand={who} face={talking ? beat.face : "시치미"} scale={1.0} />
            </div>
          </div>
        );
      })}

      <Bubble x={SLOT[beat.who]} y={940} pop={pop}>
        {beat.text}
      </Bubble>
    </AbsoluteFill>
  );
};

export const SCENE_ANIM_SEC = BEATS.reduce((a, b) => a + b.sec, 0);
