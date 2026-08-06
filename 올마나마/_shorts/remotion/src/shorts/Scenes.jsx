// 장면 — 전부 frame 계산. setTimeout·CSS 애니메이션 없음.
//
// 🔴 1차 시도는 "하나도 안 웃겼다"(2026-07-21). 원인 세 가지를 고쳤다:
//   ① 자막이 라벨투였다 → **말하듯이** 쓴다 ("황금올리브 재료비" ✕ / "그래서 다 까봤다" ○)
//   ② 올마가 표정만 바뀌었다 → **오버해서 움직인다** (자빠지고 튀어오르고 뒷목잡고)
//   ③ 제일 웃긴 반전을 뺐다 → **"근데 존나 맛있네 젠장"** 을 되살린다.
//      실컷 화내다가 결국 뜯어먹는 자기모순이 이 영상의 웃음 포인트다.
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing, random, spring } from "remotion";
import { Olma } from "../olma/Olma";
import { Table, Drumstick, ForkInHand } from "../olma/Table";
import { ChickenSet } from "../olma/ChickenSet";
import { Receipt } from "../olma/Receipt";
import { ActionLines, Impact, Dust, Sweat, Bolt, Stamp, Hearts, Backdrop } from "../olma/Effects";
import { Brush, IngredientArt } from "../olma/Ingredients";
import { Nama } from "../olma/Nama";
import { BeeToy, PriceBoard, StampTool, Toothpick } from "../olma/Props";
import { CFG, C, BG, cost, diff, T } from "./config";
import { BLACK, JUA } from "./fonts";

const won = (n) => n.toLocaleString() + "원";
const E = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };
const L = CFG.lines;

const fadeIn = (f, at, len = 7) => interpolate(f, [at, at + len], [0, 1], E);
const popIn = (f, at = 0) =>
  interpolate(f, [at, at + 10], [0.6, 1], { ...E, easing: Easing.out(Easing.back(3)) });
const drop = (f, at) => interpolate(f, [at, at + 6], [-190, 0], { ...E, easing: Easing.in(Easing.quad) });
const squash = (f, at) => interpolate(f, [at + 5, at + 8, at + 14], [1, 0.82, 1], E);

// 🔴 배경 패턴 위에 맨글씨를 올리면 안 읽힌다(2026-07-21 "글씨가 잘 안 보여").
//    자막은 **불투명 판 위에** 올린다. 세 종류로 통일:
//      Cap   설명·라벨 — 흰 판 + 검은 테두리
//      Punch 강조 한마디 — 검은 판 + 흰 글씨
//      Mark  형광펜 — 글씨 아래쪽만 노랗게 (문장이 길 때)
const Cap = ({ children, size = 56, color = "#333", style = {} }) => (
  <div
    style={{
      display: "inline-block",
      fontFamily: JUA,
      fontSize: size,
      color,
      background: "#fff",
      border: `5px solid ${C.ink}`,
      borderRadius: 16,
      padding: `${size * 0.16}px ${size * 0.5}px ${size * 0.24}px`,
      ...style,
    }}
  >
    {children}
  </div>
);

const Punch = ({ children, size = 68, bg = C.ink, color = "#fff", style = {} }) => (
  <div
    style={{
      display: "inline-block",
      fontFamily: BLACK,
      fontSize: size,
      color,
      background: bg,
      borderRadius: 18,
      letterSpacing: -3,
      padding: `${size * 0.14}px ${size * 0.46}px ${size * 0.22}px`,
      ...style,
    }}
  >
    {children}
  </div>
);

// 🔴 장면마다 배경색 + 연한 패턴(2026-07-21 "너무 칙칙해")
const Wrap = ({ children, gap = 0, bg, style = {} }) => (
  <AbsoluteFill
    style={{ alignItems: "center", justifyContent: "center", gap, padding: "0 56px", textAlign: "center", ...style }}
  >
    {bg && <Backdrop color={bg} />}
    {React.Children.map(children, (ch) =>
      React.isValidElement(ch) ? React.cloneElement(ch, { style: { flexShrink: 0, ...(ch.props.style || {}) } }) : ch
    )}
  </AbsoluteFill>
);

// ───────────────── 1. 훅
export const Hook = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  // 영수증이 위에서 쿵 떨어져 꽂힌다
  const y = interpolate(f, [0, 8], [-900, 0], { ...E, easing: Easing.in(Easing.quad) });
  const wob = f > 8 ? Math.sin((f - 8) / 2.2) * Math.max(0, 9 - (f - 8) * 0.7) : 0;
  // 영수증 착지 + 도장 찍힘, 두 번 흔들린다
  const STAMP = Math.round(fps * 0.7);
  const shake =
    (f >= 8 && f < 20 ? Math.sin(f * 3) * (20 - f) * 1.6 : 0) +
    (f >= STAMP && f < STAMP + 10 ? Math.sin(f * 3.4) * (STAMP + 10 - f) * 2.6 : 0);

  return (
    <AbsoluteFill style={{ overflow: "hidden", translate: `${shake}px 0px` }}>
      <Backdrop color={BG.hook} />
      <div
        style={{
          position: "absolute",
          top: 150,
          left: "50%",
          translate: `-500px ${y}px`,
          rotate: `${-4 + wob}deg`,
        }}
      >
        <Receipt brand={CFG.brand} menu={CFG.menu} price={CFG.sell} width={1000} hook={CFG.hook} />
      </div>

      {/* 🔴 위에 얌전히 얹은 검은 글씨는 임팩트가 없다(2026-07-21).
          영수증 위에 **빨간 도장**으로 쾅 찍는다. 매 편 같은 자리라 시리즈 시그니처가 된다. */}
      <div
        style={{
          position: "absolute",
          top: 1580,
          width: "100%",
          textAlign: "center",
          fontFamily: BLACK,
          zIndex: 5,
        }}
      >
        <Stamp at={Math.round(fps * 0.7)} text={L.hookTop} fps={fps} size={92} />
      </div>

      {/* 🔴 접시 대신 **배달 세트**(박스+콜라+치킨무). 실제로 시켜 먹는 모습이라야
          시청자가 자기 얘기로 받아들인다(2026-07-21 지시). */}
      <div style={{ position: "absolute", bottom: 40, left: "50%", translate: "-50% 0px" }}>
        <Table width={980}><g /></Table>
      </div>
      <div style={{ position: "absolute", bottom: 470, left: "50%", translate: "-50% 0px" }}>
        <ChickenSet brand={CFG.brand} width={720} box={CFG.box} />
      </div>

      {/* 영수증이 꽂히는 순간 충격파 + 먼지 */}
      <Impact at={8} x="50%" y="52%" size={620} />
      <Dust at={8} x="50%" y="56%" n={9} />
    </AbsoluteFill>
  );
};

// ───────────────── 2. 변명 깨기
export const Excuse = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const factAt = fps * 0.8;
  const kickAt = fps * 1.7;
  // 팩트가 뜨는 순간 화면이 한 번 튄다
  const jolt = f >= factAt && f < factAt + 10 ? Math.sin((f - factAt) * 1.9) * (10 - (f - factAt)) * 2.4 : 0;

  return (
    <Wrap gap={16} bg={BG.excuse} style={{ translate: `${jolt}px 0px` }}>
      {/* 팩트가 꽂히는 순간 집중선 + 번개 */}
      {f >= factAt && f < factAt + 22 && (
        <div style={{ position: "absolute", inset: 0, opacity: interpolate(f, [factAt, factAt + 20], [0.42, 0], E) }}>
          <ActionLines color={C.red} opacity={1} spin={7} />
        </div>
      )}
      <Bolt at={factAt} x="22%" y="16%" size={130} />
      <Bolt at={factAt + 2} x="78%" y="14%" size={110} />

      {/* 브랜드 주장 — 취소선으로 그어버린다 */}
      <div
        style={{
          position: "relative",
          fontFamily: JUA,
          fontSize: 58,
          color: "#555",
          background: "#fff",
          border: `5px solid ${C.ink}`,
          borderRadius: 16,
          padding: "10px 30px 14px",
          opacity: fadeIn(f, 0),
          // 🔴 긴 문구가 화면 밖으로 삐져나가 잘리는 걸 막는다(2026-07-21).
          maxWidth: 960,
          whiteSpace: "nowrap",
          overflow: "hidden",
        }}
      >
        {L.excuseClaim}
        <div
          style={{
            position: "absolute",
            left: -10,
            top: "52%",
            height: 8,
            background: C.red,
            borderRadius: 4,
            width: `${interpolate(f, [factAt - 6, factAt + 4], [0, 106], E)}%`,
          }}
        />
      </div>

      <div
        style={{
          fontFamily: BLACK,
          fontSize: 220,
          color: C.red,
          letterSpacing: -10,
          lineHeight: 1,
          marginTop: 10,
          scale: popIn(f, factAt),
          opacity: fadeIn(f, factAt, 4),
          textShadow: `0 10px 0 ${C.ink}`,
        }}
      >
        {L.excuseFact}
      </div>

      <div
        style={{
          fontFamily: BLACK,
          fontSize: 68,
          color: C.ink,
          letterSpacing: -3,
          background: C.yellow,
          padding: "6px 22px",
          borderRadius: 10,
          opacity: fadeIn(f, kickAt, 5),
          scale: popIn(f, kickAt),
        }}
      >
        {L.excuseKick}
      </div>

      {/* 🔴 34px 회색은 화면에서 거의 안 읽혔다(2026-07-21 지적). 키우고 진하게. */}
      <div style={{ opacity: fadeIn(f, kickAt + 8) }}>
        <Cap size={46} color="#333">{CFG.excuse.note}</Cap>
      </div>

      {/* 🔴 제자리 bounce만 하면 죽어 보인다(2026-07-21 "제자리만 움직이는 건 별로").
          왼쪽에서 **걸어 들어와** 팩트를 손가락질한다. 머리·상체도 따로 움직인다. */}
      <div
        style={{
          marginTop: 4,
          opacity: fadeIn(f, 2),
          translate: `${interpolate(f, [0, fps * 1.1], [-520, 0], { ...E, easing: Easing.out(Easing.quad) })}px 0px`,
        }}
      >
        <Olma
          scale={1.5}
          face={f > kickAt ? "삐뚤" : "갸웃"}
          pose={f > kickAt ? "가리킴" : "기본"}
          walk={f < fps * 1.1 ? 1 : 0}
          phase={(f / 5) * Math.PI}
          head={f > kickAt ? Math.sin(f / 4) * 7 : Math.sin(f / 9) * 4}
          lean={f > kickAt ? -7 : Math.sin(f / 11) * 3}
          bounce={f < fps * 1.1 ? Math.abs(Math.sin((f / 5) * Math.PI)) * -8 : Math.sin(f / 6) * 5}
        />
      </div>
    </Wrap>
  );
};

// ───────────────── 3. 원가 폭격
// ───────────────── 3. 재료 한 개짜리 장면 (b1~b5)
//
// 🔴 예전 Build는 재료 5개를 한 화면에 목록으로 깔고 **합계까지** 보여줬다.
//    그래서 19초에 답이 다 나오고 남은 절반을 볼 이유가 없었다(2편 완주 12.8%).
// 🔴 이제 한 장면에 **재료 하나**만 나온다. 합계는 여기서 절대 안 보여준다.
//    시청자가 머릿속으로 더하게 두는 게 이 구조의 전부다.
//
// 🔴 재료마다 반응이 달라야 4번 반복이 안 지겹다(2026-07-21).
//    ①깔림 ②가루 뒤집어씀 ③지글지글 ④방패 깨짐 ⑤퉤퉤
// 🔴 2인 체제(2026-07-21). 재료마다 **올마는 억지, 나마는 팩트 소품**을 든다.
//    이 대비가 없으면 4~5번 반복이 그냥 지겹다.
const ITEM_ACT = [
  { face: "화남", pose: "가리킴", note: "이건 프리미엄 닭이라고!", prop: "board", big: false },
  { face: "놀람", pose: "깜짝", note: "특제 가루거든?!", prop: "stamp", big: false },
  { face: "삐뚤", pose: "뒷목", note: "붓으로 바르는 게 이거야?", prop: "bee", big: true },
  { face: "삐뚤", pose: "뒷목", note: "붓으로 바르는 게 이거야?", prop: "bee", big: true },
  { face: "절규", pose: "털썩", note: "", prop: "pick", big: false },
];

export const Item = ({ i = 0 }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [name, price] = CFG.items[i];
  const act = ITEM_ACT[i] || ITEM_ACT[0];

  const AT = Math.round(fps * 0.35); // 재료가 떨어지는 시점
  const PRICE_AT = AT + Math.round(fps * 0.55); // 금액은 살짝 늦게 — 한 박자 쉬어야 읽힌다

  // 🔴 Wrap(flex 가운데정렬)에 요소가 많으면 세로가 넘쳐 잘린다(2026-07-21 재발).
  //    올마와 "1/5"가 통째로 사라졌다. 그래서 여기는 **절대 위치**로 박는다.
  const row = (top) => ({ position: "absolute", top, left: 0, right: 0, textAlign: "center" });

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop color={BG.build} />
      {act.big && <ActionLines color={C.red} opacity={0.28} spin={0} />}
      <Impact at={AT + 4} x="50%" y="34%" size={560} color="#999" />
      <Dust at={AT + 4} x="50%" y="38%" n={6} />

      {/* 몇 번째인지 — 5개 중 어디쯤인지 알아야 "아직 남았네" 하고 버틴다 */}
      <div style={{ ...row(150), opacity: fadeIn(f, 0, 4) }}>
        <Cap size={46} color="#7A6E58">
          {i + 1} / {CFG.items.length}
        </Cap>
      </div>

      {/* 재료 이름 — DB 표기 그대로 */}
      <div
        style={{
          ...row(280),
          opacity: fadeIn(f, AT, 3),
          translate: `0px ${drop(f, AT)}px`,
          scale: squash(f, AT),
        }}
      >
        <Punch size={72}>{name}</Punch>
      </div>

      {/* 🔴 재료 그림 — 위에서 쿵 떨어져 저마다 사고를 친다(2026-07-21 "아무것도 안 하는데?").
             글씨만 있으면 5초를 못 버틴다. */}
      <div
        style={{
          position: "absolute",
          top: 790,
          left: "50%",
          translate: `-50% ${drop(f, AT)}px`,
          scale: squash(f, AT),
          opacity: fadeIn(f, AT, 3),
        }}
      >
        <IngredientArt i={i} p={interpolate(f, [AT + 6, AT + 46], [0, 1], E)} />
      </div>

      {/* ④ 허니 간장소스 — 붓이 옆에서 같이 떨어진다. "붓으로 발라서"의 그 붓 */}
      {i === 3 && (
        <div
          style={{
            position: "absolute",
            top: 900,
            left: "50%",
            translate: `160px ${drop(f, AT + 4)}px`,
            rotate: `${interpolate(f, [AT + 10, AT + 30], [0, 62], E)}deg`,
            opacity: fadeIn(f, AT + 4, 3),
          }}
        >
          <Brush w={150} />
        </div>
      )}

      {/* 금액 — 이 장면의 보상 */}
      <div style={{ ...row(430), opacity: fadeIn(f, PRICE_AT, 4), scale: popIn(f, PRICE_AT) }}>
        <span
          style={{
            display: "inline-block",
            fontFamily: BLACK,
            fontSize: act.big ? 168 : 140,
            letterSpacing: -6,
            color: "#fff",
            background: act.big ? C.red : C.blue,
            borderRadius: 24,
            padding: "14px 46px 24px",
            boxShadow: `0 12px 0 ${act.big ? "#8E1109" : "#12468F"}`,
          }}
        >
          {won(price)}
        </span>
      </div>

      {act.note && (
        <div style={{ ...row(660), opacity: fadeIn(f, PRICE_AT + 10, 4) }}>
          <Cap size={54}>{act.note}</Cap>
        </div>
      )}

      {/* 🔴 올마(왼쪽) = 억지 / 나마(오른쪽) = 팩트 소품. 재료 그림과 안 겹치게 아래에 둔다 */}
      <div style={{ position: "absolute", bottom: 40, left: "50%", translate: "-520px 0px" }}>
        <Olma
          scale={0.92}
          face={act.face}
          pose={act.pose}
          head={interpolate(f, [AT + 4, AT + 8, AT + 18], [0, 16, 0], E) + Math.sin(f / 9) * 3}
          lean={interpolate(f, [AT + 4, AT + 9, AT + 20], [0, act.big ? -18 : 9, 0], E)}
          bounce={Math.sin(f / 4) * 5}
        />
      </div>
      <div style={{ position: "absolute", bottom: 40, left: "50%", translate: "-150px 0px" }}>
        <Nama
          scale={0.92}
          face="무표정"
          pose="가리킴위"
          glasses={0}
          holdR={(hx, hy) => <FactProp kind={act.prop} x={hx} y={hy} />}
        />
      </div>

      {/* 올마의 억지 — 나마 소품에 깨진다 */}
      {act.note && (
        <div style={{ position: "absolute", bottom: 690, left: 50, opacity: fadeIn(f, PRICE_AT + 6, 4) }}>
          <Cap size={44}>{act.note}</Cap>
        </div>
      )}
    </AbsoluteFill>
  );
};

// 나마가 드는 팩트 소품 — 재료마다 다르다
const FactProp = ({ kind, x, y }) => {
  switch (kind) {
    case "board":
      return <PriceBoard x={x + 60} y={y - 40} rot={-8} line1="수입산" line2="냉장" />;
    case "stamp":
      return <StampTool x={x + 30} y={y - 30} rot={-14} />;
    case "bee":
      return <BeeToy x={x + 50} y={y - 40} rot={-8} />;
    case "pick":
      return <Toothpick x={x + 20} y={y - 30} rot={-10} />;
    default:
      return null;
  }
};

// (구) 재료 5개를 한 화면에 몰아 보여주던 장면 — 2편까지 쓰던 것.
// 🔴 합계까지 보여줘서 완주율을 깎아먹었다. 지금은 안 쓰지만 비교용으로 남겨둔다.
export const Build = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const GAP = fps * 0.55;
  const at = (i) => Math.round(fps * 0.5 + i * GAP);
  const sumAt = at(CFG.items.length) + 4;

  const step = CFG.items.filter((_, i) => f >= at(i)).length;
  const FACE = ["무표정", "갸웃", "놀람", "화남", "절규"];
  const POSE = ["기본", "가리킴위", "깜짝", "털썩", "뒷목"];
  // 재료가 떨어질 때마다 올마가 짓눌린다
  const hitAt = step > 0 ? at(step - 1) : -99;
  const smash = interpolate(f, [hitAt + 5, hitAt + 9, hitAt + 16], [1, 0.84, 1], E);
  const sink = interpolate(f - at(0), [0, GAP * CFG.items.length], [0, 34], E);

  // 🔴 돈에 눌려 **점점 작아진다**(2026-07-21 지시).
  //    크게 시작(1.5) → 재료를 맞을수록 줄어들어 마지막엔 0.72까지.
  const SHRINK = [1.5, 1.28, 1.1, 0.92, 0.72];
  const bodyScale = SHRINK[Math.min(step, 4)];

  return (
    <Wrap gap={14} bg={BG.build}>
      {/* 재료가 떨어질 때마다 충격파 + 먼지 */}
      {CFG.items.map((_, i) => (
        <React.Fragment key={i}>
          <Impact at={at(i) + 5} x="50%" y={`${30 + i * 7}%`} size={520} color="#999" />
          <Dust at={at(i) + 5} x="50%" y={`${32 + i * 7}%`} n={5} />
        </React.Fragment>
      ))}

      <div style={{ scale: popIn(f) }}>
        <Punch size={70}>{L.buildTitle}</Punch>
      </div>

      <div style={{ width: "100%", maxWidth: 940, display: "flex", flexDirection: "column", gap: 12 }}>
        {CFG.items.map(([n, v], i) => (
          <div
            key={n}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 18,
              background: "#fff",
              border: `6px solid ${C.ink}`,
              borderRadius: 20,
              padding: "16px 30px",
              fontFamily: JUA,
              fontSize: 52,
              opacity: fadeIn(f, at(i), 3),
              translate: `0px ${drop(f, at(i))}px`,
              scale: squash(f, at(i)),
            }}
          >
            <span>{n}</span>
            <span style={{ fontFamily: BLACK, color: C.blue, whiteSpace: "nowrap" }}>{won(v)}</span>
          </div>
        ))}

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 18,
            background: C.yellow,
            border: `6px solid ${C.ink}`,
            borderRadius: 20,
            padding: "18px 30px",
            fontFamily: JUA,
            fontSize: 64,
            opacity: fadeIn(f, sumAt, 4),
            scale: popIn(f, sumAt),
          }}
        >
          <span>합계</span>
          <span style={{ fontFamily: BLACK, color: C.red, whiteSpace: "nowrap" }}>{won(cost)}</span>
        </div>
      </div>

      {/* 재료에 얻어맞아 점점 납작해진다.
          🔴 맞을 때마다 고개가 확 꺾이고 상체가 휘청여야 타격감이 산다 */}
      <div style={{ marginTop: 0, translate: `0px ${sink}px`, scale: smash }}>
        <Olma
          scale={bodyScale}
          face={FACE[Math.min(step, 4)]}
          pose={POSE[Math.min(step, 4)]}
          tilt={step >= 4 ? -10 : 0}
          // 맞은 직후 6프레임 동안 고개가 꺾였다 돌아온다
          head={interpolate(f, [hitAt + 4, hitAt + 8, hitAt + 18], [0, 16, 0], E) + Math.sin(f / 9) * 3}
          lean={interpolate(f, [hitAt + 4, hitAt + 9, hitAt + 20], [0, 9, 0], E) - step * 2}
          bounce={Math.sin(f / 4) * 5}
        />
      </div>
    </Wrap>
  );
};

// ───────────────── 4. 극대노
export const Climax = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();

  const CNT = fps * 0.7;
  const LEN = fps * 1.0;
  const shown = Math.round(interpolate(f, [CNT, CNT + LEN], [0, diff], { ...E, easing: Easing.out(Easing.cubic) }));
  const hit = CNT + LEN;
  const punch = interpolate(f, [hit, hit + 4, hit + 11], [1, 1.28, 1], E);

  // 🔴 sin 파동은 규칙적이라 "흔들린다"기보다 "떤다"로 보인다.
  //    random(seed)로 매 프레임 좌표를 튀게 해야 지진처럼 보인다(2026-07-21).
  //    🔴 여기에 scale을 걸면 자막 좌우가 잘린다. 이동·회전만 쓴다.
  const rage = f > hit;
  const decay = rage ? Math.max(0, 1 - (f - hit) / (fps * 2.2)) : 0;
  const shake = (random(`x${f}`) - 0.5) * 60 * decay;
  const shakeY = (random(`y${f}`) - 0.5) * 60 * decay;
  const shakeR = (random(`r${f}`) - 0.5) * 3 * decay;
  const flash = rage ? (0.2 + random(`f${f}`) * 0.16) * decay : 0;

  return (
    <AbsoluteFill style={{ translate: `${shake}px ${shakeY}px`, rotate: `${shakeR}deg` }}>
      <Backdrop color={BG.climax} />
      <AbsoluteFill style={{ background: C.red, opacity: flash }} />

      {/* 🔴 집중선 — 분노 순간 화면 전체가 돌아간다. 가운데는 비워서 자막을 안 덮는다 */}
      {rage && <ActionLines color={C.red} opacity={0.55 * decay} spin={13} />}
      <Bolt at={hit} x="16%" y="10%" size={160} />
      <Bolt at={hit + 3} x="84%" y="8%" size={140} />
      <Wrap gap={6}>
        <div style={{ opacity: fadeIn(f, 0) }}>
          <Cap size={50}>{L.climaxTop}</Cap>
        </div>
        <div style={{ opacity: fadeIn(f, 8), marginTop: 6 }}>
          <Punch size={66}>{L.climaxKick}</Punch>
        </div>
        <div
          style={{
            fontFamily: BLACK,
            fontSize: 224,
            color: C.red,
            letterSpacing: -12,
            lineHeight: 1,
            scale: punch,
            textShadow: `0 12px 0 ${C.ink}`,
          }}
        >
          {won(shown)}
        </div>
        {/* 🔴 캐릭터가 글씨에 비해 작았다. 키우고 주변에 분노 표시를 붙인다(2026-07-21) */}
        <div style={{ marginTop: 10, position: "relative" }}>
          {/* 🔴 분노는 팔을 휘저어야 보인다. 뒷목 포즈 대신 팔을 직접 흔든다.
              단, 각도가 -120~-75 구간이면 팔이 **얼굴 앞을 가로질러 입을 가린다**(2026-07-21).
              바깥쪽(양옆 위)으로만 휘젓게 범위를 잡는다. */}
          <Olma
            scale={1.6}
            face={rage ? "극대노" : "무표정"}
            armL={rage ? 58 + Math.sin(f / 2) * 32 : 0}
            armR={rage ? -58 - Math.sin(f / 2 + 1.7) * 32 : 0}
            tilt={rage ? Math.sin(f * 1.7) * 5 : 0}
            head={rage ? Math.sin(f / 1.8) * 14 : Math.sin(f / 9) * 3}
            lean={rage ? Math.sin(f / 2.6) * 11 : 0}
            bounce={rage ? Math.abs(Math.sin(f / 2.4)) * -22 : Math.sin(f / 6) * 5}
          />

          {/* 🔴 핏대·화남 표시는 **이모지 대신 SVG**로 그린다.
              이모지는 렌더 환경의 폰트에 따라 별표처럼 깨져 나온다(2026-07-21 확인). */}
          {rage &&
            [
              [10, 60, -16, 1.0],
              [500, 84, 18, 0.85],
              [110, -10, -6, 0.7],
            ].map(([x, y, rot, sc], i) => (
              <svg
                key={i}
                width={120}
                height={120}
                viewBox="0 0 100 100"
                style={{
                  position: "absolute",
                  left: x,
                  top: y,
                  rotate: `${rot}deg`,
                  scale: sc * (0.7 + decay * 0.5),
                  opacity: decay,
                }}
              >
                {/* 만화식 분노 마크(井 모양) */}
                <path
                  d="M30 22 L22 78 M58 22 L50 78 M16 40 L74 34 M12 62 L70 56"
                  stroke={C.red}
                  strokeWidth={13}
                  strokeLinecap="round"
                  fill="none"
                />
              </svg>
            ))}
        </div>
      </Wrap>
    </AbsoluteFill>
  );
};

// ───────────────── 5. 급발진 정적 — 이 영상의 웃음 포인트
export const Twist = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  // 앞 장면의 붉은 분노에서 흑백 정적으로 뚝 떨어진다.
  // 🔴 얼굴로 **냅다 돌진**해야 현타가 산다. 스프링이라 멈출 때 띠용 하고 튕긴다.
  //    🔴 실측 결과 2.2배도 과했다 — 캐릭터가 자막을 덮고 치킨이 밖으로 나간다.
  //       1.75가 "얼굴 클로즈업 + 치킨 보임 + 자막 안 가림"이 다 되는 한계선(2026-07-21).
  const zoom = spring({ fps, frame: f, config: { damping: 12, stiffness: 200 }, from: 1, to: 1.75 });
  const gray = interpolate(f, [0, 6], [1, 0], E); // 잠깐 흑백이었다가 색이 돌아옴
  // 우물우물 씹는 턱 움직임
  const chew = Math.sin(f / 3.2) * 5;

  // 🔴 치킨을 **입으로 가져가는** 동작(2026-07-21 지시).
  //    팔이 아래에서 입가로 올라오고, 치킨도 같이 따라 올라온다.
  const EAT = fps * 0.5;
  // 🔴 포크를 정교하게 움직이려다 계속 어긋났다(2026-07-21 "포크 에러가 많다").
  //    대신 **눈 감고 입 우물거리는 얼굴 연기**로 간다. 그게 훨씬 잘 읽힌다.
  //    팔은 살짝 든 채로 두고 크게 안 움직인다.
  const armR = interpolate(f, [EAT, EAT + fps * 0.6], [-20, -62], {
    ...E,
    easing: Easing.out(Easing.cubic),
  });
  // 🔴 포크는 **손에 붙여서** 그린다(Olma의 holdR). 밖에서 좌표로 맞추면
  //    팔이 회전할 때마다 어긋난다(2026-07-21 "포크 에러가 많다").
  //    팔 각도(armR)만 움직이면 포크·닭이 알아서 따라온다.
  const IN = EAT + fps * 0.7; // 입에 닿는 시각
  const OUT = IN + fps * 0.4; // 입에서 빠지는 시각
  // 물고 나면 닭은 없어진다(먹음). 빈 포크만 남는다
  const eaten = f > OUT;

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop color={BG.twist} drift={false} />
      {/* 🔴 줌은 **캐릭터·치킨에만** 건다. 자막까지 같이 키우면 화면 밖으로 나간다. */}

      {/* 🔴 화면 가운데로 옮기고 크게(2026-07-21 지시) */}
      <AbsoluteFill style={{ scale: zoom, transformOrigin: "center 40%" }}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 250 }}>
          {/* 씹을 때 고개도 같이 우물우물 */}
          <div style={{ translate: `0px ${chew}px`, filter: `grayscale(${gray})` }}>
            <Olma
              scale={1.35}
              face="황홀"
              armR={armR}
              tilt={-4}
              head={Math.sin(f / 3.2) * 5}
              lean={Math.sin(f / 7) * 3}
              // 🔴 입이 우물우물 — 씹는 연기의 핵심
              chew={f > IN ? f / 3.2 : 0}
              // 포크는 손에 든 채로. 닭은 먹고 나면 사라진다
              holdR={(hx, hy) => <ForkInHand x={hx} y={hy} eaten={eaten} />}
            />
          </div>
        </AbsoluteFill>
      </AbsoluteFill>

      {/* 🔴 별만으로는 밋밋했다(2026-07-21). **하트**가 떠올라야 "맛있다"가 읽힌다.
          캐릭터보다 **나중에** 그려야 앞에 뜬다. 뒤에 두면 몸에 가린다. */}
      <Hearts at={Math.round(IN)} x="50%" y="42%" n={10} />

      {/* 🔴 자막이 작아서 안 보였다(2026-07-21). 이 장면 자막이 이 영상의 펀치라인이라
          제일 크고 확실하게 박혀야 한다. 노란 형광펜으로 받쳐 눈에 꽂는다. */}
      <div
        style={{
          position: "absolute",
          bottom: 300,
          width: "100%",
          textAlign: "center",
          opacity: fadeIn(f, fps * 1.1, 10),
          scale: popIn(f, Math.round(fps * 1.1)),
        }}
      >
        <span
          style={{
            position: "relative",
            display: "inline-block",
            fontFamily: BLACK,
            // 🔴 문구가 길어지면 화면 폭(1080)을 넘는다. 좌우 여백이 남는 크기로.
            fontSize: 100,
            color: C.ink,
            letterSpacing: -5,
            padding: "0 20px",
          }}
        >
          <span
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 16,
              height: "44%",
              background: C.yellow,
              borderRadius: 8,
              zIndex: 0,
            }}
          />
          <span style={{ position: "relative", zIndex: 1 }}>{L.twist}</span>
        </span>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 170,
          width: "100%",
          textAlign: "center",
          opacity: fadeIn(f, fps * 2.0, 8),
        }}
      >
        <Punch size={74} bg="#555">{L.twistSub}</Punch>
      </div>
    </AbsoluteFill>
  );
};

// ───────────────── 6. 마무리 — 근데 사장님도 안 남는대
export const Close = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const kickAt = fps * 1.6;
  return (
    // 🔴 Wrap(가운데 정렬 flex)에 요소가 많으면 세로가 넘쳐 위아래가 잘린다(2026-07-21).
    //    마무리 장면은 요소가 6개라 **절대 위치로 직접 배치**하는 게 안전하다.
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Backdrop color={BG.close} />
      {/* "이 돈 어디감?"에서 당황 — 땀방울 */}
      <Sweat at={kickAt} x="62%" y="42%" />
      <Sweat at={kickAt + 8} x="36%" y="44%" flip />

      {/* 위 — 문구 2줄 */}
      <div style={{ position: "absolute", top: 210, width: "100%", textAlign: "center" }}>
        <div style={{ opacity: fadeIn(f, 0, 9) }}>
          <Punch size={78}>{L.closeTop}</Punch>
        </div>
        <div style={{ marginTop: 16, opacity: fadeIn(f, fps * 0.6) }}>
          <Cap size={40} color="#555">{L.closeSub}</Cap>
        </div>
      </div>

      {/* 가운데 — 어깨 으쓱했다가 "이 돈 어디감?"에서 화들짝 */}
      <div style={{ position: "absolute", top: 470, left: "50%", translate: "-50% 0px", scale: popIn(f, 4) }}>
        <Olma
          scale={1.25}
          face={f > kickAt ? "놀람" : "갸웃"}
          pose={f > kickAt ? "깜짝" : "으쓱"}
          head={f > kickAt ? Math.sin(f / 2.6) * 9 : Math.sin(f / 8) * 6}
          lean={f > kickAt ? Math.sin(f / 3.4) * 6 : Math.sin(f / 10) * 3}
          bounce={f > kickAt ? Math.abs(Math.sin(f / 3)) * -14 : Math.sin(f / 5) * 7}
        />
      </div>

      {/* 아래 — 한 방 문구 + 사이트 + 면책 */}
      <div style={{ position: "absolute", bottom: 150, width: "100%", textAlign: "center" }}>
        <div
          style={{
            fontFamily: BLACK,
            fontSize: 96,
            color: C.red,
            letterSpacing: -5,
            opacity: fadeIn(f, kickAt, 6),
            scale: popIn(f, kickAt),
            textShadow: `0 7px 0 ${C.ink}`,
          }}
        >
          {L.closeKick}
        </div>
        <div
          style={{
            display: "inline-block",
            fontFamily: BLACK,
            fontSize: 68,
            color: "#fff",
            background: C.ink,
            padding: "12px 38px",
            borderRadius: 20,
            letterSpacing: -2,
            marginTop: 22,
            opacity: fadeIn(f, kickAt + 12),
          }}
        >
          {CFG.site}
        </div>
        <div
          style={{
            fontFamily: JUA,
            fontSize: 27,
            color: "#8A8A8A",
            lineHeight: 1.5,
            marginTop: 20,
            opacity: fadeIn(f, kickAt + 20),
          }}
        >
          {CFG.disc.split("\n").map((l, i) => (
            <div key={i}>{l}</div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
