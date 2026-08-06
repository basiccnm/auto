// 카드뉴스 프레임 — 정본 v2 §3·5·6 구현 (2026-07-24)
//
// 🔴 웹클로 시안(드라이브 `올마나마/01_훅.png` ~ `05_맺음말.png`)이 룩의 기준.
//    남색 라디얼 배경 + 흰 패널 + 좌상단 시리즈칩 + 하단 NEXT.
// 🔴 규격 1080×1920(9:16 마스터). 인스타 캐러셀용 4:5는 렌더 후 크롭한다.
// 🔴 텍스트는 **전부 흰 패널 안에만**. 배경 위에 글자를 놓지 않는다(정본 §3).
// 🔴 NEXT 버튼은 캐러셀에만. 영상에선 끈다(props.next=false).
import React from "react";
import { AbsoluteFill } from "remotion";

import { BLACK, NOTO } from "../shorts/fonts";
import { Doodle } from "./Doodle";
import { OlmaBall3D } from "./OlmaBall3D";
import { CARDS, EP, pay, sum } from "./card_anchor";

// ── 정본 §6 색 ────────────────────────────────────────────
const C = {
  panel: "#F7F9FC",
  title: "#1C2434",
  body: "#5B6474",
  tag: "#8A94AB",
  red: "#E8493F", // 손님 입장
  blue: "#2F6FED", // 사장 입장
  gray: "#3D4657", // 계산
  boxBg: "#FFF3D6",
  boxBar: "#F5B70C",
  boxInk: "#7A5200",
};

// 카드 유형별 포인트색 — 색만 봐도 시점이 구분된다(정본 §6)
const POINT = { 훅: C.red, 손님: C.red, 계산: C.gray, 사장: C.blue, 맺음말: C.red };

const W = 1080;
const H = 1920;

// 🔴 4대 플랫폼 안전영역 (2026-07-24 지시) — 어디에 올려도 안 잘리게 한다.
//    각 앱이 가리는 곳이 달라서, **가장 넓게 가리는 값**으로 통일한다.
//      인스타 릴스   하단 캡션·버튼 ~380px, 우측 아이콘줄 ~180px
//      틱톡         하단 ~480px(제일 깊다), 우측 ~200px
//      유튜브 쇼츠   하단 ~420px, 우측 ~160px
//      네이버 클립   하단 ~360px
//    ⚠️ 인스타 피드 썸네일은 **4:5로 위아래가 잘린다** —
//       세로 240~1680 구간(=4:5 영역) 안에 핵심이 다 들어와야 한다.
// 🔴 용도별로 여백이 다르다(2026-07-24). 리모션이니 같은 카드에서 두 벌을 뽑는다.
//      card  = 인스타 캐러셀. 피드 썸네일이 4:5로 위아래를 자르니 상단 240 비움
//      video = 쇼츠·릴스·틱톡. 세로 그대로 나가니 위를 비울 이유가 없다 → 상단 100
//              대신 하단에 낙서 무대를 두므로 아래를 더 비운다
const SAFE_BY = {
  card: { top: 240, bottom: 480, right: 200, side: 78 },
  video: { top: 100, bottom: 620, right: 200, side: 78 },
};

const layout = (mode) => {
  const S = SAFE_BY[mode] || SAFE_BY.card;
  return {
    S,
    PANEL: {
      x: S.side,
      y: S.top + 30, // 칩을 뺐다(2026-07-24) — 패널을 위로 올림
      w: W - S.side * 2,
      h: H - (S.top + 30) - S.bottom, // 🔴 패널 시작을 올린 만큼 높이도 늘린다(아래 여백 제거)
      r: 30,
    },
  };
};

const won = (n) => n.toLocaleString() + "원";

// ── 옵션 비교표 (③) ────────────────────────────────────────
const OptionTable = () => {
  const { base, A, B } = EP.calc;
  const rows = [
    ["치즈피자", base, base, false],
    ["콤비네이션", A.combo, B.combo, true],
    ["토핑 2개", A.topping, B.topping, true],
  ];
  return (
    <div style={{ marginTop: 26 }}>
      <div style={{ display: "grid", gridTemplateColumns: "300px 250px 250px", marginBottom: 10 }}>
        <span />
        <span style={{ fontFamily: BLACK, fontSize: 52, color: C.red, textAlign: "right" }}>A집</span>
        <span style={{ fontFamily: BLACK, fontSize: 52, color: C.blue, textAlign: "right" }}>B집</span>
      </div>
      {rows.map(([label, a, b, up]) => (
        <div
          key={label}
          style={{
            display: "grid",
            gridTemplateColumns: "300px 250px 250px",
            alignItems: "baseline",
            padding: "16px 0",
            borderTop: "2px dashed #DFE3EC",
          }}
        >
          <span style={{ fontFamily: NOTO, fontSize: 52, color: C.body, whiteSpace: "nowrap" }}>{label}</span>
          <span
            style={{
              fontFamily: up ? BLACK : NOTO,
              fontSize: up ? 62 : 52,
              color: up ? C.red : C.title,
              textAlign: "right",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {up ? "+" : ""}
            {a.toLocaleString()}
          </span>
          <span
            style={{
              fontFamily: NOTO,
              fontSize: 52,
              color: C.title,
              textAlign: "right",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {up ? "+" : ""}
            {b.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
};

// ── 결제액 비교 (④) ────────────────────────────────────────
const ResultTable = () => {
  const { A, B } = EP.calc;
  const line = (label, a, b, strong) => (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "300px 250px 250px",
        alignItems: "baseline",
        padding: strong ? "20px 0 4px" : "14px 0",
        borderTop: "2px dashed #DFE3EC",
      }}
    >
      <span style={{ fontFamily: NOTO, fontSize: strong ? 60 : 50, color: strong ? C.title : C.body, whiteSpace: "nowrap" }}>
        {label}
      </span>
      <span
        style={{
          fontFamily: strong ? BLACK : NOTO,
          fontSize: strong ? 64 : 50,
          color: strong ? C.title : C.body,
          textAlign: "right",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {a}
      </span>
      <span
        style={{
          fontFamily: strong ? BLACK : NOTO,
          fontSize: strong ? 64 : 50,
          color: strong ? C.blue : C.body,
          textAlign: "right",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {b}
      </span>
    </div>
  );
  return (
    <div style={{ marginTop: 24 }}>
      <div style={{ display: "grid", gridTemplateColumns: "300px 250px 250px", marginBottom: 8 }}>
        <span />
        <span style={{ fontFamily: BLACK, fontSize: 50, color: C.red, textAlign: "right" }}>A집</span>
        <span style={{ fontFamily: BLACK, fontSize: 50, color: C.blue, textAlign: "right" }}>B집</span>
      </div>
      {line("소계", sum(A).toLocaleString(), sum(B).toLocaleString())}
      {line("즉시할인", "-" + A.sale.toLocaleString(), "-" + B.sale.toLocaleString())}
      {line("결제", pay(A).toLocaleString(), pay(B).toLocaleString(), true)}
    </div>
  );
};

// ── 카드 한 장 ────────────────────────────────────────────
// 🔴 NEXT 버튼은 뺐다(2026-07-24 지시). next prop은 호환용으로 남겨둔다
export const CardNews = ({ i = 0, mode = "card" }) => {
  const c = CARDS[i] || CARDS[0];
  const point = POINT[c.type] || C.red;
  const { S: SAFE, PANEL } = layout(mode);

  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(120% 90% at 50% 18%, #2A4DA6 0%, #1E3D8C 55%, #182F6E 100%)",
      }}
    >
      {/* 🔴 좌상단 "배달 꿀팁" 칩은 뺐다(2026-07-24 지시) — 없는 게 깔끔하다 */}

      {/* 플립북 낙서 — 상단 여백 채우기(2026-07-24). 영상에서만 움직인다 */}
      {c.doodle && mode === "card" && (
        <div style={{ position: "absolute", top: SAFE.top - 10, right: SAFE.side + 10 }}>
          <Doodle kind={c.doodle} width={185} />
        </div>
      )}

      {/* 흰 패널 — 글자는 전부 이 안에 */}
      <div
        style={{
          position: "absolute",
          left: PANEL.x,
          top: PANEL.y,
          width: PANEL.w,
          height: PANEL.h,
          background: C.panel,
          borderRadius: PANEL.r,
          boxShadow: "0 30px 70px rgba(0,0,0,0.28)",
          padding: "70px 66px",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* ── 표지(썸네일) 전용 레이아웃 ── */}
        {c.cover ? (
          <div style={{ margin: "auto 0", display: "flex", flexDirection: "column" }}>
            <div style={{ fontFamily: BLACK, fontSize: 96, color: C.title, lineHeight: 1.1 }}>
              {c.coverTop}
            </div>
            <div style={{ fontFamily: BLACK, fontSize: 150, color: point, lineHeight: 1.08 }}>
              {c.coverBig}
            </div>
            <div style={{ fontFamily: NOTO, fontSize: 62, color: C.body, marginTop: 34 }}>
              {c.coverSub}
            </div>
          </div>
        ) : (
          <>
        {/* 편 표시 */}
        <div style={{ fontFamily: BLACK, fontSize: 44, color: C.tag, letterSpacing: 1 }}>
          {EP.title}
        </div>

        {/* 관점 배지 */}
        {c.tag && (
        <div
          style={{
            alignSelf: "flex-start",
            marginTop: 24,
            background: point,
            borderRadius: 14,
            padding: "12px 32px",
            fontFamily: BLACK,
            fontSize: 56,
            color: "#fff",
          }}
        >
          {c.tag}
        </div>
        )}

        {/* 🔴 위 여백 — 제목을 화면 가운데로 밀어 올린다(2026-07-24 "여백 많다") */}
        <div style={{ flex: 1 }} />

        {/* 리드 */}
        {c.lead && (
          <div style={{ fontFamily: NOTO, fontSize: 72, color: C.body, marginBottom: 8 }}>{c.lead}</div>
        )}

        {/* 큰 제목 */}
        {c.big && (
          <div
            style={{
              fontFamily: BLACK,
              fontSize: 164,
              color: C.title,
              lineHeight: 1.1,
              whiteSpace: "nowrap",
            }}
          >
            {c.big}
          </div>
        )}
        {c.bigPoint && (
          <div style={{ fontFamily: BLACK, fontSize: 164, color: point, lineHeight: 1.1, whiteSpace: "nowrap" }}>
            {c.bigPoint}
          </div>
        )}

        {/* 단순 2줄 표 (②) */}
        {c.rows && (
          <div style={{ marginTop: 34 }}>
            {c.rows.map(([k, v]) => (
              <div
                key={k}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  padding: "20px 0",
                  borderTop: "2px dashed #DFE3EC",
                }}
              >
                <span style={{ fontFamily: NOTO, fontSize: 76, color: C.body }}>{k}</span>
                <span style={{ fontFamily: BLACK, fontSize: 104, color: C.title }}>{v}</span>
              </div>
            ))}
          </div>
        )}

        {c.table && <OptionTable />}
        {c.result && <ResultTable />}

        {/* 소제목 */}
        {c.sub && (
          <div
            style={{
              fontFamily: NOTO,
              fontSize: 78,
              color: C.body,
              lineHeight: 1.45,
              marginTop: 34,
              whiteSpace: "pre-line",
            }}
          >
            {c.sub}
          </div>
        )}

        {/* 🔴 CTA는 위로 올린다(2026-07-24 지시) — 아래에 두면 캐릭터에 가린다 */}
        {c.cta && (
          <div
            style={{
              marginTop: 40,
              background: C.title,
              borderRadius: 16,
              padding: "34px 32px",
              textAlign: "center",
            }}
          >
            <div style={{ fontFamily: NOTO, fontSize: 54, color: "#B9C2D4" }}>답은 여기에</div>
            <div style={{ fontFamily: BLACK, fontSize: 88, color: "#FFC42E", marginTop: 6 }}>
              {EP.site}
            </div>
          </div>
        )}

        <div style={{ flex: 1 }} />

        {/* 강조 박스 — 🔴 우측을 비워 캐릭터를 피한다(2026-07-24). 안 그러면 글자를 가린다 */}
        {c.note && (
          <div
            style={{
              background: C.boxBg,
              borderLeft: "12px solid " + C.boxBar,
              borderRadius: 12,
              padding: "26px 30px",
              marginRight: 300, // 캐릭터 자리
              fontFamily: BLACK,
              fontSize: 66,
              color: C.boxInk,
              lineHeight: 1.3,
              whiteSpace: "nowrap",
            }}
          >
            {c.note}
          </div>
        )}
          </>
        )}
      </div>

      {/* 캐릭터 — 패널 우하단에 걸쳐 선다.
          🔴 우측 아이콘줄(SAFE.right)과 하단(SAFE.bottom)을 침범하지 않는 자리 */}
      <div
        style={{
          position: "absolute",
          right: SAFE.side + 10,
          top: PANEL.y + PANEL.h - 250,
        }}
      >
        <OlmaBall3D face={c.face} prop={c.prop} size={330} />
      </div>

    </AbsoluteFill>
  );
};

export const CARD_W = W;
export const CARD_H = H;
export const CARD_N = CARDS.length;
