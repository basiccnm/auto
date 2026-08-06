// 유튜브 프로필 + 배너 — 여성향 톤 (2026-07-25)
//
// 🔴 프로필 1080×1080 — 유튜브가 **원형으로 자른다.** 가운데 원 안에만 넣는다.
// 🔴 배너 2048×1152 — 기기마다 보이는 범위가 다르다.
//    TV=전체 / PC·폰=중앙 1546×423. **핵심은 중앙 1546×423 안에** 다 들어와야 한다.
// 🔴 캐릭터: 올마=여자(핑크, 진행) / 나마=남자(노랑, 사장님)
import React from "react";
import { AbsoluteFill } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { BrandBall } from "../olma/BrandBall";
import { GridBg, ToolScatter } from "./SoftKit";
import { TONE } from "./tone";

export const ProfileSoft = () => (
  <GridBg base={TONE.bg} line={TONE.grid} size={64}>
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 4, marginTop: -30 }}>
        <BrandBall brand="올마" face="웃음" scale={1.02} blush pin lashes />
        <BrandBall brand="사장님" face="웃음" scale={0.86} blush />
      </div>
      <div style={{ fontFamily: BLACK, fontSize: 122, color: TONE.ink, letterSpacing: -2, marginTop: 10 }}>
        올마나마
      </div>
      <div style={{ fontFamily: JUA, fontSize: 50, color: TONE.point, marginTop: 2 }}>이거 얼마남아?</div>
    </AbsoluteFill>
  </GridBg>
);

export const BannerSoft = () => (
  <GridBg base={TONE.bg} line={TONE.grid} size={72}>
    <ToolScatter opacity={0.35} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      {/* 🔴 안전영역 1546×423 **안쪽**에 다 들어와야 한다(2026-07-25).
          처음엔 캐릭터가 경계에 걸쳐 나마 모자 윗부분이 잘렸다.
          모자가 볼 위로 솟으므로 나마는 더 작게 잡는다 */}
      <div style={{ width: 1400, height: 360, display: "flex", alignItems: "center", justifyContent: "center", gap: 30 }}>
        <BrandBall brand="올마" face="웃음" scale={0.72} blush />
        <div style={{ textAlign: "center" }}>
          <div style={{ fontFamily: BLACK, fontSize: 108, color: TONE.ink, letterSpacing: -3, lineHeight: 1.05 }}>
            올마나마
          </div>
          <div style={{ fontFamily: JUA, fontSize: 46, color: TONE.point, marginTop: 6 }}>
            사먹는 음식, 재료값은 얼마일까?
          </div>
          <div style={{ fontFamily: JUA, fontSize: 32, color: TONE.sub, marginTop: 8 }}>
            원가 공개 · olmanama.com
          </div>
        </div>
        <BrandBall brand="사장님" face="웃음" scale={0.6} blush />
      </div>
    </AbsoluteFill>
  </GridBg>
);

// ── 올마픽 (조합·쇼핑 채널) 브랜딩 — 2026-07-27 신설 ────────────
//
// 🔴 톤·색은 올마나마와 **같게** 간다. 두 채널이 형제로 읽혀야
//    원가 채널에서 쌓은 신뢰가 추천으로 옮겨온다.
//    구분은 **강조색 하나뿐** — 올마나마 코럴 / 올마픽 노랑.
// 🔴 캐릭터는 올마만 쓴다. 사장님(가게 주인)은 파는 쪽이라 추천 채널에 안 맞는다.
const PICK = "#E8A93C"; // 올마픽 강조색 — 노랑·주황 계열

export const ProfilePick = () => (
  <GridBg base={TONE.bg} line={TONE.grid} size={64}>
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <BrandBall brand="올마" face="웃음" scale={1.16} blush pin lashes />
      <div style={{ fontFamily: BLACK, fontSize: 134, color: TONE.ink, letterSpacing: -2, marginTop: 18 }}>
        올마픽
      </div>
      <div style={{ fontFamily: JUA, fontSize: 48, color: PICK, marginTop: 2 }}>
        집에서 이 조합
      </div>
    </AbsoluteFill>
  </GridBg>
);

export const BannerPick = () => (
  <GridBg base={TONE.bg} line={TONE.grid} size={72}>
    <ToolScatter opacity={0.35} />
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      {/* 안전영역 1546×423 안쪽 */}
      <div style={{ width: 1400, height: 360, display: "flex", alignItems: "center", justifyContent: "center", gap: 40 }}>
        <BrandBall brand="올마" face="웃음" scale={0.74} blush pin lashes />
        <div style={{ textAlign: "center" }}>
          <div style={{ fontFamily: BLACK, fontSize: 112, color: TONE.ink, letterSpacing: -3, lineHeight: 1.05 }}>
            올마픽
          </div>
          <div style={{ fontFamily: JUA, fontSize: 46, color: PICK, marginTop: 6 }}>
            사먹지 말고 집에서, 이 조합이면 됩니다
          </div>
          <div style={{ fontFamily: JUA, fontSize: 32, color: TONE.sub, marginTop: 8 }}>
            간단한 꿀조합 · 살 곳은 댓글에
          </div>
        </div>
      </div>
    </AbsoluteFill>
  </GridBg>
);
