// 기획서 1개를 영상으로 만드는 전체 과정을 한 번에 돌리는 스크립트.
// 쓰는 법:  node scripts/render.mjs 001
//
// 하는 일: 기획서 읽기 → 음성(TTS) 생성 → mp4 렌더 → 업로드용 텍스트 생성
//         → 기획서를 done/으로 이동 → WORKLOG.md 기록 → 구글 드라이브 복사
//
// 기획서는 inbox/에서 찾고, 없으면 done/에서 찾는다(이미 처리한 걸 다시 렌더할 때).
// 실패해도 LOG.md에는 반드시 기록을 남긴다. 어디서 막혔는지 알아야 하므로.

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { syncDrive } from './sync-drive.mjs';
import { buildAudio } from './tts.mjs';
import { extractFrames } from './frames.mjs';
import { buildTimeline, FPS } from '../remotion/timing.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const id = process.argv[2];

if (!id) {
  console.error('사용법: node scripts/render.mjs 001');
  process.exit(1);
}

const inboxPath = path.join(ROOT, 'inbox', `${id}.json`);
const donePath = path.join(ROOT, 'done', `${id}.json`);
const outMp4 = path.join(ROOT, 'outbox', `${id}.mp4`);
const outTxt = path.join(ROOT, 'outbox', `${id}_upload.txt`);

const today = new Date().toISOString().slice(0, 10);

function appendLog(status, note) {
  const logPath = path.join(ROOT, 'WORKLOG.md');
  const line = `${today} | ${id} | ${status} | ${note}`;
  const lines = fs.readFileSync(logPath, 'utf8').split(/\r?\n/);
  const insertAt = lines.findIndex((l) => /^\d{4}-\d{2}-\d{2} \|/.test(l));
  lines.splice(insertAt === -1 ? lines.length : insertAt, 0, line, '');
  fs.writeFileSync(logPath, lines.join('\n'), 'utf8');
  console.log(`WORKLOG.md 기록: ${line}`);
  // LOG.md가 바뀌었으니 바로 드라이브에 올린다. Claude 웹이 이걸 읽는다.
  syncDrive({ quiet: true });
}

try {
  const fromInbox = fs.existsSync(inboxPath);
  const planPath = fromInbox ? inboxPath : donePath;
  if (!fs.existsSync(planPath)) throw new Error(`기획서 없음: ${id}.json (inbox/ done/ 둘 다 없음)`);

  const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
  fs.mkdirSync(path.join(ROOT, 'outbox'), { recursive: true });

  console.log(`[1/4] 음성 생성: ${plan.product_name}`);
  const audio = buildAudio(plan, ROOT);

  // BGM — public/bgm.wav 가 있으면 깔린다 (없으면 조용히 무음).
  // 트랙을 바꾸고 싶으면 그 파일만 교체하면 된다.
  audio.bgm = fs.existsSync(path.join(ROOT, 'public', 'bgm.wav')) ? 'bgm.wav' : null;

  // 렌더에 넘길 최종 props. 기획서 + 음성 정보를 합친 것.
  const buildDir = path.join(ROOT, '.build');
  fs.mkdirSync(buildDir, { recursive: true });
  const propsPath = path.join(buildDir, `${id}.props.json`);
  fs.writeFileSync(propsPath, JSON.stringify({ ...plan, audio }, null, 2), 'utf8');

  console.log('[2/4] 영상 렌더');
  // npx.cmd를 직접 실행하면 Node 24 + 윈도우에서 EINVAL이 난다.
  // 그래서 배치파일을 거치지 않고 remotion CLI의 js 파일을 node로 바로 실행한다.
  const remotionCli = path.join(ROOT, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');
  execFileSync(
    process.execPath,
    [
      remotionCli,
      'render',
      'remotion/index.jsx',
      'Short',
      outMp4,
      `--props=${propsPath}`,
      '--codec=h264',
      '--log=info',
    ],
    { cwd: ROOT, stdio: 'inherit' }
  );

  console.log('[3/5] 검수용 프레임 추출');
  // 웹 Claude는 mp4를 못 읽는다. png로 뽑아 올려야 화면 검수가 가능하다.
  const totalFrames = buildTimeline({ ...plan, audio }).totalFrames;
  let frameNote = '프레임 추출 실패';
  try {
    const f = extractFrames({ ROOT, videoId: id, propsPath, totalFrames, fps: FPS });
    frameNote = `프레임 ${f.count}장 (${f.detail})`;
  } catch (err) {
    console.warn(`  프레임 추출 실패: ${err.message}`); // 렌더 자체를 실패로 만들지는 않는다
  }

  console.log('[4/5] 업로드용 텍스트 생성');
  const uploadText = [plan.title, '', plan.description, '', plan.hashtags.join(' '), ''].join('\n');
  // 쿠팡 파트너스 고지는 반드시 들어가야 해서 여기서 한 번 더 확인한다.
  if (!uploadText.includes('쿠팡 파트너스 활동의 일환')) {
    throw new Error('설명에 쿠팡 파트너스 고지 문구가 없음');
  }
  fs.writeFileSync(outTxt, uploadText, 'utf8');

  console.log('[5/5] 기획서 정리');
  if (fromInbox) {
    fs.mkdirSync(path.join(ROOT, 'done'), { recursive: true });
    fs.renameSync(inboxPath, donePath);
  }

  const sizeMb = (fs.statSync(outMp4).size / 1024 / 1024).toFixed(1);
  const seconds = (
    audio.hook.duration + audio.scenes.reduce((a, s) => a + s.duration, 0) + audio.cta.duration
  ).toFixed(1);
  appendLog(
    '성공',
    `outbox/${id}.mp4 (${sizeMb}MB) / 음성 ${audio.voice} ${audio.rate}, 나레이션 합계 ${seconds}초 / 제품이미지 미적용 / ${frameNote}`
  );
  console.log(`\n완료: ${outMp4}`);
} catch (err) {
  const msg = String(err.message || err).split('\n')[0].slice(0, 200);
  appendLog('실패', `[질문] ${msg}`);
  console.error(`\n실패: ${msg}`);
  process.exit(1);
}

