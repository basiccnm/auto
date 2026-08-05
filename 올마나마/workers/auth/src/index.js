/**
 * olmanama-auth — 회원·잔액·충전 워커 (2026-07-27 신설, 2단계)
 *
 * 이 워커는 olmanama.com 의 /api/* 와 /auth/* 만 받는다. 943개 정적 페이지는
 * 별도 워커 eolmanama-site-renderer 가 서빙하며, 이 파일은 거기에 관여하지 않는다.
 *
 * 2단계 범위: 카카오 로그인 왕복 + 세션 + /api/me
 * 다음: 구글·네이버(3단계) · /api/spend·/api/wallet(4단계) · /api/charge(5단계)
 */
import { json, err, notFound } from './lib/resp.js';
import { handleAuth } from './routes/auth.js';
import { handleMe, handleLogout } from './routes/me.js';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // ── 🔴 안전망: 우리 몫이 아닌 경로는 원본으로 흘려보낸다 ──────────────
    //  routes 패턴을 `olmanama.com/*` 로 잘못 쓰면 이 워커가 943페이지를 전부 받게 된다.
    //  그때 404 를 주면 **사이트가 전멸한다.** 대신 fetch(request) 로 넘기면
    //  Custom Domain 워커(site-renderer)가 origin 으로 취급되어 정상 페이지가 나간다.
    //  → 설정 실수가 장애가 아니라 "그냥 아무 일도 안 일어남"이 된다.
    if (!path.startsWith('/api/') && !path.startsWith('/auth/')) {
      return fetch(request);
    }

    try {
      if (path === '/api/health') return health(request, env);

      if (path.startsWith('/auth/')) {
        const r = await handleAuth(request, env, path);
        if (r) return r;
        return notFound();
      }

      if (path === '/api/me') return handleMe(request, env);
      if (path === '/api/logout') {
        // GET 으로 열지 않는다 — 링크 프리페치나 <img> 로 남이 로그아웃시킬 수 있다
        if (request.method !== 'POST') return err('METHOD', 'POST 로 요청하세요.', 405);
        return handleLogout(request, env);
      }

      return notFound();
    } catch (e) {
      // 스택을 밖으로 내보내지 않는다. 원인은 `wrangler tail --config workers/auth/wrangler.toml` 로 본다.
      console.error('unhandled', path, e && e.stack ? e.stack : String(e));
      return err('INTERNAL', '서버 오류입니다.', 500);
    }
  },
};

/**
 * 단계별 필수 시크릿. 배포 후 이게 비어 있으면 로그인 클릭 시 500 이 나는데
 * 원인을 찾기 어렵다. 그래서 health 가 **미리** 알려준다.
 * 3단계에서 GOOGLE_CLIENT_ID/SECRET · NAVER_LOGIN_CLIENT_ID/SECRET 을 추가한다.
 */
const REQUIRED = ['KAKAO_REST_KEY'];

/** GET /api/health — 시크릿이 빠졌으면 503 으로 내려서 deploy_auth.py 가 잡아낸다 */
async function health(request, env) {
  const missing = REQUIRED.filter((k) => !env[k]);
  const body = { worker: 'olmanama-auth', stage: 2, missing, db: 'unknown', now: new Date().toISOString() };

  // D1 바인딩이 실제로 붙었는지도 확인한다 (설정만 하고 마이그레이션을 안 돌린 상태를 잡는다)
  try {
    const r = await env.DB.prepare(`SELECT COUNT(*) AS n FROM user`).first();
    body.db = 'ok';
    body.users = r ? r.n : null;
  } catch (e) {
    body.db = 'error: ' + String(e && e.message).slice(0, 120);
  }

  if (missing.length || body.db !== 'ok') {
    return err('NOT_READY', '워커가 아직 준비되지 않았습니다.', 503, body);
  }
  return json(body);
}
