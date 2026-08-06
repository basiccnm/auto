// 낙서 프레임 점검 시트 — npx remotion still DoodleSheet out/doodle.png
import React from "react";
import { AbsoluteFill } from "remotion";

import { JUA } from "../shorts/fonts";
import { DoodleFrame, FRAMES } from "./Doodle";

const KINDS = ["화내기", "계산", "놀람"];

export const DoodleSheet = () => (
  <AbsoluteFill
    style={{
      background: "radial-gradient(120% 100% at 50% 20%, #2A4DA6 0%, #1E3D8C 55%, #182F6E 100%)",
      padding: 50,
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-around",
    }}
  >
    {KINDS.map((k) => (
      <div key={k}>
        <div style={{ fontFamily: JUA, fontSize: 40, color: "#fff", marginBottom: 8 }}>{k}</div>
        <div style={{ display: "flex", gap: 30 }}>
          {Array.from({ length: FRAMES[k] }).map((_, f) => (
            <DoodleFrame key={f} kind={k} f={f} width={210} />
          ))}
        </div>
      </div>
    ))}
  </AbsoluteFill>
);
