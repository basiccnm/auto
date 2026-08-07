// 코드탭이 쓰는 문서들을 구글 드라이브 통신 폴더로 복사한다.
// 이 세 개만 복사하는 이유: Claude 웹이 읽어야 하는 건 이 텍스트뿐이고,
// 프로젝트 전체를 드라이브에 두면 node_modules 수만 개 파일이 계속 동기화돼서
// 드라이브가 느려지고 렌더도 불안정해진다.
//
// 단독 실행:  node scripts/sync-drive.mjs
// render.mjs 안에서도 자동으로 불린다.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export const DRIVE_DIR = 'G:\\내 드라이브\\sajangpick';

// 코드탭이 드라이브로 "올리는" 파일만 넣는다 (PROTOCOL v5 §11 쓰기 권한).
// 회신NN.md는 웹이 쓰는 파일이라 여기서 절대 건드리지 않는다.
// (예전에 ANSWER.md를 여기 넣었다가 드라이브가 사본 `ANSWER (1).md`를 만들어 두 개로 갈라졌다)
// WAKE / PENDING / WATCHER_HEARTBEAT 는 watcher가 직접 쓰므로 여기 없다.
const UPLOAD = ['WORKLOG.md', 'COMMLOG.md', 'INDEX.md', 'STATE.md', 'DATA.md'];

export function syncDrive({ quiet = false } = {}) {
  // 드라이브가 꺼져 있거나 G:가 없을 수 있다. 그때 렌더까지 같이 죽으면 안 되므로
  // 여기서는 실패해도 경고만 남기고 넘어간다.
  try {
    fs.mkdirSync(DRIVE_DIR, { recursive: true });
  } catch (err) {
    console.warn(`[동기화 건너뜀] 드라이브 폴더를 만들 수 없음: ${err.message}`);
    return { ok: false, copied: [] };
  }

  const copied = [];
  for (const name of UPLOAD) {
    const src = path.join(ROOT, name);
    if (!fs.existsSync(src)) continue;
    try {
      fs.copyFileSync(src, path.join(DRIVE_DIR, name));
      copied.push(name);
    } catch (err) {
      console.warn(`[동기화 실패] ${name}: ${err.message}`);
    }
  }

  if (!quiet) {
    console.log(`드라이브 복사 완료 → ${DRIVE_DIR}  (${copied.join(', ') || '없음'})`);
  }
  return { ok: copied.length > 0, copied };
}

// 이 파일을 직접 실행했을 때만 동작 (import될 때는 실행 안 됨).
// URL 문자열끼리 비교하면 한글 경로가 인코딩돼서 안 맞는다. 실제 경로로 비교할 것.
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  syncDrive();
}
