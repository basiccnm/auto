// ============================================================
// 🔬 글자 대비 검사 (2026-08-09)
//
//   node scripts/emul_eval.mjs --file scripts/probe_contrast.js
//
// probe_screens.js 의 대비 항목이 **오탐 투성이**라 따로 뗐다. 실제로 겪은 함정 둘 —
//
//   ⚠ ① color-mix() 결과는 `color(srgb 0.101961 0 0.2 / .6)` 꼴로 온다 — **0~1 범위**다.
//        rgb() 처럼 0~255 로 읽으면 전부 «거의 검정»이 되어 미달이 쏟아진다.
//        실측: 설정 화면 «34건» → 파서 고치니 «1건». 58건 보고도 대부분 이것이었다.
//   ⚠ ② 그라데이션으로 칠한 버튼은 backgroundColor 가 transparent 다.
//        그냥 위로 올라가면 «뒤 카드»를 배경으로 잡아 흰 글씨가 1.27 로 찍힌다.
//        실제로는 갈색 알약에 흰 글씨다 — **측정 불가**로 빼고 눈으로 본다.
//   ⚠ ③ 반투명 카드(유리)는 알파 합성을 해야 한다. 흰색 44% 를 흰색으로 치면 대비가 뻥튀기된다.
// ============================================================
(() => {
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
  return JSON.stringify({ 총: out.length, 측정불가: skip, 목록: [...new Set(out)].slice(0, 12) });
})()
