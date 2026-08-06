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

// ── 머리 모양 (2026-07-21 추가) ──────────────────────────────
// 🔴 민머리라 나마(양갈래)와 나란히 두면 올마만 허전했다.
// 🔴 앞머리가 눈썹을 덮으면 표정이 죽는다. 이마 **위쪽만** 덮는다.
export const OLMA_HAIR = "#4A3A2A"; // 나마보다 살짝 어두운 갈색

// 🔴 머리카락 3안(스포츠·가르마·삐죽)은 전부 "얼굴 위에 얹은 판때기"로 보여 버렸다(2026-07-21).
//    머리를 얼굴 원 **안쪽에** 덮는 도형으로 그린 게 원인이다.
//    → 캡모자로 간다. 원래 얼굴 밖으로 나오는 물건이라 얹혀 보이는 문제가 없다.
export const CAP = { crown: "#1B6BD6", brim: "#12468F" }; // 올마 파란 몸과 맞춘 색

// 🔴 머리카락은 **얼굴 원(cx200 cy163 r98) 바깥으로 나와야** 자연스럽다(2026-07-21).
//    안쪽에 덮는 도형으로 그렸더니 전부 "얹은 판때기"로 보였다.
//    나마 양갈래가 자연스러운 것도 뒷머리가 얼굴 밖으로 퍼지기 때문이다.
const HairStrands = ({ part }) => {
  if (part === "back") return null; // 짧은 머리라 뒷머리는 따로 없다
  return (
    <g>
      {/* 정수리 덩어리 — 얼굴 위로 살짝 부풀어 나온다.
          🔴 얼굴(r98)에 비해 조금 작아 보여 아주 살짝만 키웠다(2026-07-21). 좌우 ±6, 위 -6. */}
      <path
        d="M106 134 q-4 -82 94 -82 q98 0 94 82 q-15 -36 -49 -47 q-13 17 -36 17 q-26 0 -43 -15 q-40 13 -60 45 z"
        fill={OLMA_HAIR}
        stroke={OLMA.line}
        strokeWidth={OLMA.lw}
        strokeLinejoin="round"
      />
      {/* 삐친 가닥 — 정수리에서 한 가닥. 얼굴 밖으로 뻗어 실루엣을 만든다 */}
      <path
        d="M206 62 q14 -34 42 -40 q-18 16 -20 34 q16 -8 30 -2 q-24 8 -34 24 z"
        fill={OLMA_HAIR}
        stroke={OLMA.line}
        strokeWidth={6}
        strokeLinejoin="round"
      />
      {/* 🔴 옆 가닥은 뺐다(2026-07-21 지시). 귀 위 삐침이 지저분해 보였다.
             정수리 한 가닥만으로 실루엣은 충분하다. */}
    </g>
  );
};

const Hair = ({ hair, part }) => {
  if (hair === "hair") return <HairStrands part={part} />;
  if (hair !== "cap") return null; // 안 주면 민머리
  if (part === "back") return null; // 모자는 앞에서 한 번에 그린다
  return (
    <g>
      {/* 🔴 챙 위치가 두 번 어긋났다(2026-07-21).
             1차 — 통에서 떨어져 딴 물건처럼 떴다
             2차 — 너무 내려서 **눈썹·눈을 가렸다**
          기준: 눈썹이 y≈118, 눈이 y≈150. 챙은 y 96~118 안에서 끝나야 한다.
          통 아래선(y≈100)에 물리고 왼쪽으로 짧게 뻗는다. */}
      {/* 챙 — 위로 살짝 들려 있다. 눈썹(y≈118)보다 확실히 위에서 끝난다 */}
      <path
        d="M116 106 q-52 -12 -76 -30 q-12 -9 -1 -15 q13 -7 44 8 q31 15 47 27 z"
        fill={CAP.brim}
        stroke={OLMA.line}
        strokeWidth={OLMA.lw}
        strokeLinejoin="round"
      />
      {/* 모자 통 — 🔴 키웠다(2026-07-21). 얼굴(r98)에 비해 작아서 빈약했다 */}
      <path
        d="M96 110 q4 -92 104 -92 q100 0 104 92 q-50 -22 -104 -22 q-54 0 -104 22 z"
        fill={CAP.crown}
        stroke={OLMA.line}
        strokeWidth={OLMA.lw}
        strokeLinejoin="round"
      />
      {/* 봉제선 + 꼭지 단추 */}
      <path d="M200 20 v62" stroke={OLMA.line} strokeWidth={5} opacity={0.5} />
      <circle cx={200} cy={20} r={10} fill={CAP.brim} stroke={OLMA.line} strokeWidth={5} />
    </g>
  );
};

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
      {/* 손 — 🔴 그냥 타원이면 "손"으로 안 읽힌다(2026-07-21 "퀄리티 떨어져").
          엄지 돌기를 붙이고 안쪽에 밝은 면을 넣어 부피감을 준다. */}
      <ellipse cx={hx} cy={hy} rx={16} ry={20} fill={OLMA.body} stroke={OLMA.line} strokeWidth={OLMA.lw} />
      <ellipse cx={hx - d * 12} cy={hy - 6} rx={7} ry={10} fill={OLMA.body} stroke={OLMA.line} strokeWidth={5} />
      <ellipse cx={hx - d * 3} cy={hy - 7} rx={6} ry={7} fill="#fff" opacity={0.45} />
    </g>
  );
};

// 다리 — 걸을 때 어깨(엉덩이)를 축으로 흔든다
//
// 🔴 발이 두 개 붙어 있어 한 덩어리로 보였다(2026-07-21 "발이 붙어 있는데 손처럼 만들어").
//    손과 같은 방식 — 바깥쪽으로 벌리고, 안쪽에 밝은 면을 넣어 부피를 준다.
const Leg = ({ x, deg, side = 1 }) => (
  <g
    style={{
      transformBox: "view-box",
      transformOrigin: `${x}px 400px`,
      rotate: `${deg}deg`,
    }}
  >
    <path d={`M${x} 400 v96`} stroke={OLMA.line} strokeWidth={OLMA.lw} strokeLinecap="round" />
    {/* 발 — 손처럼 둥근 덩어리. 앞코가 바깥을 향해 벌어진다 */}
    <ellipse
      cx={x + side * 9}
      cy={506}
      rx={26}
      ry={17}
      fill={OLMA.body}
      stroke={OLMA.line}
      strokeWidth={OLMA.lw}
      style={{ transformBox: "view-box", transformOrigin: `${x}px 506px`, rotate: `${side * 12}deg` }}
    />
    <ellipse cx={x + side * 6} cy={500} rx={11} ry={6} fill="#fff" opacity={0.42} />
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
  hair = "hair", // 2026-07-21 확정: 머리카락. (hair | cap | null)
  // 🔴 몸통 없이 **머리만** (2026-07-22 지시). 폴란드볼식 구성.
  //    몸·팔·다리가 없어지므로 pose/walk/hold* 는 전부 무시된다.
  //    소품을 들려야 하면 캐릭터 옆에 따로 띄워라(팔이 없으니 쥘 수 없다).
  headOnly = false,
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
      viewBox={headOnly ? "40 20 320 320" : "-90 -60 580 680"}
      width={(headOnly ? 320 : 580) * scale}
      height={(headOnly ? 320 : 680) * scale}
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
        {/* 바닥 그림자 — 🔴 이게 없으면 캐릭터가 공중에 떠 보인다(2026-07-21).
            다리보다 먼저 그려 뒤로 보낸다. 뛸수록(bounce) 작아진다. */}
        {!headOnly && (
          <>
            <ellipse
              cx={200}
              cy={508}
              rx={78 - Math.min(Math.abs(bounce), 20) * 1.2}
              ry={13}
              fill="#000"
              opacity={0.13}
            />

            {/* 다리 — 걸을 때 서로 반대로 흔들린다 */}
            <Leg x={184} deg={Math.sin(phase) * 30 * walk} side={-1} />
            <Leg x={216} deg={-Math.sin(phase) * 30 * walk} side={1} />
          </>
        )}

        {/* 🔴 몸통 위쪽(머리·팔)은 골반을 축으로 같이 기운다.
            몸 전체를 돌리는 tilt와 달리 상체만 움직여서 훨씬 사람처럼 보인다(2026-07-21). */}
        <g style={{ transformBox: "view-box", transformOrigin: "200px 400px", rotate: `${lean}deg` }}>
        {!headOnly && (
          <>
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
            {/* 몸통 하이라이트 — 왼쪽 위에 밝은 면. 납작한 사각형이 입체로 보인다 */}
            <path d="M166 268 q10 -8 22 -6 v112 q-14 4 -22 -4 z" fill="#fff" opacity={0.32} />

            {/* 🔴 가슴에 O — 올마나마의 O(2026-07-21 지시). 옷 마크라서 캐릭터 정체성이 생긴다.
                글꼴에 기대면 렌더 환경마다 달라지므로 **원 두 개**로 그린다. */}
            <circle cx={200} cy={330} r={26} fill="none" stroke={OLMA.line} strokeWidth={9} />
          </>
        )}

        {/* 머리 — 🔴 목(y=252)을 축으로 따로 까닥인다. 이게 있어야 살아 있는 것처럼 보인다 */}
        <g style={{ transformBox: "view-box", transformOrigin: "200px 252px", rotate: `${head}deg` }}>
          {/* 뒷머리 — 얼굴보다 먼저 그려 뒤로 보낸다 */}
          <Hair hair={hair} part="back" />

          {/* 얼굴 — 극대노에선 붉게 달아오른다 */}
          <circle
            cx={200}
            cy={163}
            r={98}
            fill={isRed ? "#FF8A7A" : OLMA.head}
            stroke={OLMA.line}
            strokeWidth={OLMA.lw}
          />

          {/* 🔴 아래 세 가지가 "만화 캐릭터"와 "동그라미"를 가른다(2026-07-21 "퀄리티 떨어져").
              ① 광택 — 머리 왼쪽 위 반사
              ② 볼터치 — 표정이 살아난다. 화나면 더 붉어진다
              ③ 눈썹 — 눈만 있으면 감정 폭이 좁다. 갸웃·놀람·화남이 눈썹에서 갈린다 */}
          {/* 앞머리 — 얼굴 위. 눈썹은 안 가린다 */}
          <Hair hair={hair} part="front" />

          {/* 🔴 머리 광택은 뺐다(2026-07-21). 안쪽으로 옮겨도 "머리에 뭘 얹은 것"으로 보였고,
              굵은 검은 선 + 단색 스타일에 반사광은 안 어울린다. */}
          <ellipse cx={140} cy={196} rx={20} ry={12} fill="#FF8A7A" opacity={isRed ? 0.75 : 0.42} />
          <ellipse cx={260} cy={196} rx={20} ry={12} fill="#FF8A7A" opacity={isRed ? 0.75 : 0.42} />

          {/* 눈썹 — 감정별로 각도가 다르다 */}
          {!isBliss && (
            <>
              <path
                d={isAngry ? "M142 116 l44 20" : bigEye ? "M144 112 q22 -12 44 -2" : "M146 118 q22 -8 42 -2"}
                fill="none"
                stroke={OLMA.line}
                strokeWidth={9}
                strokeLinecap="round"
              />
              <path
                d={isAngry ? "M258 116 l-44 20" : bigEye ? "M256 112 q-22 -12 -44 -2" : "M254 118 q-22 -8 -42 -2"}
                fill="none"
                stroke={OLMA.line}
                strokeWidth={9}
                strokeLinecap="round"
              />
            </>
          )}

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
              {/* 눈동자 + 하이라이트 점 — 점 하나로 눈에 생기가 돈다 */}
              <ellipse cx={168} cy={150} rx={bigEye ? 15 : 11} ry={bigEye ? 15 : 11} fill={OLMA.line} />
              <ellipse cx={232} cy={150} rx={bigEye ? 15 : 11} ry={bigEye ? 15 : 11} fill={OLMA.line} />
              <circle cx={172} cy={145} r={bigEye ? 5 : 3.6} fill="#fff" />
              <circle cx={236} cy={145} r={bigEye ? 5 : 3.6} fill="#fff" />
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
        {!headOnly && (
          <>
            <Arm side="L" deg={L} hold={holdL} />
            <Arm side="R" deg={R} hold={holdR} />
          </>
        )}
        </g>
      </g>
    </svg>
  );
};
