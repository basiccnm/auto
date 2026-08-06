// ================= API 공통 모듈 (정본 §8 "API 게이트웨이" 블록) =================
// 계약: docs/API계약-v1.md §1
//
// 이 파일은 도메인에 안 묶인다 — 에듀싱크·올마나마·B2B가 같은 부품을 쓴다(정본 원칙1).
// 모든 /api/v1/* 응답은 반드시 여기를 거친다. 트랙마다 제각각 형식을 쓰면 앱이 분기를 못 한다.

// ── 응답 봉투 (계약 §1.2) ───────────────────────────────────────
// 목록도 배열이 아니라 { items, total, cursor } 객체로 감싼다.
// 나중에 페이지네이션을 넣을 때 앱을 안 고쳐도 되게 하려는 것.
export function apiOk(data, status = 200) {
  return new Response(JSON.stringify({ ok: true, data }), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

export function apiList(items, extra = {}) {
  return apiOk({ items, total: extra.total ?? items.length, cursor: extra.cursor ?? null, ...extra });
}

// ── 에러 코드 (계약 §1.3) ───────────────────────────────────────
// code는 앱이 분기하는 값 — **절대 바꾸지 않는다**. message는 사용자에게 그대로 보여줄 한국어.
// 내부 사정(SQL 오류, 스택)은 절대 message에 넣지 않는다.
export const ERR = {
  AUTH_REQUIRED:   [401, "로그인이 필요해요."],
  AUTH_EXPIRED:    [401, "로그인이 만료됐어요. 다시 로그인해 주세요."],
  AUTH_INVALID:    [401, "로그인 정보가 올바르지 않아요."],
  REAUTH_REQUIRED: [403, "본인 확인이 필요해요."],
  FORBIDDEN:       [403, "권한이 없어요."],
  NOT_FOUND:       [404, "찾을 수 없어요."],
  VALIDATION:      [400, "입력값을 확인해 주세요."],
  LIMIT_EXCEEDED:  [403, "한도를 초과했어요."],
  DUPLICATE:       [409, "이미 사용 중이에요."],
  PAYMENT_STATE:   [409, "주문 상태가 바뀌었어요. 새로고침해 주세요."],
  STORAGE:         [500, "저장 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요."],
  SERVER:          [500, "일시적인 오류예요. 잠시 후 다시 시도해 주세요."],
};

export function apiErr(code, extra = null, messageOverride = null) {
  const [status, defaultMsg] = ERR[code] || ERR.SERVER;
  const body = { ok: false, error: { code, message: messageOverride || defaultMsg } };
  if (extra) body.data = extra;
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

// ── CORS (2026-07-25, 앱 전환) ─────────────────────────────────
// 웹(HTML)은 같은 출처라 필요 없었지만, **앱은 다른 출처에서 API를 부른다.**
//   안드로이드 Capacitor 웹뷰 = https://localhost · iOS = capacitor://localhost
//   목업 브라우저            = http://localhost:8789
// `*`로 열지 않는다 — Authorization 헤더와 토큰이 오가므로 허용 목록만 통과시킨다.
// (`*`는 credentials 요청에서 브라우저가 아예 거부하기도 한다.)
const CORS_ALLOW = new Set([
  "https://localhost",          // Capacitor 안드로이드 웹뷰(기본)
  "http://localhost",           // 개발용 http 스킴으로 띄웠을 때(에뮬레이터 혼합콘텐츠 회피). 포트 없음에 주의
  "capacitor://localhost",      // Capacitor iOS 웹뷰
  "http://localhost:8789",      // 앱 목업 서버
  "http://localhost:8788",      // 로컬 워커에서 직접 열었을 때
]);

// 허용된 출처면 그 값을, 아니면 null(헤더를 아예 안 붙인다 = 브라우저가 막는다)
export function corsOrigin(origin) {
  return origin && CORS_ALLOW.has(origin) ? origin : null;
}

export function corsHeaders(origin) {
  if (!origin) return {};
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Credentials": "true",
    /* ⚠ PUT 이 빠져 있었다(2026-08-03 에뮬 실기에서 잡음). 앱은 https://localhost 에서 뜨고
       API 는 다른 출처라 **PUT 은 프리플라이트를 탄다** — 여기 없으면 브라우저가 막는다.
       그래서 자녀 테마 저장(PUT /child/prefs)과 부모의 「이걸로 주기」(PUT /children/{id}/missions)가
       조용히 실패하고 앱에는 「인터넷 연결을 확인해 주세요」만 떴다. 서버 로그에는 아무것도 안 남는다. */
    "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Reauth-Token",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

// 이미 만들어진 응답에 CORS 헤더만 얹는다(본문·상태는 그대로).
export function withCors(res, origin) {
  if (!origin) return res;
  const h = new Headers(res.headers);
  for (const [k, v] of Object.entries(corsHeaders(origin))) h.set(k, v);
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
}

// ── 공통 형식 변환 (계약 §1.5) ─────────────────────────────────
// 날짜는 YYYYMMDD 문자열로 유지한다 — ISO로 바꾸면 academic_schedules 219만 행을 전부 변환해야 하고,
// 문자열 비교만으로 범위 질의가 되는 이점을 잃는다.
// ⚠️ **KST 기준**이다. Workers는 UTC로 돌아서 그냥 toISOString()을 쓰면 한국 새벽 0~9시에
//    날짜가 하루 전으로 나온다(실측: UTC 07-23 22:36 = KST 07-24 07:36).
//    학교 데이터는 전부 한국 날짜 기준이라 UTC를 쓰면 급식·시간표가 하루씩 밀린다.
//    index.js의 todayYmd()와 같은 규칙이어야 웹·앱이 같은 날을 본다.
export function ymdToday() {
  return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10).replace(/-/g, "");
}

// 학년 정수 코드 — 초1~6=1~6, 중1~3=7~9, 고1~3=10~12, 유치원=0.
// ⚠️ timetables.school_year(NEIS 학년도 "2026")와 **완전히 다른 개념**이다.
//    계약 §4.3에서 시간표는 neis_year로 이름을 바꿔 내보낸다.
const GRADE_BASE = { "초등학교": 0, "중학교": 6, "고등학교": 9, "유치원": -1 };
export function gradeCode(schoolKind, grade) {
  const base = GRADE_BASE[schoolKind];
  const g = parseInt(grade, 10);
  if (base == null || !(g >= 1)) return null; // 모르면 null — 0으로 뭉개지 않는다(0은 유치원)
  if (base === -1) return 0;
  return base + g;
}
export function gradeLabel(code) {
  if (code == null) return "";
  if (code === 0) return "유치원";
  if (code <= 6) return `초${code}`;
  if (code <= 9) return `중${code - 6}`;
  return `고${code - 9}`;
}

// ── 페이지네이션 (계약 §1.6) ───────────────────────────────────
export function parsePaging(url) {
  const raw = parseInt(url.searchParams.get("limit") || "50", 10);
  const limit = Math.min(200, Math.max(1, Number.isFinite(raw) ? raw : 50));
  const cursor = url.searchParams.get("cursor") || null;
  return { limit, cursor };
}

// ── 입력 검증 헬퍼 ────────────────────────────────────────────
// 실패 시 data.fields에 항목별 사유를 담아 앱이 폼에 표시할 수 있게 한다(계약 §1.3 VALIDATION).
export function validate(rules) {
  const fields = {};
  for (const [name, ok, msg] of rules) if (!ok) fields[name] = msg;
  return Object.keys(fields).length ? fields : null;
}

// ── JSON 본문 파싱 (깨진 요청에 500 대신 VALIDATION) ───────────
export async function readJson(request) {
  try {
    const ct = request.headers.get("Content-Type") || "";
    if (!ct.includes("application/json")) return null;
    return await request.json();
  } catch (_) {
    return null;
  }
}
