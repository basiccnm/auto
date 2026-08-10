// ============================================================
// 🔐 로그인·로그아웃 흐름 실측 — 깨끗한 설치에서 시작해 한 바퀴 돈다 (2026-08-10)
//
//   node scripts/emul_eval.mjs --file scripts/probe_auth_flow.js
//
// 재는 것 —
//   ① 비로그인: 아이 등록 게이트가 #login 으로 보내나
//   ② 로그인: ph5126 실계정으로 토큰이 오고 자녀가 /me 로 오나
//   ③ 자동로그인: 토큰이 저장돼 다음 부팅에도 살아 있나
//   ④ 설정 「계정」: 로그인 전=가입·로그인 / 후=로그아웃·탈퇴 로 갈리나
//   ⑤ 로그아웃: 토큰·자녀·캐시가 지워지고 다시 게이트가 걸리나
//
// ⚠ 앱 내부 규칙 (지난 실측에서 배운 것 — 어기면 오탐이 난다):
//   · api() 의 body 는 **객체** — 문자열을 주면 이중 인코딩돼 VALIDATION 이 온다
//   · 토큰 저장은 saveTokens(r.data) — 부팅 복원 근거
//   · 자녀는 loadMe() 가 /me 에서 받아 STUB.children 에 채운다
//   · 현재 자녀 키는 S.currentChildId (S.childId 아님)
// ============================================================
(async () => {
  const out = [];
  const ok = (name, pass, detail) => out.push(`${pass ? "✅" : "🔴"} ${name}${detail ? " — " + detail : ""}`);
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  // ── 0. 시작 상태 (깨끗한 설치면 비로그인이어야 한다)
  const hadToken = !!(TOKENS && TOKENS.access);
  if (hadToken) { App.logout(); await wait(500); }
  ok("0. 시작 상태 = 비로그인", !(TOKENS && TOKENS.access), hadToken ? "(로그인돼 있어 로그아웃시킴)" : "깨끗한 설치");

  // ── ① 비로그인 게이트 — 아이 등록을 눌렀을 때
  location.hash = "#home"; App.render(); await wait(300);
  App.childAddStart && App.childAddStart();
  await wait(400);
  ok("1. 아이 등록 → #login 게이트", location.hash === "#login", "hash=" + location.hash);

  // ── ② 로그인 (실계정 · 실서버) — 앱과 같은 모양으로
  let r = await api("/auth/login", { method: "POST", body: { login_id: "ph5126", password: "testpass123" } });
  const gotTok = !!(r && r.ok && r.data && r.data.access_token);
  // 실제 로그인 핸들러(app.js 8014~)와 같은 상태 전이 — S.loggedIn 을 안 넣으면 라우터가 login 으로 되돌린다
  if (gotTok) { saveTokens(r.data); S.loggedIn = true; S.serverAuth = true; S.authEnded = null; }
  ok("2. 로그인 → 토큰 수신", gotTok, gotTok ? "access " + TOKENS.access.length + "자" : JSON.stringify(r && r.error));

  // ── ②-2 자녀가 /me 로 오나 (부팅과 같은 경로)
  if (gotTok) await loadMe();
  const kids = (STUB.children || []).length;
  const kong = (STUB.children || []).find((c) => ((c.name || "") + (c.nickname || "")).indexOf("콩") >= 0);
  ok("3. 자녀 목록 서버 수신 (/me)", kids > 0, kids + "명" + (kong ? " · 「콩」 server_id=" + kong.server_id : ""));

  // ── ③ 홈이 그려지나 (로그인 상태)
  location.hash = "#home"; App.render(); await wait(800);
  const homeDrawn = !!document.querySelector(".hv3-art, .hd-top");
  ok("4. 홈 렌더", homeDrawn, homeDrawn ? "그려짐" : "빈 화면");

  // ── ③-2 전광판이 항상 떠 있나 (없는 날에도)
  const board = document.querySelector("#board .bd-mq > span");
  ok("5. 전광판 상시 표시", !!board, board ? "「" + board.textContent.slice(0, 34) + "…」" : "없음");

  // ── ④ 설정 「계정」 — 로그인 후: 로그아웃 O · 가입하기 X
  location.hash = "#mypage"; App.render(); await wait(400);
  let scr = (document.getElementById("screen") || {}).textContent || "";
  const hasLogout = scr.indexOf("로그아웃") >= 0, hasJoin = scr.indexOf("가입하기") >= 0;
  ok("6. 설정(로그인 후) = 로그아웃 O · 가입하기 X", hasLogout && !hasJoin,
    "로그아웃:" + hasLogout + " 가입하기:" + hasJoin);

  // ── ⑤ 자동로그인 근거 — 저장소에 토큰이 남아 있나
  let stored = false;
  try { for (let i = 0; i < localStorage.length; i++) { const v = localStorage.getItem(localStorage.key(i)) || ""; if (TOKENS.access && v.indexOf(TOKENS.access.slice(0, 24)) >= 0) { stored = true; break; } } } catch (e) {}
  ok("7. 토큰 저장(자동로그인 근거)", stored, stored ? "" : "저장소에 없음");

  // ── ⑥ 로그아웃
  App.logout(); await wait(600);
  ok("8. 로그아웃 → 토큰·자녀 소거", !(TOKENS && TOKENS.access) && !(STUB.children || []).length,
    "hash=" + location.hash + " 자녀=" + (STUB.children || []).length + "명");

  // ── ⑥-2 저장소도 비었나 (다음 부팅 때 자동로그인 되면 안 된다)
  let leak = false;
  try { for (let i = 0; i < localStorage.length; i++) { const v = localStorage.getItem(localStorage.key(i)) || ""; if (v.length > 80 && v.indexOf("access") >= 0 && v.indexOf("eyJ") >= 0) { leak = true; break; } } } catch (e) {}
  ok("9. 로그아웃 후 저장소에 토큰 없음", !leak);

  // ── ⑦ 로그아웃 뒤 다시 게이트
  location.hash = "#home"; App.render(); await wait(300);
  App.childAddStart && App.childAddStart(); await wait(400);
  ok("10. 로그아웃 후 아이 등록 → #login", location.hash === "#login");

  // ── ⑧ 설정 — 로그아웃 후: 두 갈래 다 정답이다
  //   · 설문 안 한 비로그인 → 라우터가 **로그인 화면**으로 게이트 (이 기기 상태)
  //   · 비회원 둘러보기(isGuest) → 설정이 열리되 「가입하기」 블록 + 로그아웃 없음
  location.hash = "#mypage"; App.render(); await wait(400);
  scr = (document.getElementById("screen") || {}).textContent || "";
  const gatedToLogin = scr.indexOf("아이디") >= 0 && scr.indexOf("로그아웃") < 0;   // 로그인 화면이 그려짐
  const guestMypage = scr.indexOf("가입하기") >= 0 && scr.indexOf("로그아웃") < 0;  // 비회원용 설정
  ok("11. 설정(로그아웃 후) 게이트", gatedToLogin || guestMypage,
    gatedToLogin ? "로그인 화면으로 게이트(비회원 아님 — 정답)" : guestMypage ? "비회원 설정(가입하기)" : "둘 다 아님");

  // ── ⑨ 다시 로그인해 «쓰던 상태»로 복원 (이후 검수는 로그인 상태로)
  r = await api("/auth/login", { method: "POST", body: { login_id: "ph5126", password: "testpass123" } });
  if (r && r.ok && r.data && r.data.access_token) {
    saveTokens(r.data); S.loggedIn = true; S.serverAuth = true; S.authEnded = null;
    await loadMe();
    location.hash = "#home"; App.render(); await wait(500);
  }
  ok("12. 재로그인 → 홈 복원", !!(TOKENS.access && (STUB.children || []).length), (STUB.children || []).length + "명");

  const fails = out.filter((l) => l.indexOf("🔴") === 0).length;
  return out.join(String.fromCharCode(10)) + String.fromCharCode(10) +
    (fails ? "🔴 " + fails + "건 실패" : "✅ 12항목 전부 통과");
})();
