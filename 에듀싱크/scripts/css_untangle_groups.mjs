// 묶음 규칙에서 «죽은 이름»만 빼낸다. 원리와 주의는 css_untangle.mjs 아래 주석 참조.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const HERE = dirname(fileURLToPath(import.meta.url));
const P = join(HERE, "..", "app", "www", "style.css");
const src = readFileSync(P, "utf8");
const dry = process.argv.includes("--dry");

/* ⚠ 쉼표로 그냥 쪼개면 `:where(a, b)` 처럼 **괄호 안의 쉼표**까지 잘라서
   `:where(.hp-tx b` 같은 반쪽 선택자가 나온다 — 그대로 지우면 CSS 가 깨진다.
   (2026-08-09 dry-run 에서 실제로 나왔다. 돌리기 전에 목록을 눈으로 봐서 잡았다.) */
const splitSel = (str) => {
  const out = []; let depth = 0, cur = "";
  for (const ch of str) {
    if (ch === "(") depth++;
    else if (ch === ")") depth--;
    if (ch === "," && depth === 0) { out.push(cur); cur = ""; continue; }
    cur += ch;
  }
  out.push(cur);
  return out.map((x) => x.trim().replace(/\s+/g, " ")).filter(Boolean);
};


const notes = [];
let s = src.replace(/\/\*[\s\S]*?\*\//g, (m) => `\u0000${notes.push(m) - 1}\u0000`);

// 최상위 규칙만 (@media 안쪽 제외)
const rules = [];
let i = 0, selStart = 0;
while (i < s.length) {
  if (s[i] === "{") {
    const sel = s.slice(selStart, i);
    let j = i + 1, d = 1;
    while (j < s.length && d > 0) { if (s[j] === "{") d++; else if (s[j] === "}") d--; j++; }
    if (!/^\s*@/.test(sel)) rules.push({ selStart, selEnd: i, sel, body: s.slice(i + 1, j - 1) });
    i = j; selStart = j; continue;
  }
  i++;
}
rules.forEach((r) => {
  r.sels = splitSel(r.sel);
  r.props = [...r.body.matchAll(/(?:^|;)\s*([a-z-]+)\s*:/gi)].map((m) => m[1]);
});
const last = new Map();
rules.forEach((r, idx) => { for (const sl of r.sels) for (const p of r.props) last.set(`${sl}|${p}`, idx); });

let cut = 0; const log = [];
const edits = [];
rules.forEach((r, idx) => {
  if (r.sels.length < 2 || !r.props.length) return;
  const keep = r.sels.filter((sl) => r.props.some((p) => last.get(`${sl}|${p}`) === idx));
  if (keep.length === r.sels.length || keep.length === 0) return;
  const dead = r.sels.filter((sl) => !keep.includes(sl));
  edits.push({ from: r.selStart, to: r.selEnd, text: (r.sel.match(/^\s*/) || [""])[0] + keep.join(", ") + " " });
  dead.forEach((d) => log.push(`${d}  ← 묶음(${r.sels.length}개)에서 뺌`));
  cut += dead.length;
});
edits.sort((a, b) => b.from - a.from);
for (const e of edits) s = s.slice(0, e.from) + e.text + s.slice(e.to);
s = s.replace(/\u0000(\d+)\u0000/g, (_, n) => notes[+n]);

console.log(`묶음에서 뺀 죽은 이름 ${cut}개`);
log.slice(0, 15).forEach((x) => console.log("   " + x));
if (log.length > 15) console.log(`   … 외 ${log.length - 15}개`);
console.log(`크기 ${Math.round(src.length / 1024)}KB → ${Math.round(s.length / 1024)}KB`);
if (dry) { console.log("\n(--dry 라 파일은 안 건드렸다)"); process.exit(0); }
writeFileSync(P, s, "utf8");
console.log("\n✅ 썼다. 검사기 4종을 다시 돌릴 것.");
