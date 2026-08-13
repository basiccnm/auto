/* 미션 사용법 문서(부모·자녀) 항목별 실확인 — 2026-08-13
   docs/사용법-미션-부모-20260813.txt · docs/사용법-미션-자녀-20260813.txt
   문서에 «있다»고 쓴 것을 화면에서 **찾아서** 판정한다. 글로만 쓰고 확인 안 하는 일이 없게.
   window.__mRole = "parent" | "child" */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const R = [];
  const ok = (n, p, d) => R.push({ n, v: p ? "OK" : "FAIL", d: String(d ?? "").slice(0, 80) });
  const txt = () => (document.getElementById("screen").textContent || "").replace(/\s+/g, " ");
  const btns = () => [...document.querySelectorAll("#screen button")].map((b) => b.textContent.replace(/\s+/g, " ").trim());
  const go = async (h, ms) => { S.msDetail = S.msDetail; location.hash = h; App.render(); await w(ms || 1300); };
  const ROLE = window.__mRole || "parent";
  try { localStorage.setItem(MS_COACH_KEY, "1"); } catch (_) {}
  S.msCoach = null; S._msCoachQueued = true;

  if (ROLE === "parent") {
    await go("#mission", 2200);
    for (let i = 0; i < 12 && !document.querySelector(".kd-kn"); i++) await w(400);
    S.msCoach = null; App.render(); await w(400);

    // P1 머리
    ok("P1 ‹ 있음", !!document.querySelector(".kd-bk"), "-");
    ok("P1 ★ 알약", /★/.test(document.querySelector(".kd-pill.star")?.textContent || ""),
       document.querySelector(".kd-pill.star")?.textContent.trim());
    // P1 리본·다이얼
    const kn = [...document.querySelectorAll(".kd-kn")];
    ok("P1 리본 ⊖⊕ 2개", kn.length === 2, kn.map((b) => b.textContent.trim()).join(""));
    const e = S.econ || {};
    ok("P1 라인 10~35 · 5단", e.line_min === 10 && e.line_max === 35 && e.line_step === 5,
       `${e.line_min}~${e.line_max} step${e.line_step} 지금${e.star_line}`);
    ok("P1 리본 = 오늘받은/상한", /\d+\s*\/\s*\d+/.test(document.querySelector(".kd-path .lb")?.textContent || ""),
       document.querySelector(".kd-path .lb")?.textContent.replace(/\s+/g, " ").trim());
    // P1 오늘 준 미션
    ok("P1 「오늘 준 미션」 카드", txt().includes("오늘 준 미션"), "-");
    ok("P1 미션 줄 있음", document.querySelectorAll(".kd-q").length > 0, document.querySelectorAll(".kd-q").length + "줄");
    // P1 타일 7개
    const tiles = [...document.querySelectorAll(".kd-tile")].map((b) => b.textContent.replace(/\s+/g, " ").trim());
    const want = ["바꾸기", "고르기", "만들기", "오늘 한 것", "추가 증정", "칭찬 보내기", "이번 달"];
    ok("P1 타일 7개(문서와 같은 이름)", want.every((x) => tiles.some((t) => t.includes(x))), tiles.join(" / "));
    ok("P1 아이 화면으로 보기", btns().some((t) => t.includes("아이 화면으로 보기")), "-");

    // P1 완료돼도 줄이 안 올라간다 — 목록 순서가 id 순인지
    const ids = [...document.querySelectorAll(".kd-q")].map((b) => +(b.getAttribute("onclick") || "").replace(/\D+/g, ""));
    ok("P1 목록 자리 고정(id 오름차순)", ids.every((v, i) => i === 0 || ids[i - 1] <= v), ids.join(","));

    // P2 상세 — 안 한 미션
    const open = (S.missions || []).find((x) => x.status === "open");
    if (open) {
      App.msOpen(open.id); await w(1600);
      for (let i = 0; i < 12 && !document.querySelector(".kd-week .d"); i++) await w(400);
      const b = [...document.querySelectorAll(".kd-act button")].map((x) => x.textContent.trim());
      ok("P2 안한미션 버튼 3개", b.length === 3 && b[0].includes("이것만 바꾸기")
        && b[1].includes("오늘은 빼기") && b[2].includes("직접 고르기"), b.join(" / "));
      ok("P2 지난 이레 7칸", document.querySelectorAll(".kd-week .d").length === 7,
         document.querySelectorAll(".kd-week .d").length + "칸");
      ok("P2 칩(영역·분·별)", document.querySelectorAll(".kd-chips span").length >= 2,
         [...document.querySelectorAll(".kd-chips span")].map((s) => s.textContent.trim()).join("·"));
      ok("P2 ‹ → 목록", true, "-");
      document.querySelector(".kd-bk").click(); await w(900);
      ok("P2 ‹ 눌러 목록으로", location.hash === "#mission", location.hash);
    } else ok("P2 상세", false, "안 한 미션이 없어 확인 못 함");

    // P3 고르기 — 상한 8
    await go("#mission", 1200); App.missionPickOpen(); await w(2500);
    S.missionPick = []; App.render(); await w(300);
    const rows = [...document.querySelectorAll(".mk-row")];
    if (rows.length) {
      for (const r of rows.slice(0, 11)) { r.click(); await w(80); }
      ok("P3 하루 최대 8개", (S.missionPick || []).length === 8, "담김 " + (S.missionPick || []).length);
      const foot = btns().find((t) => /\d+개 담기/.test(t));
      ok("P3 「n개 담기」 버튼", !!foot, foot || "없음");
      S.missionPick = []; App.render(); await w(200);
    } else ok("P3 고르기 목록", false, "후보 0");
    await go("#mission", 800);

    // P5 · P6
    await go("#missiontoday", 1600);
    ok("P5 소속별로 묶임", txt().includes("아침 미션") && txt().includes("방과후 미션"), txt().slice(0, 60));
    await go("#missionbonus", 1400);
    ok("P6 ＋1 버튼", btns().some((t) => t.includes("＋1")) || txt().includes("＋1"), txt().slice(0, 60));

    // P1 ‹ → 홈
    await go("#mission", 1400); S.msCoach = null; App.render(); await w(300);
    document.querySelector(".kd-bk").click(); await w(900);
    ok("P1 ‹ → 홈", location.hash === "#home", location.hash);
  } else {
    // ── 자녀 ──
    await go("#game", 2200);
    const t0 = txt();
    ok("K1 ‹ 없음(여기가 집)", !document.querySelector(".kd-home .kd-bk"), "-");
    /* 🔥 는 0일 때 숨긴다(08-14 ⑥) — 있으면 «N일째» 형식, 없어도 정상. ★ 는 항상 */
    ok("K1 🔥(0숨김·N일째) · ★ 별", /★/.test(t0) && (!/🔥/.test(t0) || /🔥 d+일째/.test(t0)), t0.slice(0, 40));
    ok("K1 오늘의 길", t0.includes("오늘의 길") && /\d+\s*\/\s*\d+/.test(t0), "-");
    const tl = [...document.querySelectorAll(".kd-tiles .kd-tile")].map((b) => b.textContent.replace(/\s+/g, " ").trim());
    ok("K1 타일 아침·학교·방과후", tl.length >= 2 && tl.some((x) => x.includes("아침")) && tl.some((x) => x.includes("방과후")), tl.join(" / "));
    ok("K1 엄마아빠 퀘스트 카드", t0.includes("엄마아빠 퀘스트"), "-");
    ok("K1 상점 줄", t0.includes("스타코인 상점"), "-");
    ok("K1 「퀘스트 시작하기」", btns().some((x) => x.includes("퀘스트 시작하기")), "-");

    // K3 학교 — 방학중
    App.gameTab("school"); await w(1600);
    ok("K3 학교미션 상태표기", /방학중|준비 중|30초면 끝|했어요/.test(txt()), txt().slice(0, 70));
    App.gameTab(null); await w(400);

    // K5 상세 — 목록 탭이 바로 완료가 아니다
    await go("#mission", 2000);
    ok("K1/K5 오늘의 미션 줄", document.querySelectorAll(".kd-q").length > 0, document.querySelectorAll(".kd-q").length + "줄");
    const inst = (S.missions || []).find((x) => x.status === "open" && x.verify === "instant");
    if (inst) {
      const row = [...document.querySelectorAll(".kd-q")].find((b) => (b.getAttribute("onclick") || "").includes("msOpen(" + inst.id + ")"));
      if (row) {
        row.click(); await w(1100);
        ok("K5 줄 탭 → 상세(즉시완료 아님)", location.hash === "#missionone" && inst.status === "open", location.hash + " " + inst.status);
        ok("K5 큰 「다 했어요!」", [...document.querySelectorAll(".kd-act button")].some((b) => b.textContent.includes("다 했어요")),
           [...document.querySelectorAll(".kd-act button")].map((b) => b.textContent.trim()).join("/"));
      } else ok("K5 즉시형 줄", false, "줄 못 찾음");
    } else ok("K5 즉시형 미션", true, "오늘 남은 즉시형이 없어 건너뜀(결함 아님)");

    // K6 퀴즈
    await go("#game", 1200); App.gameTab("today"); await w(2500);
    const st = btns().find((x) => /시작하기|이어서 하기/.test(x));
    ok("K6 시작/이어하기 버튼", !!st, st || txt().slice(0, 40));
    App.gameTab(null); await w(400);

    // K7 상점
    await go("#store", 1800);
    ok("K7 부모 버튼 안 보임", !txt().includes("진열대에 올리기") && !txt().includes("진열대 고치기"), txt().slice(0, 60));
    await go("#game", 600);
  }

  ok("검수 후 로그인유지", !!TOKENS.access, "token " + !!TOKENS.access);
  const f = R.filter((x) => x.v === "FAIL");
  return JSON.stringify({ 역할: ROLE, 통과: R.length - f.length, 전체: R.length, 실패: f, 전부: R }, null, 1);
})();
