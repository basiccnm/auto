// ============================================================
// 🎨 테마 섞임 탐지 — **기기에서 실제 색을 재서** 찾는다 (2026-08-08)
//
//   node scripts/emul_eval.mjs --file scripts/probe_theme_leak.js
//   CDP_PORT=9334 node scripts/emul_eval.mjs --file scripts/probe_theme_leak.js   (자녀 폰)
//
// 아이 세계(.gm/.gmw/.gmp) 안에서 **부모 테마 토큰의 색을 그대로 쓰는 요소**를 찾는다.
// 눈으로는 못 찾는다 — 테마에 따라 비슷해 보이는 색이 많고, 화면이 수십 개다.
//
// 실제로 이렇게 잡았다(08-08):
//   · 상점의 .ms-mkbtn·.ti·맨 span/b/em 이 부모 색이었다
//   · .gmp 에 토큰만 갈아입히고 color 를 안 줘서 **글자가 부모 --ink 로 상속**됐다
//
// ⚠ 0 이 나와야 통과다. 화면을 옮겨 가며(#game·#store·#tickets·#mission) 돌린다.
// ============================================================
(() => {
  // 부모 테마 토큰의 «실제 색»을 읽어 두고, 아이 세계 안에서 그 색을 쓰는 요소를 찾는다.
  const root = getComputedStyle(document.documentElement);
  const theme = {};
  ["--card-a","--card-b","--surf","--outer","--bg","--card","--chip","--accent","--accent-ink","--ink","--muted","--drawer-a"]
    .forEach(k => { const v = root.getPropertyValue(k).trim(); if (v) theme[k] = v; });
  const norm = (c) => c.replace(/\s/g, "").toLowerCase();
  const themeColors = new Map();
  for (const [k, v] of Object.entries(theme)) {
    const d = document.createElement("div"); d.style.color = v; document.body.appendChild(d);
    themeColors.set(norm(getComputedStyle(d).color), k); d.remove();
  }
  const world = document.querySelector(".gmw, .gm, .gmp");
  if (!world) return JSON.stringify({ err: "아이 세계 껍데기가 없다", hash: location.hash });
  const hits = [];
  for (const el of world.querySelectorAll("*")) {
    const cs = getComputedStyle(el);
    for (const prop of ["backgroundColor", "color", "borderTopColor"]) {
      const c = norm(cs[prop]);
      if (c === "rgba(0,0,0,0)" || c === "transparent") continue;
      const t = themeColors.get(c);
      if (t) {
        const sel = el.tagName.toLowerCase() + (el.className && typeof el.className === "string"
          ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : "");
        hits.push(sel + "  " + prop + "=" + t);
      }
    }
  }
  const uniq = [...new Set(hits)];
  return JSON.stringify({ hash: location.hash, n: uniq.length, hits: uniq.slice(0, 20) });
})()
