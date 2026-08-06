// 2인 체제 장면들 (2026-07-21)
//
// 🔴 역할이 고정돼 있다. 이걸 어기면 캐릭터가 흔들린다:
//      올마 = 억지 부리고 감정 폭발 (표정 크게, 움직임 크게)
//      나마 = 세상 덤덤. 팩트만 들이민다 (거의 무표정, 소품으로 말한다)
// 🔴 Scenes.jsx가 이미 길어서 새 장면은 여기 둔다.
// 🔴 Wrap(flex)에 요소가 많으면 세로가 넘쳐 잘린다 — 여기는 전부 절대 위치.
import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

import { Nama } from "../olma/Nama";
import { Olma } from "../olma/Olma";
import { Table } from "../olma/Table";
import { ChickenSet } from "../olma/ChickenSet";
import { Receipt } from "../olma/Receipt";
import { Backdrop, Dust, Impact } from "../olma/Effects";
import { PopEyes, Sparkles, ThumbCard, Volcano } from "../olma/BigFx";
import { Calculator, Pointer, Ruler, SignBoard, Umbrella } from "../olma/Props";
import { BG, C, CFG, cost, diff } from "./config";
import { BLACK, JUA } from "./fonts";

const E = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };
const won = (n) => n.toLocaleString() + "원";
const fadeIn = (f, at, len = 6) => interpolate(f, [at, at + len], [0, 1], E);
const row = (top) => ({ position: "absolute", top, left: 0, right: 0, textAlign: "center" });

// 자막 판 — 배경 패턴 위 맨글씨는 안 읽힌다
const Slab = ({ children, size = 88, bg = C.ink, color = "#fff" }) => (
  <span
    style={{
      display: "inline-block",
      fontFamily: BLACK,
      fontSize: size,
      letterSpacing: -4,
      color,
      background: bg,
      borderRadius: 20,
      padding: `${size * 0.13}px ${size * 0.4}px ${size * 0.21}px`,
    }}
  >
    {children}
  </span>
);

const Note = ({ children, size = 52 }) => (
  <span
    style={{
      display: "inline-block",
      fontFamily: JUA,
      fontSize: size,
      color: "#333",
      background: "#fff",
      border: `6px solid ${C.ink}`,
      borderRadius: 18,
      padding: `${size * 0.14}px ${size * 0.44}px ${size * 0.22}px`,
    }}
  >
    {children}
  </span>
);

// ───────────────── 0. 인사 (0~3초)
// 🔴 웃음 포인트: 올마가 너무 깊이 숙이다 나마 머리에 박치기 → 나마 안경 삐뚤어짐
export const Greet2 = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const BONK = Math.round(fps * 1.05); // 박치기 순간

  const bow = (d) =>
    interpolate(f, [d, Math.round(fps * 0.55) + d, BONK, BONK + 8], [0, 30, 34, 6], {
      ...E,
      easing: Easing.inOut(Easing.quad),
    });

  // 박치기 순간 화면이 튄다
  const jolt = f >= BONK && f < BONK + 9 ? Math.sin((f - BONK) * 2.1) * (9 - (f - BONK)) * 2.6 : 0;
  // 나마는 맞고 나서 뒤로 밀린다
  const push = interpolate(f, [BONK, BONK + 6, BONK + 26], [0, 26, 14], E);
  const tilt = f >= BONK ? -18 : 0; // 안경 삐뚤

  return (
    <AbsoluteFill style={{ overflow: "hidden", translate: `${jolt}px 0px` }}>
      <Backdrop color={BG.hook} />
      <Sparkles n={10} />

      <div style={{ ...row(430), opacity: fadeIn(f, 2) }}>
        <Slab size={86}>소상공인 여러분 힘내세요</Slab>
      </div>
      <div style={{ ...row(580), opacity: fadeIn(f, 10) }}>
        <Note size={58}>그냥 궁금해서 만들었습니다</Note>
      </div>

      <Impact at={BONK} x="42%" y="60%" size={420} color={C.red} />

      <div style={{ position: "absolute", bottom: 210, left: "50%", translate: "-490px 0px" }}>
        <Olma face="씩" pose="기본" scale={1.05} lean={bow(0)} head={bow(0) * 0.5} />
      </div>
      <div style={{ position: "absolute", bottom: 210, left: "50%", translate: `${-190 + push}px 0px` }}>
        <Nama
          face={f >= BONK ? "헉" : "씩"}
          pose={f >= BONK ? "깜짝" : "기본"}
          scale={1.05}
          lean={bow(3)}
          head={bow(3) * 0.5}
          glasses={tilt}
        />
      </div>
    </AbsoluteFill>
  );
};

// ───────────────── 1. 썸네일 카드 (3~6초)
// 🔴 웃음 포인트: 카드가 쾅 들어오면서 나마가 화면 구석으로 밀려난다
export const CardScene = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const IN = Math.round(fps * 0.2);
  const shove = interpolate(f, [IN + 4, IN + 12], [0, 190], { ...E, easing: Easing.out(Easing.quad) });

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop color={BG.hook} />

      {/* 밀려나는 나마 — 카드보다 먼저 그려 뒤로 */}
      <div style={{ position: "absolute", bottom: 90, left: "50%", translate: `${-160 + shove}px 0px` }}>
        <Nama face="헉" pose="털썩" scale={0.8} glasses={-18} tilt={12} />
      </div>

      <ThumbCard at={IN} top={`${CFG.brand} ${CFG.menu}`} main="원가 충격 공개" sub={CFG.hook} />
    </AbsoluteFill>
  );
};

// ───────────────── 2. 먹방 시도 (6~10초)
// 🔴 웃음 포인트: 올마가 한 입 하려는 순간 나마가 자로 손등을 찰싹
export const EatScene = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const SLAP = Math.round(fps * 1.9);

  const jolt = f >= SLAP && f < SLAP + 8 ? Math.sin((f - SLAP) * 2.4) * (8 - (f - SLAP)) * 2.2 : 0;
  // 자가 위에서 내려와 때린다
  const rulerY = interpolate(f, [SLAP - 8, SLAP], [-180, 0], { ...E, easing: Easing.in(Easing.quad) });

  return (
    <AbsoluteFill style={{ overflow: "hidden", translate: `${jolt}px 0px` }}>
      <Backdrop color={BG.hook} />

      <div style={{ ...row(230), opacity: fadeIn(f, 4) }}>
        <Note size={56}>{f >= SLAP ? "먹지 마" : "잘 먹겠습니다"}</Note>
      </div>

      <div style={{ position: "absolute", bottom: 60, left: "50%", translate: "-50% 0px" }}>
        <Table width={900}><g /></Table>
      </div>
      <div style={{ position: "absolute", top: 1180, left: "50%", translate: "-50% 0px" }}>
        <ChickenSet brand={CFG.brand} width={620} box={CFG.box} />
      </div>

      <div style={{ position: "absolute", bottom: 320, left: "50%", translate: "-520px 0px" }}>
        <Olma
          face={f >= SLAP ? "헉" : "황홀"}
          pose={f >= SLAP ? "깜짝" : "먹기"}
          scale={1.0}
          head={Math.sin(f / 8) * 4}
        />
      </div>
      <div style={{ position: "absolute", bottom: 320, left: "50%", translate: "-140px 0px" }}>
        <Nama face="무표정" pose="가리킴" scale={1.0} glasses={0} />
      </div>

      {/* 자 — 위에서 내려와 올마 손등을 때린다 */}
      <div style={{ position: "absolute", bottom: 640, left: "50%", translate: `-330px ${rulerY}px` }}>
        <Ruler x={95} y={20} rot={18} />
      </div>
      <Impact at={SLAP} x="34%" y="62%" size={330} color={C.red} />
    </AbsoluteFill>
  );
};

// ───────────────── 3. 영수증 충격 (10~15초)
// 🔴 웃음 포인트: 올마 눈알이 튀어나오고, 나마는 무심히 계산기를 꺼낸다
export const ShockScene = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const DROP = Math.round(fps * 0.5);
  const y = interpolate(f, [0, DROP], [-1000, 0], { ...E, easing: Easing.in(Easing.quad) });
  const wob = f > DROP ? Math.sin((f - DROP) / 2.2) * Math.max(0, 10 - (f - DROP) * 0.7) : 0;

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop color={BG.hook} />

      <div
        style={{
          position: "absolute",
          top: 120,
          left: "50%",
          translate: `-470px ${y}px`,
          rotate: `${-4 + wob}deg`,
        }}
      >
        <Receipt brand={CFG.brand} menu={CFG.menu} price={CFG.sell} width={940} hook={CFG.hook} />
      </div>

      <Impact at={DROP} x="50%" y="40%" size={620} />
      <Dust at={DROP} x="50%" y="44%" n={9} />

      <div style={{ position: "absolute", bottom: 120, left: "50%", translate: "-540px 0px" }}>
        <Olma face="헉" pose="깜짝" scale={1.05} />
        <PopEyes at={DROP + 3} scale={1.05} />
      </div>
      <div style={{ position: "absolute", bottom: 120, left: "50%", translate: "-150px 0px" }}>
        <Nama
          face="무표정"
          pose="가리킴위"
          scale={1.05}
          glasses={0}
          holdR={(hx, hy) => <Calculator x={hx + 40} y={hy - 30} rot={-8} lit={f > DROP + 20} />}
        />
      </div>
    </AbsoluteFill>
  );
};

// ───────────────── 4. 합계 공개 + 정적 (36~42초)
// 🔴 이 영상 최고의 웃음 포인트다. 숫자가 뜨는 순간 **소리와 움직임이 전부 멈추고**
//    둘이 아무 말 없이 화면(시청자)을 본다. 1.5초.
export const RevealScene = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const HIT = Math.round(fps * 1.2); // 합계가 뜨는 순간
  const STILL = Math.round(fps * 1.5); // 정적 길이

  const frozen = f >= HIT && f < HIT + STILL; // 이 구간엔 아무것도 안 움직인다

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop color={BG.climax} />

      <div style={{ ...row(300), opacity: fadeIn(f, 4) }}>
        <Note size={58}>다 더해보면</Note>
      </div>

      <div style={{ ...row(430), opacity: fadeIn(f, HIT, 2) }}>
        <span
          style={{
            display: "inline-block",
            fontFamily: BLACK,
            fontSize: 210,
            letterSpacing: -8,
            color: "#fff",
            background: C.red,
            borderRadius: 26,
            padding: "18px 52px 30px",
            boxShadow: "0 16px 0 #8E1109",
          }}
        >
          {won(cost)}
        </span>
      </div>
      <div style={{ ...row(710), opacity: fadeIn(f, HIT + 6, 3) }}>
        <Note size={62}>판매가 {won(CFG.sell)} 중</Note>
      </div>

      {/* 🔴 정적 구간엔 둘 다 정면을 보고 굳어 있다. 흔들림·바운스 전부 0 */}
      <div style={{ position: "absolute", bottom: 130, left: "50%", translate: "-500px 0px" }}>
        <Olma
          face={frozen ? "무표정" : "헉"}
          pose="기본"
          scale={1.05}
          bounce={frozen ? 0 : Math.sin(f / 5) * 5}
        />
      </div>
      <div style={{ position: "absolute", bottom: 130, left: "50%", translate: "-150px 0px" }}>
        <Nama face="무표정" pose="기본" scale={1.05} glasses={0} bounce={0} />
      </div>
    </AbsoluteFill>
  );
};

// ───────────────── 5. 화산 폭발 (42~49초)
// 🔴 정적이 깨지는 순간 올마 머리에서 화산. 나마는 귀마개+우산으로 태연히 막는다
export const BoomScene = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const AT = Math.round(fps * 0.2);
  const shake = f >= AT ? Math.sin(f * 1.7) * 16 : 0;

  return (
    <AbsoluteFill style={{ overflow: "hidden", translate: `${shake}px 0px` }}>
      <Backdrop color={BG.climax} />

      <Volcano at={AT} x="34%" y="56%" size={0.62} />

      <div style={{ position: "absolute", bottom: 260, left: "50%", translate: "-500px 0px" }}>
        <Olma face="극대노" pose="만세" scale={1.15} bounce={Math.sin(f / 3) * 10} />
      </div>
      <div style={{ position: "absolute", bottom: 260, left: "50%", translate: "-140px 0px" }}>
        <Nama face="무표정" pose="가리킴위" scale={1.15} earmuffs glasses={0} />
      </div>
      <div style={{ position: "absolute", bottom: 900, left: "50%", translate: "-60px 0px" }}>
        <Umbrella x={130} y={110} rot={-10} open={1} />
      </div>

      <div style={{ ...row(230), opacity: fadeIn(f, AT + 8) }}>
        <Slab size={92} bg={C.red}>{CFG.lines.climaxKick} {won(diff)}</Slab>
      </div>
    </AbsoluteFill>
  );
};

// ───────────────── 6. 남은 돈 어디로 (49~54초)
// 🔴 웃음 포인트: 진지한 질문이 떠 있는데 뒤에서 올마가 영수증을 씹어먹고 있다
export const AskScene = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop color={BG.close} />

      <div style={{ ...row(260), opacity: fadeIn(f, 2) }}>
        <Slab size={78}>{CFG.lines.closeTop}</Slab>
      </div>
      <div style={{ ...row(400), opacity: fadeIn(f, 10) }}>
        <Note size={50}>{CFG.lines.closeSub}</Note>
      </div>
      <div style={{ ...row(540), opacity: fadeIn(f, 18) }}>
        <Slab size={96} bg={C.red}>
          남은 {won(diff)}
        </Slab>
      </div>
      <div style={{ ...row(720), opacity: fadeIn(f, 26) }}>
        <Note size={62}>어디로 갔을까?</Note>
      </div>

      {/* 올마 — 영수증을 우물우물 씹는다 */}
      <div style={{ position: "absolute", bottom: 130, left: "50%", translate: "-500px 0px" }}>
        <Olma face="황홀" pose="먹기" scale={1.05} chew={f / 3} head={Math.sin(f / 7) * 4} />
      </div>
      {/* 나마 — 한심하다는 듯 지휘봉으로 올마를 가리킨다 */}
      <div style={{ position: "absolute", bottom: 130, left: "50%", translate: "-150px 0px" }}>
        <Nama
          face="일자"
          pose="가리킴"
          scale={1.05}
          glasses={0}
          holdR={(hx, hy) => <Pointer x={hx - 70} y={hy} rot={186} />}
        />
      </div>
    </AbsoluteFill>
  );
};

// ───────────────── 7. 댓글 유도 → 루프 (54~58초)
// 🔴 마지막 화면이 첫 화면(치킨 박스)과 이어져야 반복 재생이 매끄럽다
export const LoopScene = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  // 뒤로 갈수록 첫 화면 구도로 되돌아간다
  const back = interpolate(f, [Math.round(fps * 2), Math.round(fps * 3.6)], [0, 1], E);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop color={BG.close} />

      <div style={{ ...row(240), opacity: fadeIn(f, 2) * (1 - back * 0.85) }}>
        <Slab size={72}>배달비? 임대료? 본사 마진?</Slab>
      </div>

      {/* 나마가 표지판을 든다 */}
      <div style={{ position: "absolute", top: 430, left: "50%", translate: "-150px 0px", opacity: fadeIn(f, 10) }}>
        <SignBoard x={150} y={90} rot={-6} text="댓글로 알려줘" />
      </div>

      {/* 되돌아오는 치킨 박스 — 루프 연결 */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: "50%",
          translate: "-50% 0px",
          scale: String(0.7 + back * 0.4),
          opacity: 0.35 + back * 0.65,
        }}
      >
        <Table width={900}><g /></Table>
      </div>
      <div style={{ position: "absolute", top: 1210, left: "50%", translate: "-50% 0px", opacity: 0.35 + back * 0.65 }}>
        <ChickenSet brand={CFG.brand} width={600} box={CFG.box} />
      </div>

      <div style={{ position: "absolute", bottom: 380, left: "50%", translate: "-540px 0px" }}>
        <Olma face="씩" pose="가리킴위" scale={0.9} bounce={Math.sin(f / 5) * 6} />
      </div>
      <div style={{ position: "absolute", bottom: 380, left: "50%", translate: "-120px 0px" }}>
        <Nama face="씩" pose="기본" scale={0.9} glasses={0} />
      </div>

      <div style={{ ...row(1640), opacity: fadeIn(f, 20) }}>
        <Note size={54}>{CFG.site}</Note>
      </div>
    </AbsoluteFill>
  );
};
