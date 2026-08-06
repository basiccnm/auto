// 박스 색 고르기용 시안 — 확정되면 config.js의 CFG.box에 옮기고 이 파일은 지운다.
// 🔴 색은 글로 정하면 감이 안 온다. 화면으로 놓고 고른다(2026-07-21).
import React from "react";
import { AbsoluteFill } from "remotion";

import { ChickenBox } from "../olma/ChickenSet";
import { CFG, C } from "./config";
import { BLACK } from "./fonts";

export const BOX_OPTIONS = [
  { key: "A", label: "교촌 시그니처 빨강", body: "#E4002B", lid: "#B80022", logo: "#E4002B" },
  { key: "B", label: "버건디 (지금 것)", body: "#B3121B", lid: "#8E0E15", logo: "#B3121B" },
  { key: "C", label: "검정 + 빨강로고", body: "#1C1C1C", lid: "#000000", logo: "#E4002B" },
  { key: "D", label: "허니 골드", body: "#E8A21C", lid: "#C4820E", logo: "#B8760A" },
  { key: "E", label: "짙은 갈색(간장)", body: "#6B3A16", lid: "#4E2A0F", logo: "#6B3A16" },
  { key: "F", label: "검정 + 골드로고", body: "#1C1C1C", lid: "#000000", logo: "#D9A22B" },
];

export const BoxPick = () => (
  <AbsoluteFill style={{ background: "#FFF1D6", padding: 40 }}>
    <div
      style={{
        fontFamily: BLACK,
        fontSize: 64,
        color: C.ink,
        textAlign: "center",
        marginBottom: 10,
      }}
    >
      교촌 박스 색 시안
    </div>

    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 10,
        flex: 1,
      }}
    >
      {BOX_OPTIONS.map((o) => (
        <div key={o.key} style={{ textAlign: "center" }}>
          <div style={{ fontFamily: BLACK, fontSize: 40, color: C.ink }}>
            {o.key}. {o.label}
          </div>
          <svg viewBox="-20 -70 520 400" width={480} style={{ overflow: "visible" }}>
            <ChickenBox brand={CFG.brand} x={0} y={0} w={460} box={o} />
          </svg>
        </div>
      ))}
    </div>
  </AbsoluteFill>
);
