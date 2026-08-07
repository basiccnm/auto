// ================= 별도장 상점 · 2단계 보상 검증 API (2026-08-07) =================
// 지시서 「에듀싱크 MVP 재설계」 §3·§5③·§9
//
// 이 파일이 지키는 규칙 — 화면이 아니라 여기서 지켜야 우회가 안 된다:
//   ① **잔액은 star_ledger 하나로만 센다.** 상점 결제도 여기에 «음수»로 적는다.
//      따로 balance 컬럼을 두면 두 값이 반드시 어긋난다(그때부터 어느 쪽이 맞는지 아무도 모른다).
//   ② **잔액이 모자라면 서버가 막는다.** 화면에서 버튼을 가리는 것만으로는 못 막는다.
//   ③ **상한(주간·월간)도 서버가 센다.** 「주 2회」를 화면이 세면 앱을 껐다 켜서 우회된다.
//   ④ 2차 보너스는 **한 번만** 준다. 부모가 두 번 눌러도 도장이 두 번 늘지 않는다.
//   ⑤ 영수증(reward_orders)에 **상품 이름을 박아 둔다.** 진열대에서 상품을 지워도
//      «무엇을 샀는지»는 남아야 한다.
//   ⑥ 아이는 «사는 것»만 할 수 있다. 진열대 편집·보너스 승인은 부모만.

import { apiOk, apiList, apiErr, readJson } from "./api_core.js";
import { resolveAuth, hashPassword, verifyPassword } from "./auth_core.js";

const nowIso = () => new Date().toISOString();
const KST = 9 * 3600 * 1000;

/* 한국 시각 기준 오늘. 서버는 UTC 로 돌지만 아이의 «오늘»은 KST 다.
   주간·월간 상한을 UTC 로 세면 밤 9시 이후 구매가 다음 날로 넘어간다. */
function ymdKst(d) {
  const t = new Date((d ? d.getTime() : Date.now()) + KST);
  return t.toISOString().slice(0, 10).replace(/-/g, "");
}
// 상한 계산의 시작점 — 주간이면 이번 주 월요일, 월간이면 이번 달 1일 (둘 다 KST)
function periodStartIso(limitType) {
  const t = new Date(Date.now() + KST);
  t.setUTCHours(0, 0, 0, 0);
  if (limitType === "weekly") {
    const w = t.getUTCDay();                  // 0=일
    t.setUTCDate(t.getUTCDate() - ((w + 6) % 7));   // 월요일로
  } else {
    t.setUTCDate(1);
  }
  return new Date(t.getTime() - KST).toISOString();
}

function readCookie(request, name) {
  const raw = request.headers.get("Cookie") || "";
  for (const part of raw.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

/* 자녀 하나에 대한 관문. 부모도 자녀 폰도 여기를 지난다.
   ⚠ api_mission.js 의 gate() 와 **같은 규칙**이다. 한쪽만 고치면 구멍이 난다. */
async function gate(request, db, env, childId) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return { err: apiErr(auth.error) };
  if (!auth.ownerToken) return { err: apiErr("AUTH_REQUIRED") };
  const child = await db.prepare(
    "SELECT id, nickname, owner_token FROM children WHERE id = ? AND owner_token = ?"
  ).bind(childId, auth.ownerToken).first();
  if (!child) return { err: apiErr("NOT_FOUND") };
  if (auth.role === "child" && String(auth.childId) !== String(child.id)) return { err: apiErr("FORBIDDEN") };
  return { child, auth, isChild: auth.role === "child" };
}

// 잔액 — api_mission.js 와 **같은 원장**을 본다
async function starsOf(db, childId) {
  const r = await db.prepare("SELECT COALESCE(SUM(delta),0) n FROM star_ledger WHERE child_id = ?")
    .bind(childId).first();
  return (r && r.n) || 0;
}
async function addStars(db, childId, delta, reason) {
  await db.prepare("INSERT INTO star_ledger (child_id, delta, reason, created_at) VALUES (?, ?, ?, ?)")
    .bind(childId, delta, reason, nowIso()).run();
}

const rid = (p) => p + "-" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);

// ════════════════════════════════════════════════════════════
//  ① 진열대 (store_items) — 부모가 «무엇을 얼마에» 파는지 정한다
// ════════════════════════════════════════════════════════════

// GET /api/v1/children/{id}/store — 아이도 본다(사려면 봐야 한다)
async function listStore(request, db, env, childId) {
  const { child, isChild, err } = await gate(request, db, env, childId);
  if (err) return err;
  const rows = (await db.prepare(
    "SELECT item_id, title, stars_required, limit_type, limit_count FROM store_items WHERE child_id = ? ORDER BY stars_required"
  ).bind(child.id).all()).results || [];

  /* 아이 화면에는 «지금 살 수 있는지»가 같이 와야 한다.
     이걸 안 주면 아이가 눌러 보고서야 «한도 초과»를 알게 된다 — 그건 벌처럼 읽힌다. */
  const stars = await starsOf(db, child.id);
  const items = [];
  for (const r of rows) {
    let used = 0;
    if (r.limit_type && r.limit_count) {
      const u = await db.prepare(
        "SELECT COUNT(*) n FROM reward_orders WHERE child_id = ? AND item_id = ? AND created_at >= ?"
      ).bind(child.id, r.item_id, periodStartIso(r.limit_type)).first();
      used = (u && u.n) || 0;
    }
    const overLimit = !!(r.limit_type && r.limit_count && used >= r.limit_count);
    items.push({
      item_id: r.item_id, title: r.title, stars_required: r.stars_required,
      limit_type: r.limit_type, limit_count: r.limit_count, used,
      can_buy: !overLimit && stars >= r.stars_required,
      reason: overLimit ? "limit" : (stars < r.stars_required ? "stars" : null),
    });
  }
  return apiList(items, { stars });
}

// POST /api/v1/children/{id}/store — 진열대에 올리기 (부모만)
async function addStoreItem(request, db, env, childId) {
  const { child, isChild, err } = await gate(request, db, env, childId);
  if (err) return err;
  if (isChild) return apiErr("FORBIDDEN", null, "진열대는 부모님만 바꿀 수 있어요.");
  const b = await readJson(request);
  const title = String(b?.title || "").trim();
  const need = parseInt(b?.stars_required, 10);
  if (!title || title.length > 40) return apiErr("VALIDATION", null, "이름을 40자 안으로 적어 주세요.");
  if (!(need >= 1 && need <= 999)) return apiErr("VALIDATION", null, "필요한 도장 수를 확인해 주세요.");
  const lt = b?.limit_type === "weekly" || b?.limit_type === "monthly" ? b.limit_type : null;
  const lc = lt ? Math.max(1, parseInt(b?.limit_count, 10) || 1) : null;

  const id = rid("si");
  await db.prepare(
    "INSERT INTO store_items (item_id, child_id, title, stars_required, limit_type, limit_count, created_at) VALUES (?,?,?,?,?,?,?)"
  ).bind(id, child.id, title, need, lt, lc, nowIso()).run();
  return apiOk({ item_id: id }, 201);
}

// DELETE /api/v1/store/{itemId} — 진열대에서 내리기 (부모만)
// ⚠ 지난 영수증은 안 지운다. 산 기록은 상품과 별개로 남아야 한다.
async function delStoreItem(request, db, env, itemId) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  if (auth.role === "child") return apiErr("FORBIDDEN", null, "진열대는 부모님만 바꿀 수 있어요.");
  const r = await db.prepare(
    "DELETE FROM store_items WHERE item_id = ? AND child_id IN (SELECT id FROM children WHERE owner_token = ?)"
  ).bind(itemId, auth.ownerToken).run();
  if (!r.meta.changes) return apiErr("NOT_FOUND");
  return apiOk({ deleted: 1 });
}

// ════════════════════════════════════════════════════════════
//  ② 구매 (reward_orders) — 아이가 직접 산다
// ════════════════════════════════════════════════════════════

// POST /api/v1/children/{id}/store/{itemId}/buy
async function buy(request, db, env, childId, itemId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;

  const item = await db.prepare(
    "SELECT item_id, title, stars_required, limit_type, limit_count FROM store_items WHERE item_id = ? AND child_id = ?"
  ).bind(itemId, child.id).first();
  if (!item) return apiErr("NOT_FOUND", null, "그 상품은 이제 없어요.");

  // 상한 — 서버가 센다(③)
  if (item.limit_type && item.limit_count) {
    const u = await db.prepare(
      "SELECT COUNT(*) n FROM reward_orders WHERE child_id = ? AND item_id = ? AND created_at >= ?"
    ).bind(child.id, itemId, periodStartIso(item.limit_type)).first();
    if (((u && u.n) || 0) >= item.limit_count) {
      const kor = item.limit_type === "weekly" ? "이번 주" : "이번 달";
      return apiErr("LIMIT_EXCEEDED", null, `${kor}에 살 수 있는 만큼 다 샀어요.`);
    }
  }

  // 잔액 — 서버가 막는다(②)
  const stars = await starsOf(db, child.id);
  if (stars < item.stars_required) {
    return apiErr("VALIDATION", { stars, need: item.stars_required },
      `도장이 ${item.stars_required - stars}개 더 필요해요.`);
  }

  /* ⚠ 원장에 먼저 적고 영수증을 만든다. 반대로 하면 «영수증은 있는데 도장은 그대로»가 된다.
     D1 은 트랜잭션이 제한적이라 순서로 방어한다 — 둘 중 하나가 실패해도 «덜 준 쪽»으로 남게. */
  await addStars(db, child.id, -item.stars_required, `store:${itemId}`);
  const oid = rid("ro");
  await db.prepare(
    "INSERT INTO reward_orders (reward_order_id, child_id, item_id, item_title, stars_spent, status, created_at) VALUES (?,?,?,?,?,?,?)"
  ).bind(oid, child.id, itemId, item.title, item.stars_required, "requested", nowIso()).run();

  return apiOk({
    reward_order_id: oid, item_title: item.title,
    stars_spent: item.stars_required, stars_left: stars - item.stars_required,
  }, 201);
}

// GET /api/v1/children/{id}/rewards — 영수증 목록(부모·아이 공용)
async function listOrders(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const rows = (await db.prepare(
    "SELECT reward_order_id, item_title, stars_spent, status, created_at FROM reward_orders WHERE child_id = ? ORDER BY created_at DESC LIMIT 50"
  ).bind(child.id).all()).results || [];
  return apiList(rows, { stars: await starsOf(db, child.id) });
}

// POST /api/v1/rewards/{orderId}/fulfill — 「줬어요」 (부모만)
async function fulfill(request, db, env, orderId) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  if (auth.role === "child") return apiErr("FORBIDDEN", null, "부모님만 할 수 있어요.");
  const r = await db.prepare(
    "UPDATE reward_orders SET status = 'fulfilled' WHERE reward_order_id = ? AND status = 'requested' " +
    "AND child_id IN (SELECT id FROM children WHERE owner_token = ?)"
  ).bind(orderId, auth.ownerToken).run();
  if (!r.meta.changes) return apiErr("NOT_FOUND", null, "이미 처리했거나 없는 주문이에요.");
  return apiOk({ status: "fulfilled" });
}


// ════════════════════════════════════════════════════════════
//  ⑥ 아이 모드 PIN (child_mode_config) — 지시서 §4④
//     🔴 **비교는 서버가 한다.** 앱에서 비교하면 저장된 값을 읽어 우회할 수 있고,
//        그러면 «부모 화면 잠금»이 잠금 구실을 못 한다.
//     ⚠ PIN 은 4자리뿐이라 무차별 대입이 1만 번이면 끝난다 → **틀린 횟수를 서버가 센다.**
//        비밀번호와 같은 PBKDF2 로 저장하지만, 진짜 방어선은 시도 제한이다.
//     ⚠ 이건 자물쇠가 아니라 문턱이다 — 저학년이 실수로 부모 화면에 들어가는 걸 막는 것이지
//        작정한 사람을 막지 못한다. 데이터 보호는 서버 토큰이 진다.
// ════════════════════════════════════════════════════════════

const PIN_MAX_TRY = 5;             // 연속 실패 한도
const PIN_LOCK_MS = 5 * 60 * 1000; // 넘으면 5분 잠금

function pinOwner(auth) {
  /* 아이 모드는 **부모 폰**에서 쓴다. 자녀 토큰에는 애초에 나갈 문이 없다 */
  if (auth.error) return { err: apiErr(auth.error) };
  if (!auth.ownerToken) return { err: apiErr("AUTH_REQUIRED") };
  if (auth.role === "child") return { err: apiErr("FORBIDDEN", null, "이 기능은 부모님 폰에서만 써요.") };
  return { ownerToken: auth.ownerToken };
}
const isPin4 = (v) => typeof v === "string" && /^\d{4}$/.test(v);

// GET /api/v1/child-mode/pin — 정해 뒀는지만 알려준다(값은 절대 안 내보낸다)
async function pinStatus(request, db, env) {
  const { ownerToken, err } = pinOwner(await resolveAuth(request, db, env, readCookie));
  if (err) return err;
  const row = await db.prepare(
    "SELECT updated_at, fail_count, locked_until FROM child_mode_config WHERE owner_token = ?"
  ).bind(ownerToken).first();
  const lockedUntil = row?.locked_until || null;
  return apiOk({
    is_set: !!row,
    updated_at: row?.updated_at || null,
    locked: !!(lockedUntil && Date.parse(lockedUntil) > Date.now()),
    locked_until: lockedUntil,
  });
}

// POST /api/v1/child-mode/pin — 처음 정하기 / 바꾸기
//   바꿀 때는 **옛 PIN 을 같이 받는다.** 안 그러면 아이가 아이 모드에서 PIN 을 갈아치우고 나갈 수 있다.
async function pinSet(request, db, env) {
  const { ownerToken, err } = pinOwner(await resolveAuth(request, db, env, readCookie));
  if (err) return err;
  const body = await readJson(request);
  const pin = body?.pin, oldPin = body?.old_pin;
  if (!isPin4(pin)) return apiErr("VALIDATION", null, "숫자 4자리로 정해 주세요.");
  /* ⚠ 0000·1234 처럼 뻔한 것은 막는다. 아이가 제일 먼저 눌러 보는 번호다 */
  if (/^(\d)\1{3}$/.test(pin) || ["1234", "4321", "0123"].includes(pin))
    return apiErr("VALIDATION", null, "너무 쉬운 번호예요. 다른 번호로 정해 주세요.");

  const row = await db.prepare("SELECT pin_hash FROM child_mode_config WHERE owner_token = ?")
    .bind(ownerToken).first();
  if (row) {
    if (!isPin4(oldPin)) return apiErr("VALIDATION", null, "지금 쓰는 번호도 넣어 주세요.");
    if (!(await verifyPassword(oldPin, row.pin_hash)))
      return apiErr("VALIDATION", null, "지금 쓰는 번호가 달라요.");
  }
  const hash = await hashPassword(pin);
  await db.prepare(
    "INSERT INTO child_mode_config (owner_token, pin_hash, updated_at, fail_count, locked_until) " +
    "VALUES (?,?,?,0,NULL) ON CONFLICT(owner_token) DO UPDATE SET " +
    "pin_hash = excluded.pin_hash, updated_at = excluded.updated_at, fail_count = 0, locked_until = NULL"
  ).bind(ownerToken, hash, nowIso()).run();
  return apiOk({ is_set: true, updated_at: nowIso() });
}

// POST /api/v1/child-mode/unlock — 아이 모드에서 부모로 나가기
async function pinUnlock(request, db, env) {
  const { ownerToken, err } = pinOwner(await resolveAuth(request, db, env, readCookie));
  if (err) return err;
  const row = await db.prepare(
    "SELECT pin_hash, fail_count, locked_until FROM child_mode_config WHERE owner_token = ?"
  ).bind(ownerToken).first();
  /* PIN 을 안 정했으면 잠금 자체가 없다 — 문을 열어 준다(잠근 적 없는 문을 못 열면 갇힌다) */
  if (!row) return apiOk({ unlocked: true, is_set: false });

  if (row.locked_until && Date.parse(row.locked_until) > Date.now()) {
    const left = Math.ceil((Date.parse(row.locked_until) - Date.now()) / 60000);
    return apiErr("LOCKED", { locked_until: row.locked_until },
      `여러 번 틀렸어요. ${left}분 뒤에 다시 해 주세요.`);
  }
  const pin = (await readJson(request))?.pin;
  if (!isPin4(pin)) return apiErr("VALIDATION", null, "숫자 4자리를 넣어 주세요.");

  if (await verifyPassword(pin, row.pin_hash)) {
    await db.prepare("UPDATE child_mode_config SET fail_count = 0, locked_until = NULL WHERE owner_token = ?")
      .bind(ownerToken).run();
    return apiOk({ unlocked: true, is_set: true });
  }
  const n = (row.fail_count || 0) + 1;
  const lock = n >= PIN_MAX_TRY ? new Date(Date.now() + PIN_LOCK_MS).toISOString() : null;
  await db.prepare("UPDATE child_mode_config SET fail_count = ?, locked_until = ? WHERE owner_token = ?")
    .bind(lock ? 0 : n, lock, ownerToken).run();   // 잠갔으면 카운터는 리셋(잠금이 대신 막는다)
  if (lock) return apiErr("LOCKED", { locked_until: lock }, "여러 번 틀렸어요. 5분 뒤에 다시 해 주세요.");
  return apiErr("VALIDATION", { left: PIN_MAX_TRY - n }, `번호가 달라요. ${PIN_MAX_TRY - n}번 남았어요.`);
}

// ════════════════════════════════════════════════════════════
//  ③ 2단계 보상 검증 (mission_verifications)
// ════════════════════════════════════════════════════════════

// POST /api/v1/children/{id}/verify — 1차: 아이가 «했다»고 낸다(즉시 도장)
async function step1(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const b = await readJson(request);
  const code = String(b?.mission_code || "").trim();
  if (!code) return apiErr("VALIDATION", null, "어떤 미션인지 알 수 없어요.");
  const data = b?.step1_data == null ? null : String(b.step1_data).slice(0, 200);

  /* 같은 미션을 같은 날 두 번 내면 도장이 두 번 나간다 → 하루 한 번으로 막는다.
     ⚠ 아이가 잘못 눌렀을 때 «이미 했어요»가 벌처럼 읽히지 않게 문구를 부드럽게.
     ⚠ **`created_at` 은 UTC 로 저장된다.** 여기에 KST 날짜를 대면 9시간이 어긋나
       중복이 그냥 통과한다(2026-08-07 실측: 도장이 두 번 나갔다).
       DB 안에서 +9시간 해 KST 로 맞춘 뒤 비교한다 — 아이의 «오늘»은 KST 다. */
  const dup = await db.prepare(
    "SELECT verify_id FROM mission_verifications WHERE child_id = ? AND mission_code = ? " +
    "AND date(created_at, '+9 hours') = date(?, '+9 hours')"
  ).bind(child.id, code, nowIso()).first();
  if (dup) return apiOk({ verify_id: dup.verify_id, already: 1, stars: await starsOf(db, child.id) });

  const vid = rid("mv");
  const now = nowIso();
  await db.prepare(
    "INSERT INTO mission_verifications (verify_id, child_id, mission_code, step1_data, step1_granted_at, step2_approved_at, step2_bonus_stars, created_at) " +
    "VALUES (?,?,?,?,?,NULL,0,?)"
  ).bind(vid, child.id, code, data, now, now).run();
  await addStars(db, child.id, 1, `verify1:${code}`);      // 1차 보상은 항상 1개
  return apiOk({ verify_id: vid, stars: await starsOf(db, child.id) }, 201);
}

// GET /api/v1/children/{id}/verify?pending=1 — 부모의 «확인해 주세요» 목록
async function listVerify(request, db, env, childId, url) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const onlyPending = url.searchParams.get("pending") === "1";
  const sql = "SELECT verify_id, mission_code, step1_data, step1_granted_at, step2_approved_at, step2_bonus_stars, created_at " +
    "FROM mission_verifications WHERE child_id = ?" +
    (onlyPending ? " AND step2_approved_at IS NULL" : "") +
    " ORDER BY created_at DESC LIMIT 50";
  const rows = (await db.prepare(sql).bind(child.id).all()).results || [];
  return apiList(rows);
}

// POST /api/v1/verify/{verifyId}/bonus — 2차: 부모가 보고 보너스를 준다
async function step2(request, db, env, verifyId) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  if (auth.role === "child") return apiErr("FORBIDDEN", null, "보너스는 부모님이 주는 거예요.");
  const b = await readJson(request);
  const bonus = Math.max(0, Math.min(5, parseInt(b?.bonus_stars, 10) || 0));

  const row = await db.prepare(
    "SELECT v.verify_id, v.child_id, v.step2_approved_at FROM mission_verifications v " +
    "JOIN children c ON c.id = v.child_id WHERE v.verify_id = ? AND c.owner_token = ?"
  ).bind(verifyId, auth.ownerToken).first();
  if (!row) return apiErr("NOT_FOUND");
  if (row.step2_approved_at) return apiErr("DUPLICATE", null, "이미 보너스를 줬어요.");   // ④ 한 번만

  await db.prepare(
    "UPDATE mission_verifications SET step2_approved_at = ?, step2_bonus_stars = ? WHERE verify_id = ? AND step2_approved_at IS NULL"
  ).bind(nowIso(), bonus, verifyId).run();
  if (bonus > 0) await addStars(db, row.child_id, bonus, `verify2:${verifyId}`);

  // 칭찬 기록도 같이 남긴다 — 아이 화면의 «스티커»가 이걸 읽는다
  await db.prepare(
    "INSERT INTO reactions (reaction_id, child_id, sticker_type, bonus_stars, created_at) VALUES (?,?,?,?,?)"
  ).bind(rid("rc"), row.child_id, "bonus_approved", bonus, nowIso()).run();

  return apiOk({ bonus_stars: bonus, stars: await starsOf(db, row.child_id) });
}

// ════════════════════════════════════════════════════════════
//  ④ 칭찬 스티커 (reactions)
// ════════════════════════════════════════════════════════════

// POST /api/v1/children/{id}/reactions — 부모가 1초 만에 보낸다
async function react(request, db, env, childId) {
  const { child, isChild, err } = await gate(request, db, env, childId);
  if (err) return err;
  if (isChild) return apiErr("FORBIDDEN", null, "칭찬은 부모님이 보내는 거예요.");
  const b = await readJson(request);
  const t = String(b?.sticker_type || "");
  if (t !== "thumb_up" && t !== "heart") return apiErr("VALIDATION", null, "없는 스티커예요.");
  const id = rid("rc");
  await db.prepare(
    "INSERT INTO reactions (reaction_id, child_id, sticker_type, bonus_stars, created_at) VALUES (?,?,?,0,?)"
  ).bind(id, child.id, t, nowIso()).run();
  return apiOk({ reaction_id: id }, 201);
}

// GET /api/v1/children/{id}/reactions — 아이 화면이 «안 본 것»을 가져간다
async function listReactions(request, db, env, childId, url) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const since = url.searchParams.get("since");
  const rows = (await db.prepare(
    "SELECT reaction_id, sticker_type, bonus_stars, created_at FROM reactions WHERE child_id = ?" +
    (since ? " AND created_at > ?" : "") + " ORDER BY created_at DESC LIMIT 20"
  ).bind(...(since ? [child.id, since] : [child.id])).all()).results || [];
  return apiList(rows);
}

// ════════════════════════════════════════════════════════════
//  ⑤ 부모 커스텀 미션 템플릿 (parent_mission_templates)
//     하이브리드 세트 3개 중 «부모 커스텀 1개»를 여기서 뽑는다
// ════════════════════════════════════════════════════════════

async function listTemplates(request, db, env, childId) {
  const { child, err } = await gate(request, db, env, childId);
  if (err) return err;
  const rows = (await db.prepare(
    "SELECT template_id, title, stars FROM parent_mission_templates WHERE child_id = ? ORDER BY created_at DESC"
  ).bind(child.id).all()).results || [];
  return apiList(rows);
}

async function addTemplate(request, db, env, childId) {
  const { child, isChild, err } = await gate(request, db, env, childId);
  if (err) return err;
  if (isChild) return apiErr("FORBIDDEN", null, "부모님만 만들 수 있어요.");
  const b = await readJson(request);
  const title = String(b?.title || "").trim();
  if (!title || title.length > 40) return apiErr("VALIDATION", null, "15자 안팎으로 짧게 적어 주세요.");
  const stars = Math.max(1, Math.min(3, parseInt(b?.stars, 10) || 1));
  const id = rid("pt");
  await db.prepare(
    "INSERT INTO parent_mission_templates (template_id, child_id, title, stars, created_at) VALUES (?,?,?,?,?)"
  ).bind(id, child.id, title, stars, nowIso()).run();
  return apiOk({ template_id: id }, 201);
}

async function delTemplate(request, db, env, templateId) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return apiErr(auth.error);
  if (!auth.ownerToken) return apiErr("AUTH_REQUIRED");
  if (auth.role === "child") return apiErr("FORBIDDEN");
  const r = await db.prepare(
    "DELETE FROM parent_mission_templates WHERE template_id = ? AND child_id IN (SELECT id FROM children WHERE owner_token = ?)"
  ).bind(templateId, auth.ownerToken).run();
  if (!r.meta.changes) return apiErr("NOT_FOUND");
  return apiOk({ deleted: 1 });
}

// ════════════════════════════════════════════════════════════
//  라우터
//  ⚠ index.js 의 **접두어 화이트리스트**에 경로를 안 넣으면 여기까지 오지도 못하고
//    HTML 404 로 새어나간다(2026-07-27 supplies 에서 실측). 반드시 같이 등록할 것.
// ════════════════════════════════════════════════════════════
export async function handleRewardApi(request, db, env, url) {
  const p = url.pathname, m = request.method;
  let x;

  // 진열대
  x = p.match(/^\/api\/v1\/children\/(\d+)\/store\/?$/);
  if (x) {
    if (m === "GET") return listStore(request, db, env, x[1]);
    if (m === "POST") return addStoreItem(request, db, env, x[1]);
    return apiErr("VALIDATION", null, "지원하지 않는 요청 방식이에요.");
  }
  x = p.match(/^\/api\/v1\/children\/(\d+)\/store\/([\w-]+)\/buy$/);
  if (x && m === "POST") return buy(request, db, env, x[1], x[2]);
  x = p.match(/^\/api\/v1\/store\/([\w-]+)$/);
  if (x && m === "DELETE") return delStoreItem(request, db, env, x[1]);

  // 영수증
  x = p.match(/^\/api\/v1\/children\/(\d+)\/rewards\/?$/);
  if (x && m === "GET") return listOrders(request, db, env, x[1]);
  x = p.match(/^\/api\/v1\/rewards\/([\w-]+)\/fulfill$/);
  if (x && m === "POST") return fulfill(request, db, env, x[1]);

  // 2단계 검증
  x = p.match(/^\/api\/v1\/children\/(\d+)\/verify\/?$/);
  if (x) {
    if (m === "POST") return step1(request, db, env, x[1]);
    if (m === "GET") return listVerify(request, db, env, x[1], url);
    return apiErr("VALIDATION", null, "지원하지 않는 요청 방식이에요.");
  }
  x = p.match(/^\/api\/v1\/verify\/([\w-]+)\/bonus$/);
  if (x && m === "POST") return step2(request, db, env, x[1]);

  // 칭찬
  x = p.match(/^\/api\/v1\/children\/(\d+)\/reactions\/?$/);
  if (x) {
    if (m === "POST") return react(request, db, env, x[1]);
    if (m === "GET") return listReactions(request, db, env, x[1], url);
  }

  // 부모 커스텀 미션
  x = p.match(/^\/api\/v1\/children\/(\d+)\/templates\/?$/);
  if (x) {
    if (m === "GET") return listTemplates(request, db, env, x[1]);
    if (m === "POST") return addTemplate(request, db, env, x[1]);
  }
  x = p.match(/^\/api\/v1\/templates\/([\w-]+)$/);
  if (x && m === "DELETE") return delTemplate(request, db, env, x[1]);

  // 아이 모드 PIN (§4④) — childId 가 없다. 계정(owner_token) 단위다
  if (p === "/api/v1/child-mode/pin") {
    if (m === "GET") return pinStatus(request, db, env);
    if (m === "POST") return pinSet(request, db, env);
    return apiErr("VALIDATION", null, "지원하지 않는 요청 방식이에요.");
  }
  if (p === "/api/v1/child-mode/unlock" && m === "POST") return pinUnlock(request, db, env);

  return null;   // 우리 것이 아니다
}
