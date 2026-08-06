// 레시피편 2 썸네일 — 초간단 지코바 레시피 (2026-07-28)
//
// 🔴 원가편·뿌링클 레시피편과 **같은 템플릿**이다. 한 채널에 섞이니 얼굴이 같아야 한다.
//    ThumbTemplate 을 그대로 쓰고 **글자와 음식만** 바꾼다.
//    구분은 리본 문구로만 — "이거 얼마남아 N" / "초간단 레시피".
import React from "react";

import { BLACK, JUA } from "../shorts/fonts";
import { TONE } from "../cards/tone";
import { ThumbInner, ThumbLayout } from "../cards/ThumbTemplate";
import { ICON } from "../cards/props";
import { DISH4 } from "../cards/props2";

const COLORS = { 검정: "#111111", 코럴: TONE.point, 회갈색: TONE.sub };
const FONTS = { 굵게: BLACK, 동글: JUA };

// 원가편과 같은 두 줄 구조 — 메뉴명(검정) + 훅(코럴)
export const 줄 = [
  { 글: "집에서 집코바", 크기: 122, 좌우: 0, 위아래: -74, 색: "검정", 폰트: "굵게" },
  { 글: "볶으면", 크기: 150, 좌우: -89, 위아래: 82, 색: "코럴", 폰트: "굵게" },
];

export const 소품 = [
  { 그림: ICON.물음표, x: 229, y: -284, 크기: 165, 회전: -3 },
  { 그림: "food/s14_21.png", x: 0, y: -542, 크기: 200, 회전: 0 }, // 초록 체크
];

const HOOK = (
  <>
    {줄.map((s, i) => (
      <div key={i}
        style={{
          position: "absolute", left: "50%", top: "50%",
          transform: `translate(calc(-50% + ${s.좌우}px), calc(-50% + ${s.위아래}px))`,
          whiteSpace: "nowrap", lineHeight: 1.05,
          fontFamily: FONTS[s.폰트], fontSize: s.크기, color: COLORS[s.색],
        }}>
        {s.글}
      </div>
    ))}
  </>
);

const ARGS = {
  hook: HOOK,
  label: "초간단 레시피",
  // 🔴 썸네일은 **완성된 모습**이 예뻐야 한다. 조리 과정 그림은 안 예쁘다.
  //    지코바는 **빨간 양념이 자글자글한** 모습이라 `지코바닭` 을 쓴다.
  food: DISH4.지코바닭,
  fit: false,
  소품,
  화살표: [],
  리본색: "#FFFFFF",
  음식배율: 1, // 누끼 기준 자동정렬이라 미세조정 불필요
  음식내림: 90, // 🔴 음식만 내린다(2026-07-28 지시). 카드·리본·소품은 안 따라온다
};

export const ThumbZicoba = () => <ThumbLayout {...ARGS} />;
export const ThumbCardZicoba = () => <ThumbInner {...ARGS} />;
