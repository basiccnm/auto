/**
 * 응답 생성 — 이 파일 밖에서 `new Response()` 를 쓰지 않는다. (2026-07-27 신설)
 *
 * ★ 왜 한 곳으로 모으나
 *   /api/me 같은 응답에 캐시 헤더를 한 번이라도 빠뜨리면 Cloudflare 엣지가
 *   **A 의 로그인 상태·잔액을 B 에게 그대로 준다.** 라우트가 20개로 늘면 언젠가 빠뜨린다.
 *   그래서 "안 빠뜨리게 조심한다"가 아니라 **구조적으로 빠뜨릴 수 없게** 만든다.
 *
 *   같은 이유로 이 프로젝트는 전역 태그를 theme.py 의 HEAD_TAGS 한 곳에 모아뒀다.
 *   (여러 곳에 흩어놓았다가 2026-07-21 오배포 사고를 냈다)
 *
 * 규칙: 라우트 핸들러는 json()/err()/redirect() 만 쓴다.
 */

/** 모든 응답에 무조건 붙는 헤더 */
function baseHeaders(extra) {
  return {
    // 🔴 private: 엣지·프록시가 절대 공유 캐시에 담지 않는다
    //    no-store:  브라우저 뒤로가기 캐시에도 안 남긴다
    'Cache-Control': 'private, no-store, max-age=0',
    // 쿠키가 다르면 다른 응답이라는 표시. no-store 와 중복이지만 방어를 겹쳐 둔다
    'Vary': 'Cookie',
    // 이 워커의 응답은 전부 API·리다이렉트다. 검색엔진에 잡힐 이유가 없다
    'X-Robots-Tag': 'noindex, nofollow',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    ...extra,
  };
}

/** 성공 응답 — admin_server.py 의 {"ok": true, ...} 규약을 그대로 따른다 */
export function json(data, status = 200, extra) {
  return new Response(JSON.stringify({ ok: true, ...data }), {
    status,
    headers: baseHeaders({ 'Content-Type': 'application/json; charset=utf-8', ...extra }),
  });
}

/**
 * 실패 응답 — {"ok": false, "code": "...", "error": "..."}
 *   code  = 프로그램이 분기하는 값 (INSUFFICIENT 등). 절대 문구를 보고 분기하지 말 것
 *   error = 사람이 읽는 한국어 문구
 */
export function err(code, message, status = 400, extra) {
  return new Response(JSON.stringify({ ok: false, code, error: message, ...extra }), {
    status,
    headers: baseHeaders({ 'Content-Type': 'application/json; charset=utf-8' }),
  });
}

/** 리다이렉트 — OAuth 왕복에서 쓴다. 쿠키를 함께 실을 수 있다 */
export function redirect(location, cookies = []) {
  const h = baseHeaders({ Location: location });
  const r = new Response(null, { status: 302, headers: h });
  for (const c of cookies) r.headers.append('Set-Cookie', c);
  return r;
}

/** 이 워커가 받을 이유가 없는 경로 — 존재 여부를 알려주지 않는다 */
export function notFound() {
  return err('NOT_FOUND', '없는 경로입니다.', 404);
}
