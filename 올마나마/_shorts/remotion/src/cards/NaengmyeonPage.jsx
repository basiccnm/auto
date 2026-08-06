// 물냉면편 판 — 여성향 톤 (2026-08-03)
// 🔴 JeyukPage 를 그대로 복제했다. 골격·색을 건드리지 않는다 — 화면이 편마다 갈라지면 안 된다.
// 🔴 피자편(PizzaPage)과 골격은 같다. 색만 tone.js 를 따른다.
//    쇼츠는 NaengmyeonPanel 만 떼어 쓰고, 스틸(NaengmyeonPage)도 같은 걸 감싼다 → 화면이 갈라지지 않는다
import React from "react";
import { AbsoluteFill } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { BrandBall } from "../olma/BrandBall";
import { GridBg } from "./SoftKit";
import { TONE } from "./tone";
import { PAGES } from "./pages_naengmyeon";

const T = {
  panelW: 1000, pad: 40,
  lead: 66, rowName: 60, rowVal: 74,
  big: 108, sub: 52,
  sellLabel: 54, sell: 84, cost: 132,
  box: 62, seal: 34, gap: 20,
};

const Panel = ({ top = 200, pop = 1, children }) => (
  <div style={{
    position: "absolute", top, left: "50%",
    opacity: Math.min(pop * 2, 1),
    transform: `translateX(-50%) translateY(${(1 - pop) * 50}px) scale(${0.94 + pop * 0.06})`,
    transformOrigin: "50% 0%",
    width: T.panelW, boxSizing: "border-box",
    background: TONE.card, borderRadius: 38, padding: T.pad,
    boxShadow: TONE.shadow, zIndex: 2,
  }}>{children}</div>
);

const Box = ({ text }) => (
  <div style={{ marginTop: 26, background: TONE.softbox, borderRadius: 20,
    padding: "22px 28px", fontFamily: JUA, fontSize: T.box, color: "#111111", whiteSpace: "nowrap" }}>
    {text}
  </div>
);

const Seal = ({ dense = false }) => (
  // 🔴 **가격은 날마다 달라진다는 안내를 반드시 남긴다**(2026-07-25 지시).
  //    시세가 움직이는데 숫자만 박아두면 나중에 틀린 정보가 된다.
  // 줄이 많은 판(dense)에서는 한 줄로 줄여서라도 **반드시 넣는다**
  <div style={{ marginTop: dense ? 10 : 20, textAlign: "right", fontFamily: JUA,
                fontSize: dense ? T.seal - 4 : T.seal, color: "#555555", lineHeight: 1.4 }}>
    {dense ? (
      "· 재료값 기준 · 시세라 날마다 달라져요 ·"
    ) : (
      <>
        · 재료값 기준이에요 ·<br />
        · 시세라서 날마다 달라져요 ·
      </>
    )}
  </div>
);

const Body = ({ p }) => {
  if (p.kind === "rows") {
    // 🔴 줄이 4개가 되면 판이 길어져서 **말풍선이 마지막 줄을 덮는다**(2026-07-25 실제 발생).
    //    줄 수가 많은 판은 간격·글씨를 조이고 도장(Seal)을 뺀다.
    const dense = p.rows.length >= 4;
    const gap = dense ? 12 : T.gap;
    const nameSize = dense ? 54 : T.rowName;
    const valSize = dense ? 66 : T.rowVal;
    return (
      <>
        <div style={{ fontFamily: JUA, fontSize: T.lead, color: TONE.ink }}>{p.lead}</div>
        {p.rows.map(([n, v, hot]) => (
          <div key={n} style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "baseline",
            marginTop: gap, borderTop: `2px solid ${TONE.line}`, paddingTop: gap }}>
            <span style={{ fontFamily: JUA, fontSize: nameSize, color: hot ? TONE.point : TONE.ink, whiteSpace: "nowrap" }}>{n}</span>
            <span style={{ fontFamily: BLACK, fontSize: valSize, color: hot ? TONE.point : TONE.ink, whiteSpace: "nowrap" }}>{v}</span>
          </div>
        ))}
        {p.box && <Box text={p.box} />}
        <Seal dense={dense} />
      </>
    );
  }
  if (p.kind === "reveal") return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", alignItems: "baseline", columnGap: 20 }}>
        <span style={{ fontFamily: JUA, fontSize: T.sellLabel, color: TONE.ink }}>판매가</span>
        <span style={{ fontFamily: BLACK, fontSize: T.sell, color: TONE.ink, textAlign: "right" }}>
          {p.sell.toLocaleString("ko-KR")}원
        </span>
      </div>
      <div style={{ borderTop: `3px solid ${TONE.line}`, margin: "16px 0" }} />
      <div style={{ fontFamily: JUA, fontSize: T.sellLabel, color: TONE.point }}>재료값</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "baseline", marginTop: 2 }}>
        <span style={{ fontFamily: BLACK, fontSize: T.cost, color: TONE.point, whiteSpace: "nowrap" }}>
          {p.cost.toLocaleString("ko-KR")}원
        </span>
        <span style={{ fontFamily: BLACK, fontSize: T.sell, color: TONE.gold }}>{p.ratio}%</span>
      </div>
      {p.box && <Box text={p.box} />}
      <Seal />
    </>
  );
  return (
    <>
      <div style={{ fontFamily: BLACK, fontSize: T.big, color: TONE.ink, lineHeight: 1.1, whiteSpace: "nowrap" }}>{p.big1}</div>
      <div style={{ fontFamily: BLACK, fontSize: T.big, color: TONE.point, lineHeight: 1.1, whiteSpace: "nowrap" }}>{p.big2}</div>
      {p.sub && <div style={{ fontFamily: JUA, fontSize: T.sub, color: TONE.ink, marginTop: 16, whiteSpace: "nowrap" }}>{p.sub}</div>}
      <Seal />
    </>
  );
};

export const NaengmyeonPanel = ({ i = 0, top = 200, pop = 1 }) => (
  <Panel top={top} pop={pop}><Body p={PAGES[i] || PAGES[0]} /></Panel>
);

export const NaengmyeonPage = ({ i = 0 }) => (
  <GridBg base={TONE.bg} line={TONE.grid}>
    <div style={{ position: "absolute", bottom: 110, left: "calc(50% - 215px)", transform: "translateX(-50%)" }}>
      <BrandBall brand="사장님" face="웃음" scale={1.0} blush />
    </div>
    <div style={{ position: "absolute", bottom: 110, left: "calc(50% + 215px)", transform: "translateX(-50%)" }}>
      <BrandBall brand="올마" face="놀람" scale={1.15} blush pin lashes />
    </div>
    <Panel top={220}><Body p={PAGES[i] || PAGES[0]} /></Panel>
  </GridBg>
);
