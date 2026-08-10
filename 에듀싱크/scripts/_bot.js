(async () => {
  const w=(ms)=>new Promise(r=>setTimeout(r,ms));
  if (!TOKENS.access) return "🔴 로그인 풀림";
  if (!(STUB.children||[]).length) await loadMe();
  localStorage.setItem("eduthink.coachSeen","1"); S.coach=null;
  localStorage.setItem("eduthink.coachMission","1"); S.msCoach=null;
  const SC = ["home","mission","missionpick","store","tickets","meal","timetable","calendar","timeline","mypage","pay","notify","afterschool","report","docs","community"];
  const out = [];
  const cs = getComputedStyle(document.documentElement);
  out.push("sa " + cs.getPropertyValue("--sa-t").trim() + "/" + cs.getPropertyValue("--sa-b").trim());
  for (const s of SC) {
    location.hash = "#" + s; App.render(); await w(2600);
    const scr = document.getElementById("screen");
    // 화면 맨 아래 요소 — 스크롤 끝까지 내려서 잰다
    window.scrollTo(0, document.body.scrollHeight); await w(300);
    const kids = [...scr.querySelectorAll("*")].filter((e) => e.offsetHeight > 20 && getComputedStyle(e).position !== "fixed");
    let low = 0, name = "";
    for (const e of kids) { const r = e.getBoundingClientRect(); if (r.bottom > low && r.bottom < innerHeight + 400) { low = r.bottom; name = (e.className||e.tagName).toString().slice(0,16); } }
    const gap = Math.round(innerHeight - low);
    // 화면 맨 위 첫 글자가 상태바 안으로 들어갔나
    const h = scr.querySelector("h1,h2,.sub-t,.hd-top,.gmp-top,.hv3-ham");
    const top = h ? Math.round(h.getBoundingClientRect().top) : -999;
    // 상태바 자리 색 (y=4 에서 무엇이 칠하나)
    const bodyBg = getComputedStyle(document.body).backgroundColor;
    out.push(`${s} | 아래여백 ${gap}px ${gap < 48 ? "🔴" : "✅"} (${name}) | 첫요소top ${top}px ${top < 36 ? "🔴" : "✅"} | body ${bodyBg}`);
  }
  return out.join(String.fromCharCode(10));
})();
