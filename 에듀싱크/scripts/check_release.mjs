#!/usr/bin/env node
/* 출시 전 검사 — 「검수용으로 열어둔 것」이 그대로 나가는 걸 막는다.
   ⚠ 이 항목들은 **지금 지우면 검수가 막힌다**(방학이라 devDate 없이는 급식·시간표를 볼 수 없고,
     DEV_TOOLS 를 끄면 결제 흐름을 시험할 수 없다). 그래서 남겨 두되 **잊지 못하게** 한다.
   ⚠ 사람 기억에 맡기면 반드시 한 번은 새어 나간다. 그 한 번이 «공짜 이용권»이다.

   쓰는 법:  node scripts/check_release.mjs          → 지금 상태만 알려준다(항상 0으로 끝난다)
             node scripts/check_release.mjs --strict → 하나라도 열려 있으면 1로 끝난다(출시 직전) */
import { readFileSync, existsSync } from "node:fs";

const strict = process.argv.includes("--strict");
const rows = [];
const check = (name, open, how) => rows.push({ name, open, how });

// ① 서버 뒷문 — mock 결제. 켜져 있으면 누구나 공짜 이용권을 받는다.
const toml = existsSync("workers/site-renderer/wrangler.toml")
  ? readFileSync("workers/site-renderer/wrangler.toml", "utf8") : "";
check("DEV_TOOLS (모의결제 뒷문)",
  /DEV_TOOLS\s*=\s*"true"/.test(toml),
  'workers/site-renderer/wrangler.toml 의 DEV_TOOLS 를 "false" 로 바꾸고 배포');

// ② 앱의 날짜 고정 — 검수용. 남아 있어도 «앱이 보는 날»만 바뀌지만 출시본에 둘 이유가 없다.
const app = existsSync("app/www/app.js") ? readFileSync("app/www/app.js", "utf8") : "";
check("DEV_DATE (검수용 날짜 고정)",
  /const DEV_DATE\s*=/.test(app),
  "app/www/app.js 의 DEV_DATE 세 줄을 지우고 TODAY 를 원래대로");

// ③ 구글 영수증 검증 — 서비스 계정이 없으면 결제가 통째로 막힌다(막히는 쪽이 안전하지만 팔 수 없다).
check("GOOGLE_PLAY_SA 미등록 (결제가 막혀 있다)",
  true,   // 시크릿은 코드에서 알 수 없다 — 사람이 확인한다
  "Play Console 서비스 계정을 만들고 `npx wrangler secret put GOOGLE_PLAY_SA`");

// ④ 검수용으로 넣어 둔 데이터 — 남으면 실제 급식과 섞인다.
const seeds = ["scripts/seed_meals_202605_경기초.sql", "scripts/seed_meals_202605_서울과학고.sql"];
check("검수용 5월 급식 씨앗 파일",
  seeds.some((f) => existsSync(f)),
  "그 학교의 2026-05 급식 행을 지우고( DELETE FROM meals WHERE … ) 파일도 정리");

const open = rows.filter((r) => r.open);
console.log("출시 전 검사 — 검수용으로 열어둔 것\n");
for (const r of rows) {
  console.log(`  ${r.open ? "🔴 열림" : "✅ 닫힘"}  ${r.name}`);
  if (r.open) console.log(`           → ${r.how}`);
}
console.log(`\n${open.length ? `🔴 ${open.length}가지가 열려 있다.` : "✅ 전부 닫혔다."}`);
if (strict && open.length) {
  console.log("   --strict 라 여기서 멈춘다. 출시하려면 위를 먼저 닫을 것.");
  process.exit(1);
}
