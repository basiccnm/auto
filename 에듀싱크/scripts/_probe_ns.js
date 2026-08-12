(async () => {
  const w=(ms)=>new Promise(r=>setTimeout(r,ms));
  // 로그인 안 돼 있으면 시험 계정으로 (검수 환경 — STATUS ④)
  if(!localStorage.getItem("eduthink.tokens")){
    const r = await api("/auth/login", { method:"POST", body:{ login_id:"ph5126", password:"testpass123", device_label:"검수-에뮬" } });
    if(!r?.ok) return "로그인 실패: "+JSON.stringify(r).slice(0,120);
    saveTokens(r.data);
    localStorage.setItem("devDate","20260518");   // 방학이라 5월로 (출시 전 제거 — check_release 가 잡는다)
    location.reload(); return "로그인됨 — 새로고침";
  }
  location.hash="#home"; if(window.App&&App.render){App.render();} await w(2500);
  const out={size:[innerWidth,innerHeight], login:!!document.querySelector(".ns-home")};
  const home=document.querySelector(".ns-home");
  if(!home){ out.state=(document.body.textContent||"").replace(/\s+/g," ").slice(0,60); return JSON.stringify(out); }
  const scr=document.getElementById("screen");
  out.overX=scr.scrollWidth-scr.clientWidth;
  out.overY=Math.max(0,scr.scrollHeight-innerHeight);
  const now=document.querySelector(".ns-now");
  if(now){ out.nowBg=getComputedStyle(now).backgroundColor;
    const t=document.querySelector(".ns-clock .t");
    if(t) out.clockPx=Math.round(parseFloat(getComputedStyle(t).fontSize)); }
  const c=document.querySelector(".ns-row .ns-c");
  if(c){const r=c.getBoundingClientRect(); out.chip=`${Math.round(r.width)}x${Math.round(r.height)}`;}
  const bar=document.querySelector(".ns-bar");
  if(bar) out.barB=Math.round(innerHeight-bar.getBoundingClientRect().bottom);
  const row=document.querySelector(".ns-row");
  if(row) out.rowH=Math.round(row.getBoundingClientRect().height);
  return JSON.stringify(out);
})();
