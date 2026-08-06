// 캐릭터 디자인 점검용 시트 (임시) — 확정되면 지운다.
import React from "react";
import { AbsoluteFill } from "remotion";

import { Olma } from "../olma/Olma";
import { Nama } from "../olma/Nama";
import { C } from "./config";
import { BLACK } from "./fonts";

const FACES = [
  ["무표정", "기본"],
  ["갸웃", "으쓱"],
  ["놀람", "깜짝"],
  ["씩", "가리킴위"],
  ["화남", "가리킴"],
  ["극대노", "만세"],
  ["황홀", "먹기"],
];

export const OlmaSheet = () => (
  <AbsoluteFill style={{ background: "#FFF1D6", padding: "20px 30px" }}>
    <div style={{ fontFamily: BLACK, fontSize: 48, textAlign: "center", color: C.ink }}>
      올마 캡모자 · 나마 양갈래
    </div>

    <div style={{ display: "flex", justifyContent: "center", gap: 24 }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: BLACK, fontSize: 28, color: "#555" }}>민머리(전)</div>
        <Olma face="씩" pose="기본" scale={0.78} hair={null} />
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: BLACK, fontSize: 28, color: "#1B6BD6" }}>캡모자</div>
        <Olma face="씩" pose="기본" scale={0.78} hair="cap" />
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: BLACK, fontSize: 28, color: "#4A3A2A" }}>머리카락</div>
        <Olma face="씩" pose="기본" scale={0.78} hair="hair" />
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: BLACK, fontSize: 28, color: "#4A3A2A" }}>머리 · 극대노</div>
        <Olma face="극대노" pose="만세" scale={0.78} hair="hair" />
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: BLACK, fontSize: 28, color: "#B3121B" }}>나마</div>
        <Nama face="씩" pose="기본" scale={0.78} />
      </div>
    </div>

    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 10 }}>
      <div style={{ fontFamily: BLACK, fontSize: 26, color: "#555", width: 90 }}>올마</div>
      {FACES.map(([f, p]) => (
        <div key={f} style={{ textAlign: "center" }}>
          <div style={{ fontFamily: BLACK, fontSize: 22, color: "#777" }}>{f}</div>
          <Olma face={f} pose={p} scale={0.36} hair="hair" />
        </div>
      ))}
    </div>

    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ fontFamily: BLACK, fontSize: 26, color: "#B3121B", width: 90 }}>나마</div>
      {FACES.map(([f, p]) => (
        <div key={f} style={{ textAlign: "center" }}>
          <div style={{ fontFamily: BLACK, fontSize: 22, color: "#777" }}>{f}</div>
          <Nama face={f} pose={p} scale={0.36} />
        </div>
      ))}
    </div>
  </AbsoluteFill>
);
