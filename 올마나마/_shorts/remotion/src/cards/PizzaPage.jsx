// 도미노 포테이토 피자 원가편 판 (2026-07-24)
//
// 🔴 배달편(AnchorPage)과 같은 골격 — 배경 + 검은 판 + 하단 볼.
//    다른 건 판 안 내용(원가 쌓기/공개/인사이트)뿐이다.
// 🔴 상시 자막 "원재료 기준 원가"를 모든 판 하단에 자동으로 박는다 (가격원가 쇼츠 필수 규칙).
// 🔴 쇼츠(TalkPizza)는 PizzaPanel만 떼어 쓴다. 스틸(PizzaPage)도 그걸 감싼 것 → 화면이 갈라지지 않는다.
import React from "react";
import { AbsoluteFill } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { OlmaBall3D } from "./OlmaBall3D";
import { PAGES } from "./pages_pizza";

const COLOR = {
  bg: "radial-gradient(120% 90% at 50% 18%, #C0392B 0%, #8E2A1E 55%, #5E1A12 100%)", // 피자 = 토마토 레드
  panel: "rgba(12,12,14,0.86)",
  lead: "#FFFFFF",
  hot: "#FFC93C", // 강조 노랑 (치즈·도우)
  dim: "#FFFFFF",
  point: "#FF6A4D", // 인사이트 강조
  boxBg: "#FFF3D6",
  boxBar: "#F5B70C",
  boxInk: "#7A5200",
  site: "#FFC42E",
  seal: "rgba(255,255,255,0.6)", // 상시 자막
};

export const SIZE = { short: { w: 1080, h: 1920 }, card: { w: 1080, h: 1080 } };
const LAYOUT = {
  short: { panelTop: 250, ballSize: 430, ballBottom: 130, ballTop: null },
  card: { panelTop: 200, ballSize: 250, ballBottom: null, ballTop: 0 },
};

// 🔴 글씨 최소 68 (판형 바뀌어도 안 줄인다)
const TUNE = {
  panelW: 1000,
  panelPad: 40,
  lead: 74,
  rowName: 68,
  rowVal: 84,
  big: 132, // 인사이트 큰 문구
  sub: 70,
  sell: 96, // 판매가
  cost: 150, // 총원가 — 정점
  costLabel: 64,
  box: 74,
  site: 92,
  seal: 40, // 상시 자막 "원재료 기준 원가"
  rowGap: 22,
};

const Panel = ({ top, pop = 1, children }) => (
  <div
    style={{
      position: "absolute",
      top,
      left: "50%",
      opacity: Math.min(pop * 2, 1),
      transform: `translateX(-50%) translateY(${(1 - pop) * 60}px) scale(${0.92 + pop * 0.08})`,
      transformOrigin: "50% 0%",
      width: TUNE.panelW,
      boxSizing: "border-box",
      background: COLOR.panel,
      border: "8px solid #000",
      borderRadius: 30,
      padding: TUNE.panelPad,
    }}
  >
    {children}
  </div>
);

const Box = ({ text }) => (
  <div
    style={{
      marginTop: 32,
      background: COLOR.boxBg,
      borderLeft: `16px solid ${COLOR.boxBar}`,
      borderRadius: 12,
      padding: "24px 30px",
      fontFamily: BLACK,
      fontSize: TUNE.box,
      color: COLOR.boxInk,
      whiteSpace: "nowrap",
    }}
  >
    {text}
  </div>
);

// 상시 자막 — 모든 판 하단
const Seal = () => (
  <div style={{ marginTop: 26, textAlign: "right", fontFamily: JUA, fontSize: TUNE.seal, color: COLOR.seal }}>
    · 원재료 기준 원가입니다 ·
  </div>
);

const PanelBody = ({ p }) => {
  if (p.kind === "rows") {
    return (
      <>
        <div style={{ fontFamily: BLACK, fontSize: TUNE.lead, color: COLOR.lead, whiteSpace: "nowrap" }}>{p.lead}</div>
        {p.rows.map(([name, val, hot], i) => (
          <div
            key={name}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr auto",
              alignItems: "baseline",
              columnGap: 24,
              marginTop: TUNE.rowGap,
              borderTop: "3px solid rgba(255,255,255,.18)",
              paddingTop: TUNE.rowGap,
            }}
          >
            <span style={{ fontFamily: JUA, fontSize: TUNE.rowName, color: hot ? COLOR.hot : "#E6DFD4", whiteSpace: "nowrap" }}>
              {name}
            </span>
            <span
              style={{
                fontFamily: BLACK,
                fontSize: TUNE.rowVal,
                color: hot ? COLOR.hot : COLOR.dim,
                textAlign: "right",
                whiteSpace: "nowrap",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {val}
            </span>
          </div>
        ))}
        {p.box && <Box text={p.box} />}
        <Seal />
      </>
    );
  }
  if (p.kind === "reveal") {
    return (
      <>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            alignItems: "baseline",
            columnGap: 24,
          }}
        >
          <span style={{ fontFamily: JUA, fontSize: TUNE.costLabel, color: "#E6DFD4", whiteSpace: "nowrap" }}>판매가</span>
          <span style={{ fontFamily: BLACK, fontSize: TUNE.sell, color: "#E6DFD4", textAlign: "right", whiteSpace: "nowrap" }}>
            {p.sell.toLocaleString("ko-KR")}원
          </span>
        </div>
        <div style={{ borderTop: "4px solid rgba(255,255,255,.35)", margin: "18px 0" }} />
        <div style={{ fontFamily: JUA, fontSize: TUNE.costLabel, color: COLOR.hot, whiteSpace: "nowrap" }}>재료 원가</div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr auto",
            alignItems: "baseline",
            columnGap: 24,
            marginTop: 4,
          }}
        >
          <span style={{ fontFamily: BLACK, fontSize: TUNE.cost, color: COLOR.hot, whiteSpace: "nowrap" }}>
            {p.cost.toLocaleString("ko-KR")}원
          </span>
          <span style={{ fontFamily: BLACK, fontSize: TUNE.sell, color: COLOR.point, textAlign: "right", whiteSpace: "nowrap" }}>
            {p.ratio}%
          </span>
        </div>
        {p.box && <Box text={p.box} />}
        <Seal />
      </>
    );
  }
  // insight
  return (
    <>
      <div style={{ fontFamily: BLACK, fontSize: TUNE.big, color: COLOR.lead, lineHeight: 1.08, whiteSpace: "nowrap" }}>
        {p.big1}
      </div>
      <div style={{ fontFamily: BLACK, fontSize: TUNE.big, color: COLOR.point, lineHeight: 1.08, whiteSpace: "nowrap" }}>
        {p.big2}
      </div>
      {p.sub && (
        <div style={{ fontFamily: JUA, fontSize: TUNE.sub, color: "#E6DFD4", lineHeight: 1.25, marginTop: 20, whiteSpace: "nowrap" }}>
          {p.sub}
        </div>
      )}
      <Seal />
    </>
  );
};

// 판만 (쇼츠 영상용)
export const PizzaPanel = ({ i = 0, top = 200, pop = 1 }) => {
  const p = PAGES[i] || PAGES[0];
  return (
    <Panel top={top} pop={pop}>
      <PanelBody p={p} />
    </Panel>
  );
};

// 스틸 (인스타 카드 / 점검용)
export const PizzaPage = ({ i = 0, mode = "short" }) => {
  const p = PAGES[i] || PAGES[0];
  const L = LAYOUT[mode] || LAYOUT.short;
  const ballPos =
    mode === "card"
      ? { top: L.ballTop, right: 60 }
      : { bottom: L.ballBottom, left: "50%", transform: "translateX(-50%)" };
  return (
    <AbsoluteFill style={{ background: COLOR.bg }}>
      <div style={{ position: "absolute", ...ballPos }}>
        <OlmaBall3D face="놀람" size={L.ballSize} />
      </div>
      <Panel top={L.panelTop}>
        <PanelBody p={p} />
      </Panel>
    </AbsoluteFill>
  );
};
