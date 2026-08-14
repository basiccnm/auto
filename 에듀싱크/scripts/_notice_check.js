/* 공지사항 검증 — 드로어 줄·배지·목록(제목 1줄)·글·읽음 처리 */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const R = []; const ok = (n, p, d) => R.push({ n, v: p ? "OK" : "FAIL", d: String(d ?? "").slice(0, 80) });
  localStorage.removeItem("eduthink.noticeSeen");
  location.hash = "#home"; App.render(); await w(800);

  // 목록 먼저 받아 배지 셈이 서게 한다
  S.notices = undefined; location.hash = "#notices"; App.render(); await w(2000);
  const rows = [...document.querySelectorAll(".mp-row")];
  ok("목록 줄 있음", rows.length >= 1, rows.length + "줄");
  const l = rows[0] && rows[0].querySelector(".mp-l");
  const cs = l && getComputedStyle(l);
  ok("제목 1줄(말줄임)", cs && cs.whiteSpace === "nowrap" && cs.textOverflow === "ellipsis", cs && cs.whiteSpace);
  ok("내용 미리보기 없음", l && !l.textContent.includes("안녕하세요"), l && l.textContent.trim().slice(0, 40));
  ok("새 글 N 표시", rows[0] && rows[0].textContent.includes("N"), "-");

  // 드로어 배지
  location.hash = "#home"; App.render(); await w(500);
  S.drawer = true; App.render(); await w(600);
  const item = [...document.querySelectorAll(".ns-item")].find((b) => b.textContent.includes("공지사항"));
  ok("드로어에 공지사항 줄", !!item, item && item.textContent.replace(/\s+/g, " ").trim());
  const foot = [...document.querySelectorAll(".ns-foot .ns-item")].map((b) => b.textContent.trim());
  ok("내정보·설정 «위»에 위치", !!item && !item.closest(".ns-foot"), foot.join("/"));
  ok("드로어 배지 1", item && /1/.test(item.textContent), "-");
  S.drawer = false; App.render(); await w(300);

  // 글 열기 → 본문 → 읽음 처리로 배지 사라짐
  location.hash = "#notices"; App.render(); await w(600);
  document.querySelector(".mp-row").click(); await w(900);
  const t = (document.getElementById("screen").textContent || "").replace(/\s+/g, " ");
  ok("글 열림(#notice)+본문", location.hash === "#notice" && t.includes("안녕하세요, 학교퀘스트입니다"), location.hash);
  location.hash = "#notices"; App.render(); await w(600);
  ok("읽고 나면 N 사라짐", !document.querySelector(".mp-row").textContent.includes("N"), "-");
  location.hash = "#home"; App.render(); await w(600);
  S.drawer = true; App.render(); await w(500);
  const item2 = [...document.querySelectorAll(".ns-item")].find((b) => b.textContent.includes("공지사항"));
  ok("드로어 배지도 사라짐", item2 && !/\d/.test(item2.textContent.replace("공지사항", "")), item2 && item2.textContent.trim());
  S.drawer = false; location.hash = "#home"; App.render();
  const f = R.filter((x) => x.v === "FAIL");
  return JSON.stringify({ 통과: R.length - f.length, 전체: R.length, 실패: f, 전부: R });
})();
