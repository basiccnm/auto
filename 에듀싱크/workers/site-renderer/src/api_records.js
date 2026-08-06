// ================= 블록5 — 자녀·기록·방과후 API =================
// 계약: docs/API계약-v1.md §1(공통규약) · §5(자녀·기록 API)
//
// 이 파일 하나가 /api/v1/children · /api/v1/records · /api/v1/activities 전부를 담는다.
// index.js에는 import 1줄 + 라우터 1줄만 추가한다(계약 §7.4 트랙 충돌 방지).
import { deleteChildCascade, deleteRecordAssets, r2KeysOf } from "./data_children.js";
import { resolveAuth, verifyReauth } from "./auth_core.js";
// 이용권 판정은 블록2(주문 상태기계)가 주인이다. 여기서 orders를 직접 조회하면
// "무엇이 유료인가"의 정의가 두 곳으로 갈라진다 — 삭제 연쇄가 두 벌이 됐던 것과 같은 실수다.
import { hasActivePass } from "./api_orders.js";
//
// **기존 HTML 핸들러(/records, /activities, /child/edit …)는 손대지 않는다.** 병존이다.
// 웹은 지금 그대로 돌고, 앱은 이 API만 본다. 전환 시점은 계약 §8-5에서 따로 정한다.
//
// 설계에서 절대 어기지 않는 것(정본 §3-5 · 계약 §5.2):
//   ① records.image_key(R2 키)는 **어떤 응답에도 넣지 않는다.** 아예 SELECT조차 하지 않고
//      `image_key IS NOT NULL`만 뽑아온다 — 실수로 새 나갈 경로 자체를 없앤다.
//   ② 자녀 실명(identifiers.name)은 **목록에서 생략, 상세에서만**.
//   ③ 남의 것 접근은 403이 아니라 **404**. 403은 "그 id가 존재한다"를 알려준다.
//   ④ 기록 응답의 시기는 `period` 객체로 묶는다. 블록1.5 grades가 같은 축을 공유한다.

import {
  apiOk,
  apiList,
  apiErr,
  parsePaging,
  gradeCode,
  gradeLabel,
  readJson,
} from "./api_core.js";

// ── 인증 ──────────────────────────────────────────────────────
// 계약 §1.4 — Authorization 헤더 우선, 없으면 쿠키 폴백(전환기 동안 앱·웹이 같은 API를 쓴다).
// 블록1 완료로 임시 구현을 걷어내고 auth_core.resolveAuth로 교체했다(회신19 §2-2).
//
// **요청당 딱 한 번만 푼다.** 예전엔 라우터가 resolveOwner로 한 번, requireReauth가 또 한 번
// 풀어서 수정·삭제 요청마다 계정 조회가 두 벌 돌았다. 라우터가 푼 결과를 아래로 넘긴다(회신20 §4).
//
// 반환에서 owner_token과 account를 **일부러 분리해 둔다** — 계약 §2.1 그대로
// owner_token은 **데이터 키**(소유권 SQL에 쓴다), account는 **신원**(과금·재인증에 쓴다).
// 핸들러는 자기가 필요한 쪽만 받는다.
async function resolveRequestAuth(request, db, env) {
  return resolveAuth(request, db, env, getCookie);
}

// 재인증(step-up) — 계약 §3.4 · 정본 §4.5 "입력은 쉽게, 수정·삭제는 어렵게".
// 되돌리기 어려운 요청(수정·삭제)에만 건다. 업로드엔 안 건다 — 정본 §0의 승부처가 "넣는 데 30초"다.
// 앱은 X-Reauth-Token 헤더로 /api/v1/auth/reauth에서 받은 5분짜리 토큰을 보낸다.
//
// ⚠️ 쿠키만 있고 accounts 행이 없는 **레거시 사용자는 여기서 AUTH_REQUIRED로 막힌다.**
// 의도된 동작이다(회신20 §4) — 되돌릴 수 없는 요청에 신원이 없으면 안 된다.
// 정본 §4 승계대로 **한 번 로그인하면 accounts가 생기며 owner_token이 그대로 이어져** 풀린다.
// 웹은 병존 경로(쿠키)로 계속 동작하므로 그 사이에도 막히지 않는다.
//
// 반환: null(통과) | apiErr 응답
async function requireReauth(request, env, account) {
  if (!account) return apiErr("AUTH_REQUIRED");
  const ok = await verifyReauth(request, env, account.id);
  return ok ? null : apiErr("REAUTH_REQUIRED");
}

// ── index.js에서 복사한 소형 헬퍼 ────────────────────────────
// index.js는 named export가 없고(export default 하나뿐) 여기서 import하면 순환 참조가 된다.
// 그래서 **의미가 고정된 소형 헬퍼만** 복제한다. 값이 바뀌면 양쪽을 함께 고쳐야 한다(TODO: 공용 모듈로 승격).
function getCookie(request, name) {
  const header = request.headers.get("Cookie") || "";
  const match = header.match(new RegExp(`(?:^|; )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}

// Workers는 UTC라 그냥 new Date()를 쓰면 한국 새벽에 날짜가 하루 밀린다. KST 고정.
function todayYmd() {
  const kst = new Date(Date.now() + 9 * 60 * 60 * 1000);
  return (
    kst.getUTCFullYear().toString() +
    String(kst.getUTCMonth() + 1).padStart(2, "0") +
    String(kst.getUTCDate()).padStart(2, "0")
  );
}

const SEM2_FALLBACK = "20260901"; // 학사일정에 개학일이 없는 학교 폴백(약속보다 후한 방향)
function schoolOpenUntil(school) {
  return (school && school.sem2_start) || SEM2_FALLBACK;
}
function isFreeOpenForSchool(school, today = todayYmd()) {
  return today < schoolOpenUntil(school);
}

const MAX_CHILDREN = 3;
const FREE_MAX_CHILDREN = 1;
const FREE_MAX_RECORDS = 20;
const PAID_MAX_RECORDS = 1000;
// 2026-07-28 사장님 확정: **2주 체험 후 전면 유료.** 무료 티어는 없다.
// (7일은 «알림장 한 번 받아보기»도 안 되는 길이였다 — 한 주 다 돌려봐야 값을 안다)
const TRIAL_DAYS = 14;
function maxChildrenFor(isPaid, freeOpen = false) {
  return freeOpen || isPaid ? MAX_CHILDREN : FREE_MAX_CHILDREN;
}
function maxRecordsFor(isPaid, freeOpen = false) {
  return freeOpen || isPaid ? PAID_MAX_RECORDS : FREE_MAX_RECORDS;
}
// 유료 판정은 **`orders`만 본다**(회신20 §4). 쿠키(`subscriber=1`) 판정을 걷어냈다.
//
// 🔴 `children.trial_expires_at`을 보면 안 된다. 거기엔 자녀 등록 시 자동으로 붙는
//    **7일 무료체험 기한도 섞여 있어** 체험 중인 사람이 유료 상한을 전부 쓰게 된다.
//    돈을 냈다는 사실이 남는 곳은 `orders`뿐이다.
//
// childId를 주면 **그 자녀 것만** 본다 — 정본 §5·계약 §6.3이 자녀별 과금이라
// 계정 단위로 뭉뚱그리면 A 자녀에게 산 이용권으로 B 자녀 상한까지 열린다.
// 자녀 수 상한처럼 계정 전체가 기준인 곳은 childId 없이 부른다.
async function isPaidFor(db, account, childId = null) {
  return hasActivePass(db, account && account.id, childId);
}

// 업로드 시점 → 학기 추정(3~8월=1학기, 9~2월=2학기). index.js estimateSemester와 동일.
function estimateSemester(today = todayYmd()) {
  const mo = +String(today).slice(4, 6);
  return mo >= 3 && mo <= 8 ? 1 : 2;
}

// (r2KeysOf·R2_DERIVED_SUFFIXES는 data_children.js에서 import — 복제 제거 2026-07-24)

const RECORD_CATEGORIES = ["award", "report_card", "grade_sheet", "certificate", "activity", "other"];
const CATEGORY_KO = {
  award: "상장", report_card: "통지표", grade_sheet: "성적표",
  certificate: "자격증", activity: "활동", other: "기타",
};
const UPLOAD_MAX_BYTES = 4 * 1024 * 1024;
const UPLOAD_MAX_FILES = 10;
const UPLOAD_MIME = ["image/jpeg", "image/png", "image/webp"];
const ACT_TYPES = ["academy", "afterschool", "activity"];

// ── 소유권 검증 (모든 경로가 여기를 통과한다) ────────────────
// index.js ownedChild와 같은 SQL. 학교급이 있어야 학년 코드를 계산할 수 있어 schools를 조인한다.
async function ownedChild(db, ownerToken, childId) {
  if (!ownerToken || !childId) return null;
  return db
    .prepare(
      `SELECT c.*, s.name AS school_name, s.slug AS school_slug, s.school_kind, s.sem2_start
       FROM children c JOIN schools s ON s.id = c.school_id
       WHERE c.id = ? AND c.owner_token = ?`
    )
    .bind(childId, ownerToken)
    .first();
}

// ── 응답 모양 (계약 §5.1 · §5.2) ─────────────────────────────
function passOf(row) {
  const exp = row.trial_expires_at || null;
  return {
    active: !!(exp && new Date(exp).getTime() > Date.now()),
    expires_at: exp,
    // 이 자녀 학교가 아직 개학 전이면 유료와 동일 취급(자녀 단위 개방 — index.js와 같은 규칙).
    free_open_until: schoolOpenUntil(row),
  };
}

// withName=true는 **상세 응답에서만**. 목록에서 실명을 흘리지 않는다(정본 §3-5).
function childShape(row, { name = null, counts = null } = {}) {
  const gc = gradeCode(row.school_kind, row.grade);
  const out = {
    id: row.id,
    nickname: row.nickname || null,
    school: { slug: row.school_slug, name: row.school_name, kind: row.school_kind },
    grade: row.grade == null ? null : String(row.grade),
    class_name: row.class_name || null,
    grade_code: gc,
    birth_year: row.birth_year == null ? null : Number(row.birth_year),
    /* 프로필 사진 (2026-07-27) — R2 키는 절대 안 나간다. 연번 경로만.
       없으면 null 이고 앱은 이모지 얼굴로 되돌아간다. */
    photo: row.photo_key ? `/api/v1/children/${row.id}/photo` : null,
    pass: passOf(row),
  };
  if (name !== null) out.name = name;
  if (counts) out.counts = counts;
  return out;
}

// 계약 §5.2 — **AI 입력 형식**. 오늘 화면에 맞춰 뽑으면 그 실수가 3~4년 굳는다.
// period를 객체로 묶는 이유: 블록1.5 grades가 같은 시기 축(school_year·semester)을 공유한다.
function recordShape(r) {
  const sy = r.school_year == null ? null : Number(r.school_year);
  const sem = r.semester == null ? null : Number(r.semester);
  return {
    id: r.id,
    child_id: r.child_id,
    category: r.category,
    period: {
      school_year: sy,
      semester: sem,
      label: sy == null ? null : `${gradeLabel(sy)}${sem ? ` ${sem}학기` : ""}`,
    },
    title: r.title || null,
    note: r.note == null ? null : r.note,
    // image_key는 절대 나가지 않는다. 연번 경로만 준다 — 실제 방어는 매 요청 소유권 SQL이고 실패는 404.
    image: r.has_image
      ? {
          url: `/api/v1/records/${r.id}/image`,
          thumb: `/api/v1/records/${r.id}/image?thumb=1`,
          bytes: r.bytes == null ? null : Number(r.bytes),
        }
      : null,
    /* 사진 여러 장 (2026-07-27) — 앞·뒤가 한 기록에 묶인다.
       주소는 **연번**만 준다(?page=0,1,2…). R2 키는 여전히 절대 안 나간다. */
    pages: Number(r.page_count || (r.has_image ? 1 : 0)),
    images: Array.from({ length: Number(r.page_count || (r.has_image ? 1 : 0)) }, (_, i) => ({
      url: `/api/v1/records/${r.id}/image?page=${i}`,
      thumb: `/api/v1/records/${r.id}/image?page=${i}&thumb=1`,
    })),
    created_at: r.created_at,
  };
}

function activityShape(a) {
  return {
    id: a.id,
    child_id: a.child_id,
    type: a.type,
    name: a.name,
    days_of_week: a.days_of_week, // 계약 §1.5 — CSV 문자열 "1,3" (1=월 … 7=일)
    start_time: a.start_time,
    end_time: a.end_time,
    start_date: a.start_date, // YYYYMMDD 문자열(계약 §1.5)
    end_date: a.end_date,
    created_at: a.created_at,
    updated_at: a.updated_at || null,
  };
}

// ================= 라우터 =================
export async function handleRecordsApi(request, db, env, url) {
  const path = url.pathname;
  const method = request.method.toUpperCase();

  try {
    // 요청당 인증 해석은 여기 한 번뿐. 아래로는 푼 결과만 넘긴다.
    const auth = await resolveRequestAuth(request, db, env);
    const owner = auth.ownerToken;
    const account = auth.account;

    // 이미지 서빙만 예외적으로 먼저 잡는다 — 실패 시 JSON 404를 내야 하고, 토큰 없음도 404다
    // (401을 주면 "그 id가 있다"가 새 나간다. 기존 handleRecordImage와 같은 규칙).
    let m = path.match(/^\/api\/v1\/records\/(\d+)\/image\/?$/);
    if (m) {
      if (method !== "GET") return errMethod();
      // page = 몇 번째 장(0부터). 이상한 값은 0으로 — 음수·NaN 이 SQL OFFSET 에 들어가면 안 된다.
      const pg = Math.max(0, parseInt(url.searchParams.get("page") || "0", 10) || 0);
      return serveRecordImage(db, env, owner, m[1], url.searchParams.get("thumb") === "1", pg);
    }

    // 토큰이 만료·위조된 경우를 **구분해서** 돌려준다(계약 §1.3).
    // 전부 AUTH_REQUIRED로 뭉개면 앱이 refresh를 시도하지 못하고 로그인 화면으로 튕긴다 —
    // access가 30분짜리라 30분마다 재로그인을 시키는 셈이 된다(회신20 §4).
    if (auth.error) return apiErr(auth.error);
    if (!owner) return apiErr("AUTH_REQUIRED");

    // /api/v1/children
    if (/^\/api\/v1\/children\/?$/.test(path)) {
      if (method === "GET") return listChildren(db, owner, account);
      if (method === "POST") return createChild(request, db, env, owner, account);
      return errMethod();
    }

    // /api/v1/children/{id}
    m = path.match(/^\/api\/v1\/children\/(\d+)\/?$/);
    if (m) {
      if (method === "GET") return getChild(db, owner, m[1]);
      if (method === "PATCH") {
        const re = await requireReauth(request, env, account);
        if (re) return re;
        return patchChild(request, db, owner, m[1]);
      }
      if (method === "DELETE") {
        const re = await requireReauth(request, env, account);
        if (re) return re;
        return deleteChild(db, env, owner, m[1]);
      }
      return errMethod();
    }

    // /api/v1/children/{id}/records
    /* 자녀 프로필 사진 (2026-07-27).
       GET 은 이미지 서빙이라 **토큰 없음도 404** — 401을 주면 «그 자녀가 있다»가 새 나간다.
       기록 사진(serveRecordImage)과 같은 규칙이다. */
    m = path.match(/^\/api\/v1\/children\/(\d+)\/photo\/?$/);
    if (m) {
      if (method === "GET") return serveChildPhoto(db, env, owner, m[1]);
      if (auth.error) return apiErr(auth.error);
      if (!owner) return apiErr("AUTH_REQUIRED");
      if (method === "POST") return putChildPhoto(request, db, env, owner, m[1]);
      if (method === "DELETE") return deleteChildPhoto(db, env, owner, m[1]);
      return errMethod();
    }

    m = path.match(/^\/api\/v1\/children\/(\d+)\/records\/?$/);
    if (m) {
      if (method !== "GET") return errMethod();
      return listRecords(db, url, owner, account, m[1]);
    }

    // /api/v1/children/{id}/activities
    m = path.match(/^\/api\/v1\/children\/(\d+)\/activities\/?$/);
    if (m) {
      if (method === "GET") return listActivities(db, url, owner, m[1]);
      if (method === "POST") return createActivity(request, db, owner, m[1]);
      return errMethod();
    }

    // /api/v1/records
    if (/^\/api\/v1\/records\/?$/.test(path)) {
      if (method !== "POST") return errMethod();
      return uploadRecords(request, db, env, owner, account);
    }

    // /api/v1/records/{id}
    m = path.match(/^\/api\/v1\/records\/(\d+)\/?$/);
    if (m) {
      if (method !== "DELETE") return errMethod();
      const re = await requireReauth(request, env, account);
      if (re) return re;
      return deleteRecord(db, env, owner, m[1]);
    }

    // /api/v1/activities/{id}
    m = path.match(/^\/api\/v1\/activities\/(\d+)\/?$/);
    if (m) {
      const re = await requireReauth(request, env, account);
      if (re) return re;
      if (method === "PATCH") return patchActivity(request, db, owner, m[1]);
      if (method === "DELETE") return deleteActivity(db, owner, m[1]);
      return errMethod();
    }

    return apiErr("NOT_FOUND");
  } catch (e) {
    // 내부 사정(SQL 오류·스택)은 절대 message에 담지 않는다(계약 §1.2).
    return apiErr("SERVER");
  }
}

function errMethod() {
  return apiErr("VALIDATION", { method: "unsupported" }, "지원하지 않는 요청 방식이에요.");
}

// ================= 자녀 =================
// GET /api/v1/children — 실명 없음(목록). counts는 한 번의 GROUP BY로 모아 N+1을 피한다.
async function listChildren(db, owner, account) {
  const { results: kids } = await db
    .prepare(
      `SELECT c.*, s.name AS school_name, s.slug AS school_slug, s.school_kind, s.sem2_start
       FROM children c JOIN schools s ON s.id = c.school_id
       WHERE c.owner_token = ? ORDER BY c.created_at, c.id`
    )
    .bind(owner)
    .all();
  if (!kids.length) return apiList([]);

  const ids = kids.map((k) => k.id);
  const ph = ids.map(() => "?").join(",");
  const [recs, acts] = await Promise.all([
    db.prepare(`SELECT child_id, COUNT(*) AS n FROM records WHERE child_id IN (${ph}) GROUP BY child_id`).bind(...ids).all(),
    db.prepare(`SELECT child_id, COUNT(*) AS n FROM activity_schedules WHERE child_id IN (${ph}) GROUP BY child_id`).bind(...ids).all(),
  ]);
  const rMap = Object.fromEntries(recs.results.map((r) => [r.child_id, r.n]));
  const aMap = Object.fromEntries(acts.results.map((r) => [r.child_id, r.n]));

  // 자녀 수 상한은 **계정 전체** 기준이라 childId 없이 묻는다(어느 자녀 이용권이든 하나 있으면 열림).
  const paid = await isPaidFor(db, account);
  return apiList(
    kids.map((k) => childShape(k, { counts: { records: rMap[k.id] || 0, activities: aMap[k.id] || 0 } })),
    { limit: maxChildrenFor(paid, kids.some((k) => isFreeOpenForSchool(k))) }
  );
}

// GET /api/v1/children/{id} — 상세. 실명은 **여기서만** 내려간다(정본 §3-5).
async function getChild(db, owner, id) {
  const child = await ownedChild(db, owner, id);
  if (!child) return apiErr("NOT_FOUND");
  const [ident, rc, ac] = await Promise.all([
    db.prepare("SELECT name FROM identifiers WHERE child_id = ?").bind(child.id).first(),
    db.prepare("SELECT COUNT(*) AS n FROM records WHERE child_id = ?").bind(child.id).first(),
    db.prepare("SELECT COUNT(*) AS n FROM activity_schedules WHERE child_id = ?").bind(child.id).first(),
  ]);
  return apiOk(
    childShape(child, {
      name: ident ? ident.name : null,
      counts: { records: (rc && rc.n) || 0, activities: (ac && ac.n) || 0 },
    })
  );
}

// POST /api/v1/children — 웹 handleRegisterChild의 서버측 규칙을 그대로 옮긴 것.
// 이중 확인 페이지(confirmed=1)는 화면 흐름이라 API에는 없다 — 앱이 확인 UI를 담당한다.
async function createChild(request, db, env, owner, account) {
  const body = (await readJson(request)) || {};
  const slug = String(body.school_slug || "").trim();
  const grade = String(body.grade == null ? "" : body.grade).trim();
  const className = String(body.class_name == null ? "" : body.class_name).trim();
  const nickname = String(body.nickname || "").trim();
  const childName = String(body.name || "").trim();
  const consented = body.consent === true || body.consent === 1 || body.consent === "1";
  const recOn = env && env.FEATURE_RECORDS === "true";

  const fields = {};
  if (!slug) fields.school_slug = "학교를 선택해 주세요.";
  if (!grade) fields.grade = "학년을 선택해 주세요.";
  if (!nickname) fields.nickname = "별명을 입력해 주세요.";
  // 이름·보호자 동의는 기록 기능(FEATURE_RECORDS)이 켜져 있을 때만 필수 — 웹과 같은 조건.
  if (recOn && !childName) fields.name = "자녀 이름을 입력해 주세요.";
  if (recOn && !consented) fields.consent = "보호자 동의가 필요해요.";
  if (Object.keys(fields).length) return apiErr("VALIDATION", { fields });

  const school = await db
    .prepare("SELECT id, slug, name, school_kind, sem2_start FROM schools WHERE slug = ?")
    .bind(slug)
    .first();
  if (!school) return apiErr("NOT_FOUND", null, "학교를 찾을 수 없어요.");

  // 중복 차단 — 같은 학교·학년·반은 한 번만(쌍둥이는 한 명으로). 다른 학년·반은 허용.
  const dup = await db
    .prepare("SELECT id FROM children WHERE owner_token = ? AND school_id = ? AND grade = ? AND COALESCE(class_name,'') = COALESCE(?, '')")
    .bind(owner, school.id, grade, className || null)
    .first();
  if (dup) return apiErr("DUPLICATE", { child_id: dup.id }, "같은 학교·학년·반 자녀가 이미 등록되어 있어요.");

  const freeOpen = isFreeOpenForSchool(school);
  // 새 자녀를 만드는 자리라 아직 childId가 없다 → 계정 기준(자녀 수 상한도 계정 기준이라 맞다).
  const paid = await isPaidFor(db, account);
  const cnt = await db.prepare("SELECT COUNT(*) AS n FROM children WHERE owner_token = ?").bind(owner).first();
  const used = (cnt && cnt.n) || 0;

  // 무료회원 제한 — 개방 기간(자녀 학교가 아직 개학 전)이면 적용하지 않는다.
  // free_trials 이력은 "자녀를 지우고 재체험"하는 허점을 막는다(계정당 1회).
  if (!paid && !freeOpen) {
    const usedTrial = await db.prepare("SELECT 1 FROM free_trials WHERE owner_token = ?").bind(owner).first();
    if (usedTrial || used >= FREE_MAX_CHILDREN) {
      return apiErr("LIMIT_EXCEEDED", { limit: FREE_MAX_CHILDREN, used }, "무료로는 자녀 1명까지 등록할 수 있어요.");
    }
  }
  if (used >= MAX_CHILDREN) {
    return apiErr("LIMIT_EXCEEDED", { limit: MAX_CHILDREN, used }, `자녀는 최대 ${MAX_CHILDREN}명까지 등록할 수 있어요.`);
  }

  const nowIso = new Date().toISOString();
  const trialExpires = new Date(Date.now() + TRIAL_DAYS * 86400000).toISOString();
  const ins = await db
    .prepare(
      `INSERT INTO children (owner_token, school_id, grade, class_name, nickname, is_test, trial_expires_at, created_at, consent_at, consent_method)
       VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)`
    )
    .bind(owner, school.id, grade, className || null, nickname, trialExpires, nowIso,
          recOn ? nowIso : null, recOn ? "checkbox" : null)
    .run();
  const newId = ins && ins.meta && ins.meta.last_row_id;

  // 실명은 identifiers에만 — children·records·로그 어디에도 저장하지 않는다.
  if (newId && recOn && childName) {
    await db
      .prepare("INSERT OR REPLACE INTO identifiers (child_id, name, created_at) VALUES (?, ?, ?)")
      .bind(newId, childName, nowIso)
      .run();
  }
  await db.prepare("INSERT OR IGNORE INTO free_trials (owner_token, first_used_at) VALUES (?, ?)").bind(owner, nowIso).run();

  const row = await ownedChild(db, owner, newId);
  return apiOk(childShape(row, { name: recOn && childName ? childName : null, counts: { records: 0, activities: 0 } }), 201);
}

// PATCH /api/v1/children/{id} — 별명은 자유 수정, 학년·반은 promote(새 학년도 전환)로만.
// 웹 handleChildEdit과 같은 규칙: 바로 다음 학년으로만, 자녀당 1회, 반 재선택 필수.
async function patchChild(request, db, owner, id) {
  const child = await ownedChild(db, owner, id);
  if (!child) return apiErr("NOT_FOUND");
  const body = (await readJson(request)) || {};

  const nickname = body.nickname == null ? null : String(body.nickname).trim();
  if (nickname !== null && !nickname) {
    return apiErr("VALIDATION", { fields: { nickname: "별명은 비워둘 수 없어요." } });
  }
  const promote = body.promote === true || body.promote === 1 || body.promote === "1";

  if (promote) {
    if (child.grade_promoted) {
      return apiErr("VALIDATION", { fields: { promote: "새 학년도 전환은 자녀당 1회만 가능해요." } });
    }
    const maxGrade = child.school_kind === "초등학교" ? 6 : 3;
    const nextGrade = Number(child.grade) + 1;
    const grade = String(body.grade == null ? "" : body.grade).trim();
    const className = String(body.class_name == null ? "" : body.class_name).trim();
    if (Number(grade) !== nextGrade || nextGrade > maxGrade) {
      return apiErr("VALIDATION", { fields: { grade: "학년은 바로 다음 학년으로만 변경할 수 있어요." } });
    }
    // 진급하면 반 편성이 새로 된다 — 빠지면 작년 반이 남아 시간표·급식이 어긋난다.
    if (!className) {
      return apiErr("VALIDATION", { fields: { class_name: "새 학년의 반을 선택해 주세요." } });
    }
    await db
      .prepare("UPDATE children SET nickname = ?, grade = ?, class_name = ?, grade_promoted = 1 WHERE id = ? AND owner_token = ?")
      .bind(nickname || child.nickname, String(nextGrade), className, child.id, owner)
      .run();
  } else if (nickname !== null) {
    await db.prepare("UPDATE children SET nickname = ? WHERE id = ? AND owner_token = ?").bind(nickname, child.id, owner).run();
  } else {
    return apiErr("VALIDATION", { fields: { nickname: "변경할 값이 없어요." } });
  }

  const row = await ownedChild(db, owner, child.id);
  const ident = await db.prepare("SELECT name FROM identifiers WHERE child_id = ?").bind(child.id).first();
  return apiOk(childShape(row, { name: ident ? ident.name : null }));
}

// DELETE /api/v1/children/{id}
// 삭제는 **data_children.deleteChildCascade 하나만** 탄다(회신19 §2-1).
// 예전엔 순환 import를 피하려 복제본을 뒀는데, 두 벌이면 테이블이 늘 때 한 곳을 빠뜨려
// R2에 아이 사진이 영구히 남는다. 공용 모듈로 승격해 단일 진입점을 복원했다.
async function deleteChild(db, env, owner, id) {
  const child = await db.prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?").bind(id, owner).first();
  if (!child) return apiErr("NOT_FOUND");
  const r = await deleteChildCascade(db, env, child.id);
  if (!r.ok) return apiErr("STORAGE");
  return apiOk({ deleted: true, id: child.id });
}

// ================= 기록 =================
// GET /api/v1/children/{id}/records?category=&q=&limit=&cursor=
// 정렬은 id DESC(최신 업로드 우선) — 계약 §1.6이 "cursor는 마지막 id"라고 못박았다.
// 학년·학기 그룹핑은 앱이 period로 한다(웹 타임라인과 정렬 기준이 다른 이유).
async function listRecords(db, url, owner, account, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");

  const { limit, cursor } = parsePaging(url);
  const cat = url.searchParams.get("category") || "";
  const q = (url.searchParams.get("q") || "").trim();

  // image_key는 SELECT조차 하지 않는다 — 응답에 새 나갈 경로 자체를 없앤다(계약 §5.2).
  let sql = `SELECT id, child_id, category, school_year, semester, title, note, bytes, created_at,
                    (image_key IS NOT NULL) AS has_image,
                    (SELECT COUNT(*) FROM record_images ri WHERE ri.record_id = records.id) AS page_count
             FROM records WHERE child_id = ?`;
  const binds = [child.id];
  if (RECORD_CATEGORIES.includes(cat)) { sql += " AND category = ?"; binds.push(cat); }
  if (q) { sql += " AND title LIKE ?"; binds.push(`%${q}%`); }
  const cid = parseInt(cursor || "", 10);
  if (Number.isFinite(cid)) { sql += " AND id < ?"; binds.push(cid); }
  sql += " ORDER BY id DESC LIMIT ?";
  binds.push(limit + 1); // 한 건 더 뽑아 다음 페이지 유무를 판정

  const { results } = await db.prepare(sql).bind(...binds).all();
  const hasMore = results.length > limit;
  const rows = hasMore ? results.slice(0, limit) : results;

  const total = await db.prepare("SELECT COUNT(*) AS n FROM records WHERE child_id = ?").bind(child.id).first();
  return apiList(rows.map(recordShape), {
    total: (total && total.n) || 0,
    cursor: hasMore ? String(rows[rows.length - 1].id) : null,
    // 기록 상한은 **이 자녀** 기준이다(자녀별 과금) — A 자녀 이용권으로 B 자녀 상한이 열리면 안 된다.
    limit_records: maxRecordsFor(await isPaidFor(db, account, child.id), isFreeOpenForSchool(child)),
  });
}

// POST /api/v1/records (multipart/form-data) — 계약 §5.3.
// 재인증 없음: 정본 §0의 승부처가 "넣는 데 30초"다. 위험은 펼쳐보기·고치기·지우기에 있다.
// 쓰기 순서 **R2 → D1**, D1 실패 시 방금 올린 R2 객체를 보상 삭제. 장별 독립 처리.
async function uploadRecords(request, db, env, owner, account) {
  let form;
  try {
    form = await request.formData();
  } catch (_) {
    return apiErr("VALIDATION", { fields: { body: "multipart/form-data 로 보내주세요." } });
  }
  const child = await ownedChild(db, owner, (form.get("child_id") || "").toString().trim());
  if (!child) return apiErr("NOT_FOUND");
  if (!env.RECORDS) return apiErr("STORAGE");

  const category = (form.get("category") || "").toString();
  if (!RECORD_CATEGORIES.includes(category)) {
    return apiErr("VALIDATION", { fields: { category: "기록 종류를 선택해 주세요." } });
  }

  // 시기 — 사용자가 고른 값 우선, 없으면 자동 추정. 배치 전체에 같은 값을 적용한다.
  const syRaw = parseInt((form.get("school_year") || "").toString(), 10);
  const semRaw = parseInt((form.get("semester") || "").toString(), 10);
  const schoolYear = Number.isFinite(syRaw) && syRaw >= 0 && syRaw <= 12 ? syRaw : gradeCode(child.school_kind, child.grade);
  const semester = semRaw === 1 || semRaw === 2 ? semRaw : estimateSemester();
  if (schoolYear == null) {
    return apiErr("VALIDATION", { fields: { school_year: "학년을 알 수 없어요. 학년을 함께 보내주세요." } });
  }

  const files = form.getAll("files").filter((f) => f && typeof f === "object" && f.size != null);
  const thumbs = form.getAll("files_t").filter((f) => f && typeof f === "object" && f.size != null);
  if (!files.length) return apiErr("VALIDATION", { fields: { files: "사진을 선택해 주세요." } });
  if (files.length > UPLOAD_MAX_FILES) {
    return apiErr("VALIDATION", { fields: { files: `한 번에 ${UPLOAD_MAX_FILES}장까지 올릴 수 있어요.` } });
  }

  const limit = maxRecordsFor(await isPaidFor(db, account, child.id), isFreeOpenForSchool(child));
  const cnt = await db.prepare("SELECT COUNT(*) AS n FROM records WHERE child_id = ?").bind(child.id).first();
  const used = (cnt && cnt.n) || 0;
  const room = Math.max(0, limit - used);
  if (room <= 0) return apiErr("LIMIT_EXCEEDED", { limit, used });

  const nowIso = new Date().toISOString();
  const title = (form.get("title") || "").toString().trim() ||
    `${gradeLabel(schoolYear)} ${semester}학기 ${CATEGORY_KO[category]}`;
  const note = (form.get("note") || "").toString().trim() || null;
  const savedIds = [];
  const skipped = [];

  /* 올라온 사진 전부를 **기록 한 건**으로 묶는다 (2026-07-27).
     예전엔 사진 한 장마다 records 행을 하나씩 만들었다 — 통지표 앞·뒤 2장을 넣으면
     「통지표」가 두 건으로 갈렸다. 이제 records 는 «한 건», 사진은 record_images 에 순서대로.
     R2 먼저 → D1 나중 순서는 그대로다(삭제와 같은 이유: 키를 잃으면 고아가 영구히 남는다). */
  const put = [];                       // 이번에 R2 에 올린 키 — 실패하면 이걸 되돌린다
  const images = [];                    // { key, bytes } 순서대로
  /* R2 저장을 **전부 동시에** 보낸다(2026-07-31 «저장이 너무 느리다»).
     전엔 원본→썸네일→다음 장… 한 줄이어서 2장에 4.5초가 걸렸다. 장수만큼 곱으로 늘던 구조.
     순서는 통과한 장 목록(jobs)을 먼저 확정해 두므로 동시에 올려도 안 섞인다. */
  const jobs = [];
  for (let i = 0; i < files.length && jobs.length < room; i++) {
    const f = files[i];
    if (f.size > UPLOAD_MAX_BYTES) { skipped.push({ index: i, reason: "too_big" }); continue; }
    if (f.type && !UPLOAD_MIME.includes(f.type)) { skipped.push({ index: i, reason: "mime" }); continue; }
    // child_id를 키 접두사로 — 고아가 생겨도 list({prefix:'rec/17/'})로 자녀 단위 대조·청소가 된다.
    jobs.push({ index: i, f, thumbBlob: thumbs[i], key: `rec/${child.id}/${crypto.randomUUID()}` });
  }
  const done = await Promise.all(jobs.map(async (j) => {
    try {
      const ps = [env.RECORDS.put(j.key, j.f.stream(), { httpMetadata: { contentType: j.f.type || "image/jpeg" } })];
      const hasThumb = j.thumbBlob && j.thumbBlob.size > 0 && j.thumbBlob.size <= UPLOAD_MAX_BYTES;
      if (hasThumb) ps.push(env.RECORDS.put(j.key + "_t", j.thumbBlob.stream(), { httpMetadata: { contentType: j.thumbBlob.type || "image/jpeg" } }));
      await Promise.all(ps);
      return { ok: true, j, hasThumb };
    } catch (e) { return { ok: false, j }; }
  }));
  for (const r of done) {               // jobs 순서 그대로라 장 순서가 지켜진다
    if (!r.ok) { skipped.push({ index: r.j.index, reason: "save_failed" }); continue; }
    put.push(r.j.key);
    if (r.hasThumb) put.push(r.j.key + "_t");
    images.push({ key: r.j.key, bytes: r.j.f.size });
  }

  if (images.length) {
    try {
      // 대표 사진(첫 장)은 image_key 에도 넣는다 — 옛 코드·옛 앱이 아직 이 칸을 읽는다.
      const totalBytes = images.reduce((a, x) => a + (x.bytes || 0), 0);
      const ins = await db.prepare(
        `INSERT INTO records (child_id, category, school_year, semester, title, note, image_key, bytes, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      ).bind(child.id, category, schoolYear, semester, title, note, images[0].key, totalBytes, nowIso, nowIso).run();
      const recId = ins && ins.meta && ins.meta.last_row_id;
      await db.batch(images.map((x, ord) => db.prepare(
        `INSERT INTO record_images (record_id, ord, image_key, bytes, created_at) VALUES (?, ?, ?, ?, ?)`
      ).bind(recId, ord, x.key, x.bytes, nowIso)));
      savedIds.push(recId);
    } catch (e) {
      // 보상 삭제 — R2엔 올라갔는데 D1이 실패한 경우. 없으면 보이지 않는 고아가 영구히 남는다.
      try { if (put.length) await env.RECORDS.delete(put); } catch (_) { /* rec/{child_id}/ 대조로 나중에 청소 */ }
      images.forEach((_, i) => skipped.push({ index: i, reason: "save_failed" }));
      images.length = 0;
    }
  }

  const overflow = files.length - images.length - skipped.length;
  let saved = [];
  if (savedIds.length) {
    const ph = savedIds.map(() => "?").join(",");
    const { results } = await db
      .prepare(
        `SELECT id, child_id, category, school_year, semester, title, note, bytes, created_at,
                (image_key IS NOT NULL) AS has_image,
                (SELECT COUNT(*) FROM record_images ri WHERE ri.record_id = records.id) AS page_count
         FROM records WHERE id IN (${ph}) ORDER BY id`
      )
      .bind(...savedIds)
      .all();
    saved = results.map(recordShape);
  }
  return apiOk({
    saved,
    skipped,
    overflow: overflow > 0 ? overflow : 0, // 상한에 걸려 시도조차 못 한 장수
    limit,
    used: used + saved.length,
  }, saved.length ? 201 : 200);
}

// DELETE /api/v1/records/{id} — R2(원본+파생) 먼저, D1 나중.
async function deleteRecord(db, env, owner, id) {
  const rec = await db
    .prepare(
      `SELECT r.id, r.image_key FROM records r JOIN children c ON c.id = r.child_id
       WHERE r.id = ? AND c.owner_token = ?`
    )
    .bind(id, owner)
    .first();
  if (!rec) return apiErr("NOT_FOUND");
  // 삭제는 data_children의 공용 함수만 탄다 — R2(원본+파생) 먼저, D1 나중.
  const r = await deleteRecordAssets(db, env, rec);
  if (!r.ok) return apiErr("STORAGE");
  return apiOk({ deleted: true, id: rec.id });
}

/* ── 자녀 프로필 사진 (2026-07-27) ─────────────────────────
   썸네일을 따로 두지 않는다 — 프로필은 원래 작게 쓰므로 한 장이면 충분하다.
   앱이 480px로 줄여서 보낸다(기록 사진과 같은 prepShot 경로). */
const CHILD_PHOTO_MAX = 1_500_000;      // 1.5MB. 480px JPEG이면 100KB 남짓이라 넉넉하다

async function serveChildPhoto(db, env, owner, id) {
  if (!owner) return apiErr("NOT_FOUND");
  const row = await db
    .prepare("SELECT photo_key FROM children WHERE id = ? AND owner_token = ?")
    .bind(id, owner).first();
  if (!row || !row.photo_key) return apiErr("NOT_FOUND");
  if (!env.RECORDS) return apiErr("STORAGE");
  const obj = await env.RECORDS.get(row.photo_key);
  if (!obj) return apiErr("NOT_FOUND");
  return new Response(obj.body, {
    headers: {
      "Content-Type": obj.httpMetadata?.contentType || "image/jpeg",
      "Cache-Control": "private, max-age=86400",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

async function putChildPhoto(request, db, env, owner, id) {
  const child = await db
    .prepare("SELECT id, photo_key FROM children WHERE id = ? AND owner_token = ?")
    .bind(id, owner).first();
  if (!child) return apiErr("NOT_FOUND");
  if (!env.RECORDS) return apiErr("STORAGE");

  let form;
  try { form = await request.formData(); } catch (_) { return apiErr("VALIDATION"); }
  const f = form.get("file");
  if (!f || typeof f !== "object" || f.size == null) {
    return apiErr("VALIDATION", { fields: { file: "사진을 골라주세요." } });
  }
  if (f.size > CHILD_PHOTO_MAX) {
    return apiErr("VALIDATION", { fields: { file: "사진이 너무 커요." } });
  }
  if (f.type && !UPLOAD_MIME.includes(f.type)) {
    return apiErr("VALIDATION", { fields: { file: "사진 형식만 올릴 수 있어요." } });
  }

  const key = `child/${child.id}/${crypto.randomUUID()}`;
  await env.RECORDS.put(key, f.stream(), { httpMetadata: { contentType: f.type || "image/jpeg" } });
  try {
    await db.prepare("UPDATE children SET photo_key = ? WHERE id = ?").bind(key, child.id).run();
  } catch (e) {
    try { await env.RECORDS.delete(key); } catch (_) {}   // 보상 삭제 — 고아를 남기지 않는다
    return apiErr("STORAGE");
  }
  // 옛 사진은 **DB를 바꾼 뒤** 지운다. 먼저 지우면 실패했을 때 사진 없는 자녀가 된다.
  if (child.photo_key && child.photo_key !== key) {
    try { await env.RECORDS.delete(child.photo_key); } catch (_) {}
  }
  return apiOk({ photo: `/api/v1/children/${child.id}/photo` });
}

async function deleteChildPhoto(db, env, owner, id) {
  const child = await db
    .prepare("SELECT id, photo_key FROM children WHERE id = ? AND owner_token = ?")
    .bind(id, owner).first();
  if (!child) return apiErr("NOT_FOUND");
  await db.prepare("UPDATE children SET photo_key = NULL WHERE id = ?").bind(child.id).run();
  if (child.photo_key && env.RECORDS) {
    try { await env.RECORDS.delete(child.photo_key); } catch (_) {}
  }
  return apiOk({ deleted: true });
}

// GET /api/v1/records/{id}/image[?thumb=1]
// R2는 비공개 버킷이라 워커가 매 요청 소유권을 확인하고 스트리밍한다.
// **권한 없음도 403이 아니라 404** — 그 기록의 존재 여부 자체를 숨긴다(계약 §1.3).
async function serveRecordImage(db, env, owner, id, thumb, page = 0) {
  if (!owner) return apiErr("NOT_FOUND");
  /* page = 몇 번째 장인가(0부터). 안 주면 대표(첫 장).
     소유권은 여기서 한 번 더 본다 — record_images 만 조인하면 남의 기록 사진이 샌다. */
  const rec = await db
    .prepare(
      `SELECT COALESCE(
                (SELECT ri.image_key FROM record_images ri
                  WHERE ri.record_id = r.id ORDER BY ri.ord LIMIT 1 OFFSET ?),
                CASE WHEN ? = 0 THEN r.image_key ELSE NULL END
              ) AS image_key
         FROM records r JOIN children c ON c.id = r.child_id
        WHERE r.id = ? AND c.owner_token = ?`
    )
    .bind(page, page, id, owner)
    .first();
  if (!rec || !rec.image_key) return apiErr("NOT_FOUND");
  if (!env.RECORDS) return apiErr("STORAGE");

  const key = thumb ? rec.image_key + "_t" : rec.image_key;
  let obj = await env.RECORDS.get(key);
  // 썸네일이 없는 기록(구버전/생성 실패)은 원본으로 폴백 — 깨진 칸을 보여주지 않는다.
  if (!obj && thumb) obj = await env.RECORDS.get(rec.image_key);
  if (!obj) return apiErr("NOT_FOUND");

  return new Response(obj.body, {
    headers: {
      "Content-Type": obj.httpMetadata?.contentType || "image/jpeg",
      // private: 개인 사진이라 공용 캐시(CDN·프록시)에 남지 않게. 브라우저 캐시만 허용.
      "Cache-Control": "private, max-age=86400",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

// ================= 방과후·활동 =================
// GET /api/v1/children/{id}/activities[?active=1]
// 기본은 **전부** 준다. 웹 화면은 오늘 유효한 것만 보여주지만, API는 DB가 가진 사실을 숨기지 않는다
// (정본 §3-3 "DB는 자산, 화면은 소모품"). 오늘 기준만 필요하면 active=1.
async function listActivities(db, url, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const activeOnly = url.searchParams.get("active") === "1";
  const today = todayYmd();

  const sql = activeOnly
    ? `SELECT * FROM activity_schedules WHERE child_id = ? AND start_date <= ? AND end_date >= ? ORDER BY start_time, id`
    : `SELECT * FROM activity_schedules WHERE child_id = ? ORDER BY start_time, id`;
  const stmt = activeOnly
    ? db.prepare(sql).bind(child.id, today, today)
    : db.prepare(sql).bind(child.id);
  const { results } = await stmt.all();
  return apiList(results.map(activityShape), { today });
}

// 요일은 배열 [1,3] 도, CSV "1,3" 도 받는다. 저장·응답은 계약 §1.5의 CSV로 통일.
function parseDays(v) {
  if (v == null) return null;
  const arr = Array.isArray(v) ? v : String(v).split(",");
  const days = arr.map((d) => parseInt(String(d).trim(), 10)).filter((d) => d >= 1 && d <= 7);
  return days.length ? [...new Set(days)].sort((a, b) => a - b).join(",") : null;
}

// 서버 검증 — 프론트만 믿으면 직접 POST로 우회된다(웹 handleActivitySave와 같은 규칙).
function validateActivity({ type, name, days, st, et, sd, ed }) {
  const fields = {};
  if (!ACT_TYPES.includes(type)) fields.type = "종류를 선택해 주세요.";
  if (!name) fields.name = "이름을 입력해 주세요.";
  if (!days) fields.days_of_week = "요일을 선택해 주세요.";
  if (!/^\d{2}:\d{2}$/.test(st) || !/^\d{2}:\d{2}$/.test(et)) fields.time = "시간 형식은 HH:MM 이에요.";
  else if (et <= st) fields.time = "종료 시간이 시작 시간보다 빨라요.";
  if (!/^\d{8}$/.test(sd) || !/^\d{8}$/.test(ed)) fields.date = "날짜 형식은 YYYYMMDD 예요.";
  else if (ed < sd) fields.date = "종료일이 시작일보다 빨라요.";
  return Object.keys(fields).length ? fields : null;
}

async function createActivity(request, db, owner, childId) {
  const child = await ownedChild(db, owner, childId);
  if (!child) return apiErr("NOT_FOUND");
  const b = (await readJson(request)) || {};

  const v = {
    type: String(b.type || ""),
    name: String(b.name || "").trim().slice(0, 40),
    days: parseDays(b.days_of_week != null ? b.days_of_week : b.days),
    st: String(b.start_time || "").trim(),
    et: String(b.end_time || "").trim(),
    sd: String(b.start_date || "").replace(/-/g, "").trim(),
    ed: String(b.end_date || "").replace(/-/g, "").trim(),
  };
  const fields = validateActivity(v);
  if (fields) return apiErr("VALIDATION", { fields });

  const nowIso = new Date().toISOString();
  const ins = await db
    .prepare(
      `INSERT INTO activity_schedules (child_id, type, name, days_of_week, start_time, end_time, start_date, end_date, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(child.id, v.type, v.name, v.days, v.st, v.et, v.sd, v.ed, nowIso, nowIso)
    .run();
  const row = await db
    .prepare("SELECT * FROM activity_schedules WHERE id = ?")
    .bind(ins && ins.meta && ins.meta.last_row_id)
    .first();
  return apiOk(activityShape(row), 201);
}

// PATCH /api/v1/activities/{id} — 부분 수정. 기존 행을 읽어 병합한 뒤 전체를 다시 검증한다
// (부분 수정이어도 "종료<시작" 같은 조합 오류는 막아야 한다).
async function patchActivity(request, db, owner, id) {
  const cur = await db
    .prepare(
      `SELECT a.* FROM activity_schedules a JOIN children c ON c.id = a.child_id
       WHERE a.id = ? AND c.owner_token = ?`
    )
    .bind(id, owner)
    .first();
  if (!cur) return apiErr("NOT_FOUND");
  const b = (await readJson(request)) || {};

  const days = b.days_of_week != null || b.days != null ? parseDays(b.days_of_week != null ? b.days_of_week : b.days) : cur.days_of_week;
  const v = {
    type: b.type != null ? String(b.type) : cur.type,
    name: b.name != null ? String(b.name).trim().slice(0, 40) : cur.name,
    days,
    st: b.start_time != null ? String(b.start_time).trim() : cur.start_time,
    et: b.end_time != null ? String(b.end_time).trim() : cur.end_time,
    sd: b.start_date != null ? String(b.start_date).replace(/-/g, "").trim() : cur.start_date,
    ed: b.end_date != null ? String(b.end_date).replace(/-/g, "").trim() : cur.end_date,
  };
  const fields = validateActivity(v);
  if (fields) return apiErr("VALIDATION", { fields });

  // 소유 검증을 UPDATE 조건에도 함께 박는다 — 남의 일정을 못 고치게 이중으로.
  await db
    .prepare(
      `UPDATE activity_schedules SET type=?, name=?, days_of_week=?, start_time=?, end_time=?,
       start_date=?, end_date=?, updated_at=? WHERE id=? AND child_id=?`
    )
    .bind(v.type, v.name, v.days, v.st, v.et, v.sd, v.ed, new Date().toISOString(), cur.id, cur.child_id)
    .run();
  const row = await db.prepare("SELECT * FROM activity_schedules WHERE id = ?").bind(cur.id).first();
  return apiOk(activityShape(row));
}

async function deleteActivity(db, owner, id) {
  const row = await db
    .prepare(
      `SELECT a.id FROM activity_schedules a JOIN children c ON c.id = a.child_id
       WHERE a.id = ? AND c.owner_token = ?`
    )
    .bind(id, owner)
    .first();
  if (!row) return apiErr("NOT_FOUND");
  await db.prepare("DELETE FROM activity_schedules WHERE id = ?").bind(row.id).run();
  return apiOk({ deleted: true, id: row.id });
}
