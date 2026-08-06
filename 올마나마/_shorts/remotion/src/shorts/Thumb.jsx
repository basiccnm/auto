// 썸네일 — 영상 첫 화면(훅)을 그대로 쓴다.
//
// 🔴 썸네일을 따로 디자인하면 영상과 톤이 어긋나고, 메뉴가 바뀔 때마다 두 군데를 고쳐야 한다.
//    훅 화면이 이미 "메뉴명 + 금액 + 올마나마?"라 썸네일 조건을 다 갖췄다(2026-07-21).
import React from "react";
import { AbsoluteFill } from "remotion";
import { Table } from "../olma/Table";
import { Receipt } from "../olma/Receipt";
import { CFG, C } from "./config";

export const Thumb = ({ wide = false }) => (
  <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
    {wide ? (
      // 가로(롱폼용) — 영수증을 왼쪽, 식탁을 오른쪽에 나란히
      <>
        <div style={{ position: "absolute", top: 20, left: 60, rotate: "-4deg" }}>
          <Receipt brand={CFG.brand} menu={CFG.menu} price={CFG.sell} width={560} hook={CFG.hook} />
        </div>
        <div style={{ position: "absolute", bottom: -60, right: 20 }}>
          <Table width={620} />
        </div>
      </>
    ) : (
      <>
        <div style={{ position: "absolute", top: 110, left: "50%", translate: "-500px 0px", rotate: "-4deg" }}>
          <Receipt brand={CFG.brand} menu={CFG.menu} price={CFG.sell} width={1000} hook={CFG.hook} />
        </div>
        <div style={{ position: "absolute", bottom: 60, left: "50%", translate: "-50% 0px" }}>
          <Table width={980} />
        </div>
      </>
    )}
  </AbsoluteFill>
);
