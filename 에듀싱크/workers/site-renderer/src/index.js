import {
  homePage,
  searchResultsPage,
  schoolDetailPage,
  kinderDetailPage,
  mypagePage,
  childrenManagePage,
  purgeAllPage,
  recordsPage,
  activitiesPage,
  subscribePage,
  payCompletePage,
  paymentsHistoryPage,
  notificationsPage,
  aboutPage,
  termsPage,
  privacyPage,
  helpPage,
  registerChildPage,
  onboardingPage,
  registerConfirmPage,
  childEditPage,
  noticePage,
  loginPage,
  feedbackPage,
  accountDeletePage,
} from "./templates.js";
import { sendPush } from "./push.js";
import { OG_PNG_BASE64 } from "./og_image.js";
import { ICON512_BASE64, FAVICON_ICO_BASE64 } from "./icons.js";
import { formsListPage, formPage } from "./forms.js";
import { providersFrom, authorizeUrl, fetchIdentity, providerLabel } from "./auth.js";
import { corsOrigin, corsHeaders, withCors } from "./api_core.js";
import { handleRecordsApi } from "./api_records.js";
import { handleLifeApi, claimInvite } from "./api_life.js";
import { resolveAuth, signToken, authSecret, TOKEN_TTL } from "./auth_core.js";
import { handleSchoolsApi } from "./api_schools.js";
import { handleAuthApi, linkSocialAccount } from "./api_auth.js";
import { handleOrdersApi, confirmOrderByAdmin, cancelOrderByAdmin } from "./api_orders.js";
import { handleSupportApi, answerInquiry, closeInquiry } from "./api_support.js";
import { handleMissionApi, missionCron } from "./api_mission.js";
import { handleRewardApi } from "./api_reward.js";
import { handleQuizApi } from "./api_quiz.js";
/* 🏫 학교 미션 «제공자» — 이 import 하나가 국내판과 해외판을 가른다(기획서 v2 §09).
   빼면 홈이 4칸에서 3칸이 되고, 나머지 미션 시스템은 그대로 돈다. */
import { handleSchoolMissionApi } from "./school_missions.js";
import { deleteChildCascade, deleteRecordAssets } from "./data_children.js";
import { withdrawAccount } from "./data_accounts.js";
import { findAccountByToken } from "./auth_core.js";

// 서비스워커 — 무페이로드 푸시 수신 시 서버에 "방금 울린 알림"(/api/push/latest)을 조회해
// 일정 이름·상세를 채워 표시. 조회 실패/해당 없음이면 기본 문구. 클릭 시 해당 학교 일정 탭으로 이동.
const SERVICE_WORKER_JS = `self.addEventListener('push', function(e){
  var fallback = {title:'아이서랍', body:'오늘 급식·시간표·챙길 일정을 확인하세요', url:'/mypage'};
  e.waitUntil(
    fetch('/api/push/latest', {credentials:'same-origin'})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(d){
        var n = (d && d.ok && d.title) ? d : fallback;
        return self.registration.showNotification(n.title, {body:n.body, data:{url:n.url}, tag:'reminder'});
      })
      .catch(function(){ return self.registration.showNotification(fallback.title, {body:fallback.body, data:{url:fallback.url}, tag:'reminder'}); })
  );
});
self.addEventListener('notificationclick', function(e){
  e.notification.close();
  e.waitUntil(clients.matchAll({type:'window'}).then(function(cs){
    var u=(e.notification.data&&e.notification.data.url)||'/mypage';
    for(var i=0;i<cs.length;i++){ if('focus' in cs[i]) return cs[i].focus(); }
    if(clients.openWindow) return clients.openWindow(u);
  }));
});`;

// 웹푸시 구독 저장(브라우저 → 서버).
async function handlePushSubscribe(request, db) {
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
  // 알림 설정도 켬.
  const upd = await db.prepare("UPDATE notif_settings SET enabled=1, updated_at=? WHERE owner_token=?").bind(nowIso, ownerToken).run();
  if (!upd.meta || upd.meta.changes === 0) await db.prepare("INSERT INTO notif_settings (owner_token, enabled, updated_at) VALUES (?, 1, ?)").bind(ownerToken, nowIso).run();
  const resp = json({ ok: true });
  for (const c of setCookie) resp.headers.append("Set-Cookie", c);
  return resp;
}

// 내 구독으로 테스트 알림 발송(실기기 확인용).
async function handlePushTest(request, db, env) {
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

// 자녀 무료 등록 시 부여하는 체험 기간(일). 결제 없이 이 기간 동안 전체 잠금 해제(§백엔드지시서).
// 2026-07-28 사장님 확정: 체험 후 전면 유료. 무료 티어는 없다.
// 2026-08-10 대표님 확정: 체험은 **1주일**(api_records.js TRIAL_DAYS = 7).
// (7일은 «알림장 한 번 받아보기»도 안 되는 길이였다 — 한 주 다 돌려봐야 값을 안다)
const TRIAL_DAYS = 14;
// 이용권 하나로 등록 가능한 자녀 최대 수. 무료는 FREE_MAX_CHILDREN(1명)까지.
// 2026-07-19: 인원별 추가 과금(자녀2 +500원·자녀3 +1,000원) 폐지 → 단일 기간권에 3명 포함.
// 4명 이상 실다자녀는 고객센터 수동 예외로 처리한다(코드 상한은 3 유지).
const MAX_CHILDREN = 3;
const FREE_MAX_CHILDREN = 1;
// 무료 기록 상한(블록1). 초과 시 **신규 업로드만** 잠그고 열람·검색·삭제는 항상 허용한다
// — 쌓은 걸 볼모로 잡지 않는다(지시서 v4 1-2).
const FREE_MAX_RECORDS = 20;
const PAID_MAX_RECORDS = 1000; // 자녀당(어뷰징 상한)

// ── 무료 개방 기간 — **학교(자녀)별 개별 전환** ──────────────────
// 2026-07-19 결정(docs/회신.md): 전역 날짜 하나로 끊지 않고 **자녀가 다니는 학교의 2학기 개학일**을 기준으로 삼는다.
//   · 일괄 날짜는 어느 쪽이든 거짓말이 된다 — 이르면 늦게 개학하는 1만+개교의 무료 기간을 깎고,
//     늦추면 이미 개학한 학교에 "개학 전까지 무료"가 거짓이 된다. 학교별이면 모든 사용자에게 문장이 참이다.
//   · 마케팅 문구도 개인화된다: "우리 아이 학교 개학 전까지 무료".
// 개학일은 schools.sem2_start(YYYYMMDD)에 사전 계산돼 있다(migrate_sem2start). 219만 행을 매 요청 뒤지지 않기 위함.
const SEM2_FALLBACK = "20260901"; // 학사일정에 개학일이 없는 학교(3,699개교) 폴백 — 약속보다 후한 방향.
function ymd(d = new Date()) {
  return d.toISOString().slice(0, 10).replace(/-/g, "");
}
function schoolOpenUntil(school) {
  return (school && school.sem2_start) || SEM2_FALLBACK;
}
// 이 학교가 아직 개학 전인가 = 무료 개방 중인가. 개방 중이면 ①자녀 수 ②콘텐츠 ③기록 한도를 모두 푼다.
function isFreeOpenForSchool(school, today = ymd()) {
  return today < schoolOpenUntil(school);
}
// 회원 등급별 자녀 등록 한도 — 화면 문구("1/1명" vs "1/3명")와 서버 차단이 같은 값을 쓰도록 한 곳에서 관리.
// freeOpen은 호출부가 "지금 다루는 학교" 기준으로 계산해 넘긴다(자녀 단위 원칙).
function maxChildrenFor(isPaid, freeOpen = false) {
  return (freeOpen || isPaid) ? MAX_CHILDREN : FREE_MAX_CHILDREN;
}
// 자녀당 기록 상한. 개방 중인 학교의 자녀는 유료와 동일하게 취급.
function maxRecordsFor(isPaid, freeOpen = false) {
  return (freeOpen || isPaid) ? PAID_MAX_RECORDS : FREE_MAX_RECORDS;
}


// 블록1 자녀기록 전체 스위치. 운영 기본 OFF, 로컬(.dev.vars) ON.
// 새 기능은 전부 이 방식으로 — 플래그 OFF로 배포하고, 완성·검증 후 사장님 지시로 ON.
function featureRecords(env) {
  return env && env.FEATURE_RECORDS === "true";
}

const LEVEL_TO_KIND = { elem: "초등학교", mid: "중학교", high: "고등학교" };
import {
  adminMonitorPage,
  adminBannersPage,
  adminCorrectPage,
  adminMembersPage,
  adminReportsPage,
  adminFeedbackPage,
  adminPaymentsPage,
  adminOrdersPage,
  adminAuditPage,
  adminInquiriesPage,
  adminCommunityPage,
  adminDataPage,
} from "./admin_templates.js";

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      // 개발 중 브라우저가 옛 렌더를 캐시해 라벨-값이 어긋나 보이는 문제 방지(2026-07-12).
      "Cache-Control": "no-store",
    },
  });
}

// 상대경로 302. Response.redirect()는 절대 URL만 받는데, `wrangler dev --remote` 모드에선
// url.origin이 배포 도메인(workers.dev)으로 잡혀 미배포 시 "Nothing here"가 뜬다.
// Location에 상대경로를 주면 브라우저가 현재 호스트(127.0.0.1:8788 등) 기준으로 해석해 머문다.
function redirect(location) {
  return new Response(null, { status: 302, headers: { Location: location } });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function todayYmd() {
  // Workers 런타임은 UTC 기준이라 그냥 new Date()를 쓰면 한국시간 새벽(UTC로는 전날)에
  // 날짜가 하루 밀린다(2026-07-12 실사로 발견). KST(UTC+9) 기준으로 명시적으로 계산.
  const kst = new Date(Date.now() + 9 * 60 * 60 * 1000);
  return (
    kst.getUTCFullYear().toString() +
    String(kst.getUTCMonth() + 1).padStart(2, "0") +
    String(kst.getUTCDate()).padStart(2, "0")
  );
}

// 검색 키워드 의도 인식(§무료유료경계 지시서_5). "숭미초 급식", "숭미초 시간표"처럼
// 학교명과 함께 들어온 급식/시간표/학사일정 단어를 tab 의도로 인식하고, 그 단어를
// 검색어에서 제거한 나머지로 학교를 찾는다. 매칭 1곳이면 해당 탭으로 딥링크.
const INTENT_KEYWORDS = [
  { tab: "meal", words: ["급식", "식단표", "식단", "메뉴"] },
  { tab: "timetable", words: ["시간표"] },
  { tab: "schedule", words: ["학사일정", "학사정보", "방학", "휴업일"] },
];

function parseSearchIntent(rawQuery) {
  let cleaned = rawQuery;
  let tab = null;
  for (const { tab: t, words } of INTENT_KEYWORDS) {
    for (const w of words) {
      if (cleaned.includes(w)) {
        if (tab === null) tab = t; // 첫 매칭 의도만 딥링크에 사용
        cleaned = cleaned.split(w).join(" ");
      }
    }
  }
  return { schoolQuery: cleaned.replace(/\s+/g, " ").trim(), tab };
}

async function handleSearch(db, url) {
  const q = (url.searchParams.get("q") || "").trim();
  const level = url.searchParams.get("level") || "";
  // 학교명 검색어도 학교급 필터도 없으면 홈으로.
  if (!q && !level) return html(homePage());

  // 탭 의도("숭미초 급식")는 학교명만 뽑는 용도로만 쓴다 — 특정 탭으로 직행시키지 않는다(§검색 직행 제거).
  const { schoolQuery } = parseSearchIntent(q);
  // 키워드만 입력("급식")해서 학교명이 비면 원본으로 폴백(잘못된 전체검색 방지).
  const effectiveQuery = schoolQuery || q;

  // 유치원은 1차 범위에서 최종 제외(§결정로그) — 검색 노출하지 않는다.
  const kind = LEVEL_TO_KIND[level] || null;
  let sql = "SELECT * FROM schools WHERE name LIKE ?";
  const binds = [`%${effectiveQuery}%`];
  if (kind) {
    sql += " AND school_kind = ?";
    binds.push(kind);
  }
  sql += " ORDER BY name LIMIT 50";
  const { results: schools } = await db.prepare(sql).bind(...binds).all();

  // 검색은 결과 건수와 무관하게(1건이어도) 항상 결과 목록을 먼저 보여준다 — 상세는 사용자가 목록에서 선택해야 진입.
  return html(searchResultsPage(effectiveQuery, level, schools));
}

// ===== 온디맨드 NEIS 수집 =====
// 전국 12,563개교 콘텐츠(급식·시간표·학사일정)를 D1에 통째로 밀어넣으면 시간표만 1,150만행이라 무리.
// → 학교를 열 때 그 학교 것만 NEIS에서 즉시 받아 D1에 캐시(lazy). 다음부턴 D1에서 바로 읽힘.
// 인증키 없이도 조회 가능(2026-07-12 확인). 배치 인서트로 D1 왕복 최소화.
function ymdAddDays(ymd, days) {
  const d = new Date(Date.UTC(+ymd.slice(0, 4), +ymd.slice(4, 6) - 1, +ymd.slice(6, 8) + days));
  return `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(d.getUTCDate()).padStart(2, "0")}`;
}
// YYYYMMDD → 요일(0=일,1=월,…,6=토). 시간표를 요일 단위로 축약/조회할 때 사용.
function weekdayOf(ymd) {
  return new Date(Date.UTC(+ymd.slice(0, 4), +ymd.slice(4, 6) - 1, +ymd.slice(6, 8))).getUTCDay();
}
// NEIS 인증키(env.NEIS_API_KEY) — fetch 진입점에서 1회 세팅. ⚠️ 키 없으면 NEIS가 5건만 주므로 필수.
let NEIS_KEY = "";
async function neisGet(endpoint, params) {
  const base = { Type: "json", pSize: "1000", ...params };
  if (NEIS_KEY) base.KEY = NEIS_KEY; // 키 있을 때만(빈 KEY는 미인증 취급되어 5건 제한)
  const qs = new URLSearchParams(base);
  // 타임아웃은 AbortController로(일부 로컬 런타임이 AbortSignal.timeout 미지원 → fetch 옵션에서 예외날 수 있음).
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
  const body = data[endpoint];
  return (body && body[1] && body[1].row) || [];
}
// 급식 원문("밥<br/>국 (5.6)") → [{name, allergens:[5,6]}]. common.py parse_dishes와 동일 규칙.
function parseDishesJs(raw) {
  if (!raw) return [];
  const out = [];
  for (let chunk of raw.split("<br/>")) {
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
function currentSemester(today) { const mo = +today.slice(4, 6); return (mo >= 3 && mo <= 7) ? "1" : "2"; }
// 학년도(AY) — 3월 시작. 1~2월은 "전년도 학년도 2학기"에 속하므로 달력연도-1을 반환.
// (예: 2027-01 → 2026학년도 2학기. 달력연도를 그대로 쓰면 NEIS 조회·D1 필터가 모두 빈 결과가 된다.)
function schoolYearOf(today) {
  const y = +today.slice(0, 4), mo = +today.slice(4, 6);
  return String(mo >= 3 ? y : y - 1);
}
// D1 batch는 문장 수 제한이 있어 큰 인서트는 청크로 나눠 실행(학사일정 1년치·시간표 등 수백 행 대비).
async function batchChunked(db, stmts, size = 50) {
  for (let i = 0; i < stmts.length; i += size) await db.batch(stmts.slice(i, i + size));
}

// 급식 보유 창 — 롤링(2026-07-24 지시: 달 단위로 끊지 말고 계속 앞으로 밀어라).
// 판정 기준은 "언제 받았나"(TTL)다. "며칠치 남았나"로 판정하면 안 된다 —
// 방학엔 NEIS에 급식 자체가 없어서 항상 부족으로 나오고, 열 때마다 NEIS를 때리게 된다.
const MEAL_FETCH_DAYS = 60;   /* 30 → 60 (2026-08-09) — 지난달 급식을 볼 수 있게 */
const MEAL_RESYNC_DAYS = 7;   // 학교당 최대 주 1회만 다시 받는다(급식표는 수시로 바뀜)

async function ensureMeals(db, school, today) {
  // ⚠️ 예전엔 `COUNT(*) > 0`이면 건너뛰었다 → 한 번 채운 뒤로는 미래 급식이 전부 소진될 때까지
  // 절대 다시 안 받았다. 개학해서 새 급식표가 올라와도 반영이 안 된다.
  // 이제는 마지막 수집 시각으로 판정한다(주 1회). 남은 일수로 판정하면 방학에 NEIS를 계속 때린다.
  const mc = await db.prepare("SELECT MAX(last_synced_at) AS synced FROM meals WHERE school_id=?").bind(school.id).first();
  if (mc && mc.synced && mc.synced >= new Date(Date.now() - MEAL_RESYNC_DAYS * 86400000).toISOString()) return;
  const rows = await neisGet("mealServiceDietInfo", { ATPT_OFCDC_SC_CODE: school.office_code, SD_SCHUL_CODE: school.school_code, MLSV_FROM_YMD: today, MLSV_TO_YMD: ymdAddDays(today, MEAL_FETCH_DAYS) });
  if (!rows.length) return;
  const now = new Date().toISOString();
  const stmts = rows.map((r) => {
    const raw = r.DDISH_NM || "";
    return db.prepare("INSERT OR IGNORE INTO meals (school_id, meal_date, meal_type_code, meal_type_name, dishes, dishes_parsed, calorie_info, origin_info, nutrition_info, last_synced_at) VALUES (?,?,?,?,?,?,?,?,?,?)")
      .bind(school.id, r.MLSV_YMD, r.MMEAL_SC_CODE, r.MMEAL_SC_NM, raw, JSON.stringify(parseDishesJs(raw)), r.CAL_INFO || null, r.ORPLC_INFO || null, r.NTR_INFO || null, now);
  });
  await batchChunked(db, stmts);
}
// 학사일정을 받아올 기간 — **학년도 기준**(2026-07-25).
// 달력연도(0101~1231)로만 긁으면 **1~2월(졸업식·종업식·학년말방학)이 통째로 빠진다.**
// 그 두 달은 같은 학년도(3월 시작)에 속해 NEIS에 이미 공시돼 있다(실측: 서울숭미초 2027-01~02 68건).
// 시작을 ay0101로 잡는 건 학년도 시작 전(1~2월)에 조회해도 그 해가 통째로 들어오게 하려는 것.
function scheduleRange(today) {
  const ay = +schoolYearOf(today);
  return { from: `${ay}0101`, to: `${ay + 1}0228` };
}
async function ensureSchedules(db, school, today) {
  const { from, to } = scheduleRange(today);
  // "한 건이라도 있으면 건너뛰기"는 안 된다 — 달력연도로 받아둔 학교는 1~2월이 비어 있는데도
  // 있다고 판단해 영영 안 채워진다. **범위 끝쪽(다음해 1~2월)이 있는지**로 본다.
  const tail = await db.prepare("SELECT COUNT(*) AS n FROM academic_schedules WHERE school_id=? AND event_date BETWEEN ? AND ?")
    .bind(school.id, `${to.slice(0, 4)}0101`, to).first();
  if (tail && tail.n > 0) return;
  const rows = await neisGet("SchoolSchedule", { ATPT_OFCDC_SC_CODE: school.office_code, SD_SCHUL_CODE: school.school_code, AA_FROM_YMD: from, AA_TO_YMD: to });
  if (!rows.length) return;
  const now = new Date().toISOString();
  const seen = new Set(), stmts = [];
  for (const r of rows) {
    const k = `${r.AA_YMD}|${r.EVENT_NM}`;
    if (seen.has(k)) continue; seen.add(k);
    stmts.push(db.prepare("INSERT OR IGNORE INTO academic_schedules (school_id, event_date, event_name, event_content, closure_type, grade_flags, last_synced_at) VALUES (?,?,?,?,?,?,?)")
      .bind(school.id, r.AA_YMD, r.EVENT_NM, r.EVENT_CNTNT || null, r.SBTR_DD_SC_NM || null, "{}", now));
  }
  if (stmts.length) await batchChunked(db, stmts);
}
// 학사일정 강제 갱신(롤링 크론용) — ensureSchedules와 달리 기존 데이터가 있어도 다시 받아 교체.
// NEIS가 빈 응답/오류를 주면 기존 데이터를 지우지 않고 그대로 둔다(안전).
async function refreshSchedules(db, school, today) {
  const { from, to } = scheduleRange(today);
  const rows = await neisGet("SchoolSchedule", { ATPT_OFCDC_SC_CODE: school.office_code, SD_SCHUL_CODE: school.school_code, AA_FROM_YMD: from, AA_TO_YMD: to });
  if (!rows.length) return false;
  const now = new Date().toISOString();
  const seen = new Set(), stmts = [db.prepare("DELETE FROM academic_schedules WHERE school_id = ? AND event_date BETWEEN ? AND ?").bind(school.id, from, to)];
  for (const r of rows) {
    const k = `${r.AA_YMD}|${r.EVENT_NM}`;
    if (seen.has(k)) continue; seen.add(k);
    stmts.push(db.prepare("INSERT OR IGNORE INTO academic_schedules (school_id, event_date, event_name, event_content, closure_type, grade_flags, last_synced_at) VALUES (?,?,?,?,?,?,?)")
      .bind(school.id, r.AA_YMD, r.EVENT_NM, r.EVENT_CNTNT || null, r.SBTR_DD_SC_NM || null, "{}", now));
  }
  await batchChunked(db, stmts);
  return true;
}

/* ═══ 우리 사용자 학교 «먼저» 자동 갱신 (2026-08-13 대표님:
     「학교일정·시간표·급식 등을 자동으로 가져올 수 있게 돌려야 해」) ═══════════

   여태 크론이 한 건 **학사일정뿐**이었고, 그것도 전국 12,564 개 학교를 무차별로
   3곳/분씩 돌았다(한 바퀴 ≈ 3일). **급식과 시간표는 크론이 아예 안 건드렸다** —
   사용자가 그 화면을 열 때만(온디맨드) 받아왔다.
   실측(2026-08-13): 학교 12,564 곳 중 급식 보유 14곳 · 시간표 보유 8곳.

   그래서 이런 구멍이 난다 — 개학해서 새 급식표가 올라왔는데 **앱을 열기 전까지는**
   앱이 아직 방학인 줄 안다. 홈 「오늘 급식」과 알림이 그 사이 빈 채로 있다.

   → 자녀가 등록된 학교는 **전국 롤링보다 먼저, 더 자주** 채운다.
     대상이 «우리 아이 학교»뿐이라 수가 적고, 주기를 두어 NEIS 부담도 작다.
   ⚠ 시각 기록(sync_state)을 **성공·실패와 무관하게** 찍는다 — 안 그러면 NEIS 가 조용한
     학교 하나 때문에 매분 같은 곳을 때린다(웹방화벽에 걸리는 지름길이다). */
const KID_MEAL_HOURS = 12;   // 급식 — 반나절에 한 번(개학·식단 변경을 그날 안에 잡는다)
const KID_SCHED_DAYS = 3;    // 학사일정 — 사흘에 한 번
const KID_TT_DAYS = 3;       // 시간표 — 사흘에 한 번
const KID_BATCH = 2;         // 한 틱에 학교 2곳까지 (매분 도니 금세 한 바퀴)

async function rollChildSchoolsRefresh(db, today) {
  const mealCut = new Date(Date.now() - KID_MEAL_HOURS * 3600000).toISOString();
  const schedCut = new Date(Date.now() - KID_SCHED_DAYS * 86400000).toISOString();
  const ttCut = new Date(Date.now() - KID_TT_DAYS * 86400000).toISOString();

  /* 자녀가 실제로 등록된 학교만. 검수용(is_test=1)은 뺀다 — 대표님 검수 계정 때문에
     NEIS 를 도는 건 낭비다. 오래 안 받은 학교부터. */
  const { results: targets } = await db.prepare(
    `SELECT s.id, s.office_code, s.school_code, s.school_kind,
            st.meals_synced_at, st.schedules_synced_at, st.timetable_synced_at
       FROM schools s
       JOIN (SELECT DISTINCT school_id FROM children WHERE is_test = 0) k ON k.school_id = s.id
       LEFT JOIN sync_state st ON st.school_id = s.id
      WHERE st.school_id IS NULL
         OR COALESCE(st.meals_synced_at, '') < ?
         OR COALESCE(st.schedules_synced_at, '') < ?
         OR COALESCE(st.timetable_synced_at, '') < ?
      ORDER BY COALESCE(st.meals_synced_at, '') ASC
      LIMIT ?`
  ).bind(mealCut, schedCut, ttCut, KID_BATCH).all();

  const now = new Date().toISOString();
  for (const school of targets || []) {
    // ── 급식 — 지금부터 앞으로. ensureMeals 는 «주 1회» 잠금이 걸려 있어 여기선 직접 받는다
    if (!school.meals_synced_at || school.meals_synced_at < mealCut) {
      try {
        const rows = await neisGet("mealServiceDietInfo", {
          ATPT_OFCDC_SC_CODE: school.office_code, SD_SCHUL_CODE: school.school_code,
          MLSV_FROM_YMD: today, MLSV_TO_YMD: ymdAddDays(today, MEAL_FETCH_DAYS),
        });
        const stmts = rows.map((r) => {
          const raw = r.DDISH_NM || "";
          return db.prepare("INSERT OR IGNORE INTO meals (school_id, meal_date, meal_type_code, meal_type_name, dishes, dishes_parsed, calorie_info, origin_info, nutrition_info, last_synced_at) VALUES (?,?,?,?,?,?,?,?,?,?)")
            .bind(school.id, r.MLSV_YMD, r.MMEAL_SC_CODE, r.MMEAL_SC_NM, raw,
                  JSON.stringify(parseDishesJs(raw)), r.CAL_INFO || null, r.ORPLC_INFO || null, r.NTR_INFO || null, now);
        });
        if (stmts.length) await batchChunked(db, stmts);
      } catch { /* 시각은 아래에서 찍는다 — 다음 주기에 재시도 */ }
      await db.prepare(
        "INSERT INTO sync_state (school_id, meals_synced_at) VALUES (?, ?) ON CONFLICT(school_id) DO UPDATE SET meals_synced_at = excluded.meals_synced_at"
      ).bind(school.id, now).run();
    }

    // ── 학사일정 — 이미 있는 강제 갱신을 그대로 쓴다(빈 응답이면 기존 것을 안 지운다)
    if (!school.schedules_synced_at || school.schedules_synced_at < schedCut) {
      try { await refreshSchedules(db, school, today); } catch { /* 다음 주기 */ }
      await db.prepare(
        "INSERT INTO sync_state (school_id, schedules_synced_at) VALUES (?, ?) ON CONFLICT(school_id) DO UPDATE SET schedules_synced_at = excluded.schedules_synced_at"
      ).bind(school.id, now).run();
    }

    // ── 시간표 — 학교가 아니라 **학년·반**마다다. 그 학교에 등록된 자녀들의 반만 받는다
    if (!school.timetable_synced_at || school.timetable_synced_at < ttCut) {
      try {
        const { results: classes } = await db.prepare(
          "SELECT DISTINCT grade, class_name FROM children WHERE school_id = ? AND is_test = 0"
        ).bind(school.id).all();
        for (const c of classes || []) await ensureTimetable(db, school, c.grade, c.class_name, today);
      } catch { /* 다음 주기 */ }
      await db.prepare(
        "INSERT INTO sync_state (school_id, timetable_synced_at) VALUES (?, ?) ON CONFLICT(school_id) DO UPDATE SET timetable_synced_at = excluded.timetable_synced_at"
      ).bind(school.id, now).run();
    }
  }
  return (targets || []).length;
}

// 롤링 갱신 1틱 — 갱신한 지 REFRESH_DAYS 지난(또는 미시도) 학교를 BATCH곳 골라 다시 받는다.
// 매분 실행돼도 대부분의 분엔 대상 0곳(전부 최신)이라 NEIS 호출이 없다. 연초(1월)엔 조회 연도가
// 바뀌므로 한 바퀴(약 3일) 돌면서 새해 일정으로 자동 교체된다. 신규 학교(sync_state 없음)가 최우선.
async function rollSchedulesRefresh(db, today) {
  const REFRESH_DAYS = 30, BATCH = 3;
  const cutoff = new Date(Date.now() - REFRESH_DAYS * 86400000).toISOString();
  const { results: stale } = await db.prepare(
    `SELECT s.id, s.office_code, s.school_code, st.schedules_synced_at
     FROM schools s LEFT JOIN sync_state st ON st.school_id = s.id
     WHERE st.school_id IS NULL OR st.schedules_synced_at IS NULL OR st.schedules_synced_at < ?
     ORDER BY st.schedules_synced_at ASC LIMIT ?`
  ).bind(cutoff, BATCH).all();
  const now = new Date().toISOString();
  for (const school of stale) {
    try { await refreshSchedules(db, school, today); } catch { /* 실패해도 시각은 기록 — 다음 바퀴에 재시도 */ }
    await db.prepare(
      "INSERT INTO sync_state (school_id, schedules_synced_at) VALUES (?, ?) ON CONFLICT(school_id) DO UPDATE SET schedules_synced_at = excluded.schedules_synced_at"
    ).bind(school.id, now).run();
  }
  return stale.length;
}

// 현재 탭에 필요한 콘텐츠만 온디맨드로 채운다(§성능: 학교 클릭=overview 시엔 NEIS 호출 0 → 즉시 렌더).
async function ensureContentForTab(db, school, today, tab) {
  if (tab === "meal") await ensureMeals(db, school, today);
  else if (tab === "schedule") await ensureSchedules(db, school, today);
  // overview/community/timetable: 여기선 호출 안 함(시간표는 유료 자녀 확정 후 별도 처리).
}

// 시간표 캐시 보장(유료 자녀의 학년·반). 없으면 NEIS에서 받아 저장.
// 비동기 워밍 엔드포인트 — 템플릿이 콘텐츠 없을 때 호출. 서버가 NEIS에서 받아 캐시하고 {ok} 반환.
// 페이지는 이미 렌더된 상태이므로 사용자는 로더만 보고, 완료되면 JS가 새로고침(?w=1)한다.
async function handleSchoolWarm(request, db, url) {
  const slug = url.searchParams.get("slug");
  const kind = url.searchParams.get("kind"); // meal | schedule | timetable
  if (!slug || !kind) return json({ ok: false }, 400);
  const school = await db.prepare("SELECT * FROM schools WHERE slug = ?").bind(decodeURIComponent(slug)).first();
  if (!school) return json({ ok: false }, 404);
  const today = todayYmd();
  try {
    if (kind === "meal") await ensureMeals(db, school, today);
    else if (kind === "schedule") await ensureSchedules(db, school, today);
    else if (kind === "timetable") {
      const grade = url.searchParams.get("grade");
      const className = url.searchParams.get("class") || null;
      if (grade) await ensureTimetable(db, school, grade, className, today);
    }
    return json({ ok: true });
  } catch (e) {
    return json({ ok: false, error: String(e) });
  }
}

async function ensureTimetable(db, school, grade, className, today) {
  const ep = TT_ENDPOINT[school.school_kind];
  if (!ep) return;
  const ay = schoolYearOf(today), sem = currentSemester(today);
  // 이미 이 학기 시간표가 있으면 스킵(학기 바뀌면 새 학기분을 다시 받는다).
  const cnt = await db.prepare("SELECT COUNT(*) AS n FROM timetables WHERE school_id=? AND school_year=? AND semester=? AND grade=? AND COALESCE(class_name,'')=COALESCE(?,'')").bind(school.id, ay, sem, grade, className || null).first();
  if (cnt && cnt.n > 0) return;
  // 과거~미래로 넓게 받아서 요일별 "가장 자주 나온 과목"을 정규 시간표로 축약 저장.
  // 과거(−35일)를 포함해야 방학 직전·직후에 워밍해도 정상 수업 주간의 5요일이 모두 잡힌다(금요일 공백 방지).
  // SEM 파라미터가 학기를 강제하므로 구간이 지난 학기 날짜까지 걸쳐도 다른 학기 데이터는 섞이지 않는다.
  const rows = await neisGet(ep, { ATPT_OFCDC_SC_CODE: school.office_code, SD_SCHUL_CODE: school.school_code, AY: ay, SEM: sem, GRADE: grade, CLASS_NM: className || "", TI_FROM_YMD: ymdAddDays(today, -35), TI_TO_YMD: ymdAddDays(today, 14) });
  if (!rows.length) return;
  // (요일|반|교실|교시) → {과목 카운트, 대표 메타}. 반/교실은 고교 선택과목 때문에 키에 포함.
  const tally = new Map();
  for (const r of rows) {
    const w = weekdayOf(r.ALL_TI_YMD);
    if (w < 1 || w > 5) continue; // 주말 제외
    const subj = (r.ITRT_CNTNT || "").trim();
    if (!subj) continue;
    const key = [w, r.CLASS_NM || "", r.CLRM_NM || "", r.PERIO].join("|");
    let e = tally.get(key);
    if (!e) { e = { counts: new Map(), meta: r, w }; tally.set(key, e); }
    e.counts.set(subj, (e.counts.get(subj) || 0) + 1);
  }
  const now = new Date().toISOString();
  const stmts = [];
  for (const { counts, meta, w } of tally.values()) {
    let best = null, bc = -1;
    for (const [s, c] of counts) { if (c > bc) { bc = c; best = s; } }
    stmts.push(db.prepare(
      "INSERT OR IGNORE INTO timetables (school_id, school_year, semester, day_night, track_name, department_name, classroom_name, weekday, grade, class_name, period, subject, last_synced_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
    ).bind(school.id, ay, sem, meta.DGHT_CRSE_SC_NM || null, meta.ORD_SC_NM || null, meta.DDDEP_NM || null, meta.CLRM_NM || null, w, meta.GRADE, meta.CLASS_NM, meta.PERIO, best, now));
  }
  if (stmts.length) await batchChunked(db, stmts);
}

async function handleSchoolDetail(db, slug, url, request, env) {
  const school = await db
    .prepare("SELECT * FROM schools WHERE slug = ?")
    .bind(slug)
    .first();
  if (!school) return html("학교를 찾을 수 없습니다.", 404);

  const today = todayYmd();
  const tab = url.searchParams.get("tab") || "overview";
  const ownerToken = getCookie(request, "owner_token");

  // 온디맨드 콘텐츠는 서버에서 블로킹하지 않는다(NEIS가 느려 페이지가 5초 멈추던 문제).
  // 대신 페이지를 즉시 렌더하고, 캐시가 비었으면 템플릿이 "불러오는 중" 표시 + /api/school-warm 호출 후 새로고침.
  const warmed = url.searchParams.get("w") === "1"; // 이미 워밍 시도했는지(무한루프 방지)

  // 아래 5개 쿼리는 서로 의존관계가 없어(모두 school.id/today만 필요) 병렬 실행 — 순차 await였을 때
  // 원격 D1 왕복 지연이 누적되어 페이지가 느렸음(§성능개선).
  const yearNow = today.slice(0, 4);
  const [siblingsRes, allMealsRes, schedulesRes, details, yearSchedulesRes, communityPostsRes] = await Promise.all([
    ownerToken
      ? db
          .prepare(
            `SELECT children.*, schools.slug AS school_slug, schools.name AS school_name, schools.school_kind AS school_kind
             FROM children JOIN schools ON schools.id = children.school_id
             WHERE owner_token = ? ORDER BY children.created_at`
          )
          .bind(ownerToken)
          .all()
      : Promise.resolve({ results: [] }),
    // 급식: 오늘 이후 전체(조식/중식/석식 모두) — 급식 탭에서 3끼 탭으로 보여주기 위해 전부 넘긴다.
    // 기숙사형 고교는 조식·석식도 제공하므로 날짜별 대표 1건으로 줄이지 않는다.
    db
      .prepare("SELECT * FROM meals WHERE school_id = ? AND meal_date >= ? ORDER BY meal_date, meal_type_code LIMIT 90")
      .bind(school.id, today)
      .all(),
    // 학사일정: 오늘 이후 날짜순. LIMIT는 "이달의 행사"(중요일정 자동분류)가 월말 이벤트까지
    // 커버하도록 넉넉히. 첫 건=가장 가까운 일정, 중요일정 분류/이달의행사는 templates에서 계산.
    db
      .prepare("SELECT * FROM academic_schedules WHERE school_id = ? AND event_date >= ? ORDER BY event_date LIMIT 60")
      .bind(school.id, today)
      .all(),
    // 학교 상세 공시(학교알리미) — 아직 데이터가 없으면 null. 있으면 스탯 그리드가 6칸으로 확장된다.
    db.prepare("SELECT * FROM school_details WHERE school_id = ?").bind(school.id).first(),
    // 학사일정 탭의 "월별 행사 달력"용 — 올해 전체(과거 포함) 조회. 위 schedules(오늘 이후)와 별개로
    // 월 이동(이전/다음 달)을 서버 재조회 없이 클라이언트에서 바로 처리하기 위해 연간 데이터를 통째로 넘긴다.
    db
      .prepare("SELECT event_date, event_name, closure_type FROM academic_schedules WHERE school_id = ? AND event_date BETWEEN ? AND ? ORDER BY event_date")
      .bind(school.id, `${yearNow}0101`, `${yearNow}1231`)
      .all(),
    // 커뮤니티: 숨김(hidden) 처리 안 된 글만, 최신순 50개.
    db
      .prepare(
        // 작성자 표시명 = display_name(직접 입력) 우선, 없으면(구 데이터) "익명".
        // 작성자 표시명 = 스냅샷된 커뮤니티 닉네임(display_name) 우선, 없으면 "익명". 학년·반은 작성 당시 박제값.
        `SELECT community_posts.*, COALESCE(NULLIF(TRIM(community_posts.display_name), ''), '익명') AS author_nickname
         FROM community_posts
         WHERE community_posts.school_id = ? AND community_posts.hidden = 0
         ORDER BY community_posts.created_at DESC LIMIT 100`
      )
      .bind(school.id)
      .all(),
  ]);
  const siblings = siblingsRes.results;
  const allMeals = allMealsRes.results;
  const schedules = schedulesRes.results;
  const yearSchedules = yearSchedulesRes.results;
  const communityPosts = communityPostsRes.results;

  // 유료(잠금 해제) 판정: owner_token 쿠키의 등록 자녀 중 이 학교에 해당하는 게 있으면 유료 화면.
  // 관리자 테스트 자녀 등록(§관리자지시서_1 §4)도 이 경로로 잠금이 풀린다(결제 없이 QA용).
  let paidChild = null;
  if (ownerToken) {
    // 이 학교에 등록된 자녀 중, 테스트(is_test)거나 이용권이 유효(trial_expires_at>now)한 것만 유료.
    // 무료 개방 기간(FREE_OPEN_UNTIL 이전)에는 체험 만료를 무시하고 전원 개방한다 —
    // 이게 없으면 "개학 전까지 무료"인데 등록 7일 뒤 잠기는 구멍이 생긴다(2026-07-19 수정, Q1=A).
    const nowIso = new Date().toISOString();
    const freeOpen = isFreeOpenForSchool(school);
    const valid = (c) => c.school_id === school.id && (c.is_test || freeOpen || (c.trial_expires_at && c.trial_expires_at > nowIso));
    // ?child=<id>로 특정 자녀 선택(같은 학교에 형제가 있을 때 전환용). 없으면 첫 유효 자녀.
    const childParam = url.searchParams.get("child");
    paidChild = (childParam ? siblings.find((c) => String(c.id) === childParam && valid(c)) : null)
      || siblings.find(valid) || null;
  }
  // 잠금 해제(유료 화면)는 로그인(계정)한 사용자만 — 미로그인 브라우저에 남은 자녀 쿠키로 남의 일정 세부가
  // 열리던 문제 방지(로그인 게이팅과 일관). 관리자 테스트 자녀(is_test)는 QA용이라 로그인 없이도 해제.
  const account = await getAccount(db, request);
  const paid = !!paidChild && (paidChild.is_test || !!account);

  // 시간표 탭 하단 요약줄용 — 오늘 요일에 걸리는 방과후·활동.
  // 유효기간은 SQL로, 요일은 JS로 거른다(days_of_week가 CSV라 LIKE는 "1"이 "11"에 걸린다).
  let todayActs = [];
  if (paid && paidChild) {
    const dow = new Date().getDay() || 7; // JS 0=일 → 우리 규칙 7=일
    const { results: ta } = await db
      .prepare("SELECT * FROM activity_schedules WHERE child_id = ? AND start_date <= ? AND end_date >= ? ORDER BY start_time")
      .bind(paidChild.id, today, today)
      .all();
    todayActs = ta.filter((a) => String(a.days_of_week || "").split(",").map((x) => parseInt(x, 10)).includes(dow));
  }

  // 학사일정 달력의 "내 일정"(개인 이벤트) — 유료 자녀 소유. 학교 일정과 함께 달력에 표시.
  let personalEvents = [];
  if (paid) {
    const pe = await db.prepare("SELECT id, event_date, label, detail, remind_at FROM personal_events WHERE child_id = ? AND owner_token = ? ORDER BY event_date").bind(paidChild.id, ownerToken).all();
    personalEvents = pe.results;
  }

  // 유료: 등록 자녀의 학년·반 시간표를 실데이터로 조회. 무료는 조회 안 함(blur 샘플).
  // 시간표는 요일(weekday) 단위로 축약 저장되므로 현재 학기(school_year+semester) 것만 조회하면
  // 월~금 1벌이 그대로 나온다. 날짜 개념이 없어 시간이 지나도 항상 같은 주간표가 표시된다.
  let timetable = [];
  let personalSchedule = [];
  let scheduleSettings = null;
  if (paid) {
    // 시간표도 온디맨드지만 블로킹 안 함 — 비었으면 템플릿이 워밍 후 새로고침(아래 warm 스크립트).
    // 아래 4개도 서로 독립적(전부 school/paidChild만 필요)이라 병렬 실행.
    const [ttRes, ovRes, psRes, ssRow] = await Promise.all([
      db
        .prepare(
          `SELECT * FROM timetables WHERE school_id = ?
           AND school_year = ? AND semester = ?
           AND grade = ? AND COALESCE(class_name,'') = COALESCE(?, '')
           ORDER BY weekday, CAST(period AS INTEGER) LIMIT 80`
        )
        .bind(school.id, schoolYearOf(today), currentSemester(today), paidChild.grade, paidChild.class_name)
        .all(),
      // 반 단위 공개 오버라이드 — 같은 학교·학년·반의 수정 내용을 모든 유료 사용자에게 반영(요일 기준).
      db
        .prepare(
          `SELECT weekday, period, subject FROM timetable_overrides
           WHERE school_id = ?
           AND grade = ? AND COALESCE(class_name,'') = COALESCE(?, '')`
        )
        .bind(school.id, paidChild.grade, paidChild.class_name)
        .all(),
      // 개인 스케줄러(학원·방과후 등) — 이 자녀 소유자 본인만 보이는 비공개 일정.
      db
        .prepare("SELECT weekday, period, label FROM personal_schedule WHERE child_id = ? AND owner_token = ?")
        .bind(paidChild.id, ownerToken)
        .all(),
      // 교시/점심 시간 개인 설정(있으면 표준 대신 사용).
      db
        .prepare("SELECT settings_json FROM schedule_settings WHERE child_id = ? AND owner_token = ?")
        .bind(paidChild.id, ownerToken)
        .first(),
    ]);
    timetable = ttRes.results;
    personalSchedule = psRes.results;
    if (ssRow) { try { scheduleSettings = JSON.parse(ssRow.settings_json); } catch { scheduleSettings = null; } }

    // 오버라이드 병합(요일 기준).
    const ovMap = new Map(ovRes.results.map((o) => [`${o.weekday}|${o.period}`, o.subject]));
    for (const r of timetable) {
      const key = `${r.weekday}|${r.period}`;
      if (ovMap.has(key)) { r.subject = ovMap.get(key); r.edited = true; ovMap.delete(key); }
    }
    // 원본에 없던 칸(빈 교시)에 새로 채운 수정분은 합성 행으로 추가.
    for (const [key, subject] of ovMap) {
      const [weekday, period] = key.split("|");
      timetable.push({ weekday: Number(weekday), period, subject, grade: paidChild.grade, class_name: paidChild.class_name, edited: true });
    }
  }

  // 시간표가 비었을 때 원인 구분(미제공 vs 방학 vs 학기말) — 원인별 다른 문구 노출(§신규버그).
  let timetableEmptyReason = null;
  if (paid && timetable.length === 0) {
    const anyRow = await db
      .prepare(
        "SELECT COUNT(*) AS n FROM timetables WHERE school_id = ? AND grade = ? AND COALESCE(class_name,'') = COALESCE(?, '')"
      )
      .bind(school.id, paidChild.grade, paidChild.class_name)
      .first();
    if (!anyRow || anyRow.n === 0) {
      timetableEmptyReason = "none"; // 이 학교/반의 시간표가 아예 없음(미제공)
    } else {
      const ymdShift = (days) => {
        const d = new Date(Date.now() + 9 * 3600 * 1000 + days * 86400000);
        return `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(d.getUTCDate()).padStart(2, "0")}`;
      };
      const vac = await db
        .prepare("SELECT COUNT(*) AS n FROM academic_schedules WHERE school_id = ? AND event_name LIKE '%방학%' AND event_date BETWEEN ? AND ?")
        .bind(school.id, ymdShift(-5), ymdShift(21))
        .first();
      timetableEmptyReason = vac && vac.n > 0 ? "vacation" : "break";
    }
  }

  return html(
    schoolDetailPage({
      school,
      details,
      tab,
      todayYmd: today,
      allMeals,
      schedules,
      yearSchedules,
      communityPosts,
      personalEvents,
      upcoming: schedules[0] || null,
      eventsRest: schedules.slice(1, 6),
      paid,
      child: paidChild,
      // 헤더 자녀 배지(스위처)는 로그인한 사용자에게만. 미로그인 브라우저에 owner_token 쿠키만 남아
      // 있어도 남의 자녀 별명이 보이던 문제(공용 PC) 수정 — 2026-07-19.
      // 잠금 판정(paid)만 계정을 보고 배지는 안 봤던 게 원인. 관리자 테스트 자녀(is_test)는 QA용이라 예외.
      siblings: account ? siblings : siblings.filter((c) => c.is_test),
      todayActs,
      timetable,
      personalSchedule,
      scheduleSettings,
      timetableEmptyReason,
      mealDay: Number(url.searchParams.get("d") || 0),
      mealType: url.searchParams.get("mt") || "",
      reported: url.searchParams.get("reported") === "1",
      subscriber: isSubscriber(request),
      vapidPublic: (env && env.VAPID_PUBLIC) || "", // 웹푸시 구독(알림 켜기) 클라이언트 키
      warmed, // 온디맨드 워밍 이미 시도했는지(무한 새로고침 방지)
      pwaGuide: env && env.FEATURE_PWA_GUIDE === "true", // "미리 만들되 숨김" — 플래그 켜면 노출.
    })
  );
}

async function handleKinderDetail(db, slug) {
  const kinder = await db
    .prepare("SELECT * FROM kindergartens WHERE slug = ?")
    .bind(slug)
    .first();
  if (!kinder) return html("유치원을 찾을 수 없습니다.", 404);
  return html(kinderDetailPage(kinder));
}

function getCookie(request, name) {
  const header = request.headers.get("Cookie") || "";
  const match = header.match(new RegExp(`(?:^|; )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}

// 결제 미구현 상태에서 유료 가입자 화면을 테스트하기 위한 스위치(브라우저 쿠키).
// 관리자가 /admin/members 에서 켜고 끔. 켜지면 "+"가 검색으로, 자녀 최대 3명 등록 허용.
function isSubscriber(request) {
  return getCookie(request, "subscriber") === "1";
}

function newToken() {
  return crypto.randomUUID();
}

// 자녀 무료 등록(공개, 결제 없음) — 등록 즉시 1주일 체험으로 전체 잠금 해제.
// 학년별 실제 학급수 맵({"1":4,"2":3,...}) — 반 드롭다운을 그 학년 실제 학급수로 제한(§지시서3).
// 1순위: 학교알리미 grade_breakdown(정확하지만 전국 7개교만 보유) → 2순위: NEIS classInfo(전 학교 대응).
// 둘 다 실패하면 빈 맵 → 화면에서 15반 폴백(없는 정보를 지어내지 않고 넓게 두는 쪽).
async function loadGradeClassMap(db, school) {
  const map = {};
  if (!school) return map;
  const d = await db.prepare("SELECT grade_breakdown FROM school_details WHERE school_id = ?").bind(school.id).first();
  if (d && d.grade_breakdown) {
    try {
      for (const g of JSON.parse(d.grade_breakdown)) {
        if (g && g.grade != null && g.classes != null) map[String(g.grade)] = Number(g.classes);
      }
    } catch { /* 파싱 실패 → 아래 NEIS 폴백 */ }
  }
  if (!Object.keys(map).length && school.office_code && school.school_code) {
    const rows = await neisGet("classInfo", {
      ATPT_OFCDC_SC_CODE: school.office_code,
      SD_SCHUL_CODE: school.school_code,
      AY: schoolYearOf(todayYmd()), // 1~2월엔 전년도 학년도의 학급 편성이 유효
    });
    const byGrade = {};
    for (const r of rows) {
      const g = String(r.GRADE || "").trim();
      const cn = String(r.CLASS_NM || "").trim();
      if (!g || !cn) continue;
      (byGrade[g] = byGrade[g] || new Set()).add(cn);
    }
    for (const g in byGrade) map[g] = byGrade[g].size;
  }
  return map;
}

async function handleRegisterChild(request, db, url, env) {
  if (request.method === "GET") {
    const slug = url.searchParams.get("school");
    const school = slug
      ? await db.prepare("SELECT id, slug, name, school_kind, office_code, school_code, sem2_start FROM schools WHERE slug = ?").bind(decodeURIComponent(slug)).first()
      : null;
    const gradeClassMap = await loadGradeClassMap(db, school);
    // 개방 중이면 "1주일 체험" 문구가 사실과 달라 조건 분기한다(회신4 Q3).
    return html(registerChildPage(school, gradeClassMap, isSubscriber(request), isFreeOpenForSchool(school), schoolOpenUntil(school), featureRecords(env)));
  }
  // POST
  const form = await request.formData();
  const slug = (form.get("school_slug") || "").toString().trim();
  const grade = (form.get("grade") || "").toString().trim();
  const className = (form.get("class_name") || "").toString().trim();
  const nickname = (form.get("nickname") || "").toString().trim();
  // 실명은 identifiers 전용. 별명과 분리해서 받는다(회신4 Q1=A / B-9).
  const childName = (form.get("name") || "").toString().trim();
  // 보호자 동의는 필수 — 프론트 required만 믿으면 직접 POST로 우회된다.
  const consented = form.get("consent") === "1";
  if (!slug || !grade || !nickname) return html("학교·학년·별명은 필수입니다. 홈에서 학교를 먼저 선택해 주세요.", 400);
  // 이름·보호자 동의는 블록1(자녀기록) 추가분이다. 플래그가 꺼져 있으면 화면에 그 칸이 없으므로
  // 서버도 요구하지 않는다 — 요구하면 기존 등록 흐름이 통째로 막힌다.
  const recOn = featureRecords(env);
  if (recOn) {
    if (!childName) return html("자녀 이름을 입력해 주세요.", 400);
    if (!consented) {
      return html(noticePage("보호자 동의가 필요해요", "자녀 기록을 등록·보관하려면 <b>보호자 동의</b>에 체크해 주세요.", "/register-child?school=" + encodeURIComponent(slug), "✋"));
    }
  }

  const school = await db.prepare("SELECT id, slug, name FROM schools WHERE slug = ?").bind(slug).first();
  if (!school) return html("학교를 찾을 수 없습니다.", 404);

  const existingToken = getCookie(request, "owner_token");
  const backToSchool = `/school/${encodeURIComponent(school.slug)}/`;

  // 중복 차단 — 같은 학교·같은 학년·같은 반은 한 번만(쌍둥이는 한 명으로 등록). 다른 학년·반은 허용.
  if (existingToken) {
    const dup = await db
      .prepare("SELECT id FROM children WHERE owner_token = ? AND school_id = ? AND grade = ? AND COALESCE(class_name,'') = COALESCE(?, '')")
      .bind(existingToken, school.id, grade, className || null)
      .first();
    if (dup) {
      return html(noticePage(
        "이미 등록된 반이에요",
        "같은 학교·학년·반 자녀가 <b>이미 등록</b>되어 있어요. 쌍둥이는 한 명만 등록하면 됩니다.<br>다른 학년·반은 등록할 수 있어요.",
        backToSchool,
        "👀",
      ));
    }
  }

  // 무료회원(비구독자) 제한 — 다음 둘 중 하나면 차단. 확인 페이지(confirmed=1) 이전에 걸리므로
  // 프론트 안내가 아니라 서버에서 실제로 막힌다(직접 POST해도 동일).
  //  (a) 이미 자녀가 1명 이상 → 확정 사양 "무료회원은 자녀 1명만". free_trials 이력이 없는
  //      과거 데이터(로직 도입 전 등록분)도 이 조건으로 정확히 걸린다.
  //  (b) free_trials 이력 있음 → 자녀를 지우고 재체험하는 허점 차단(계정당 1회).
  // 유료 가입자(subscriber 쿠키)는 이 제한을 건너뛰고 최대 3명(MAX_CHILDREN)까지 등록 가능.
  // 무료 개방 중(등록 대상 학교가 아직 개학 전)이면 무료 1명 제한을 적용하지 않는다. 하드 상한(3명)은 아래에서 여전히 적용.
  if (existingToken && !isSubscriber(request) && !isFreeOpenForSchool(school)) {
    const [used, kidCnt] = await Promise.all([
      db.prepare("SELECT 1 FROM free_trials WHERE owner_token = ?").bind(existingToken).first(),
      db.prepare("SELECT COUNT(*) AS n FROM children WHERE owner_token = ?").bind(existingToken).first(),
    ]);
    if (used || (kidCnt && kidCnt.n >= FREE_MAX_CHILDREN)) {
      return html(noticePage(
        "무료회원은 자녀 1명만 등록 가능합니다",
        "무료로는 <b>자녀 1명</b>까지 이용할 수 있어요. 자녀를 더 추가하려면 <b>구독(유료)</b>이 필요합니다.<br><span style=\"display:inline-block;margin-top:8px;font-size:12.5px;color:#6B7688\">· 자녀 2명 <b>+500원/월</b> · 자녀 3명 <b>+1,000원/월</b></span>",
        `/school/${encodeURIComponent(school.slug)}/`,
        "🎁",
        { href: "/subscribe", label: "구독하고 자녀 추가하기" },
      ));
    }
  }

  // 이중 확인: 1차 제출은 요약 확인 페이지로. confirmed=1 재확인 후에만 실제 등록.
  // (학교·학년·반이 정확해야 유료 시간표 공유가 올바르게 매칭됨 — §시간표수정 전제조건)
  if (form.get("confirmed") !== "1") {
    // 이번에 등록하는 자녀가 "몇 번째"인지(자녀1/2/3) — 기존 자녀 수 + 1. 확인 문구에 사용.
    let ordinal = 1;
    if (existingToken) {
      const cnt = await db.prepare("SELECT COUNT(*) AS n FROM children WHERE owner_token = ?").bind(existingToken).first();
      ordinal = ((cnt && cnt.n) || 0) + 1;
    }
    return html(registerConfirmPage(school, { grade, className, nickname, ordinal, name: childName, consent: consented }));
  }

  let ownerToken = getCookie(request, "owner_token");
  const setCookie = [];
  if (!ownerToken) {
    ownerToken = newToken();
    setCookie.push(`owner_token=${ownerToken}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax`);
  }
  // 최대 3명 제한 — 앱 디자인 안내 페이지 + 돌아가기 링크(§지시서7).
  const cnt = await db.prepare("SELECT COUNT(*) AS n FROM children WHERE owner_token = ?").bind(ownerToken).first();
  if (cnt && cnt.n >= MAX_CHILDREN) {
    return html(noticePage(
      "자녀는 최대 3명까지예요",
      `한 계정에 자녀는 <b>최대 ${MAX_CHILDREN}명</b>까지 등록할 수 있어요. 자녀 관리에서 기존 자녀를 정리한 뒤 다시 등록해 주세요.`,
      "/mypage/children",
      "👨‍👩‍👧",
    ));
  }
  const trialExpires = new Date(Date.now() + TRIAL_DAYS * 86400000).toISOString();
  const nowIso = new Date().toISOString();
  // consent_at / consent_method: 만14세 미만 동의 기록(v4 1-5).
  // consent_method는 지금 'checkbox' 고정 — 확인 수단이 정해지면 그 값으로 바뀌고, 소급 구분이 가능해진다.
  const ins = await db
    .prepare(
      "INSERT INTO children (owner_token, school_id, grade, class_name, nickname, is_test, trial_expires_at, created_at, consent_at, consent_method) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)"
    )
    .bind(ownerToken, school.id, grade, className || null, nickname, trialExpires, nowIso,
          recOn ? nowIso : null, recOn ? "checkbox" : null)
    .run();
  // 실명은 identifiers에만 — children·records·로그 어디에도 저장하지 않는다(로드맵 절대규칙 ①).
  // 전용 접근 계층을 통해서만 읽고 쓴다. 여기가 유일한 쓰기 지점.
  const newChildId = ins && ins.meta && ins.meta.last_row_id;
  if (newChildId && recOn && childName) {
    await db
      .prepare("INSERT OR REPLACE INTO identifiers (child_id, name, created_at) VALUES (?, ?, ?)")
      .bind(newChildId, childName, nowIso)
      .run();
  }
  // 무료체험 사용 이력 1회 기록(계정당 1회 제한의 기준). 이미 있으면 무시 — 자녀 삭제해도 유지된다.
  await db
    .prepare("INSERT OR IGNORE INTO free_trials (owner_token, first_used_at) VALUES (?, ?)")
    .bind(ownerToken, nowIso)
    .run();

  // 등록 완료 → 온보딩(알림·PWA 안내) 흐름으로.
  const resp = redirect(`/onboarding?school=${encodeURIComponent(school.slug)}`);
  for (const c of setCookie) resp.headers.append("Set-Cookie", c);
  return resp;
}

// 시간표 수정 저장(반 단위 공개 오버라이드). 해당 학교·학년·반의 유료 자녀를 가진 owner_token만 허용.
async function handleTimetableEdit(request, db) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false, error: "unauthorized" }, 403);

  const form = await request.formData();
  const slug = (form.get("school_slug") || "").toString().trim();
  const grade = (form.get("grade") || "").toString().trim();
  const className = (form.get("class_name") || "").toString().trim();
  const weekday = parseInt((form.get("weekday") || "").toString(), 10);
  const period = (form.get("period") || "").toString().trim();
  const subject = (form.get("subject") || "").toString().trim().slice(0, 20);
  if (!slug || !grade || !(weekday >= 1 && weekday <= 5) || !period || !subject) {
    return json({ ok: false, error: "invalid" }, 400);
  }

  const school = await db.prepare("SELECT id FROM schools WHERE slug = ?").bind(slug).first();
  if (!school) return json({ ok: false, error: "no_school" }, 404);

  // 권한: 그 학교·학년·반에 유효한(테스트 or 이용권 유효) 자녀가 있어야 수정 가능.
  // 그 학교가 아직 개학 전이면(무료 개방) 만료 조건을 건너뛴다 — 게이팅 일관.
  const nowIso = new Date().toISOString();
  const child = await db
    .prepare(
      `SELECT id FROM children WHERE owner_token = ? AND school_id = ? AND grade = ?
       AND COALESCE(class_name,'') = COALESCE(?, '')
       AND (is_test = 1 OR ? = 1 OR (trial_expires_at IS NOT NULL AND trial_expires_at > ?)) LIMIT 1`
    )
    .bind(ownerToken, school.id, grade, className || null, isFreeOpenForSchool(school) ? 1 : 0, nowIso)
    .first();
  if (!child) return json({ ok: false, error: "forbidden" }, 403);

  // upsert: UPDATE 먼저, 없으면 INSERT (표현식 유니크 인덱스라 ON CONFLICT 대신 수동 처리).
  const upd = await db
    .prepare(
      `UPDATE timetable_overrides SET subject = ?, edited_by = ?, updated_at = ?
       WHERE school_id = ? AND grade = ? AND COALESCE(class_name,'') = COALESCE(?, '')
       AND weekday = ? AND period = ?`
    )
    .bind(subject, ownerToken, nowIso, school.id, grade, className || null, weekday, period)
    .run();
  if (!upd.meta || upd.meta.changes === 0) {
    await db
      .prepare(
        `INSERT INTO timetable_overrides (school_id, grade, class_name, weekday, period, subject, edited_by, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .bind(school.id, grade, className || null, weekday, period, subject, ownerToken, nowIso)
      .run();
  }
  return json({ ok: true, subject });
}

// 개인 스케줄러 저장 — 하교 후 학원·방과후 등 개인 일정. 본인(owner_token) 자녀에게만 저장/노출.
async function handlePersonalSchedule(request, db) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false, error: "unauthorized" }, 403);

  const form = await request.formData();
  const childId = (form.get("child_id") || "").toString().trim();
  const weekday = parseInt((form.get("weekday") || "").toString(), 10);
  const period = parseInt((form.get("period") || "").toString(), 10);
  const label = (form.get("label") || "").toString().trim().slice(0, 20);
  if (!childId || !(weekday >= 1 && weekday <= 5) || !(period >= 1 && period <= 10)) {
    return json({ ok: false, error: "invalid" }, 400);
  }

  // 소유권: 이 자녀가 내 것(owner_token)인지 확인.
  const child = await db
    .prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?")
    .bind(childId, ownerToken)
    .first();
  if (!child) return json({ ok: false, error: "forbidden" }, 403);

  const nowIso = new Date().toISOString();
  if (!label) {
    // 빈 값이면 삭제.
    await db.prepare("DELETE FROM personal_schedule WHERE child_id = ? AND weekday = ? AND period = ?")
      .bind(childId, weekday, period).run();
    return json({ ok: true, label: "" });
  }
  const upd = await db
    .prepare("UPDATE personal_schedule SET label = ?, updated_at = ? WHERE child_id = ? AND weekday = ? AND period = ?")
    .bind(label, nowIso, childId, weekday, period)
    .run();
  if (!upd.meta || upd.meta.changes === 0) {
    await db
      .prepare("INSERT INTO personal_schedule (owner_token, child_id, weekday, period, label, updated_at) VALUES (?, ?, ?, ?, ?, ?)")
      .bind(ownerToken, childId, weekday, period, label, nowIso)
      .run();
  }
  return json({ ok: true, label });
}

// 교시/점심 시간 개인 설정 저장·초기화 — 본인 자녀에게만. action=reset이면 표준으로 되돌림(행 삭제).
async function handleScheduleSettings(request, db) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false, error: "unauthorized" }, 403);
  const form = await request.formData();
  const childId = (form.get("child_id") || "").toString().trim();
  const action = (form.get("action") || "").toString();
  if (!childId) return json({ ok: false, error: "invalid" }, 400);

  const child = await db.prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?").bind(childId, ownerToken).first();
  if (!child) return json({ ok: false, error: "forbidden" }, 403);

  const slug = (form.get("school_slug") || "").toString().trim();
  const back = slug ? `/school/${encodeURIComponent(slug)}/?tab=timetable` : "/";

  if (action === "reset") {
    // 시간 설정 초기화 + 바꾼 과목(학교 시간표 오버라이드)도 이 반 기준으로 원래대로 되돌림.
    await db.prepare("DELETE FROM schedule_settings WHERE child_id = ?").bind(childId).run();
    const c = await db.prepare("SELECT school_id, grade, class_name FROM children WHERE id = ?").bind(childId).first();
    if (c) {
      await db.prepare(
        "DELETE FROM timetable_overrides WHERE school_id = ? AND grade = ? AND COALESCE(class_name,'') = COALESCE(?, '')"
      ).bind(c.school_id, c.grade, c.class_name).run();
    }
    return redirect(back);
  }

  // 교시 시간 + 점심 파싱/검증. periods[p] = "HH:MM-HH:MM".
  const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;
  const periods = {};
  for (let p = 1; p <= 10; p++) {
    const s = (form.get(`p${p}s`) || "").toString().trim();
    const e = (form.get(`p${p}e`) || "").toString().trim();
    if (HHMM.test(s) && HHMM.test(e)) periods[p] = { s, e };
  }
  const lunchAfter = parseInt((form.get("lunch_after") || "").toString(), 10);
  const ls = (form.get("lunch_s") || "").toString().trim();
  const le = (form.get("lunch_e") || "").toString().trim();
  const lunch = (lunchAfter >= 1 && lunchAfter <= 10 && HHMM.test(ls) && HHMM.test(le)) ? { after: lunchAfter, s: ls, e: le } : null;
  if (Object.keys(periods).length === 0) return json({ ok: false, error: "invalid" }, 400);

  const settingsJson = JSON.stringify({ periods, lunch });
  const nowIso = new Date().toISOString();
  const upd = await db.prepare("UPDATE schedule_settings SET settings_json = ?, updated_at = ? WHERE child_id = ?")
    .bind(settingsJson, nowIso, childId).run();
  if (!upd.meta || upd.meta.changes === 0) {
    await db.prepare("INSERT INTO schedule_settings (child_id, owner_token, settings_json, updated_at) VALUES (?, ?, ?, ?)")
      .bind(childId, ownerToken, settingsJson, nowIso).run();
  }
  return redirect(back);
}

// 교시/점심 시간 인라인 부분수정 — 그리드에서 한 교시(또는 점심)만 바꿔 저장(merge). 본인 자녀만.
async function handleScheduleTime(request, db) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false, error: "unauthorized" }, 403);
  const form = await request.formData();
  const childId = (form.get("child_id") || "").toString().trim();
  const target = (form.get("target") || "").toString().trim(); // "1".."10" 또는 "lunch"
  const s = (form.get("s") || "").toString().trim();
  const e = (form.get("e") || "").toString().trim();
  const after = parseInt((form.get("after") || "").toString(), 10);
  const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;
  if (!childId || !target) return json({ ok: false, error: "invalid" }, 400);

  const child = await db.prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?").bind(childId, ownerToken).first();
  if (!child) return json({ ok: false, error: "forbidden" }, 403);

  const row = await db.prepare("SELECT settings_json FROM schedule_settings WHERE child_id = ? AND owner_token = ?").bind(childId, ownerToken).first();
  let obj = { periods: {}, lunch: null };
  if (row) { try { obj = JSON.parse(row.settings_json); } catch { /* keep default */ } }
  obj.periods = obj.periods || {};

  if (target === "lunch") {
    obj.lunch = obj.lunch || {};
    if (HHMM.test(s) && HHMM.test(e)) { obj.lunch.s = s; obj.lunch.e = e; }
    if (after >= 1 && after <= 10) obj.lunch.after = after;
    if (!obj.lunch.after) obj.lunch.after = 4;
  } else {
    const p = parseInt(target, 10);
    if (!(p >= 1 && p <= 10) || !HHMM.test(s) || !HHMM.test(e)) return json({ ok: false, error: "invalid" }, 400);
    obj.periods[String(p)] = { s, e };
  }

  const settingsJson = JSON.stringify(obj);
  const nowIso = new Date().toISOString();
  const upd = await db.prepare("UPDATE schedule_settings SET settings_json = ?, updated_at = ? WHERE child_id = ?").bind(settingsJson, nowIso, childId).run();
  if (!upd.meta || upd.meta.changes === 0) {
    await db.prepare("INSERT INTO schedule_settings (child_id, owner_token, settings_json, updated_at) VALUES (?, ?, ?, ?)").bind(childId, ownerToken, settingsJson, nowIso).run();
  }
  return json({ ok: true, s, e, after: obj.lunch ? obj.lunch.after : null });
}

// 학사일정 "내 일정" 추가 — 유료 자녀 소유. 날짜(YYYYMMDD)+내용. JSON 응답(달력 JS가 갱신).
async function handleCalendarEventAdd(request, db) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false, error: "unauthorized" }, 403);
  const form = await request.formData();
  const childId = (form.get("child_id") || "").toString().trim();
  const date = (form.get("date") || "").toString().replace(/-/g, "").trim(); // YYYY-MM-DD 또는 YYYYMMDD 허용
  const label = (form.get("label") || "").toString().trim().slice(0, 40);
  if (!childId || !/^\d{8}$/.test(date) || !label) return json({ ok: false, error: "invalid" }, 400);
  // 소유권 확인.
  const child = await db.prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?").bind(childId, ownerToken).first();
  if (!child) return json({ ok: false, error: "forbidden" }, 403);
  const res = await db.prepare("INSERT INTO personal_events (owner_token, child_id, event_date, label, created_at) VALUES (?, ?, ?, ?, ?)")
    .bind(ownerToken, childId, date, label, new Date().toISOString()).run();
  return json({ ok: true, id: res.meta && res.meta.last_row_id, date, label });
}
// 학사일정 "내 일정" 삭제 — 본인(owner_token) 것만.
async function handleCalendarEventDelete(request, db) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false, error: "unauthorized" }, 403);
  const form = await request.formData();
  const id = (form.get("id") || "").toString().trim();
  if (!id) return json({ ok: false, error: "invalid" }, 400);
  await db.prepare("DELETE FROM personal_events WHERE id = ? AND owner_token = ?").bind(id, ownerToken).run();
  return json({ ok: true });
}
// GET /api/push/latest — 방금(15분 내) 알림 시각이 된 내 일정의 제목·내용·이동 URL.
// 서비스워커가 푸시 수신 순간 호출해 "무슨 일정인지" 채워서 알림을 띄운다(무페이로드 푸시 보완).
// remind_sent 플래그 대신 시각 창(now-15분~now)으로 판정 — 크론의 발송/마킹과 순서 경합이 없다.
async function handlePushLatest(request, db) {
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false }, 403);
  const now = Date.now();
  const from = new Date(now - 15 * 60000).toISOString();
  const to = new Date(now).toISOString();
  const { results } = await db.prepare(
    `SELECT pe.label, pe.detail, pe.event_date, s.slug
     FROM personal_events pe
     JOIN children c ON c.id = pe.child_id
     JOIN schools s ON s.id = c.school_id
     WHERE pe.owner_token = ? AND pe.remind_at IS NOT NULL AND pe.remind_at BETWEEN ? AND ?
     ORDER BY pe.remind_at DESC LIMIT 5`
  ).bind(ownerToken, from, to).all();
  if (!results.length) return json({ ok: true, title: null }); // 해당 없음 → SW가 기본 문구 사용
  const ev = results[0];
  const d = ev.event_date || "";
  const dateStr = d.length === 8 ? `${Number(d.slice(4, 6))}월 ${Number(d.slice(6, 8))}일` : "";
  const more = results.length > 1 ? ` 외 ${results.length - 1}건` : "";
  return json({
    ok: true,
    title: `📌 ${ev.label}${more}`,
    body: ev.detail || (dateStr ? `${dateStr} 일정이에요` : "일정 알림이에요"),
    url: `/school/${encodeURIComponent(ev.slug)}/?tab=schedule`,
  });
}

// 학사일정 "내 일정" 수정 — 본인(owner_token) 것 label만 변경.
async function handleCalendarEventEdit(request, db) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false, error: "unauthorized" }, 403);
  const form = await request.formData();
  const id = (form.get("id") || "").toString().trim();
  const label = (form.get("label") || "").toString().trim().slice(0, 40);
  // detail(상세내용)은 선택 — 폼에 있으면 함께 갱신, 없으면 label만 갱신.
  const hasDetail = form.has("detail");
  const detail = (form.get("detail") || "").toString().trim().slice(0, 300);
  if (!id || !label) return json({ ok: false, error: "invalid" }, 400);
  // 알림: remind_off=1이면 해제(null). remind_date(YYYYMMDD)+remind_time(HH:MM)이면 KST로 해석 → UTC ISO로 저장.
  // 시각/내용이 바뀌면 remind_sent=0으로 리셋해 다시 발송되게 한다.
  const hasRemind = form.has("remind_off") || form.has("remind_date");
  let remindAt = null;
  if (form.has("remind_date") && !(form.get("remind_off") === "1")) {
    const rd = (form.get("remind_date") || "").toString().replace(/-/g, "").trim();
    const rt = (form.get("remind_time") || "").toString().trim();
    const mt = rt.match(/^(\d{1,2}):(\d{2})$/);
    if (/^\d{8}$/.test(rd) && mt) {
      // KST(UTC+9) 벽시계 → UTC. Date.UTC에 시(hh-9)를 넣으면 자정 넘김도 정상 롤오버.
      const y = +rd.slice(0, 4), mo = +rd.slice(4, 6), d = +rd.slice(6, 8);
      remindAt = new Date(Date.UTC(y, mo - 1, d, +mt[1] - 9, +mt[2])).toISOString();
    }
  }
  let res;
  if (hasRemind) {
    res = hasDetail
      ? await db.prepare("UPDATE personal_events SET label = ?, detail = ?, remind_at = ?, remind_sent = 0 WHERE id = ? AND owner_token = ?").bind(label, detail || null, remindAt, id, ownerToken).run()
      : await db.prepare("UPDATE personal_events SET label = ?, remind_at = ?, remind_sent = 0 WHERE id = ? AND owner_token = ?").bind(label, remindAt, id, ownerToken).run();
  } else {
    res = hasDetail
      ? await db.prepare("UPDATE personal_events SET label = ?, detail = ? WHERE id = ? AND owner_token = ?").bind(label, detail || null, id, ownerToken).run()
      : await db.prepare("UPDATE personal_events SET label = ? WHERE id = ? AND owner_token = ?").bind(label, id, ownerToken).run();
  }
  if (!res.meta || !res.meta.changes) return json({ ok: false, error: "forbidden" }, 403);
  return json({ ok: true, id, label, detail: hasDetail ? detail : undefined, remind_at: hasRemind ? remindAt : undefined });
}

// 정보 오류 신고 저장 — 상세정보가 실제와 다를 때 사용자 제보. 개인정보 미수집.
async function handleReport(request, db, url) {
  if (request.method !== "POST") return html("잘못된 요청입니다.", 405);
  const form = await request.formData();
  const slug = (form.get("school_slug") || "").toString().trim();
  const category = (form.get("category") || "").toString().trim().slice(0, 20);
  const message = (form.get("message") || "").toString().trim().slice(0, 500);
  if (!slug || !message) return html("신고 내용을 입력해 주세요.", 400);

  const school = await db.prepare("SELECT id, slug FROM schools WHERE slug = ?").bind(slug).first();
  if (!school) return html("학교를 찾을 수 없습니다.", 404);

  const ownerToken = getCookie(request, "owner_token"); // 등록 사용자면 참고용으로만 기록(선택).
  await db
    .prepare(
      "INSERT INTO info_reports (school_id, category, message, owner_token, created_at) VALUES (?, ?, ?, ?, ?)"
    )
    .bind(school.id, category || null, message, ownerToken || null, new Date().toISOString())
    .run();

  // 접수 완료 → 학교정보 탭으로 복귀(감사 플래그). "학년별 현황"이 개요와 통합되며 학교정보(overview) 탭 소속이 됨.
  return redirect(`/school/${encodeURIComponent(school.slug)}/?tab=overview&reported=1`);
}

// 베타 의견 접수 — 특정 학교와 무관한 서비스 전반 의견. GET은 폼, POST는 저장 후 감사 화면.
async function handleFeedback(request, db) {
  if (request.method !== "POST") return html(feedbackPage(false));
  const form = await request.formData();
  const category = (form.get("category") || "").toString().trim().slice(0, 20);
  const message = (form.get("message") || "").toString().trim().slice(0, 1000);
  if (!message) return html(feedbackPage(false));
  const ownerToken = getCookie(request, "owner_token"); // 등록 사용자면 참고용으로만 기록(선택).
  await db
    .prepare("INSERT INTO beta_feedback (category, message, owner_token, created_at) VALUES (?, ?, ?, ?)")
    .bind(category || null, message, ownerToken || null, new Date().toISOString())
    .run();
  return html(feedbackPage(true));
}

// 욕설 키워드 자동 마스킹(§커뮤니티 지시서) — 매칭된 글자를 전부 *로 치환. 완전한 필터링은 아니고 노출 노력.
const PROFANITY_WORDS = ["시발", "씨발", "개새끼", "병신", "지랄", "좆", "존나", "쓰레기", "죽어", "미친놈", "미친년"];
function maskProfanity(text) {
  let out = text;
  for (const w of PROFANITY_WORDS) {
    if (!w) continue;
    out = out.split(w).join("*".repeat(w.length));
  }
  return out;
}

// 이 학교의 "유료(작성 권한) 자녀" 1명 조회 — 커뮤니티 작성/닉네임 설정 공통.
// 무료 개방 기간에는 만료 조건을 건너뛴다(게이팅 일관 — FREE_OPEN_UNTIL).
// 무료 개방 판정은 그 학교의 개학일 기준 — SQL 안에서 schools를 조인해 오늘과 비교한다.
// (호출부가 school 객체를 안 가진 경로가 있어 쿼리에서 직접 본다. 폴백은 SEM2_FALLBACK과 같은 값.)
async function communityAuthorChild(db, ownerToken, schoolId, nowIso) {
  return db
    .prepare(
      `SELECT c.id, c.grade, c.class_name, c.community_nickname, c.community_nickname_changed_at
       FROM children c JOIN schools s ON s.id = c.school_id
       WHERE c.owner_token = ? AND c.school_id = ?
       AND (c.is_test = 1
            OR ? < COALESCE(s.sem2_start, ?)
            OR (c.trial_expires_at IS NOT NULL AND c.trial_expires_at > ?))
       ORDER BY c.created_at LIMIT 1`
    )
    .bind(ownerToken, schoolId, ymd(), SEM2_FALLBACK, nowIso)
    .first();
}

// 커뮤니티 고정 닉네임 설정/변경(§지시서D10) — 최초 설정 후 30일간 잠금, 그 뒤 재변경 가능. 비우면 익명.
const NICK_LOCK_DAYS = 30;
async function handleCommunityNickname(request, db) {
  if (request.method !== "POST") return html("잘못된 요청입니다.", 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return html("자녀 등록 후 이용할 수 있어요.", 403);
  const form = await request.formData();
  const slug = (form.get("school_slug") || "").toString().trim();
  const nickname = (form.get("nickname") || "").toString().trim().slice(0, 12);
  const school = await db.prepare("SELECT id, slug FROM schools WHERE slug = ?").bind(slug).first();
  if (!school) return html("학교를 찾을 수 없습니다.", 404);

  const nowIso = new Date().toISOString();
  const child = await communityAuthorChild(db, ownerToken, school.id, nowIso);
  if (!child) return html("유료(자녀 등록) 사용자만 이용할 수 있어요.", 403);

  const back = `/school/${encodeURIComponent(school.slug)}/?tab=community`;
  // 30일 잠금 확인 — 마지막 변경 +30일 이전이면 변경 거부.
  if (child.community_nickname_changed_at) {
    const elapsed = Date.now() - new Date(child.community_nickname_changed_at).getTime();
    if (elapsed < NICK_LOCK_DAYS * 86400000) {
      const daysLeft = Math.ceil((NICK_LOCK_DAYS * 86400000 - elapsed) / 86400000);
      return html(noticePage(
        "닉네임은 30일마다 변경할 수 있어요",
        `커뮤니티 닉네임은 설정 후 <b>30일간 변경할 수 없어요</b>. <b>${daysLeft}일</b> 뒤에 다시 바꿀 수 있습니다.`,
        back, "🔒",
      ));
    }
  }
  const masked = nickname ? maskProfanity(nickname) : null; // 비우면 NULL(익명)
  await db
    .prepare("UPDATE children SET community_nickname = ?, community_nickname_changed_at = ? WHERE id = ?")
    .bind(masked, nowIso, child.id)
    .run();
  return redirect(back);
}

// 커뮤니티 글 작성 — 유료(등록) 사용자만, 1~3줄(90자 제한), 이미지/링크 없이 텍스트만.
// 고정 닉네임·작성 당시 학년/반 박제·도배 방지(연속 2개, 5분/타인글로 해제) 적용(§지시서D).
async function handleCommunityPost(request, db) {
  if (request.method !== "POST") return html("잘못된 요청입니다.", 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return html("자녀 등록 후 이용할 수 있어요.", 403);

  const form = await request.formData();
  const slug = (form.get("school_slug") || "").toString().trim();
  const body = (form.get("body") || "").toString().trim().slice(0, 90);
  if (!slug || !body) return html("내용을 입력해 주세요.", 400);

  const school = await db.prepare("SELECT id, slug FROM schools WHERE slug = ?").bind(slug).first();
  if (!school) return html("학교를 찾을 수 없습니다.", 404);

  const nowIso = new Date().toISOString();
  const child = await communityAuthorChild(db, ownerToken, school.id, nowIso);
  if (!child) return html("유료(자녀 등록) 사용자만 글을 쓸 수 있어요.", 403);

  const back = `/school/${encodeURIComponent(school.slug)}/?tab=community`;
  // 도배 방지(§지시서D12): 이 학교 최근 2개 글이 모두 나(owner_token)이고 마지막 글이 5분 이내면 3번째 차단.
  // 사이에 타인 글이 있으면 연속이 끊겨 recent 2개가 모두 나가 아니게 되므로 자동 허용(즉시 리셋).
  const recent = await db
    .prepare("SELECT owner_token, created_at FROM community_posts WHERE school_id = ? AND hidden = 0 ORDER BY created_at DESC LIMIT 2")
    .bind(school.id)
    .all();
  const r = recent.results || [];
  if (r.length >= 2 && r[0].owner_token === ownerToken && r[1].owner_token === ownerToken) {
    const sinceLast = Date.now() - new Date(r[0].created_at).getTime();
    if (sinceLast < 5 * 60 * 1000) {
      return html(noticePage(
        "잠시 후 다시 작성해 주세요",
        "연속으로 <b>2개까지</b> 작성할 수 있어요. 다음 글은 <b>5분 뒤</b> 또는 다른 분이 글을 남긴 뒤에 쓸 수 있습니다.",
        back, "✋",
      ));
    }
  }

  const masked = maskProfanity(body);
  // 닉네임·학년·반 스냅샷(박제) — 이후 프로필이 바뀌어도 이 글은 작성 당시 값 유지.
  const nickSnap = (child.community_nickname || "").trim() || null;
  await db
    .prepare("INSERT INTO community_posts (school_id, child_id, owner_token, display_name, author_grade, author_class, body, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    .bind(school.id, child.id, ownerToken, nickSnap, child.grade || null, child.class_name || null, masked, nowIso)
    .run();

  return redirect(back);
}

// 커뮤니티 글 신고 — 같은 사용자 중복 신고 방지, 3회 누적 시 자동 숨김.
async function handleCommunityReport(request, db) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return json({ ok: false, error: "unauthorized" }, 403);

  const form = await request.formData();
  const postId = (form.get("post_id") || "").toString().trim();
  if (!postId) return json({ ok: false, error: "invalid" }, 400);

  const post = await db.prepare("SELECT id, school_id FROM community_posts WHERE id = ?").bind(postId).first();
  if (!post) return json({ ok: false, error: "not_found" }, 404);

  try {
    await db
      .prepare("INSERT INTO community_reports (post_id, owner_token, created_at) VALUES (?, ?, ?)")
      .bind(postId, ownerToken, new Date().toISOString())
      .run();
  } catch {
    return json({ ok: true, already: true }); // UNIQUE(post_id, owner_token) 위반 = 이미 신고함
  }

  await db.prepare("UPDATE community_posts SET report_count = report_count + 1 WHERE id = ?").bind(postId).run();
  const row = await db.prepare("SELECT report_count FROM community_posts WHERE id = ?").bind(postId).first();
  if (row && row.report_count >= 3) {
    await db.prepare("UPDATE community_posts SET hidden = 1 WHERE id = ?").bind(postId).run();
  }
  return json({ ok: true, hidden: row && row.report_count >= 3 });
}

// 자녀 정보 수정 — 별명은 자유 수정, 학교·학년·반은 잠금(읽기전용).
// 학년/반은 "새 학년도 전환"에서만 명시적으로 변경 허용(경고 후). owner_token 소유권 필수.
async function handleChildEdit(request, db, url) {
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return html("접근 권한이 없습니다.", 403);

  const id = (request.method === "POST"
    ? (await request.clone().formData()).get("id")
    : url.searchParams.get("id")) || "";

  const child = await db
    .prepare(
      `SELECT children.*, schools.name AS school_name, schools.slug AS school_slug, schools.school_kind AS school_kind,
              schools.office_code AS office_code, schools.school_code AS school_code
       FROM children JOIN schools ON schools.id = children.school_id
       WHERE children.id = ? AND children.owner_token = ?`
    )
    .bind(id, ownerToken)
    .first();
  // 소유하지 않은 자녀는 존재 자체를 숨김(권한 없음).
  if (!child) return html("자녀 정보를 찾을 수 없거나 수정 권한이 없습니다.", 404);

  if (request.method === "POST") {
    const form = await request.formData();
    const action = (form.get("action") || "").toString();
    const nickname = (form.get("nickname") || "").toString().trim();
    if (!nickname) return html("별명은 비워둘 수 없습니다.", 400);

    if (action === "promote") {
      // 새 학년도 전환: 바로 다음 학년으로만, 1회만 허용.
      if (child.grade_promoted) {
        return html(noticePage("이미 학년을 변경했어요", "새 학년도 전환은 자녀당 <b>1회</b>만 가능합니다.", `/child/edit?id=${child.id}`, "✅"));
      }
      const maxGrade = child.school_kind === "초등학교" ? 6 : 3;
      const nextGrade = Number(child.grade) + 1;
      const grade = (form.get("grade") || "").toString().trim();
      const className = (form.get("class_name") || "").toString().trim();
      // 서버측 검증: 반드시 "현재+1" 학년, 상한 이내.
      if (Number(grade) !== nextGrade || nextGrade > maxGrade) {
        return html(noticePage("변경할 수 없어요", "학년은 <b>바로 다음 학년</b>으로만 변경할 수 있어요.", `/child/edit?id=${child.id}`, "⚠️"));
      }
      // 진급하면 반 편성이 새로 되므로 반 선택은 필수 — 빠지면 작년 반이 그대로 남아 시간표·급식이 어긋난다.
      if (!className) {
        return html(noticePage("반을 선택해 주세요", "진급하면 반이 새로 편성돼요. <b>새 학년의 반</b>을 선택한 뒤 다시 눌러주세요.", `/child/edit?id=${child.id}`, "🔢"));
      }
      await db
        .prepare("UPDATE children SET nickname = ?, grade = ?, class_name = ?, grade_promoted = 1 WHERE id = ? AND owner_token = ?")
        .bind(nickname, String(nextGrade), className || null, child.id, ownerToken)
        .run();
    } else {
      // 기본: 별명만 수정(학교·학년·반 잠금).
      await db
        .prepare("UPDATE children SET nickname = ? WHERE id = ? AND owner_token = ?")
        .bind(nickname, child.id, ownerToken)
        .run();
    }
    return redirect(`/school/${encodeURIComponent(child.school_slug)}/`);
  }

  // 진급 폼의 반 선택도 그 학교 학년별 실제 학급수로 제한(등록 폼과 동일 소스).
  const gradeClassMap = await loadGradeClassMap(db, { id: child.school_id, office_code: child.office_code, school_code: child.school_code });
  return html(childEditPage(child, gradeClassMap));
}

// 자녀 삭제 — 본인(owner_token) 자녀만. 개인 일정·시간설정도 함께 정리.
// ================= 자녀 삭제 연쇄 (단일 진입점) =================
// 지시서 v4 1-13(B-11): 자녀 삭제 = identifiers·records·activity_schedules + R2 원본
//                       + 기존 personal_schedule·personal_events·schedule_settings 전부 파기.
//
// **삭제 경로는 이 함수 하나만 쓴다** — 사용자 단건 삭제 / 전체 삭제 / admin 삭제 모두.
// 흩어놓으면 테이블을 추가할 때마다 한 곳을 빠뜨려 고아 데이터가 남는다(실제로 personal_events가
// 사용자 삭제 경로에서 빠져 있었고, admin 삭제는 children만 지우고 있었다 — 2026-07-19 수정).
//
// (deleteChildCascade·r2KeysOf는 data_children.js로 승격 — 삭제 경로 단일 진입점 복원 2026-07-24)

async function handleChildDelete(request, db, env) {
  if (request.method !== "POST") return html("잘못된 요청입니다.", 405);
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return html("접근 권한이 없습니다.", 403);
  const form = await request.formData();
  const id = (form.get("id") || "").toString().trim();
  // 소유 검증 — 남의 자녀를 지울 수 없게 owner_token 일치 확인 후 연쇄 삭제.
  const child = await db.prepare("SELECT id FROM children WHERE id = ? AND owner_token = ?").bind(id, ownerToken).first();
  if (!child) return html("자녀 정보를 찾을 수 없거나 권한이 없습니다.", 404);
  const r = await deleteChildCascade(db, env, child.id);
  if (!r.ok) return html("사진 삭제 중 문제가 생겨 중단했습니다. 잠시 후 다시 시도해 주세요.", 500);
  return redirect("/mypage/children");
}

// 결제 페이지 — 자녀 수 기본값을 소유 자녀 수로.
async function handleSubscribe(request, db) {
  const ownerToken = getCookie(request, "owner_token");
  let cc = 1;
  if (ownerToken) {
    const r = await db.prepare("SELECT COUNT(*) AS n FROM children WHERE owner_token = ? AND is_test = 0").bind(ownerToken).first();
    cc = Math.min(3, Math.max(1, (r && r.n) || 1));
  }
  return html(subscribePage(cc));
}

// 기간권 가격표(원) — 2026-07-19 단일가화.
// 이전에는 자녀 수별로 값이 달랐으나(자녀2 +500원·자녀3 +1,000원) 인원별 추가 과금을 폐지하고
// **이용권 하나로 자녀 3명까지** 포함으로 바꿨다. 기간(개월)만 남는다.
// 기간권(단건 결제)이라 가격을 바꿔도 다음 구매분부터 적용된다 — 기존 payments 이력은 소급 수정하지 않는다.
const PAY_PRICES = { 1: 3500, 3: 9500, 6: 16800, 12: 29400 };
function priceFor(months) {
  return PAY_PRICES[months] || 0;
}

// 더미 결제 — DB 기록 + 자녀 이용기간을 "기존 만료일부터 이어서" 연장. PG 승인 후 실제 API로 교체.
// 정식 결제(PG) 연동 전까지 결제 자체를 막는 스위치. 베타 기간엔 더미 결제가 실행되면 안 되므로
// 프론트 버튼 비활성화와 별개로 서버에서도 차단한다(직접 POST 우회 방지). PG 붙일 때 false로.
const PAYMENTS_DISABLED = true;

async function handlePay(request, db) {
  if (request.method !== "POST") return html("잘못된 요청입니다.", 405);
  if (PAYMENTS_DISABLED) {
    return html(noticePage("베타 기간에는 결제가 필요 없어요", "지금은 베타 서비스라 <b>결제 없이 모든 기능이 무료</b>로 열려 있어요. 정식 결제는 정식 오픈 때 제공됩니다.", "/mypage", "🎉"));
  }
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) {
    return html(noticePage("먼저 자녀를 등록해 주세요", "이용권은 등록된 자녀에게 적용돼요. 홈에서 학교를 검색해 자녀를 먼저 등록해 주세요.", "/", "👶"));
  }
  const form = await request.formData();
  const childCount = Math.min(3, Math.max(1, parseInt((form.get("child_count") || "").toString(), 10) || 1));
  const monthsRaw = parseInt((form.get("months") || "").toString(), 10);
  const months = [1, 3, 6, 12].includes(monthsRaw) ? monthsRaw : 1;
  const method = ["card", "phone", "vbank"].includes((form.get("method") || "").toString()) ? form.get("method").toString() : "card";
  const autoRenew = form.get("auto_renew") === "1" ? 1 : 0;
  // 금액은 기간만으로 결정된다(2026-07-19 단일가화). childCount는 이력 통계용으로만 기록.
  const amount = priceFor(months);

  // 연장 기준: 소유 자녀들의 현재 최대 만료일(없거나 지났으면 지금)부터 이어붙임.
  const kids = (await db.prepare("SELECT trial_expires_at FROM children WHERE owner_token = ? AND is_test = 0").bind(ownerToken).all()).results;
  let baseMs = Date.now();
  for (const k of kids) { if (k.trial_expires_at) { const t = new Date(k.trial_expires_at).getTime(); if (t > baseMs) baseMs = t; } }
  const d = new Date(baseMs); d.setUTCMonth(d.getUTCMonth() + months);
  const newExpiry = d.toISOString();

  await db.prepare("UPDATE children SET trial_expires_at = ? WHERE owner_token = ? AND is_test = 0").bind(newExpiry, ownerToken).run();
  await db.prepare(
    "INSERT INTO payments (owner_token, child_count, months, amount, method, auto_renew, status, new_expiry, created_at) VALUES (?, ?, ?, ?, ?, ?, 'paid', ?, ?)"
  ).bind(ownerToken, childCount, months, amount, method, autoRenew, newExpiry, new Date().toISOString()).run();

  return html(payCompletePage({ amount, months, childCount, method, autoRenew, newExpiry }));
}

// 마이페이지 허브 — 등록 자녀 요약(오늘 급식·다가오는 중요일정)·이용기간·만료 배너 + 하위 메뉴 + 계정(소셜 로그인) 상태.
async function handleMypage(request, db, env) {
  const ownerToken = getCookie(request, "owner_token");
  const today = todayYmd();
  // 이 기기의 owner_token에 연결된 계정(있으면 "로그인됨" 표시, 없으면 연결 유도). accounts 기준.
  const account = ownerToken ? await accountForToken(db, ownerToken) : null;
  let children = [];
  if (ownerToken) {
    const { results } = await db
      .prepare(
        `SELECT children.*, schools.name AS school_name, schools.slug AS school_slug, schools.sem2_start AS sem2_start
         FROM children JOIN schools ON schools.id = children.school_id
         WHERE owner_token = ? ORDER BY children.created_at`
      )
      .bind(ownerToken)
      .all();
    children = results;
    for (const c of children) {
      // 무료 개방 문구를 자녀 카드에 개인화해 띄우기 위한 값(회신 Q4 3번째 위치).
      c._freeOpen = isFreeOpenForSchool(c);
      c._openUntil = schoolOpenUntil(c);
      c._meal = await db
        .prepare("SELECT * FROM meals WHERE school_id = ? AND meal_date = ? AND meal_type_name = '중식' LIMIT 1")
        .bind(c.school_id, today)
        .first();
      const ev = await db
        .prepare("SELECT * FROM academic_schedules WHERE school_id = ? AND event_date >= ? ORDER BY event_date LIMIT 40")
        .bind(c.school_id, today)
        .all();
      c._events = ev.results;
    }
  }
  // PG 미연동 동안 결제 관련 진입점을 숨긴다(v4 1-1) — 서버 상수와 화면이 어긋나지 않게 값으로 넘긴다.
  return html(mypagePage(children, today, account, providersFrom(env), !PAYMENTS_DISABLED, featureRecords(env)));
}

// ================= 자녀·데이터 전체 삭제 (v4 6절 · 1-13) =================
// GET  /mypage/purge — 지워질 것을 수량으로 보여주는 이중 확인 화면
// POST /mypage/purge — 확인 문구가 정확할 때만 실행. 파기는 withdrawAccount() 단일 경로만 사용.
//
// **이 화면은 "자녀 데이터 삭제"가 아니라 계정 탈퇴다**(2026-07-24 확정, 회신20 §3-3·§5).
// 예전엔 자녀 연쇄만 돌고 accounts·auth_methods·users·알림·푸시가 그대로 남았는데,
// 화면은 "전부 삭제했습니다"라고 말하고 있었다 — 사용자 기만이자 파기 의무 위반 소지였다.
async function handlePurgeAll(request, db, env) {
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return redirect("/mypage");

  const { results: kids } = await db.prepare("SELECT id FROM children WHERE owner_token = ?").bind(ownerToken).all();
  const ids = kids.map((k) => k.id);

  if (request.method === "GET") {
    // 지워질 것을 실제로 세어 보여준다 — "모든 데이터"라고만 쓰면 실감이 안 난다.
    let records = 0, schedules = 0, posts = 0;
    if (ids.length) {
      const ph = ids.map(() => "?").join(",");
      const r = await db.prepare(`SELECT COUNT(*) AS n FROM records WHERE child_id IN (${ph})`).bind(...ids).first();
      const s = await db.prepare(`SELECT COUNT(*) AS n FROM activity_schedules WHERE child_id IN (${ph})`).bind(...ids).first();
      // 커뮤니티 글도 연쇄 삭제 대상이라 여기서 함께 센다 — 세는 목록과 실제 지우는 목록이
      // 어긋나면 이 화면이 거짓말을 하게 된다(2026-07-24).
      const p = await db.prepare(`SELECT COUNT(*) AS n FROM community_posts WHERE child_id IN (${ph})`).bind(...ids).first();
      records = (r && r.n) || 0;
      schedules = (s && s.n) || 0;
      posts = (p && p.n) || 0;
    }
    return html(purgeAllPage({ children: ids.length, records, schedules, posts }));
  }

  if (request.method !== "POST") return html("잘못된 요청입니다.", 405);
  const form = await request.formData();
  // 서버에서도 확인 문구를 검사한다 — 프론트 비활성화만 믿으면 직접 POST로 우회된다.
  if ((form.get("confirm") || "").toString().trim() !== "전체삭제") {
    return html(noticePage("확인 문구가 달라요", "삭제를 진행하려면 <b>전체삭제</b>를 정확히 입력해 주세요.", "/mypage/purge", "✋"));
  }
  // 계정 단위 파기 — 자녀 연쇄 + 신원·인증·연락 파기 + 결제·신고 이력 익명화가 한 함수 안에 있다.
  const account = await findAccountByToken(db, ownerToken);
  const r = await withdrawAccount(db, env, ownerToken, account);
  if (!r.ok) {
    return html(noticePage("삭제 중 문제가 생겼어요", "사진 원본을 지우다 문제가 생겨 <b>중단</b>했습니다. 일부만 지워졌을 수 있어요. 잠시 후 다시 시도해 주세요.", "/mypage", "⚠️"));
  }

  // 쿠키를 즉시 만료시킨다 — 안 지우면 브라우저에 남은 옛 토큰으로 계속 돌아다니게 된다.
  // (그 토큰은 이제 아무 데도 안 닿지만, 남겨둘 이유가 없다.)
  const resp = html(noticePage(
    "탈퇴 처리했습니다",
    "계정과 개인정보, 자녀 정보와 업로드한 원본까지 모두 파기했습니다.<br>" +
    "일부 <b>거래·신고 이력</b>은 법령에 따라 <b>누구인지 알 수 없는 형태로</b> 보관됩니다.<br>" +
    "그동안 이용해 주셔서 감사합니다.",
    "/", "🗑️"
  ));
  resp.headers.append("Set-Cookie", "owner_token=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax");
  return resp;
}

// 결제 내역(마이페이지 하위) — 본인 결제 이력 + 영수증 요약.
async function handleMypagePayments(request, db) {
  const ownerToken = getCookie(request, "owner_token");
  let payments = [];
  if (ownerToken) {
    payments = (await db.prepare("SELECT * FROM payments WHERE owner_token = ? ORDER BY created_at DESC").bind(ownerToken).all()).results;
  }
  return html(paymentsHistoryPage(payments));
}

/* ── 공지사항 관리 (2026-08-14 대표님 「공지사항 같은 게시판」) ─────────
   업데이트·이벤트·점검 공지를 여기서 쓰면 앱 드로어 「공지사항」에 배포 없이 뜬다.
   앱 쪽 정본은 GET /api/v1/notices — 여긴 쓰는 곳(Basic Auth 뒤)이다. */
async function handleAdminNotices(request, db) {
  if (request.method === "POST") {
    const f = await request.formData();
    const title = String(f.get("title") || "").trim().slice(0, 80);
    const body = String(f.get("body") || "").trim().slice(0, 4000);
    if (title && body) {
      await db.prepare("INSERT INTO announcements (title, body, created_at, active) VALUES (?, ?, ?, 1)")
        .bind(title, body, new Date().toISOString()).run();
    }
    return redirect("/admin/notices");
  }
  const { results } = await db.prepare(
    "SELECT id, title, created_at, active FROM announcements ORDER BY id DESC LIMIT 100").all();
  const esc2 = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  return html(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>공지사항 관리</title>
  <body style="font-family:system-ui;max-width:640px;margin:24px auto;padding:0 16px">
  <h2>공지사항 <a href="/admin" style="font-size:13px">← 관리자 홈</a></h2>
  <form method="post" style="display:grid;gap:8px;margin:14px 0;padding:14px;border:1px solid #ddd;border-radius:10px">
    <input name="title" maxlength="80" placeholder="제목 (앱 목록에 이 한 줄만 보입니다)" required style="padding:10px">
    <textarea name="body" rows="6" maxlength="4000" placeholder="내용" required style="padding:10px"></textarea>
    <button style="padding:10px;font-weight:700">올리기</button>
  </form>
  ${(results || []).map((n) => `
    <div style="display:flex;gap:10px;align-items:center;padding:10px 0;border-bottom:1px solid #eee;${n.active ? "" : "opacity:.45"}">
      <b style="flex:1">${esc2(n.title)}</b>
      <span style="font-size:12px;color:#777">${String(n.created_at).slice(0, 10)}</span>
      <form method="post" action="/admin/notices/${n.id}/toggle" style="margin:0">
        <button style="font-size:12px">${n.active ? "내리기" : "다시 올리기"}</button>
      </form>
    </div>`).join("")}
  </body>`);
}

// 알림 설정(마이페이지 하위) — 웹푸시 신청/해제 상태 저장 + 실제 구독/발송.
async function handleMypageNotifications(request, db, env) {
  let ownerToken = getCookie(request, "owner_token");
  const setCookie = [];
  if (request.method === "POST") {
    if (!ownerToken) { ownerToken = newToken(); setCookie.push(`owner_token=${ownerToken}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax`); }
    const form = await request.formData();
    const enabled = form.get("action") === "on" ? 1 : 0;
    const nowIso = new Date().toISOString();
    const upd = await db.prepare("UPDATE notif_settings SET enabled = ?, updated_at = ? WHERE owner_token = ?").bind(enabled, nowIso, ownerToken).run();
    if (!upd.meta || upd.meta.changes === 0) {
      await db.prepare("INSERT INTO notif_settings (owner_token, enabled, updated_at) VALUES (?, ?, ?)").bind(ownerToken, enabled, nowIso).run();
    }
    const resp = redirect("/mypage/notifications");
    for (const c of setCookie) resp.headers.append("Set-Cookie", c);
    return resp;
  }
  let enabled = false;
  if (ownerToken) {
    const row = await db.prepare("SELECT enabled FROM notif_settings WHERE owner_token = ?").bind(ownerToken).first();
    enabled = !!(row && row.enabled);
  }
  return html(notificationsPage(enabled, env && env.VAPID_PUBLIC));
}

// 자녀 관리 — 목록 + 슬롯(N/3) + 수정/학년갱신/삭제 진입. (등록은 학교상세와 동일 흐름)
async function handleChildrenManage(request, db) {
  const ownerToken = getCookie(request, "owner_token");
  let children = [];
  if (ownerToken) {
    const { results } = await db
      .prepare(
        `SELECT children.*, schools.name AS school_name, schools.slug AS school_slug, schools.sem2_start AS sem2_start
         FROM children JOIN schools ON schools.id = children.school_id
         WHERE owner_token = ? ORDER BY children.created_at`
      )
      .bind(ownerToken)
      .all();
    children = results;
  }
  // 한도는 회원 등급 기준(무료 1 / 유료 3) — 화면 문구가 서버 차단과 어긋나지 않게 같은 값 사용.
  // 개방 판정: 등록된 자녀의 학교 중 **하나라도 개학 전**이면 아직 개방으로 본다(더 후한 쪽).
  // 자녀가 없으면 아직 등록 전이라 개방으로 취급 — 첫 등록을 막지 않기 위함.
  const paid = isSubscriber(request);
  const freeOpen = children.length === 0 || children.some((c) => isFreeOpenForSchool(c));
  return html(childrenManagePage(children, maxChildrenFor(paid, freeOpen), paid));
}

// [삭제됨 2026-07-19] handleMypageChildren — 학교 slug를 손으로 입력해 검증 없이 INSERT하던 옛 테스트 폼.
//   어디서도 호출되지 않는 죽은 코드였고(/mypage/children은 handleChildrenManage가 서비스),
//   consent_at·identifiers·trial_expires_at을 채우지 않아 살아나면 동의 없는 자녀가 생겼다.
//   회신4 '옛 테스트 폼을 정식 화면으로 교체' 지시에 따라 제거. 정식 화면은 childrenManagePage.

// 유료 대시보드에서 쓸 "오늘 급식·시간표" 데이터 API 스켈레톤. 실제 발송(웹푸시 등)은 아직 없음 —
// 지금은 데이터만 반환. UI 미노출과 마찬가지로 FEATURE_MYPAGE로 게이트.
async function handleChildToday(db, env, childId) {
  if (env.FEATURE_MYPAGE !== "true") return html("페이지를 찾을 수 없습니다.", 404);

  const child = await db
    .prepare(
      `SELECT children.*, schools.name AS school_name FROM children
       JOIN schools ON schools.id = children.school_id WHERE children.id = ?`
    )
    .bind(childId)
    .first();
  if (!child) return json({ error: "not_found" }, 404);

  const today = todayYmd();

  const meal = await db
    .prepare("SELECT * FROM meals WHERE school_id = ? AND meal_date = ? ORDER BY meal_type_code LIMIT 3")
    .bind(child.school_id, today)
    .all();

  const timetable = await db
    .prepare(
      `SELECT * FROM timetables WHERE school_id = ? AND weekday = ?
       AND school_year = ? AND semester = ?
       AND grade = ? AND COALESCE(class_name, '') = ? ORDER BY CAST(period AS INTEGER)`
    )
    .bind(child.school_id, weekdayOf(today), schoolYearOf(today), currentSemester(today), child.grade, child.class_name || "")
    .all();

  return json({
    child: { id: child.id, nickname: child.nickname, school_name: child.school_name },
    date: today,
    meals: meal.results,
    timetable: timetable.results,
  });
}

// ============================================================
/* ── 관리자 «데이터» 화면 (2026-07-28) ─────────────────────────
   표를 골라 보고 **넣고·고치고·지운다.** 표마다 화면을 만들지 않는다 — 표가 늘 때마다
   화면을 또 만들어야 하고, 그러다 보면 어떤 표는 손댈 길이 없어진다.

   ⚠ 실서버 D1 을 직접 건드리는 화면이라 안전장치를 넣었다.
     ① 표 이름은 **아래 목록에 있는 것만.** 넘어온 문자열을 SQL 에 그대로 넣지 않는다
     ② 컬럼도 PRAGMA 로 읽은 실제 이름과 대조한 것만 쓴다
     ③ 고치기·지우기는 **id 하나**만 대상. WHERE 없는 UPDATE/DELETE 를 만들 길이 없다
     ④ 학교 원본(schools·meals 같은 ETL 결과)은 목록에서 뺐다 — 여기서 지울 일이 없고
        실수로 지우면 되살릴 수가 없다. */
const ADMIN_TABLES = [
  "children", "accounts", "auth_methods", "identifiers", "records", "record_images",
  "supplies", "activity_schedules", "personal_events", "documents", "messages",
  "community_posts", "community_reports", "orders", "payments", "banners",
  "beta_feedback", "info_reports", "inquiries", "community_bans", "child_invites", "notif_settings",
  "timetable_overrides", "schedule_settings", "free_trials", "app_state",
];
const adminTable = (t) => (ADMIN_TABLES.includes(t) ? t : ADMIN_TABLES[0]);

async function adminCols(db, table) {
  const { results } = await db.prepare(`PRAGMA table_info(${table})`).all();
  return (results || []).map((c) => ({ name: c.name, type: c.type, notnull: c.notnull }));
}

async function handleAdminData(request, db, url) {
  const table = adminTable(url.searchParams.get("t") || "");
  const q = (url.searchParams.get("q") || "").trim();
  const page = Math.max(1, parseInt(url.searchParams.get("p") || "1", 10) || 1);
  const per = 50;
  const badges = await getAdminBadges(db);
  const cols = await adminCols(db, table);
  if (!cols.length) {
    return html(adminDataPage({ table, tables: ADMIN_TABLES, cols: [], rows: [], total: 0, page: 1, per, q, msg: "", badges }));
  }
  // 검색은 «아무 칸이나» — 컬럼을 전부 이어 붙여 한 번에 본다(표마다 검색칸을 따로 정하지 않으려고).
  const hay = cols.map((c) => `COALESCE(${c.name},'')`).join(" || ' ' || ");
  const where = q ? `WHERE (${hay}) LIKE ?` : "";
  const args = q ? [`%${q}%`] : [];
  const cnt = await db.prepare(`SELECT COUNT(*) AS n FROM ${table} ${where}`).bind(...args).first();
  const order = cols.some((c) => c.name === "id") ? "ORDER BY id DESC" : "";
  const { results } = await db
    .prepare(`SELECT * FROM ${table} ${where} ${order} LIMIT ? OFFSET ?`)
    .bind(...args, per, (page - 1) * per).all();
  return html(adminDataPage({
    table, tables: ADMIN_TABLES, cols, rows: results || [], total: cnt?.n || 0,
    page, per, q, msg: url.searchParams.get("msg") || "", badges,
  }));
}

async function handleAdminDataSave(request, db) {
  const form = await request.formData();
  const table = adminTable(form.get("t") || "");
  const mode = form.get("mode") === "insert" ? "insert" : "update";
  const cols = await adminCols(db, table);
  // 폼에서 온 이름을 그대로 쓰지 않는다 — PRAGMA 로 읽은 실제 컬럼과 대조한 것만 남긴다.
  const idBlank = !String(form.get("f_id") || "").trim();
  const use = cols.filter((c) => form.has(`f_${c.name}`) && !(mode === "insert" && c.name === "id" && idBlank));
  const val = (c) => { const v = form.get(`f_${c.name}`); return v === "" ? null : v; };
  const back = (m) => redirect(`/admin/data?t=${encodeURIComponent(table)}&msg=${encodeURIComponent(m)}`);

  if (mode === "insert") {
    const names = use.map((c) => c.name);
    if (!names.length) return back("넣을 값이 없습니다");
    await db.prepare(`INSERT INTO ${table} (${names.join(",")}) VALUES (${names.map(() => "?").join(",")})`)
      .bind(...use.map(val)).run();
    return back("넣었습니다");
  }
  const id = form.get("id");
  if (!id) return back("id 가 없습니다");
  const set = use.filter((c) => c.name !== "id");
  if (!set.length) return back("바꿀 값이 없습니다");
  await db.prepare(`UPDATE ${table} SET ${set.map((c) => `${c.name}=?`).join(",")} WHERE id=?`)
    .bind(...set.map(val), id).run();
  return back("고쳤습니다");
}

async function handleAdminDataDelete(request, db) {
  const form = await request.formData();
  const table = adminTable(form.get("t") || "");
  const id = form.get("id");
  const back = (m) => redirect(`/admin/data?t=${encodeURIComponent(table)}&msg=${encodeURIComponent(m)}`);
  if (!id) return back("id 가 없습니다");
  await db.prepare(`DELETE FROM ${table} WHERE id = ?`).bind(id).run();
  return back("지웠습니다");
}

// 관리자 페이지 (/admin, Basic Auth) — §에듀싱크_관리자페이지_지시서.md
// 정식 인증 체계는 나중에, 지금은 학원비사이트 tipoff-api와 동일한 고정 비밀번호 Basic Auth.
// ============================================================

function checkBasicAuth(request, env) {
  const auth = request.headers.get("Authorization") || "";
  if (!auth.startsWith("Basic ")) return false;
  let decoded = "";
  try { decoded = atob(auth.slice(6)); } catch { return false; }
  const idx = decoded.indexOf(":");
  const user = idx === -1 ? decoded : decoded.slice(0, idx);
  const password = idx === -1 ? "" : decoded.slice(idx + 1);
  // 아이디 칸에 비번을 넣든, 비번 칸에 넣든 둘 다 통과(브라우저 Basic Auth 팝업 혼동 방지).
  return password === env.ADMIN_PASSWORD || user === env.ADMIN_PASSWORD;
}

/* 관리자 이름 — Basic Auth 사용자명. 감사 로그의 «누가»다.
   ⚠ 지금은 고정 비밀번호 한 벌이라 사람을 못 가른다. 그래도 «빈칸»보다는 낫고,
     나중에 관리자 계정을 나누면 이 함수만 고치면 된다. */
function adminActor(request) {
  const auth = request.headers.get("Authorization") || "";
  if (!auth.startsWith("Basic ")) return "unknown";
  try {
    const d = atob(auth.slice(6));
    const i = d.indexOf(":");
    return (i === -1 ? d : d.slice(0, i)) || "admin";
  } catch { return "unknown"; }
}

/* 🔴 감사 로그 — 「누가·언제·무엇을·대상·사유」(대표님 요구 §4).
   ⚠ **기록에 실패해도 하던 일을 막지 않는다.** 로그 때문에 CS 가 멈추면 안 된다.
     대신 콘솔에 남겨서 놓친 걸 나중에 찾을 수 있게 한다. */
async function audit(db, request, action, { kind = null, id = null, detail = null, reason = null } = {}) {
  try {
    await db.prepare(
      "INSERT INTO admin_audit (at, actor, action, target_kind, target_id, detail, reason, ip) VALUES (?,?,?,?,?,?,?,?)"
    ).bind(new Date().toISOString(), adminActor(request), action,
      kind, id == null ? null : String(id), detail, reason,
      request.headers.get("CF-Connecting-IP") || null).run();
  } catch (e) { console.error("[audit]", action, e && e.message); }
}

function unauthorized() {
  return new Response("Unauthorized", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="admin"' },
  });
}

async function handleAdminMonitor(db) {
  const { results: schoolCounts } = await db
    .prepare("SELECT school_kind, COUNT(*) AS cnt FROM schools GROUP BY school_kind")
    .all();

  const { results: lastSync } = await db
    .prepare(
      `SELECT schools.name, schools.school_kind,
              (SELECT MAX(last_synced_at) FROM meals WHERE meals.school_id = schools.id) AS last_meal,
              (SELECT MAX(last_synced_at) FROM timetables WHERE timetables.school_id = schools.id) AS last_timetable,
              (SELECT MAX(last_synced_at) FROM academic_schedules WHERE academic_schedules.school_id = schools.id) AS last_schedule
       FROM schools ORDER BY schools.name LIMIT 100`
    )
    .all();

  const { results: recentErrors } = await db
    .prepare(
      `SELECT etl_error_log.*, schools.name AS school_name FROM etl_error_log
       LEFT JOIN schools ON schools.id = etl_error_log.target_school_id
       ORDER BY occurred_at DESC LIMIT 30`
    )
    .all();

  const latestRun = await db.prepare("SELECT * FROM etl_runs ORDER BY started_at DESC LIMIT 1").first();

  const totalsRow = await db.prepare(
    `SELECT (SELECT COUNT(*) FROM schools) AS schools,
            (SELECT COUNT(DISTINCT school_id) FROM academic_schedules) AS schedules,
            (SELECT COUNT(*) FROM school_details) AS details,
            (SELECT COUNT(DISTINCT school_id) FROM meals) AS meals`
  ).first();

  const badges = await getAdminBadges(db);
  return html(adminMonitorPage({ schoolCounts, lastSync, recentErrors, latestRun, totals: totalsRow, badges }));
}

async function handleAdminBanners(request, db) {
  if (request.method === "POST") {
    const form = await request.formData();
    await db
      .prepare(
        `INSERT INTO banners (
          slot, banner_type, code_snippet, image_url, link_url, alt_text,
          advertiser_name, region_office_code, starts_at, ends_at, paid, active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)`
      )
      .bind(
        Number(form.get("slot")),
        form.get("banner_type"),
        form.get("code_snippet") || null,
        form.get("image_url") || null,
        form.get("link_url") || null,
        form.get("alt_text") || null,
        form.get("advertiser_name") || null,
        form.get("region_office_code") || null,
        form.get("starts_at") || null,
        form.get("ends_at") || null,
        form.get("paid") ? 1 : 0,
        new Date().toISOString()
      )
      .run();
  }

  const { results: banners } = await db.prepare("SELECT * FROM banners ORDER BY slot, id DESC").all();
  return html(adminBannersPage(banners, await getAdminBadges(db)));
}

async function handleAdminBannerToggle(db, id) {
  await db.prepare("UPDATE banners SET active = 1 - active WHERE id = ?").bind(id).run();
  return redirect("/admin/banners");
}

async function handleAdminBannerDelete(db, id) {
  await db.prepare("DELETE FROM banners WHERE id = ?").bind(id).run();
  return redirect("/admin/banners");
}

// 배너 수정 — 이미지/링크/문구/광고주/지역/기간/코드/결제 갱신.
async function handleAdminBannerEdit(request, db, id) {
  const form = await request.formData();
  await db.prepare(
    `UPDATE banners SET image_url=?, link_url=?, alt_text=?, advertiser_name=?, region_office_code=?, starts_at=?, ends_at=?, code_snippet=?, paid=? WHERE id=?`
  ).bind(
    form.get("image_url") || null, form.get("link_url") || null, form.get("alt_text") || null,
    form.get("advertiser_name") || null, form.get("region_office_code") || null,
    form.get("starts_at") || null, form.get("ends_at") || null, form.get("code_snippet") || null,
    form.get("paid") ? 1 : 0, id
  ).run();
  return redirect("/admin/banners");
}

async function handleAdminCorrect(request, db, url) {
  // 수정 이력 전체(최근 30) — 원복 대상.
  const editLog = (await db.prepare(
    `SELECT l.*, s.name AS school_name FROM admin_edit_log l
     LEFT JOIN meals m ON l.table_name='meals' AND m.id=l.record_id
     LEFT JOIN academic_schedules a ON l.table_name='academic_schedules' AND a.id=l.record_id
     LEFT JOIN schools s ON s.id = COALESCE(m.school_id, a.school_id)
     ORDER BY l.edited_at DESC LIMIT 30`
  ).all()).results;

  const badges = await getAdminBadges(db);
  const schoolSlug = url.searchParams.get("school_slug");
  if (!schoolSlug) return html(adminCorrectPage(null, [], [], editLog, badges));

  const school = await db.prepare("SELECT * FROM schools WHERE slug = ?").bind(schoolSlug).first();
  if (!school) return html(adminCorrectPage(null, [], [], editLog, badges));

  const { results: meals } = await db
    .prepare("SELECT * FROM meals WHERE school_id = ? ORDER BY meal_date DESC LIMIT 20")
    .bind(school.id)
    .all();
  const { results: schedules } = await db
    .prepare("SELECT * FROM academic_schedules WHERE school_id = ? ORDER BY event_date DESC LIMIT 20")
    .bind(school.id)
    .all();

  return html(adminCorrectPage(school, meals, schedules, editLog, badges));
}

// 보정 취소(원복) — admin_edit_log의 old_value로 되돌리고 이력 삭제. 화이트리스트 필드만.
async function handleAdminCorrectUndo(request, db) {
  const form = await request.formData();
  const logId = (form.get("log_id") || "").toString();
  const log = await db.prepare("SELECT * FROM admin_edit_log WHERE id = ?").bind(logId).first();
  if (!log) return redirect("/admin/correct");
  const allowed = { meals: ["dishes"], timetables: ["subject"], academic_schedules: ["event_name", "event_content"] };
  if (!allowed[log.table_name] || !allowed[log.table_name].includes(log.field_name)) return html("복원할 수 없는 항목입니다.", 400);
  await db.prepare(`UPDATE ${log.table_name} SET ${log.field_name} = ? WHERE id = ?`).bind(log.old_value, log.record_id).run();
  await db.prepare("DELETE FROM admin_edit_log WHERE id = ?").bind(logId).run();
  return redirect("/admin/correct");
}

async function logAdminEdit(db, tableName, recordId, fieldName, oldValue, newValue) {
  await db
    .prepare(
      "INSERT INTO admin_edit_log (table_name, record_id, field_name, old_value, new_value, edited_at) VALUES (?, ?, ?, ?, ?, ?)"
    )
    .bind(tableName, recordId, fieldName, oldValue, newValue, new Date().toISOString())
    .run();
}

async function handleAdminCorrectMeal(request, db, id) {
  const form = await request.formData();
  const newDishes = (form.get("dishes") || "").toString();
  const before = await db.prepare("SELECT dishes, school_id FROM meals WHERE id = ?").bind(id).first();
  if (!before) return html("대상을 찾을 수 없습니다.", 404);

  await db.prepare("UPDATE meals SET dishes = ? WHERE id = ?").bind(newDishes, id).run();
  await logAdminEdit(db, "meals", id, "dishes", before.dishes, newDishes);

  const school = await db.prepare("SELECT slug FROM schools WHERE id = ?").bind(before.school_id).first();
  return redirect(`/admin/correct?school_slug=${encodeURIComponent(school.slug)}`);
}

async function handleAdminCorrectSchedule(request, db, id) {
  const form = await request.formData();
  const newName = (form.get("event_name") || "").toString();
  const before = await db.prepare("SELECT event_name, school_id FROM academic_schedules WHERE id = ?").bind(id).first();
  if (!before) return html("대상을 찾을 수 없습니다.", 404);

  await db.prepare("UPDATE academic_schedules SET event_name = ? WHERE id = ?").bind(newName, id).run();
  await logAdminEdit(db, "academic_schedules", id, "event_name", before.event_name, newName);

  const school = await db.prepare("SELECT slug FROM schools WHERE id = ?").bind(before.school_id).first();
  return redirect(`/admin/correct?school_slug=${encodeURIComponent(school.slug)}`);
}

// 유료 회원 페이지 — 등록된 자녀(테스트 포함) 목록.
async function handleAdminMembers(db, request, url) {
  const { results } = await db
    .prepare(
      `SELECT children.*, schools.name AS school_name, schools.slug AS school_slug
       FROM children JOIN schools ON schools.id = children.school_id ORDER BY children.created_at DESC`
    )
    .all();
  // 부모(owner_token) 1건 → 자녀 최대 3명 묶음으로 그룹화(§관리자지시서 회원관리).
  const groupMap = new Map();
  for (const c of results) {
    if (!groupMap.has(c.owner_token)) groupMap.set(c.owner_token, []);
    groupMap.get(c.owner_token).push(c);
  }
  // 회원 상세 모달용 부가 데이터: 소셜계정 / 결제내역 / 알림신청 / 무료체험 — 전부 owner_token으로 묶는다.
  /* ⚠ 예전엔 `users`(옛 토큰 계정)만 읽었다. 그런데 실서버는 **전원이 `accounts`**
     (아이디·비밀번호 가입)이고 `users` 는 **0행**이다 → 관리자 목록에 이메일·아이디가
     하나도 안 나오고 전부 「토큰」으로만 보였다(2026-08-09 실측: accounts 10건 · users 0건).
     대표님 지적 「아이디가 확실히 있어야 한다」의 원인이 이것이다 — 데이터는 멀쩡했고 화면이 안 읽었다.
     → 둘 다 읽어 `accounts` 를 우선한다. 옛 토큰 계정이 남아 있어도 그대로 보인다. */
  const { results: users } = await db.prepare("SELECT owner_token, provider, nickname, created_at, last_login_at FROM users").all();
  const acctMap = new Map(users.map((u) => [u.owner_token, { ...u, kind: "token" }]));
  const { results: accts } = await db.prepare(
    `SELECT a.owner_token, a.display_name, a.email, a.status, a.created_at, a.last_login_at,
            (SELECT identifier FROM auth_methods WHERE account_id = a.id ORDER BY id LIMIT 1) AS login_id
       FROM accounts a`
  ).all();
  for (const a of accts) {
    acctMap.set(a.owner_token, {
      owner_token: a.owner_token, provider: "id", nickname: a.display_name,
      email: a.email, login_id: a.login_id, status: a.status,
      created_at: a.created_at, last_login_at: a.last_login_at, kind: "account",
    });
  }
  const { results: pays } = await db.prepare("SELECT * FROM payments ORDER BY created_at DESC").all();
  const payMap = new Map();
  for (const p of pays) { if (!payMap.has(p.owner_token)) payMap.set(p.owner_token, []); payMap.get(p.owner_token).push(p); }
  const { results: notifs } = await db.prepare("SELECT owner_token, enabled FROM notif_settings").all();
  const notifMap = new Map(notifs.map((n) => [n.owner_token, !!n.enabled]));
  const { results: trials } = await db.prepare("SELECT owner_token FROM free_trials").all();
  const trialSet = new Set(trials.map((t) => t.owner_token));
  const groups = [...groupMap.entries()].map(([token, kids]) => ({
    token, kids,
    account: acctMap.get(token) || null,
    payments: payMap.get(token) || [],
    notif: notifMap.get(token) || false,
    trial: trialSet.has(token),
  }));
  /* 걸러 보기 (2026-08-10 대표님 요구 §7) — 「유료 / 무료를 별도 표시」.
     ⚠ «유료»의 뜻을 한 곳에서 정한다: **결제 이력이 있고 환불이 아닌 것**이 하나라도 있으면 유료.
       화면마다 다르게 세면 같은 회원이 표마다 다른 칸에 앉는다. */
  const isPaid = (g) => (g.payments || []).some((p) => p.status !== "refunded");
  const pay = (url && url.searchParams.get("pay")) || "";
  const shown = pay === "paid" ? groups.filter(isPaid)
    : pay === "free" ? groups.filter((g) => !isPaid(g))
    : groups;
  const badges = await getAdminBadges(db);
  return html(adminMembersPage(shown, isSubscriber(request), MAX_CHILDREN, badges, {
    pay, nPaid: groups.filter(isPaid).length, nFree: groups.filter((g) => !isPaid(g)).length,
    /* 결과 배너 (2026-08-12) — 조정이 조용히 무시돼도 성공처럼 보였다(«30일 넣었는데 왜 안 들어가») */
    ok: (url && url.searchParams.get("ok")) || "", err: (url && url.searchParams.get("err")) || "",
  }));
}

// 관리자 네비 배지용 — 미처리 신고/의견 수(가벼운 COUNT).
async function getAdminBadges(db) {
  // 입금대기·미답변 문의는 «사람이 손대야 끝나는» 일이라 배지로 세운다 — 안 보이면 며칠씩 멈춘다.
  const r = await db.prepare(
    "SELECT (SELECT COUNT(*) FROM info_reports WHERE status='open') AS reports, (SELECT COUNT(*) FROM beta_feedback WHERE status='open') AS feedback, (SELECT COUNT(*) FROM orders WHERE status='awaiting_deposit') AS orders, (SELECT COUNT(*) FROM inquiries WHERE status='open') AS inquiries, (SELECT COUNT(*) FROM community_posts WHERE hidden = 1) AS flags"
  ).first();
  return { reports: (r && r.reports) || 0, feedback: (r && r.feedback) || 0, orders: (r && r.orders) || 0,
    inquiries: (r && r.inquiries) || 0, flags: (r && r.flags) || 0 };
}

// 이용기간 수동 조정(CS) — 해당 부모의 (테스트 아닌) 자녀 만료일을 ±일 조정.
async function handleAdminAdjustExpiry(request, db) {
  const form = await request.formData();
  const token = (form.get("owner_token") || "").toString();
  const days = parseInt((form.get("days") || "").toString(), 10);
  const reason = (form.get("reason") || "").toString().trim();
  if (!token || !Number.isFinite(days)) return redirect("/admin/members?err=bad");
  /* 🔴 **사유 없이는 못 바꾼다**(대표님 요구 §2·§4).
     이용권을 손으로 주고 회수하는 이상, 사유가 없으면 나중에
     «왜 이 계정만 1년이지?» 를 아무도 답할 수 없다. */
  if (reason.length < 2) return redirect("/admin/members?err=reason");

  const kids = (await db.prepare("SELECT id, trial_expires_at FROM children WHERE owner_token = ? AND is_test = 0").bind(token).all()).results;
  for (const k of kids) {
    const base = k.trial_expires_at ? new Date(k.trial_expires_at).getTime() : Date.now();
    const nd = new Date(base + days * 86400000).toISOString();
    await db.prepare("UPDATE children SET trial_expires_at = ? WHERE id = ?").bind(nd, k.id).run();
  }
  await audit(db, request, "pass_adjust", {
    kind: "account", id: token,
    detail: `${days > 0 ? "+" : ""}${days}일 · 자녀 ${kids.length}명`, reason,
  });
  return redirect("/admin/members?ok=adjust");
}

// 결제 관리 — 결제 내역 전체 조회(검색: 이름/owner_token 일부) + 환불/수정/삭제.
async function handleAdminPayments(request, db, url) {
  const q = (url.searchParams.get("q") || "").trim();
  let sql = "SELECT * FROM payments";
  const binds = [];
  if (q) { sql += " WHERE owner_token LIKE ? OR payer_name LIKE ?"; binds.push(`%${q}%`, `%${q}%`); }
  sql += " ORDER BY created_at DESC LIMIT 200";
  const { results } = await db.prepare(sql).bind(...binds).all();
  // 결제자 이름 폴백용: 로그인 회원 닉네임 매핑(payer_name 없을 때 표시).
  const { results: users } = await db.prepare("SELECT owner_token, nickname FROM users").all();
  const nameMap = {};
  for (const u of users) if (u.nickname) nameMap[u.owner_token] = u.nickname;
  return html(adminPaymentsPage(results, q, nameMap, await getAdminBadges(db)));
}

/* 앱 주문 — orders 표(앱 인앱결제·무통장·모의). 부모 이름은 accounts, 자녀 별명은 children에서 끌어온다.
   자녀가 지워져도 주문 줄은 남아야 한다(정산 근거) → LEFT JOIN. */
/* 감사 기록 보기 (2026-08-10) — 읽기 전용이다. 지우는 라우트는 만들지 않는다.
   ⚠ 500줄만 본다. 다 보여주면 느리고, 오래된 것은 어차피 화면에서 안 찾는다(필요하면 검색). */
async function handleAdminAudit(db, url) {
  const q = (url.searchParams.get("q") || "").trim();
  let sql = "SELECT * FROM admin_audit";
  const binds = [];
  if (q) {
    sql += " WHERE reason LIKE ? OR target_id LIKE ? OR actor LIKE ? OR detail LIKE ?";
    binds.push(`%${q}%`, `%${q}%`, `%${q}%`, `%${q}%`);
  }
  sql += " ORDER BY id DESC LIMIT 500";
  const { results } = await db.prepare(sql).bind(...binds).all();
  const rows = (results || []).map((r) => ({
    ...r,
    atF: String(r.at || "").replace("T", " ").slice(0, 16),
    targetKind: r.target_kind, targetShort: String(r.target_id || "").slice(0, 10),
  }));
  return html(adminAuditPage(rows, { q }, await getAdminBadges(db)));
}

async function handleAdminOrders(db, url) {
  const q = (url.searchParams.get("q") || "").trim();
  const status = (url.searchParams.get("s") || "").trim();
  let sql = `SELECT o.*, a.display_name AS parent_name, c.nickname AS child_nickname
             FROM orders o
             LEFT JOIN accounts a ON a.id = o.account_id
             LEFT JOIN children c ON c.id = o.child_id`;
  const where = [];
  const binds = [];
  if (status && ORDER_STATES.includes(status)) { where.push("o.status = ?"); binds.push(status); }
  if (q) { where.push("(a.display_name LIKE ? OR c.nickname LIKE ? OR o.payer_name LIKE ?)"); binds.push(`%${q}%`, `%${q}%`, `%${q}%`); }
  if (where.length) sql += " WHERE " + where.join(" AND ");
  sql += " ORDER BY o.created_at DESC LIMIT 200";
  const { results } = await db.prepare(sql).bind(...binds).all();
  return html(adminOrdersPage(results, { q, status }, await getAdminBadges(db)));
}
const ORDER_STATES = ["pending", "awaiting_deposit", "confirmed", "active", "expired", "cancelled"];

/* 문의 — 미답변이 항상 위로 온다. 「접수순」으로만 정렬하면 오래된 답변완료가 화면을 채워
   오늘 들어온 미답변이 스크롤 아래로 밀린다(오류 신고 탭과 같은 규칙). */
/* 대화 신고 — 신고가 하나라도 붙은 글을 모은다. 내려간 것(hidden)이 위로 온다.
   신고 없는 글은 여기 안 나온다 — 관리자가 남의 대화를 훑어보는 화면이 아니다. */
async function handleAdminCommunity(db) {
  const { results } = await db.prepare(
    `SELECT p.id, p.body, p.owner_token, p.hidden, p.report_count, p.created_at,
            p.author_grade, p.author_class,
            (SELECT COUNT(*) FROM community_reports r WHERE r.post_id = p.id) AS reports,
            s.name AS school_name, a.display_name AS parent_name
       FROM community_posts p
       LEFT JOIN schools s ON s.id = p.school_id
       LEFT JOIN accounts a ON a.owner_token = p.owner_token
      WHERE EXISTS (SELECT 1 FROM community_reports r WHERE r.post_id = p.id)
      ORDER BY p.hidden DESC, reports DESC, p.created_at DESC
      LIMIT 200`
  ).all();
  const { results: bans } = await db.prepare(
    `SELECT b.*, a.display_name AS parent_name FROM community_bans b
      LEFT JOIN accounts a ON a.owner_token = b.owner_token
      ORDER BY b.created_at DESC LIMIT 100`
  ).all();
  return html(adminCommunityPage(results, bans, await getAdminBadges(db)));
}

const INQUIRY_STATES = ["open", "answered", "closed"];
async function handleAdminInquiries(db, url) {
  const q = (url.searchParams.get("q") || "").trim();
  const status = (url.searchParams.get("s") || "").trim();
  let sql = `SELECT i.*, a.display_name AS parent_name, c.nickname AS child_nickname
             FROM inquiries i
             LEFT JOIN accounts a ON a.id = i.account_id
             LEFT JOIN children c ON c.id = i.child_id`;
  const where = [];
  const binds = [];
  if (status && INQUIRY_STATES.includes(status)) { where.push("i.status = ?"); binds.push(status); }
  if (q) { where.push("(i.title LIKE ? OR i.body LIKE ? OR a.display_name LIKE ?)"); binds.push(`%${q}%`, `%${q}%`, `%${q}%`); }
  if (where.length) sql += " WHERE " + where.join(" AND ");
  sql += " ORDER BY (i.status = 'open') DESC, i.created_at DESC LIMIT 200";
  const { results } = await db.prepare(sql).bind(...binds).all();
  return html(adminInquiriesPage(results, { q, status }, await getAdminBadges(db)));
}

async function handleAdminRefund(db, id) {
  await db.prepare("UPDATE payments SET status = 'refunded' WHERE id = ?").bind(id).run();
  return redirect("/admin/payments");
}

// 결제 수정 — 결제자 이름·금액만(더미 결제 CS 정정용). 기간·자녀·수단은 결제 원본이라 미변경.
async function handleAdminPaymentEdit(request, db, id) {
  const form = await request.formData();
  const payerName = (form.get("payer_name") || "").toString().trim();
  const amount = parseInt((form.get("amount") || "").toString(), 10);
  await db.prepare("UPDATE payments SET payer_name = ?, amount = COALESCE(?, amount) WHERE id = ?")
    .bind(payerName || null, Number.isFinite(amount) ? amount : null, id).run();
  return redirect("/admin/payments");
}

async function handleAdminPaymentDelete(db, id) {
  await db.prepare("DELETE FROM payments WHERE id = ?").bind(id).run();
  return redirect("/admin/payments");
}

// 학교 이름 자동완성(관리자 데이터보정·테스트자녀 등록 공용) — 이름 일부로 검색, JSON 반환.
async function handleAdminSchoolSearch(db, url) {
  const q = (url.searchParams.get("q") || "").trim();
  if (!q) return json([]);
  const { results } = await db.prepare(
    `SELECT name, slug, school_kind, sido FROM schools WHERE name LIKE ? ORDER BY name LIMIT 10`
  ).bind(`%${q}%`).all();
  return json(results.map((s) => ({
    name: s.name, slug: s.slug, kind: s.school_kind || "", region: s.sido || "",
  })));
}

// 회원 자녀 정보 수정(관리자) — 별명·학년·반. 오등록 정정용.
async function handleAdminMemberEditChild(request, db, id) {
  const form = await request.formData();
  const nickname = (form.get("nickname") || "").toString().trim();
  const grade = (form.get("grade") || "").toString().trim();
  const className = (form.get("class_name") || "").toString().trim();
  if (!nickname || !grade) return html("별명·학년은 필수입니다.", 400);
  await db.prepare("UPDATE children SET nickname = ?, grade = ?, class_name = ? WHERE id = ?")
    .bind(nickname, grade, className || null, id).run();
  return redirect("/admin/members");
}

// QA용 계정 연결 — 이 브라우저의 owner_token에 소셜 계정 행을 만들어 "로그인됨" 상태로 만든다.
// 로그인 게이트(needsLogin)가 users 행 유무로 판정하므로, 이게 없으면 /mypage·/register-child 등
// 로그인 필요 화면을 QA할 수 없다(실제로 검증이 막혀 있었다).
//
// **인증 우회 경로가 아니다** — 이중 잠금(회신2 Q4 조건):
//   ① admin Basic Auth 뒤에서만 접근 가능
//   ② DEV_TOOLS !== "true"면 admin 안에서도 동작하지 않음
// 배포 전 시뮬레이션 체크리스트: "운영에서 이 도구 비노출 확인".
async function handleAdminDevAccount(request, db, env) {
  if (env.DEV_TOOLS !== "true") return html("개발 도구가 꺼져 있습니다.", 404);
  let ownerToken = getCookie(request, "owner_token");
  const setCookie = [];
  if (!ownerToken) {
    ownerToken = crypto.randomUUID();
    setCookie.push(`owner_token=${ownerToken}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax`);
  }
  const nowIso = new Date().toISOString();
  const existing = await db.prepare("SELECT id FROM users WHERE owner_token = ?").bind(ownerToken).first();
  if (existing) {
    await db.prepare("UPDATE users SET last_login_at = ? WHERE owner_token = ?").bind(nowIso, ownerToken).run();
  } else {
    await db
      .prepare("INSERT INTO users (provider, provider_uid, nickname, owner_token, created_at, last_login_at) VALUES ('kakao', ?, 'QA계정', ?, ?, ?)")
      .bind("qa-" + ownerToken.slice(0, 8), ownerToken, nowIso, nowIso)
      .run();
  }
  const resp = redirect("/admin/members");
  for (const c of setCookie) resp.headers.append("Set-Cookie", c);
  return resp;
}

// 회원(부모) 전체 삭제 — 해당 owner_token의 모든 자녀를 연쇄 삭제.
// 예전엔 children만 지워서 personal_schedule·personal_events·schedule_settings가 고아로 남았다(2026-07-19 수정).
async function handleAdminMemberTokenDelete(request, db, env) {
  const form = await request.formData();
  const token = (form.get("owner_token") || "").toString();
  if (token) {
    const { results } = await db.prepare("SELECT id FROM children WHERE owner_token = ?").bind(token).all();
    for (const c of results) await deleteChildCascade(db, env, c.id);
  }
  return redirect("/admin/members");
}

// 이 브라우저를 유료 가입자로 표시/해제(결제 미구현 테스트용 스위치).
async function handleAdminSubscriber(request) {
  const form = await request.formData();
  const on = (form.get("action") || "").toString() === "on";
  const resp = redirect("/admin/members");
  resp.headers.append("Set-Cookie", on
    ? "subscriber=1; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax"
    : "subscriber=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax");
  return resp;
}

// 정보 오류 신고 열람(관리자). open 먼저, 최신순.
async function handleAdminReports(request, db) {
  const { results } = await db
    .prepare(
      `SELECT info_reports.*, schools.name AS school_name, schools.slug AS school_slug
       FROM info_reports JOIN schools ON schools.id = info_reports.school_id
       ORDER BY (info_reports.status = 'open') DESC, info_reports.created_at DESC LIMIT 200`
    )
    .all();
  return html(adminReportsPage(results, await getAdminBadges(db)));
}

async function handleAdminResolveReport(db, id) {
  await db.prepare("UPDATE info_reports SET status = 'resolved' WHERE id = ?").bind(id).run();
  return redirect("/admin/reports");
}

// 베타 의견 열람(관리자). open 먼저, 최신순.
async function handleAdminFeedback(request, db) {
  const { results } = await db
    .prepare("SELECT * FROM beta_feedback ORDER BY (status = 'open') DESC, created_at DESC LIMIT 300")
    .all();
  return html(adminFeedbackPage(results, await getAdminBadges(db)));
}

async function handleAdminResolveFeedback(db, id) {
  await db.prepare("UPDATE beta_feedback SET status = 'resolved' WHERE id = ?").bind(id).run();
  return redirect("/admin/feedback");
}

// 테스트 자녀 등록(§관리자지시서_1 §4) — 결제 없이 잠금 해제. is_test=1 + owner_token 쿠키 세팅.
async function handleAdminAddTestChild(request, db) {
  const form = await request.formData();
  const schoolSlug = (form.get("school_slug") || "").toString().trim();
  const grade = (form.get("grade") || "").toString().trim();
  const className = (form.get("class_name") || "").toString().trim();
  const nickname = (form.get("nickname") || "").toString().trim();
  if (!schoolSlug || !grade || !nickname) return html("필수 항목이 비어있습니다.", 400);

  const school = await db.prepare("SELECT id FROM schools WHERE slug = ?").bind(schoolSlug).first();
  if (!school) return html("학교를 찾을 수 없습니다. slug을 확인하세요.", 404);

  // 관리자 브라우저의 owner_token(없으면 생성)에 테스트 자녀를 묶는다.
  let ownerToken = getCookie(request, "owner_token");
  const setCookie = [];
  if (!ownerToken) {
    ownerToken = crypto.randomUUID();
    setCookie.push(`owner_token=${ownerToken}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax`);
  }
  // trial_expires_at을 함께 채운다 — 비워두면 admin 회원목록의 그룹 pill이 이 자녀를 "만료"로
  // 오인하던 불일치가 생긴다(2026-07-19 수정). QA용이라 넉넉히 1년.
  const nowIso = new Date().toISOString();
  const testExpires = new Date(Date.now() + 365 * 86400000).toISOString();
  await db
    .prepare(
      "INSERT INTO children (owner_token, school_id, grade, class_name, nickname, is_test, trial_expires_at, created_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)"
    )
    .bind(ownerToken, school.id, grade, className || null, nickname, testExpires, nowIso)
    .run();

  const resp = redirect("/admin/members");
  for (const c of setCookie) resp.headers.append("Set-Cookie", c);
  return resp;
}

// admin 자녀 단건 삭제 — 사용자 경로와 같은 연쇄 삭제를 탄다(2026-07-19).
async function handleAdminDeleteChild(db, id, env) {
  // 반환값을 반드시 확인한다 — 예전엔 무시해서 R2 실패 시 아무것도 안 지워졌는데도
  // 302로 넘어가 "삭제됐다"고 보였다(2026-07-24 발견). 조용한 실패가 가장 나쁘다.
  const r = await deleteChildCascade(db, env, id);
  if (!r.ok) return html("사진 삭제 중 문제가 생겨 중단했습니다. 다시 시도해 주세요.", 500);
  return redirect("/admin/members");
}

// ===== 로컬 개발 전용 QA 도구 (/dev/*) =====
// URL 접속만으로 특정 테스트 계정의 owner_token 쿠키를 심어주는 엔드포인트.
// 이중 게이트로 배포 환경 노출을 원천 차단:
//   ① env.DEV_TOOLS === "true"  — 이 값은 .dev.vars(로컬 wrangler dev만 로드, 배포엔 미포함)에만 존재
//   ② 호스트가 localhost / 127.0.0.1 — workers.dev에선 절대 참이 될 수 없음
// 둘 다 만족해야 살아난다. 하나라도 아니면 일반 404로 응답(라우트 자체가 없는 것처럼).
// QA 라우트(/dev/*) 스위치. 원래 localhost로만 한정했으나, 배포본을 다른 기기·웹에서 QA해야 해서
// DEV_TOOLS="true"면 배포 도메인에서도 허용한다(2026-07-17). ⚠️ 이 값이 켜져 있으면 owner_token만
// 알면 그 계정으로 들어갈 수 있으므로, QA가 끝나면 wrangler.toml에서 "false"로 내리고 재배포할 것.
function isDevToolsEnabled(env, url) {
  return !!(env && env.DEV_TOOLS === "true");
}

// GET /dev/login-as?token=<owner_token>[&to=<경로>]
// 받은 owner_token을 그대로 쿠키로 심고 학교상세(기본) 또는 지정 경로로 리다이렉트.
function handleDevLoginAs(url) {
  const token = (url.searchParams.get("token") || "").trim();
  if (!token) return html("token 쿼리 파라미터가 필요합니다. 예: /dev/login-as?token=<owner_token>", 400);
  // 기본 목적지: 학교상세(마이페이지로 바꾸려면 &to=/mypage). 안전하게 내부 절대경로만 허용.
  let to = (url.searchParams.get("to") || "/mypage").trim();
  if (!to.startsWith("/")) to = "/mypage";
  const resp = new Response(null, { status: 302, headers: { Location: to } });
  // 실제 로그인 흐름과 동일하게 HttpOnly·1년 만료로 심는다.
  resp.headers.append("Set-Cookie", `owner_token=${encodeURIComponent(token)}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax`);
  // sub=1이면 유료(구독) 회원으로 진입 — 유료 판정이 subscriber 쿠키 기준이라 QA용으로 같이 심는다.
  // sub=0(또는 생략)이면 무료회원으로 보이도록 명시적으로 제거(이전 QA 세션의 쿠키 잔존 방지).
  resp.headers.append("Set-Cookie", url.searchParams.get("sub") === "1"
    ? "subscriber=1; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax"
    : "subscriber=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax");
  return resp;
}

// GET /dev/logout — owner_token 쿠키 삭제(미가입 상태로 되돌림).
function handleDevLogout() {
  const resp = new Response(null, { status: 302, headers: { Location: "/" } });
  resp.headers.append("Set-Cookie", "owner_token=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax");
  return resp;
}

// ============================================================
// 소셜 로그인(카카오·구글·네이버) — auth.js 공통 모듈 사용.
// 데이터 키는 계속 owner_token: 최초 로그인 시 현재 기기의 익명 토큰을 계정에 채택(데이터 승계),
// 이후 어느 기기에서 로그인하든 그 토큰을 쿠키로 복원 → 다기기에서 자녀·일정이 그대로 보인다.
// ============================================================

// GET /login — 로그인 화면. 키가 등록된 제공자 버튼만 노출(키 도착 순서대로 부분 오픈).
async function handleLoginPage(request, db, env) {
  const ownerToken = getCookie(request, "owner_token");
  const account = ownerToken ? await accountForToken(db, ownerToken) : null; // accounts 기준(회신24 §2)
  return html(loginPage(providersFrom(env), account));
}

// GET /auth/:provider — state 쿠키 심고 제공자 로그인 화면으로.
function handleAuthStart(provider, env, url) {
  if (!providersFrom(env).includes(provider)) {
    return html(noticePage("준비 중인 로그인이에요", "이 로그인 방식은 아직 준비 중입니다. 다른 방법으로 로그인해 주세요.", "/login", "🔧"));
  }
  const state = crypto.randomUUID();
  const target = authorizeUrl(provider, env, url.origin, state);
  const resp = new Response(null, { status: 302, headers: { Location: target } });
  resp.headers.append("Set-Cookie", `oauth_state=${state}; Path=/; Max-Age=600; HttpOnly; SameSite=Lax`);
  return resp;
}

// GET /auth/:provider/callback — code→프로필 조회→계정 upsert→owner_token 복원/채택.
async function handleAuthCallback(provider, request, db, env, url) {
  const fail = (msg) => html(noticePage("로그인에 실패했어요", `${msg}<br>잠시 후 다시 시도해 주세요.`, "/login", "🙏"));
  if (url.searchParams.get("error")) return fail("로그인이 취소되었거나 제공자에서 오류가 났어요.");
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state") || "";
  const savedState = getCookie(request, "oauth_state") || "";
  if (!code) return fail("인증 코드가 없어요.");
  if (!savedState || savedState !== state) return fail("보안 확인(state)에 실패했어요.");

  const identity = await fetchIdentity(provider, env, url.origin, code, state);
  if (!identity || identity.error || !identity.uid) {
    // 원인을 반드시 남긴다 — `wrangler tail`로 확인. 사용자에겐 내부 응답을 노출하지 않는다.
    console.error(`[auth:${provider}] ${(identity && identity.error) || "identity null"}`);
    return fail("프로필 조회에 실패했어요.");
  }

  const nowIso = new Date().toISOString();
  const existing = await db.prepare("SELECT * FROM users WHERE provider = ? AND provider_uid = ?").bind(provider, identity.uid).first();
  let ownerToken;
  if (existing) {
    // 기존 계정 — 그 계정의 데이터 키를 이 기기에 복원.
    ownerToken = existing.owner_token;
    await db.prepare("UPDATE users SET nickname = COALESCE(?, nickname), last_login_at = ? WHERE id = ?")
      .bind(identity.nickname, nowIso, existing.id).run();
  } else {
    // 신규 계정 — 이 기기의 익명 토큰을 채택(기존 자녀·일정 승계). 없으면 새 토큰.
    ownerToken = getCookie(request, "owner_token") || newToken();
    await db.prepare("INSERT INTO users (provider, provider_uid, nickname, owner_token, created_at, last_login_at) VALUES (?, ?, ?, ?, ?, ?)")
      .bind(provider, identity.uid, identity.nickname, ownerToken, nowIso, nowIso).run();
  }
  // accounts 승계(정본 §4) — 기존 users 로직은 그대로 두고 계정 체계에도 연결한다.
  // owner_token을 그대로 넘기므로 children·records·R2가 통째로 살아남는다. 실패해도 로그인은 막지 않는다.
  try {
    await linkSocialAccount(db, provider, identity.uid, identity.nickname, ownerToken);
  } catch (e) {
    console.error("[auth] linkSocialAccount 실패:", e && e.message);
  }

  // 로그인 후 복귀: 게이트가 남긴 login_next(같은 오리진 경로)로, 없으면 /mypage.
  let dest = "/mypage";
  const nextRaw = getCookie(request, "login_next");
  if (nextRaw) {
    const d = decodeURIComponent(nextRaw);
    if (d.startsWith("/") && !d.startsWith("//")) dest = d;
  }
  const resp = new Response(null, { status: 302, headers: { Location: dest } });
  resp.headers.append("Set-Cookie", `owner_token=${encodeURIComponent(ownerToken)}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax`);
  resp.headers.append("Set-Cookie", "oauth_state=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax");
  resp.headers.append("Set-Cookie", "login_next=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax");
  return resp;
}

// GET /logout — 이 기기에서만 로그아웃(쿠키 삭제). 계정·데이터는 그대로, 재로그인하면 복원.
function handleLogout() {
  const resp = new Response(null, { status: 302, headers: { Location: "/" } });
  resp.headers.append("Set-Cookie", "owner_token=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax");
  return resp;
}

function manifest(origin) {
  return json({
    name: "아이서랍",
    short_name: "학교정보",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#2E7D5B",
    // PWA 설치·홈화면 추가 아이콘 — 512 하나로 any/maskable 모두 커버.
    icons: [
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  });
}

// 학교 표준 서식 — /forms?school=<slug>[&type=counsel|field|absence|earlyleave]
// 학교명은 항상 채우고, 로그인+해당 학교 자녀가 있으면 학년·반·별명까지 미리 채운다.
async function handleForms(db, url, request) {
  const slug = safeDecode(url.searchParams.get("school") || "");
  if (!slug) return html("학교를 찾을 수 없습니다.", 404);
  const school = await db.prepare("SELECT id, name, slug FROM schools WHERE slug = ?").bind(slug).first();
  if (!school) return html("학교를 찾을 수 없습니다.", 404);

  // 자녀 미리채움 — 로그인(계정) 상태이고 이 학교에 등록된 자녀가 있을 때만.
  let child = null;
  const account = await getAccount(db, request);
  if (account) {
    const ownerToken = getCookie(request, "owner_token");
    child = await db
      .prepare("SELECT nickname, grade, class_name FROM children WHERE owner_token = ? AND school_id = ? ORDER BY created_at LIMIT 1")
      .bind(ownerToken, school.id)
      .first();
  }

  const type = (url.searchParams.get("type") || "").trim();
  if (!type) return html(formsListPage(school, child));
  const page = formPage(school, type, child);
  if (!page) return html("서식을 찾을 수 없습니다.", 404);
  return html(page);
}

// 잘못 인코딩된 URL(비정상 클라이언트·봇)에서 decodeURIComponent가 던지는 URIError를 흡수 → null.
function safeDecode(s) {
  try { return decodeURIComponent(s); } catch { return null; }
}
// 현재 요청의 로그인 계정 — **판정 기준은 accounts다**(2026-07-24, 회신24 §2).
// 예전엔 소셜 `users` 표를 봐서, 아이디/비번으로 가입한 계정(API 가입, users 행 없음)은
// 웹에 로그인해도 게이트를 못 넘고 탈퇴도 못 했다. 이제 로그인 수단과 무관하게 계정이 기준이다.
// (`users`는 admin 회원목록 표시용으로만 남는다 — 소셜 콜백이 계속 채운다.)
async function getAccount(db, request) {
  const t = getCookie(request, "owner_token");
  if (!t) return null;
  return accountForToken(db, t);
}

// owner_token → 화면 표시용 계정 요약. 반환 모양 {provider, nickname}은 기존 users 조회와
// 동일하게 유지한다 — 템플릿(mypage·login의 "○○로 로그인됨" 카드)이 그대로 읽는다.
// provider: kakao|google|naver|id. 최근 쓴 로그인 수단을 대표로 고른다.
async function accountForToken(db, ownerToken) {
  const row = await db
    .prepare(
      `SELECT a.display_name, m.kind
         FROM accounts a LEFT JOIN auth_methods m ON m.account_id = a.id
        WHERE a.owner_token = ? AND a.status = 'active'
        ORDER BY m.last_used_at DESC LIMIT 1`
    )
    .bind(ownerToken)
    .first();
  if (!row) return null;
  const provider = row.kind ? row.kind.replace(/^social_/, "").replace("id_password", "id") : "id";
  return { provider, nickname: row.display_name };
}
// 하이브리드 로그인 게이팅(2026-07-18) — 열람(홈·검색·학교상세·급식)은 비로그인 허용,
// 개인화(자녀 등록·마이페이지·시간표수정·일정·알림·결제)는 로그인 필수. 공용 PC 쿠키 공유로 남의 자녀 노출 방지.
function needsLogin(path) {
  if (path === "/mypage" || path.startsWith("/mypage/")) return true;
  if (path === "/records" || path.startsWith("/records/")) return true; // 자녀 사진 — 반드시 로그인 뒤
  if (path === "/activities" || path.startsWith("/activities/")) return true;
  if (path === "/register-child" || path === "/onboarding") return true;
  if (path === "/child/edit" || path === "/child/delete") return true;
  if (path === "/timetable/edit") return true;
  if (path.startsWith("/schedule/")) return true;   // /schedule/personal|settings|time (학교 탭 ?tab=schedule은 해당 없음)
  if (path.startsWith("/calendar/")) return true;
  if (path.startsWith("/community/")) return true;
  if (path === "/subscribe" || path === "/pay") return true;
  return false; // 급식/학교정보 열람·검색·오류신고·베타의견·SW·push API는 열어둔다
}

// /api/v1 공용 인증 해석 — api_records.js와 같은 규칙(쿠키 또는 Bearer)
function apiCookie(request, name) {
  const raw = request.headers.get("Cookie") || "";
  const hit = raw.split(";").map((v) => v.trim()).find((v) => v.startsWith(name + "="));
  return hit ? decodeURIComponent(hit.slice(name.length + 1)) : null;
}
const apiErrJson = (code) => new Response(
  JSON.stringify({ ok: false, error: { code, message: "권한이 없어요." } }),
  { status: 403, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
const resolveApiAuth = (request, db, env) => resolveAuth(request, db, env, apiCookie);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const db = env.DB;
    NEIS_KEY = env.NEIS_API_KEY || ""; // 온디맨드 NEIS 호출용 인증키(없으면 5건 제한)

    // 로컬 개발 전용 QA 도구 — 이중 게이트(DEV_TOOLS + localhost) 통과 시에만 살아난다. 배포엔 미노출.
    if (path === "/dev/login-as" && isDevToolsEnabled(env, url)) return handleDevLoginAs(url);

    /* ── 앱을 웹으로 — /app/ 밑에 www 를 그대로 (2026-08-12) ──
       같은 출처라 앱의 /api/v1 호출이 그대로 먹는다. 사이트 라우팅은 안 건드린다. */
    if (path === "/app") return Response.redirect(url.origin + "/app/", 301);
    if (path.startsWith("/app/") && env.APP_ASSETS) {
      const sub = path.slice("/app".length);
      const assetUrl = url.origin + (sub === "/" ? "/index.html" : sub);
      return env.APP_ASSETS.fetch(new Request(assetUrl, request));
    }

    // ── 앱 API (계약 v1) — HTML 라우트와 완전 분리. 웹은 안 깨진다.
    // 앱은 다른 출처(https://localhost 등)에서 부르므로 여기서 CORS를 한 번에 씌운다.
    // 개별 핸들러는 CORS를 몰라도 된다 — 응답에 헤더만 덧입힌다.
    if (path.startsWith("/api/v1/")) {
      const origin = corsOrigin(request.headers.get("Origin"));
      // 프리플라이트(OPTIONS)는 라우팅 전에 끝낸다. 본문도 인증도 없다.
      if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(origin) });

      /* 🔒 자녀 기기 토큰이 만질 수 있는 것 — **화이트리스트**. 여기 없으면 전부 막는다.
         ⚠ 2026-07-31 실측 사고: 이 검사가 `/api/v1/children/...` 갈래 **안에만** 있어서
            `/api/v1/me`(부모 이름·이메일·형제 목록)와 `POST /api/v1/orders`(결제 주문 생성)가
            자녀 토큰으로 그대로 통과했다. 관문을 라우팅 **앞**으로 올려 전 경로에 건다.
           ① 그 아이 대화(messages) ② 그 아이 준비물(supplies) — 읽기·추가만.
           ⚠ 삭제(DELETE)는 어디서도 안 연다 — 아이가 지우면 엄마가 모른다.
           ⚠ 소유권은 여기서 안 본다. api_life 가 childId 를 토큰의 아이와 대조한다. */
      const CHILD_OK = [
        /^\/api\/v1\/children\/\d+\/messages(\/seen)?\/?$/,
        /^\/api\/v1\/children\/\d+\/supplies\/?$/,
        /* 미션(2026-08-01) — 아이가 자기 폰에서 **오늘 것을 보고 해내는** 자리다.
           고르는 것(PUT)·확인(approve)·되돌리기(revert)는 부모 것이라 여기 안 넣는다.
           경로 모양만 보므로 «그 아이인지»는 api_mission 의 gate() 가 한 번 더 본다. */
        /^\/api\/v1\/children\/\d+\/missions\/?$/,
        /^\/api\/v1\/missions\/\d+\/(done|photo|skip)$/,
        /* 급식·시간표·학사일정 (2026-08-02). 자녀 화면이 «급식만 볼 수 있어요»라고 약속해 놓고
           실제로는 못 불렀다 — 그동안 화면에 뜬 급식은 그 폰에 남아 있던 **부모 캐시**였다.
           학교 정보는 교육청 공개 데이터고, 아이는 제 학교를 이미 안다. 읽기만 통과시킨다. */
        /^\/api\/v1\/schools\/(?!search)[^/]+(\/(meals|timetable|schedules|info))?\/?$/,
        // 자녀 앱 테마·급식 평가(2026-08-02) — 자녀 토큰 전용 경로 둘.
        // ⚠ 어제 prefs 를 넣었다고 보고했으나 실제 커밋엔 빠져 있었다(패치 오탐). 이번에 확실히.
        /^\/api\/v1\/child\/prefs\/?$/,
        /^\/api\/v1\/missions\/meal-rate\/?$/,
        /^\/api\/v1\/missions\/play-log\/?$/,
        /^\/api\/v1\/missions\/subject-log\/?$/,
        /* 🎮 미션 게임 (2026-08-08) — **아이 폰이 게임의 집이다.**
           여기 안 올리면 아이 토큰으로는 퀴즈도 상점도 안 열린다. 실측으로 잡았다:
           서버는 멀쩡한데 아이 화면에서만 «권한이 없어요»가 떴다.
           «그 아이인지»는 각 파일의 gate() 가 한 번 더 본다 — 여기서는 경로 모양만 본다. */
        /^\/api\/v1\/children\/\d+\/quiz(\/(retry|answer|stats))?\/?$/,
        /^\/api\/v1\/children\/\d+\/school-missions(\/bonus)?\/?$/,
        /^\/api\/v1\/children\/\d+\/mission-sets(\/bonus)?\/?$/,
        /* 상점 — 아이는 «바꾸기»만 한다(진열대 편집·티켓 처리는 부모 것이라 gate 가 막는다) */
        /^\/api\/v1\/children\/\d+\/store\/?$/,
        // ⚠ 실제 경로는 /store/{상품id}/buy 다. 한때 /store/buy 로 적어 두어
        //   아이가 «바꾸기»를 누르면 FORBIDDEN 이 났다(08-08 두 폰 실측으로 잡음).
        //   경로 모양을 손으로 적을 때는 **라우터의 정규식과 나란히 놓고** 확인할 것.
        //   ⚠ 블록 주석(/* … */) 안에 경로를 쓰지 말 것 — `**/buy` 의 `*/` 가 주석을 거기서 닫는다.
        /^\/api\/v1\/children\/\d+\/store\/[\w-]+\/buy\/?$/,
        // 🎲 리롤 — 아이가 누른다. 없으면 아이 폰에서만 「권한이 없어요」가 뜬다
  /^\/api\/v1\/children\/\d+\/missions\/reroll\/?$/,
  /^\/api\/v1\/children\/\d+\/rewards\/?$/,
        /* 2단계 검증 — 1차(아이가 냄)는 아이 것이다. 보너스(2차)는 부모 것이라 gate 가 막는다 */
        /^\/api\/v1\/children\/\d+\/verify\/?$/,
        /* ⚙️ 경제 설정 읽기 (2026-08-12) — 아이 화면도 「오늘 18/30」을 그려야 한다.
           읽기만 연다. **정하는 것(PUT /star-line)은 여기 없다** — 부모 것이고,
           그게 「무조건 통과」를 막는 유일한 손잡이라 아이가 쥐면 의미가 없다. */
        /^\/api\/v1\/children\/\d+\/econ\/?$/,
      ];
      let res = null;
      if (path === "/api/v1/auth/child-claim" && request.method === "POST") {
        // 아이 폰이 6자리 코드를 내고 자녀 전용 토큰을 받아간다. 아직 아무 자격이 없으니 인증을 안 건다.
        res = await claimInvite(request, db, env, signToken, authSecret, TOKEN_TTL);
        if (res) return withCors(res, origin);
      }
      {
        // 토큰이 있을 때만 본다(없으면 각 핸들러가 알아서 401을 준다)
        const gate = await resolveApiAuth(request, db, env);
        if (gate.role === "child" && (!CHILD_OK.some((re) => re.test(path)) || request.method === "DELETE")) {
          return withCors(apiErrJson("FORBIDDEN"), origin);
        }
      }
      if (path.startsWith("/api/v1/auth") || path === "/api/v1/me" || path.startsWith("/api/v1/me/")) res = await handleAuthApi(request, db, env, url);
      else if (path === "/api/v1/plans" || path.startsWith("/api/v1/orders") || path.startsWith("/api/v1/admin/orders")
               || path === "/api/v1/billing/verify")
        res = await handleOrdersApi(request, db, env, url, checkBasicAuth(request, env));
      else if (path.startsWith("/api/v1/inquiries")) res = await handleSupportApi(request, db, env, url);
      else if (path === "/api/v1/missions/subject-log" && request.method === "POST") {
        const a = await resolveApiAuth(request, db, env);
        const { subjectLog } = await import("./api_mission.js");
        res = await subjectLog(request, db, a);
      }
      else if (path === "/api/v1/missions/play-log" && request.method === "POST") {
        const a = await resolveApiAuth(request, db, env);
        const { playLog } = await import("./api_mission.js");
        res = await playLog(request, db, a);
      }
      else if (path === "/api/v1/missions/meal-rate" && request.method === "POST") {
        // 급식 평가(0802-3) — 자녀 토큰 검증은 관문(CHILD_OK)이 이미 통과시킨 뒤다
        const a = await resolveApiAuth(request, db, env);
        const { mealRate } = await import("./api_mission.js");
        res = await mealRate(request, db, a);
      }
      else if (path === "/api/v1/missions" || path.match(/^\/api\/v1\/missions\/(\d+\/|U-)/)
               // 🔔 미션 알림 설정(2026-08-14) — 접두어 화이트리스트에 안 넣으면 HTML 404 로 샌다(아래 주석 참조)
               || path === "/api/v1/notify-prefs")
        res = await handleMissionApi(request, db, env, url);
      // 공지사항 읽기(2026-08-14) — 개인정보 없음, 로그인 불필요. 쓰기는 /admin/notices 뒤에 있다
      else if (path === "/api/v1/notices" && request.method === "GET") {
        const { results } = await db.prepare(
          "SELECT id, title, body, created_at FROM announcements WHERE active = 1 ORDER BY id DESC LIMIT 50").all();
        res = json({ ok: true, data: { items: results || [] } });
      }
      else if (path.startsWith("/api/v1/schools")) res = await handleSchoolsApi(request, db, env, url);
      // 별도장 상점·2단계 보상 (2026-08-07) — /children/* 밖에 있는 것들
      else if (path.startsWith("/api/v1/store/") || path.startsWith("/api/v1/rewards/") ||
               path.startsWith("/api/v1/verify/") || path.startsWith("/api/v1/templates/") ||
               // 아이 모드 PIN (2026-08-07) — ⚠ 위 `/api/v1/child/` 접두어와는 **다른 경로**다.
               //   하이픈이라 `child/` 에 안 걸린다. 여기 안 적으면 HTML 404 로 샌다.
               path === "/api/v1/child-mode" || path.startsWith("/api/v1/child-mode/")) {
        res = await handleRewardApi(request, db, env, url);
      }
      else if (path.startsWith("/api/v1/children") || path.startsWith("/api/v1/child/") || path.startsWith("/api/v1/records") ||
               path.startsWith("/api/v1/activities") || path.startsWith("/api/v1/documents") || path.startsWith("/api/v1/community") || path.startsWith("/api/v1/events") ||
               path.startsWith("/api/v1/supplies")) {
        // ⚠️ 이 목록은 **접두어 화이트리스트**다. api_life.js에 라우트를 새로 열어도
        //    여기 접두어를 안 넣으면 조용히 HTML 404로 새어나간다(2026-07-27 supplies에서 실측).
        // 자녀 토큰 차단은 **위 관문**에서 이미 끝났다(전 경로 공통).
        const a = await resolveApiAuth(request, db, env);
        // 미션이 먼저 — /children/{id}/missions 는 다른 데서 안 잡는다
        res = await handleMissionApi(request, db, env, url);
        // 상점·검증·칭찬·템플릿 (2026-08-07) — 역시 /children/{id}/* 를 나눠 쓴다
        if (!res) res = await handleRewardApi(request, db, env, url);
        // 데일리 퀴즈도 /children/{id}/* 를 나눠 쓴다 (2026-08-08)
        if (!res) res = await handleQuizApi(request, db, env, url);
        // 학교 미션 제공자 — 국내판에서만 끼운다(기획서 v2 §09)
        if (!res) res = await handleSchoolMissionApi(request, db, env, url);
        // 서류·대화·커뮤니티가 그다음(자녀 하위 경로를 공유). 자기 것이 아니면 null을 주고 넘긴다.
        if (!res) res = await handleLifeApi(request, db, env, url, a);
        if (!res) res = await handleRecordsApi(request, db, env, url);
      }
      if (res) return withCors(res, origin);
      // 어느 것도 아니면 아래 HTML 라우트로 흘려보낸다(지금까지와 같은 동작)
    }

    // 소셜 로그인(카카오·구글·네이버)
    if (path === "/login") return handleLoginPage(request, db, env);
    if (path === "/logout") return handleLogout();
    const authMatch = path.match(/^\/auth\/(kakao|google|naver)(\/callback)?$/);
    if (authMatch) {
      return authMatch[2]
        ? handleAuthCallback(authMatch[1], request, db, env, url)
        : handleAuthStart(authMatch[1], env, url);
    }
    if (path === "/dev/logout" && isDevToolsEnabled(env, url)) return handleDevLogout();

    // 로그인 게이트 — 개인화 경로는 로그인(소셜 계정) 필수. 비로그인이면 /login으로.
    // GET이면 login_next 쿠키에 목적지를 담아 로그인 후 원래 화면으로 복귀시킨다.
    if (needsLogin(path)) {
      const acct = await getAccount(db, request);
      if (!acct) {
        const resp = redirect("/login");
        if (request.method === "GET") {
          resp.headers.append("Set-Cookie", `login_next=${encodeURIComponent(path + url.search)}; Path=/; Max-Age=600; HttpOnly; SameSite=Lax`);
        }
        return resp;
      }
    }

    if (path === "/") return html(homePage());
    if (path === "/search") return handleSearch(db, url);
    if (path === "/register-child") return handleRegisterChild(request, db, url, env);
    if (path === "/onboarding") {
      const slug = url.searchParams.get("school");
      const school = slug ? await db.prepare("SELECT slug, name FROM schools WHERE slug = ?").bind(decodeURIComponent(slug)).first() : null;
      return html(onboardingPage(school));
    }
    if (path === "/child/edit") return handleChildEdit(request, db, url);
    if (path === "/timetable/edit") return handleTimetableEdit(request, db);
    if (path === "/schedule/personal") return handlePersonalSchedule(request, db);
    if (path === "/schedule/settings") return handleScheduleSettings(request, db);
    if (path === "/schedule/time") return handleScheduleTime(request, db);
    if (path === "/report") return handleReport(request, db, url);
    if (path === "/feedback") return handleFeedback(request, db);
    if (path === "/api/school-warm") return handleSchoolWarm(request, db, url);
    if (path === "/calendar/event/add") return handleCalendarEventAdd(request, db);
    if (path === "/calendar/event/delete") return handleCalendarEventDelete(request, db);
    if (path === "/calendar/event/edit") return handleCalendarEventEdit(request, db);
    if (path === "/community/post") return handleCommunityPost(request, db);
    if (path === "/community/nickname") return handleCommunityNickname(request, db);
    if (path === "/community/report") return handleCommunityReport(request, db);
    if (path === "/subscribe") return handleSubscribe(request, db);
    if (path === "/pay") return handlePay(request, db);
    if (path === "/about") return html(aboutPage());
    if (path === "/terms") return html(termsPage());
    if (path === "/privacy") return html(privacyPage());
    // 계정 삭제 안내 — **구글 플레이 필수**. 스토어 「데이터 보안」 양식에 이 URL 을 적는다.
    // 별칭 둘 다 받는다(심사자가 흔히 쓰는 경로라 어느 쪽으로 들어와도 열려야 한다).
    if (path === "/account-delete" || path === "/delete-account") return html(accountDeletePage());
    // 스토어 등록에 넣을 **공개** 지원 URL. 로그인 뒤에 숨은 화면은 심사에 못 쓴다.
    if (path === "/help" || path === "/support" || path === "/faq") return html(helpPage());
    // 학교 표준 서식(초등) — 학교명(+등록 자녀 학년·반) 채운 인쇄/PDF 서식. 로그인 없이도 열람 가능.
    if (path === "/forms") return handleForms(db, url, request);

    // 공유 미리보기 이미지(OG) — 카톡·페북 등이 og:image로 가져간다. 정적이라 길게 캐시.
    if (path === "/og.png") {
      const bin = Uint8Array.from(atob(OG_PNG_BASE64), (c) => c.charCodeAt(0));
      return new Response(bin, {
        headers: { "Content-Type": "image/png", "Cache-Control": "public, max-age=604800, immutable" },
      });
    }
    // 브랜드 아이콘 — 브라우저 탭(파비콘) / iOS 홈화면·PWA 설치 아이콘.
    if (path === "/favicon.ico") {
      const bin = Uint8Array.from(atob(FAVICON_ICO_BASE64), (c) => c.charCodeAt(0));
      return new Response(bin, {
        headers: { "Content-Type": "image/x-icon", "Cache-Control": "public, max-age=604800, immutable" },
      });
    }
    if (path === "/icon-512.png") {
      const bin = Uint8Array.from(atob(ICON512_BASE64), (c) => c.charCodeAt(0));
      return new Response(bin, {
        headers: { "Content-Type": "image/png", "Cache-Control": "public, max-age=604800, immutable" },
      });
    }
    // 사이트맵 — 학교 상세 12,563개를 검색봇이 찾도록. robots.txt에서 위치를 알린다. 하루 캐시.
    if (path === "/sitemap.xml") {
      const { results } = await db.prepare("SELECT slug FROM schools ORDER BY id").all();
      const xmlEsc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      const loc = (p) => `<url><loc>${xmlEsc(url.origin + p)}</loc></url>`;
      const statics = ["/", "/about", "/terms", "/privacy"].map(loc).join("");
      const schools = results.map((s) => loc(`/school/${encodeURIComponent(s.slug)}/`)).join("");
      const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${statics}${schools}</urlset>`;
      return new Response(xml, {
        headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=86400" },
      });
    }
    if (path === "/manifest.json") return manifest(url.origin);
    if (path === "/robots.txt") {
      const indexable = env.SITE_INDEXABLE === "true";
      // /mypage/, /api/, /admin은 SITE_INDEXABLE과 무관하게 항상 색인 차단(비공개 라우트).
      // /forms는 학교×4종 = 5만 개 유사 페이지라 색인되면 "얇은 중복 콘텐츠"로 SEO에 해로워 항상 차단.
      const base = indexable ? "User-agent: *\nAllow: /\n" : "User-agent: *\nDisallow: /\n";
      // ?tab= 변형 주소는 크롤 금지 — 급식·시간표 탭은 온디맨드라 크롤러가 열 때마다 NEIS를 호출한다.
      // 12,563개교를 봇이 돌면 NEIS 대량 호출(키·IP 차단 위험) + D1 용량 증가. 학교 기본 페이지만 수집시킨다.
      // 개학 후 급식을 전국 적재하면(=DB에 이미 존재) 그때 이 줄을 빼서 급식 색인을 열면 된다.
      // /app 은 부모앱 웹 버전(2026-08-12) — 검색에 나올 물건이 아니다. 항상 차단.
      const blocks = "Disallow: /mypage/\nDisallow: /api/\nDisallow: /admin\nDisallow: /forms\nDisallow: /login\nDisallow: /subscribe\nDisallow: /pay\nDisallow: /app\nDisallow: /*?tab=\n";
      const sitemap = indexable ? `\nSitemap: ${url.origin}/sitemap.xml\n` : "";
      return new Response(`${base}${blocks}${sitemap}`, {
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    const schoolMatch = path.match(/^\/school\/([^/]+)\/?$/);
    if (schoolMatch) {
      const sl = safeDecode(schoolMatch[1]);
      if (sl === null) return html("페이지를 찾을 수 없습니다.", 404); // 잘못 인코딩된 URL(봇 등) → 500 대신 404
      return handleSchoolDetail(db, sl, url, request, env);
    }

    const kinderMatch = path.match(/^\/kinder\/([^/]+)\/?$/);
    if (kinderMatch) {
      const kl = safeDecode(kinderMatch[1]);
      if (kl === null) return html("페이지를 찾을 수 없습니다.", 404);
      return handleKinderDetail(db, kl);
    }

    if (path === "/mypage" || path === "/mypage/") return handleMypage(request, db, env);
    if (path === "/mypage/children") return handleChildrenManage(request, db);
    if (path === "/mypage/purge") return handlePurgeAll(request, db, env);
    // 기록(블록1) — 업로드·삭제·이미지 서빙. 전부 owner_token 소유권 검증을 거친다.
    // 블록1 자녀기록 — FEATURE_RECORDS가 "true"가 아니면 **라우트 자체를 죽인다**(404).
    // 운영에는 코드가 올라가되 사용자에겐 없는 것처럼 보이게 하는 게 목적(2026-07-19 사장님 지시).
    // 메뉴만 숨기고 라우트를 열어두면 URL을 직접 치는 사람에게 미완성 화면이 노출된다.
    if (path === "/records" || path.startsWith("/records/") || path === "/activities" || path.startsWith("/activities/")) {
      if (!featureRecords(env)) return html("페이지를 찾을 수 없습니다.", 404);
    }
    if (path === "/records") return handleRecordsPage(request, db, env);
    if (path === "/activities") return handleActivities(request, db, env);
    if (path === "/activities/save") return handleActivitySave(request, db, env);
    if (path === "/activities/delete") return handleActivityDelete(request, db, env);
    if (path === "/records/upload") return handleRecordUpload(request, db, env);
    if (path === "/records/delete") return handleRecordDelete(request, db, env);
    const recImg = path.match(/^\/records\/(\d+)\/img(\/t)?$/);
    if (recImg) return handleRecordImage(request, db, env, recImg[1], !!recImg[2]);
    if (path === "/child/delete") return handleChildDelete(request, db, env);
    if (path === "/mypage/payments") return handleMypagePayments(request, db);
    if (path === "/mypage/notifications") return handleMypageNotifications(request, db, env);
    if (path === "/sw.js") return new Response(SERVICE_WORKER_JS, { headers: { "Content-Type": "application/javascript", "Cache-Control": "no-cache" } });
    if (path === "/api/push/subscribe") return handlePushSubscribe(request, db);
    if (path === "/api/push/latest") return handlePushLatest(request, db);
    if (path === "/api/push/test") return handlePushTest(request, db, env);

    const childTodayMatch = path.match(/^\/api\/children\/(\d+)\/today\/?$/);
    if (childTodayMatch) return handleChildToday(db, env, childTodayMatch[1]);

    // 관리자 페이지 — 전부 Basic Auth 필수(§관리자페이지 지시서).
    if (path.startsWith("/admin")) {
      if (!checkBasicAuth(request, env)) return unauthorized();

      if (path === "/admin" || path === "/admin/") return handleAdminMonitor(db);
      if (path === "/admin/banners") return handleAdminBanners(request, db);
      // 공지사항 작성 (2026-08-14) — 업데이트·이벤트 공지. 쓰면 앱에 배포 없이 뜬다
      if (path === "/admin/notices") return handleAdminNotices(request, db);
      { const m2 = path.match(/^\/admin\/notices\/(\d+)\/toggle$/);
        if (m2 && request.method === "POST") {
          await db.prepare("UPDATE announcements SET active = 1 - active WHERE id = ?").bind(m2[1]).run();
          return redirect("/admin/notices");
        } }

      const bannerToggleMatch = path.match(/^\/admin\/banners\/(\d+)\/toggle$/);
      if (bannerToggleMatch && request.method === "POST")
        return handleAdminBannerToggle(db, bannerToggleMatch[1]);

      const bannerDeleteMatch = path.match(/^\/admin\/banners\/(\d+)\/delete$/);
      if (bannerDeleteMatch && request.method === "POST")
        return handleAdminBannerDelete(db, bannerDeleteMatch[1]);

      const bannerEditMatch = path.match(/^\/admin\/banners\/(\d+)\/edit$/);
      if (bannerEditMatch && request.method === "POST")
        return handleAdminBannerEdit(request, db, bannerEditMatch[1]);

      if (path === "/admin/correct" && request.method === "GET") return handleAdminCorrect(request, db, url);
      if (path === "/admin/correct/undo" && request.method === "POST") return handleAdminCorrectUndo(request, db);

      const correctMealMatch = path.match(/^\/admin\/correct\/meals\/(\d+)$/);
      if (correctMealMatch && request.method === "POST")
        return handleAdminCorrectMeal(request, db, correctMealMatch[1]);

      const correctScheduleMatch = path.match(/^\/admin\/correct\/schedules\/(\d+)$/);
      if (correctScheduleMatch && request.method === "POST")
        return handleAdminCorrectSchedule(request, db, correctScheduleMatch[1]);

      if (path === "/admin/reports") return handleAdminReports(request, db);
      const reportResolveMatch = path.match(/^\/admin\/reports\/(\d+)\/resolve$/);
      if (reportResolveMatch && request.method === "POST")
        return handleAdminResolveReport(db, reportResolveMatch[1]);

      if (path === "/admin/feedback") return handleAdminFeedback(request, db);
      const feedbackResolveMatch = path.match(/^\/admin\/feedback\/(\d+)\/resolve$/);
      if (feedbackResolveMatch && request.method === "POST")
        return handleAdminResolveFeedback(db, feedbackResolveMatch[1]);

      if (path === "/admin/school-search") return handleAdminSchoolSearch(db, url);

      if (path === "/admin/members") return handleAdminMembers(db, request, url);
      if (path === "/admin/members/subscriber" && request.method === "POST")
        return handleAdminSubscriber(request);
      if (path === "/admin/members/dev-account" && request.method === "POST")
        return handleAdminDevAccount(request, db, env);
      if (path === "/admin/members/dev-seed" && request.method === "POST")
        return handleAdminDevSeed(request, db, env);
      if (path === "/admin/members/add-test-child" && request.method === "POST")
        return handleAdminAddTestChild(request, db);
      if (path === "/admin/members/token-delete" && request.method === "POST") {
        // 되돌릴 수 없는 삭제 — 무엇을 지웠는지 남긴다
        const f = await request.clone().formData().catch(() => null);
        await audit(db, request, "member_delete", { kind: "account",
          id: f ? String(f.get("owner_token") || "") : null, detail: "부모의 자녀 전체 삭제" });
        return handleAdminMemberTokenDelete(request, db, env);
      }
      const childEditMatch = path.match(/^\/admin\/members\/(\d+)\/edit$/);
      if (childEditMatch && request.method === "POST") return handleAdminMemberEditChild(request, db, childEditMatch[1]);
      const childDeleteMatch = path.match(/^\/admin\/members\/(\d+)\/delete$/);
      if (childDeleteMatch && request.method === "POST") {
        await audit(db, request, "child_delete", { kind: "child", id: childDeleteMatch[1], detail: "자녀 삭제" });
        return handleAdminDeleteChild(db, childDeleteMatch[1], env);
      }
      if (path === "/admin/members/adjust" && request.method === "POST") return handleAdminAdjustExpiry(request, db);

      if (path === "/admin/community") return handleAdminCommunity(db);
      const flagRestore = path.match(/^\/admin\/community\/(\d+)\/restore$/);
      if (flagRestore && request.method === "POST") {
        // 신고 기록을 지우고 다시 보이게 한다 — 안 지우면 다음 신고 하나에 또 내려간다
        await db.batch([
          db.prepare("DELETE FROM community_reports WHERE post_id = ?").bind(flagRestore[1]),
          db.prepare("UPDATE community_posts SET hidden = 0, report_count = 0 WHERE id = ?").bind(flagRestore[1]),
        ]);
        return redirect("/admin/community");
      }
      const flagDrop = path.match(/^\/admin\/community\/(\d+)\/delete$/);
      if (flagDrop && request.method === "POST") {
        await db.batch([
          db.prepare("DELETE FROM community_reports WHERE post_id = ?").bind(flagDrop[1]),
          db.prepare("DELETE FROM community_posts WHERE id = ?").bind(flagDrop[1]),
        ]);
        return redirect("/admin/community");
      }
      if (path === "/admin/community/ban" && request.method === "POST") {
        const form = await request.formData();
        const tok = (form.get("owner_token") || "").toString();
        const days = parseInt((form.get("days") || "7").toString(), 10) || 7;
        if (tok) {
          const until = new Date(Date.now() + days * 86400000).toISOString();
          await db.prepare(
            `INSERT INTO community_bans (owner_token, until, reason, created_at) VALUES (?, ?, ?, ?)
             ON CONFLICT(owner_token) DO UPDATE SET until = excluded.until, created_at = excluded.created_at`
          ).bind(tok, until, `신고 누적 · ${days}일`, new Date().toISOString()).run();
        }
        return redirect("/admin/community");
      }
      if (path === "/admin/community/unban" && request.method === "POST") {
        const form = await request.formData();
        const tok = (form.get("owner_token") || "").toString();
        if (tok) await db.prepare("DELETE FROM community_bans WHERE owner_token = ?").bind(tok).run();
        return redirect("/admin/community");
      }

      if (path === "/admin/inquiries") return handleAdminInquiries(db, url);
      const inqAnswerMatch = path.match(/^\/admin\/inquiries\/(\d+)\/answer$/);
      if (inqAnswerMatch && request.method === "POST") {
        const form = await request.formData();
        await answerInquiry(db, inqAnswerMatch[1], (form.get("answer") || "").toString());
        return redirect("/admin/inquiries");
      }
      const inqCloseMatch = path.match(/^\/admin\/inquiries\/(\d+)\/close$/);
      if (inqCloseMatch && request.method === "POST") {
        await closeInquiry(db, inqCloseMatch[1]);
        return redirect("/admin/inquiries");
      }

      if (path === "/admin/audit") return handleAdminAudit(db, url);
      if (path === "/admin/orders") return handleAdminOrders(db, url);
      /* ⚠ 돈이 오가는 자리 — **누가 확인했는지 남긴다.** 남기지 않으면
         나중에 «이 주문은 왜 켜졌지?» 를 아무도 답할 수 없다. */
      const ordConfirmMatch = path.match(/^\/admin\/orders\/(\d+)\/confirm$/);
      if (ordConfirmMatch && request.method === "POST") {
        const r = await confirmOrderByAdmin(db, ordConfirmMatch[1]);
        await audit(db, request, "order_confirm", { kind: "order", id: ordConfirmMatch[1],
          detail: r && r.ok ? `이용권 ${r.expires} 까지` : `실패(${r && r.reason})` });
        return redirect("/admin/orders");
      }
      const ordCancelMatch = path.match(/^\/admin\/orders\/(\d+)\/cancel$/);
      if (ordCancelMatch && request.method === "POST") {
        const r = await cancelOrderByAdmin(db, ordCancelMatch[1]);
        await audit(db, request, "order_cancel", { kind: "order", id: ordCancelMatch[1],
          detail: r && r.ok ? "취소" : `실패(${r && r.reason})` });
        return redirect("/admin/orders");
      }

      if (path === "/admin/payments") return handleAdminPayments(request, db, url);
      if (path === "/admin/data" && request.method === "GET") return handleAdminData(request, db, url);
      if (path === "/admin/data/save" && request.method === "POST") return handleAdminDataSave(request, db);
      if (path === "/admin/data/del" && request.method === "POST") return handleAdminDataDelete(request, db);
      const refundMatch = path.match(/^\/admin\/payments\/(\d+)\/refund$/);
      if (refundMatch && request.method === "POST") return handleAdminRefund(db, refundMatch[1]);
      const payEditMatch = path.match(/^\/admin\/payments\/(\d+)\/edit$/);
      if (payEditMatch && request.method === "POST") return handleAdminPaymentEdit(request, db, payEditMatch[1]);
      const payDeleteMatch = path.match(/^\/admin\/payments\/(\d+)\/delete$/);
      if (payDeleteMatch && request.method === "POST") return handleAdminPaymentDelete(db, payDeleteMatch[1]);

      return html("페이지를 찾을 수 없습니다.", 404);
    }

    return html("페이지를 찾을 수 없습니다.", 404);
  },

  // 매일 아침(Cron) 알림 발송 — 신청(enabled=1)한 모든 구독에 무페이로드 푸시.
  // 매분 실행(wrangler.toml crons) — ① 알림 시각이 된 "내 일정" 웹푸시 발송, ② 학사일정 롤링 자동 갱신.
  async scheduled(event, env, ctx) {
    const db = env.DB;
    if (!db) return;
    NEIS_KEY = env.NEIS_API_KEY || ""; // 크론 경로에도 필수 — 없으면 NEIS가 5건만 줘 갱신이 데이터를 망친다.
    const now = new Date().toISOString();

    /* 미션 — ①다음날 오전 8시가 지난 「확인 대기」를 묻지도 따지지도 않고 승인한다.
       이 한 줄이 아이에게 «내가 한 일은 반드시 보상받는다»를 증명한다 — 기다림은 여기서 배워진다.
       ②7일 지난 미션 사진을 지운다(서랍과 달리 임시 증거다).
       실패해도 다른 크론 일을 막지 않게 따로 감싼다. */
    try { await missionCron(db, env); } catch (e) { /* 다음 분에 다시 한다 */ }

    // ⓪ 개학일 도래 자녀에게 체험 7일 일괄 재부여 (연착륙 — docs/회신.md Q2=A-2, 학교별 개별 전환)
    //    개학 첫 주가 급식·시간표의 가치를 가장 크게 체감하는 때라, 그 주를 쓰게 한 뒤 잠금이 오도록 한다.
    //    · 대상: 오늘이 소속 학교 개학일이고, 아직 재부여 안 됐고(regranted_at IS NULL), 실제 자녀(is_test=0)
    //    · **1회성 보장**: regranted_at을 같은 UPDATE에서 찍는다. 이미 찍힌 자녀는 다음 크론에서 제외되므로
    //      매분 실행돼도 만료일이 계속 밀리지 않는다(이게 없으면 영원히 안 잠긴다).
    //    · free_trials의 "계정당 1회" 차단은 이 배치에 한해 무시한다(기존 결정).
    //    · 크론이 하루 놓쳐도 조건이 `<= 오늘`이라 다음 실행에서 따라잡는다.
    try {
      const today = ymd();
      const expiry = new Date(Date.now() + TRIAL_DAYS * 86400000).toISOString();
      await db
        .prepare(
          `UPDATE children SET trial_expires_at = ?, regranted_at = ?
           WHERE is_test = 0 AND regranted_at IS NULL
             AND school_id IN (SELECT id FROM schools WHERE COALESCE(sem2_start, ?) <= ?)`
        )
        .bind(expiry, now, SEM2_FALLBACK, today)
        .run();
    } catch (e) {
      // 재부여 실패가 아래 알림·갱신을 막지 않게 삼킨다. 다음 크론에서 재시도된다.
    }

    /* ⓪-2 탈퇴 유예 만료 파기 (2026-07-31 방침: 탈퇴 후 3개월 보존, 이후 파기)
       DELETE /me 는 잠그기만 하고, 여기서 90일 지난 계정을 단일 파기 경로(withdrawAccount)로 지운다.
       한 번에 몇 건만 — R2 사진 삭제가 섞여 있어 크론 한 번에 몰아 지우면 시간을 다 쓴다. 매분 도니 밀리지 않는다. */
    try {
      const cutoff = new Date(Date.now() - 90 * 86400000).toISOString();
      const { results: expired } = await db.prepare(
        "SELECT id, owner_token FROM accounts WHERE status='withdrawn_pending' AND withdrawn_at <= ? LIMIT 3"
      ).bind(cutoff).all();
      for (const a of expired) {
        const acc = await db.prepare("SELECT * FROM accounts WHERE id=?").bind(a.id).first();
        await withdrawAccount(db, env, a.owner_token, acc);   // 실패 시 다음 크론이 다시 집는다(status가 안 바뀌므로)
      }
    } catch (e) { /* 다음 크론에서 재시도 */ }

    // ① 일정 알림 발송 — VAPID 키가 있을 때만(없어도 ② 갱신은 계속 돈다).
    if (env.VAPID_PRIVATE) {
      // 알림 시각이 지났고(remind_at<=now) 아직 안 보낸 일정 × 알림 켠 소유자의 구독. 각 (일정×구독) 1행.
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
      // 발송된 일정은 한 번만 가도록 플래그.
      for (const evId of sentEvents) {
        await db.prepare("UPDATE personal_events SET remind_sent = 1 WHERE id = ?").bind(evId).run();
      }
    }

    /* ②-0 **우리 아이 학교 먼저** — 급식·학사일정·시간표를 자동으로 받아 둔다(2026-08-13).
       전국 롤링(②)보다 앞에 둔다. 사용자가 앱을 열기 전에 이미 채워져 있어야
       홈의 「오늘 급식」과 알림이 개학 첫날부터 맞는다. */
    try { await rollChildSchoolsRefresh(db, todayYmd()); } catch { /* 다음 분에 재시도 */ }

    // ② 학사일정 롤링 갱신 — 30일 지난 학교 3곳/분. 전국 1바퀴 ≈ 3일, 평소엔 대상 0곳(호출 없음).
    try { await rollSchedulesRefresh(db, todayYmd()); } catch { /* 다음 분에 재시도 */ }
  },
};

// ================= 블록1: 기록 업로드 · 조회 =================
// 설계 정본: docs/화면설계.md 3~5절. 지시서 v4 1-2(상한)·4절(시기추정)·5절(보안).

// 학년 정수 코드(v4 1-12): 초1~6=1~6, 중1~3=7~9, 고1~3=10~12, 유치원 0 예약.
// 학교급이 다른 형제의 기록이 한 테이블에 섞여도 "3"이 초3인지 중3인지 구분되게 하려는 것.
// ⚠️ schoolYearOf()라는 이름은 이미 있고 뜻이 전혀 다르다(NEIS 학년도 "2026") — 절대 재사용 금지.
const GRADE_BASE = { "초등학교": 0, "중학교": 6, "고등학교": 9, "유치원": -1 };
function gradeCodeOf(schoolKind, grade) {
  const base = GRADE_BASE[schoolKind];
  const g = parseInt(grade, 10);
  if (base == null || !(g >= 1)) return null; // 모르면 null — 0으로 뭉개지 않는다(0은 유치원 예약값)
  if (base === -1) return 0;
  return base + g;
}
function gradeLabelOf(code) {
  if (code === 0) return "유치원";
  if (code <= 6) return `초${code}`;
  if (code <= 9) return `중${code - 6}`;
  return `고${code - 9}`;
}
// 업로드 시점 → 학기 추정(v4 4절). 3~8월=1학기, 9~2월=2학기.
// 1~2월이 "직전 학년도"인 이유: 한국 학년도는 3월 시작이라 겨울방학 아이는 아직 진급 전이다.
// 즉 달력 연도만 하나 줄고 **학년 코드는 그대로**다. 여기서 코드를 빼면 실제와 어긋난다.
function estimateSemester(today = todayYmd()) {
  const mo = +String(today).slice(4, 6);
  return (mo >= 3 && mo <= 8) ? 1 : 2;
}

const RECORD_CATEGORIES = ["award", "report_card", "grade_sheet", "certificate", "activity", "other"];
const CATEGORY_KO = {
  award: "상장", report_card: "통지표", grade_sheet: "성적표",
  certificate: "자격증", activity: "활동", other: "기타",
};
const UPLOAD_MAX_BYTES = 4 * 1024 * 1024; // 서버 최종 방어선(브라우저 리사이즈 실패 대비)
const UPLOAD_MAX_FILES = 10;
const UPLOAD_MIME = ["image/jpeg", "image/png", "image/webp"];

// 소유권 검증 — owner_token → child_id. 모든 기록 경로가 이걸 먼저 통과한다.
// 자녀 정보에 학교급이 필요해 schools를 조인한다(학년 코드 계산용).
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

// 기록 이미지 서빙 — R2는 비공개 버킷이라 워커가 매 요청 소유권을 확인하고 스트리밍한다.
// URL 파라미터를 일부러 records.id(연번)로 둔다: UUID를 URL에 넣으면 "URL을 아는 사람 = 권한자"라는
// 잘못된 보안 모델이 생긴다. 실제 방어는 아래 SQL 한 줄이고, image_key의 UUID는 경로 추측 방지용일 뿐이다.
// 권한 없음도 **403이 아니라 404** — 그 기록의 존재 여부 자체를 숨긴다.
async function handleRecordImage(request, db, env, recordId, thumb) {
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return html("찾을 수 없습니다.", 404);
  const rec = await db
    .prepare(
      `SELECT r.image_key FROM records r JOIN children c ON c.id = r.child_id
       WHERE r.id = ? AND c.owner_token = ?`
    )
    .bind(recordId, ownerToken)
    .first();
  if (!rec || !rec.image_key) return html("찾을 수 없습니다.", 404);
  if (!env.RECORDS) return html("저장소를 사용할 수 없습니다.", 503);

  const key = thumb ? rec.image_key + "_t" : rec.image_key;
  let obj = await env.RECORDS.get(key);
  // 썸네일이 없는 기록(구버전/생성 실패)은 원본으로 폴백 — 깨진 칸을 보여주지 않는다.
  if (!obj && thumb) obj = await env.RECORDS.get(rec.image_key);
  if (!obj) return html("찾을 수 없습니다.", 404);

  return new Response(obj.body, {
    headers: {
      "Content-Type": obj.httpMetadata?.contentType || "image/jpeg",
      // private: 공용 캐시(CDN·프록시)에 남지 않게. 개인 사진이므로 브라우저 캐시만 허용.
      "Cache-Control": "private, max-age=86400",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

// 기록 업로드 — POST /records/upload
// 쓰기 순서: **R2 PUT → D1 INSERT**. 삭제(deleteChildCascade)와 같은 방향이고 이유도 같다 —
// 복구 가능한 쪽으로 실패시킨다. D1을 먼저 쓰면 타임라인에 영영 안 지워지는 깨진 칸이 남는다.
// 다중 업로드는 **장별 독립 처리**: 3장 중 2번째가 실패해도 1·3은 저장한다.
// 전부 롤백하면 사용자는 방금 고른 사진을 처음부터 다시 골라야 한다.
async function handleRecordUpload(request, db, env) {
  if (request.method !== "POST") return json({ ok: false, error: "method" }, 405);
  const ownerToken = getCookie(request, "owner_token");
  const form = await request.formData();
  const childId = (form.get("child_id") || "").toString().trim();
  const child = await ownedChild(db, ownerToken, childId);
  if (!child) return json({ ok: false, error: "forbidden" }, 403);
  if (!env.RECORDS) return json({ ok: false, error: "storage_unavailable" }, 503);

  const category = (form.get("category") || "").toString();
  if (!RECORD_CATEGORIES.includes(category)) return json({ ok: false, error: "category" }, 400);

  // 시기 — 사용자가 고른 값 우선, 없으면 자동 추정(v4 4절). 배치 전체에 같은 값을 적용한다(백필).
  const syRaw = parseInt((form.get("school_year") || "").toString(), 10);
  const semRaw = parseInt((form.get("semester") || "").toString(), 10);
  const schoolYear = Number.isFinite(syRaw) && syRaw >= 0 && syRaw <= 12 ? syRaw : gradeCodeOf(child.school_kind, child.grade);
  const semester = semRaw === 1 || semRaw === 2 ? semRaw : estimateSemester();
  if (schoolYear == null) return json({ ok: false, error: "grade_unknown" }, 400);

  const files = form.getAll("files").filter((f) => f && typeof f === "object" && f.size != null);
  const thumbs = form.getAll("files_t").filter((f) => f && typeof f === "object" && f.size != null);
  if (!files.length) return json({ ok: false, error: "no_files" }, 400);
  if (files.length > UPLOAD_MAX_FILES) return json({ ok: false, error: "too_many", max: UPLOAD_MAX_FILES }, 400);

  // 상한 — 개방 기간이면 유료와 동일 취급(자녀 학교 개학일 기준).
  const limit = maxRecordsFor(isSubscriber(request), isFreeOpenForSchool(child));
  const cnt = await db.prepare("SELECT COUNT(*) AS n FROM records WHERE child_id = ?").bind(child.id).first();
  const used = (cnt && cnt.n) || 0;
  const room = Math.max(0, limit - used);
  if (room <= 0) return json({ ok: false, error: "limit", limit, used }, 403);

  const nowIso = new Date().toISOString();
  const title = `${gradeLabelOf(schoolYear)} ${semester}학기 ${CATEGORY_KO[category]}`;
  const saved = [];
  const skipped = [];

  for (let i = 0; i < files.length && saved.length < room; i++) {
    const f = files[i];
    if (f.size > UPLOAD_MAX_BYTES) { skipped.push({ i, reason: "too_big" }); continue; }
    if (f.type && !UPLOAD_MIME.includes(f.type)) { skipped.push({ i, reason: "mime" }); continue; }

    // child_id를 키 접두사로 둔다 — 고아가 생겨도 list({prefix:'rec/17/'})로 자녀 단위 대조·청소가 된다.
    // 평평한 키였다면 DB 없이는 무엇이 무엇인지 영영 알 수 없다.
    const key = `rec/${child.id}/${crypto.randomUUID()}`;
    const thumbBlob = thumbs[i];
    let putOriginal = false, putThumb = false;
    try {
      await env.RECORDS.put(key, f.stream(), { httpMetadata: { contentType: f.type || "image/jpeg" } });
      putOriginal = true;
      if (thumbBlob && thumbBlob.size > 0 && thumbBlob.size <= UPLOAD_MAX_BYTES) {
        await env.RECORDS.put(key + "_t", thumbBlob.stream(), { httpMetadata: { contentType: thumbBlob.type || "image/jpeg" } });
        putThumb = true;
      }
      await db
        .prepare(
          `INSERT INTO records (child_id, category, school_year, semester, title, image_key, bytes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
        )
        .bind(child.id, category, schoolYear, semester, title, key, f.size, nowIso, nowIso)
        .run();
      saved.push(key);
    } catch (e) {
      // 보상 삭제 — R2엔 올라갔는데 D1이 실패한 경우 방금 올린 객체를 즉시 되돌린다.
      // 이게 없으면 사용자에게 보이지 않는 고아 이미지가 R2에 영구히 남는다.
      try {
        const undo = [];
        if (putOriginal) undo.push(key);
        if (putThumb) undo.push(key + "_t");
        if (undo.length) await env.RECORDS.delete(undo);
      } catch (_) { /* 보상마저 실패 — 고아 잔류. rec/{child_id}/ 대조로 나중에 청소 가능 */ }
      skipped.push({ i, reason: "save_failed" });
    }
  }

  const overflow = files.length - saved.length - skipped.length;
  return json({
    ok: saved.length > 0,
    saved: saved.length,
    skipped: skipped.length,
    overflow: overflow > 0 ? overflow : 0, // 상한에 걸려 아예 시도조차 못 한 장수
    limit, used: used + saved.length,
  });
}

// 기록 단건 삭제 — 실제 삭제는 data_children.deleteRecordAssets 하나만 탄다.
// 여기서 하는 일은 **소유권 확인까지**다(그 함수는 "이미 확인된 record만 받는다"가 계약).
// 순서·보상 규칙(R2 원본+파생 먼저 → D1 나중)은 그 파일에 한 벌만 있다 — 예전엔 이 자리에
// 같은 로직이 복사돼 있었고, 그게 삭제 경로가 두 벌이 되는 시작점이었다(2026-07-24 합류).
async function handleRecordDelete(request, db, env) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  const form = await request.formData();
  const id = (form.get("id") || "").toString().trim();
  const rec = await db
    .prepare(
      `SELECT r.id, r.image_key, r.child_id FROM records r JOIN children c ON c.id = r.child_id
       WHERE r.id = ? AND c.owner_token = ?`
    )
    .bind(id, ownerToken)
    .first();
  if (!rec) return json({ ok: false, error: "not_found" }, 404);
  // R2 삭제가 실패하면 D1을 지우지 않고 중단한다(고아 확정 방지) — 그 판단도 공용 함수 안에 있다.
  const r = await deleteRecordAssets(db, env, rec);
  if (!r.ok) return json({ ok: false, error: "storage" }, 500);
  return json({ ok: true });
}

// 기록 타임라인 — GET /records?child=<id>&cat=<category>&q=<검색어>
// 목업 ②. 학년·학기 섹션으로 묶어 최신이 위로 오게 정렬한다.
async function handleRecordsPage(request, db, env) {
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return redirect("/mypage");
  const url = new URL(request.url);

  const { results: kids } = await db
    .prepare(
      `SELECT c.*, s.name AS school_name, s.slug AS school_slug, s.school_kind, s.sem2_start
       FROM children c JOIN schools s ON s.id = c.school_id
       WHERE c.owner_token = ? ORDER BY c.created_at`
    )
    .bind(ownerToken)
    .all();
  if (!kids.length) {
    return html(noticePage("먼저 자녀를 등록해 주세요", "기록은 자녀별로 보관돼요. 홈에서 학교를 검색해 자녀를 먼저 등록해 주세요.", "/", "👶"));
  }

  const wantId = url.searchParams.get("child");
  const child = kids.find((k) => String(k.id) === wantId) || kids[0];
  const cat = url.searchParams.get("cat") || "";
  const q = (url.searchParams.get("q") || "").trim();

  // 실명은 identifiers에만 — 기록 화면에서만 조인해 표시한다(로드맵 절대규칙 ①).
  const ident = await db.prepare("SELECT name FROM identifiers WHERE child_id = ?").bind(child.id).first();

  let sql = `SELECT id, category, school_year, semester, title, note, created_at FROM records WHERE child_id = ?`;
  const binds = [child.id];
  if (RECORD_CATEGORIES.includes(cat)) { sql += " AND category = ?"; binds.push(cat); }
  if (q) { sql += " AND title LIKE ?"; binds.push(`%${q}%`); }
  sql += " ORDER BY school_year DESC, semester DESC, id DESC LIMIT 500";
  const { results: records } = await db.prepare(sql).bind(...binds).all();

  const limit = maxRecordsFor(isSubscriber(request), isFreeOpenForSchool(child));
  const total = await db.prepare("SELECT COUNT(*) AS n FROM records WHERE child_id = ?").bind(child.id).first();

  return html(recordsPage({
    kids, child, childName: ident ? ident.name : "",
    records, cat, q,
    used: (total && total.n) || 0, limit,
    defaultSemester: estimateSemester(),
    defaultSchoolYear: gradeCodeOf(child.school_kind, child.grade),
  }));
}

// ================= 방과후·활동 (블록1 ⑤) =================
// 유효기간(start_date~end_date)으로 방학 특강과 학기 정규 학원을 같은 구조에 담는다.
// 종료일이 지나면 주간 뷰·요약줄에서 자동으로 사라진다 — 사용자가 지울 필요가 없다.
const ACT_TYPES = ["academy", "afterschool", "activity"];

async function handleActivities(request, db, env) {
  const ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) return redirect("/mypage");
  const url = new URL(request.url);

  const { results: kids } = await db
    .prepare(
      `SELECT c.*, s.name AS school_name, s.slug AS school_slug, s.school_kind
       FROM children c JOIN schools s ON s.id = c.school_id
       WHERE c.owner_token = ? ORDER BY c.created_at`
    )
    .bind(ownerToken)
    .all();
  if (!kids.length) {
    return html(noticePage("먼저 자녀를 등록해 주세요", "방과후·활동 일정은 자녀별로 관리돼요. 홈에서 학교를 검색해 자녀를 먼저 등록해 주세요.", "/", "👶"));
  }
  const wantId = url.searchParams.get("child");
  const child = kids.find((k) => String(k.id) === wantId) || kids[0];

  // 유효기간 필터는 SQL에서, 요일 매칭은 JS에서 한다.
  // days_of_week가 CSV("1,3")라 SQL LIKE로 매칭하면 "1"이 "11"에도 걸린다. 자녀당 일정은 많아야 수십 개다.
  const today = todayYmd();
  const { results: acts } = await db
    .prepare(
      `SELECT * FROM activity_schedules
       WHERE child_id = ? AND start_date <= ? AND end_date >= ?
       ORDER BY start_time, id`
    )
    .bind(child.id, today, today)
    .all();

  return html(activitiesPage({ kids, child, acts, today }));
}

// 등록·수정 — POST /activities/save
async function handleActivitySave(request, db, env) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  const form = await request.formData();
  const childId = (form.get("child_id") || "").toString().trim();
  const child = await ownedChild(db, ownerToken, childId);
  if (!child) return json({ ok: false, error: "forbidden" }, 403);

  const id = (form.get("id") || "").toString().trim();
  const type = (form.get("type") || "").toString();
  const name = (form.get("name") || "").toString().trim().slice(0, 40);
  const days = form.getAll("days").map((d) => parseInt(d.toString(), 10)).filter((d) => d >= 1 && d <= 7);
  const st = (form.get("start_time") || "").toString().trim();
  const et = (form.get("end_time") || "").toString().trim();
  const sd = (form.get("start_date") || "").toString().replace(/-/g, "").trim();
  const ed = (form.get("end_date") || "").toString().replace(/-/g, "").trim();

  // 서버 검증 — 프론트 required만 믿으면 직접 POST로 우회된다.
  if (!ACT_TYPES.includes(type)) return json({ ok: false, error: "type" }, 400);
  if (!name) return json({ ok: false, error: "name" }, 400);
  if (!days.length) return json({ ok: false, error: "days" }, 400);
  if (!/^\d{2}:\d{2}$/.test(st) || !/^\d{2}:\d{2}$/.test(et)) return json({ ok: false, error: "time" }, 400);
  if (et <= st) return json({ ok: false, error: "time_order" }, 400);
  if (!/^\d{8}$/.test(sd) || !/^\d{8}$/.test(ed)) return json({ ok: false, error: "date" }, 400);
  if (ed < sd) return json({ ok: false, error: "date_order" }, 400);

  const nowIso = new Date().toISOString();
  const dow = days.sort((a, b) => a - b).join(",");
  if (id) {
    // 수정 — 소유 검증을 UPDATE 조건에 함께 박아 남의 일정을 못 고치게 한다.
    const r = await db
      .prepare(
        `UPDATE activity_schedules SET type=?, name=?, days_of_week=?, start_time=?, end_time=?,
         start_date=?, end_date=?, updated_at=? WHERE id=? AND child_id=?`
      )
      .bind(type, name, dow, st, et, sd, ed, nowIso, id, child.id)
      .run();
    if (!r.meta || !r.meta.changes) return json({ ok: false, error: "not_found" }, 404);
  } else {
    await db
      .prepare(
        `INSERT INTO activity_schedules (child_id, type, name, days_of_week, start_time, end_time, start_date, end_date, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .bind(child.id, type, name, dow, st, et, sd, ed, nowIso, nowIso)
      .run();
  }
  return redirect(`/activities?child=${encodeURIComponent(child.id)}`);
}

async function handleActivityDelete(request, db, env) {
  if (request.method !== "POST") return json({ ok: false }, 405);
  const ownerToken = getCookie(request, "owner_token");
  const form = await request.formData();
  const id = (form.get("id") || "").toString().trim();
  const row = await db
    .prepare(
      `SELECT a.id, a.child_id FROM activity_schedules a JOIN children c ON c.id = a.child_id
       WHERE a.id = ? AND c.owner_token = ?`
    )
    .bind(id, ownerToken)
    .first();
  if (!row) return json({ ok: false, error: "not_found" }, 404);
  await db.prepare("DELETE FROM activity_schedules WHERE id = ?").bind(row.id).run();
  return redirect(`/activities?child=${encodeURIComponent(row.child_id)}`);
}

// QA 데모 데이터 심기 — 지금 이 브라우저 계정에 자녀·기록·방과후를 한 번에 채운다.
//
// 왜 필요한가: dev-account는 쿠키가 없으면 매번 **새 빈 계정**을 만든다. 그래서 검수자가
// "로그인 상태로 만들기"를 누르면 데이터가 하나도 없는 계정으로 들어가고, 채워진 화면
// (3열 썸네일 그리드·주간 뷰 블록 배치)을 볼 수 없다. 실제로 검수 두 번이 그렇게 막혔다.
//
// admin Basic Auth + DEV_TOOLS 이중 잠금 뒤에만 존재한다(회신2 Q4 조건과 동일).
const DEMO_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAADwAAABQCAIAAAC5DqcCAAAAaklEQVR42u3PMQEAAAgDoC251a3g" +
  "TwjQk040ChQoUKBAgQIFChQoUKBAgQIFChQoUKBAgQIFChQoUKBAgQIFChQoUKBAgQIFChQoUKBA" +
  "gQIFChQoUKBAgQIFChQoUKBAgQIFChQoUKDgWwtVsAABBLxUIQAAAABJRU5ErkJggg==";

function b64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function handleAdminDevSeed(request, db, env) {
  if (env.DEV_TOOLS !== "true") return html("개발 도구가 꺼져 있습니다.", 404);
  if (request.method !== "POST") return html("잘못된 요청입니다.", 405);

  // 계정 생성 + 쿠키 설정 + 데이터 심기를 **한 함수에서** 처리한다.
  // 버튼이 둘로 나뉘어 있을 때 "로그인 상태로 만들기"가 심은 토큰과 "데모 심기"가 쓰는 토큰이
  // 어긋나 검수가 세 번 막혔다(회신15). 한 번에 끝내면 불일치 자체가 불가능하다.
  const setCookie = [];
  let ownerToken = getCookie(request, "owner_token");
  if (!ownerToken) {
    ownerToken = crypto.randomUUID();
    setCookie.push(`owner_token=${ownerToken}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax`);
  }
  // 로그인 게이트(needsLogin)는 users 행 유무로 판정한다 — 없으면 만들어 준다.
  {
    const nowIso0 = new Date().toISOString();
    const u = await db.prepare("SELECT id FROM users WHERE owner_token = ?").bind(ownerToken).first();
    if (!u) {
      await db
        .prepare("INSERT INTO users (provider, provider_uid, nickname, owner_token, created_at, last_login_at) VALUES ('kakao', ?, 'QA계정', ?, ?, ?)")
        .bind("qa-" + ownerToken.slice(0, 8), ownerToken, nowIso0, nowIso0)
        .run();
    } else {
      await db.prepare("UPDATE users SET last_login_at = ? WHERE owner_token = ?").bind(nowIso0, ownerToken).run();
    }
    // accounts에도 연결 — 이게 없으면 /api/v1/me가 401을 낸다(users만 있고 계정이 없어서).
    // QA 도구도 실제 로그인과 같은 상태를 만들어야 앱 API를 검증할 수 있다.
    try {
      await linkSocialAccount(db, "kakao", "qa-" + ownerToken.slice(0, 8), "QA계정", ownerToken);
    } catch (e) {
      console.error("[dev-seed] linkSocialAccount 실패:", e && e.message);
    }
  }

  const nowIso = new Date().toISOString();
  const today = todayYmd();

  // 1) 자녀 — 없으면 만든다. 이미 있으면 첫 자녀를 그대로 쓴다(중복 생성 방지).
  let child = await db
    .prepare("SELECT c.*, s.school_kind FROM children c JOIN schools s ON s.id=c.school_id WHERE c.owner_token = ? ORDER BY c.id LIMIT 1")
    .bind(ownerToken)
    .first();
  if (!child) {
    /* 데모용 자녀를 심을 학교. **특정 학교를 박지 않는다**(2026-08-03 지시) —
       데모는 «초등학교 아무 곳»이면 목적을 다한다. 이름은 아래 안내문에서 실제 심은 곳을 쓴다. */
    const school = await db.prepare(
      "SELECT id, name, school_kind FROM schools WHERE school_kind LIKE '초%' ORDER BY id LIMIT 1").first();
    if (!school) return html("기준 학교를 찾을 수 없습니다.", 500);
    const trial = new Date(Date.now() + 365 * 86400000).toISOString();
    const ins = await db
      .prepare(
        `INSERT INTO children (owner_token, school_id, grade, class_name, nickname, is_test, trial_expires_at, created_at, consent_at, consent_method)
         VALUES (?, ?, '3', '1', '첫째', 0, ?, ?, ?, 'checkbox')`
      )
      .bind(ownerToken, school.id, trial, nowIso, nowIso)
      .run();
    const cid = ins && ins.meta && ins.meta.last_row_id;
    await db.prepare("INSERT OR REPLACE INTO identifiers (child_id, name, created_at) VALUES (?, ?, ?)").bind(cid, "김서준", nowIso).run();
    child = await db.prepare("SELECT c.*, s.school_kind FROM children c JOIN schools s ON s.id=c.school_id WHERE c.id = ?").bind(cid).first();
  }

  // 2) 기록 — 여러 학년·학기·종류로 심어 타임라인 그룹핑과 필터가 눈에 보이게 한다.
  const have = await db.prepare("SELECT COUNT(*) AS n FROM records WHERE child_id = ?").bind(child.id).first();
  if (!have || !have.n) {
    const demo = [
      ["award", 3, 1], ["report_card", 3, 1], ["activity", 3, 1],
      ["award", 2, 2], ["grade_sheet", 2, 2],
      ["certificate", 2, 1], ["other", 2, 1],
    ];
    const bytes = b64ToBytes(DEMO_PNG_B64);
    for (const [cat, sy, sem] of demo) {
      const key = `rec/${child.id}/${crypto.randomUUID()}`;
      try {
        if (env.RECORDS) {
          await env.RECORDS.put(key, bytes, { httpMetadata: { contentType: "image/png" } });
          await env.RECORDS.put(key + "_t", bytes, { httpMetadata: { contentType: "image/png" } });
        }
        await db
          .prepare(
            `INSERT INTO records (child_id, category, school_year, semester, title, image_key, bytes, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
          )
          .bind(child.id, cat, sy, sem, `${gradeLabelOf(sy)} ${sem}학기 ${CATEGORY_KO[cat]}`, key, bytes.length, nowIso, nowIso)
          .run();
      } catch (e) { /* 한 건 실패해도 나머지는 심는다 */ }
    }
  }

  // 3) 방과후 — 요일·시간대를 흩어 배치해 주간 뷰 블록과 시간축 자동확장이 보이게 한다.
  const haveAct = await db.prepare("SELECT COUNT(*) AS n FROM activity_schedules WHERE child_id = ?").bind(child.id).first();
  if (!haveAct || !haveAct.n) {
    const end = new Date(Date.now() + 120 * 86400000).toISOString().slice(0, 10).replace(/-/g, "");
    const demoActs = [
      ["academy", "수학학원", "1,3", "16:00", "18:00"],
      ["activity", "축구교실", "6", "09:00", "11:00"],   // 기본 축(14~22시) 밖 → 자동확장 시연
      ["afterschool", "피아노", "5", "16:00", "17:00"],
      ["academy", "영어학원", "2,4", "17:00", "19:00"],
    ];
    for (const [type, name, dow, st, et] of demoActs) {
      await db
        .prepare(
          `INSERT INTO activity_schedules (child_id, type, name, days_of_week, start_time, end_time, start_date, end_date, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
        )
        .bind(child.id, type, name, dow, st, et, today, end, nowIso, nowIso)
        .run();
    }
  }

  const recCnt = await db.prepare("SELECT COUNT(*) AS n FROM records WHERE child_id = ?").bind(child.id).first();
  const actCnt = await db.prepare("SELECT COUNT(*) AS n FROM activity_schedules WHERE child_id = ?").bind(child.id).first();
  const resp = html(noticePage(
    "데모 데이터를 심었습니다",
    `자녀 <b>첫째</b>(김서준 3-1) · 기록 <b>${(recCnt && recCnt.n) || 0}건</b> · 방과후 <b>${(actCnt && actCnt.n) || 0}건</b><br>` +
    `<span style="font-size:11px;color:#8A94A6">이 브라우저 계정: ${ownerToken.slice(0, 8)}… (자녀 id ${child.id})</span><br><br>` +
    `<a href="/records" style="color:#2E7D5B;font-weight:800">기록 보기</a> · <a href="/activities" style="color:#2E7D5B;font-weight:800">방과후 보기</a>`,
    "/records",
    "🌱"
  ));
  for (const c of setCookie) resp.headers.append("Set-Cookie", c);
  return resp;
}
