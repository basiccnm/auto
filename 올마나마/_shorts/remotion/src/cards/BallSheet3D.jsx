// 올마볼 3D 점검 시트 — 표정·소품 한눈에 (2026-07-24)
//   npx remotion still BallSheet3D out/ball3d.png
import React from "react";
import { AbsoluteFill } from "remotion";

import { JUA } from "../shorts/fonts";
import { OlmaBall3D } from "./OlmaBall3D";

const ITEMS = [
  { face: "기본" },
  { face: "웃음" },
  { face: "놀람" },
  { face: "화남" },
  { face: "시무룩" },
  { face: "눈치" },
  { face: "진땀" },
  // 🔴 아래 둘은 표정이 아니라 **표정 + 소품 조합 예시**다(2026-07-24).
  //    표정 목록으로 오해받아 "사장은 뭐야?" 소리를 들었다. 라벨에 조합을 드러낸다
  { face: "기본", prop: "요리사모자", label: "기본 + 모자" },
  { face: "계산", prop: "계산기", label: "계산 + 계산기" },
];

export const BallSheet3D = () => (
  <AbsoluteFill
    style={{
      background: "radial-gradient(120% 100% at 50% 20%, #2A4DA6 0%, #1E3D8C 55%, #182F6E 100%)",
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      alignItems: "center",
      justifyItems: "center",
      padding: 40,
    }}
  >
    {ITEMS.map((it, i) => (
      <div key={i} style={{ textAlign: "center" }}>
        <OlmaBall3D face={it.face} prop={it.prop} size={300} />
        <div style={{ fontFamily: JUA, fontSize: 34, color: "#fff", marginTop: 10 }}>
          {it.label || it.face}
        </div>
      </div>
    ))}
  </AbsoluteFill>
);
