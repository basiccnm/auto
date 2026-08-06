// ================= 고객센터 문의 API (2026-08-01) =================
// 계약: docs/API계약-v1.md §7(신설)
//
// 왜 표를 새로 두나 — info_reports(학교 정보 오류)·beta_feedback(베타 의견)은 **받기만** 한다.
// 고객센터는 답이 사용자에게 돌아가야 한다. 저 두 표에 answer 칸을 덧붙이지 않는 이유는
// 「급식이 틀렸다」와 「결제가 안 된다」가 처리하는 사람도 순서도 다르기 때문이다.
// 한 목록에 섞으면 관리자가 둘 다 놓친다.
//
// 흐름: 앱에서 등록 → 관리자 탭에 open 으로 뜸 → 답변 저장(answered) → 앱이 안 읽은 답 배지 →
//       사용자가 열어보면 seen_at 기록 → 배지 사라짐.

import { apiOk, apiList, apiErr, validate, readJson } from "./api_core.js";
import { resolveAuth } from "./auth_core.js";

// 앱의 「문의 종류」와 같은 값이어야 한다(app.js ASK_CATS). 모르는 값이 오면 other 로 떨어뜨린다.
const CATEGORIES = ["data", "record", "payment", "account", "bug", "other"];

const TITLE_MAX = 60;
const BODY_MAX = 2000;
const META_MAX = 500;
// 한 계정이 하루에 넣을 수 있는 문의 수 — 실수로 연타하거나 자동으로 쏟아지는 것을 막는다.
const DAY_LIMIT = 20;

function publicInquiry(r, { withBody = true } = {}) {
  return {
    id: r.id,
    category: r.category,
    title: r.title,
    ...(withBody ? { body: r.body } : {}),
    status: r.status,
    answer: r.answer || null,
    answered_at: r.answered_at || null,
    seen_at: r.seen_at || null,
    created_at: r.created_at,
  };
}

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

// ── POST /api/v1/inquiries — 문의 등록 ──────────────────────
async function createInquiry(request, db, env) {
  const { account, err } = await requireAccount(request, db, env);
  if (err) return err;

  const b = await readJson(request);
  if (!b) return apiErr("VALIDATION", { fields: { body: "JSON 본문이 필요해요." } });

  const title = String(b.title || "").trim().slice(0, TITLE_MAX);
  const body = String(b.body || "").trim().slice(0, BODY_MAX);
  const category = CATEGORIES.includes(String(b.category)) ? String(b.category) : "other";
  const email = String(b.contact_email || "").trim().slice(0, 120);
  const childId = b.child_id != null ? parseInt(b.child_id, 10) : null;

  const fields = validate([
    ["title", title.length >= 2, "제목을 2자 이상 적어 주세요."],
    ["body", body.length >= 5, "문의 내용을 조금만 더 적어 주세요."],
    ["contact_email", !email || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email), "이메일 주소를 확인해 주세요."],
  ]);
  if (fields) return apiErr("VALIDATION", { fields });

  // 남의 자녀를 붙일 수 없다. 내 자녀가 아니면 그냥 «자녀 없음»으로 받는다(문의 자체를 막을 이유는 없다).
  let child = null;
  if (Number.isFinite(childId)) {
    const c = await db.prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?")
      .bind(childId, account.owner_token).first();
    if (c) child = c.id;
  }

  const since = new Date(Date.now() - 86400000).toISOString();
  const n = await db.prepare("SELECT COUNT(*) AS n FROM inquiries WHERE account_id = ? AND created_at > ?")
    .bind(account.id, since).first();
  if ((n?.n || 0) >= DAY_LIMIT) {
    return apiErr("LIMIT_EXCEEDED", null, "오늘 접수한 문의가 많아요. 기존 문의에 이어서 적어 주세요.");
  }

  // meta 는 «제 폰에선 안 돼요»를 되묻지 않으려고 받는다. 사용자가 넣은 값을 그대로 믿지 않고 길이만 자른다.
  let meta = null;
  if (b.meta && typeof b.meta === "object") {
    try { meta = JSON.stringify(b.meta).slice(0, META_MAX); } catch (_) { meta = null; }
  }

  const now = new Date().toISOString();
  const r = await db.prepare(
    `INSERT INTO inquiries (account_id, child_id, category, title, body, meta, contact_email, status, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)`
  ).bind(account.id, child, category, title, body, meta, email || null, now, now).run();

  const row = await db.prepare("SELECT * FROM inquiries WHERE id = ?").bind(r.meta.last_row_id).first();
  return apiOk({ inquiry: publicInquiry(row) }, 201);
}

// ── GET /api/v1/inquiries — 내 문의 목록 ────────────────────
// 목록에는 본문을 안 싣는다 — 목록 화면은 제목·상태만 쓴다. 상세에서 받아간다.
async function listInquiries(request, db, env) {
  const { account, err } = await requireAccount(request, db, env);
  if (err) return err;
  const { results } = await db.prepare(
    "SELECT * FROM inquiries WHERE account_id = ? ORDER BY created_at DESC LIMIT 100"
  ).bind(account.id).all();
  // 안 읽은 답 개수 — 앱이 이 숫자로 배지를 띄운다
  const unread = results.filter((r) => r.status === "answered" && !r.seen_at).length;
  return apiList(results.map((r) => publicInquiry(r, { withBody: false })), { unread });
}

// ── GET /api/v1/inquiries/{id} — 상세(열면 읽음 처리) ───────
async function getInquiry(request, db, env, id) {
  const { account, err } = await requireAccount(request, db, env);
  if (err) return err;
  const row = await db.prepare("SELECT * FROM inquiries WHERE id = ? AND account_id = ?")
    .bind(id, account.id).first();
  if (!row) return apiErr("NOT_FOUND");   // 남의 문의도 404 — 존재 여부를 숨긴다(계약 §1.3)

  // 답이 달린 것을 열었으면 그 자리에서 읽음 처리한다. 「읽음」 버튼을 따로 두면 아무도 안 누른다.
  if (row.status === "answered" && !row.seen_at) {
    const now = new Date().toISOString();
    await db.prepare("UPDATE inquiries SET seen_at = ?, updated_at = ? WHERE id = ?").bind(now, now, id).run();
    row.seen_at = now;
  }
  return apiOk({ inquiry: publicInquiry(row) });
}

// ── 관리자 답변 (관리자 화면에서 부른다) ────────────────────
// 상태 전이는 여기 한 곳에서만 — 화면 쪽에서 UPDATE 를 따로 쓰면 답변 없이 answered 가 된다.
export async function answerInquiry(db, id, answer) {
  const text = String(answer || "").trim().slice(0, BODY_MAX);
  if (text.length < 2) return { ok: false, reason: "empty" };
  const row = await db.prepare("SELECT id FROM inquiries WHERE id = ?").bind(id).first();
  if (!row) return { ok: false, reason: "not_found" };
  const now = new Date().toISOString();
  // 답을 고치면 seen_at 을 지운다 — 고친 답을 «이미 읽음»으로 두면 사용자가 영영 못 본다.
  await db.prepare(
    "UPDATE inquiries SET answer = ?, status = 'answered', answered_at = ?, seen_at = NULL, updated_at = ? WHERE id = ?"
  ).bind(text, now, now, id).run();
  return { ok: true };
}

export async function closeInquiry(db, id) {
  const now = new Date().toISOString();
  await db.prepare("UPDATE inquiries SET status = 'closed', updated_at = ? WHERE id = ?").bind(now, id).run();
  return { ok: true };
}

// ── 라우터 ──────────────────────────────────────────────────
export async function handleSupportApi(request, db, env, url) {
  const p = url.pathname;
  const m = request.method;

  if (p === "/api/v1/inquiries" && m === "POST") return createInquiry(request, db, env);
  if (p === "/api/v1/inquiries" && m === "GET") return listInquiries(request, db, env);

  const one = p.match(/^\/api\/v1\/inquiries\/(\d+)$/);
  if (one && m === "GET") return getInquiry(request, db, env, one[1]);

  return apiErr("NOT_FOUND");
}
