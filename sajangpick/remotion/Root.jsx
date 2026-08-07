import React from 'react';
import { Composition } from 'remotion';
import { Short } from './Short.jsx';
import { buildTimeline, FPS, WIDTH, HEIGHT } from './timing.js';
// 기본값은 고정 샘플을 쓴다.
// inbox의 기획서를 직접 import하면, 그 파일이 done/으로 옮겨진 뒤 빌드가 깨진다.
import defaultProps from './sample.json';

export const RemotionRoot = () => (
  <Composition
    id="Short"
    component={Short}
    width={WIDTH}
    height={HEIGHT}
    fps={FPS}
    durationInFrames={900}
    defaultProps={defaultProps}
    // 기획서마다 장면 수가 다르므로 영상 길이를 props에서 계산한다.
    calculateMetadata={({ props }) => ({
      durationInFrames: buildTimeline(props).totalFrames,
    })}
  />
);
