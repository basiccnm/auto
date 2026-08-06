// 레시피편 2 조립 — 초간단 지코바 레시피 (2026-07-28)
//
// 🔴 첫 장면 = 썸네일. ThumbCardZicoba(배경 없는 알맹이)를 그대로 쓴다.
//    ShopCombo 가 배경(GridBg)을 이미 깔기 때문에 알맹이만 얹으면 된다.
import React from "react";

import { ShopCombo } from "./ShopCombo";
import { ThumbCardZicoba } from "./ThumbZicoba";
import { EP, ITEMS, total, STEPS, DONE, 손 } from "./combo_zicoba";

export const SHOP_ZICOBA_SEC = 15;

export const ShopZicoba = () => (
  <ShopCombo
    EP={EP} ITEMS={ITEMS} total={total} STEPS={STEPS} DONE={DONE} 손={손}
    renderHook={() => <ThumbCardZicoba />}
    voiceDir="voiceR2"
  />
);
