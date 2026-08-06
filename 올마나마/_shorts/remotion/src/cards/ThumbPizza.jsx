// 도미노 포테이토 피자편 썸네일 — 원가 시리즈 1 (2026-07-24)
//
// 🔴 마라탕·배달 썸네일과 같은 형태: 배경 + 상단 검은 판(4줄) + 시리즈 배지.
//    ⚠️ 배달편은 닻(추상기호) 넣었다가 11회로 죽었다. 피자편은 **배경이 피자 매장**이라
//    음식 맥락이 이미 화면에 있다(썸네일 3원칙: 음식 or 큰 숫자).
// 🔴 훅 = 숫자 대비. "27,900원 L사이즈, 원가는 / 단돈 4,200원"
// 🔴 쇼츠 0프레임과 같은 그림이어야 한다 → 배경도 talk_engine과 같은 pizza01 + 같은 그라데이션.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
// eslint-disable-next-line no-unused-vars

import { BLACK, JUA } from "../shorts/fonts";
import { EP, cost } from "./card_pizza";

const COLOR = {
  panel: "rgba(12,12,14,0.86)",
  sub: "#F0C9A0",
  line1: "#FFFFFF",
  point: "#FFC93C", // 원가 숫자 = 노랑 강조
  title: "#FF8A5C",
  badge: "#C0392B",
  badgeInk: "#FFFFFF",
};

// ── 썸네일 템플릿 (2026-07-24 지시) ──────────────────────────
// 🔴 매 편 데이터만 바뀐다. 구조는 고정:
//    ① 제목(도미노 포테이토 피자) — 제일 크게
//    ② 판매가(27,900원) — 크게
//    ③ 조건(무옵션 · L사이즈) — 작게
//    ④ 원가(원가 4,230원) — 중앙, 노랑 강조
//    배지 = "{series} 1" (피자/치킨/마라탕…)
//  ⚠️ 전부 중앙정렬. 글자 크기는 아래 TUNE 하나로 조절.
const TUNE = {
  panelTop: 250,
  panelW: 1000,
  panelPadX: 40,
  panelPadY: 34,
  title: 88, // ① 제목
  sell: 118, // ② 판매가 — 크게
  cond: 46, // ③ 조건 — 작게
  cost: 158, // ④ 원가 — 이 편의 주인공. 판매가보다 크게 (노랑 강조)
  gap: 12,
  badge: 66,
  badgeGap: 16,
};

const won = (n) => n.toLocaleString("ko-KR");

const T = {
  title: EP.title, // 도미노 포테이토 피자
  sell: `${won(EP.sell)}원`, // 27,900원
  cond: EP.cond, // 무옵션 · L사이즈
  cost: `원가 ${won(cost)}원`, // 원가 4,230원
  badge: `${EP.series} ${EP.ep}`, // 이거 얼마남아 1
};

const center = { textAlign: "center", whiteSpace: "nowrap", lineHeight: 1.05 };

// 판+배지+피자 — 쇼츠 훅이 이걸 그대로 쓴다 (배경은 talk_engine이 깐다)
// 🔴 피자 일러스트는 마라탕 그릇이 있던 자리(판 아래)에 크게 얹는다. 썸네일 3원칙 = 음식 화면 절반
// 🔴 mode="card"(1080×1080 인스타)는 세로 여백이 없어 판을 위로, 피자를 작게 아래에.
const CARD_LAYOUT = {
  short: { panelTop: TUNE.panelTop, pizzaBottom: 320, pizzaW: 860 },
  card: { panelTop: 70, pizzaBottom: 20, pizzaW: 560 },
};
export const ThumbCard = ({ mode = "short" }) => {
  const L = CARD_LAYOUT[mode] || CARD_LAYOUT.short;
  return (
  <>
    {/* 피자 — 판보다 뒤 레이어, 하단에 크게 */}
    <Img
      src={staticFile("bg/pizza_top.png")}
      style={{
        position: "absolute",
        bottom: L.pizzaBottom,
        left: "50%",
        transform: "translateX(-50%)",
        width: L.pizzaW,
        zIndex: 0,
        filter: "drop-shadow(0 14px 30px rgba(0,0,0,.55))",
      }}
    />
  <div
    style={{
      position: "absolute",
      top: L.panelTop,
      left: "50%",
      transform: "translateX(-50%)",
      width: TUNE.panelW,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      zIndex: 1,
    }}
  >
    <div
      style={{
        width: "100%",
        boxSizing: "border-box",
        background: COLOR.panel,
        border: "8px solid #000",
        borderRadius: 30,
        padding: `${TUNE.panelPadY}px ${TUNE.panelPadX}px`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: TUNE.gap,
      }}
    >
      {/* ① 제목 */}
      <div style={{ ...center, fontFamily: BLACK, fontSize: TUNE.title, color: COLOR.title }}>{T.title}</div>
      {/* ② 판매가 */}
      <div style={{ ...center, fontFamily: BLACK, fontSize: TUNE.sell, color: COLOR.line1, marginTop: 4 }}>{T.sell}</div>
      {/* ③ 조건 (작게) */}
      <div style={{ ...center, fontFamily: JUA, fontSize: TUNE.cond, color: COLOR.sub, marginTop: -2 }}>{T.cond}</div>
      {/* ④ 원가 (노랑 강조) */}
      <div style={{ ...center, fontFamily: BLACK, fontSize: TUNE.cost, color: COLOR.point, marginTop: 8 }}>{T.cost}</div>
    </div>
    <div
      style={{
        width: "100%",
        boxSizing: "border-box",
        marginTop: TUNE.badgeGap,
        background: COLOR.badge,
        border: "6px solid #000",
        borderRadius: 26,
        padding: "24px 0",
        textAlign: "center",
        fontFamily: JUA, // 🔴 배지는 JUA(둥근 폰트) — 폰 작은 화면에서 각진 BLACK이 뭉개져 보임(2026-07-24)
        fontSize: TUNE.badge,
        color: COLOR.badgeInk,
      }}
    >
      {T.badge}
    </div>
  </div>
  </>
  );
};

// 스틸(썸네일 파일) — 쇼츠 0프레임과 같은 그림. mode="card"면 인스타 1:1 표지
export const ThumbPizza = ({ mode = "short" }) => (
  <AbsoluteFill style={{ background: "#000" }}>
    <Img src={staticFile("bg/pizza01.png")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, rgba(0,0,0,.5) 0%, rgba(0,0,0,0) 26%, rgba(0,0,0,0) 44%, rgba(0,0,0,.62) 100%)",
      }}
    />
    <ThumbCard mode={mode} />
  </AbsoluteFill>
);
