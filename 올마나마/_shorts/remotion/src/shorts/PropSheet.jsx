// 소품 점검용 시트 (임시) — 확정되면 지운다.
import React from "react";
import { AbsoluteFill } from "remotion";

import {
  BeeToy, Calculator, EarMuffs, Glasses, Magnifier, Pointer,
  PriceBoard, Ruler, SignBoard, StampTool, Toothpick, Umbrella,
} from "../olma/Props";
import { Nama } from "../olma/Nama";
import { C } from "./config";
import { BLACK } from "./fonts";

// 손에 드는 소품 — 시트에서는 가운데(120,110)에 놓고 본다
const HELD = [
  ["자 (손등 때리기)", (p) => <Ruler {...p} />],
  ["계산기", (p) => <Calculator {...p} />],
  ["단가표 표지판", (p) => <PriceBoard {...p} />],
  ["돋보기", (p) => <Magnifier {...p} />],
  ["도장", (p) => <StampTool {...p} />],
  ["꿀벌 인형", (p) => <BeeToy {...p} />],
  ["이쑤시개+무", (p) => <Toothpick {...p} />],
  ["우산", (p) => <Umbrella {...p} />],
  ["지휘봉", (p) => <Pointer {...p} />],
  ["표지판", (p) => <SignBoard {...p} />],
];

export const PropSheet = () => (
  <AbsoluteFill style={{ background: "#FFF1D6", padding: "20px 30px" }}>
    <div style={{ fontFamily: BLACK, fontSize: 48, textAlign: "center", color: C.ink }}>
      소품 12종
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gridAutoRows: "260px" }}>
      {HELD.map(([label, render]) => (
        <div key={label} style={{ textAlign: "center" }}>
          <div style={{ fontFamily: BLACK, fontSize: 24, color: "#555" }}>{label}</div>
          <svg viewBox="0 0 260 210" width={260} style={{ overflow: "visible" }}>
            {render({ x: 130, y: 105 })}
          </svg>
        </div>
      ))}
    </div>

    {/* 얼굴에 붙는 것들 — 나마에 씌워서 본다 */}
    <div style={{ display: "flex", justifyContent: "center", gap: 60, marginTop: 10 }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: BLACK, fontSize: 24, color: "#555" }}>안경</div>
        <Nama face="무표정" pose="기본" scale={0.6} glasses={0} />
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: BLACK, fontSize: 24, color: "#555" }}>안경 삐뚤 (부딪힌 뒤)</div>
        <Nama face="헉" pose="깜짝" scale={0.6} glasses={-18} />
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: BLACK, fontSize: 24, color: "#555" }}>귀마개 (화산 대비)</div>
        <Nama face="무표정" pose="기본" scale={0.6} earmuffs />
      </div>
    </div>
  </AbsoluteFill>
);
