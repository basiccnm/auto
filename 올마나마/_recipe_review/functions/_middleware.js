// 레시피 리뷰 뷰어 — 전 페이지에 HTTP Basic Auth를 건다.
// wtable 원본을 그대로 보여주는 검토용이라 검색엔진·타인 접근을 막아야 한다.
export async function onRequest({ request, env, next }) {
  const auth = request.headers.get("Authorization");
  const user = env.REVIEW_USER;
  const pass = env.REVIEW_PASS;

  if (auth) {
    const [scheme, encoded] = auth.split(" ");
    if (scheme === "Basic" && encoded) {
      const decoded = atob(encoded);
      const idx = decoded.indexOf(":");
      const u = decoded.slice(0, idx);
      const p = decoded.slice(idx + 1);
      if (u === user && p === pass) {
        return next();
      }
    }
  }

  return new Response("Auth required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="recipe-review"' },
  });
}
