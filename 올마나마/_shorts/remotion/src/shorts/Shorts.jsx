// 쇼츠 전체 조립 (2026-07-21 재구성)
//
// <Sequence>로 구간을 나누면 그 안의 컴포넌트는 자기 구간 0프레임부터 다시 센다.
// → 장면끼리 시간이 안 섞인다.
import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { Hook, Item } from "./Scenes";
import { Greet } from "./Greet";
import {
  AskScene, BoomScene, EatScene, LoopScene, RevealScene, ShockScene,
} from "./Scenes2";
import { Sound } from "./Sound";
import { C, T, TOTAL } from "./config";

// 🔴 3편부터 **올마·나마 2인 체제**다(2026-07-21).
//    올마=억지·폭발 / 나마=덤덤·팩트. 장면마다 이 대비가 있어야 반복이 안 지겹다.
// 🔴 재료 합계는 RevealScene(36초)까지 절대 안 보여준다 = 지연된 보상.
//    2편은 19초에 다 까서 완주 12.8%로 끝났다.
// 🔴 앞 두 장면(인사 → 훅)은 **매 편 고정 시그니처**다. 갈아엎지 말 것(2026-07-21 원복).
//    박치기 Greet2·썸네일 CardScene은 승인 전까지 쓰지 않는다.
const SCENES = [
  { C: Greet, from: T.greet, name: "인사(고정)" },
  { C: Hook, from: T.card, name: "훅 영수증+배달세트(고정·썸네일)" },
  { C: EatScene, from: T.eat, name: "먹방→손등 찰싹" },
  { C: ShockScene, from: T.hook, name: "영수증 충격" },
  { C: () => <Item i={0} />, from: T.b1, name: "① 닭 정육" },
  { C: () => <Item i={1} />, from: T.b2, name: "② 브레딩믹스" },
  { C: () => <Item i={3} />, from: T.b3, name: "③④ 식용유+허니소스" },
  { C: () => <Item i={4} />, from: T.b5, name: "⑤ 치킨무" },
  { C: RevealScene, from: T.climax, name: "합계공개 + 정적" },
  { C: BoomScene, from: T.boom, name: "화산 폭발" },
  { C: AskScene, from: T.close, name: "남은 돈 어디로" },
  { C: LoopScene, from: T.loop, name: "댓글 유도 → 루프" },
];

// 장면 전환 — 🔴 60px 스르륵은 선비 같아서 쇼츠에선 바로 넘긴다(2026-07-21).
//    화면 밖(1500px)에서 날아와 스프링으로 통통 튕기며 꽂힌다. 사람이 못 하는 걸 하는 게 애니메이션.
// 🔴 CSS transition 금지 — 렌더에서 어긋난다. 전부 프레임 계산.
const Turn = ({ dur, children, noEnter = false }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 등장 — 아래에서 날아차기
  const inY = noEnter
    ? 0
    : spring({ fps, frame: f, config: { damping: 10, mass: 1.2, stiffness: 180 }, from: 1500, to: 0 });

  // 퇴장 — 위로 냅다 던짐.
  // 🔴 dur이 짧으면 f-(dur-8)이 곧바로 양수가 돼 시작하자마자 튕겨나간다. 길이 가드 필수.
  const outY =
    dur > 20
      ? spring({ fps, frame: f - (dur - 8), config: { damping: 15, stiffness: 250 }, from: 0, to: -1500 })
      : 0;

  return (
    <AbsoluteFill
      style={{
        opacity: noEnter ? 1 : Math.min(f / 3, 1),
        translate: `0px ${inY + outY}px`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

// bgm=false → 틱톡·인스타·네이버클립용(외부 음원은 매칭돼 음소거된다)
export const Shorts = ({ bgm = true }) => {
  const { fps } = useVideoConfig();
  const sec = (s) => Math.round(s * fps);

  return (
    // 🔴 배경색은 장면마다 다르다(Scenes.jsx의 Backdrop). 여기선 전환 중 틈이 비지 않게만 깐다
    <AbsoluteFill style={{ background: C.bg, fontFamily: "'Malgun Gothic','맑은 고딕',sans-serif" }}>
      {SCENES.map((s, i) => {
        const end = i + 1 < SCENES.length ? SCENES[i + 1].from : TOTAL;
        const dur = sec(end - s.from);
        const Comp = s.C;
        return (
          <Sequence key={i} name={s.name} from={sec(s.from)} durationInFrames={dur}>
            <Turn dur={dur} noEnter={i === 0}>
              <Comp />
            </Turn>
          </Sequence>
        );
      })}

      <Sound bgm={bgm} />
    </AbsoluteFill>
  );
};
