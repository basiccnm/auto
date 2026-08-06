// 소리 — BGM + 효과음
//
// 🔴 예전엔 mp4를 다 뽑은 뒤 mix.py로 얹었다. `-shortest` 때문에 33초가 23.8초로 잘렸다.
//    Remotion은 <Audio>를 타임라인에 올리면 렌더할 때 같이 들어간다. 잘릴 일이 없다.
//
// 🔴 bgm=false = 틱톡·인스타·네이버클립용.
//    유튜브 오디오보관함 음악은 **유튜브에서만** 안전하다. 다른 플랫폼은 외부 음원을
//    매칭해 영상을 음소거시킨다(2026-07-21 틱톡에서 실제로 걸림).
//    효과음(딱·동전·쿵)은 음악이 아니라 안 걸리므로 그대로 둔다.
import React from "react";
import { Audio } from "@remotion/media";
import { Sequence, staticFile, useVideoConfig } from "remotion";
import { BUILD_AT, CFG, T, TOTAL } from "./config";

const f = (name) => staticFile(`sfx/${name}`);

// 한 방 효과음. 🔴 dur로 끊어야 한다 — coins.mp3는 원본이 23초라 다음 장면까지 달그락거린다.
const Hit = ({ t, src, vol = 1, name, dur = 2.5 }) => {
  const { fps } = useVideoConfig();
  return (
    <Sequence name={name || src} from={Math.round(t * fps)} durationInFrames={Math.round(dur * fps)} layout="none">
      <Audio src={f(src)} volume={vol} />
    </Sequence>
  );
};

// 숫자가 올라가는 동안 "띠리리리" — 짧은 클릭을 촘촘히 겹쳐 쌓는다
const CountUp = ({ from, len, step = 0.075, vol = 0.3 }) => (
  <>
    {Array.from({ length: Math.floor(len / step) }, (_, i) => (
      <Hit key={i} t={from + i * step} src="click.mp3" vol={vol} dur={0.4} name={`카운트${i}`} />
    ))}
  </>
);

export const Sound = ({ bgm = true }) => {
  const { fps } = useVideoConfig();
  // 🔴 재료가 한 장면씩 쪼개졌다(2026-07-21). 예전엔 T.build 한 곳에서 0.62초 간격으로
  //    다다닥 떨어졌지만, 이제 b1~b5 각 장면 시작 직후에 하나씩 난다.
  //    ⚠️ 여기 소리 배치는 **임시**다. 새 옹알이·BGM을 만든 뒤 한 번에 다시 짠다.
  const rowAt = (i) => BUILD_AT[i] + 0.35;
  const sumAt = T.climax + 2.2; // 합계는 극대노에서 처음 공개된다

  return (
    <>
      {/* ── BGM ── 🔴 급발진 정적(T.twist)에서 **완전히 끊는다.** 그 정적이 이 영상의 핵심이다.
             🔴 볼륨은 낮게. 옹알이가 주인공이고 BGM은 바닥에 깔리는 것뿐이다(2026-07-21 지시) */}
      {/* 🔴 합계가 뜨는 순간(T.climax+1.2초)부터 1.5초 **완전 정적**.
             이 영상 최고의 웃음 포인트라 소리를 칼같이 끊어야 한다. */}
      {bgm && (
        <Sequence name="BGM" from={0} durationInFrames={Math.round((T.climax + 1.2) * fps)} layout="none">
          <Audio src={f("bgm.mp3")} volume={0.09} loop />
        </Sequence>
      )}
      {/* 정적이 끝나고 화산부터 다시 */}
      {bgm && (
        <Sequence
          name="BGM 후반"
          from={Math.round(T.boom * fps)}
          durationInFrames={Math.round((TOTAL - T.boom) * fps)}
          layout="none"
        >
          <Audio src={f("bgm_twist.mp3")} volume={0.11} loop />
        </Sequence>
      )}

      {/* 🔴 옹알이 — 알아들을 수 없는 소리 + 자막. 감정별 5개를 68편 내내 돌려쓴다.
             또박또박 읽으면 자막과 겹쳐서 재미가 없다. */}

      {/* 훅 — 영수증이 쿵 떨어지고 도장이 찍힌다 */}
      <Hit t={T.hook + 0.25} src="paper.mp3" vol={0.55} dur={1.2} name="영수증 착지" />
      <Hit t={T.hook + 0.7} src="punch.mp3" vol={0.7} dur={1.0} name="도장 쾅" />
      <Hit t={T.hook + 0.85} src="babble_surprise.mp3" vol={0.85} dur={1.5} name="옹알이 뺙" />

      {/* 인사 — 박치기 */}
      <Hit t={T.greet + 1.05} src="punch.mp3" vol={0.6} dur={0.9} name="박치기" />
      <Hit t={T.greet + 1.2} src="babble_surprise.mp3" vol={0.8} dur={1.3} name="옹알이 뺙" />

      {/* 썸네일 카드 */}
      <Hit t={T.card + 0.2} src="sting.mp3" vol={0.7} dur={1.6} name="카드 등장" />

      {/* 먹방 → 손등 찰싹 */}
      <Hit t={T.eat + 1.9} src="punch.mp3" vol={0.65} dur={0.8} name="손등 찰싹" />
      <Hit t={T.eat + 2.0} src="babble_ouch.mp3" vol={0.85} dur={1.6} name="옹알이 아야" />

      {/* 원가 폭격 — 한 줄마다 딱. 중간에 한 번 "윽 아야" */}
      {CFG.items.map((_, i) => (
        <Hit key={i} t={rowAt(i)} src="tick.mp3" vol={0.62} name={`재료${i + 1}`} />
      ))}
      <Hit t={rowAt(1) + 0.15} src="babble_ouch.mp3" vol={0.85} dur={2.0} name="옹알이 윽아야" />
      {/* ④ 허니 간장소스 = 방패 깨지는 자리. 여기만 소리를 세게 준다 */}
      <Hit t={rowAt(3) + 0.1} src="crash.mp3" vol={0.6} dur={1.6} name="방패 깨짐" />
      <Hit t={rowAt(3) + 0.4} src="babble_point.mp3" vol={0.9} dur={2.4} name="옹알이 고작 이거야" />
      <Hit t={sumAt} src="coins.mp3" vol={0.7} dur={1.5} name="합계 공개" />

      {/* 극대노 — 띠리리리 올라가다 폭발 */}
      <CountUp from={T.climax + 0.7} len={1.0} />
      <Hit t={T.climax + 1.7} src="boom.mp3" vol={0.8} dur={2.2} name="폭발" />
      <Hit t={T.climax + 1.75} src="crash.mp3" vol={0.5} name="충격" />
      <Hit t={T.climax + 1.95} src="babble_rage.mp3" vol={0.9} dur={2.6} name="옹알이 극대노" />

      {/* 🔴 급발진 정적 — 진입 순간 "끼기긱"으로 BGM을 잘라내는 느낌을 준다.
             그다음엔 **씹는 소리만** 남긴다. 그 대비가 웃음 포인트다 */}
      {/* 🔴 정적 — 합계가 뜨는 T.climax+1.2 부터 1.5초. **여기엔 아무 소리도 넣지 않는다.**
             끼기긱으로 잘라내는 느낌만 준다. */}
      <Hit t={T.climax + 1.1} src="scratch.mp3" vol={0.6} dur={1.0} name="끼기긱(정적 진입)" />

      {/* 마무리 — 영수증 씹기 */}
      <Hit t={T.close + 1.4} src="chew.mp3" vol={0.65} dur={3.0} name="영수증 씹는 소리" />
      <Hit t={T.close + 1.8} src="babble_yum.mp3" vol={0.85} dur={2.4} name="옹알이 뇸뇸" />

      {/* 마무리 */}
      <Hit t={T.close} src="sting.mp3" vol={0.6} name="마무리" />
      <Hit t={T.close + 1.6} src="pop.mp3" vol={0.5} name="화들짝" />
      <Hit t={T.close + 1.75} src="babble_cheer.mp3" vol={0.85} dur={1.5} name="옹알이 뺘뱌" />
    </>
  );
};
