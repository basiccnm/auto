// ================= 학교 읽기 API (블록3+4) =================
// 계약: docs/API계약-v1.md §1(공통규약) · §4(읽기 API)
//
//   GET  /api/v1/schools/search?q=&level=&limit=&cursor=
//   GET  /api/v1/schools/{slug}
//   GET  /api/v1/schools/{slug}/meals?from=&to=
//   GET  /api/v1/schools/{slug}/timetable?grade=&class=
//   GET  /api/v1/schools/{slug}/schedules?from=&to=
//   POST /api/v1/schools/{slug}/warm
//
// 전부 **인증 불필요**(공용 데이터). 기존 HTML 핸들러(handleSearch/handleSchoolDetail/
// handleSchoolWarm)와 **병존**한다 — 웹은 이 파일과 무관하게 그대로 돈다.
//
// ⚠️ index.js의 온디맨드 NEIS 함수(ensureMeals/ensureSchedules/ensureTimetable)는
//    export되어 있지 않고, index.js가 이 파일을 import하므로 역방향 import는 순환이 된다.
//    → warm에 필요한 최소 로직만 여기 자립적으로 다시 담았다(index.js는 1줄도 안 고친다).

import { apiOk, apiList, apiErr, parsePaging, ymdToday } from "./api_core.js";

// ── 공통 소도구 ────────────────────────────────────────────────

// level 코드 → schools.school_kind. index.js LEVEL_TO_KIND와 같은 표.
// 유치원은 1차 범위에서 제외(§결정로그)라 검색 노출하지 않는다.
const LEVEL_TO_KIND = { elem: "초등학교", mid: "중학교", high: "고등학교" };
const KINDS = new Set(["초등학교", "중학교", "고등학교"]);

const isYmd = (s) => typeof s === "string" && /^\d{8}$/.test(s);

// 커서는 계약 §1.6대로 **불투명 문자열**이다. 학교 하위 자원(급식·시간표·일정)은
// 한 학교당 행 수가 작아 offset으로 충분하다 — 앱은 이 값을 해석하지 않는다.
function encCursor(offset) {
  return btoa(`o${offset}`);
}
function decCursor(c) {
  if (!c) return 0;
  try {
    const s = atob(c);
    if (s[0] !== "o") return 0;
    const n = parseInt(s.slice(1), 10);
    return Number.isFinite(n) && n >= 0 ? n : 0;
  } catch {
    return 0;
  }
}
// 다음 페이지가 있을 때만 cursor를 채운다(limit만큼 꽉 찼으면 더 있다고 본다).
function listOut(items, limit, offset) {
  return apiList(items, { cursor: items.length === limit ? encCursor(offset + limit) : null });
}

// LIKE 와일드카드가 검색어에 들어오면 전체검색이 되어버린다 → 이스케이프.
function likeEscape(s) {
  return s.replace(/[\\%_]/g, (m) => `\\${m}`);
}

// ── 응답 변환 (계약 §4.1) ─────────────────────────────────────
// schools + school_details를 한 행으로 조인해 받은 flat row를 그대로 받는다.
function schoolOut(r) {
  const address = [r.address_road, r.address_detail].filter((x) => x && String(x).trim()).join(" ");
  const hasDetail = r.class_count != null || r.student_count != null;
  return {
    slug: r.slug,
    name: r.name,
    kind: r.school_kind,
    sido: r.sido,
    address: address || null,
    phone: r.phone || null,
    homepage: r.homepage || null,
    sem2_start: r.sem2_start || null,
    detail: hasDetail ? { class_count: r.class_count ?? null, student_count: r.student_count ?? null } : null,
  };
}

const SCHOOL_COLS = `s.id AS sid, s.slug, s.name, s.school_kind, s.sido, s.address_road, s.address_detail,
                     s.phone, s.homepage, s.sem2_start, d.class_count, d.student_count`;
const SCHOOL_FROM = `FROM schools s LEFT JOIN school_details d ON d.school_id = s.id`;

// 급식 dishes — dishes_parsed(JSON) 우선, 없으면 원문을 분해.
// **[{name, allergens:[]}] 객체 배열로 내보낸다** (계약 §4.2 개정, 2026-07-24).
//   처음엔 계약 예시대로 이름만 냈는데, DB의 dishes_parsed엔 알레르기 번호가 **이미 들어 있다**.
//   API가 그걸 버리면 나중에 "자녀 알레르기 하이라이트"를 만들 때 API를 다시 고쳐야 하고,
//   앱이 이미 배포된 뒤면 버전 호환 문제까지 생긴다.
//   정본 원칙2 — "저장 형식 = 미래 입력 형식. 오늘 화면에 맞춰 대충 뽑으면 그 실수를 API 층에서 반복한다."
//   → 있는 데이터를 버리지 않는다. 이름만 필요한 화면은 d.name만 읽으면 된다.
function dishesOut(row) {
  if (row.dishes_parsed) {
    try {
      const arr = JSON.parse(row.dishes_parsed);
      if (Array.isArray(arr)) {
        return arr
          .map((d) => (typeof d === "string"
            ? { name: d, allergens: [] }
            : { name: (d && d.name) || "", allergens: (d && d.allergens) || [] }))
          .filter((d) => d.name);
      }
    } catch {
      /* 깨진 JSON이면 아래 원문 분해로 폴백 */
    }
  }
  return parseDishesJs(row.dishes || "");
}
// (parseDishNames 제거 2026-07-24 — 알레르기까지 파싱하는 parseDishesJs로 통일)

// ── 라우터 ────────────────────────────────────────────────────
// index.js가 넘겨주는 진입점. path는 반드시 "/api/v1/schools"로 시작한다.
export async function handleSchoolsApi(request, db, env, url) {
  try {
    const rest = url.pathname.slice("/api/v1/schools".length); // "" | "/search" | "/{slug}" | "/{slug}/meals" ...
    const segs = rest.split("/").filter(Boolean).map((s) => {
      try { return decodeURIComponent(s); } catch { return s; }
    });
    const method = request.method.toUpperCase();

    if (segs.length === 0) return apiErr("NOT_FOUND");

    if (segs.length === 1 && segs[0] === "search") {
      if (method !== "GET") return methodErr();
      return await searchSchools(db, url);
    }

    const slug = segs[0];
    const sub = segs[1] || null;
    if (segs.length > 2) return apiErr("NOT_FOUND");

    // warm은 학교 행 전체(office_code·school_code)가 필요하고, 나머지는 조인 행이면 충분하다.
    if (sub === "warm") {
      if (method !== "POST") return methodErr();
      return await warmSchool(request, db, env, url, slug);
    }

    const school = await db
      .prepare(`SELECT ${SCHOOL_COLS} ${SCHOOL_FROM} WHERE s.slug = ?`)
      .bind(slug)
      .first();
    if (!school) return apiErr("NOT_FOUND");

    if (method !== "GET") return methodErr();
    if (!sub) return apiOk(schoolOut(school));
    if (sub === "meals") return await schoolMeals(db, url, school.sid);
    if (sub === "timetable") return await schoolTimetable(db, url, school.sid);
    if (sub === "schedules") return await schoolSchedules(db, url, school.sid);
    return apiErr("NOT_FOUND");
  } catch (e) {
    // 내부 사정은 절대 message에 넣지 않는다(계약 §1.2).
    console.error("[api_schools]", e && e.stack ? e.stack : String(e));
    return apiErr("SERVER");
  }
}

function methodErr() {
  return apiErr("VALIDATION", { fields: { method: "지원하지 않는 요청 방식이에요." } });
}

// ── §4 검색 ───────────────────────────────────────────────────
// 대응: index.js handleSearch(211). 의도 파싱("숭미초 급식")은 웹 UX 전용이라 API에는 없다 —
// 앱은 탭을 직접 고르므로 검색어를 임의로 깎으면 오히려 결과가 어긋난다.
async function searchSchools(db, url) {
  const q = (url.searchParams.get("q") || "").trim();
  const level = (url.searchParams.get("level") || "").trim();
  if (!q && !level) {
    return apiErr("VALIDATION", { fields: { q: "검색어나 학교급 중 하나는 필요해요." } });
  }
  // level은 elem|mid|high. 알 수 없는 값은 handleSearch와 같이 "필터 없음"으로 흘린다.
  const kind = LEVEL_TO_KIND[level] || (KINDS.has(level) ? level : null);

  const { limit, cursor } = parsePaging(url);
  const offset = decCursor(cursor);

  let sql = `SELECT ${SCHOOL_COLS} ${SCHOOL_FROM} WHERE 1=1`;
  const binds = [];
  if (q) {
    sql += ` AND s.name LIKE ? ESCAPE '\\'`;
    binds.push(`%${likeEscape(q)}%`);
  }
  if (kind) {
    sql += " AND s.school_kind = ?";
    binds.push(kind);
  }
  sql += " ORDER BY s.name, s.id LIMIT ? OFFSET ?";
  binds.push(limit, offset);

  const { results } = await db.prepare(sql).bind(...binds).all();
  return listOut(results.map(schoolOut), limit, offset);
}

// ── §4.2 급식 ─────────────────────────────────────────────────
async function schoolMeals(db, url, schoolId) {
  const from = url.searchParams.get("from") || ymdToday();
  const to = url.searchParams.get("to") || null;
  const bad = {};
  if (!isYmd(from)) bad.from = "YYYYMMDD 형식이어야 해요.";
  if (to !== null && !isYmd(to)) bad.to = "YYYYMMDD 형식이어야 해요.";
  if (Object.keys(bad).length) return apiErr("VALIDATION", { fields: bad });

  const { limit, cursor } = parsePaging(url);
  const offset = decCursor(cursor);

  let sql = "SELECT meal_date, meal_type_name, dishes, dishes_parsed, calorie_info, origin_info, nutrition_info FROM meals WHERE school_id = ? AND meal_date >= ?";
  const binds = [schoolId, from];
  if (to) { sql += " AND meal_date <= ?"; binds.push(to); }
  // 기숙사형 고교는 조식·석식도 있으므로 날짜별 1건으로 줄이지 않는다.
  sql += " ORDER BY meal_date, meal_type_code, id LIMIT ? OFFSET ?";
  binds.push(limit, offset);

  const { results } = await db.prepare(sql).bind(...binds).all();
  const items = results.map((r) => ({
    date: r.meal_date,            // YYYYMMDD 문자열 그대로(계약 §1.5)
    type: r.meal_type_name,
    dishes: dishesOut(r),
    calorie: r.calorie_info || null,
    origin: r.origin_info || null,
    nutrition: r.nutrition_info || null,
  }));
  return listOut(items, limit, offset);
}

// ── §4.3 시간표 ───────────────────────────────────────────────
// 🔴 timetables.school_year는 NEIS 학년도 문자열("2026")이다. records.school_year(학년 정수코드)와
//    이름만 같고 뜻이 완전히 다르다 → **응답에서만 neis_year로 rename**한다. DB는 안 건드린다.
async function schoolTimetable(db, url, schoolId) {
  const grade = (url.searchParams.get("grade") || "").trim();
  const className = (url.searchParams.get("class") || "").trim();
  const { limit, cursor } = parsePaging(url);
  const offset = decCursor(cursor);

  // 시간표는 요일 단위로 축약 저장돼 날짜 개념이 없다 → 현재 학년도·학기분만 뽑으면 월~금 1벌이 나온다.
  const today = ymdToday();
  const ay = schoolYearOf(today);
  const sem = semesterOf(url, today);

  /* ⚠ 「그 학년에 어떤 반이 있나」만 알고 싶을 때가 있다(자녀 등록의 반 고르기).
     예전엔 시간표를 통째로 받아 반 이름을 추려 썼는데, **페이징 기본 50건**에 잘려서
     경기초 4학년이 「난초·매화·장미」인데 「난초·매화」만 나왔다.
     반이 많은 학교는 상한 200건으로도 모자란다 → 반 이름만 주는 길을 따로 낸다. */
  if (url.searchParams.get("classes") === "1") {
    const { results } = await db.prepare(
      "SELECT DISTINCT class_name FROM timetables WHERE school_id=? AND school_year=? AND semester=? AND grade=? AND COALESCE(class_name,'')<>'' ORDER BY class_name"
    ).bind(schoolId, ay, sem, grade).all();
    return apiOk({ items: results.map((r) => r.class_name), semester: sem, neis_year: ay });
  }

  let sql = "SELECT weekday, period, subject, grade, class_name, school_year, semester FROM timetables WHERE school_id = ? AND school_year = ? AND semester = ?";
  const binds = [schoolId, ay, sem];
  if (grade) { sql += " AND grade = ?"; binds.push(grade); }
  if (className) { sql += " AND COALESCE(class_name,'') = ?"; binds.push(className); }
  sql += " ORDER BY CAST(grade AS INTEGER), class_name, weekday, CAST(period AS INTEGER), id LIMIT ? OFFSET ?";
  binds.push(limit, offset);

  const { results } = await db.prepare(sql).bind(...binds).all();
  const items = results.map((r) => ({
    weekday: r.weekday == null ? null : Number(r.weekday),
    period: r.period,
    subject: r.subject,
    grade: r.grade,
    class_name: r.class_name,
    neis_year: r.school_year,  // ← rename (계약 §4.3)
    semester: r.semester,
  }));
  return listOut(items, limit, offset);
}

// ── §4.4 학사일정 ─────────────────────────────────────────────
// grade_flags는 내보내지 않는다 — 301MB 죽은 데이터이고 아무도 안 읽는다(계약 §4.4).
async function schoolSchedules(db, url, schoolId) {
  const from = url.searchParams.get("from") || ymdToday();
  const to = url.searchParams.get("to") || null;
  const bad = {};
  if (!isYmd(from)) bad.from = "YYYYMMDD 형식이어야 해요.";
  if (to !== null && !isYmd(to)) bad.to = "YYYYMMDD 형식이어야 해요.";
  if (Object.keys(bad).length) return apiErr("VALIDATION", { fields: bad });

  const { limit, cursor } = parsePaging(url);
  const offset = decCursor(cursor);

  let sql = "SELECT event_date, event_name, event_content, closure_type FROM academic_schedules WHERE school_id = ? AND event_date >= ?";
  const binds = [schoolId, from];
  if (to) { sql += " AND event_date <= ?"; binds.push(to); }
  sql += " ORDER BY event_date, id LIMIT ? OFFSET ?";
  binds.push(limit, offset);

  const { results } = await db.prepare(sql).bind(...binds).all();
  const items = results.map((r) => ({
    date: r.event_date,
    name: r.event_name,
    content: r.event_content || null,
    closure_type: r.closure_type || null,
  }));
  return listOut(items, limit, offset);
}

// ============ 온디맨드 NEIS 워밍 (POST /warm) ============
// 대응: index.js handleSchoolWarm(376). 전국 12,563개교 콘텐츠를 D1에 통째로 넣으면
// 시간표만 1,150만행이라 무리 → 학교를 열 때 그 학교 것만 받아 캐시(lazy).
// GET 조회는 D1만 읽는다. 비어 있으면 앱이 이 엔드포인트를 부르고 다시 GET 한다.

async function warmSchool(request, db, env, url, slug) {
  let body = null;
  try {
    if ((request.headers.get("Content-Type") || "").includes("application/json")) body = await request.json();
  } catch {
    body = null;
  }
  const pick = (k) => {
    const v = (body && body[k] != null ? String(body[k]) : null) || url.searchParams.get(k);
    return v ? String(v).trim() : "";
  };
  const kind = pick("kind"); // meal | schedule | timetable
  if (!["meal", "schedule", "timetable"].includes(kind)) {
    return apiErr("VALIDATION", { fields: { kind: "meal · schedule · timetable 중 하나여야 해요." } });
  }

  const school = await db.prepare("SELECT * FROM schools WHERE slug = ?").bind(slug).first();
  if (!school) return apiErr("NOT_FOUND");

  const key = env.NEIS_API_KEY || ""; // 없으면 NEIS가 5건만 준다 — 반드시 넘긴다.
  const today = ymdToday();
  try {
    if (kind === "meal") await warmMeals(db, school, today, key);
    else if (kind === "schedule") await warmSchedules(db, school, today, key);
    else {
      const grade = pick("grade");
      if (!grade) return apiErr("VALIDATION", { fields: { grade: "시간표는 학년이 필요해요." } });
      await warmTimetable(db, school, grade, pick("class") || null, today, key, pick("semester"));
    }
  } catch (e) {
    console.error("[api_schools/warm]", e && e.stack ? e.stack : String(e));
    return apiErr("SERVER");
  }
  return apiOk({ slug: school.slug, kind, warmed: true });
}

// ── NEIS 호출부 (index.js와 동일 규칙, 자립 복제) ──────────────
async function neisGet(endpoint, params, key) {
  const base = { Type: "json", pSize: "1000", ...params };
  if (key) base.KEY = key;
  const qs = new URLSearchParams(base);
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 9000);
  let resp;
  try { resp = await fetch(`https://open.neis.go.kr/hub/${endpoint}?${qs}`, { signal: ctrl.signal }); }
  catch { return []; }
  finally { clearTimeout(timer); }
  if (!resp.ok) return [];
  let data;
  try { data = await resp.json(); } catch { return []; }
  if (data.RESULT) return []; // INFO-200(자료없음) 또는 오류
  const bodyRows = data[endpoint];
  return (bodyRows && bodyRows[1] && bodyRows[1].row) || [];
}

function ymdAddDays(y, days) {
  const d = new Date(Date.UTC(+y.slice(0, 4), +y.slice(4, 6) - 1, +y.slice(6, 8) + days));
  return `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(d.getUTCDate()).padStart(2, "0")}`;
}
function weekdayOf(y) {
  return new Date(Date.UTC(+y.slice(0, 4), +y.slice(4, 6) - 1, +y.slice(6, 8))).getUTCDay();
}
function currentSemester(today) {
  const mo = +today.slice(4, 6);
  return mo >= 3 && mo <= 7 ? "1" : "2";
}
// 요청에 학기가 실려 오면 그걸 쓴다. 안 실려 오면 오늘 기준.
// ⚠ 방학에는 **다음 학기 시간표가 NEIS 에 아직 없다** — 실측(2026-08-09, 경기초):
//   1학기는 전 학년 「난초·매화·모란·장미」가 다 나오는데 2학기는 전 학년 0건이었다.
//   그래서 앱이 반 이름을 고르려고 이전 학기를 되짚어 물어본다.
function semesterOf(url, today) {
  const q = (url.searchParams.get("semester") || "").trim();
  return q === "1" || q === "2" ? q : currentSemester(today);
}
// 그 학기 «한복판» 날짜 — NEIS 시간표는 날짜창으로 조회하는데,
// 방학 중에 「오늘±」로 물으면 수업일이 하나도 안 걸려서 빈손으로 돌아온다.
function midOfSemester(ay, sem) {
  const y = +ay;
  return sem === "1" ? String(y) + "0520" : String(y + (1 - 1)) + "1110";
}
// 학년도(AY)는 3월 시작 — 1~2월은 전년도 학년도 2학기다.
function schoolYearOf(today) {
  const y = +today.slice(0, 4), mo = +today.slice(4, 6);
  return String(mo >= 3 ? y : y - 1);
}
// D1 batch는 문장 수 제한이 있어 큰 인서트는 청크로 나눈다.
async function batchChunked(db, stmts, size = 50) {
  for (let i = 0; i < stmts.length; i += size) await db.batch(stmts.slice(i, i + size));
}
// 급식 원문 → [{name, allergens}]. 응답에도 이 형태 그대로 나간다(계약 §4.2 개정).
function parseDishesJs(raw) {
  if (!raw) return [];
  const out = [];
  for (let chunk of String(raw).split("<br/>")) {
    chunk = chunk.trim();
    if (!chunk) continue;
    const m = chunk.match(/^(.*?)\s*\(([\d.]+)\)\s*$/);
    let name, allergens;
    if (m) { name = m[1].trim(); allergens = m[2].split(".").filter(Boolean).map(Number); }
    else { name = chunk; allergens = []; }
    if (name) out.push({ name, allergens });
  }
  return out;
}

const TT_ENDPOINT = { "초등학교": "elsTimetable", "중학교": "misTimetable", "고등학교": "hisTimetable" };

// index.js와 같은 값으로 맞춰 둔다. (이 파일은 index.js와 의도적으로 독립 — 위 14행 주석 참고)
/* ⚠ 30 → 60 (2026-08-09 지시). 「오늘부터 30일」만 받으니 **지난달 급식을 못 본다** —
   리포트의 «지난달 비교»도 못 하고, 학기 초에 지난 학기를 돌아볼 수도 없다.
   NEIS 는 과거 급식도 준다(실측 확인). 한 번에 두 달을 받아 둔다. */
const MEAL_FETCH_DAYS = 60;
const MEAL_RESYNC_DAYS = 7;   // 남은 일수가 아니라 수집 시각으로 판정(방학엔 급식이 없어 항상 부족으로 보인다)

async function warmMeals(db, school, today, key) {
  // `COUNT(*) > 0`이면 건너뛰던 것을 고쳤다. 1건만 남아도 재수집을 안 해 창이 계속 줄었다
  // (2026-07-24 운영 D1 실측: 학교별 1~6일치). 마지막 캐시일이 충분히 앞설 때만 건너뛴다.
  // `COUNT(*) > 0`이면 건너뛰던 것을 고쳤다 — 개학해 새 급식표가 올라와도 반영이 안 됐다.
  const mc = await db.prepare("SELECT MAX(last_synced_at) AS synced FROM meals WHERE school_id=?").bind(school.id).first();
  if (mc && mc.synced && mc.synced >= new Date(Date.now() - MEAL_RESYNC_DAYS * 86400000).toISOString()) return;
  const rows = await neisGet("mealServiceDietInfo", {
    ATPT_OFCDC_SC_CODE: school.office_code, SD_SCHUL_CODE: school.school_code,
    MLSV_FROM_YMD: today, MLSV_TO_YMD: ymdAddDays(today, MEAL_FETCH_DAYS),
  }, key);
  if (!rows.length) return;
  const now = new Date().toISOString();
  const stmts = rows.map((r) => {
    const raw = r.DDISH_NM || "";
    return db.prepare("INSERT OR IGNORE INTO meals (school_id, meal_date, meal_type_code, meal_type_name, dishes, dishes_parsed, calorie_info, origin_info, nutrition_info, last_synced_at) VALUES (?,?,?,?,?,?,?,?,?,?)")
      .bind(school.id, r.MLSV_YMD, r.MMEAL_SC_CODE, r.MMEAL_SC_NM, raw, JSON.stringify(parseDishesJs(raw)), r.CAL_INFO || null, r.ORPLC_INFO || null, r.NTR_INFO || null, now);
  });
  await batchChunked(db, stmts);
}

// 학사일정 범위는 **학년도 기준**이다(2026-07-25). 달력연도로 긁으면 1~2월(졸업식·종업식·학년말방학)이 빠진다.
// index.js scheduleRange()와 같은 규칙 — 한쪽만 고치면 웹과 앱이 다른 기간을 보게 된다.
function scheduleRange(today) {
  const ay = +schoolYearOf(today);
  return { from: `${ay}0101`, to: `${ay + 1}0228` };
}
async function warmSchedules(db, school, today, key) {
  const { from, to } = scheduleRange(today);
  // 있는지 판단은 **범위 끝쪽(다음해 1~2월)** 으로. 달력연도로 받아둔 학교는 앞쪽만 차 있다.
  const tail = await db.prepare("SELECT COUNT(*) AS n FROM academic_schedules WHERE school_id=? AND event_date BETWEEN ? AND ?")
    .bind(school.id, `${to.slice(0, 4)}0101`, to).first();
  if (tail && tail.n > 0) return;
  const rows = await neisGet("SchoolSchedule", {
    ATPT_OFCDC_SC_CODE: school.office_code, SD_SCHUL_CODE: school.school_code,
    AA_FROM_YMD: from, AA_TO_YMD: to,
  }, key);
  if (!rows.length) return;
  const now = new Date().toISOString();
  const seen = new Set(), stmts = [];
  for (const r of rows) {
    const k = `${r.AA_YMD}|${r.EVENT_NM}`;
    if (seen.has(k)) continue;
    seen.add(k);
    stmts.push(db.prepare("INSERT OR IGNORE INTO academic_schedules (school_id, event_date, event_name, event_content, closure_type, grade_flags, last_synced_at) VALUES (?,?,?,?,?,?,?)")
      .bind(school.id, r.AA_YMD, r.EVENT_NM, r.EVENT_CNTNT || null, r.SBTR_DD_SC_NM || null, "{}", now));
  }
  if (stmts.length) await batchChunked(db, stmts);
}

async function warmTimetable(db, school, grade, className, today, key, semReq) {
  const ep = TT_ENDPOINT[school.school_kind];
  if (!ep) return;
  const ay = schoolYearOf(today);
  const sem = semReq === "1" || semReq === "2" ? semReq : currentSemester(today);
  const cnt = await db.prepare("SELECT COUNT(*) AS n FROM timetables WHERE school_id=? AND school_year=? AND semester=? AND grade=? AND COALESCE(class_name,'')=COALESCE(?,'')")
    .bind(school.id, ay, sem, grade, className || null).first();
  if (cnt && cnt.n > 0) return;
  // 과거(−35일)를 포함해야 방학 직전·직후 워밍에서도 월~금 5요일이 모두 잡힌다.
  const rows = await neisGet(ep, {
    ATPT_OFCDC_SC_CODE: school.office_code, SD_SCHUL_CODE: school.school_code,
    AY: ay, SEM: sem, GRADE: grade, CLASS_NM: className || "",
    /* 지금 학기면 「오늘 언저리」가 맞다. 지난 학기를 되짚는 요청이면
       오늘 기준 날짜창엔 그 학기 수업일이 하나도 안 들어온다 → 그 학기 한복판으로 옮긴다. */
    ...(sem === currentSemester(today)
      ? { TI_FROM_YMD: ymdAddDays(today, -35), TI_TO_YMD: ymdAddDays(today, 14) }
      : { TI_FROM_YMD: ymdAddDays(midOfSemester(ay, sem), -14), TI_TO_YMD: ymdAddDays(midOfSemester(ay, sem), 14) }),
  }, key);
  if (!rows.length) return;
  // (요일|반|교실|교시) → 가장 자주 나온 과목을 정규 시간표로 축약 저장.
  const tally = new Map();
  for (const r of rows) {
    const w = weekdayOf(r.ALL_TI_YMD);
    if (w < 1 || w > 5) continue;
    const subj = (r.ITRT_CNTNT || "").trim();
    if (!subj) continue;
    const k = [w, r.CLASS_NM || "", r.CLRM_NM || "", r.PERIO].join("|");
    let e = tally.get(k);
    if (!e) { e = { counts: new Map(), meta: r, w }; tally.set(k, e); }
    e.counts.set(subj, (e.counts.get(subj) || 0) + 1);
  }
  const now = new Date().toISOString();
  const stmts = [];
  for (const { counts, meta, w } of tally.values()) {
    let best = null, bc = -1;
    for (const [s, c] of counts) if (c > bc) { bc = c; best = s; }
    stmts.push(db.prepare(
      "INSERT OR IGNORE INTO timetables (school_id, school_year, semester, day_night, track_name, department_name, classroom_name, weekday, grade, class_name, period, subject, last_synced_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
    ).bind(school.id, ay, sem, meta.DGHT_CRSE_SC_NM || null, meta.ORD_SC_NM || null, meta.DDDEP_NM || null, meta.CLRM_NM || null, w, meta.GRADE, meta.CLASS_NM, meta.PERIO, best, now));
  }
  if (stmts.length) await batchChunked(db, stmts);
}
