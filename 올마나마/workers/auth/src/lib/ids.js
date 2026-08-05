/** ID·해시·시각 — 워커 전역에서 이것만 쓴다 (2026-07-27) */

const HEX = '0123456789abcdef';

/** 암호학적 난수 hex 문자열 (n바이트 → 2n자) */
export function randomHex(bytes = 16) {
  const b = crypto.getRandomValues(new Uint8Array(bytes));
  let s = '';
  for (const x of b) s += HEX[x >> 4] + HEX[x & 15];
  return s;
}

/** URL-safe base64 (PKCE·세션 토큰용) */
export function randomToken(bytes = 32) {
  const b = crypto.getRandomValues(new Uint8Array(bytes));
  return b64url(b);
}

export function b64url(bytes) {
  let s = '';
  for (const x of bytes) s += String.fromCharCode(x);
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/** sha256 → hex. 세션 토큰을 DB에 넣기 전에 반드시 통과시킨다 */
export async function sha256Hex(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  let s = '';
  for (const x of new Uint8Array(buf)) s += HEX[x >> 4] + HEX[x & 15];
  return s;
}

/** sha256 → base64url. PKCE code_challenge(S256) 형식 */
export async function sha256B64url(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return b64url(new Uint8Array(buf));
}

/**
 * 시각 문자열 — 🔴 워커의 모든 시각은 이 함수로만 만든다.
 * UTC ISO8601 + 'Z'. admin_store.py 의 KST 로컬시각과 섞이면 9시간 어긋난 채 굴러가므로
 * 'Z' 가 붙어 있는 것 자체가 "이건 UTC다"라는 표시다.
 */
export function now(offsetSeconds = 0) {
  return new Date(Date.now() + offsetSeconds * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z');
}

/** 접두어 + 랜덤 — u_xxxx 처럼 눈으로 종류가 구분되는 id */
export function newId(prefix, bytes = 12) {
  return prefix + '_' + randomHex(bytes);
}
