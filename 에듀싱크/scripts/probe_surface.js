// ============================================================
// 🎚 면 대비 — 배경 ↔ 카드가 갈리는가 (2026-08-09)
//
//   node scripts/emul_eval.mjs --file scripts/probe_surface.js
//
// ⚠ 지금까지 «글자 대비»만 쟀다(probe_contrast). 글자가 다 통과해도
//   **카드가 배경에 묻히면** 화면은 밋밋하고 «공책 느낌»이 된다.
//   실제로 이 앱은 배경↔카드가 1.28:1 이던 적이 있다.
// ⚠ 유리는 반투명이라 알파를 합성해서 «실제로 칠해진 색»을 구해야 한다.
// 기준: 1.15:1 미만이면 사실상 같은 면이다(경계가 테두리로만 남는다).
// ============================================================
(async () => {
  const px = (c) => {
    if (!c) return null;
    const n = (c.match(/[\d.]+/g) || []).map(Number);
    if (!n.length) return null;
    if (/^color\(/.test(c)) return [n[0]*255, n[1]*255, n[2]*255, n.length>3?n[3]:1];
    return [n[0], n[1], n[2], n.length > 3 ? n[3] : 1];
  };
  const over = (f, b) => [0,1,2].map((i) => f[i]*f[3] + b[i]*(1-f[3]));
  const lum = (v) => { const [r,g,b] = v.map((x) => { x/=255; return x<=.03928 ? x/12.92 : Math.pow((x+.055)/1.055, 2.4); }); return .2126*r+.7152*g+.0722*b; };
  const cr = (a, b) => { const [x,y] = [lum(a), lum(b)].sort((m,n)=>n-m); return (x+.05)/(y+.05); };
  const paint = (el) => { let e = el, st = [];
    while (e) { const p = px(getComputedStyle(e).backgroundColor);
      if (p && p[3] > 0) { st.push(p); if (p[3] >= 1) break; } e = e.parentElement; }
    let base = [255,255,255];
    for (let i = st.length-1; i >= 0; i--) base = over(st[i], base);
    return base; };

  const THEMES = Array.from({length: 18}, (_, i) => "theme_" + String(i+1).padStart(2, "0"));
  const bad = [];
  for (const art of THEMES) {
    for (const th of ["light", "dark"]) {
      App.setTheme(th); App.setArt(art);
      location.hash = "#home"; App.render();
      await new Promise((r) => setTimeout(r, 260));
      const card = document.querySelector(".hv3-card, .card");
      const scr = document.getElementById("screen") || document.body;
      if (!card) continue;
      const v = cr(paint(card), paint(scr.parentElement || document.body));
      if (v < 1.15) bad.push(`${art}/${th} → 배경↔카드 ${v.toFixed(2)}`);
    }
  }
  App.setTheme("light"); App.setArt("theme_13"); location.hash = "#home"; App.render();
  return JSON.stringify({ 잰조합: 36, 묻힌조합: bad.length, 목록: bad }, null, 1);
})()
