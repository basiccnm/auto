// 썸네일 표준 템플릿 — 전 편 공통 (2026-07-25 확정)
//
// 🔴 **박스 위치·크기는 고정이다. 편이 바뀌어도 절대 안 움직인다.**
//    바뀌는 건 안에 들어가는 글자와 음식 이미지뿐이다.
//    - 훅 카드   : 크기 고정. **글자가 많든 적든 카드 안을 꽉 채우게** 자동 축소·확대된다
//    - 시리즈 리본: 위치 고정
//    - 메뉴 이미지: 박스를 꽉 채운다
//
// 🔴 기준 비율은 **4:5**(릴스). 쇼츠는 9:16 전체가 보이고, 릴스는 4:5 로 잘린다.
//    주력이 쇼츠·릴스라 4:5 안에 다 넣는다 → y 285 ~ 1635.
//    (인스타 프로필 격자 1:1 에서는 위아래가 조금 잘리지만 그 화면은 버린다)
//
//    위 여백  285 ~ 418   (133)
//    훅 카드  418 ~ 818   (400)  ← 고정
//    리본     854 ~ 946   ( 92)  ← 고정
//    메뉴     962 ~ 1502  (540)
//    아래 여백1502 ~ 1635  (133)  ← 위 여백과 같게
import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { continueRender, delayRender, Img, staticFile } from "remotion";

import { TONE } from "./tone";
import { GridBg, Ribbon } from "./SoftKit";
import { BLACK, JUA } from "../shorts/fonts";
import { FOOD_TRIM } from "./food_trim";

const ARROW_COLORS = { 검정: "#111111", 진한갈색: "#4A3A32", 코럴: "#E05575", 회갈색: "#6E5A4E", 금색: "#DDA05A" };

// ── 고정 좌표. 여기 숫자를 편마다 바꾸지 마라 ──────────────
export const THUMB = {
  safeTop: 285,
  safeBottom: 1635,

  cardTop: 418,
  cardW: 940,
  cardH: 400,
  cardPad: 74, // 🔴 글자가 카드 모서리에 닿지 않게 하는 여백. 이걸 줄이면 글씨가 커진다

  ribbonTop: 854, // 2026-07-25 지시로 10px 내림
  ribbonW: 600,
  ribbonFont: 52,

  foodTop: 962,
  foodW: 1080,
  foodH: 540,
};

/**
 * 상자 크기는 고정하고 **안의 내용만** 상자에 맞게 줄인다.
 * 글자 수가 편마다 달라도 카드가 흔들리지 않게 하는 것이 목적이다.
 *
 * 🔴 두 가지를 반드시 지킨다(2026-07-25 스튜디오에서 글자가 2.4배로 터진 사고):
 *   ① 크기는 **offsetWidth/offsetHeight** 로 잰다. getBoundingClientRect 는
 *      transform 이 반영된 값이라 배율을 다시 계산하면 눈덩이처럼 커진다.
 *   ② 배율 상한은 **1** — 절대 확대하지 않는다. 측정이 실패해도 원래 크기로 남는다.
 *      (그래서 각 편의 기본 글자 크기를 카드에 꽉 차게 잡아두는 게 맞다)
 *
 * 폰트가 늦게 로드되면 폭이 바뀌므로 로드 후 한 번 더 잰다.
 */
export const FitBox = ({ w, h, pad = 0, max = 1, children }) => {
  const ref = useRef(null);
  const [handle] = useState(() => delayRender("thumb-fitbox"));
  const [scale, setScale] = useState(null);

  useLayoutEffect(() => {
    let dead = false;
    const measure = () => {
      if (dead || !ref.current) return;
      const cw = ref.current.offsetWidth;
      const ch = ref.current.offsetHeight;
      if (!cw || !ch) return setScale(1);
      setScale(Math.min((w - pad * 2) / cw, (h - pad * 2) / ch, max));
    };
    measure(); // 폰트가 이미 있으면 여기서 끝난다
    document.fonts.ready.then(measure); // 늦게 로드되면 다시 잰다
    return () => {
      dead = true;
    };
  }, [w, h, pad, max]);

  useEffect(() => {
    if (scale !== null) continueRender(handle);
  }, [scale, handle]);

  return (
    <div
      style={{
        width: w,
        height: h,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      <div
        ref={ref}
        style={{
          transform: `scale(${scale ?? 1})`,
          transformOrigin: "center center",
          visibility: scale === null ? "hidden" : "visible",
          whiteSpace: "nowrap",
        }}
      >
        {children}
      </div>
    </div>
  );
};

/**
 * @param hook  훅 카드 내용 (JSX). 크기 걱정 말고 쓰면 알아서 맞춰진다
 * @param label 리본 글자
 * @param food  음식 이미지 경로 (public 기준). 박스를 꽉 채운다
 */
// 🔴 **알맹이만.** 배경을 안 그린다 —
//    쇼츠 훅 장면은 talk_engine 이 이미 배경을 깔고 그 위에 이걸 얹기 때문이다.
//    (여기서 GridBg 를 또 그리면 격자가 두 겹으로 겹친다)
// fit=false 면 FitBox 를 안 쓴다 — 줄마다 좌표·크기를 직접 정하는 편(조정.html 로 맞춘 편)에서 쓴다
// 🔴 위로 갈수록 가늘고 아래로 굵어지는 **둥근 화살표**. 가격 떨어지는 느낌용.
//    s14_25(아이콘 화살표)는 너무 정형화돼서 안 쓴다(2026-07-25 지시).
export const FatArrow = ({ size = 240, color = "#E05575" }) => (
  <svg viewBox="0 0 160 240" width={size * 0.67} height={size} style={{ overflow: "visible" }}>
    <path
      d="M 80 14 C 73 62, 71 104, 71 142 L 30 142 L 80 222 L 130 142 L 89 142 C 89 104, 87 62, 80 14 Z"
      fill={color} stroke={color} strokeWidth="20" strokeLinejoin="round" strokeLinecap="round"
    />
  </svg>
);

// ── 음식 일러 — **캔버스가 아니라 누끼 영역** 기준으로 크기를 맞춘다 ──────
//
// 🔴 2026-07-27 지적: "밑에 음식 일러가 사이즈가 너무 차이나. 바탕 사이즈가 아닌 누끼딴 부분으로."
//    일러마다 투명 여백이 달라서 같은 박스에 contain 하면 보이는 크기가 제각각이었다.
//      빙수 2816x1536 캔버스에 내용 1427x1255 → 화면 502px  /  엽떡 → 648px
//    편마다 `음식배율` 을 손으로 만져 맞추던 걸 여기서 **자동으로** 없앤다.
//
// 🔴 **목표는 내용(누끼) 크기다.** 아래 두 숫자만 지키면 전 편이 같은 구도가 된다.
//    `음식배율` 은 이 목표에 곱하는 미세조정 — 기본 1, 웬만하면 건드리지 마라.
export const FOOD_FIT = {
  내용높이: 540, // 화면에 보이는 음식의 높이
  내용폭: 940, // 가로로 긴 그림이 카드보다 넓어지지 않게 하는 상한
};

const FoodImg = ({ food, 배율 = 1, 내림 = 0 }) => {
  const t = FOOD_TRIM[food];
  const cx = 540; // 무대 가로 한가운데
  // 🔴 `내림` 은 **음식만** 위아래로 미는 값이다(양수 = 아래).
  //    카드·리본·소품은 안 따라온다 — "음식만 내려" 했는데 다 같이 내려가던 사고를 막는다.
  const cy = THUMB.foodTop + THUMB.foodH / 2 + 내림; // 음식 박스 세로 한가운데

  // 잰 값이 없는 그림(새로 넣고 food_trim.py 를 안 돌린 경우)은 옛 방식으로 그린다
  if (!t) {
    return (
      <div
        style={{
          position: "absolute", top: THUMB.foodTop, left: "50%", transform: "translateX(-50%)",
          width: THUMB.foodW * 배율, height: THUMB.foodH * 배율, marginTop: 내림, zIndex: 1,
        }}
      >
        <Img src={staticFile(food)} style={{ width: "100%", height: "100%", objectFit: "contain", filter: FOOD_SHADOW }} />
      </div>
    );
  }

  const [fx, fy, fw, fh, ar] = t; // 누끼 x,y,w,h (0~1) + 캔버스 가로세로비
  const TW = FOOD_FIT.내용폭 * 배율;
  const TH = FOOD_FIT.내용높이 * 배율;
  // 이미지를 H 높이로 그리면 보이는 내용은 (H*ar*fw) x (H*fh) 다. 그게 목표에 딱 맞게 H 를 푼다
  const H = Math.min(TW / (ar * fw), TH / fh);
  const W = H * ar;

  return (
    <Img
      src={staticFile(food)}
      style={{
        position: "absolute",
        width: W,
        height: H,
        // 누끼 영역의 한가운데가 (cx, cy) 에 오도록 이미지를 민다
        left: cx - W * (fx + fw / 2),
        top: cy - H * (fy + fh / 2),
        zIndex: 1,
        filter: FOOD_SHADOW,
      }}
    />
  );
};

const FOOD_SHADOW = "drop-shadow(0 14px 30px rgba(180,120,90,.24))";
const NOTE_FONTS = { 굵게: BLACK, 동글: JUA };

// 무대 한가운데(540, 960)를 (0,0) 으로 놓는다 — 편집기와 좌표계가 같다
const Layer = ({ x, y, rot = 0, z = 6, children }) => (
  <div
    style={{
      position: "absolute", left: "50%", top: "50%",
      transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) rotate(${rot}deg)`,
      zIndex: z,
    }}
  >
    {children}
  </div>
);

// 🔴 `쪽지` = **카드 바깥**에 놓는 짧은 글(재업 표시 같은 것).
//    훅 글자는 카드 안에서 잘리므로(overflow hidden) 카드 위로 못 올린다 → 이 자리로 뺀다.
//    좌표는 소품·화살표와 같은 무대 중심 기준. 카드 윗변이 y = -542 다.
export const ThumbInner = ({ hook, label, food, pad = THUMB.cardPad, fit = true, 소품 = [], 화살표 = [], 쪽지 = [], 리본색 = TONE.ink, 음식배율 = 1, 음식내림 = 0 }) => (
  <>
    {/* ① 훅 카드 — 크기 고정 */}
    <div
      style={{
        position: "absolute",
        top: THUMB.cardTop,
        left: "50%",
        transform: "translateX(-50%)",
        width: THUMB.cardW,
        height: THUMB.cardH,
        boxSizing: "border-box",
        background: TONE.card,
        borderRadius: 40,
        boxShadow: TONE.shadow,
        zIndex: 2,
      }}
    >
      {fit ? (
        <FitBox w={THUMB.cardW} h={THUMB.cardH} pad={pad}>
          {hook}
        </FitBox>
      ) : (
        // 자동축소를 안 써도 **가운데 정렬은 해야 한다**(안 하면 글씨가 카드 위로 새어 나간다)
        <div
          style={{
            width: "100%", height: "100%", display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", overflow: "hidden",
          }}
        >
          {hook}
        </div>
      )}
    </div>

    {/* ② 시리즈 리본 — 위치 고정 */}
    <div
      style={{
        position: "absolute",
        top: THUMB.ribbonTop,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 3,
      }}
    >
      {/* 🔴 리본 글씨는 흰색이 아니라 **메뉴명과 같은 진한 갈색**(2026-07-25 지시).
          핑크 위 흰 글씨는 흐리멍텅해 보인다 */}
      <Ribbon text={label} w={THUMB.ribbonW} color={TONE.ribbon} ink={리본색} fontSize={THUMB.ribbonFont} />
    </div>

    {/* ③ 소품 — 편집기에서 올린 것 */}
    {소품.map((s, i) => (
      <Layer key={`p${i}`} x={s.x} y={s.y} rot={s.회전}>
        <Img src={staticFile(s.그림)} style={{ width: s.크기, height: s.크기, objectFit: "contain" }} />
      </Layer>
    ))}

    {/* ④ 화살표 */}
    {화살표.map((s, i) => (
      <Layer key={`a${i}`} x={s.x} y={s.y} rot={s.회전}>
        <FatArrow size={s.크기} color={ARROW_COLORS[s.색] || TONE.point} />
      </Layer>
    ))}

    {/* ④-2 쪽지 — 카드 바깥 글자 */}
    {쪽지.map((s, i) => (
      <Layer key={`n${i}`} x={s.x} y={s.y} rot={s.회전 || 0} z={7}>
        <div style={{ fontFamily: NOTE_FONTS[s.폰트] || JUA, fontSize: s.크기,
          color: ARROW_COLORS[s.색] || TONE.sub, whiteSpace: "nowrap", lineHeight: 1.05 }}>{s.글}</div>
      </Layer>
    ))}

    {/* ⑤ 메뉴 이미지 — 누끼 영역을 박스에 맞춘다 */}
    <FoodImg food={food} 배율={음식배율} 내림={음식내림} />
  </>
);

// 배경까지 포함한 완성본 — 썸네일 Still 은 이걸 쓴다
export const ThumbLayout = (props) => (
  <GridBg base={TONE.bg} line={TONE.grid}>
    <ThumbInner {...props} />
  </GridBg>
);
