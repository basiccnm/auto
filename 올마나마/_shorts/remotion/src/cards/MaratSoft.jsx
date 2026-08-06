// 마라탕 2편을 여성향 톤으로 — 시안 (2026-07-25)
// 🔴 참고 이미지대로: 격자배경 + 리본배너 + 흰 카드 + 주방도구 소품 + 캐릭터
//    부품은 SoftKit.jsx (전부 코드로 그림). 음식만 이미지.
import React from "react";
import { Img, staticFile } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { BrandBall } from "../olma/BrandBall";
import { GridBg, Ribbon, CloudBubble, ToolScatter, SoftCard } from "./SoftKit";

const C = { ink: "#5A4A42", sub: "#A08D82", point: "#E8748A", gold: "#E0A040" };

// ① 표지 — 훅
// 🔴 배경 톤 시안(2026-07-25) — "색이 너무 밝다"
//    A: 베이지를 한 단계 낮춤 / B: 웜그레이로 더 눌러서 흰 카드가 확실히 떠 보이게
const BG_A = { base: "#EFE6D9", line: "rgba(150,120,95,.20)" };
// 🔴 빙수편 톤 — 복숭아·크림 계열. 베이지보다 따뜻하고 여성향에 맞다(2026-07-25 지시)
const BG_P = { base: "#FBE4D6", line: "rgba(190,130,105,.18)" };
const BG_B = { base: "#E3DACE", line: "rgba(130,105,85,.22)" };

export const MaratSoftA = () => (
  <GridBg base={BG_A.base} line={BG_A.line}>
    <ToolScatter opacity={0.55} />
    <SoftCard top={200} pad="34px 40px">
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 48, color: C.sub }}>마라탕 원가공개</div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 108, color: C.ink, marginTop: 10 }}>
        이거 팍팍 담으면
      </div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 122, color: C.point, marginTop: 2 }}>
        완벽한 호구
      </div>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 54, color: C.sub, marginTop: 14 }}>
        사장님 최애 TOP 10
      </div>
    </SoftCard>
    <div style={{ position: "absolute", top: 700, left: "50%", transform: "translateX(-50%)", zIndex: 3 }}>
      <Ribbon text="이거 얼마남아 3" w={620} />
    </div>
    <Img src={staticFile("bg/marat_bowl.png")}
      style={{ position: "absolute", top: 860, left: "50%", transform: "translateX(-50%)", width: 700, zIndex: 1 }} />
    <div style={{ position: "absolute", bottom: 90, left: "calc(50% - 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="사장님" face="시치미" scale={1.0} blush />
    </div>
    <div style={{ position: "absolute", bottom: 90, left: "calc(50% + 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="올마" face="놀람" scale={1.15} blush />
    </div>
  </GridBg>
);

export const MaratSoftP = () => (
  <GridBg base={BG_P.base} line={BG_P.line}>
    <ToolScatter opacity={0.5} />
    <SoftCard top={200} pad="34px 40px">
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 48, color: C.sub }}>마라탕 원가공개</div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 108, color: C.ink, marginTop: 10 }}>
        이거 팍팍 담으면
      </div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 122, color: C.point, marginTop: 2 }}>
        완벽한 호구
      </div>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 54, color: C.sub, marginTop: 14 }}>
        사장님 최애 TOP 10
      </div>
    </SoftCard>
    <div style={{ position: "absolute", top: 700, left: "50%", transform: "translateX(-50%)", zIndex: 3 }}>
      <Ribbon text="이거 얼마남아 3" w={620} />
    </div>
    <Img src={staticFile("bg/marat_bowl.png")}
      style={{ position: "absolute", top: 860, left: "50%", transform: "translateX(-50%)", width: 700, zIndex: 1 }} />
    <div style={{ position: "absolute", bottom: 90, left: "calc(50% - 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="사장님" face="시치미" scale={1.0} blush />
    </div>
    <div style={{ position: "absolute", bottom: 90, left: "calc(50% + 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="올마" face="놀람" scale={1.15} blush />
    </div>
  </GridBg>
);

export const MaratSoftB = () => (
  <GridBg base={BG_B.base} line={BG_B.line}>
    <ToolScatter opacity={0.55} />
    <SoftCard top={200} pad="34px 40px">
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 48, color: C.sub }}>마라탕 원가공개</div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 108, color: C.ink, marginTop: 10 }}>
        이거 팍팍 담으면
      </div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 122, color: C.point, marginTop: 2 }}>
        완벽한 호구
      </div>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 54, color: C.sub, marginTop: 14 }}>
        사장님 최애 TOP 10
      </div>
    </SoftCard>
    <div style={{ position: "absolute", top: 700, left: "50%", transform: "translateX(-50%)", zIndex: 3 }}>
      <Ribbon text="이거 얼마남아 3" w={620} />
    </div>
    <Img src={staticFile("bg/marat_bowl.png")}
      style={{ position: "absolute", top: 860, left: "50%", transform: "translateX(-50%)", width: 700, zIndex: 1 }} />
    <div style={{ position: "absolute", bottom: 90, left: "calc(50% - 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="사장님" face="시치미" scale={1.0} blush />
    </div>
    <div style={{ position: "absolute", bottom: 90, left: "calc(50% + 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="올마" face="놀람" scale={1.15} blush />
    </div>
  </GridBg>
);

export const MaratSoft1 = () => (
  <GridBg>
    <ToolScatter opacity={0.5} />
    <SoftCard top={150} pad="34px 40px">
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 48, color: C.sub }}>마라탕 원가공개</div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 108, color: C.ink, marginTop: 10 }}>
        이거 팍팍 담으면
      </div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 122, color: C.point, marginTop: 2 }}>
        완벽한 호구
      </div>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 54, color: C.sub, marginTop: 14 }}>
        사장님 최애 TOP 10
      </div>
    </SoftCard>
    <div style={{ position: "absolute", top: 640, left: "50%", transform: "translateX(-50%)", zIndex: 3 }}>
      <Ribbon text="이거 얼마남아 3" w={620} />
    </div>
    <Img
      src={staticFile("food/s09_02.png")}
      style={{ position: "absolute", top: 850, left: "50%", transform: "translateX(-50%)", width: 760, zIndex: 1 }}
    />
    <div style={{ position: "absolute", bottom: 90, left: "calc(50% - 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="사장님" face="시치미" scale={1.0} blush />
    </div>
    <div style={{ position: "absolute", bottom: 90, left: "calc(50% + 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="올마" face="놀람" scale={1.15} blush />
    </div>
  </GridBg>
);

// ② 순위표
const RANK = [
  [1, "양배추", 113], [2, "알배기배추", 118], [3, "숙주나물", 143], [4, "팽이버섯", 157], [5, "목이버섯", 223],
  [6, "청경채", 239], [7, "큐브감자", 268], [8, "두부피", 280], [9, "옥수수면", 282], [10, "얼갈이배추", 284],
];
export const MaratSoft2 = () => (
  <GridBg>
    <ToolScatter opacity={0.45} />
    <SoftCard top={200} pad="38px 44px">
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 46, color: C.sub }}>전 재료 62종 종합</div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 82, color: C.ink, marginTop: 4 }}>
        사장님 최애 TOP 10
      </div>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 30, color: "#C0AEA4", marginTop: 8, marginBottom: 18 }}>
        100g 기준 · 손질·인건비 제외 도매가
      </div>
      {RANK.map(([r, n, v]) => {
        const top3 = r <= 3;
        return (
          <div key={n} style={{ display: "grid", gridTemplateColumns: "120px 1fr auto", alignItems: "baseline",
            padding: "12px 0", borderBottom: r < 10 ? "2px solid #F3EAE3" : "none" }}>
            <span style={{ fontFamily: top3 ? BLACK : JUA, fontSize: top3 ? 62 : 46,
              color: top3 ? C.point : C.sub, textAlign: "right", paddingRight: 18 }}>{r}위</span>
            <span style={{ fontFamily: top3 ? BLACK : JUA, fontSize: top3 ? 62 : 50, color: C.ink }}>{n}</span>
            <span style={{ fontFamily: BLACK, fontSize: top3 ? 62 : 50, color: top3 ? C.point : C.gold }}>
              {v.toLocaleString("ko-KR")}원
            </span>
          </div>
        );
      })}
    </SoftCard>
  </GridBg>
);

// ③ 대사 장면
export const MaratSoft3 = () => (
  <GridBg>
    <ToolScatter opacity={0.5} />
    <div style={{ position: "absolute", top: 620, left: "50%", transform: "translateX(-50%)", zIndex: 3 }}>
      <CloudBubble text="월세랑 사골 국물값은" tail="right" />
    </div>
    <div style={{ position: "absolute", bottom: 260, left: "calc(50% - 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="사장님" face="발끈" scale={1.15} blush fire />
    </div>
    <div style={{ position: "absolute", bottom: 260, left: "calc(50% + 215px)", transform: "translateX(-50%)", zIndex: 3 }}>
      <BrandBall brand="올마" face="화들짝" scale={1.0} blush />
    </div>
  </GridBg>
);
