/* ═══════════════════════════════════════════════════════════
   FCM 테스트 발송 (2026-07-25)

   폰에 푸시가 진짜 도착하는지 확인하는 도구. 외부 라이브러리 없이
   서비스계정 키 → JWT 서명 → OAuth2 토큰 → FCM v1 로 직접 쏜다.

   쓰는 법:
     node tools/fcm-send.mjs <기기토큰> ["제목"] ["본문"]
     (기기토큰 = 앱 → 알림 화면 → "이 기기 푸시 켜기" 후 화면에 뜨는 값)

   키 위치: D:\_보관\eduthink-fcm-serviceaccount.json  (드라이브·git 밖. 채팅에 붙이지 말 것)
     다른 곳이면  FCM_KEY=경로  로 넘긴다.

   ⚠ 헤드업(화면 위로 튀어나오게) 하려면 세 개가 다 맞아야 한다:
     ① 앱이 만든 채널 importance 5   (www/app.js _pushChannel)
     ② 매니페스트 default_notification_channel_id 가 같은 id
     ③ 이 발송 payload 의 android.priority=high + notification.channel_id
   ═══════════════════════════════════════════════════════════ */
import fs from "node:fs";
import crypto from "node:crypto";

const KEY_PATH = process.env.FCM_KEY || "D:\\_보관\\eduthink-fcm-serviceaccount.json";
const CHANNEL = "eduthink_urgent";                       // app.js·매니페스트와 같아야 한다

const [token, title = "엄마", body = "학원 끝나면 바로 집으로"] = process.argv.slice(2);
if (!token) { console.error("기기 토큰이 필요하다 → node tools/fcm-send.mjs <토큰> [제목] [본문]"); process.exit(1); }
if (!fs.existsSync(KEY_PATH)) { console.error("서비스계정 키가 없다: " + KEY_PATH); process.exit(1); }

const key = JSON.parse(fs.readFileSync(KEY_PATH, "utf8"));
const b64 = (o) => Buffer.from(typeof o === "string" ? o : JSON.stringify(o)).toString("base64url");

// 1) 서비스계정으로 JWT를 만들어 서명한다
const now = Math.floor(Date.now() / 1000);
const claim = {
  iss: key.client_email, scope: "https://www.googleapis.com/auth/firebase.messaging",
  aud: "https://oauth2.googleapis.com/token", iat: now, exp: now + 3600,
};
const unsigned = b64({ alg: "RS256", typ: "JWT" }) + "." + b64(claim);
const jwt = unsigned + "." + crypto.createSign("RSA-SHA256").update(unsigned).sign(key.private_key, "base64url");

// 2) JWT → 액세스 토큰
const tokRes = await fetch("https://oauth2.googleapis.com/token", {
  method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion: jwt }),
});
const tokJson = await tokRes.json();
if (!tokJson.access_token) { console.error("토큰 실패:", tokJson); process.exit(1); }

// 3) 발송 — 헤드업으로 뜨게 채널·우선순위를 명시한다
const res = await fetch(`https://fcm.googleapis.com/v1/projects/${key.project_id}/messages:send`, {
  method: "POST",
  headers: { authorization: "Bearer " + tokJson.access_token, "content-type": "application/json" },
  body: JSON.stringify({
    message: {
      token,
      notification: { title, body },
      android: {
        priority: "high",
        notification: { channel_id: CHANNEL, default_sound: true, default_vibrate_timings: true },
      },
    },
  }),
});
const out = await res.json();
console.log(res.status === 200 ? "보냄 ✓ " + out.name : "실패 " + res.status + " " + JSON.stringify(out));
