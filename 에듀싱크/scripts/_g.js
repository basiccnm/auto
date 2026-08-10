(async () => { const w=(ms)=>new Promise(r=>setTimeout(r,ms)); await w(3000);
  if (!TOKENS.access) return "🔴 로그인풀림"; if(!(STUB.children||[]).length) await loadMe();
  localStorage.setItem("eduthink.coachSeen","1"); S.coach=null;
  localStorage.setItem("eduthink.coachMission","1"); S.msCoach=null;
  location.hash="#mission"; App.render(); await w(1300); return "ok"; })();
