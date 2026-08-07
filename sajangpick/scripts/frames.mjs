// 렌더가 끝난 영상에서 검수용 프레임 6장을 뽑아 통신 폴더에 올린다. (회신01)
//
// 왜 필요한가: 웹 Claude는 드라이브에서 mp4를 읽지 못하고 png는 읽는다.
// 그래서 화면 품질 검수는 프레임 이미지로만 가능하다.
//
// mp4에서 잘라내지 않고 Remotion으로 그 프레임을 다시 그린다.
// ffmpeg 추가 설치가 필요 없고, 압축 손실이 없어 자막 가독성을 정확히 볼 수 있다.

// 렌더 없이 프레임만 다시 뽑고 싶을 때:  node scripts/frames.mjs 001

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DRIVE_DIR } from './sync-drive.mjs';
import { buildTimeline, FPS } from '../remotion/timing.js';

// 1장은 0.5초 지점(후킹 검수용), 나머지 5장은 전체 길이를 균등 분할.
export function pickFrames(totalFrames, fps = 30) {
  const first = Math.round(0.5 * fps);
  const rest = [0.1, 0.3, 0.5, 0.7, 0.9].map((r) =>
    Math.min(totalFrames - 1, Math.round(totalFrames * r))
  );
  return [first, ...rest];
}

export function extractFrames({ ROOT, videoId, propsPath, totalFrames, fps = 30 }) {
  const outDir = path.join(DRIVE_DIR, 'frames', videoId);
  fs.mkdirSync(outDir, { recursive: true });

  const remotionCli = path.join(ROOT, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');
  const frames = pickFrames(totalFrames, fps);
  const written = [];

  frames.forEach((frame, i) => {
    const out = path.join(outDir, `${videoId}_f${i + 1}.png`);
    execFileSync(
      process.execPath,
      [
        remotionCli,
        'still',
        'remotion/index.jsx',
        'Short',
        out,
        `--props=${propsPath}`,
        `--frame=${frame}`,
        '--log=error',
      ],
      { cwd: ROOT, stdio: 'pipe' }
    );
    written.push(`f${i + 1}=${(frame / fps).toFixed(1)}초`);
  });

  console.log(`  프레임 ${written.length}장 → ${outDir}`);
  return { dir: outDir, count: written.length, detail: written.join(', ') };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const videoId = process.argv[2];
  if (!videoId) {
    console.error('사용법: node scripts/frames.mjs 001');
    process.exit(1);
  }
  const propsPath = path.join(ROOT, '.build', `${videoId}.props.json`);
  const props = JSON.parse(fs.readFileSync(propsPath, 'utf8'));
  const { totalFrames } = buildTimeline(props);
  extractFrames({ ROOT, videoId, propsPath, totalFrames, fps: FPS });
}
