/**
 * OAuth 코어 — provider 에 무관한 부분 전부 (2026-07-27)
 *
 *   GET /auth/:provider/start?next=/dish_pizza     로그인 시작
 *   GET /auth/:provider/callback?code=..&state=..  콜백
 *   GET /auth/:provider/link?next=/mypage          로그인한 상태에서 계정 추가 연결 (3단계 UI)
 *
 * 🔴 redirect_uri 는 **apex 하나로 고정**한다(https://olmanama.com/...).
 *    콘솔 등록값과 한 글자라도 다르면 조용히 실패하는데, www/apex 를 둘 다 등록해두면
 *    어느 쪽으로 갈지 예측이 안 돼 디버깅이 지옥이 된다. www 로 들어오면 apex 로 넘긴다.
 */
import { redirect, err } from '../lib/resp.js';
import { getProvider } from '../providers/index.js';
import { randomToken, randomHex, sha256B64url, now, newId } from '../lib/ids.js';
import {
  createSession, currentUser, readCookie,
  OAUTH_COOKIE, oauthCookie, clearOauthCookie,
} from '../lib/session.js';

const ORIGIN = 'https://olmanama.com';
const STATE_TTL = 300;   // 5분

function redirectUriFor(providerId) {
  return `${ORIGIN}/auth/${providerId}/callback`;
}

/**
 * 로그인 후 돌아갈 경로. **우리 사이트 내부 경로만** 허용한다.
 * `//evil.com` 같은 값이 들어오면 오픈 리다이렉트가 되므로 걸러낸다.
 */
function safeNext(raw) {
  if (!raw || typeof raw !== 'string') return '/';
  if (!raw.startsWith('/') || raw.startsWith('//')) return '/';
  return raw;
}

/** 로그인 실패는 JSON 이 아니라 화면으로 보낸다 — 사용자가 보는 흐름이기 때문 */
function loginError(code) {
  return redirect(`${ORIGIN}/login?err=${encodeURIComponent(code)}`, [clearOauthCookie()]);
}

export async function handleAuth(request, env, path) {
  const m = path.match(/^\/auth\/([a-z]+)\/(start|callback|link)$/);
  if (!m) return null;                       // 우리 소관이 아니면 라우터가 404 를 낸다
  const [, providerId, action] = m;

  const provider = getProvider(providerId);
  if (!provider) return err('UNKNOWN_PROVIDER', '지원하지 않는 로그인 방식입니다.', 404);

  const url = new URL(request.url);

  // www 로 들어왔으면 apex 로 넘긴다 (redirect_uri 를 apex 로 고정했기 때문)
  if (url.hostname !== 'olmanama.com') {
    return redirect(ORIGIN + path + url.search);
  }

  if (action === 'start' || action === 'link') {
    return start(request, env, provider, url, action === 'link');
  }
  return callback(request, env, provider, url);
}

async function start(request, env, provider, url, isLink) {
  if (!env.KAKAO_REST_KEY && provider.id === 'kakao') {
    return err('MISSING_SECRETS', '카카오 REST 키가 설정되지 않았습니다.', 503);
  }

  // 계정 연결은 로그인한 상태에서만
  let linkUserId = null;
  if (isLink) {
    const me = await currentUser(env, request);
    if (!me) return loginError('LOGIN_REQUIRED');
    linkUserId = me.id;
  }

  const state = randomHex(16);
  const codeVerifier = provider.supportsPKCE ? randomToken(32) : null;
  const codeChallenge = codeVerifier ? await sha256B64url(codeVerifier) : null;

  await env.DB.prepare(
    `INSERT INTO oauth_state (state, provider, code_verifier, redirect_after, link_user_id, created_at, expires_at)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)`
  ).bind(
    state, provider.id, codeVerifier, safeNext(url.searchParams.get('next')),
    linkUserId, now(), now(STATE_TTL)
  ).run();

  const dest = provider.authorizeUrl(env, {
    state, codeChallenge, redirectUri: redirectUriFor(provider.id),
  });
  // state 사본을 쿠키에도 심는다(double-submit). DB 와 쿠키가 **둘 다** 맞아야 통과.
  return redirect(dest, [oauthCookie(state)]);
}

async function callback(request, env, provider, url) {
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  // 사용자가 카카오 동의 화면에서 '취소'를 누르면 code 없이 error 만 온다 — 실패가 아니라 취소다
  if (url.searchParams.get('error')) return loginError('CANCELED');
  if (!code || !state) return loginError('BAD_REQUEST');

  // ① 쿠키 사본 대조
  if (readCookie(request, OAUTH_COOKIE) !== state) return loginError('STATE_MISMATCH');

  // ② DB 대조 후 즉시 삭제 (1회용 — 재사용 공격 차단)
  const row = await env.DB.prepare(
    `SELECT * FROM oauth_state WHERE state = ?1 AND provider = ?2`
  ).bind(state, provider.id).first();
  await env.DB.prepare(`DELETE FROM oauth_state WHERE state = ?1`).bind(state).run();
  if (!row) return loginError('STATE_NOT_FOUND');
  if (row.expires_at <= now()) return loginError('STATE_EXPIRED');

  // ③ 토큰 교환 → 프로필
  let profile;
  try {
    const tokens = await provider.exchange(env, {
      code, codeVerifier: row.code_verifier, redirectUri: redirectUriFor(provider.id),
    });
    profile = await provider.profile(env, tokens);
  } catch (e) {
    console.error('oauth', provider.id, e && e.message);
    return loginError('PROVIDER_ERROR');
  }
  if (!profile || !profile.uid) return loginError('NO_PROFILE');

  // ④ 계정 찾기/만들기
  const userId = await resolveUser(env, provider.id, profile, row.link_user_id);
  if (!userId) return loginError('ALREADY_LINKED');

  // ⑤ 세션 발급
  const sessCookie = await createSession(env, userId, request);
  await env.DB.prepare(`UPDATE user SET last_login_at = ?1 WHERE id = ?2`)
    .bind(now(), userId).run();

  return redirect(ORIGIN + safeNext(row.redirect_after), [sessCookie, clearOauthCookie()]);
}

/**
 * identity → user 해결.
 *  · 이미 연결된 identity 면 그 회원으로 로그인
 *  · link 요청이면 현재 회원에 identity 를 붙인다 (이미 남의 계정에 붙어 있으면 거부)
 *  · 그 외에는 **새 회원을 만든다** — 같은 이메일이어도 병합하지 않는다(스키마 주석 참고)
 */
async function resolveUser(env, providerId, profile, linkUserId) {
  const existing = await env.DB.prepare(
    `SELECT user_id FROM oauth_identity WHERE provider = ?1 AND provider_uid = ?2`
  ).bind(providerId, profile.uid).first();

  if (linkUserId) {
    if (existing) return existing.user_id === linkUserId ? linkUserId : null;   // 남의 계정이면 거부
    await insertIdentity(env, providerId, profile, linkUserId);
    return linkUserId;
  }
  if (existing) return existing.user_id;

  const userId = newId('u');
  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO user (id, nickname, email, created_at, last_login_at) VALUES (?1, ?2, ?3, ?4, ?4)`
    ).bind(userId, profile.nickname, profile.email, now()),
    identityStmt(env, providerId, profile, userId),
  ]);
  return userId;
}

function identityStmt(env, providerId, profile, userId) {
  return env.DB.prepare(
    `INSERT INTO oauth_identity
       (provider, provider_uid, user_id, email_at_link, nickname_at_link, profile_json, linked_at)
     VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)`
  ).bind(
    providerId, profile.uid, userId, profile.email, profile.nickname,
    JSON.stringify(profile.raw || {}).slice(0, 4000), now()
  );
}

async function insertIdentity(env, providerId, profile, userId) {
  await identityStmt(env, providerId, profile, userId).run();
}
