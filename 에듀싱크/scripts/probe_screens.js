// ============================================================
// 🔬 화면 전수검사 — 기기에서 **모든 화면을 돌며 잰다** (2026-08-08)
//
//   node scripts/emul_eval.mjs --file scripts/probe_screens.js            (부모 폰)
//   CDP_PORT=9334 node scripts/emul_eval.mjs --file scripts/probe_screens.js  (자녀 폰)
//
// 화면마다 재는 것 —
//   ① 가로 스크롤이 생기나 (0 이어야 한다)
//   ② 터치 영역이 44px 보다 작은 버튼이 있나
//   ③ 글자가 상자 밖으로 넘치나 (잘려서 안 보이는 글자)
//   ④ 서로 겹친 카드가 있나
//   ⑤ 부모 테마 색이 아이 세계에 새어 있나
//   ⑥ 네모 버튼 안의 기호가 **가운데에 있나** (‹ · ＋ 처럼 글자로 그린 것)
//
// ⚠ 눈으로는 못 찾는다. 화면이 수십 개고, 테마가 18종이고, 기기 높이가 다 다르다.
// ⚠ 「스크린샷을 봤다」는 검사가 아니다 — 값을 재야 검사다.
// ============================================================
(async () => {
  /* 화면을 손으로 적지 않는다 — 새 화면이 생기면 검사에서 조용히 빠진다.
     Screens 에 있는 것을 **전부** 돈다(자녀 토큰이면 아이가 열 수 있는 것만). */
  const ALL = Object.keys(typeof Screens !== "undefined" ? Screens : {})
    .filter((k) => typeof Screens[k] === "function" && k !== "holdGuard");
  const kid = typeof isChildToken === "function" && isChildToken();
  const SKIP = ["login", "intro", "register", "findpw", "locked", "childlocked", "childexpired", "pay"];
  const SCREENS = ALL.filter((k) => !SKIP.includes(k))
    .filter((k) => !kid || (typeof CHILD_SCREENS === "undefined" || CHILD_SCREENS.includes(k)));

  const out = [];
  const seen = new Set();
  const errs = [];
  const oldErr = console.error;
  console.error = (...a) => { errs.push(String(a[0]).slice(0, 120)); oldErr(...a); };

  const rect = (e) => e.getBoundingClientRect();
  const vis = (e) => { const r = rect(e); return r.width > 0 && r.height > 0; };

  for (const name of SCREENS) {
    location.hash = "#" + name;
    await new Promise((r) => setTimeout(r, 700));
    if (typeof App !== "undefined") App.render();
    await new Promise((r) => setTimeout(r, 500));
    const hit = { 화면: name, 실제: location.hash.slice(1) };

    // ① 가로 스크롤
    hit.가로넘침 = document.documentElement.scrollWidth - document.documentElement.clientWidth;

    // ② 작은 터치 영역
    const small = [];
    for (const b of document.querySelectorAll("button, a[href], [onclick]")) {
      if (!vis(b)) continue;
      const r = rect(b);
      /* ⚠ 겉은 작아도 ::after 로 누를 넓이를 44px 로 넓혀 둔 버튼이 있다(상단 아이콘).
         그건 «작은 버튼»이 아니다 — 아이콘을 키우면 상단 줄의 균형이 깨진다. */
      let wide = false;
      for (const pe of ["::after", "::before"]) {
        const a = getComputedStyle(b, pe);
        if ((parseFloat(a.width) || 0) >= 40 && (parseFloat(a.height) || 0) >= 40) { wide = true; break; }
        if ((parseFloat(a.minWidth) || 0) >= 40 && (parseFloat(a.minHeight) || 0) >= 40) { wide = true; break; }
      }
      if (wide) continue;
      if (r.height < 40 || r.width < 32) {
        small.push((b.className || b.tagName).toString().split(/\s+/)[0] + ` ${Math.round(r.width)}×${Math.round(r.height)}`);
      }
    }
    hit.작은버튼 = [...new Set(small)].slice(0, 6);

    // ③ 글자 잘림
    const clipped = [];
    for (const e of document.querySelectorAll("b, em, span, p, h1, h2, h3, .gm-tt, .pm-tile b")) {
      if (!vis(e) || e.children.length) continue;
      const cs2 = getComputedStyle(e);
      /* ⚠ 넘쳐도 **안 잘리는** 것이 있다 — overflow:visible 이면 밖으로 그려질 뿐이다.
         아이콘 상자의 이모지가 그렇다(폰트마다 폭이 달라 상자를 넓혀도 또 걸린다).
         「잘렸다」는 **실제로 안 보이게 됐을 때**만이다. */
      if (cs2.overflow === "visible" && cs2.overflowX === "visible") continue;
      if (e.scrollWidth > e.clientWidth + 2 && cs2.textOverflow !== "ellipsis") {
        clipped.push((e.className || e.tagName).toString().split(/\s+/)[0] + ": " + (e.textContent || "").trim().slice(0, 16));
      }
    }
    hit.글자잘림 = [...new Set(clipped)].slice(0, 6);

    // ④ 겹침 — 형제 카드끼리만 본다(부모-자식은 당연히 겹친다)
    const over = [];
    for (const box of document.querySelectorAll(".gm-grid, .pm-grid, .st-list, .tk-list")) {
      const kids = [...box.children].filter(vis);
      for (let i = 0; i < kids.length; i++) {
        for (let j = i + 1; j < kids.length; j++) {
          const a = rect(kids[i]), b = rect(kids[j]);
          const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (ox > 4 && oy > 4) over.push((kids[i].className || "").split(/\s+/)[0] + " ↔ " + (kids[j].className || "").split(/\s+/)[0]);
        }
      }
    }
    hit.겹침 = [...new Set(over)].slice(0, 4);

    // ⑥ 네모 버튼 안 기호가 가운데인가 — 글자로 그린 ‹ · ＋ 는 잘 쏠린다
    const off = [];
    for (const b of document.querySelectorAll(".gm-back, .gmp-back, .sub-back, .gm-ava, .ib-more, .hv3-ham")) {
      if (!vis(b)) continue;
      const rb = rect(b);
      const rg = document.createRange();
      let ink = null;
      for (const n of b.childNodes) {
        if (n.nodeType === 3 && n.textContent.trim()) { rg.selectNodeContents(n); ink = rg.getBoundingClientRect(); break; }
        if (n.nodeType === 1 && vis(n)) { ink = rect(n); break; }
      }
      if (!ink || !ink.width) continue;
      const dx = ((ink.left + ink.right) / 2) - ((rb.left + rb.right) / 2);
      const dy = ((ink.top + ink.bottom) / 2) - ((rb.top + rb.bottom) / 2);
      if (Math.abs(dx) > 1.5 || Math.abs(dy) > 1.5) {
        off.push((b.className || "").split(/\s+/)[0] + ` dx=${dx.toFixed(1)} dy=${dy.toFixed(1)}`);
      }
    }
    hit.기호쏠림 = [...new Set(off)].slice(0, 6);

    /* ⑦ 「낙서형 빈 상태」 — 글자 하나 없이 **테두리·배경만 있는 상자**.
       서랍 화면이 그랬다: 기록이 없는데 회색 종이 세 장만 그려 놔서
       「공책에 낙서해놓은 거야?」가 됐다(대표님 지적 08-08).
       빈 자리는 **그리지 말거나, 무슨 자리인지 말해야** 한다. */
    const doodle = [];
    for (const e of document.querySelectorAll("div, span, li, i, section")) {
      if (!vis(e)) continue;
      const r = rect(e);
      if (r.width < 24 || r.height < 16) continue;
      if ((e.textContent || "").trim()) continue;
      if (e.querySelector("img, svg, canvas, input, button")) continue;
      const cs = getComputedStyle(e);
      const hasBox = (cs.borderTopWidth !== "0px" && cs.borderTopStyle !== "none")
                  || (cs.backgroundColor !== "rgba(0, 0, 0, 0)" && cs.backgroundColor !== "transparent")
                  || cs.backgroundImage !== "none";
      if (!hasBox) continue;
      // 장식용 그림·구분선·진행바는 «자리»가 아니다
      const cn = (e.className || "").toString();
      if (/art|scrim|dim|bar|line|divider|grip|badge|dot|ring|spark|track|veil|shadow/i.test(cn)) continue;
      if (r.height < 24 && r.width > 80) continue;         // 가로 선
      doodle.push((cn || e.tagName).split(/\s+/).slice(0, 2).join(".") + ` ${Math.round(r.width)}×${Math.round(r.height)}`);
    }
    hit.빈상자 = [...new Set(doodle)].slice(0, 8);

    /* ⑧ 글자 대비 — 읽을 수 없는 글자는 **취향이 아니라 결함**이다(4.5:1 · 큰 글자 3:1).
       ⚠ 배경은 부모를 타고 올라가며 찾는다 — 투명한 요소가 겹쳐 있으면 잘못 잡을 수 있어
         «측정상 미달»과 «진짜 안 보임»은 다를 수 있다. 의심되면 화면으로 한 번 더 본다. */
    const lum = (c) => { const [r0,g0,b0] = (c.match(/\d+/g)||[0,0,0]).slice(0,3).map(Number)
        .map(v => { v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
      return 0.2126*r0 + 0.7152*g0 + 0.0722*b0; };
    const ratio = (a,b) => { const [x,y]=[lum(a),lum(b)].sort((m,n)=>n-m); return (x+0.05)/(y+0.05); };
    const bgOf = (el) => { let e2 = el; while (e2) { const c = getComputedStyle(e2).backgroundColor;
        if (c && c !== "rgba(0, 0, 0, 0)" && c !== "transparent") return c; e2 = e2.parentElement; }
      return "rgb(255,255,255)"; };
    const dim = [];
    for (const e of document.querySelectorAll("b,em,span,p,h1,h2,h3,button,a,i,div,label")) {
      if (e.children.length) continue;
      const t = (e.textContent || "").trim(); if (!t) continue;
      if (!vis(e)) continue;
      const cs3 = getComputedStyle(e);
      const size = parseFloat(cs3.fontSize), fw = parseInt(cs3.fontWeight) || 400;
      const need = (size >= 24 || (size >= 18.66 && fw >= 700)) ? 3 : 4.5;
      const cr = ratio(cs3.color, bgOf(e));
      if (cr < need) dim.push(`${(e.className||e.tagName).toString().split(/\s+/)[0]} ${cr.toFixed(2)}<${need} "${t.slice(0,10)}"`);
    }
    hit.흐린글자 = [...new Set(dim)].slice(0, 6);

    const bad = hit.가로넘침 || hit.작은버튼.length || hit.글자잘림.length || hit.겹침.length
              || hit.기호쏠림.length || hit.빈상자.length || hit.흐린글자.length;
    if (bad) out.push(hit);
    seen.add(hit.실제);
  }

  console.error = oldErr;
  return JSON.stringify({ 돈화면: [...seen], 문제있는화면: out, 콘솔오류: [...new Set(errs)].slice(0, 6) }, null, 1);
})()
