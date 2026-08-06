// ================= 계정·인증 모듈 (정본 §8 공통 블록) =================
// 계약: docs/API계약-v1.md §2·§3
//
// 도메인에 안 묶인다 — 에듀싱크·올마나마·B2B가 같은 부품을 쓴다(정본 원칙1).
// 여기엔 "학교"도 "자녀"도 없다. 계정·로그인수단·토큰만 다룬다.
//
// 왜 외부 라이브러리를 안 쓰나: Cloudflare Workers는 Node 런타임이 아니라 bcrypt·jsonwebtoken이
// 그대로 안 돈다. Web Crypto가 표준으로 들어 있어 그걸로 충분하다(의존성 0).

// ── 유틸 ─────────────────────────────────────────────────────
const enc = new TextEncoder();

function b64urlFromBytes(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlToBytes(str) {
  const s = str.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((str.length + 3) % 4);
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
function b64urlJson(obj) {
  return b64urlFromBytes(enc.encode(JSON.stringify(obj)));
}
// 타이밍 공격 방지 — 길이가 달라도 조기 반환하지 않는다.
function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// ── 비밀번호 해시 (PBKDF2-SHA256) ────────────────────────────
// bcrypt가 없어서 PBKDF2를 쓴다. Workers CPU 시간 제한이 있어 반복을 무한정 못 올린다.
// 10만 회는 요청당 수십 ms 수준이라 무료 플랜 CPU 한도(10ms→유료 30s) 안에서 안전하다.
const PBKDF2_ITER = 100000;

export async function hashPassword(password) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: PBKDF2_ITER, hash: "SHA-256" }, key, 256
  );
  // 형식: pbkdf2$반복수$솔트$해시 — 나중에 반복수를 올려도 옛 해시를 계속 검증할 수 있다.
  return `pbkdf2$${PBKDF2_ITER}$${b64urlFromBytes(salt)}$${b64urlFromBytes(new Uint8Array(bits))}`;
}

export async function verifyPassword(password, stored) {
  if (!stored || !stored.startsWith("pbkdf2$")) return false;
  const [, iterStr, saltB64, hashB64] = stored.split("$");
  const iter = parseInt(iterStr, 10);
  if (!(iter > 0)) return false;
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: b64urlToBytes(saltB64), iterations: iter, hash: "SHA-256" }, key, 256
  );
  return timingSafeEqual(b64urlFromBytes(new Uint8Array(bits)), hashB64);
}

// ── 토큰 (HMAC-SHA256 서명, JWT 형식) ────────────────────────
// 계약 §3.1 — access 30분 / refresh 90일 / reauth 5분.
// 무상태라 Workers와 궁합이 좋다. 대신 "이 토큰 그만"을 말하려면 revoked_tokens가 필요하다.
export const TOKEN_TTL = { access: 30 * 60, refresh: 90 * 86400, reauth: 5 * 60 };

async function hmacKey(secret) {
  return crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

export async function signToken(payload, secret, ttlSec) {
  const now = Math.floor(Date.now() / 1000);
  const body = { ...payload, iat: now, exp: now + ttlSec, jti: crypto.randomUUID() };
  const head = b64urlJson({ alg: "HS256", typ: "JWT" });
  const data = `${head}.${b64urlJson(body)}`;
  const sig = await crypto.subtle.sign("HMAC", await hmacKey(secret), enc.encode(data));
  return `${data}.${b64urlFromBytes(new Uint8Array(sig))}`;
}

// 반환: { ok:true, payload } | { ok:false, reason:"invalid"|"expired" }
// 만료와 위조를 구분해서 돌려준다 — 앱이 "refresh 시도"와 "로그아웃"을 갈라야 하기 때문.
export async function verifyToken(token, secret) {
  if (!token || typeof token !== "string") return { ok: false, reason: "invalid" };
  const parts = token.split(".");
  if (parts.length !== 3) return { ok: false, reason: "invalid" };
  const [head, body, sig] = parts;
  let valid;
  try {
    valid = await crypto.subtle.verify("HMAC", await hmacKey(secret), b64urlToBytes(sig), enc.encode(`${head}.${body}`));
  } catch (_) {
    return { ok: false, reason: "invalid" };
  }
  if (!valid) return { ok: false, reason: "invalid" };
  let payload;
  try {
    payload = JSON.parse(new TextDecoder().decode(b64urlToBytes(body)));
  } catch (_) {
    return { ok: false, reason: "invalid" };
  }
  if (!payload.exp || payload.exp < Math.floor(Date.now() / 1000)) return { ok: false, reason: "expired" };
  return { ok: true, payload };
}

// 토큰 서명 비밀키.
//   로컬: .dev.vars 의 AUTH_SECRET
//   운영: wrangler secret put AUTH_SECRET
//
// 🔒 없으면 **거부한다**(2026-07-25). 예전엔 코드에 박힌 개발용 키로 조용히 넘어갔는데,
//    그 상태로 배포되면 그 키를 아는 사람이 **아무 계정의 토큰이나 위조**할 수 있다.
//    조용히 약해지느니 로그인이 안 되는 게 낫다 — 빠뜨린 걸 바로 알 수 있다.
export function authSecret(env) {
  const s = env && env.AUTH_SECRET;
  if (s && String(s).length >= 32) return s;
  throw new Error(
    "AUTH_SECRET 없음(또는 32자 미만) — 로컬은 .dev.vars, 운영은 `npx wrangler secret put AUTH_SECRET`."
  );
}

// ── 계정 조회·생성 ───────────────────────────────────────────
export async function findAccountById(db, accountId) {
  return db.prepare("SELECT * FROM accounts WHERE id = ? AND status = 'active'").bind(accountId).first();
}

export async function findAccountByToken(db, ownerToken) {
  if (!ownerToken) return null;
  return db.prepare("SELECT * FROM accounts WHERE owner_token = ? AND status = 'active'").bind(ownerToken).first();
}

// 로그인 수단으로 계정 찾기. kind+identifier가 UNIQUE라 한 건만 나온다.
export async function findAccountByAuth(db, kind, identifier) {
  return db
    .prepare(
      `SELECT a.* FROM accounts a JOIN auth_methods m ON m.account_id = a.id
       WHERE m.kind = ? AND m.identifier = ? AND a.status = 'active'`
    )
    .bind(kind, identifier)
    .first();
}

// 계정 생성 — owner_token을 받으면 그걸 승계한다(기존 쿠키 사용자의 자녀·기록이 딸려온다).
// 이게 정본 §4 "무손실 승계"의 실체다. 새 토큰을 만들면 그 사람의 기존 데이터가 끊긴다.
export async function createAccount(db, { ownerToken, displayName, email, phone, birthYmd }) {
  const token = ownerToken || crypto.randomUUID();
  const now = new Date().toISOString();
  const r = await db
    .prepare(
      `INSERT INTO accounts (owner_token, display_name, email, phone, phone_verified, birth_ymd, status, created_at, last_login_at)
       VALUES (?, ?, ?, ?, 0, ?, 'active', ?, ?)`
    )
    .bind(token, displayName || null, email || null, phone || null, birthYmd || null, now, now)
    .run();
  return { id: r.meta.last_row_id, owner_token: token };
}

export async function addAuthMethod(db, accountId, kind, identifier, secret = null, verified = 0) {
  const now = new Date().toISOString();
  await db
    .prepare(
      `INSERT OR IGNORE INTO auth_methods (account_id, kind, identifier, secret, verified, created_at, last_used_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(accountId, kind, identifier, secret, verified, now, now)
    .run();
}

export async function touchLogin(db, accountId, kind = null, identifier = null) {
  const now = new Date().toISOString();
  await db.prepare("UPDATE accounts SET last_login_at = ? WHERE id = ?").bind(now, accountId).run();
  if (kind && identifier) {
    await db.prepare("UPDATE auth_methods SET last_used_at = ? WHERE kind = ? AND identifier = ?")
      .bind(now, kind, identifier).run();
  }
}

// ── 토큰 폐기 ────────────────────────────────────────────────
export async function revokeToken(db, jti, accountId, expEpoch) {
  await db
    .prepare("INSERT OR IGNORE INTO revoked_tokens (jti, account_id, expires_at, revoked_at) VALUES (?, ?, ?, ?)")
    .bind(jti, accountId || null, new Date(expEpoch * 1000).toISOString(), new Date().toISOString())
    .run();
}
export async function isRevoked(db, jti) {
  if (!jti) return false;
  const r = await db.prepare("SELECT 1 AS x FROM revoked_tokens WHERE jti = ?").bind(jti).first();
  return !!r;
}

// ── 요청에서 인증 주체 꺼내기 (계약 §1.4) ───────────────────
// 판정 순서: Authorization 헤더 → 없으면 쿠키.
// 전환기 동안 앱(토큰)과 웹(쿠키)이 같은 API를 쓴다.
// 반환: { account, ownerToken, via:"token"|"cookie"|null, error:null|"AUTH_EXPIRED"|"AUTH_INVALID" }
export async function resolveAuth(request, db, env, getCookieFn) {
  const header = request.headers.get("Authorization") || "";
  if (header.startsWith("Bearer ")) {
    const v = await verifyToken(header.slice(7).trim(), authSecret(env));
    if (!v.ok) {
      return { account: null, ownerToken: null, via: null, error: v.reason === "expired" ? "AUTH_EXPIRED" : "AUTH_INVALID" };
    }
    if (v.payload.typ !== "access") {
      return { account: null, ownerToken: null, via: null, error: "AUTH_INVALID" };
    }
    if (await isRevoked(db, v.payload.jti)) {
      return { account: null, ownerToken: null, via: null, error: "AUTH_INVALID" };
    }
    const account = await findAccountById(db, v.payload.sub);
    if (!account) return { account: null, ownerToken: null, via: null, error: "AUTH_INVALID" };
    /* 🔒 자녀 기기는 **1명당 1대**(2026-07-31 지시). 토큰의 기기 표식이 지금 등록된 것과 다르면
       («새 코드로 다른 폰이 붙었다») 옛 폰은 여기서 끊는다.
       ⚠ 옛 토큰(dev 없음)은 통과시킨다 — 이미 쓰고 있는 아이 폰이 갑자기 죽으면 안 된다.
          다음에 코드를 다시 받으면 그때부터 1대 규칙에 들어온다. */
    if (v.payload.role === "child" && v.payload.dev && v.payload.chd) {
      const c = await db.prepare("SELECT child_device FROM children WHERE id = ?").bind(v.payload.chd).first();
      // 표식이 다르거나(다른 폰이 붙음) **비어 있으면**(부모가 연결 끊음) 막는다
      if (!c || c.child_device !== v.payload.dev) {
        return { account: null, ownerToken: null, via: null, error: "AUTH_INVALID" };
      }
    }
    /* 🔒 부모 기기는 **2대까지**(2026-08-01 — 엄마·아빠가 각자 폰에서 본다).
       3번째가 로그인하면 가장 오래 안 쓴 기기가 표에서 지워지고, 그 폰은 여기서 끊긴다.
       ⚠ 옛 토큰(dev 없음)은 통과시킨다 — 이미 쓰던 사람이 갑자기 튕기면 안 된다.
          다음 로그인부터 2대 규칙에 들어온다. */
    if (v.payload.role !== "child" && v.payload.dev) {
      const d = await db.prepare("SELECT id FROM account_devices WHERE id = ? AND account_id = ?")
        .bind(v.payload.dev, account.id).first();
      if (!d) return { account: null, ownerToken: null, via: null, error: "AUTH_INVALID" };
    }
    // 자녀 기기 토큰(2026-07-25) — 같은 계정의 데이터를 보지만 **권한이 좁다**.
    // role/childId를 끝까지 들고 가서 index.js가 허용 경로만 통과시킨다.
    // 여기서 안 넘기면 자녀 폰이 부모 권한을 그대로 갖게 된다.
    return {
      account, ownerToken: account.owner_token, via: "token", error: null,
      role: v.payload.role === "child" ? "child" : "parent",
      childId: v.payload.chd || null,
      deviceId: v.payload.dev || null,   // 내 정보에서 «지금 이 폰»을 표시하는 데 쓴다
    };
  }

  // 웹 폴백 — 쿠키. 계정이 아직 없는 익명 사용자도 owner_token만으로 자기 데이터를 본다.
  const cookieToken = getCookieFn ? getCookieFn(request, "owner_token") : null;
  if (!cookieToken) return { account: null, ownerToken: null, via: null, error: null };
  const account = await findAccountByToken(db, cookieToken);
  return { account, ownerToken: cookieToken, via: "cookie", error: null, role: "parent", childId: null };
}

// 재인증(step-up) 검증 — 계약 §3.4.
// 수정·삭제처럼 되돌리기 어려운 요청에만 요구한다. 업로드엔 안 건다(정본 §0 "넣는 데 30초").
export async function verifyReauth(request, env, accountId) {
  const t = request.headers.get("X-Reauth-Token") || "";
  if (!t) return false;
  const v = await verifyToken(t, authSecret(env));
  return !!(v.ok && v.payload.typ === "reauth" && String(v.payload.sub) === String(accountId));
}
