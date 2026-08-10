(async () => {
  try {
    const t0 = Date.now();
    const res = await fetch("https://eduthink-site-renderer.dndmotor1.workers.dev/api/v1/health", { method: "GET" });
    return JSON.stringify({ status: res.status, ms: Date.now() - t0 });
  } catch (e) { return "fetch 실패: " + (e && e.message); }
})();
