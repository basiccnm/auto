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
import { grantStars, spendStars, starsOf as coinBalance } from "./star_core.js";

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
  const stars = await coinBalance(db, child.id);
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
  /* ⚠ 상한 999 는 «하루 3개, 미션 1개 = ★1» 시절의 값이었다.
     지금은 하루 상한이 60 이라 ★2,000 짜리 자전거가 한 달, ★10,000 이 반년짜리 목표가 된다 —
     **큰 목표가 이 앱 경제의 뼈대**인데 999 가 그걸 막고 있었다(기획서 v2 §02·§04).
     ⚠ 그래도 무한은 아니다. 오타로 ★999999 를 걸면 아이가 «영영 못 사는 것»만 보게 된다. */
  if (!(need >= 1 && need <= 99999)) return apiErr("VALIDATION", null, "필요한 도장 수를 확인해 주세요(1~99,999).");
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
  const stars = await coinBalance(db, child.id);
  if (stars < item.stars_required) {
    return apiErr("VALIDATION", { stars, need: item.stars_required },
      `도장이 ${item.stars_required - stars}개 더 필요해요.`);
  }

  /* ⚠ 원장에 먼저 적고 영수증을 만든다. 반대로 하면 «영수증은 있는데 도장은 그대로»가 된다.
     D1 은 트랜잭션이 제한적이라 순서로 방어한다 — 둘 중 하나가 실패해도 «덜 준 쪽»으로 남게. */
  await spendStars(db, child.id, item.stars_required, `store:${itemId}`);
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
  return apiList(rows, { stars: await coinBalance(db, child.id) });
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
  if (dup) return apiOk({ verify_id: dup.verify_id, already: 1, stars: await coinBalance(db, child.id) });

  const vid = rid("mv");
  const now = nowIso();
  await db.prepare(
    "INSERT INTO mission_verifications (verify_id, child_id, mission_code, step1_data, step1_granted_at, step2_approved_at, step2_bonus_stars, created_at) " +
    "VALUES (?,?,?,?,?,NULL,0,?)"
  ).bind(vid, child.id, code, data, now, now).run();
  await grantStars(db, child.id, 1, `verify1:${code}`);   // 1차는 소액 — 진짜는 부모의 2차 보너스
  return apiOk({ verify_id: vid, stars: await coinBalance(db, child.id) }, 201);
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
  if (bonus > 0) await grantStars(db, row.child_id, bonus, `verify2:${verifyId}`);

  // 칭찬 기록도 같이 남긴다 — 아이 화면의 «스티커»가 이걸 읽는다
  await db.prepare(
    "INSERT INTO reactions (reaction_id, child_id, sticker_type, bonus_stars, created_at) VALUES (?,?,?,?,?)"
  ).bind(rid("rc"), row.child_id, "bonus_approved", bonus, nowIso()).run();

  return apiOk({ bonus_stars: bonus, stars: await coinBalance(db, row.child_id) });
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
//  ⑥ 아이 모드 4자리 PIN (child_mode_config) — 지시서 §0-6 · §5④
//
//  부모 폰을 같이 쓰는 저학년용이다. 아이 모드로 들어가면 서랍·설정이 숨고,
//  **부모 모드로 돌아올 때만** PIN 을 묻는다(들어갈 때는 안 묻는다 — 아이가 들어가는 거니까).
//
//  ⚠ 이 PIN 은 **부모 토큰으로** 오간다. 아이 모드는 «부모 폰 공유»라 토큰이 그대로 부모 것이다.
//    자녀 폰(자녀 토큰)은 여기 올 일이 없다 — 그쪽은 애초에 자녀 화면만 열린다.
//  ⚠ 경우의 수가 1만 개뿐이라 **틀린 횟수를 서버가 센다.** 화면에서 세면 앱을 껐다 켜면 0 이 된다
//    (상점 상한을 서버가 세는 것과 같은 이유).
// ════════════════════════════════════════════════════════════

const PIN_MAX_FAIL = 5;          // 연속 5번 틀리면 잠근다
const PIN_LOCK_MIN = 5;          // 기본 5분
const PIN_LOCK_MIN_LONG = 30;    // 10번째부터는 30분

// 부모 토큰만 통과. 아이 모드 PIN 은 부모 계정 하나에 하나다(자녀별이 아니다).
async function pinGate(request, db, env) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return { err: apiErr(auth.error) };
  if (!auth.ownerToken) return { err: apiErr("AUTH_REQUIRED") };
  if (auth.role === "child") return { err: apiErr("FORBIDDEN", null, "부모님 기기에서만 쓸 수 있어요.") };
  return { auth };
}

const isPin = (v) => /^\d{4}$/.test(String(v || ""));

// GET /api/v1/child-mode — 「PIN 이 걸려 있나」만 알려준다. 해시는 절대 안 내보낸다.
async function pinStatus(request, db, env) {
  const { auth, err } = await pinGate(request, db, env);
  if (err) return err;
  const row = await db.prepare(
    "SELECT locked_until FROM child_mode_config WHERE owner_token = ?"
  ).bind(auth.ownerToken).first();
  const lockedFor = row && row.locked_until && row.locked_until > nowIso()
    ? Math.ceil((Date.parse(row.locked_until) - Date.now()) / 1000) : 0;
  return apiOk({ has_pin: row ? 1 : 0, locked_for: lockedFor });
}

// POST /api/v1/child-mode/pin — 걸기·바꾸기. 이미 있으면 지금 PIN 을 같이 받아야 한다.
async function pinSet(request, db, env) {
  const { auth, err } = await pinGate(request, db, env);
  if (err) return err;
  const b = await readJson(request);
  if (!isPin(b?.pin)) return apiErr("VALIDATION", null, "숫자 네 자리로 정해 주세요.");
  /* 1111·1234 처럼 뻔한 건 막는다 — 아이가 제일 먼저 눌러 보는 번호다.
     막지 않으면 PIN 이 있으나 마나가 된다. */
  if (/^(\d)\1{3}$/.test(b.pin) || "0123456789".includes(b.pin) || "9876543210".includes(b.pin)) {
    return apiErr("VALIDATION", null, "1111·1234 처럼 쉬운 번호는 쓸 수 없어요.");
  }

  const row = await db.prepare(
    "SELECT pin_hash FROM child_mode_config WHERE owner_token = ?"
  ).bind(auth.ownerToken).first();
  if (row && !(await verifyPassword(String(b?.current_pin || ""), row.pin_hash))) {
    return apiErr("FORBIDDEN", null, "지금 쓰는 번호가 달라요.");
  }

  const hash = await hashPassword(b.pin);
  await db.prepare(
    "INSERT INTO child_mode_config (owner_token, pin_hash, fail_count, locked_until, updated_at) VALUES (?,?,0,NULL,?) " +
    "ON CONFLICT(owner_token) DO UPDATE SET pin_hash = excluded.pin_hash, fail_count = 0, locked_until = NULL, updated_at = excluded.updated_at"
  ).bind(auth.ownerToken, hash, nowIso()).run();
  return apiOk({ has_pin: 1 });
}

// POST /api/v1/child-mode/pin/verify — 부모 모드로 돌아올 때
async function pinVerify(request, db, env) {
  const { auth, err } = await pinGate(request, db, env);
  if (err) return err;
  const b = await readJson(request);

  const row = await db.prepare(
    "SELECT pin_hash, fail_count, locked_until FROM child_mode_config WHERE owner_token = ?"
  ).bind(auth.ownerToken).first();
  // PIN 을 안 걸었으면 잠글 것도 없다 — 그냥 열어 준다(아이 모드를 안 쓰는 사람)
  if (!row) return apiOk({ ok: 1, has_pin: 0 });

  /* 잠겨 있으면 **맞아도 안 열어 준다.** 여기서 먼저 걸러야 «맞을 때까지 두드리기»가 막힌다. */
  if (row.locked_until && row.locked_until > nowIso()) {
    const sec = Math.ceil((Date.parse(row.locked_until) - Date.now()) / 1000);
    return apiErr("LIMIT_EXCEEDED", { locked_for: sec },
      `너무 여러 번 틀렸어요. ${Math.ceil(sec / 60)}분 뒤에 다시 해 주세요.`);
  }

  if (isPin(b?.pin) && await verifyPassword(String(b.pin), row.pin_hash)) {
    await db.prepare(
      "UPDATE child_mode_config SET fail_count = 0, locked_until = NULL WHERE owner_token = ?"
    ).bind(auth.ownerToken).run();
    return apiOk({ ok: 1 });
  }

  const fails = (row.fail_count || 0) + 1;
  let lockedUntil = null;
  if (fails >= PIN_MAX_FAIL) {
    const mins = fails >= PIN_MAX_FAIL * 2 ? PIN_LOCK_MIN_LONG : PIN_LOCK_MIN;
    lockedUntil = new Date(Date.now() + mins * 60000).toISOString();
  }
  await db.prepare(
    "UPDATE child_mode_config SET fail_count = ?, locked_until = ? WHERE owner_token = ?"
  ).bind(fails, lockedUntil, auth.ownerToken).run();

  if (lockedUntil) {
    const sec = Math.ceil((Date.parse(lockedUntil) - Date.now()) / 1000);
    return apiErr("LIMIT_EXCEEDED", { locked_for: sec },
      `너무 여러 번 틀렸어요. ${Math.ceil(sec / 60)}분 뒤에 다시 해 주세요.`);
  }
  // 남은 횟수를 알려 준다 — 몇 번 남았는지 모르면 갑자기 잠기는 걸로 읽힌다
  return apiErr("VALIDATION", { left: PIN_MAX_FAIL - fails },
    `번호가 달라요. ${PIN_MAX_FAIL - fails}번 더 틀리면 잠겨요.`);
}

// DELETE /api/v1/child-mode/pin — 아이 모드 그만 쓰기. 지금 PIN 을 알아야 지운다.
async function pinClear(request, db, env) {
  const { auth, err } = await pinGate(request, db, env);
  if (err) return err;
  const b = await readJson(request);
  const row = await db.prepare(
    "SELECT pin_hash, locked_until FROM child_mode_config WHERE owner_token = ?"
  ).bind(auth.ownerToken).first();
  if (!row) return apiOk({ has_pin: 0 });
  if (row.locked_until && row.locked_until > nowIso()) {
    return apiErr("LIMIT_EXCEEDED", null, "잠겨 있는 동안에는 지울 수 없어요.");
  }
  if (!(await verifyPassword(String(b?.pin || ""), row.pin_hash))) {
    return apiErr("FORBIDDEN", null, "번호가 달라요.");
  }
  await db.prepare("DELETE FROM child_mode_config WHERE owner_token = ?").bind(auth.ownerToken).run();
  return apiOk({ has_pin: 0 });
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

  // 아이 모드 PIN
  if (p === "/api/v1/child-mode" && m === "GET") return pinStatus(request, db, env);
  if (p === "/api/v1/child-mode/pin") {
    if (m === "POST") return pinSet(request, db, env);
    if (m === "DELETE") return pinClear(request, db, env);
    return apiErr("VALIDATION", null, "지원하지 않는 요청 방식이에요.");
  }
  if (p === "/api/v1/child-mode/pin/verify" && m === "POST") return pinVerify(request, db, env);

  return null;   // 우리 것이 아니다
}
