// 만화 이펙트 모음 — 병맛 타격감용 (2026-07-21)
//
// 🔴 전부 SVG + frame 계산. 투명 영상 소스(알파 채널)를 얹으면 무겁고 렌더가 느려진다.
// 🔴 CSS 애니메이션 금지 — 되감을 때 어긋난다.
import React from "react";
import { useCurrentFrame, interpolate, random, Easing } from "remotion";

const E = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };

// ── 집중선 — 분노·충격 순간 배경에 깔린다
export const ActionLines = ({ color = "#E5352B", opacity = 0.5, spin = 9 }) => {
  const f = useCurrentFrame();
  const rot = (f * spin) % 360;
  return (
    <svg viewBox="0 0 1080 1920" style={{ position: "absolute", inset: 0, opacity }}>
      <g style={{ transformBox: "view-box", transformOrigin: "540px 960px", rotate: `${rot}deg` }}>
        {Array.from({ length: 28 }).map((_, i) => (
          <line
            key={i}
            x1={540}
            y1={960}
            x2={540}
            y2={-900}
            stroke={color}
            strokeWidth={10 + (i % 4) * 9}
            // 🔴 가운데를 비워야 자막·캐릭터를 안 덮는다
            strokeDasharray="520 900"
            style={{ transformBox: "view-box", transformOrigin: "540px 960px", rotate: `${i * (360 / 28)}deg` }}
          />
        ))}
      </g>
    </svg>
  );
};

// ── 충격파 — 뭔가 쿵 떨어진 자리에서 원이 퍼진다
export const Impact = ({ at, x = "50%", y = "50%", color = "#111", size = 420 }) => {
  const f = useCurrentFrame();
  const k = interpolate(f, [at, at + 12], [0, 1], { ...E, easing: Easing.out(Easing.quad) });
  const op = interpolate(f, [at, at + 3, at + 12], [0, 0.7, 0], E);
  if (f < at || f > at + 14) return null;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      style={{ position: "absolute", left: x, top: y, translate: "-50% -50%", opacity: op }}
    >
      <ellipse cx={100} cy={100} rx={20 + k * 78} ry={8 + k * 30} fill="none" stroke={color} strokeWidth={9 - k * 6} />
    </svg>
  );
};

// ── 먼지 — 착지·충격 지점에서 퍽 하고 퍼진다
export const Dust = ({ at, x = "50%", y = "70%", n = 7, color = "#C9BFA8" }) => {
  const f = useCurrentFrame();
  if (f < at || f > at + 18) return null;
  return (
    <div style={{ position: "absolute", left: x, top: y }}>
      {Array.from({ length: n }).map((_, i) => {
        const a = (random(`d${i}`) - 0.5) * Math.PI * 1.4;
        const d = interpolate(f, [at, at + 16], [0, 90 + random(`e${i}`) * 90], { ...E, easing: Easing.out(Easing.quad) });
        const op = interpolate(f, [at, at + 3, at + 16], [0, 0.75, 0], E);
        const r = 10 + random(`r${i}`) * 16;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              width: r * 2,
              height: r * 2,
              borderRadius: "50%",
              background: color,
              opacity: op,
              translate: `${Math.cos(a) * d - r}px ${-Math.abs(Math.sin(a)) * d * 0.5 - r}px`,
            }}
          />
        );
      })}
    </div>
  );
};

// ── 땀방울 — 당황·난감할 때 머리 옆에 툭
export const Sweat = ({ at, x = "50%", y = "30%", flip = false }) => {
  const f = useCurrentFrame();
  if (f < at || f > at + 26) return null;
  const drop = interpolate(f, [at, at + 20], [0, 70], { ...E, easing: Easing.in(Easing.quad) });
  const op = interpolate(f, [at, at + 4, at + 20, at + 26], [0, 1, 1, 0], E);
  const sc = interpolate(f, [at, at + 6], [0.4, 1], E);
  return (
    <svg
      width={64}
      height={90}
      viewBox="0 0 60 84"
      style={{
        position: "absolute",
        left: x,
        top: y,
        opacity: op,
        translate: `${flip ? -20 : 20}px ${drop}px`,
        scale: sc,
      }}
    >
      <path
        d="M30 4 C44 30 54 44 54 56 a24 24 0 0 1 -48 0 C6 44 16 30 30 4 z"
        fill="#8FD3F4"
        stroke="#111"
        strokeWidth={6}
        strokeLinejoin="round"
      />
      <ellipse cx={22} cy={54} rx={7} ry={11} fill="#fff" opacity={0.8} />
    </svg>
  );
};

// ── 번개 — 충격 강조. 화면 위쪽에서 지직
export const Bolt = ({ at, x = "50%", y = "18%", color = "#FFD400", size = 150 }) => {
  const f = useCurrentFrame();
  if (f < at || f > at + 16) return null;
  // 🔴 깜빡여야 만화 같다. 켜졌다 꺼졌다를 반복
  const on = Math.floor((f - at) / 2) % 2 === 0;
  const op = on ? interpolate(f, [at, at + 14], [1, 0], E) : 0;
  return (
    <svg
      width={size}
      height={size * 1.6}
      viewBox="0 0 100 160"
      style={{ position: "absolute", left: x, top: y, opacity: op, translate: "-50% 0px" }}
    >
      <path
        d="M58 4 L18 84 h30 L34 156 L84 66 h-32 z"
        fill={color}
        stroke="#111"
        strokeWidth={7}
        strokeLinejoin="round"
      />
    </svg>
  );
};

// ── 도장 — 쾅 찍히고 튕긴다.
//  🔴 글씨만 얹으면 밋밋하다(2026-07-21). 크게 왔다가 스프링으로 튕겨야 "찍혔다"가 된다.
//     잉크 번짐은 테두리를 **일부러 삐뚤게** 그려서 낸다. 자로 잰 사각형은 도장처럼 안 보인다.
export const Stamp = ({ at = 0, text, color = "#E5352B", rot = -11, size = 92, fps = 30 }) => {
  const f = useCurrentFrame();
  if (f < at) return null;
  const k = f - at;
  // 하늘에서 큼직하게 내려와 쾅 — 살짝 작아졌다 제자리
  const sc = interpolate(k, [0, 5, 9, 14], [2.6, 0.88, 1.06, 1], { ...E, easing: Easing.out(Easing.quad) });
  const op = interpolate(k, [0, 4], [0, 1], E);
  // 찍힌 뒤 잔진동
  const wob = k > 5 ? Math.sin((k - 5) / 1.6) * Math.max(0, 4 - (k - 5) * 0.35) : 0;

  const padX = size * 0.55;
  const padY = size * 0.32;

  return (
    <div
      style={{
        position: "relative",
        display: "inline-block",
        rotate: `${rot + wob}deg`,
        scale: sc,
        opacity: op,
      }}
    >
      {/* 잉크 테두리 — 이중선(바깥 굵게, 안쪽 얇게)이라야 도장 같다 */}
      <svg
        viewBox="0 0 400 140"
        preserveAspectRatio="none"
        style={{ position: "absolute", inset: `-${padY}px -${padX}px`, width: `calc(100% + ${padX * 2}px)`, height: `calc(100% + ${padY * 2}px)` }}
      >
        <path
          d="M8 14 L392 6 L396 128 L6 134 Z"
          fill="none"
          stroke={color}
          strokeWidth={11}
          strokeLinejoin="round"
        />
        <path
          d="M22 28 L378 21 L381 114 L20 120 Z"
          fill="none"
          stroke={color}
          strokeWidth={5}
          strokeLinejoin="round"
        />
      </svg>
      <div
        style={{
          fontSize: size,
          color,
          letterSpacing: -3,
          padding: `${padY}px ${padX}px`,
          whiteSpace: "nowrap",
          lineHeight: 1.05,
        }}
      >
        {text}
      </div>
    </div>
  );
};

// ── 하트 — 맛있어서 자지러질 때 둥둥 떠오른다
//  🔴 별만으로는 밋밋했다(2026-07-21). 하트가 있어야 "맛있다"가 읽힌다.
export const Hearts = ({ at, x = "50%", y = "40%", n = 7, color = "#FF4D6D" }) => {
  const f = useCurrentFrame();
  if (f < at) return null;
  return (
    <div style={{ position: "absolute", left: x, top: y }}>
      {Array.from({ length: n }).map((_, i) => {
        const born = at + i * 5;
        if (f < born) return null;
        const k = f - born;
        const life = 40;
        // 위로 떠오르며 좌우로 살랑
        const up = interpolate(k, [0, life], [0, -300], { ...E, easing: Easing.out(Easing.quad) });
        const sway = Math.sin(k / 7 + i) * (28 + random(`w${i}`) * 22);
        const op = interpolate(k, [0, 6, life * 0.7, life], [0, 1, 1, 0], E);
        const sc = interpolate(k, [0, 8], [0.2, 0.7 + random(`s${i}`) * 0.7], E);
        const rot = Math.sin(k / 9 + i) * 18;
        const dx = (random(`x${i}`) - 0.5) * 240;
        return (
          <svg
            key={i}
            width={110}
            height={100}
            viewBox="0 0 100 90"
            style={{
              position: "absolute",
              translate: `${dx + sway - 55}px ${up}px`,
              opacity: op,
              scale: sc,
              rotate: `${rot}deg`,
            }}
          >
            <path
              d="M50 84 C14 56 6 36 16 22 C26 8 44 12 50 26 C56 12 74 8 84 22 C94 36 86 56 50 84 z"
              fill={color}
              stroke="#111"
              strokeWidth={6}
              strokeLinejoin="round"
            />
            <ellipse cx={34} cy={32} rx={8} ry={5} fill="#fff" opacity={0.75} style={{ rotate: "-28deg" }} />
          </svg>
        );
      })}
    </div>
  );
};

// ── 배경 — 장면마다 색이 바뀌고, 그 위에 연한 패턴이 깔린다
//  🔴 크림색 단색은 칙칙하다(2026-07-21). 장면별로 색이 확 바뀌면 전환이 눈에 들어오고
//     리듬도 생긴다. 패턴은 **아주 연하게** — 진하면 굵은 선 캐릭터와 싸운다.
export const Backdrop = ({ color, tint = "#000", opacity = 0.05, drift = true }) => {
  const f = useCurrentFrame();
  // 천천히 흐르면 살아 있는 느낌이 난다
  const dx = drift ? (f * 0.35) % 180 : 0;
  const dy = drift ? (f * 0.2) % 180 : 0;
  return (
    <AbsoluteFillLike color={color}>
      <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity }}>
        <defs>
          <pattern id={`p-${color.replace("#", "")}`} width={180} height={180} patternUnits="userSpaceOnUse"
                   patternTransform={`translate(${dx} ${dy})`}>
            {/* 동전 */}
            <circle cx={40} cy={40} r={17} fill="none" stroke={tint} strokeWidth={6} />
            <text x={40} y={49} textAnchor="middle" fontSize={22} fill={tint} fontWeight="900">₩</text>
            {/* 닭다리 실루엣 */}
            <path d="M120 34 c14 0 24 10 24 22 c0 10 -8 18 -18 20 l-8 16 l-8 -16 c-10 -2 -18 -10 -18 -20 c0 -12 10 -22 24 -22 z"
                  fill={tint} />
            {/* 점 */}
            <circle cx={150} cy={130} r={7} fill={tint} />
            <circle cx={60} cy={140} r={5} fill={tint} />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill={`url(#p-${color.replace("#", "")})`} />
      </svg>
    </AbsoluteFillLike>
  );
};

const AbsoluteFillLike = ({ color, children }) => (
  <div style={{ position: "absolute", inset: 0, background: color, overflow: "hidden" }}>{children}</div>
);

// ── 화면 흔들기 래퍼 — 감싸면 안의 모든 게 같이 떨린다
export const Shake = ({ children, on = false, power = 20 }) => {
  const f = useCurrentFrame();
  if (!on) return <>{children}</>;
  const x = (random(`sx${f}`) - 0.5) * power * 2;
  const y = (random(`sy${f}`) - 0.5) * power * 2;
  const r = (random(`sr${f}`) - 0.5) * (power / 8);
  return <div style={{ translate: `${x}px ${y}px`, rotate: `${r}deg` }}>{children}</div>;
};
