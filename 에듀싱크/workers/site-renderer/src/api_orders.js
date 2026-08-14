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
/* 🔴 2026-08-14 대표님 확정 — «1자녀 / 패밀리» 2단. 자녀 자리별 차등(2,900/2,000/1,500)은 폐기.
   ─ 1자녀 월 5,900 · 패밀리(자녀 3명까지) 월 9,900
   ─ 기간 할인은 «할인율»이 아니라 «무료 개월»로 말한다 — 16.7%보다 「2개월 무료」가 잘 팔린다
       3개월 = 약 1주 덤 · 6개월 = 약 보름 덤 · **12개월 = 딱 10개월 값(2개월 무료)**
   ─ 3·6개월 할인폭을 일부러 작게 뒀다. 계단이 12개월로 몰려야 장기 결제가 는다
   ⚠ 앱(app.js STUB.plans)과 **같은 값이어야 한다.** 다르면 화면과 청구액이 어긋난다 */
export const PLAN_PRICES = { 1: 5900, 3: 16900, 6: 32900, 12: 59000 };
const PLAN_DISCOUNT = { 1: null, 3: "1주 덤", 6: "보름 덤", 12: "2개월 무료" };

/* ── 티어 «1자녀 / 패밀리» (2026-08-14 대표님 확정) ───────────────
   자녀 자리별 차등(2,900/2,000/1,500)을 버리고 두 갈래로 바꿨다.
   ─ 이유 ①: 원가가 자녀 수와 거의 무관하다. NEIS 조회는 **학교 단위**라 형제는 같은 자료를 쓴다
   ─ 이유 ②: 「월 5,900원, 아이 몇이든 9,900원」이 한 줄로 설명된다. 자리별 할인표는 설명이 길다
   ─ 이유 ③: 자녀 2명이면 5,900×2=11,800 > 9,900 이라 **2명부터 패밀리가 저절로 이득**이 된다
   ⚠ 앱(app.js STUB.plans·PLAN_FAMILY)과 **같은 값이어야 한다.** */
export const PLAN_PRICES_FAMILY = { 1: 9900, 3: 27900, 6: 54900, 12: 99000 };
const FAMILY_MAX_CHILDREN = 3;   // 패밀리 한 장으로 덮는 자녀 수(MAX_CHILDREN 과 같게)

/* 이 계정이 «패밀리»인가 — 이용권이 살아 있는 다른 자녀가 있으면 패밀리 값으로 본다.
   ⚠ 자기 자신은 안 센다(연장할 때 자기 때문에 티어가 바뀌면 안 된다).
   혼자만 쓰면 다시 1자녀 값이 된다 — 하나만 쓰는 집에 패밀리 값을 물리지 않는다. */
async function isFamily(db, accountId, childId) {
  const now = new Date().toISOString();
  const row = await db.prepare(
    `SELECT COUNT(DISTINCT child_id) AS n FROM orders
      WHERE account_id = ? AND child_id != ? AND status = 'active' AND expires_at > ?`
  ).bind(accountId, childId, now).first();
  return ((row && row.n) || 0) > 0;
}

const priceOf = (family, months) => (family ? PLAN_PRICES_FAMILY : PLAN_PRICES)[months];

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
  let family = false;
  const childId = parseInt(url?.searchParams.get("child_id") || "", 10);
  if (Number.isFinite(childId)) {
    const auth = await resolveAuth(request, db, env, readCookie);
    if (auth.account) {
      const child = await db.prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?")
        .bind(childId, auth.account.owner_token).first();
      if (child) family = await isFamily(db, auth.account.id, childId);
    }
  }
  return apiList(
    [1, 3, 6, 12].map((m) => ({
      months: m,
      amount: priceOf(family, m),
      list_amount: PLAN_PRICES[m],                 // 정가 — 화면에서 취소선으로 보여준다
      discount: PLAN_DISCOUNT[m],
      per_month: Math.round(priceOf(family, m) / m),
    })),
    { family,
      tier: family ? "family" : "single",
      note: family
        ? `패밀리 이용권이에요 — 자녀 ${FAMILY_MAX_CHILDREN}명까지 한 장으로 씁니다.`
        : "자녀 1명 기준이에요. 둘째부터는 패밀리가 더 저렴해요." }
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
  const family = await isFamily(db, account.id, childId);
  const amount = priceOf(family, months);

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
/* 🔴 2026-08-14 — 가격이 «1자녀 / 패밀리» 2단이 되면서 상품도 **8개**가 됐다(4개 → 8개).
   Play Console 에 아래 ID 그대로 등록한다. 상품 ID 는 한 번 만들면 못 바꾸니 오타 주의.
   ⚠ 개월수만 보고 값을 정하면 안 된다 — 패밀리 상품인지도 같이 봐야 청구액이 맞다. */
const IAP_PRODUCTS = {
  pass_1m: 1, pass_3m: 3, pass_6m: 6, pass_12m: 12,                       // 1자녀
  pass_family_1m: 1, pass_family_3m: 3, pass_family_6m: 6, pass_family_12m: 12,  // 패밀리
};
const IAP_IS_FAMILY = (productId) => String(productId).includes("_family_");

const PLAY_PKG = "com.eduthink.app";
const PLAY_SCOPE = "https://www.googleapis.com/auth/androidpublisher";

/* 액세스 토큰은 1시간짜리다 — 요청마다 새로 받으면 느리고 구글 쿼터를 태운다.
   워커 인스턴스가 살아 있는 동안만 들고 있는다(죽으면 다시 받는다). */
let _playTok = { v: null, exp: 0 };

const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)))
  .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const b64urlStr = (s) => b64url(new TextEncoder().encode(s));

/* PEM(PKCS#8) → CryptoKey. 서비스 계정 JSON 의 private_key 는 줄바꿈이 escape 된 채로 온다. */
async function importPkcs8(pem) {
  const body = String(pem).replace(/\\n/g, String.fromCharCode(10))
    .replace(/-----[A-Z ]+-----/g, "").replace(/\s+/g, "");
  const raw = Uint8Array.from(atob(body), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey("pkcs8", raw.buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
}

/* 서비스 계정 → OAuth 액세스 토큰 (JWT bearer).
   ⚠ 실패를 «성공»으로 흘리지 않는다 — 여기서 새면 그게 곧 공짜 이용권이다. */
async function playAccessToken(env) {
  const now = Math.floor(Date.now() / 1000);
  if (_playTok.v && _playTok.exp > now + 60) return _playTok.v;

  let sa;
  try { sa = JSON.parse(env.GOOGLE_PLAY_SA); } catch { return null; }
  if (!sa || !sa.client_email || !sa.private_key) return null;

  const head = b64urlStr(JSON.stringify({ alg: "RS256", typ: "JWT" }));
  const claim = b64urlStr(JSON.stringify({
    iss: sa.client_email, scope: PLAY_SCOPE,
    aud: "https://oauth2.googleapis.com/token", iat: now, exp: now + 3600,
  }));
  let jwt;
  try {
    const key = await importPkcs8(sa.private_key);
    const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key,
      new TextEncoder().encode(head + "." + claim));
    jwt = head + "." + claim + "." + b64url(sig);
  } catch (e) { console.error("[iap/jwt]", e && e.message); return null; }

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  let res;
  try {
    res = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST", signal: ctrl.signal,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=" + encodeURIComponent(jwt),
    });
  } catch { return null; } finally { clearTimeout(timer); }
  if (!res.ok) { console.error("[iap/token]", res.status); return null; }
  const j = await res.json().catch(() => null);
  if (!j || !j.access_token) return null;
  _playTok = { v: j.access_token, exp: now + (j.expires_in || 3600) };
  return j.access_token;
}

/* 구글에 «이 영수증이 진짜인가»를 묻는다.
   ⚠ **여기가 결제의 마지막 관문**이다. 통과시키는 조건을 넓히면 그만큼 공짜가 샌다.
     · purchaseState 0 = 구매완료. 1 = 취소, 2 = 보류(가족 승인 대기 등) → 둘 다 거절.
     · acknowledgementState 는 확인만 하고 막지 않는다 — 우리가 곧 승인할 것이라서.
   ⚠ 서비스 계정이 없거나 구글이 답을 안 주면 **거절**한다. 열어 두면 그게 곧 구멍이다. */
async function verifyGooglePurchase(env, productId, token) {
  if (!env.GOOGLE_PLAY_SA) return { ok: false, reason: "not_configured" };
  const at = await playAccessToken(env);
  if (!at) return { ok: false, reason: "auth_failed" };

  const url = `https://androidpublisher.googleapis.com/androidpublisher/v3/applications/${PLAY_PKG}`
    + `/purchases/products/${encodeURIComponent(productId)}/tokens/${encodeURIComponent(token)}`;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  let res;
  try { res = await fetch(url, { headers: { Authorization: "Bearer " + at }, signal: ctrl.signal }); }
  catch { return { ok: false, reason: "network" }; }
  finally { clearTimeout(timer); }

  if (res.status === 404) return { ok: false, reason: "not_found" };   // 없는 영수증
  if (!res.ok) { console.error("[iap/verify]", res.status); return { ok: false, reason: "http_" + res.status }; }
  const j = await res.json().catch(() => null);
  if (!j) return { ok: false, reason: "bad_json" };
  if (j.purchaseState !== 0) return { ok: false, reason: "state_" + j.purchaseState };
  return { ok: true, orderId: j.orderId || null, acknowledged: j.acknowledgementState === 1 };
}

/* 승인(acknowledge) — 3일 안에 안 하면 구글이 **자동 환불**한다.
   ⚠ 실패해도 이용권은 이미 켰다. 여기서 되돌리면 돈 낸 사람이 못 쓴다 —
     로그만 남기고 넘어간다(실패하면 환불되니 손해는 우리가 아니라 우리 쪽 매출이다). */
async function ackGooglePurchase(env, productId, token) {
  const at = await playAccessToken(env);
  if (!at) return false;
  const url = `https://androidpublisher.googleapis.com/androidpublisher/v3/applications/${PLAY_PKG}`
    + `/purchases/products/${encodeURIComponent(productId)}/tokens/${encodeURIComponent(token)}:acknowledge`;
  try {
    const r = await fetch(url, { method: "POST",
      headers: { Authorization: "Bearer " + at, "Content-Type": "application/json" }, body: "{}" });
    if (!r.ok) console.error("[iap/ack]", r.status);
    return r.ok;
  } catch (e) { console.error("[iap/ack]", e && e.message); return false; }
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
  /* ⚠ 인앱결제는 **구글이 받은 금액**이 진짜다. 여기 amount 는 우리 장부용 기록이다.
     티어는 «계정 상태»가 아니라 **산 상품 ID**로 정한다 — 사용자가 패밀리 상품을 샀으면
     그 값으로 적어야 구글 영수증과 우리 장부가 맞는다(계정 상태로 재계산하면 어긋난다). */
  const family = IAP_IS_FAMILY(productId);
  const r = await db.prepare(
    `INSERT INTO orders (account_id, child_id, months, amount, method, status, provider_token, created_at, updated_at)
     VALUES (?, ?, ?, ?, 'google_iap', 'pending', ?, ?, ?)`
  ).bind(account.id, childId, months, priceOf(family, months), token, now, now).run();

  const order = await db.prepare("SELECT * FROM orders WHERE id = ?").bind(r.meta.last_row_id).first();
  const expires = await activate(db, order);
  /* 🔴 **승인(acknowledge)을 안 하면 구글이 3일 뒤 자동 환불한다.**
     이용권을 켠 «뒤에» 부른다 — 승인부터 하고 켜다가 실패하면 돈은 받고 못 쓰게 된다. */
  if (!v.acknowledged) await ackGooglePurchase(env, productId, token);
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
