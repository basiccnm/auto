// 영상 길이 계산을 한 곳에 모아둔 파일.
// Root.jsx(전체 길이)와 Short.jsx(각 장면 위치)가 같은 값을 써야 하므로 공유한다.
//
// 길이 기준: 음성(props.audio)이 있으면 실제 음성 길이에 맞춘다.
// 음성이 아직 없으면 글자 수로 대충 추정한다(스튜디오 미리보기용).

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;

// 대사가 끝나자마자 컷이 넘어가면 급해 보여서 뒤에 약간 여유를 준다.
const PAD_SEC = 0.15;

const framesFor = (seconds) => Math.max(1, Math.round(seconds * FPS));

// 음성이 없을 때만 쓰는 추정치. 한국어는 대략 초당 6~7글자.
const estimate = (text) => Math.min(3.5, Math.max(2.0, text.length * 0.15));

export function buildTimeline(props) {
  const { hook, scenes, cta, audio } = props;

  const hookSec = audio?.hook ? audio.hook.duration + PAD_SEC : 3;
  const ctaSec = audio?.cta ? audio.cta.duration + PAD_SEC + 0.6 : 3.5;

  const hookFrames = framesFor(Math.max(2.5, hookSec));
  let cursor = hookFrames;

  const sceneBlocks = scenes.map((scene, i) => {
    const sec = audio?.scenes?.[i]
      ? audio.scenes[i].duration + PAD_SEC
      : estimate(scene.narration);
    const durationInFrames = framesFor(sec);
    const block = {
      ...scene,
      index: i,
      from: cursor,
      durationInFrames,
      audioSrc: audio?.scenes?.[i]?.src ?? null,
    };
    cursor += durationInFrames;
    return block;
  });

  const ctaFrames = framesFor(Math.max(3, ctaSec));

  return {
    hook: {
      from: 0,
      durationInFrames: hookFrames,
      audioSrc: audio?.hook?.src ?? null,
    },
    scenes: sceneBlocks,
    cta: {
      from: cursor,
      durationInFrames: ctaFrames,
      audioSrc: audio?.cta?.src ?? null,
    },
    totalFrames: cursor + ctaFrames,
  };
}
