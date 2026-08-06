// 올마 캐릭터 — Remotion판 (2026-07-21)
//
// 기존 olma.js를 그대로 옮겼다. 다른 점은 딱 하나:
//   예전:  setPose(el,"만세")  → DOM을 건드려 바꿈 → 되감으면 상태가 안 맞아 화면이 깨짐
//   지금:  <Olma pose="만세"/> → 받은 값대로 그릴 뿐 → '되감기'라는 개념 자체가 없음
//
// 🔴 팔은 몸통 **뒤에** 그리면 들어올릴 때 몸에 가려 사라진다(2026-07-21 렌더에서 발견).
//    반드시 torso 다음에 그린다.
// 🔴 CSS transition 금지 — 렌더에서 프레임이 어긋난다. 움직임은 전부 프레임 계산으로.
import React from "react";

export const OLMA = { head: "#F7EFA8", body: "#A9D3EF", line: "#000", lw: 7 };

// 팔 각도 (어깨 기준 회전)
export const POSES = {
  기본: { L: 0, R: 0 },
  가리킴: { L: 6, R: -95 },
  가리킴위: { L: 6, R: -100 },
  으쓱: { L: 38, R: -38 },
  // 🔴 150도로 세우면 팔이 짧아 손이 머리 옆에 딱 붙어 귀마개처럼 보인다(2026-07-21).
  //    125도로 벌려야 머리를 비껴 V자 만세가 된다.
  만세: { L: 125, R: -125 },
  깜짝: { L: 60, R: -60 },
  털썩: { L: 110, R: -110 },
  뒷목: { L: -140, R: -150 },
  // 🔴 손을 입가로 가져가는 자세 — 치킨 뜯어먹는 장면용(2026-07-21)
  먹기: { L: 8, R: -132 },
};

export const MOUTHS = {
  무표정: "M180 196 h40",
  놀람: "M200 196 m-12 0 a12 12 0 1 0 24 0 a12 12 0 1 0 -24 0",
  갸웃: "M182 196 q9 -7 18 0 t18 0",
  씩: "M180 190 q20 18 40 0",
  헉: "M200 200 m-22 0 a22 26 0 1 0 44 0 a22 26 0 1 0 -44 0",
  삐뚤: "M176 198 q22 -14 44 4",
  일자: "M186 196 h28",
  // 🔴 웃기려면 표정이 더 필요하다(2026-07-21 "하나도 안 웃겨")
  절규: "M200 202 m-30 0 a30 34 0 1 0 60 0 a30 34 0 1 0 -60 0", // 입 쩍 벌리고 소리침
  황홀: "M178 188 q22 26 44 0", // 만족스러운 미소 (먹을 때)
  침: "M178 192 q22 20 44 0", // 씩 + 아래로 침
  화남: "M178 204 q22 -16 44 0", // 입꼬리가 처진 거꾸로 U자
  극대노: "M170 190 q30 -14 60 0 l-14 30 h-32 z", // 화나서 크게 벌린 입
};

// 🔴 화난 표정은 **눈이 바뀌어야** 산다. 입만 바꾸면 안 화나 보인다(2026-07-21).
const ANGRY_FACES = ["화남", "절규", "극대노"];
const RED_FACES = ["극대노"]; // 얼굴까지 붉게 달아오르는 단계

const Arm = ({ side, deg, hold }) => {
  const x = side === "L" ? 152 : 248;
  const d = side === "L" ? -1 : 1;
  const hx = x + d * 15, hy = 374; // 손 중심
  return (
    <g
      style={{
        // 🔴 transform-box를 view-box로 고정해야 브라우저마다 회전 원점이 안 어긋난다
        transformBox: "view-box",
        transformOrigin: `${x}px 268px`,
        rotate: `${deg}deg`,
      }}
    >
      <path
        d={`M${x} 268 q${d * 22} 55 ${d * 14} 96`}
        fill="none"
        stroke={OLMA.line}
        strokeWidth={OLMA.lw}
        strokeLinecap="round"
      />
      {/* 🔴 손에 쥔 물건은 **팔 안에** 그린다(2026-07-21 "포크 에러가 많다").
          밖에서 좌표로 맞추면 팔이 회전할 때마다 어긋난다. 여기 두면 항상 손에 붙어 있다.
          🔴 다만 팔 회전을 그대로 받으면 포크가 뒤집힌다 → **손목처럼 역회전으로 상쇄**한다.
             완전 상쇄(-deg)면 뻣뻣하니 0.8만 상쇄해 손목이 살짝 꺾인 느낌을 남긴다. */}
      {hold && (
        <g style={{ transformBox: "view-box", transformOrigin: `${hx}px ${hy}px`, rotate: `${-deg * 0.8}deg` }}>
          {hold(hx, hy)}
        </g>
      )}
      <ellipse
        cx={hx}
        cy={hy}
        rx={15}
        ry={19}
        fill={OLMA.body}
        stroke={OLMA.line}
        strokeWidth={OLMA.lw}
      />
    </g>
  );
};

// 다리 — 걸을 때 어깨(엉덩이)를 축으로 흔든다
const Leg = ({ x, deg }) => (
  <g
    style={{
      transformBox: "view-box",
      transformOrigin: `${x}px 400px`,
      rotate: `${deg}deg`,
    }}
  >
    <path d={`M${x} 400 v100`} stroke={OLMA.line} strokeWidth={OLMA.lw} strokeLinecap="round" />
    <path
      d={`M${x - 14} 500 a20 14 0 0 1 28 0 z`}
      fill={OLMA.body}
      stroke={OLMA.line}
      strokeWidth={OLMA.lw}
      strokeLinejoin="round"
    />
  </g>
);

export const Olma = ({
  face = "무표정",
  pose = "기본",
  scale = 1,
  tilt = 0, // 고개 갸웃 (deg)
  bounce = 0, // 통통 뛰기 (px)
  armL = null, // 포즈 대신 각도를 직접 줄 때 (전환 중간값)
  armR = null,
  walk = 0, // 걷기 세기 0=서 있음, 1=걷는 중
  phase = 0, // 걸음 위상 (프레임에서 계산해 넣는다)
  head = 0, // 🔴 머리만 따로 까닥 (목 기준 회전). 몸 전체를 돌리는 tilt와 다르다
  lean = 0, // 몸통만 기울이기 (골반 기준)
  holdR = null, // 오른손에 쥔 물건 — (hx,hy) => JSX. 팔과 같이 회전하므로 안 어긋난다
  holdL = null,
  chew = 0, // 🔴 입이 우물거리는 위상. 0이면 안 씹는다
  style = {},
}) => {
  const p = POSES[pose] || POSES["기본"];
  // 걸을 때는 팔도 다리 반대로 흔든다
  const swing = Math.sin(phase) * 26 * walk;
  const L = armL === null ? p.L + swing : armL;
  const R = armR === null ? p.R + swing : armR;
  const mouth = MOUTHS[face] || MOUTHS["무표정"];
  const bigEye = face === "놀람" || face === "헉";
  const isAngry = ANGRY_FACES.includes(face);
  const isRed = RED_FACES.includes(face);
  // 🔴 맛있게 먹을 때는 **눈을 감아야** 산다(2026-07-21). 포크를 정교하게 움직이는 것보다
  //    눈·입 연기가 훨씬 잘 읽힌다.
  const isBliss = face === "황홀" || face === "감음";

  return (
    // 🔴 viewBox를 0 0 400 560으로 두면 만세·놀람처럼 **팔을 든 포즈에서 손이 잘린다**
    //    (2026-07-21 인트로에서 발견). 사방에 여유를 줘서 어떤 포즈든 안 잘리게 한다.
    <svg
      viewBox="-90 -60 580 680"
      width={580 * scale}
      height={680 * scale}
      xmlns="http://www.w3.org/2000/svg"
      style={{ overflow: "visible", ...style }}
    >
      <g
        style={{
          transformBox: "view-box",
          transformOrigin: "200px 500px",
          translate: `0px ${bounce}px`,
          rotate: `${tilt}deg`,
        }}
      >
        {/* 다리 — 걸을 때 서로 반대로 흔들린다 */}
        <Leg x={186} deg={Math.sin(phase) * 30 * walk} />
        <Leg x={214} deg={-Math.sin(phase) * 30 * walk} />

        {/* 🔴 몸통 위쪽(머리·팔)은 골반을 축으로 같이 기운다.
            몸 전체를 돌리는 tilt와 달리 상체만 움직여서 훨씬 사람처럼 보인다(2026-07-21). */}
        <g style={{ transformBox: "view-box", transformOrigin: "200px 400px", rotate: `${lean}deg` }}>
        {/* 몸통 */}
        <rect
          x={152}
          y={252}
          width={96}
          height={150}
          rx={26}
          fill={OLMA.body}
          stroke={OLMA.line}
          strokeWidth={OLMA.lw}
        />

        {/* 머리 — 🔴 목(y=252)을 축으로 따로 까닥인다. 이게 있어야 살아 있는 것처럼 보인다 */}
        <g style={{ transformBox: "view-box", transformOrigin: "200px 252px", rotate: `${head}deg` }}>
          {/* 얼굴 — 극대노에선 붉게 달아오른다 */}
          <circle
            cx={200}
            cy={163}
            r={98}
            fill={isRed ? "#FF8A7A" : OLMA.head}
            stroke={OLMA.line}
            strokeWidth={OLMA.lw}
          />

          {/* 눈 — 화나면 치켜뜬 도끼눈 */}
          {isBliss ? (
            // 감은 눈 — 만족스러운 ∪자 (^^)
            <>
              <path d="M148 152 q20 -22 40 0" fill="none" stroke={OLMA.line} strokeWidth={8} strokeLinecap="round" />
              <path d="M212 152 q20 -22 40 0" fill="none" stroke={OLMA.line} strokeWidth={8} strokeLinecap="round" />
            </>
          ) : isAngry ? (
            <>
              <path d="M146 138 l38 16 l-20 14 z" fill={OLMA.line} strokeLinejoin="round" />
              <path d="M254 138 l-38 16 l20 14 z" fill={OLMA.line} strokeLinejoin="round" />
            </>
          ) : (
            <>
              <ellipse cx={168} cy={150} rx={bigEye ? 13 : 9} ry={bigEye ? 13 : 9} fill={OLMA.line} />
              <ellipse cx={232} cy={150} rx={bigEye ? 13 : 9} ry={bigEye ? 13 : 9} fill={OLMA.line} />
            </>
          )}

          {/* 입 — 크게 벌린 입은 안쪽을 채워야 구멍처럼 보인다.
              🔴 chew를 주면 입이 세로로 우물거린다(씹는 연기) */}
          <path
            style={
              chew
                ? { transformBox: "view-box", transformOrigin: "200px 196px", scale: `1 ${1 + Math.sin(chew) * 0.45}` }
                : undefined
            }
            d={mouth}
            fill={face === "극대노" || face === "절규" || face === "헉" || face === "놀람" ? "#fff" : "none"}
            stroke={OLMA.line}
            strokeWidth={6}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>

        {/* 🔴 팔은 **맨 마지막**에 그린다.
            몸통 뒤에 그리면 들어올릴 때 몸에 가리고,
            머리 뒤에 그리면 만세·놀람에서 손이 머리 원 안으로 들어가 사라진다
            (2026-07-21 인트로에서 "팔이 다 짤린다"로 확인).
            팔을 내렸을 때는 머리보다 아래라 겹치지 않으므로 맨 위에 그려도 문제없다. */}
        <Arm side="L" deg={L} hold={holdL} />
        <Arm side="R" deg={R} hold={holdR} />
        </g>
      </g>
    </svg>
  );
};
