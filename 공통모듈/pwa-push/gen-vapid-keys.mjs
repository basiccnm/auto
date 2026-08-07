// VAPID 키쌍 생성 — push.js가 기대하는 형식(공개키 65바이트 비압축, 개인키 32바이트 d, 둘 다 base64url).
// 실행: node gen-vapid-keys.mjs
// 출력된 키를: VAPID_PUBLIC → wrangler.toml [vars] 또는 secret, VAPID_PRIVATE → 반드시 `wrangler secret put VAPID_PRIVATE`
import crypto from "node:crypto";

const ecdh = crypto.createECDH("prime256v1");
ecdh.generateKeys();

const b64url = (buf) => buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

const pub = ecdh.getPublicKey();   // 65바이트 비압축(0x04||x||y)
const priv = ecdh.getPrivateKey(); // 32바이트 d

if (pub.length !== 65 || pub[0] !== 0x04) throw new Error("공개키 형식 이상: " + pub.length);

console.log("VAPID_PUBLIC=" + b64url(pub));
console.log("VAPID_PRIVATE=" + b64url(priv));
console.log("");
console.log("적용:");
console.log("  1) VAPID_PUBLIC  → wrangler.toml [vars] (클라이언트에도 내려가는 값이라 공개돼도 됨)");
console.log("  2) VAPID_PRIVATE → wrangler secret put VAPID_PRIVATE (절대 코드/설정 파일에 넣지 말 것)");
console.log("  3) (선택) VAPID_SUBJECT → mailto:연락받을주소");
