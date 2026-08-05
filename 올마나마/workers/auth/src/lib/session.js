/**
 * 세션 — 쿠키 발급·검증·폐기 (2026-07-27)
 *
 * 쿠키:  __Secure-olma_sess=<랜덤32B base64url>; Domain=olmanama.com; Path=/;
 *        Secure; HttpOnly; SameSite=Lax; Max-Age=30일
 *
 * ★ 왜 __Host- 가 아니라 __Secure- 인가
 *   __Host- 는 Domain 지정을 **금지**한다. 이 사이트는 apex 와 www 를 둘 다 서빙하므로
 *   Domain=olmanama.com 이 필요하다(www 에서 로그인해도 apex 콜백의 쿠키가 유효해야 함).
 *
 * ★ 왜 SameSite=Lax 인가
 *   OAuth 콜백은 카카오 쪽에서 넘어오는 top-level GET 네비게이션이다. Lax 에서는 쿠키가 실리고
 *   Strict 에서는 안 실린다 → Strict 면 콜백 직후 로그인 상태가 안 보여 새로고침을 한 번 더 해야 한다.
 *
 * ★ 왜 DB에 해시만 저장하나
 *   D1 이 통째로 유출돼도 세션을 훔칠 수 없다. 쿠키 원문은 브라우저에만 있다.
 */
import { randomToken, sha256Hex, now } from './ids.js';

export const SESS_COOKIE = '__Secure-olma_sess';
export const OAUTH_COOKIE = '__Secure-olma_oauth';
const SESS_DAYS = 30;
const COOKIE_DOMAIN = 'olmanama.com';

/** 요청 헤더에서 쿠키 하나 꺼내기 */
export function readCookie(request, name) {
  const raw = request.headers.get('Cookie') || '';
  for (const part of raw.split(';')) {
    const i = part.indexOf('=');
    if (i < 0) continue;
    if (part.slice(0, i).trim() === name) return decodeURIComponent(part.slice(i + 1).trim());
  }
  return null;
}

function cookie(name, value, maxAge, extra = '') {
  // ⚠️ 로컬 wrangler dev(http)에서는 Secure 쿠키가 저장되지 않는다.
  //    로컬 확인은 `wrangler dev --local-protocol https` 로 할 것.
  return `${name}=${encodeURIComponent(value)}; Domain=${COOKIE_DOMAIN}; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${extra}`;
}

/** 세션 생성 → [쿠키문자열] 반환. 호출부가 redirect() 에 실어 보낸다 */
export async function createSession(env, userId, request) {
  const token = randomToken(32);
  const id = await sha256Hex(token);
  const ua = request.headers.get('User-Agent') || '';
  await env.DB.prepare(
    `INSERT INTO session (id, user_id, created_at, expires_at, last_seen_at, ua_hash, ip_first)
     VALUES (?1, ?2, ?3, ?4, ?3, ?5, ?6)`
  ).bind(
    id, userId, now(), now(SESS_DAYS * 86400),
    (await sha256Hex(ua)).slice(0, 16),
    request.headers.get('CF-Connecting-IP') || ''
  ).run();
  return cookie(SESS_COOKIE, token, SESS_DAYS * 86400);
}

/**
 * 현재 로그인 사용자 — 없으면 null.
 * 만료·폐기·탈퇴를 모두 확인한다.
 */
export async function currentUser(env, request) {
  const token = readCookie(request, SESS_COOKIE);
  if (!token) return null;
  const id = await sha256Hex(token);
  const row = await env.DB.prepare(
    `SELECT s.id AS sid, s.expires_at, s.last_seen_at,
            u.id, u.nickname, u.email, u.role, u.status
       FROM session s JOIN user u ON u.id = s.user_id
      WHERE s.id = ?1 AND s.revoked_at IS NULL`
  ).bind(id).first();
  if (!row) return null;
  if (row.expires_at <= now()) return null;          // 문자열 비교로 충분 — ISO8601 은 사전순 = 시간순
  if (row.status !== 'active') return null;

  // last_seen_at 은 하루 1회만 갱신한다. 매 요청 UPDATE 하면 D1 쓰기 요금과 경합이 붙는다.
  if (!row.last_seen_at || row.last_seen_at < now(-86400)) {
    await env.DB.prepare(`UPDATE session SET last_seen_at = ?1 WHERE id = ?2`)
      .bind(now(), row.sid).run();
  }
  return { id: row.id, nickname: row.nickname, email: row.email, role: row.role, sid: row.sid };
}

/** 로그아웃 — 해당 세션만 무효화 */
export async function revokeSession(env, request) {
  const token = readCookie(request, SESS_COOKIE);
  if (token) {
    await env.DB.prepare(`UPDATE session SET revoked_at = ?1 WHERE id = ?2 AND revoked_at IS NULL`)
      .bind(now(), await sha256Hex(token)).run();
  }
  return cookie(SESS_COOKIE, '', 0);
}

/** OAuth 왕복용 단기 쿠키 (state double-submit) */
export function oauthCookie(state) {
  return cookie(OAUTH_COOKIE, state, 600);
}
export function clearOauthCookie() {
  return cookie(OAUTH_COOKIE, '', 0);
}
