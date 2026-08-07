// Workers(D1) 라우트 예시 — 구독 저장 / 테스트 발송 / 크론 자동 발송.
// 출처: 에듀싱크 index.js — 2026-07-16 실기기 검증본을 범용화. 프로젝트에 맞게 고쳐서 붙일 것(직접 import 금지).
//
// 전제:
//  - 사용자 식별: owner_token 쿠키(익명 UUID). 다른 식별자를 쓰면 owner_token 자리만 바꾸면 됨.
//  - DB: D1 (env.DB). schema.sql의 push_subscriptions + notif_settings 테이블 필요.
//  - env: VAPID_PRIVATE / VAPID_PUBLIC / VAPID_SUBJECT (gen-vapid-keys.mjs로 생성,
//         wrangler secret put VAPID_PRIVATE — 공개키는 vars에 둬도 됨)

import { sendPush } from "./push.js";

// ── fetch() 라우팅에 추가 ─────────────────────────────────────────
// if (path === "/sw.js") return new Response(SW_JS, { headers: { "Content-Type": "application/javascript", "Cache-Control": "no-cache" } });
// if (path === "/api/push/subscribe") return handlePushSubscribe(request, env.DB);
// if (path === "/api/push/test") return handlePushTest(request, env.DB, env);

// 웹푸시 구독 저장(브라우저 → 서버). endpoint 기준 upsert라 중복 구독 걱정 없음.
export async function handlePushSubscribe(request, db) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  let ownerToken = getCookie(request, "owner_token");
  const setCookie = [];
  if (!ownerToken) { ownerToken = crypto.randomUUID(); setCookie.push(`owner_token=${ownerToken}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax`); }
  let sub;
  try { sub = await request.json(); } catch { return json({ ok: false, error: "invalid" }, 400); }
  if (!sub || !sub.endpoint || !sub.keys) return json({ ok: false, error: "invalid" }, 400);
  const nowIso = new Date().toISOString();
  await db.prepare(
    `INSERT INTO push_subscriptions (owner_token, endpoint, p256dh, auth, created_at) VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(endpoint) DO UPDATE SET owner_token=excluded.owner_token, p256dh=excluded.p256dh, auth=excluded.auth`
  ).bind(ownerToken, sub.endpoint, sub.keys.p256dh || "", sub.keys.auth || "", nowIso).run();
  // 구독하면 알림 설정도 켬.
  const upd = await db.prepare("UPDATE notif_settings SET enabled=1, updated_at=? WHERE owner_token=?").bind(nowIso, ownerToken).run();
  if (!upd.meta || upd.meta.changes === 0) await db.prepare("INSERT INTO notif_settings (owner_token, enabled, updated_at) VALUES (?, 1, ?)").bind(ownerToken, nowIso).run();
  const resp = json({ ok: true });
  for (const c of setCookie) resp.headers.append("Set-Cookie", c);
  return resp;
}

// 내 구독으로 테스트 알림 발송(실기기 확인용). 404/410 응답은 만료 구독 → 즉시 삭제.
export async function handlePushTest(request, db, env) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false, error: "no_token" }, 403);
  if (!env.VAPID_PRIVATE || !env.VAPID_PUBLIC) return json({ ok: false, error: "vapid_missing" }, 500);
  const subs = (await db.prepare("SELECT * FROM push_subscriptions WHERE owner_token=?").bind(ownerToken).all()).results;
  let sent = 0, gone = 0;
  for (const s of subs) {
    try {
      const st = await sendPush({ endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } }, env);
      if (st === 201 || st === 200) sent++;
      else if (st === 404 || st === 410) { gone++; await db.prepare("DELETE FROM push_subscriptions WHERE endpoint=?").bind(s.endpoint).run(); }
    } catch { /* skip */ }
  }
  return json({ ok: true, subs: subs.length, sent, gone });
}

// ── 크론 자동 발송 예시 (wrangler.toml: [triggers] crons = ["* * * * *"]) ──
// "보낼 것"을 고르는 쿼리(여기선 personal_events.remind_at)만 프로젝트에 맞게 교체.
export async function cronSendDue(db, env) {
  if (!env.VAPID_PRIVATE) return; // 키 없으면 조용히 스킵
  const now = new Date().toISOString();
  // 알림 시각이 지났고 아직 안 보낸 건 × 알림 켠 소유자의 구독. 각 (건×구독) 1행.
  const { results: due } = await db.prepare(
    `SELECT pe.id AS ev_id, ps.endpoint, ps.p256dh, ps.auth
     FROM personal_events pe
     JOIN notif_settings n ON n.owner_token = pe.owner_token AND n.enabled = 1
     JOIN push_subscriptions ps ON ps.owner_token = pe.owner_token
     WHERE pe.remind_at IS NOT NULL AND pe.remind_sent = 0 AND pe.remind_at <= ?`
  ).bind(now).all();
  const sentEvents = new Set();
  for (const r of due) {
    try {
      const st = await sendPush({ endpoint: r.endpoint, keys: { p256dh: r.p256dh, auth: r.auth } }, env);
      if (st === 404 || st === 410) await db.prepare("DELETE FROM push_subscriptions WHERE endpoint = ?").bind(r.endpoint).run();
      else sentEvents.add(r.ev_id);
    } catch { /* 다음 대상 계속 */ }
  }
  // 발송된 건은 한 번만 가도록 플래그.
  for (const evId of sentEvents) {
    await db.prepare("UPDATE personal_events SET remind_sent = 1 WHERE id = ?").bind(evId).run();
  }
}

// ── 유틸(프로젝트에 이미 있으면 그쪽 것 사용) ──────────────────────
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json; charset=utf-8" } });
}
function getCookie(request, name) {
  const h = request.headers.get("Cookie") || "";
  const m = h.match(new RegExp("(?:^|;\\s*)" + name + "=([^;]+)"));
  return m ? decodeURIComponent(m[1]) : "";
}
