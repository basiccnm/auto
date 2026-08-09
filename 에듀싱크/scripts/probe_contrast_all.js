// ============================================================
// 🔬 대비 전수 — **모든 화면 × 여러 테마**를 브라우저 안에서 한 바퀴 (2026-08-09)
//
//   node scripts/emul_eval.mjs --file scripts/probe_contrast_all.js
//
// ⚠ 화면마다 node 를 새로 띄우면 20화면에 몇 분이 걸린다. 그래서 그동안
//   «20화면 2테마»만 재고 「전수」라고 불렀다 — 실제로는 52화면 18테마다.
//   화면 이동·측정을 전부 브라우저 안에서 돌려 한 번의 호출로 끝낸다.
// ============================================================
(async () => {
  const measure = () => {
  /* ⚠ 색 문자열은 두 가지로 온다 —
       rgb(26, 26, 31) / rgba(255,255,255,.44)   ← 0~255
       color(srgb 0.101961 0 0.2 / 0.6)          ← **0~1** (color-mix 결과가 이 꼴로 온다)
     둘을 같은 자로 읽으면 color-mix 색이 전부 «거의 검정»으로 잡혀 오탐이 쏟아진다. */
  const px = (c) => {
    if (!c) return null;
    const n = (c.match(/[\d.]+(?=[\s,)/])|[\d.]+/g) || []).map(Number);
    if (!n.length) return null;
    if (/^color\(/.test(c)) {                       // 0~1 → 0~255
      const [r, g, b] = n.slice(0, 3).map((v) => v * 255);
      return [r, g, b, n.length > 3 ? n[3] : 1];
    }
    return [n[0], n[1], n[2], n.length > 3 ? n[3] : 1];
  };
  const over = (f, b) => [0, 1, 2].map((i) => f[i] * f[3] + b[i] * (1 - f[3]));
  const lum = (v) => { const [r, g, b] = v.map((x) => { x /= 255; return x <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); }); return .2126 * r + .7152 * g + .0722 * b; };
  const cr = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + .05) / (y + .05); };
  const bg = (el) => {
    let e = el; const st = [];
    while (e) { const p = px(getComputedStyle(e).backgroundColor);
      if (p && p[3] > 0) { st.push(p); if (p[3] >= 1) break; }
      e = e.parentElement; }
    let base = [255, 255, 255];
    for (let i = st.length - 1; i >= 0; i--) base = over(st[i], base);
    return base;
  };
  /* 자기 자신 ~ 불투명 배경을 만나기 전까지 사이에 그라데이션이 있으면 «측정 불가» */
  const paintedByGradient = (el) => {
    let e = el;
    while (e) {
      const s = getComputedStyle(e);
      if (/gradient/.test(s.backgroundImage)) return true;
      const p = px(s.backgroundColor);
      if (p && p[3] >= 1) return false;
      e = e.parentElement;
    }
    return false;
  };
  const out = []; let skip = 0;
  for (const e of document.querySelectorAll("b,em,span,p,h1,h2,h3,button,a,i,div,label")) {
    if (e.children.length) continue;
    const t = (e.textContent || "").trim(); if (!t) continue;
    const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) continue;
    const c = getComputedStyle(e); const col = px(c.color); if (!col) continue;
    /* 그라데이션으로 칠한 면 위의 글자는 잴 수 없다 — 재려 들면 뒤 카드를 배경으로 잡아 오탐이 난다 */
    if (paintedByGradient(e)) { skip++; continue; }
    const sz = parseFloat(c.fontSize), fw = parseInt(c.fontWeight) || 400;
    const need = (sz >= 24 || (sz >= 18.66 && fw >= 700)) ? 3 : 4.5;
    const b = bg(e);
    const v = cr(over(col, b), b);
    if (v < need) out.push(((e.className || e.tagName) + "").split(/\s+/)[0] + " " + v.toFixed(2) + "<" + need + ' "' + t.slice(0, 12) + '"');
  }
  return { 총: out.length, 목록: [...new Set(out)].slice(0, 6) };
};
  const ALL = Object.keys(typeof Screens !== "undefined" ? Screens : {})
    .filter((k) => typeof Screens[k] === "function" && k !== "holdGuard");
  const SKIP = ["login", "intro", "register", "findpw", "locked", "childlocked", "childexpired"];
  const SCREENS = ALL.filter((k) => !SKIP.includes(k));
  /* 테마는 «밝기 양극단 + 채도 높은 것»을 고른다 — 18종을 다 도는 것보다
     깨지는 자리를 훨씬 빨리 드러낸다. 통과하면 사이 값들은 따라온다. */
  const SETS = [["light", "theme_13"], ["light", "theme_07"], ["light", "theme_01"],
                ["dark", "theme_04"], ["dark", "theme_10"]];
  const bad = [];
  let screensSeen = 0;
  for (const [th, art] of SETS) {
    App.setTheme(th); App.setArt(art);
    for (const sc of SCREENS) {
      location.hash = "#" + sc;
      await new Promise((r) => setTimeout(r, 260));
      App.render();
      await new Promise((r) => setTimeout(r, 170));
      screensSeen++;
      const m = measure();
      if (m.총) bad.push(th + "/" + art + "/" + sc + " → " + m.목록.join(" | "));
    }
  }
  App.setTheme("light"); App.setArt("theme_13"); location.hash = "#home"; App.render();
  return JSON.stringify({ 화면수: SCREENS.length, 조합: SETS.length, 잰횟수: screensSeen,
                          문제: bad.length, 목록: bad.slice(0, 25) }, null, 1);
})()
