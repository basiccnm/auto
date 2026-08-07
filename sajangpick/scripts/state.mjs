// STATE.md 를 만든다. 웹 Claude가 깨어났을 때 이거 하나만 읽으면
// 지금 무슨 상황인지 알 수 있게 하는 요약 파일.
//
// 내용은 전부 실제 폴더/파일에서 읽어온 값이다. 손으로 적지 않는다.
// SEQ 체계는 회신02에서 폐기됐다 — 통신 현황은 요청NN/회신NN 번호로만 판별한다.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { syncDrive, DRIVE_DIR } from './sync-drive.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const WATCHER_STATE = path.join(ROOT, '.build', 'watcher-state.json');

const list = (dir, filter) => {
  try {
    return fs.readdirSync(path.join(ROOT, dir)).filter(filter);
  } catch {
    return [];
  }
};

// 통신 폴더를 스캔해 "회신이 안 온 요청"과 "마지막으로 처리한 회신"을 알아낸다.
function commStatus() {
  let names = [];
  try {
    names = fs.readdirSync(DRIVE_DIR);
  } catch {
    return { open: '드라이브 읽기 불가', lastHandled: '-' };
  }

  const reqs = names.map((n) => n.match(/^요청(\d{2})\.md$/)?.[1]).filter(Boolean);
  const replies = new Set(names.map((n) => n.match(/^회신(\d{2})\.md$/)?.[1]).filter(Boolean));
  const open = reqs.filter((n) => !replies.has(n));

  // 처리 완료 표시는 watcher의 상태 파일이 단일 원본이다 (--handled 로 기록됨).
  let handled = [];
  try {
    handled = JSON.parse(fs.readFileSync(WATCHER_STATE, 'utf8')).handledReplies ?? [];
  } catch {
    /* 아직 없음 */
  }
  const nums = handled.map((n) => n.match(/(\d{2})/)?.[1]).filter(Boolean).sort();

  return {
    open: open.length ? open.map((n) => `요청${n}`).join(', ') : '없음',
    lastHandled: nums.length ? nums[nums.length - 1] : '-',
  };
}

export function writeState({ status = '대기중', current = '없음' } = {}) {
  const log = fs.existsSync(path.join(ROOT, 'WORKLOG.md'))
    ? fs.readFileSync(path.join(ROOT, 'WORKLOG.md'), 'utf8')
    : '';

  // 아직 답이 안 온 [질문]이 몇 개인지 센다.
  const questions = (log.match(/\|\s*\[질문\]\s*\|/g) || []).length;

  const inbox = list('inbox', (f) => f.endsWith('.json'));
  const done = list('done', (f) => f.endsWith('.json'));
  const mp4 = list('outbox', (f) => f.endsWith('.mp4'));
  const comm = commStatus();

  const now = new Date();
  const p = (n) => String(n).padStart(2, '0');
  const stamp = `${now.toISOString().slice(0, 10)} ${p(now.getHours())}:${p(now.getMinutes())}`;

  const lines = [
    `UPDATED: ${stamp}`,
    `HEARTBEAT: ${stamp}`,
    `STATUS: ${status}`,
    `LAST_HANDLED_REPLY: ${comm.lastHandled}`,
    `OPEN: ${comm.open}`,
    `CURRENT: ${current}`,
    `PENDING_QUESTIONS: ${questions}`,
    `INBOX: ${inbox.join(', ') || '비어있음'}`,
    `DONE: ${done.join(', ') || '없음'}`,
    `OUTBOX: ${mp4.join(', ') || '없음'}`,
  ];

  fs.writeFileSync(path.join(ROOT, 'STATE.md'), lines.join('\n') + '\n', 'utf8');
  syncDrive({ quiet: true });
  return lines.join('\n');
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log(writeState());
}
