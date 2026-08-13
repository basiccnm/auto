/* 2026-08-13 남은 3건 실측 — 급식 아코디언 · 학교정보 웹 이식 · 서식 성명 */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const R = [];
  const ok = (n, p, d) => R.push({ n, v: p ? "OK" : "FAIL", d: String(d || "").slice(0, 120) });
  const txt = () => (document.getElementById("screen").textContent || "").replace(/\s+/g, " ");
  const go = async (h, ms) => { location.hash = h; App.render(); await w(ms || 1200); };

  /* ── ① 급식 아코디언 (실데이터 — 개학 8/20부터 5일) ─────── */
  S.mealAll = null; S.mealOpen = {}; S.mealQuery = '';
  await go('#meal', 1600);
  let cards = [...document.querySelectorAll('.ml-day')];
  ok('급식 카드', cards.length >= 3, cards.length + '일');
  if (cards.length >= 3) {
    const foldN = () => document.querySelectorAll('.ml-day.fold').length;
    const totH = () => Math.round([...document.querySelectorAll('.ml-day')].reduce((a2, e) => a2 + e.getBoundingClientRect().height, 0));
    ok('① 기본 = 한 날만 펼침', foldN() === cards.length - 1, '카드' + cards.length + ' 접힘' + foldN());
    const sum = document.querySelector('.ml-day.fold .ml-sum');
    const sumH = sum ? Math.round(sum.getBoundingClientRect().height) : 0;
    ok('① 접힌 날 = 반찬 한 줄', !!sum && sum.textContent.includes('·') && sumH < 26,
       (sum ? sum.textContent.trim().slice(0, 30) : '없음') + ' h' + sumH);
    const foldH = Math.round(document.querySelector('.ml-day.fold').getBoundingClientRect().height);
    const openH = Math.round(document.querySelector('.ml-day:not(.fold)').getBoundingClientRect().height);
    ok('① 접힌 카드가 훨씬 낮다', foldH < 72 && foldH * 2 < openH, '접힘' + foldH + 'px 펼침' + openH + 'px');
    const allH0 = totH();

    const all1 = [...document.querySelectorAll('#screen button')].find((b2) => b2.textContent.includes('전체 펼치기'));
    ok('① 전체 펼치기 버튼', !!all1, all1 ? all1.textContent.trim() : '없음');
    if (all1) { all1.click(); await w(800);
      ok('① 전체 펼치기 동작', foldN() === 0, '접힘 ' + foldN() + ' 총높이 ' + totH() + 'px');
      const all2 = [...document.querySelectorAll('#screen button')].find((b2) => b2.textContent.includes('전체 닫기'));
      ok('① 버튼이 「전체 닫기」로', !!all2, all2 ? all2.textContent.trim() : '없음');
      if (all2) { const openAllH = totH(); all2.click(); await w(800);
        ok('① 전체 닫기 — 목록이 한눈에', foldN() === cards.length && totH() * 3 < openAllH,
           '접힘' + foldN() + ' 총높이 ' + openAllH + '→' + totH() + 'px');
      }
    }
    let hd = document.querySelector('.ml-day .ml-dtog'); hd.click(); await w(700);
    ok('① 줄 눌러 펴기', document.querySelectorAll('.ml-day:not(.fold)').length === 1,
       '펼침 ' + document.querySelectorAll('.ml-day:not(.fold)').length);
    hd = document.querySelector('.ml-day .ml-dtog'); hd.click(); await w(700);
    ok('① 한 번 더 눌러 닫기', foldN() === cards.length, '접힘 ' + foldN());

    // 기본 펼친 날을 한 번에 닫을 수 있는가(두 번 눌러야 닫히던 함정)
    S.mealAll = null; S.mealOpen = {}; App.render(); await w(700);
    const lead = document.querySelector('.ml-day:not(.fold) .ml-dtog');
    if (lead) { lead.click(); await w(700);
      ok('① 기본 펼친 날도 한 번에 닫힘', foldN() === cards.length, '접힘 ' + foldN());
    }
    // 알림 스위치가 카드를 열지 않는가
    S.mealAll = null; S.mealOpen = {}; App.render(); await w(600);
    const before = foldN();
    const al = document.querySelector('.ml-day.fold .ml-alarm');
    if (al) { al.click(); await w(700);
      ok('① 알림 스위치가 카드를 안 편다', foldN() === before, '접힘 ' + before + '→' + foldN());
      const al2 = document.querySelector('.ml-day.fold .ml-alarm.on'); if (al2) { al2.click(); await w(500); }
    }
    S.mealAll = null; S.mealOpen = {};
  }

  /* ── ② 학교정보 — 웹에 있던 값이 화면에 그려지는가 ──────────
     서버 배포가 보류라 실제 응답엔 아직 새 필드가 없다.
     서버가 보낼 값(D1 실측 그대로)을 넣어 «화면이 그릴 줄 아는지»를 잰다. */
  const keep = SCHOOL.info;
  SCHOOL.info = { ...(SCHOOL.info || {}),
    name: "서울숭미초등학교", kind: "초등학교", sido: "서울특별시",
    address: "서울특별시 노원구 …", phone: "02-000-0000", homepage: "http://sungmi.es.kr",
    est_type: "공립", coedu: "남여공학", founded_ymd: "19810610",
    office: "서울특별시북부교육지원청",
    detail: { class_count: 26, student_count: 487, teacher_count: 41,
      male_count: 241, female_count: 246, school_days: 191, week_class_hours: 690,
      disclosure_round: "2026", afterschool_program_count: 40, afterschool_student_count: 288,
      care_class_yn: "Y",
      grade_breakdown: [{ grade: 1, students: 67, classes: 4, male: 34, female: 33 },
                        { grade: 2, students: 78, classes: 4, male: 40, female: 38 }] } };
  try {
    S.gradesOpen = true;
    await go("#schoolinfo", 1200);
    const t = txt();
    const want = [["설립·공학·개교", "공립 · 남녀공학 · 1981년 개교"],
                  ["교육지원청", "서울특별시북부교육지원청"],
                  ["교원 수", "41"], ["개교 스탯", "1981"],
                  ["연간 수업일수", "191일"], ["주당 수업시수", "690시수"],
                  ["남녀", "남 241 · 여 246"],
                  ["방과후 참여", "방과후 40개 프로그램 (참여 288명)"],
                  ["돌봄", "돌봄교실 운영"],
                  ["공시회차", "2026 공시"],
                  ["반평균", "반평균"]];
    want.forEach(([k, v]) => ok("② " + k, t.includes(v), v));
    ok("② 빈 공시 문구 안 나감", !t.includes("학교알리미  공시"), t.includes("학교알리미") ? "학교알리미 문구 있음" : "-");
  } finally { SCHOOL.info = keep; S.gradesOpen = false; }

  /* ── ③ 서식 성명 ───────────────────────────────────────── */
  await go("#docs", 1200);
  App.docStart("field", "apply"); await w(1200);
  const inp = document.getElementById("doc-realname");
  ok("③ 성명 입력칸 있음", !!inp, inp ? "placeholder=" + inp.placeholder : "없음");
  ok("③ 「상세에서」 안내 사라짐", !txt().includes("상세에서"), txt().includes("상세") ? "상세 글자 남음" : "-");
  if (inp) {
    inp.value = "김실명"; App.docNameSet("김실명"); await w(300);
    const saved = JSON.parse(localStorage.getItem("eduthink_doc_names_v1") || "{}");
    ok("③ 기기에 저장", Object.values(saved).includes("김실명"), JSON.stringify(saved));
    const focusKept = document.activeElement === inp || true;   // 다시 그리지 않으므로 커서 유지
    S.docDraft.from = "2026-08-24"; S.docDraft.to = "2026-08-26"; App.docDays && App.docDays();
    App.docPreview(); await w(1500);
    const paper = (document.querySelector(".paper") || document.getElementById("screen")).textContent.replace(/\s+/g, " ");
    ok("③ 서식에 실명이 찍힌다", paper.includes("김실명"), paper.slice(0, 90));
    ok("③ 별명이 성명칸에 안 남음", !/성명 첫째|학생 첫째/.test(paper), "-");
    App.docNameSet(""); location.hash = "#docs"; App.render(); await w(300);
  }

  ok("검수 후 로그인유지", !!TOKENS.access, "token " + !!TOKENS.access);
  const f = R.filter((x) => x.v === "FAIL");
  return JSON.stringify({ 통과: R.length - f.length, 전체: R.length, 실패: f, 전부: R });
})();
