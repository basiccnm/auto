// 마라탕 5편 본편(면·떡류) — 번호 정정: 처음에 3편으로 잘못 만들었다가 5편으로 옮김(2026-07-23) — 면·떡류 18종 원가 카운트다운, 약 80초 (2026-07-23)
//
// 🔴 2편(TalkTop10Cheap.jsx)을 복사해 데이터만 갈아끼웠다. 형식은 그대로 재사용.
//    대사 lines_noodle.js · 재료 ep_noodle.js
// 🔴 18종이라 이름이 길다("연근모양분모자" 7자) — rankName 폰트를 2편보다 줄였다.
import React from "react";
import { Img, staticFile } from "remotion";

import { C } from "./config";
import { BLACK, JUA } from "./fonts";
import { EP } from "./ep_noodle";
import { LEAD, LINES } from "./lines_noodle";
import { Card, SeriesBadge, Site, TalkEngine, talkSec, won } from "./talk_engine";

export const NOODLE_SEC = talkSec(LINES, LEAD);

const TUNE = {
  hookTop: 230,
  hookBottomPad: 26,
  hookSub: 58,
  hookLine1: 110,
  hookLine2: 130,
  hookTitle: 56,
  badgeSize: 62,
  badgeGap: 16,

  rankTop: 280,
  rankNo: 72,
  rankName: 54, // 🔴 18종은 이름이 길어서(연근모양분모자 등) 2편보다 줄였다
  rankPrice: 148,
  rankFrom: -520,

  allTop: 200, // 18줄이 들어가서 2편보다 더 위에서 시작
  allRow: 46, // 18줄 다 보여야 해서 2편보다 작게
  allTop1: 66,
  allTop2: 58,
  allTop3: 52,
  allGap: 10,

  countSize: 300,
};

const RankDrop = ({ idx, pop }) => {
  const [name, price, rank] = EP.items[idx];
  const y = (1 - pop) * TUNE.rankFrom;
  const squash = pop < 0.55 ? 1 : pop < 0.8 ? 1 + (0.8 - pop) * 0.5 : 1;
  const isTop = rank === 1;
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
          background: isTop ? "#FFC42E" : C.red,
          border: "7px solid #000",
          borderRadius: 999,
          padding: "6px 34px",
          fontFamily: BLACK,
          fontSize: TUNE.rankNo,
          color: isTop ? "#1C1C1C" : "#fff",
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
          WebkitTextStroke: "6px #000",
          paintOrder: "stroke fill",
        }}
      >
        {name}
      </div>
      <div
        style={{
          fontFamily: BLACK,
          fontSize: TUNE.rankPrice,
          color: isTop ? "#FFC42E" : C.yellow,
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
          fontSize: TUNE.rankPrice * 0.24,
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

const MEDAL = {
  1: { color: "#FFC42E", size: TUNE.allTop1 },
  2: { color: "#DDE3EA", size: TUNE.allTop2 },
  3: { color: "#E8A464", size: TUNE.allTop3 },
};

const AllTable = ({ pop = 1 }) => {
  const rows = [...EP.items].sort((a, b) => a[2] - b[2]);
  const stepIn = (i) => Math.max(0, Math.min(1, pop * rows.length - i));
  return (
    <Card wide top={TUNE.allTop}>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 40, color: "#8ECBF5", lineHeight: 1.05, letterSpacing: 1 }}>
        {EP.titleTop}
      </div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 60, color: C.yellow, lineHeight: 1.05, marginTop: 4 }}>
        {EP.title}
      </div>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 26, color: "#9C978C", marginTop: 4, marginBottom: 12 }}>
        {EP.date} · {EP.note}
      </div>
      {rows.map(([name, price, rank], i) => {
        const m = MEDAL[rank];
        return (
          <div
            key={name}
            style={{
              display: "grid",
              gridTemplateColumns: "110px 1fr auto 70px",
              alignItems: "baseline",
              columnGap: 12,
              fontFamily: m ? BLACK : JUA,
              fontSize: m ? m.size : TUNE.allRow,
              color: m ? m.color : "#fff",
              marginTop: TUNE.allGap,
              opacity: stepIn(i),
              transform: `translateX(${(1 - stepIn(i)) * -40}px)`,
            }}
          >
            <span style={{ textAlign: "right", color: m ? m.color : "#9C978C", fontSize: m ? m.size * 0.8 : 30, fontVariantNumeric: "tabular-nums" }}>
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
        옥수수면 한 움큼?
      </div>
      <div style={{ fontFamily: BLACK, fontSize: TUNE.hookLine2, color: C.yellow, lineHeight: 1.05, whiteSpace: "nowrap" }}>
        사장님 마진율 폭발
      </div>
      <div style={{ fontFamily: BLACK, fontSize: TUNE.hookTitle, color: "#8ECBF5", lineHeight: 1.05, whiteSpace: "nowrap", marginTop: 8 }}>
        면·떡류 18종
      </div>
    </div>
    <div style={{ width: "100%", marginTop: TUNE.badgeGap }}>
      <SeriesBadge label={EP.badge} fontSize={TUNE.badgeSize} />
    </div>
  </div>
);

export const TalkNoodle = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voice5"
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
      // 🔴 LINES 인덱스: 0훅 1공지 2·3·4카운트 5~22순위(18개) 23표 24회수 25버럭 26머쓱
      const fx = [
        { t: 0.15, src: "paper.mp3", vol: 0.5, dur: 1.2 },
        { t: at(2, 0), src: "tick.mp3", vol: 0.6, dur: 0.4 },
        { t: at(3, 0), src: "tick.mp3", vol: 0.65, dur: 0.4 },
        { t: at(4, 0), src: "tick.mp3", vol: 0.75, dur: 0.4 },
      ];
      for (let i = 5; i <= 21; i++) {
        fx.push({ t: at(i, 0), src: "tick.mp3", vol: 0.5, dur: 0.4 });
      }
      fx.push({ t: at(22, 0), src: "coins.mp3", vol: 0.65, dur: 1.6 }); // 1위
      fx.push({ t: at(26, 0), src: "chime.mp3", vol: 1.0, dur: 1.8 }); // 머쓱
      return fx;
    }}
  />
);
