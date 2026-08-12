/* kd(듀오링고) 화면 전수검사 (2026-08-12 대표님 「3가지 사이즈로 다 맞춰서」)
   _mission_fixture 와 같은 주입 위에서 **A모듈 스윕과 같은 항목**을 잰다:
   ①가로넘침 ②상단침범(--sa-t) ③하단꼬리(끝까지 내려도 마지막 내용이 화면 안)
   ④버튼 가려짐(한가운데 히트테스트) ⑤24px 미만 터치 목표 ⑥글자 크기 이상(<11px·>76px)
   window.__mshot = parent|kid|one|onewait|pick|store|tickets|quiz|quizplay */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const MODE = window.__mshot || "parent";

  /* 네트워크 차단 — 실서버 실패 응답이 주입 상태를 지운다(_mission_fixture 와 같은 이유) */
  if (!window.__fetchCut) { window.__fetchCut = 1; window.fetch = () => new Promise(() => {}); }
  await w(150);

  TOKENS.access = "fixture"; S.loggedIn = true;
  if (!cur()) {
    STUB.children.push({ id: 991, server_id: 1, nickname: "민서", grade: "3",
      school: { name: "검수초", kind: "초등학교" },
      pass: { active: true, expires_at: new Date(Date.now() + 7 * 86400000).toISOString() } });
    S.currentChildId = 991;
  }
  localStorage.setItem(MS_COACH_KEY, "1"); S.msCoach = null; S._msCoachQueued = true;

  S.econ = { star_line: 25, line_min: 10, line_max: 35, line_step: 5, line_default: 25,
    limit: 25, mission_budget: 10, hidden_limit: 5, max_per_day: 8, min_per_day: 2, auto_pass_instant: true };
  S.coin = { stars: 12, earned_today: 12, star_line: 25, limit: 25, room: 13, level: 2, streak: 3 };
  S.missionStars = 12;
  S.missions = [
    { id: 1, code: "M-A1", title: "일어나서 물 한 컵 마시기", area: "body", minutes: 1, verify: "instant", slot: "morning", stars: 1, status: "done", got: 1 },
    { id: 2, code: "M-A2", title: "책 십오 분 자리 지키기", area: "read", minutes: 15, verify: "instant", slot: "after", stars: 3, status: "done", got: 3 },
    { id: 3, code: "M-A3", title: "숙제 오 분 시작하기", area: "study", minutes: 5, verify: "instant", slot: "after", stars: 2, status: "open" },
    { id: 4, code: "M-A4", title: "내일 배울 곳 훑어보기", area: "study", minutes: 5, verify: "instant", slot: "after", stars: 2, status: "open",
      why: "내일 뭘 배우는지 한 번 보면 수업이 «아는 이야기»로 시작해요." },
    { id: 5, code: "M-A5", title: "알림장 보고 준비물 챙기기", area: "prep", minutes: 3, verify: "review", verify_hint: "챙긴 가방 속", slot: "after", stars: 2, status: "waiting" },
  ];
  S.verifyPending = [{ verify_id: "v1", mission_code: "M-S01", step1_data: "급식 다 먹었어요", created_at: "2026-08-12" }];
  S.msWeek = { code: "M-A4", days: [
    { ymd: "0806", wd: "수", st: "done" }, { ymd: "0807", wd: "목", st: "miss" }, { ymd: "0808", wd: "금", st: "miss" },
    { ymd: "0809", wd: "토", st: "none" }, { ymd: "0810", wd: "일", st: "none" }, { ymd: "0811", wd: "월", st: "done" },
    { ymd: "0812", wd: "오늘", st: "none", today: true }] };
  S.missionCatalog = { mid: [
    { code: "C-1", title: "책 십오 분 자리 지키기", area: "read", stars: 3, minutes: 15, verify: "instant" },
    { code: "C-2", title: "숙제 오 분 시작하기", area: "study", stars: 2, minutes: 5, verify: "instant" },
    { code: "C-3", title: "가방 속 쓰레기 비우기", area: "things", stars: 1, minutes: 2, verify: "instant" },
    { code: "C-4", title: "알림장 보고 준비물 챙기기", area: "prep", stars: 2, minutes: 3, verify: "review" },
    { code: "C-5", title: "우리 집 미션 — 윙크 20분", area: "study", stars: 2, minutes: 20, verify: "instant", mine: true }] };
  S.missionPick = ["C-1", "C-2"]; S.pickBand = "mid";
  S.store = [
    { item_id: "a", title: "늦게 자기 30분", stars_required: 20, can_buy: true },
    { item_id: "b", title: "게임 30분", stars_required: 15, limit_type: "weekly", limit_count: 2, used: 2, can_buy: false, reason: "limit" }];
  S.rewards = [
    { reward_order_id: "r1", item_title: "게임 30분", stars_spent: 15, status: "requested", created_at: "2026-08-11" },
    { reward_order_id: "r2", item_title: "늦게 자기", stars_spent: 20, status: "fulfilled", created_at: "2026-08-09" }];

  S.kidMode = ["kid", "quiz", "quizplay"].includes(MODE);
  S.quizResult = null; S.quizFeed = null; clearInterval(QUIZ_TIMER);
  if (MODE === "one") { S.msDetail = 4; location.hash = "#missionone"; }
  else if (MODE === "onewait") { S.msDetail = 5; location.hash = "#missionone"; }
  else if (MODE === "pick") { S._pickSelfLoad = true; location.hash = "#missionpick"; }
  else if (MODE === "store") { location.hash = "#store"; }
  else if (MODE === "tickets") { location.hash = "#tickets"; }
  else if (MODE === "quiz" || MODE === "quizplay") {
    S.gmTheme = "sky";
    S.quiz = { total: 10, answered: 2, sec_per_q: 7, perfect_bonus: 5, items: [
      { code: "q1", field: "ko", kind: "mc", q: "«사과»를 영어로 하면?", options: ["apple", "banana", "grape", "melon"], sec: 7 }] };
    S.quizIdx = -1; S.gameTab = "today"; location.hash = "#game";
  }
  else location.hash = "#mission";
  App.render(); await w(600);
  if (MODE === "quizplay") { S.quizIdx = 0; App.render(); await w(400); clearInterval(QUIZ_TIMER); }

  /* ── 재기 ─────────────────────────────────────────────── */
  const scr = document.getElementById("screen");
  const saT = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--sa-t")) || 0;
  /* ⚠ 하단 바닥은 innerHeight 다 — 내비바는 이제 **네이티브가 웹뷰를 잘라서** 막는다(STATUS ③,
     MainActivity bottomMargin). 옛 CSS-여백 시절처럼 navTest 를 빼면 **이중 차감**이라
     9판 전부 «하단 31» 헛것이 떴다(2026-08-12 실측). navTest 는 기록용으로만 남긴다. */
  const NAV = window.__navTest || 0;
  const floorY = innerHeight;
  const label = (e) => (e.getAttribute("aria-label") || e.textContent || e.tagName).replace(/\s+/g, " ").trim().slice(0, 14);

  // ① 가로넘침
  const overX = Math.max(0, document.documentElement.scrollWidth - innerWidth);

  // ② 상단침범 — 맨 위로 올려놓고 잰다
  scr.scrollTop = 0; window.scrollTo(0, 0); await w(120);
  let topHit = [];
  for (const e of scr.querySelectorAll("button,b,span,h2,p,em,i")) {
    const r = e.getBoundingClientRect();
    if (r.height && r.top < saT - 1 && getComputedStyle(e).position !== "fixed"
        && getComputedStyle(e).visibility !== "hidden") topHit.push(label(e));
  }

  // ③ 하단꼬리 — 끝까지 내리고, 눈에 보이는 마지막 요소의 바닥이 화면 안인가
  const scroller = document.scrollingElement;
  scroller.scrollTop = scroller.scrollHeight; scr.scrollTop = scr.scrollHeight; await w(200);
  /* ⚠ div 를 세면 배경 컨테이너(.gm 등 fixed inset:0)가 잡혀 «화면 끝 = 초과» 헛것이 된다 —
     **잎사귀(내용)만** 잰다: 버튼·글줄·그림. */
  let lastBottom = 0;
  for (const e of scr.querySelectorAll("button,p,li,b,em,span,img,h2")) {
    const r = e.getBoundingClientRect();
    if (r.height >= 8 && r.width >= 8 && r.bottom > lastBottom && r.top < innerHeight) lastBottom = r.bottom;
  }
  const tailOver = Math.max(0, Math.round(lastBottom - floorY));

  // ④⑤ 버튼 — 가려짐 + 터치 목표
  const hidden = [], small = [];
  const btns = [...scr.querySelectorAll("button,[onclick]")].filter((e) => {
    const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    return r.width >= 8 && r.height >= 8 && cs.visibility !== "hidden" && cs.display !== "none" && +cs.opacity >= .2 && !e.disabled;
  });
  for (const e of btns) {
    e.scrollIntoView({ block: "center" }); await w(150);   // ⚠ 50ms 는 헛것을 만든다(A스윕 교훈)
    const r = e.getBoundingClientRect();
    if (r.height < 24) small.push(label(e) + "(" + Math.round(r.height) + ")");
    const cx = Math.min(Math.max(r.left + r.width / 2, 1), innerWidth - 1);
    const cy = Math.min(Math.max(r.top + r.height / 2, 1), innerHeight - 1);
    const t = document.elementFromPoint(cx, cy);
    const ok = t && (e === t || e.contains(t) || t.contains(e));
    if (!ok) hidden.push(label(e) + "←" + (t ? (t.className || t.tagName).toString().slice(0, 12) : "?"));
  }

  // ⑥ 글자 크기 이상
  let badFont = [];
  for (const e of scr.querySelectorAll("*")) {
    if (!e.childNodes.length) continue;
    const hasText = [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!hasText) continue;
    const fs = parseFloat(getComputedStyle(e).fontSize);
    if (fs < 11 || fs > 76) badFont.push(label(e) + "(" + fs + ")");
  }

  scroller.scrollTop = 0;
  return JSON.stringify({ mode: MODE, w: innerWidth, h: innerHeight, nav: NAV,
    가로넘침: overX, 상단침범: topHit.slice(0, 3), 하단초과: tailOver,
    버튼: btns.length, 가려짐: hidden.slice(0, 4), 작은터치: small.slice(0, 4), 글자이상: badFont.slice(0, 3) });
})();
