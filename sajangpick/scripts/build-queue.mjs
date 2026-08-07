// outbox의 산출물을 업로더 대기열(uploader/queue.json)로 변환한다.
//
// 업로더(uploader/upload_yt.py)는 올마나마에서 복사해온 것이라 queue.json 형식을 쓴다.
// 우리 산출물은 {id}.mp4 + {id}_upload.txt 이므로 여기서 그 형식으로 바꿔준다.
//
// {id}_upload.txt 구조: 1행 제목 / 빈줄 / 설명 여러 줄 / 빈줄 / 해시태그 한 줄
//
// 실행: node scripts/build-queue.mjs
// 이미 queue.json에 있는 영상의 업로드 상태(status)는 보존한다.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUTBOX = path.join(ROOT, 'outbox');
const QUEUE = path.join(ROOT, 'uploader', 'queue.json');

const old = fs.existsSync(QUEUE) ? JSON.parse(fs.readFileSync(QUEUE, 'utf8')) : { videos: [] };
const oldById = new Map(old.videos.map((v) => [v.id, v]));

const ids = fs
  .readdirSync(OUTBOX)
  .filter((f) => f.endsWith('.mp4'))
  .map((f) => f.replace(/\.mp4$/, ''))
  .sort();

const videos = ids.map((id) => {
  const txtPath = path.join(OUTBOX, `${id}_upload.txt`);
  let title = id;
  let desc = '';
  let tags = [];

  if (fs.existsSync(txtPath)) {
    const lines = fs.readFileSync(txtPath, 'utf8').split(/\r?\n/);
    title = lines[0]?.trim() || id;
    // 마지막 비어있지 않은 줄이 해시태그 줄
    const nonEmpty = lines.map((l, i) => ({ l: l.trim(), i })).filter((x) => x.l);
    const last = nonEmpty[nonEmpty.length - 1];
    if (last && last.l.startsWith('#')) {
      tags = last.l.split(/\s+/).map((t) => t.replace(/^#/, ''));
      desc = lines.slice(1, last.i).join('\n').trim();
    } else {
      desc = lines.slice(1).join('\n').trim();
    }
  }

  return {
    id,
    brand: '사장픽',
    file_yt: `../outbox/${id}.mp4`,
    title,
    desc,
    tags,
    // 이미 올린 기록은 지우면 안 된다 — 같은 영상을 두 번 올리게 된다
    status: oldById.get(id)?.status ?? {},
    note: oldById.get(id)?.note ?? {},
    uploaded_at: oldById.get(id)?.uploaded_at ?? {},
  };
});

fs.mkdirSync(path.dirname(QUEUE), { recursive: true });
fs.writeFileSync(QUEUE, JSON.stringify({ videos }, null, 2), 'utf8');
console.log(`queue.json 갱신: ${videos.length}편 (${ids.join(', ')})`);
