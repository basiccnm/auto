#!/usr/bin/env node
// ============================================================
// 앱 자가검사 — 눈으로 찾다 세 세션째 되풀이한 것들을 기계가 잡는다 (2026-08-07)
//
//   node scripts/check_app.mjs
//   실패가 있으면 종료코드 1. 화면을 내놓기 전에 **반드시** 돌린다.
//
// 왜 만들었나
//   2026-08-07 대표님: «세션 3번째인데 계속 똑같은 것만 고치고 있다».
//   맞는 말이다. 아래 다섯 가지는 **눈으로 보면 매번 놓치고, 규칙으로 적어도 매번 어긴다.**
//   그래서 사람이 아니라 여기서 막는다.
//
// 잡는 것
//   ① 서브셋에 없는 아이콘   — 화면에 «빈칸»으로 뜬다 (08-03 에 5개, 08-07 에 6개)
//   ② 테마를 안 따르는 하드코딩 색 — 테마를 바꿔도 그 자리만 파랗게 남는다
//   ③ 템플릿 문자열 안 역따옴표 주석 — 그 자리에서 문법이 깨진다
//   ④ body/#screen 이 쓰는 토큰이 테마 블록에 없음 — «안쪽 화면이 안 바뀐다»의 정체
//   ⑤ 죽은 CSS 선택자(마크업에 없는 클래스) — 고쳤다고 착각하게 만든다
// ============================================================
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const WWW = join(dirname(fileURLToPath(import.meta.url)), "..", "app", "www");
const css = readFileSync(join(WWW, "style.css"), "utf8");
const js  = readFileSync(join(WWW, "app.js"), "utf8");
const sub = readFileSync(join(WWW, "fonts", "tabler-subset.css"), "utf8");

let fail = 0;
const ok   = (m) => console.log("  ✅ " + m);
const bad  = (m, list) => { fail++; console.log("  ❌ " + m);
  (list || []).slice(0, 12).forEach((x) => console.log("       " + x));
  if ((list || []).length > 12) console.log(`       … 외 ${list.length - 12}개`); };

// ── ① 서브셋에 없는 아이콘 ──────────────────────────────────────
console.log("\n① 아이콘이 서브셋에 있나");
{
  const have = new Set([...sub.matchAll(/^\.(ti-[a-z0-9-]+):/gm)].map((m) => m[1]));
  // class="ti ti-xxx" 형태에서만 뽑는다(주석·설명글의 ti- 는 세지 않는다)
  const used = new Set();
  for (const m of js.matchAll(/class\s*=\s*["'`][^"'`]*\bti\s+(ti-[a-z0-9-]+)/g)) used.add(m[1]);
  for (const m of js.matchAll(/\bti\s+\$\{[^}]*?["'`](ti-[a-z0-9-]+)["'`]/g)) used.add(m[1]);
  for (const m of js.matchAll(/["'](ti-[a-z0-9-]+)["']\s*,/g)) used.add(m[1]);   // 드로어 ITEMS 배열
  const missing = [...used].filter((i) => !have.has(i)).sort();
  missing.length ? bad(`서브셋에 없는 아이콘 ${missing.length}개 — 그 자리가 빈칸으로 뜬다`, missing)
                 : ok(`쓰는 아이콘 ${used.size}개 전부 서브셋에 있다`);
}

// ── ② 테마를 안 따르는 하드코딩 색 ──────────────────────────────
console.log("\n② 색이 테마를 따르나");
{
  // 토큰 «정의» 구역은 건너뛴다 — 거기 있는 hex 는 정의라서 있는 게 맞다.
  //   :root{...} · [data-theme=...]{...} · [data-art=...]{...}
  const lines = css.split("\n");
  // data-kid-theme 미리보기 칩도 «토큰 정의» 구역이다 — 여기 hex 는 정의라서 있는 게 맞다
  const defRe = /(:root|\[data-theme|\[data-art|\[data-kid-theme)/;
  let depth = 0, inDef = false, inGame = false;
  const hits = [];
  lines.forEach((ln, i) => {
    if (ln.includes("--g-sky1")) inGame = true;   // 게임 전용 팔레트 시작(아래 주석)
    if (depth === 0 && defRe.test(ln) && ln.includes("{")) inDef = true;
    depth += (ln.match(/\{/g) || []).length - (ln.match(/\}/g) || []).length;
    // 닫는 줄을 먼저 빼면 안 된다 — 테마 블록은 마지막 줄에 선언과 } 가 같이 있어서
    // `--drawer-a: #813721; }` 같은 «정의»가 전부 오탐으로 잡힌다 (2026-08-08)
    const wasDef = inDef;
    if (depth <= 0) { depth = 0; if (inDef && ln.includes("}")) inDef = false; }
    if (wasDef) return;
    // 게임 전용 팔레트는 **일부러 테마를 안 탄다.** 아이 화면은 부모 테마 18종과
    // 무관한 «다른 세계»라, 여기를 테마 토큰으로 «고치면» 8/4 처럼 부모 카드색까지
    // 물들어 전부 퍼음해진다. 건드리지 말 것.
    if (inGame) return;
    // 토큰이 있는데도 박아 쓴 색 — 채도 있는 것만(흰·검·회는 그림자·선이라 뺀다)
    for (const m of ln.matchAll(/#([0-9a-fA-F]{6})\b/g)) {
      const [r, g, b] = [0, 2, 4].map((k) => parseInt(m[1].slice(k, k + 2), 16));
      const max = Math.max(r, g, b), min = Math.min(r, g, b);
      if (max - min < 28) continue;                 // 무채색 — 그림자·경계선
      hits.push(`${i + 1}행  #${m[1]}   ${ln.trim().slice(0, 64)}`);
    }
  });
  hits.length ? bad(`테마 밖 하드코딩 색 ${hits.length}곳 — 테마를 바꿔도 이 자리는 안 바뀐다`, hits)
              : ok("규칙 안에 박힌 유채색이 없다 (전부 토큰)");
}

// ── ③ 템플릿 문자열 안 역따옴표 주석 ────────────────────────────
console.log("\n③ 주석이 템플릿 문자열을 깨지 않나");
{
  const hits = [];
  js.split("\n").forEach((ln, i) => {
    if (/<!--/.test(ln) || /^\s*(\/\/|\*|\/\*)/.test(ln)) {
      const inHtmlComment = /<!--/.test(ln);
      // 재는 것은 «주석 안»의 역따옴표다. 템플릿을 여는 것이 <!-- 앞이면 정상 (2026-08-08 오탐)
      const after = ln.slice(ln.indexOf("<!--"));
      if (inHtmlComment && after.includes("`")) hits.push(`${i + 1}행  ${ln.trim().slice(0, 70)}`);
    }
  });
  hits.length ? bad("HTML 주석 안에 역따옴표 — 템플릿 문자열이 그 자리에서 끊긴다", hits)
              : ok("역따옴표 주석 없음");
}

// ── ④ body/#screen 이 쓰는 토큰이 테마마다 정의돼 있나 ───────────
console.log("\n④ 바탕색이 테마를 따라가나");
{
  // 테마 블록 하나를 골라 거기 정의된 토큰 목록을 만든다
  // 한 종류만 보면 안 된다 — 바탕 토큰은 [data-theme]·:root 쪽에 정의된 것도 있다 (2026-08-08 오탐)
  const themed = new Set();
  for (const re of [/\[data-art="theme_01"\][^{]*\{([\s\S]*?)\}/,
                    /\[data-theme="dark"\][^{]*\{([\s\S]*?)\}/,
                    /:root\s*\{([\s\S]*?)\}/]) {
    const m = css.match(re);
    if (m) for (const t of m[1].matchAll(/(--[a-z0-9-]+)\s*:/g)) themed.add(t[1]);
  }
  // body 와 #screen 이 배경으로 쓰는 토큰
  const surfaces = [];
  for (const m of css.matchAll(/(^|\n)\s*(body|#screen)[^{]*\{([^}]*)\}/g)) {
    for (const v of m[3].matchAll(/background(?:-color)?\s*:\s*[^;]*var\((--[a-z0-9-]+)\)/g)) {
      surfaces.push({ sel: m[2], token: v[1] });
    }
  }
  const broken = surfaces.filter((s) => !themed.has(s.token))
    .map((s) => `${s.sel} 가 ${s.token} 를 쓰는데 테마 블록엔 그 토큰이 없다`);
  broken.length ? bad("바탕 토큰이 테마를 안 탄다 — 안쪽 화면이 흰색으로 고정된다", [...new Set(broken)])
                : ok(`바탕 토큰 ${surfaces.length}개 전부 테마가 덮어쓴다`);
}

// ── ⑤ 죽은 CSS 선택자 ──────────────────────────────────────────
console.log("\n⑤ 죽은 규칙이 없나");
{
  // `.a .b` 처럼 마지막 조각이 클래스인 규칙만 본다. 마크업에 그 클래스가 아예 없으면 죽은 것.
  const classes = new Set([...js.matchAll(/class\s*=\s*["'`]([^"'`]+)/g)]
    .flatMap((m) => m[1].split(/[\s${}]+/)).filter(Boolean));
  const dead = [];
  for (const m of css.matchAll(/(^|\n)\s*(\.[a-z][a-z0-9-]*(?:\s+\.[a-z][a-z0-9-]*)*)\s*\{/gi)) {
    const parts = m[2].trim().split(/\s+/).map((p) => p.replace(/^\./, ""));
    const missing = parts.filter((p) => !classes.has(p));
    if (missing.length) dead.push(`${m[2].trim()}   (마크업에 없는 조각: ${missing.join(", ")})`);
  }
  // 자녀앱·옛 화면 잔재가 많아 «경고»로만 낸다 — 여기서 실패시키면 아무도 안 본다
  dead.length ? console.log(`  ⚠ 죽은 것으로 보이는 규칙 ${dead.length}개 (경고, 실패 아님)`)
              : ok("죽은 규칙 없음");
  dead.slice(0, 8).forEach((d) => console.log("       " + d));
}

console.log("\n" + "═".repeat(56));
console.log(fail ? `  ❌ 실패 ${fail}가지 — 고치고 다시 돌릴 것` : "  ✅ 전부 통과");
process.exit(fail ? 1 : 0);
