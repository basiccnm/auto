// 마라탕 3편 본편 — 종합 TOP10 · 담으면 인상 쓰는(제일 비싼) 재료, 약 65초 (2026-07-23)
//
// 🔴 2편(TalkTop10Cheap.jsx)과 짝. 다른 점은 딱 하나 — **1위가 제일 비싸다.**
//    그래서 정점 색을 금색이 아니라 경고색(EP.peakColor, 빨강)으로 바꿨다.
//    나머지 구조(카운트다운·순위 낙하·전체 표·소품·감정텍스트)는 2편과 동일.
import React from "react";
import { Img, staticFile } from "remotion";

import { C } from "./config";
import { BLACK, JUA } from "./fonts";
import { EP } from "./ep_top10expensive";
import { LEAD, LINES } from "./lines_top10expensive";
import { Card, SeriesBadge, Site, TalkEngine, talkSec, won } from "./talk_engine";

export const TOP10EXPENSIVE_SEC = talkSec(LINES, LEAD);

const TUNE = {
  hookTop: 230,
  hookBottomPad: 26,
  hookSub: 58,
  hookLine1: 100,
  hookLine2: 128,
  hookTitle: 56,
  badgeSize: 62,
  badgeGap: 16,

  rankTop: 280,
  rankNo: 76,
  rankName: 62,
  rankPrice: 148,
  rankFrom: -520,

  allTop: 230,
  allRow: 62,
  allTop1: 90,
  allTop2: 80,
  allTop3: 72,
  allGap: 18,

  countSize: 300,
};

// 🔴 1위만 EP.peakColor(경고 빨강) — 2편의 금색과 다르게, "여기 담으면 안 좋다"는 신호
const RankDrop = ({ idx, pop }) => {
  const [name, price, rank] = EP.items[idx];
  const y = (1 - pop) * TUNE.rankFrom;
  const squash = pop < 0.55 ? 1 : pop < 0.8 ? 1 + (0.8 - pop) * 0.5 : 1;
  const isTop = rank === 1;
  const peak = EP.peakColor || C.red;
  return (
    <div
      style={{
        position: "absolute",
        top: TUNE.rankTop,
        left: "50%",
        zIndex: 6,
        transform: `translateX(-50%) translateY(${y}px) scaleX(${squash}) scaleY(${2 - squash})`,
        transformOrigin: "50% 100%",
        opacity: Math.min(pop * 3, 1),
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textShadow: "0 8px 24px rgba(0,0,0,.75)",
      }}
    >
      <div
        style={{
          background: isTop ? peak : C.red,
          border: "7px solid #000",
          borderRadius: 999,
          padding: "6px 34px",
          fontFamily: BLACK,
          fontSize: TUNE.rankNo,
          color: "#fff",
          marginBottom: 8,
          whiteSpace: "nowrap",
        }}
      >
        {rank}위
      </div>
      <div
        style={{
          fontFamily: JUA,
          fontSize: TUNE.rankName,
          color: "#fff",
          whiteSpace: "nowrap",
          lineHeight: 1.0,
          WebkitTextStroke: "7px #000",
          paintOrder: "stroke fill",
        }}
      >
        {name}
      </div>
      <div
        style={{
          fontFamily: BLACK,
          fontSize: TUNE.rankPrice,
          color: isTop ? peak : C.yellow,
          whiteSpace: "nowrap",
          lineHeight: 1.05,
          WebkitTextStroke: "9px #000",
          paintOrder: "stroke fill",
        }}
      >
        {won(price)}
      </div>
      {/* 🔴 "100g 기준"이 화면에 안 보인다는 지적(2026-07-23) — 가격 바로 밑에 상시 표기 */}
      <div
        style={{
          fontFamily: JUA,
          fontSize: TUNE.rankPrice * 0.22,
          color: "#fff",
          whiteSpace: "nowrap",
          marginTop: -4,
          WebkitTextStroke: "4px #000",
          paintOrder: "stroke fill",
        }}
      >
        (100g 기준)
      </div>
    </div>
  );
};

const Countdown = ({ n, pop }) => (
  <div
    style={{
      position: "absolute",
      top: 480,
      left: "50%",
      zIndex: 7,
      transform: `translateX(-50%) scale(${1.5 - pop * 0.5})`,
      opacity: Math.min(pop * 3, 1),
      fontFamily: BLACK,
      fontSize: TUNE.countSize,
      color: n === 1 ? C.red : "#fff",
      WebkitTextStroke: "18px #000",
      paintOrder: "stroke fill",
      textShadow: "0 10px 30px rgba(0,0,0,.6)",
    }}
  >
    {n}
  </div>
);

// 🔴 이 편은 1위가 경고색, 2·3위만 은·동 — 금색을 안 쓴다("최악"에 금메달은 안 어울린다)
const MEDAL = (peak) => ({
  1: { color: peak, size: TUNE.allTop1 },
  2: { color: "#DDE3EA", size: TUNE.allTop2 },
  3: { color: "#E8A464", size: TUNE.allTop3 },
});

const AllTable = ({ pop = 1 }) => {
  const rows = [...EP.items].sort((a, b) => a[2] - b[2]);
  const stepIn = (i) => Math.max(0, Math.min(1, pop * rows.length - i));
  const MEDALS = MEDAL(EP.peakColor || C.red);
  return (
    <Card wide top={TUNE.allTop}>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 44, color: "#8ECBF5", lineHeight: 1.05, letterSpacing: 1 }}>
        {EP.titleTop}
      </div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 64, color: EP.peakColor, lineHeight: 1.05, marginTop: 6 }}>
        {EP.title}
      </div>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 27, color: "#9C978C", marginTop: 6, marginBottom: 14 }}>
        {EP.date}
      </div>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 24, color: "#FF9B87", marginTop: -6, marginBottom: 14 }}>
        {EP.note}
      </div>
      {rows.map(([name, price, rank], i) => {
        const m = MEDALS[rank];
        return (
          <div
            key={name}
            style={{
              display: "grid",
              gridTemplateColumns: "140px 1fr auto 90px",
              alignItems: "baseline",
              columnGap: 16,
              fontFamily: m ? BLACK : JUA,
              fontSize: m ? m.size : TUNE.allRow,
              color: m ? m.color : "#fff",
              marginTop: TUNE.allGap,
              opacity: stepIn(i),
              transform: `translateX(${(1 - stepIn(i)) * -40}px)`,
            }}
          >
            <span style={{ textAlign: "right", color: m ? m.color : "#9C978C", fontSize: m ? m.size * 0.82 : 42, fontVariantNumeric: "tabular-nums" }}>
              {rank}위
            </span>
            <span style={{ whiteSpace: "nowrap" }}>{name}</span>
            <span style={{ fontVariantNumeric: "tabular-nums", textAlign: "right", whiteSpace: "nowrap" }}>{won(price)}</span>
            <span />
          </div>
        );
      })}
    </Card>
  );
};

const HookCard = () => (
  <div
    style={{
      position: "absolute",
      top: TUNE.hookTop,
      left: "50%",
      transform: "translateX(-50%)",
      width: 1000,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
    }}
  >
    <div
      style={{
        position: "relative",
        width: "100%",
        boxSizing: "border-box",
        background: "rgba(12,12,14,0.82)",
        border: "8px solid #000",
        borderRadius: 30,
        padding: `26px 34px ${TUNE.hookBottomPad}px`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
      }}
    >
      <Img
        src={staticFile("bg/marat_bowl.png")}
        style={{ position: "absolute", top: 28, left: 370, zIndex: -1, width: 260, translate: "25.2px 993.3px", scale: 3.96 }}
      />
      <div style={{ fontFamily: JUA, fontSize: TUNE.hookSub, color: "#C9C4B8", lineHeight: 1.02, whiteSpace: "nowrap", marginTop: -2 }}>
        마라탕 원가공개
      </div>
      <div style={{ fontFamily: BLACK, fontSize: TUNE.hookLine1, color: "#fff", lineHeight: 1.05, whiteSpace: "nowrap" }}>
        사장님이 쳐다볼 때
      </div>
      <div style={{ fontFamily: BLACK, fontSize: TUNE.hookLine2, color: EP.peakColor, lineHeight: 1.05, whiteSpace: "nowrap" }}>
        눈치 보이는 재료
      </div>
      <div style={{ fontFamily: BLACK, fontSize: TUNE.hookTitle, color: "#8ECBF5", lineHeight: 1.05, whiteSpace: "nowrap", marginTop: 8 }}>
        {EP.title}
      </div>
    </div>
    <div style={{ width: "100%", marginTop: TUNE.badgeGap }}>
      <SeriesBadge label={EP.badge} fontSize={TUNE.badgeSize} />
    </div>
  </div>
);

export const Talk3 = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voice3"
    defaultBg="marat01"
    renderCards={(p, { bigIn, partPop }) => (
      <>
        {p.count && <Countdown n={p.count} pop={partPop} />}
        {p.rank != null && <RankDrop idx={p.rank} pop={partPop} />}
        {p.all && <AllTable pop={partPop} />}
        {p.site && <Site pop={bigIn} site={EP.site} />}
      </>
    )}
    renderHook={() => <HookCard />}
    sfx={(at) => {
      // 🔴 LINES 인덱스: 0훅 1공지(3파트) 2·3·4카운트 5~14순위(10개) 15표 16회수 17버럭 18머쓱
      const fx = [
        { t: 0.15, src: "paper.mp3", vol: 0.5, dur: 1.2 },
        { t: at(2, 0), src: "tick.mp3", vol: 0.6, dur: 0.4 },
        { t: at(3, 0), src: "tick.mp3", vol: 0.65, dur: 0.4 },
        { t: at(4, 0), src: "tick.mp3", vol: 0.75, dur: 0.4 },
      ];
      for (let i = 5; i <= 13; i++) {
        fx.push({ t: at(i, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 });
      }
      fx.push({ t: at(14, 0), src: "coins.mp3", vol: 0.7, dur: 1.6 }); // 1위(양고기) — 임팩트
      fx.push({ t: at(18, 0), src: "chime.mp3", vol: 1.0, dur: 1.8 }); // 머쓱
      return fx;
    }}
  />
);
