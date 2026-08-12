/* A모듈 버튼·링크 실동작 검사 (2026-08-11 대표님 «카드 버튼 안 눌리는 것도 있는데»)
   window.__mode = "hit" | "act"
   - hit: 누르는 것마다 한가운데를 히트테스트 — **다른 요소에 가려서** 못 눌리는 걸 찾는다
   - act: 실제로 click() 을 쏘고 «무슨 일이 일어났는지» 본다(주소·시트·화면 내용).
          아무 일도 없으면 무반응으로 기록한다.
   ⚠ 되돌리기 어려운 것(탈퇴·삭제·결제·전송·로그아웃…)은 act 에서 안 누른다 — 이름으로 거른다. */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const MODE = window.__mode || "hit";
  const SCREENS = (window.__sweepList || "home,school,timetable,community,docs,notify,help,mypage,calendar,game,supplies,afterschool,timeline,theme,report,pay,tickets,store,childmode,backup,asks,switch").split(",");
  const DANGER = /탈퇴|withdraw|logout|logOut|quit|delete|Del\(|remove|reset|pay|Pay|purchase|buy|mock|billing|refund|export|backup|send|Send|submit|shoot|camera|upload|kakao|google|naver|childAdd|claim|verify|approve|reject|docSave|supplyDel|window\.open|openExt|open\(|sister|http|링크|바깥|외부|scan|Scan|촬영|찍|사진|picker|Picker|file|File/;

  const label = (e) => (e.getAttribute("aria-label") || e.textContent || e.className || e.tagName)
    .toString().replace(/\s+/g, " ").trim().slice(0, 16);
  const clickables = (scr) => [...scr.querySelectorAll("button,[onclick],a[href]")].filter((e) => {
    if (e.disabled) return false;
    const r = e.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) return false;
    const cs = getComputedStyle(e);
    if (cs.visibility === "hidden" || cs.display === "none" || +cs.opacity < .2) return false;
    return true;
  });
  const modalsOpen = () => document.querySelectorAll(
    ".modal,.overlay,.cm-dim,.chatdim,.ns-dim,.dim,.killwrap,[class*='sheet']:not([class*='hidden'])").length;
  const closeAll = async () => {
    for (const f of ["sheetClose", "editClose", "modalClose", "drawerClose", "dayClose", "planClose",
      "stickerClose", "reactClose", "pinClose", "viewerClose", "chatClose", "holdClose", "askClose"]) {
      try { if (typeof App[f] === "function") App[f](); } catch (_) {}
    }
    for (const d of document.querySelectorAll(".cm-dim,.chatdim,.ns-dim,.dim,.overlay")) { try { d.click(); } catch (_) {} }
    await w(120);
  };
  const go = async (sc) => { await closeAll(); location.hash = "#" + sc; try { App.render(); } catch (_) {} await w(900); };

  const out = [];
  for (const sc of SCREENS) {
    await go(sc);
    const scr = document.getElementById("screen");
    const list0 = clickables(scr);
    const n = list0.length;
    const rows = [];

    if (MODE === "hit") {
      for (const e of clickables(scr)) {
        /* ⚠ 50ms 는 짧다 — 스크롤이 안 끝난 채로 재서 «가려짐(MAIN)» 헛것이 무더기로 나왔다
           (2026-08-12: 손으로 확인하니 전부 정상이었다). 자리를 잡을 때까지 기다린다. */
        e.scrollIntoView({ block: "center" }); await w(180);
        const r = e.getBoundingClientRect();
        const cx = Math.min(Math.max(r.left + r.width / 2, 1), innerWidth - 1);
        const cy = Math.min(Math.max(r.top + r.height / 2, 1), innerHeight - 1);
        const t = document.elementFromPoint(cx, cy);
        const ok = t && (e === t || e.contains(t) || t.contains(e));
        if (!ok) rows.push({ 뭐: label(e), 가림: t ? (t.className || t.tagName).toString().slice(0, 18) : "?" });
      }
      window.scrollTo(0, 0);
      out.push({ sc, 누르는것: n, 가려짐: rows.slice(0, 6) });
      continue;
    }

    /* act — 하나 누를 때마다 화면을 새로 그려서 서로 안 섞이게 한다 */
    const CAP = 28;
    for (let i = 0; i < Math.min(n, CAP); i++) {
      await go(sc);
      const list = clickables(document.getElementById("screen"));
      const e = list[i]; if (!e) break;
      const code = (e.getAttribute("onclick") || "") + (e.getAttribute("onpointerdown") || "") + (e.getAttribute("href") || "");
      if (DANGER.test(code) || DANGER.test(e.textContent || "")) continue;
      if (/^(mailto:|tel:|https?:)/.test(e.getAttribute("href") || "")) continue;   // 앱 밖으로 나간다
      const before = { hash: location.hash, modal: modalsOpen(),
        len: document.getElementById("screen").innerHTML.length,
        txt: (document.body.textContent || "").length };
      e.scrollIntoView({ block: "center" }); await w(40);
      try { e.click(); } catch (err) { rows.push({ 뭐: label(e), 문제: "예외:" + String(err).slice(0, 30) }); continue; }
      await w(420);
      const scr2 = document.getElementById("screen");
      const after = { hash: location.hash, modal: modalsOpen(),
        len: scr2 ? scr2.innerHTML.length : 0,
        txt: (document.body.textContent || "").length };
      /* 🔴 주소가 바뀐 것만으로는 성공이 아니다 — «#school/meal» 사고에서 주소는 바뀌고
         화면은 홈에 머물렀다(대표님이 손으로 발견). **내용이 바뀌어야** 눌린 것이다. */
      const changed = after.modal !== before.modal
        || Math.abs(after.len - before.len) > 8 || Math.abs(after.txt - before.txt) > 4
        || !!document.querySelector(".toast");
      if (!changed) rows.push({ 뭐: label(e), 문제: "무반응", 코드: code.replace(/\s+/g, " ").slice(0, 40) });
    }
    out.push({ sc, 누르는것: n, 눌러봄: Math.min(n, CAP), 이상: rows.slice(0, 6) });
  }
  await closeAll(); location.hash = "#home"; try { App.render(); } catch (_) {}
  return JSON.stringify(out);
})();
