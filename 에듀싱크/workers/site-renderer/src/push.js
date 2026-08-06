// 웹푸시(Web Push) — VAPID 서명 + 무페이로드(tickle) 발송. 서비스워커가 고정 문구 알림 표시.
// 페이로드 암호화(aes128gcm)는 1차 범위 밖 — 무페이로드 푸시로 SW가 기본 문구를 띄운다.

function b64urlToU8(s) {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  const bin = atob(s);
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}
function u8ToB64url(u) {
  let bin = "";
  for (let i = 0; i < u.length; i++) bin += String.fromCharCode(u[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function importVapidKey(privateB64, publicB64) {
  const priv = b64urlToU8(privateB64);
  const pub = b64urlToU8(publicB64); // 65바이트 비압축(0x04||x||y)
  const jwk = {
    kty: "EC", crv: "P-256",
    x: u8ToB64url(pub.slice(1, 33)),
    y: u8ToB64url(pub.slice(33, 65)),
    d: u8ToB64url(priv),
    ext: true,
  };
  return crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
}

async function signVapidJwt(key, aud, sub) {
  const enc = (o) => u8ToB64url(new TextEncoder().encode(JSON.stringify(o)));
  const input = enc({ typ: "JWT", alg: "ES256" }) + "." + enc({ aud, exp: Math.floor(Date.now() / 1000) + 12 * 3600, sub });
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, new TextEncoder().encode(input));
  return input + "." + u8ToB64url(new Uint8Array(sig)); // ES256 서명은 raw r||s → 그대로 JWS
}

// 구독 하나에 무페이로드 푸시 발송. 반환: HTTP status(201=수락, 404/410=만료).
export async function sendPush(subscription, env) {
  const aud = new URL(subscription.endpoint).origin;
  const key = await importVapidKey(env.VAPID_PRIVATE, env.VAPID_PUBLIC);
  const jwt = await signVapidJwt(key, aud, env.VAPID_SUBJECT || "mailto:admin@example.com");
  const res = await fetch(subscription.endpoint, {
    method: "POST",
    headers: {
      TTL: "86400",
      Authorization: `vapid t=${jwt}, k=${env.VAPID_PUBLIC}`,
    },
  });
  return res.status;
}
