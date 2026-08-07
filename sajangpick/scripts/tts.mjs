// 기획서의 대사를 음성 파일(mp3)로 만들고, 각 대사가 몇 초인지 알아낸다.
//
// 왜 길이가 필요한가: 자막이 음성보다 먼저 사라지거나 늦게 뜨면 어색하다.
// 그래서 "글자 수로 추정"하지 않고 실제 음성 길이에 자막을 맞춘다.
// edge-tts가 자막(srt) 파일도 같이 내주는데, 거기 마지막 시각이 곧 음성 길이다.
//
// 음성 파일은 public/audio/{video_id}/ 에 넣는다.
// Remotion은 public 폴더를 staticFile()로 읽기 때문에 여기 있어야 영상에 붙는다.

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

// 목소리와 속도. 쇼츠는 말이 느리면 이탈하므로 기본보다 빠르게 읽힌다.
// 2026-08-01 대표 지시로 +18% → **+70%**(원래 속도의 170%). 쇼츠 이탈률을 더 줄이려는 것.
// ⚠ 속도를 바꾸면 «글자수 → 초» 환산이 통째로 달라진다.
//    +18% 기준은 약 5.8자/초였고, +70%면 대략 8.4자/초다.
//    즉 20~30초에 들어가는 분량이 150자 → 200자 안팎으로 늘어난다.
//    기획서(제미나이)에 넘기는 규격도 같이 고쳐야 대본이 짧아져 영상이 뜬금없이 끝나지 않는다.
export const VOICE = 'ko-KR-InJoonNeural'; // 남성. 여성은 ko-KR-SunHiNeural
export const RATE = '+70%';

// srt 마지막 줄의 끝 시각을 초 단위로 뽑는다.
function durationFromSrt(srtPath) {
  const text = fs.readFileSync(srtPath, 'utf8');
  const stamps = [...text.matchAll(/-->\s*(\d\d):(\d\d):(\d\d)[,.](\d{1,3})/g)];
  if (stamps.length === 0) return null;
  const [, h, m, s, ms] = stamps[stamps.length - 1];
  return Number(h) * 3600 + Number(m) * 60 + Number(s) + Number(ms) / 1000;
}

function speak(text, outMp3) {
  const outSrt = outMp3.replace(/\.mp3$/, '.srt');
  execFileSync(
    'python',
    [
      '-m', 'edge_tts',
      '--voice', VOICE,
      '--rate', RATE,
      '--text', text,
      '--write-media', outMp3,
      '--write-subtitles', outSrt,
    ],
    { stdio: 'pipe' }
  );

  const duration = durationFromSrt(outSrt);
  if (!duration) throw new Error(`음성 길이를 읽지 못함: ${path.basename(outMp3)}`);
  return duration;
}

// 기획서 하나를 통째로 음성화한다. 후킹 / 각 장면 / CTA 전부.
export function buildAudio(plan, ROOT) {
  const dir = path.join(ROOT, 'public', 'audio', plan.video_id);
  fs.mkdirSync(dir, { recursive: true });

  const rel = (name) => `audio/${plan.video_id}/${name}`;

  const hookDur = speak(plan.hook, path.join(dir, 'hook.mp3'));
  console.log(`  후킹 ${hookDur.toFixed(2)}초`);

  const scenes = plan.scenes.map((scene, i) => {
    const d = speak(scene.narration, path.join(dir, `s${i}.mp3`));
    console.log(`  장면 ${i + 1} ${d.toFixed(2)}초`);
    return { src: rel(`s${i}.mp3`), duration: d };
  });

  const ctaDur = speak(plan.cta, path.join(dir, 'cta.mp3'));
  console.log(`  CTA ${ctaDur.toFixed(2)}초`);

  const total = hookDur + scenes.reduce((a, s) => a + s.duration, 0) + ctaDur;
  console.log(`  음성 합계 ${total.toFixed(1)}초`);

  return {
    voice: VOICE,
    rate: RATE,
    hook: { src: rel('hook.mp3'), duration: hookDur },
    scenes,
    cta: { src: rel('cta.mp3'), duration: ctaDur },
  };
}
