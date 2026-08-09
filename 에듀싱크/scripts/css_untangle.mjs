// ============================================================
// 🧵 CSS 실타래 풀기 (2026-08-09)
//
//   node scripts/css_untangle.mjs --dry     (무엇을 지울지 보기만)
//   node scripts/css_untangle.mjs           (실제로 지운다)
//
// 원리 — **같은 선택자 문자열**이 여러 번 나오면 특정성이 같으므로 **뒤엣것이 이긴다.**
// 그러니 앞쪽 규칙에서 «뒤에 또 나오는 속성»만 지우면 **결과가 한 글자도 안 바뀐다.**
// 죽은 선언만 사라지고 화면은 그대로다.
//
// ⚠ 지키는 것 —
//   ① `@media`·`@supports` 안쪽은 **건드리지 않는다**(적용 조건이 달라 «뒤엣것이 이긴다»가 성립 안 함)
//   ② 주석은 한 줄도 지우지 않는다 — 이 저장소는 «왜 그렇게 고쳤나»를 주석에 남긴다
//   ③ 속성이 다 지워져 빈 껍데기가 된 규칙만 통째로 뺀다
//   ④ 지운 뒤 **반드시 대비·면대비·유리·구조 검사를 다시 돌린다**
// ============================================================
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const P = join(HERE, "..", "app", "www", "style.css");
const src = readFileSync(P, "utf8");
const dry = process.argv.includes("--dry");

// 주석을 자리표시자로 빼 둔다(건드리지 않기 위해)
const notes = [];
let s = src.replace(/\/\*[\s\S]*?\*\//g, (m) => `\u0000${notes.push(m) - 1}\u0000`);

// 최상위 규칙만 모은다 — @media 안쪽은 depth>0 이라 건너뛴다
const rules = [];
let depth = 0, i = 0, selStart = 0;
while (i < s.length) {
  const c = s[i];
  if (c === "{") {
    if (depth === 0) {
      const sel = s.slice(selStart, i);
      const isAt = /^\s*@/.test(sel);
      let j = i + 1, d = 1;
      while (j < s.length && d > 0) { if (s[j] === "{") d++; else if (s[j] === "}") d--; j++; }
      if (!isAt) rules.push({ selRaw: sel, bodyStart: i + 1, bodyEnd: j - 1 });
      i = j; selStart = j; depth = 0; continue;
    }
  }
  i++;
}

// 선택자 문자열별로 «어느 속성이 어디서 마지막으로 정해졌나»
const lastAt = new Map();  // `${sel}|${prop}` -> 규칙 인덱스
rules.forEach((r, idx) => {
  const body = s.slice(r.bodyStart, r.bodyEnd);
  r.sels = r.selRaw.split(",").map((x) => x.trim().replace(/\s+/g, " ")).filter(Boolean);
  r.decls = [...body.matchAll(/(?:^|;)\s*([a-z-]+)\s*:\s*([^;]*)/gi)].map((m) => ({ prop: m[1], raw: m[0], at: m.index }));
  for (const sel of r.sels) for (const d of r.decls) lastAt.set(`${sel}|${d.prop}`, idx);
});

// 앞쪽에서 «뒤에 또 나오는» 선언을 지운다 — 선택자가 하나뿐인 규칙만(여러 개면 다른 선택자에 영향)
let removed = 0; const log = [];
const cuts = [];
rules.forEach((r, idx) => {
  if (r.sels.length !== 1) return;
  const sel = r.sels[0];
  for (const d of r.decls) {
    if (lastAt.get(`${sel}|${d.prop}`) === idx) continue;   // 여기가 마지막이면 살린다
    cuts.push({ from: r.bodyStart + d.at, to: r.bodyStart + d.at + d.raw.length });
    log.push(`${sel} — ${d.prop}`);
    removed++;
  }
});
cuts.sort((a, b) => b.from - a.from);
for (const c of cuts) s = s.slice(0, c.from) + (s[c.from] === ";" ? ";" : "") + s.slice(c.to);

// 빈 껍데기가 된 규칙 정리
const emptied = (s.match(/(?:^|\})\s*[^{}@]+\{\s*;*\s*\}/g) || []).length;
s = s.replace(/([^{}@]+)\{\s*;*\s*\}/g, (m, sel) => (/\u0000/.test(sel) ? m : ""));

s = s.replace(/\u0000(\d+)\u0000/g, (_, n) => notes[+n]);   // 주석 복원

console.log(`죽은 선언 ${removed}개 · 빈 껍데기 ${emptied}개`);
log.slice(0, 20).forEach((x) => console.log("   " + x));
if (log.length > 20) console.log(`   … 외 ${log.length - 20}개`);
console.log(`크기 ${Math.round(src.length / 1024)}KB → ${Math.round(s.length / 1024)}KB`);
if (dry) { console.log("\n(--dry 라 파일은 안 건드렸다)"); process.exit(0); }
writeFileSync(P, s, "utf8");
console.log("\n✅ 썼다. **이제 검사기 4종을 다시 돌릴 것** — 결과가 같아야 한다.");
