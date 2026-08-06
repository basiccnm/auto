// 브랜드볼 — 편마다 바뀌는 세 번째 캐릭터 (2026-07-22)
//
// 🔴 왜 만들었나: 폴란드볼은 **국기**가 있어서 원 하나로 캐릭터가 성립한다.
//    우리 올마·나마는 머리 모양이 그 역할을 하므로 국기가 필요 없다.
//    대신 "국기 자리"에 해당하는 건 **편마다 바뀌는 브랜드**다.
//    나마가 혼자 하던 반박을, 변명하는 브랜드에게 받아치게 하면 대비가 하나 더 생긴다.
//
// 🔴 로고 도안은 쓰지 않는다. **색 + 이름**까지가 안전선이다.
//    띠(band)는 국기 줄무늬 자리를 대신하는 장치일 뿐 로고가 아니다.
//
// 🔴 선 굵기·검정색은 Olma/Nama와 같은 값을 쓴다. 따로 놀면 다른 그림에서 오려 붙인 것처럼 보인다.
import React from "react";
// 🔴 띠 글자는 맑은고딕이라 각졌다(2026-07-22). 둥근 Jua로 바꿔 그림체와 결을 맞춘다.
import { BLACK, JUA } from "../shorts/fonts";

// 🔴 구분법(2026-07-22 확정): 캐릭터마다 장치가 하나씩이다.
//    올마 = 아무것도 없음(로고 그대로) / 소비자·본사 = 볼 가운데 글자 인쇄
//    사장님 = 요리사 빵모자에 "사장님" 글자 (2026-07-22 지시 — 앞치마는 뺐고, 볼 몸엔 안 쓴다)

export const BRANDS = {
  // 🔴 올마는 **채널 로고 그 자체**다(2026-07-22). 띠도 마크도 붙이지 않는다.
  //    로고에 뭘 더하는 순간 로고가 아니게 된다. 아무것도 없는 게 정체성이다.
  // 🔴 눈동자는 검정이 아니라 짙은 갈색이다(2026-07-22 지시). 검정 테두리와 겹쳐 딱딱해 보였다.
  // 🔴 2026-07-25 **색 스왑** — 올마=여자(진행자)=핑크 / 나마=남자(사장님)=노랑.
  //    전엔 올마가 노랑이었는데 목소리를 여성으로 바꾸면서 역할이 뒤집혔다.
  //    코드 키(올마·사장님)는 그대로 둔다 — 기존 lines_*.js 의 who 를 안 건드려도 되게.
  올마: { body: "#F5A9C0", band: null, pupil: "#2B1C10" },
  // ── 돈 내는 쪽
  // 🔴 모자는 두 번 그려도 계속 겹쳐 보여서 버렸다(2026-07-22 "차라리 교촌처럼").
  // 🔴 가운데 인쇄는 입과 겹쳤다 — 소비자는 **이마에 조그맣게** 쓴다(2026-07-22 지시).
  소비자: { body: "#F2A65A", logo: "소비자", logoColor: "#FFFFFF", forehead: true },
  // ── 만드는 쪽 — 🔴 앞치마는 뺐다(2026-07-22 마라탕 편 지시).
  //    대신 **요리사 빵모자에 "사장님" 글자**를 쓴다. 볼 몸엔 아무것도 안 쓴다.
  // 🔴 목소리가 여성이라 볼 색은 핑크 유지.
  //    나마(사장님) — 노랑. 살구 배경에서 안 묻히게 채도를 조금 올렸다
  사장님: { body: "#F5DE7A", hat: true, hatLabel: "사장님", pupil: "#2B1C10" },
  // ── 본사 — 검정 볼 + 흰 로고만. 넥타이는 달아봤다가 뺐다(2026-07-22 "너무 내려옴, 삭제").
  //    🔴 검정 볼엔 검정 눈썹·입이 안 보인다. ink로 밝은 선을 따로 준다.
  교촌: { body: "#1C1C1C", logo: "KYOCHON", logoColor: "#FFFFFF", ink: "#EDEDED" },
  비비큐: { body: "#E5352B", band: "#FFD400", label: "BBQ", labelColor: "#7A1410" },
  비에이치씨: { body: "#F26522", band: "#111111", label: "bhc", labelColor: "#fff" },
};

// 머리 — 🔴 원 **바깥으로** 나와야 자연스럽다. 안쪽에 덮으면 얹은 판때기로 보인다(Olma.jsx와 같은 교훈).
const HAIR = "#4A3A2A";
const Hair = ({ kind }) => {
  if (kind === "tuft")
    return <path d="M196 52 q-6 -44 26 -50 q-16 20 -4 46 z" fill={HAIR} stroke={LINE} strokeWidth={7} strokeLinejoin="round" />;
  if (kind === "twin")
    // 🔴 눈높이에 붙이면 귀마개로 보인다(2026-07-22). 아래로 내리고 길게 뽑는다.
    return (
      <g>
        <ellipse cx="44" cy="286" rx="36" ry="66" fill={HAIR} stroke={LINE} strokeWidth={8} transform="rotate(-20 44 286)" />
        <ellipse cx="356" cy="286" rx="36" ry="66" fill={HAIR} stroke={LINE} strokeWidth={8} transform="rotate(20 356 286)" />
      </g>
    );
  return null;
};

// ── 붙였다 뗐다 하는 것들 (2026-07-22) ──────────────────────
// 🔴 **기본값은 전부 꺼짐이다.** 한 캐릭터에 두 개 이상 켜지 말 것.
//    왕관+돈다발+금반지를 한꺼번에 붙이면 3편에서 겪은 그 조잡함이 그대로 재현된다.
//    그 장면이 무슨 말을 하려는지에 맞는 **하나만** 켠다.
// 👁 속눈썹 — **눈 위에만** 단다(2026-07-25 지시. 아래는 안 단다).
//    눈 흰자는 cx 140·260 / cy 182 / rx 42 ry 50 이다. 그 위쪽 곡선을 따라 3가닥씩.
const Lashes = ({ ink = "#111" }) => (
  <g fill={ink} stroke="none">
    {[140, 260].map((cx) => (
      <g key={cx}>
        {/* 🔴 다섯 번 고쳤다(2026-07-25) — ①직선 ②뾰족 ③떠있음 ④눈축소 반영 ⑤**더 짧게**.
            흰자(rx36 ry43, 위 테두리 y=139)에 붙여 아주 짧게 얹는다 */}
        <path d={`M${cx - 26} 150 q-5 -4 -10 -8 q2 3 3 5 q3 4 7 6 z`} />
        <path d={`M${cx - 10} 142 q-3 -4 -5 -10 q0 3 1 6 q1 4 4 6 z`} />
        <path d={`M${cx + 6} 141 q2 -4 5 -10 q0 3 -1 6 q-1 4 -4 6 z`} />
        <path d={`M${cx + 22} 148 q6 -4 11 -8 q-2 3 -4 5 q-3 4 -7 5 z`} />
      </g>
    ))}
  </g>
);

// 🎀 머리핀 — 올마가 여자라는 걸 한눈에(2026-07-25 지시).
//    볼 왼쪽 위에 비스듬히. 모자(나마)와 자리가 안 겹치게 왼쪽으로 뺀다.
// 🔴 핀은 볼 **안쪽**으로 넣는다(2026-07-25 지시) — 절반쯤만 테두리 밖으로 나가게.
//    볼은 cx200 cy200 r155 라 왼쪽 위 테두리가 대략 (90,90) 근처다.
const HairPin = ({ color = "#FF6B8A" }) => (
  <g transform="translate(100,56) rotate(-18) scale(0.92)">
    {/* 리본 왼쪽·오른쪽 날개 */}
    <path d="M0 26 q-34 -30 -46 -2 q-10 26 20 30 q18 2 26 -14 z" fill={color} stroke={LINE} strokeWidth={7} strokeLinejoin="round" />
    <path d="M8 26 q34 -30 46 -2 q10 26 -20 30 q-18 2 -26 -14 z" fill={color} stroke={LINE} strokeWidth={7} strokeLinejoin="round" />
    {/* 가운데 매듭 */}
    <circle cx="4" cy="30" r="13" fill={color} stroke={LINE} strokeWidth={7} />
  </g>
);

const Crown = () => (
  <g>
    <path
      d="M92 62 l30 -74 l38 46 l40 -70 l40 70 l38 -46 l30 74 z"
      fill="#FFC42E"
      stroke={LINE}
      strokeWidth={9}
      strokeLinejoin="round"
    />
    <circle cx="122" cy="-4" r="11" fill="#E4002B" stroke={LINE} strokeWidth={6} />
    <circle cx="278" cy="-4" r="11" fill="#E4002B" stroke={LINE} strokeWidth={6} />
  </g>
);

// 🔴 사장님은 빵모자 **위에 "사장님" 글자**를 쓴다(2026-07-22 지시). 볼 몸엔 안 쓴다.
// 🔴 모자를 조금 낮췄다(2026-07-22 지시) — 전체를 아래로 18 이동.
const ChefHat = ({ label }) => (
  <g transform="translate(0, 18)">
    <path
      d="M96 66 q-42 -6 -42 -50 q0 -40 44 -40 q6 -34 52 -34 q28 -30 62 0 q46 0 50 34 q44 0 44 40 q0 44 -42 50 z"
      fill="#FDFDFD"
      stroke={LINE}
      strokeWidth={9}
      strokeLinejoin="round"
    />
    <rect x="92" y="58" width="216" height="30" rx="10" fill="#E9E9E9" stroke={LINE} strokeWidth={8} />
    {label && (
      <text x="200" y="42" textAnchor="middle" fontSize="58" fontFamily={JUA} fill={LINE}>
        {label}
      </text>
    )}
  </g>
);

// 반짝이는 안경 — 나마 전용. 눈 위에 그대로 얹는다
const Specs = () => (
  <g>
    <circle cx="140" cy="182" r="58" fill="#DFF3FF" opacity={0.55} stroke={LINE} strokeWidth={8} />
    <circle cx="260" cy="182" r="58" fill="#DFF3FF" opacity={0.55} stroke={LINE} strokeWidth={8} />
    <path d="M198 180 h4" stroke={LINE} strokeWidth={9} strokeLinecap="round" />
    <path d="M82 172 l-26 -12 M318 172 l26 -12" stroke={LINE} strokeWidth={8} strokeLinecap="round" />
    <path d="M112 158 l24 -16 M232 158 l24 -16" stroke="#fff" strokeWidth={11} strokeLinecap="round" />
  </g>
);

// ══ 마라탕 시리즈용 소품 7종 (2026-07-23 추가) ══════════════
// 🔴 제미나이 대본이 "돋보기 들고 팩트폭행" "선글라스 쓱 내리며" 같은 지시를 줬는데
//    우리 캐릭터엔 그런 소품이 없었다. 표정 9종만으로는 감정이 다 안 나와서 추가한다.
// 🔴 선 굵기·검정색은 볼과 같은 값을 쓴다. 따로 놀면 오려 붙인 것처럼 보인다.
// 🔴 여전히 **한 캐릭터에 두 개 이상 켜지 말 것.** 3편이 조잡해진 원인이 그거였다.

// 돋보기 — 팩트 들이밀 때. 오른쪽 아래에서 얼굴을 가리지 않게 비스듬히
const Magnifier = () => (
  <g transform="translate(255,150) scale(0.45) rotate(28 300 250)">
    <circle cx="300" cy="250" r="62" fill="#DFF3FF" opacity={0.5} stroke={LINE} strokeWidth={10} />
    <circle cx="300" cy="250" r="62" fill="none" stroke="#fff" strokeWidth={4} opacity={0.7} />
    <path d="M282 222 l18 -14" stroke="#fff" strokeWidth={10} strokeLinecap="round" />
    <rect x="288" y="310" width="26" height="72" rx="12" fill="#8A5A22" stroke={LINE} strokeWidth={9} />
  </g>
);

// 선글라스 — 거만·자신만만. 안경(Specs)과 달리 검게 채운다
const Sunglasses = () => (
  <g>
    <path d="M74 158 h252" stroke={LINE} strokeWidth={12} strokeLinecap="round" />
    <rect x="78" y="158" width="112" height="76" rx="24" fill="#1C1C1C" stroke={LINE} strokeWidth={9} />
    <rect x="210" y="158" width="112" height="76" rx="24" fill="#1C1C1C" stroke={LINE} strokeWidth={9} />
    <path d="M190 178 h20" stroke={LINE} strokeWidth={10} strokeLinecap="round" />
    {/* 빛 반사 — 이게 있어야 유리로 보인다 */}
    <path d="M96 214 l30 -40 M232 214 l30 -40" stroke="#fff" strokeWidth={9} strokeLinecap="round" opacity={0.8} />
  </g>
);

// 확성기 — 공지·외침.
// 🔴 **왼쪽 바깥**으로 뺐다(2026-07-23). 오른쪽에 두면 옆 캐릭터 얼굴을 가린다 —
//    두 볼 사이 간격이 140px뿐이라 폭 180px짜리 확성기가 못 들어간다.
//    올마가 항상 왼쪽 캐릭터라 왼쪽은 화면 가장자리까지 비어 있다.
// 🔴 2026-07-24 위치 교정 — 원래 translate(-10,150)이라 x가 -17~46,
//    즉 볼(viewBox 0~400) **왼쪽 밖**이었다. 손에 든 게 아니라 허공에 떠서 화면 끝에 잘렸다.
//    볼 왼쪽 안쪽(x 46~134)으로 당겨 든 것처럼 보이게 한다.
const Megaphone = () => (
  <g transform="translate(28,135) scale(0.55) rotate(14 40 250)">
    {/* 나팔이 왼쪽을 향한다 */}
    <path d="M100 214 l-72 -34 v140 l72 -34 z" fill="#E5352B" stroke={LINE} strokeWidth={9} strokeLinejoin="round" />
    <rect x="96" y="222" width="38" height="56" rx="10" fill="#C9C4B8" stroke={LINE} strokeWidth={8} />
    {/* 소리 물결 */}
    <g stroke={LINE} strokeWidth={8} strokeLinecap="round" fill="none">
      <path d="M8 214 q-18 36 0 72" />
      <path d="M-16 196 q-30 54 0 108" />
    </g>
  </g>
);

// 차트봉(지시봉) — 순위 짚을 때
const Pointer = () => (
  <g transform="translate(250,120) scale(0.5) rotate(-32 316 264)">
    <rect x="304" y="150" width="20" height="210" rx="9" fill="#F7EFA8" stroke={LINE} strokeWidth={8} />
    <rect x="298" y="140" width="32" height="26" rx="8" fill="#E5352B" stroke={LINE} strokeWidth={8} />
  </g>
);

// 손나팔 — 알린다. 입 옆에 손을 모은 모양
// 🔴 2026-07-24 위치 교정 — 원래 translate(255,150)이라 x가 405~468.
//    viewBox(400)를 통째로 벗어나 **옆 캐릭터에 붙어 보였다**(대표님 지적).
//    볼 오른쪽 안쪽(x 270~326)으로 당기고 키워서 진짜 손처럼 보이게 한다.
const HandCall = () => (
  <g transform="translate(0,20) scale(0.9)">
    <path
      d="M300 258 q34 -22 62 -6 q-10 26 -30 40 q-22 14 -38 2 z"
      fill="#F7EFA8"
      stroke={LINE}
      strokeWidth={9}
      strokeLinejoin="round"
    />
    <g stroke={LINE} strokeWidth={8} strokeLinecap="round" fill="none">
      <path d="M378 244 q16 30 0 60" />
      <path d="M400 228 q26 46 0 92" />
    </g>
  </g>
);

// 불 뿜기 — 사장님 대폭발
// 🔴 2026-07-24 위치 교정 — 원래 좌표가 y 208~300, 즉 **얼굴 정중앙**이라
//    불이 눈·입을 덮어버렸다(대표님 지적: "이펙트가 잘못 걸림").
//    입(y≈250) 아래로 내려 얼굴을 안 가리고 아래로 뿜게 한다.
const FireBreath = () => (
  <g transform="translate(0,105)">
    <path
      d="M200 300 q-30 -50 -8 -92 q6 34 26 44 q-6 -54 24 -84 q-4 42 22 66 q14 14 10 42 q-6 36 -74 24 z"
      fill="#FF7A1A"
      stroke={LINE}
      strokeWidth={9}
      strokeLinejoin="round"
    />
    <path
      d="M200 292 q-16 -30 -4 -56 q4 20 15 26 q-3 -32 14 -50 q-2 25 13 39 q8 8 6 25 q-4 21 -44 16 z"
      fill="#FFD400"
    />
  </g>
);

// 눈물 콧물 — 오열. 양쪽 눈에서 폭포처럼
const Wailing = () => (
  <g fill="#8ECBF5" stroke={LINE} strokeWidth={7} strokeLinejoin="round">
    <path d="M118 214 q-16 60 -6 96 q10 22 26 0 q10 -36 -6 -96 z" />
    <path d="M262 214 q-16 60 -6 96 q10 22 26 0 q10 -36 -6 -96 z" />
  </g>
);

// 앞치마 — 사장님.
// 🔴 볼 아래에 따로 매달면 "볼에 붙은 판"으로 보인다(2026-07-22 두 번 실패).
//    폴란드볼 옷은 **몸통(볼 하반부)을 덮어야** 옷으로 읽힌다.
// 🔴 길이는 볼 그림자 언저리까지만(2026-07-22 지시). 길게 늘어뜨렸더니 치마가 됐다.
// 🔴 끈은 대각선 위로, **눈 옆까지** 올라가야 어깨에 건 것처럼 보인다(2026-07-22 지시).
const APRON = "#FAF6EC";
// 🔴 어깨끈은 결국 뺐다(2026-07-22 "어깨띠 안 하게"). 대신 앞치마 윗단을 볼 가장자리까지
//    넓혀 **몸에 두른 것처럼** 만든다 — 양끝이 원 윤곽에 닿으면 뒤로 감긴 것으로 읽힌다.
const Apron = () => (
  <g>
    {/* 몸판 — 입 밑에서 시작. 윗단 양끝이 볼 가장자리(y=276에서 x≈65·335)에 닿는다 */}
    <path
      d="M66 276 Q200 310 334 276 L354 382 Q200 416 46 382 z"
      fill={APRON}
      stroke={LINE}
      strokeWidth={9}
      strokeLinejoin="round"
    />
    {/* 윗단 박음질 선 */}
    <path d="M76 292 Q200 324 324 292" fill="none" stroke="#D3CAB4" strokeWidth={6} strokeLinecap="round" />
    {/* 주름 — 아래로 갈수록 바깥으로 벌어진다 */}
    {[140, 200, 260].map((x, i) => (
      <path
        key={x}
        d={`M${x} 318 q${(i - 1) * 6} 32 ${(i - 1) * 14} 64`}
        stroke="#D3CAB4"
        strokeWidth={6}
        strokeLinecap="round"
        fill="none"
      />
    ))}
  </g>
);

// 볼에 튄 기름 — 사장님 전용
const OilSpots = () => (
  <g fill="#8A5A22" opacity={0.55}>
    <ellipse cx="96" cy="238" rx="14" ry="9" transform="rotate(-18 96 238)" />
    <ellipse cx="124" cy="262" rx="8" ry="6" />
    <ellipse cx="306" cy="246" rx="11" ry="7" transform="rotate(14 306 246)" />
  </g>
);

// 표정 3종. 브랜드는 늘 "변명하는 쪽"이라 이 셋이면 편당 충분하다.
//   시치미 = 아무 일 없다는 듯      (재료 공개 전)
//   변명   = 눈 굴리며 땀           (원가가 까일 때)
//   발끈   = 억울해서 소리침        (합계 공개 뒤)
// 🔴 표정이 안 읽힌다는 지적(2026-07-22). 쇼츠는 작은 화면이라 **과장해야** 보인다.
//    ① 눈썹 각도를 크게 — 표정의 8할이 눈썹이다
//    ② 눈동자를 크게 움직인다 — 시선이 어디 있는지 보여야 감정이 산다
//    ③ 입 크기를 표정마다 확 다르게 — 다 비슷하면 다 같은 얼굴이다
const FACES = {
  // 웃음 — 눈썹이 위로 부드럽게 휘고 입이 활짝
  웃음: { browL: "M104 128 q32 -26 62 -8", browR: "M234 120 q30 -18 62 8", pupil: [0, 4], mouth: "M166 250 q34 40 68 0", sweat: false },
  // 시치미 — 아무 감정 없음. 눈썹 수평, 입 일자. 나머지 표정의 기준점
  시치미: { browL: "M106 126 h60", browR: "M234 126 h60", pupil: [0, 0], mouth: "M170 254 h60", sweat: false },
  // 변명 — 눈을 딴 데로 굴리고 땀. 눈썹은 팔자로 처진다
  변명: { browL: "M104 118 q32 22 62 12", browR: "M234 130 q30 -12 62 -12", pupil: [17, 9], mouth: "M164 256 q13 -16 26 0 t26 0 t26 0", sweat: true },
  // 발끈 — 눈썹을 V자로 확 치켜올리고 입을 크게 벌린다
  // 🔴 입이 눈에 가까우면 코처럼 보인다(2026-07-22 두 번 지적). 아래에 크게.
  발끈: { browL: "M100 108 q34 4 64 30", browR: "M236 138 q30 -26 64 -30", pupil: [0, 6], mouth: "M200 288 m-46 0 a46 34 0 1 0 92 0 a46 34 0 1 0 -92 0", sweat: false },
  // 놀람 — 눈썹이 확 올라가고 눈동자가 작아진다. 입은 작고 동그랗게
  놀람: { browL: "M100 98 q34 -18 64 -6", browR: "M236 92 q30 -12 64 6", pupil: [0, -6], small: true, mouth: "M200 268 m-26 0 a26 30 0 1 0 52 0 a26 30 0 1 0 -52 0", sweat: false },
  // 화남 — 🔴 발끈과 다르다. 발끈은 **소리치는 중**(입 벌림), 화남은 **참는 중**(입 꽉 다뭄).
  //    참는 얼굴이라 핏대로 감정을 보여준다. 둘을 같이 쓰면 감정이 올라가는 게 보인다.
  화남: { browL: "M98 104 q36 8 66 34", browR: "M236 138 q30 -26 66 -34", pupil: [0, 8], mouth: "M158 282 q42 -34 84 0", vein: true, sweat: false },

  // ── 감정 단계 (2026-07-22 추가) ─────────────────────────────
  // 🔴 TTS로는 감정을 못 넣는다. **얼굴이 대신해야 한다.**
  //    특히 교촌은 재료가 하나씩 까일수록 당황해야 하는데 계속 같은 얼굴이었다.
  //    시치미 → 당황 → 진땀 순으로 올려서 쓴다.
  당황: { browL: "M104 116 q34 20 64 14", browR: "M236 130 q30 -8 64 -14", pupil: [13, -5], small: true, mouth: "M166 268 q12 -14 24 0 t24 0 t24 0", sweat: 2, flush: true },
  진땀: { browL: "M102 112 q34 26 64 20", browR: "M236 132 q30 -4 64 -20", pupil: [16, 8], small: true, mouth: "M200 280 m-30 0 a30 22 0 1 0 60 0 a30 22 0 1 0 -60 0", sweat: 3, flush: true },
  // 사장님 전용 — 하소연. 변명(눈 굴림)과 달리 **눈을 내리깔고 지쳐 있다**
  지침: { browL: "M104 122 q34 22 64 16", browR: "M234 138 q30 -6 64 -16", pupil: [0, 12], mouth: "M162 286 q38 -22 76 0", sweat: 1 },

  // ══ 사장님 감정 확장 8종 (2026-07-23 추가) ══════════════════
  // 🔴 "표정이 너무 적다, 3~4개뿐" 지적. 순위가 10개씩 나오는데 같은 얼굴만 반복됐다.
  //    놀람→화들짝→경악, 진땀→식은땀→멘붕 처럼 **같은 감정의 단계**를 만들어
  //    순위가 내려갈수록 감정이 올라가게 쓴다.

  // 화들짝 — 놀람보다 한 단계 위. 눈썹이 머리 밖까지 튀고 눈동자가 점처럼 작아진다
  화들짝: { browL: "M96 86 q36 -22 68 -4", browR: "M236 82 q32 -14 68 8", pupil: [0, -10], small: true, mouth: "M200 272 m-34 0 a34 40 0 1 0 68 0 a34 40 0 1 0 -68 0", sweat: 1 },

  // 경악 — 정점. 입이 네모나게 벌어지고 땀 두 방울
  경악: { browL: "M92 78 q38 -26 72 -2", browR: "M236 76 q34 -16 72 10", pupil: [0, -12], small: true, mouth: "M154 254 h92 v56 h-92 z", sweat: 2, flush: true },

  // 식은땀 — 겉으론 태연한데 땀 한 방울. 시치미와 진땀 사이
  식은땀: { browL: "M106 124 h60", browR: "M234 126 h60", pupil: [6, 4], mouth: "M170 258 q30 10 60 0", sweat: 1 },

  // 멘붕 — 넋이 나갔다. 눈동자가 위로 돌아가고 입이 파르르
  멘붕: { browL: "M104 110 q34 26 64 18", browR: "M236 128 q30 -8 64 -18", pupil: [0, -14], small: true, mouth: "M160 274 q10 -12 20 0 t20 0 t20 0 t20 0", sweat: 3, flush: true },

  // 억울 — 눈물 그렁그렁. 눈썹 팔자로 처지고 입이 삐뚤
  억울: { browL: "M102 116 q34 24 64 14", browR: "M236 130 q30 -10 64 -14", pupil: [0, 10], mouth: "M164 278 q26 -18 52 -2 q10 8 20 2", sweat: 1, flush: true },

  // 씨익 — 음흉하게 웃는다. 눈은 반달, 입은 한쪽만 올라간다
  씨익: { browL: "M104 124 q32 -14 62 -4", browR: "M236 120 q30 -10 62 4", pupil: [8, 2], mouth: "M162 258 q40 26 78 -12", sweat: false },

  // 좌절 — 눈을 감고 고개를 떨군다. 눈썹도 축 처진다
  좌절: { browL: "M104 128 q34 20 64 18", browR: "M234 146 q30 -4 64 -18", pupil: [0, 16], small: true, mouth: "M168 288 h64", sweat: 2 },

  // 뿌듯 — 사장님이 반전으로 태세 전환할 때. 눈 반달 + 활짝
  뿌듯: { browL: "M102 122 q34 -18 64 -6", browR: "M236 116 q30 -12 64 6", pupil: [0, 6], mouth: "M158 254 q42 44 84 0", flush: true },
};

// 핏대 — 화날 때 이마에 뜬다. 만화 기호라 설명이 필요 없다
const Vein = () => (
  <g stroke="#E5352B" strokeWidth={9} strokeLinecap="round" fill="none">
    <path d="M292 74 l26 -18 M292 74 l26 18 M292 74 l-4 -30 M292 74 l-4 30" />
  </g>
);

const LINE = "#000";
const LW = 9;

// 🔴 crown·hat·specs·oil 은 **그 장면에서 필요할 때만** 켠다. 기본은 전부 꺼짐.
export const BrandBall = ({
  brand = "교촌",
  face = "시치미",
  scale = 1,
  tilt = 0,
  x = 0,
  y = 0,
  crown = false, // 금관 — 본사가 위세 부리는 장면
  hat = false, // 위생모 — 사장님
  specs = false, // 반짝이는 안경 — 나마가 계산할 때
  oil = false, // 볼에 튄 기름 — 사장님 고단함
  // ── 마라탕 시리즈용 (2026-07-23) — 여전히 한 번에 하나만 켠다
  magnifier = false, // 돋보기 — 팩트 들이밀 때
  sunglasses = false, // 선글라스 — 거만·자신만만
  megaphone = false, // 확성기 — 공지·외침
  pointer = false, // 지시봉 — 순위 짚을 때
  handcall = false, // 손나팔 — 알린다
  fire = false, // 불 뿜기 — 사장님 대폭발
  wail = false, // 눈물 콧물 — 오열
  // 🔴 여성향 톤 테스트용(2026-07-25). 기본 꺼짐이라 기존 편엔 영향 없다.
  pin = false, // 🎀 머리핀 — 여자 캐릭터 표시(올마)
  lashes = false, // 👁 속눈썹(위에만) — 여자 캐릭터 표시
  blush = false, // 볼터치 — 발그레. 이거 하나로 인상이 확 부드러워진다
  hearts = false, // 하트눈 — 감탄·좋아함 (발끈·불뿜기의 여성향 대체)
  // 🔴 말하는 동안 입이 벌어지는 정도 0~1 (2026-07-22).
  //    목소리 파형에서 뽑아 넣는다. 입이 고정이면 소리만 나고 얼굴은 굳어 보인다.
  //    null이면 표정에 정해진 입 모양을 그대로 쓴다.
  mouth = null,
}) => {
  const B = BRANDS[brand] || BRANDS["교촌"];
  // 🔴 올마는 **항상** 핀·속눈썹·볼터치를 켠다(2026-07-25).
  //    talk_engine 이 캐릭터를 그릴 때 prop 을 안 넘겨서 본편에서만 남자로 나왔다.
  //    캐릭터 정체성은 호출부가 아니라 여기서 보장한다.
  if (brand === "올마") { pin = true; lashes = true; blush = true; }
  if (brand === "사장님") { blush = true; }
  const F = FACES[face] || FACES["시치미"];
  const [px, py] = F.pupil || [0, 0];
  const hasBand = Boolean(B.band);
  // 검정 볼(교촌)엔 검정 눈썹·입이 안 보인다 — 볼별로 선 색을 바꿀 수 있게
  const INK = B.ink || LINE;

  return (
    <svg
      width={400 * scale}
      height={400 * scale}
      viewBox="0 0 400 400"
      style={{ overflow: "visible", transform: `translate(${x}px, ${y}px) rotate(${tilt}deg)` }}
    >
      {/* 🔴 띠는 원 밖으로 삐져나오면 안 된다. 클립으로 가둔다. */}
      <defs>
        <clipPath id={`ball-${brand}`}>
          <circle cx="200" cy="200" r="155" />
        </clipPath>
      </defs>

      {/* 바닥 그림자 — 없으면 공중에 뜬 것처럼 보인다. 앞치마 밑단이 그림자 언저리에 온다 */}
      <ellipse cx="200" cy={B.apron ? 402 : 368} rx={B.apron ? 145 : 120} ry="20" fill="#000" opacity="0.13" />

      {/* 뒷머리(양갈래)는 볼보다 먼저 그려 뒤로 보낸다 */}
      {B.hair === "twin" && <Hair kind="twin" />}

      <g clipPath={`url(#ball-${brand})`}>
        <circle cx="200" cy="200" r="155" fill={B.body} />
        {/* 국기 줄무늬 자리 — 브랜드 색 띠 + 이름
            🔴 입(y≈250)과 겹쳐서 ₩가 지저분했다(2026-07-22). 띠를 아래로 내렸다. */}
        {/* 본사 — 🔴 로고는 **크고 두껍게**. 볼이 둥그니 곡선을 따라 휘어 양끝이 뒤로 감긴다.
            다 안 보여도 된다. 오히려 그래야 공에 인쇄된 것처럼 보인다(2026-07-22). */}
        {/* 🔴 fontSize 72는 K·N이 너무 잘려 못 읽었다(2026-07-22). 줄이고 곡선을 완만하게.
            양끝이 볼 가장자리에 살짝만 걸려야 "감긴 것"으로 보이면서도 읽힌다.
            짧은 이름(소비자)은 잘릴 일이 없으니 더 키운다. */}
        {B.logo && !B.forehead && (
          <>
            <defs>
              <path id={`arc-${brand}`} d="M28 252 q172 50 344 0" fill="none" />
            </defs>
            <text
              fontSize={B.logo.length <= 4 ? 72 : 60}
              letterSpacing="2"
              fontFamily={BLACK}
              fill={B.logoColor}
            >
              <textPath href={`#arc-${brand}`} startOffset="50%" textAnchor="middle">
                {B.logo}
              </textPath>
            </text>
          </>
        )}
        {/* 이마 글자 — 소비자. 가운데 인쇄는 입과 겹쳐서 이마로 올렸다. 조그맣게 */}
        {B.logo && B.forehead && (
          <text
            x="200"
            y="100"
            textAnchor="middle"
            fontSize="46"
            letterSpacing="2"
            fontFamily={BLACK}
            fill={B.logoColor}
          >
            {B.logo}
          </text>
        )}
        {hasBand && (
          <>
            <rect x="0" y="272" width="400" height="64" fill={B.band} />
            <text
              x="200"
              y="325"
              textAnchor="middle"
              fontSize={B.label.length <= 1 ? 56 : 46}
              fontFamily={JUA}
              fill={B.labelColor}
            >
              {B.label}
            </text>
          </>
        )}
      </g>
      {/* 🔴 얼굴 빨개짐 — 당황·진땀일 때만(2026-07-22).
          볼 전체를 붉게 덮으면 브랜드 색이 죽으니 **뺨 두 군데만** 물들인다.
          검정 볼(교촌)에서도 보이도록 진한 붉은색을 쓴다. */}
      {F.flush && (
        <g clipPath={`url(#ball-${brand})`}>
          <ellipse cx="96" cy="236" rx="46" ry="26" fill="#E5352B" opacity="0.42" />
          <ellipse cx="304" cy="236" rx="46" ry="26" fill="#E5352B" opacity="0.42" />
        </g>
      )}

      <circle cx="200" cy="200" r="155" fill="none" stroke={LINE} strokeWidth={LW} />

      {/* 🔴 앞치마는 볼 **위에** 입힌다(윤곽선 다음). 볼 하반부를 덮어야 옷으로 읽힌다 */}
      {B.apron && <Apron />}

      {/* 정수리 한 가닥은 볼 위로 삐져나온다 */}
      {B.hair === "tuft" && <Hair kind="tuft" />}

      {/* 눈 — 로고 얼굴은 점 두 개, 나머지는 폴란드볼식 흰자 눈 */}
      {F.dot
        ? [152, 248].map((cx) => <circle key={cx} cx={cx} cy="178" r="23" fill={LINE} />)
        : [140, 260].map((cx) => (
            <g key={cx}>
              {/* 🔴 흰자를 줄였다(2026-07-25: "눈이 너무 크다"). rx42→36 · ry50→43 */}
              <ellipse cx={cx} cy="182" rx="36" ry="43" fill="#fff" stroke={LINE} strokeWidth={LW - 2} />
              <circle cx={cx + px} cy={182 + py} r={F.small ? 11 : 16} fill={B.pupil || LINE} />
            </g>
          ))}

      {/* 눈썹 — 표정의 8할이다. 눈만 그리면 다 똑같아 보인다. 로고 얼굴엔 없다 */}
      {/* 🔴 여자(lashes)는 **눈썹을 안 그린다**(2026-07-25 지시).
          속눈썹이 눈매를 만들어주므로 눈썹까지 있으면 인상이 세진다 */}
      {!F.dot && !lashes && (
        <>
          <path d={F.browL} fill="none" stroke={INK} strokeWidth={lashes ? 11 : 17} strokeLinecap="round" />
          <path d={F.browR} fill="none" stroke={INK} strokeWidth={lashes ? 11 : 17} strokeLinecap="round" />
        </>
      )}

      {lashes && !F.dot && <Lashes ink={INK} />}

      {/* 입 — 🔴 띠·가운데 로고가 있으면 위로 올려 글자와 덜 겹치게 한다. 이마 글자·올마는 그대로 */}
      <g transform={`translate(0,${hasBand || (B.logo && !B.forehead) ? -22 : 0})`}>
        {mouth === null ? (
          <path
            d={F.mouth}
            fill={face === "발끈" ? "#7A1010" : "none"}
            stroke={INK}
            strokeWidth="10"
            strokeLinecap="round"
          />
        ) : (
          // 말하는 중 — 소리 크기만큼 벌어진다. 다물면 표정의 원래 입으로 돌아간다
          mouth < 0.06 ? (
            <path d={F.mouth} fill="none" stroke={INK} strokeWidth="10" strokeLinecap="round" />
          ) : (
            // 🔴 눈에 가까우면 코로 보인다(2026-07-22 세 번째 같은 실수). 아래에 그린다.
            //    벌어질수록 아래로 더 내려가야 턱이 벌어지는 것처럼 보인다.
            <ellipse
              cx="200"
              cy={280 + mouth * 10}
              rx={30 + mouth * 14}
              ry={9 + mouth * 32}
              fill="#7A1010"
              stroke={INK}
              strokeWidth="9"
            />
          )
        )}
      </g>

      {/* 붙였다 뗐다 하는 것들 — 그 장면에 맞는 하나만 켠다 */}
      {oil && <OilSpots />}
      {specs && <Specs />}
      {crown && <Crown />}
      {/* 마라탕 시리즈 소품 (2026-07-23) — 불·눈물은 얼굴 위에 얹히므로 나중에 그린다 */}
      {magnifier && <Magnifier />}
      {sunglasses && <Sunglasses />}
      {megaphone && <Megaphone />}
      {pointer && <Pointer />}
      {handcall && <HandCall />}
      {wail && <Wailing />}
      {fire && <FireBreath />}
      {pin && <HairPin />}
      {/* 볼터치 — 눈 아래 양볼. 반투명 코럴이라 볼 색을 안 가린다 */}
      {/* 🔴 볼터치는 **볼**에 있어야 한다(2026-07-25 지적).
          cy 212 는 눈(cy 182, ry 50 → 132~232)과 겹쳐서 눈까지 발그레했다.
          눈 아래 y 258 로 내리고 바깥쪽으로 벌린다.
       🔴 핑크볼(올마)은 핑크 위에 핑크라 안 보인다 → **흰 하이라이트를 깔고** 그 위에 코럴. */}
      {blush && (
        <g>
          {/* 🔴 올마(핑크볼)는 **흰색만**(2026-07-25 지시). 핑크 위에 코럴을 얹으면 탁해진다.
              나마(노랑볼)는 코럴. 둘 다 크기는 작게 — 크면 취한 것처럼 보인다. */}
          {B.body === "#F5A9C0" ? (
            <g fill="#fff" opacity="0.62">
              <ellipse cx="106" cy="256" rx="24" ry="13" />
              <ellipse cx="294" cy="256" rx="24" ry="13" />
            </g>
          ) : (
            <g fill="#FF7A8A" opacity="0.24">
              <ellipse cx="106" cy="256" rx="23" ry="12" />
              <ellipse cx="294" cy="256" rx="23" ry="12" />
            </g>
          )}
        </g>
      )}
      {/* 하트눈 — 눈 위에 겹쳐 그린다. 감탄·좋아함 */}
      {hearts && (
        <g fill="#FF4D6D" stroke={LINE} strokeWidth={6} strokeLinejoin="round">
          <path d="M140 148 c-14 -16 -38 -6 -38 14 c0 20 26 34 38 44 c12 -10 38 -24 38 -44 c0 -20 -24 -30 -38 -14 z" />
          <path d="M260 148 c-14 -16 -38 -6 -38 14 c0 20 26 34 38 44 c12 -10 38 -24 38 -44 c0 -20 -24 -30 -38 -14 z" />
        </g>
      )}
      {/* 사장님은 빵모자가 기본 장착(BRANDS.hat) — 프롭으로도 켤 수 있다 */}
      {(hat || B.hat) && <ChefHat label={B.hatLabel} />}

      {/* 핏대 — 화날 때만 */}
      {F.vein && <Vein />}

      {/* 땀 — 🔴 개수로 당황 정도를 표현한다(2026-07-22). 1방울=살짝, 3방울=진땀.
          TTS가 감정을 못 실으니 얼굴이 대신해야 한다. */}
      {F.sweat &&
        [
          { x: 318, y: 128, s: 1 },
          { x: 92, y: 148, s: 0.8 },
          { x: 300, y: 208, s: 0.7 },
        ]
          .slice(0, F.sweat === true ? 1 : F.sweat)
          .map((d) => (
            <g key={d.x} transform={`translate(${d.x - 318},${d.y - 128}) scale(${d.s})`} transform-origin="318 128">
              <path
                d="M318 128 q16 26 16 38 a16 16 0 0 1 -32 0 q0 -12 16 -38 z"
                fill="#8ECBF5"
                stroke={LINE}
                strokeWidth="7"
              />
            </g>
          ))}
    </svg>
  );
};
