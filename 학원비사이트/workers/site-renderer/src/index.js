import {
  academyDetailPage,
  dojoDetailPage,
  categoryListPage,
  sigunguHubPage,
  sidoHubPage,
  dongHubPage,
  homePage,
  privacyPage,
  registerPage,
  searchResultsPage,
} from "./templates.js";

const ACADEMY_CATEGORY_SLUGS = new Set([
  "bosup", "yeeneung", "eohak", "gita", "jikeop", "doksuil", "jonghap", "giye", "inmun",
]);
const DOJO_CATEGORY_SLUGS = new Set([
  "taekwondo", "boxing", "judo", "hapkido", "wrestling", "kumdo", "wushu", "gita",
]);

const ACADEMY_ALIVE = "NOT (status = '폐원' AND closed_at < datetime('now','-2 years'))";
const DOJO_ALIVE = "NOT (is_open = 0 AND closed_ymd < date('now','-2 years'))";

// 목록/검색결과 노출 우선순위 티어. 배열 구조라서 추후 광고 그룹은 { col: "is_ad" }를
// 맨 앞에 unshift만 하면 최상단에 붙는다(하드코딩 if 없이 ORDER BY가 자동 생성됨).
// ① 정보제공(info_provided): 내부는 고정순서 금지 → 일 단위 로테이션(rotate:true)
// ② 수강료 확인됨(has_fee_data): 내부 기존 규칙(name)
// ③ 나머지
const LIST_TIERS = [
  { col: "info_provided", rotate: true },
  { col: "has_fee_data" },
];

// 하루 단위 시드(UTC 날짜). 같은 날은 값이 고정돼 Workers/D1 캐시와 충돌하지 않고,
// 날짜가 바뀌면 ①티어(정보제공) 내부 순서가 회전한다.
function daySeed() {
  return Math.floor(Date.now() / 86400000);
}

// 티어 배열로부터 ORDER BY 절 생성. hasFee=false면 도장처럼 수강료 개념 없는 테이블용.
function tierOrderBy(seed, { hasFee = true } = {}) {
  const tiers = hasFee ? LIST_TIERS : LIST_TIERS.filter((t) => t.col !== "has_fee_data");
  const parts = tiers.map((t) => `${t.col} DESC`);
  const rot = tiers.find((t) => t.rotate);
  if (rot) parts.push(`CASE WHEN ${rot.col}=1 THEN (id + ${seed}) % 100 ELSE 0 END`);
  parts.push("name");
  return parts.join(", ");
}

const CACHE_TTL = 3600; // 1시간 edge 캐시
// 템플릿/렌더링 로직을 바꿀 때마다 이 값을 올려서 이전 배포의 캐시를 무효화한다 (재배포해도 캐시가 자동으로 안 지워짐).
const CACHE_VERSION = "38";

// 과목 키워드 기반 분류. 예체능은 학원(예능/기예)+도장 전체를 묶은 특수 그룹(세부 칩으로 좁히기 가능).
// "기타"는 홈 화면 하단 링크에는 노출하지 않되(사용자 요청), 허브의 분야 버튼에는 포함.
// 시안 10분류(키워드 기반). icon = 시안의 아이콘 타일(glyph 문자 또는 Phosphor 아이콘 클래스).
// 체육(pe)은 학원 키워드 + 도장 전체를 포함하는 특수 그룹(special:"pe"), 도장 종목 칩으로 좁히기 가능.
const SUBJECT_GROUPS = [
  { key: "korean", name: "국어·논술", glyph: "가나다", glyphSize: 14 },
  { key: "math", name: "수학", glyph: "π", glyphSize: 28 },
  { key: "english", name: "영어", glyph: "ABC", glyphSize: 16 },
  { key: "science", name: "과학", icon: "ph-flask" },
  { key: "art", name: "미술", icon: "ph-paint-brush" },
  { key: "music", name: "음악", glyph: "♪", glyphSize: 28 },
  {
    key: "pe",
    name: "체육",
    icon: "ph-basketball",
    special: "pe",
    chips: [
      { name: "태권도", q: "태권도" },
      { name: "검도", q: "검도" },
      { name: "유도", q: "유도" },
      { name: "복싱", q: "복싱" },
      { name: "합기도", q: "합기도" },
      { name: "무용", q: "무용" },
    ],
  },
  { key: "foreign", name: "외국어", icon: "ph-translate" },
  { key: "library", name: "독서실·스터디카페", icon: "ph-book-open-text" },
];
const ETC_SUBJECT = { key: "etc", name: "기타", icon: "ph-dots-three" };
const SUBJECT_GROUPS_WITH_ETC = [...SUBJECT_GROUPS, ETC_SUBJECT];

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

function xml(body, status = 200) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
}

function minPrice(feeParsedJson) {
  if (!feeParsedJson) return null;
  try {
    const items = JSON.parse(feeParsedJson);
    if (!items || !items.length) return null;
    return Math.min(...items.map((i) => i.price).filter((p) => typeof p === "number"));
  } catch {
    return null;
  }
}

async function attachRatings(db, entityType, rows) {
  if (!rows.length) return rows;
  const slugs = rows.map((r) => r.slug);
  const placeholders = slugs.map(() => "?").join(",");
  const { results } = await db
    .prepare(
      `SELECT entity_slug, AVG(score) as avg, COUNT(*) as cnt FROM ratings
       WHERE entity_type = ? AND entity_slug IN (${placeholders}) GROUP BY entity_slug`
    )
    .bind(entityType, ...slugs)
    .all();
  const map = {};
  for (const r of results) map[r.entity_slug] = r;
  return rows.map((r) => ({
    ...r,
    rating_avg: map[r.slug] ? map[r.slug].avg : 0,
    rating_count: map[r.slug] ? map[r.slug].cnt : 0,
    min_price: r.fee_parsed ? minPrice(r.fee_parsed) : null,
  }));
}

async function getBanner(db, slot, sido, sigungu, categorySlug) {
  const row = await db
    .prepare(
      `SELECT * FROM banners
       WHERE slot = ? AND active = 1
         AND (sido IS NULL OR sido = ?)
         AND (sigungu IS NULL OR sigungu = ?)
         AND (category_slug IS NULL OR category_slug = ?)
       ORDER BY (sido IS NOT NULL) + (sigungu IS NOT NULL) + (category_slug IS NOT NULL) DESC
       LIMIT 1`
    )
    .bind(slot, sido, sigungu, categorySlug)
    .first();
  return row || null;
}

async function getBannersForSlots(db, sido, sigungu, categorySlug) {
  const [b1, b2, b3] = await Promise.all([
    getBanner(db, 1, sido, sigungu, categorySlug),
    getBanner(db, 2, sido, sigungu, categorySlug),
    getBanner(db, 3, sido, sigungu, categorySlug),
  ]);
  return { 1: b1, 2: b2, 3: b3 };
}

async function getRelatedAcademies(db, sigungu, categorySlug, excludeSlug) {
  const { results } = await db
    .prepare(
      `SELECT name, slug, sido, sigungu, has_fee_data, info_provided FROM academies
       WHERE sigungu = ? AND category_slug = ? AND slug != ? AND ${ACADEMY_ALIVE}
       ORDER BY info_provided DESC, has_fee_data DESC, name LIMIT 5`
    )
    .bind(sigungu, categorySlug, excludeSlug)
    .all();
  return results;
}

async function getRelatedDojos(db, sigungu, categorySlug, excludeSlug) {
  const { results } = await db
    .prepare(
      `SELECT name, slug, sido, sigungu FROM dojos
       WHERE sigungu = ? AND category_slug = ? AND slug != ? AND is_open = 1
       ORDER BY name LIMIT 5`
    )
    .bind(sigungu, categorySlug, excludeSlug)
    .all();
  return results;
}

async function getRatingStats(db, entityType, slug) {
  const row = await db
    .prepare(`SELECT COUNT(*) as count, AVG(score) as average FROM ratings WHERE entity_type = ? AND entity_slug = ?`)
    .bind(entityType, slug)
    .first();
  return { count: row.count || 0, average: row.average || 0 };
}

async function renderDetail(env, sido, sigungu, slug) {
  const db = env.DB;
  const academy = await db
    .prepare(`SELECT * FROM academies WHERE sido = ? AND sigungu = ? AND slug = ? AND ${ACADEMY_ALIVE}`)
    .bind(sido, sigungu, slug)
    .first();
  if (academy) {
    const related = await getRelatedAcademies(db, sigungu, academy.category_slug, slug);
    const ratingStats = await getRatingStats(db, "academy", slug);
    const banners = await getBannersForSlots(db, sido, sigungu, academy.category_slug);
    return html(academyDetailPage(env, academy, related, ratingStats, banners));
  }

  const dojo = await db
    .prepare(`SELECT * FROM dojos WHERE sido = ? AND sigungu = ? AND slug = ? AND ${DOJO_ALIVE}`)
    .bind(sido, sigungu, slug)
    .first();
  if (dojo) {
    // 분야 표기는 인허가 종목명(sport_name) 우선. "태권도장" 대신 "태권도"로 노출(뱃지/빵부스러기/계층 전부).
    dojo.category_name = dojo.sport_name || dojo.category_name;
    const related = await getRelatedDojos(db, sigungu, dojo.category_slug, slug);
    const ratingStats = await getRatingStats(db, "dojo", slug);
    const banners = await getBannersForSlots(db, sido, sigungu, dojo.category_slug);
    return html(dojoDetailPage(env, dojo, related, ratingStats, banners));
  }

  return null;
}

async function renderCategoryList(env, sido, sigungu, categorySlug, page, sort) {
  const db = env.DB;
  const PAGE_SIZE = 20;
  const offset = (page - 1) * PAGE_SIZE;
  const seed = daySeed();

  let academies = [];
  let dojos = [];
  let categoryName = null;

  if (ACADEMY_CATEGORY_SLUGS.has(categorySlug)) {
    const { results } = await db
      .prepare(
        `SELECT id, name, slug, sido, sigungu, has_fee_data, info_provided, category_name, course_name, inst_type, fee_parsed, dong FROM academies
         WHERE sido = ? AND sigungu = ? AND category_slug = ? AND ${ACADEMY_ALIVE}
         ORDER BY ${tierOrderBy(seed)} LIMIT ? OFFSET ?`
      )
      .bind(sido, sigungu, categorySlug, PAGE_SIZE + 1, offset)
      .all();
    academies = results;
    if (academies.length) categoryName = academies[0].category_name;
  }

  if (DOJO_CATEGORY_SLUGS.has(categorySlug)) {
    const { results } = await db
      .prepare(
        `SELECT id, name, slug, sido, sigungu, info_provided, category_name, sport_name, is_open, dong FROM dojos
         WHERE sido = ? AND sigungu = ? AND category_slug = ? AND is_open = 1
         ORDER BY ${tierOrderBy(seed, { hasFee: false })} LIMIT ? OFFSET ?`
      )
      .bind(sido, sigungu, categorySlug, PAGE_SIZE + 1, offset)
      .all();
    dojos = results;
    if (!categoryName && dojos.length) categoryName = dojos[0].sport_name || dojos[0].category_name;
  }

  if (!academies.length && !dojos.length && page === 1) return null;

  const hasMore = academies.length > PAGE_SIZE || dojos.length > PAGE_SIZE;
  academies = await attachRatings(db, "academy", academies.slice(0, PAGE_SIZE));
  dojos = await attachRatings(db, "dojo", dojos.slice(0, PAGE_SIZE));

  let totalCount = 0;
  if (ACADEMY_CATEGORY_SLUGS.has(categorySlug)) {
    const r = await db
      .prepare(`SELECT COUNT(*) as c FROM academies WHERE sido = ? AND sigungu = ? AND category_slug = ? AND ${ACADEMY_ALIVE}`)
      .bind(sido, sigungu, categorySlug)
      .first();
    totalCount += r.c;
  }
  if (DOJO_CATEGORY_SLUGS.has(categorySlug)) {
    const r = await db
      .prepare(`SELECT COUNT(*) as c FROM dojos WHERE sido = ? AND sigungu = ? AND category_slug = ? AND is_open = 1`)
      .bind(sido, sigungu, categorySlug)
      .first();
    totalCount += r.c;
  }

  const banner = await getBanner(db, 1, sido, sigungu, categorySlug);

  return html(
    categoryListPage(env, sido, sigungu, categorySlug, categoryName || categorySlug, academies, dojos, page, hasMore, totalCount, banner, sort)
  );
}

// 과목별 건수를 한 번의 쿼리(학원)+한 번의 쿼리(도장)로 계산. dong을 주면 읍면동 범위로 좁혀짐.
async function getSubjectCounts(db, sido, sigungu, dong) {
  const whereBase = ["sido = ?"];
  const params = [sido];
  if (sigungu) { whereBase.push("sigungu = ?"); params.push(sigungu); }
  if (dong) { whereBase.push("dong = ?"); params.push(dong); }

  const academyWhere = [...whereBase, ACADEMY_ALIVE].join(" AND ");
  const dojoWhere = [...whereBase, "is_open = 1"].join(" AND ");

  const aRow = await db
    .prepare(
      `SELECT
         SUM(CASE WHEN name LIKE '%국어%' OR name LIKE '%논술%' OR category_name LIKE '%국어%' OR category_name LIKE '%논술%' THEN 1 ELSE 0 END) as korean,
         SUM(CASE WHEN name LIKE '%수학%' OR category_name LIKE '%수학%' THEN 1 ELSE 0 END) as math,
         SUM(CASE WHEN name LIKE '%영어%' OR category_name LIKE '%영어%' THEN 1 ELSE 0 END) as english,
         SUM(CASE WHEN name LIKE '%과학%' OR category_name LIKE '%과학%' THEN 1 ELSE 0 END) as science,
         SUM(CASE WHEN name LIKE '%미술%' OR category_name LIKE '%미술%' THEN 1 ELSE 0 END) as art,
         SUM(CASE WHEN name LIKE '%음악%' OR name LIKE '%피아노%' OR name LIKE '%성악%' OR category_name LIKE '%음악%' THEN 1 ELSE 0 END) as music,
         SUM(CASE WHEN name LIKE '%체육%' OR name LIKE '%무용%' OR name LIKE '%태권%' OR name LIKE '%발레%' THEN 1 ELSE 0 END) as pe,
         SUM(CASE WHEN name LIKE '%어학원%' OR name LIKE '%외국어%' OR category_name LIKE '%어학원%' THEN 1 ELSE 0 END) as foreign_lang,
         SUM(CASE WHEN name LIKE '%독서실%' OR name LIKE '%스터디카페%' OR name LIKE '%스터디룸%' OR category_name LIKE '%독서실%' THEN 1 ELSE 0 END) as library,
         SUM(CASE WHEN category_slug IN ('gita','jikeop','inmun') THEN 1 ELSE 0 END) as etc,
         COUNT(*) as total
       FROM academies WHERE ${academyWhere}`
    )
    .bind(...params)
    .first();

  const dRow = await db.prepare(`SELECT COUNT(*) as c FROM dojos WHERE ${dojoWhere}`).bind(...params).first();

  return {
    counts: {
      korean: aRow.korean || 0,
      math: aRow.math || 0,
      english: aRow.english || 0,
      science: aRow.science || 0,
      art: aRow.art || 0,
      music: aRow.music || 0,
      pe: (aRow.pe || 0) + (dRow.c || 0),
      foreign: aRow.foreign_lang || 0,
      library: aRow.library || 0,
      etc: aRow.etc || 0,
    },
    academyCount: aRow.total || 0,
    dojoCount: dRow.c || 0,
  };
}

// 과목키 -> 학원 WHERE 조건. getSubjectCounts의 CASE WHEN과 동일한 기준을 재사용(읍면동 목록 필터링용).
function subjectAcademyCondition(key) {
  switch (key) {
    case "korean": return "(name LIKE '%국어%' OR name LIKE '%논술%' OR category_name LIKE '%국어%' OR category_name LIKE '%논술%')";
    case "math": return "(name LIKE '%수학%' OR category_name LIKE '%수학%')";
    case "english": return "(name LIKE '%영어%' OR category_name LIKE '%영어%')";
    case "science": return "(name LIKE '%과학%' OR category_name LIKE '%과학%')";
    case "art": return "(name LIKE '%미술%' OR category_name LIKE '%미술%')";
    case "music": return "(name LIKE '%음악%' OR name LIKE '%피아노%' OR name LIKE '%성악%' OR category_name LIKE '%음악%')";
    case "pe": return "(name LIKE '%체육%' OR name LIKE '%무용%' OR name LIKE '%태권%' OR name LIKE '%발레%')";
    case "foreign": return "(name LIKE '%어학원%' OR name LIKE '%외국어%' OR category_name LIKE '%어학원%')";
    case "library": return "(name LIKE '%독서실%' OR name LIKE '%스터디카페%' OR name LIKE '%스터디룸%' OR category_name LIKE '%독서실%')";
    case "etc": return "category_slug IN ('gita','jikeop','inmun')";
    default: return "1=0";
  }
}

// 읍면동 페이지에서 분야 버튼 클릭 시 하단 목록을 채우는 조회. 예체능은 chipQ로 세부 키워드 좁히기 가능.
async function getSubjectList(db, sido, sigungu, dong, subjectKey, chipQ) {
  const where = ["sido = ?", "sigungu = ?", "dong = ?"];
  const baseParams = [sido, sigungu, dong];

  let academies = [];
  let dojos = [];

  const aCond = subjectAcademyCondition(subjectKey);
  if (aCond !== "1=0") {
    const params = [...baseParams];
    let extra = "";
    if (chipQ) {
      extra = " AND (name LIKE ? OR category_name LIKE ?)";
      params.push(`%${chipQ}%`, `%${chipQ}%`);
    }
    const { results } = await db
      .prepare(
        `SELECT id, name, slug, sido, sigungu, has_fee_data, info_provided, category_name, course_name, fee_parsed, dong FROM academies
         WHERE ${where.join(" AND ")} AND ${aCond} AND ${ACADEMY_ALIVE}${extra}
         ORDER BY ${tierOrderBy(daySeed())}`
      )
      .bind(...params)
      .all();
    academies = results;
  }

  if (subjectKey === "pe") {
    const params = [...baseParams];
    let extra = "";
    if (chipQ) {
      extra = " AND (name LIKE ? OR category_name LIKE ?)";
      params.push(`%${chipQ}%`, `%${chipQ}%`);
    }
    const { results } = await db
      .prepare(
        `SELECT id, name, slug, sido, sigungu, info_provided, category_name, sport_name, is_open, dong FROM dojos
         WHERE ${where.join(" AND ")} AND is_open = 1${extra}
         ORDER BY ${tierOrderBy(daySeed(), { hasFee: false })}`
      )
      .bind(...params)
      .all();
    dojos = results;
  }

  academies = await attachRatings(db, "academy", academies);
  dojos = await attachRatings(db, "dojo", dojos);
  return { academies, dojos };
}

async function renderDongHub(env, sido, sigungu, dong, subjectKey, chipQ) {
  const db = env.DB;
  const { counts, academyCount, dojoCount } = await getSubjectCounts(db, sido, sigungu, dong);
  if (!academyCount && !dojoCount) return null;

  const list = subjectKey ? await getSubjectList(db, sido, sigungu, dong, subjectKey, chipQ) : null;

  return html(
    dongHubPage(env, sido, sigungu, dong, SUBJECT_GROUPS_WITH_ETC, counts, academyCount + dojoCount, subjectKey, chipQ, list)
  );
}

async function renderSigunguHub(env, sido, sigungu) {
  const db = env.DB;
  const { counts, academyCount, dojoCount } = await getSubjectCounts(db, sido, sigungu, null);

  if (!academyCount && !dojoCount) return null;

  return html(sigunguHubPage(env, sido, sigungu, SUBJECT_GROUPS_WITH_ETC, counts, academyCount + dojoCount));
}

// 시도 페이지: 구 목록 대신 분야 아이콘 그리드(시도 전체 범위) — 시안 기준.
async function renderSidoHub(env, sido) {
  const db = env.DB;
  const { counts, academyCount, dojoCount } = await getSubjectCounts(db, sido, null, null);
  if (!academyCount && !dojoCount) return null;
  return html(sigunguHubPage(env, sido, null, SUBJECT_GROUPS_WITH_ETC, counts, academyCount + dojoCount));
}

async function getRegionMap(db) {
  const { results } = await db
    .prepare(
      `SELECT DISTINCT sido, sigungu, dong FROM (
         SELECT sido, sigungu, dong FROM academies WHERE dong IS NOT NULL
         UNION
         SELECT sido, sigungu, dong FROM dojos WHERE dong IS NOT NULL
       ) ORDER BY sido, sigungu, dong`
    )
    .all();
  const { results: sgResults } = await db
    .prepare(
      `SELECT DISTINCT sido, sigungu FROM (
         SELECT sido, sigungu FROM academies
         UNION
         SELECT sido, sigungu FROM dojos
       ) ORDER BY sido, sigungu`
    )
    .all();

  const map = {};
  for (const r of sgResults) {
    if (r.sigungu === "미상") continue;
    if (!map[r.sido]) map[r.sido] = {};
    if (!map[r.sido][r.sigungu]) map[r.sido][r.sigungu] = [];
  }
  for (const r of results) {
    if (r.sigungu === "미상" || !map[r.sido] || !(r.sigungu in map[r.sido])) continue;
    map[r.sido][r.sigungu].push(r.dong);
  }
  return map;
}

async function renderHome(env) {
  const db = env.DB;
  const { results } = await db
    .prepare(
      `SELECT DISTINCT sido FROM (
         SELECT sido FROM academies
         UNION
         SELECT sido FROM dojos
       ) ORDER BY sido`
    )
    .all();
  return html(homePage(env, results.map((r) => r.sido), SUBJECT_GROUPS));
}

async function renderSearch(env, query, sido, sigungu, dong, subject, page = 1) {
  const db = env.DB;
  const q = query ? `%${query}%` : null;
  // subject가 있으면 해당 분류 조건 적용. 체육(pe)만 도장 전체 포함, 나머지는 학원 전용.
  const subjectCond = subject ? subjectAcademyCondition(subject) : null;
  const includeDojos = !subject || subject === "pe";

  const academyWhere = ["1=1"];
  const academyParams = [];
  if (sido) { academyWhere.push("sido = ?"); academyParams.push(sido); }
  if (sigungu) { academyWhere.push("sigungu = ?"); academyParams.push(sigungu); }
  if (dong) { academyWhere.push("dong = ?"); academyParams.push(dong); }
  if (subjectCond) { academyWhere.push(subjectCond); }
  if (q) { academyWhere.push("(name LIKE ? OR category_name LIKE ?)"); academyParams.push(q, q); }
  academyWhere.push(ACADEMY_ALIVE);

  const dojoWhere = ["is_open = 1"];
  const dojoParams = [];
  if (sido) { dojoWhere.push("sido = ?"); dojoParams.push(sido); }
  if (sigungu) { dojoWhere.push("sigungu = ?"); dojoParams.push(sigungu); }
  if (dong) { dojoWhere.push("dong = ?"); dojoParams.push(dong); }
  // 체육(pe) 그룹은 도장 전체 포함(지역 필터만). 그 외 분류는 도장 제외.
  if (q) { dojoWhere.push("(name LIKE ? OR category_name LIKE ?)"); dojoParams.push(q, q); }

  // 이전엔 LIMIT 60 하드코딩으로 전체 결과가 60개로 잘려 보였음(버그) — 페이지네이션 + 실제 총건수 쿼리로 교체.
  const PAGE_SIZE = 30;
  const offset = (page - 1) * PAGE_SIZE;
  const seed = daySeed();
  const [academiesRes, dojosRes, academyTotalRow, dojoTotalRow] = await Promise.all([
    db
      .prepare(
        `SELECT id, name, slug, sido, sigungu, has_fee_data, info_provided, category_name, course_name, fee_parsed, dong FROM academies
         WHERE ${academyWhere.join(" AND ")} ORDER BY ${tierOrderBy(seed)} LIMIT ? OFFSET ?`
      )
      .bind(...academyParams, PAGE_SIZE + 1, offset)
      .all(),
    includeDojos
      ? db
          .prepare(
            `SELECT id, name, slug, sido, sigungu, is_open, info_provided, category_name, sport_name, dong FROM dojos
             WHERE ${dojoWhere.join(" AND ")} ORDER BY ${tierOrderBy(seed, { hasFee: false })} LIMIT ? OFFSET ?`
          )
          .bind(...dojoParams, PAGE_SIZE + 1, offset)
          .all()
      : Promise.resolve({ results: [] }),
    db.prepare(`SELECT COUNT(*) as c FROM academies WHERE ${academyWhere.join(" AND ")}`).bind(...academyParams).first(),
    includeDojos
      ? db.prepare(`SELECT COUNT(*) as c FROM dojos WHERE ${dojoWhere.join(" AND ")}`).bind(...dojoParams).first()
      : Promise.resolve({ c: 0 }),
  ]);

  const hasMore = academiesRes.results.length > PAGE_SIZE || dojosRes.results.length > PAGE_SIZE;
  const academies = await attachRatings(db, "academy", academiesRes.results.slice(0, PAGE_SIZE));
  const dojos = await attachRatings(db, "dojo", dojosRes.results.slice(0, PAGE_SIZE));
  const totalCount = (academyTotalRow.c || 0) + (dojoTotalRow.c || 0);

  // 시군구까지 지정된 경우 상단 카테고리 필터바용 개수 계산
  let counts = null;
  if (sido && sigungu) {
    counts = (await getSubjectCounts(db, sido, sigungu, dong)).counts;
  }
  return html(
    searchResultsPage(env, query, academies, dojos, sido, sigungu, dong, subject, SUBJECT_GROUPS_WITH_ETC, counts, totalCount, page, hasMore)
  );
}

async function renderSitemapIndex(env, origin) {
  const db = env.DB;
  const academyCount = (await db.prepare(`SELECT COUNT(*) as c FROM academies WHERE ${ACADEMY_ALIVE}`).first()).c;
  const dojoCount = (await db.prepare(`SELECT COUNT(*) as c FROM dojos WHERE ${DOJO_ALIVE}`).first()).c;
  const CHUNK = 40000;
  const academyChunks = Math.ceil(academyCount / CHUNK);
  const dojoChunks = Math.ceil(dojoCount / CHUNK);

  let entries = "";
  for (let i = 0; i < academyChunks; i++) {
    entries += `<sitemap><loc>${origin}/sitemaps/academies-${i}.xml</loc></sitemap>`;
  }
  for (let i = 0; i < dojoChunks; i++) {
    entries += `<sitemap><loc>${origin}/sitemaps/dojos-${i}.xml</loc></sitemap>`;
  }

  return xml(`<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${entries}</sitemapindex>`);
}

async function renderSitemapChunk(env, origin, type, chunkIndex) {
  const db = env.DB;
  const CHUNK = 40000;
  const offset = chunkIndex * CHUNK;

  const table = type === "academies" ? "academies" : "dojos";
  const alive = type === "academies" ? ACADEMY_ALIVE : DOJO_ALIVE;

  const { results } = await db
    .prepare(`SELECT sido, sigungu, slug FROM ${table} WHERE ${alive} ORDER BY id LIMIT ? OFFSET ?`)
    .bind(CHUNK, offset)
    .all();

  if (!results.length) return xml(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>`, 404);

  const urls = results
    .map((r) => `<url><loc>${origin}/${encodeURIComponent(r.sido)}/${encodeURIComponent(r.sigungu)}/${encodeURIComponent(r.slug)}/</loc></url>`)
    .join("");

  return xml(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`);
}

// 카카오톡/SNS 링크 공유 시 미리보기에 쓰일 og:image. 별도 이미지 파일 없이 SVG를 직접 서빙.
function ogImageSvg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#16213e"/>
      <stop offset="1" stop-color="#1a2a52"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="490" y="150" width="220" height="220" rx="48" fill="#3b5bdb"/>
  <circle cx="565" cy="235" r="42" fill="none" stroke="white" stroke-width="18"/>
  <line x1="596" y1="266" x2="650" y2="320" stroke="white" stroke-width="20" stroke-linecap="round"/>
  <text x="600" y="470" text-anchor="middle" font-family="Malgun Gothic, Apple SD Gothic Neo, sans-serif" font-size="56" font-weight="800" fill="#ffffff">우리아이학원정보</text>
  <text x="600" y="520" text-anchor="middle" font-family="Malgun Gothic, Apple SD Gothic Neo, sans-serif" font-size="26" font-weight="500" fill="#aebbdc">우리 아이에게 맞는 학원, 수강료까지 한눈에</text>
</svg>`;
}

function robotsTxt(env) {
  if (env.SITE_INDEXABLE === "true") {
    return new Response("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n", {
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
  return new Response("User-agent: *\nDisallow: /\n", {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

async function handleRequest(request, env, ctx) {
  const url = new URL(request.url);
  const path = url.pathname;

  if (path === "/robots.txt") return robotsTxt(env);

  if (path === "/og-image.svg") {
    return new Response(ogImageSvg(), {
      headers: { "Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=86400" },
    });
  }

  // 임시 캐시 퍼지 라우트: Cloudflare 엣지가 Worker 실행 전에 자체 캐싱한 응답을 강제로 지운다.
  // ?key=EPURGE_KEY&target=/path/ 형태로 호출. 작업 끝나면 제거할 것.
  if (path === "/__purge") {
    if (url.searchParams.get("key") !== "purge-dev-2026") {
      return new Response("forbidden", { status: 403 });
    }
    const target = url.searchParams.get("target") || "/";
    const targetUrl = new URL(target, url.origin);
    const deleted = await caches.default.delete(new Request(targetUrl.toString()));
    return new Response(`purged ${targetUrl.toString()}: ${deleted}`, { status: 200 });
  }

  if (path === "/search" || path === "/search/") {
    const q = (url.searchParams.get("q") || "").trim();
    const sido = (url.searchParams.get("sido") || "").trim() || null;
    const sigungu = (url.searchParams.get("sigungu") || "").trim() || null;
    const dong = (url.searchParams.get("dong") || "").trim() || null;
    const subject = (url.searchParams.get("subject") || "").trim() || null;
    const page = Math.max(1, Number(url.searchParams.get("page") || "1") || 1);

    // 검색어(또는 예체능처럼 subject로 조건이 이미 있는 경우) 없이 지역만 고른 경우:
    // 읍면동까지는 안 골랐으면 기존 허브/목록 페이지로 보내는 게 더 유용함
    if (!q && !subject && !dong && sido && sigungu) {
      return Response.redirect(`${url.origin}/${encodeURIComponent(sido)}/${encodeURIComponent(sigungu)}/`, 302);
    }
    if (!q && !subject && !dong && sido && !sigungu) {
      return Response.redirect(`${url.origin}/${encodeURIComponent(sido)}/`, 302);
    }
    env.REGION_MAP = await getRegionMap(env.DB);
    if (!q && !subject && !sido) {
      return html(searchResultsPage(env, "", [], [], null, null, null));
    }
    return renderSearch(env, q, sido, sigungu, dong, subject, page);
  }

  // 캐시 확인 (sitemap/xml 제외한 HTML 페이지는 REGION_MAP이 헤더 검색폼에 필요)
  // 캐시 키에 CACHE_VERSION을 심어서, 재배포 시 값을 올리면 이전 배포의 캐시가 자동으로 무효화되게 함
  const cache = caches.default;
  const versionedUrl = new URL(url.toString());
  versionedUrl.searchParams.set("__v", CACHE_VERSION);
  const cacheKey = new Request(versionedUrl.toString(), request);
  if (request.method === "GET") {
    const cached = await cache.match(cacheKey);
    if (cached) {
      const outgoing = new Response(cached.body, cached);
      outgoing.headers.set("Cache-Control", "no-store");
      return outgoing;
    }
  }

  let response;

  if (path === "/privacy/" || path === "/privacy") {
    env.REGION_MAP = await getRegionMap(env.DB);
    response = html(privacyPage(env));
  } else if (path === "/register/" || path === "/register") {
    env.REGION_MAP = await getRegionMap(env.DB);
    response = html(registerPage(env, SUBJECT_GROUPS_WITH_ETC));
  } else if (path === "/sitemap.xml") {
    response = await renderSitemapIndex(env, url.origin);
  } else if (path.startsWith("/sitemaps/")) {
    const m = path.match(/^\/sitemaps\/(academies|dojos)-(\d+)\.xml$/);
    response = m ? await renderSitemapChunk(env, url.origin, m[1], Number(m[2])) : new Response("Not found", { status: 404 });
  } else {
    env.REGION_MAP = await getRegionMap(env.DB);
    const segments = path.split("/").filter(Boolean).map(decodeURIComponent);

    if (segments.length === 0) {
      response = await renderHome(env);
    } else if (segments.length === 1) {
      response = (await renderSidoHub(env, segments[0])) || new Response("Not found", { status: 404 });
    } else if (segments.length === 2) {
      response = (await renderSigunguHub(env, segments[0], segments[1])) || new Response("Not found", { status: 404 });
    } else if (segments.length === 3) {
      const [sido, sigungu, third] = segments;
      if (ACADEMY_CATEGORY_SLUGS.has(third) || DOJO_CATEGORY_SLUGS.has(third)) {
        const page = Number(url.searchParams.get("page") || "1");
        const sort = url.searchParams.get("sort") === "fee" ? "fee" : null;
        response = (await renderCategoryList(env, sido, sigungu, third, page, sort)) || new Response("Not found", { status: 404 });
      } else if (env.REGION_MAP[sido] && env.REGION_MAP[sido][sigungu] && env.REGION_MAP[sido][sigungu].includes(third)) {
        const subject = (url.searchParams.get("subject") || "").trim() || null;
        const chip = (url.searchParams.get("chip") || "").trim() || null;
        response = (await renderDongHub(env, sido, sigungu, third, subject, chip)) || new Response("Not found", { status: 404 });
      } else {
        response = (await renderDetail(env, sido, sigungu, third)) || new Response("Not found", { status: 404 });
      }
    } else {
      response = new Response("Not found", { status: 404 });
    }
  }

  if (request.method === "GET" && response.status === 200) {
    // 내부 캐시(cache.put)에는 긴 TTL을 주되, 실제 클라이언트/Cloudflare 엣지로 나가는 응답은
    // no-store로 보내서 캐싱을 전부 우리 코드(cacheKey 버전 관리)가 통제하게 한다.
    // (Cache-Control: public을 그대로 내보내면 Cloudflare 엣지가 Worker 실행 전에 자체 캐싱해버려서
    //  재배포해도 반영이 안 되는 문제가 있었음)
    const bodyForCache = await response.clone().arrayBuffer();
    const storedResponse = new Response(bodyForCache, response);
    storedResponse.headers.set("Cache-Control", `public, max-age=${CACHE_TTL}`);
    ctx.waitUntil(cache.put(cacheKey, storedResponse));

    const outgoing = new Response(bodyForCache, response);
    outgoing.headers.set("Cache-Control", "no-store");
    return outgoing;
  }

  return response;
}

export default {
  async fetch(request, env, ctx) {
    try {
      return await handleRequest(request, env, ctx);
    } catch (err) {
      console.error(err);
      return new Response("일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", {
        status: 500,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }
  },
};
