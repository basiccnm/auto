(async () => {
  try {
    const c = new AbortController(); setTimeout(() => c.abort(), 8000);
    const res = await fetch("https://eduthink-site-renderer.dndmotor1.workers.dev/api/v1/health", { signal: c.signal });
    return "status=" + res.status;
  } catch (e) { return "fetch 실패: " + (e && (e.name + " " + e.message)); }
})();
