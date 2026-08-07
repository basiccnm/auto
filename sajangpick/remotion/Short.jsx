import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { buildTimeline } from './timing.js';

// 브랜드 색. 흰 배경 + 주황 포인트 + 진한 회색 글자.
const ORANGE = '#F97316';
const INK = '#1A1A1A';
const PAPER = '#FFFFFF';
const CREAM = '#FFF7ED';

const FONT = "'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif";

// 화면 하단 20%(=384px)는 플랫폼 UI가 가리므로 글자를 넣지 않는다.
const SAFE_BOTTOM = 400;

// 나레이션 음성. 아직 음성을 안 만든 상태(스튜디오 미리보기 등)면 조용히 넘어간다.
const Narration = ({ src }) => (src ? <Audio src={staticFile(src)} /> : null);

// 배경음악. 음성 대비 약 -18dB(≈0.125). loop라 영상 길이와 무관하게 깔린다. (회신04 §B.3)
const Bgm = ({ src }) => (src ? <Audio src={staticFile(src)} volume={0.125} loop /> : null);

// 자막을 단어 단위로 쪼개 하나씩 톡톡 떠오르게 한다. (회신04 §B.2 — 과하지 않게)
const WordPop = ({ text, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(' ');
  return (
    <div style={style}>
      {words.map((w, i) => {
        const s = spring({
          frame,
          fps,
          delay: i * 3, // 단어당 0.1초 간격
          config: { damping: 200 },
          durationInFrames: 10,
        });
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              opacity: s,
              transform: `translateY(${(1 - s) * 26}px)`,
              marginRight: '0.24em',
            }}
          >
            {w}
          </span>
        );
      })}
    </div>
  );
};

const base = {
  fontFamily: FONT,
  color: INK,
  fontWeight: 900,
  letterSpacing: '-0.03em',
  lineHeight: 1.22,
  textAlign: 'center',
  // 한국어는 이걸 안 주면 "이거" 가 "이/거" 처럼 단어 중간에서 잘린다.
  wordBreak: 'keep-all',
  overflowWrap: 'break-word',
};

// 후킹 문구가 길면 글자를 줄여서 3줄 이상으로 쏟아지지 않게 한다.
const hookFontSize = (text) => (text.length <= 12 ? 140 : text.length <= 16 ? 118 : 100);

// 흰 배경 위를 천천히 흐르는 주황 도형들.
// 제품 이미지가 없어도 화면이 죽어 보이지 않게 하는 장치.
const Paper = ({ seed = 0, drift = 0 }) => (
  <AbsoluteFill style={{ backgroundColor: PAPER, overflow: 'hidden' }}>
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${PAPER} 55%, ${CREAM} 100%)` }} />
    <div
      style={{
        position: 'absolute',
        top: -320 + seed * 40,
        right: -280,
        width: 900,
        height: 900,
        borderRadius: '50%',
        background: ORANGE,
        opacity: 0.1,
        transform: `translateY(${drift * 60}px)`,
      }}
    />
    <div
      style={{
        position: 'absolute',
        bottom: -420,
        left: -300,
        width: 1000,
        height: 1000,
        borderRadius: '50%',
        background: ORANGE,
        opacity: 0.07,
        transform: `translateY(${-drift * 40}px)`,
      }}
    />
  </AbsoluteFill>
);

// 첫 3초. 컷을 빠르게 끊어서 스크롤을 멈추게 하는 구간.
// 흰 화면과 주황 화면을 번갈아 때려서 시선을 잡는다.
const Hook = ({ text, durationInFrames }) => {
  const frame = useCurrentFrame();
  const CUTS = 6;
  const per = durationInFrames / CUTS;
  const cut = Math.min(CUTS - 1, Math.floor(frame / per));
  const inCut = frame - cut * per;
  const inverted = cut % 2 === 1;

  const pop = interpolate(inCut, [0, per * 0.4], [1.16, 1], { extrapolateRight: 'clamp' });
  const tilt = cut % 2 === 0 ? -2 : 2;

  return (
    <AbsoluteFill style={{ backgroundColor: inverted ? ORANGE : PAPER }}>
      {!inverted && <Paper seed={cut} drift={cut / CUTS} />}
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 80px',
          paddingBottom: SAFE_BOTTOM,
        }}
      >
        <div
          style={{
            ...base,
            color: inverted ? PAPER : INK,
            fontSize: hookFontSize(text),
            transform: `scale(${pop}) rotate(${tilt}deg)`,
          }}
        >
          {text}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const ProductPill = ({ name }) => (
  <div
    style={{
      position: 'absolute',
      top: 130,
      left: 90,
      right: 90,
      display: 'flex',
      justifyContent: 'center',
    }}
  >
    <div
      style={{
        fontFamily: FONT,
        fontSize: 32,
        fontWeight: 700,
        color: ORANGE,
        border: `4px solid ${ORANGE}`,
        borderRadius: 999,
        padding: '16px 40px',
        maxWidth: 860,
        textAlign: 'center',
        lineHeight: 1.3,
        backgroundColor: 'rgba(255,255,255,0.9)',
      }}
    >
      {name}
    </div>
  </div>
);

// 지금 몇 번째 장면인지 보여주는 점. 끝이 보이면 이탈이 줄어든다.
const Dots = ({ index, total }) => (
  <div
    style={{
      position: 'absolute',
      top: 300,
      left: 0,
      right: 0,
      display: 'flex',
      justifyContent: 'center',
      gap: 16,
    }}
  >
    {Array.from({ length: total }).map((_, i) => (
      <div
        key={i}
        style={{
          width: i === index ? 56 : 18,
          height: 18,
          borderRadius: 999,
          backgroundColor: i === index ? ORANGE : 'rgba(249,115,22,0.25)',
        }}
      />
    ))}
  </div>
);

const Scene = ({ scene, productName, total, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 12 });
  const progress = interpolate(frame, [0, durationInFrames], [0, 1], { extrapolateRight: 'clamp' });
  // 자막 뒤 주황 형광펜이 왼쪽에서 오른쪽으로 그어진다.
  const marker = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 18, delay: 4 });

  return (
    <AbsoluteFill>
      <Paper seed={scene.index} drift={progress} />

      {/* 배경에 크게 깔리는 장면 번호 */}
      <div
        style={{
          position: 'absolute',
          top: 430,
          left: 0,
          right: 0,
          textAlign: 'center',
          fontFamily: FONT,
          fontSize: 460,
          fontWeight: 900,
          color: ORANGE,
          opacity: 0.09,
          lineHeight: 1,
          transform: `scale(${interpolate(progress, [0, 1], [1, 1.06])})`,
        }}
      >
        {scene.index + 1}
      </div>

      <ProductPill name={productName} />
      <Dots index={scene.index} total={total} />

      {/* 제품 이미지가 없는 동안은 자막을 화면 중앙에 둔다.
          아래쪽에 붙이면 가운데가 텅 비어서 미완성처럼 보인다.
          이미지가 붙으면 이 블록을 하단으로 되돌린다. */}
      <div
        style={{
          position: 'absolute',
          left: 70,
          right: 70,
          top: 360,
          bottom: SAFE_BOTTOM,
          display: 'flex',
          alignItems: 'center',
          opacity: enter,
          transform: `translateY(${interpolate(enter, [0, 1], [50, 0])}px)`,
        }}
      >
        <div style={{ position: 'relative', display: 'inline-block', width: '100%' }}>
          {/* 형광펜 */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              bottom: 10,
              height: 62,
              backgroundColor: ORANGE,
              opacity: 0.3,
              borderRadius: 8,
              transformOrigin: 'left center',
              transform: `scaleX(${marker}) rotate(-1deg)`,
            }}
          />
          <WordPop text={scene.caption} style={{ ...base, fontSize: 96, position: 'relative' }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Cta = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 15 });
  const pulse = 1 + Math.sin(frame / 7) * 0.015;
  // 링크 안내 화살표가 아래위로 살랑거린다 (회신04 §B.4)
  const bob = Math.sin(frame / 5) * 10;

  return (
    <AbsoluteFill style={{ backgroundColor: ORANGE }}>
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 90px',
          paddingBottom: SAFE_BOTTOM + 60,
          gap: 48,
          opacity: enter,
        }}
      >
        <div
          style={{
            ...base,
            color: PAPER,
            fontSize: 104,
            transform: `scale(${pulse}) translateY(${interpolate(enter, [0, 1], [40, 0])}px)`,
          }}
        >
          {text}
        </div>
        <div
          style={{
            fontFamily: FONT,
            fontSize: 46,
            fontWeight: 800,
            color: ORANGE,
            backgroundColor: PAPER,
            borderRadius: 999,
            padding: '22px 52px',
          }}
        >
          댓글로 알려주세요
        </div>
      </AbsoluteFill>

      {/* 링크 유도 — 세이프존 바로 위 (회신04 §B.4) */}
      <div
        style={{
          position: 'absolute',
          bottom: SAFE_BOTTOM + 20,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 6,
          opacity: enter,
        }}
      >
        <div
          style={{
            fontFamily: FONT,
            fontSize: 44,
            fontWeight: 900,
            color: '#7A2E00',
            backgroundColor: '#FFD75E',
            borderRadius: 16,
            padding: '18px 44px',
          }}
        >
          제품 링크는 더보기에서 확인
        </div>
        <div
          style={{
            fontSize: 64,
            color: '#FFD75E',
            fontWeight: 900,
            transform: `translateY(${bob}px)`,
          }}
        >
          ▼
        </div>
      </div>

      {/* 쿠팡 파트너스 고지. 영상에도 반드시 들어가야 한다. */}
      <div
        style={{
          position: 'absolute',
          bottom: 56,
          left: 70,
          right: 70,
          fontFamily: FONT,
          fontSize: 25,
          color: 'rgba(255,255,255,0.75)',
          textAlign: 'center',
        }}
      >
        이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 수수료를 제공받습니다.
      </div>
    </AbsoluteFill>
  );
};

export const Short = (props) => {
  const { hook, cta, product_name } = props;
  const timeline = buildTimeline(props);
  const total = timeline.scenes.length;

  return (
    <AbsoluteFill style={{ backgroundColor: PAPER }}>
      <Bgm src={props.audio?.bgm} />

      <Sequence from={timeline.hook.from} durationInFrames={timeline.hook.durationInFrames}>
        <Narration src={timeline.hook.audioSrc} />
        <Hook text={hook} durationInFrames={timeline.hook.durationInFrames} />
      </Sequence>

      {timeline.scenes.map((scene) => (
        <Sequence key={scene.index} from={scene.from} durationInFrames={scene.durationInFrames}>
          <Narration src={scene.audioSrc} />
          <Scene
            scene={scene}
            productName={product_name}
            total={total}
            durationInFrames={scene.durationInFrames}
          />
        </Sequence>
      ))}

      <Sequence from={timeline.cta.from} durationInFrames={timeline.cta.durationInFrames}>
        <Narration src={timeline.cta.audioSrc} />
        <Cta text={cta} />
      </Sequence>
    </AbsoluteFill>
  );
};
