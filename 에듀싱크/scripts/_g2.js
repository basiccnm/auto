(async () => { const w=(ms)=>new Promise(r=>setTimeout(r,ms));
  location.hash="#home"; App.render(); await w(1300); return "ok"; })();
