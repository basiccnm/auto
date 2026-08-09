#!/usr/bin/env node
/* 화면 지도 — 각 화면의 «들어오는 길»과 «나가는 길»을 센다.
   2026-08-10 대표님 지적: 「논리적으로 돌아가는 게 왜 자꾸 이상하게 구성되어 있나」.
   말로 세면 또 놓친다. 코드에서 직접 센다.
   ⚠ 두 번 헛다리를 짚었다:
     ① `Screens` 밖(STUB)에도 `school:`·`supplies:` 같은 **같은 이름의 데이터**가 있다
        → 파일 전체에서 찾으면 데이터를 화면 본문으로 착각한다. Screens 안에서만 찾는다.
     ② 화면이 다른 화면·헬퍼에 **위임**하면 뒤로가기가 그쪽에 있다
        (`meal: () => Screens.school()`) → 한 겹 따라간다. */
import { readFileSync } from "node:fs";
const src = readFileSync("app/www/app.js", "utf8");

const S0 = src.indexOf("const Screens = {");
const S1 = src.indexOf("\n};", S0);

const screens = [];
{
  const body = src.slice(S0, S1);
  const re = /\n  ([a-zA-Z][\w-]*)\s*:\s*(\(|async)/g;
  let m; while ((m = re.exec(body))) screens.push(m[1]);
}

const bodyOf = (name) => {
  const i = src.indexOf("\n  " + name + ":", S0);
  if (i < 0 || i > S1) return "";
  let end = S1;
  for (const o of screens) {
    const j = src.indexOf("\n  " + o + ":", i + 3);
    if (j > i && j < end) end = j;
  }
  return src.slice(i, end);
};
const fnBody = (name) => {
  const i = src.search(new RegExp("\nfunction\s+" + name + "\\b"));
  return i < 0 ? "" : src.slice(i, i + 8000);
};
const resolved = (name) => {
  let b = bodyOf(name);
  for (const o of screens) if (o !== name && b.includes("Screens." + o + "(")) b += bodyOf(o);
  for (const m of b.matchAll(/\b([a-zA-Z]\w{3,})\(/g)) b += fnBody(m[1]);
  return b;
};

const inbound = new Map(screens.map((s) => [s, 0]));
for (const m of src.matchAll(/['"`]#([a-zA-Z][\w-]*)['"`]/g)) {
  if (inbound.has(m[1])) inbound.set(m[1], inbound.get(m[1]) + 1);
}

const OUT = /subHeader\(|class="back"|App\.goBack\(|gm-back|lg-close|sub-back|hv3-ham|drawerOpen\(/;
const rows = screens.map((s) => ({ name: s, in: inbound.get(s), out: OUT.test(resolved(s)) }));

const noExit = rows.filter((r) => r.in > 0 && !r.out);
const dead = rows.filter((r) => r.in === 0);
const many = rows.filter((r) => r.in >= 5).sort((a, b) => b.in - a.in);

console.log("화면 " + rows.length + "개\n");
console.log("❌ 나가는 길이 없다 — " + noExit.length + "곳");
noExit.forEach((r) => console.log("   " + r.name + "  (들어오는 길 " + r.in + ")"));
console.log("\n⚠ 들어오는 길이 없다 — " + dead.length + "곳  (라우터가 직접 띄우는 화면일 수 있다)");
dead.forEach((r) => console.log("   " + r.name));
console.log("\n⚠ 입구가 5곳 이상 — " + many.length + "곳");
many.forEach((r) => console.log("   " + r.name + "  " + r.in + "곳"));
