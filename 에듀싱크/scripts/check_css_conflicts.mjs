// ============================================================
// 🧩 CSS 충돌 검사 (2026-08-09)
//
//   node scripts/check_css_conflicts.mjs
//
// 왜 만들었나 — 2026-08-09 하루에 **「규칙을 썼는데 밀려서 안 먹었다」가 네 번** 났다.
//   · .tk 를 유리 목록에 넣었는데 아이 세계 규칙이 뒤에서 덮고 있었다
//   · 일요일 규칙이 «오늘이면서 일요일인 칸»을 덮어 대비 2.09 를 만들었다
//   · .rp-hd 에 색을 줬는데 자식이 자기 색을 갖고 있었다
//   · .mr-star 라는 **없는 클래스**에 색을 줬다
//
// ⚠ 성능 문제가 아니다 — 실측 시작 719ms · 렌더 1ms 로 멀쩡하다.
//   **다음 수정이 서로 싸우는 것**이 문제다. 그걸 미리 잡는다.
// ⚠ 오탐이 쏟아지는 검사기는 없는 것만 못하다(오늘 「흐린 글자 58건」이 그랬다).
//   그래서 셋 다 «거의 확실한 것»만 잡도록 좁혔다.
// ============================================================
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const cssRaw = readFileSync(join(HERE, "..", "app", "www", "style.css"), "utf8");
/* ⚠ app.js 만 보면 유령이 306개 나온다 — **워커 템플릿**(관리자·공개 사이트)이
   쓰는 클래스를 통째로 놓치기 때문이다. style.css 는 앱과 웹이 같이 쓴다. */
const SRC = ["app/www/app.js", "app/www/index.html"].concat(
  readdirSync(join(HERE, "..", "workers", "site-renderer", "src")).filter((f) => f.endsWith(".js")).map((f) => join("workers", "site-renderer", "src", f)));
const js = SRC.map((f) => { try { return readFileSync(join(HERE, "..", f), "utf8"); } catch { return ""; } }).join(String.fromCharCode(10));
const css = cssRaw.replace(/\/\*[\s\S]*?\*\//g, " ");
const lineOf = (i) => cssRaw.slice(0, i).split("\n").length;

const rules = [];
for (const m of css.matchAll(/([^{}@]+)\{([^{}]*)\}/g)) {
  const at = lineOf(m.index);
  const props = [...m[2].matchAll(/(?:^|;)\s*([a-z-]+)\s*:/g)].map((x) => x[1]);
  for (const s of m[1].split(",").map((x) => x.trim().replace(/\s+/g, " ")).filter(Boolean)) {
    rules.push({ sel: s, props, body: m[2], at });
  }
}

let warn = 0;
const say = (t, list, cap = 12) => {
  warn++; console.log(`  ⚠ ${t}`);
  list.slice(0, cap).forEach((x) => console.log(`       ${x}`));
  if (list.length > cap) console.log(`       … 외 ${list.length - cap}개`);
};

// ── ① 같은 선택자가 같은 속성을 여러 곳에서 다시 정한다 ──────────
console.log("① 같은 선택자가 같은 속성을 여러 곳에서 다시 정하나 (앞엣것은 죽은 규칙)");
{
  const bySel = new Map();
  for (const r of rules) (bySel.get(r.sel) || bySel.set(r.sel, []).get(r.sel)).push(r);
  const bad = [];
  for (const [sel, rs] of bySel) {
    if (rs.length < 2) continue;
    const seen = new Set(); const dup = new Set();
    for (const r of rs) for (const p of r.props) (seen.has(p) ? dup : seen).add(p);
    if (dup.size) bad.push(`${sel} — ${[...dup].slice(0, 4).join(", ")} (줄 ${rs.map((r) => r.at).join(", ")})`);
  }
  bad.length ? say(`${bad.length}곳 — 뒤엣것만 살아 있다. 한 곳으로 합칠 것`, bad) : console.log("  ✅ 없음");
}

// ── ② 앱에 아예 없는 이름에 스타일을 줬나 ───────────────────────
console.log("\n② app.js 어디에도 없는 클래스에 스타일을 줬나 (짐작으로 쓴 선택자)");
{
  /* ⚠ class="..." 만 훑었더니 유령이 327개 나왔다 — 템플릿·동적 조립·JS 상수를 다 놓쳤다.
     → 이름이 app.js 안에 «문자로라도» 있으면 쓰는 것으로 본다.
       놓치는 건 있어도 **거짓말은 안 한다.** */
  const ghosts = new Set();
  for (const r of rules) {
    for (const c of r.sel.matchAll(/\.([a-z][\w-]{2,})/gi)) if (!js.includes(c[1])) ghosts.add(c[1]);
  }
  const g = [...ghosts].sort();
  g.length ? say(`${g.length}개 — 오타이거나 옛 이름이다`, g, 20) : console.log("  ✅ 없음");
}

// ── ③ 어두운 글씨색인데 다크 규칙이 없다 ────────────────────────
console.log("\n③ 어두운 글씨색인데 다크 규칙이 없나 (오늘 네 번 깨진 실수)");
{
  const DARK = /\[data-theme="(dark|navy|charcoal|lavender)"\]/;
  const darkSels = new Set(rules.filter((r) => DARK.test(r.sel))
    .map((r) => r.sel.replace(/:root(\[data-theme="[^"]+"\])?\s*/g, "").trim()));
  /* ⚠ 「고정 hex 를 썼다」만으로 잡으면 186곳이 나오는데 대부분 멀쩡하다.
     오늘 실제로 깨진 건 **어두운 «글씨»색**뿐이다(sun 4.09 → 1.59 · 요일 1.41). 그것만 본다. */
  const lum = (hex) => {
    const h = hex.replace("#", "");
    const p = h.length === 3 ? h.split("").map((c) => c + c) : [h.slice(0, 2), h.slice(2, 4), h.slice(4, 6)];
    const [r, g, b] = p.map((x) => parseInt(x, 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const bad = [];
  for (const r of rules) {
    if (DARK.test(r.sel)) continue;
    const c = r.body.match(/(?:^|;)\s*color\s*:\s*(#[0-9a-f]{3,6})\b/i);
    if (!c || lum(c[1]) > 0.22) continue;
    if (!darkSels.has(r.sel.replace(/^:root\s*/, "").trim())) bad.push(`${r.sel}  color:${c[1]}  (줄 ${r.at})`);
  }
  bad.length ? say(`${bad.length}곳 — 다크에서 안 보일 수 있다`, bad) : console.log("  ✅ 없음");
}

console.log("\n════════════════════════════════════════════════════════");
console.log(warn ? `  ⚠ 살펴볼 것 ${warn}가지 (실패가 아니라 «다음에 싸울 자리»다)` : "  ✅ 충돌 없음");
