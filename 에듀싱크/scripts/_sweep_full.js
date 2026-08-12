/* A모듈(부모앱) 전수검사 (2026-08-11 대표님 지시)
   화면마다 «값으로» 잰다 — ①상단·하단 침범 ②넘침·화면밖 ③글자 대비
   ④JS 오류 ⑤글자 크기 이상 ⑥깨진 손잡이(onclick이 없는 함수를 부름)
   ⑦없는 화면으로 가는 링크 ⑧너무 작은 터치 목표 ⑨깨진 이미지·아이콘 폰트 ⑩칩 32 고정
   ⚠ 에뮬은 내비바가 없어 하단 검사가 헛통과한다 — window.__navTest=48 로 한 번 더. */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const SCREENS = (window.__sweepList || "home,school,timetable,community,docs,notify,help,mypage,calendar,game,supplies,afterschool,timeline,theme,report,pay,tickets,store,childmode,backup,asks,switch").split(",");
  /* 자녀앱(B모듈)은 홈 안에서 탭으로 갈린다 — 주소가 하나라 S.gameTab 을 돌려 가며 잰다.
     window.__kidTabs=1 이면 game 화면을 탭별로 펼쳐서 검사한다(2026-08-12). */
  const KID_TABS = window.__kidTabs ? [null, "morning", "school", "after", "shop", "profile"] : null;

  /* JS 오류 그물 — 한 번만 건다 */
  if (!window.__errHooked) {
    window.__errHooked = 1; window.__errs = [];
    addEventListener("error", (e) => window.__errs.push(String(e.message || e).slice(0, 80)));
    addEventListener("unhandledrejection", (e) => window.__errs.push("P:" + String(e.reason).slice(0, 70)));
  }

  if (window.__navTest) {
    document.documentElement.style.setProperty("--sa-bottom", window.__navTest + "px");
    await w(200);
  }

  /* 대비 — 반투명은 합성, 그라디언트 면은 건너뜀 (기존 스윕과 같은 식) */
  const parse = (s) => {
    const m = s.match(/color\(srgb ([\d.]+) ([\d.]+) ([\d.]+)(?:\s*\/\s*([\d.]+))?\)/);
    if (m) return [ +m[1] * 255, +m[2] * 255, +m[3] * 255, m[4] === undefined ? 1 : +m[4] ];
    const n = (s.match(/[\d.]+/g) || [0, 0, 0]).map(Number);
    return [ n[0] || 0, n[1] || 0, n[2] || 0, n[3] === undefined ? 1 : n[3] ];
  };
  const over = (fg, bg) => fg.slice(0, 3).map((v, i) => v * fg[3] + bg[i] * (1 - fg[3]));
  const lumOf = (c) => { const [r, g, b] = c.slice(0, 3).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const bgOf = (el) => {
    const stack = []; let e = el;
    while (e && e !== document.documentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] > 0) stack.push(c); e = e.parentElement; }
    let base = [255, 255, 255];
    for (let i = stack.length - 1; i >= 0; i--) base = over(stack[i], base);
    return base;
  };
  const ratio = (colStr, bgArr) => { const fg = over(parse(colStr), bgArr); const [l1, l2] = [lumOf(fg), lumOf(bgArr)].sort((x, y) => y - x); return (l1 + 0.05) / (l2 + 0.05); };

  const iconFontOK = document.fonts ? document.fonts.check("16px 'tabler-icons'") : true;
  /* 검사 목록을 펼친다 — game 은 탭 수만큼 늘어난다 */
  const JOBS = [];
  for (const sc of SCREENS) {
    if (sc === "game" && KID_TABS) KID_TABS.forEach((t) => JOBS.push({ sc, tab: t }));
    else JOBS.push({ sc, tab: undefined });
  }
  const out = [];
  for (const job of JOBS) {
    const sc = job.tab === undefined ? job.sc : `${job.sc}:${job.tab || "home"}`;
    const errsBefore = window.__errs.length;
    location.hash = "#" + job.sc;
    if (job.tab !== undefined) S.gameTab = job.tab;
    try { App.render(); } catch (e) { window.__errs.push("render:" + String(e).slice(0, 60)); }
    await w(1400);
    const scr = document.getElementById("screen");
    const px = (v) => parseFloat(v) || 0;
    const saT = px(getComputedStyle(scr).paddingTop);
    const saB = px(getComputedStyle(document.documentElement).getPropertyValue("--sa-b"));

    const clipped = (e) => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const o = getComputedStyle(p); if (o.overflowX === "hidden" || o.overflow === "hidden" || o.overflowX === "auto") return true; } return false; };
    const overX = scr.scrollWidth - scr.clientWidth;
    let outer = 0;
    for (const e of scr.querySelectorAll("*")) {
      const r = e.getBoundingClientRect();
      if (r.width > 0 && (r.left < -1 || r.right > innerWidth + 1) && !clipped(e)) outer++;
    }

    /* 글자 — 대비 + 크기 이상(11px 미만은 못 읽고, 76px 초과는 시계(74)보다 크니 이상) */
    let lowC = 0, worstT = "", small = 0, smallT = "", big = 0;
    const seen = new Set();
    for (const e of scr.querySelectorAll("span,b,em,p,h1,h2,h3,div,button,a,label,i,input")) {
      const own = e.firstChild && e.firstChild.nodeType === 3 && e.firstChild.nodeValue.trim();
      if (!own) continue;
      const t = e.textContent.trim(); if (!t || seen.has(t)) continue;
      const r = e.getBoundingClientRect(); if (r.width < 4 || r.height < 4) continue;
      const cs = getComputedStyle(e);
      if (cs.visibility === "hidden" || +cs.opacity < .3) continue;
      seen.add(t);
      const fs = parseFloat(cs.fontSize);
      if (fs < 11) { small++; if (!smallT) smallT = t.slice(0, 12) + "@" + fs.toFixed(1); }
      if (fs > 76) big++;
      let grad = false;
      for (let p = e; p && p !== document.documentElement; p = p.parentElement) { if (getComputedStyle(p).backgroundImage !== "none") { grad = true; break; } }
      if (grad) continue;
      const bold = +cs.fontWeight >= 700;
      const need = (fs >= 24 || (fs >= 18.66 && bold)) ? 3 : 4.5;
      const cr = ratio(cs.color, bgOf(e));
      if (cr < need) { lowC++; if (!worstT) worstT = t.slice(0, 12) + "@" + cr.toFixed(2); }
    }

    /* 상·하단 침범 — «읽는 것»만 */
    const meat = [...scr.querySelectorAll("*")].filter((e) => {
      const r = e.getBoundingClientRect();
      if (r.width < 8 || r.height < 6) return false;
      const own = e.firstChild && e.firstChild.nodeType === 3 && e.firstChild.nodeValue.trim();
      return !!own || /^(BUTTON|INPUT|TEXTAREA|SELECT|IMG)$/.test(e.tagName);
    });
    let hitTop = 0, hitBot = 0, botWho = "";
    for (const e of meat) {
      const r = e.getBoundingClientRect();
      if (r.top < saT - 0.5 && r.bottom > 0) hitTop++;
      const cs2 = getComputedStyle(e);
      const stuck = cs2.position === "fixed" || cs2.position === "sticky"
        || (e.closest && !!e.closest(".ns-bar,.ns-actbar,.stickybar,.inputbar,.ib,.pvfoot,#tabbar,.dw-fab,.chatbar"));
      if (stuck && r.bottom > innerHeight - saB + 0.5) { hitBot++; if (!botWho) botWho = (e.className || e.tagName).toString().slice(0, 16); }
    }
    window.scrollTo(0, document.body.scrollHeight); await w(200);
    if (document.body.scrollHeight > innerHeight + 4) {
      let low = -1e9, who = "";
      for (const e of meat) {
        const cs2 = getComputedStyle(e);
        if (cs2.position === "fixed" || cs2.position === "sticky") continue;
        const r = e.getBoundingClientRect();
        if (r.bottom > low) { low = r.bottom; who = (e.className || e.tagName).toString().slice(0, 16); }
      }
      if (Math.round(innerHeight - saB - low) < 0) { hitBot++; if (!botWho) botWho = "끝:" + who; }
    }
    window.scrollTo(0, 0);

    /* 동작 — onclick 이 부르는 App.* 가 실제로 있나 · 가는 화면이 실제로 있나 */
    const badFn = new Set(), badGo = new Set();
    for (const e of scr.querySelectorAll("[onclick],[onpointerdown],[oninput],[onchange]")) {
      const code = (e.getAttribute("onclick") || "") + ";" + (e.getAttribute("onpointerdown") || "")
        + ";" + (e.getAttribute("oninput") || "") + ";" + (e.getAttribute("onchange") || "");
      for (const m of code.matchAll(/App\.(\w+)\s*\(/g)) if (typeof App[m[1]] !== "function") badFn.add(m[1]);
      for (const m of code.matchAll(/hash\s*=\s*['"]#([\w-]+)/g)) {
        const name = m[1];
        if (typeof Screens === "object" && !(name in Screens)) badGo.add(name);
      }
    }
    /* 터치 목표 — 누르는 것이 24px 미만이면 손가락이 못 잡는다 */
    let tinyTap = 0, tinyWho = "";
    for (const e of scr.querySelectorAll("button,[onclick],a[href]")) {
      const r = e.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (getComputedStyle(e).visibility === "hidden") continue;
      if ((r.width < 24 || r.height < 24) && e.textContent.trim().length > 0) {
        tinyTap++; if (!tinyWho) tinyWho = (e.className || e.tagName).toString().slice(0, 14) + `(${Math.round(r.width)}x${Math.round(r.height)})`;
      }
    }
    /* 깨진 이미지 · 32px 칩 어긋남 */
    let imgBad = 0;
    for (const im of scr.querySelectorAll("img")) if (im.complete && im.naturalWidth === 0) imgBad++;
    let chipBad = 0;
    for (const c of scr.querySelectorAll(".ns-c")) {
      const r = c.getBoundingClientRect();
      if (Math.abs(r.width - 32) > 1 || Math.abs(r.height - 32) > 1) chipBad++;
    }

    out.push({ sc, errs: window.__errs.slice(errsBefore).slice(0, 3),
      overX, outer, lowC, worstT, small, smallT, big,
      hitTop, hitBot, botWho,
      badFn: [...badFn].slice(0, 4), badGo: [...badGo].slice(0, 4),
      tinyTap, tinyWho, imgBad, chipBad });
  }
  return JSON.stringify({ iconFontOK, screens: out });
})();
