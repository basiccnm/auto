// 카드뉴스 — 인스타 캐러셀용 1:1 정사각 (2026-07-24)
//
// 🔴 쇼츠(9:16)와 다른 트랙이다. 쇼츠는 영상, 이건 **정지 이미지 여러 장**.
//    같은 데이터(ep_*.js)를 쓰되 화면은 처음부터 다시 짠다 —
//    세로 영상 레이아웃을 정사각에 우겨넣으면 여백이 이상해진다.
//
// 🔴 인스타 캐러셀 규격: 1080×1080, 2~10장, JPEG 권장.
//    글씨는 크게. 피드에서 축소돼 보이므로 작은 글씨는 안 읽힌다.
//
// 렌더:
//   npx remotion still Card0 out/cards/card-0.png --props='{"i":0}'
//   → 실제로는 render_cards.py 가 장수만큼 돌려준다
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { EP } from "../shorts/ep_top10cheap";

const C = {
  bg: "#12100E",
  yellow: "#FFC42E",
  red: "#E5352B",
  gray: "#9C978C",
  blue: "#8ECBF5",
};

const W = 1080;
const PAD = 72;

// ── 공통 껍데기 ────────────────────────────────────────────
const Frame = ({ children, bg }) => (
  <AbsoluteFill style={{ background: C.bg }}>
    {bg && (
      <Img
        src={staticFile("bg/" + bg + ".png")}
        style={{
          position: "absolute",
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: 0.28,
        }}
      />
    )}
    <AbsoluteFill
      style={{
        padding: PAD,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
      }}
    >
      {children}
    </AbsoluteFill>
    {/* 채널 표식 — 캡처돼 돌아다녀도 출처가 남는다 */}
    <div
      style={{
        position: "absolute",
        bottom: 36,
        right: PAD,
        fontFamily: JUA,
        fontSize: 30,
        color: C.gray,
      }}
    >
      olmanama.com
    </div>
  </AbsoluteFill>
);

// ── ① 표지 ────────────────────────────────────────────────
const Cover = () => (
  <Frame bg="marat06">
    <div style={{ fontFamily: JUA, fontSize: 46, color: C.blue, marginBottom: 18 }}>
      마라탕 원가공개 · 전 재료 62종
    </div>
    <div style={{ fontFamily: BLACK, fontSize: 128, color: "#fff", lineHeight: 1.08 }}>
      이거 팍팍 담으면
    </div>
    <div style={{ fontFamily: BLACK, fontSize: 148, color: C.yellow, lineHeight: 1.08 }}>
      완벽한 호구
    </div>
    <div
      style={{
        marginTop: 40,
        alignSelf: "flex-start",
        background: C.red,
        border: "7px solid #000",
        borderRadius: 999,
        padding: "14px 40px",
        fontFamily: BLACK,
        fontSize: 48,
        color: "#fff",
      }}
    >
      사장님 최애 TOP 10
    </div>
    <div style={{ marginTop: 30, fontFamily: JUA, fontSize: 32, color: C.gray }}>
      → 넘겨서 순위 보기
    </div>
  </Frame>
);

// ── ② 순위 카드 (5개씩) ────────────────────────────────────
const MEDAL = { 1: C.yellow, 2: "#DDE3EA", 3: "#E8A464" };

const RankPage = ({ from, to, note }) => {
  const rows = [...EP.items].sort((a, b) => a[2] - b[2]).filter((r) => r[2] >= from && r[2] <= to);
  return (
    <Frame bg="marat01">
      <div style={{ fontFamily: JUA, fontSize: 40, color: C.blue, marginBottom: 6 }}>
        100g 기준 · 손질·인건비 제외 도매가
      </div>
      <div style={{ fontFamily: BLACK, fontSize: 68, color: C.yellow, marginBottom: 30 }}>
        {from}위 ~ {to}위
      </div>
      {rows.map(([name, price, rank]) => {
        const m = MEDAL[rank];
        return (
          <div
            key={name}
            style={{
              display: "grid",
              gridTemplateColumns: "150px 1fr auto",
              alignItems: "baseline",
              columnGap: 20,
              marginTop: 26,
              fontFamily: m ? BLACK : JUA,
              fontSize: m ? 82 : 68,
              color: m || "#fff",
            }}
          >
            <span style={{ textAlign: "right", fontSize: m ? 66 : 52, color: m || C.gray }}>
              {rank}위
            </span>
            <span style={{ whiteSpace: "nowrap" }}>{name}</span>
            <span style={{ fontVariantNumeric: "tabular-nums" }}>
              {price.toLocaleString()}원
            </span>
          </div>
        );
      })}
      {note && (
        <div style={{ marginTop: 40, fontFamily: JUA, fontSize: 36, color: C.blue }}>
          {note}
        </div>
      )}
    </Frame>
  );
};

// ── ③ 마무리 ──────────────────────────────────────────────
const Outro = () => (
  <Frame bg="marat03">
    <div style={{ fontFamily: BLACK, fontSize: 96, color: "#fff", lineHeight: 1.12 }}>
      1위 양배추
    </div>
    <div style={{ fontFamily: BLACK, fontSize: 150, color: C.yellow, lineHeight: 1.05 }}>
      100g 113원
    </div>
    <div
      style={{
        marginTop: 34,
        fontFamily: JUA,
        fontSize: 46,
        color: "#fff",
        lineHeight: 1.45,
      }}
    >
      셀프바 가격은 100g 2,700원.
      <br />
      같은 무게로 <b style={{ color: C.yellow }}>20배 넘게</b> 차이 납니다.
    </div>
    <div
      style={{
        marginTop: 44,
        fontFamily: JUA,
        fontSize: 34,
        color: C.gray,
        lineHeight: 1.5,
      }}
    >
      ※ 손질비·조리비·인건비 제외한 순수 재료 도매가입니다.
      <br />※ 채소는 장마·폭염에 시세가 크게 오릅니다. 2026.7.23 기준.
    </div>
    <div
      style={{
        marginTop: 46,
        alignSelf: "flex-start",
        background: C.red,
        border: "7px solid #000",
        borderRadius: 999,
        padding: "16px 44px",
        fontFamily: BLACK,
        fontSize: 44,
        color: "#fff",
      }}
    >
      궁금한 메뉴 댓글 주세요
    </div>
  </Frame>
);

// ── 카드 목록 — 이 순서대로 캐러셀에 들어간다 ────────────────
export const CARDS = [
  { id: "cover", el: <Cover /> },
  { id: "rank-10-6", el: <RankPage from={6} to={10} /> },
  { id: "rank-5-1", el: <RankPage from={1} to={5} note="채소·버섯이 몰린 건 우연이 아닙니다" /> },
  { id: "outro", el: <Outro /> },
];

export const Card = ({ i = 0 }) => CARDS[i]?.el ?? <Frame />;
export const CARD_COUNT = CARDS.length;
export const CARD_SIZE = W;
