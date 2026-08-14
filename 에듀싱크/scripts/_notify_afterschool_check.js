/* 부모폰: ⑦ 방과후 블록 색 · ⑩ 미션 알림 토글(실서버 저장까지) */
(async () => {
  const w = (ms) => new Promise((r) => setTimeout(r, ms));
  const R = []; const ok = (n, p, d) => R.push({ n, v: p ? "OK" : "FAIL", d: String(d ?? "").slice(0, 90) });

  // ⑦ 방과후 블록 — 칸 전체가 색인가
  location.hash = "#afterschool"; App.render(); await w(1600);
  const blk = document.querySelector(".blk");
  if (!blk) ok("⑦ 방과후 블록", true, "등록된 학원 없음 — 건너뜀");
  else {
    const cs = getComputedStyle(blk);
    const bg = cs.backgroundColor;
    // 흰 카드(--card ≈ rgb(255,…) 계열 순백)면 실패 — 색이 섞였으면 채널이 갈린다
    let m = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!m) { const s2 = bg.match(/color\(srgb ([\d.]+) ([\d.]+) ([\d.]+)/);
      if (s2) m = [0, Math.round(s2[1] * 255), Math.round(s2[2] * 255), Math.round(s2[3] * 255)]; }
    const tinted = m && !(String(m[1]) === String(m[2]) && String(m[2]) === String(m[3]));
    ok("⑦ 블록 칸이 색으로 참", !!tinted, bg);
  }

  // ⑩ 알림 설정 — 화면 토글 + 실서버 PUT/GET 왕복
  location.hash = "#notify"; App.render(); await w(2000);
  const t = (document.getElementById("screen").textContent || "").replace(/\s+/g, " ");
  ok("⑩ 토글 2개 보임", t.includes("미션 해냈을 때") && t.includes("확인 기다릴 때"), t.slice(0, 80));
  const before = await api("/notify-prefs").catch(() => null);
  ok("⑩ GET", !!before?.ok, JSON.stringify(before?.data));
  await App.notifyPrefSet("mission_done", false); await w(1200);
  const mid = await api("/notify-prefs").catch(() => null);
  ok("⑩ 끄기 저장됨", mid?.ok && mid.data.mission_done === false, JSON.stringify(mid?.data));
  await App.notifyPrefSet("mission_done", true); await w(1200);
  const after = await api("/notify-prefs").catch(() => null);
  ok("⑩ 다시 켜기 저장됨", after?.ok && after.data.mission_done === true, JSON.stringify(after?.data));
  location.hash = "#home"; App.render(); await w(300);

  const f = R.filter((x) => x.v === "FAIL");
  return JSON.stringify({ 통과: R.length - f.length, 전체: R.length, 실패: f, 전부: R });
})();
