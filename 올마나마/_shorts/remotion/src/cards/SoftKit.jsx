// 여성향 톤 공용 부품 (2026-07-25)
//
// 🔴 격자배경·리본배너·말풍선·주방도구를 **코드로** 그린다. 이미지 안 쓴다.
//    이미지로 하면 편마다 누끼 따고 관리해야 하는데, 이런 단순한 도형은 코드가 낫다.
//    (음식 일러스트는 이미지가 맞다 — 그건 public/food 에 있다)
//
// 🔴 색은 TONE 하나로 통일. 편마다 파스텔 색만 바꾸면 전체가 따라 바뀐다.
import React from "react";
import { AbsoluteFill } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";

// ── 격자 배경 ────────────────────────────────────────────────
// 🔴 노트 느낌. 단색 그라데이션만 쓰면 허전한데 이걸 깔면 화면이 찬다.
export const GridBg = ({ base = "#F7F4EE", line = "rgba(180,150,130,.16)", size = 54, children }) => (
  <AbsoluteFill
    style={{
      background: base,
      backgroundImage: `linear-gradient(${line} 1.5px, transparent 1.5px), linear-gradient(90deg, ${line} 1.5px, transparent 1.5px)`,
      backgroundSize: `${size}px ${size}px`,
    }}
  >
    {children}
  </AbsoluteFill>
);

// ── 리본 배너 ────────────────────────────────────────────────
// 🔴 양끝 제비꼬리 + 접힌 그림자. 시리즈 배지로 쓴다.
export const Ribbon = ({ text, color = "#F5A9B8", ink = "#fff", w = 620, fontSize = 54, tail = 44 }) => (
  <div style={{ position: "relative", width: w, height: 92, display: "flex", alignItems: "center", justifyContent: "center" }}>
    {/* 왼쪽 꼬리 */}
    <div
      style={{
        position: "absolute", left: -tail, top: 18, width: tail + 26, height: 56,
        background: color, filter: "brightness(.88)",
        clipPath: "polygon(0 0, 100% 0, 100% 100%, 0 100%, 22% 50%)",
      }}
    />
    {/* 오른쪽 꼬리 */}
    <div
      style={{
        position: "absolute", right: -tail, top: 18, width: tail + 26, height: 56,
        background: color, filter: "brightness(.88)",
        clipPath: "polygon(0 0, 100% 0, 78% 50%, 100% 100%, 0 100%)",
      }}
    />
    {/* 본체 */}
    <div
      style={{
        position: "relative", width: "100%", height: 92, background: color, borderRadius: 18,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontFamily: JUA, fontSize, color: ink, whiteSpace: "nowrap", zIndex: 1,
      }}
    >
      {text}
    </div>
  </div>
);

// ── 구름 말풍선 ──────────────────────────────────────────────
// 🔴 원을 여러 개 겹쳐 만든다. 꼬리는 작은 원 두 개.
export const CloudBubble = ({ text, color = "#E7D9F5", ink = "#5A4A63", fontSize = 56, tail = "left" }) => (
  <div style={{ position: "relative", display: "inline-block" }}>
    <svg width="640" height="230" viewBox="0 0 640 230" style={{ display: "block" }}>
      <g fill={color}>
        <ellipse cx="180" cy="120" rx="130" ry="82" />
        <ellipse cx="330" cy="96" rx="150" ry="90" />
        <ellipse cx="470" cy="124" rx="128" ry="78" />
        <ellipse cx="255" cy="70" rx="92" ry="56" />
        <ellipse cx="400" cy="66" rx="86" ry="52" />
      </g>
      {/* 꼬리 — 작은 원 두 개가 아래로 */}
      <g fill={color}>
        {tail === "left" ? (
          <>
            <circle cx="150" cy="196" r="22" />
            <circle cx="112" cy="216" r="12" />
          </>
        ) : (
          <>
            <circle cx="490" cy="196" r="22" />
            <circle cx="528" cy="216" r="12" />
          </>
        )}
      </g>
    </svg>
    <div
      style={{
        position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
        paddingBottom: 26, fontFamily: JUA, fontSize, color: ink, whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  </div>
);

// ── 주방도구 (배경 소품) ─────────────────────────────────────
// 🔴 빈 공간에 흩뿌려 화면을 채운다. 파스텔이라 주인공을 안 가린다.
const Tool = ({ kind, color }) => {
  const s = { fill: "none", stroke: color, strokeWidth: 11, strokeLinecap: "round", strokeLinejoin: "round" };
  if (kind === "ladle")
    return (
      <svg width="90" height="200" viewBox="0 0 90 200">
        <path d="M45 12 V120" {...s} />
        <path d="M12 120 a33 33 0 0 0 66 0 z" fill={color} />
      </svg>
    );
  if (kind === "spatula")
    return (
      <svg width="90" height="200" viewBox="0 0 90 200">
        <path d="M45 12 V110" {...s} />
        <rect x="14" y="108" width="62" height="74" rx="16" fill={color} />
        <path d="M30 126 V166 M45 126 V166 M60 126 V166" stroke="#fff" strokeWidth="7" strokeLinecap="round" />
      </svg>
    );
  if (kind === "spoon")
    return (
      <svg width="80" height="200" viewBox="0 0 80 200">
        <path d="M40 20 V128" {...s} />
        <ellipse cx="40" cy="152" rx="30" ry="40" fill={color} />
      </svg>
    );
  if (kind === "knife")
    return (
      <svg width="80" height="200" viewBox="0 0 80 200">
        <path d="M40 14 L64 76 L40 150 L16 76 Z" fill={color} />
        <path d="M40 150 V188" {...s} />
      </svg>
    );
  // whisk
  return (
    <svg width="80" height="200" viewBox="0 0 80 200">
      <path d="M40 14 V96" {...s} />
      <path d="M40 96 q-30 40 0 84 q30 -44 0 -84" {...s} />
      <path d="M40 96 q-14 44 0 84 q14 -44 0 -84" {...s} />
    </svg>
  );
};

// 🔴 좌표는 화면 네 귀퉁이 쪽. 가운데(주인공 자리)는 비운다
const TOOLS = [
  { kind: "ladle", x: 60, y: 120, rot: -18, c: "#C9B6E4" },
  { kind: "spatula", x: 890, y: 90, rot: 16, c: "#F5B8C8" },
  { kind: "spoon", x: 120, y: 1560, rot: 24, c: "#B8D8E8" },
  { kind: "knife", x: 900, y: 1520, rot: -12, c: "#F7C9A8" },
  { kind: "whisk", x: 940, y: 760, rot: 8, c: "#CFE0C0" },
  { kind: "spoon", x: 40, y: 800, rot: -14, c: "#F3D9A8" },
];

export const ToolScatter = ({ opacity = 0.85 }) => (
  <>
    {TOOLS.map((t, i) => (
      <div
        key={i}
        style={{
          position: "absolute", left: t.x, top: t.y,
          transform: `rotate(${t.rot}deg)`, opacity, zIndex: 0,
        }}
      >
        <Tool kind={t.kind} color={t.c} />
      </div>
    ))}
  </>
);

// ── 흰 카드 ──────────────────────────────────────────────────
export const SoftCard = ({ children, top, bottom, w = 940, pad = "40px 44px", radius = 34 }) => (
  <div
    style={{
      position: "absolute", top, bottom, left: "50%", transform: "translateX(-50%)",
      width: w, boxSizing: "border-box", background: "#fff", borderRadius: radius,
      padding: pad, boxShadow: "0 14px 40px rgba(170,140,120,.16)", zIndex: 2,
    }}
  >
    {children}
  </div>
);
