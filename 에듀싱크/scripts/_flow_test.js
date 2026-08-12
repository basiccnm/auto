/* 기능 시나리오 전수검사 (2026-08-12 대표님 «이런 걸 내가 하나하나 찾는 게 아니라 너가 찾아야»)
   사용자가 하는 일을 **그대로** 한다 — 넣고·고치고·체크하고·지우고·화면을 오간다.
   흐름마다 «눈에 보이는 결과»로 판정한다. 통과 못 하면 그게 고장 목록이다.
   ⚠ 서버에 흔적이 남는 것(전송·결제·자녀조작)은 안 한다. 로컬 STUB 흐름만. */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  if (!window.__errHooked) {
    window.__errHooked = 1; window.__errs = [];
    addEventListener("error", (e) => window.__errs.push(String(e.message || e).slice(0, 80)));
    addEventListener("unhandledrejection", (e) => window.__errs.push("P:" + String(e.reason).slice(0, 70)));
  }
  const scrTxt = () => (document.getElementById("screen")?.textContent || "").replace(/\s+/g, " ");
  const stuck = () => /불러오는 중|넣는 중/.test(scrTxt());
  const go = async (h) => { location.hash = h; App.render(); await w(900); };
  const menuLabels = () => (S.holdMenu?.actions || []).map((a) => a.label);
  const clickBtn = (re, scope) => {
    const b = [...(scope || document).querySelectorAll("button")].find((x) => re.test(x.textContent.trim()));
    if (b) b.click(); return !!b;
  };

  const flows = [];
  const F = (name, fn) => flows.push({ name, fn });

  /* ── 준비물 ─────────────────────────────────────────── */
  F("준비물-입력바로 넣기", async () => {
    await go("#supplies");
    const n0 = STUB.supplies.length;
    const inp = document.getElementById("ib-t");
    if (!inp) return "입력바 없음";
    S.ibText = "검사실내화"; inp.value = "검사실내화";
    if (!clickBtn(/^넣기$/)) return "넣기 버튼 없음";
    await w(700);
    if (STUB.supplies.length !== n0 + 1) return "개수가 안 늘음";
    if (!scrTxt().includes("검사실내화")) return "목록에 안 보임";
    return null;
  });
  F("준비물-여러 날짜 묶임", async () => {
    // 서로 다른 날짜 두 개를 코드로 넣고 — 화면이 날짜별로 묶어 보여주는지
    const mk = (item, date) => STUB.supplies.push({ id: Math.max(0, ...STUB.supplies.map(s => s.id)) + 1, item, date, done: false });
    mk("검사물감", ymdPlus(TODAY, 2)); mk("검사줄넘기", ymdPlus(TODAY, 3));
    await go("#supplies"); await w(300);
    const heads = [...document.querySelectorAll(".sp-dhd b")].map(b => b.textContent);
    if (heads.length < 2) return "날짜 묶음이 안 갈림(" + heads.join("/") + ")";
    if (!scrTxt().includes("검사물감") || !scrTxt().includes("검사줄넘기")) return "항목 누락";
    return null;
  });
  F("준비물-체크 토글", async () => {
    const s = STUB.supplies.find((x) => x.item === "검사실내화");
    if (!s) return "대상 없음";
    await App.supplyToggle(s.id); await w(500);
    if (!s.done) return "done 안 바뀜";
    const row = [...document.querySelectorAll(".sp-row")].find((r) => r.textContent.includes("검사실내화"));
    if (!row || !row.classList.contains("done")) return "화면에 체크 표시 안 됨";
    await App.supplyToggle(s.id); await w(300);
    return null;
  });
  F("준비물-꾹 메뉴(날짜·반복·지우기)", async () => {
    const s = STUB.supplies.find((x) => x.item === "검사실내화");
    const row = [...document.querySelectorAll(".sp-row")].find((r) => r.textContent.includes("검사실내화"));
    if (!row) return "줄 없음";
    // holdSupply 는 길게 눌러야 — 메뉴 내용만 직접 검사
    App.holdSupply({ clientX: 10, clientY: 10 }, s.id); await w(900);
    const ls = menuLabels();
    App.holdClose && App.holdClose();
    if (!ls.length) return "꾹 메뉴 안 뜸";
    if (!/날짜|지우기/.test(ls.join(","))) return "메뉴 구성 이상: " + ls.join(",");
    return null;
  });
  F("준비물-알림 화면", async () => {
    await go("#supplies");
    if (!clickBtn(/알림/)) return "알림 버튼 없음";
    await w(800);
    if (!/#notify/.test(location.hash)) return "알림 화면으로 안 감(" + location.hash + ")";
    return null;
  });

  /* ── 일정 ───────────────────────────────────────────── */
  F("일정-넣고 달력에 보임", async () => {
    S.day = TODAY; App.editOpen("plan"); await w(500);
    const t = document.getElementById("ed-t");
    t.value = "검사일정"; t.dispatchEvent(new Event("input")); await w(150);
    const sv = document.querySelector(".ed-act .ed-save");
    if (sv.disabled) return "넣기 버튼 잠김";
    sv.click(); await w(800);
    await go("#calendar");
    if (!scrTxt().includes("검사일정")) return "달력에 안 보임";
    return null;
  });
  F("일정-탭 메뉴→수정→저장", async () => {
    const ev = STUB.myEvents.find((x) => x.title === "검사일정");
    if (!ev) return "대상 없음";
    App.eventMenu(ev.id); await w(400);
    if (!menuLabels().includes("수정")) return "메뉴에 수정 없음";
    S.holdMenu.actions.find((a) => a.label === "수정").run(); S.holdMenu = null; await w(700);
    const t = document.getElementById("ed-t");
    if (!t) return "수정 화면 안 열림(" + location.hash + ")";
    t.value = "검사일정2"; t.dispatchEvent(new Event("input")); await w(150);
    document.querySelector(".ed-act .ed-save").click(); await w(800);
    if (!STUB.myEvents.find((x) => x.title === "검사일정2")) return "수정 저장 안 됨";
    return null;
  });
  F("일정-반복 켜고 저장", async () => {
    S.day = TODAY; App.editOpen("plan"); await w(500);
    const t = document.getElementById("ed-t");
    t.value = "검사반복"; t.dispatchEvent(new Event("input")); await w(150);
    if (!clickBtn(/매주 .요일/)) return "반복 칩 없음";
    await w(400);
    document.querySelector(".ed-act .ed-save").click(); await w(800);
    const ev = STUB.myEvents.find((x) => x.title === "검사반복");
    if (!ev) return "저장 안 됨";
    return null;
  });
  F("일정-삭제(반복은 모두 지우기)", async () => {
    for (const title of ["검사일정2", "검사반복"]) {
      const ev = STUB.myEvents.find((x) => x.title === title);
      if (!ev) continue;
      App.eventMenu(ev.id); await w(300);
      const acts = S.holdMenu?.actions || [];
      const del = acts.find((a) => /이후 반복 모두/.test(a.label)) || acts.find((a) => /삭제|이 날만/.test(a.label));
      if (!del) return "삭제 메뉴 없음";
      del.run(); S.holdMenu = null; await w(700);
      if (STUB.myEvents.find((x) => x.title === title)) return title + " 안 지워짐";
    }
    return null;
  });

  /* ── 방과후·시간표 ──────────────────────────────────── */
  F("방과후-넣기→그리드", async () => {
    await go("#afterschool");
    const col = document.querySelectorAll(".wk-col")[1];
    const rc = col.getBoundingClientRect();
    App.planTap({ currentTarget: col, clientY: rc.top + 40 }, 2); await w(500);
    if (location.hash !== "#editact") return "폼 안 열림";
    S.planDraft.name = "검사학원"; S.planDraft.color = 2;
    if (!clickBtn(/^추가$/)) return "추가 버튼 없음";
    await w(800);
    if (location.hash !== "#afterschool") return "격자로 복귀 안 함(" + location.hash + ")";
    if (![...document.querySelectorAll(".blk b")].some((b) => b.textContent === "검사학원")) return "블록 안 생김";
    return null;
  });
  F("방과후-탭 메뉴(이동·수정·삭제)", async () => {
    const a = STUB.activities.find((x) => x.name === "검사학원");
    App.planMenu(a.id, 2); await w(400);
    const ls = menuLabels(); App.holdClose();
    if (ls.join(",") !== "이동,수정,삭제") return "메뉴 이상: " + ls.join(",");
    return null;
  });
  F("시간표-하교후 탭 메뉴 + 셀 편집", async () => {
    await go("#timetable");
    const item = document.querySelector(".ttp-item");
    if (item) { item.click(); await w(400);
      const ls = menuLabels(); App.holdClose();
      if (!/수정/.test(ls.join(","))) return "하교후 메뉴 이상: " + ls.join(",");
    }
    // 셀 편집 — 편집 가능한 칸을 눌러 과목 화면이 뜨는지
    const cell = document.querySelector(".tt-grid .editable, .tt-grid > div[onclick]");
    if (!cell) return "편집 가능한 칸 없음";
    cell.click(); await w(700);
    const ok = location.hash === "#edittt" || !!document.getElementById("tt-v");
    if (!ok) return "과목 편집이 안 열림(" + location.hash + ")";
    App.ttClose && App.ttClose(); await w(300);
    return null;
  });
  F("방과후-삭제(폼에서)→복귀", async () => {
    const a = STUB.activities.find((x) => x.name === "검사학원");
    if (!a) return "대상 없음";
    await go("#afterschool");
    App.planEdit(a.id); await w(500);
    App.planDelete(); await w(300);
    App.planKillDo(); await w(600);
    if (location.hash === "#editact") return "폼에 갇힘";
    if (STUB.activities.find((x) => x.name === "검사학원")) return "안 지워짐";
    return null;
  });

  /* ── 알림·테마·홈편집·기타 ──────────────────────────── */
  F("알림-매일 알림 토글", async () => {
    await go("#notify");
    const on0 = !!S.remind?.on;
    const sw = document.querySelector('.swt, [role="switch"], input[type="checkbox"]');
    if (!sw) return "토글 없음";
    sw.click(); await w(600);
    if (!!S.remind?.on === on0) return "값이 안 바뀜";
    sw.click ? (document.querySelector('.swt, [role="switch"], input[type="checkbox"]')?.click()) : 0;
    await w(300);
    return null;
  });
  F("테마-바꾸고 적용", async () => {
    await go("#theme");
    const before = S.art;
    const other = [...document.querySelectorAll(".ns-th")].find((b) => !b.classList.contains("on"));
    if (!other) return "다른 테마 없음";
    other.click(); await w(400);
    if (!clickBtn(/이 테마 사용/)) return "적용 버튼 안 깨어남";
    await w(800);
    if (S.art === before) return "적용 안 됨";
    App.setArt(before); await w(300);   // 원복
    return null;
  });
  F("홈 카드 편집-끄고 켜기", async () => {
    await go("#homeedit");
    const key = (S.menuHidden.includes("meal") ? null : "meal") || "dday";
    const n0 = S.menuHidden.length;
    App.menuToggle(key); await w(400);
    if (S.menuHidden.length === n0) return "토글 안 먹음";
    App.menuToggle(key); await w(300);
    return null;
  });
  F("문의 쓰기 화면", async () => {
    await go("#ask");
    const ta = document.querySelector("textarea, .ed-title");
    if (!ta) return "입력칸 없음";
    return null;
  });
  F("서류-체험학습 서식 열림+자동채움", async () => {
    await go("#docs");
    App.docStart("field", "apply"); await w(800);
    const txt = scrTxt();
    if (!/자동으로 채웠어요/.test(txt)) return "자동채움 안 보임";
    if (stuck()) return "불러오는 중 갇힘";
    App.goBack(); await w(400);
    return null;
  });

  /* ── 실행 ───────────────────────────────────────────── */
  const out = [];
  for (const f of flows) {
    const e0 = window.__errs.length;
    let r;
    try { r = await f.fn(); } catch (err) { r = "예외: " + String(err).slice(0, 60); }
    const errs = window.__errs.slice(e0);
    if (r || errs.length) out.push({ 흐름: f.name, 문제: r || null, 오류: errs.slice(0, 2) });
  }
  // 검사 잔재 청소
  STUB.supplies = STUB.supplies.filter((s) => !/^검사/.test(s.item || ""));
  STUB.myEvents = STUB.myEvents.filter((e) => !/^검사/.test(e.title || ""));
  STUB.activities = STUB.activities.filter((a) => !/^검사/.test(a.name || ""));
  location.hash = "#home"; App.render();
  return JSON.stringify({ 검사: flows.length, 실패: out.length, 목록: out });
})();
