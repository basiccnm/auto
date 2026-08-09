// ============================================================
// 🔌 연결 전수 검사 (2026-08-08)
//
//   node scripts/check_wiring.mjs
//
// 눈으로 찾지 말자고 만든 것이다. 화면을 하나씩 눌러 보는 방식으로는
// «누르면 아무 일도 안 나는 버튼»과 «없는 화면으로 가는 링크»를 절대 다 못 찾는다.
// 실제로 08-08 에 이런 것들이 나왔다:
//   · 끝낸 미션 타일이 App.gameTab('39') 같은 **없는 화면**으로 갔다
//   · 아이 토큰이 게임 경로를 못 지나가서 아이 폰에서만 「권한이 없어요」가 떴다
//   · 관문에 /store/buy 라고 적었는데 실제는 /store/{상품id}/buy 였다
//
// 여기서 재는 것 넷:
//   ① onclick="App.xxx(" 로 부르는 함수가 App 에 **있는가**
//   ② location.hash='#yyy' 의 화면이 Screens 에 **있는가**
//   ③ 앱이 부르는 api('/...') 경로가 워커 라우터에 **잡히는가**
//   ④ 아이가 쓰는 화면이 부르는 경로가 **자녀 토큰 관문(CHILD_OK)** 을 지나가는가
// ============================================================
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const js = readFileSync(join(HERE, "..", "app", "www", "app.js"), "utf8");
const SRC = join(HERE, "..", "workers", "site-renderer", "src");
const serverFiles = ["index.js", "api_mission.js", "api_reward.js", "api_quiz.js",
  "api_life.js", "api_core.js", "school_missions.js", "api_auth.js", "api_records.js"];
const server = serverFiles.map((f) => {
  try { return readFileSync(join(SRC, f), "utf8"); } catch { return ""; }
}).join("\n");

let fail = 0, warn = 0;
const bad = (t, list) => { fail++; console.log(`  ❌ ${t}`); list.slice(0, 14).forEach((x) => console.log(`       ${x}`)); if (list.length > 14) console.log(`       … 외 ${list.length - 14}개`); };
const soft = (t, list) => { warn++; console.log(`  ⚠ ${t}`); list.slice(0, 10).forEach((x) => console.log(`       ${x}`)); };
const ok = (t) => console.log(`  ✅ ${t}`);

// ── ① App.xxx( 가 실제로 있는가 ─────────────────────────────
console.log("① 버튼이 부르는 함수가 있나");
{
  // App = { ... } 안의 메서드 이름을 모은다 (async 포함, 한 줄 정의도)
  const names = new Set();
  for (const m of js.matchAll(/^\s{2}(?:async\s+)?([A-Za-z_$][\w$]*)\s*\(/gm)) names.add(m[1]);
  for (const m of js.matchAll(/^\s{2}([A-Za-z_$][\w$]*):\s*(?:async\s*)?\(/gm)) names.add(m[1]);

  /* ⚠ 주석 안의 예시(`onclick="App.f('…')" 처럼`)까지 세면 오탐이 난다 — 주석을 먼저 걷는다 */
  const live = js.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/^\s*\/\/.*$/gm, " ");
  const called = new Set();
  for (const m of live.matchAll(/App\.([A-Za-z_$][\w$]*)\s*\(/g)) called.add(m[1]);

  const missing = [...called].filter((n) => !names.has(n)).sort();
  missing.length ? bad(`App 에 없는 함수를 부른다 ${missing.length}개 — 눌러도 아무 일이 안 난다`, missing)
                 : ok(`부르는 함수 ${called.size}개 전부 있다`);
}

// ── ② location.hash 의 화면이 있는가 ────────────────────────
console.log("\n② 링크가 가리키는 화면이 있나");
{
  const screens = new Set();
  const block = js.slice(js.indexOf("const Screens = {"));
  for (const m of block.matchAll(/^\s{2}([a-z][\w-]*)\s*:\s*(?:\(|function|async)/gm)) screens.add(m[1]);
  // 문자열 키로 쓴 화면도 있다
  for (const m of block.matchAll(/^\s{2}"([a-z][\w-]*)"\s*:/gm)) screens.add(m[1]);

  const goes = new Set();
  for (const m of js.matchAll(/location\.hash\s*=\s*["'`]#([a-z][\w-]*)["'`]/g)) goes.add(m[1]);
  for (const m of js.matchAll(/href="#([a-z][\w-]*)"/g)) goes.add(m[1]);

  const missing = [...goes].filter((n) => !screens.has(n)).sort();
  missing.length ? bad(`없는 화면으로 가는 링크 ${missing.length}개`, missing)
                 : ok(`가는 화면 ${goes.size}개 전부 있다`);
}

// ── ③ 앱이 부르는 API 가 서버에 잡히는가 ───────────────────
console.log("\n③ 앱이 부르는 API 가 서버에 있나");
{
  const calls = new Set();
  for (const m of js.matchAll(/\bapi\(\s*`([^`]+)`/g)) calls.add(m[1]);
  for (const m of js.matchAll(/\bapi\(\s*"([^"]+)"/g)) calls.add(m[1]);

  const missing = [];
  for (const raw of calls) {
    // `${...}` 를 «아무 값»으로 바꾸고, 물음표 뒤는 버린다
    /* ⚠ `${q}` 처럼 **경로 뒤에 붙는 조각**은 «1» 로 바꾸면 앞 단어와 붙어 버린다
       (reactions${q} → reactions1). 값 자리는 «/» 로 끊어서 넣는다. */
    const path = raw.split("?")[0].replace(/\$\{[^}]*\}/g, "/1/");
    const parts = path.split("/").filter(Boolean);
    if (!parts.length) continue;
    // 서버 쪽에 그 경로 조각들이 한 정규식/문자열 안에 같이 나오나 — 느슨하지만 «오타»는 잡는다
    const words = parts.filter((p) => /^[a-z][\w-]*$/i.test(p));
    const hit = words.every((w) => server.includes(w));
    if (!hit) missing.push(raw + "   (" + words.filter((w) => !server.includes(w)).join(", ") + " 가 서버에 없다)");
  }
  missing.length ? bad(`서버에 없는 경로를 부른다 ${missing.length}개`, missing)
                 : ok(`부르는 API ${calls.size}개 전부 서버에 있다`);
}

// ── ④ 아이 화면이 쓰는 경로가 자녀 관문을 지나는가 ──────────
console.log("\n④ 아이 폰이 그 경로를 지나갈 수 있나");
{
  const idx = readFileSync(join(SRC, "index.js"), "utf8");
  const s = idx.indexOf("const CHILD_OK = [");
  const e = idx.indexOf("];", s);
  const block = s < 0 ? "" : idx.slice(s, e);
  const res = [];
  for (const m of block.matchAll(/\/\^([^/]|\\\/)+\$\//g)) {
    try { res.push(new RegExp(m[0].slice(1, -1))); } catch { /* 무시 */ }
  }
  // 아이 화면(게임·상점·티켓·학교미션)이 실제로 부르는 경로들
  const KID = [
    "/api/v1/children/1/quiz", "/api/v1/children/1/quiz/answer", "/api/v1/children/1/quiz/retry",
    "/api/v1/children/1/school-missions", "/api/v1/children/1/school-missions/bonus",
    "/api/v1/children/1/store", "/api/v1/children/1/store/si-abc123/buy",
    "/api/v1/children/1/rewards", "/api/v1/children/1/missions",
    "/api/v1/missions/meal-rate", "/api/v1/missions/play-log", "/api/v1/missions/subject-log",
    "/api/v1/missions/1/done", "/api/v1/missions/1/photo",
  ];
  const blocked = KID.filter((p) => !res.some((re) => re.test(p)));
  blocked.length ? bad(`아이 토큰이 못 지나가는 경로 ${blocked.length}개 — 아이 폰에서만 「권한이 없어요」가 뜬다`, blocked)
                 : ok(`아이가 쓰는 경로 ${KID.length}개 전부 통과한다`);
  if (!res.length) soft("CHILD_OK 목록을 못 읽었다 — index.js 모양이 바뀌었나", []);
}

/* 템플릿 문자열 «본문»에 들어간 블록주석은 주석이 아니라 **화면에 찍히는 글자**다.
   2026-08-10 폰 실측에서 설정 화면에 주석 한 문단이 통째로 노출됐다 — 여기에 함께 태운다. */
try {
  const { execFileSync } = await import("node:child_process");
  execFileSync(process.execPath, ["scripts/check_template_comments.mjs", "app/www/app.js"], { stdio: "inherit" });
} catch { fail++; }

console.log("\n════════════════════════════════════════════════════════");
if (fail) { console.log(`  ❌ 실패 ${fail}가지 — 고치고 다시 돌릴 것`); process.exit(1); }
console.log(`  ✅ 연결 이상 없음${warn ? ` (경고 ${warn})` : ""}`);
