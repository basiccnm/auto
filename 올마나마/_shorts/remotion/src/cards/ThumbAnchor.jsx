// 배달 1편 썸네일 — 마라탕 시리즈 썸네일과 **똑같은 형태** (2026-07-24)
//
// 🔴 형태는 마라탕 3편 썸네일(out/마라탕3편_인상쓰는TOP10.mp4 0프레임) 실측 그대로다.
//      배경 꽉 참 → 상단 검은 판 → 판 안에 4줄(서브·큰줄1·큰줄2·편제목) → 바로 아래 시리즈 배지 → 하단에 주인공 그림
//    임의로 구조를 바꾸지 말 것. 마라탕과 같은 얼굴로 보여야 시리즈로 읽힌다.
//
// 🔴 색은 **미지정**(2026-07-24 지시). 아래 COLOR 하나만 고치면 전부 바뀐다.
//    지금 값은 배달 카드뉴스에서 쓰던 남색+빨강을 임시로 넣어둔 것뿐이다.
//
// 🔴 글씨는 마라탕보다 키웠다(지시: "지금 보기가 힘들다").
//    마라탕 3편 대비 서브 58→66 · 큰줄1 100→126 · 큰줄2 128→160 · 제목 56→74
//    ⚠️ 판 안쪽 폭이 932px다. 글씨를 더 키우면 한 줄이 넘쳐 두 줄로 흘러내린다(카드뉴스에서 났던 사고).
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { EP } from "./card_anchor";

// ── 색 (미지정 — 여기만 고치면 된다) ─────────────────────────
const COLOR = {
  bg: "radial-gradient(120% 90% at 50% 18%, #2A4DA6 0%, #1E3D8C 55%, #182F6E 100%)",
  panel: "rgba(12,12,14,0.86)", // 판
  sub: "#C9C4B8", // 서브줄
  line1: "#FFFFFF", // 큰줄 1
  point: "#FF5B45", // 큰줄 2 = 강조. 이 색이 편의 성격을 정한다
  title: "#8ECBF5", // 편 제목
  badge: "#E8493F", // 시리즈 배지 바탕
  badgeInk: "#FFFFFF",
};

// ── 조정용 숫자 (여기만 고치면 된다) ─────────────────────────
const TUNE = {
  panelTop: 230, // 판 세로 위치 (마라탕과 동일)
  panelW: 1000,
  panelPadX: 34,
  panelPadY: 26,

  sub: 66, // "배달앱 꿀팁"
  line1: 126, // "할인 큰 집이"
  line2: 160, // "더 비싸다?"  ← 강조
  title: 74, // 편 제목
  badge: 70, // 시리즈 배지
  badgeGap: 16,

  ballSize: 560, // 하단 주인공 — 마라탕의 마라탕그릇 자리
  ballBottom: 150,
};

// 문구 — 데이터는 card_anchor.js에서 온다
const T = {
  sub: `${EP.series}`, // 배달 꿀팁
  line1: "할인 큰 집이",
  line2: "더 비싸다?",
  title: EP.title, // 배달 옵션 꼼수의 비밀
  badge: `${EP.series} 1`,
};

// ⚓ 닻 — 마라탕 썸네일에서 **마라탕 그릇이 있던 자리**를 채운다 (2026-07-24 지시).
//    "앵커링(anchoring)"의 어원이 닻이다. 편 주제를 그림 하나로 설명해 주고,
//    빈 매장 배경이라 아래가 휑하던 것도 같이 해결된다.
//    🔴 SVG로 직접 그린다 — 이모지는 기기마다 모양이 달라 렌더가 흔들린다.
const Anchor = ({ size = 620 }) => (
  <svg width={size} height={size} viewBox="0 0 200 200" style={{ overflow: "visible" }}>
    <g
      fill="none"
      stroke="#0E0E10"
      strokeWidth={17}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {/* 고리 */}
      <circle cx="100" cy="30" r="15" />
      {/* 기둥 */}
      <path d="M100 45 V172" />
      {/* 가로대 */}
      <path d="M64 70 H136" />
      {/* 갈고리 — 바닥에서 양쪽으로 휜다 */}
      <path d="M38 118 q0 54 62 54 q62 0 62 -54" />
      {/* 갈고리 끝 미늘 */}
      <path d="M38 118 l-16 22 M38 118 l22 12" />
      <path d="M162 118 l16 22 M162 118 l-22 12" />
    </g>
    <g fill="none" stroke="#F5B70C" strokeWidth={9} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="100" cy="30" r="15" />
      <path d="M100 45 V172" />
      <path d="M64 70 H136" />
      <path d="M38 118 q0 54 62 54 q62 0 62 -54" />
      <path d="M38 118 l-16 22 M38 118 l22 12" />
      <path d="M162 118 l16 22 M162 118 l-22 12" />
    </g>
  </svg>
);

// 🔴 판+배지만 따로 뽑아둔다 — 쇼츠(TalkAnchor)의 훅 화면이 이걸 그대로 쓴다.
//    쇼츠에선 배경·캐릭터를 talk_engine이 그리니 여기서 배경을 또 깔면 안 된다.
//    **썸네일과 쇼츠 첫 프레임이 같은 그림이어야** 목록에서 본 얼굴이 영상에서 이어진다
// 🔴 판형별 배치 (2026-07-24) — 문구·글씨크기·색은 완전히 같고 **위치만** 다르다.
//    short = 1080×1920 쇼츠 훅 / card = 1080×1080 인스타 캐러셀 표지.
//    캐러셀 1번 장이 곧 피드 썸네일이라 **쇼츠 훅을 그대로 쓴다**(2026-07-24 지시).
const THUMB_LAYOUT = {
  short: { panelTop: 230, anchorSize: 620, anchorBottom: 230 },
  card: { panelTop: 120, anchorSize: 230, anchorBottom: 14 },
};

export const ThumbCard = ({ mode = "short" }) => {
  const L = THUMB_LAYOUT[mode] || THUMB_LAYOUT.short;
  return (
  <>
    {/* 닻은 판보다 뒤(아래 레이어). 마라탕에서 그릇이 있던 자리다 */}
    <div style={{ position: "absolute", bottom: L.anchorBottom, left: "50%", transform: "translateX(-50%)", zIndex: 0 }}>
      <Anchor size={L.anchorSize} />
    </div>
    <div
      style={{
        position: "absolute",
        top: L.panelTop,
        left: "50%",
        transform: "translateX(-50%)",
        width: TUNE.panelW,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <div
        style={{
          width: "100%",
          boxSizing: "border-box",
          background: COLOR.panel,
          border: "8px solid #000",
          borderRadius: 30,
          padding: `${TUNE.panelPadY}px ${TUNE.panelPadX}px`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div style={{ fontFamily: JUA, fontSize: TUNE.sub, color: COLOR.sub, lineHeight: 1.02, whiteSpace: "nowrap" }}>
          {T.sub}
        </div>
        <div style={{ fontFamily: BLACK, fontSize: TUNE.line1, color: COLOR.line1, lineHeight: 1.05, whiteSpace: "nowrap" }}>
          {T.line1}
        </div>
        <div style={{ fontFamily: BLACK, fontSize: TUNE.line2, color: COLOR.point, lineHeight: 1.05, whiteSpace: "nowrap" }}>
          {T.line2}
        </div>
        <div
          style={{
            fontFamily: BLACK,
            fontSize: TUNE.title,
            color: COLOR.title,
            lineHeight: 1.05,
            whiteSpace: "nowrap",
            marginTop: 8,
          }}
        >
          {T.title}
        </div>
      </div>

      {/* 시리즈 배지 — talk_engine의 SeriesBadge는 빨강 고정이라, 색을 바꿀 수 있게 여기서 그린다 */}
      <div
        style={{
          width: "100%",
          boxSizing: "border-box",
          marginTop: TUNE.badgeGap,
          background: COLOR.badge,
          border: "6px solid #000",
          borderRadius: 26,
          padding: "26px 0",
          textAlign: "center",
          fontFamily: BLACK,
          fontSize: TUNE.badge,
          color: COLOR.badgeInk,
        }}
      >
        {T.badge}
      </div>
    </div>
  </>
  );
};

// 스틸(썸네일 파일)
// 🔴 **쇼츠의 0프레임과 픽셀 단위로 같아야 한다**(2026-07-24).
//    쇼츠 썸네일은 유튜브 앱에서만 바꿀 수 있어서 사실상 첫 화면이 썸네일이다.
//    그래서 배경도 talk_engine과 같은 store03 + 같은 그라데이션을 쓰고,
//    캐릭터도 안 넣는다(엔진이 훅 화면에선 캐릭터를 숨긴다).
//    단색 배경에 3D 볼을 얹은 옛 버전은 영상 첫 프레임과 달라서 폐기했다.
export const ThumbAnchor = ({ mode = "short" }) => (
  <AbsoluteFill style={{ background: "#000" }}>
    <Img src={staticFile("bg/store03.png")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(180deg, rgba(0,0,0,.5) 0%, rgba(0,0,0,0) 26%, rgba(0,0,0,0) 44%, rgba(0,0,0,.62) 100%)",
      }}
    />
    <ThumbCard mode={mode} />
  </AbsoluteFill>
);
