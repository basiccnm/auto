/* ═══════════════════════════════════════════════════════════
   테스트용 가짜 학교 만들기 (2026-07-25, 사장님 지시)

   왜: 지금은 **방학이라 급식·시간표가 비어 있어** 앱 화면을 검수할 수가 없다.
       실제 학교 데이터는 NEIS가 주는 대로라 우리가 채울 수 없으므로,
       **가짜 학교 한 곳**을 만들어 급식·시간표·학사일정을 넣어두고 그걸로 본다.

   ⚠ 실서비스 D1에 들어간다. 지우기 쉽게 슬러그에 `-testschool`을 박았다.
      정리:  node scripts/seed_test_school.mjs --clean

   쓰는 법:
     node scripts/seed_test_school.mjs           (SQL 파일만 만든다)
     node scripts/seed_test_school.mjs --clean   (지우는 SQL을 만든다)
   그다음:
     npx wrangler d1 execute eduthink-db --remote --file ../../scripts/_seed_test_school.sql
   ═══════════════════════════════════════════════════════════ */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DIR = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(DIR, "_seed_test_school.sql");
const CLEAN = process.argv.includes("--clean");

const SLUG = "테스트초등학교-testschool";
const NAME = "테스트초등학교";
const OFFICE = "T10", CODE = "9999999";

const q = (v) => (v == null ? "NULL" : `'${String(v).replace(/'/g, "''")}'`);
const sql = [];

sql.push("-- 자동 생성: scripts/seed_test_school.mjs — 손으로 고치지 말 것");

if (CLEAN) {
  sql.push(`DELETE FROM meals WHERE school_id IN (SELECT id FROM schools WHERE slug=${q(SLUG)});`);
  sql.push(`DELETE FROM timetables WHERE school_id IN (SELECT id FROM schools WHERE slug=${q(SLUG)});`);
  sql.push(`DELETE FROM academic_schedules WHERE school_id IN (SELECT id FROM schools WHERE slug=${q(SLUG)});`);
  sql.push(`DELETE FROM school_details WHERE school_id IN (SELECT id FROM schools WHERE slug=${q(SLUG)});`);
  sql.push(`-- 이 학교로 등록한 자녀가 있으면 아래 줄은 FK로 실패한다. 자녀부터 지우고 다시 실행할 것.`);
  sql.push(`DELETE FROM schools WHERE slug=${q(SLUG)};`);
  fs.writeFileSync(OUT, sql.join("\n") + "\n", "utf8");
  console.log("지우는 SQL을 만들었다 → " + OUT);
  process.exit(0);
}

const NOW = "2026-07-25T00:00:00.000Z";

// ── 학교 ──────────────────────────────────────────────────
// ⚠ 학교 행은 **지우지 않는다.** 이미 이 학교로 등록한 자녀가 있으면 children.school_id가
//    이 행을 참조해서 FOREIGN KEY 위반으로 전체가 실패한다(2026-07-26 실측).
//    그래서 학교는 «없으면 넣고 있으면 그대로», 딸린 데이터만 갈아끼운다.
sql.push(`DELETE FROM meals WHERE school_id IN (SELECT id FROM schools WHERE slug=${q(SLUG)});`);
sql.push(`DELETE FROM timetables WHERE school_id IN (SELECT id FROM schools WHERE slug=${q(SLUG)});`);
sql.push(`DELETE FROM academic_schedules WHERE school_id IN (SELECT id FROM schools WHERE slug=${q(SLUG)});`);
sql.push(`DELETE FROM school_details WHERE school_id IN (SELECT id FROM schools WHERE slug=${q(SLUG)});`);
sql.push(`INSERT OR IGNORE INTO schools (office_code, office_name, school_code, name, school_kind, sido, jurisdiction_office, address_road, phone, homepage, slug, last_synced_at, sem2_start)
VALUES (${q(OFFICE)}, '테스트교육청', ${q(CODE)}, ${q(NAME)}, '초등학교', '테스트특별시', '테스트교육지원청',
        '테스트특별시 테스트구 테스트로 1', '02-0000-0000', 'https://example.invalid', ${q(SLUG)}, ${q(NOW)}, '20260820');`);
const SID = `(SELECT id FROM schools WHERE slug=${q(SLUG)})`;

// 학교 규모 — 학년별 학급수(앱 자녀등록의 반 목록이 이 값을 쓴다)
const gb = JSON.stringify([1, 2, 3, 4, 5, 6].map((g) => ({ grade: g, classes: 4, students: 96 })));
sql.push(`INSERT INTO school_details (school_id, source_school_code, student_count, class_count, teacher_count, last_synced_at, grade_breakdown)
VALUES (${SID}, ${q(CODE)}, 576, 24, 38, ${q(NOW)}, ${q(gb)});`);

// ── 날짜 도우미 ────────────────────────────────────────────
const ymd = (d) => d.toISOString().slice(0, 10).replace(/-/g, "");
const addDays = (d, n) => new Date(d.getTime() + n * 86400000);
const START = new Date(Date.UTC(2026, 6, 20));   // 2026-07-20 (오늘 앞뒤로 보이게)
const DAYS = 200;                                 // 약 7개월치

// ── 급식 — 방학이어도 매 평일 채운다 ─────────────────────
const MENUS = [
  ["기장밥", "미역국", "돈육김치볶음", "콩나물무침", "배추김치", "요구르트"],
  ["보리밥", "된장찌개", "고등어구이", "시금치나물", "깍두기", "사과"],
  ["카레라이스", "쇠고기무국", "치킨너겟", "오이무침", "배추김치", "우유"],
  ["잡곡밥", "감자국", "제육볶음", "브로콜리숙회", "총각김치", "바나나"],
  ["백미밥", "북어국", "닭갈비", "무생채", "배추김치", "귤"],
  ["짜장밥", "계란국", "군만두", "단무지", "배추김치", "요구르트"],
  ["현미밥", "순두부찌개", "삼치구이", "숙주나물", "깍두기", "포도"],
];
// 알레르기 표기(숫자)는 NEIS 원문 형식 그대로 — 앱이 파싱해서 쓴다
const ALG = { "돈육김치볶음": "5.6.10", "고등어구이": "5.6.17", "치킨너겟": "1.2.5.6.15", "우유": "2", "요구르트": "2",
  "제육볶음": "5.6.10", "닭갈비": "5.6.15", "군만두": "1.5.6.10", "삼치구이": "5.6.17", "계란국": "1.5", "순두부찌개": "5.6" };

let mealN = 0;
for (let i = 0; i < DAYS; i++) {
  const d = addDays(START, i);
  const dow = d.getUTCDay();
  if (dow === 0 || dow === 6) continue;                       // 주말 제외
  // ⚠ 7일 주기로 돌리면 **매주 같은 요일에 같은 메뉴**가 나온다 — 월요일마다 기장밥.
  //   실제 급식은 그렇지 않고, 검수할 때 "다 똑같다"로 보인다(2026-07-26 지적).
  //   메뉴 수와 서로소인 수를 곱해 요일과 안 맞물리게 한다.
  const menu = MENUS[(i * 3 + Math.floor(i / 5)) % MENUS.length];
  const raw = menu.map((x) => (ALG[x] ? `${x} (${ALG[x]})` : x)).join("<br/>");
  const parsed = JSON.stringify(menu.map((x) => ({
    name: x, allergens: (ALG[x] || "").split(".").filter(Boolean).map(Number),
  })));
  sql.push(`INSERT INTO meals (school_id, meal_date, meal_type_code, meal_type_name, dishes, dishes_parsed, calorie_info, last_synced_at)
VALUES (${SID}, ${q(ymd(d))}, '2', '중식', ${q(raw)}, ${q(parsed)}, '650.3 Kcal', ${q(NOW)});`);
  mealN++;
}

// ── 시간표 — 1~6학년 × 1~4반 은 너무 크다. 앱이 보는 3학년 1반만 채운다 ──
const SUBJ = ["국어", "수학", "사회", "과학", "영어", "체육", "음악", "미술", "실과", "도덕", "창의적체험활동"];
// ⚠ 학기를 둘 다 넣는다. API가 **오늘 날짜로 학기를 계산**해서 그 학기만 조회한다
//   (3~7월=1학기, 8~2월=2학기). 한 학기만 넣으면 지금(7월)은 1학기라 빈 화면이 된다 — 실제로 겪음.
let ttN = 0;
for (const sem of ["1", "2"]) {
  for (let wd = 1; wd <= 5; wd++) {          // 월~금
    for (let p = 1; p <= 6; p++) {
      const s = SUBJ[(wd * 7 + p + (sem === "2" ? 3 : 0)) % SUBJ.length];
      sql.push(`INSERT INTO timetables (school_id, school_year, semester, weekday, grade, class_name, period, subject, last_synced_at)
VALUES (${SID}, '2026', ${q(sem)}, ${wd}, '3', '1', ${p}, ${q(s)}, ${q(NOW)});`);
      ttN++;
    }
  }
}

// ── 학사일정 — 방학·개학·행사 (2026-07 ~ 2027-02) ────────
const EVENTS = [
  ["20260720", "여름방학", "", "휴업일"],
  ["20260815", "광복절", "", "공휴일"],
  ["20260820", "2학기 개학", "등교 시간 8시 40분", null],
  ["20260724", "여름방학 독서교실", "도서관", null],
  ["20260731", "방학중 돌봄교실", "", null],
  ["20260807", "교사 연수", "", "휴업일"],
  ["20260828", "학부모 상담주간 시작", "9/1까지", null],
  ["20260911", "안전교육의 날", "", null],
  ["20260918", "체육대회 예비일", "", null],
  ["20261002", "개교기념일", "", "휴업일"],
  ["20261030", "수업공개의 날", "2~3교시", null],
  ["20261113", "진로체험의 날", "", null],
  ["20261127", "학예회 총연습", "", null],
  ["20260904", "가을 운동회", "우천 시 9/11로 연기", null],
  ["20260925", "추석 연휴 시작", "", "휴업일"],
  ["20261009", "한글날", "", "공휴일"],
  ["20261016", "학예발표회", "체육관", null],
  ["20261023", "현장체험학습", "국립중앙박물관", null],
  ["20261106", "학부모 공개수업", "3~4교시", null],
  ["20261120", "독서 골든벨", "", null],
  ["20261204", "김장 나눔의 날", "", null],
  ["20261218", "2학기 기말 정리주간", "", null],
  ["20261224", "겨울방학식", "단축수업", null],
  ["20261225", "성탄절", "", "공휴일"],
  ["20261228", "겨울방학", "", "휴업일"],
  ["20270101", "신정", "", "공휴일"],
  ["20270202", "개학", "", null],
  ["20270212", "졸업식", "10시 강당", null],
  ["20270213", "종업식", "", null],
];
EVENTS.forEach(([date, name, content, closure]) => {
  sql.push(`INSERT INTO academic_schedules (school_id, event_date, event_name, event_content, closure_type, grade_flags, last_synced_at)
VALUES (${SID}, ${q(date)}, ${q(name)}, ${q(content || null)}, ${q(closure)}, '{}', ${q(NOW)});`);
});

fs.writeFileSync(OUT, sql.join("\n") + "\n", "utf8");
console.log(`SQL 생성 → ${OUT}\n  급식 ${mealN}일 · 시간표 ${ttN}칸(3학년 1반) · 학사일정 ${EVENTS.length}건`);
