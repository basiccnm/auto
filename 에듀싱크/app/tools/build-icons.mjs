/* ═══════════════════════════════════════════════════════════
   Tabler 아이콘 로컬 번들 만들기 (2026-07-25)

   왜: 폰 앱은 오프라인·CSP라 CDN(<link ...jsdelivr...>)이 안 뜬다.
       그렇다고 전체 폰트를 넣으면 woff2 857KB + CSS 236KB가 통째로 따라온다.
       우리가 쓰는 건 50개 남짓 → 그것만 잘라 넣는다.

   쓰는 법 (아이콘을 새로 쓰기 시작했으면 다시 돌린다):
     cd app && node tools/build-icons.mjs
   준비물: npm i @tabler/icons-webfont@3.24.0 · pip install fonttools brotli

   만드는 것: www/fonts/tabler-subset.woff2 · www/fonts/tabler-subset.css
   ═══════════════════════════════════════════════════════════ */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const WWW = path.join(APP, "www");
const OUT = path.join(WWW, "fonts");
const DIST = path.join(APP, "node_modules", "@tabler", "icons-webfont", "dist");
const VERSION = "3.24.0";

if (!fs.existsSync(DIST)) {
  console.error("@tabler/icons-webfont 이 없다 → cd app && npm i @tabler/icons-webfont@" + VERSION);
  process.exit(1);
}
fs.mkdirSync(OUT, { recursive: true });

// 1) 목업 소스에서 실제로 쓰는 ti-xxx 를 전부 긁는다
const src = ["app.js", "index.html", "style.css"]
  .map((f) => fs.readFileSync(path.join(WWW, f), "utf8")).join("\n");
const used = [...new Set([...src.matchAll(/\bti-[a-z0-9]+(?:-[a-z0-9]+)*/g)].map((m) => m[0]))].sort();

// 2) 공식 CSS에서 클래스 → 코드포인트
const map = new Map();
for (const m of fs.readFileSync(path.join(DIST, "tabler-icons.min.css"), "utf8")
  .matchAll(/\.ti-([a-z0-9-]+):before\{content:"\\([0-9a-f]+)"\}/g)) map.set("ti-" + m[1], m[2]);

const found = used.filter((u) => map.has(u));
const missing = used.filter((u) => !map.has(u));
if (missing.length) console.warn("⚠ 이름이 틀렸거나 없는 아이콘: " + missing.join(", "));
// `ti-${cond ? "a" : "b"}` 처럼 이름을 쪼개 쓰면 여기서 못 찾아 그 아이콘만 빈칸이 된다.
// 조용히 빠지면 폰에서야 발견하므로 미리 잡는다.
const split = [...src.matchAll(/\bti-\$\{/g)].length;
if (split) { console.error(`아이콘 이름을 template로 쪼갠 곳 ${split}군데 — 'ti-\${…}' 대신 전체 이름을 쓸 것`); process.exit(1); }
if (!found.length) { console.error("찾은 아이콘이 없다 — 정규식/버전 확인"); process.exit(1); }

// 3) 폰트를 그 글자들만 남기고 잘라낸다
const woff2 = path.join(OUT, "tabler-subset.woff2");
execFileSync("python", ["-m", "fontTools.subset",
  path.join(DIST, "fonts", "tabler-icons.woff2"),
  "--unicodes=" + found.map((f) => "U+" + map.get(f)).join(","),
  "--flavor=woff2", "--layout-features=", "--no-hinting", "--desubroutinize",
  "--output-file=" + woff2,
], { stdio: "inherit" });

// 4) 최소 CSS — @font-face + 쓰는 클래스만
// 파일 이름은 그대로인데 내용만 바뀌므로, 아이콘 목록이 달라지면 ?v= 가 바뀌게 해서
// 브라우저·웹뷰가 옛 폰트를 계속 쓰는 일을 막는다(2026-07-25: 새 아이콘 2개가 빈칸으로 나왔다).
const stamp = found.length + "-" + [...found.join(",")].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 7).toString(36);
const css = `/* 자동 생성 — tools/build-icons.mjs (Tabler ${VERSION} 서브셋 ${found.length}자).
   손으로 고치지 말 것. 아이콘을 새로 쓰면 스크립트를 다시 돌린다. */
@font-face {
  font-family: "tabler-icons";
  font-style: normal;
  font-weight: 400;
  font-display: block;
  src: url("tabler-subset.woff2?v=${stamp}") format("woff2");
}
.ti {
  font-family: "tabler-icons" !important;
  font-style: normal; font-weight: normal; font-variant: normal;
  text-transform: none; line-height: 1;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
  display: inline-block; speak: none;
}
${found.map((f) => `.${f}::before { content: "\\${map.get(f)}"; }`).join("\n")}
`;
fs.writeFileSync(path.join(OUT, "tabler-subset.css"), css, "utf8");

const kb = (p) => Math.round(fs.statSync(p).size / 1024) + "KB";
console.log(`아이콘 ${found.length}개 · woff2 ${kb(woff2)} (원본 ${kb(path.join(DIST, "fonts", "tabler-icons.woff2"))}) · css ${kb(path.join(OUT, "tabler-subset.css"))}`);
