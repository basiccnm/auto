// 마라탕 2편 본편 — 종합 TOP10 · 사장님 최애(제일 싼) 재료, 약 42초 (2026-07-23)
//
// 🔴 조립은 talk_engine.jsx. 이 파일은 화면(카드)만 정의한다.
//    대사 lines_top10cheap.js · 재료 ep_top10cheap.js
//
// 🔴 3~7편도 이 파일을 복사해서 EP/LINES import만 갈아끼우면 된다.
//    순위 카운트다운 형식이 같아서 카드는 그대로 재사용된다.
import React from "react";
import { Img, staticFile } from "remotion";

import { C } from "./config";
import { BLACK, JUA } from "./fonts";
import { EP } from "./ep_top10cheap";
import { LEAD, LINES } from "./lines_top10cheap";
import { Card, SeriesBadge, Site, TalkEngine, talkSec, won } from "./talk_engine";

export const TOP10CHEAP_SEC = talkSec(LINES, LEAD);

// ── 조정용 숫자 (여기만 고치면 된다) ──────────────────────────
const TUNE = {
  hookTop: 230,
  hookBottomPad: 26,
  hookSub: 58, // "마라탕 원가공개" 윗줄
  hookLine1: 120, // 훅 첫 줄
  hookLine2: 148, // 훅 둘째 줄(강조)
  hookTitle: 62, // 편 제목 (사장님 최애 TOP 10)
  badgeSize: 62,
  badgeGap: 16,

  rankTop: 280, // 순위 카드 세로 위치
  rankNo: 76, // "10위"
  rankName: 66, // 재료 이름
  rankPrice: 156, // 가격
  rankFrom: -520, // 위에서 떨어지는 높이

  // 전체 표 — 🔴 브랜드볼이 없는 화면이라 위아래를 다 쓴다(2026-07-23 지시).
  //    카드를 내리는 게 아니라 **위치는 그대로 두고 아래로 길게** 늘린다.
  //    상단 안전영역(192) 바로 아래에서 시작해 화면을 꽉 채운다
  allTop: 230, // 전체 표 세로 위치
  allRow: 66, // 4~10위
  allTop1: 96, // 1위 (금)
  allTop2: 86, // 2위 (은)
  allTop3: 78, // 3위 (동)
  allGap: 18, // 줄 간격 — 붙어 있으면 못 읽는다

  countSize: 300, // 3-2-1 숫자 크기
};

// ── ② 카드: 순위 하나가 쿵 떨어진다 ──────────────────────────
// 🔴 리스트를 쌓지 않는다(2026-07-23 확정) — 큰 숫자 하나만 보여주고,
//    누적 리스트는 마지막 전체 표에서 몰아 본다. 화면이 훨씬 깔끔하다.
const RankDrop = ({ idx, pop }) => {
  const [name, price, rank] = EP.items[idx];
  const y = (1 - pop) * TUNE.rankFrom;
  // 착지 순간 가로로 눌렸다 펴진다 = 무게감
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
      {/* 순위 배지 — 1위만 금색 */}
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

// ── ② 카드: 3-2-1 카운트다운 ────────────────────────────────
// 🔴 대사를 셋으로 쪼갰으므로(2026-07-23) 이 컴포넌트는 숫자 하나만 그린다.
//    크게 튀어나왔다가 살짝 줄어드는 임팩트. 1은 빨간색으로 확 바뀐다
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

// ── ② 카드: 전체 표 ─────────────────────────────────────────
// 🔴 1위가 맨 위로 오게 뒤집었다(2026-07-23 지시) — 공개는 10위→1위 순이지만
//    표는 1위가 위에 있어야 순위표로 읽힌다.
// 🔴 1·2·3위는 금·은·동으로 색을 달리하고 글씨도 키운다. 나머지와 확실히 구분된다.
const MEDAL = {
  1: { color: "#FFC42E", size: TUNE.allTop1 }, // 금
  2: { color: "#DDE3EA", size: TUNE.allTop2 }, // 은
  3: { color: "#E8A464", size: TUNE.allTop3 }, // 동
};

const AllTable = ({ pop = 1 }) => {
  // 표시는 1위부터 — 공개 순서(10→1)의 역순
  const rows = [...EP.items].sort((a, b) => a[2] - b[2]);
  const stepIn = (i) => Math.max(0, Math.min(1, pop * rows.length - i));
  return (
    <Card wide top={TUNE.allTop}>
      {/* 🔴 타이틀 두 줄(2026-07-23 지시) — 윗줄은 범위(회색·작게), 아랫줄이 제목(노랑·크게).
          색을 나눠야 "62종 전체에서 뽑았다"는 안내와 제목이 안 섞인다 */}
      <div
        style={{
          textAlign: "center",
          fontFamily: JUA,
          fontSize: 48,
          color: "#8ECBF5",
          lineHeight: 1.05,
          letterSpacing: 1,
        }}
      >
        {EP.titleTop}
      </div>
      <div
        style={{
          textAlign: "center",
          fontFamily: BLACK,
          fontSize: 78,
          color: C.yellow,
          lineHeight: 1.05,
          marginTop: 6,
        }}
      >
        {EP.title}
      </div>
      <div
        style={{
          textAlign: "center",
          fontFamily: JUA,
          fontSize: 30,
          color: "#9C978C",
          marginTop: 6,
          marginBottom: 16,
        }}
      >
        {EP.date} · {EP.note}
      </div>
      {/* 🔴 3단 그리드로 세로줄을 맞춘다(2026-07-23 지시) —
          순위는 오른쪽 정렬(1위·10위 자릿수가 달라도 "위"가 세로로 맞음),
          제품명은 왼쪽 정렬, 가격은 오른쪽 정렬. flex space-between이면 이름 길이에 따라 흔들린다 */}
      {rows.map(([name, price, rank], i) => {
        const m = MEDAL[rank];
        return (
          <div
            key={name}
            style={{
              display: "grid",
              // 🔴 금액 위치(2026-07-23) — 오른쪽 끝에 붙이면 시선이 멀고, 너무 당기면 허전하다.
              //    마지막 여백 칸을 90px만 두는 선에서 맞췄다. 금액은 우측 정렬(자릿수 세로 정렬)
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
            <span
              style={{
                textAlign: "right",
                color: m ? m.color : "#9C978C",
                fontSize: m ? m.size * 0.82 : 42,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {rank}위
            </span>
            <span style={{ whiteSpace: "nowrap" }}>{name}</span>
            <span
              style={{
                fontVariantNumeric: "tabular-nums",
                textAlign: "right",
                whiteSpace: "nowrap",
              }}
            >
              {won(price)}
            </span>
            <span />
          </div>
        );
      })}
    </Card>
  );
};

// ── ② 카드: 훅 = 썸네일 ──────────────────────────────────────
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
        style={{
          position: "absolute",
          top: 28,
          left: 370,
          zIndex: -1,
          width: 260,
          translate: "25.2px 993.3px",
          scale: 3.96,
        }}
      />
      <div
        style={{
          fontFamily: JUA,
          fontSize: TUNE.hookSub,
          color: "#C9C4B8",
          lineHeight: 1.02,
          whiteSpace: "nowrap",
          marginTop: -2,
        }}
      >
        마라탕 원가공개
      </div>
      <div
        style={{
          fontFamily: BLACK,
          fontSize: TUNE.hookLine1,
          color: "#fff",
          lineHeight: 1.05,
          whiteSpace: "nowrap",
        }}
      >
        이거 팍팍 담으면
      </div>
      <div
        style={{
          fontFamily: BLACK,
          fontSize: TUNE.hookLine2,
          color: C.yellow,
          lineHeight: 1.05,
          whiteSpace: "nowrap",
        }}
      >
        완벽한 호구
      </div>
      {/* 🔴 썸네일에 편 제목을 박는다(2026-07-23 지시) — 목록에서 뭘 다루는 편인지 바로 보인다 */}
      <div
        style={{
          fontFamily: BLACK,
          fontSize: TUNE.hookTitle,
          color: "#8ECBF5",
          lineHeight: 1.05,
          whiteSpace: "nowrap",
          marginTop: 8,
        }}
      >
        {EP.title}
      </div>
    </div>
    <div style={{ width: "100%", marginTop: TUNE.badgeGap }}>
      <SeriesBadge label={EP.badge} fontSize={TUNE.badgeSize} />
    </div>
  </div>
);

// ── 본편 ──────────────────────────────────────────────────────
export const TalkTop10Cheap = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voice2"
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
    sfx={(at) => [
      { t: 0.15, src: "paper.mp3", vol: 0.5, dur: 1.2 },
      // 3-2-1 (LINE 2·3·4) — 대사가 셋으로 쪼개져 인덱스도 셋
      { t: at(2, 0), src: "tick.mp3", vol: 0.6, dur: 0.4 },
      { t: at(3, 0), src: "tick.mp3", vol: 0.65, dur: 0.4 },
      { t: at(4, 0), src: "tick.mp3", vol: 0.75, dur: 0.4 },
      // 순위 10위~2위 (LINE 5~13)
      { t: at(5, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(6, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(7, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(8, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(9, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(10, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(11, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(12, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(13, 0), src: "tick.mp3", vol: 0.6, dur: 0.45 },
      // 1위 (LINE 14) — 동전
      { t: at(14, 0), src: "coins.mp3", vol: 0.65, dur: 1.6 },
      // 마무리 차임 (LINE 18 머쓱)
      { t: at(18, 0), src: "chime.mp3", vol: 1.0, dur: 1.8 },
    ]}
  />
);
