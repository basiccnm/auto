// watcher — 상시 살아있는 감시 프로세스 (PROTOCOL v5 §2)
//
//   node watcher.mjs                30초마다 계속 감시
//   node watcher.mjs --once         한 번만 검사하고 종료 (점검용)
//   node watcher.mjs --handled 00   회신00을 처리 완료로 표시 (코드탭이 처리한 뒤 실행)
//
// 하는 일 (판단은 하지 않는다):
//   1. 통신 폴더에서 새 회신NN.md 발견 → PENDING.md에 추가 + WAKE.md에 CODE_NEEDED + 알림
//   2. 요청NN.md이 20분 넘게 회신 없음 → WAKE.md에 WEB_NEEDED + 알림
//   3. 회신 안의 화이트리스트 명령만 자동 실행 (회신02에서 확정):
//        RUN: render 001    렌더 1건
//        RUN: frames 001    검수 프레임 6장 추출→드라이브 업로드
//        RUN: renderall     inbox의 모든 기획서를 번호순 렌더
//      (구형 `AUTO_RENDER: 001` 표기도 render로 인정)
//   4. WATCHER_HEARTBEAT.md 갱신 (내가 살아있다는 표시. 드라이브에도 올라감 —
//      웹은 이 시각이 10분 이상 지났으면 watcher가 죽었다고 판단한다)
//
// ⚠ 자유 문장으로 된 지시는 실행하지 않는다. watcher는 "누굴 깨울지" 알리는 역할까지다.
//    실제 구현·수정은 코드탭(사람이 보는 자리)에서 한다.

import { execFileSync, execFileSync as run } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const COMM = 'G:\\내 드라이브\\sajangpick';
const STATE_FILE = path.join(ROOT, '.build', 'watcher-state.json');

const INTERVAL_MS = 30_000;
// 요청 후 이 시간이 지나도록 회신이 없으면 웹을 깨운다.
// 2026-08-01 사용자 지시로 20분 → 5분. 사람이 기다리기엔 20분이 너무 길다.
const REPLY_TIMEOUT_MS = 5 * 60 * 1000;

const once = process.argv.includes('--once');

// ── 유틸 ──────────────────────────────────────────────────────────

const stamp = () => {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
};

function loadState() {
  try {
    return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  } catch {
    return { handledReplies: [], notified: {}, autoRendered: [] };
  }
}

function saveState(s) {
  fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
  fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2), 'utf8');
}

// watcher가 쓰는 파일은 통신 폴더에 바로 쓴다(웹이 읽어야 하므로).
// 로컬에도 같은 걸 남겨서 드라이브가 꺼져 있어도 흔적이 남게 한다.
function writeBoth(name, text) {
  fs.writeFileSync(path.join(ROOT, name), text, 'utf8');
  try {
    fs.mkdirSync(COMM, { recursive: true });
    fs.writeFileSync(path.join(COMM, name), text, 'utf8');
  } catch {
    /* 드라이브 꺼짐 — 로컬만 남기고 넘어간다 */
  }
}

function readEnvFile() {
  const file = path.join(ROOT, '.env');
  if (!fs.existsSync(file)) return {};
  const out = {};
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) out[m[1]] = m[2].trim();
  }
  return out;
}

// ── 알림 ──────────────────────────────────────────────────────────

// 윈도우 토스트. 추가 설치 없이 파워셸 내장 기능만 쓴다.
// 따옴표 문제를 피하려고 문구는 환경변수로 넘긴다.
const TOAST_PS = `
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] > $null
$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$n = $x.GetElementsByTagName('text')
$n[0].AppendChild($x.CreateTextNode($env:SP_TITLE)) > $null
$n[1].AppendChild($x.CreateTextNode($env:SP_BODY)) > $null
$t = [Windows.UI.Notifications.ToastNotification]::new($x)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe').Show($t)
`;

function toast(title, body) {
  try {
    run('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', TOAST_PS], {
      env: { ...process.env, SP_TITLE: title, SP_BODY: body },
      stdio: 'ignore',
      timeout: 15_000,
    });
  } catch {
    /* 알림 실패가 감시를 멈추게 하면 안 된다 */
  }
}

// 폰 알림. 토큰이 없으면 조용히 넘어간다(아직 사용자에게 못 받은 상태).
async function telegram(text) {
  const env = { ...readEnvFile(), ...process.env };
  const token = env.TELEGRAM_BOT_TOKEN;
  const chatId = env.TELEGRAM_CHAT_ID;
  if (!token || !chatId) return false;
  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text }),
    });
    return true;
  } catch {
    return false;
  }
}

async function notify(text) {
  console.log(`[알림] ${text}`);
  toast('사장픽', text);
  await telegram(text);
}

// ── 폴더 스캔 ──────────────────────────────────────────────────────

function scanComm() {
  let files;
  try {
    files = fs.readdirSync(COMM, { withFileTypes: true }).filter((e) => e.isFile());
  } catch {
    return null; // 드라이브 접근 불가
  }

  const pick = (re) =>
    files
      .map((e) => {
        const m = e.name.match(re);
        if (!m) return null;
        const full = path.join(COMM, e.name);
        return { num: m[1], name: e.name, full, mtime: fs.statSync(full).mtimeMs };
      })
      .filter(Boolean);

  return {
    replies: pick(/^회신(\d{2})\.md$/),
    requests: pick(/^요청(\d{2})\.md$/),
  };
}

// ── 한 번 검사 ─────────────────────────────────────────────────────

async function tick() {
  const state = loadState();
  const now = Date.now();
  const comm = scanComm();

  writeBoth(
    'WATCHER_HEARTBEAT.md',
    `UPDATED: ${stamp()}\nALIVE: yes\nPID: ${process.pid}\nINTERVAL: ${INTERVAL_MS / 1000}초\n`
  );

  if (!comm) {
    console.log(`${stamp()} 통신 폴더를 읽을 수 없습니다 (드라이브 꺼짐?)`);
    return;
  }

  // 1) 새 회신 찾기
  const fresh = comm.replies.filter((r) => !state.handledReplies.includes(r.name));

  // 3) 회신 안의 화이트리스트 명령만 자동 실행. 자유 문장은 절대 실행하지 않는다.
  for (const reply of fresh) {
    const text = fs.readFileSync(reply.full, 'utf8');

    // `RUN: render 001` 형식 + 구형 `AUTO_RENDER: 001` 도 render로 인정
    const cmds = [
      ...[...text.matchAll(/^\s*RUN:\s*(render|frames)\s+([0-9A-Za-z_-]+)\s*$/gm)].map((m) => ({
        cmd: m[1],
        arg: m[2],
      })),
      ...[...text.matchAll(/^\s*RUN:\s*renderall\s*$/gm)].map(() => ({ cmd: 'renderall', arg: '' })),
      ...[...text.matchAll(/^\s*AUTO_RENDER:\s*([0-9A-Za-z_-]+)\s*$/gm)].map((m) => ({
        cmd: 'render',
        arg: m[1],
      })),
    ];

    for (const { cmd, arg } of cmds) {
      const key = `${reply.name}:${cmd}:${arg}`;
      if (state.autoRendered.includes(key)) continue;

      // renderall은 실행 시점의 inbox 목록을 번호순으로 돈다
      const targets =
        cmd === 'renderall'
          ? fs
              .readdirSync(path.join(ROOT, 'inbox'))
              .filter((f) => /^[0-9A-Za-z_-]+\.json$/.test(f))
              .map((f) => f.replace(/\.json$/, ''))
              .sort()
          : [arg];

      const script = cmd === 'frames' ? 'frames.mjs' : 'render.mjs';

      console.log(`${stamp()} ${cmd} 실행 (${reply.name}) → ${targets.join(', ') || '대상 없음'}`);
      for (const id of targets) {
        await notify(`[사장픽] ${cmd} 시작 — ${id}`);
        try {
          execFileSync(process.execPath, [path.join(ROOT, 'scripts', script), id], {
            cwd: ROOT,
            stdio: 'inherit',
          });
          await notify(`[사장픽] ${cmd} 완료 — ${id}`);
        } catch {
          await notify(`[사장픽] ${cmd} 실패 — ${id} (WORKLOG 확인). 다음 건으로 넘어감`);
        }
      }
      state.autoRendered.push(key);
      saveState(state);
    }
  }

  // 2) 요청 후 20분 넘게 회신이 없는 건 웹을 깨워야 한다
  const replyNums = new Set(comm.replies.map((r) => r.num));
  const stale = comm.requests.filter(
    (q) => !replyNums.has(q.num) && now - q.mtime > REPLY_TIMEOUT_MS
  );

  // PENDING.md — 코드탭이 처리해야 할 목록
  const pendingLines = fresh.map((r) => {
    const firstLine = fs.readFileSync(r.full, 'utf8').split(/\r?\n/)[0].trim();
    return `- ${r.name} | ${firstLine || '(주제 없음)'}`;
  });
  writeBoth(
    'PENDING.md',
    `UPDATED: ${stamp()}\n\n# 코드탭이 처리할 대기 목록\n\n${pendingLines.join('\n') || '- 없음'}\n`
  );

  // WAKE.md — 누굴 깨울지 한 장
  const codeNeeded = fresh.length ? fresh.map((r) => r.num).join(',') : '-';
  const webNeeded = stale.length ? stale.map((q) => q.num).join(',') : '-';
  writeBoth(
    'WAKE.md',
    [
      `UPDATED: ${stamp()}`,
      `WEB_NEEDED: ${webNeeded}`,
      `CODE_NEEDED: ${codeNeeded}`,
      `WATCHER_ALIVE: yes`,
      '',
    ].join('\n')
  );

  // 알림은 상태가 바뀔 때만. 30초마다 울리면 아무도 안 본다.
  const signature = `${webNeeded}|${codeNeeded}`;
  if (signature !== state.notified.signature) {
    if (codeNeeded !== '-') await notify(`[사장픽] 코드탭 확인 필요 — 회신${codeNeeded} 도착`);
    if (webNeeded !== '-') await notify(`[사장픽] 웹 확인 필요 — 요청${webNeeded} 20분 경과`);
    state.notified.signature = signature;
    saveState(state);
  }

  console.log(`${stamp()} WEB_NEEDED=${webNeeded} CODE_NEEDED=${codeNeeded}`);
}

// ── 실행 ──────────────────────────────────────────────────────────

async function loop() {
  try {
    await tick();
  } catch (err) {
    console.error(`${stamp()} watcher 오류: ${err.message}`);
  }
}

// 코드탭이 회신을 처리한 뒤 이걸 실행해야 대기 목록에서 빠진다.
const handledIdx = process.argv.indexOf('--handled');
if (handledIdx !== -1) {
  const num = process.argv[handledIdx + 1];
  if (!/^\d{2}$/.test(num ?? '')) {
    console.error('사용법: node watcher.mjs --handled 00');
    process.exit(1);
  }
  const s = loadState();
  const name = `회신${num}.md`;
  if (!s.handledReplies.includes(name)) s.handledReplies.push(name);
  saveState(s);
  s.notified.signature = null; // 다음 검사에서 WAKE.md가 다시 계산되도록
  saveState(s);
  console.log(`${name} 처리완료로 표시했습니다.`);
  await loop();
} else if (once) {
  await loop();
} else {
  console.log(`watcher 시작 — ${INTERVAL_MS / 1000}초 간격. 통신 폴더: ${COMM}`);
  await loop();
  setInterval(loop, INTERVAL_MS);
}
