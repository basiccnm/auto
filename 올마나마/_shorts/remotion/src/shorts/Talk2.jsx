// 마라탕 2편 본편 — 셀프마라탕 채소 원가 공개, 약 50초 (2026-07-23)
//
// 🔴 조립은 talk_engine.jsx가 한다. 이 파일은 **화면(카드)만** 정의한다.
//    대사는 lines_marat2.js, 재료 단가는 ep_marat2.js.
//
// ── 화면 객체 번호 (대표님과 소통용) ──────────────────────────
//    ① 배경  ② 카드  ③ 말풍선  ④ 왼쪽=올마  ⑤ 오른쪽=사장님  ⑥ 효과음
//
// 🔴 반복 조정하는 숫자는 아래 TUNE 하나에 모았다. 스튜디오 패널 대신 여기 숫자를 직접 고친다
//    (2026-07-22 대표님 선호: "내가 편집기로 수정할 부위 체크할게, 숫자 써서").
import React from "react";
import { Img, staticFile } from "remotion";

import { C } from "./config";
import { BLACK, JUA } from "./fonts";
import { EP } from "./ep_marat2";
import { LEAD, LINES } from "./lines_marat2";
import {
  Card,
  Row,
  SeriesBadge,
  Site,
  TalkEngine,
  talkSec,
  won,
} from "./talk_engine";

export const TALK2_SEC = talkSec(LINES, LEAD);

// ── 조정용 숫자 (여기만 고치면 된다) ──────────────────────────
const TUNE = {
  hookTop: 230, // 훅 카드 세로 위치
  hookBottomPad: 26, // 훅 카드 아래 여백
  hookSub: 62, // "마라탕집 사장이 알려주는" 크기
  hookLine1: 128, // "야채 듬뿍?"
  hookLine2: 158, // "사장님은 개이득" (제일 큼)
  badgeSize: 62, // 시리즈 배지 글자
  badgeGap: 16, // 카드와 배지 사이

  listTop: 200, // 단가표 세로 위치
  listRow: 52, // 단가표 한 줄 글자 크기
  listHot: 62, // 방금 뜬 줄(노랑) 크기

  allTop: 260, // 전체 표 세로 위치 (볼이 없어서 아래로 여유 있다)
  allRow: 52, // 전체 표 한 줄
  allTopRow: 62, // 전체 표 1위(고수) 줄

  // 쿵 떨어지는 큰 가격
  // 🔴 640이면 말풍선(820)과 겹쳐서 지저분했다(2026-07-23) — 위쪽 빈 벽으로 올렸다.
  //    안전영역(상단 192) 아래, 말풍선 위. 둘 다 안 가리고 보인다.
  dropTop: 300, // 세로 위치
  dropName: 66, // 재료 이름
  dropPrice: 168, // 가격 숫자 (공간이 넓어져서 키움)
  dropFrom: -520, // 얼마나 위에서 떨어지나 (화면 밖에서)
};

// ── ② 카드: 단가표 — 한 줄씩 쌓인다 ─────────────────────────
// 🔴 13종을 한 화면에 다 넣으면 글자가 작아진다. 생물 11종까지만 쌓고,
//    마른 것 2종은 그 아래 구분선 밑에 따로 붙인다(불린 기준이라 성격이 다름).
// 🔴 pop = 방금 뜬 줄만 왼쪽에서 슥 들어온다. 이미 떠 있던 줄은 가만히 있는다
//    (전부 매번 움직이면 표가 덜덜 떨려서 못 읽는다).
const Ledger = ({ upto = 0, hot = -1, dried, pop }) => (
  <Card top={TUNE.listTop}>
    <div
      style={{
        fontFamily: BLACK,
        fontSize: 54,
        color: C.yellow,
        lineHeight: 1.05,
        whiteSpace: "nowrap",
      }}
    >
      셀프마라탕 채소 100g 단가
    </div>
    <div
      style={{
        fontFamily: JUA,
        fontSize: 32,
        color: "#9C978C",
        marginTop: 2,
        marginBottom: 6,
        whiteSpace: "nowrap",
      }}
    >
      {EP.date} · {EP.note}
    </div>

    {EP.fresh.slice(0, upto).map(([name, v], i) => (
      <Row
        key={name}
        name={name}
        val={won(v)}
        hi={i === hot}
        dim={hot >= 0 && i !== hot}
        size={i === hot ? TUNE.listHot : TUNE.listRow}
        pop={i === hot ? pop : 1}
      />
    ))}

    {dried > 0 && (
      <>
        <div style={{ borderTop: "5px solid #4A4A4A", margin: "14px 0 4px" }} />
        <div
          style={{
            fontFamily: JUA,
            fontSize: 34,
            color: "#9C978C",
            marginBottom: 2,
          }}
        >
          마른 재료 (불린 기준)
        </div>
        {EP.dried.slice(0, dried).map(([name, v], i) => (
          <Row
            key={name}
            name={name}
            val={won(v)}
            hi={i === dried - 1}
            size={i === dried - 1 ? TUNE.listHot : TUNE.listRow}
            pop={i === dried - 1 ? pop : 1}
          />
        ))}
      </>
    )}
  </Card>
);

// ── ② 카드: 전체 표 — 캡처해서 저장할 만한 화면 ──────────────
// 🔴 13줄을 한 카드에 넣어야 해서 글자를 줄이고 두 칸으로 나눈다.
// 🔴 브랜드볼이 사라진 화면이라 표를 크게 쓴다(2026-07-23 지시: "너무 가려서 안 보여").
//    13줄이 위에서부터 촤르륵 순서대로 펼쳐진다 — pop 하나로 줄마다 시차를 준다.
const AllTable = ({ pop = 1 }) => {
  const all = [
    ...EP.fresh.map(([n, v], i) => ({ n, v, top: i === EP.fresh.length - 1 })),
    { divider: true },
    ...EP.dried.map(([n, v]) => ({ n, v, dry: true })),
  ];
  // 줄마다 등장 시차 — pop이 0→1로 오르는 동안 위에서부터 순서대로 뜬다
  const stepIn = (i) => {
    const t = pop * all.length - i;
    return Math.max(0, Math.min(1, t));
  };
  return (
    <Card wide top={TUNE.allTop}>
      <div
        style={{
          textAlign: "center",
          fontFamily: BLACK,
          fontSize: 64,
          color: C.yellow,
          lineHeight: 1.05,
        }}
      >
        셀프마라탕 채소 100g 단가
      </div>
      <div
        style={{
          textAlign: "center",
          fontFamily: JUA,
          fontSize: 34,
          color: "#9C978C",
          marginTop: 2,
          marginBottom: 14,
        }}
      >
        {EP.date} · {EP.note}
      </div>
      {all.map((r, i) =>
        r.divider ? (
          <div
            key="div"
            style={{
              borderTop: "4px solid #4A4A4A",
              margin: "14px 0 6px",
              opacity: stepIn(i),
            }}
          />
        ) : (
          <div
            key={r.n}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              fontFamily: r.top ? BLACK : JUA,
              fontSize: r.top ? TUNE.allTopRow : TUNE.allRow,
              color: r.top ? C.yellow : "#fff",
              marginTop: 5,
              opacity: stepIn(i),
              transform: `translateX(${(1 - stepIn(i)) * -40}px)`,
            }}
          >
            <span>
              {r.n}
              {r.dry && (
                <span style={{ fontSize: 28, color: "#9C978C" }}> (불린 기준)</span>
              )}
            </span>
            <span style={{ fontVariantNumeric: "tabular-nums" }}>{won(r.v)}</span>
          </div>
        ),
      )}
    </Card>
  );
};

// ── ② 카드: 쿵 떨어지는 큰 가격 ──────────────────────────────
// 🔴 2026-07-23 지시 — 리스트에 한 줄 늘어나는 것만으로는 밋밋하다.
//    "숙주 얼마" 할 때 그 가격이 **멀리서 말풍선 위로 크게 쿵** 떨어져야 한다.
//    리스트(Ledger)는 그대로 두고 그 위에 얹는다.
const DropPrice = ({ name, price, pop }) => {
  // 위에서 떨어져 바닥을 치고 살짝 튄다 — spring이 1을 넘겼다 돌아오는 구간이 그 튐이다
  const y = (1 - pop) * TUNE.dropFrom;
  // 착지 순간(pop 0.55~0.8)에 가로로 눌렸다 펴진다 = 무게감
  const squash = pop < 0.55 ? 1 : pop < 0.8 ? 1 + (0.8 - pop) * 0.5 : 1;
  return (
    <div
      style={{
        position: "absolute",
        top: TUNE.dropTop,
        left: "50%",
        zIndex: 6, // 말풍선(5)보다 위
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
          fontFamily: JUA,
          fontSize: TUNE.dropName,
          color: "#fff",
          whiteSpace: "nowrap",
          lineHeight: 1.0,
        }}
      >
        {name}
      </div>
      <div
        style={{
          fontFamily: BLACK,
          fontSize: TUNE.dropPrice,
          color: C.yellow,
          whiteSpace: "nowrap",
          lineHeight: 1.05,
          WebkitTextStroke: "8px #000",
          paintOrder: "stroke fill",
        }}
      >
        {won(price)}
      </div>
    </div>
  );
};

// ── ② 카드: 훅 = 썸네일 ──────────────────────────────────────
// 🔴 0프레임에 최종 크기로 완성돼 있어야 한다(커지는 애니메이션 금지).
//    쇼츠 썸네일은 유튜브 앱에서만 바꿀 수 있어서 첫 화면이 곧 썸네일이다.
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
      {/* 그릇 일러스트 — flow 밖에 둬서 글자를 밀지 않는다 */}
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
        마라탕집 사장이 까는 채소 원가
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
        야채 듬뿍?
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
        사장님은 개이득
      </div>
    </div>
    <div style={{ width: "100%", marginTop: TUNE.badgeGap }}>
      <SeriesBadge label={EP.badge} fontSize={TUNE.badgeSize} />
    </div>
  </div>
);

// ── 본편 ──────────────────────────────────────────────────────
export const Talk2 = () => (
  <TalkEngine
    lines={LINES}
    lead={LEAD}
    voiceDir="voice2"
    defaultBg="marat01"
    renderCards={(p, { bigIn, partPop, dropPop }) => (
      <>
        {/* 🔴 단가 공개 구간엔 리스트를 안 띄운다(2026-07-23 지시) —
            "하나씩 말할 때 뒤에 리스트는 없애면 되고".
            큰 가격 하나만 쿵 떨어지고, 누적 리스트는 마지막 전체 표에서 몰아 보여준다 */}
        {p.drop != null && (
          <DropPrice
            name={EP.fresh[p.drop][0]}
            price={EP.fresh[p.drop][1]}
            pop={dropPop}
          />
        )}
        {p.dropDry != null && (
          <DropPrice
            name={`${EP.dried[p.dropDry][0]} (불린 기준)`}
            price={EP.dried[p.dropDry][1]}
            pop={dropPop}
          />
        )}
        {p.all && <AllTable pop={partPop} />}
        {p.site && <Site pop={bigIn} site={EP.site} />}
      </>
    )}
    renderHook={() => <HookCard />}
    sfx={(at) => [
      // 영수증 — 시작
      { t: 0.15, src: "paper.mp3", vol: 0.5, dur: 1.2 },
      // 재료 한 줄씩 틱 (13종)
      { t: at(3, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(3, 1), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(4, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(4, 1), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(5, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(5, 1), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(6, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(6, 1), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(7, 0), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(7, 1), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      // 1위 고수 — 여기만 강조음
      { t: at(8, 1), src: "coins.mp3", vol: 0.6, dur: 1.5 },
      // 마른 것 2종
      { t: at(9, 1), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      { t: at(9, 2), src: "tick.mp3", vol: 0.55, dur: 0.45 },
      // 마무리 차임
      { t: at(12, 1), src: "chime.mp3", vol: 1.0, dur: 1.8 },
    ]}
  />
);
