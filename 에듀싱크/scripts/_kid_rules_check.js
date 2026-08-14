/* 08-14 지적 검증 — 자녀폰에서: ④ 타일→상세 통일 · ① 재밌던수업 원 · ⑥ 🔥 숨김 */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const R = [];
  const ok = (n, p, d) => R.push({ n, v: p ? "OK" : "FAIL", d: String(d ?? "").slice(0, 90) });

  // ⑥ 🔥 — streak 0이면 숨고, 3이면 「3일째」
  location.hash = "#game"; App.gameTab(null); App.render(); await w(1500);
  ok("⑥ 🔥0 숨김", !document.querySelector(".kd-pill.fire"), "-");
  const keep = S.coin ? { ...S.coin } : null;
  if (S.coin) { S.coin.streak = 3; App.render(); await w(300);
    const f = document.querySelector(".kd-pill.fire");
    ok("⑥ 🔥3 = 「3일째」", !!f && f.textContent.includes("3일째"), f && f.textContent.trim());
    S.coin = keep; App.render(); await w(200);
  }

  // ④ 방과후 카드 타일 = 상세로 (즉시 완료 아님)
  App.gameTab("after"); await w(1800);
  const open = (S.missions || []).find((x) => x.status === "open");
  if (open) {
    const tile = [...document.querySelectorAll(".gm-tile")].find((b) => (b.getAttribute("onclick") || "").includes("msOpen(" + open.id + ")"));
    ok("④ 타일 onclick=msOpen", !!tile, tile ? "있음" : [...document.querySelectorAll(".gm-tile")].map(b=>b.getAttribute("onclick")).join("|").slice(0,80));
    if (tile) {
      const st0 = open.status;
      tile.click(); await w(1200);
      ok("④ 탭→상세(#missionone)·즉시완료 아님", location.hash === "#missionone" && open.status === st0,
         location.hash + " " + open.status);
      const done = [...document.querySelectorAll(".kd-act button")].find((b) => /다 했어요|사진 찍기/.test(b.textContent));
      ok("④ 상세에 확정 버튼", !!done, done && done.textContent.trim());
      location.hash = "#game"; App.render(); await w(600);
    }
  } else ok("④ 안 한 미션", true, "open 없음 — 건너뜀(결함 아님)");
  App.gameTab(null); await w(300);

  // ① 재밌던 수업 — 원이 눌러서 채워지는가 (개학 학교=셋째 폰에서만 과목이 있다)
  location.hash = "#childsubject"; App.render(); await w(1200);
  const t = (document.getElementById("screen").textContent || "").replace(/\s+/g, " ");
  if (t.includes("수업이 없는 날")) {
    ok("① 재밌던수업", true, "이 아이는 오늘 수업 없음 — 셋째 폰에서 본다");
  } else {
    const btns = [...document.querySelectorAll(".kd2-pick1 button")];
    ok("① 과목 줄 있음", btns.length > 0, btns.length + "개");
    if (btns.length) {
      btns[0].click(); await w(400);
      const on = document.querySelector(".kd2-pick1 button.on");
      const i = on && on.querySelector("i");
      const cs = i && getComputedStyle(i);
      ok("① 누르면 원이 채워짐", !!on && cs && cs.backgroundColor !== "rgba(0, 0, 0, 0)",
         on ? `bg ${cs.backgroundColor}` : "on 없음");
      const cta = document.querySelector(".kd2-cta");
      ok("① 보내기 활성화", cta && !cta.disabled, "-");
      btns[0].click(); await w(300);   // 원복(다시 눌러 해제)
    }
  }
  location.hash = "#game"; App.render(); await w(400);

  const f = R.filter((x) => x.v === "FAIL");
  return JSON.stringify({ 통과: R.length - f.length, 전체: R.length, 실패: f, 전부: R });
})();
