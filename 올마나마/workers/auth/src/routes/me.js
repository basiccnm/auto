/**
 * /api/me · /api/logout (2026-07-27)
 *
 * 🔴 이 응답은 사람마다 다르다. 캐시되면 남의 로그인 상태가 새어나간다.
 *    캐시 헤더는 lib/resp.js 의 json()/err() 가 무조건 붙이므로 여기서 신경 쓸 게 없다 —
 *    **그게 resp.js 를 만든 이유다.** 이 파일에서 new Response() 를 쓰지 말 것.
 */
import { json } from '../lib/resp.js';
import { currentUser, revokeSession } from '../lib/session.js';
import { providerIds } from '../providers/index.js';

/** GET /api/me → 로그인 상태. 비로그인도 200 이다(에러가 아니라 정상 상태다) */
export async function handleMe(request, env) {
  const me = await currentUser(env, request);
  if (!me) return json({ login: false, providers: providerIds() });

  const ids = await env.DB.prepare(
    `SELECT provider FROM oauth_identity WHERE user_id = ?1`
  ).bind(me.id).all();

  return json({
    login: true,
    user: { id: me.id, nickname: me.nickname, email: me.email, role: me.role },
    linked: (ids.results || []).map((r) => r.provider),
    providers: providerIds(),
  });
}

/** POST /api/logout — GET 로 열지 않는다(링크 프리페치·CSRF 로 남이 로그아웃시킬 수 있다) */
export async function handleLogout(request, env) {
  const clear = await revokeSession(env, request);
  return json({ login: false }, 200, { 'Set-Cookie': clear });
}
