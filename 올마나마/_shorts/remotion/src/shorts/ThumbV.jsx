// 쇼츠 세로 썸네일 전용 (1080×1920) — 3안 비교용
//
// 🔴 훅 화면 재사용(Thumb.jsx)은 세로에서 **식탁이 영수증 하단을 덮어 olmanama.com이 잘렸다**(2026-07-21).
//    그래서 세로는 썸네일 전용 레이아웃으로 따로 판다.
//
// 🔴 안전영역 — 쇼츠는 화면 위아래를 UI가 먹는다. 중요한 건 y 300~1500 안에 둔다.
//      위 ~150px  : 검색/뒤로가기
//      아래 ~350px: 제목·채널명·설명
//      오른쪽 ~180px: 좋아요·댓글·공유 버튼
//
// 🔴 금액은 config에서 계산된 값을 쓴다. 손으로 적으면 메뉴 바뀔 때 화면과 어긋난다.
import React from "react";
import { AbsoluteFill } from "remotion";

import { Olma } from "../olma/Olma";
import { ActionLines, Backdrop } from "../olma/Effects";
import { Receipt } from "../olma/Receipt";
import { Table } from "../olma/Table";
import { ChickenSet } from "../olma/ChickenSet";
import { BG, CFG, C, cost } from "./config";
import { BLACK, JUA } from "./fonts";

const won = (n) => n.toLocaleString() + "원";

// 검은 판 강조 — 배경 위 맨글씨는 안 읽힌다
const Slab = ({ children, size = 96, bg = C.ink, color = "#fff", style = {} }) => (
  <div
    style={{
      display: "inline-block",
      fontFamily: BLACK,
      fontSize: size,
      lineHeight: 1.02,
      color,
      background: bg,
      borderRadius: 20,
      letterSpacing: -4,
      padding: `${size * 0.13}px ${size * 0.4}px ${size * 0.21}px`,
      ...style,
    }}
  >
    {children}
  </div>
);

const Label = ({ children, size = 58, style = {} }) => (
  <div
    style={{
      display: "inline-block",
      fontFamily: JUA,
      fontSize: size,
      color: "#333",
      background: "#fff",
      border: `6px solid ${C.ink}`,
      borderRadius: 18,
      padding: `${size * 0.14}px ${size * 0.46}px ${size * 0.22}px`,
      ...style,
    }}
  >
    {children}
  </div>
);

const Site = ({ bottom = 150 }) => (
  <div
    style={{
      position: "absolute",
      bottom,
      left: 0,
      right: 0,
      textAlign: "center",
      fontFamily: BLACK,
      fontSize: 52,
      letterSpacing: -2,
      color: "#6B6152",
    }}
  >
    {CFG.site}
  </div>
);

// ───────────────────────────────────────────────── 1안 · 숫자 대비
// 파는 값과 재료값을 위아래로 때려 붙인다. 3m 밖에서도 숫자만 보이면 성공.
const V1 = () => (
  <AbsoluteFill style={{ background: "#FFF1D6", overflow: "hidden" }}>
    <div style={{ position: "absolute", top: 250, left: 0, right: 0, textAlign: "center" }}>
      <Label size={62}>{CFG.brand} {CFG.menu}</Label>
    </div>

    {/* 파는 값 — 취소선 */}
    <div style={{ position: "absolute", top: 400, left: 0, right: 0, textAlign: "center" }}>
      <div
        style={{
          fontFamily: BLACK,
          fontSize: 150,
          letterSpacing: -6,
          color: "#B4A894",
          textDecoration: "line-through",
          textDecorationThickness: 12,
          textDecorationColor: C.red,
        }}
      >
        {won(CFG.sell)}
      </div>
    </div>

    {/* 재료값 — 이 화면의 주인공 */}
    <div style={{ position: "absolute", top: 590, left: 0, right: 0, textAlign: "center" }}>
      <div style={{ fontFamily: JUA, fontSize: 66, color: "#5A5040", marginBottom: 8 }}>재료값은</div>
      <Slab size={190} bg={C.red} style={{ boxShadow: "0 14px 0 #8E1109" }}>
        {won(cost)}
      </Slab>
    </div>

    <div style={{ position: "absolute", bottom: 300, left: "50%", translate: "-50% 0" }}>
      <Olma face="헉" pose="깜짝" scale={1.15} />
    </div>
    <Site />
  </AbsoluteFill>
);

// ───────────────────────────────────────────────── 2안 · 올마 극대노
// 캐릭터를 세우는 안. 채널을 기억시키는 데는 이쪽이 세다.
const V2 = () => (
  <AbsoluteFill style={{ background: "#FFD9D2", overflow: "hidden" }}>
    <ActionLines color={C.red} opacity={0.32} spin={0} />

    <div style={{ position: "absolute", top: 240, left: 0, right: 0, textAlign: "center" }}>
      <Slab size={112}>{CFG.lines.hookTop}</Slab>
    </div>

    <div style={{ position: "absolute", top: 620, left: "50%", translate: "-50% 0" }}>
      <Olma face="극대노" pose="만세" scale={1.5} />
    </div>

    <div style={{ position: "absolute", bottom: 330, left: 0, right: 0, textAlign: "center" }}>
      <Slab size={128} bg={C.yellow} color={C.ink} style={{ boxShadow: "0 12px 0 #B99A00" }}>
        재료값 {won(cost)}
      </Slab>
    </div>
    <Site bottom={200} />
  </AbsoluteFill>
);

// ───────────────────────────────────────────────── 3안 · 영수증 단독
// 원래 훅 화면에서 **겹치던 식탁을 뺀** 안. 톤이 영상과 가장 같다.
const V3 = () => (
  <AbsoluteFill style={{ background: "#FFF1D6", overflow: "hidden" }}>
    <div
      style={{
        position: "absolute",
        top: 210,
        left: "50%",
        translate: "-50% 0",
        rotate: "-3deg",
      }}
    >
      <Receipt brand={CFG.brand} menu={CFG.menu} price={CFG.sell} width={880} hook={CFG.hook} />
    </div>

    <div style={{ position: "absolute", bottom: 250, left: 70 }}>
      <Olma face="놀람" pose="가리킴위" scale={0.95} />
    </div>

    <div style={{ position: "absolute", bottom: 420, right: 60 }}>
      <Slab size={104} bg={C.red} style={{ rotate: "-6deg", boxShadow: "0 12px 0 #8E1109" }}>
        원가 {won(cost)}
      </Slab>
    </div>
  </AbsoluteFill>
);

// ───────────────────────────────────────────────── 4·5안 · 훅 화면 그대로
// 대표님 지정(2026-07-21): 영상 첫 화면 구도를 쓰되 도장 유무만 다르게.
//
// 🔴 원본 훅은 배달세트가 영수증 하단을 덮어 olmanama.com이 "a.om"으로 잘렸다.
//    썸네일에서는 **영수증을 위로, 세트를 아래로** 떼어 놓아 주소가 온전히 보이게 한다.
//      영수증 top 60 · width 940  → 주소줄 ≈ y1104, 종이 끝 ≈ y1191
//      세트   top 1210            → 겹치지 않는다

// 🔴 Effects의 Stamp는 프레임 애니메이션이라 정지화면(frame 0)에서 투명하게 나온다.
//    썸네일용으로 "다 찍힌 상태"만 그리는 판을 따로 둔다.
const StampStill = ({ text, color = C.red, rot = -11, size = 92 }) => {
  const padX = size * 0.55;
  const padY = size * 0.32;
  return (
    <div style={{ position: "relative", display: "inline-block", rotate: `${rot}deg`, fontFamily: BLACK }}>
      <svg
        viewBox="0 0 400 140"
        preserveAspectRatio="none"
        style={{
          position: "absolute",
          inset: `-${padY}px -${padX}px`,
          width: `calc(100% + ${padX * 2}px)`,
          height: `calc(100% + ${padY * 2}px)`,
        }}
      >
        <path d="M8 14 L392 6 L396 128 L6 134 Z" fill="none" stroke={color} strokeWidth={11} strokeLinejoin="round" />
        <path d="M22 28 L378 21 L381 114 L20 120 Z" fill="none" stroke={color} strokeWidth={5} strokeLinejoin="round" />
      </svg>
      <div style={{ fontSize: size, color, letterSpacing: -3, padding: `${padY}px ${padX}px`, whiteSpace: "nowrap", lineHeight: 1.05 }}>
        {text}
      </div>
    </div>
  );
};

const HookLook = ({ stamp }) => (
  <AbsoluteFill style={{ background: BG.hook, overflow: "hidden" }}>
    <Backdrop color={BG.hook} />

    <div style={{ position: "absolute", top: 60, left: "50%", translate: "-470px 0px", rotate: "-4deg" }}>
      <Receipt brand={CFG.brand} menu={CFG.menu} price={CFG.sell} width={940} hook={CFG.hook} />
    </div>

    <div style={{ position: "absolute", bottom: 40, left: "50%", translate: "-50% 0px" }}>
      <Table width={980}><g /></Table>
    </div>
    <div style={{ position: "absolute", top: 1210, left: "50%", translate: "-50% 0px" }}>
      <ChickenSet brand={CFG.brand} width={700} box={CFG.box} />
    </div>

    {stamp && (
      <div style={{ position: "absolute", top: 1660, width: "100%", textAlign: "center", zIndex: 5 }}>
        <StampStill text={CFG.lines.hookTop} size={92} />
      </div>
    )}
  </AbsoluteFill>
);

const V4 = () => <HookLook stamp />;
const V5 = () => <HookLook stamp={false} />;

const VARIANTS = { 1: V1, 2: V2, 3: V3, 4: V4, 5: V5 };

export const ThumbV = ({ v = 1 }) => {
  const Picked = VARIANTS[v] || V1;
  return <Picked />;
};
