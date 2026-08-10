(async () => {
  const w=(ms)=>new Promise(r=>setTimeout(r,ms));
  document.documentElement.style.background = "red";
  await w(600);
  return "html=red 칠함, innerH=" + innerHeight + " screenH=" + screen.height + " dpr=" + devicePixelRatio;
})();
