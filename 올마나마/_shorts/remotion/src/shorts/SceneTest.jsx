// 실제 장면 시안 — 카툰 배경 + 볼 (2026-07-22)
//
// 🔴 장면당 요소는 셋까지: **자막 한 줄 + 숫자 하나 + 캐릭터**.
//    3편이 조잡해진 원인이 한 화면에 다 넣은 것이었다.
// 🔴 한 화면엔 캐릭터 **둘까지**. 넷을 세우면 얼굴이 작아져 표정이 안 보인다.
// 🔴 자막은 판때기 없이 **흰 글씨 + 검정 테두리**. 참고 채널 방식이고 배경을 덜 가린다.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

import { BrandBall } from "../olma/BrandBall";
import { C } from "./config";
import { BLACK, JUA } from "./fonts";

// 🔴 x는 화면 중앙에서의 거리. left+translate만 쓰면 요소 왼쪽 끝이 그 자리에 놓여 오른쪽이 잘린다.
const At = ({ children, x, y, style = {} }) => (
  <div style={{ position: "absolute", top: y, left: `calc(50% + ${x}px)`, transform: "translateX(-50%)", ...style }}>
    {children}
  </div>
);

// 말풍선 — 🔴 화면 위 별도 자막은 쓰지 않는다(2026-07-22 지시).
//    대사는 **말하는 캐릭터 바로 위**에 붙인다. 누가 말하는지가 자막 위치로 드러난다.
//    꼬리가 캐릭터 쪽을 향해야 한다 — 없으면 그냥 떠 있는 판이 된다.
const Bubble = ({ children, x, y, size = 48, tail = "down" }) => (
  <div style={{ position: "absolute", top: y, left: `calc(50% + ${x}px)`, transform: "translateX(-50%)" }}>
    <div
      style={{
        position: "relative",
        background: "#fff",
        border: "8px solid #000",
        borderRadius: 26,
        padding: "14px 26px 20px",
        fontFamily: JUA,
        fontSize: size,
        color: "#111",
        whiteSpace: "nowrap",
        textAlign: "center",
      }}
    >
      {children}
      {tail === "down" && (
        <>
          {/* 꼬리 — 검정 삼각형 위에 흰 삼각형을 겹쳐 테두리처럼 보이게 한다 */}
          <div
            style={{
              position: "absolute",
              bottom: -34,
              left: "50%",
              marginLeft: -20,
              width: 0,
              height: 0,
              borderLeft: "20px solid transparent",
              borderRight: "20px solid transparent",
              borderTop: "34px solid #000",
            }}
          />
          <div
            style={{
              position: "absolute",
              bottom: -20,
              left: "50%",
              marginLeft: -12,
              width: 0,
              height: 0,
              borderLeft: "12px solid transparent",
              borderRight: "12px solid transparent",
              borderTop: "22px solid #fff",
            }}
          />
        </>
      )}
    </div>
  </div>
);

// 🔴 캐릭터는 **아래쪽에 크게** 앉힌다(2026-07-22). 위에 작게 두면 배경에 묻힌다.
//    참고 채널도 볼이 화면 하단 1/3을 차지한다.
const BALL_Y = 1210;
const BALL_S = 1.15;

export const SceneTest = ({ v = 1 }) => {
  // v1 = 훅(교촌 변명) · v2 = 재료(숫자 공개) · v3 = 사장님 하소연
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Img src={staticFile("bg/store03.png")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />

      {/* 🔴 배경이 밝아서 흰 자막이 묻힌다. 위아래에 어두운 그라데이션을 깐다 */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,.55) 0%, rgba(0,0,0,0) 26%, rgba(0,0,0,0) 48%, rgba(0,0,0,.62) 100%)",
        }}
      />

      {v === 1 && (
        <>
          <At x={-270} y={BALL_Y}><BrandBall brand="올마" face="시치미" scale={BALL_S} /></At>
          <At x={270} y={BALL_Y + 30}><BrandBall brand="교촌" face="시치미" scale={BALL_S} /></At>
          <Bubble x={270} y={BALL_Y - 190}>붓으로 발랐거든요</Bubble>
        </>
      )}

      {v === 2 && (
        <>
          {/* 숫자는 하나만. 화면에서 제일 큰 요소로 박는다 */}
          <div
            style={{
              position: "absolute",
              top: 330,
              width: "100%",
              textAlign: "center",
              fontFamily: BLACK,
              fontSize: 200,
              color: C.yellow,
              WebkitTextStroke: "22px #000",
              paintOrder: "stroke fill",
            }}
          >
            6,860원
          </div>
          <At x={-270} y={BALL_Y}><BrandBall brand="올마" face="시치미" scale={BALL_S} /></At>
          <At x={270} y={BALL_Y + 30}><BrandBall brand="소비자" face="발끈" scale={BALL_S} /></At>
          <Bubble x={-270} y={BALL_Y - 190}>닭 정육</Bubble>
        </>
      )}

      {v === 3 && (
        <>
          <At x={-270} y={BALL_Y}><BrandBall brand="올마" face="놀람" scale={BALL_S} /></At>
          <At x={270} y={BALL_Y}><BrandBall brand="사장님" face="변명" scale={BALL_S} oil /></At>
          <Bubble x={250} y={BALL_Y - 200}>저도 남는 게 없어요</Bubble>
        </>
      )}
    </AbsoluteFill>
  );
};
