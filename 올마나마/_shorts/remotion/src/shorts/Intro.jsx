// 인트로 — 첫 장면 구도부터 확정 (2026-07-21)
//
// 🔴 움직임은 나중에. 지금은 **정지 화면 구도만** 잡는다.
//    (영수증 날아오기·자빠지기·별 튀기는 구도 확정 후에 얹는다)
//
// 구도:  위 텍스트 / 가운데 탁자 + 황금올리브 / 그 위에 영수증 / 옆에 올마
import React from "react";
import { AbsoluteFill } from "remotion";
import { Olma } from "../olma/Olma";
import { Table } from "../olma/Table";
import { Receipt } from "../olma/Receipt";
import { CFG, C } from "./config";
import { BLACK, JUA } from "./fonts";

export const Intro = () => {
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      {/* 🔴 영수증을 **먼저** 그려 뒤로 보낸다. 탁자·치킨이 앞으로 나와야
          영수증 아래 핑킹가위 자국이 탁자에 살짝 걸린다(2026-07-21 지시). */}
      <div
        style={{
          position: "absolute",
          top: 110,
          left: "50%",
          translate: "-440px 0px",
          rotate: "-4deg",
        }}
      >
        <Receipt brand={CFG.brand} menu={CFG.menu} price={CFG.sell} width={880} hook="올마나마?" />
      </div>

      {/* 탁자 + 치킨 — 영수증 앞. Table의 viewBox 중심이 450/900이라 -50%면 정확히 가운데 */}
      <div style={{ position: "absolute", bottom: 60, left: "50%", translate: "-50% 0px" }}>
        <Table width={980} />
      </div>

    </AbsoluteFill>
  );
};
