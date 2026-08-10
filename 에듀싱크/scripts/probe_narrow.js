// 좁은 화면(폴드 커버 368px)에서 «눌려서 못 읽는 것»만 찾는다 (2026-08-10)
//   CDP_PORT=9444 node scripts/emul_eval.mjs --file scripts/probe_narrow.js
// ⚠ 스샷으로는 못 잡는다 — 잘린 글자는 «...» 없이 그냥 사라지거나 두 줄로 접힌다.
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const SC = ["home","mission","missionpick","store","tickets","meal","timetable","calendar","timeline",
              "afterschool","supplies","mypage","pay","notify","docs","doc-form","report","theme","day",
              "community","schoolinfo","help","homeedit","child-add","switch","backup","game"];
  const out = [];
  for (const s of SC) {
    location.hash = "#" + s; App.render(); await w(1700);
    const bad = [];
    const seen = new Set();
    for (const e of document.querySelectorAll("#screen *")) {
      const cs = getComputedStyle(e);
      if (cs.display === "none" || !e.offsetHeight) continue;
      const txt = (e.textContent || "").trim();
      // ① 가로로 잘린 글자 — 넘치는데 숨김이면 못 읽는다
      const clipped = e.scrollWidth > e.clientWidth + 2 && /hidden|clip/.test(cs.overflowX) &&
        !e.querySelector("*") && txt.length > 1 && cs.textOverflow !== "ellipsis" &&
        !/bd-mq|marquee/.test(e.className || "");
      // ② 부모 밖으로 새는 것
      const r = e.getBoundingClientRect();
      const over = r.right > innerWidth + 1 || r.left < -1;
      if ((clipped || over) && !seen.has(txt.slice(0, 20))) {
        seen.add(txt.slice(0, 20));
        bad.push((clipped ? "잘림" : "넘침") + " " + (e.className || e.tagName).toString().slice(0, 18) + " 「" + txt.slice(0, 22) + "」");
      }
      if (bad.length > 3) break;
    }
    // ③ 가로 스크롤
    const sc = document.scrollingElement || document.documentElement;
    const hs = sc.scrollWidth > innerWidth + 1;
    if (bad.length || hs) out.push(s + (hs ? " 가로스크롤🔴" : "") + (bad.length ? " | " + bad.join(" / ") : ""));
  }
  return out.length ? out.join(String.fromCharCode(10)) : "✅ 좁은 화면에서 눌린 곳 없음 (" + innerWidth + "px)";
})();
