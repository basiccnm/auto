// 여성향 톤 시안 — 2026-07-25
//
// 🔴 목적: "지금 스타일이 너무 남자 취향"이라는 지적에 대한 **비교용 시안**이다.
//    본편이 아니다. 반응 보고 방향 정한 뒤 버리거나 정식 편으로 키운다.
//
// 🔴 지금(남성향) → 시안(여성향) 바꾼 것 4가지. 구조·캐릭터 자산은 그대로 쓴다.
//    ① 배경   어두운 매장          → 밝은 크림·복숭아 그라데이션
//    ② 판     검은 판 + 빨강/노랑   → 흰 카드 + 코럴/로즈, 라운드 크게
//    ③ 캐릭터 크게(430)            → 작게(230). 음식이 주인공, 볼터치 켬
//    ④ 폰트   각진 BLACK 위주       → 둥근 JUA 위주, 숫자만 BLACK
import React from "react";
import { AbsoluteFill } from "remotion";

import { BLACK, JUA } from "../shorts/fonts";
import { BrandBall } from "../olma/BrandBall";

// 설빙 애플망고치즈설빙 (DB 실측)
const EP = {
  title: "애플망고치즈설빙",
  brand: "설빙",
  sell: 14500,
  cost: 2970,
  items: [
    ["우유얼음", 620],
    ["애플망고", 1180],
    ["크림치즈", 640],
    ["연유·토핑", 530],
  ],
};

const C = {
  bg: "linear-gradient(170deg, #FFF6EE 0%, #FFE9DC 45%, #FFD9C9 100%)",
  card: "#FFFFFF",
  ink: "#4A3B36", // 진한 갈색 — 검정보다 부드럽다
  sub: "#9A857C",
  point: "#FF7A8A", // 코럴 핑크
  gold: "#E8A33D",
  line: "#F2E1D6",
};

const won = (n) => n.toLocaleString("ko-KR");

// 공통 틀 — 밝은 배경 + 흰 카드 + 작은 캐릭터
const Frame = ({ children, face = "웃음", hearts = false }) => (
  <AbsoluteFill style={{ background: C.bg }}>
    {/* 캐릭터는 작게, 화면 아래 오른쪽 — 음식·글이 주인공 */}
    <div style={{ position: "absolute", bottom: 60, right: 40, opacity: 0.97 }}>
      <BrandBall brand="올마" face={face} scale={0.58} blush hearts={hearts} />
    </div>
    {children}
  </AbsoluteFill>
);

const Card = ({ children, top = 300 }) => (
  <div
    style={{
      position: "absolute",
      top,
      left: "50%",
      transform: "translateX(-50%)",
      width: 940,
      boxSizing: "border-box",
      background: C.card,
      borderRadius: 44,
      padding: "54px 48px",
      boxShadow: "0 18px 50px rgba(180,120,100,.18)",
    }}
  >
    {children}
  </div>
);

// ① 훅 — 숫자 대비지만 부드럽게
export const SoftHook = () => (
  <Frame face="놀람" hearts>
    <Card top={260}>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 54, color: C.sub }}>{EP.brand}</div>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 76, color: C.ink, marginTop: 6 }}>
        {EP.title}
      </div>
      <div
        style={{
          textAlign: "center",
          fontFamily: BLACK,
          fontSize: 104,
          color: C.ink,
          marginTop: 26,
          letterSpacing: -2,
        }}
      >
        {won(EP.sell)}원
      </div>
      <div style={{ height: 2, background: C.line, margin: "30px 0" }} />
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 52, color: C.sub }}>재료값은</div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 130, color: C.point, marginTop: 2 }}>
        {won(EP.cost)}원
      </div>
    </Card>
  </Frame>
);

// ② 재료 — 부드러운 목록
export const SoftItems = () => (
  <Frame face="웃음">
    <Card top={320}>
      <div style={{ fontFamily: JUA, fontSize: 62, color: C.ink, marginBottom: 10 }}>재료값을 더해보면</div>
      {EP.items.map(([n, v]) => (
        <div
          key={n}
          style={{
            display: "grid",
            gridTemplateColumns: "1fr auto",
            alignItems: "baseline",
            padding: "22px 0",
            borderBottom: `2px solid ${C.line}`,
          }}
        >
          <span style={{ fontFamily: JUA, fontSize: 58, color: C.sub }}>{n}</span>
          <span style={{ fontFamily: BLACK, fontSize: 66, color: C.ink }}>{won(v)}원</span>
        </div>
      ))}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr auto",
          alignItems: "baseline",
          marginTop: 24,
        }}
      >
        <span style={{ fontFamily: JUA, fontSize: 58, color: C.point }}>합계</span>
        <span style={{ fontFamily: BLACK, fontSize: 84, color: C.point }}>{won(EP.cost)}원</span>
      </div>
    </Card>
  </Frame>
);

// ③ 마무리 — 이득 프레임
export const SoftClose = () => (
  <Frame face="씨익" hearts>
    <Card top={340}>
      <div style={{ textAlign: "center", fontFamily: JUA, fontSize: 68, color: C.ink, lineHeight: 1.35 }}>
        집에서 만들면
      </div>
      <div style={{ textAlign: "center", fontFamily: BLACK, fontSize: 108, color: C.point, marginTop: 10 }}>
        4인분 나와요
      </div>
      <div
        style={{
          marginTop: 34,
          background: "#FFF4EC",
          borderRadius: 26,
          padding: "26px 30px",
          textAlign: "center",
          fontFamily: JUA,
          fontSize: 46,
          color: C.sub,
          lineHeight: 1.45,
        }}
      >
        재료값 기준이에요 · 만드는 품은 빼고요
      </div>
    </Card>
  </Frame>
);

// ── 비교안 B: 배경만 밝게 ────────────────────────────────────
// 🔴 "썸네일·캐릭터는 그대로 가고 배경으로만 가능할까?"(2026-07-25 질문)에 대한 시안.
//    지금 편(검은 판 + 큰 캐릭터) 구조를 **그대로** 두고 배경만 밝은 톤으로 갈았다.
//    장점: 시리즈 일관성이 안 깨지고, 배경 이미지만 교체하면 되니 작업량이 거의 없다.
import { Img, staticFile } from "remotion";
import { BLACK as B2, JUA as J2 } from "../shorts/fonts";

export const SoftBgOnly = () => (
  <AbsoluteFill style={{ background: "linear-gradient(170deg,#FFF3E6 0%,#FFE3D2 50%,#FFD2C4 100%)" }}>
    {/* 캐릭터는 지금 크기 그대로(음식 자리엔 디저트가 들어갈 자리) */}
    <div style={{ position: "absolute", bottom: 120, left: "50%", transform: "translateX(-50%)" }}>
      <BrandBall brand="올마" face="놀람" scale={1.15} blush />
    </div>
    {/* 판은 지금과 같은 검은 판 */}
    <div
      style={{
        position: "absolute",
        top: 250,
        left: "50%",
        transform: "translateX(-50%)",
        width: 1000,
        boxSizing: "border-box",
        background: "rgba(12,12,14,0.86)",
        border: "8px solid #000",
        borderRadius: 30,
        padding: 40,
        textAlign: "center",
      }}
    >
      <div style={{ fontFamily: B2, fontSize: 88, color: "#FF8A5C" }}>설빙 애플망고치즈설빙</div>
      <div style={{ fontFamily: B2, fontSize: 118, color: "#fff", marginTop: 8 }}>14,500원</div>
      <div style={{ fontFamily: J2, fontSize: 46, color: "#F0C9A0", marginTop: 4 }}>1인분 · 무옵션</div>
      <div style={{ fontFamily: B2, fontSize: 158, color: "#FFC93C", marginTop: 14 }}>원가 2,970원</div>
    </div>
  </AbsoluteFill>
);

// ── 비교안 B-2: 피자편 실제 장면을 밝은 톤으로 ────────────────
// 🔴 "토크피자는 모르겠네"(2026-07-25) — 말로는 감이 안 오니 **같은 장면**을 나란히 보려고 만든다.
//    지금 편(어두운 배경)과 이것(밝은 배경 + 볼터치)만 다르고 판·글자·구조는 완전히 같다.
export const SoftPizzaScene = () => (
  <AbsoluteFill style={{ background: "linear-gradient(170deg,#FFF3E6 0%,#FFE3D2 50%,#FFD2C4 100%)" }}>
    {/* 캐릭터 두 명 — 지금 편과 같은 자리·같은 크기 */}
    <div style={{ position: "absolute", top: 1145, left: "calc(50% - 225px)", transform: "translateX(-50%)" }}>
      <BrandBall brand="올마" face="놀람" scale={1.28} blush />
    </div>
    <div style={{ position: "absolute", top: 1145, left: "calc(50% + 225px)", transform: "translateX(-50%)" }}>
      <BrandBall brand="사장님" face="식은땀" scale={1.0} blush />
    </div>
    {/* 판 — 지금 편과 같은 검은 판 */}
    <div
      style={{
        position: "absolute",
        top: 200,
        left: "50%",
        transform: "translateX(-50%)",
        width: 1000,
        boxSizing: "border-box",
        background: "rgba(12,12,14,0.86)",
        border: "8px solid #000",
        borderRadius: 30,
        padding: 40,
      }}
    >
      <div style={{ fontFamily: B2, fontSize: 74, color: "#fff" }}>재료 원가</div>
      {[["모차렐라 치즈", "1,306원", true], ["도우", "1,013원", true]].map(([n, v, hot]) => (
        <div key={n} style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "baseline",
          marginTop: 22, borderTop: "3px solid rgba(255,255,255,.18)", paddingTop: 22 }}>
          <span style={{ fontFamily: J2, fontSize: 68, color: hot ? "#FFC93C" : "#E6DFD4" }}>{n}</span>
          <span style={{ fontFamily: B2, fontSize: 84, color: hot ? "#FFC93C" : "#fff" }}>{v}</span>
        </div>
      ))}
      <div style={{ marginTop: 32, background: "#FFF3D6", borderLeft: "16px solid #F5B70C", borderRadius: 12,
        padding: "24px 30px", fontFamily: B2, fontSize: 74, color: "#7A5200" }}>
        이 둘이 벌써 원가의 55%
      </div>
      <div style={{ marginTop: 26, textAlign: "right", fontFamily: J2, fontSize: 40, color: "rgba(255,255,255,.6)" }}>
        · 원재료 기준 원가입니다 ·
      </div>
    </div>
  </AbsoluteFill>
);

// ── 비교안 D: 판까지 밝게 (2026-07-25 확정 방향) ──────────────
// 🔴 "배경이나 글씨 색상이 게임 스타일이라 그런 것 같다"는 진단이 맞았다.
//    영향이 큰 순서: ① 판 색(검정→크림) ② 강조색(형광노랑→코럴) ③ 배경 ④ 볼터치
//    배경만 밝히면 검은 판 + 형광 노랑이 남아 여전히 게임 HUD 로 읽힌다.
// 🔴 판 **구조·글자 크기·캐릭터 위치는 그대로**다. 색만 바꿔 시리즈 형식은 유지한다.
export const SoftPizzaLight = () => (
  <AbsoluteFill style={{ background: "linear-gradient(170deg,#FFF6EE 0%,#FFE9DC 50%,#FFDCCB 100%)" }}>
    <div style={{ position: "absolute", top: 1145, left: "calc(50% - 225px)", transform: "translateX(-50%)" }}>
      <BrandBall brand="올마" face="놀람" scale={1.28} blush />
    </div>
    <div style={{ position: "absolute", top: 1145, left: "calc(50% + 225px)", transform: "translateX(-50%)" }}>
      <BrandBall brand="사장님" face="식은땀" scale={1.0} blush />
    </div>
    <div
      style={{
        position: "absolute",
        top: 200,
        left: "50%",
        transform: "translateX(-50%)",
        width: 1000,
        boxSizing: "border-box",
        background: "#FFFFFF",          // 검정 → 흰색
        borderRadius: 40,               // 라운드 키움
        padding: 44,
        boxShadow: "0 16px 44px rgba(180,120,100,.20)",  // 테두리 대신 그림자
      }}
    >
      <div style={{ fontFamily: J2, fontSize: 68, color: "#4A3B36" }}>재료 원가</div>
      {[["모차렐라 치즈", "1,306원", true], ["도우", "1,013원", true]].map(([n, v, hot]) => (
        <div key={n} style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "baseline",
          marginTop: 20, borderTop: "2px solid #F2E1D6", paddingTop: 20 }}>
          <span style={{ fontFamily: J2, fontSize: 64, color: hot ? "#FF7A8A" : "#9A857C" }}>{n}</span>
          <span style={{ fontFamily: B2, fontSize: 78, color: hot ? "#FF7A8A" : "#4A3B36" }}>{v}</span>
        </div>
      ))}
      <div style={{ marginTop: 30, background: "#FFF4EC", borderRadius: 22,
        padding: "24px 30px", fontFamily: J2, fontSize: 62, color: "#8A6A5E" }}>
        이 둘이 벌써 원가의 55%
      </div>
      <div style={{ marginTop: 22, textAlign: "right", fontFamily: J2, fontSize: 38, color: "#C0AA9E" }}>
        · 원재료 기준 원가입니다 ·
      </div>
    </div>
  </AbsoluteFill>
);
