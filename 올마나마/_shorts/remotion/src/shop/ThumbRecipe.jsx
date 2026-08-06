// 레시피편 썸네일 — 원가편과 **같은 템플릿**을 쓴다 (2026-07-27)
//
// 🔴 두 형식이 한 채널에 섞이므로 썸네일이 같은 얼굴이어야 한다.
//    ThumbTemplate 을 그대로 쓰고 **글자와 음식만** 바꾼다.
//    구분은 리본 문구로만 한다 — "이거 얼마남아 N" / "초간단 레시피".
import React from "react";

import { BLACK, JUA } from "../shorts/fonts";
import { TONE } from "../cards/tone";
import { ThumbInner, ThumbLayout } from "../cards/ThumbTemplate";
import { ICON } from "../cards/props";
import { DISH4 } from "../cards/props2";
import { EP } from "./combo_bburinkle";

const COLORS = { 검정: "#111111", 코럴: TONE.point, 회갈색: TONE.sub };
const FONTS = { 굵게: BLACK, 동글: JUA };

// 원가편과 같은 두 줄 구조 — 메뉴명(검정) + 훅(코럴)
export const 줄 = [
  { 글: "집에서 뿌링클", 크기: 122, 좌우: 0, 위아래: -74, 색: "검정", 폰트: "굵게" },
  { 글: "쉐키쉐키", 크기: 150, 좌우: -96, 위아래: 88, 색: "코럴", 폰트: "굵게" },
];

export const 소품 = [
  { 그림: ICON.물음표, x: 250, y: -276, 크기: 170, 회전: -3 },
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
  // 🔴 썸네일은 **완성된 모습**이 예뻐야 한다. 통에 담긴 그림은 조리 과정이라 안 예쁘다.
  //    🔴 뿌링클은 **하얀 시즈닝이 묻은** 치킨이어야 한다. 그냥 후라이드는 틀리다.
  food: DISH4.뿌링클치킨,
  fit: false,
  소품,
  화살표: [],
  리본색: "#FFFFFF",
  음식배율: 1, // 누끼 기준 자동정렬로 바뀌어 미세조정 불필요
};

export const ThumbRecipe = () => <ThumbLayout {...ARGS} />;
export const ThumbCardRecipe = () => <ThumbInner {...ARGS} />;
