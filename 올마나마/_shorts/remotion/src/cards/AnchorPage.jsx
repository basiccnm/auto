// 배달 1편 뒷장 화면 — 마라탕 본편 형식 (2026-07-24)
//
// 🔴 마라탕 본편 구조를 그대로 쓴다: 배경 + 검은 판 한 장 + 하단 캐릭터.
//    러닝헤드·태그칩 같은 작은 글씨는 전부 뺐다 (2026-07-24 지시: "작은 건 XXX").
//
// 🔴 옛 카드뉴스에서 났던 결함 3개를 **구조로** 막는다
//    ① 라벨이 두 줄로 흘러내림 → 모든 텍스트 nowrap. 문구를 길게 쓰면 안 들어간다
//    ② 두 숫자가 붙어 겹침     → A집·B집을 위아래 두 줄로 분리(한 줄에 값 하나)
//    ③ 볼이 글자를 가림        → 볼은 **판 밖 아래**에만 둔다. 판이 제일 긴 장도 y1063,
//                                볼 머리가 y1309이라 안 닿는다
import React from "react";
import { AbsoluteFill } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { OlmaBall3D } from "./OlmaBall3D";
import { PAGES } from "./pages_anchor";

// 🔴 색은 미지정 — ThumbAnchor.jsx의 COLOR와 같은 값이다. 바꿀 땐 둘 다 고칠 것
const COLOR = {
  bg: "radial-gradient(120% 90% at 50% 18%, #2A4DA6 0%, #1E3D8C 55%, #182F6E 100%)",
  panel: "rgba(12,12,14,0.86)",
  lead: "#FFFFFF",
  kicker: "#C9C4B8",
  a: "#FF5B45", // A집 — 할인 큰 집(꼼수)
  b: "#6BB6FF", // B집 — 할인 적은 집(정상)
  dim: "#FFFFFF",
  boxBg: "#FFF3D6",
  boxBar: "#F5B70C",
  boxInk: "#7A5200",
  site: "#FFC42E",
};

// ── 판형 (2026-07-24) ────────────────────────────────────────
// 🔴 **한 소스에서 두 벌이 나온다.** 데이터·문구·색·글씨크기는 완전히 같고,
//    다른 건 판 위치와 볼 자리뿐이다. 문구를 두 번 관리하면 반드시 어긋난다.
//      short = 1080×1920 쇼츠용. 판은 위, 볼은 아래 크게
//      card  = 1080×1080 인스타 캐러셀용. 정사각이라 아래 여백이 없다 →
//              볼을 **판 위쪽 바깥**으로 올린다. 판 안으로 들여보내면 글자를 가린다(옛 사고)
export const SIZE = { short: { w: 1080, h: 1920 }, card: { w: 1080, h: 1080 } };

const LAYOUT = {
  short: { panelTop: 250, ballSize: 430, ballBottom: 130, ballTop: null },
  card: { panelTop: 210, ballSize: 250, ballBottom: null, ballTop: 0 },
};

// ── 조정용 숫자 (여기만 고치면 된다) ─────────────────────────
// 🔴 전부 68 이상이다. 이 밑으로 내리지 말 것 (판형이 바뀌어도 글씨는 안 줄인다)
const TUNE = {
  panelW: 1000,
  panelPad: 40,

  lead: 74, // 리드 문장
  kicker: 68, // 무슨 값인지 (즉시할인·최종 결제액…)
  badge: 68, // A집 / B집 알약
  value: 130, // 숫자 — 이 편의 주인공
  big: 150, // why·cta 큰 문구
  sub: 74, // 보조 문장
  box: 76, // 하단 강조바
  site: 96, // olmanama.com

  badgeCol: 200, // 알약 칸 고정폭 — 값이 밀리지 않는다
  colGap: 40,
  rowGap: 24,
};

// pop을 주면 판이 살짝 아래에서 올라오며 커진다 (쇼츠에서 장이 넘어가는 느낌)
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

// 한 줄 = [A집 알약] [값]. 한 줄에 값이 하나뿐이라 숫자를 크게 쓸 수 있다
const ValueRow = ({ who, value, hot }) => {
  const col = who === "A집" ? COLOR.a : COLOR.b;
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `${TUNE.badgeCol}px 1fr`,
        columnGap: TUNE.colGap,
        alignItems: "center",
        marginTop: TUNE.rowGap,
      }}
    >
      <div
        style={{
          background: col,
          border: "5px solid #000",
          borderRadius: 999,
          padding: "8px 0",
          textAlign: "center",
          fontFamily: BLACK,
          fontSize: TUNE.badge,
          color: "#fff",
        }}
      >
        {who}
      </div>
      <div
        style={{
          fontFamily: BLACK,
          fontSize: TUNE.value,
          color: hot ? col : COLOR.dim,
          textAlign: "right",
          whiteSpace: "nowrap",
          lineHeight: 1.1,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {value}
      </div>
    </div>
  );
};

const Box = ({ text }) => (
  <div
    style={{
      marginTop: 40,
      background: COLOR.boxBg,
      borderLeft: `16px solid ${COLOR.boxBar}`,
      borderRadius: 12,
      padding: "26px 32px",
      fontFamily: BLACK,
      fontSize: TUNE.box,
      color: COLOR.boxInk,
      whiteSpace: "nowrap",
    }}
  >
    {text}
  </div>
);

// ── 판만 따로 (쇼츠 영상용) ──────────────────────────────────
// 🔴 쇼츠(TalkAnchor)는 배경·캐릭터·말풍선을 talk_engine이 직접 그린다.
//    그래서 판만 떼어 쓴다. 스틸(AnchorPage)도 결국 이걸 감싼 것이라
//    **화면이 두 벌로 갈라지지 않는다** — 한 곳만 고치면 스틸도 영상도 같이 바뀐다.
// 🔴 쇼츠에선 showBox=false 로 쓴다. 판이 길어지면 y820 말풍선과 겹치기 때문이다.
//    (판 top 200 + 최대 높이 588 = 788 → 말풍선 바로 위에서 끝난다)
export const AnchorPanel = ({ i = 0, top = 200, pop = 1, showBox = true, showSite = true }) => {
  const p = PAGES[i] || PAGES[0];
  return (
    <Panel top={top} pop={pop}>
      <PanelBody p={p} showBox={showBox} showSite={showSite} />
    </Panel>
  );
};

export const AnchorPage = ({ i = 0, mode = "short" }) => {
  const p = PAGES[i] || PAGES[0];
  const L = LAYOUT[mode] || LAYOUT.short;
  // short = 볼이 화면 아래 가운데 / card = 볼이 판 위 오른쪽(정사각엔 아래 여백이 없다)
  const ballPos =
    mode === "card"
      ? { top: L.ballTop, right: 60 }
      : { bottom: L.ballBottom, left: "50%", transform: "translateX(-50%)" };
  return (
    <AbsoluteFill style={{ background: COLOR.bg }}>
      <div style={{ position: "absolute", ...ballPos }}>
        <OlmaBall3D face={p.face} prop={p.prop || null} size={L.ballSize} />
      </div>

      <Panel top={L.panelTop}>
        <PanelBody p={p} showBox showSite />
      </Panel>
    </AbsoluteFill>
  );
};

const PanelBody = ({ p, showBox, showSite }) => {
  return (
    <>
        {/* 문구형 장 — why · cta */}
        {p.big1 && (
          <>
            <div style={{ fontFamily: BLACK, fontSize: TUNE.big, color: COLOR.lead, lineHeight: 1.08, whiteSpace: "nowrap" }}>
              {p.big1}
            </div>
            <div style={{ fontFamily: BLACK, fontSize: TUNE.big, color: COLOR.a, lineHeight: 1.08, whiteSpace: "nowrap" }}>
              {p.big2}
            </div>
            <div
              style={{
                fontFamily: JUA,
                fontSize: TUNE.sub,
                color: COLOR.kicker,
                lineHeight: 1.25,
                marginTop: 22,
                whiteSpace: "pre-line",
              }}
            >
              {p.sub}
            </div>
          </>
        )}

        {/* 숫자형 장 — problem · option · result */}
        {p.lead && (
          <>
            <div style={{ fontFamily: BLACK, fontSize: TUNE.lead, color: COLOR.lead, lineHeight: 1.1, whiteSpace: "nowrap" }}>
              {p.lead}
            </div>
            <div
              style={{
                fontFamily: JUA,
                fontSize: TUNE.kicker,
                color: COLOR.kicker,
                marginTop: 18,
                whiteSpace: "nowrap",
              }}
            >
              {p.kicker}
            </div>
            <ValueRow who="A집" value={p.a} hot={p.win === "a"} />
            <ValueRow who="B집" value={p.b} hot={p.win === "b"} />
          </>
        )}

        {p.box && showBox && <Box text={p.box} />}

        {/* 마무리 — 사이트 유도 */}
        {p.site && showSite && (
          <div
            style={{
              marginTop: 40,
              background: "#14161C",
              border: "6px solid #000",
              borderRadius: 20,
              padding: "28px 0",
              textAlign: "center",
              fontFamily: BLACK,
              fontSize: TUNE.site,
              color: COLOR.site,
            }}
          >
            {p.site}
          </div>
        )}
    </>
  );
};
