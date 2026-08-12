/* 미션 화면(듀오링고 이식) 에뮬 검수용 상태 주입 (2026-08-12)
   서버 없이 화면만 실측한다 — 에뮬은 http(로컬 워커)가 클리어텍스트로 막혀 있고,
   기능은 데스크톱 브라우저 + 로컬 워커에서 이미 전수 통과했다.
   여기서 보는 것은 «실기 크기·인셋·메이플체에서 안 깨지나»다.
   window.__mshot = "parent" | "kid" | "one" | "pick" 으로 판을 고른다. */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const MODE = window.__mshot || "parent";

  /* 🔌 네트워크를 끊는다 — 안 끊으면 실서버로 나간 loadChildren/AUTH 가 6초 뒤에 실패로 돌아와
     주입한 아이·토큰을 지우고 «아이 등록» 화면으로 밀어낸다(2026-08-12 실측: 다섯 판 전부 그렇게 찍혔다).
     영원히 안 끝나는 약속으로 바꾸면 걸려 있던 요청도 새 요청도 화면을 못 건드린다. */
  window.fetch = () => new Promise(() => {});
  await w(200);

  // 로그인 없이 화면 게이트만 통과시키는 최소 상태
  // ⚠ cur() 는 S.children 이 아니라 **STUB.children + S.currentChildId** 를 읽는다(1039행) —
  //   S.children 에 넣으면 라우터가 «아이 없음»으로 보고 #child-add 로 민다(2026-08-12 다섯 판 실측)
  TOKENS.access = "fixture";
  S.loggedIn = true;
  if (!cur()) {
    const kid0 = { id: 991, server_id: 1, nickname: "민서", grade: "3",
      school: { name: "검수초", kind: "초등학교" },
      // 이용권 게이트 통과 — 없으면 «체험이 끝났어요» 잠금 화면이 찍힌다(2026-08-12 실측)
      pass: { active: true, expires_at: new Date(Date.now() + 7 * 86400000).toISOString() } };
    STUB.children.push(kid0);
    S.currentChildId = 991;
  }
  localStorage.setItem(MS_COACH_KEY, "1"); S.msCoach = null; S._msCoachQueued = true;

  S.econ = { star_line: 25, line_min: 10, line_max: 35, line_step: 5, line_default: 25,
    limit: 25, mission_budget: 10, hidden_limit: 5, max_per_day: 8, min_per_day: 2,
    auto_pass_instant: true };
  S.coin = { stars: 12, earned_today: 12, star_line: 25, limit: 25, room: 13,
    hidden_today: 0, hidden_limit: 5, level: 2, streak: 3 };
  S.missionStars = 12;
  S.missions = [
    { id: 1, code: "M-A1", title: "일어나서 물 한 컵 마시기", area: "body", minutes: 1,
      verify: "instant", slot: "morning", stars: 1, status: "done", got: 1 },
    { id: 2, code: "M-A2", title: "책 십오 분 자리 지키기", area: "read", minutes: 15,
      verify: "instant", slot: "after", stars: 3, status: "done", got: 3 },
    { id: 3, code: "M-A3", title: "숙제 오 분 시작하기", area: "study", minutes: 5,
      verify: "instant", slot: "after", stars: 2, status: "open" },
    { id: 4, code: "M-A4", title: "내일 배울 곳 훑어보기", area: "study", minutes: 5,
      verify: "instant", slot: "after", stars: 2, status: "open",
      why: "내일 뭘 배우는지 한 번 보면 수업이 «아는 이야기»로 시작해요. 오래 걸리지 않아 매일 할 수 있어요." },
    { id: 5, code: "M-A5", title: "알림장 보고 준비물 챙기기", area: "prep", minutes: 3,
      verify: "review", verify_hint: "챙긴 가방 속", slot: "after", stars: 2, status: "waiting" },
  ];
  S.verifyPending = [];
  S.msWeek = { code: "M-A4", days: [
    { ymd: "0806", wd: "수", st: "done" }, { ymd: "0807", wd: "목", st: "miss" },
    { ymd: "0808", wd: "금", st: "miss" }, { ymd: "0809", wd: "토", st: "none" },
    { ymd: "0810", wd: "일", st: "none" }, { ymd: "0811", wd: "월", st: "done" },
    { ymd: "0812", wd: "오늘", st: "none", today: true },
  ] };
  S.missionCatalog = { mid: [
    { code: "C-1", title: "책 십오 분 자리 지키기", area: "read", stars: 3, minutes: 15, verify: "instant" },
    { code: "C-2", title: "숙제 오 분 시작하기", area: "study", stars: 2, minutes: 5, verify: "instant" },
    { code: "C-3", title: "가방 속 쓰레기 비우기", area: "things", stars: 1, minutes: 2, verify: "instant" },
    { code: "C-4", title: "알림장 보고 준비물 챙기기", area: "prep", stars: 2, minutes: 3, verify: "review", mine: false },
    { code: "C-5", title: "우리 집 미션 — 윙크 20분", area: "study", stars: 2, minutes: 20, verify: "instant", mine: true },
  ] };
  S.missionPick = ["C-1", "C-2"];
  S.pickBand = "mid";

  S.kidMode = MODE === "kid" || MODE.startsWith("quiz");
  if (MODE === "one") { S.msDetail = 4; location.hash = "#missionone"; }
  else if (MODE === "pick") { S._pickSelfLoad = true; location.hash = "#missionpick"; }
  else if (MODE.startsWith("quiz")) {
    /* quiz-sky … quiz-mint — 퀴즈(전투) 화면을 테마별로. B안 바탕 검수용(2026-08-12) */
    S.gmTheme = MODE.split("-")[1] || "sky";
    S.quiz = { total: 10, answered: 2, sec_per_q: 7, perfect_bonus: 5, items: [
      { code: "q1", field: "ko", kind: "mc", q: "«사과»를 영어로 하면?",
        options: ["apple", "banana", "grape", "melon"], sec: 7 }] };
    S.gameTab = "today"; location.hash = "#game";
  }
  else location.hash = "#mission";
  App.render(); await w(700);
  if (MODE.startsWith("quiz")) { S.quizIdx = 0; App.render(); await w(400); }

  // 검수 값 — 상단·하단 침범, 가로 넘침, 리본 높이, 캔디 버튼
  const scr = document.getElementById("screen");
  const saT = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--sa-t")) || 0;
  let topHit = 0;
  for (const e of scr.querySelectorAll("button,b,span,h2,p")) {
    const r = e.getBoundingClientRect();
    if (r.height && r.top < saT - 1 && getComputedStyle(e).position !== "fixed") topHit++;
  }
  const bar = document.querySelector(".kd-path .bar");
  return JSON.stringify({
    mode: MODE, hash: location.hash,
    가로넘침: document.documentElement.scrollWidth - innerWidth,
    상단침범: topHit,
    리본높이: bar ? bar.offsetHeight : null,
    글꼴: getComputedStyle(document.querySelector(".kd-scr") || scr).fontFamily.split(",")[0],
    내용: (scr.textContent || "").replace(/\s+/g, " ").slice(0, 110),
  });
})();
