// ============================================================
// 🧊 유리 안 먹은 자리 찾기 (2026-08-09)
//
//   node scripts/emul_eval.mjs --file scripts/probe_glass.js
//
// 눈으로 38장을 보는 대신 **불투명한 큰 면**을 전 화면에서 찾는다.
// 유리는 반투명(알파 < 1)이다 — 알파가 1인 넓은 면이 남아 있으면 그게 «공책 느낌»의 자리다.
// ⚠ 화면 바탕(body·#screen)과 버튼·칩은 뺀다. 불투명해야 맞는 것들이다.
// ============================================================
(async () => {
  const ALL = Object.keys(typeof Screens !== "undefined" ? Screens : {})
    .filter((k) => typeof Screens[k] === "function" && k !== "holdGuard");
  const SKIP = ["login", "intro", "register", "findpw", "locked", "childlocked", "childexpired"];
  const px = (c) => (c.match(/[\d.]+/g) || []).map(Number);
  const hits = {};
  for (const sc of ALL.filter((k) => !SKIP.includes(k))) {
    location.hash = "#" + sc;
    await new Promise((r) => setTimeout(r, 300));
    App.render();
    await new Promise((r) => setTimeout(r, 250));
    for (const e of document.querySelectorAll("div, section, li, ul, article, label, form")) {
      const r = e.getBoundingClientRect();
      if (r.width < 140 || r.height < 34) continue;          // 작은 것은 칩·뱃지다
      if (r.width > 380 && r.height > 600) continue;          // 화면 바탕
      const cs = getComputedStyle(e);
      const p = px(cs.backgroundColor);
      if (p.length < 3) continue;
      const a = p.length > 3 ? p[3] : 1;
      if (a < 1) continue;                                    // 이미 반투명 = 유리
      if (cs.backgroundColor === "rgba(0, 0, 0, 0)") continue;
      const cn = (e.className || "").toString().split(/\s+/)[0];
      if (!cn) continue;
      (hits[cn] = hits[cn] || new Set()).add(sc);
    }
  }
  const out = Object.entries(hits)
    .map(([k, v]) => [k, [...v]])
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 20)
    .map(([k, v]) => `${k}  (${v.length}화면) ${v.slice(0, 4).join(",")}`);
  return JSON.stringify({ 불투명한_면: out.length, 목록: out }, null, 1);
})()
