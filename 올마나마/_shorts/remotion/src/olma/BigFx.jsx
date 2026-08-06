// 큰 이펙트 — 화산·눈알·썸네일 카드 (2026-07-21)
//
// 🔴 Effects.jsx가 이미 길어서 큰 것들만 따로 뺐다.
// 🔴 전부 frame 계산. CSS 애니메이션 금지 — 되감을 때 어긋난다.
// 🔴 이모지 금지 — 렌더 환경 폰트에 따라 깨진다. 전부 SVG.
import React from "react";
import { Easing, interpolate, random, useCurrentFrame } from "remotion";

const E = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };
const LINE = "#000";

// ── 화산 폭발 — 올마 머리에서 터진다. at 프레임부터 시작
//    x,y는 분화구 위치(화면 비율). 연기 → 용암 → 재 순으로 올라온다.
export const Volcano = ({ at = 0, x = "50%", y = "40%", size = 1 }) => {
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = f - at;

  // 🔴 1차는 "연기 몇 조각"이라 폭발로 안 보였다(2026-07-21).
  //    세기를 안 죽이고(0.85 유지), 개수·크기·속도를 전부 키운다.
  const power = interpolate(k, [0, 6, 90], [0, 1, 0.85], { ...E, easing: Easing.out(Easing.quad) });

  return (
    // 🔴 좌표 함정(2026-07-21) — viewBox의 원점(0,0)이 **분화구**다.
    //    -50% -50%로 놓으면 원점이 svg 한가운데가 아니라 아래쪽에 있어서
    //    불기둥이 캐릭터 다리에서 솟아 치마처럼 보였다.
    //    svg 아래변이 원점이므로 **-50% -100%**로 놓아야 (x,y)가 분화구가 된다.
    <div style={{ position: "absolute", left: x, top: y, translate: "-50% -100%", pointerEvents: "none" }}>
      <svg viewBox="-460 -1100 920 1200" width={920 * size} height={1200 * size} style={{ overflow: "visible" }}>
        {/* 연기 기둥 — 굵게 뭉쳐 올라간다 */}
        {Array.from({ length: 30 }, (_, i) => {
          const seed = random(`vs${i}`);
          const t = ((k / 40) + seed) % 1;
          const up = -90 - t * 880 * power;
          const spread = (seed - 0.5) * 520 * t;
          const r = (52 + seed * 96) * (0.4 + t) * power;
          return (
            <circle
              key={`s${i}`}
              cx={spread}
              cy={up}
              r={r}
              fill={i % 3 === 0 ? "#5C534A" : "#847B6F"}
              opacity={(1 - t * 0.85) * 0.8}
            />
          );
        })}

        {/* 용암 — 크고 많게. 위로 솟았다 포물선으로 떨어진다 */}
        {Array.from({ length: 26 }, (_, i) => {
          const seed = random(`vl${i}`);
          const t = ((k / 22) + seed) % 1;
          const ang = (seed - 0.5) * 2.2;
          const d = t * 620 * power;
          return (
            <circle
              key={`l${i}`}
              cx={Math.sin(ang) * d}
              cy={-Math.abs(Math.cos(ang)) * d + t * t * 460}
              r={(16 + seed * 30) * power}
              fill={seed > 0.55 ? "#FFD24A" : "#E5352B"}
              stroke={LINE}
              strokeWidth={4}
              opacity={1 - t * 0.55}
            />
          );
        })}

        {/* 🔴 불기둥이 **삼각 고깔**처럼 보였다(2026-07-21). 폭이 좁고 곧게 뻗어서다.
               불꽃은 아래가 넓고 위로 갈수록 **여러 갈래로 갈라져 흔들려야** 한다.
               갈래마다 높이를 다르게 주고, 프레임에 따라 좌우로 일렁이게 한다. */}
        {/* 🔴 갈래가 **뾰족한 삼각형**이라 톱니처럼 보였다(2026-07-21).
               제어점을 바깥으로 크게 빼서 옆구리를 불룩하게 만들고,
               꼭대기는 한 점이 아니라 살짝 휘어지게 한다. */}
        {[
          { dx: 0, h: 1.0, w: 86, c: "#FF8A2B" },
          { dx: -112, h: 0.66, w: 62, c: "#FF8A2B" },
          { dx: 112, h: 0.72, w: 62, c: "#FF8A2B" },
          { dx: -56, h: 0.84, w: 52, c: "#FFD24A" },
          { dx: 56, h: 0.78, w: 52, c: "#FFD24A" },
        ].map((fl, i) => {
          const sway = Math.sin(k / 3 + i) * 26 * power;
          const top = -560 * fl.h * power;
          const tipX = fl.dx + sway;
          return (
            <path
              key={i}
              d={
                `M${fl.dx - fl.w} 46 ` +
                // 왼쪽 옆구리 — 제어점을 바깥·위로 빼서 불룩하게
                `C${fl.dx - fl.w * 1.9} ${top * 0.36} ${tipX - fl.w * 1.15} ${top * 0.76} ${tipX} ${top} ` +
                // 오른쪽 옆구리 — 대칭
                `C${tipX + fl.w * 1.15} ${top * 0.76} ${fl.dx + fl.w * 1.9} ${top * 0.36} ${fl.dx + fl.w} 46 Z`
              }
              fill={fl.c}
              stroke={i < 3 ? LINE : "none"}
              strokeWidth={5}
              strokeLinejoin="round"
              opacity={0.95 * power}
            />
          );
        })}
        {/* 분화구 입구 — 불꽃 아래를 덮어 "여기서 나온다"를 만든다 */}
        <ellipse cx={0} cy={48} rx={132 * power} ry={26 * power} fill="#E5352B" stroke={LINE} strokeWidth={6} />
      </svg>
    </div>
  );
};

// ── 눈알 튀어나옴 — 충격받았을 때. 얼굴 앞에 겹쳐 쓴다
//    Olma의 눈 좌표(168/232, 150)에 맞춰 두 개를 쏜다.
export const PopEyes = ({ at = 0, scale = 1 }) => {
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = f - at;
  // 튀어나갔다(0~7) → 부들부들(7~14) → 돌아옴(14~22)
  const out = interpolate(k, [0, 7, 14, 22], [0, 1, 1, 0], { ...E, easing: Easing.out(Easing.back(2)) });
  const wob = k > 7 && k < 14 ? Math.sin(k * 2.2) * 6 : 0;
  if (out <= 0.01) return null;

  const Eye = ({ cx }) => (
    <g style={{ translate: `0px ${-70 * out + wob}px` }}>
      {/* 눈알 */}
      <circle cx={cx} cy={150} r={30 * (0.5 + out * 0.5)} fill="#fff" stroke={LINE} strokeWidth={6} />
      <circle cx={cx} cy={150 + 6 * out} r={12} fill={LINE} />
      {/* 튀어나온 줄기 */}
      <path
        d={`M${cx} ${150 + 26 * out} v${52 * out}`}
        stroke={LINE}
        strokeWidth={7}
        strokeLinecap="round"
        opacity={out}
      />
    </g>
  );

  return (
    <svg
      viewBox="-90 -60 580 680"
      width={580 * scale}
      height={680 * scale}
      style={{ position: "absolute", inset: 0, overflow: "visible", pointerEvents: "none" }}
    >
      <Eye cx={168} />
      <Eye cx={232} />
    </svg>
  );
};

// ── 썸네일 카드 — 오프닝 3~6초. 비스듬히 날아와 쿵 꽂힌다
export const ThumbCard = ({ at = 0, top = "", main = "", sub = "" }) => {
  const f = useCurrentFrame();
  const k = f - at;
  if (k < 0) return null;

  // 멀리서(2.4배) 날아와 살짝 작아졌다 제자리
  const sc = interpolate(k, [0, 6, 10, 15], [2.4, 0.9, 1.06, 1], { ...E, easing: Easing.out(Easing.quad) });
  const op = interpolate(k, [0, 4], [0, 1], E);
  const rot = interpolate(k, [0, 8, 15], [-14, 3, -2], { ...E, easing: Easing.out(Easing.quad) });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: op,
        scale: String(sc),
        rotate: `${rot}deg`,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          background: "#fff",
          border: `12px solid ${LINE}`,
          borderRadius: 34,
          padding: "46px 60px 56px",
          textAlign: "center",
          boxShadow: "0 22px 0 rgba(0,0,0,0.22)",
          maxWidth: 940,
        }}
      >
        {top && <div style={{ fontSize: 62, color: "#5A5040", marginBottom: 8 }}>{top}</div>}
        <div style={{ fontSize: 128, color: "#E5352B", lineHeight: 1.04, letterSpacing: -5 }}>{main}</div>
        {sub && (
          <div
            style={{
              marginTop: 18,
              display: "inline-block",
              fontSize: 58,
              background: "#FFD400",
              borderRadius: 14,
              padding: "8px 26px 14px",
            }}
          >
            {sub}
          </div>
        )}
      </div>
    </div>
  );
};

// ── 반짝임 — 인사 장면용. 별이 톡톡 튄다
export const Sparkles = ({ n = 10, color = "#FFD400" }) => {
  const f = useCurrentFrame();
  return (
    <svg viewBox="0 0 1080 1920" style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {Array.from({ length: n }, (_, i) => {
        const seed = random(`sp${i}`);
        const t = ((f / 38) + seed) % 1;
        const s = Math.sin(t * Math.PI) * (14 + seed * 16);
        const cx = 90 + seed * 900;
        const cy = 300 + random(`spy${i}`) * 1100;
        if (s <= 0.5) return null;
        return (
          <path
            key={i}
            d={`M${cx} ${cy - s} L${cx + s * 0.32} ${cy - s * 0.32} L${cx + s} ${cy} L${cx + s * 0.32} ${cy + s * 0.32} L${cx} ${cy + s} L${cx - s * 0.32} ${cy + s * 0.32} L${cx - s} ${cy} L${cx - s * 0.32} ${cy - s * 0.32} Z`}
            fill={color}
            stroke={LINE}
            strokeWidth={3}
            opacity={Math.sin(t * Math.PI)}
          />
        );
      })}
    </svg>
  );
};
