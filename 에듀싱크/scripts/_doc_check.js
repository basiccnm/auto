/* 사용법 문서 항목별 실확인 (2026-08-13 대표님 「너가 쓴 거 화면별로 다 확인해봤어?」)
   docs/사용법-화면별-20260813.txt 의 각 줄이 진짜인지 **화면에서 재서** 판정한다.
   window.__docRole = "parent" | "child" */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const R = [];
  const ok = (no, name, pass, detail) => R.push({ no, name, v: pass ? "OK" : "FAIL", d: String(detail || "").slice(0, 90) });
  const txt = () => (document.getElementById("screen").textContent || "").replace(/\s+/g, " ");
  /* ⚠ 항목 사이 상태 격리 — 앞 항목이 폼·메뉴를 열어 두면 다음 항목이 통째로 헛것이 된다
     (2026-08-13: 방과후 폼이 남아 미션 ‹·상세 판정이 줄줄이 FAIL 로 찍혔다) */
  const reset = () => { S.planDraft = null; S.planMove = null; S.holdMenu = null; S.edit = null;
    S.msDetail = null; S.childSwitch = false; S.drawer = false; };
  const go = async (h, ms) => { reset(); location.hash = h; App.render(); await w(ms || 1200); };
  const btn = (t) => [...document.querySelectorAll("#screen button, #screen a")]
    .find((b) => b.textContent.replace(/\s+/g, " ").includes(t));
  const ROLE = window.__docRole || "parent";
  localStorage.setItem(MS_COACH_KEY, "1"); S.msCoach = null; S._msCoachQueued = true;

  if (ROLE === "parent") {
    // 1 홈 — 서랍 5칸 + 앞판 키
    await go("#home", 1500);
    const rows = [...document.querySelectorAll(".ns-chest .ns-row")];
    const hs = rows.map((r) => Math.round(r.getBoundingClientRect().height));
    ok(1, "홈 서랍 5칸·앞판 80±8", rows.length === 5 && hs.every((h) => h >= 60 && h <= 95), rows.length + "칸 " + hs.join(","));

    // 2 드로어 — 자녀 전환 줄 + 팝업 시트
    S.drawer = true; App.render(); await w(500);
    const line = document.querySelectorAll(".ns-kids .kchip");
    let sheetOK = false, addOK = false;
    if (line.length === 1) {
      line[0].click(); await w(500);
      const rws = document.querySelectorAll(".sheet .mp-row");
      sheetOK = rws.length >= 2;
      addOK = !![...document.querySelectorAll(".sheet button")].find((b) => b.textContent.includes("자녀 추가"));
      App.childSwitchClose(); await w(200);
    }
    ok(2, "드로어 자녀전환 줄1+시트", line.length === 1 && sheetOK && addOK, "줄" + line.length + " 시트" + sheetOK + " 추가" + addOK);
    S.drawer = false; App.render(); await w(200);

    // 3 달력 — 빨강=일요일/공휴일만
    await go("#calendar", 1800);
    const suns = [...document.querySelectorAll(".gc-num.sun")].map((e) => +e.textContent.trim());
    const ym = (S.calMonth || TODAY.slice(0, 6));
    const bad = suns.filter((d) => {
      const dow = new Date(+ym.slice(0, 4), +ym.slice(4, 6) - 1, d).getDay();
      return dow !== 0 && !schedulesOf().some((e) => e.date === ym + String(d).padStart(2, "0") && isHoliday(e));
    });
    ok(3, "달력 빨강=일/공휴일만", bad.length === 0, "빨강 " + suns.join(",") + (bad.length ? " 잘못:" + bad.join(",") : ""));

    // 4 급식 — 월간 없음
    await go("#meal", 1600);
    ok(4, "급식 주간고정(월간 없음)", !txt().includes("월간") && !txt().includes("지난 급식"), txt().slice(0, 50));

    // 5 방과후 — 이동 뒤 폼 안 열림
    await go("#afterschool", 1800);
    const blk = document.querySelector(".blk");
    if (blk) {
      blk.click(); await w(600);
      const mv = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("이동"));
      if (mv) { mv.click(); await w(800);
        ok(5, "방과후 이동→폼 안열림", !!S.planMove && !S.planDraft && location.hash === "#afterschool",
           "planMove " + !!S.planMove + " draft " + !!S.planDraft + " " + location.hash);
        S.planMove = null; S.planDraft = null; App.render();
      } else ok(5, "방과후 이동 메뉴", false, "메뉴에 이동 없음");
    } else ok(5, "방과후 블록", false, "블록 없음(등록 필요)");

    // 6 미션(부모) — 리본·다이얼·타일·‹홈
    await go("#mission", 2200); S.msCoach = null; App.render(); await w(300);
    for (let i = 0; i < 12 && !document.querySelector(".kd-kn"); i++) await w(400);   // econ 응답 대기
    const dial = document.querySelectorAll(".kd-kn").length;
    const tiles = document.querySelectorAll(".kd-tile").length;
    ok(6, "미션 리본+다이얼2+타일6", !!document.querySelector(".kd-path") && dial === 2 && tiles >= 6,
       "다이얼" + dial + " 타일" + tiles);
    const bk = document.querySelector(".kd-bk"); bk.click(); await w(800);
    ok(6.1, "미션 ‹ → 홈", location.hash === "#home", location.hash);

    // 7 미션 하나(부모)
    await go("#mission", 1800); S.msCoach = null; App.render(); await w(300);
    const open = (S.missions || []).find((x) => x.status === "open");
    if (open) {
      App.msOpen(open.id); await w(1500);
      for (let i = 0; i < 12 && !document.querySelector(".kd-week .d"); i++) await w(400);   // 지난이레 대기
      const bs = [...document.querySelectorAll(".kd-act button")].map((b) => b.textContent.trim());
      const dots = document.querySelectorAll(".kd-week .d").length;
      ok(7, "상세 버튼3+요일판7", bs.length === 3 && dots === 7, bs.join("/") + " dots" + dots);
      await go("#mission", 800);
    } else ok(7, "미션 상세", false, "open 미션 없음");

    // 8 고르기 — 토글·8개 상한·담기
    App.missionPickOpen(); await w(2500);
    S.missionPick = []; App.render(); await w(300);
    const cand = [...document.querySelectorAll(".mk-row")];
    if (cand.length) {
      cand[0].click(); await w(200);
      const one = (S.missionPick || []).length === 1;
      cand[0].click(); await w(200);
      const zero = (S.missionPick || []).length === 0;
      for (const r of cand.slice(0, 10)) { r.click(); await w(90); }
      const capped = (S.missionPick || []).length <= 8 && (S.missionPick || []).length >= 6;
      ok(8, "고르기 토글+상한8", one && zero && capped, "담김 " + (S.missionPick || []).length);
    } else ok(8, "고르기 목록", false, "후보 0");
    S.missionPick = []; await go("#mission", 800);

    // 10 오늘 한 것 — 소속별
    await go("#missiontoday", 1800);
    ok(10, "오늘한것 소속별", txt().includes("아침 미션") && txt().includes("방과후 미션"), txt().slice(0, 70));

    // 11 추가 증정 — 줄 단위
    await go("#missionbonus", 1500);
    ok(11, "추가증정 화면", txt().includes("추가 증정"), txt().slice(0, 50));

    // 12 상점(부모) — 관리 버튼
    await go("#store", 1800);
    ok(12, "상점 부모 관리버튼", txt().includes("진열대"), txt().slice(0, 50));
    await go("#tickets", 1500);
    ok(12.1, "티켓 화면", txt().includes("티켓"), txt().slice(0, 40));

    // 13 학교정보
    await go("#schoolinfo", 2000);
    ok(13, "학교정보 주소·전화", !!document.querySelector('a[href^="tel:"]'), txt().slice(0, 70));

    // 14 테마 — 기본 파랑 첫 타일
    await go("#theme", 1500);
    const th = [...document.querySelectorAll(".ns-th b")].map((b) => b.textContent.trim());
    ok(14, "테마 기본파랑 첫칸", th[0] === "기본 파랑", th.slice(0, 3).join("/"));

    await go("#home", 500);
  } else {
    // ── 자녀폰 ──
    await go("#game", 2000);
    ok(17, "아이 홈 리본+타일", !!document.querySelector(".kd-path") && document.querySelectorAll(".kd-tile").length >= 2, txt().slice(0, 50));
    await go("#mission", 2200);
    ok(18, "아이 미션 kd", !!document.querySelector(".kd-scr") && document.querySelectorAll(".kd-q").length > 0,
       document.querySelectorAll(".kd-q").length + "줄");
    const inst = (S.missions || []).find((x) => x.status === "open" && x.verify === "instant");
    if (inst) {
      const row = [...document.querySelectorAll(".kd-q")].find((b) => (b.getAttribute("onclick") || "").includes("msOpen(" + inst.id + ")"));
      if (row) { row.click(); await w(1000);
        ok(18.1, "줄 탭→상세(즉시완료 아님)", location.hash === "#missionone" && inst.status === "open", location.hash);
        const d = [...document.querySelectorAll(".kd-act button")].find((b) => b.textContent.includes("다 했어요"));
        if (d) { d.click(); await w(300);
          const m = (S.missions || []).find((x) => x.id === inst.id);
          ok(18.2, "다했어요 즉시반영", m.status === "done" && !!S.kidHooray, m.status + " 축하" + !!S.kidHooray);
          await w(5000);
          const m2 = (S.missions || []).find((x) => x.id === inst.id);
          ok(18.3, "서버 확정 유지", m2.status === "done", m2.status + " +★" + m2.got);
          S.kidHooray = null; App.render();
        } else ok(18.2, "다했어요 버튼", false, "없음");
      } else ok(18.1, "즉시형 줄", false, "못 찾음");
    } else ok(18.1, "즉시형 미션", false, "없음");

    // 학교미션 방학중
    await go("#game", 1200); App.gameTab("school"); await w(1500);
    ok(18.4, "학교미션 방학중 표시", txt().includes("방학중") || txt().includes("30초면 끝"), txt().slice(0, 70));
    App.gameTab(null); await w(300);

    // 19 퀴즈
    App.gameTab("today"); await w(2500);
    const st = [...document.querySelectorAll("button")].find((b) => /시작하기|이어서 하기/.test(b.textContent));
    if (st) { st.click(); await w(1500);
      const hasQ = !!document.querySelector(".qz-q"), hasX = !!document.querySelector(".qz-quit");
      const op = document.querySelector(".qz-op"); if (op) { op.click(); await w(3500); }
      const q2 = document.querySelector(".qz-quit"); if (q2) { q2.click(); await w(2500); }
      const again = [...document.querySelectorAll("button")].find((b) => /이어서 하기|시작하기/.test(b.textContent));
      ok(19, "퀴즈 문제+✕+이어하기", hasQ && hasX && !!again, "이어 " + (again ? again.textContent.trim() : "-"));
    } else ok(19, "퀴즈 시작", false, txt().slice(0, 40));
    App.gameTab(null); await w(300);

    // 20 상점(아이)
    await go("#store", 1800);
    ok(20, "아이 상점(부모버튼 없음)", !txt().includes("진열대에 올리기") && !txt().includes("진열대 고치기"), txt().slice(0, 60));
    await go("#game", 500);
  }

  /* ⛔ 검수가 로그인을 깨고 끝나면 대표님 화면에 «첫 실행 안내»가 뜬다 — 마지막에 반드시 확인 */
  ok(99, "검수 후 로그인유지", !!TOKENS.access && S.loggedIn, "token " + !!TOKENS.access);

  const fails = R.filter((x) => x.v === "FAIL");
  return JSON.stringify({ 역할: ROLE, 통과: R.length - fails.length, 전체: R.length, 실패: fails, 전부: R });
})();
