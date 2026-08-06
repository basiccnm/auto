// 레시피편 1 조립 — 집에서 뿌링클 (2026-07-27)
//
// 🔴 첫 장면 = 썸네일. ThumbCardRecipe(배경 없는 알맹이)를 그대로 쓴다.
//    ShopCombo 가 배경(GridBg)을 이미 깔기 때문에 알맹이만 얹으면 된다.
import React from "react";

import { ShopCombo } from "./ShopCombo";
import { ThumbCardRecipe } from "./ThumbRecipe";
import { EP, ITEMS, total, STEPS, DONE, 손 } from "./combo_bburinkle";

export const SHOP_BBU_SEC = 15;

export const ShopBburinkle = () => (
  <ShopCombo
    EP={EP} ITEMS={ITEMS} total={total} STEPS={STEPS} DONE={DONE} 손={손}
    renderHook={() => <ThumbCardRecipe />}
    voiceDir="voiceR1"
  />
);
