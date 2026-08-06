// ================= 주문·결제 API (블록2) =================
// 계약: docs/API계약-v1.md §6 · 정본설계 v1 §5
//
// 지난 실수의 정확한 위치: "더미를 둔 것"이 아니라 **주문·입금대기·확인·활성이라는 구조 자체가 없이**
// PAYMENTS_DISABLED=true로 막아둔 것이었다. 이번엔 상태기계를 진짜로 만들고 결제수단만 갈아끼운다.
//
// method가 플러그다 — mock | bank_transfer | pg | google_iap 넷이 **같은 전이를 탄다**.
// PG를 붙일 때 상태기계는 손대지 않는다.

import { apiOk, apiList, apiErr, validate, readJson } from "./api_core.js";
import { resolveAuth, verifyReauth } from "./auth_core.js";

// ── 가격 (계약 §6.4) ────────────────────────────────────────
// **자녀 1명당** 가격이다(정본 §5 자녀별 과금). 가족 단일가가 아니다.
// 회신18에서 1개월 1만원 확정, 나머지는 작업 기준값. 기간권이라 이 상수 하나로 다음 구매분부터 조정된다.
// ⚠ 앱(app.js STUB.plans)과 **같은 값이어야 한다.** 다르면 결제 금액이 화면과 어긋난다.
//    2026-07-28 인하: 월 10,000 → 2,900 (시장 조사 — 경쟁 앱이 전부 무료)
export const PLAN_PRICES = { 1: 2900, 3: 7900, 6: 14900, 12: 25000 };
const PLAN_DISCOUNT = { 1: null, 3: "10% 할인", 6: "15% 할인", 12: "20% 할인" };

/* ── 둘째부터 싸게 (2026-08-01) ─────────────────────────────
   자녀별 과금은 그대로 둔다 — 성적·기록은 아이마다 다른 개인 자료라 한 장으로 나눠 쓸 수 없다.
   대신 자녀가 둘·셋이면 부담이 2배·3배로 뛰는 게 문제였다(월 8,700원). 순번마다 값을 낮춘다.
     누적 월액 = 1명 2,900 · 2명 4,900 · 3명 6,400   (둘째 +2,000 · 셋째 +1,500)
   기간권도 첫째와 같은 할인 비율을 태워 100원 단위로 맞췄다.
   ⚠ 앱(app.js PLAN_SEATS)과 **같은 값이어야 한다.** 다르면 화면과 결제 금액이 어긋난다. */
const PLAN_PRICES_BY_SEAT = {
  1: { 1: 2900, 3: 7900, 6: 14900, 12: 25000 },
  2: { 1: 2000, 3: 5400, 6: 10300, 12: 17200 },
  3: { 1: 1500, 3: 4100, 6:  7700, 12: 12900 },
};
const MAX_SEAT = 3;

/* 이 자녀가 몇 번째 자리인가 — **이 자녀 말고** 이용권이 살아 있는 자녀 수 + 1.
   그 자녀 자신은 세지 않는다(연장할 때 자기 때문에 한 칸 밀리면 안 된다).
   첫째 이용권이 끝나면 남은 아이가 다시 1번 자리(정가)가 된다 — 하나만 쓰면 정가가 맞다. */
async function seatOf(db, accountId, childId) {
  const now = new Date().toISOString();
  const row = await db.prepare(
    `SELECT COUNT(DISTINCT child_id) AS n FROM orders
      WHERE account_id = ? AND child_id != ? AND status = 'active' AND expires_at > ?`
  ).bind(accountId, childId, now).first();
  return Math.min(MAX_SEAT, ((row && row.n) || 0) + 1);
}

const priceOf = (seat, months) => (PLAN_PRICES_BY_SEAT[seat] || PLAN_PRICES_BY_SEAT[1])[months];

const METHODS = ["mock", "bank_transfer", "pg", "google_iap"];

// ── 상태 전이표 (계약 §6.1) ─────────────────────────────────
// 여기 없는 전이는 전부 거부한다. 상태를 코드 여기저기서 바꾸면 추적이 안 된다.
const TRANSITIONS = {
  pending:           ["awaiting_deposit", "active", "cancelled"], // mock은 pending→active 직행
  awaiting_deposit:  ["confirmed", "cancelled"],
  confirmed:         ["active"],
  active:            ["expired"],
  expired:           [],
  cancelled:         [],
};
function canTransit(from, to) {
  return (TRANSITIONS[from] || []).includes(to);
}

function publicOrder(o) {
  return {
    id: o.id,
    child_id: o.child_id,
    months: o.months,
    amount: o.amount,
    method: o.method,
    status: o.status,
    payer_name: o.payer_name,
    created_at: o.created_at,
    confirmed_at: o.confirmed_at,
    activated_at: o.activated_at,
    expires_at: o.expires_at,
  };
}

// ── 이용권 판정 (계약 §6.3) — **"유료인가"의 유일한 정의** ──────
// 블록5(api_records.js)가 상한을 계산할 때 이 함수를 부른다. orders를 저쪽에서 직접 조회하면
// 정의가 두 벌이 되고, 상태 전이가 바뀔 때 한쪽만 고쳐진다.
//
// 🔴 `children.trial_expires_at`으로 판정하면 안 된다 — 자녀 등록 시 붙는 **7일 무료체험**이
//    같은 칸에 섞여 있어서 체험자가 유료 상한을 전부 쓰게 된다(회신20 §4).
//    `activate()`가 저 칸을 연장하는 건 "이용 만료일 표시"용이고, **결제 사실의 근거는 orders다.**
//
// `expires_at`을 함께 보는 이유: active → expired 전이를 돌리는 배치가 없어서
// 기간이 끝나도 상태는 'active'로 남는다. 만료일을 안 보면 영구 이용권이 된다.
//
// childId를 주면 그 자녀 것만 본다(자녀별 과금). 없으면 계정에 유효한 이용권이 하나라도 있는지.
export async function hasActivePass(db, accountId, childId = null) {
  // 쿠키만 있는 레거시 사용자는 계정이 없다 → 무료. 로그인하면 accounts가 생기며 열린다(정본 §4 승계).
  if (!accountId) return false;
  const now = new Date().toISOString();
  const row = childId == null
    ? await db
        .prepare("SELECT 1 FROM orders WHERE account_id = ? AND status = 'active' AND expires_at > ? LIMIT 1")
        .bind(accountId, now)
        .first()
    : await db
        .prepare("SELECT 1 FROM orders WHERE account_id = ? AND child_id = ? AND status = 'active' AND expires_at > ? LIMIT 1")
        .bind(accountId, childId, now)
        .first();
  return !!row;
}

// ── 인증 (계약 §1.4) ────────────────────────────────────────
function readCookie(request, name) {
  const raw = request.headers.get("Cookie") || "";
  for (const part of raw.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

async function requireAccount(request, db, env) {
  const auth = await resolveAuth(request, db, env, readCookie);
  if (auth.error) return { err: apiErr(auth.error) };
  if (!auth.account) return { err: apiErr("AUTH_REQUIRED") };
  return { account: auth.account };
}

// ── GET /api/v1/plans — 상품 목록 ───────────────────────────
// 회신18: "표시용으로만 노출 OK. 1차는 모의결제라 실결제 연결 없음 → 정책 리스크 없음."
// child_id 를 주면 **그 자녀의 자리값**으로 계산해서 돌려준다. 안 주면 첫째 기준(정가).
async function plans(request, db, env, url) {
  let seat = 1;
  const childId = parseInt(url?.searchParams.get("child_id") || "", 10);
  if (Number.isFinite(childId)) {
    const auth = await resolveAuth(request, db, env, readCookie);
    if (auth.account) {
      const child = await db.prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?")
        .bind(childId, auth.account.owner_token).first();
      if (child) seat = await seatOf(db, auth.account.id, childId);
    }
  }
  return apiList(
    [1, 3, 6, 12].map((m) => ({
      months: m,
      amount: priceOf(seat, m),
      list_amount: PLAN_PRICES[m],                 // 정가 — 화면에서 취소선으로 보여준다
      discount: PLAN_DISCOUNT[m],
      per_month: Math.round(priceOf(seat, m) / m),
    })),
    { seat, note: seat > 1 ? `${seat}번째 자녀라 더 저렴해요.` : "자녀 1명당 가격입니다." }
  );
}

// ── POST /api/v1/orders — 주문 생성 ─────────────────────────
async function createOrder(request, db, env) {
  const { account, err } = await requireAccount(request, db, env);
  if (err) return err;

  const b = await readJson(request);
  if (!b) return apiErr("VALIDATION", { fields: { body: "JSON 본문이 필요해요." } });

  const months = parseInt(b.months, 10);
  const method = String(b.method || "bank_transfer");
  const childId = b.child_id != null ? parseInt(b.child_id, 10) : null;
  const payerName = String(b.payer_name || "").trim().slice(0, 30);

  const fields = validate([
    ["months", PLAN_PRICES[months] != null, "이용 기간을 선택해 주세요."],
    ["method", METHODS.includes(method), "결제 수단을 확인해 주세요."],
    ["child_id", Number.isFinite(childId), "자녀를 선택해 주세요."],
  ]);
  if (fields) return apiErr("VALIDATION", { fields });

  // 자녀별 과금이라 **그 자녀가 내 것인지** 반드시 확인한다. 남의 자녀에 결제를 걸 수 없다.
  const child = await db
    .prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?")
    .bind(childId, account.owner_token)
    .first();
  if (!child) return apiErr("NOT_FOUND");

  // mock은 개발·검증용이라 DEV_TOOLS 뒤에서만 허용한다. 운영에 새어나가면 공짜 이용권이 된다.
  if (method === "mock" && env.DEV_TOOLS !== "true") {
    return apiErr("VALIDATION", { fields: { method: "사용할 수 없는 결제 수단이에요." } });
  }

  const now = new Date().toISOString();
  // 무통장은 곧장 입금대기로 간다 — 사용자가 계좌를 보고 송금해야 하므로.
  const status = method === "bank_transfer" ? "awaiting_deposit" : "pending";

  // 값은 **서버가 정한다.** 앱이 보낸 금액을 믿으면 100원짜리 주문이 들어온다.
  const seat = await seatOf(db, account.id, childId);
  const amount = priceOf(seat, months);

  const r = await db
    .prepare(
      `INSERT INTO orders (account_id, child_id, months, amount, method, status, payer_name, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(account.id, childId, months, amount, method, status, payerName || null, now, now)
    .run();

  const order = await db.prepare("SELECT * FROM orders WHERE id = ?").bind(r.meta.last_row_id).first();
  return apiOk({ order: publicOrder(order), bank: status === "awaiting_deposit" ? bankInfo() : null }, 201);
}

// 입금 계좌 안내. 사업자 정보가 아직 없어 자리만 만들어 둔다(정본 §12 대표님 대기 항목).
function bankInfo() {
  return { bank: "(준비 중)", account_no: "(준비 중)", holder: "(준비 중)", note: "입금자명을 주문자와 같게 해주세요." };
}

// ── GET /api/v1/orders ──────────────────────────────────────
async function listOrders(request, db, env) {
  const { account, err } = await requireAccount(request, db, env);
  if (err) return err;
  const { results } = await db
    .prepare("SELECT * FROM orders WHERE account_id = ? ORDER BY created_at DESC LIMIT 100")
    .bind(account.id)
    .all();
  return apiList(results.map(publicOrder));
}

// ── GET /api/v1/orders/{id} ─────────────────────────────────
async function getOrder(request, db, env, id) {
  const { account, err } = await requireAccount(request, db, env);
  if (err) return err;
  const o = await db.prepare("SELECT * FROM orders WHERE id = ? AND account_id = ?").bind(id, account.id).first();
  if (!o) return apiErr("NOT_FOUND"); // 남의 주문도 404 — 존재 여부를 숨긴다(계약 §1.3)
  return apiOk({ order: publicOrder(o), bank: o.status === "awaiting_deposit" ? bankInfo() : null });
}

// ── POST /api/v1/orders/{id}/cancel ─────────────────────────
async function cancelOrder(request, db, env, id) {
  const { account, err } = await requireAccount(request, db, env);
  if (err) return err;
  const o = await db.prepare("SELECT * FROM orders WHERE id = ? AND account_id = ?").bind(id, account.id).first();
  if (!o) return apiErr("NOT_FOUND");
  if (!canTransit(o.status, "cancelled")) {
    return apiErr("PAYMENT_STATE", { status: o.status }, "이미 처리된 주문은 취소할 수 없어요.");
  }
  const now = new Date().toISOString();
  await db.prepare("UPDATE orders SET status='cancelled', updated_at=? WHERE id=?").bind(now, id).run();
  const after = await db.prepare("SELECT * FROM orders WHERE id=?").bind(id).first();
  return apiOk({ order: publicOrder(after) });
}

// ── 이용권 활성 (계약 §6.3) ─────────────────────────────────
// active 전이 시 children.trial_expires_at을 연장한다.
// **기존 만료일이 남아 있으면 그 뒤에 이어붙인다** — 남은 기간을 버리지 않는다.
// 자녀별 과금이라 orders.child_id의 자녀만 연장된다.
async function activate(db, order) {
  const now = Date.now();
  const child = await db.prepare("SELECT trial_expires_at FROM children WHERE id = ?").bind(order.child_id).first();
  let base = now;
  if (child && child.trial_expires_at) {
    const t = new Date(child.trial_expires_at).getTime();
    if (t > base) base = t;
  }
  const d = new Date(base);
  d.setUTCMonth(d.getUTCMonth() + order.months);
  const expires = d.toISOString();
  const nowIso = new Date().toISOString();

  await db.batch([
    db.prepare("UPDATE children SET trial_expires_at = ? WHERE id = ?").bind(expires, order.child_id),
    db.prepare("UPDATE orders SET status='active', activated_at=?, expires_at=?, updated_at=? WHERE id=?")
      .bind(nowIso, expires, nowIso, order.id),
  ]);
  return expires;
}

// ── POST /api/v1/orders/{id}/mock-pay — 모의결제 ────────────
// 정본 §5 "테스트 = 버튼 딸깍 모의결제". 실제 돈이 안 오간다.
// DEV_TOOLS 뒤에서만 산다 — 운영에 새어나가면 공짜 이용권이 된다.
async function mockPay(request, db, env, id) {
  if (env.DEV_TOOLS !== "true") return apiErr("NOT_FOUND");
  const { account, err } = await requireAccount(request, db, env);
  if (err) return err;
  const o = await db.prepare("SELECT * FROM orders WHERE id = ? AND account_id = ?").bind(id, account.id).first();
  if (!o) return apiErr("NOT_FOUND");
  if (!canTransit(o.status, "active")) {
    return apiErr("PAYMENT_STATE", { status: o.status }, "지금은 결제할 수 없는 상태예요.");
  }
  const expires = await activate(db, o);
  const after = await db.prepare("SELECT * FROM orders WHERE id=?").bind(id).first();
  return apiOk({ order: publicOrder(after), pass_expires_at: expires });
}

/* ── POST /api/v1/billing/verify — 구글 인앱결제 확인 (2026-07-31 틀) ──
   앱이 «샀다»고 말한 것을 **믿지 않는다.** 구매 토큰을 구글에 물어 진짜인지 확인한 뒤에만 이용권을 켠다.
   (안 하면 위조 요청 한 번으로 누구나 공짜 이용권을 얻는다 — 인앱결제 사고의 1번 원인)

   지금은 **자리만** 있다: GOOGLE_PLAY_SA(서비스 계정 JSON)가 설정되면 verifyGooglePurchase() 안이 채워진다.
   그 전까지는 검증을 통과시키지 않는다 — 열어두면 그게 곧 구멍이다.

   흐름: 상품ID→개월수 → 토큰 중복 확인(재사용 차단) → 구글 확인 → orders 기록 → activate() 로 연장. */
const IAP_PRODUCTS = { pass_1m: 1, pass_3m: 3, pass_6m: 6, pass_12m: 12 };

async function verifyGooglePurchase(env, productId, token) {
  // 서비스 계정이 없으면 «확인 불가» — 통과시키지 않는다.
  if (!env.GOOGLE_PLAY_SA) return { ok: false, reason: "not_configured" };
  /* TODO(계정 열리면):
       ① 서비스 계정 JWT → OAuth 액세스 토큰
       ② GET androidpublisher/v3/applications/com.eduthink.app/purchases/products/{productId}/tokens/{token}
       ③ purchaseState===0(구매완료) && consumptionState 확인 → { ok:true, orderId }
       ④ 소모성이면 consume 까지 (안 하면 같은 상품을 다시 못 산다) */
  return { ok: false, reason: "not_implemented" };
}

async function billingVerify(request, db, env) {
  const { account, err } = await requireAccount(request, db, env);
  if (err) return err;
  const b = await readJson(request);
  if (!b) return apiErr("VALIDATION", { fields: { body: "JSON 본문이 필요해요." } });

  const productId = String(b.product_id || "");
  const token = String(b.purchase_token || "");
  const childId = b.child_id != null ? parseInt(b.child_id, 10) : null;
  const months = IAP_PRODUCTS[productId];

  const fields = validate([
    ["product_id", !!months, "알 수 없는 상품이에요."],
    ["purchase_token", token.length > 10, "구매 정보를 확인할 수 없어요."],
    ["child_id", Number.isFinite(childId), "자녀를 선택해 주세요."],
  ]);
  if (fields) return apiErr("VALIDATION", { fields });

  // 남의 자녀에 이용권을 걸 수 없다
  const child = await db.prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?")
    .bind(childId, account.owner_token).first();
  if (!child) return apiErr("NOT_FOUND");

  // 같은 구매 토큰을 두 번 쓰지 못하게 — 한 번 결제로 여러 번 연장하는 것을 막는다
  const dup = await db.prepare("SELECT id FROM orders WHERE provider_token = ?").bind(token).first();
  if (dup) return apiErr("PAYMENT_STATE", { order_id: dup.id }, "이미 처리된 결제예요.");

  const v = await verifyGooglePurchase(env, productId, token);
  if (!v.ok) {
    return apiErr("PAYMENT_STATE", { reason: v.reason },
      v.reason === "not_configured" ? "결제 확인 준비가 끝나지 않았어요. 잠시 후 다시 시도해 주세요." : "결제를 확인하지 못했어요.");
  }

  const now = new Date().toISOString();
  /* ⚠ 인앱결제는 **구글이 받은 금액**이 진짜다. 여기 amount 는 우리 장부용 기록이라
     자리값으로 계산해 둔다. 실제 청구액과 어긋나지 않으려면 Play Console 상품 가격도
     자리별로 나눠 등록해야 한다(pass_1m_2 처럼) — 계정이 열리면 그때 맞춘다. */
  const seat = await seatOf(db, account.id, childId);
  const r = await db.prepare(
    `INSERT INTO orders (account_id, child_id, months, amount, method, status, provider_token, created_at, updated_at)
     VALUES (?, ?, ?, ?, 'google_iap', 'pending', ?, ?, ?)`
  ).bind(account.id, childId, months, priceOf(seat, months), token, now, now).run();

  const order = await db.prepare("SELECT * FROM orders WHERE id = ?").bind(r.meta.last_row_id).first();
  const expires = await activate(db, order);
  const after = await db.prepare("SELECT * FROM orders WHERE id=?").bind(order.id).first();
  return apiOk({ order: publicOrder(after), expires_at: expires });
}

/* ── 입금 확인 (관리자) ──────────────────────────────────────
   무통장 흐름의 핵심. 관리자가 통장을 보고 확인 → 이용권 활성.
   실제 PG가 붙으면 이 자리를 웹훅이 대신한다(같은 activate를 부른다).

   ⚠ 상태 전이는 **여기 한 곳**에서만 한다 — API(/api/v1/admin/orders/…)와 관리자 화면(/admin/orders)이
   같은 함수를 부른다. 화면 쪽에서 UPDATE를 따로 쓰면 전이표를 우회해 «취소된 주문이 이용중»이 된다. */
export async function confirmOrderByAdmin(db, id) {
  const o = await db.prepare("SELECT * FROM orders WHERE id = ?").bind(id).first();
  if (!o) return { ok: false, reason: "not_found" };

  const nowIso = new Date().toISOString();
  // 무통장만 confirmed 를 거친다. pending(모의·PG·인앱)은 전이표상 active 로 직행한다.
  if (o.status === "awaiting_deposit") {
    await db.prepare("UPDATE orders SET status='confirmed', confirmed_by='admin', confirmed_at=?, updated_at=? WHERE id=?")
      .bind(nowIso, nowIso, id).run();
    o.status = "confirmed";
  }
  if (!canTransit(o.status, "active")) return { ok: false, reason: "state", status: o.status };
  const expires = await activate(db, o);
  return { ok: true, expires };
}

// 관리자 취소 — 아직 이용권이 안 켜진 주문만. active 를 되돌리는 길은 두지 않는다(만료일 조정으로 처리).
export async function cancelOrderByAdmin(db, id) {
  const o = await db.prepare("SELECT * FROM orders WHERE id = ?").bind(id).first();
  if (!o) return { ok: false, reason: "not_found" };
  if (!canTransit(o.status, "cancelled")) return { ok: false, reason: "state", status: o.status };
  const now = new Date().toISOString();
  await db.prepare("UPDATE orders SET status='cancelled', updated_at=? WHERE id=?").bind(now, id).run();
  return { ok: true };
}

// ── POST /api/v1/admin/orders/{id}/confirm ──────────────────
async function adminConfirm(request, db, env, id, isAdmin) {
  if (!isAdmin) return apiErr("FORBIDDEN");
  const r = await confirmOrderByAdmin(db, id);
  if (!r.ok) {
    if (r.reason === "not_found") return apiErr("NOT_FOUND");
    return apiErr("PAYMENT_STATE", { status: r.status }, "확인할 수 없는 상태예요.");
  }
  const after = await db.prepare("SELECT * FROM orders WHERE id=?").bind(id).first();
  return apiOk({ order: publicOrder(after), pass_expires_at: r.expires });
}

// ── 라우터 ──────────────────────────────────────────────────
export async function handleOrdersApi(request, db, env, url, isAdmin = false) {
  const p = url.pathname;
  const m = request.method;

  if (p === "/api/v1/plans" && m === "GET") return plans(request, db, env, url);
  if (p === "/api/v1/billing/verify" && m === "POST") return billingVerify(request, db, env);
  if (p === "/api/v1/orders" && m === "GET") return listOrders(request, db, env);
  if (p === "/api/v1/orders" && m === "POST") return createOrder(request, db, env);

  const mMock = p.match(/^\/api\/v1\/orders\/(\d+)\/mock-pay$/);
  if (mMock && m === "POST") return mockPay(request, db, env, mMock[1]);

  const mCancel = p.match(/^\/api\/v1\/orders\/(\d+)\/cancel$/);
  if (mCancel && m === "POST") return cancelOrder(request, db, env, mCancel[1]);

  const mConfirm = p.match(/^\/api\/v1\/admin\/orders\/(\d+)\/confirm$/);
  if (mConfirm && m === "POST") return adminConfirm(request, db, env, mConfirm[1], isAdmin);

  const mGet = p.match(/^\/api\/v1\/orders\/(\d+)$/);
  if (mGet && m === "GET") return getOrder(request, db, env, mGet[1]);

  return apiErr("NOT_FOUND");
}
