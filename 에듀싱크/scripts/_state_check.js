/* ══════════════════════════════════════════════════════════════════
   상태별 전 화면 검사 (2026-08-13 — 대표님 「시간표 undefined」 이후)

   왜 만들었나
     _doc_check.js 는 사용법 문서의 20 항목 중 16 개만 봤고 **시간표·준비물·서류·
     대화알림·고객센터·내정보는 아예 안 열었다.** 그 사각지대에서
     「undefined학년 undefined반 · undefined학기」가 실사용자(대표님) 눈에 먼저 띄었다.
     → 이 검사기는 **모든 화면을 열어 보고** 아래 5가지를 기계적으로 잰다.

   무엇을 잡나
     ① undefined / NaN / null / [object Object] 가 화면 글자에 새는 것   ← 시간표 사고
     ② 가로 넘침 (화면 밖으로 나간 요소)
     ③ 상태바·내비바 침범 (위 24px 아래 0px 규칙)
     ④ 빈 화면 (글자 10자 미만 = 렌더 실패)
     ⑤ 콘솔 오류

   쓰는 법   window.__stateRole = "parent" | "child" | "logout"
   ⛔ 로그아웃 검사는 **웹(/app)에서** 한다. 에뮬에서 로그아웃시키면 대표님 로그인이 날아간다.
   ══════════════════════════════════════════════════════════════════ */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const ROLE = window.__stateRole || "parent";
  const R = [];

  /* 콘솔 오류 수집 — 한 번만 건다 */
  if (!window.__errBag) {
    window.__errBag = [];
    const oe = console.error;
    console.error = function (...a) { window.__errBag.push(String(a[0]).slice(0, 120)); oe.apply(console, a); };
    window.addEventListener("error", (e) => window.__errBag.push("throw " + String(e.message).slice(0, 120)));
  }

  const PARENT = ["home", "calendar", "day", "meal", "timetable", "afterschool", "supplies",
    "schoolinfo", "community", "mission", "missiontoday", "missionbonus", "store", "tickets",
    "docs", "notify", "mypage", "report", "theme", "help", "asks", "backup", "homeedit", "switch"];
  const CHILD = ["game", "mission", "store", "tickets", "childtt", "childmealrate",
    "childsubject", "childfriend", "childtheme"];
  const LOGOUT = ["login", "register", "findpw", "terms", "policy", "childlink", "intro"];
  const LIST = ROLE === "child" ? CHILD : ROLE === "logout" ? LOGOUT : PARENT;

  /* ⚠ 앞 화면이 열어 둔 폼·메뉴가 다음 화면 판정을 통째로 망친다(_doc_check 에서 겪음) */
  const reset = () => {
    try {
      S.planDraft = null; S.planMove = null; S.holdMenu = null; S.edit = null; S.msDetail = null;
      S.childSwitch = false; S.drawer = false; S.ttEdit = null; S.docDraft = S.docDraft || null;
      S.allergenOpen = false; S.mealSearchOpen = false; S.mealQuery = "";
    } catch (_) {}
  };

  /* 새는 값 — 눈에 보이는 «글자»에서만 찾는다. 클래스 이름 따위는 보지 않는다. */
  const LEAK = /undefined|NaN|\[object Object\]|\bnull\b/;

  for (const name of LIST) {
    reset();
    location.hash = "#" + name;
    App.render();
    await w(1300);
    const sc = document.getElementById("screen");
    const de = document.documentElement;
    const t = (sc?.textContent || "").replace(/\s+/g, " ").trim();

    const leak = t.match(LEAK);
    const leakCtx = leak ? t.slice(Math.max(0, leak.index - 22), leak.index + 26) : "";

    /* 가로 넘침 = **페이지가 실제로 옆으로 밀리는 것**만 센다.
       요소 하나하나를 재면 전광판(.ns-mq)처럼 «일부러 넘겨 놓고 잘라 보여주는» 것이
       전부 걸려서 진짜 사고가 묻힌다(2026-08-13). */
    const over = de.scrollWidth > de.clientWidth + 1
      ? [{ className: `페이지 ${de.scrollWidth}px > ${de.clientWidth}px` }] : [];

    /* 말없이 잘린 글자 — nowrap 인데 칸보다 길고 «…»도 안 붙는 것.
       홈편집 부제가 「…각자의 화면에 그」에서 뚝 끊겨 있었다. */
    const cut = [...(sc?.querySelectorAll("*") || [])].filter((e) => {
      if (e.children.length) return false;                       // 글자를 직접 든 칸만
      const cs = getComputedStyle(e);
      if (cs.whiteSpace !== "nowrap" || cs.textOverflow === "ellipsis") return false;
      if (e.closest(".ns-mq")) return false;                     // 전광판은 흐르는 게 정상
      return e.scrollWidth > e.clientWidth + 1 && (e.textContent || "").trim().length > 6;
    });

    /* 상태바(위)·내비바(아래) — 실기 값은 --sa-t/--sa-b 가 안다 */
    const saT = parseFloat(getComputedStyle(de).getPropertyValue("--sa-t")) || 0;
    const top = [...(document.querySelectorAll("header, .nav, #screen > *") || [])]
      .filter((e) => { const r = e.getBoundingClientRect(); return r.height > 0 && r.top < saT - 0.5; });

    const bad = [];
    if (leak) bad.push("샘:" + leakCtx);
    if (over.length) bad.push("가로넘침 " + over[0].className);
    if (cut.length) bad.push("글자잘림 «" + (cut[0].textContent || "").trim().slice(0, 30) + "»");
    if (top.length) bad.push("상태바침범 " + (top[0].className || top[0].tagName));
    if (t.length < 10) bad.push("빈 화면");

    R.push({ 화면: name, v: bad.length ? "FAIL" : "OK", d: bad.join(" / ") || t.slice(0, 40) });
  }

  reset();
  location.hash = ROLE === "child" ? "#game" : ROLE === "logout" ? "#login" : "#home";
  App.render(); await w(400);

  const errs = (window.__errBag || []).slice(-6);
  const f = R.filter((x) => x.v === "FAIL");
  return JSON.stringify({
    역할: ROLE, 통과: R.length - f.length, 전체: R.length,
    실패: f, 콘솔오류: errs,
    로그인유지: ROLE === "logout" ? "해당없음" : !!TOKENS.access,
  }, null, 1);
})();
