/* ═══════════════════════════════════════════════════════════════
   앱 구조 목업 v1 — 라우터 + 화면 12종 (회신25-2)

   데이터는 전부 STUB이지만 **모양이 계약 응답과 1:1**이다.
   갈아끼울 때는 각 화면의 STUB.xxx 참조를 fetch("/api/v1/…")로 바꾸면 끝 —
   화면 코드는 계약의 필드명만 안다.
   ═══════════════════════════════════════════════════════════════ */

// ── 알레르기 표준 코드(학교급식 1~18) ─────────────────────────
const ALLERGEN_KO = {
  1: "난류", 2: "우유", 3: "메밀", 4: "땅콩", 5: "대두", 6: "밀",
  7: "고등어", 8: "게", 9: "새우", 10: "돼지고기", 11: "복숭아", 12: "토마토",
  13: "아황산류", 14: "호두", 15: "닭고기", 16: "쇠고기", 17: "오징어", 18: "조개류",
};
/* 오늘 날짜 — **KST 기준**으로 실제 오늘을 쓴다.
   2026-07-27까지 "20260724"로 박혀 있었다. 목업을 만들던 날에 고정한 값인데,
   그대로 두니 «오늘» 표시·D-day·급식이 사흘씩 어긋났다(실측).
   Date 기본값은 기기 시간대라 해외·에뮬레이터에서 하루가 밀린다 — 서버(api_core.ymdToday)와 같은 규칙으로 맞춘다. */
/* 개발 스위치 — 화면 검수용 토글을 한 줄로 켜고 끈다(2026-07-27).
   「자녀 화면으로 보기」·「기숙사형 학교로 보기」는 우리가 화면을 확인하려고 둔 것이지
   학부모가 볼 것이 아니다. **배포 전 false 로 바꾼다**(docs/작업로그.md 배포 체크리스트). */
const DEV_TOOLS = false;   // 배포 상태(2026-07-27). 화면 검수할 때만 true 로 되돌린다.

/* ⚠ 검수용 날짜 고정 (2026-08-09) — 🔴 출시 전 이 세 줄을 지운다(STATUS 에 적어 뒀다).
   방학에는 급식·시간표가 비어서 화면 절반을 볼 수 없다. 학기 중 날짜로 돌려 봐야
   «진짜 화면»을 검수할 수 있다. 에뮬이 루팅이 아니라 기기 날짜를 못 바꿔서 앱에 둔다.
     localStorage.setItem("devDate", "20260520") 하고 새로고침 → 그 날로 본다. 지우면 원래대로.
   ⚠ 서버는 자기 날짜로 판단한다 — 이건 «앱이 보는 날»만 바꾼다(권한이 늘지 않는다). */
const DEV_DATE = (() => { try { return (localStorage.getItem("devDate") || "").match(/^\d{8}$/)?.[0] || ""; } catch (e) { return ""; } })();
const TODAY = DEV_DATE || new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10).replace(/-/g, "");

// 한 달치 급식 — 실제로는 GET …/meals?from&to 한 번으로 받는다(기간 조회).
// 목업이라 평일에 반찬 풀을 돌려 채운다. 모양은 계약 응답과 동일.
function mealMonth() {
  const pool = [
    [{ name: "옥수수밥", allergens: [] }, { name: "근대된장국", allergens: [5, 6] }, { name: "제육볶음", allergens: [5, 6, 10] }, { name: "아몬드멸치볶음", allergens: [13] }, { name: "배추김치", allergens: [9] }],
    [{ name: "흑미밥", allergens: [] }, { name: "미역국", allergens: [16] }, { name: "돈까스", allergens: [1, 5, 6, 10] }, { name: "마카로니샐러드", allergens: [1, 2, 6] }, { name: "깍두기", allergens: [9] }],
    [{ name: "카레라이스", allergens: [2, 5, 6, 10] }, { name: "유부장국", allergens: [5, 6] }, { name: "치킨텐더", allergens: [1, 6, 15] }, { name: "단무지", allergens: [13] }, { name: "포기김치", allergens: [9] }],
    [{ name: "기장밥", allergens: [] }, { name: "북어채국", allergens: [1, 5, 6] }, { name: "고등어구이", allergens: [7] }, { name: "시금치나물", allergens: [5, 6] }, { name: "총각김치", allergens: [9] }],
    [{ name: "잔치국수", allergens: [1, 5, 6, 15] }, { name: "감자전", allergens: [6] }, { name: "새우튀김", allergens: [1, 6, 9] }, { name: "요구르트", allergens: [2] }, { name: "석박지", allergens: [9] }],
  ];
  // 기숙사형(조식·석식 제공) 학교가 실제로 있다 — 운영 D1 실측: 조식 1개교·석식 2개교.
  // 그래서 끼니는 3종을 다 담고, 화면에서 있는 끼니만 탭으로 보여준다(웹 templates.js와 같은 규칙).
  const breakfast = [{ name: "모닝빵", allergens: [1, 2, 6] }, { name: "우유", allergens: [2] }, { name: "삶은계란", allergens: [1] }, { name: "사과", allergens: [] }];
  const dinner = [{ name: "볶음밥", allergens: [1, 5, 6] }, { name: "계란국", allergens: [1] }, { name: "탕수육", allergens: [1, 5, 6, 10] }, { name: "깍두기", allergens: [9] }];
  const kcal = ["680.4", "712.8", "745.1", "659.3", "701.6"];
  const out = [];
  for (let d = 1; d <= 31; d++) {
    const wd = new Date(2026, 6, d).getDay();
    if (wd === 0 || wd === 6) continue;              // 주말은 급식 없음
    const i = (d - 1) % pool.length;
    const date = "202607" + String(d).padStart(2, "0");
    out.push({ date, type: "조식", dishes: breakfast, calorie: "412.0 Kcal" });
    out.push({ date, type: "중식", dishes: pool[i], calorie: kcal[i] + " Kcal" });
    out.push({ date, type: "석식", dishes: dinner, calorie: "588.2 Kcal" });
  }
  return out;
}
const MEAL_KOR = { "조식": "아침", "중식": "점심", "석식": "저녁" };
const MEAL_ORDER = { "조식": 0, "중식": 1, "석식": 2 };

// ── STUB — 계약(API계약-v1.md) 응답 모양 그대로 ────────────────
const STUB = {
  // GET /api/v1/me (§3.2)
  me: {
    account: { id: 1, display_name: "김하늘", email: "h***@gmail.com", phone_verified: false },
    auth_methods: [{ kind: "id_password", verified: true }],
  },
  // GET /api/v1/children (§5.1) — 목록엔 실명 없음(name은 상세 전용)
  children: [
    { id: 1, nickname: "첫째", school: { slug: null, name: "", kind: "" },
      grade: "3", class_name: "1", grade_code: 3, birth_year: 2017,
      pass: { active: true, expires_at: "2026-10-24T00:00:00.000Z", free_open_until: "20260820" },
      counts: { records: 6, activities: 3 } },
    { id: 2, nickname: "둘째", school: { slug: null, name: "", kind: "" },
      grade: "1", class_name: "2", grade_code: 1, birth_year: 2019,
      pass: { active: false, expires_at: null, free_open_until: "20260820" },
      counts: { records: 2, activities: 1 } },
  ],
  // GET /api/v1/schools/{slug} (§4.1)
  /* 학교 정보의 **빈 틀**. 값은 서버(SCHOOL.info)나 자녀 등록값이 채운다.
     ⚠ 여기에 실제 학교를 박아 두면 안 된다(2026-08-03 지시) —
       자녀를 다른 학교로 등록해도 name/slug/kind 만 덮이고 **주소·전화·홈페이지·학급수는
       견본 학교 값이 그대로 화면에 나갔다.** 못 채운 자리는 «빈칸»이 정답이다. */
  school: { slug: null, name: "", kind: "",
    sido: "", address: "", phone: "", homepage: "", sem2_start: null,
    detail: null },
  // GET …/meals (§4.2) — dishes는 {name, allergens[]} 객체 배열(회신19 확정. 문자열 배열 아님!)
  // 기간 조회(주간·월간)를 전제로 한 달치를 담는다. 실제로는 from/to를 붙여 한 번에 받아온다.
  meals: mealMonth(),
  // GET …/schedules (§4.4) — closure_type은 NEIS 휴업 유형. 중요도 필드는 없어 이름으로 분류한다(웹과 같은 규칙).
  schedules: [
    { date: "20260801", name: "여름방학", content: null, closure_type: "휴업일" },
    { date: "20260808", name: "토요휴업일", content: null, closure_type: "휴업일" },
    { date: "20260815", name: "광복절", content: null, closure_type: "공휴일" },
    { date: "20260820", name: "2학기 개학식", content: null, closure_type: null },
    { date: "20260828", name: "가을 현장체험학습", content: "종일", closure_type: null },
    { date: "20260904", name: "학부모 공개수업", content: "3~4교시", closure_type: null },
    { date: "20260921", name: "학부모 상담주간", content: "9/21~9/25", closure_type: null },
    { date: "20261003", name: "개천절", content: null, closure_type: "공휴일" },
  ],
  // GET …/timetable (§4.3) — 요일 1~5 × 교시. neis_year 리네임 반영.
  timetable: {
    neis_year: "2026", semester: "2", grade: "3", class_name: "1",
    grid: [
      ["국어", "수학", "국어", "체육", "국어"],
      ["수학", "국어", "통합", "수학", "창체"],
      ["통합", "체육", "수학", "국어", "통합"],
      ["체육", "통합", "통합", "통합", "수학"],
      ["창체", "", "음악", "미술", ""],
    ],
  },
  // GET /api/v1/children/1/records (§5.2) — period 객체·image url. 앱이 period로 그룹핑(회신19).
  records: [
    { id: 6, category: "award",       period: { school_year: 3, semester: 1, label: "초3 1학기" }, title: "교내 독서왕 상장", icon: "ti-award" },
    { id: 5, category: "report_card", period: { school_year: 3, semester: 1, label: "초3 1학기" }, title: "초3 1학기 통지표", icon: "ti-file-text" },
    { id: 4, category: "activity",    period: { school_year: 3, semester: 1, label: "초3 1학기" }, title: "과학의 날 활동", icon: "ti-flask" },
    { id: 3, category: "award",       period: { school_year: 2, semester: 2, label: "초2 2학기" }, title: "그리기 대회 입상", icon: "ti-award" },
    { id: 2, category: "report_card", period: { school_year: 2, semester: 2, label: "초2 2학기" }, title: "초2 2학기 통지표", icon: "ti-file-text" },
    { id: 1, category: "certificate", period: { school_year: 2, semester: 1, label: "초2 1학기" }, title: "한자 8급 자격증", icon: "ti-certificate" },
  ],
  // GET /api/v1/children/1/activities (§5) — days_of_week CSV(1=월), HH:MM
  activities: [
    { id: 1, type: "academy",     name: "수학학원", days_of_week: "1,3", start_time: "16:00", end_time: "17:30", color: 0 },
    { id: 2, type: "afterschool", name: "방과후 로봇", days_of_week: "2",   start_time: "14:40", end_time: "15:40", color: 3 },
    { id: 3, type: "activity",    name: "수영",       days_of_week: "4,5", start_time: "17:00", end_time: "18:00", color: 5 },
  ],
  // ── 요청28 ① 학교생활 서류 ──────────────────────────────
  // 서식 4종은 실제 학교 양식(2026학년도 서울숭미초)에서 필드를 그대로 옮겼다.
  // 원본: 에듀싱크\*.hwp 4개. 학교마다 조금씩 다르지만 뼈대는 같다.
  docSituations: [
    { key: "field",   icon: "<i class='ti ti-plane'></i>", label: "가족여행 · 체험학습",
      desc: "실시 3일 전까지" },
    { key: "absence", icon: "<i class='ti ti-mood-sick'></i>", label: "아파서 · 결석",
      desc: "결석일부터 5일 이내" },
    // 조퇴·외출증은 뺐다(2026-07-24 지시) — 실제로는 전화 한 통으로 끝나고,
    // 엄마가 데리러 가면 그냥 보내준다. 서류가 필요 없는 절차라 앱에 둘 이유가 없다.
    { key: "counsel", icon: "<i class='ti ti-message-circle'></i>", label: "선생님과 상담",
      desc: "희망 시간 3개까지" },
  ],

  // 학교가 요구하는 규칙 — 엄마들이 모르는 것들. 앱이 대신 지켜준다.
  docRules: {
    fieldQuotaDays: 19,        // 연 허용 일수(수업일수 10%)
    fieldUsedDays: 3,          // 올해 이미 쓴 일수(5월 제주 3일)
    fieldMaxRun: 10,           // 연속 최대
    fieldSafetyOver: 5,        // 연속 이 일수를 넘으면 안전확인·비상연락처 필수
    fieldApplyBefore: 3,       // 실시 며칠 전까지 신청
    fieldReportWithin: 7,      // 실시 후 며칠 이내 보고서(넘기면 미인정 결석)
    absenceWithin: 5,          // 결석일부터 며칠 이내 신고서(넘기면 미인정 결석)
    sickCertOver: 2,           // 질병결석이 이 일수를 넘으면 진단서 필수(약봉투·처방전 불인정)
  },
  // 경조사 인정 일수(결석신고서 표 그대로)
  familyEvents: [
    { label: "결혼 — 형제·자매, 부, 모", days: 1 },
    { label: "사망 — 부모, 조부모, 외조부모", days: 5 },
    { label: "사망 — 부모의 (외)조부모, 형제자매 및 그 배우자", days: 3 },
    { label: "사망 — 부모의 형제·자매 및 그 배우자", days: 3 },
    { label: "입양 — 학생 본인", days: 20 },
  ],
  // 상담 가능 시간(학년별) — 실제 서식에 적힌 그대로
  counselHours: {
    "1": "14:00~16:30 (수·금은 13:30~16:30)", "2": "14:00~16:30 (수·금은 13:30~16:30)",
    "3": "14:00~16:30 (목은 15:00~16:30)",   "4": "14:00~16:30 (목은 15:00~16:30)",
    "5": "15:00~16:30 (수는 14:00~16:30)",   "6": "15:00~16:30 (수는 14:00~16:30)",
  },

  // 제출한 서류 — 실제로는 GET /api/v1/children/{id}/documents
  documents: [
    // 신청서만 내고 보고서를 아직 안 낸 상태 — 7일 기한이 도는 중(앱이 이어주는 흐름)
    { id: 1, kind: "field", title: "제주 가족여행", from: "20260512", to: "20260514", days: 3,
      place: "제주특별자치도", endedDaysAgo: 4, reported: false },
  ],

  // GET /api/v1/schools?q= (학교 검색) — 전국 12,563개교.
  // <i class='ti ti-alert-triangle'></i> 동명 학교가 많다(실측: 금성초 11곳·교동초 9곳·삼성초 9곳) → 목록에 반드시 주소를 같이 보여줘야 고를 수 있다.
  /* ⚠ **견본 학교 목록을 두지 않는다**(2026-08-03 지시).
     여기에 실제 학교 몇 곳을 담아 두면, 서버를 못 붙였을 때 등록 화면에
     «남의 학교»가 후보로 떠서 그중 하나를 고르게 된다. 검색은 서버만 답한다 —
     못 붙으면 결과가 없다고 말하는 것이 정직하다. */
  schoolSearch: [],

  // 커뮤니티 — 웹과 같은 "반 단위 짧은 글"(같은 반 학부모끼리). 실제로는 GET/POST /api/v1/community.
  // 익명은 아니고 별명 단위. 준비물·분실물·질문 같은 생활 정보가 오간다.
  communityPosts: [
    { id: 3, author: "3학년 1반 학부모", when: "2시간 전", body: "내일 3교시 공개수업 맞죠? 주차 가능한지 아시는 분?", likes: 2, replies: 1 },
    { id: 2, author: "지호 엄마", when: "어제", body: "체육복 파란색 상의 하나 주웠어요. 이름표가 지워져 있네요. 분실하신 분 연락주세요.", likes: 5, replies: 3 },
    { id: 1, author: "3학년 1반 학부모", when: "3일 전", body: "받아쓰기 급수표 어디서 받는지 아시나요? 아이가 안 가져왔다고 해서요.", likes: 1, replies: 4 },
  ],

  // 내 일정(개인) — 특정 날짜의 병원·여행 등. 매주 반복되는 학원은 activities(방과후)가 따로 맡는다.
  // start/end 없으면 '종일'로 다룬다.
  myEvents: [
    { id: 1, date: "20260728", title: "치과 정기검진", memo: "미소치과", start: "16:00", end: "17:00" },
    { id: 2, date: "20260814", title: "할머니댁", memo: "1박 2일" },
    { id: 3, date: "20260820", title: "개학 준비물 사기", memo: "실내화·크레파스", start: "18:00", end: "19:00" },
  ],
  // 준비물(2026-07-27) — «내일 뭐 가져가?» 를 앱이 기억한다.
  // 일정과 따로 두는 이유: 준비물은 학사일정에도 내 일정에도 안 붙고 그냥 «내일» 챙기는 것이다.
  supplies: [
    { id: 1, date: "20260728", item: "실내화", memo: "이름표 붙이기", done: false },
    { id: 2, date: "20260728", item: "리코더", memo: "", done: true },
  ],

  // 초등 일과표 — 1일 다이어리에서 수업을 시간 위에 얹으려면 교시별 시각이 필요하다.
  periods: [
    { n: 1, start: "09:00", end: "09:40" }, { n: 2, start: "09:50", end: "10:30" },
    { n: 3, start: "10:40", end: "11:20" }, { n: 4, start: "11:30", end: "12:10" },
    { n: 5, start: "13:00", end: "13:40" },
  ],
  lunch: { start: "12:10", end: "13:00" },

  // ── 요청28 ② 부모→자녀 원터치 알림 ───────────────────────
  // 자주 쓰는 것 먼저. 실제로는 계정별 저장.
  noticePresets: ["4시 태권도 가", "학원 끝나면 바로 집으로", "오늘 비 와, 우산 챙겨", "저녁 먹고 와", "엄마가 조금 늦어"],
  // 한 줄기 대화(2026-07-25) — 부모→자녀 알림과 자녀 답이 같은 목록에 쌓인다.
  //   from  = 보낸 쪽("parent" | "child")
  //   seen  = 받는 쪽이 봤는가 (부모 글이면 자녀가 확인, 자녀 글이면 부모가 읽음)
  notices: [
    { id: 1, from: "parent", text: "오늘 급식에 새우 있어. 조심해", at: "07-23 08:10", seen: true },
    { id: 2, from: "child",  text: "응 알았어", at: "07-23 08:12", seen: true },
    { id: 3, from: "parent", text: "학원 끝나면 바로 집으로", at: "오늘 15:40", seen: false },  // 자녀 뷰에 «확인» 버튼이 뜬다
    { id: 4, from: "child",  text: "학원 끝났어. 지금 가는 중", at: "오늘 17:02", seen: false }, // 부모가 아직 안 읽음
  ],
  // 아이가 손가락 한 번으로 보내는 답 — 아이는 타자가 느리다. 답장은 고르는 게 기본, 쓰는 건 덤.
  childPresets: ["응 알았어", "지금 가는 중", "조금 늦어", "데리러 와줘", "학원 끝났어"],

  /* GET /api/v1/plans (§6.2) — 자녀 1명당.
     ⚠ 2026-07-28 값을 내렸다(월 10,000 → 2,900). 시장 조사 결과가 이유다 —
       급식·시간표 앱(오늘학교·김급식류)이 전부 **무료**라 만 원은 학습앱 가격대 신호를 줬다.
       다만 준비물·방과후·위젯·자녀폰·기록보관을 합쳐놓은 곳은 없어서 무료로 갈 이유도 없다.
       구글 수수료 15% + 부가세 10% 를 빼면 2,900원 중 **약 2,240원**이 남는다. */
  plans: [
    { months: 1,  amount: 2900,  discount: null,       per_month: 2900 },
    { months: 3,  amount: 7900,  discount: "9% 할인",  per_month: 2633 },
    { months: 6,  amount: 14900, discount: "14% 할인", per_month: 2483 },
    { months: 12, amount: 25000, discount: "28% 할인", per_month: 2083 },
  ],
};

const CATEGORY_KO = { award: "상장", report_card: "통지표", grade_sheet: "성적표", certificate: "자격증", activity: "활동", other: "기타" };
/* 긴 과목명이 칸에서 줄바뀜돼 지저분해지는 것을 막는다(웹 templates.js와 같은 취지).
   자주 나오는 초등 과목만 줄인다 — 모르는 이름은 건드리지 않는다. */
/* 칸에 들어갈 짧은 이름 — 시안 10b 는 **2글자**를 기준으로 잡았다.
   368px에서 5칸이면 한 칸이 약 58px 뿐이라 「즐거운 생활」이 «즐거/운생/활» 3줄로 깨졌다(2026-07-28 실측). */
const SUBJ_SHORT = { "창의적체험활동": "창체", "자율·자치활동": "자율", "동아리활동": "동아리",
  "진로활동": "진로", "봉사활동": "봉사", "안전한 생활": "안전", "통합교과": "통합",
  "즐거운 생활": "즐생", "즐거운생활": "즐생", "슬기로운 생활": "슬생", "슬기로운생활": "슬생",
  "바른 생활": "바생", "바른생활": "바생" };
const shortSubject = (v) => SUBJ_SHORT[String(v || "").trim()] || v || "";
const DAY_KO = ["월", "화", "수", "목", "금"];
/* ⛔ 동물 이모지 8종을 없앴다(2026-07-28 지시: "아이등록에 이모티콘 다 지워").
   대신 **별명 첫 글자**를 쓴다 — 연락처 앱들이 쓰는 방식이고, 아이가 둘이면
   「때 / 셋」처럼 그 자리에서 갈린다. 이모지는 기기·폰트마다 모양이 달라지기도 했다.
   사진을 넣으면 사진이 이긴다(childFace). */
const initialOf = (c) => (String(c?.nickname || c?.name || "").trim()[0] || "•");
// 홈 하단 캐러셀 — 가로로 넘기는 "지금 챙길 것" 카드들. 오늘 급식·미제출·최근 기록·메시지.
function homeCarousel() {
  const c = cur();
  const cards = [];
  const on = (k) => !S.carHidden.includes(k);          // 사용자가 끈 카드는 아예 만들지 않는다
  // 아이가 보낸 안 읽은 말 — 누르면 대화창이 바로 올라온다
  const unseen = unreadFor("parent");
  // icon 은 **클래스 이름만** 넣는다 — 아래에서 <i>로 감싼다. 태그째 넣으면 이중으로 감싸져 마크업이 깨진다(2026-07-25).
  if (unseen && on("msg")) cards.push({ cls: "m", icon: "ti-message-circle", top: `안 읽은 메시지 ${unseen}`, sub: STUB.notices[STUB.notices.length - 1].text.slice(0, 16), go: "App.openMessages()" });
  // 오늘 급식
  const meal = STUB.meals.find((m) => m.date === TODAY && m.type === "중식");
  if (meal && on("meal")) cards.push({ cls: "a", icon: "ti-bowl", top: "오늘 급식", sub: meal.dishes.slice(0, 2).map((x) => x.name).join(" · "), go: "location.hash='#meal';App.render()" });
  // 미제출 보고서
  if (on("report")) STUB.documents.filter((d) => d.kind === "field" && !d.reported).forEach((d) => {
    const left = STUB.docRules.fieldReportWithin - d.endedDaysAgo;
    cards.push({ cls: "w", icon: "ti-pencil", top: `보고서 D-${left}`, sub: "안 내면 미인정 결석", go: `App.docStart('field','report',${d.id})` });
  });
  // 내일 준비물(2026-07-27) — 오늘 저녁에 챙겨야 하는 것. «오늘»이 아니라 «내일»을 보는 게 핵심이다.
  if (on("supply")) {
    const tm = ymdPlus(TODAY, 1);
    const left = STUB.supplies.filter((s) => s.date === tm && !s.done);
    if (left.length) cards.push({ cls: "w", icon: "ti-checkbox", top: `내일 준비물 ${left.length}개`,
      sub: left.map((s) => s.item).join(" · ").slice(0, 18), go: "location.hash='#supplies'" });
  }
  // 다가오는 학교 행사 D-day(2026-07-27) — 달력은 «며칠인지», 이건 «며칠 남았는지»를 말한다.
  if (on("dday")) {
    const next = schedulesOf()
      .filter((e) => e.date >= TODAY && classifyEvent(e.name, e.closure_type) && !e.name.includes("토요휴업일"))
      .sort((a, b) => (a.date < b.date ? -1 : 1))[0];
    if (next) {
      const c2 = classifyEvent(next.name, next.closure_type);
      cards.push({ cls: "a", icon: c2.icon, top: `${ddayLabel(next.date)} ${next.name}`,
        sub: `${+next.date.slice(4, 6)}월 ${+next.date.slice(6)}일 (${weekdayKo(next.date)})`,
        go: `S.calMonth='${next.date.slice(0, 6)}';location.hash='#calendar';App.render()` });
    }
  }
  // 최근 기록
  if (STUB.records[0] && on("record")) cards.push({ cls: "b", icon: STUB.records[0].icon, top: "최근 기록", sub: STUB.records[0].title.slice(0, 16), go: `App.openRecord(${STUB.records[0].id})` });

  if (!cards.length) return "";
  const i = S.carIdx % cards.length;
  const k = cards[i];
  // 자동으로 한 장씩 부드럽게 넘어간다(auto carousel). 손으로 안 넘겨도 됨.
  return `
  <div class="carousel">
    <button class="ccard ${k.cls}" onclick="${k.go}">
      <span class="cc-ico"><i class='ti ${k.icon}'></i></span>
      <!-- ⚠️ 반드시 esc — top/sub 에는 아이가 보낸 말·기록 제목·학사일정 이름이 그대로 들어온다(2026-07-27 발견).
           서버가 걸러줄 거라고 믿지 않는다. 화면에 꽂는 마지막 지점에서 막는다. -->
      <span class="cc-txt"><b>${esc(k.top)}</b><span class="cc-sub">${esc(k.sub)}</span></span>
      <span class="cc-go"><i aria-hidden="true" class="ti ti-chevron-right"></i></span>
    </button>
    <div class="cardots">${cards.map((_, j) => `<i class="${j === i ? "on" : ""}"></i>`).join("")}</div>
  </div>`;
}

// 홈 원형 메뉴 — 켜기/끄기·순서는 사용자가 정한다(#homeedit).
// key = 설정에 저장되는 고유값(순서가 바뀌어도 이 값으로 찾는다).
// ci  = 색 번호 고정 — 순서를 바꿔도 급식은 계속 같은 색이어야 알아본다(위치에 색을 매기면 안 됨).
/* ⚠ 2026-08-02 메뉴 개편 — 격자에서 **탭·홈카드와 겹치는 항목을 목록째 뺐다.**
   급식·준비물·방과후 = 홈 큰 카드 / 일정·미션·서랍(기록) = 하단 탭 / 시간표 = 방과후 카드 상세.
   같은 곳으로 가는 문이 두 개면 «어느 게 진짜냐»를 화면이 설명해야 한다.
   라벨은 동사형 — 자주 안 쓰는 기능일수록 이름만 보고 뭘 하는 건지 알아야 한다(지시).
   옛 key 는 저장된 menuOrder 에 남아 있어도 menuOf() 가 걸러서 안전하다. */
const HOME_MENU = [
  { key: "notify",   ci: 6, icon: "ti-bell",     label: "알림", go: () => { location.hash = "#notify"; } },
  /* 라벨은 2~4자 명사(2026-08-02 지시 — 한 줄 고정). 동사 설명은 진입한 화면이 한다. */
  { key: "after",    ci: 3, icon: "ti-run",      label: "방과후", go: () => { location.hash = "#afterschool"; } },
  { key: "docs",     ci: 5, icon: "ti-file-text",label: "체험학습", go: () => { location.hash = "#docs"; } },
  { key: "school",   ci: 7, icon: "ti-school",   label: "학교정보", go: () => { S.schoolTab = "info"; location.hash = "#school"; } },
  { key: "community",ci: 3, icon: "ti-messages", label: "커뮤니티", go: () => { S.schoolTab = "community"; location.hash = "#school"; } },
];
const MENU_KEYS = HOME_MENU.map((m) => m.key);
const menuOf = (k) => HOME_MENU.find((m) => m.key === k);
/* 홈 격자에 올라가는 것 = 켠 것, 저장된 순서대로.
   끈 것은 사라지지 않는다 — 홈 맨 아래 «한 줄»로 내려간다(homeMoreItems). */
const homeMenuItems = () => S.menuOrder.map(menuOf).filter((m) => m && !S.menuHidden.includes(m.key));
const homeMoreItems = () => S.menuOrder.map(menuOf).filter((m) => m && S.menuHidden.includes(m.key));
// 개편 후 다섯 개뿐이라 전부 격자에 올린다. (예전엔 넷을 기본으로 내렸다)
const MENU_OFF_DEFAULT = [];

// ── 맨 밑 대화창(2026-07-25) — 엄마↔자녀 양방향 ────────────────
// 닫혀 있을 땐 화면 맨 밑 작은 바 하나. 누르면 올라온다. 홈과 자녀 뷰에서 같은 부품을 쓴다.
// 역할은 목업 스위치(S.childView)로 갈리고, 실앱은 로그인 계정 종류로 갈린다.
// 준비물 날짜 라벨 — 「내일 · 8월 18일 화」. 오늘·내일은 이름으로 부른다(시안 10d).
/* 점심시간 — 학교·학년마다 다르다(저학년은 4교시 뒤, 고학년은 5교시 뒤).
   NEIS가 안 주는 값이라 **사용자가 고친다.** 안 고쳤으면 학교 기본값을 쓴다.
   시간표·하루 일정 세 곳이 다 이 함수를 본다 — 값을 각자 읽으면 한 곳만 고치는 사고가 난다. */
const lunchOf = () => ({
  after: S.lunchAfter ?? 4,
  start: S.lunchTime?.start || STUB.lunch.start,
  end: S.lunchTime?.end || STUB.lunch.end,
});

const supDayLabel = (d) => {
  const head = d === TODAY ? "오늘 · " : d === ymdPlus(TODAY, 1) ? "내일 · " : "";
  return `${head}${+d.slice(4, 6)}월 ${+d.slice(6)}일 ${weekdayKo(d)}`;
};

const myRole = () => (S.childView ? "child" : "parent");
// 내가 아직 안 본, 상대가 보낸 말의 수
const unreadFor = (role) => STUB.notices.filter((n) => n.from !== role && !n.seen).length;

function chatDock() {
  /* 🔇 고정 대화바 제거(2026-08-03 사장님: "고정으로 되어있는데 없애버려").
     자녀에게 한 줄 보내기는 알림 화면(#notify)에 그대로 있다.
     되살리려면 아래 return "" 한 줄만 지우면 된다 — 시트·읽음처리 코드는 다 살아 있다. */
  return "";
  const c = cur();
  const role = myRole();
  const you = role === "parent" ? esc(c.nickname) : "엄마";
  const last = STUB.notices[STUB.notices.length - 1];
  if (!S.chatOpen) {
    const un = unreadFor(role);
    return `
    <button class="chatbar" onclick="App.chatOpen()">
      <!-- 분홍 원형 아이콘을 뺐다(2026-07-28, 시안 10g) — 화면에서 유일하게 남은 파스텔이라 혼자 떴다.
           자녀 아바타(사진 또는 캐릭터)를 쓰면 «누구와의 대화인지»까지 말해준다. -->
      ${childFace(c, "cb-face")}
      <span class="cb-txt"><b>${you}</b><span class="cb-last">${last ? esc(last.text.slice(0, 20)) : "대화를 시작해요"}</span></span>
      ${un ? `<span class="cb-badge">${un}</span>` : ""}
      <span class="cb-up"><i class='ti ti-chevron-up'></i></span>
    </button>`;
  }
  const presets = role === "parent" ? STUB.noticePresets : STUB.childPresets;
  return `
  <div class="chatdim" onclick="App.chatClose()"></div>
  <div class="chatsheet">
    <div class="cs-hd">
      <b>${you}</b>
      <button class="iconbtn ghosticon" onclick="App.chatClose()" aria-label="대화창 닫기"><i class='ti ti-chevron-down'></i></button>
    </div>
    <div class="cs-body" id="csbody">
      <!-- 내 말 옆 «1» = 상대가 아직 안 봤다. 보면 사라진다(카톡과 같은 규칙 — 설명이 필요 없다) -->
      ${STUB.notices.map((n) => {
        const mine = n.from === role;
        return `
        <div class="bub ${mine ? "me" : "you"}">
          <span class="bb">${esc(n.text)}</span>
          <span class="bt">${mine && !n.seen ? `<b class="unread1">1</b>` : ""}${n.at}</span>
        </div>`;
      }).join("")}
    </div>
    <!-- 아이도 엄마도 대부분 여기서 끝난다 — 타자는 마지막 수단 -->
    <div class="cs-presets">${presets.map((p) => `<button class="preset" onclick="App.chatSend('${jsq(p)}')">${p}</button>`).join("")}</div>
    <div class="cs-input">
      <input id="ci" placeholder="${role === "parent" ? esc(c.nickname) + "에게" : "엄마에게"} 보낼 말" value="${esc(S.chatText)}"
             oninput="S.chatText=this.value" onkeydown="if(event.key==='Enter')App.chatSend()">
      <button class="cs-send" onclick="App.chatSend()" aria-label="보내기"><i class='ti ti-send'></i></button>
    </div>
  </div>`;
}

// 홈 캐러셀에 넣을 수 있는 카드 종류 — 사용자가 켜고 끈다(#homeedit).
const CAR_CARDS = [
  { key: "msg",    label: "안 읽은 메시지", desc: "자녀가 보낸 답이 있을 때만" },
  { key: "meal",   label: "오늘 급식", desc: "오늘 점심 메뉴 두 가지" },
  { key: "report", label: "보고서 D-day", desc: "안 내면 미인정 결석" },
  { key: "record", label: "최근 기록", desc: "마지막으로 올린 사진" },
  { key: "supply", label: "내일 준비물", desc: "아직 안 챙긴 것만" },
  { key: "dday",   label: "다가오는 학교 행사", desc: "며칠 남았는지" },
];
const won = (n) => n.toLocaleString("ko-KR") + "원";

// 회원가입 유효성 — 한 칸씩. 틀리면 사유를 돌려주고, 맞으면 null.
// 실앱은 이걸 클라이언트에서만 믿지 말고 서버(§3.3)에서도 같은 규칙으로 막아야 한다(중복 확인 포함).
function regCheck(key, v) {
  v = (v || "").trim();
  switch (key) {
    case "userid":
      if (!/^[a-zA-Z0-9]+$/.test(v)) return "영문·숫자만 쓸 수 있어요";
      if (v.length < 4) return "4자 이상이어야 해요";
      return null;
    case "pw":
      if (v.length < 8) return "8자 이상이어야 해요";
      if (!/[a-zA-Z]/.test(v) || !/[0-9]/.test(v)) return "영문과 숫자를 함께 넣어주세요";
      return null;
    case "pw2":
      return v === (S.reg.pw || "") ? null : "비밀번호가 서로 달라요";
    case "name":
      return v.length >= 2 ? null : "이름을 확인해 주세요";
    case "birth":
      if (!/^\d{8}$/.test(v)) return "8자리 숫자로 적어주세요 (예: 19850312)";
      { const y = +v.slice(0, 4), m = +v.slice(4, 6), d = +v.slice(6);
        if (y < 1900 || y > 2020 || m < 1 || m > 12 || d < 1 || d > 31) return "생년월일을 다시 확인해 주세요"; }
      return null;
    case "email":
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) ? null : "이메일 형식이 맞지 않아요";
    case "phone":
      if (!v) return null;                          // 선택 항목
      return /^01\d{8,9}$/.test(v.replace(/-/g, "")) ? null : "휴대폰 번호를 확인해 주세요";
    default: return null;
  }
}
// 필수 칸이 전부 통과했는지
function regValid() {
  const r = S.reg;
  const required = ["userid", "pw", "pw2", "name", "birth", "email"];
  if (required.some((k) => !r[k] || regCheck(k, r[k]))) return false;
  if (r.phone && regCheck("phone", r.phone)) return false;
  return r.t1 && r.t2;
}

/* ═══ 화면에 글자 넣기 — 이스케이프 (2026-07-25) ═══════════
   이 앱은 화면을 innerHTML로 통째로 다시 그린다. 사람이 쓴 글(대화·커뮤니티·별명·서류)과
   서버에서 온 값(학교 이름·주소·급식 메뉴)을 그대로 끼워 넣으면 **그게 HTML로 실행된다.**
   브라우저면 낙서로 끝나지만, 우리는 **Capacitor 웹뷰**다 — 스크립트가 돌면
   카메라·지문·파일·푸시 플러그인(window.Capacitor.Plugins)까지 그대로 잡힌다.

   규칙: 사람이 쓴 값·서버에서 온 값은 **반드시 esc()** 를 거친다.
        onclick="App.f('…')" 처럼 **인라인 JS 문자열** 안에 넣을 땐 jsq().
   ═══════════════════════════════════════════════════════════ */
const ESC_MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (v) => (v == null ? "" : String(v).replace(/[&<>"']/g, (ch) => ESC_MAP[ch]));
// 줄바꿈을 살려야 하는 긴 글(서류 내용·상담 내용) — 이스케이프 먼저, <br>는 그 다음
const escBr = (v) => esc(v).replace(/\n/g, "<br>");
// 인라인 JS 문자열 안에 들어갈 값. JS로 먼저 막고(따옴표·역슬래시·개행), 그 위에 HTML 이스케이프.
const jsq = (v) => esc(String(v == null ? "" : v).replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/\r?\n/g, "\\n"));

/* ═══ 서버 연결 (2026-07-25) ═══════════════════════════════
   목업은 지금까지 스텁만으로 혼자 돌았다. 여기서부터 **진짜 API**를 부른다.
   원칙: 서버가 없거나 죽어도 목업은 계속 돌아야 한다 — 실패하면 스텁으로 되돌아간다.
     (대표님이 목업을 클릭 검수하는 동안 워커를 안 띄웠다고 화면이 멈추면 안 된다)

   주소: 아직 **배포 0회**라 로컬 워커(8788)를 본다. 배포하면 여기 한 줄만 바꾸면 된다.
   CORS: 워커 쪽 api_core.js 의 허용 목록에 이 출처들이 들어 있어야 한다.
   ═══════════════════════════════════════════════════════════ */
/* 서버 주소.
   ⚠ 기기마다 «PC를 가리키는 이름»이 다르다 —
     실기기(USB/무선): adb reverse 로 localhost 가 PC를 가리킨다
     LDPlayer 등 일부 에뮬레이터: adb reverse 가 안 먹어서 **PC의 LAN IP**로 붙어야 한다
   그래서 저장된 값이 있으면 그걸 먼저 쓴다. 배포하면 이 기본값만 배포 주소로 바꾸면 된다.
     바꾸는 법(개발용): localStorage.setItem("eduthink.api","http://172.30.1.19:8788") 후 새로고침 */
const API_BASE = (() => {
  if (location.port === "8788") return "";
  try { const v = localStorage.getItem("eduthink.api"); if (v) return v.replace(/\/$/, ""); } catch (e) {}
  return "https://eduthink-site-renderer.dndmotor1.workers.dev";   // 실서버(2026-07-27 배포)
})();
const API_TIMEOUT = 6000;                       // 서버가 없으면 6초 안에 포기하고 스텁으로
const UPLOAD_TIMEOUT = 60000;                   // 사진 업로드는 오래 걸린다 — 따로 넉넉히

// ── 로그인 토큰 ───────────────────────────────────────────
// access는 짧고 refresh는 길다(계약 §3.1). 앱은 이걸 들고 다녀야 기록을 올리고 볼 수 있다.
// 목업 단계라 localStorage에 둔다. 실앱은 안드로이드 키스토어(암호화 저장)로 옮긴다 — 그때 여기만 고치면 된다.
const TOKENS = { access: null, refresh: null };
const TOKEN_KEY = "eduthink.tokens";
function saveTokens(t) {
  if (t) { TOKENS.access = t.access_token || t.access || null; TOKENS.refresh = t.refresh_token || t.refresh || null; }
  else { TOKENS.access = TOKENS.refresh = null; }
  try { t ? localStorage.setItem(TOKEN_KEY, JSON.stringify(TOKENS)) : localStorage.removeItem(TOKEN_KEY); } catch (e) {}
}
function loadTokens() {
  try { Object.assign(TOKENS, JSON.parse(localStorage.getItem(TOKEN_KEY) || "{}")); } catch (e) {}
}
/* 지금 들고 있는 게 **자녀 토큰인가**. 화면 게이트의 근거는 반드시 여기여야 한다.
   ⚠ S.childView 를 근거로 쓰면 안 된다 — 그건 부모가 미리보기로 켜는 목업 스위치라
      앱이 다시 켜지거나 상태가 한 번 흐트러지면 그냥 false 가 된다.
   2026-08-02 폰 실측: 자녀폰에서 카메라를 다녀오자 부모 홈이 그대로 떴다
   (체험 남은 날·이용권·설정·서랍 썸네일까지). 서버는 막았지만 화면이 안 막혔다.
   토큰 서명은 검증하지 않는다 — 여기서 하는 건 «무엇을 보여줄까»지 «무엇을 허락할까»가 아니다.
   진짜 허락은 서버가 한다(자녀 토큰은 /me·/children·/records·/orders 전부 FORBIDDEN). */
function isChildToken() {
  const t = TOKENS.access;
  if (!t) return false;
  try {
    const b = t.split(".")[1];
    if (!b) return false;
    const j = JSON.parse(decodeURIComponent(escape(atob(b.replace(/-/g, "+").replace(/_/g, "/")))));
    return j.role === "child";
  } catch (e) { return false; }
}

// 서버 호출. 로그인돼 있으면 토큰을 자동으로 붙이고, access가 만료되면 **한 번만** 갱신하고 재시도한다.
async function api(path, { method = "GET", body, form, timeout, reauth, _retry } = {}) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), timeout || (form ? UPLOAD_TIMEOUT : API_TIMEOUT));
  try {
    const res = await fetch(`${API_BASE}/api/v1${path}`, {
      method, signal: ac.signal,
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),      // form은 브라우저가 경계문자열까지 넣어야 하므로 손대지 않는다
        ...(TOKENS.access ? { Authorization: "Bearer " + TOKENS.access } : {}),
        ...(reauth ? { "X-Reauth-Token": reauth } : {}),   // 수정·삭제처럼 무거운 요청에만 실린다(계약 §3.4)
      },
      body: form || (body ? JSON.stringify(body) : undefined),
    });
    const j = await res.json();
    // access가 만료됐으면 refresh로 새로 받아 한 번 더 — 사용자는 다시 로그인할 필요가 없다
    /* 자녀폰은 refresh 가 없다 — 토큰이 죽으면(만료·부모가 끊음) 그걸로 끝이다.
       조용히 로그인으로 튕기지 말고 아이 눈높이 안내 화면으로(2026-08-02 구멍 2-2). */
    if (!j?.ok && ["AUTH_EXPIRED", "AUTH_INVALID", "AUTH_REQUIRED"].includes(j?.error?.code)
        && isChildToken() && !TOKENS.refresh && !S.childLinkEnded) {
      S.childLinkEnded = true;
      location.hash = "#childexpired";
      setTimeout(() => App.render(), 0);
    }
    if (!j?.ok && j?.error?.code === "AUTH_EXPIRED" && TOKENS.refresh && !_retry) {
      const r = await api("/auth/refresh", { method: "POST", body: { refresh_token: TOKENS.refresh }, _retry: true });
      if (r?.ok) { saveTokens(r.data); return api(path, { method, body, form, timeout, reauth, _retry: true }); }
      saveTokens(null);
    }
    return j;
  } catch (e) {
    /* 🔌 인터넷이 끊기거나 시간이 초과되면 fetch가 **예외를 던진다**(2026-07-27 실측).
       여태 그대로 밖으로 새서, 호출한 쪽의 `if (r?.ok)` 는 아예 실행되지 않았다.
       → 화면에는 넣은 것처럼 남고 서버엔 없는 «유령 줄»이 생긴다(준비물 추가에서 재현).
       호출부를 전부 try/catch로 감싸는 대신 **여기서 봉투 모양으로 맞춰** 돌려준다.
       그러면 기존 `if (r?.ok)` 검사가 전부 그대로 옳게 동작한다. */
    const offline = e && (e.name === "AbortError" || String(e.message || "").includes("fetch"));
    return { ok: false, error: {
      code: offline ? "NETWORK" : "SERVER",
      message: offline ? "인터넷 연결을 확인해 주세요." : "일시적인 오류예요. 잠시 후 다시 시도해 주세요.",
    } };
  } finally { clearTimeout(t); }
}

/* ═══ 사진 줄이기 (2026-07-25) ═══════════════════════════
   폰 사진은 한 장 5~12MB다. 그대로 올리면 느리고 R2 비용이 든다.
   계약 §5.3: **원본 긴 변 2000px·JPEG 0.85 / 썸네일 480px·0.7**, 서버 상한 4MB·10장.
   캔버스로 다시 그리면 **EXIF(찍은 위치·기기)가 자동으로 지워진다** — 아이 사진에 집 좌표가
   붙어 나가면 안 되므로 이건 부가효과가 아니라 요구사항이다.
   (계약 메모엔 "앱엔 캔버스가 없다"고 적혀 있지만 Capacitor 웹뷰는 크롬이라 캔버스가 있다.) */
const IMG = { long: 2000, quality: 0.85, thumbLong: 480, thumbQuality: 0.7 };

function loadImage(src) {
  return new Promise((res, rej) => {
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => rej(new Error("사진을 읽지 못했어요"));
    /* ⚠ crossOrigin 을 무조건 붙이면 **카메라 사진이 통째로 안 읽힌다**(2026-07-27).
       Capacitor 가 주는 경로(capacitor://…, https://localhost/_capacitor_file_/…)는
       CORS 헤더를 안 보내므로 anonymous 로 요청하면 브라우저가 거부해 onerror 로 떨어진다.
       → 화면에는 «사진을 줄이는 중 문제가 생겼어요»만 뜨고 저장이 안 됐다.
       (data: URL 로 시험했을 땐 통과해서 한참 못 잡았다.)
       **다른 출처일 때만** 붙인다 — 캔버스 오염을 막아야 하는 건 그 경우뿐이다. */
    try {
      const u = new URL(src, location.href);
      if (u.origin !== location.origin && u.protocol !== "data:" && u.protocol !== "blob:") {
        im.crossOrigin = "anonymous";
      }
    } catch (e) { /* 상대경로·data: 등 — 그냥 붙이지 않는다 */ }
    im.src = src;
  });
}

// 그릴 대상(이미지든 캔버스든)을 긴 변 max로 맞춰 새 캔버스에 그린다
function drawScaled(srcEl, srcW, srcH, max) {
  const scale = Math.min(1, max / Math.max(srcW, srcH));
  const w = Math.round(srcW * scale), h = Math.round(srcH * scale);
  const cv = document.createElement("canvas");
  cv.width = w; cv.height = h;
  const cx = cv.getContext("2d");
  cx.imageSmoothingQuality = "high";
  cx.fillStyle = "#fff"; cx.fillRect(0, 0, w, h);      // 투명 배경이 검게 나오는 것 방지
  cx.drawImage(srcEl, 0, 0, w, h);
  return cv;
}
/* JPEG로 굽기 — ⚠ `canvas.toBlob()` 을 쓰면 **안 된다**(2026-07-27 실측, 갤럭시 Z Fold6).
     toBlob        4070ms
     toDataURL       48ms  ← 같은 105KB 결과인데 **85배** 빠르다
     OffscreenCanvas 4065ms (convertToBlob 도 같은 길을 탄다)
   크기와 무관하게 4초로 일정했다 — 인코딩이 아니라 웹뷰가 어딘가에서 기다린다는 뜻이다.
   그래서 사진 2장 저장에 29초가 걸렸다(굽기 4번 × 4초 + 업로드).
   toDataURL 로 굽고 fetch 로 Blob 을 만든다(9ms). 결과 파일은 완전히 같다. */
const toBlob = async (cv, q) => {
  const url = cv.toDataURL("image/jpeg", q);
  return (await fetch(url)).blob();
};

/* 사진 한 장 → { 원본(줄인 것), 썸네일 }
   ⚠ 성능이 곧 기능이다 — 정본 §0의 승부처가 "넣는 데 30초"다.
   예전엔 원본을 **두 번 해독**해서(큰 것·썸네일 따로) 3000×4000 한 장에 3초씩 걸렸다.
   지금은 **한 번만 해독**하고, 썸네일은 이미 줄여둔 캔버스를 다시 줄여서 만든다.
   480px를 4000px가 아니라 2000px에서 뽑으니 그리는 양도 1/4이다. (2026-07-26 실측 개선) */
async function prepShot(src) {
  const im = await loadImage(src);
  const big = drawScaled(im, im.naturalWidth, im.naturalHeight, IMG.long);
  const small = drawScaled(big, big.width, big.height, IMG.thumbLong);
  const [full, thumb] = await Promise.all([
    toBlob(big, IMG.quality), toBlob(small, IMG.thumbQuality),
  ]);
  return { full, thumb };
}

// ── 앱 상태 (목업 전용 — 실앱에서는 저장소/토큰) ───────────────
/* 어두운 테마로 치는 키 목록 — 2026-08-02에 테마를 2벌로 줄이면서 생겼다.
   옛 키(흑연·심야·재)를 저장해 둔 사람이 있어서 «어둡게»에 접어 넣는다. style.css 도 같은 목록을 쓴다. */
const DARK_THEMES = ["dark", "lavender", "navy", "charcoal"];

/* ── 테마 세트 (2026-08-03 지시서 0803-1 §6) ────────────────────
   라이트/다크(=UI 토큰)는 그대로 두고 그 위에 «배경 그림 + 포인트 색» 한 겹만 얹는다.
   여기에 한 줄 추가하고 style.css 에 색 두 줄을 넣으면 테마가 하나 는다 — 그게 전부다.
   ⚠ 그림은 전부 신규 제작 예정이다. 지금은 그라데이션 자리만 잡혀 있고,
     파일이 나오면 style.css 의 --art-img 만 채우면 이 목록은 안 건드려도 된다. */
/* ── 첫 실행 설문 (§5) ─────────────────────────────────────────
   **답이 앱에 쓰이는 것만 묻는다.** 나이·성별처럼 안 쓰는 건 묻지 않는다 —
   묻고 안 쓰면 그건 그냥 개인정보 수집이다.
     who  → 앱 말투("어머니/아버지") · 나중에 자녀 앱 «엄마한테 보내기» 호칭
     kids → 설문 끝나고 자녀 등록으로 곧장 보낸다
     need → 코치마크 첫 장을 그 쪽으로 돌린다 */
const OB_Q = [
  { key: "who", q: "아빠세요, 엄마세요?", s: "앱이 부르는 말을 맞춰 둘게요",
    opts: [["mom", "엄마예요"], ["dad", "아빠예요"], ["etc", "그 외 보호자예요"]] },
  { key: "kids", q: "자녀가 몇 명이세요?", s: "이어서 아이를 등록할 거예요",
    opts: [["1", "한 명"], ["2", "두 명"], ["3", "세 명 이상"]] },
  /* 2026-08-03 지시로 «뭐가 제일 필요하세요»(need) 를 나이대로 바꿨다.
     ⚠ need 는 **코치마크 첫 장 문구**를 골라 주고 있었다(COACH_FIRST).
       이제 안 오므로 그 자리는 기본 문구로 떨어진다 — 화면은 안 깨진다.
       need 를 되살리려면 문항을 하나 더 만들지 말고 이 자리를 되돌릴 것(설문은 3문항으로 못 박았다).
     ⚠ 나이대는 **개인정보다.** 개인정보처리방침 수집항목과 스토어 「데이터 보안」 양식에
       반드시 올려야 한다. 안 올리고 받으면 최소수집 원칙 위반이다. */
  { key: "age", q: "나이대가 어떻게 되세요?", s: "또래 부모님들이 뭘 쓰는지 참고해요",
    opts: [["20", "20대"], ["30", "30대"], ["40", "40대"], ["50", "50대 이상"]] },
];
/* 소개 슬라이드 3장 (§5) — 그림이 주인공이라 글은 짧다.
   ⚠ 그림 파일은 **아직 없다.** style.css 의 `--intro-1~3` 을 채우면 그대로 걸린다(슬롯 방식). */
const INTRO_SLIDES = [
  { t: "학교 소식이 저절로", s: "급식 · 시간표 · 학사일정을 매번 찾아보지 않아도 돼요" },
  { t: "잔소리 대신 미션", s: "아이가 스스로 해내고 도장을 받아요. 시키는 사람이 안 돼도 됩니다" },
  { t: "6년이 서랍에 쌓여요", s: "상장 · 통지표는 사진 한 장이면 끝. 학년별로 정리돼요" },
];
const COACH_KEY = "eduthink.coachSeen";   // 코치마크는 계정당 한 번만 뜬다

const ART_SETS = [
  { key: "theme_01", label: "서재" },
  { key: "theme_02", label: "은행나무길" },
  { key: "theme_03", label: "언덕 우체통" },
  { key: "theme_04", label: "밤 마을" },
  { key: "theme_05", label: "노을 골대" },
  { key: "theme_06", label: "가을 길" },
  { key: "theme_07", label: "눈 오두막" },
  { key: "theme_08", label: "반딧불 숲" },
  { key: "theme_09", label: "별 산맥" },
  { key: "theme_10", label: "바다 요트" },
  { key: "theme_11", label: "벚꽃 길" },
  { key: "theme_12", label: "별똥별 밤" },
  { key: "theme_13", label: "구름 기구" },
  { key: "theme_14", label: "벽난로" },
  { key: "theme_15", label: "겨울 공원" },
  { key: "theme_16", label: "창가 책상" },
  { key: "theme_17", label: "라벤더 들판" },
  { key: "theme_18", label: "등대" }
];

const S = {
  loggedIn: false,
  theme: "light",         // 앱 테마 — 밝게 / 어둡게 두 벌 (2026-08-02, 그 전엔 6종)
  kidTheme: null,         // 자녀 앱 테마 (pastel/quest) — null 이면 첫 실행 = 고르는 화면
  kidAccent: null,        // 자녀 앱 포인트 색 키
  kidHooray: null,        // 방금 끝낸 미션 축하 오버레이 {title, stars}
  kidShootId: null,       // 사진 인증 화면이 보고 있는 미션 id
  kidTTDay: "today",      // 자녀 시간표 — 오늘/내일
  mealDraft: { stars: 0, best: null },    // 급식 평가 — 별점(1~5) + 제일 맛있던 것 하나
  friends: [],            // 아이가 넣어둔 친구 이름 — 한 번 넣으면 다음부터 칩으로 뜬다
  friendDraft: { picked: [], alone: false, adding: null },
  friendLogged: false,    // 오늘 «누구랑 놀았어»를 이미 했나 (실앱은 서버가 판정)
  friendBusy: false,
  linkWarn: false,        // 자녀폰 미연결 안내 팝업 (물음표를 눌렀을 때만)
  deckIdx: 0,             // 자녀 홈 카드 덱에서 보고 있는 장
  classNames: null, classBusy: false,   // 그 학교·학년의 «실제» 반 이름 (없으면 숫자로 폴백)
  report: null, reportMonth: null, reportBusy: false,   // 부모 월간 리포트
  kidTab: "daily",        // 자녀 미션 탭 — daily(일일 퀘스트) | quest(의뢰)
  subjectBest: null,      // 오늘 제일 재밌었던 과목
  subjectLogged: false,
  subjectBusy: false,
  mealRated: false,       // 오늘 급식 평가를 이미 했나 (실앱은 서버가 판정)
  mealBusy: false,        // 급식 평가 보내는 중 — 두 번 누르기 방지
  childLinkEnded: false,  // 자녀 토큰이 만료·해제됨 — 전용 안내 화면으로
  carIdx: 0,              // 홈 캐러셀 현재 카드
  // ── 홈 편집(사용자 설정) — 실앱은 서버(계정 설정)에, 목업은 localStorage에 담는다
  menuOrder: [...MENU_KEYS],   // 원형 메뉴 순서
  menuHidden: [...MENU_OFF_DEFAULT],   // 카드에서 내린 것 — 홈 맨 아래 한 줄로 간다
  carHidden: [],               // 끈 캐러셀 카드 key
  carAuto: true,               // 캐러셀 자동 넘김
  holiOff: false,              // 홈에서 공휴일 일정 빼기(2026-07-31 «광복절 굳이» 지시) — 학교탭 달력엔 그대로 둔다
  marketing: null,             // 광고성 수신 동의 {email,sms,call} — /me 가 채운다. null=아직 모름
  editMode: false,             // 홈 편집 화면에서 드래그 중인지(재렌더 억제용)
  currentChildId: 1,
  bioUnlocked: false,     // §4.5 열람 잠금 — 세션당 1회
  appLock: false,         // 앱 잠금 켬/끔 (내정보에서 설정 · 저장됨)
  appLocked: false,       // 지금 잠겨 있나 — 켠 상태로 앱을 켜거나 오래 자리를 비우면 true
  uploadStep: 0,          // 0 카메라 · 1 미리보기 · 2 저장됨
  shots: [],              // 앞·뒤 여러 장 [{web, path}] — 한 기록에 묶는다
  ocrText: null, ocrBusy: false,   // OCR 원문 · 진행중
  uploadTitle: null,               // OCR로 뽑은/입력한 제목
  zoomIdx: null,                   // 미리보기에서 크게 보는 사진 인덱스
  uploadBusy: false,      // 사진 줄이고 올리는 중 — 저장 버튼이 두 번 눌리지 않게
  tlLevel: null,          // 보고 있는 학교급 0초·1중·2고 (null=지금 다니는 곳)
  tlOpen: null,           // 기록 화면에서 펼친 학년 하나(null=지금 학년, -1=전부 접힘). 시안대로 한 번에 하나만 편다
  recSearch: false,       // 서랍의 검색칸을 폈나
  recQ: "",               // 기록 검색어 — 비면 평소 학년 아코디언으로 돌아간다
  // ── 고객센터 (2026-08-01) ──
  faqQ: "",               // 자주 묻는 질문 검색어
  faqOpen: null,          // 펼친 질문 하나(검색 중엔 전부 펼침)
  faqSec: null,           // 펼친 갈래 하나. null = 전부 접힘(기본)
  inquiries: null,        // 내 문의 목록 (null = 아직 안 받아옴)
  askDraft: { category: "data", title: "", body: "", contact_email: "" },
  askBusy: false,         // 보내는 중 — 버튼 두 번 눌림 방지
  askOpen: null,          // 내 문의에서 펼친 건
  uploadType: "상장", uploadGrade: "", uploadSem: "", uploadDate: null, savedLabel: null,   // 업로드 종류·학년·학기·날짜
  uploadPeriod: null,
  viewRecord: null, recordMenuOpen: false, pageIdx: 0, zoomed: false,   // 기록 크게 보기 · 페이지 · 확대
  recordEdit: false, editTitle: null, editType: null, editPeriod: null, editDate: null, // 저장 후 수정
  pushToken: null, _pushWired: false,        // FCM 토큰 · 리스너 1회 등록 플래그
  planSel: 3,
  schoolTab: "info",
  reauthThen: null,       // 재인증 대상 설명
  reauthAction: null,     // 최종 확인 통과 시 실행할 함수
  reauthStage: 1,         // 1 본인확인 · 2 최종 삭제 확인
  planDraft: null,        // 방과후 빈 칸을 눌렀을 때 입력 바에 담기는 값
  planKill: null,         // 지우기 확인 중인 일정 {id, name} — L4 창(시안 10f)
  mealRange: "week",      // 급식 보기 범위 — 주간 · 월간
  mealQuery: "",          // 급식 메뉴 검색어
  supMemoOpen: false,     // 준비물 메모칸을 폈나 — 평소엔 접는다(시안 10d: 입력은 한 줄)
  mealSearchOpen: false,  // 메뉴 검색칸을 폈나 — 시안 10a 는 평소엔 접어둔다(메뉴가 주인)
  myAllergens: [5, 6],    // 우리 아이 알레르기 코드(예시: 대두·밀). 실제로는 자녀 정보에 저장
  mealAlarms: [],         // 알람 켠 "날짜|끼니" 들 — 실앱은 네이티브 로컬 푸시 예약
  mealType: "중식",       // 보고 있는 끼니
  allergenOpen: false,    // 알레르기 18종 칩 — 기본은 접어둔다(펼치면 화면을 다 먹는다)
  gradesOpen: false,      // 학년별 현황 — 기본 접힘(웹 §지시서9와 같은 규칙)
  childDraft: { grade: "3", class_name: "1", nickname: "", name: "", agree: false, school: null },
  childEditId: null,      // 자녀 수정 중인 id (null이면 신규 등록)
  schoolQuery: "",        // 학교 검색어
  schoolHits: null,       // 검색 결과 (null = 아직 안 찾음)
  schoolBusy: false,      // 서버에 물어보는 중
  schoolFrom: "server",   // server | stub — 서버를 못 붙으면 스텁으로 대체한 표시
  communityDraft: "",     // 커뮤니티 한 마디 작성 중
  communityOpen: null,    // (구) 펼쳐 본 글 id
  // ── 커뮤니티 = 오픈채팅 (2026-08-01) ──
  commJoined: false,      // 이 자녀가 방에 참여했나
  commPosts: [],          // 받아온 대화 (참여 시점 이후만 온다)
  commSince: 0,           // 마지막으로 받아간 글 id — 새 것만 이어 받는다
  commBusy: false,        // 참여·전송 중
  commMenuFor: null,      // 눌러서 연 신고·차단 시트의 대상 글 id
  commLeaveAsk: false,    // 나가기 확인 시트
  commTimer: null,        // 새 대화 받아오는 타이머
  planList: null,         // 서버가 준 요금표(자녀 자리값 반영). null = 아직 안 받음 → STUB.plans 폴백
  planSeat: 1,            // 이 자녀가 몇 번째 자리인가 — 둘째부터 값이 내려간다
  devices: [],            // 이 계정을 보는 폰 목록(엄마·아빠). 2대까지
  deviceLimit: 2,
  // ── 미션 (2026-08-01) ──
  missions: null,         // 오늘 것 (null = 아직 안 받아옴)
  missionStars: 0,        // 모은 도장
  missionBusy: null,      // 지금 처리 중인 미션 id — 버튼 두 번 눌림 방지
  missionCatalog: null,   // 학년대별 카탈로그 캐시 { low:[], mid:[], high:[] }
  pickBand: null,         // 미션 고르기 화면에서 보고 있는 학년대
  missionPick: [],        // 시트에서 고른 code 들
  msDetail: null,         // 카드 상세 시트에 띄운 미션 id (2026-08-03 카드판)
         // 카드 상세 시트에 띄운 미션 id (2026-08-03 카드판)
  /* ── 스타코인 상점 · 2단계 보상 (2026-08-07 지시서 §3·§5) ──────────────────
     ⚠ 잔액(스타코인)은 **여기 따로 세지 않는다.** `missionStars` 하나만 본다 —
       서버도 `star_ledger` 원장 하나로 세고, 상점 결제는 거기 «음수»로 적힌다.
       화면에 두 번째 숫자를 만들면 반드시 어긋나고, 그때부터 어느 쪽이 맞는지 아무도 모른다.
     ⚠ 살 수 있는지(`can_buy`)도 **화면이 다시 계산하지 않는다.** 서버가 준 값을 그대로 쓴다.
       주간·월간 상한은 서버만 정확히 셀 수 있다(앱을 껐다 켜면 화면 계산은 초기화된다). */
  store: null,            // 진열대 [{item_id,title,stars_required,limit_type,limit_count,used,can_buy,reason}]
  rewards: null,          // 티켓(영수증) [{reward_order_id,item_title,stars_spent,status,created_at}]
  storeBusy: null,        // 지금 바꾸는 중인 item_id — 두 번 눌림 방지
  storeEdit: false,       // 부모 «진열대 고치기» 모드
  storeAdd: null,         // 올리기 시트 {title, need, limitType, limitCount}
  /* ── 🎮 미션 게임 (2026-08-08 기획서 §01·§04·§08) ──────────────────
     하단 ★ 를 누르면 부모 앱이 아니라 **아이의 세계**로 들어간다.
     이 묶음이 그대로 모듈 B(글로벌 단독 앱)의 얼굴이 된다 — 부모 화면 상태와 섞지 말 것. */
  coin: null,             // {stars, earned_today, limit, room} — 서버가 계산한다. 화면이 세지 않는다
  quiz: null,             // 오늘 세트 {items, done, correct, ...}
  quizIdx: 0,             // 몇 번째 문제
  quizPick: {},           // {code: 1~4}
  quizLeft: 0,            // 남은 초
  quizResult: null,       // 채점 결과 {correct, coins, review, ...}
  quizStats: null,        // 분야별 정답률 (박사 뱃지)
  gameTab: null,          // null=홈(2×2 타일) | morning | school | after | today | shop | profile
  gmTheme: null,          // 아이 배경색 (sky|lime|lav|sunset|mint) — 부모 테마와 무관
  clear: null,            // 클리어 연출 {icon,name,stars} — 1.2초만 산다
  quizMy: null,           // 방금 «고른» 보기 — 서버 답이 오기 전에도 표시한다
  quizFeed: null,         // 문제 하나를 답한 «직후» 뜨는 정답 — 다음 문제로 넘어가면 사라진다
  schoolMs: null,         // 학교 «미션» 오늘 상태 — 서버 school_missions.js 가 정본
  msets: null,            // 아침·방과후 «세트 완주» 상태 {morning:{done,all,taken},after:{…}}
  gamePreview: false,     // 부모가 «아이 화면»을 일부러 들여다보는 중
  pmTab: null,            // 부모 관리 안쪽 화면 (todo|bonus|today) — null 이면 카드 허브
  giveBusy: false,        // 추가 증정 중복 누름 방지
  bonusGiven: null,       // 오늘 «추가 증정»을 이미 준 미션 id 들 — 서버가 정본
                          // ⚠ 전역 SCHOOL(급식·시간표)과 다른 것이다. 이름을 섞지 말 것
  verifyPending: null,    // 부모가 볼 «확인해 주세요» [{verify_id,mission_code,step1_data,...}]
  verifyBusy: null,
  step1For: null,         // 1차 제출 시트를 띄운 미션 code (아이 화면)
  reactSheet: null,       // 칭찬 스티커 고르기 시트를 띄운 자녀 id
  kidSticker: null,       // 아이 화면에 띄울 칭찬 팝업 {sticker_type,bonus_stars}
  reactSeen: null,        // 마지막으로 본 칭찬 시각(ISO) — 이후 것만 팝업
  // ── 아이 모드 + 4자리 PIN (§0-6 · §5④) ──
  kidMode: false,         // 아이 모드가 켜져 있나 (부모 폰 공유)
  pinHas: null,           // 서버에 PIN 이 걸려 있나 (null = 아직 안 물어봄)
  pinPad: null,           // 키패드가 떠 있을 때의 용도: 'set' | 'unlock' | 'clear'
  pinBuf: "",             // 지금까지 누른 숫자
  pinPrev: "",            // 바꾸기·지우기에서 «지금 쓰는 번호»
  pinMsg: "",             // 키패드 아래 안내 한 줄 (브라우저 alert 금지 — §11-5)
  pinLockFor: 0,          // 잠긴 남은 초
  introIdx: 0,            // 온보딩에서 몇 장·몇 번째 질문인지 (2026-08-03)
  introStep: null,        // 첫 실행 단계 — slides | survey | notify (§5)
  drawer: false,          // ☰ 좌측 서랍 (2026-08-03 홈 v3)
  // ── 지시서 0803-1 (2026-08-03) ──
  art: "theme_01",        // 테마 세트 — 배경 일러스트 + 포인트 색 (§6). 라이트/다크와 별개다
  /* 오늘 화면에 어떤 줄을 켜 둘까 (§2 «카드 편집»). 시간표는 **기본 켜짐**이 지시다.
     끈 것은 사라지는 게 아니라 각자의 화면(급식·시간표·달력·준비물·미션)에 그대로 있다. */
  todayCards: { now: true, meal: true, tt: true, plan: true, sup: true, mission: true, photo: true },
  keepShot: null,         // 이 사진 미션은 도장 찍을 때 «서랍에도» 넣는다 — 미션 id (§2)
  coach: null,            // 코치마크 몇 장째 (null = 안 뜸)
  onboard: null,          // 첫 실행 설문 답 {who,kids,age} — 물은 것만 담는다(§5)
  day: null,              // 일간 화면이 보고 있는 날짜 YYYYMMDD (§2)
  edit: null,             // 전체 화면 편집기 (§3). null = 안 열림
  themePick: null,        // 테마 화면에서 «고른» 값 — «사용»을 눌러야 확정된다 (§4)
  themeFirst: false,      // 첫 실행 흐름에서 연 테마 화면인가 — 그때만 «나중에»가 뜬다 (§5)
  backup: { range: "1y", fmt: "txt" },   // 내보내기 화면이 고른 값 (§4)
  timeOpt: { weekStart: "sun", dateFmt: "ko", timeFmt: "24" },   // 시간 옵션 (§4)
  ibText: "",             // 메신저식 입력바에 치고 있는 글자 (§3)
  _missionBusyLoad: false,// 받아오는 중 — 그리기가 잦아 같은 요청이 겹치는 것을 막는다
  missionNew: null,       // 우리 집 미션 만들기 폼 (null = 닫힘)
  reg: { userid: "", pw: "", pw2: "", name: "", birth: "", email: "", phone: "", t1: true, t2: true },  // 회원가입 입력
  regServerErr: {},       // 서버가 돌려준 칸별 사유(중복 아이디·이메일 등). _ 는 칸 없는 사유
  regBusy: false,         // 서버에 확인하는 중
  loginBusy: false,
  pwShow: false,          // 비밀번호 «보기»       // 로그인 확인 중
  serverAuth: false,      // 진짜 계정으로 로그인했는가(기록을 서버에 올릴 수 있는가)
  // 비밀번호 찾기 — step 1 본인확인 · 2 코드 · 3 새 비번 · 4 완료
  findpw: { step: 1, userid: "", email: "", code: "", pw: "", pw2: "", err: {} },
  holdMenu: null,         // 길게 눌러 뜬 메뉴 {title, actions}
  reauthToken: null, reauthUntil: 0,   // 5분짜리 본인확인 표
  pwAsk: null,                         // 비밀번호를 물어보는 창
  nameDraft: null,                     // 내 이름 고치는 창 (null = 닫힘)
  /* 켜자마자 서버에서 내 정보를 받아오는 중인가.
     이게 없으면 loadMe() 가 끝나기 전에 «자녀 0명»으로 보고 등록 화면으로 튕긴다
     (2026-07-27: 앱을 나갔다 들어오면 매번 자녀 등록부터 나왔다). */
  booting: false,
  linkCode: "", linkErr: "", linkBusy: false,   // 자녀폰 연결(6자리 코드)
  childLinked: null,                           // 이 폰이 연결된 자녀(자녀 모드일 때)
  inviteCode: null, inviteUntil: 0, inviteBusy: false,   // 부모가 만든 초대 코드
  // 요청28 ① 서류
  docKind: null,          // "field" 교외체험학습 · "absence" 결석계
  docPhase: "apply",      // "apply" 신청서(가기 전) · "report" 보고서(다녀와서)
  docDraft: {},           // 입력 중인 서류 값
  // 일정 다이어리 · 시간표 터치 편집
  calMonth: TODAY.slice(0, 6),   // 보고 있는 달 — 열면 이번 달(고정값이면 해가 바뀌어도 그 달을 연다)
  calPick: null,          // 고른 날짜(YYYYMMDD) — null이면 «오늘»(또는 보는 달 1일)이 열린다
  calFold: false,         // true = 주간 접힘. 달력을 한 줄로 줄이고 아래 하루 상세를 넓게 본다
  /* 바탕화면 위젯에 띄울 줄 — 순서가 곧 위젯의 줄 순서다.
     기본은 전부 켜 둔다(2026-07-27 「전체 정보를 한눈에」). 필요 없는 사람이 끄면 된다. */
  widgetRows: ["meal", "timetable", "schedule", "myevent", "supplies", "dday"],
  evDraft: null,          // 내 일정 추가 중인 값
  ttEdit: null,           // 편집 중인 시간표 셀 {row, col, cur}
  ttOwnOpen: false,       // 칸 편집 시트에서 「직접 쓰기」를 폈나(시안 10c)
  ttFold: {},             // 시간표 아코디언을 손으로 접었나 {school,after} — 비면 시각으로 자동
  lunchAfter: null,       // 점심이 몇 교시 뒤인지(null=학교 기본 4). 사용자가 고친다
  lunchTime: null,        // {start,end} — 안 고쳤으면 null
  lunchEdit: null,        // 점심 고치는 시트 {after,start,end}
  promote: null,          // 진급 확인 중인 자녀 {id, from, to, class_name}
  promoteDone: [],        // 이번에 진급을 마친 자녀 id — 같은 카드를 또 띄우지 않는다
  ttOwn: "",              // 목록에 없는 과목을 직접 적을 때
  ttOverrides: {},        // 내가 고친 셀 "row-col" → 과목 (실제로는 timetable_overrides)
  /* 하교 후 개인 일정 — 웹(templates.js §개인 일정)에 있던 「+ 줄 추가」를 앱에도 옮긴다.
     학교 시간표 **아래**에 붙는 나만 보는 줄이다. 학원·과외처럼 학교가 모르는 일정을 적는다.
     최대 4줄인 것도 웹과 같다 — 더 늘리면 시간표가 아니라 그냥 표가 된다. */
  /* ⛔ ttPersonal / ttPersonalRows / ttPersonalTime 을 없앴다(2026-07-28).
     시간표의 「하교 후」가 방과후 화면과 **딴 데이터**를 쓰던 흔적이다 —
     같은 학원을 두 번 적어야 했고, 이쪽은 이 폰에만 남아 기기를 바꾸면 날아갔다.
     지금은 양쪽 다 STUB.activities(서버 저장) 하나를 본다. */
  // 준비물(2026-07-27) — 기본 날짜를 **내일**로 둔다. 준비물은 전날 저녁에 적는다.
  supDraft: { date: "", item: "", memo: "" },   // date 는 부팅 때 «내일»로 채운다(간단판)
  // 매일 알림(2026-07-27) — 저녁엔 «내일 준비물», 아침엔 «오늘 하루».
  remind: { on: false, evening: "20:30", morning: "07:30" },
  // 요청28 ② 알림
  noticeText: "",         // 부모가 보낼 문구
  docZoom: false,         // 서류 미리보기 — false면 한 화면에 맞춤, true면 원래 크기
  chatOpen: false,        // 맨 밑 대화창 — 접힘(작은 바) / 펼침(시트)
  chatText: "",           // 대화창 입력 중인 말
  childView: false,       // 자녀 뷰로 보기 — 목업 전용 스위치(실앱은 로그인 역할로 분기)
  dorm: false,            // 기숙사형(조식·석식 제공) 학교 시늉 — 목업 전용 토글
};
// 서버 데이터로 덮어쓰기 전의 «처음 값». 로그아웃하면 여기로 되돌린다.
/* ⚠ 배포본에는 **데모 데이터가 없어야 한다**(2026-07-27 지시: "기존에 있던 건 싹 사라져야 함").
   목업 «첫째·둘째»·기록 6개·대화·커뮤니티 글은 화면을 검수하려고 넣어 둔 것이지
   갓 가입한 학부모가 볼 것이 아니다. 남의 아이 정보처럼 보여서 신뢰가 깨진다.

   여기서 한 번에 비운다 — 화면마다 «비어 있으면» 분기를 넣으면 한 곳만 빠뜨려도 새어 나온다.
   비우는 것은 **사람에게 딸린 값**만이다. 교시 시각·점심시간·서식 규칙·빠른 문구처럼
   앱이 늘 쓰는 값은 그대로 둔다(비우면 화면이 망가진다). */
if (!DEV_TOOLS) {
  STUB.children = []; STUB.records = []; STUB.notices = []; STUB.communityPosts = [];
  STUB.documents = []; STUB.supplies = []; STUB.myEvents = []; STUB.activities = [];
  STUB.familyEvents = [];
  /* ⚠ STUB.plans 는 비우지 **않는다**(2026-07-28 발견). 요금표는 «사람에게 딸린 값»이 아니라
     앱이 늘 쓰는 값이다. 비워놓고 채우는 곳이 없어서 배포본의 이용권 화면이
     **영구히 빈 화면**이었다 — 요금제 0개, 「모의결제」 버튼 하나만 떠 있었다. */
  STUB.me.account = { id: null, display_name: "", email: "", phone_verified: false };
  // 학교·급식·시간표는 자녀를 등록해야 채워진다. 미리 «서울숭미초등학교»가 보이면 안 된다.
  STUB.school = { slug: null, name: "", kind: "초등학교" };
  STUB.meals = []; STUB.schedules = [];
  /* ⚠ 빈 시간표도 **칸은 있어야 한다**(6교시 × 5요일). 전엔 줄만 있고 칸이 없는 [[],[],…] 라
     「칸을 눌러 채우세요」라면서 누를 칸이 하나도 안 그려졌다(2026-08-03 전수검사 12번). */
  STUB.timetable = { grade: "", class_name: "", neis_year: "", semester: "",
    grid: Array.from({ length: 6 }, () => ["", "", "", "", ""]) };
}

const SEED = {
  children: STUB.children.map((c) => ({ ...c })),
  records: STUB.records.map((r) => ({ ...r })),
  notices: STUB.notices.map((n) => ({ ...n })),
  communityPosts: STUB.communityPosts.map((p) => ({ ...p })),
  documents: STUB.documents.map((d) => ({ ...d })),
  supplies: STUB.supplies.map((x) => ({ ...x })),
};

const cur = () => STUB.children.find((c) => c.id === S.currentChildId);
/* ── 그리기 전용 «빈 아이» (2026-08-04) ──────────────────────────────
   비회원은 앱 안을 **다 볼 수 있다.** 그런데 서랍·서류·결제·알림 같은 화면은
   `cur().grade` 처럼 자녀를 그냥 읽고 있어서 **자녀가 없으면 통째로 죽었다**(7개 화면 실측).
   그래서 «값이 다 빈 아이»를 세워 뼈대는 그대로 그리게 한다 — 빈 칸은 빈 칸으로 보인다.
   ⚠ **화면을 그릴 때만 쓴다.** 권한·저장·결제 판단에는 절대 쓰지 말 것 —
     그쪽에서 이걸 쓰면 «아이가 있다»고 착각해 잠금이 새어 나간다. 그건 `cur()` 다.
   ⚠ `esc(undefined)` 는 빈 문자열이라 화면에 «undefined» 가 찍히지 않는다(확인함). */
const BLANK_CHILD = Object.freeze({
  id: 0, nickname: "", name: "", grade: "", class_name: "", grade_code: 0,
  photo: null, photoLocal: null, school: {}, pass: {}, counts: {},
});
const curView = () => cur() || BLANK_CHILD;

/* ═══ 학교 데이터 — 자녀의 학교에서 가져온다 (2026-07-25) ═══
   여태 화면들이 `schoolInfo()`·`mealsOf()` 같은 **고정 스텁**을 읽고 있었다.
   그래서 자녀를 다른 학교로 등록해도 학교 탭은 계속 서울숭미초를 보여줬다(실측).
   이제 **지금 고른 자녀의 학교 slug**로 서버에서 받아 캐시하고, 화면은 아래 네 함수만 본다.
   서버가 없거나 실패하면 스텁으로 돌아간다 — 목업이 멈추면 안 된다.  */
const SCHOOL = { slug: null, info: null, meals: null, schedules: null, timetable: null, busy: false, from: "stub" };
/* 기록·서류·대화·커뮤니티가 **지금 어느 자녀 것인지** 기억한다.
   학교 데이터는 slug로 갈아끼웠는데 이건 안 해서, 자녀를 바꿔도 **첫째 기록이 둘째 화면에 남았다**(2026-07-26 실측). */
const LOADED = { childId: null, busy: false };

const ymdPlus = (base, days) => {
  const d = new Date(+base.slice(0, 4), +base.slice(4, 6) - 1, +base.slice(6));
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
};

S.supDraft.date = ymdPlus(TODAY, 1);   // S는 ymdPlus보다 위에 있어서 여기서 채운다

/* ── D-day (2026-07-27) ────────────────────────────────────
   경쟁 앱(스쿨메이트·쌤핀)이 공통으로 가진 것. 달력은 «며칠인지»를 알려주지만
   학부모가 실제로 궁금한 건 «며칠 남았는지»다.
   음수(지난 날)는 null로 돌려준다 — 화면마다 "D+3"을 다르게 해석하지 않게 여기서 잘라둔다. */
const dayDiff = (ymd) => {
  const a = new Date(+TODAY.slice(0, 4), +TODAY.slice(4, 6) - 1, +TODAY.slice(6));
  const b = new Date(+ymd.slice(0, 4), +ymd.slice(4, 6) - 1, +ymd.slice(6));
  return Math.round((b - a) / 86400000);
};
const ddayLabel = (ymd) => {
  const n = dayDiff(ymd);
  if (n < 0) return null;
  return n === 0 ? "오늘" : n === 1 ? "내일" : `D-${n}`;
};

/* ── 과목 색 (2026-07-27) ──────────────────────────────────
   학원 시간표 앱들이 과목마다 색을 준다 — 표가 «글자 덩어리»가 아니라 «무늬»로 읽힌다.
   위치가 아니라 **과목 이름**으로 색을 정한다(시간표가 바뀌어도 국어는 계속 같은 색).
   자주 나오는 과목만 고정하고, 나머지는 이름 해시로 고르게 흩는다. */
const SUBJ_CI = { "국어": 0, "수학": 1, "영어": 2, "과학": 3, "사회": 4, "체육": 5,
  "음악": 6, "미술": 7, "창의적체험활동": 8,
  /* 겹침 분리(2026-08-03 디자인 감사) — 실과=과학·도덕=사회·통합=창체가 같은 색이라
     같은 주에 앉으면 색이 정보가 아니라 소음이 됐다. 전용 색 셋을 준다 */
  "실과": 9, "도덕": 10, "통합교과": 11, "안전한 생활": 5 };
const SUBJ_N = 9;
function subjectCi(v) {
  const s = String(v || "").trim();
  if (!s) return null;
  if (SUBJ_CI[s] !== undefined) return SUBJ_CI[s];
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 9973;
  return h % SUBJ_N;
}

// 화면이 쓰는 접근자 — 받아온 게 있으면 그것, 없으면 스텁
const schoolInfo = () => SCHOOL.info || { ...STUB.school, ...(cur()?.school || {}) };
/* 등록한 학교 이름. **없으면 빈 문자열**이다 — 견본 학교명을 대신 넣지 않는다(2026-08-03 지시).
   앞이 비어 보이는 표시(«· 초등학교», «장 귀하»)를 막으려면 부르는 쪽에서 빈 값을 걸러야 한다. */
const schoolName = (c) => String((c || cur())?.school?.name || SCHOOL.info?.name || "").trim();
const mealsOf = () => SCHOOL.meals || STUB.meals;
const schedulesOf = () => SCHOOL.schedules || STUB.schedules;
const ttOf = () => SCHOOL.timetable || STUB.timetable;

/* 로그인 뒤 내 계정·자녀를 받아온다(GET /me).
   화면의 자녀(STUB.children)에 **서버 id(server_id)** 를 붙여준다 —
   기록을 올릴 때 서버는 이 id로 "누구 아이인지"를 확인한다. 없으면 목업 자녀로만 남는다. */
/* 사용자 데이터를 처음 상태로 되돌린다. 로그아웃·계정 전환 때 부른다.
   서버에서 받아 채운 자리를 비우고, 사진 캐시(blob)도 놓아준다. */
function resetUserData() {
  STUB.children = SEED.children.map((c) => ({ ...c }));
  STUB.records = SEED.records.map((r) => ({ ...r }));
  STUB.notices = SEED.notices.map((n) => ({ ...n }));
  STUB.communityPosts = SEED.communityPosts.map((p) => ({ ...p }));
  STUB.documents = SEED.documents.map((d) => ({ ...d }));
  STUB.supplies = SEED.supplies.map((x) => ({ ...x }));
  S.currentChildId = STUB.children[0]?.id ?? 1;
  SCHOOL.slug = null; SCHOOL.info = SCHOOL.meals = SCHOOL.schedules = SCHOOL.timetable = null;
  SCHOOL.from = "stub";
  IMG_CACHE.clear();
  S.childLinked = null; S.inviteCode = null;
  LOADED.childId = null; LOADED.busy = false;
  /* «이 달은 이미 받았다» 표시를 지운다 — 계정이 바뀌었는데 안 지우면
     다음 사람 달력이 «받아온 적 있음»으로 남아 영영 비어 있다. */
  MARKS_GOT.clear();
}

async function loadMe() {
  try {
    const r = await api("/me");
    if (!r?.ok) return;
    /* 내 계정 정보로 갈아끼운다 — 안 하면 목업 «김하늘»이 남의 이름으로 보인다. */
    if (r.data.account) STUB.me.account = { ...STUB.me.account, ...r.data.account };
    if (r.data.marketing) S.marketing = r.data.marketing;   // 광고성 수신 동의 — 내정보 토글이 보여준다
    // 이 계정을 보는 폰 목록(엄마·아빠). 내 정보에서 확인하고 끊는다.
    if (r.data.devices) { S.devices = r.data.devices; S.deviceLimit = r.data.device_limit || 2; }

    /* ⚠ 자녀는 **0명일 때도** 갈아끼운다(2026-07-27 사장님 발견).
       예전엔 `if (kids.length)` 라 서버가 «자녀 없음»을 줘도 목업 «첫째·둘째»가 그대로 남았다.
       갓 가입한 사람 화면에 서울숭미초등학교 다니는 아이 둘과 기록 6개·이용권이 떠 있었다.
       내 것이 아닌 데이터를 보여주는 것이라 기능 문제가 아니라 신뢰 문제다. */
    const kids = r.data.children || [];
    if (!kids.length) {
      STUB.children = []; clearKids();
      STUB.records = []; STUB.notices = []; STUB.documents = []; STUB.supplies = [];
      STUB.myEvents = []; STUB.activities = []; STUB.communityPosts = [];
      S.currentChildId = null;
      SCHOOL.slug = null; SCHOOL.info = SCHOOL.meals = SCHOOL.schedules = SCHOOL.timetable = null;
      IMG_CACHE.clear();
      LOADED.childId = null;
      return;                       // 받아올 아이가 없으니 기록·학교도 부를 것이 없다
    }
    {
      STUB.children = kids.map((k, i) => ({
        id: i + 1, server_id: k.id, nickname: k.nickname || k.name || `아이${i + 1}`,
        name: k.name || "",
        photo: k.photo || null,          // 프로필 사진 주소(없으면 이모지 얼굴)
        grade: String(k.grade ?? 3), class_name: String(k.class_name ?? 1), grade_code: k.grade_code ?? null,
        school: k.school || { slug: null, name: "학교 미등록", kind: "초등학교" },
        counts: k.counts || { records: 0 },
        /* 이용권 — ⚠ 「me」와 「children」 엔드포인트가 **서로 다른 이름으로 준다.**
             · GET /children  → pass: {active, expires_at, free_open_until}
             · GET /me        → pass_expires_at (평평한 값 하나)
           앱은 /me 로 시작하는데 pass 만 찾고 있어서, 체험이 살아 있는 사람도
           늘 «이용권 없음»으로 읽혔다. 게이트를 켜자마자 **전원이 잠겼다**(2026-07-28 실측).
           둘 다 받아준다. active 는 여기서 기한을 보고 직접 판정한다. */
        child_device: !!k.child_device, child_device_at: k.child_device_at || null,   // 자녀폰 연결 상태
        pass: k.pass || (() => {
          const exp = k.pass_expires_at || null;
          return { active: !!(exp && new Date(exp).getTime() > Date.now()), expires_at: exp };
        })(),
      }));
      S.currentChildId = pickDefaultChild(STUB.children).id;   // 기본 자녀부터 — 없으면 첫째
      saveKids();          // 다음에 켤 때 이걸로 먼저 그린다
    }
    // 셋을 동시에 — 한 줄로 세우면 요청당 ~1초씩 그대로 더해진다(2026-07-31 실측 6~8초)
    await Promise.all([
      loadRecords(),
      loadLife(),
      loadSchool(true),      // 캐시 무시하고 새로 — 안 그러면 옛 급식·시간표가 남는다
    ]);
    saveLifeCache(cur());    // 다음에 켤 때·자녀 전환 때 첫 그림을 이걸로 즉시 그린다
  } catch (e) { /* 서버 없음 — 목업 그대로 */ }
}

/* 지금 고른 자녀의 기록 목록을 받아 화면 형식으로 바꾼다.
   사진은 서버가 권한을 확인한 요청에만 내보내므로 **주소만** 받아 <img>가 불러가게 한다. */
async function loadRecords() {
  const c = cur();
  if (!TOKENS.access || !c?.server_id) return;
  // 목록은 자녀 밑에 있다 — `/records?child_id=` 가 아니라 `/children/{id}/records` (실측)
  const r = await api(`/children/${encodeURIComponent(c.server_id)}/records`);
  if (!r?.ok) return;
  const ICON = { award: "ti-award", report_card: "ti-file-text", grade_sheet: "ti-chart-bar",
    certificate: "ti-certificate", activity: "ti-flask", other: "ti-paperclip" };
  STUB.records = (r.data.items || []).map((x) => ({
    id: x.id, server_id: x.id, category: x.category,
    period: x.period, title: x.title, icon: ICON[x.category] || "ti-paperclip",
    // 사진 주소는 서버가 준 것을 그대로 쓴다(직접 조립하면 규칙이 바뀔 때 어긋난다).
    // 값은 아직 안 넣는다 — 아래 hydrateImages()가 인증을 붙여 받아온 뒤 채운다.
    /* 사진 여러 장 (2026-07-27) — 서버가 pages·images 를 준다.
       주소는 서버가 준 것을 그대로 쓴다(직접 조립하면 규칙이 바뀔 때 어긋난다).
       값은 아직 안 넣는다 — hydrateImages() 가 인증을 붙여 받아온 뒤 채운다. */
    image: x.image ? PLACEHOLDER : null,
    images: (x.images || []).map(() => PLACEHOLDER),
    _thumb: x.images?.[0]?.thumb || x.image?.thumb || null,
    _full: x.images?.[0]?.url || x.image?.url || null,
    _pages: (x.images || []).map((im) => im.url),      // 크게보기에서 장을 넘길 때 쓴다
  }));
  App.render();
}

/* 서류·대화·커뮤니티를 서버에서 받아 화면 형식으로 (2026-07-25).
   셋 다 여태 앱 안에서만 돌아 앱을 지우면 사라졌다. 이제 서버가 정본이다.
   서버가 없거나 로그인 전이면 아무것도 안 하고 목업 값을 그대로 둔다. */
async function loadLife() {
  const c = cur();
  if (!TOKENS.access || !c?.server_id) return;
  const base = `/children/${encodeURIComponent(c.server_id)}`;
  // 여섯을 한 번에 — 두 묶음으로 나누면 왕복이 두 번(요청당 ~1초 회선에서 체감이 배로 는다)
  const [docs, msgs, posts, acts, evs, sup] = await Promise.all([
    api(`${base}/documents`), api(`${base}/messages`), api(`${base}/community`),
    api(`${base}/activities`), api(`${base}/events`), api(`${base}/supplies`),
  ]);

  if (docs?.ok) {
    // 화면은 「미제출 보고서」를 kind==="field" && !reported 로 찾는다 — 서버 값을 그 모양으로 맞춘다
    STUB.documents = docs.data.items.map((d) => ({
      id: d.id, kind: d.kind, phase: d.phase, title: d.title, reported: d.reported,
      from: d.from_ymd, to: d.to_ymd, days: d.days, payload: d.payload,
      endedDaysAgo: d.to_ymd ? Math.max(0, Math.round((Date.now() - new Date(
        `${d.to_ymd.slice(0, 4)}-${d.to_ymd.slice(4, 6)}-${d.to_ymd.slice(6)}`).getTime()) / 86400000)) : 0,
    }));
  }
  if (msgs?.ok) {
    STUB.notices = msgs.data.items.map((m) => ({
      id: m.id, from: m.sender, text: m.text, seen: m.seen,
      at: (m.created_at || "").slice(5, 16).replace("T", " "),
    }));
  }
  if (sup?.ok) {
    STUB.supplies = sup.data.items.map((s) => ({
      id: s.id, server_id: s.id, date: s.date, item: s.item, memo: s.memo || "", done: !!s.done,
    }));
  }
  if (acts?.ok) {
    STUB.activities = acts.data.items.map((a) => ({
      id: a.id, server_id: a.id, type: a.type, name: a.name, color: a.color ?? 0,
      days_of_week: String(a.days_of_week ?? a.days ?? ""), start_time: a.start_time, end_time: a.end_time,
    }));
  }
  if (evs?.ok) {
    STUB.myEvents = evs.data.items.map((e) => ({
      id: e.id, server_id: e.id, date: e.date, title: e.title, memo: e.memo || "",
      start: e.start || "", end: e.start || "",
      // 서버는 알림 «시각»을 준다 — 화면 선택칸은 «몇 분 전»이라 되돌려 맞춘다
      remind: (() => {
        if (!e.remind_at || !e.start) return "";
        const [hh, mm] = e.start.split(":").map(Number);
        const at = new Date(e.remind_at);
        const base = new Date(+e.date.slice(0, 4), +e.date.slice(4, 6) - 1, +e.date.slice(6), hh, mm);
        const diff = Math.round((base - at) / 60000);
        if (at.getHours() === 20 && at.getDate() !== base.getDate()) return "prev";
        return [0, 10, 30, 60].includes(diff) ? String(diff) : "";
      })(),
    }));
  }
  if (posts?.ok) {
    STUB.communityPosts = posts.data.items.map((p) => ({
      id: p.id, author: p.display_name, body: p.body, mine: p.mine,
      when: (p.created_at || "").slice(5, 16).replace("T", " "), likes: 0, replies: 0,
    }));
  }
  App.render();
}

// 1×1 투명 — 실제 사진이 오기 전 자리
const PLACEHOLDER = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

/* 사진은 **로그인한 사람 것인지 확인한 요청에만** 서버가 내보낸다.
   그런데 <img src="…">는 토큰을 못 싣는다(브라우저가 헤더를 안 붙인다).
   그래서 토큰을 붙여 직접 받아온 뒤 blob 주소로 바꿔 끼운다.
   부수효과로 사진이 캐시돼 스크롤할 때마다 다시 받지 않는다. */
const IMG_CACHE = new Map();
/* 받아둔 주소를 **동기로** 꺼낼 수 있게 따로 담는다(2026-07-31).
   IMG_CACHE 는 «약속(Promise)»이라 화면을 그리는 순간에는 값을 못 쓴다 —
   그래서 장을 넘길 때마다 빈 칸부터 그리고 나서 사진이 늦게 들어왔다. */
const IMG_READY = new Map();
async function fetchImage(pathOnServer) {
  if (IMG_CACHE.has(pathOnServer)) return IMG_CACHE.get(pathOnServer);
  const p = (async () => {
    const res = await fetch(API_BASE + pathOnServer, {
      headers: TOKENS.access ? { Authorization: "Bearer " + TOKENS.access } : {},
    });
    if (!res.ok) { const e = new Error("이미지를 받지 못했어요"); e.status = res.status; IMG_CACHE.delete(pathOnServer); throw e; }
    const url = URL.createObjectURL(await res.blob());
    IMG_READY.set(pathOnServer, url);
    return url;
  })();
  IMG_CACHE.set(pathOnServer, p);
  return p;
}
/* 크게보기에서 장 넘김이 느렸다(2026-07-31 «드럽게 늦게 넘어가») — 다음 장을 그때서야 받았기 때문.
   기록을 열 때 **모든 장을 미리** 받아둔다. 보통 2~3장이라 부담이 작고, 넘기는 순간은 캐시에서 꺼낸다. */
function prefetchPages(rec) {
  if (!TOKENS.access || !rec) return;
  const paths = [...(rec._pages || []), rec._full].filter(Boolean);
  paths.forEach((p) => { fetchImage(p).catch(() => {}); });
}
// 화면을 다시 그릴 때마다 비어 있는 사진 자리를 채운다
function hydrateImages() {
  if (!TOKENS.access) return;
  document.querySelectorAll("img[data-rec]").forEach(async (im) => {
    const path = im.getAttribute("data-rec");
    if (!path || im.dataset.done) return;
    im.dataset.done = "1";
    /* 3상태(2026-08-02) — 회색 상자가 «기다리는 중»인지 «죽은 것»인지 화면이 말해야 한다.
       rec-loading = 받는 중(스켈레톤) / rec-none = 서버에 없음(404) / rec-fail = 실패(재시도) */
    im.classList.add("rec-loading");
    try {
      im.src = await fetchImage(path);
      im.classList.remove("rec-loading");
    } catch (e) {
      im.classList.remove("rec-loading");
      const box = im.parentElement;
      if (e && e.status === 404) {
        im.classList.add("rec-none");
        box?.insertAdjacentHTML("beforeend", `<span class="rec-msg">아직 사진이 없어요</span>`);
      } else {
        im.classList.add("rec-fail");
        box?.insertAdjacentHTML("beforeend",
          `<button class="rec-retry" onclick="App.recRetry(this)">사진을 못 불러왔어요 · 다시 시도</button>`);
      }
    }
  });
}

// 서버에서 학교 한 벌을 받아 캐시한다. 자녀를 바꾸면 다시 부른다.
async function loadSchool(force) {
  const c = cur();
  const slug = c?.school?.slug;
  if (!slug || SCHOOL.busy) return;
  if (!force && SCHOOL.slug === slug) return;
  SCHOOL.busy = true;
  const path = "/schools/" + encodeURIComponent(slug);
  const from = ymdPlus(TODAY, -30), to = ymdPlus(TODAY, 210);   // 지난달 ~ 앞으로 7개월
  try {
    const hasClass = c.grade && c.class_name;      // 비회원은 학년·반이 없다
    const [info, meals, sched, tt] = await Promise.all([
      api(path), api(`${path}/meals?from=${from}&to=${to}`), api(`${path}/schedules?from=${from}&to=${to}`),
      hasClass ? api(`${path}/timetable?grade=${encodeURIComponent(c.grade)}&class=${encodeURIComponent(c.class_name)}`)
               : Promise.resolve(null),
    ]);
    SCHOOL.slug = slug;
    SCHOOL.info = info?.ok ? { ...info.data, detail: info.data.detail || STUB.school.detail } : null;
    SCHOOL.meals = meals?.ok ? meals.data.items : null;
    SCHOOL.schedules = sched?.ok ? sched.data.items : null;
    SCHOOL.timetable = tt?.ok && tt.data.items.length ? toGrid(tt.data.items) : null;
    SCHOOL.from = "server";
    if (cur()) saveSchool(c);   // 다음에 켤 때 이걸로 먼저 그린다(같은 날·같은 반일 때만)
  } catch (e) {
    SCHOOL.slug = slug; SCHOOL.from = "stub";       // 못 붙었다 — 스텁으로 보여주되 그 사실을 표시한다
    SCHOOL.info = SCHOOL.meals = SCHOOL.schedules = SCHOOL.timetable = null;
  }
  SCHOOL.busy = false;
  App.render();
}

// 서버 시간표(줄 목록) → 화면이 쓰는 격자 [교시][요일]
function toGrid(items) {
  const grid = Array.from({ length: 7 }, () => ["", "", "", "", ""]);
  let maxP = 0;
  items.forEach((r) => {
    const p = +r.period, w = +r.weekday;             // weekday 1=월 … 5=금
    if (!(p >= 1 && p <= 7) || !(w >= 1 && w <= 5)) return;
    grid[p - 1][w - 1] = r.subject || "";
    if (p > maxP) maxP = p;
  });
  return { neis_year: items[0]?.neis_year, semester: items[0]?.semester,
    grade: items[0]?.grade ?? cur()?.grade, class_name: items[0]?.class_name ?? cur()?.class_name,
    grid: grid.slice(0, Math.max(maxP, 5)) };
}

// ═══ 화면들 ═══════════════════════════════════════════════════


/* ── 바탕화면 위젯 (2026-07-27) ────────────────────────────
   위젯은 웹뷰 **밖**이라 localStorage 를 못 읽는다. 앱이 그릴 때마다 네이티브로 밀어준다.

   무엇을 보여줄지는 **사용자가 고른다**(#homeedit → 바탕화면 위젯).
   그래서 네이티브는 «급식»·«시간표» 같은 종류를 하나도 모른다 — 여기서 만든 줄 목록을 그대로 그린다.
   종류를 늘릴 때 자바를 안 고쳐도 되게 하려는 것이다.

   각 항목은 그 줄의 «글」을 만든다. 빈 문자열을 돌려주면 그 줄은 아예 안 나온다 —
   «오늘 일정 없음» 같은 빈 줄로 자리를 먹느니 다른 줄에 자리를 주는 게 낫다. */
/* icon(이모지)은 **위젯 본체용**이다 — 바탕화면 위젯은 RemoteViews라 아이콘 폰트를 못 쓴다.
   ic/ci 는 **앱 화면용**(홈 편집 목록). 두 목록이 나란히 있는데 한쪽만 맨 이모지면
   같은 조작인데 다른 기능처럼 보인다(2026-08-01). 그래서 앱 안에서는 홈 카드와 같은 색 칩을 쓴다. */
const WIDGET_ITEMS = [
  { key: "meal", icon: "🍚", ic: "ti-tools-kitchen-2", ci: 0, label: "오늘 급식", go: "#school/meal", make: () => {
      const m = mealsOf().find((x) => x.date === TODAY && x.type === "중식");
      return m ? m.dishes.slice(0, 4).map((x) => x.name).join(" · ") : "오늘은 급식이 없어요";
    } },
  { key: "timetable", icon: "🕐", ic: "ti-table", ci: 2, label: "오늘 시간표", go: "#school/timetable", make: () => {
      const wd = new Date(+TODAY.slice(0, 4), +TODAY.slice(4, 6) - 1, +TODAY.slice(6)).getDay();
      if (wd < 1 || wd > 5) return "오늘은 수업이 없어요";
      const col = wd - 1;
      const subs = (ttOf().grid || []).map((row, r) => S.ttOverrides[`${r}-${col}`] ?? row[col])
        .filter(Boolean).map(shortSubject);
      return subs.length ? subs.join(" ") : "오늘은 수업이 없어요";
    } },
  { key: "schedule", icon: "🏫", ic: "ti-calendar", ci: 1, label: "오늘 학교 일정", go: "#school/schedule", make: () => {
      const sc = schedulesOf().filter((e) => e.date === TODAY && !e.name.includes("토요휴업일"));
      return sc.length ? sc.map((e) => e.name).join(" · ") : "";
    } },
  { key: "myevent", icon: "📔", ic: "ti-notebook", ci: 4, label: "오늘 내 일정", go: "#school/schedule", make: () => {
      const mine = STUB.myEvents.filter((e) => e.date === TODAY);
      return mine.length ? mine.map((e) => (e.start ? `${e.start} ${e.title}` : e.title)).join(" · ") : "";
    } },
  /* 준비물만 특별하다 — 한 줄로 뭉치지 않고 **항목마다 한 줄**을 쓴다.
     위젯에서 누르면 그 자리에서 체크되기 때문이다(앱을 안 열어도 된다).
     rows() 를 가진 항목은 여러 줄로 펼쳐진다. 나머지는 make() 로 한 줄이다. */
  { key: "supplies", icon: "🎒", ic: "ti-backpack", ci: 5, label: "내일 준비물", go: "#supplies", rows: () => {
      const t = ymdPlus(TODAY, 1);
      const all = STUB.supplies.filter((x) => x.date === t);
      if (!all.length) return [];
      const left = all.filter((x) => !x.done);
      if (!left.length) return [{ icon: "🎒", text: "내일 준비물 다 챙겼어요", go: "#supplies" }];
      // 너무 많으면 위젯을 다 먹는다 — 세 개까지만 체크 줄로 펼치고 나머지는 요약 한 줄
      const head = left.slice(0, 3);
      const out = head.map((x) => ({ icon: "⬜", text: x.item, go: "#supplies", check: String(x.id) }));
      if (left.length > head.length) {
        out.push({ icon: "🎒", text: `준비물 ${left.length - head.length}개 더`, go: "#supplies" });
      }
      return out;
    } },
  /* 미션(2026-08-02) — **앱을 안 열어도** 「2/3 · 확인 1」이 바탕화면에 보인다.
     부모가 확인해줄 게 있다는 걸 알아야 아이가 안 기다린다. */
  { key: "mission", icon: "🎯", ic: "ti-target", ci: 4, label: "오늘 미션", go: "#mission", make: () => {
      const m = S.missions;
      if (!m || !m.length) return "";
      const done = m.filter((x) => x.status === "done").length;
      const wait = m.filter((x) => x.status === "waiting").length;
      const next = m.find((x) => x.status === "open");
      return `${done}/${m.length}${wait ? ` · 확인 ${wait}` : ""}${next ? ` · ${next.title}` : ""}`;
    } },
  { key: "dday", icon: "📌", ic: "ti-pin", ci: 6, label: "다가오는 행사", go: "#school/schedule", make: () => {
      // 오늘 이후 «중요한» 학교 일정 하나. 지난 것과 토요휴업일은 뺀다.
      const next = schedulesOf().filter((e) => e.date > TODAY && classifyEvent(e.name, e.closure_type))
        .sort((a, b) => a.date.localeCompare(b.date))[0];
      if (!next) return "";
      const dd = ddayLabel(next.date);
      return `${dd ? dd + " " : ""}${next.name}`;
    } },
];
const WIDGET_KEYS = WIDGET_ITEMS.map((x) => x.key);
const widgetItemOf = (k) => WIDGET_ITEMS.find((x) => x.key === k);
const WIDGET_MAX = 6;      // 자바 레이아웃의 줄 수와 같아야 한다(widget_school.xml)

let WIDGET_LAST = "";
function pushWidget() {
  const P = window.Capacitor?.Plugins?.SchoolWidget;
  if (!P || !S.loggedIn) return;
  const c = cur();
  if (!c) return;

  // 고른 순서대로, 글이 비지 않은 것만. 최대 6줄.
  // rows() 를 가진 항목(준비물)은 여러 줄로 펼쳐지고, 나머지는 make() 로 한 줄이다.
  const rows = S.widgetRows.map(widgetItemOf).filter(Boolean)
    .flatMap((it) => (it.rows ? it.rows() : [{ icon: it.icon, text: it.make(), go: it.go }]))
    .filter((r) => r && r.text).slice(0, WIDGET_MAX);

  const data = {
    child: c.nickname,   // 위젯은 이모지를 못 그린다(RemoteViews)
    date: `${+TODAY.slice(4, 6)}/${+TODAY.slice(6)} (${weekdayKo(TODAY)})`,
    rows: JSON.stringify(rows),
  };
  const key = JSON.stringify(data);
  if (key === WIDGET_LAST) return;   // render()는 탭만 눌러도 돈다 — 같은 값이면 네이티브를 안 두드린다
  WIDGET_LAST = key;
  P.update(data).catch(() => {});    // 실패해도 앱은 계속 돈다 — 위젯은 부가 기능이다
}

/* 위젯의 어느 줄을 눌렀는지 네이티브가 window.__widgetGo 에 넣고 이벤트를 쏜다(MainActivity.java).
   앱이 꺼져 있었으면 이벤트가 우리보다 먼저 올 수도 있어, 이벤트와 «이미 들어와 있는 값» 둘 다 본다. */
function widgetGo() {
  const go = window.__widgetGo;
  if (!go) return;
  window.__widgetGo = null;
  const [hash, tab] = go.split("/");            // 예: "#school/meal"
  if (tab) S.schoolTab = tab;
  if (location.hash === hash) App.render();
  else location.hash = hash;
}
window.addEventListener("widgetgo", widgetGo);

/* 위젯에서 체크한 준비물을 받아온다 (2026-07-27).
   위젯은 «눌렀다»는 사실만 적어 둔다 — 방송 수신기는 몇 초 만에 죽는 자리라
   거기서 서버를 부르면 조용히 실패한다. 서버 반영은 앱이 열릴 때 여기서 한다.
   받아간 뒤 네이티브 쪽 목록은 비워진다(안 비우면 열 때마다 다시 뒤집힌다). */
async function drainWidgetChecks() {
  const P = window.Capacitor?.Plugins?.SchoolWidget;
  if (!P || !P.takePending) return;
  let ids = [];
  try { ids = JSON.parse((await P.takePending()).ids || "[]"); } catch (e) { return; }
  if (!ids.length) return;
  let n = 0;
  for (const raw of ids) {
    const s2 = STUB.supplies.find((x) => String(x.id) === String(raw));
    if (!s2 || s2.done) continue;      // 이미 앱에서 체크했으면 건드리지 않는다
    await App.supplyToggle(s2.id);
    n++;
  }
  if (n) { WIDGET_LAST = ""; App.render(); toast(`위젯에서 체크한 준비물 ${n}개를 반영했어요`); }
}

/* ── 한글 입력과 다시 그리기 (2026-07-27) ─────────────────
   글자를 칠 때마다 render() 를 부르면 조합 중이던 <input> 이 통째로 새 노드로 갈린다.
   그러면 IME 가 잡고 있던 조합 상태가 날아가 «김» 이 «ㄱㅣㅁ» 으로 풀려 찍힌다(사장님 발견).
   영문·숫자는 한 글자가 곧 한 글자라 티가 안 났다.

   그래서 **조합 중에는 그리지 않는다.** 조합이 끝나면 그때 한 번 그린다.
   칸별 빨간 글씨(유효성)는 조합이 끝난 뒤에 뜨는데, 어차피 조합 도중의 반쪽 글자로
   «틀렸다»고 말해봐야 의미가 없다. */
let IME_ON = false;      // 지금 한글을 조합 중인가
let IME_DIRTY = false;   // 조합 때문에 미뤄둔 다시 그리기가 있는가
document.addEventListener("compositionstart", () => { IME_ON = true; });
document.addEventListener("compositionend", () => {
  IME_ON = false;
  if (!IME_DIRTY) return;
  IME_DIRTY = false;
  renderKeepFocus();
});
/* 조합 중에 다른 곳을 누르거나 앱을 떠나면 compositionend 가 안 올 수 있다.
   그대로 두면 미뤄둔 그리기가 영영 안 돌아 화면이 옛것으로 굳는다 — 여기서 풀어준다. */
function imeFlush() {
  if (!IME_ON && !IME_DIRTY) return;
  IME_ON = false;
  if (IME_DIRTY) { IME_DIRTY = false; App.render(); }
}
document.addEventListener("focusout", imeFlush);
document.addEventListener("visibilitychange", imeFlush);

/* 입력 중에 쓰는 다시 그리기 — 조합 중이면 미루고, 아니면 **커서 자리를 지키며** 그린다.
   예전엔 value 가 같은 칸을 찾아 되돌렸는데, 같은 값이 두 칸이면 엉뚱한 칸으로 뛰었다.
   id 로 찾는다 — 입력칸에 id 가 없으면 focus 복원을 포기한다(글자는 안 잃는다). */
function renderKeepFocus() {
  if (IME_ON) { IME_DIRTY = true; return; }
  const a = document.activeElement;
  const id = a && a.id;
  const start = a && a.selectionStart, end = a && a.selectionEnd;
  App.render();
  if (!id) return;
  const back = document.getElementById(id);
  if (!back) return;
  back.focus();
  try { if (start != null) back.setSelectionRange(start, end); } catch (e) {}
}


/* ── 안드로이드 뒤로가기 (2026-07-27) ────────────────────────
   여태 아무 처리도 없어서 **어느 화면에서든 뒤로가기를 누르면 앱이 그냥 꺼졌다**(사장님 발견).
   웹뷰 앱은 이걸 직접 다뤄야 한다 — 안 하면 안드로이드가 액티비티를 통째로 닫는다.

   순서: ①열린 창을 먼저 닫고 ②그다음 상위 화면으로 ③홈에서만 종료.
   홈에서도 한 번에 안 끈다 — 실수로 눌러 앱이 꺼지면 쓰던 것을 잃는다. 두 번 눌러야 나간다. */
let BACK_EXIT_AT = 0;
function backPressed() {
  // ① 열려 있는 창부터 닫는다(위에서부터)
  if (S.holdMenu) { App.holdClose?.(); return; }
  if (S.pwAsk) { S.pwAsk = null; App.render(); return; }
  if (S.viewRecord) { S.viewRecord = null; S.recordMenuOpen = false; App.render(); return; }
  if (S.evDraft) { App.evCancel(); return; }
  if (S.ttEdit) { App.ttClose(); return; }
  if (S.chatOpen) { S.chatOpen = false; App.render(); return; }

  // ② 상위 화면으로
  const here = (location.hash || "").slice(1);
  if (here && here !== "home" && here !== "login") { location.hash = "#home"; return; }

  // ③ 홈(또는 로그인)에서 두 번 눌러야 나간다
  const now = Date.now();
  if (now - BACK_EXIT_AT < 2000) {
    const C = window.Capacitor;
    (C?.Plugins?.App?.exitApp || (() => C?.nativePromise?.("App", "exitApp", {})))();
    return;
  }
  BACK_EXIT_AT = now;
  toast("한 번 더 누르면 앱이 꺼져요");
}
/* 뒤로가기 연결 — ⚠ 여기서 두 번 헛발질했다(2026-07-27).
   ① `@capacitor/app` 이 package.json 에 없어서 안드로이드에 **등록조차 안 돼** 있었다.
   ② 등록한 뒤에도 `Capacitor.Plugins.App` 은 비어 있었다 — 그건 npm 래퍼(JS)가 채우는 값인데
      우리는 번들러를 안 써서 그 JS가 돌지 않는다. `Capacitor.registerPlugin` 도 없다(그것도 래퍼 쪽 API).
   네이티브 브리지가 직접 주는 `Capacitor.addListener(플러그인, 이벤트, 콜백)` 를 쓴다.
   그리고 안드로이드는 **toggleBackButtonHandler(true)** 를 켜야 뒤로가기를 JS로 넘겨준다 —
   안 켜면 리스너를 붙여도 안드로이드가 그냥 액티비티를 닫는다. */
const CapApp = window.Capacitor?.Plugins?.App || null;
function bindBackButton() {
  const C = window.Capacitor;
  if (!C || !C.isPluginAvailable?.("App")) return false;
  try {
    C.addListener("App", "backButton", backPressed);
    // 안드로이드에게 «뒤로가기는 우리가 처리한다»고 알린다
    (C.Plugins?.App?.toggleBackButtonHandler
      || ((o) => C.nativePromise?.("App", "toggleBackButtonHandler", o)))({ enabled: true });
    return true;
  } catch (e) { return false; }
}
if (!bindBackButton()) {
  // 브리지가 아직 안 붙었을 수 있다 — 로드가 끝난 뒤 한 번 더
  window.addEventListener("load", bindBackButton);
}

/* 바깥 브라우저로 열기 — 학교 홈페이지·자매 사이트처럼 **우리 앱 밖**으로 나가는 주소.
   앱 안 웹뷰에 띄우면 권한·쿠키가 섞이고, 사용자는 «앱이 이상해졌다»고 느낀다.
   @capacitor/browser 는 앱 안 탭으로 열어서 «기본 브라우저»가 아니다(2026-07-27 지시) —
   그래서 네이티브 플러그인에서 Intent.ACTION_VIEW 로 바로 넘긴다. */
function openExternal(url, label) {
  const u = String(url || "").trim();
  if (!/^https?:\/\//i.test(u)) return toast(`${label || "주소"}가 없어요`);
  const P = window.Capacitor?.Plugins?.SchoolWidget;
  if (P?.openUrl) { P.openUrl({ url: u }).catch(() => toast("브라우저를 열지 못했어요")); return; }
  window.open(u, "_blank", "noopener");     // 브라우저에서 볼 때(목업)
}

/* ── 약관·방침 문안 (2026-07-31) — 정본은 워커 templates.js(/terms·/privacy)와 동일. 같이 고칠 것 ── */
const LEGAL = {
  effective: "2026-08-01",
  terms: [
    ["제1조 (목적)", "본 약관은 베이직씨엔엠(이하 '회사')이 제공하는 '아이서랍' 서비스(웹 및 모바일 앱, 이하 '서비스')의 이용 조건과 회사·이용자의 권리, 의무를 정합니다."],
    ["제2조 (서비스 내용)", "서비스는 ① NEIS·학교알리미 등 공공데이터 기반의 급식·시간표·학사일정 안내 ② 자녀 기록(상장·통지표 등) 보관 ③ 교외체험학습 신청서·결석신고서 등 서식 작성 도움 ④ 준비물·일정 관리와 알림 ⑤ 자녀 기기 연결 기능을 제공합니다."],
    ["제3조 (정보의 성격)", "급식·시간표·학사일정은 공공데이터 공시 시점 기준이며 학교 사정으로 실제와 다를 수 있습니다. 서식은 일반적인 양식을 기준으로 하며 학교마다 다를 수 있으므로 제출 전 학교 안내를 확인해야 합니다. 서비스가 제공하는 정보는 참고용입니다."],
    ["제4조 (계정)", "가입은 보호자 본인이 해야 하며, 계정·비밀번호 관리 책임은 이용자에게 있습니다. 만 14세 미만 아동은 직접 가입할 수 없고, 자녀 기기 연결은 보호자가 발급한 코드로만 가능합니다."],
    ["제5조 (이용권과 결제)", "서비스는 무료 체험 기간(자녀 등록 후 14일) 후 유료 이용권으로 이용합니다. 결제는 Google Play 인앱 결제로 처리되며, 가격·기간은 결제 화면에 표시된 내용을 따릅니다. 이용권은 자녀 1명 기준이며 자녀 추가 시 별도 이용권이 필요합니다."],
    ["제6조 (환불)", "환불은 Google Play 환불 정책과 전자상거래 등에서의 소비자보호에 관한 법률에 따릅니다."],
    ["제7조 (이용자 콘텐츠)", "이용자가 올린 기록(사진·메모 등)의 권리는 이용자에게 있으며, 회사는 보관·표시 목적 범위에서만 처리합니다. 회사는 이용자 콘텐츠를 광고 등 다른 목적에 쓰지 않습니다."],
    ["제8조 (금지행위)", "타인의 계정 도용, 서비스의 비정상적 이용(자동화 수집, 서버 공격 등), 법령 위반 목적의 이용을 금지합니다."],
    ["제9조 (서비스 변경·중단)", "회사는 서비스 내용을 변경하거나 중단할 수 있으며, 유료 이용자에게 불리한 중대한 변경은 사전에 알립니다."],
    ["제10조 (책임의 한계)", "회사는 공공데이터 원본의 오류·지연, 천재지변, 이용자 귀책으로 인한 손해에 대해 책임을 지지 않습니다."],
    ["제11조 (해지·탈퇴)", "이용자는 앱의 내정보에서 언제든 탈퇴할 수 있습니다. 탈퇴 시 데이터는 개인정보처리방침에 따라 3개월 보관 후 파기됩니다."],
    ["제12조 (준거법)", "본 약관은 대한민국 법률에 따르며, 분쟁은 민사소송법상 관할 법원에 제기합니다."],
    ["문의", "베이직씨엔엠 (사업자등록번호 746-21-02507) · dndmotor1@gmail.com"],
  ],
  privacy: [
    ["1. 수집하는 개인정보", "서비스 제공에 필요한 최소한만 수집합니다.\n· 계정: 아이디, 비밀번호(암호화 저장), 보호자 이름, 생년월일, 이메일, 휴대폰 번호(선택), 카카오 로그인 시 카카오 회원번호·닉네임\n· 자녀: 별명, 자녀 이름(선택 — 서식 작성용, 분리 보관하며 화면에 표시하지 않음), 학교·학년·반, 프로필 사진(선택)\n· 이용자가 저장하는 내용: 기록 사진·메모, 준비물, 개인 일정, 출결 서식 작성 내용\n· 자동 수집: 접속 기록, 기기 알림 토큰\n· 결제: Google Play 주문 정보(상품·일시·주문번호). 카드번호 등 결제수단 정보는 Google이 처리하며 회사는 보관하지 않습니다."],
    ["2. 이용 목적", "서비스 제공(급식·시간표·학사일정 안내, 기록 보관, 서식 작성, 알림), 계정 식별과 데이터 복원, 이용권·결제 관리, 고지사항 전달, 부정 이용 방지에 씁니다. 광고성 정보 전송은 별도로 동의한 경우에만 합니다."],
    ["3. 보유 기간", "회원 탈퇴 후 3개월간 보관한 뒤 파기합니다(실수 탈퇴 문의·분쟁 대응 목적. 이 기간에도 로그인은 되지 않습니다). 즉시 파기를 원하면 문의해 주세요.\n법령이 따로 정한 것은 그 기간을 따릅니다: 계약·결제 기록 5년, 소비자 불만·분쟁 처리 기록 3년(전자상거래법), 접속 기록 3개월(통신비밀보호법)."],
    ["4. 처리 위탁과 국외 이전", "서비스 운영을 위해 아래에 처리를 맡깁니다.\n· Cloudflare, Inc.(미국) — 서버 운영·데이터 보관. 이전 항목: 제1항의 정보 전부, 이전 시점: 서비스 이용 시 상시, 보유 기간: 위 제3항과 같음\n· Google LLC(미국) — 결제 처리, 앱 알림 발송\n· 주식회사 카카오 — 간편 로그인\n이용자는 국외 이전을 거부할 수 있으나 이 경우 서비스 이용이 불가능합니다."],
    ["5. 제3자 제공", "법령에 따른 경우를 제외하고 개인정보를 제3자에게 제공하지 않습니다."],
    ["6. 아동의 개인정보", "자녀 정보는 보호자(법정대리인)가 직접 입력하고 그 수집·이용에 동의합니다. 만 14세 미만 아동은 직접 가입할 수 없으며, 자녀 기기 연결은 보호자가 발급한 코드로만 가능합니다. 자녀 이름은 분리 보관하고 앱 화면에 표시하지 않습니다."],
    ["7. 파기 방법", "보유 기간이 지난 정보는 지체 없이 파기합니다. 전자 파일은 복구할 수 없는 방법으로 삭제하고, 사진 원본(저장소)도 함께 삭제합니다."],
    ["8. 이용자의 권리", "이용자는 언제든 자기 정보의 열람·정정·삭제·처리정지를 요구하고 동의를 철회할 수 있습니다. 앱의 내정보 또는 아래 연락처로 요청하면 지체 없이 처리합니다."],
    ["9. 광고성 정보 수신", "광고성 정보(혜택·소식)는 가입 시 또는 이후에 선택 동의한 경우에만 이메일·문자·전화로 보냅니다. 앱의 내정보에서 채널별로 언제든 철회할 수 있으며, 동의하지 않아도 서비스 이용에 제한이 없습니다."],
    ["10. 안전성 확보 조치", "비밀번호 일방향 암호화, 전 구간 통신 암호화(HTTPS), 자녀 이름 분리 보관, 접근 권한 최소화, 로그인 시도 제한을 적용합니다."],
    ["11. 개인정보 보호책임자", "베이직씨엔엠 대표 (사업자등록번호 746-21-02507) · dndmotor1@gmail.com — 개인정보 관련 문의·불만·피해 구제를 처리합니다. 그 밖에 개인정보침해 신고는 한국인터넷진흥원 개인정보침해신고센터(118)로 할 수 있습니다."],
    ["12. 고지", "이 방침을 바꾸면 시행 7일 전(이용자에게 불리한 변경은 30일 전) 앱 공지로 알립니다."],
  ],
};
function legalScreen(title, sections) {
  return `
  <a class="back" href="javascript:history.back()" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
  <h1 class="pg-h">${esc(title)}</h1>
  <p class="legal-eff">시행일 ${LEGAL.effective}</p>
  <div class="legal">${sections.map(([h, t]) => `
    <section>
      <b>${esc(h)}</b>
      <p>${esc(t).replace(/\n/g, "<br>")}</p>
    </section>`).join("")}</div>`;
}

/* ═══ 미션 (2026-08-01) ═══════════════════════════════════
   부모가 오늘 3개를 정하면 아이가 자기 폰에서 해낸다. 규칙은 전부 서버가 지킨다 —
   여기서는 화면만 맞춘다(앱에서만 막으면 우회되고, 앱이 안 막으면 눌러본 뒤에야 거절당해 답답하다).

   판정 셋:
     즉시   — 누르면 그 자리에서 도장
     대기   — 사진을 찍어 보내고 부모 확인을 기다린다(다음날 아침 8시엔 자동으로 받는다)
     하루끝 — 「안 하기」 미션. 하루가 끝나면 앱이 알아서 판정한다 */
const MISSION_AREA = { body: "몸", things: "내 물건", study: "공부", prep: "챙기기", read: "읽기",
  family: "가족", outside: "바깥", digital: "디지털", mind: "마음", money: "돈" };
/* 학년대 — 1~2 저 · 3~4 중 · 5~6 고. 서버 카탈로그의 band 와 같은 기준이다. */
const bandOf = (c) => (+((c || cur())?.grade) <= 2) ? "low" : (+((c || cur())?.grade) <= 4) ? "mid" : "high";
const missionWaiting = () => (S.missions || []).filter((x) => x.status === "waiting").length;
const missionOf = (id) => (S.missions || []).find((x) => x.id === id);

/* ═══ 자주 묻는 질문 (2026-08-01) ═══════════════════════════
   ⚠ 워커 templates.js 의 공개 고객센터(/help)와 **같은 문안**이다. 한쪽만 고치지 말 것.
   여기 답은 전부 «지금 앱이 실제로 하는 일»이다. 모르는 것을 그럴듯하게 적지 않는다 —
   FAQ가 틀리면 문의가 줄기는커녕 «앱이 거짓말한다»는 문의가 새로 들어온다.
   숫자(체험 14일·보관 3개월·자녀 1대)는 약관·코드와 같아야 한다. */
const FAQ = [
  ["시작하기", [
    ["자녀는 어떻게 등록하나요?",
      "내 정보 → 자녀 추가에서 학교 이름을 검색하고 학년·반을 고르면 됩니다. 전국 초·중·고를 이름 일부만으로 찾을 수 있어요."],
    ["자녀를 여러 명 등록할 수 있나요?",
      "네. 홈 위쪽 자녀 이름을 눌러 바꿉니다. 앱을 켰을 때 먼저 열릴 자녀는 홈 편집에서 정할 수 있어요."],
    ["학년이 올라가면 어떻게 하나요?",
      "새 학년이 되면 앱이 먼저 물어봅니다. 확인만 누르면 학년이 올라가고, 반은 내 정보에서 고칩니다."],
  ]],
  ["급식·시간표·일정", [
    ["급식이 실제와 달라요.",
      "급식·시간표·학사일정은 학교가 공공데이터(NEIS)에 올린 자료를 그대로 보여줍니다. 학교 사정으로 바뀌면 앱 쪽 반영이 늦을 수 있어요. 화면의 오류 신고로 알려주시면 확인합니다."],
    ["시간표가 비어 있어요.",
      "방학이거나 학교가 아직 올리지 않은 경우입니다. 개학 뒤에도 비어 있으면 문의해 주세요. 칸을 눌러 직접 채워 넣을 수도 있습니다."],
    ["공휴일이 일정에 뜨는 게 거슬려요.",
      "홈 편집 → 「일정에 공휴일」을 끄면 홈에서 사라집니다. 학교탭 달력에는 그대로 남아요."],
    ["일정 알림은 어떻게 켜나요?",
      "일정을 넣을 때 알림 시각을 함께 고르면 됩니다(정시·10분 전·30분 전·1시간 전·전날). 지난 시각은 알림이 가지 않아요."],
  ]],
  ["기록(서랍)", [
    ["기록한 사진은 어디에 저장되나요?",
      "저희 서버에 보관합니다. 통신은 전 구간 암호화하고, 올리신 사진을 광고 등 다른 목적으로 쓰지 않습니다."],
    ["실수로 지운 기록을 되살릴 수 있나요?",
      "되살릴 수 없습니다. 지우기 전에 한 번 더 확인 창이 뜨는 이유예요."],
    ["「서버에 안 올라갔어요」가 떴어요.",
      "사진을 올리는 도중 통신이 끊긴 경우입니다. 기록은 폰에 남아 있으니 서랍 위 「다시 올리기」를 누르면 이어서 올라갑니다."],
    ["예전 기록을 찾고 싶어요.",
      "서랍 오른쪽 위 「검색」에서 제목·종류·학년·학기로 찾을 수 있습니다."],
  ]],
  ["자녀 폰 연결", [
    ["자녀 폰은 어떻게 연결하나요?",
      "내 정보 → 자녀폰에서 코드를 발급하고, 자녀 폰의 앱에 그 코드를 넣으면 됩니다. 코드는 한 번만 쓸 수 있어요."],
    ["자녀 폰은 몇 대까지 되나요?",
      "자녀 1명당 1대입니다. 새 폰을 연결하면 이전 폰은 자동으로 끊깁니다."],
    ["자녀 폰에서 뭘 볼 수 있나요?",
      "준비물과 대화만 볼 수 있습니다. 기록·결제·보호자 정보는 자녀 폰에서 열리지 않습니다."],
    ["연결을 끊고 싶어요.",
      "내 정보 → 자녀폰 → 끊기를 누르면 그 즉시 자녀 폰에서 접속이 끊깁니다."],
  ]],
  ["이용권·결제", [
    ["무료로 얼마나 써볼 수 있나요?",
      "자녀를 등록하면 14일 동안 모든 기능을 무료로 쓸 수 있습니다. 자동으로 결제되지 않아요."],
    ["결제는 자녀별인가요?",
      "네. 이용권은 자녀 1명 기준이라 자녀가 늘면 이용권도 따로 필요합니다."],
    ["환불하고 싶어요.",
      "앱 결제는 Google Play를 통해 이뤄집니다. Play 스토어 → 결제 및 정기 결제 → 주문 내역에서 환불을 신청할 수 있고, 진행이 어려우면 문의해 주세요."],
    ["이용권이 남았는데 연장하면 어떻게 되나요?",
      "남은 기간 뒤에 이어 붙습니다. 남은 날짜가 사라지지 않아요."],
  ]],
  ["계정·보안", [
    ["비밀번호를 잊었어요.",
      "로그인 화면의 「비밀번호 찾기」에서 가입할 때 쓴 이메일로 본인 확인 후 새로 정할 수 있습니다."],
    ["앱에 잠금을 걸 수 있나요?",
      "내 정보 → 앱 잠금을 켜면 앱을 열 때 지문으로 확인합니다."],
    ["탈퇴하면 자료는 어떻게 되나요?",
      "탈퇴 후 3개월 동안 보관했다가 완전히 파기합니다. 그 안에 다시 로그인하시면 자료가 그대로 살아납니다."],
    ["광고 메일·문자를 그만 받고 싶어요.",
      "내 정보 → 알림·수신 설정에서 언제든 끌 수 있습니다. 끄셔도 서비스 이용에는 아무 영향이 없습니다."],
  ]],
];
/* 문의에 자동으로 붙이는 정보. 「무슨 폰 쓰세요? 앱 버전은요?」를 되묻는 왕복 한 번이 하루를 잡아먹는다.
   ⚠ versionName(android/app/build.gradle)과 같은 값이어야 한다 — 올릴 때 같이 고칠 것. */
const APP_VERSION = "1.0";
function deviceLabel() {
  const ua = navigator.userAgent || "";
  const and = ua.match(/Android\s+([\d.]+)/);
  // 안드로이드 UA의 모델명은 «; SM-S911N Build/» 꼴로 들어온다
  const model = ua.match(/;\s*([^;)]+?)\s+Build\//);
  if (and) return `안드로이드 ${and[1]}${model ? " · " + model[1] : ""}`;
  if (/iPhone|iPad/.test(ua)) return "iOS";
  return "웹";
}

// 문의 종류 — 서버 api_support.js CATEGORIES 와 같은 값이어야 한다
const ASK_CATS = [
  ["data", "학교정보(급식·시간표·일정)"],
  ["record", "기록·사진"],
  ["payment", "이용권·결제"],
  ["account", "계정·탈퇴"],
  ["bug", "오류·앱이 이상해요"],
  ["other", "그 밖의 문의"],
];

/* ═══ 인앱결제 (2026-07-31 틀만) ═══════════════════════════
   앱에서 파는 이용권은 **구글 인앱결제가 강제**다(PG 못 씀). 수수료는 15%(연 100만 달러까지).
   Play 개발자 계정이 열리면 ①on = true ②Play Console 에 상품 4개를 아래 ID 로 등록
   ③@capacitor-community/admob 처럼 결제 플러그인 설치 — 화면·서버는 손대지 않는다.
   상품은 **소모성**으로 만든다(자동갱신 구독 아님): 약관에 «자동 갱신은 명시 동의 시만»이라 적었다. */
const BILLING = {
  on: false,
  products: { 1: "pass_1m", 3: "pass_3m", 6: "pass_6m", 12: "pass_12m" },
};
const billingPlugin = () =>
  window.Capacitor?.Plugins?.InAppPurchase || window.Capacitor?.Plugins?.Purchases ||
  window.Capacitor?.Plugins?.GooglePlayBilling || null;

/* ── 앱 표시 「별이」 (2026-08-03 지시) ──────────────────────────────
   로그인 머리에 **서랍 모양 표시**를 그리고 있었는데, 앱 아이콘은 «밤하늘 + 웃는 별»이다.
   설치 아이콘과 첫 화면이 다르면 «다른 앱을 연 것» 같다 → 아이콘과 **같은 도형**을 쓴다.
   ⚠ 파일로 안 넣고 SVG 로 그린다 — 아이콘 원본(`app/tools/build-appicon.mjs`)과
     같은 좌표·같은 색이라, 아이콘을 고치면 여기도 같이 고쳐야 한다는 걸 잊지 말 것. */
function starMark(size = 54) {
  return `
  <svg class="lg-star" width="${size}" height="${size}" viewBox="0 0 512 512" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id="sm-bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#4A7BD4"/><stop offset="1" stop-color="#1B3F7E"/></linearGradient>
      <radialGradient id="sm-st" cx="0.35" cy="0.28" r="1">
        <stop offset="0" stop-color="#FFE58A"/><stop offset="0.55" stop-color="#FFC531"/>
        <stop offset="1" stop-color="#E89B00"/></radialGradient>
    </defs>
    <rect width="512" height="512" rx="124" fill="url(#sm-bg)"/>
    <circle cx="120" cy="100" r="7" fill="rgba(255,255,255,.7)"/>
    <circle cx="420" cy="150" r="5" fill="rgba(255,255,255,.55)"/>
    <circle cx="90" cy="330" r="5" fill="rgba(255,255,255,.4)"/>
    <circle cx="430" cy="380" r="6" fill="rgba(255,255,255,.35)"/>
    <path d="M256 78 l52 106 117 17 -85 83 20 117 -104 -55 -104 55 20 -117 -85 -83 117 -17 z" fill="url(#sm-st)"/>
    <path d="M256 100 l44 90 99 14 -20 20 c-60 -34 -150 -40 -196 -10 l-25 -24 98 -14 z" fill="rgba(255,255,255,.35)"/>
    <circle cx="222" cy="252" r="15" fill="#3A2A00"/><circle cx="290" cy="252" r="15" fill="#3A2A00"/>
    <circle cx="227" cy="246" r="5" fill="#FFF"/><circle cx="295" cy="246" r="5" fill="#FFF"/>
    <path d="M226 296 q30 26 60 0" fill="none" stroke="#3A2A00" stroke-width="12" stroke-linecap="round"/>
    <circle cx="196" cy="284" r="12" fill="rgba(255,120,90,.45)"/>
    <circle cx="316" cy="284" r="12" fill="rgba(255,120,90,.45)"/>
  </svg>`;
}

/* 자매 사이트 — 주소가 정해지면 **여기만** 채운다(url 이 비면 버튼이 안 그려진다). */
const SISTER_SITES = {
  academy: { name: "우리아이학원정보", url: "" },   // 도메인 정해지면 넣을 것
};
function sisterLink(key, title, sub) {
  const site = SISTER_SITES[key];
  if (!site?.url) return "";
  return `<button class="sisterlink" onclick="App.openSister('${jsq(key)}')">
      <span class="sl-ico"><i class='ti ti-school'></i></span>
      <span class="sl-txt"><b>${esc(title)}</b><span>${esc(sub)}</span></span>
      <span class="sl-go"><i class='ti ti-external-link'></i></span>
    </button>`;
}

/* ═══ 광고 자리 (2026-07-31 «미리 잡아놔») ═══════════════════
   앱은 애드센스가 아니라 **AdMob**이다(웹 태그를 넣으면 정책 위반).
   지금은 **자리만** 잡아둔다 — Play 개발자 계정이 열리면 여기 unitId 를 채우고
   @capacitor-community/admob 플러그인만 붙이면 화면은 손대지 않는다.

   ⚠ 돈 낸 사람에게는 안 띄운다 — 2,900원의 값어치가 «광고 없음»이기도 하다.
      체험 중(무료로 쓰는 동안)에만 보인다. ADS.on=false 면 어디에도 안 나온다. */
const ADS = {
  on: false,                 // 플러그인·단위ID 준비되면 true
  showToPaid: false,         // 유료 이용권 사용자에게도 띄울지(기본 안 띄움)
  slots: {
    home:   { unitId: "", label: "홈 하단" },      // 홈 카드 묶음 아래
    drawer: { unitId: "", label: "서랍 목록" },    // 기록(서랍) 학년 목록 위
  },
};
/* 광고 한 칸. 자리를 실제로 차지하게 그린다 —
   나중에 광고가 들어왔을 때 화면이 «밀리는» 일이 없어야 한다(레이아웃 이동 방지). */
function adSlot(key) {
  if (!ADS.on || !ADS.slots[key]) return "";
  const c = cur();
  const paid = passOpen(c) && passDaysLeft(c) > 14;   // 체험이 아니라 실제 구매 상태
  if (paid && !ADS.showToPaid) return "";
  return `<div class="adbox" data-ad="${key}"><span>광고</span></div>`;
}

const Screens = {
  // ── 1. 로그인 — 일반(ID/비번) + 소셜. POST /api/v1/auth/login · GET /auth/{provider} ──
  /* 로그인 — 시안 9a (2026-07-27)
     없앤 것: 흰 카드 두 겹 · 「급식·시간표…부터 우리 아이 기록 보관까지」 두 줄 설명 ·
              소셜 버튼의 브랜드색·아이콘(잘림과 테마 충돌의 원인).
     들어간 것: 서랍(종이 3장 + 도장) 표시 · 입력 52px · 소셜 3등분 윤곽선 ·
              자녀폰 코드는 맨 아래 점선 한 줄. */
  /* ⚠ 위로 쏠려 있었다(2026-08-03 지시). 내용이 적은 화면을 위에 몰면 아래가 텅 비어
       «덜 만든 화면»으로 읽힌다 — 첫 실행(.ob-wrap)과 **같은 문법**으로 세로로 펼친다:
       가운데가 남는 자리를 차지하고, 자녀폰 줄은 아래에 붙는다. */
  login: () => `
    <div class="lg-wrap">
    <div class="lg">
      <div class="lg-hd">
        ${starMark()}
        <div>
          <h1 class="lg-title">아이<span class="br">서랍</span></h1>
          <p class="lg-sub">학교 소식과 아이의 12년</p>
        </div>
      </div>

      <div class="lg-form">
        <div class="lg-field"><input id="login-id" placeholder="아이디" autocomplete="username"></div>
        <div class="lg-field">
          <input id="login-pw" type="${S.pwShow ? "text" : "password"}" placeholder="비밀번호" autocomplete="current-password"
                 onkeydown="if(event.key==='Enter')App.login()">
          <button class="lg-eye" onclick="App.pwShow()">${S.pwShow ? `<i aria-hidden="true" class="ti ti-eye-off"></i>숨기기` : `<i aria-hidden="true" class="ti ti-eye"></i>보기`}</button>
        </div>
        <button class="lg-go" onclick="App.login()">${S.loginBusy ? "확인 중…" : "로그인"}</button>
      </div>

      <div class="lg-links">
        <a href="#findpw">아이디 찾기</a><i></i>
        <a href="#findpw">비밀번호 찾기</a><i></i>
        <a href="#register" class="on">가입</a>
      </div>
      <!-- 「가입이 안 돼요」를 물을 자리 — 로그인 못 하는 사람에게 로그인 뒤에 있는 문의는 소용없다 -->
      <div class="lg-links lg-help" style="margin-top:0">
        <a href="#help"><i aria-hidden="true" class="ti ti-message-circle"></i>고객센터 · 자주 묻는 질문</a></div>

      <div class="lg-or"><i></i><span>간편하게</span><i></i></div>
      <!-- 브랜드색·아이콘 없이 윤곽선 3등분 — 368px에서 안 잘리고 어떤 테마에서도 성립한다(시안 9c) -->
      <div class="lg-social">
        <button onclick="App.login()">카카오</button>
        <button onclick="App.login()">네이버</button>
        <button onclick="App.login()">Google</button>
      </div>

      ${DEV_TOOLS ? `<p class="sub" style="text-align:center;margin-top:14px">비워두고 눌러도 둘러볼 수 있어요. <b class="stub">개발용</b></p>` : ""}
    </div>

    <!-- 자녀폰은 로그인하지 않는다 — 엄마 계정이 자녀폰에 남으면 결제·기록 삭제까지 열린다(2026-07-25 확정) -->
    <div class="lg-child">
      <button onclick="location.hash='#childlink'"><i aria-hidden="true" class="ti ti-link"></i>자녀폰 연결하기</button>
    </div>
    </div>`,

  /* ── 1-2. 자녀폰 연결 — 6자리 코드 (2026-07-25) ─────────────
     자녀폰에는 엄마 계정을 넣지 않는다. 코드로 «그 아이 대화만» 되는 토큰을 받는다.
     서버: POST /api/v1/auth/child-claim (인증 불필요, 10분·1회용) */
  /* 코드 연결(0802-3 ⑤ 신규) — 첫 관문. 큰 숫자 입력, 안내는 한 줄. */
  childlink: () => `
    <a class="back" href="#login" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <div class="kd2-link">
      <h1 class="kd2-h1">숫자 6개를 넣어요</h1>
      <p class="kd2-sub">부모님 폰에 떠 있는 그 숫자예요</p>
      <input id="lk-code" class="code" inputmode="numeric" maxlength="6" placeholder="⚬⚬⚬⚬⚬⚬"
             value="${esc(S.linkCode)}" oninput="S.linkCode=this.value.replace(/[^0-9]/g,'')"
             onkeydown="if(event.key==='Enter')App.childLink()">
      ${S.linkErr ? `<p class="err">${esc(S.linkErr)}</p>` : ""}
      <button class="kd2-cta" onclick="App.childLink()">${S.linkBusy ? "확인 중…" : "연결하기"}</button>
      <p class="fine"><i aria-hidden="true" class="ti ti-lock"></i> 이 폰엔 부모님 계정이 저장되지 않아요</p>
    </div>`,

  /* ── 1-1. 비밀번호 찾기 (2026-07-25) ─────────────────────────
     두 가지를 같은 페이지가 맡는다:
       ① 비밀번호를 잊었을 때
       ② 로그인 10회 실패로 잠겼을 때 — 기다리지 말고 여기서 본인 확인하고 바로 푼다(사장님 지시)
     ⚠ 지금은 **화면만** 있다. 실제로 코드를 보내려면 메일 발송이 붙어야 하고,
       법적 본인확인(휴대폰 실명인증)은 나중에 붙인다(사장님: "법적인 건 추후").
       서버에 필요한 것: POST /auth/find-password (코드 발송) · /auth/reset-password (코드+새 비번) */
  /* 비밀번호 찾기 — ⚠ 지금은 «준비 중»을 정직하게 말하는 화면이다(2026-08-03 전수검사 2번).
     그 전엔 이메일 코드·카카오 확인·새 비번까지 전부 목업이었다 — 아무 6자리나 통과되고
     비번은 서버에 가지도 않으면서 「다 됐어요」가 나왔다. 안 되는 걸 되는 척하는 게 최악이다.
     메일 인프라(도메인)가 붙으면 원래 4단계 흐름을 복원한다(git: 832df8f 이전). */
  /* ── 첫 실행 설문 (2026-08-03 지시서 0803-1 §5) ─────────────
     그림 넘기기 4장을 **설문 3문항**으로 바꿨다. 넘기는 장은 아무것도 안 남기지만,
     이건 답이 그대로 앱에 쓰인다. **쓰이지 않을 것은 묻지 않는다.**
     설문 → (로그인·가입) → 자녀 등록 → 홈에서 코치마크 3장 + 첫 행동. */
  /* 첫 실행 — 세 단계다(2026-08-03 §5):
       ① 소개 슬라이드 3장 → ② 설문 3문항 → ③ 알림 권한 → (가입 · 자녀 등록 · 테마 · 코치마크)
     ⚠ 슬라이드 그림은 **파일이 아직 없다.** 자리(슬롯)만 잡아 두고 색면으로 대신한다 —
       파일이 오면 style.css 의 --intro-1~3 한 줄씩만 채우면 된다(§6 «이미지 파일 우선, 슬롯 방식»). */
  intro: () => {
    const step = S.introStep || "slides";

    // ① 소개 슬라이드 — 좌우 스와이프 + 점 + 건너뛰기
    if (step === "slides") {
      const i = Math.min(S.introIdx || 0, INTRO_SLIDES.length - 1);
      const sl = INTRO_SLIDES[i];
      const last = i === INTRO_SLIDES.length - 1;
      return `
      <div class="ob-wrap" id="obslides">
        <div class="in-art2" data-slot="${i + 1}" aria-hidden="true"></div>
        <div class="ob-mid">
          <h1 class="in-t">${sl.t}</h1>
          <p class="in-s">${sl.s}</p>
          <div class="in-dots">${INTRO_SLIDES.map((_, k) => `<i class="${k === i ? "on" : ""}"></i>`).join("")}</div>
        </div>
        <div class="ob-bot">
          <button class="ob-go" onclick="${last ? "App.introToSurvey()" : "App.introNext()"}">${last ? "시작하기" : "다음"}</button>
          <!-- 2026-08-03 지시: 건너뛰기를 그림 위 오른쪽 구석에서 «주 버튼 아래»로 내렸다.
               구석의 작은 글씨는 그림과 겹쳐 잘 안 보이고 손가락도 멀다.
               «나중에»(테마·알림)와 같은 자리·같은 모양이라 규칙이 하나로 모인다. -->
          <button class="cm-skip" style="width:100%;margin-top:4px"
            onclick="App.introToSurvey()">건너뛰기</button>
        </div>
      </div>`;
    }

    // ③ 알림 권한 — **왜 필요한지 말하고** 묻는다. 이유 없이 물으면 거절이 기본값이 된다
    if (step === "notify") {
      return `
      <div class="ob-wrap">
        <div class="in-art2" data-slot="bell" aria-hidden="true"></div>
        <div class="ob-mid">
          <h1 class="in-t">아이 사진이 오면 알려드려요</h1>
          <p class="in-s">미션을 해내고 사진을 보내면 바로 알림이 가요.<br>
            저녁에 «내일 준비물» 도 한 번 알려드립니다.</p>
        </div>
        <div class="ob-bot">
          <button class="ob-go" onclick="App.introAskPush()">알림 받기</button>
          <button class="cm-skip" style="width:100%;margin-top:6px" onclick="App.introDone()">나중에</button>
        </div>
      </div>`;
    }

    // ② 설문 — 진행바 + 라디오 카드 + **하단 풀폭 계속**(고르자마자 넘어가지 않는다)
    const i = Math.min(S.introIdx || 0, OB_Q.length - 1);
    const q = OB_Q[i];
    const got = (S.onboard || {})[q.key];
    return `
    <div class="ob-wrap">
      <div class="ob-bar">${OB_Q.map((_, k) => `<i class="${k <= i ? "on" : ""}"></i>`).join("")}</div>
      ${i > 0 ? `<button class="back" style="position:static;margin-bottom:10px" onclick="App.introBack()" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></button>` : ""}
      <!-- data-n = 선택지 개수. 넷이면 CSS 가 셋과 **같은 높이**로 조여 준다 —
           문항마다 「계속」이 위아래로 움직이면 «다른 화면»처럼 읽힌다(2026-08-03 지시) -->
      <div class="ob-qbox" data-n="${q.opts.length}">
        <h1 class="ob-q">${q.q}</h1>
        <p class="ob-s">${q.s}</p>
        ${q.opts.map(([v, label, sub]) => `
          <button class="ob-opt ${got === v ? "on" : ""}" onclick="App.obSet('${q.key}', '${jsq(v)}')">
            <i class="rd"></i><span>${label}</span>${sub ? `<em>${sub}</em>` : ""}
          </button>`).join("")}
      </div>
      <div class="ob-bot">
        <!-- 「건너뛰기」를 뺐다(대표님 지시 2026-08-09).
             이 화면은 **앱을 누구에게 맞출지 정하는 자리**다 — 부모 유형·자녀 수·나이대를
             모르면 첫 화면부터 엉뚱한 걸 보여주게 된다. 물음이 셋뿐이고 전부 한 번 누르면 끝이다.
             ⚠ 대신 «뒤로»(←)는 남긴다. 앞 답을 고칠 길까지 막으면 갇힌 느낌이 든다. -->
        <button class="ob-go" ${got ? "" : "disabled"} onclick="App.obNext()">계속</button>
      </div>
    </div>`;
  },

  /* ── 비회원 «둘러보기» 홈 (2026-08-03 지시) ─────────────────────
     회원 홈을 그대로 쓰지 않는다. 자녀가 없는 채로 그리면 미션·서랍 자리가 빈 껍데기가 되고
     잠금이 샐 구멍이 열두 군데 생긴다. 여기서는 **학교에서 오는 것만** 보여준다. */
  findpw: () => `
    <a class="back" href="#login" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 class="pg-h">비밀번호 찾기</h1>
    <p class="sub">이메일 재설정 기능을 준비하고 있어요</p>

    <div class="card" style="margin-top:16px">
      <b style="display:block;font-size:15px;margin-bottom:8px">지금은 이렇게 도와드려요</b>
      <p class="sub" style="margin:0 0 14px;line-height:1.7">
        <b>카카오·네이버·구글로 가입</b>하셨다면 — 로그인 화면에서 그 버튼으로 바로 들어올 수 있어요.<br>
        <b>아이디로 가입</b>하셨다면 — 고객센터로 문의해 주세요. 본인 확인 후 바로 풀어드립니다.</p>
      <button class="btn-primary" onclick="location.hash='#help'">고객센터 가기</button>
      <button class="btn-line" style="margin-top:8px" onclick="location.hash='#login'"><i aria-hidden="true" class="ti ti-chevron-left"></i>로그인으로 돌아가기</button>
    </div>`,

  register: () => {
    const r = S.reg;
    const field = (key, label, opts) => {
      const v = r[key] || "";
      // 앞칸 검사는 앱이(형식), 뒷칸 검사는 서버가(중복·약관) 한다. 서버 답이 있으면 그게 우선이다.
      const msg = (v ? regCheck(key, v) : null) || S.regServerErr[key] || null;
      return `
        <label class="f">${label}</label>
        <input id="reg-${key}" ${opts.type ? `type="${opts.type}"` : ""} ${opts.mode ? `inputmode="${opts.mode}"` : ""}
          placeholder="${esc(opts.ph)}" value="${esc(v)}" oninput="App.regSet('${key}', this.value)"
          class="${msg ? "bad-input" : v ? "ok-input" : ""}">
        ${msg ? `<p class="fielderr">${msg}</p>` : v ? `<p class="fieldok"><i class='ti ti-check'></i> 좋아요</p>` : ""}`;
    };
    return `
    <a class="back" href="#login" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 style="margin-top:8px">회원가입</h1>
    <p class="sub">휴대폰 번호는 비밀번호를 잊었을 때만 써요.</p>
    <div class="card">
      ${field("userid", "아이디 *", { ph: "영문·숫자 4자 이상" })}
      ${field("pw", "비밀번호 *", { type: "password", ph: "8자 이상, 영문+숫자" })}
      ${field("pw2", "비밀번호 확인 *", { type: "password", ph: "다시 한 번" })}
      ${field("name", "이름 *", { ph: "보호자 이름" })}
      ${field("birth", "생년월일 *", { ph: "19850312", mode: "numeric" })}
      ${field("email", "이메일 *", { ph: "비밀번호 찾기에 쓰여요" })}
      ${field("phone", "휴대폰 (선택)", { ph: "01012345678", mode: "numeric" })}
      <div class="check"><input type="checkbox" id="t1" ${r.t1 ? "checked" : ""} onchange="App.regSet('t1', this.checked)"><label for="t1">이용약관 동의 (필수)</label><a class="see" href="#terms">보기</a></div>
      <div class="check"><input type="checkbox" id="t2" ${r.t2 ? "checked" : ""} onchange="App.regSet('t2', this.checked)"><label for="t2">개인정보 수집·이용 동의 (필수)</label><a class="see" href="#policy">보기</a></div>
      <!-- 광고성 수신(선택, 2026-07-31) — 켜면 채널 셋이 나온다. 기본 전부 체크, 끄는 건 자유.
           동의 여부·일시는 서버(accounts.marketing)에 남는다 — 정보통신망법상 기록 의무. -->
      <div class="check"><input type="checkbox" id="t3" ${r.t3 ? "checked" : ""} onchange="App.regSet('t3', this.checked)"><label for="t3">혜택·소식 받기 (선택)</label></div>
      ${r.t3 ? `<div class="reg-mkt">
        ${[["m1", "메일"], ["m2", "문자"], ["m3", "전화"]].map(([k, nm]) => `
          <label class="mk"><input type="checkbox" ${r[k] !== false ? "checked" : ""} onchange="App.regSet('${k}', this.checked)">${nm}</label>`).join("")}
      </div>` : ""}
      <!-- 가입 다음은 곧바로 자녀 등록이다. 자녀가 없으면 앱이 보여줄 게 없다(2026-07-24 확정). -->
      <div style="margin-top:16px"><button class="btn-primary" onclick="App.registerDone()">
        ${S.regBusy ? "확인 중…" : "가입하고 자녀 등록하기"}</button></div>
      ${S.regServerErr._ ? `<p class="fielderr" style="text-align:center">${S.regServerErr._}</p>` : ""}
    </div>`;
  },

  /* ── 2-1. 이용약관 · 개인정보처리방침 (2026-07-31) ─────────────
     문안 정본은 워커 templates.js(/terms·/privacy — 스토어 심사가 보는 URL)와 같다.
     앱 안에도 두는 이유: 가입 화면·내정보에서 서버 없이(오프라인·심사 중) 바로 읽혀야 한다.
     ⚠ 한쪽을 고치면 반드시 양쪽을 같이 고칠 것. */
  terms: () => legalScreen("이용약관", LEGAL.terms),
  policy: () => legalScreen("개인정보처리방침", LEGAL.privacy),

  /* ── 2-5. 미션 — 부모 화면 (2026-08-01) ──────────────────────
     「오늘 뭘 줬나」와 「애가 했나」 두 가지만 보면 되는 화면이다.
     부모가 안 들어와도 3개는 이미 차 있다 — 여기서는 **보고 넘기거나 갈아끼우기만** 한다. */
  mission: () => {
    const c = cur();
    const list = S.missions;
    /* ⚠ 아이가 없으면(구경 중) 미션을 부를 데가 없어 **«불러오는 중…»에서 영영 멈췄다**
       (2026-08-04 실측). 안 오는 것과 없는 것은 다르다 — 없는 쪽을 정직하게 말한다. */
    if (!c) return `${subHeader("미션")}
      <div class="ms-empty">
        <b>아이를 등록하면 시작해요</b>
        <button class="btn-primary" onclick="location.hash='#register'">아이 등록하기</button>
      </div>`;
    if (list === null) return `${subHeader("미션")}<p class="sub">불러오는 중…</p>`;

    const done = list.filter((x) => x.status === "done").length;
    const waiting = list.filter((x) => x.status === "waiting");
    const ST = {
      open:    { ko: "아직", cls: "ms-open" },
      waiting: { ko: "확인 기다림", cls: "ms-wait" },
      done:    { ko: "완료", cls: "ms-done" },
      skipped: { ko: "못 했어요", cls: "ms-skip" },
    };

    return `
    ${subHeader("미션")}
    <p class="sub">오늘 <b>${esc(c.nickname)}</b>에게 준 것 · 모은 도장 <b class="ms-star">★ ${S.missionStars}</b></p>
    ${childLinkWarn()}

    <!-- 🎲 리롤 — 하루 한 번. «하루 한 번»은 서버의 PRIMARY KEY(child_id, ymd) 가 강제한다.
         화면은 세지 않는다 — 앱이 세면 폰 두 대에서 각자 세다가 두 번 바뀐다.
         ⚠ 아직 시작 안 한 것만 바뀐다. 해낸 것(확인 기다림·완료)은 그대로 둔다 —
           해낸 것을 리롤로 날리면 그건 보상이 아니라 벌이다. -->
    ${list.some((x) => x.status === "open") ? `<button class="ms-reroll" onclick="App.msReroll()">
      🎲 <span><b>오늘 미션 바꾸기</b><em>하루 한 번 · 아직 시작 안 한 것만</em></span></button>` : ""}

    ${list.map((x, i) => {
      const st = ST[x.status] || ST.open;
      /* 카드 = 번호·이름·상태 셋만. 자세한 건 눌러서(시안 2026-08-03) */
      return `
      <button class="msc ${st.cls}" onclick="App.msOpen(${x.id})">
        <span class="msc-no">${x.status === "done" ? `<i aria-hidden="true" class="ti ti-check"></i>` : i + 1}</span>
        <b>${esc(x.title)}</b>
        <span class="msc-tag">${x.status === "waiting" ? (x.verify === "review" ? "사진 확인" : "확인하기") : x.status === "open" ? `★${x.stars}` : st.ko}</span>
      </button>`;
    }).join("")}

    ${(() => {
      /* 카드 상세 시트 — 확인·되돌리기·바꾸기가 전부 이 안 */
      const x = list.find((v) => v.id === S.msDetail);
      if (!x) return "";
      const st = ST[x.status] || ST.open;
      return `
      <div class="modal sheetwrap" onclick="App.msClose()">
        <div class="sheet" onclick="event.stopPropagation()">
          <div class="sheet-grip"></div>
          <h2 class="msc-dt">${esc(x.title)}</h2>
          <div class="msc-meta">
            <em>${esc(MISSION_AREA[x.area] || "")}</em>${x.minutes ? `<em>${x.minutes}분</em>` : ""}<em class="star">★${x.stars}</em><em>${x.verify === "review" ? "사진 확인" : x.verify === "endday" ? "하루 끝 확인" : "눌러서 보고"}</em><em>${st.ko}</em>
          </div>
          ${x.status === "waiting" ? `
            ${x.verify === "review"
              ? `<img class="msc-photo" src="${PLACEHOLDER}" data-rec="/api/v1/missions/${x.id}/photo" alt="아이가 보낸 사진">`
              : `<p class="msc-said">아이가 <b>다 했어요</b>를 눌렀어요</p>`}
            <button class="btn-primary" onclick="App.missionApprove(${x.id})"><i aria-hidden="true" class="ti ti-check"></i>잘했어! 도장 찍기</button>
            ${x.verify !== "review" ? "" : `
            <!-- 사진 확인에 따라붙는 «서랍에 보관» (2026-08-03 §2) — 도장은 오늘 것이고 서랍은 12년 것이다.
                 도장을 찍으면 사진은 미션에서 사라진다. 남기고 싶은 한 장은 여기서 서랍으로 옮긴다. -->
            <button class="msc-keep ${S.keepShot === x.id ? "on" : ""}" onclick="App.keepShot(${x.id})">
              <i aria-hidden="true" class="ti ${S.keepShot === x.id ? "ti-check" : "ti-photo"}"></i>
              ${S.keepShot === x.id ? "도장 찍을 때 서랍에 넣어요" : "서랍에 보관하기"}</button>`}
            <button class="msc-sub" onclick="App.missionRevert(${x.id});App.msClose()">다시 해볼까?</button>
            <p class="mp-hint" style="text-align:center">안 보면 <b>아침 8시</b> 자동</p>`
          : x.status === "open" ? `
            <button class="btn-primary" onclick="App.msClose();App.missionPickOpen()"><i aria-hidden="true" class="ti ti-grip-vertical"></i>다른 미션으로 바꾸기</button>`
          : `
            <button class="btn-primary" onclick="App.missionRevert(${x.id});App.msClose()">${x.status === "skipped" ? "다시 줘볼까?" : "다시 해볼까?"}</button>`}
        </div>
      </div>`;
    })()}

    <!-- ── 2단계 보상의 «2차» (2026-08-07 §3.2) ────────────────────────────
         1차는 아이가 낸 순간 서버가 도장 1개를 준다. 여기는 **부모가 보고 보너스를 주는** 자리다.
         ⚠ 목적은 «대충 하면 기본 1개, 정성껏 하면 보너스»를 아이가 몸으로 익히는 것이다.
           그래서 보너스를 **안 주는 것도 정상 동작**이다 — 「확인만 하기」를 같이 둔다.
         ⚠ 서버가 «한 번만»을 지킨다. 두 번 눌러도 도장이 두 번 나가지 않는다. -->
    ${(() => {
      const kid = isChildToken() || S.childView || S.kidMode;
      const pend = kid ? [] : (S.verifyPending || []);
      if (!pend.length) return "";
      return `
      <div class="vf-wrap">
        <h2 class="vf-t">확인해 주세요 <em>${pend.length}</em></h2>
        <p class="vf-sub">문제집·독서록을 보고 정성껏 했으면 보너스를 줘요.</p>
        ${pend.map((v) => {
          const busy = S.verifyBusy === v.verify_id;
          return `
          <div class="vf">
            <div class="vf-bd">
              <b>${esc(v.mission_code)}</b>
              ${v.step1_data ? `<em>${esc(v.step1_data)}</em>` : ""}
              <span class="vf-at">${esc(fmtIsoDay(v.created_at))} 냈어요</span>
            </div>
            <div class="vf-act">
              ${[1, 2, 3].map((n) => `
                <button class="vf-b" ${busy ? "disabled" : ""}
                  onclick="App.verifyBonus('${v.verify_id}', ${n})">★${n}</button>`).join("")}
              <button class="vf-b none" ${busy ? "disabled" : ""}
                onclick="App.verifyBonus('${v.verify_id}', 0)">확인만</button>
            </div>
          </div>`;
        }).join("")}
      </div>`;
    })()}

    <!-- 칭찬 스티커 — 1초 만에 고른다(§5⑤). 아이 폰에 큰 팝업으로 뜬다 -->
    ${(isChildToken() || S.childView || S.kidMode) ? "" : `
    <button class="ms-mkbtn" onclick="App.reactOpen(${c.server_id || 0})">
      <i aria-hidden="true" class="ti ti-award"></i>
      <span><b>칭찬 보내기</b><em>아이 화면에 스티커가 떠요</em></span></button>`}

    <!-- 스타코인 상점 — 모은 도장을 쓰는 자리. 미션 화면에서 바로 간다 -->
    <button class="ms-mkbtn" onclick="location.hash='#store'">
      <i aria-hidden="true">★</i>
      <span><b>스타코인 상점</b><em>모은 도장으로 바꿔요</em></span></button>

    <!-- 리포트 — 일일 퀘스트가 쌓아온 것을 부모가 보는 자리(2026-08-03) -->
    <button class="ms-mkbtn" onclick="location.hash='#report'">
      <i aria-hidden="true" class="ti ti-chart-bar"></i>
      <span><b>이번 달 리포트</b><em>반찬 · 친구 · 과목</em></span>
    </button>
    <!-- 우리 집 미션은 시트 안쪽이 아니라 여기서도 바로 열린다 — 부모가 제일 하고 싶어 하는 일이다 -->
    <button class="ms-mkbtn" onclick="App.missionMakeOpen()">
      <i aria-hidden="true" class="ti ti-plus"></i>
      <span><b>우리 집 미션 만들기</b><em>구몬 3장 · 윙크 20분처럼</em></span>
    </button>
    <p class="mp-hint">매일 아침 세 개가 자동으로 차요</p>

    <!-- 미션 고르기 «반쪽 시트» 폐지(2026-08-03) — 전용 화면 Screens.missionpick 이 대신한다.
         고를 것이 수십 개라 시트로는 절반밖에 못 봤다. -->
    ${reactSheetView()}
    ${stickerView()}
`;
  },

  /* ═══ 🎮 미션 게임 — 아이의 세계 (2026-08-08 기획서 §01·§08) ═══════════
     하단 ★ 로 들어온다. 부모 앱 위에 얹힌 화면이 아니라 **다른 세계**로 보여야 한다:
     머리띠·카드 문법을 그대로 쓰지 않고, 상태창 하나로 시작한다.
     ⚠ 이 화면 묶음이 그대로 모듈 B(글로벌 단독 앱)가 된다 — 학교 데이터 참조는
       「학교 미션」 한 줄로만 두어 나중에 끊기 쉽게 한다.
     ⚠ 코인·리밋은 **서버가 준 값만** 쓴다. 화면이 더하거나 세지 않는다. */
  game: () => {
    const c = curView();
    const coin = S.coin || { stars: 0, earned_today: 0, limit: COIN_LIMIT, room: COIN_LIMIT, level: 1 };

    /* ⚠⚠ **부모에게 아이 세계를 보여주지 않는다.**
       ★ 를 누르면 아이 폰에서는 «게임», 부모 폰에서는 «관리 화면»이다.
       부모 페이지는 관리자 페이지다 — 화려할 필요 없고 알아보기 쉬우면 된다(대표님 지시 08-08).
       아이 세계를 보고 싶으면 «아이 화면 미리보기»로 일부러 들어간다. */
    const kid = isChildToken() || S.kidMode;
    if (!kid && !S.gamePreview) return parentMissionAdmin(c, coin);

    /* 안쪽 화면(카드를 열었거나 상점·프로필)이면 그쪽을 그린다.
       ⚠ 탭이 아니다 — 탭은 부모 앱의 문법이고, 아이 화면은 «들어갔다 나오는» 문법이다. */
    const inner = { morning: 1, school: 1, after: 1, today: 1, shop: 1, profile: 1 }[S.gameTab];
    if (inner) {
      /* 문제를 푸는 «동안»에는 배경이 붉어진다 — 보스전이라는 신호이자,
         배경색 5종 중 무엇을 골랐든 이 순간만은 같은 긴장감이 되게 한다(시안 v4 ②). */
      const playing = S.gameTab === "today" && !S.quizResult && S.quiz
                   && !S.quiz.done && S.quizIdx >= 0;
      /* ⚠ 홈만 «화면에 딱 맞는» 고정 높이다. 안쪽 화면(상점·카드·프로필)은 줄이 늘어나므로
         고정 높이 flex 로 두면 스크롤이 아니라 **자식이 눌려서 서로 겹친다**(08-08 실기).
         그런 화면에는 `sc` 를 붙여 보통 문서처럼 흐르게 한다. */
      const scroll = S.gameTab !== "today" || !!S.quizResult || !!(S.quiz && S.quiz.done);
      return `<div class="gm ${playing ? "qzp" : gmTheme()}${scroll ? " sc" : ""}">${
        S.gameTab === "shop"    ? gameShop()
      : S.gameTab === "profile" ? gameProfile(c, coin)
      : S.gameTab === "today"   ? gameQuiz()
      :                           gameCard(S.gameTab)
      }</div>${stickerView()}${clearView()}`;
    }

    const pct = coin.limit ? Math.min(100, Math.round((coin.earned_today / coin.limit) * 100)) : 0;
    const tiles = gameCats().map((t) => gameTile(t)).join("");

    return `
    <div class="gm ${gmTheme()}">
      <!-- 캐릭터 시트 — 아바타 자리는 비워 둔다(캐릭터는 업데이트 분, 기획서 v2 §01.4) -->
      <div class="gm-hero">
        ${(!isChildToken() && !S.kidMode && S.gamePreview)
          ? `<button class="gm-ava" onclick="App.gamePreviewOff()" aria-label="미리보기 끝내기">‹</button>`
          : `<button class="gm-ava" onclick="App.gameTab('profile')" aria-label="내 프로필">${gmAvatar(c)}</button>`}
        <div class="gm-me">
          <span class="gm-lv">Lv.${coin.level || 1} ${gmRank(coin.level || 1)}</span>
          <b class="gm-nm">${esc(c.nickname || "나")}</b>
        </div>
        <div class="gm-purse"><i aria-hidden="true">★</i><b>${coin.stars}</b></div>
      </div>

      <!-- 오늘 얼마나 벌었나 — 상한이 게임의 시계다(기획서 v2 §02) -->
      <div class="gm-xp">
        <div class="gm-xpb"><span style="width:${pct}%"></span></div>
        <div class="gm-xpt">오늘 ${coin.earned_today} / ${coin.limit}
          ${coin.room > 0 ? `<em>${coin.room}개 더!</em>` : `<em class="full">오늘은 여기까지</em>`}</div>
      </div>

      <!-- 2×2 타일 — 홈이든 카드 안이든 «같은 문법»이라 아이가 배울 것이 없다 -->
      <div class="gm-grid">${tiles}</div>

      ${gmShopBar(true)}
    </div>
    ${stickerView()}${clearView()}`;
  },

  /* ── 스타코인 상점 (2026-08-07 지시서 §5③) ────────────────────────────
     아이는 «사는 것»만, 부모는 «진열대 고치기»까지. 같은 화면 안에서 갈린다.
     ⚠ 말은 게이밍 언어다 — 「바꾸기」「🎟 티켓」. 구매·결제·주문이라고 쓰지 않는다(§1.1).
     ⚠ 못 사는 이유(`reason`)를 **서버가 준 대로** 보여 준다. 버튼만 흐리게 하면
       아이는 «고장»으로 읽는다 — 왜 안 되는지가 화면에 있어야 한다. */
  store: () => {
    const c = cur();
    const kid = isChildToken() || S.childView || S.kidMode;
    if (!c) return `${subHeader("스타코인 상점")}
      <div class="ms-empty">
        <b>아이를 등록하면 열려요</b>
        <button class="btn-primary" onclick="location.hash='#register'">아이 등록하기</button>
      </div>`;
    if (S.store === null) return `${subHeader("스타코인 상점")}<p class="sub">불러오는 중…</p>`;

    const stars = S.missionStars || 0;
    const why = { limit: "이번 기간엔 다 바꿨어요", stars: "스타코인이 모자라요" };

    return `
    ${subHeader("스타코인 상점")}
    <div class="st-purse"><i aria-hidden="true">★</i><b>${stars}</b><em>지금 가진 스타코인</em></div>

    ${!S.store.length ? `
      <div class="ms-empty">
        <b>진열대가 비어 있어요</b>
        ${kid ? "" : `<button class="btn-primary" onclick="App.storeAddOpen()">진열대에 올리기</button>`}
      </div>` : `
      <ul class="st-list">
        ${S.store.map((it) => {
          const busy = S.storeBusy === it.item_id;
          const lim = it.limit_type
            ? `<em class="st-lim">${it.limit_type === "weekly" ? "주" : "달"} ${it.limit_count}번 중 ${it.used}번</em>` : "";
          return `
          <li class="st-item ${it.can_buy ? "" : "off"}">
            <div class="st-bd"><b>${esc(it.title)}</b>${lim}</div>
            <div class="st-act">
              <span class="st-need">★${it.stars_required}</span>
              ${S.storeEdit && !kid
                ? `<button class="st-del" onclick="App.storeDel('${it.item_id}')" aria-label="내리기">
                     <i aria-hidden="true" class="ti ti-trash"></i></button>`
                : `<button class="st-buy" ${it.can_buy && !busy ? "" : "disabled"}
                     onclick="App.storeBuy('${it.item_id}')">${busy ? "…" : "바꾸기"}</button>`}
            </div>
            ${it.can_buy ? "" : `<p class="st-why">${why[it.reason] || ""}</p>`}
          </li>`;
        }).join("")}
      </ul>
      ${kid ? "" : `
      <div class="st-tools">
        <button class="ms-mkbtn" onclick="App.storeAddOpen()">
          <i aria-hidden="true" class="ti ti-plus"></i>
          <span><b>진열대에 올리기</b><em>무엇과 바꿔 줄지 정해요</em></span></button>
        <button class="ms-mkbtn" onclick="App.storeEditToggle()">
          <i aria-hidden="true" class="ti ${S.storeEdit ? "ti-check" : "ti-pencil"}"></i>
          <span><b>${S.storeEdit ? "다 고쳤어요" : "진열대 고치기"}</b><em>올린 것을 내려요</em></span></button>
      </div>`}`}

    <button class="ms-mkbtn" onclick="location.hash='#tickets'">
      <i aria-hidden="true" class="ti ti-receipt"></i>
      <span><b>내 티켓</b><em>바꾼 것들이 여기 모여요</em></span></button>

    ${storeAddSheet()}`;
  },

  /* ── 내 티켓 (reward_orders) ────────────────────────────────────
     ⚠ 서버는 requested / fulfilled 로 적지만 화면에는 «기다리는 중» / «받았어요» 로만 쓴다.
     ⚠ 「바꿔줬어요」는 부모만 누른다 — 아이가 스스로 받았다고 처리하면 그건 기록이 아니다. */
  tickets: () => {
    const c = cur();
    const kid = isChildToken() || S.childView || S.kidMode;
    // 빈 상태는 상점과 **같은 문법**으로 — 한쪽만 맨 글씨면 덜 만든 화면으로 읽힌다
    if (!c) return `${subHeader("내 티켓")}
      <div class="ms-empty">
        <b>아이를 등록하면 열려요</b>
        <button class="btn-primary" onclick="location.hash='#register'">아이 등록하기</button>
      </div>`;
    if (S.rewards === null) return `${subHeader("내 티켓")}<p class="sub">불러오는 중…</p>`;
    if (!S.rewards.length) return `${subHeader("내 티켓")}
      <div class="ms-empty">
        <b>아직 바꾼 게 없어요</b>
        <button class="btn-primary" onclick="location.hash='#store'">상점 열기</button>
      </div>`;

    return `
    ${subHeader("내 티켓")}
    <ul class="tk-list">
      ${S.rewards.map((o) => {
        const done = o.status === "fulfilled";
        const busy = S.storeBusy === o.reward_order_id;
        return `
        <li class="tk ${done ? "done" : "wait"}">
          <span class="tk-ic" aria-hidden="true">🎟</span>
          <div class="tk-bd">
            <b>${esc(o.item_title)}</b>
            <em>★${o.stars_spent} · ${esc(fmtIsoDay(o.created_at))}</em>
          </div>
          ${done
            ? `<span class="tk-st done">받았어요</span>`
            : kid
              ? `<span class="tk-st">기다리는 중</span>`
              : `<button class="tk-give" ${busy ? "disabled" : ""}
                   onclick="App.rewardFulfill('${o.reward_order_id}')">${busy ? "…" : "바꿔줬어요"}</button>`}
        </li>`;
      }).join("")}
    </ul>`;
  },

  /* ── 아이 모드 + 4자리 PIN (§0-6 · §5④) ─────────────────────────
     부모 폰을 같이 쓰는 저학년용. **들어갈 땐 안 묻고 나올 때만 묻는다.** */
  childmode: () => {
    /* ⚠ 로그인 전에는 서버에 물어볼 수 없다 → `pinHas` 가 null 로 남는다.
       그대로 두면 「확인하는 중…」이 **영영** 떠 있다(2026-08-07 에뮬 실기에서 잡음).
       미션 화면에서 겪은 그 함정과 같다 — **안 오는 것과 없는 것은 다르다.**
       없는 쪽을 정직하게 말하고 길을 준다. */
    if (!S.loggedIn) return `${subHeader("아이 모드")}
      <div class="ms-empty">
        <b>가입하면 쓸 수 있어요</b>
        <button class="btn-primary" onclick="location.hash='#register'">가입하기</button>
      </div>`;
    const has = S.pinHas;
    return `
    ${subHeader("아이 모드")}
    <p class="sub">아이에게 폰을 잠깐 넘길 때 켜요. 서랍·설정이 숨고 <b>미션과 상점만</b> 보여요.</p>

    <div class="cm-card">
      <div class="cm-row">
        <div class="cm-bd"><b>나갈 때 쓸 번호</b>
          <em>${has === null ? "확인하는 중…" : has ? "정해져 있어요" : "아직 없어요"}</em></div>
        <button class="cm-btn" onclick="App.pinOpen('set')">${has ? "바꾸기" : "정하기"}</button>
      </div>
      ${!has ? "" : `
      <div class="cm-row">
        <div class="cm-bd"><b>번호 지우기</b><em>아이 모드를 그만 쓸 때</em></div>
        <button class="cm-btn sub" onclick="App.pinOpen('clear')">지우기</button>
      </div>`}
    </div>

    <button class="btn-primary cm-go" onclick="App.kidModeOn()">
      <i aria-hidden="true" class="ti ti-user"></i> 아이 모드 켜기</button>
    <p class="mp-hint">번호를 다섯 번 틀리면 5분 동안 잠겨요.</p>

    ${pinPadView()}`;
  },

  /* ── 2-2. 고객센터 (2026-08-01) ───────────────────────────────
     한 화면에 다 넣는다: 답이 왔는지 → 자주 묻는 질문 → 그래도 안 되면 문의.
     순서가 곧 안내다. 문의 버튼을 맨 위에 두면 FAQ를 아무도 안 읽고 같은 질문이 계속 들어온다. */
  help: () => {
    const unread = (S.inquiries || []).filter((x) => x.status === "answered" && !x.seen_at).length;
    const q = (S.faqQ || "").trim().toLowerCase();
    const groups = FAQ
      .map(([sec, rows]) => [sec, rows.filter(([a, b]) => !q || (sec + a + b).toLowerCase().includes(q))])
      .filter(([, rows]) => rows.length);
    const hitCount = groups.reduce((n, [, rows]) => n + rows.length, 0);

    return `
    <a class="back" href="javascript:history.back()" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 class="pg-h">고객센터</h1>
    <p class="sub">찾아보고 없으면 바로 물어보세요</p>

    ${S.inquiries === null ? "" : (S.inquiries || []).length ? `
      <button class="hlp-my" onclick="location.hash='#asks'">
        <span class="hlp-ico"><i class='ti ti-message-circle'></i></span>
        <span class="hlp-txt"><b>내 문의 ${S.inquiries.length}건</b>
          <span>${unread ? `답변 ${unread}건이 왔어요` : "주고받은 내용 보기"}</span></span>
        ${unread ? `<em class="hlp-dot">${unread}</em>` : ""}
        <i class='ti ti-chevron-right'></i>
      </button>` : ""}

    <div class="dw-search" style="margin-top:14px">
      <i class='ti ti-search'></i>
      <input id="faqq" value="${esc(S.faqQ || "")}" placeholder="예: 환불, 시간표, 탈퇴"
        oninput="App.faqQuery(this.value)" autocomplete="off">
      ${S.faqQ ? `<button class="iconbtn" onclick="App.faqQuery('')" aria-label="지우기"><i class='ti ti-x'></i></button>` : ""}
    </div>
    ${q ? `<p class="sub" style="margin:10px 2px 0">${hitCount ? `${hitCount}개 찾았어요` : "답이 없네요 — 아래에서 물어보세요"}</p>` : ""}

    ${groups.map(([sec, rows]) => {
      const secOpen = q ? true : S.faqSec === sec;
      return `
      <div class="faq-sec ${secOpen ? "on" : ""}">
        <button class="faq-sechd" onclick="App.faqSecToggle('${jsq(sec)}')">
          <span>${esc(sec)}</span><em>${rows.length}</em>
          <i aria-hidden="true" class='ti ti-chevron-down'></i>
        </button>
        ${!secOpen ? "" : rows.map(([ques, ans]) => {
          const key = ques.slice(0, 24);
          const open = q ? true : S.faqOpen === key;   // 검색 중엔 전부 펴둔다 — 찾아놓고 또 누르게 하지 않는다
          return `
          <div class="faq-q ${open ? "on" : ""}">
            <button onclick="App.faqToggle('${jsq(key)}')">
              <span>${esc(ques)}</span><i class='ti ti-chevron-down'></i>
            </button>
            ${open ? `<p>${esc(ans)}</p>` : ""}
          </div>`;
        }).join("")}
      </div>`;
    }).join("")}

    <div class="card" style="margin-top:18px">
      <b style="display:block;font-size:14px;margin-bottom:6px">답을 못 찾으셨나요?</b>
      <p class="sub" style="margin:0 0 12px">보통 <b>1~2 영업일</b> 안에 답을 드려요</p>
      <button class="btn-primary" onclick="location.hash='#ask'">문의하기</button>
    </div>

    <!-- 사업자 정보는 통신판매업 신고 사업자의 표시 의무다. 고객센터에 두는 것이 관례이고
         스토어 심사도 여기를 본다. 약관·방침의 값과 어긋나면 안 된다. -->
    <div class="card" style="margin-top:12px">
      <p class="sub" style="margin:0;line-height:1.7">
        베이직씨엔엠 · 사업자등록번호 746-21-02507<br>
        문의 <a href="mailto:dndmotor1@gmail.com">dndmotor1@gmail.com</a><br>
        평일 10:00~18:00 (점심 12:00~13:00 · 주말·공휴일 휴무)
      </p>
      <div class="row" style="margin-top:10px">
        <button class="btn-line" onclick="location.hash='#terms'"><i aria-hidden="true" class="ti ti-file-text"></i>이용약관</button>
        <button class="btn-line" onclick="location.hash='#policy'"><i aria-hidden="true" class="ti ti-lock"></i>개인정보처리방침</button>
      </div>
    </div>`;
  },

  // ── 2-3. 문의하기 — POST /api/v1/inquiries ──
  // 앱 버전·기기·학교를 자동으로 붙인다. 「무슨 폰 쓰세요?」를 되묻는 왕복 한 번이 하루를 잡아먹는다.
  ask: () => {
    const d = S.askDraft || {};
    const c = cur();
    return `
    <a class="back" href="#help" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 class="pg-h">문의하기</h1>

    <label class="f">어떤 내용인가요?</label>
    <select id="ask-cat" onchange="App.askSet('category', this.value)">
      ${ASK_CATS.map(([k, n]) => `<option value="${k}" ${d.category === k ? "selected" : ""}>${esc(n)}</option>`).join("")}
    </select>

    <label class="f">제목</label>
    <input id="ask-title" value="${esc(d.title || "")}" maxlength="60" placeholder="한 줄로 요약해 주세요"
      oninput="App.askSet('title', this.value)">

    <label class="f">내용</label>
    <textarea id="ask-body" maxlength="2000" placeholder="언제 · 어느 화면에서 · 무엇이 안 됐는지 적어주면 빨라요"
      oninput="App.askSet('body', this.value); autoGrow(this)">${esc(d.body || "")}</textarea>

    <label class="f">답을 메일로도 받을까요? (선택)</label>
    <input id="ask-mail" type="email" value="${esc(d.contact_email || "")}" placeholder="비우면 앱으로만 알려드려요"
      oninput="App.askSet('contact_email', this.value)">

    <p class="notice" style="margin-top:14px">보내면 아래 정보가 함께 전달돼요 — 앱 ${APP_VERSION} · ${esc(deviceLabel())}${c ? ` · ${esc(c.nickname)}(${esc(c.school?.name || "학교 미등록")})` : ""}</p>

    <div class="row" style="margin-top:16px">
      <button class="btn-line" onclick="location.hash='#help'">취소</button>
      <button class="btn-primary" onclick="App.askSend()" ${S.askBusy ? "disabled" : ""}>${S.askBusy ? "보내는 중…" : "보내기"}</button>
    </div>`;
  },

  // ── 2-4. 내 문의 내역 ──
  asks: () => {
    const list = S.inquiries;
    const CAT = Object.fromEntries(ASK_CATS);
    const ST = { open: ["접수됨", "hlp-st open"], answered: ["답변 왔어요", "hlp-st ans"], closed: ["종료", "hlp-st done"] };
    return `
    <a class="back" href="#help" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 style="margin-top:8px">내 문의</h1>
    ${list === null ? `<p class="sub">불러오는 중…</p>`
      : !list.length ? `<p class="sub">아직 보낸 문의가 없어요.</p>`
      : list.map((x) => {
        const [ko, cls] = ST[x.status] || ST.open;
        const open = S.askOpen === x.id;
        return `
        <div class="card hlp-item ${open ? "on" : ""}">
          <button onclick="App.askOpenOne(${x.id})">
            <span class="hlp-hd">
              <b>${esc(x.title)}</b>
              <span class="${cls}">${ko}${x.status === "answered" && !x.seen_at ? " · 새 답변" : ""}</span>
            </span>
            <span class="sub">${esc(CAT[x.category] || "문의")} · ${x.created_at.slice(0, 10).replace(/-/g, ".")}</span>
          </button>
          ${open ? `
            <div class="hlp-body">
              <p class="hlp-mine">${esc(x.body || "")}</p>
              ${x.answer ? `<p class="hlp-ans"><b>답변</b>${esc(x.answer)}</p>`
                : `<p class="sub" style="margin:0">아직 답변 전 — 보통 1~2 영업일</p>`}
            </div>` : ""}
        </div>`;
      }).join("")}
    <div class="row" style="margin-top:16px"><button class="btn-primary" onclick="location.hash='#ask'">새 문의</button></div>`;
  },

  // ── 3. 홈 — 원형 메뉴(2026-07-24 지시: 하단 탭 버리고 크고 단순한 원형 메뉴).
  // "보고 바로 이해되고 몇 번 안 눌러 끝난다"가 승부처. 첫 화면은 비우고, 깊이는 각 페이지·팝업으로.
  /* 홈 — 시안 D (2026-08-02). 「읽는 화면」에서 「보는 화면」으로 갈아엎었다.
     그 전(시안 7b)은 상태를 단 카드 6장이 세로로 선 목록이었다. 글을 읽어야 뭔지 알았다.

     바뀐 것 셋:
       ① 오늘 꼭 봐야 하는 셋(급식 / 하교·방과후 / 내일 준비물)만 큰 카드로 올린다
       ② 나머지는 아이콘 격자 — 아이콘 + 이름 + 숫자 한 줄
       ③ 하단 고정 탭바가 돌아왔다(index.html). 상단 집버튼은 자리를 내줬다

     색 규칙 — 종류별 색은 없다. 아이콘은 --icon 회색 단색이고,
     빨강(--todo)은 «해야 할 일·미확인», 초록(--done)은 «완료»일 때만 켠다.
     ⚠ 색만으로 뜻을 전하지 않는다. 점·체크 옆에는 늘 같은 뜻의 글자가 붙는다. */
  /* ── 3. 오늘 (2026-08-03 지시서 0803-1 §2) ───────────────────
     기본 화면은 이것 하나다. 부모가 하루에 하는 일(확인·도장·준비물 체크·일정 추가)이
     **이 화면 안에서 끝나야 한다.**
     구성: 일러스트 띠 → ①지금 1줄 → ②학교 그룹 → ③아이 그룹 → 하단 3버튼.
     ⚠ 밀도: 한 줄에 한 가지, 여러 개면 «외 n». 줄 자체는 오늘카드 편집에서 끌 수 있다. */
  home: () => {
    const c = cur();
    const T = S.todayCards;
    const unread = unreadFor("parent");
    const dow = new Date(`${TODAY.slice(0, 4)}-${TODAY.slice(4, 6)}-${TODAY.slice(6)}`).getDay();
    const wdKo = ["일", "월", "화", "수", "목", "금", "토"][dow];

    // 내일 준비물 — 저녁(19시~) 배너도 같은 값을 쓴다
    const tomorrow = ymdPlus(TODAY, 1);
    const packs = STUB.supplies.filter((x) => x.date === tomorrow && !x.done);
    /* 배너 슬롯은 **행사 전용**이다(2026-08-03 지시).
       저녁 «내일 챙길 것 n개» 배너는 없앴다 — 바로 아래 준비물 버튼에 같은 숫자가 뜨고 있어서
       한 화면에 같은 말이 두 번 나왔다(§4 «기능당 입구 하나»).
       ⚠ 저녁 알림(푸시)은 그대로다. 없앤 건 «화면 안 배너»뿐이다. */
    const nextBig = schedulesOf()
      .filter((e) => e.date >= TODAY
        && !(S.holiOff && (e.closure_type || "").includes("공휴일"))
        && !e.name.includes("토요휴업일")
        && classifyEvent(e.name, e.closure_type))
      .sort((a, b) => a.date.localeCompare(b.date))[0];

    /* 한 줄 부품 — [아이콘][이름][값][>] . 값이 길면 … 로 자른다(밀도 규칙) */
    const line = (cls, icon, name, value, go) => `
      <button class="hv3-line ${cls}" onclick="${go}">
        <span class="ic ${cls}"><i aria-hidden="true" class="ti ${icon}"></i></span>
        <b>${name}</b><span class="tx">${value}</span>
        <i aria-hidden="true" class="ti ti-chevron-right go"></i>
      </button>`;

    /* ── 내용을 직접 보여주는 줄 (2026-08-03 지시) ────────────────
       「급식 ›」처럼 제목과 화살표만 있으면 **눌러야만 알 수 있다.**
       부모가 하루에 확인하는 것들이라 이름은 작게 위로 올리고 **내용이 본문**이 된다.
       화살표는 빼고, 줄 전체를 눌러 상세로 간다(이동은 그대로 유지).
       ⚠ 값은 이미 esc() 를 거쳤거나 우리가 만든 마크업이다 — 여기서 다시 escape 하지 않는다. */
    /* ⚠ 이름을 **값 위 별도 줄**로 두면 줄 수가 두 배가 된다 —
       360×800 에서 162px 넘쳤다(2026-08-03 실측). 값 앞에 작은 라벨로 붙여 한 줄에 넣는다. */
    const body = (cls, icon, name, html, go) => `
      <button class="hv3-line big ${cls}" onclick="${go}">
        <span class="ic ${cls}"><i aria-hidden="true" class="ti ${icon}"></i></span>
        <span class="bd"><span class="vl"><em class="nm">${name}</em>${html}</span></span>
      </button>`;
    /* 없는 날 — 줄을 지우지 않고 **회색 한 줄로 줄인다.**
       아예 없애면 「어제는 있었는데 오늘은 왜 없지」를 앱 탓으로 읽는다. */
    const none = (cls, icon, text) => `
      <div class="hv3-line empty">
        <span class="ic ${cls}"><i aria-hidden="true" class="ti ${icon}"></i></span>
        <span class="bd"><span class="vl">${text}</span></span>
      </div>`;
    const more = (arr, n) => arr.length > n ? ` <em class="hv3-more">외 ${arr.length - n}</em>` : "";

    return `
    <div class="hd-top">
      ${S.kidMode
        ? `<button class="hv3-ham" onclick="App.kidModeOff()" aria-label="부모 모드로 나가기">
             <i aria-hidden="true" class="ti ti-lock"></i></button>`
        : `<button class="hv3-ham" onclick="App.drawerOpen()" aria-label="메뉴${unread ? ` · 안 읽음 ${unread}개` : ""}"><i aria-hidden="true" class="ti ti-menu-2"></i>${unread ? `<span class="hd-badge">${unread}</span>` : ""}</button>`}
      <!-- 아이가 없으면(구경 중) 자녀칩 자리에 **앱 이름**만 둔다(2026-08-04 지시).
           ⚠ 여기에 「가입하기」 버튼을 뒀다가 걷어냈다. 들어오자마자 가입을 들이밀면
             «구경하러 왔는데 문 앞에서 붙잡는» 꼴이다. 가입 길은 서랍(☰)에 있으면 족하다.
           ⚠ 빈 알약은 그리지 않는다 — «내 아이가 사라졌나»로 읽힌다. -->
      <!-- ⚠ 자녀 «프로필 칩»을 걷어냈다(대표님 지시 08-08).
           아이를 바꾸는 길은 **서랍 안**에 그대로 있다(hv3-drwho) — 입구가 둘일 이유가 없고,
           맨 위 줄이 비면 그림이 더 크게 보인다. -->
      <span class="hd-gap"></span>
      <!-- 서랍·알림 아이콘을 걷어냈다(대표님 지시 2026-08-09).
           **메뉴 안에 「서랍」과 「대화」가 이미 있다** — 입구가 둘일 이유가 없고,
           맨 위 줄이 비면 그림이 더 크게 보인다(자녀 칩을 걷어낸 것과 같은 이유).
           안 읽은 개수는 **메뉴 버튼 위 숫자**로 옮겼다 — 새 알림이 온 걸 홈에서 모르면
           그건 기능이 준 것이다. -->
    </div>

    <!-- 일러스트 헤더 + 전광판.
         ⚠ 예전 규칙(§6)은 「그림만 · 정보 텍스트를 얹지 않는다」였다. **08-09 대표님 지시로 바꿨다** —
           「시계를 일러까지 올려서 투명 유지하면서」. 유리판은 뒤가 비쳐야 유리라서,
           맨색 위에 얹으면 흐림이 티가 안 난다. 그림 위에 얹어야 참조(타운보드)처럼 읽힌다.
         ⚠ 그래서 aria-hidden 을 뗐다 — 안에 **읽어야 할 글자**(날짜·시각)가 들어왔다.
         ⚠ 그림은 테마마다 밝기가 다르다. 글자 대비는 그림이 아니라 **아래 어둠막(::after)**
           이 책임진다 — 막을 지우면 밝은 그림에서 시계가 사라진다. -->
    <div class="hv3-art">${boardView()}</div>

    ${promoteCard(c)}
    <!-- 아이가 없으면(구경 중) **다음에 뭘 할지**를 홈에서 말해 준다(2026-08-09 실기).
         ⚠ 예전에 여기 「가입하기」를 뒀다가 걷어낸 적이 있다 — 들어오자마자 가입을
           들이미는 게 싫어서였다. 그건 지금도 맞다. 그래서 **가입이 아니라 «이유»**를 말한다.
         ⚠ 빈 카드 넉 장만 있는 홈은 «고장난 앱»처럼 보인다.
           ☰ 안에 「아이 등록하기」가 있지만, 메뉴를 열어야 보이는 것은 «없는 것»에 가깝다. -->
    ${cur() ? "" : `<button class="hm-start" onclick="location.hash='#child-add'">
      <b>아이를 등록하면 시작돼요</b>
      <em>급식 · 시간표 · 학사일정이 매일 저절로 들어와요<i aria-hidden="true" class="ti ti-chevron-right"></i></em>
    </button>`}
    <!-- ⚠ 여기에 «지금은 구경만 하고 계세요» 가입 유도 카드를 얹었다가 걷어냈다(2026-08-04 지시).
         비회원에게 보여주려는 건 **회원이 보는 그 화면 그대로**다. 그 위에 안내 카드를 덧대면
         «진짜 화면»이 아니라 광고가 낀 화면이 된다. 가입 길은 위 자녀칩 자리 하나로 족하다. -->
    ${(() => {
      const d = passDaysLeft(c);
      if (!passOpen(c) || d < 0 || d > 3) return "";
      return `<button class="hd-trial" onclick="location.hash='#pay'">
        체험 ${d === 0 ? "오늘까지" : `${d}일 남음`}<em>이용권 보기<i aria-hidden="true" class="ti ti-chevron-right"></i></em></button>`;
    })()}
    <!-- D-day 행사 — 가장 가까운 «큰» 학교 행사 하나만. 없으면 슬롯 자체가 없다 -->
    ${!nextBig ? "" : `<button class="hd-trial" onclick="App.dayOpen('${nextBig.date}')">
      ${esc(nextBig.name)}<em>${esc(ddayLabel(nextBig.date) || "")}<i aria-hidden="true" class="ti ti-chevron-right"></i></em></button>`}

    <!-- ① 전광판 — **표시 전용.** 탭도 링크도 없다(§1).
         시각은 분마다 갱신되고, 아이 상태는 시간표·학원을 보고 저절로 바뀐다.
         ⚠ 시간표가 없거나 방학이면 **아무 말도 안 한다** — 시각만 남긴다(지어내기 금지). -->

    <!-- ② 일정 카드 — 오늘 일정을 **내용 그대로**. 탭하면 일간 화면 -->
    ${(() => {
      const acts = STUB.activities.filter((a) => String(a.days_of_week || "").split(",").includes(String(dow)));
      const mine = (STUB.myEvents || []).filter((e) => e.date === TODAY);
      const sch  = schedulesOf().filter((e) => e.date === TODAY && !e.name.includes("토요휴업일")
        && !(S.holiOff && (e.closure_type || "").includes("공휴일")));
      const all = [
        ...sch.map((e) => ({ at: "", t: e.name, k: "sc" })),
        ...mine.map((e) => ({ at: e.start || "", t: e.title, k: "me" })),
      ].sort((x, y) => String(x.at || "99:99").localeCompare(String(y.at || "99:99")));
      const SHOW = 3;
      /* 세 카드를 **같은 한 줄 문법**으로 맞춘다(2026-08-04 지시) —
         [아이콘] 제목 …… 값 [>]. 내용이 있으면 그 아래로 펼친다.
         ⚠ 하나만 아이콘이 있으면 그 줄만 특별해 보인다 → 셋 다 준다. */
      return `<button class="hv3-card k-day" onclick="App.dayOpen('${TODAY}')">
        <div class="hv3-hdrow">
          <span class="ic"><i aria-hidden="true" class="ti ti-calendar"></i></span>
          <b>오늘 일정</b>
          ${all.length ? `<em class="val">${all.length}개</em>` : `<em class="val">일정이 없어요</em>`}
          <i aria-hidden="true" class="ti ti-chevron-right go"></i>
        </div>
        ${!all.length ? "" : `<ul class="hv3-evs">${all.slice(0, SHOW).map((x) => `
            <li class="${x.k}"><span class="at">${x.at ? esc(fmtT(x.at)) : "종일"}</span><span class="tx">${esc(x.t)}</span></li>`).join("")}
          </ul>${all.length > SHOW ? `<p class="hv3-morep">외 ${all.length - SHOW}개</p>` : ""}`}
      </button>`;
    })()}

    <!-- ③ 준비물 — **버튼 하나.** 내용은 나열하지 않는다. 숫자는 «내일» 미체크 개수(§1) -->
    ${(() => {
      const n = packs.length;
      return `<button class="hv3-card k-supply ${n ? "on" : ""}" onclick="location.hash='#supplies'">
        <div class="hv3-hdrow">
          <span class="ic"><i aria-hidden="true" class="ti ti-backpack"></i></span>
          <b>내일 준비물</b>
          ${n ? `<span class="cnt">${n}</span>` : `<em class="val">완료</em>`}
          <i aria-hidden="true" class="ti ti-chevron-right go"></i>
        </div></button>`;
    })()}

    <!-- ④ 방과후 -->
    ${(() => {
      const acts = STUB.activities.filter((a) => String(a.days_of_week || "").split(",").includes(String(dow)))
        .sort((x, y) => String(x.start_time).localeCompare(String(y.start_time)));
      return `<button class="hv3-card k-after" onclick="location.hash='#afterschool'">
        <div class="hv3-hdrow">
          <span class="ic"><i aria-hidden="true" class="ti ti-run"></i></span>
          <b>방과후 · 학원</b>
          <em class="val">${acts.length ? `${acts.length}개` : "없어요"}</em>
          <i aria-hidden="true" class="ti ti-chevron-right go"></i>
        </div>
        ${!acts.length ? "" : `<ul class="hv3-evs">${acts.map((a) => `
            <li class="act"><span class="at">${esc(fmtT((a.start_time || "").slice(0, 5)))}</span>
              <span class="tx">${esc(a.name)}</span>
              <span class="til">${esc(fmtT((a.end_time || "").slice(0, 5)))}</span></li>`).join("")}</ul>`}
      </button>`;
    })()}


    <!-- ⑤ 확인해 주세요 — 2단계 보상의 «2차»가 기다리는 자리 (2026-08-07 §3.2).
         ⚠ 앱에서 **빨강을 쓰는 유일한 자리**다. 여기가 흔해지면 빨강이 아무 뜻도 없어진다.
         ⚠ 아이 화면에는 안 그린다 — 보너스를 주는 건 부모다. -->
    ${(() => {
      const kid = isChildToken() || S.childView || S.kidMode;
      const n = kid ? 0 : (S.verifyPending || []).length;
      if (!n) return "";
      return `<button class="hv3-card k-mission need" onclick="location.hash='#game'">
        <div class="hv3-hdrow">
          <span class="ic"><i aria-hidden="true" class="ti ti-eye"></i></span>
          <b>확인해 주세요</b><span class="cnt">${n}</span>
          <i aria-hidden="true" class="ti ti-chevron-right go"></i>
        </div>
        </button>`;
    })()}

    <!-- ⑥ 오늘 미션 — 홈 아래가 통째로 비어 있었다(2026-08-07 §6.4 «MVP 핵심 기능 완전 누락»).
         ⚠ 🎲 리롤은 **넣지 않았다.** 서버에 그 길이 아직 없다 —
           눌러도 아무 일이 없는 버튼을 두면 그게 고장으로 읽힌다(§4 «안 되는 스위치 금지»). -->
    ${(() => {
      const list = S.missions;
      /* ⚠ 아직 안 받아온 상태(null)라고 카드를 **지우면 안 된다.**
         비회원(구경)은 `loadMissions` 가 아예 안 돌아 null 로 영영 남는다 →
         2026-08-07 에뮬 실기에서 **비회원 홈 아래가 그대로 비어 있었다**(§6.4 가 지적한 그 모습).
         «회원이 보는 진짜 홈 그대로»가 원칙이므로 빈 상태 카드를 그대로 보여 준다. */
      const done = (list || []).filter((x) => x.status === "done").length;
      if (!list || !list.length) {
        return `<button class="hv3-card k-mission" onclick="location.hash='#game'">
          <div class="hv3-hdrow">
            <span class="ic"><i aria-hidden="true" class="ti ti-target"></i></span>
            <b>오늘 미션</b><em class="val">아직 없어요</em>
            <i aria-hidden="true" class="ti ti-chevron-right go"></i>
          </div></button>`;
          /* ⚠ 설명 한 줄을 덧붙이지 않는다(2026-08-07 지시). 다른 카드는 «제목 + 값 + ›» 한 줄인데
             여기만 «골라 주면 아이가…» 를 달아 두면 그 카드만 튀고, 매번 읽을 말도 아니다. */
      }
      return `<button class="hv3-card k-mission" onclick="location.hash='#game'">
        <div class="hv3-hdrow">
          <span class="ic"><i aria-hidden="true" class="ti ti-target"></i></span>
          <b>오늘 미션</b><em class="val">${done}/${list.length}</em>
          <i aria-hidden="true" class="ti ti-chevron-right go"></i>
        </div>
        <ul class="hv3-msn">${list.slice(0, 3).map((x) => `
          <!-- ⚠ 아이콘은 **서브셋에 있는 것만** 쓴다. 없는 이름을 쓰면 그 자리가 «빈칸»으로 뜬다
               (2026-08-03 에 5개가 그랬고, 2026-08-07 에 내가 6개를 또 그렇게 넣었다).
               fonts/tabler-subset.css 에 그 이름이 있는지 보고 쓸 것. ti-circle 은 없다 → ti-square.
               ⚠ 이 주석에 역따옴표를 쓰지 말 것 — 템플릿 문자열 안이라 그 자리에서 문법이 깨진다. -->
          <li class="${x.status}"><i aria-hidden="true" class="ti ${x.status === "done" ? "ti-circle-check" : "ti-square"}"></i>
            <span class="tx">${esc(x.title)}</span><span class="st">★${x.stars}</span></li>`).join("")}
        </ul></button>`;
    })()}

    <!-- 스타코인 상점 카드는 홈에서 뺐다(2026-08-07 지시) — 부모의 매일 화면에 매일 볼 것이 아니다.
         입구는 드로어 «보상» 그룹. 미션·확인해주세요 카드는 부모 일이라 남긴다. -->

    <!-- 하단 3버튼 (§1) — 좌 달력 · 가운데 큰 ＋ · 우 미션 -->
    <!-- 달력에만 라벨이 없어 셋이 삐뚤어 보였다(2026-08-04 지적) — 같은 자리에 같은 라벨을 준다 -->
    <button class="hv3-cal" onclick="location.hash='#calendar'" aria-label="달력">
      <i aria-hidden="true" class="ti ti-calendar"></i></button>
    <button class="hv3-fab" onclick="App.editOpen('plan')" aria-label="새로 넣기">
      <i aria-hidden="true" class="ti ti-plus"></i></button>
    ${(() => {
      const wait = (S.missions || []).filter((x) => x.status === "waiting").length;
      const done = (S.missions || []).filter((x) => x.status === "done").length;
      /* ★ = **미션 게임**으로 들어간다(2026-08-08 대표님 지시).
           ⚠ «아이 전용 화면»이 아니다 — 부모도 아이도 이 안으로 들어오고, 안에서 역할만 갈린다
             (부모는 내주고·승인하고, 아이는 해내고 받는다).
           ⚠ 한 번 #mission 으로 되돌렸다가 다시 고쳤다. 지시는 «노란 별 = 게임 미션»이다. */
      return `<button class="hv3-star" onclick="location.hash='#game'" aria-label="미션 게임">
        <span class="st">★</span>${wait ? `<em class="bdg">${wait}</em>` : ""}</button>`;
    })()}

    ${drawerView(c)}
    ${coachView()}
    ${reactSheetView()}
    ${stickerView()}
    ${pinPadView()}

    ${chatDock()}
    <!-- 자녀폰 미연결 안내 — 물음표를 눌렀을 때만(2026-08-03 폰 실기) -->
    ${!S.linkWarn ? "" : `
    <div class="modal sheetwrap" onclick="App.linkWarnClose()">
      <div class="sheet" onclick="event.stopPropagation()">
        <div class="sheet-grip"></div>
        <div class="sheet-hd"><b>자녀폰이 아직 연결되지 않았어요</b></div>
        <p class="lw-p">사진 미션은 <b>아이 폰에서 찍어 보내야</b> 도장이 나가요.</p>
        <p class="lw-p">내 정보 → 자녀폰에서 <b>6자리 코드</b>를 받아 넣으면 돼요.</p>
        <div class="sheet-act nodel">
          <button class="act-cancel" onclick="App.linkWarnClose()">닫기</button>
          <button class="act-del" style="background:var(--accent);color:#fff"
            onclick="App.linkWarnClose();location.hash='#mypage'">연결하러 가기</button>
        </div>
      </div>
    </div>`}`;
  },

  // ── 3-1. 홈 편집 — 원형 메뉴 켜기/끄기 + 끌어서 순서 · 캐러셀 내용(2026-07-25) ──
  // 한 화면 = 한 가지. 여기서 바꾸면 홈에 바로 반영된다(저장 버튼 없음 — 되돌리기만 둔다).
  homeedit: () => {
    /* ── 오늘 카드 고르기 (2026-08-03 §2 «카드 편집») ────────────
       원형 메뉴 순서/켜기 블록을 여기서 뺐다 — 격자 메뉴는 홈 v3에서 사라졌고,
       그 스위치는 켜져도 **아무 일도 안 일어나는 상태**였다(2026-07-28에 캐러셀에서 겪은 그 함정).
       안 되는 스위치를 남겨 두면 사용자는 앱이 고장 났다고 읽는다.
       ⚠ S.menuOrder / S.menuHidden 값은 지우지 않았다 — 격자를 되살릴 때 그대로 쓴다. */
    /* ⚠ 설명문은 **이름만으로 모르는 것에만** 붙인다(2026-08-03 지시).
       「급식」·「시간표」·「내일 준비물」은 이름이 곧 설명이다 — 회색 글씨를 더하면 소음이다. */
    const CARDS = [
      ["now",     "ti-clock",             "지금",         "«3교시 수업 중»처럼 시간 따라 바뀌어요"],
      ["meal",    "ti-tools-kitchen-2",   "급식",         ""],
      ["tt",      "ti-table",             "시간표",       ""],
      ["plan",    "ti-pin",               "오늘 일정",    ""],
      ["sup",     "ti-backpack",          "내일 준비물",  ""],
      ["mission", "ti-star",              "미션 도장",    ""],
      ["photo",   "ti-camera",            "확인해 주세요", "아이가 보낸 사진 — 끄면 알림만 남아요"],
    ];
    const on = CARDS.filter(([k]) => S.todayCards[k]).length;
    return `
    <a class="back" href="#home" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 style="margin-top:8px">오늘 카드</h1>
    <p class="sub">끈 것은 없어지지 않아요 — 각자의 화면에 그대로 있어요</p>

    <div class="card" style="padding:8px 10px">
      <div class="edhd"><b>오늘 화면에 보일 줄</b><span class="sub" style="margin:0">${on}/${CARDS.length}개</span></div>
      <div class="edlist">
        ${CARDS.map(([k, ic, nm, sub]) => {
          const off = !S.todayCards[k];
          return `
          <div class="edrow ${off ? "off" : ""}">
            <span class="edico"><i class="ti ${ic}"></i></span>
            <span class="edname">${nm}${sub ? `<em style="display:block;font-style:normal;font-size:12px;color:var(--muted);font-weight:600">${sub}</em>` : ""}</span>
            <button class="swt ${off ? "" : "on"}" onclick="App.todayToggle('${k}')" aria-label="${nm} ${off ? "켜기" : "끄기"}"><i></i></button>
          </div>`;
        }).join("")}
      </div>
    </div>

    <!-- 바탕화면 위젯 (2026-07-27) — 「보고 싶은 내용을 넣게」·「전체 정보를 한눈에」 지시.
         홈 메뉴 편집과 같은 부품(.edrow·.swt·화살표)을 쓴다 — 두 곳에서 조작법이 다르면 헷갈린다. -->
    <div class="card" style="padding:8px 10px">
      <div class="edhd"><b>바탕화면 위젯</b><span class="sub" style="margin:0">${S.widgetRows.length}줄 보임</span></div>
      <p class="sub" style="padding:0 4px 6px">앱을 안 열고 바탕화면에서 봐요. 위젯을 길게 눌러 크게 늘리면 고른 것이 다 보입니다.</p>
      <div class="edlist">
        ${(() => {
          // 켠 것을 순서대로 먼저, 끈 것을 아래에 — 「지금 위젯에 뭐가 있나」가 위에서 바로 읽힌다
          const on = S.widgetRows.map(widgetItemOf).filter(Boolean);
          const off = WIDGET_ITEMS.filter((x) => !S.widgetRows.includes(x.key));
          return [...on, ...off].map((it) => {
            const i = S.widgetRows.indexOf(it.key);
            const isOn = i >= 0;
            return `
            <div class="edrow ${isOn ? "" : "off"}">
              <span class="edico" style="background:var(--c${it.ci});color:var(--f${it.ci})"><i class="ti ${it.ic}"></i></span>
              <span class="edname">${esc(it.label)}</span>
              ${isOn ? `
                <button class="iconbtn ghosticon" ${i === 0 ? "disabled" : ""} onclick="App.widgetMove('${it.key}',-1)" aria-label="위로"><i class='ti ti-chevron-up'></i></button>
                <button class="iconbtn ghosticon" ${i === on.length - 1 ? "disabled" : ""} onclick="App.widgetMove('${it.key}',1)" aria-label="아래로"><i class='ti ti-chevron-down'></i></button>` : ""}
              <button class="swt ${isOn ? "on" : ""}" onclick="App.widgetToggle('${it.key}')" aria-label="${esc(it.label)} ${isOn ? "끄기" : "켜기"}"><i></i></button>
            </div>`;
          }).join("");
        })()}
      </div>
    </div>

<div class="card" style="padding:8px 10px">
      <div class="edhd"><b>일정에 공휴일</b></div>
      <div class="edlist">
        <div class="edrow">
          <span class="edname">광복절·설날 같은 공휴일 보이기</span>
          <button class="swt ${S.holiOff ? "" : "on"}" onclick="App.holiToggle()" aria-label="공휴일 일정 ${S.holiOff ? "켜기" : "끄기"}"><i></i></button>
        </div>
      </div>
      <p class="sub" style="padding:0 4px 6px;margin:0">꺼도 학교탭 달력에는 그대로 있어요</p>
    </div>

    <!-- ⛔ 「맨 위 알림 카드」 3종 + 「자동으로 넘기기」 를 여기서 뺐다(2026-07-28).
         새 홈(시안 5a)에는 넘기는 캐러셀이 없다 — homeCarousel() 을 부르는 곳이 0이었다.
         스위치는 켜지고 저장까지 됐지만 **아무 일도 안 일어났다.** 안 되는 스위치를 두면
         사용자는 앱이 고장 났다고 읽는다. 캐러셀을 되살릴 때 이 자리에 다시 넣는다. -->

    <div class="row" style="margin-top:16px">
      <button class="btn-line" onclick="App.todayReset()">모두 켜기</button>
      <button class="btn-primary" onclick="location.hash='#home'">완료</button>
    </div>
`;
  },

  // ── 4. 학교탭 — 정보·급식·일정·시간표 서브탭. GET /api/v1/schools/{slug}/* ──
  /* 일정 탭(2026-08-02 메뉴 개편) — 달력이 하단 탭으로 승격됐다.
     화면은 학교 화면의 일정 탭 그대로다. 새로 그리지 않고 탭만 맞춰서 넘긴다 —
     같은 달력이 두 벌 생기면 한쪽만 고치는 사고가 난다. */
  /* 달력 (§2) — 학교 화면을 경유하지 않는다.
     예전엔 school() 을 탔더니 머리에 «서울초등학교 · 불러오는 중…» 같은 학교 부제가 따라붙었다.
     달력은 학교 것이 아니라 **우리 집 것**이다(학교 행사 + 내 일정 + 아이 흔적). */
  calendar: () => {
    S.schoolTab = "schedule";
    const ym = S.calMonth || TODAY.slice(0, 6);
    return subHeader("달력", `${+ym.slice(0, 4)}년 ${+ym.slice(4, 6)}월`) + diaryTab();
  },

  school: () => {
    const sc = schoolInfo();
    /* ⚠ 「schedule」은 **이제 학교 화면의 탭이 아니다** — 달력은 #calendar 로 떨어져 나갔다.
       그런데 calendar() 가 S.schoolTab = "schedule" 을 전역에 써 놓고 나가서,
       달력을 본 뒤 #school 에 닿으면 학교정보 자리에 달력이 그려졌다(08-09 실측:
       두 화면 스샷이 픽셀까지 같았다). 메뉴로 들어오면 go() 가 info 를 넣어 괜찮고
       뒤로가기·옛 주소·딥링크로 올 때만 터진다.
       → 없는 탭으로 들어온 것이니 «학교정보»로 되돌린다. 위의 커뮤니티 처리와 같은 방식이다. */
    if (S.schoolTab === "schedule") S.schoolTab = "info";
    // 중·고에서 커뮤니티 탭으로 들어오면(홈 메뉴·옛 주소) 학교정보로 되돌린다 — 없는 탭에 갇히지 않게
    if (S.schoolTab === "community" && !String(sc.kind || "").startsWith("초")) S.schoolTab = "info";
    const t = S.schoolTab;
    // 지금 보고 있는 게 서버 값인지 스텁인지 숨기지 않는다 — 방학이라 비는 것과 못 붙은 것은 다른 문제다
    const src = SCHOOL.busy ? `<span class="stub">불러오는 중…</span>`
      : SCHOOL.from === "stub" ? `<span class="stub">예시 데이터예요</span>` : "";
    /* ⚠ 예전엔 이 객체의 **다섯 탭을 전부 그려 놓고 하나만 골라 썼다.**
       급식을 보는데 커뮤니티까지 그려지니, 커뮤니티가 `cur().grade` 를 읽다가
       **자녀가 없는 비회원에서 통째로 죽었다**(2026-08-03 실측).
       이제 «고른 탭만» 그린다 — 함수로 담아 두고 마지막에 한 번만 부른다. */
    const body = ({
      info: () => `
        <!-- 규모(전교생·학급·교원)는 학부모가 제일 먼저 보는 값이라 회색 한 줄이 아니라 숫자로 크게 세운다.
             학년별은 접어둔다(웹 §지시서9와 같은 규칙). 출처는 학교알리미 공시. -->
        <!-- 학교 이름은 화면 제목(h1)에 이미 있다 → 카드에선 뺀다(2026-07-24 검수: 바로 위아래로 두 번 나옴) -->
        <!-- 전화번호는 **누르면 걸려야** 한다(2026-08-01) — 여태 회색 글자라 학부모가 번호를 외워
             전화앱에 다시 쳤다. 주소가 없는 홈페이지 버튼도 뺀다: 눌러서 아무 일도 안 나는 버튼은
             자매 사이트 때와 같은 문제다(고장으로 읽힌다). -->
        <div class="card">
          <!-- ⚠ 빈 값을 그냥 이으면 «· 초등학교»처럼 앞이 비어 보인다(2026-08-03 지시).
               있는 것만 모아서 잇는다 — 하나도 없으면 줄 자체를 안 그린다. -->
          ${(() => {
            const head = [sc.sido, sc.kind].filter(Boolean).map(esc).join(" · ");
            const addr = esc(sc.address || "");
            return (head || addr) ? `<p class="sub" style="margin-top:0">${head}${head && addr ? "<br>" : ""}${addr}</p>` : "";
          })()}
          ${sc.phone || sc.homepage ? `<div class="row" style="margin-top:10px">
            ${sc.phone ? `<a class="btn btn-line" href="tel:${esc(String(sc.phone).replace(/[^0-9+]/g, ""))}"><i class='ti ti-phone'></i> ${esc(sc.phone)}</a>` : ""}
            ${sc.homepage ? `<button class="btn-line" onclick="openExternal('${jsq(sc.homepage)}','학교 홈페이지')"><i class='ti ti-link'></i> 홈페이지</button>` : ""}
          </div>` : ""}
        </div>

        <!-- 공시에 없는 값은 「-」로 자리만 채우지 않는다. 빈 칸 하나가 «우리 학교는 교원이 없나»로 읽힌다. -->
        ${(() => {
          const st = [
            [sc.detail?.student_count, "전교생"],
            [sc.detail?.class_count, "학급"],
            [sc.detail?.teacher_count, "교원"],
          ].filter(([v]) => v != null);
          return st.length ? `<div class="stats">${st.map(([v, k]) => `<div><b>${v}</b><span>${k}</span></div>`).join("")}</div>` : "";
        })()}

        <!-- 학년별 현황은 **자료가 있을 때만** 접이 카드를 그린다.
             펼쳤는데 아무것도 없으면 «앱이 고장났다»가 된다(2026-08-01: 실제로 빈 채로 열렸다). -->
        ${(sc.detail?.grade_breakdown || []).length ? `
        <div class="card foldbox">
          <button class="foldhd" onclick="App.toggleGrades()">
            <span><b style="font-size:13px">학년별 현황</b>
              <span class="foldsum">${sc.detail.grade_breakdown.length}개 학년 · 학급수와 인원</span></span>
            <span class="caret">${S.gradesOpen ? `<i aria-hidden="true" class="ti ti-chevron-up"></i>` : `<i aria-hidden="true" class="ti ti-chevron-down"></i>`}</span>
          </button>
          ${S.gradesOpen ? `
            <div class="gradelist">
              ${sc.detail.grade_breakdown.map((g) => `
                <div class="graderow">
                  <b>${g.grade}학년</b>
                  <span class="gcls">${g.classes}학급</span>
                  <span class="gnum">${g.students}명 <span class="gsex">남 ${g.male} · 여 ${g.female}</span></span>
                </div>`).join("")}
            </div>
            <p class="notice" style="padding:0 16px 14px">반별 인원은 공시되지 않아 학년 단위로만 제공돼요 ·
              학교알리미 ${esc(String(sc.detail?.disclosure_round ?? ""))} 공시 기준</p>` : ""}
        </div>` : ""}`,
      meal: () => mealTab(),
      schedule: () => diaryTab(),
      timetable: () => timetableTab(),
      community: () => communityTab(),
    }[t] || (() => ""))();
    /* 커뮤니티는 **초등만** 연다(2026-08-01). 중·고는 성적·입시·교사 얘기가 붙어 분쟁이 커지고,
       그쪽은 이미 맘카페가 잡고 있어 우리가 이길 수 없다. 빈 탭을 보여주느니 탭 자체를 숨긴다. */
    /* ⚠ 서브탭 줄(.subtabs)을 뺐다(2026-08-03 «탈출 불가» 수정).
       드로어에서 「시간표」를 눌렀는데 학교 탭 다섯 개가 통째로 딸려오면
       «내가 뭘 눌렀지»가 되고, 나가는 길도 탭마다 달라진다.
       이제 화면 하나 = 할 일 하나이고, 나가는 길은 ← 하나다.
       이 school 화면 자체는 **옛 주소 호환용**으로만 남는다 — 아래 라우터가 단독 화면으로 넘긴다. */
    const TITLE = { info: "학교정보", meal: "급식", schedule: "일정", timetable: "시간표", community: "커뮤니티" };
    return `
    <!-- ⚠ 부제에 로딩 배지(src)를 붙이면 «급식 / 서울초등학교 불러오는 중…»이 된다.
         부제는 «어느 학교인가»만 말한다. 불러오는 중 표시는 본문이 진다. -->
    ${subHeader(esc(TITLE[t] || "학교"), esc(schoolName(cur())))}
    ${body}`;
  },

  /* ── 드로어·오늘 카드에서 들어가는 단독 화면들 (2026-08-03) ──
     예전엔 전부 `#school` 한 곳으로 보내고 탭으로 갈랐다. 그래서 어디로 들어가든
     화면이 «학교 탭»이었고, 탭 줄이 남아 나가는 길이 흐려졌다.
     ⚠ 그림은 school() 이 그대로 그린다 — **같은 화면을 두 벌 만들지 않는다.**
       두 벌이 되면 한쪽만 고치는 사고가 난다(달력에서 이미 겪었다). */
  /* ⚠ 시간표는 하교 뒤면 **접힌 채로** 뜬다(2026-07-28 지시: 3시엔 5교시가 아니라 학원이 궁금하다).
     그건 학교 화면 안에서 훑을 때 맞는 말이고, **드로어에서 「시간표」를 눌러 들어왔을 땐 틀리다** —
     누른 것이 안 보이면 그게 고장이다. 이 길로 들어오면 편 채로 시작한다. */
  /* ── 내보내기 · 가져오기 (2026-08-03 §4) ────────────────────────
     ⚠ 이름은 «내보내기 · 가져오기»다. «수출·수입»은 export/import 를 기계번역한 말이라
       한국어 앱에서는 뜻이 통하지 않는다(§4 명시).
     ⚠ 유료 항목에는 왕관을 단다 — 눌러 보고 나서야 «돈 내야 한다»를 알면 그게 함정이다. */
  backup: () => {
    const b = S.backup || {};
    const RANGE = [["1m", "최근 1개월"], ["6m", "최근 6개월"], ["1y", "최근 1년"], ["all", "전체"]];
    return `
    ${subHeader("내보내기 · 가져오기", "기록을 파일로")}

    <div class="ed-chips" style="margin-top:6px">
      ${RANGE.map(([v, n]) => `<button class="${(b.range || "1y") === v ? "on" : ""}" onclick="App.backupSet('range','${v}')">${n}</button>`).join("")}
    </div>

    <div class="bk-list" style="margin-top:14px">
      <button class="bk-row ${(b.fmt || "txt") === "txt" ? "on" : ""}" onclick="App.backupSet('fmt','txt')">
        <i aria-hidden="true" class="ti ti-file-text"></i>
        <span class="bd"><b>글자 파일 (TXT)</b><em>사진 없음</em></span>
      </button>
      <button class="bk-row ${b.fmt === "pdf" ? "on" : ""}" onclick="App.backupSet('fmt','pdf')">
        <i aria-hidden="true" class="ti ti-printer"></i>
        <span class="bd"><b>PDF <em class="bk-pro"><i aria-hidden="true" class="ti ti-award"></i>유료</em></b>
          <em>사진까지 포함, 인쇄용</em></span>
      </button>
    </div>

    <button class="btn-primary" style="margin-top:18px" onclick="App.backupRun()">내보내기</button>

    <div class="mp-sec" style="margin-top:26px">가져오기</div>
    <div class="mp-list">
      <button class="mp-row" onclick="App.backupImport()">
        <span class="mp-l">파일에서 되살리기<em>예전에 내보낸 파일을 고르면 그대로 돌아와요</em></span>
        <i aria-hidden="true" class="ti ti-chevron-right"></i></button>
    </div>`;
  },

  /* ── 이름 고치기 — 전용 화면 (2026-08-03 §4) ─────────────────── */
  editname: () => `
    ${subHeader("이름", "앱 안에서만 써요")}
    <label class="ed-f" for="name-edit">보호자 이름</label>
    <input class="ed-title" id="name-edit" maxlength="20" placeholder="예: 김하늘"
      value="${esc(S.nameDraft ?? "")}" oninput="S.nameDraft=this.value"
      onkeydown="if(event.key==='Enter')App.nameSave()">
    <p class="mp-hint">서식(체험학습 신청서 등)에 «학부모» 칸으로 들어가요</p>
    <div class="ed-act">
      <button class="ed-cancel" onclick="App.nameCancel()">취소</button>
      <button class="ed-save" onclick="App.nameSave()">저장</button>
    </div>`,

  /* ── 방과후·학원 고치기 — 전용 화면 (§4) ────────────────────── */
  editact: () => {
    const d = S.planDraft;
    if (!d) return `${subHeader("방과후")}<p class="sub">불러오는 중…</p>`;
    return `
    ${subHeader(d.id ? "학원 고치기" : "새 학원",
      (d.days || []).length ? d.days.map((n) => DAY_KO[n - 1]).join(" ") : "요일을 골라주세요")}

    <label class="ed-f" for="pb-name">이름</label>
    <input class="ed-title" id="pb-name" placeholder="학원·활동 이름"
      value="${esc(d.name)}" oninput="S.planDraft.name=this.value">

    <label class="ed-f">시간</label>
    <div class="qk-row">
      <input type="time" class="ed-time" style="margin:0" value="${d.start}" oninput="S.planDraft.start=this.value">
      <span>~</span>
      <input type="time" class="ed-time" style="margin:0" value="${d.end}" oninput="S.planDraft.end=this.value">
    </div>

    <!-- 요일은 여러 날 — 「월·수 피아노」가 학원 두 개가 되면 안 된다(2026-07-28 통합) -->
    <label class="ed-f">요일</label>
    <div class="ed-chips">
      ${DAY_KO.map((n, i) => `
        <button class="${(d.days || []).includes(i + 1) ? "on" : ""}" onclick="App.planDay(${i + 1})">${n}</button>`).join("")}
    </div>

    <label class="ed-f">색</label>
    <div class="swatches">
      ${PLAN_COLORS.map((c, i) => `
        <button class="sw ${d.color === i ? "on" : ""}" style="--tag:${c.v}"
                onclick="App.planColor(${i})" aria-label="색 ${i + 1}"></button>`).join("")}
    </div>

    <div class="ed-act">
      <button class="ed-cancel" onclick="App.planCancel()">취소</button>
      <button class="ed-save" onclick="App.planSave()">${d.id ? "저장" : "추가"}</button>
    </div>
    ${d.id ? `<button class="ed-del" onclick="App.planDelete()">지우기</button>` : ""}`;
  },

  /* ── 시간표 한 칸 고치기 — 전용 화면 (§4) ───────────────────── */
  edittt: () => {
    const e = S.ttEdit;
    if (!e) return `${subHeader("시간표")}<p class="sub">불러오는 중…</p>`;
    const SUBJ = ["국어", "수학", "사회", "과학", "영어", "체육", "음악", "미술", "실과",
                  "도덕", "통합", "창체", "동아리", "자율"];
    return `
    ${subHeader("과목 고치기", `${DAY_KO[e.c] || ""}요일 ${e.r + 1}교시`)}
    <label class="ed-f" for="tt-v">과목</label>
    <input class="ed-title" id="tt-v" maxlength="12" placeholder="과목 이름"
      value="${esc(e.v ?? "")}" oninput="S.ttEdit.v=this.value"
      onkeydown="if(event.key==='Enter')App.ttSave()">
    <div class="ed-chips" style="margin-top:10px">
      ${SUBJ.map((n) => `<button class="${e.v === n ? "on" : ""}" onclick="App.ttSet('${jsq(n)}')">${n}</button>`).join("")}
    </div>
    <p class="mp-hint">비워서 저장하면 그 칸이 빈 칸이 돼요</p>
    <div class="ed-act">
      <button class="ed-cancel" onclick="App.ttClose()">취소</button>
      <button class="ed-save" onclick="App.ttSave()">저장</button>
    </div>`;
  },

  /* ── 미션 하나 — 전용 화면 (§4) ──────────────────────────────
     확인·되돌리기·서랍 보관이 전부 여기 있다. 사진을 시트로 보면 절반이 잘렸다. */
  missionone: () => {
    const list = S.missions || [];
    const x = list.find((v) => v.id === S.msDetail);
    if (!x) return `${subHeader("미션")}<p class="sub">불러오는 중…</p>`;
    const ST = { open: "아직", waiting: "확인 기다림", done: "완료", skipped: "못 했어요" };
    return `
    ${subHeader("미션", ST[x.status] || "")}
    <h2 class="msc-dt">${esc(x.title)}</h2>
    <div class="msc-meta">
      <em>${esc(MISSION_AREA[x.area] || "")}</em>${x.minutes ? `<em>${x.minutes}분</em>` : ""}
      <em class="star">★${x.stars}</em>
      <em>${x.verify === "review" ? "사진 확인" : x.verify === "endday" ? "하루 끝 확인" : "눌러서 보고"}</em>
    </div>
    ${x.status === "waiting" ? `
      ${x.verify === "review"
        ? `<img class="msc-photo" src="${PLACEHOLDER}" data-rec="/api/v1/missions/${x.id}/photo" alt="아이가 보낸 사진">`
        : `<p class="msc-said">아이가 <b>다 했어요</b>를 눌렀어요</p>`}
      <button class="btn-primary" onclick="App.missionApprove(${x.id});App.goHome()"><i aria-hidden="true" class="ti ti-check"></i>잘했어! 도장 찍기</button>
      ${x.verify !== "review" ? "" : `
      <button class="msc-keep ${S.keepShot === x.id ? "on" : ""}" onclick="App.keepShot(${x.id})">
        <i aria-hidden="true" class="ti ${S.keepShot === x.id ? "ti-check" : "ti-photo"}"></i>
        ${S.keepShot === x.id ? "도장 찍을 때 서랍에 넣어요" : "서랍에 보관하기"}</button>`}
      <button class="msc-sub" onclick="App.missionRevert(${x.id});location.hash='#mission'">다시 해볼까?</button>
      <p class="mp-hint" style="text-align:center">안 보면 <b>아침 8시</b> 자동</p>`
    : x.status === "open" ? `
      <button class="btn-primary" onclick="location.hash='#mission';App.missionPickOpen()"><i aria-hidden="true" class="ti ti-grip-vertical"></i>다른 미션으로 바꾸기</button>`
    : `
      <button class="btn-primary" onclick="App.missionRevert(${x.id});location.hash='#mission'">${x.status === "skipped" ? "다시 줘볼까?" : "다시 해볼까?"}</button>`}`;
  },

  /* ── 미션 고르기 — 전용 전체 화면 (2026-08-03 지시) ──────────────
     반쪽 시트를 화면으로 올렸다. 고를 것이 수십 개라 시트로는 절반밖에 못 봤다.
     ⚠ 학년대(band)를 **탭으로** 연다. 자녀 학년으로 기본 선택하되 다른 학년대도 볼 수 있다 —
       같은 3학년이라도 «아직 저학년 같은 아이»와 «벌써 고학년 같은 아이»가 있다.
     ⚠ 「추천」은 **아직 안 담은 것 중에서** 고른다. 이미 담은 걸 또 권하면 추천이 아니다.
     ⚠ 넣으면 안 되는 것(mission_banned 20종)은 **서버가 애초에 안 준다**(missions 테이블에 없음). */
  missionpick: () => {
    const c = cur();
    const band = S.pickBand || bandOf(c);
    const list = (S.missionCatalog || {})[band];
    const picked = S.missionPick || [];
    const BANDS = [["low", "저학년"], ["mid", "중학년"], ["high", "고학년"]];

    const head = `
      ${subHeader("미션 고르기", `${picked.length}개 담김`)}
      <div class="mk-bands">
        ${BANDS.map(([v, n]) => `<button class="${band === v ? "on" : ""}" onclick="App.pickBand('${v}')">${n}</button>`).join("")}
      </div>`;

    if (!Array.isArray(list)) return `${head}<p class="sub" style="margin-top:20px">불러오는 중…</p>`;
    if (!list.length) return `${head}<p class="sub" style="margin-top:20px">고를 수 있는 미션이 없어요</p>`;

    const row = (m) => {
      const on = picked.includes(m.code);
      return `
      <button class="mk-row ${on ? "on" : ""}" onclick="App.missionToggle('${jsq(m.code)}')">
        <span class="bd">
          <b>${m.mine ? `<i class="mk-mine">우리 집</i>` : ""}${esc(m.title)}</b>
          <em>★${m.stars}${m.minutes ? ` · ${m.minutes}분` : ""}${m.verify === "review" ? " · 사진 인증" : ""}</em>
        </span>
        ${on ? `<span class="mk-in">담김</span>` : `<span class="mk-add">＋</span>`}
      </button>`;
    };

    // 추천 — 아직 안 담은 것 중 별이 큰 순서로 셋. «오늘 뭘 줄까»를 대신 정해 준다
    const rec = list.filter((m) => !picked.includes(m.code))
      .sort((a, b) => (b.stars || 0) - (a.stars || 0)).slice(0, 3);

    // 영역별 묶음 — MISSION_AREA 순서를 따른다(뒤죽박죽이면 매번 다른 화면이 된다)
    const byArea = Object.keys(MISSION_AREA)
      .map((k) => [k, list.filter((m) => m.area === k)])
      .filter(([, arr]) => arr.length);
    const rest = list.filter((m) => !MISSION_AREA[m.area]);
    if (rest.length) byArea.push(["_etc", rest]);

    return `
    ${head}
    ${!rec.length ? "" : `
    <div class="mk-sec">
      <div class="mk-st"><b>추천</b><em>아직 안 담은 것 중에서</em></div>
      ${rec.map(row).join("")}
    </div>`}
    ${byArea.map(([k, arr]) => `
      <div class="mk-sec">
        <!-- ⚠ 개수를 이름 옆에 맨숫자로 붙이면 «몸 2» 가 한 단어처럼 읽힌다(2026-08-03 지적).
             목록을 보면 몇 개인지 바로 아는데 굳이 적을 이유가 없다. -->
        <div class="mk-st"><b>${k === "_etc" ? "그 밖에" : MISSION_AREA[k]}</b></div>
        ${arr.map(row).join("")}
      </div>`).join("")}

    <button class="mk-make" onclick="App.editOpen('mission')">
      <i aria-hidden="true" class="ti ti-plus"></i>우리 집 미션 만들기</button>

    <div class="mk-bot">
      <button class="mk-go" ${picked.length ? "" : "disabled"} onclick="App.missionSave()">
        ${picked.length ? `${picked.length}개 담기` : "고른 것이 없어요"}</button>
    </div>`;
  },

  /* ── 테마 고르기 — 전용 전체 화면 (2026-08-03 §4·§6) ─────────────
     반쪽 시트를 폐지하고 화면으로 올렸다. 테마는 «화면 전체가 바뀌는 것»인데
     시트로 고르면 화면의 절반이 가려져 **무엇이 바뀌는지 볼 수가 없었다.**
     ⚠ 미리보기는 **실물**이다 — 그 세트의 배경·카드·포인트 색을 그대로 칠한 작은 화면.
       옆 테마가 살짝 보여야 «더 있다»가 읽힌다(캐러셀).
     ⚠ 고르는 즉시 적용하지 않는다. 아래 «사용» 을 눌러야 확정이다 —
       훑어보다 실수로 바뀌면 되돌리는 길을 또 찾아야 한다. */
  theme: () => {
    const pickArt = S.themePick?.art || S.art;
    const pickTheme = S.themePick?.theme || (DARK_THEMES.includes(S.theme) ? "dark" : "light");
    const changed = pickArt !== S.art || pickTheme !== (DARK_THEMES.includes(S.theme) ? "dark" : "light");
    return `
    ${subHeader("테마", "배경과 밝기")}

    <div class="th-mode">
      ${[["light", "밝게"], ["dark", "어둡게"]].map(([v, n]) => `
        <button class="${pickTheme === v ? "on" : ""}" onclick="App.themePick('theme','${v}')">${n}</button>`).join("")}
    </div>

    <!-- 실물 미리보기 캐러셀 — 옆 것이 살짝 보이게 (§6) -->
    <div class="th-car" id="thcar">
      ${ART_SETS.map((a) => `
        <button class="th-item ${pickArt === a.key ? "on" : ""}" onclick="App.themePick('art','${jsq(a.key)}')">
          <span class="ph" data-art="${esc(a.key)}" data-theme="${esc(pickTheme)}">
            <span class="ph-bar"></span>
            <span class="ph-card"><i></i><i class="s"></i></span>
            <span class="ph-card"><i></i></span>
            <span class="ph-fab"></span>
          </span>
          <b>${esc(a.label)}</b>
        </button>`).join("")}
    </div>

    <div class="th-act">
      <button class="th-use" ${changed ? "" : "disabled"} onclick="App.themeApply()">
        ${changed ? "이 테마 사용" : "지금 쓰는 테마예요"}</button>
      ${!S.themeFirst ? "" : `<button class="cm-skip" style="width:100%;margin-top:4px" onclick="App.themeLater()">나중에</button>`}
    </div>`;
  },

  /* ── 전체 화면 편집기 (2026-08-03 지시서 0803-2 §3) ─────────────
     «제대로 입력». 팝업도 반쪽 시트도 아니다 — 화면 하나를 통째로 쓴다.
     ⚠ **시스템 날짜 피커를 쓰지 않는다**(§3). 폰마다 생김새가 달라 우리 화면이 아니게 되고,
       한 번에 한 달밖에 못 본다. 화면 안에 미니 달력을 편다.
     ⚠ 시간은 **칩**이다. 「아침·하교 후·저녁」이 부모가 실제로 쓰는 단위고,
       분 단위가 필요한 날만 직접 입력을 연다. 아무것도 안 고르면 «종일»이다.
     ⚠ [넣기][취소]를 화면에 **항상 적어 둔다** — 뒤로가기로만 빠져나가게 두지 않는다. */
  edit: () => {
    const e = S.edit;
    if (!e) return `${subHeader("입력")}<p class="sub">불러오는 중…</p>`;
    const KIND = { plan: "일정", sup: "준비물", mission: "미션" };
    const isSup = e.kind === "sup";

    // 미니 달력 — 그 달만. 시스템 피커 대신 이걸 편다
    const ym = e.month || e.date.slice(0, 6);
    const yy = +ym.slice(0, 4), mm = +ym.slice(4, 6);
    const first = weekOffset(new Date(yy, mm - 1, 1).getDay());
    const last = new Date(yy, mm, 0).getDate();
    const cells = [...Array(first).fill(null), ...Array.from({ length: last }, (_, i) => ym + String(i + 1).padStart(2, "0"))];
    while (cells.length % 7) cells.push(null);

    // 시간 칩 — 「아침·하교 후·저녁」은 학교 리듬이다. 시각은 자주 쓰는 두 개만 둔다
    const TIMES = [["", "종일"], ["08:00", "아침"], ["15:00", "하교 후"], ["19:00", "저녁"], ["16:00", "16:00"], ["17:00", "17:00"]];

    return `
    ${subHeader(e.id ? `${KIND[e.kind] || ""} 고치기` : `새 ${KIND[e.kind] || ""}`)}

    <label class="ed-f" for="ed-t">${isSup ? "뭘 챙기나요" : e.kind === "mission" ? "아이에게 뭘 시킬까요" : "무슨 일인가요"}</label>
    <input id="ed-t" class="ed-title" maxlength="40" autocomplete="off"
      placeholder="${isSup ? "예: 실내화" : e.kind === "mission" ? "예: 윙크 20분 하기" : "예: 치과"}"
      value="${esc(e.title)}" oninput="S.edit.title=this.value">

    ${(() => {
      // 최근에 넣은 것 재사용 — 「치과·태권도」처럼 되풀이되는 이름을 다시 타자 치게 하지 않는다
      const recent = recentTitles(e.kind).filter((t) => t !== e.title).slice(0, 6);
      if (!recent.length) return "";
      return `<div class="ed-chips recent">${recent.map((t) => `
        <button onclick="App.editSet('title', '${jsq(t)}')">${esc(t)}</button>`).join("")}</div>`;
    })()}

    ${e.kind === "mission" ? "" : `
    <label class="ed-f">언제</label>
    <div class="ed-cal">
      <div class="ed-calhd">
        <button onclick="App.editMonth(-1)" aria-label="지난달"><i aria-hidden="true" class="ti ti-chevron-left"></i></button>
        <b>${yy}년 ${mm}월</b>
        <button onclick="App.editMonth(1)" aria-label="다음달"><i aria-hidden="true" class="ti ti-chevron-right"></i></button>
      </div>
      <div class="ed-calwk">${weekDays().map((d) => `<span class="${d === "일" ? "sun" : ""}">${d}</span>`).join("")}</div>
      <div class="ed-calgrid">
        ${cells.map((k) => k
          ? `<button class="ed-d ${k === e.date ? "on" : ""} ${k === TODAY ? "tdy" : ""}"
               onclick="App.editSet('date', '${k}')">${+k.slice(6)}</button>`
          : `<span class="ed-d empty"></span>`).join("")}
      </div>
    </div>

    <label class="ed-f">시간</label>
    <div class="ed-chips">
      ${TIMES.map(([v, n]) => `<button class="${e.time === v ? "on" : ""}" onclick="App.editSet('time', '${v}')">${n}</button>`).join("")}
      <button class="${e.timeOpen ? "on" : ""}" onclick="App.editTimeOpen()">직접 입력</button>
    </div>
    ${!e.timeOpen ? "" : `<input class="ed-time" type="time" value="${esc(e.time || "")}" oninput="S.edit.time=this.value">`}

    <label class="ed-f">되풀이</label>
    <div class="ed-chips">
      <button class="${e.repeat ? "on" : ""}" onclick="App.editSet('repeat', ${e.repeat ? "false" : "true"})">
        매주 ${["일","월","화","수","목","금","토"][new Date(`${e.date.slice(0,4)}-${e.date.slice(4,6)}-${e.date.slice(6)}`).getDay()]}요일</button>
    </div>`}

    ${e.kind !== "mission" ? "" : `
    <label class="ed-f">얼마나 · 어떻게 확인</label>
    <div class="ed-chips">
      ${[1, 5, 10, 20, 30].map((n) => `<button class="${e.minutes === n ? "on" : ""}" onclick="App.editSet('minutes', ${n})">${n}분</button>`).join("")}
    </div>
    <div class="ed-chips">
      ${[["instant", "눌러서 보고"], ["review", "사진 내기"], ["endday", "하루 끝에"]].map(([v, n]) =>
        `<button class="${e.verify === v ? "on" : ""}" onclick="App.editSet('verify', '${v}')">${n}</button>`).join("")}
    </div>`}

    <label class="ed-f" for="ed-m">메모 <em>(선택)</em></label>
    <input id="ed-m" class="ed-memo" maxlength="60" placeholder="한 줄만" value="${esc(e.memo || "")}" oninput="S.edit.memo=this.value">

    <!-- 넣기·취소는 **화면에 적혀 있어야 한다**(§3). 뒤로가기만으로 빠져나가게 두지 않는다 -->
    <div class="ed-act">
      <button class="ed-cancel" onclick="App.editCancel()">취소</button>
      <button class="ed-save" ${e.busy || !String(e.title).trim() ? "disabled" : ""} onclick="App.editSave()">
        ${e.busy ? "넣는 중…" : e.id ? "저장" : "넣기"}</button>
    </div>
    ${!e.id ? "" : `<button class="ed-del" onclick="App.editDelete()">지우기</button>`}
    `;
  },

  /* ── 일간 전체 화면 (2026-08-03 지시서 0803-2 §2) ──────────────
     «앞날은 계획, 지난날은 기록». 같은 화면이 날짜에 따라 성격만 바뀐다.
     담는 것은 **딱 네 가지** — 일정 · 준비물 · 미션 · 방과후.
     ⚠ 급식과 기록은 여기 없다(§2). 급식은 급식판이, 기록은 서랍이 진다 — 입구가 둘이면 미로가 된다.
     ⚠ **시간축 그리드를 쓰지 않는다**(§2). 빈 시간이 화면을 다 먹고, 종일 일정을 놓을 자리가 없다.
       시간 라벨을 붙인 «목록»이다. */
  day: () => {
    const c = cur();
    const key = S.day || TODAY;
    const y = +key.slice(0, 4), mo = +key.slice(4, 6), d = +key.slice(6);
    const wd = new Date(y, mo - 1, d).getDay();
    const wdKo = ["일", "월", "화", "수", "목", "금", "토"][wd];
    const past = key < TODAY;                   // 지난 날 = 기록 모드
    const today = key === TODAY;

    const sch = schedulesOf().filter((e) => e.date === key && !e.name.includes("토요휴업일"));
    const mine = (STUB.myEvents || []).filter((e) => e.date === key);
    const sup = STUB.supplies.filter((x) => x.date === key);
    const acts = STUB.activities.filter((a) => String(a.days_of_week || "").split(",").includes(String(wd)))
      .sort((x, z) => String(x.start_time).localeCompare(String(z.start_time)));
    const mk = marksOf(key);

    // 일정 = 학교 + 부모. 시간순. 시각 없는 것(학교 행사)은 «종일»로 맨 위
    const evs = [
      ...sch.map((e) => ({ at: "", t: e.name, sub: e.content || "", k: "sc",
                           holi: (e.closure_type || "").includes("공휴일") })),
      ...mine.map((e) => ({ at: e.start || "", t: e.title, sub: e.memo || "", k: "me", id: e.id })),
    ].sort((a, b) => String(a.at || "00:00").localeCompare(String(b.at || "00:00")));

    /* ⚠ **빈 카드를 나열하지 않는다**(2026-08-03 지시).
       「일정 없어요 / 준비물 없어요 / 미션은 아침에 / 방과후 없어요」 네 장이 줄지어 있으면
       화면이 «없다»는 말로 가득 찬다. 있는 것만 카드로 만들고, 전부 비면 한 줄로 합친다. */
    const secs = [];
    const sec = (title, count, body) => {
      if (body) secs.push(`
      <section class="dy-sec">
        <div class="dy-st"><b>${title}</b>${count ? `<em>${count}</em>` : ""}</div>
        ${body}
      </section>`);
      return "";        // ⚠ 값을 안 돌려주면 템플릿에 «undefined» 가 찍힌다
    };

    return `
    ${subHeader(past ? "지난 날 · 기록" : today ? "오늘" : (ddayLabel(key) || "앞으로"))}

    <!-- 큰 날짜 머리 (2026-08-07 마이다이어리 벤치마킹) — 「07 8월 금요일」처럼 날짜 숫자가 주인공.
         날짜 형식 설정(fmtD)은 여기선 안 탄다 — 숫자 하나라 형식이 갈릴 게 없다. -->
    <div class="dy-big">
      <b>${String(d).padStart(2, "0")}</b>
      <span><em>${mo}월 ${wdKo}요일</em><i>${y}</i></span>
    </div>

    <!-- 좌우로 밀면 날짜가 넘어간다(§7). 버튼도 같이 둔다 — 제스처만 있으면 모르는 사람은 못 쓴다 -->
    <div class="dy-nav">
      <button onclick="App.dayMove(-1)" aria-label="전날"><i aria-hidden="true" class="ti ti-chevron-left"></i></button>
      <button class="tdy" onclick="App.dayOpen('${TODAY}')" ${today ? "disabled" : ""}>오늘</button>
      <button onclick="App.dayMove(1)" aria-label="다음날"><i aria-hidden="true" class="ti ti-chevron-right"></i></button>
    </div>

    <div class="dy-wrap ${past ? "past" : ""}" id="dywrap">
    ${sec("일정", evs.length, !evs.length ? "" : `
        <ul class="dy-list">${evs.map((e) => `
          <!-- 길게 누르면 고치기(§7). 버튼(연필)도 같이 둔다 — 제스처만 있으면 모르는 사람은 못 쓴다 -->
          <li class="${e.k}${e.holi ? " holi" : ""}"${e.k === "me" && !past ? ` onpointerdown="App.holdEvent(${e.id})"` : ""}>
            <span class="at">${e.at ? esc(fmtT(e.at)) : "종일"}</span>
            <span class="bd"><b>${esc(e.t)}</b>${e.sub ? `<em>${esc(e.sub)}</em>` : ""}</span>
            ${e.k === "me" && !past ? `<button class="ed" onclick="App.editOpen('plan', ${e.id})" aria-label="고치기"><i aria-hidden="true" class="ti ti-pencil"></i></button>` : ""}
          </li>`).join("")}</ul>`)}

    ${sec("준비물", sup.length, !sup.length ? "" : `
        <ul class="dy-list chk">${sup.map((x) => `
          <li class="${x.done ? "done" : ""}">
            ${past ? `<span class="mk">${x.done ? "✓" : "—"}</span>`
                   : `<button class="mk" onclick="App.supplyToggle(${x.id})" aria-label="${esc(x.item || "")} ${x.done ? "취소" : "챙김"}">${x.done ? "✓" : ""}</button>`}
            <span class="bd"><b>${esc(x.item || x.name || "")}</b>${x.memo ? `<em>${esc(x.memo)}</em>` : ""}</span>
          </li>`).join("")}</ul>`)}

    ${sec("미션", null, (() => {
        // 오늘 것만 실제 목록을 안다. 지난 날은 «흔적»(도장 수)만 남아 있다(§3 marksOf)
        if (today && Array.isArray(S.missions) && S.missions.length) {
          const done = S.missions.filter((x) => x.status === "done").length;
          return `<ul class="dy-list">${S.missions.map((x) => `
            <li class="ms ${x.status}">
              <span class="mk ${x.status === "done" ? "on" : ""}">${x.status === "done" ? "★" : "☆"}</span>
              <span class="bd"><b>${esc(x.title)}</b><em>${x.status === "done" ? "도장 받음" : x.status === "waiting" ? "확인 기다림" : "아직"}</em></span>
            </li>`).join("")}</ul>
            <button class="dy-go" onclick="location.hash='#mission'">미션 화면에서 보기 · ★ ${done}/${S.missions.length}</button>`;
        }
        if (mk && mk.stamp) return `<p class="dy-mk">★ 도장 ${mk.stamp}${mk.of ? `/${mk.of}` : ""}개${mk.meal ? ` · 급식 평가 ★${mk.meal}` : ""}</p>`;
        return "";
      })())}

    ${sec("방과후", acts.length, !acts.length ? "" : `
        <ul class="dy-list">${acts.map((a) => `
          <li class="act">
            <span class="at">${esc(fmtT((a.start_time || "").slice(0, 5)))}</span>
            <span class="bd"><b>${esc(a.name)}</b><em>~${esc(fmtT((a.end_time || "").slice(0, 5)))}</em></span>
          </li>`).join("")}</ul>`)}

      ${secs.length ? secs.join("") : `<p class="dy-blank">${past ? "이날은 아무것도 없었어요" : "이날은 아직 비어 있어요"}</p>`}
    </div>

    <!-- 가벼운 입력 (§3). 지난 날에는 안 띄운다 — 지나간 날에 일정을 넣을 일은 없다 -->
    ${past ? "" : inputBar("plan", "일정을 한 줄로 (예: 치과)")}`;
  },

  timetable: () => {
    S.schoolTab = "timetable";
    S.ttFold = { ...(S.ttFold || {}), school: true };
    return Screens.school();
  },
  meal:      () => { S.schoolTab = "meal";      return Screens.school(); },
  schoolinfo:() => { S.schoolTab = "info";      return Screens.school(); },
  community: () => { S.schoolTab = "community"; return Screens.school(); },

  // ── 5. 자녀 등록 — POST /api/v1/children (§5.1). 실명·동의는 기록 기능용 ──
  "child-add": () => {
    // ⚠ 이 화면은 **자녀가 없을 때도** 그려져야 한다 — cur()를 쓰면 안 된다.
    const sc = S.childDraft.school || schoolInfo();
    // 학년 범위는 학교급에 따라, 반 개수는 그 학년의 실제 학급수(학교알리미)로 제한한다.
    // 웹에도 같은 규칙이 있다(templates.js — 없으면 15까지 폴백).
    const maxGrade = sc.kind === "초등학교" ? 6 : 3;
    const g = S.childDraft.grade;
    // 서버 detail 에는 학년별 학급수가 없다(계약 §4.1은 전교생·학급수만) → 없으면 전체 학급수를 학년으로 나눠 추정
    const gb = sc.detail?.grade_breakdown;
    const classes = gb ? (gb.find((x) => x.grade === +g)?.classes ?? 15)
      : Math.max(1, Math.round((sc.detail?.class_count ?? 24) / maxGrade));
    const editing = S.childEditId != null;   // 수정 모드면 제목·버튼이 달라진다
    return `
    <!-- 시안 9b — 가운데 제목 · 좌측 뒤로. 아바타가 화면의 주인공이다. -->
    <div class="ca-top">
      <a class="ca-back" href="#${editing ? "mypage" : "switch"}" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
      <span class="ca-title">${editing ? "아이 정보" : "아이 등록"}</span>
      <span class="ca-step"></span>
    </div>

    <div class="ca-avatar">
      <button class="ca-face" onclick="App.childPhotoPick()">
        ${S.childDraft.photoPreview                                  /* 아직 안 올라간 사진 — 방금 고른 그림을 바로 보여준다 */
          ? `<img src="${S.childDraft.photoPreview}" alt="">`
          : S.childDraft.photo
            ? `<img src="${PLACEHOLDER}" data-rec="${S.childDraft.photo}" alt="">`
            : `<span class="ini">${esc(initialOf(S.childDraft))}</span>`}
        <em><i class='ti ti-camera'></i></em>
      </button>
    </div>
    <!-- 캐릭터 고르기 줄을 없앴다(2026-07-28) — 아바타는 «사진» 아니면 «별명 첫 글자» 둘뿐이다 -->
    ${S.childDraft.photoPreview || S.childDraft.photo
      ? `<div class="ca-picked"><button class="btn-ghost" onclick="App.childPhotoClear()">사진 빼기</button></div>`
      : ""}
    ${editing ? "" : `<div class="ca-note">아이마다 이용권이 따로예요 · <b>2주 무료 체험</b></div>`}
    <div class="card">
      <!-- 학교 검색이 자녀 등록의 첫 관문이다. 동명 학교가 많아 주소를 같이 보여준다. -->
      <label class="f">학교 *</label>
      <input id="school-q" placeholder="학교 이름을 입력하세요" value="${esc(S.schoolQuery)}" oninput="App.schoolSearch(this.value)">
      ${(() => {
        const q = S.schoolQuery.trim();
        if (!q) return S.childDraft.school
          ? `<div class="picked-school"><i class='ti ti-circle-check'></i> <b>${esc(sc.name)}</b><span class="ntime">${esc(sc.address)}</span></div>`
          : `<p class="sub">전국 12,563개 학교에서 찾아요.</p>`;
        if (q.length < 2) return `<p class="sub">두 글자 이상 적어주세요.</p>`;
        if (S.schoolBusy || S.schoolHits === null) return `<p class="sub">찾는 중…</p>`;
        const hits = S.schoolHits;
        if (!hits.length) return S.schoolFrom === "offline"
          ? `<p class="sub">지금은 학교를 찾을 수 없어요. 인터넷 연결을 확인하고 다시 해주세요.</p>`
          : `<p class="sub">"${q}" 로 찾은 학교가 없어요. 이름을 다시 확인해 주세요.</p>`;
        return `
          <p class="sub">${hits.length}곳 찾았어요 — <b>주소를 보고</b> 우리 학교를 고르세요.
</p>
          <div class="schoollist">
            ${hits.map((s) => `
              <!-- 시·도 배지는 뺐다 — 주소가 이미 "서울특별시 …"로 시작해 같은 말이 두 번 나왔다(2026-07-24) -->
              <div class="srow" onclick="App.schoolPick('${jsq(s.slug)}')">
                <span><b>${esc(s.name)}</b><span class="ntime">${esc(s.address)}</span></span>
                <span class="caret"><i aria-hidden="true" class="ti ti-chevron-right"></i></span>
              </div>`).join("")}
          </div>`;
      })()}
      <div class="row">
        <div><label class="f">학년 *</label>
          <select onchange="App.childGrade(this.value)">
            ${Array.from({ length: maxGrade }, (_, i) => i + 1).map((n) =>
              `<option value="${n}" ${+g === n ? "selected" : ""}>${n}학년</option>`).join("")}
          </select></div>
        <div><label class="f">반</label>
          <!-- ⚠ 예전엔 «1반~N반» 숫자만 골랐다. 그런데 **반 이름이 말인 학교가 있다** —
               경기초 4학년은 「난초·매화·장미」다(2026-08-09 실측). 숫자로 저장하면
               NEIS 에 CLASS_NM=2 로 묻게 되고 **시간표가 영영 0건**이 된다.
               화면엔 「아직 올라오지 않음」만 떠서 부모는 이유를 알 수 없었다.
               → 그 학교·학년의 **실제 반 이름**을 받아오면 그걸 고르게 한다. -->
          <select onchange="S.childDraft.class_name=this.value">
            ${(S.classNames || []).length
              ? S.classNames.map((n) =>
                  `<option value="${esc(n)}" ${String(S.childDraft.class_name) === String(n) ? "selected" : ""}>${esc(n)}${/^\d+$/.test(n) ? "반" : ""}</option>`).join("")
              : Array.from({ length: classes }, (_, i) => i + 1).map((n) =>
                  `<option value="${n}" ${+S.childDraft.class_name === n ? "selected" : ""}>${n}반</option>`).join("")}
          </select>
          <p class="sub">${(S.classNames || []).length
            ? (S.classNames.some((n) => String(n) === String(S.childDraft.class_name))
                ? `${g}학년 실제 반 이름이에요`
                /* ⚠ 저장된 반이 실제 목록에 없으면 **시간표가 안 나온다.**
                   조용히 두면 부모는 이유를 모른 채 빈 시간표만 본다 — 반드시 말해 준다. */
                : `⚠ 지금 「${esc(String(S.childDraft.class_name))}」로 돼 있는데 이 학년엔 없는 반이에요. 다시 골라주세요`)
            : (S.classBusy ? "반 이름을 알아보는 중…"
                : `${g}학년은 ${classes}개 반이에요 · 학교가 시간표를 올리면 실제 반 이름으로 바뀌어요`)}</p></div>
      </div>
      <label class="f">별명 * <span style="font-weight:400">(화면에는 이 이름만 보여요)</span></label>
      <input id="ce-nick" placeholder="예: 셋째" value="${esc(S.childDraft.nickname)}" oninput="S.childDraft.nickname=this.value">
      <label class="f">자녀 이름 <span style="font-weight:400">(기록 보관용 — 분리 보관돼요)</span></label>
      <input id="ce-name" placeholder="실명" value="${esc(S.childDraft.name)}" oninput="S.childDraft.name=this.value">



      <div class="check"><input type="checkbox" id="cs" ${S.childDraft.agree ? "checked" : ""} onchange="S.childDraft.agree=this.checked">
        <label for="cs">보호자 동의 — 자녀 기록 보관에 동의합니다 (기록 기능 필수)</label></div>
      <div style="margin-top:16px"><button class="btn-primary" onclick="App.childSave()">${editing ? "수정 저장" : "등록하기"}</button></div>
    </div>
    <p class="notice">무료로 자녀 1명, 이용권이 있으면 3명까지 등록할 수 있어요. 아이 실명은 앱 어디에도 표시되지 않습니다.</p>`;
  },

  // ── 6. 자녀 전환 = 캐릭터 선택 (정본 §10 — "여러 프로필 나열"이 아니라 캐릭터를 고르는 화면) ──
  switch: () => `
    <h1 style="text-align:center;padding-top:26px">누구의 기록을 볼까요?</h1>
    <p class="sub" style="text-align:center">캐릭터를 고르면 그 자녀로 전환돼요</p>
    <div class="charselect">
      ${STUB.children.map((c) => {
        // 기본 자녀(형제가 있을 때만) — 앱을 켜면 이 아이부터. 아무도 안 골랐으면 첫째가 기본.
        const many = STUB.children.length > 1;
        const isDef = many && pickDefaultChild(STUB.children).id === c.id;
        return `
        <div class="char-card ${c.id === S.currentChildId ? "current" : ""}" onclick="App.pickChild(${c.id})">
          <div class="face ini">${esc(initialOf(c))}</div>
          <div class="nm">${esc(c.nickname)}</div>
          <div class="sc">${esc(schoolName(c).replace("등학교", ""))}<br>${c.grade}학년 ${c.class_name}반</div>
          ${(() => { const pl = passLabel(c); return `<div class="pl ${pl.cls}" style="margin-top:7px">${pl.t}</div>`; })()}
          ${many ? (isDef
            ? `<div class="def-mark">앱 켜면 이 아이</div>`
            : `<button class="def-set" onclick="event.stopPropagation();App.defChildSet(${c.id})">기본으로</button>`) : ""}
        </div>`;
      }).join("")}
      <div class="char-card add" onclick="App.childAddStart()"><div style="font-size:30px">＋</div><div class="nm" style="font-size:13px">자녀 추가</div></div>
    </div>`,

  // ── 7. 기록 업로드 — §0 급소 "넣는 데 30초": 카메라 → 미리보기 → 재촬영/확정 → 저장 ──
  //    실앱: <input capture>가 Capacitor에서 네이티브 카메라를 연다. POST /api/v1/records (§5.3).
  upload: () => {
    const c = curView();
    const step = S.uploadStep;
    const stepBar = `
      <div class="steps">
        <span class="${step === 0 ? "on" : ""}">① 촬영</span>
        <span class="${step === 1 ? "on" : ""}">② 확인</span>
        <span class="${step === 2 ? "on" : ""}">③ 저장</span>
      </div>`;
    const hasCam = !!window.Capacitor?.Plugins?.Camera;   // 앱(네이티브)에서만 진짜 카메라
    const stage = [
      // 0 촬영/앨범 선택 — 저장은 여기서 안 나온다. 사진을 넣어야 다음(미리보기→저장)으로 간다.
      `<div class="camera-box">
         <button class="bigshot" onclick="App.shoot()"><i class='ti ti-camera'></i></button>
         <div style="font-size: var(--fs-sm)">누르면 <b>찍기·갤러리</b>를 고를 수 있어요<br>종이는 테두리를 자동으로 잘라요</div>
       </div>
       <div class="stickybar">
         <button class="btn-primary" onclick="App.shoot()"><i class='ti ti-camera'></i> 사진 등록</button>
       </div>
       ${hasCam ? "" : `<p class="notice">지금은 브라우저라 카메라가 안 열려요 — <b>앱(폰)에서</b> 실제 스캔·촬영이 동작합니다.</p>`}`,
      // 1 미리보기 → 종류/시기 고르고 저장. 저장 버튼은 탭바 위 고정 바(사진이 커도 항상 눌린다 2026-07-24).
      `<!-- 앞·뒤 여러 장을 한 기록에 묶는다(2026-07-24). 통지표는 뒷면에도 내용이 있다. -->
       <div class="shotgrid">
         ${S.shots.map((s, i) => `
           <div class="shotthumb">
             <img src="${s.web}" alt="${i + 1}번째" onclick="App.zoomShot(${i})">
             <span class="shotnum">${i + 1}</span>
             <button class="shotdel" onclick="App.removeShot(${i})"><i class='ti ti-x'></i></button>
           </div>`).join("")}
         <button class="shotadd" onclick="App.addShot()">＋<span>한 장 더</span></button>
       </div>
       <p class="sub" style="margin-top:2px">누르면 크게 봐요 · 현재 ${S.shots.length}장</p>
       ${S.zoomIdx != null && S.shots[S.zoomIdx] ? `
         <div class="overlay viewer" onclick="App.closeZoom()">
           <div class="viewer-card" onclick="event.stopPropagation()">
             <div class="viewer-top"><b>${S.zoomIdx + 1}번째 사진</b>
               <button class="iconbtn" onclick="App.closeZoom()"><i class='ti ti-x'></i></button></div>
             <div class="viewer-img"><img src="${S.shots[S.zoomIdx].web}" alt=""></div>
           </div>
         </div>` : ""}
       ${S.ocrBusy ? `<p class="notice"><i class='ti ti-search'></i> 제목·종류를 자동으로 채우는 중…</p>` : ""}
       <div class="card">
         <label class="f">제목 <span style="font-weight:400">(사진에서 자동 추출 — 확인·수정)</span></label>
         <input id="rec-title" placeholder="예: 교내 독서왕 상장" value="${esc(S.uploadTitle)}" oninput="S.uploadTitle=this.value">
         <label class="f">종류</label>
         <select onchange="S.uploadType=this.value">
           ${["상장", "통지표", "성적표", "자격증", "활동", "기타"].map((v) =>
             `<option ${S.uploadType === v ? "selected" : ""}>${v}</option>`).join("")}
         </select>
         <label class="f">날짜 <span style="font-weight:400">(사진에서 자동 추출 — 확인·수정)</span></label>
         <input type="date" value="${S.uploadDate ? ymdDash(S.uploadDate) : ""}" onchange="S.uploadDate=this.value.replace(/-/g,'')">
         <label class="f">학년 · 학기 * <span style="font-weight:400;color:var(--danger)">직접 선택하세요</span></label>
         <div class="row" style="margin-top:0">
           <!-- 안 고르고 저장을 누르면 토스트만 떴다 사라져 «느려서 안 되는» 줄 알았다(2026-07-31 실사용).
                이제 빨간 테두리 + 아래 문구가 고를 때까지 남는다 -->
           <select class="${S.uploadErr && !S.uploadGrade ? "bad-input" : ""}" onchange="S.uploadGrade=this.value;S.uploadErr=0;App.render()">
             <option value="" ${!S.uploadGrade ? "selected" : ""}>학년</option>
             ${[1, 2, 3, 4, 5, 6].map((g) => `<option value="${g}" ${+S.uploadGrade === g ? "selected" : ""}>${g}학년</option>`).join("")}
           </select>
           <select class="${S.uploadErr && !S.uploadSem ? "bad-input" : ""}" onchange="S.uploadSem=this.value;S.uploadErr=0;App.render()">
             <option value="" ${!S.uploadSem ? "selected" : ""}>학기</option>
             ${[1, 2].map((s) => `<option value="${s}" ${+S.uploadSem === s ? "selected" : ""}>${s}학기</option>`).join("")}
           </select>
         </div>
         ${S.uploadErr ? `<p class="fielderr">학년·학기를 골라야 저장할 수 있어요</p>` : ""}
       </div>
       <div class="stickybar">
         <button class="btn-ghost" onclick="App.retake()"><i class='ti ti-arrow-back-up'></i> 처음</button>
         <button class="btn-primary" onclick="App.confirmShot()">${S.uploadBusy ? "올리는 중…" : `저장 (${S.shots.length}장)`}</button>
       </div>`,
      // 2 저장됨 — 방금 만든 기록을 그대로 보여준다
      `<div class="camera-box" style="background:#2E4636;padding:14px">
         <div style="font-size:54px"><i class='ti ti-circle-check'></i></div>
         <div style="margin-top:10px;color:#fff;text-align:center"><b>${esc(c.nickname)} · ${S.savedLabel || ""}</b><br>
           <span style="font-size:12px">저장했어요</span></div>
       </div>
       <div class="row">
         <button class="btn-ghost" onclick="App.retake()"><i class='ti ti-camera'></i> 한 장 더</button>
         <button class="btn-primary" onclick="location.hash='#timeline'">타임라인 보기</button>
       </div>`,
    ][step];
    return `${childChip()}<h1>기록 올리기</h1><p class="sub">찍고 → 확인하고 → 끝. 30초를 지키는 게 이 앱의 승부처예요.</p>${stepBar}${stage}`;
  },

  // ── 8. 타임라인 — GET /children/{id}/records. 서버는 id DESC, 그룹핑은 앱이 period로(회신19 §3-4) ──
  /* 기록 「아이의 서랍」 — 시안 5a/6a (2026-07-27)
     바뀐 것: ①맨 위에 **가장 최근 한 장을 크게** — 서랍을 열면 오늘 뭘 넣었는지 바로 보인다
              ②학교급 세그먼트(초·중·고) — 초등 6칸 고정이던 구조를 12칸으로. 중·고가 생겨도 화면은 안 늘어난다
              ③학년 줄에서 「비어 있어요」 같은 글을 뺐다 — **사진 더미**가 상태를 말한다(빈 학년은 흐린 빈 종이)
              ④사진 격자 3열 → 2열. 종이가 커야 뭔지 알아본다
     accent 는 딱 세 곳뿐이다 — 학교급 탭 숫자 · 「넣기」 · ＋ (시안 6b). */
  timeline: () => {
    const c = curView();
    const nowGrade = +c.grade || 1;
    const kind = c.school?.kind || "초등학교";
    const entryYear = +TODAY.slice(0, 4) - (nowGrade - 1);

    // 학교급 3구역. 지금 다니는 학교급이 기본으로 열린다.
    const LEVELS = [
      { key: "초", name: "초등학교", n: 6 },
      { key: "중", name: "중학교", n: 3 },
      { key: "고", name: "고등학교", n: 3 },
    ];
    const curLevel = kind.startsWith("고") ? 2 : kind.startsWith("중") ? 1 : 0;
    /* ⚠ **아직 안 온 학년은 그리지 않는다**(2026-07-28 지시).
       2학년인데 3~6학년 빈 칸이 넉 줄 늘어서면 «내가 뭘 안 넣었나» 싶고, 화면만 길어졌다.
       학년이 오르면 그때 한 줄씩 늘어난다 — 서랍이 아이와 같이 자란다.
       학교급도 마찬가지다. 초등학생 화면에 「중·고」 탭을 띄울 이유가 없다. */
    const lv = Math.min(S.tlLevel ?? curLevel, curLevel);
    const shownLevels = LEVELS.slice(0, curLevel + 1);

    const byKey = {};
    STUB.records.forEach((r) => {
      const k = `${r.period?.school_year ?? nowGrade}|${r.period?.semester ?? 1}`;
      (byKey[k] = byKey[k] || []).push(r);
    });
    // 지금은 다니는 학교급 기록만 갖고 있다 — 다른 급은 아직 빈 칸이다(진학하면 채워진다)
    const recsOf = (g) => (lv === curLevel ? [...(byKey[`${g}|1`] || []), ...(byKey[`${g}|2`] || [])] : []);
    const semOf = (g, sem) => (lv === curLevel ? (byKey[`${g}|${sem}`] || []) : []);
    const levelCount = (li) => (li === curLevel ? STUB.records.length : 0);

    // 가장 최근 한 장 — 목록을 훑지 않아도 오늘 넣은 게 보인다
    const latest = STUB.records[0];
    const shots = (r) => (r?.images || []).length || 1;

    /* 사진이 없으면 큰 카드를 세우지 않는다(2026-08-03) — 회색 덩어리가 화면을 먹는다.
       한 줄짜리 «가장 최근»으로 눕힌다. 사진이 있을 때만 16:9 를 쓴다. */
    const hero = !latest ? "" : !latest.image ? `
      <button class="dw-recent" onclick="App.openRecord(${latest.id})">
        <i aria-hidden="true" class="ti ti-file-text"></i>
        <span class="tx"><b>${esc(latest.title)}</b>
          <span>${esc(latest.period.label)}${latest.date ? ` · ${+latest.date.slice(4, 6)}월 ${+latest.date.slice(6)}일` : ""}</span></span>
        <em>가장 최근</em>
        <i aria-hidden="true" class="ti ti-chevron-right go"></i>
      </button>` : `
      <button class="dw-hero" onclick="App.openRecord(${latest.id})">
        <img src="${latest.image}" ${latest._thumb ? `data-rec="${latest._thumb}"` : ""} alt="">
        <span class="dw-scrim"></span>
        <span class="dw-badge accent">가장 최근</span>
        ${shots(latest) > 1 ? `<span class="dw-badge right">${shots(latest)}장</span>` : ""}
        <span class="dw-herotxt">
          <b>${esc(latest.title)}</b>
          <span>${esc(latest.period.label)}${latest.date ? ` · ${+latest.date.slice(4, 6)}월 ${+latest.date.slice(6)}일` : ""}</span>
        </span>
      </button>`;

    // 학년 줄 오른쪽 — 겹쳐 놓은 종이. 없으면 빈 종이 세 장이 흐리게.
    /* ⚠ 기록이 **없으면 빈 종이를 그리지 않는다**(2026-08-08 지적: 「공책에 낙서해놓은 거야?」).
       회색 상자 세 개만 덩그러니 놓이면 «뭔가 있어야 하는데 비었다»로 읽히고,
       학년이 넉 줄이면 화면이 통째로 낙서가 된다. 없으면 **개수로 말한다.** */
    const stack = (rows) => {
      if (!rows.length) return `<span class="dw-none">아직 없어요</span>`;
      return `<span class="dw-stack">${rows.slice(0, 3).map((r) => `
        <i>${r?.image ? `<img src="${r.image}" ${r._thumb ? `data-rec="${r._thumb}"` : ""} alt="">` : ""}</i>`).join("")}
        ${rows.length > 3 ? `<em>+${rows.length - 3}</em>` : ""}</span>`;
    };

    const semBlock = (g, sem) => {
      const rows = semOf(g, sem);
      return `
      <div class="dw-semhd"><span>${sem}학기</span>
        <em>${rows.length ? `${rows.length}건` : "없어요"}</em>
        <button onclick="App.addRecordAt(${g}, ${sem})"><span class="pl">＋</span> 넣기</button></div>
      ${rows.length ? `<div class="dw-grid">${rows.map((r) => `
        <button class="dw-item" onclick="if(!App.holdGuard())App.openRecord(${r.id})" onpointerdown="App.holdRecord(${r.id})">
          <span class="dw-shot">
            ${r.image ? `<img src="${r.image}" ${r._thumb ? `data-rec="${r._thumb}"` : ""} alt="">` : `<i class='ti ${r.icon}'></i>`}
            ${shots(r) > 1 ? `<em>${shots(r)}장</em>` : ""}
          </span>
          <span class="dw-t">${esc(r.title)}</span>
          <span class="dw-d">${r.date ? `${r.date.slice(4, 6)}.${r.date.slice(6)}` : ""}</span>
        </button>`).join("")}</div>` : ""}`;
    };

    /* 기록 검색(2026-08-01) — 학년이 쌓이면 아코디언을 다 열어 훑어야 «작년 통지표»가 나온다.
       찾는 말은 제목만이 아니다: 「통지표」(종류)·「3학년」·「1학기」·날짜로도 찾는다.
       그래서 한 줄로 이어 붙여 한 번에 본다 — 검색칸을 종류별로 나누면 아무도 안 쓴다. */
    const q = (S.recQ || "").trim().toLowerCase();
    const hits = !q ? null : STUB.records.filter((r) => [
      r.title, r.period?.label, CATEGORY_KO[r.category],
      `${r.period?.school_year ?? ""}학년`, `${r.period?.semester ?? ""}학기`,
      r.date, r.date ? `${+r.date.slice(4, 6)}월 ${+r.date.slice(6)}일` : "",
    ].join(" ").toLowerCase().includes(q));

    const L = LEVELS[lv];
    return `
    ${subHeader("서랍", esc(c.nickname))}
    <div class="dw-top">
      <!-- ⚠ 이니셜 얼굴 옆에 이름을 또 쓰면 「테 테스트아이」로 읽힌다(08-08). 이름만 둔다 -->
      <button class="dw-child" onclick="location.hash='#switch'">
        <span>${esc(c.nickname)}</span><i class='ti ti-chevron-down'></i>
      </button>
      <span class="dw-acts"><button onclick="App.recordSearch()">${S.recSearch ? "닫기" : "검색"}</button></span>
    </div>
    ${S.recSearch ? `
      <div class="dw-search">
        <i class='ti ti-search'></i>
        <input id="recq" value="${esc(S.recQ)}" placeholder="제목·종류·학기로 찾기 (예: 통지표, 3학년)"
          oninput="App.recordQuery(this.value)" autocomplete="off">
        ${S.recQ ? `<button class="iconbtn" onclick="App.recordQuery('')" aria-label="지우기"><i class='ti ti-x'></i></button>` : ""}
      </div>` : ""}

    <div class="dw-hd"><b>${esc(c.nickname)}의 서랍</b><span>${entryYear}년 입학 · ${STUB.records.length}건</span></div>
    ${S.uploadStep === 1 && S.shots.length ? `
      <button class="dw-pending" onclick="location.hash='#upload'">
        <i class='ti ti-alert-triangle'></i> 찍어둔 사진 ${S.shots.length}장이 저장 전이에요<em>이어서 저장<i aria-hidden="true" class="ti ti-chevron-right"></i></em>
      </button>` : ""}
    ${S.upFail ? `
      <button class="dw-pending" onclick="App.retryUpload()">
        <i class='ti ti-alert-triangle'></i> 기록 1건이 서버에 안 올라갔어요<em>다시 올리기<i aria-hidden="true" class="ti ti-chevron-right"></i></em>
      </button>` : ""}
    ${hits ? `
      <div class="dw-hits">
        <p class="sub" style="padding:0 2px 8px;margin:0">${hits.length ? `${hits.length}건 찾았어요` : "찾는 기록이 없어요"}</p>
        ${hits.length ? `<div class="dw-grid">${hits.map((r) => `
          <button class="dw-item" onclick="App.openRecord(${r.id})">
            <span class="dw-shot">
              ${r.image ? `<img src="${r.image}" ${r._thumb ? `data-rec="${r._thumb}"` : ""} alt="">` : `<i class='ti ${r.icon}'></i>`}
              ${shots(r) > 1 ? `<em>${shots(r)}장</em>` : ""}
            </span>
            <span class="dw-t">${esc(r.title)}</span>
            <span class="dw-d">${esc(r.period?.label || "")}</span>
          </button>`).join("")}</div>` : ""}
      </div>
      ${recordViewer()}` : `
    ${hero}

    ${shownLevels.length < 2 ? "" : `<div class="dw-seg">
      ${shownLevels.map((x, i) => `
        <button class="${i === lv ? "on" : ""}" onclick="App.tlLevel(${i})">
          ${x.key}<em>${levelCount(i) || ""}</em>
        </button>`).join("")}
    </div>`}

    ${adSlot("drawer")}

    <div class="dw-years">
      ${Array.from({ length: lv < curLevel ? L.n : Math.min(nowGrade, L.n) }, (_, i) => i + 1).reverse().map((g) => {
        const rows = recsOf(g);
        const open = (S.tlOpen === null ? (lv === curLevel ? nowGrade : 0) : S.tlOpen) === g;
        return `
        <div class="dw-year">
          <button class="dw-yearhd" onclick="App.tlToggle(${g})">
            <span class="dw-g ${rows.length ? "" : "dim"}"><b>${g}학년</b><span>${entryYear + (lv === 0 ? g - 1 : lv === 1 ? 5 + g : 8 + g)}</span></span>
            ${stack(rows)}
            <span class="dw-n">${rows.length || ""}</span>
          </button>
          <!-- 빈 학년도 펼쳐진다(2026-07-31) — 전엔 기록이 0이면 눌러도 아무 일이 없어
               «아코디언이 안 된다»로 읽혔다. 펼치면 학기별 「넣기」가 나온다 -->
          ${open ? `<div class="dw-body">${semBlock(g, 1)}${semBlock(g, 2)}</div>` : ""}
        </div>`;
      }).join("")}
    </div>

    <div class="dw-fab"><button onclick="App.shoot()"><span>＋</span> 기록 넣기</button></div>
    ${recordViewer()}`}`;
  },

  // ── 9. 방과후 주간뷰 — GET /children/{id}/activities ──
  // 주간 타임그리드 — 작은 칸에 글자를 우겨넣지 않는다(2026-07-24 지시).
  // 가로=월~금, 세로=시간축. 시간은 축에서 읽으므로 블록 안에는 이름만 넣는다(글자 잘림 원인 제거).
  afterschool: () => {
    // 오늘 열을 짚어준다 — 주간 격자에서 제일 먼저 궁금한 것이 «오늘 뭐 있지»다
    const todayCol = new Date(`${TODAY.slice(0,4)}-${TODAY.slice(4,6)}-${TODAY.slice(6)}`).getDay() - 1;
    const byDay = [[], [], [], [], []];
    STUB.activities.forEach((a) => a.days_of_week.split(",").forEach((d) => byDay[+d - 1].push(a)));
    const hours = [];
    for (let h = GRID.h0; h < GRID.h1; h++) hours.push(h);
    return `
    ${subHeader("방과후 · 학원")}
    <!-- 자매 사이트 — 학원을 찾는 맥락이 여기다(방과후 시간표를 짜다가 "어디 보내지?"가 나온다).
         앱 안 웹뷰가 아니라 **바깥 브라우저**로 연다: 우리 앱은 아이 정보를 다루므로
         남의 페이지를 앱 안에 띄우면 쿠키·권한이 섞이고 스토어 심사에서도 설명이 길어진다.
         ⚠ 주소가 없으면 **버튼 자체를 안 그린다**(2026-07-31) — 눌러서 안 열리는 링크는
            스토어 심사 반려 사유이고, 사용자에겐 고장으로 보인다. 주소가 생기면 SISTER_SITES 만 채운다. -->
    ${sisterLink("academy", "우리 동네 학원 찾기", "우리아이학원정보 — 학원비·과목별로 비교")}
    ${STUB.activities.length ? "" : `
    <button class="ms-mkbtn" onclick="App.planNew()">
      <i aria-hidden="true" class="ti ti-plus"></i>
      <span><b>방과후 · 학원 넣기</b></span></button>`}
    <!-- 「[네이티브 자리] 실앱은 드래그를 그대로 씁니다」를 걷어낼 때 엉뚱한 문장이 붙어
         «시간이 늘어납니다 순서는 화살표로 바꿔요»가 됐다(2026-07-27). 사람이 읽는 말로 되돌린다. -->
    <!-- ⚠ 세로 구분선이 없어서 «이게 화요일인지 수요일인지» 안 읽혔다(2026-07-28 사장님 지적).
         칸마다 왼쪽 선을 긋고, 홀·짝 요일에 아주 옅은 톤 차이를 준다. 오늘은 강조색으로.
         색을 다섯 개 쓰지 않는다 — 학원 블록이 이미 색을 갖고 있어서 배경까지 알록달록하면 싸운다. -->
    <div class="wk">
      <div class="wk-hd"><div></div>${DAY_KO.map((d, i) => `<div class="${i === todayCol ? "today" : ""}">${d}</div>`).join("")}</div>
      <div class="wk-body">
        <div class="wk-axis">${hours.map((h) => `<div style="height:${GRID.px * 2}px"><span>${h}시</span></div>`).join("")}</div>
        ${DAY_KO.map((d, i) => `
          <div class="wk-col d${i} ${i % 2 ? "alt" : ""} ${i === todayCol ? "today" : ""}"
               role="button" aria-label="${d}요일 — 눌러서 일정 넣기" onclick="App.planTap(event, ${i + 1})">
            ${hours.map(() => `<div class="wk-slot" style="height:${GRID.px * 2}px"></div>`).join("")}
            ${byDay[i].map((a) => `
              <div class="blk" onclick="if(!App.holdGuard())App.planEdit(${a.id})" onpointerdown="App.holdPlan(${a.id})" style="top:${gridTop(a.start_time)}px;height:${Math.max(GRID.px, gridTop(a.end_time) - gridTop(a.start_time))}px;--tag:${planColor(a.color, a.name).v}"
                   onclick="event.stopPropagation();App.askDelete('일정 「${esc(a.name)}」 수정·삭제')">
                <b>${esc(a.name)}</b>
                <i class="grip" onpointerdown="App.gripDown(event, ${a.id}, ${i + 1})"></i>
              </div>`).join("")}
          </div>`).join("")}
      </div>
    </div>
`;
  },

  /* ── 9-2. 준비물 체크리스트 (2026-07-27) ────────────────────
     GET/POST /children/{id}/supplies · PATCH/DELETE /supplies/{id}
     리서치에서 학원·학교 일정 앱들이 공통으로 가진 것이었고, 우리 커뮤니티에서
     가장 많이 오가는 말도 «내일 뭐 가져가?» 였다.
     기준 날짜를 «오늘»이 아니라 **«내일»**로 잡는다 — 준비물은 전날 저녁에 챙긴다. */
  supplies: () => {
    const on = STUB.supplies.filter((s) => s.date >= TODAY).sort((a, b) => (a.date === b.date ? a.id - b.id : a.date < b.date ? -1 : 1));
    const past = STUB.supplies.filter((s) => s.date < TODAY).sort((a, b) => (a.date > b.date ? -1 : 1)).slice(0, 20);
    const byDate = [];
    on.forEach((s) => {
      const g = byDate.find((x) => x.date === s.date);
      (g ? g.items : (byDate.push({ date: s.date, items: [] }), byDate[byDate.length - 1].items)).push(s);
    });
    /* 시안 10d (2026-07-28) — **체크가 주인공이다.**
       예전엔 입력이 3칸(날짜·이름·메모) + 버튼 + 반복버튼으로 다섯 줄을 먹고,
       정작 체크박스는 기본 크기(약 16px)라 손끝으로 누르기 어려웠다.
       ① 입력은 **한 줄**. 날짜·반복은 그 아래 «칩» 두 개로 접는다
       ② 체크 32px 원. 체크되면 **채우고 취소선** — 바탕화면 위젯과 같은 문법이다
       ③ 메모는 항목 밑 작은 줄. 없으면 아예 자리를 안 쓴다 */
    /* 줄마다 붙던 휴지통 제거(2026-08-03 간단판) — 지우기·날짜·반복은 꾹 메뉴 하나로 */
    const line = (s) => `
      <label class="sp-row ${s.done ? "done" : ""}" onpointerdown="App.holdSupply(event, ${s.id})">
        <input type="checkbox" ${s.done ? "checked" : ""} onchange="if(!App.holdGuard())App.supplyToggle(${s.id})">
        <i class="sp-box"></i>
        <span class="sp-t"><b>${esc(s.item)}</b>${s.memo ? `<span>${esc(s.memo)}</span>` : ""}</span>
      </label>`;

    return `
    ${subHeader("준비물")}
    <div class="sp-hd">
      <button class="sp-alarm" onclick="location.hash='#notify'">${S.remind?.on ? `알림 ${esc(S.remind.evening)}` : "알림 끔"}</button>
    </div>

    <!-- 입력칸은 화면 «아래 고정»으로 옮겼다(§3) — 목록 위에 있으면 스크롤할 때마다 사라진다 -->

    ${byDate.length ? byDate.map((g) => {
      const left = g.items.filter((s) => !s.done).length;
      return `
      <div class="sp-day">
        <div class="sp-dhd">
          <b>${supDayLabel(g.date)}</b>
          <span class="${left ? "" : "ok"}">${g.items.length - left} / ${g.items.length}</span>
        </div>
        <div class="sp-list">${g.items.map(line).join("")}</div>
      </div>`;
    }).join("") : `<div class="sp-empty">아직 없음</div>`}

    <p class="gc-hint">항목을 꾹 누르면 날짜·반복·지우기</p>
    ${inputBar("sup", "내일 챙길 것 (예: 실내화)")}

    ${past.length ? `
      <div class="sp-day">
        <div class="sp-dhd"><b>지난 준비물</b></div>
        <div class="sp-past">${past.map((s) => `${esc(s.item)} <em>${+s.date.slice(4, 6)}.${+s.date.slice(6)}</em>`).join(" · ")}</div>
      </div>` : ""}`;
  },

  // ── 10. 마이페이지 — GET /api/v1/me · DELETE /api/v1/me ──
  /* ── 10. 내 정보 (2026-07-28 재설계) ────────────────────────
     흰 카드가 **7개** 쌓여 있었고, 탈퇴처럼 되돌릴 수 없는 것과 테마처럼 가벼운 것이
     같은 무게로 나란히 있었다(사장님 지적). 이제 **섹션 머리 + 목록** 하나로 간다.
     ① 카드는 4개. 머리글은 카드 «밖»에 두어 카드가 곧 «묶음»이 된다
     ② 테마 6칸 격자는 시트로 접었다 — 자주 바꾸는 게 아닌데 화면 한 판을 먹고 있었다
     ③ 탈퇴는 빨간 큰 버튼이 아니라 **맨 아래 조용한 줄**이다. 되돌릴 수 없는 것은
        손이 먼저 가면 안 된다. 경고문은 누른 뒤 확인 창이 말한다 */
  mypage: () => {
    const me = STUB.me;
    /* 테마 2벌(2026-08-02) — 옛 6키는 style.css 에서 새 두 벌에 매달아 뒀다.
       저장해 둔 값이 옛 키여도 이름이 «—»로 비지 않게 여기서도 같이 접는다. */
    const themeName = ({ light: "밝게", warmgray: "밝게", ivory: "밝게", mint: "밝게",
                        dark: "어둡게", lavender: "어둡게", navy: "어둡게", charcoal: "어둡게" }[S.theme] || "밝게")
      + " · " + (ART_SETS.find((a) => a.key === S.art)?.label || "새벽");
    /* 행마다 왼쪽 선형 아이콘(2026-08-02 다이어트) — 홈 격자와 같은 스타일.
       파랑은 절제: 아이콘은 회색, 값·경고만 기능색. icon 이 빈 문자열이면 칸 자체가 없다(계정 구역). */
    const row = (icon, label, value, onclick, cls = "") => `
      <button class="mp-row ${cls}" ${onclick ? `onclick="${onclick}"` : ""}>
        ${icon ? `<span class="mp-i"><i aria-hidden="true" class="ti ${icon}"></i></span>` : ""}
        <span class="mp-l">${label}</span>
        ${value ? `<span class="mp-v">${value}</span>` : ""}
        ${onclick ? `<span class="mp-go"><i aria-hidden="true" class="ti ti-chevron-right"></i></span>` : ""}
      </button>`;
    return `
    ${subHeader("내 정보 · 설정")}

    <div class="mp-me">
      <div class="mp-mine">
        <b onclick="App.nameEdit()">${esc(me.account.display_name) || "이름을 넣어주세요"}<i class='ti ti-pencil'></i></b>
        <span>${esc(me.account.email)}</span>
      </div>
    </div>

    <div class="mp-sec">자녀</div>
    <div class="mp-list">
      ${STUB.children.map((c) => {
        const pl = passLabel(c);
        return row("ti-user", `${esc(c.nickname)} <em>${c.grade}학년 ${c.class_name}반</em>`,
          `<span class="pl ${pl.cls}">${pl.t}</span>`, `App.childEditStart(${c.id})`);
      }).join("")}
      ${row("ti-plus", "자녀 추가", "", "App.childAddStart()", "accent")}
    </div>

    <!-- 자녀폰 연결(2026-07-31) — **아이 1명당 1대.** 누가 붙어 있는지 여기서 보고, 끊을 수도 있다.
         새 코드로 다른 폰이 붙으면 앞 폰은 그 자리에서 끊긴다(서버가 기기 표식으로 판정). -->
    <div class="mp-sec">자녀폰</div>
    <div class="mp-list">
      ${STUB.children.map((c) => {
        const on = !!c.child_device;
        const when = c.child_device_at ? String(c.child_device_at).slice(0, 10).replace(/-/g, ".") : "";
        /* ⚠ 연결된 아이는 «불이 들어온» 것처럼 보여야 한다(08-09 지시).
           지금까지는 정작 «자녀 추가» 쪽이 강조색이라 켜진 것처럼 보이고,
           진짜 붙어 있는 아이 줄이 밋밋했다 — 순서가 반대였다. */
        return `<div class="mp-row two${on ? " lit" : ""}">
          <span class="mp-l">${esc(c.nickname)}<em>${on ? `연결됨${when ? ` · ${when}부터` : ""}` : "연결 안 됨"}</em></span>
          <span class="cl-acts">
            ${on ? `<button class="cl-off" onclick="App.unlinkChild(${c.id})">끊기</button>` : ""}
            <button class="cl-on" onclick="App.inviteChild(${c.id})">${on ? "다시 연결" : "연결하기"}</button>
          </span>
        </div>`;
      }).join("")}
    </div>
    ${S.inviteCode ? `<div class="cl-code">
      <b>${esc(S.inviteCode)}</b>
      <span>${S.inviteFor ? `${esc(S.inviteFor)} 폰에서 ` : ""}「자녀폰인가요?」에 10분 안에 넣어주세요</span>
      <button class="mp-link" onclick="App.inviteClose()">닫기</button>
    </div>` : ""}

    <!-- 서식(2026-08-02 메뉴 개편) — 하단 탭에서 내려와 여기 산다. 라벨은 동사형:
         1년에 몇 번 안 쓰는 기능이라 이름만 보고 뭘 하는 건지 알아야 한다 -->
    <div class="mp-sec">신청·서류</div>
    <div class="mp-list">
      ${row("ti-pencil", "체험학습 신청하기", "", "App.docStart('field','apply')")}
      ${row("ti-file-text", "결석·조퇴 서류 내기", "", "location.hash='#docs'")}
      ${(() => {
        const und = STUB.documents.filter((d) => d.kind === "field" && !d.reported).length;
        return und ? row("ti-flag", "체험학습 보고서 내기", `<span class="pl warn">안 낸 것 ${und}</span>`, "location.hash='#docs'") : "";
      })()}
    </div>

    <div class="mp-sec">앱</div>
    <div class="mp-list">
      ${row("ti-photo", "테마", themeName, "location.hash='#theme'")}
      ${row("ti-bell", "알림", S.remind?.on ? `준비물 ${esc(S.remind.evening)}` : "끔", "location.hash='#notify'")}
      ${row("ti-lock", "앱 잠금", S.appLock ? "켜짐 · 지문·얼굴" : "꺼짐", "App.appLockToggle()")}
      ${row("ti-receipt", "이용권", cur()?.pass?.active ? "쓰는 중" : "무료", "location.hash='#pay'")}
      ${row("ti-share-2", "내보내기 · 가져오기", "", "location.hash='#backup'")}
    </div>

    <!-- 시간 옵션 (2026-08-03 §4) — 토글 목록 + **항목 밑 회색 설명**이 이 화면의 문법이다.
         ⚠ 「요일 시작」은 달력이 월요일부터냐 일요일부터냐다. 학교 주간표는 월요일부터라
           헷갈리는 사람이 많아서 고를 수 있게 둔다. -->
    <div class="mp-sec">시간 옵션</div>
    <div class="mp-list">
      ${(() => {
        const T = S.timeOpt || {};
        /* ⚠ 설명문을 안 붙인다(2026-08-03 지시) — 「일 / 월」, 「8월 3일 / 8.3」처럼
           **선택지 자체가 설명**이다. 이름만으로 아는 것에 회색 글씨를 더하면 소음이다. */
        const seg = (key, opts, label) => `
          <div class="mp-row two">
            <span class="mp-l">${label}</span>
            <span class="mp-seg">${opts.map(([v, n]) =>
              `<button class="${(T[key] || opts[0][0]) === v ? "on" : ""}" onclick="App.timeOpt('${key}','${v}')">${n}</button>`).join("")}</span>
          </div>`;
        return seg("weekStart", [["sun", "일"], ["mon", "월"]], "요일 시작")
             + seg("dateFmt", [["ko", "8월 3일"], ["dot", "8.3"]], "날짜 형식")
             + seg("timeFmt", [["24", "15:00"], ["12", "오후 3시"]], "시간 형식");
      })()}
    </div>

    <!-- 연결된 기기 (2026-08-01) — 엄마·아빠가 각자 폰에서 같은 계정을 본다.
         2대까지고, 3번째가 로그인하면 가장 오래 안 쓴 폰이 밀려난다.
         「지금 이 폰」을 표시해 주지 않으면 자기 폰을 끊어버린다. -->
    ${(S.devices || []).length ? `
    <div class="mp-sec">이 계정을 보는 폰 <em class="mp-cnt">${S.devices.length}/${S.deviceLimit || 2}</em></div>
    <div class="mp-list">
      ${S.devices.map((d) => `
        <div class="mp-row two">
          <span class="mp-l">${esc(d.label || "이름 없는 폰")}${d.this_device ? `<em>지금 이 폰</em>` : `<em>마지막 접속 ${esc((d.last_seen_at || "").slice(0, 10).replace(/-/g, "."))}</em>`}</span>
          ${d.this_device ? "" : `<button class="cl-off" onclick="App.deviceRemove('${jsq(d.id)}')">끊기</button>`}
        </div>`).join("")}
    </div>
    <p class="mp-hint">${S.deviceLimit || 2}대까지 · 새 폰이 들어오면 가장 오래된 폰이 끊겨요</p>` : ""}

    <!-- 고객센터는 「계정」이 아니라 별도 칸에 둔다 — 결제·기록·오류 문의가 다 여기로 오므로
         약관 아래 묻히면 못 찾는다. 안 읽은 답변이 있으면 여기서 먼저 보인다(2026-08-01). -->
    <div class="mp-sec">도움말</div>
    <div class="mp-list">
      ${(() => {
        const unread = (S.inquiries || []).filter((x) => x.status === "answered" && !x.seen_at).length;
        return row("ti-message-circle", "고객센터 · 자주 묻는 질문", unread ? `답변 ${unread}건` : "", "location.hash='#help'", unread ? "danger" : "");
      })()}
    </div>

    <div class="mp-sec">계정</div>
    <div class="mp-list">
      ${row("", "이용약관", "", "location.hash='#terms'")}
      ${row("", "개인정보처리방침", "", "location.hash='#policy'")}
      ${row("", "로그아웃", "", "App.logout()")}
      ${(() => {
        // 광고성 수신 채널별 켜고 끄기 — 철회 수단은 의무다(방침 9항). 서버(accounts.marketing)에 바로 반영.
        const mk = S.marketing || {};
        const chip = (k, nm) => `<button class="mk-chip ${mk[k] ? "on" : ""}" onclick="event.stopPropagation();App.mkToggle('${k}')">${nm}</button>`;
        return `<div class="mp-row two"><span class="mp-l">혜택·소식 받기</span>
          <span class="mk-chips">${chip("email", "메일")}${chip("sms", "문자")}${chip("call", "전화")}</span></div>`;
      })()}
      ${row("", "회원 탈퇴", "", "App.withdrawAsk()", "danger")}
    </div>

    <!-- 이름 수정 시트 폐지(§4) — 전용 화면 Screens.editname -->

    <!-- 테마 «반쪽 시트» 폐지(2026-08-03 §3·§4) — 전용 화면 Screens.theme 이 대신한다.
         화면 절반을 가린 채 테마를 고르면 **무엇이 바뀌는지 볼 수가 없다.** -->
`;
  },

  /* ── 부모 월간 리포트 (2026-08-03) ────────────────────────────
     일일 퀘스트 셋이 한 달 동안 쌓은 것을 부모에게 한 장으로 돌려준다.
     ⚠ **숫자는 반드시 «몇 번 중 몇 번»으로 쓴다.** 비율만 보여주면 한 번짜리를 사실로 믿는다.
        한 반 30명·같은 성별 15명이라 분모가 작은 게 정상이다.
     ⚠ 아이 화면엔 이게 없다. 지난달 취향은 아이 관심 밖이다. */
  report: () => {
    const c = cur();
    const r = S.report;
    const mm = (S.reportMonth || TODAY.slice(0, 6));
    const label = `${mm.slice(0, 4)}년 ${+mm.slice(4)}월`;
    const nav = `
      <div class="rp-nav">
        <button onclick="App.reportMove(-1)" aria-label="지난달"><i aria-hidden="true" class="ti ti-chevron-left"></i></button>
        <b>${label}</b>
        <button onclick="App.reportMove(1)" ${mm >= TODAY.slice(0, 6) ? "disabled" : ""} aria-label="다음달"><i aria-hidden="true" class="ti ti-chevron-right"></i></button>
      </div>`;

    if (!r || S.reportBusy) return `
      <a class="back" href="#mission" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
      <h1 class="pg-h">${esc(c?.nickname || "아이")} 리포트</h1>
      ${nav}
      <p class="sub" style="margin-top:20px">불러오는 중…</p>`;

    // 셋 다 비었으면 «아직 모으는 중» 한 장. 빈 표를 늘어놓으면 고장난 것처럼 보인다
    const total = (r.meal?.days || 0) + (r.play?.days || 0) + (r.subject?.days || 0);
    if (!total) return `
      <a class="back" href="#mission" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
      <h1 class="pg-h">${esc(c?.nickname || "아이")} 리포트</h1>
      ${nav}
      <div class="rp-empty">
        <i aria-hidden="true" class="ti ti-clock"></i>
        <b>아직 모으는 중이에요</b>
        <span>열흘쯤 모이면 나와요</span>
      </div>`;

    const bar = (n, max) => `<i style="width:${max ? Math.round((n / max) * 100) : 0}%"></i>`;
    const rows = (items, key, cntKey, unit) => {
      const max = Math.max(...items.map((x) => x[cntKey]), 1);
      return items.map((x) => `
        <li><b>${esc(String(x[key]))}</b>
          <span class="rp-bar">${bar(x[cntKey], max)}</span>
          <em>${x[cntKey]}${unit}</em></li>`).join("");
    };

    /* ⚠ 한 달을 봤는데 «알려주는 게 없다»는 지적(08-09). 세부 목록만 있고 요약이 없었다.
       맨 위에 «며칠 남겼나»를 먼저 놓는다 — 부모가 제일 먼저 궁금한 것이다.
       ⚠ 없는 숫자를 만들지 않는다. 여기 쓰는 값은 전부 서버가 준 것뿐이다. */
    const sum = [
      ["🍚", "급식", r.meal?.days || 0],
      ["🧒", "친구", r.play?.days || 0],
      ["📘", "과목", r.subject?.days || 0],
    ];
    return `
    <a class="back" href="#mission" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 class="pg-h">${esc(c?.nickname || "아이")} 리포트</h1>
    ${nav}

    <div class="rp-sum">
      <b class="rp-sum-h">${+mm.slice(4)}월에 <em>${total}일</em> 남겼어요</b>
      <div class="rp-sum-g">
        ${sum.map(([ic, ko, n]) => `<div><span>${ic}</span><b>${n}<i>일</i></b><em>${ko}</em></div>`).join("")}
      </div>
    </div>

    ${r.meal?.days ? `
    <div class="rp-sec">
      <div class="rp-hd"><b>급식</b><span>${r.meal.days}일 기록${r.meal.avg_stars ? ` · 평균 ★${r.meal.avg_stars}` : ""}</span></div>
      ${r.meal.cats?.length ? `<p class="rp-lead">어떤 <b>종류</b>를 좋아하나</p>
        <ul class="rp-list">${rows(r.meal.cats, "cat", "best", "번 1등")}</ul>` : ""}
      ${r.meal.dishes?.length ? `<p class="rp-lead">두 번 이상 나온 <b>메뉴</b></p>
        <ul class="rp-list">${r.meal.dishes.map((d) => `
          <li><b>${esc(d.name)}</b><span class="rp-bar">${bar(d.best, Math.max(...r.meal.dishes.map((x) => x.shown)))}</span>
            <em>${d.shown}번 중 ${d.best}번</em></li>`).join("")}</ul>`
        : `<p class="rp-note">두 번 이상 나온 메뉴가 아직 없어요</p>`}
    </div>` : ""}

    ${r.play?.days ? `
    <div class="rp-sec">
      <div class="rp-hd"><b>친구</b><span>${r.play.days}일 기록${r.play.alone ? ` · 혼자 논 날 ${r.play.alone}일` : ""}</span></div>
      ${r.play.friends?.length ? `<ul class="rp-list">${rows(r.play.friends, "name", "n", "일")}</ul>`
        : `<p class="rp-note">아직 이름이 안 모였어요.</p>`}
      <p class="rp-note">아이가 직접 고른 이름이에요</p>
    </div>` : ""}

    ${r.subject?.items?.length ? `
    <div class="rp-sec">
      <div class="rp-hd"><b>재밌었던 과목</b><span>${r.subject.days}일 기록</span></div>
      <ul class="rp-list">${rows(r.subject.items, "subject", "n", "일")}</ul>
      <p class="rp-note">성적이 아니라 <b>재미</b>예요</p>
    </div>` : ""}`;
  },

  /* ── 10-1. 잠금 (2026-07-28) ─────────────────────────────
     체험 2주가 끝나고 이용권이 없을 때 뜬다. **기록은 안 지운다** —
     지운다고 하면 무섭고, 실제로도 안 지운다. 다시 열면 그대로 있다고 말해준다. */
  locked: () => {
    const c = cur();
    return `
    <div class="lk">
      <div class="lk-mark"><i class='ti ti-lock'></i></div>
      <h1 class="lk-h">체험이 끝났어요</h1>
      <p class="lk-p">${esc(c?.nickname || "아이")}의 급식·시간표·준비물·기록을<br>계속 보려면 이용권이 필요해요.</p>
      <div class="lk-keep">
        <b>넣어둔 기록은 그대로 있습니다</b>
        <span>지우지 않아요 · 이용권을 사면 다시 보입니다</span>
      </div>
      <button class="lk-go" onclick="location.hash='#pay'">이용권 보기</button>
      <div class="lk-sub">
        <button onclick="location.hash='#mypage'">내 정보</button>
        <i>·</i>
        <button onclick="App.logout()">로그아웃</button>
      </div>
    </div>`;
  },

  // ── 11. 결제(모의) — GET /plans · POST /orders · mock-pay (§6). 자녀별 과금 ──
  /* 이용권 — **자녀별**이다(성적·기록은 아이마다 다른 개인 자료라 한 장으로 못 나눈다).
     대신 둘째·셋째는 값을 낮춘다(2026-08-01). 자리값·금액은 **서버가 정한다** —
     여기서 계산하면 화면과 청구액이 어긋난다. STUB.plans 는 서버를 못 붙었을 때의 폴백. */
  pay: () => {
    const c = curView();
    const list = S.planList || STUB.plans;
    const seat = S.planSeat || 1;
    return `
    <a class="back" href="#mypage" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 style="margin-top:8px">이용권</h1>
    <p class="sub">자녀 1명당 하나씩 — 지금은 <b>${esc(c.nickname)}</b> 이용권을 골라요</p>
    ${seat > 1 ? `<p class="seatnote"><i class='ti ti-discount'></i> <b>${seat}번째 자녀</b>라 더 저렴해요</p>` : ""}
    ${list.map((p) => `
      <div class="plan ${S.planSel === p.months ? "on" : ""}" onclick="App.pickPlan(${p.months})">
        <span><b>${p.months}개월</b> ${p.discount ? `<span class="disc">${p.discount}</span>` : ""}<div class="sub">월 ${won(p.per_month)}꼴</div></span>
        <b>${p.list_amount && p.list_amount !== p.amount ? `<s>${won(p.list_amount)}</s> ` : ""}${won(p.amount)}</b>
      </div>`).join("")}
    <div style="margin-top:16px"><button class="btn-primary${BILLING.on ? "" : " soon"}" ${S.payBusy ? "disabled" : ""} onclick="App.buyPlan()">
      ${S.payBusy ? "결제 확인 중…" : (BILLING.on ? "구글 플레이로 결제" : "결제 준비 중")}</button></div>
    <p class="mp-hint">자동 갱신 없음 · 구글 플레이 결제 · <b>카드번호는 저희 서버에 저장하지 않습니다</b></p>`;
  },

  // ── 요청28 ① 학교생활 서류 — 진입은 "상황 선택" ──────────
  // 엄마가 서류 이름을 몰라도 되게. 상황만 고르면 맞는 서류로 보낸다.
  /* ── 8. 서류 (2026-07-28 재설계) ─────────────────────────
     흰 카드 4개 + 회색 안내문 두 덩이였다. 여기서 급한 건 하나뿐 —
     **보고서 미제출**은 안 내면 미인정 결석이 된다. 그건 맨 위에 경고로 세우고,
     나머지(남은 일수·서식 고르기)는 조용한 목록으로 내렸다. */
  docs: () => {
    const c = cur();
    const R = STUB.docRules;
    const left = R.fieldQuotaDays - R.fieldUsedDays;
    const pending = STUB.documents.filter((d) => d.kind === "field" && !d.reported);
    return `
    ${subHeader("서류", "체험학습 · 출결")}

    ${pending.map((d) => {
      const dleft = R.fieldReportWithin - d.endedDaysAgo;   // 실시 후 7일 이내
      return `
      <!-- 미제출은 «미인정 결석»으로 바뀌는 사안이라 기한을 숫자로 세운다(실제 서식 명시) -->
      <button class="dc-alert ${dleft <= 3 ? "hot" : ""}" onclick="App.docStart('field','report',${d.id})">
        <span class="dc-dday">D-${dleft}</span>
        <span class="dc-at">
          <b>보고서 안 냄</b>
          <em>${esc(d.title)} · ${fmtDate(d.from)}~${fmtDate(d.to)}</em>
          <i>안 내면 미인정 결석</i>
        </span>
        <span class="mp-go"><i aria-hidden="true" class="ti ti-chevron-right"></i></span>
      </button>`;
    }).join("")}

    <div class="mp-sec">올해 교외체험학습</div>
    <div class="dc-quota">
      <div class="qbar"><span style="width:${(R.fieldUsedDays / R.fieldQuotaDays) * 100}%"></span></div>
      <div class="dc-qt"><b>${left}일 남음</b><span>${R.fieldUsedDays} / ${R.fieldQuotaDays}일</span></div>
    </div>

    <div class="mp-sec">서식 만들기</div>
    <div class="mp-list">
      ${STUB.docSituations.map((s) => `
        <button class="mp-row two" onclick="App.docStart('${s.key}','apply')">
          <!-- 아이콘은 docSituations 에 이미 정의돼 있었는데 여기서 안 꺼내 쓰고 있었다(2026-08-03) -->
          <span class="mp-i">${s.icon}</span>
          <span class="mp-l">${esc(s.label)}<em>${esc(String(s.desc).split(String.fromCharCode(10)).join(" · "))}</em></span>
          <span class="mp-go"><i aria-hidden="true" class="ti ti-chevron-right"></i></span>
        </button>`).join("")}
    </div>

    <p class="mp-hint">${[schoolName(c), "2026학년도 기준"].filter(Boolean).map(esc).join(" ")} · 학교마다 달라 참고용이에요</p>`;
  },

  // 서류 작성 — 아이 정보는 자동, 엄마는 날짜·사유만.
  // 필드는 실제 학교 양식(hwp 4종)에서 그대로 옮겼다.
  "doc-form": () => {
    const c = curView();
    const d = S.docDraft;
    const R = STUB.docRules;
    const k = S.docKind, isReport = S.docPhase === "report";
    const days = d.days ?? 3;

    const auto = `
      <div class="card autofill">
        <b style="font-size:13px">자동으로 채웠어요</b>
        <div class="afrow"><span>학교</span><b>${esc(schoolName(c))}</b></div>
        <div class="afrow"><span>학년·반</span><b>${c.grade}학년 ${c.class_name}반</b></div>
        <div class="afrow"><span>이름</span><b>${esc(c.nickname)} <span class="todo">실명은 상세에서</span></b></div>
        <div class="afrow"><span>보호자</span><b>${esc(STUB.me.account.display_name)}</b></div>
      </div>`;

    const period = (label, note) => `
      <label class="f">${label} *</label>
      <div class="row" style="margin-top:0">
        <input type="date" value="${d.from || "2026-08-24"}" oninput="S.docDraft.from=this.value;App.docDays()">
        <input type="date" value="${d.to || "2026-08-26"}" oninput="S.docDraft.to=this.value;App.docDays()">
      </div>
      <p class="sub">기간 중 <b>${days}일간</b> — ${note}</p>`;

    // ── 교외체험학습 신청서 ─────────────────────────────
    const fieldApply = () => {
      const left = R.fieldQuotaDays - R.fieldUsedDays;
      const overRun = days > R.fieldMaxRun;
      const needSafety = days > R.fieldSafetyOver;
      const overQuota = days > left;
      return `
      ${auto}
      <div class="card">
        <label class="f">성별 *</label>
        <div class="segline">${["남", "여"].map((g) =>
          `<button class="${d.sex === g ? "on" : ""}" onclick="App.docSet('sex','${g}')">${g}</button>`).join("")}</div>
        <label class="f">주소 *</label><input id="doc-place" placeholder="예: 서울 관악구 …" value="${esc(d.addr)}" oninput="S.docDraft.addr=this.value">
        ${period("기간", "공휴일·자율휴업일을 뺀 <b>결석하는 날 수</b>만 셉니다")}

        ${overQuota ? `<p class="warnline"><i class='ti ti-alert-triangle'></i> 올해 남은 일수(${left}일)를 넘습니다 — 초과분은 <b>미인정 결석</b>이에요.</p>` : ""}
        ${overRun ? `<p class="warnline"><i class='ti ti-alert-triangle'></i> 연속 ${R.fieldMaxRun}일을 넘을 수 없어요.</p>` : ""}

        <label class="f">장소 * <span class="sdesc" style="display:inline">시·도까지 적어요</span></label>
        <input id="doc-dest" placeholder="예: 경상북도 경주시" value="${esc(d.place)}" oninput="S.docDraft.place=this.value">

        <label class="f">보호자 동행 확인 *</label>
        <div class="segline">${["예", "아니오"].map((v) =>
          `<button class="${d.accompany === v ? "on" : ""}" onclick="App.docSet('accompany','${v}')">${v}</button>`).join("")}</div>
        ${d.accompany === "아니오"
          ? `<p class="warnline"><i class='ti ti-alert-triangle'></i> 보호자(또는 친족 성인) 동행이 없으면 <b>허가되지 않습니다</b>.</p>`
          : `<p class="sub">보호자·친권자·후견인 또는 친족 성인이 함께 가야 해요.</p>`}

        ${needSafety ? `
          <!-- 연속 5일 초과 시에만 나타나는 칸 — 실제 양식도 이 조건일 때만 쓴다 -->
          <div class="condbox">
            <b style="font-size:13px">연속 ${R.fieldSafetyOver}일을 넘어서 추가로 필요해요</b>
            <label class="check"><input type="checkbox" ${d.safety ? "checked" : ""} onchange="App.docSet('safety',this.checked)">
              <span>기간 중 1회 이상 아이가 담임 선생님께 연락하겠습니다</span></label>
            <label class="f">상시 연락 가능한 비상 연락처 *</label>
            <input inputmode="numeric" placeholder="010-0000-0000" value="${esc(d.emergency)}" oninput="S.docDraft.emergency=this.value">
          </div>` : ""}

        <label class="f">학습계획 * <span class="sdesc" style="display:inline">날짜별로 구체적으로</span></label>
        <!-- 한 줄짜리 칸이라 긴 계획을 못 적었다(2026-07-31 지적). 여러 줄 칸으로 바꾸고,
             적는 만큼 칸이 저절로 늘어난다(autoGrow). 학교 양식도 여러 줄로 쓰는 자리다. -->
        ${(d.planDays || []).map((p, i) => `
          <div class="planrow tall">
            <b>${p.date}</b>
            <textarea id="docplan-${i}" rows="2" placeholder="그 날 무엇을 배울지 — 길게 적어도 돼요"
              oninput="App.docPlan(${i}, this.value); autoGrow(this)">${esc(p.text)}</textarea>
          </div>`).join("") || `<p class="sub">기간을 고르면 날짜별 칸이 생겨요.</p>`}

        <div class="check"><input type="checkbox" id="dc" checked><label for="dc">위 내용이 사실임을 보호자가 확인합니다</label></div>
        <div style="margin-top:14px"><button class="btn-primary" onclick="App.docPreview()">미리보기</button></div>
      </div>
      <p class="notice"><i class='ti ti-pin'></i> 실시 <b>${R.fieldApplyBefore}일 전까지</b> 담임 선생님께 내야 해요 ·
        다녀온 뒤 <b>${R.fieldReportWithin}일 이내</b>에 보고서까지 내야 출석으로 인정됩니다.</p>`;
    };

    // ── 교외체험학습 보고서 ─────────────────────────────
    const fieldReport = () => `
      ${auto}
      <div class="card">
        ${period("학습일시", "신청서에 적은 기간이 그대로 들어왔어요")}
        <label class="f">체험학습 내용 *</label>
        <textarea rows="6" placeholder="교육활동이 드러나게 자세히&#10;예: 성산일출봉에서 화산 지형을 관찰하고…"
          oninput="S.docDraft.did=this.value">${esc(d.did)}</textarea>
        <div class="check"><input type="checkbox" id="dc" checked><label for="dc">위와 같이 체험학습을 하였음을 보고합니다</label></div>
        <div style="margin-top:14px"><button class="btn-primary" onclick="App.docPreview()">미리보기</button></div>
      </div>
      <p class="notice"><i class='ti ti-pin'></i> 실시 후 <b>${R.fieldReportWithin}일 이내</b> 제출 — 넘기면 <b class="bad">미인정 결석</b>으로 처리됩니다.</p>`;

    // ── 결석신고서 ─────────────────────────────────────
    const absence = () => {
      const kinds = [
        ["sick", "질병"], ["official", "출석인정"], ["family", "경조사"], ["etc", "기타"], ["none", "미인정"],
      ];
      const t = d.absKind || "sick";
      const needCert = t === "sick" && days > R.sickCertOver;
      return `
      ${auto}
      <div class="card">
        <label class="f">성별 *</label>
        <div class="segline">${["남", "여"].map((g) =>
          `<button class="${d.sex === g ? "on" : ""}" onclick="App.docSet('sex','${g}')">${g}</button>`).join("")}</div>

        ${period("결석 기간", "주말·공휴일을 뺀 <b>실제 결석한 날 수</b>")}

        <label class="f">결석 종류 *</label>
        <div class="chips">${kinds.map(([v, n]) =>
          `<button class="chip ${t === v ? "on" : ""}" onclick="App.docSet('absKind','${v}')">${n}</button>`).join("")}</div>

        ${t === "sick" ? `
          <p class="${needCert ? "warnline" : "sub"}">${needCert
            ? `<i class='ti ti-alert-triangle'></i> ${days}일이면 <b>의사 진단서 또는 의견서</b>가 필요해요 — 약봉투·처방전은 인정되지 않습니다.`
            : `${R.sickCertOver}일 이내라 처방전·약봉투·진료확인서 또는 담임 확인으로 됩니다.`}</p>` : ""}

        ${t === "family" ? `
          <label class="f">경조사 종류 *</label>
          <select onchange="App.docSet('family',this.value)">
            <option value="">고르세요</option>
            ${STUB.familyEvents.map((f) => `<option value="${esc(f.label)}" ${d.family === f.label ? "selected" : ""}>${esc(f.label)} — ${f.days}일</option>`).join("")}
          </select>
          <p class="sub">증빙: 청첩장·부고장 등</p>` : ""}

        ${t === "official" ? `<p class="sub">감염병(진단서·소견서·진료확인서) · 학생선수(공문·훈련계획서) · 생리통(월 1회) · 천재지변 등</p>` : ""}
        ${t === "none" ? `<p class="warnline"><i class='ti ti-alert-triangle'></i> 미인정 결석입니다. 연속 3일 이상이면 학교가 보호자·학생 면담, 가정방문 등으로 소재를 확인합니다.</p>` : ""}

        <label class="f">결석 사유 * <span class="sdesc" style="display:inline">병명·사유를 구체적으로</span></label>
        <!-- 한 줄 칸이면 «구체적으로»라고 해놓고 길게 못 적는다(2026-07-31) -->
        <textarea id="doc-reason" class="grow" rows="2" placeholder="예: 급성 장염으로 3일간 통원 치료"
          oninput="S.docDraft.reason=this.value; autoGrow(this)">${esc(d.reason)}</textarea>
        <label class="f">증빙 서류</label>
        <input id="doc-proof" placeholder="예: 진단서 · 진료확인서 · 처방전" value="${esc(d.proof)}" oninput="S.docDraft.proof=this.value">

        <div class="check"><input type="checkbox" id="dc" checked><label for="dc">위와 같이 결석신고서를 제출합니다</label></div>
        <div style="margin-top:14px"><button class="btn-primary" onclick="App.docPreview()">미리보기</button></div>
      </div>
      <p class="notice"><i class='ti ti-pin'></i> 결석일부터 <b>${R.absenceWithin}일 이내</b>에 증빙과 함께 내야 해요 —
        넘기면 <b class="bad">미인정 결석</b>으로 처리됩니다.</p>`;
    };

    // ── 학부모 상담 신청서 ──────────────────────────────
    const counsel = () => {
      const hours = STUB.counselHours[c.grade] || "";
      const w = d.wish || [{}, {}, {}];
      return `
      ${auto}
      <div class="card">
        <label class="f">보호자 연락처 *</label>
        <input inputmode="numeric" placeholder="010-0000-0000" value="${esc(d.phone)}" oninput="S.docDraft.phone=this.value">
        <label class="f">학생과의 관계 *</label>
        <input id="doc-rel" placeholder="예: 모" value="${esc(d.relation)}" oninput="S.docDraft.relation=this.value">

        <div class="condbox">
          <b style="font-size:13px">${c.grade}학년 상담 가능 시간</b>
          <p class="sub">${hours}<br>학교 안전 관리로 <b>야간 상담은 하지 않습니다</b>.</p>
        </div>

        <label class="f">희망 시간 * <span class="sdesc" style="display:inline">3개까지 적으면 조율이 쉬워요</span></label>
        ${[0, 1, 2].map((i) => `
          <div class="wishrow">
            <b>${i + 1}희망</b>
            <input id="doc-when" placeholder="예: 9/4 (목) 15:00" value="${esc(w[i]?.when)}" oninput="App.docWish(${i},'when',this.value)">
            <div class="segline sm">${["대면", "비대면"].map((m) =>
              `<button class="${w[i]?.how === m ? "on" : ""}" onclick="App.docWish(${i},'how','${m}')">${m}</button>`).join("")}</div>
          </div>`).join("")}

        <label class="f">상담 내용 *</label>
        <textarea rows="5" placeholder="상담 이유와 자녀에 관한 의견"
          oninput="S.docDraft.note=this.value">${esc(d.note)}</textarea>

        <div style="margin-top:14px"><button class="btn-primary" onclick="App.docPreview()">미리보기</button></div>
      </div>
      <p class="notice"><i class='ti ti-pin'></i> 담임 선생님이 확정하면 <b>상담 확정 통보서</b>로 시간·장소를 알려줍니다.</p>`;
    };

    const body = k === "field" ? (isReport ? fieldReport() : fieldApply())
      : k === "absence" ? absence() : counsel();

    return `
    <a class="back" href="#docs" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 style="margin-top:8px">${docTitle()}</h1>
    ${body}`;
  },

  // 미리보기 = 학교에 낼 종이 그대로. 한 화면에 한 장이 통째로 들어온다(2026-07-25 지시).
  "doc-preview": () => `
    <div class="pvbar">
      <a class="back" href="#doc-form" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
      <b>${docTitle()}</b>
      <button class="iconbtn ghosticon" onclick="App.docZoom()" aria-label="${S.docZoom ? "화면에 맞추기" : "크게 보기"}">
        <i class='ti ${S.docZoom ? "ti-zoom-out" : "ti-zoom-in"}'></i></button>
    </div>

    <div class="docview ${S.docZoom ? "zoomed" : ""}" id="docview">
      <div class="page" id="docpage">${docPaper()}</div>
    </div>

    <div class="pvfoot">
      <button class="btn-line" onclick="toast('인쇄·PDF 저장은 기기 기능을 씁니다')"><i class='ti ti-printer'></i> 출력 · PDF 저장</button>
      <button class="btn-primary" onclick="App.docSave()">기록으로 남기기</button>
    </div>`,

  // ── 요청28 ② 부모 → 자녀 원터치 알림 ─────────────────────
  /* ── 9. 알림 (2026-07-28 재설계) ──────────────────────────
     흰 카드 5개가 같은 무게로 쌓여 있었다. 실제로 여기서 하는 일은 딱 둘이다 —
     **아이에게 보내기**와 **나에게 오는 알림 시각**. 그 둘을 위로 올리고
     기기 등록·보낸 내역은 아래로 내렸다. 안내문(「~해요」)은 전부 뺐다. */
  notify: () => {
    const c = curView();
    const sent = STUB.notices.slice().reverse().filter((n) => n.from === "parent");
    return `
    ${subHeader("대화 · 알림")}

    <div class="mp-sec">${c.nickname ? esc(c.nickname) + "에게 보내기" : "아이에게 보내기"}</div>
    <div class="nt-send">
      <input id="nt" placeholder="아이에게 보낼 말" value="${esc(S.noticeText)}"
             oninput="S.noticeText=this.value" onkeydown="if(event.key==='Enter')App.sendNotice()">
      <button class="nt-go" onclick="App.sendNotice()"><i aria-hidden="true" class="ti ti-send"></i>보내기</button>
    </div>
    <div class="nt-presets">
      ${STUB.noticePresets.map((p) => `<button onclick="App.sendNotice('${jsq(p)}')">${p}</button>`).join("")}
    </div>

    <div class="mp-sec">나에게 오는 알림</div>
    <div class="mp-list">
      <label class="mp-row">
        <span class="mp-l">매일 알림<em>저녁 준비물 · 아침 하루</em></span>
        <input type="checkbox" ${S.remind.on ? "checked" : ""} onchange="App.remindToggle(this.checked)">
        <i class="mp-swt"></i>
      </label>
      ${S.remind.on ? `
      <label class="mp-row"><span class="mp-l">저녁</span>
        <input class="mp-time" type="time" value="${S.remind.evening}" onchange="App.remindTime('evening',this.value)"></label>
      <label class="mp-row"><span class="mp-l">아침</span>
        <input class="mp-time" type="time" value="${S.remind.morning}" onchange="App.remindTime('morning',this.value)"></label>` : ""}
    </div>

    ${sent.length ? `
    <div class="mp-sec">보낸 알림</div>
    <div class="mp-list">
      ${sent.map((n) => `
        <div class="nt-row">
          <span class="nt-t">${esc(n.text)}<em>${esc(n.at)}</em></span>
          <span class="nt-s ${n.seen ? "seen" : ""}">${n.seen ? "확인함" : "보냄"}</span>
        </div>`).join("")}
    </div>` : ""}

    <div class="mp-sec">이 기기</div>
    <div class="mp-list">
      <button class="mp-row" onclick="App.pushRegister()">
        <span class="mp-l">푸시 받기</span>
        <span class="mp-v">${S.pushToken ? "켜짐" : "꺼짐"}</span>
        ${S.pushToken ? "" : `<span class="mp-go"><i aria-hidden="true" class="ti ti-chevron-right"></i></span>`}
      </button>
      ${S.pushToken && DEV_TOOLS ? `<div class="tokenbox" onclick="App.copyToken()">${esc(S.pushToken)}</div>` : ""}
    </div>

    ${DEV_TOOLS ? `<div class="card devtool">
      <label class="check"><input type="checkbox" ${S.childView ? "checked" : ""} onchange="App.toggleChildView()">
        <span>자녀 화면으로 보기 <b class="stub">개발용</b></span></label>
    </div>` : ""}`;
  },

  // 자녀 뷰 = 제한 사용자. 알림 받기 + 자기 시간표·급식만. 결제·삭제·형제정보 없음.
  /* ── 자녀: 시간표·오늘 점심 (지시서 0802-3 1-2) ─────────────
     부모 학교 탭을 재사용하지 않는다 — 오늘/내일만, 교시 목록 + 점심 카드. */
  childtt: () => {
    const tomorrow = S.kidTTDay === "tomorrow";
    const day = tomorrow ? ymdPlus(TODAY, 1) : TODAY;
    const wd = new Date(`${day.slice(0,4)}-${day.slice(4,6)}-${day.slice(6)}`).getDay();
    const col = wd - 1;
    const grid = ttOf()?.grid || [];
    const subs = (col >= 0 && col <= 4)
      ? grid.map((row) => String(row?.[col] || "").trim()).filter(Boolean) : [];
    const meal = mealsOf().find((m) => m.date === day && m.type === "중식");
    const nowMin = new Date().getHours() * 60 + new Date().getMinutes();
    const lunchAt = S.lunchAfter ?? 4;   // 점심은 n교시 뒤(부모 설정 공유값)
    const seg = (key, nm) => `<button class="${S.kidTTDay === key ? "on" : ""}"
      onclick="S.kidTTDay='${key}';App.render()">${nm}</button>`;
    const row = (i, name) => {
      const pd = STUB.periods[i];
      const now = !tomorrow && pd && nowMin >= toMin(pd.start) && nowMin < toMin(pd.end);
      return `<div class="kd2-p ${now ? "now" : ""}"><i>${i + 1}</i><b>${esc(shortSubject(name))}</b>
        <span>${now ? "지금" : esc(pd?.start || "")}</span></div>`;
    };
    const lunchCard = meal ? `
      <div class="kd2-lunch mid"><span class="ic"><i aria-hidden="true" class="ti ti-tools-kitchen-2"></i></span>
        <span class="tx"><b>${tomorrow ? "내일" : "오늘"} 점심</b>
        <span>${meal.dishes.slice(0, 3).map((x) => esc(x.name)).join(" · ")}</span></span></div>` : "";
    return `
    <a class="back" href="#game" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 class="kd2-h1">시간표</h1>
    <div class="kd2-seg">${seg("today", "오늘")}${seg("tomorrow", "내일")}</div>
    ${subs.length ? `
      <div class="kd2-tt">
        ${subs.slice(0, lunchAt).map((s, i) => row(i, s)).join("")}
        ${lunchCard}
        ${subs.slice(lunchAt).map((s, i) => row(i + lunchAt, s)).join("")}
      </div>`
      : `${lunchCard}<p class="kd2-sub" style="margin-top:14px">${tomorrow ? "내일은" : "오늘은"} 수업이 없어요</p>`}`;
  },

  /* ── 자녀: 급식 평가 — 묻는 건 둘뿐(2026-08-02 재설계 2) ─────────
     ① 오늘 급식 별 몇 개  ② 그중 제일 맛있던 것 하나. **탭 두 번이면 끝난다.**

     앞 판은 어른 기준이었다 — 메뉴가 위아래로 두 번 나오고(회색 칩 + 순서 칩),
     한 화면에서 두 가지 일을 시키고, 다섯 개를 순서대로 매기게 했다.
     여덟 살에게 판단 다섯 번은 숙제다. 3~5등은 어차피 대충 찍어서 데이터도 지저분해진다.
     → 메뉴 목록은 **고르는 카드 하나로 합치고**, 순위는 1등만 받는다. */
  childmealrate: () => {
    const meal = mealsOf().find((m) => m.date === TODAY && m.type === "중식");
    if (!meal) { location.hash = "#game"; return ""; }
    const d = S.mealDraft;
    return `
    <a class="back" href="#game" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 class="kd2-h1">오늘 급식 어땠어?</h1>

    <p class="kd2-starhint">${d.stars ? "" : "별을 눌러서 골라줘"}</p>
    <div class="kd2-stars" role="group" aria-label="별점">
      ${[1, 2, 3, 4, 5].map((n) => `
        <button class="${d.stars >= n ? "on" : ""}" onclick="S.mealDraft.stars=${n};App.render()"
          aria-label="별 ${n}개">★</button>`).join("")}
    </div>

    <div class="kd2-q2">제일 맛있던 건?</div>
    <div class="kd2-pick1">
      ${meal.dishes.map((x) => `
        <button class="${d.best === x.name ? "on" : ""}"
          onclick="S.mealDraft.best = S.mealDraft.best === '${jsq(x.name)}' ? null : '${jsq(x.name)}';App.render()">
          <i></i><b>${esc(x.name)}</b>
        </button>`).join("")}
    </div>

    <button class="kd2-cta" ${d.stars && !S.mealBusy ? "" : "disabled"} onclick="App.mealRateSubmit()">
      ${S.mealBusy ? "보내는 중…" : `<i aria-hidden="true" class="ti ti-send"></i>보내기`}</button>`;
  },

  /* ── 자녀: 오늘 제일 재밌었던 과목? (2026-08-02) ────────────────
     일일 퀘스트 셋째. 시간표가 이미 있으니 **고르기만** 하면 된다.
     부모 리포트에서 값어치가 가장 큰 축 — 「우리 애가 수학을 재밌어한다」는
     성적표가 알려주지 않는 것이다. 과목은 주 단위로 반복돼서 한 달이면 표본이 충분하다. */
  childsubject: () => {
    const subs = todaySubjects();
    if (!subs.length) { location.hash = "#game"; return ""; }
    return `
    <a class="back" href="#game" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 class="kd2-h1">오늘 제일 재밌었던 건?</h1>

    <div class="kd2-pick1" style="margin-top:22px">
      ${subs.map((n) => `
        <button class="${S.subjectBest === n ? "on" : ""}"
          onclick="S.subjectBest = S.subjectBest === '${jsq(n)}' ? null : '${jsq(n)}';App.render()">
          <i></i><b>${esc(n)}</b>
        </button>`).join("")}
    </div>

    <button class="kd2-cta" ${S.subjectBest && !S.subjectBusy ? "" : "disabled"}
      onclick="App.subjectSubmit()">${S.subjectBusy ? "보내는 중…" : `<i aria-hidden="true" class="ti ti-send"></i>보내기`}</button>`;
  },

  /* ── 자녀: 오늘 누구랑 놀았어? (2026-08-02) ─────────────────────
     부모는 아이 교우관계를 모른다 — 아이가 먼저 말하지 않는다. 그런데 이건
     **부모가 제일 알고 싶어 하는 것**이다. 그래서 이름을 받는다.

     받는 건 **이름 문자열 하나뿐**이다(성별·연락처·학교 아무것도 안 받는다).
     타이핑은 **처음 한 번뿐** — 넣어두면 다음부터 칩으로 떠서 탭만 하면 된다.
     여러 명 고를 수 있고, 「혼자 놀았어」도 답이다(그것도 부모가 알아야 할 신호다). */
  childfriend: () => {
    const d = S.friendDraft;
    return `
    <a class="back" href="#game" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 class="kd2-h1">오늘 누구랑 놀았어?</h1>
    <p class="kd2-sub">여러 명 골라도 돼요</p>

    <div class="kd2-friends">
      ${S.friends.map((n) => `
        <button class="${d.picked.includes(n) ? "on" : ""}" onclick="App.friendTap('${jsq(n)}')">
          ${esc(n)}</button>`).join("")}
      <button class="add" onclick="App.friendAddStart()">＋ 새 친구</button>
    </div>

    <button class="kd2-alone ${d.alone ? "on" : ""}" onclick="App.friendAlone()">
      <i></i>오늘은 혼자 놀았어
    </button>

    ${d.adding === null ? "" : `
    <div class="modal sheetwrap" onclick="App.friendAddCancel()">
      <div class="sheet" onclick="event.stopPropagation()">
        <div class="sheet-grip"></div>
        <div class="sheet-hd"><b>친구 이름</b><span>부르는 대로 적어도 돼요</span></div>
        <input class="sheet-name" id="fr-add" maxlength="10" placeholder="예: 서연"
               value="${esc(d.adding)}" oninput="S.friendDraft.adding=this.value"
               onkeydown="if(event.key==='Enter')App.friendAddSave()">
        <div class="sheet-act nodel" style="grid-template-columns:1fr">
          <button class="act-save" onclick="App.friendAddSave()">넣기</button>
        </div>
      </div>
    </div>`}

    <button class="kd2-cta" ${(d.picked.length || d.alone) && !S.friendBusy ? "" : "disabled"}
      onclick="App.friendSubmit()">${S.friendBusy ? "보내는 중…" : `<i aria-hidden="true" class="ti ti-send"></i>보내기`}</button>`;
  },

  /* ── 자녀: 화면 고르기 (첫 실행 + 「화면 바꾸기」) ────────────
     12벌을 손으로 적지 않는다 — KID_THEMES 에서 뽑는다. 하나 늘려도 여기는 안 고친다.
     ⚠ 미리보기 칸에 data-kid-theme 을 박아서 **그 테마 색이 실제로 보이게** 한다.
        이름만 늘어놓으면 여덟 살은 못 고른다. */
  childtheme: () => `
    <h1 class="kd2-h1">내 화면 고르기</h1>
    <p class="kd2-sub">나중에 언제든 바꿀 수 있어요</p>
    <div class="kd2-picks">
      ${Object.entries(KID_THEMES).map(([k, t]) => `
        <button class="kd2-pick ${S.kidTheme === k ? "on" : ""}" onclick="App.kidTheme('${jsq(k)}')">
          <span class="kd2-prev" data-kid-theme="${k}" data-kid-accent="${k}">
            <i class="pv-star">★ 37</i>
            <i class="pv-card"><b></b><em></em></i>
            <i class="pv-btn"></i>
          </span>
          <b>${esc(t.name)}</b>
        </button>`).join("")}
    </div>`,

  /* ── 자녀: 별의 길 ─────────────────────────────────────────
     ⚠ 이 화면은 2026-08-03에 **실수로 통째로 지워졌다가 복구된 것**이다.
        테마 고르기를 12벌용으로 갈아끼울 때 잘라낼 범위를 «다음 `},`»로 잡았는데,
        childtheme 은 `,` 로 끝나서 그 뒤 childboard 의 `},` 가 잡혔다.
        범위를 줄 번호가 아니라 «다음 스크린 이름»으로 잡으면 이런 일이 안 난다.
     색 12벌이 되면서 격자판 갈래는 없앴다 — 판이 둘이면 색만 바꿔도 화면이 달라 보인다. */

  /* ── 자녀: 사진 인증 ── */
  childshoot: () => {
    const m = (S.missions || []).find((x) => x.id === S.kidShootId);
    if (!m) { location.hash = "#game"; return ""; }
    return `
    <a class="back" href="#game" aria-label="뒤로"><i aria-hidden="true" class="ti ti-chevron-left"></i></a>
    <h1 class="kd2-h1">${esc(m.title)}</h1>
    <p class="kd2-sub">${"하는 모습을 찍어서 보여주세요"}</p>
    <button class="kd2-shot" onclick="App.missionShoot(${m.id})" ${S.missionBusy === m.id ? "disabled" : ""}>
      <span class="lens"><i aria-hidden="true" class="ti ti-camera"></i></span>
      <b>${S.missionBusy === m.id ? "보내는 중…" : "눌러서 찍기"}</b>
    </button>`;
  },

  /* ── 자녀: 연결이 끝났을 때 (2026-08-02 구멍 2-2) —
     토큰이 만료됐거나 부모님이 끊었다. 아이 눈높이로, 잘못한 게 아니라고 말해준다. */
  childlocked: () => `
    <div class="kd2-end">
      <span class="ic"><i aria-hidden="true" class="ti ti-clock"></i></span>
      <h1 class="kd2-h1">지금은 쉬는 중이에요</h1>
      <p class="kd2-sub"><b>엄마아빠에게 말해주면</b> 다시 열려요</p>
    </div>`,

  childexpired: () => `
    <div class="kd2-end">
      <span class="ic"><i aria-hidden="true" class="ti ti-link"></i></span>
      <h1 class="kd2-h1">연결이 끝났어요</h1>
      <p class="kd2-sub">부모님 폰에서 <b>새 코드</b>를 받아요</p>
      <button class="kd2-cta" onclick="S.childLinkEnded=false;S.linkCode='';location.hash='#childlink';App.render()">새 코드 넣기</button>
    </div>`,

  /* ── 자녀 홈 = 오늘 카드 «덱» (2026-08-03 개편) ────────────────
     이전엔 질문 카드가 세로로 줄줄이 서 있어서 설문지처럼 읽혔다("연구 직원이 쓰는 화면 같아").
     목록은 **훑는 것**이고 덱은 **해치우는 것**이다 — 부모 화면(목록)과 아이 화면을
     구조로 가른다. 색만 다른 같은 화면이던 문제의 뿌리가 여기였다.

     · 한 번에 한 장. 뒤에 남은 장이 겹쳐 보여서 **숫자를 안 읽어도 몇 개 남았는지 안다**
     · 끝낸 것·기다리는 것은 덱에서 빠진다. 다 하면 「오늘 끝!」 한 장
     · 탭(일일/의뢰) 폐기 → 카드마다 「바로 별」/「엄마 확인」 배지.
       탭은 눌러봐야 알지만 배지는 그 카드를 볼 때 같이 읽힌다
     ⚠ 덱만 갈아끼웠다. 아래 준비물·엄마 말·오늘 하루는 그대로 둔다 —
        그건 질문이 아니라 참고할 것이라 목록이 맞다. */
};

/* ═══ 길게 누르기 = 메뉴 (2026-07-26 지시) ═══════════════
   안드로이드 홈화면에서 아이콘을 꾹 누르면 설정이 뜨는 그 방식.
   작은 항목마다 «⋯» 버튼을 달면 화면이 지저분해지고 손가락으로 누르기도 어렵다.
   길게 누르면 뜨게 하면 화면은 깨끗하고, 쓸 사람은 다 안다.

   ⚠ 스크롤과 싸우지 않게 만든다 — 손가락이 10px 넘게 움직이면 «스크롤 중»으로 보고 취소한다.
     그리고 길게 눌러 메뉴가 뜨면 뒤이어 오는 click은 삼킨다(안 그러면 메뉴 뜨고 화면도 넘어간다). */
const HOLD_MS = 450, HOLD_SLOP = 10;
let holdTimer = null, holdFired = false;

function holdStart(e, title, actions) {
  clearTimeout(holdTimer);
  holdFired = false;
  const x0 = e.clientX, y0 = e.clientY;
  const cancel = () => { clearTimeout(holdTimer); document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); };
  const move = (ev) => { if (Math.abs(ev.clientX - x0) > HOLD_SLOP || Math.abs(ev.clientY - y0) > HOLD_SLOP) cancel(); };
  const up = () => cancel();
  document.addEventListener("pointermove", move);
  document.addEventListener("pointerup", up);
  holdTimer = setTimeout(() => {
    cancel();
    holdFired = true;
    if (navigator.vibrate) navigator.vibrate(12);      // 눌렸다는 손끝 신호
    S.holdMenu = { title, actions };
    App.render();
  }, HOLD_MS);
}
/* 길게 누르면 메뉴 없이 **바로 실행** — 달력 날짜처럼 할 일이 하나뿐인 자리용(2026-08-03) */
function holdDirect(e, fn) {
  clearTimeout(holdTimer);
  holdFired = false;
  const x0 = e.clientX, y0 = e.clientY;
  const cancel = () => { clearTimeout(holdTimer); document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); };
  const move = (ev) => { if (Math.abs(ev.clientX - x0) > HOLD_SLOP || Math.abs(ev.clientY - y0) > HOLD_SLOP) cancel(); };
  const up = () => cancel();
  document.addEventListener("pointermove", move);
  document.addEventListener("pointerup", up);
  holdTimer = setTimeout(() => {
    cancel();
    holdFired = true;
    if (navigator.vibrate) navigator.vibrate(12);
    fn();
  }, HOLD_MS);
}
// 길게 눌러 메뉴가 떴으면 이어지는 click은 무시한다
const holdGuard = () => { if (holdFired) { holdFired = false; return true; } return false; };

function pwAskView() {
  const a = S.pwAsk;
  if (!a) return "";
  return `
  <div class="modal">
    <div class="modal-card">
      <b style="font-size:15px"><i class='ti ti-lock'></i> ${esc(a.reason)}</b>
      <p class="sub">계속하려면 비밀번호를 한 번 더 확인해요.</p>
      <input id="pw-ask" type="password" placeholder="비밀번호" value="${esc(a.value)}"
             oninput="App.pwAskSet(this.value)" onkeydown="if(event.key==='Enter')App.pwAskDone(true)">
      <div class="row">
        <button class="btn-ghost" onclick="App.pwAskDone(false)">취소</button>
        <button class="btn-primary" onclick="App.pwAskDone(true)">확인</button>
      </div>
    </div>
  </div>`;
}

function holdMenuView() {
  const h = S.holdMenu;
  if (!h) return "";
  return `
  <div class="modal" onclick="App.holdClose()">
    <div class="modal-card" onclick="event.stopPropagation()">
      <b style="font-size:15px">${esc(h.title)}</b>
      <div class="holdlist">
        ${h.actions.map((a, i) => `
          <button class="${a.danger ? "danger" : ""}" onclick="App.holdRun(${i})">
            <i class="ti ${a.icon || "ti-pencil"}"></i> ${esc(a.label)}</button>`).join("")}
      </div>
      <div style="margin-top:10px"><button class="btn-ghost" style="width:100%" onclick="App.holdClose()">닫기</button></div>
    </div>
  </div>`;
}

// ── 상단 자녀 칩 ────────────────────────────────────────────
// 자녀 등록은 가입 직후에 끝난다 → 홈에 "아직 자녀가 없다면" 같은 안내를 둘 이유가 없다(2026-07-24 지적).
// 나중에 자녀를 더 넣는 건 자녀 전환(#switch)의 ＋ 카드와 마이페이지에서 한다.
/* 자녀 얼굴 — 사진이 있으면 사진, 없으면 이모지(2026-07-27).
   사진은 인증이 필요해서 hydrateImages() 가 나중에 채운다(data-rec). */
/* 자녀폰 미연결 + 사진 미션(2026-08-02 구멍 2-1) — 부모가 «아이가 안 하네»로
   오해하는 자리. 연결되면(child_device) 조건이 꺼져서 자동으로 사라진다. */
function childLinkWarn() {
  const c = cur();
  if (!c || c.child_device) return "";
  if (!(S.missions || []).some((m) => m.verify === "review" && m.status === "open")) return "";
  /* 한 줄짜리 경고가 미션 카드 안에서 도장 3칸을 밀어냈고, 파란 카드 안이라
     파란 알약처럼 보여 **경고로 안 읽혔다**(2026-08-03 폰 실기).
     늘 떠 있어야 할 말이 아니라 **궁금할 때 보는 말**이다 — 물음표 하나로 줄인다. */
  return `<button class="ms-linkq" onclick="App.linkWarnOpen()">자녀폰 미연결<i aria-hidden="true" class="ti ti-info-circle"></i></button>`;
}

function childFace(c, cls = "") {
  if (!c) return "";
  // photoLocal = 아직 서버에 안 올라간 사진(등록 직후 잠깐). 올라가면 photo 로 바뀐다.
  if (c.photoLocal) return `<span class="cface ${cls}"><img src="${c.photoLocal}" alt=""></span>`;
  return c.photo
    ? `<span class="cface ${cls}"><img src="${PLACEHOLDER}" data-rec="${c.photo}" alt=""></span>`
    : `<span class="cface ${cls} ini">${esc(initialOf(c))}</span>`;
}

function childChip() {
  const c = curView();
  return `<div class="childchip" onclick="location.hash='#switch'">
    ${childFace(c, "avatar")} ${esc(c.nickname)} <span class="hd-caret"><i aria-hidden="true" class="ti ti-chevron-down"></i></span>
  </div>`;
}
// ── 방과후 주간 타임그리드 ──────────────────────────────────
// h0~h1 = 방과후 시간대. px = 30분당 높이(이 값만 키우면 그리드가 길어진다).
/* ⚠ px 는 «30분»의 높이다. 30px 이면 한 시간이 60px — 블록에 이름 한 줄도 겨우 들어가
   「방과후 코딩」이 세 줄로 쪼개졌다(08-09 지적). 44 로 올려 한 시간 88px 로 본다. */
/* ⚠ 30 은 너무 촘촘(이름이 세 줄로 쪼개짐), 44 는 **너무 길다**(화면을 한참 내려야 한다).
   36 = 한 시간 72px. 이름 두 줄이 들어가면서 13~21시가 한 화면에 담긴다. */
const GRID = { h0: 13, h1: 21, px: 36 };
/* 일정 색 — 학원별로 구분하려고 사용자가 직접 고른다(2026-07-24 지시).
   ⚠ 값을 여기 적지 않는다(2026-07-28, 시안 10g). 파스텔 6종을 하드코딩해 뒀더니
      테마를 갈아도 이 색만 안 따라와서 어두운 테마에서 혼자 밝게 떴다.
      이제 **--tag1~5** 라는 변수 5개를 style.css 가 테마마다 정의하고, 여기선 이름만 부른다. */
const PLAN_COLORS = [1, 2, 3, 4, 5].map((n) => ({ v: `var(--tag${n})` }));
/* ⚠ color 가 없으면 전부 0번 색이 됐다 — 서버로 넣은 활동은 color 를 안 준다.
   그래서 수요일에 「방과후 코딩」과 「피아노 학원」이 같은 색으로 보였다(08-09 지적).
   → 색이 없으면 **이름으로 정한다.** 같은 학원은 언제나 같은 색이고, 다른 학원은 갈린다. */
const nameHue = (s0) => { let h = 0; for (const ch of String(s0 || "")) h = (h * 31 + ch.charCodeAt(0)) % 997; return h; };
/* ⚠ color 가 **0** 으로 들어온다(null 이 아니다) — 그래서 ?? 로는 못 걸러 전부 1번 색이었다.
   0 은 «안 골랐다»는 뜻이다. 사용자가 직접 고른 값은 1 이상이다.
   → 0·null·undefined 면 이름으로 정한다. 같은 학원은 언제나 같은 색이다. */
const planColor = (i, name) => PLAN_COLORS[(i > 0 ? i : nameHue(name)) % PLAN_COLORS.length];
/* 급식 종류 — 「어디가 뭔지 모르겠다」(2026-08-09 지적).
   밥·국·반찬·김치·후식이 전부 같은 모양이라 눈이 걸릴 곳이 없었다.
   ⚠ 이름만 보고 정한다(NEIS 가 종류를 안 준다). 못 맞히면 «반찬»으로 둔다 —
     틀린 이름표보다 «반찬»이 낫다. 억지로 분류하지 않는다. */
const MEAL_KIND = [
  { k: "rice",  ko: "밥",   re: /밥|면|국수|죽|떡국|파스타|리조또|비빔|덮밥|카레/ },
  { k: "soup",  ko: "국",   re: /국|탕|찌개|스프|수프/ },
  { k: "kimchi",ko: "김치", re: /김치|깍두기|장아찌|단무지|피클/ },
  { k: "des",   ko: "후식", re: /우유|요구르트|주스|음료|사과|바나나|수박|파인애플|토마토|배|귤|포도|멜론|푸딩|케이크|아이스|빵|떡$/ },
];
const mealKind = (name) => (MEAL_KIND.find((x) => x.re.test(String(name || ""))) || { k: "side", ko: "반찬" });
const toMin = (t) => +t.slice(0, 2) * 60 + +t.slice(3);
const toHHMM = (m) => String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
const gridTop = (t) => ((toMin(t) - GRID.h0 * 60) / 30) * GRID.px;
const snap10 = (m) => Math.round(m / 10) * 10;

// 빈 칸을 누르면 올라오는 입력 바. 값이 없으면 렌더하지 않는다.
function planBar() {
  const d = S.planDraft;
  if (!d) return "";
  /* 시안 10e (2026-07-28) — **아래에서 올라오는 시트(L3)**.
     화면 밑 가로바 시절엔 다이어리 블록에 가려 입력칸이 안 눌렸다(2026-07-25 실측).
     가운데 모달로 옮겼다가, 이번엔 시트로 내린다 — 손가락이 닿는 아래쪽에 버튼이 모인다.
     버튼 비율 삭제 1 : 취소 1 : 저장 2 는 7f 규칙 그대로다. */
  /* 방과후 «반쪽 시트» 폐지(2026-08-03 §4) — 전용 화면 Screens.editact 가 대신한다.
     이 함수는 render() 가 매 화면에 붙이는 자리라 **빈 문자열만 돌려준다.** */
  return "";
}

/* 일정 지우기 확인 — 시안 10f (L4 · 최상단).
   ⚠ 가림막을 눌러도 안 닫는다(onclick 없음). 되돌릴 수 없는 확인은 «스쳐서 사라지는» 창이면 안 된다.
      실제로 삭제 확인이 사진 뒤에 깔려 눌러도 아무 일 없어 보인 적이 있다(2026-07-27). */
function lunchSheet() {
  const d = S.lunchEdit;
  if (!d) return "";
  const max = Math.max(5, (ttOf().grid || []).length);
  return `
  <div class="modal sheetwrap" onclick="App.lunchCancel()">
   <div class="sheet" onclick="event.stopPropagation()">
    <div class="sheet-grip"></div>
    <div class="sheet-hd"><b>점심시간</b><span>학년마다 달라요</span></div>

    <div class="sheet-lbl">몇 교시 뒤</div>
    <div class="lunch-after">
      ${Array.from({ length: max }, (_, i) => i + 1).map((n) => `
        <button class="${d.after === n ? "on" : ""}" onclick="App.lunchAfter(${n})">${n}교시</button>`).join("")}
    </div>

    <div class="sheet-lbl">시각</div>
    <div class="sheet-two">
      <label><span>시작</span><input type="time" value="${d.start}" oninput="S.lunchEdit.start=this.value"></label>
      <label><span>끝</span><input type="time" value="${d.end}" oninput="S.lunchEdit.end=this.value"></label>
    </div>

    <div class="sheet-act nodel">
      <button class="act-cancel" onclick="App.lunchCancel()">취소</button>
      <button class="act-save" onclick="App.lunchSave()">저장</button>
    </div>
   </div>
  </div>`;
}

/* 진급 (2026-07-28 지시) — 학년이 바뀌는 **2~3월**에 앱이 먼저 말한다.
   ⚠ 학년은 **자동으로 올리고**, 반은 **물어본다.**
     학년은 시간이 정하니 틀릴 일이 없다. 반은 학교가 새로 짜므로 앱이 알 길이 없다 —
     모르는 값을 지어내면 시간표·급식이 통째로 남의 반 것이 된다.
   기준: 학년도가 바뀌었는데(3월 이후) 자녀 학년을 아직 안 올렸으면 뜬다. */
function needPromote(c) {
  if (!c || S.promoteDone?.includes(c.id)) return null;
  const y = +TODAY.slice(0, 4), m = +TODAY.slice(4, 6);
  if (m < 2 || m > 3) return null;                 // 2~3월에만
  const entry = c.entry_year || (y - (+c.grade - 1));
  const should = (m >= 3 ? y : y - 1) - entry + 1;  // 3월부터 새 학년
  const max = (c.school?.kind || "").startsWith("초") ? 6 : 3;
  if (should <= +c.grade || should > max) return null;
  return { id: c.id, from: +c.grade, to: should };
}
/* ── 「지금 뭐 하는 중」 (2026-07-28 지시) ─────────────────────
   시간표는 표일 뿐이다. 엄마가 궁금한 건 «지금 이 아이가 뭘 하고 있나»다.
   교시 시각·점심·학원 시각을 이미 다 갖고 있으니, 지금 시각과 맞춰 한 줄로 말해준다.
     등교 전 → 수업 → (쉬는 시간) → 점심 → 수업 → 하교 → 학원 → 하루 끝
   ⚠ 주말·방학이면 아무 말도 안 한다. 「수업 중」이라고 하면 그게 곧 거짓말이다. */
/* ═══ 시간 옵션 (2026-08-03 §4) ═══════════════════════════════════
   설정에 스위치를 두면 **화면이 실제로 바뀌어야 한다.** 안 바뀌면 그건 고장이다.
   요일 시작은 달력 두 곳(달력 화면·편집기 미니 달력)이, 형식 둘은 아래 두 함수가 쓴다. */
const weekStartMon = () => (S.timeOpt?.weekStart || "sun") === "mon";
// 요일 머리 — 월요일 시작이면 한 칸씩 돌린다
const weekDays = () => weekStartMon() ? ["월","화","수","목","금","토","일"] : ["일","월","화","수","목","금","토"];
// 그 달 1일이 격자에서 몇 번째 칸인가
const weekOffset = (jsDay) => weekStartMon() ? (jsDay + 6) % 7 : jsDay;
/* 시각 — "15:00" → 24시간이면 그대로, 12시간이면 "오후 3시"(정각이 아니면 분까지) */
function fmtT(hhmm) {
  const v = String(hhmm || "").trim();
  if (!/^\d{1,2}:\d{2}$/.test(v)) return v;
  if ((S.timeOpt?.timeFmt || "24") === "24") return v;
  const h = +v.slice(0, v.indexOf(":")), m = +v.slice(v.indexOf(":") + 1);
  const ap = h < 12 ? "오전" : "오후";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${ap} ${h12}시${m ? ` ${m}분` : ""}`;
}
/* 날짜 — (8, 3) → "8월 3일" 또는 "8.3" */
const fmtD = (mo, d) => (S.timeOpt?.dateFmt || "ko") === "dot" ? `${mo}.${d}` : `${mo}월 ${d}일`;

/* ═══ 최근 입력 재사용 (2026-08-03 지시서 0803-2 §3) ═══════════════
   「치과」·「태권도」처럼 되풀이되는 이름을 다시 타자 치게 하지 않는다.
   ⚠ 이 폰에만 담는다 — 서버에 보낼 값이 아니다. 유형별로 따로 담아야
     준비물 칸에 「치과」가 뜨는 일이 없다. */
const TITLE_KEY = "eduthink.recentTitles";
function recentTitles(kind) {
  try {
    const all = JSON.parse(localStorage.getItem(TITLE_KEY) || "{}");
    return Array.isArray(all[kind]) ? all[kind] : [];
  } catch (e) { return []; }
}
function rememberTitle(kind, title) {
  const t = String(title || "").trim();
  if (t.length < 2) return;
  try {
    const all = JSON.parse(localStorage.getItem(TITLE_KEY) || "{}");
    const list = [t, ...(all[kind] || []).filter((x) => x !== t)].slice(0, 8);
    all[kind] = list;
    localStorage.setItem(TITLE_KEY, JSON.stringify(all));
  } catch (e) {}
}

/* ═══ 메신저식 입력바 (§3) ═══════════════════════════════════════
   «가벼운 입력». 일간·준비물 화면 아래에 붙어 있고, 제목만 치고 엔터면 들어간다.
   ⚠ **뒤 내용이 밀리면 안 된다**(§3 «레이아웃 점프 0»).
     그래서 position: fixed 로 띄우고, 화면 아래 여백을 입력바 높이만큼 미리 비워 둔다.
     문서 흐름에 넣으면 키보드가 올라올 때마다 목록이 출렁인다.
   ⚠ 「제대로 입력」으로 넘어가는 길을 옆에 둔다 — 날짜·반복이 필요하면 거기로 간다. */
function inputBar(kind, ph) {
  return `
  <div class="ib">
    <input id="ib-t" class="ib-in" placeholder="${ph}" value="${esc(S.ibText || "")}"
      autocomplete="off" oninput="S.ibText=this.value"
      onkeydown="if(event.key==='Enter')App.ibAdd('${kind}')">
    <button class="ib-more" onclick="App.ibToEditor('${kind}')" aria-label="자세히 넣기">
      <i aria-hidden="true" class="ti ti-plus"></i></button>
    <button class="ib-go" onclick="App.ibAdd('${kind}')">넣기</button>
  </div>`;
}

/* ═══ 전광판 (2026-08-03 지시서 0803-2 §1) ═══════════════════════
   홈 맨 위 고정. **표시 전용이다** — 탭도 링크도 없다.
   시각(분 단위) + 아이가 지금 뭐 하는지 + 임박한 부모 일정 한 줄.

   ⚠ **지어내지 않는다.** 시간표가 없거나 방학이면 아이 상태 줄을 아예 안 그린다.
     시각만 남는다. 「3교시 국어」를 방학에 말하는 것이 이 화면이 할 수 있는 최악이다.
   ⚠ 표시 전용이라 button 이 아니라 div 다. 누를 수 없게 생겨야 안 누른다. */
function boardView() {
  const d = new Date();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  const n = nowDoing();                       // 없으면 null — 그 줄을 안 그린다
  // 임박한 부모 일정 = 오늘 것 중 «지금 이후» 가장 가까운 하나. 지난 것은 임박이 아니다
  const nowMin = d.getHours() * 60 + d.getMinutes();
  const next = (STUB.myEvents || [])
    .filter((e) => e.date === TODAY && e.start && toMin(e.start) >= nowMin)
    .sort((a, b) => String(a.start).localeCompare(String(b.start)))[0];
  return `
  <div class="bd" id="board" aria-live="polite">
    <!-- 시계 — «날짜 · 요일» 위, «시각» 아래. 한 줄에 몰면 날짜가 시각에 묻힌다(2026-08-04) -->
    <div class="bd-time">
      <span class="dt">${fmtD(+TODAY.slice(4, 6), +TODAY.slice(6))} ${["일", "월", "화", "수", "목", "금", "토"][d.getDay()]}요일</span>
      <!-- ⚠ 초까지 보여 준다(2026-08-09 지시). 콜론은 1초마다 깜빡여 «살아 있다»를 말한다.
           초를 안 보여 주면 화면이 멈춘 것처럼 보인다. -->
      <span class="tm">${hh}<i class="${d.getSeconds() % 2 ? "off" : ""}">:</i>${mm}<u>${ss}</u></span>
    </div>
    ${n ? `<div class="bd-now ${n.k}"><i></i><b>${n.t}</b>${n.s ? `<em>${n.s}</em>` : ""}</div>` : ""}
    ${next ? `<div class="bd-next"><i aria-hidden="true" class="ti ti-pin"></i>${esc(next.start)} ${esc(next.title)}</div>` : ""}
  </div>`;
}
/* ⚠ 예전엔 **분이 바뀔 때만** 갈아끼웠다 — 초를 보여 주기로 했으니 1초마다 돈다.
   화면 전체를 다시 그리지 않고 전광판 마크업만 바꿔 끼우므로 입력·스크롤은 안 튄다.
   분이 바뀔 때만 전광판을 갈아끼운다.
   ⚠ 화면 전체를 다시 그리면 안 된다 — 입력 중이던 칸이 날아가고(한글 조합 깨짐),
     스크롤도 튄다. 전광판 마크업만 바꿔 끼운다. */
let QUIZ_TIMER = null;   // 퀴즈 문제당 카운트다운(전체 렌더와 분리)
let CLEAR_TIMER = null;  // 클리어 연출 자동 닫기(1.2초)
let FEED_TIMER = null;   // 정답을 보여 주는 시간(맞으면 1.1초, 틀리면 2.2초)
let BOARD_TIMER = null;
function startBoard() {
  clearInterval(BOARD_TIMER);
  BOARD_TIMER = setInterval(() => {
    const el = document.getElementById("board");
    if (!el) { clearInterval(BOARD_TIMER); BOARD_TIMER = null; return; }
    const box = document.createElement("div");
    box.innerHTML = boardView();
    const fresh = box.firstElementChild;
    if (fresh && fresh.innerHTML !== el.innerHTML) el.innerHTML = fresh.innerHTML;
  }, 1000);   // 1초마다 — 초를 보여 주기로 했으니(2026-08-09). 전광판 마크업만 바꿔 끼워 가볍다
}

/* ═══ 아이 흔적 (2026-08-03 지시서 0803-1 §3) ═══════════════════
   달력 날짜마다 «그날 아이가 뭘 했나»를 점으로 남긴다.
   ⚠ 이 배치는 **실서버·DB 적용 금지**다. 그래서 지난 날짜를 서버에 물어볼 수 없다 —
     대신 이 폰이 **실제로 본 것만** 날짜별로 적어 둔다(도장·사진·급식 평가).
     지어낸 값은 하나도 없다. 오늘부터 하루씩 쌓이고, 나중에 서버가 이력을 주면
     같은 자리(marksOf)에 부어 넣기만 하면 화면은 안 고쳐도 된다.
   ⚠ 자녀별로 따로 적는다 — 둘째 달력에 첫째 도장이 뜨면 그건 거짓말이다. */
const DAY_MARK_KEY = "eduthink.dayMarks";
let DAY_MARKS = {};
function loadDayMarks() {
  try { DAY_MARKS = JSON.parse(localStorage.getItem(DAY_MARK_KEY) || "{}") || {}; } catch (e) { DAY_MARKS = {}; }
}
function saveDayMarks() {
  try { localStorage.setItem(DAY_MARK_KEY, JSON.stringify(DAY_MARKS)); } catch (e) {}
}
const markKey = (ymd, childId) => `${childId ?? S.currentChildId}|${ymd}`;
const marksOf = (ymd, childId) => DAY_MARKS[markKey(ymd, childId)] || null;
function noteMark(ymd, patch, childId) {
  const k = markKey(ymd, childId);
  const was = JSON.stringify(DAY_MARKS[k] || null);
  const next = { ...(DAY_MARKS[k] || {}), ...patch };
  // 값이 그대로면 저장하지 않는다 — 그리기마다 localStorage 를 두드리면 스크롤이 걸린다
  if (JSON.stringify(next) === was) return false;
  DAY_MARKS[k] = next; saveDayMarks(); return true;
}
/* 서버에서 그 달 이력을 받아 부어 넣는다 (2026-08-03 지시서 회신 ②).
   GET /children/{id}/marks?month=YYYYMM → { days: { "20260803": {stamp,of,photo,meal} } }
   ⚠ 서버 값이 **이 폰이 적어 둔 것보다 세다.** 이 폰은 자기가 본 것만 알지만 서버는 전부 안다.
     (급식 평가는 아이 폰에서 일어나서 부모 폰엔 아예 안 잡힌다 — 그걸 서버가 채운다.)
   ⚠ 서버가 없거나 로그인 전이면 **조용히 아무 일도 안 한다.** 이 폰이 적어 둔 값은 그대로 살아 있다.
   ⚠ 같은 달을 두 번 받지 않는다 — 달력에서 달을 넘길 때마다 부르는 자리라 그냥 두면 계속 때린다. */
const MARKS_GOT = new Set();
async function loadMarks(ym, force) {
  const c = cur();
  if (!TOKENS.access || !c?.server_id || !/^\d{6}$/.test(String(ym || ""))) return;
  const key = `${c.server_id}|${ym}`;
  if (!force && MARKS_GOT.has(key)) return;
  MARKS_GOT.add(key);
  try {
    const r = await api(`/children/${c.server_id}/marks?month=${ym}`);
    if (!r?.ok) { MARKS_GOT.delete(key); return; }
    const days = r.data?.days || {};
    let changed = false;
    Object.keys(days).forEach((ymd) => {
      if (noteMark(ymd, days[ymd], S.currentChildId)) changed = true;
    });
    if (changed) App.render();
  } catch (_) { MARKS_GOT.delete(key); }   // 다음에 다시 시도할 수 있게 표시를 지운다
}

/* 오늘 것을 적어 둔다 — 미션 목록이 들어와 있을 때만. 목록이 null 이면 «0개»가 아니라 «모른다»다. */
function noteToday() {
  const list = S.missions;
  if (!Array.isArray(list) || !list.length) return;
  const stamp = list.filter((x) => x.status === "done").length;
  const photo = list.filter((x) => x.verify === "review" && (x.status === "done" || x.status === "waiting")).length;
  noteMark(TODAY, { stamp, of: list.length, photo });
}

/* ═══ 하위 화면 머리 (2026-08-03 «탈출 불가» 수정) ═══════════════
   드로어·오늘 카드에서 들어간 화면은 **나올 길이 화면에 보여야 한다.**
   여태 학교 화면에는 ← 가 아예 없었다 — 시스템 뒤로가기를 아는 사람만 빠져나올 수 있었다.

   규칙(전부 이 함수 하나로 지킨다):
     · ← 는 **언제나 오늘 화면으로.** 「직전 화면」이 아니다 —
       드로어에서 들어왔는지 카드에서 들어왔는지에 따라 목적지가 달라지면 그게 미로다.
     · 제목은 «지금 어디인가»만 말한다. 학교 이름 같은 건 부제로 내린다.
     · 하단 3버튼은 여기 없다(홈에만 그린다) — 돌아가는 길은 ← 하나뿐이다.
   ⚠ 이 머리를 쓰는 화면에는 `.subtabs` 를 넣지 않는다. 탭 줄이 있으면 «여긴 학교 탭 안»이 되고,
     그러면 또 어느 탭에서 어디로 나가는지가 생긴다. 화면 하나 = 할 일 하나. */
/* ═══ 🎮 미션 게임 탭 세 개 (2026-08-08) ═══════════════════════════════
   ⚠ 전부 `function` 선언이다 — Screens 가 파일 위쪽이라 const 면 그릴 때 죽는다. */

/* 지금이 어느 시간대인가 — 기획서 §01 «한 번에 다 안 보여준다».
   ⚠ 미션의 `slot` 값(morning/after/evening/any)과 같은 말을 써야 한다. */
function nowSlot() {
  const h = new Date().getHours();
  if (h < 12) return "morning";
  if (h < 18) return "after";
  return "evening";
}
const SLOT_KO = { morning: "아침", after: "방과후", evening: "저녁", any: "아무 때나" };

/* ═══ 🧭 부모 관리 화면 (2026-08-08, 대표님 지시) ═══════════════════════
   「부모페이지는 관리자 페이지야. 화려하진 않아도 알아보기 쉽게」
   「추가 스탬프를 줄 수 있는 확인하는 곳이 없잖아」

   여기서 하는 일은 넷이다 — **확인 · 스탬프 주기 · 진열대 · 미리보기.**
   ⚠ 부모 테마 토큰(--card-a/--ink/--accent)을 쓴다. 게임 팔레트는 아이 세계 전용이다.
   ⚠ 아이 세계를 여기에 섞지 않는다. 보고 싶으면 «아이 화면 미리보기»로 일부러 들어간다. */
function parentMissionAdmin(c, coin) {
  const nm = esc(c.nickname || "아이");
  if (!c.id) return `${subHeader("미션 관리")}
    <p class="empty-mid">아이를 등록하면 시작해요</p>`;

  const head = (title, sub) => `
    <div class="gmp-top">
      <button class="gmp-back" onclick="${S.pmTab ? "App.pmTab(null)" : "App.goBack()"}" aria-label="뒤로">‹</button>
      <div><b>${esc(title)}</b>${sub ? `<em>${esc(sub)}</em>` : ""}</div>
    </div>`;

  const waitMission = (S.missions || []).filter((x) => x.status === "waiting").length;
  const waitVerify = (S.verifyPending || []).length;
  const waitTicket = (S.rewards || []).filter((o) => o.status === "requested").length;
  const todo = waitMission + waitVerify + waitTicket;
  const done = (S.missions || []).filter((x) => x.status === "done");
  const given = S.bonusGiven || [];
  const leftBonus = done.filter((x) => given.indexOf(x.id) < 0).length;

  /* ── 안쪽 화면 ─────────────────────────────────────────────
     ⚠ 한 장에 다 펼치면 스크롤이 길어져 «무엇부터 봐야 하는지»가 안 보인다
       (대표님 지시 08-08: 「카드로 각 화면으로 들어가서 보게. 한 번에 다 펼치지 말고」). */
  if (S.pmTab === "todo") {
    return `<div class="gmp">${head("확인해 주세요", todo ? `${todo}건` : "지금은 없어요")}
      ${!todo ? `<p class="pm-none">지금 확인할 게 없어요</p>` : `
        ${!waitVerify ? "" : `<button class="pm-go" onclick="location.hash='#mission'">
          <span class="pm-i">📸</span><b>아이가 낸 것</b><span class="pm-cnt">${waitVerify}</span></button>`}
        ${!waitMission ? "" : `<button class="pm-go" onclick="location.hash='#mission'">
          <span class="pm-i">✅</span><b>미션 확인 기다림</b><span class="pm-cnt">${waitMission}</span></button>`}
        ${!waitTicket ? "" : `<button class="pm-go" onclick="location.hash='#tickets'">
          <span class="pm-i">🎟</span><b>바꿔 달라고 한 것</b><span class="pm-cnt">${waitTicket}</span></button>`}`}
    </div>`;
  }

  if (S.pmTab === "bonus") {
    return `<div class="gmp">${head("추가 증정", "해낸 미션에 ＋1")}
      ${!done.length ? `<p class="pm-none">아이가 미션을 끝내면 여기서 ＋1을 얹어 줄 수 있어요</p>`
        : done.map((x) => {
          const had = given.indexOf(x.id) >= 0;
          return `
          <div class="pm-row">
            <span class="pm-i">⭐</span>
            <b>${esc(x.title)}</b>
            ${had ? `<span class="pm-ok">＋1 줬어요</span>`
                  : `<button class="pm-plus" ${S.giveBusy ? "disabled" : ""}
                       onclick="App.missionBonus(${x.id})">＋1</button>`}
          </div>`;
        }).join("")}
      <p class="pm-fine">한 미션에 한 번만 · 오늘 받은 것이 ${coin.limit}개를 넘으면 안 들어가요</p>
    </div>`;
  }

  if (S.pmTab === "today") {
    const sets = S.msets || {}, sc = S.schoolMs, q = S.quiz;
    const row = (icon, name, d, all, extra) => `
      <div class="pm-row">
        <span class="pm-i">${icon}</span><b>${esc(name)}</b>
        <span class="pm-n">${all ? `${d} / ${all}` : "오늘 없음"}</span>
        ${d >= all && all > 0 ? `<span class="pm-ok">완료</span>` : ""}${extra || ""}
      </div>`;
    return `<div class="gmp">${head("오늘 아이가 한 것", "모은 스탬프 ★" + coin.stars)}
      ${row("🌅", "아침 미션", sets.morning?.done || 0, sets.morning?.all || 0)}
      ${sc && sc.available === false ? "" : row("🏫", "학교 미션", sc?.done || 0, sc?.all || 0)}
      ${row("📚", "방과후 미션", sets.after?.done || 0, sets.after?.all || 0)}
      ${row("⚔️", "오늘의 미션", q?.done ? 1 : 0, 1,
            q?.done ? `<span class="pm-sub">${q.correct} / ${q.total} 맞힘</span>` : "")}
    </div>`;
  }

  /* ── 허브 — 2×2 카드. 아이 홈과 **같은 문법**이라 배울 게 없다 ── */
  const tile = (key, icon, name, note, cnt, cls) => `
    <button class="pm-tile${cls ? " " + cls : ""}" onclick="${key.startsWith("#") ? `location.hash='${key}'` : `App.pmTab('${key}')`}">
      ${cnt ? `<span class="pm-badge">${cnt}</span>` : ""}
      <span class="pm-ti">${icon}</span>
      <b>${esc(name)}</b>
      <em>${esc(note)}</em>
    </button>`;

  return `
  <div class="gmp">
    <div class="gmp-top">
      <button class="gmp-back" onclick="App.goBack()" aria-label="뒤로">‹</button>
      <div><b>${nm} 미션 관리</b></div>
    </div>

    <div class="pm-top">
      <div class="pm-big"><b>★ ${coin.stars}</b><em>모은 스탬프</em></div>
      <div class="pm-big"><b>${coin.earned_today} / ${coin.limit}</b><em>오늘 받은 것</em></div>
      <div class="pm-big"><b>Lv.${coin.level || 1}</b><em>${gmRank(coin.level || 1)}</em></div>
    </div>

    <div class="pm-grid">
      ${tile("todo", "🔔", "확인해 주세요", todo ? `${todo}건 기다려요` : "지금은 없어요", todo, todo ? "hot" : "")}
      ${tile("bonus", "⭐", "추가 증정", leftBonus ? `${leftBonus}개에 줄 수 있어요` : "해낸 미션에 ＋1", leftBonus)}
      ${tile("today", "📋", "오늘 한 것", "아침·학교·방과후", 0)}
      ${tile("#store", "🏪", "진열대 꾸미기", "바꿀 것을 정해요", 0)}
      ${tile("#mission", "🎯", "미션 고르기", "무엇을 시킬지", 0)}
      ${tile("preview", "👀", "아이 화면", "아이가 보는 그대로", 0)}
    </div>
  </div>`;
}

/* ═══ 🎮 아이 화면 조각 (2026-08-08, 기획서 v2 §01 · 시안 v4 B안) ═══════
   홈도 카드 안도 **같은 타일**이다. 화면마다 다른 규칙을 배울 필요가 없어야 한다.
   ⚠ 색은 **게임 전용 팔레트**를 쓴다 — 부모 테마 18종의 색 토큰을 건드리지 않는다.
     아이 테마는 배경 그라데이션 한 쌍만 바뀌고 카드는 항상 흰색이다.
   ⚠ 아이콘은 전부 이모지다. 서브셋 폰트에 없는 `ti-*` 를 쓰면 빈 네모가 뜬다(08-07 사고). */

/* 하루 코인 상한 — 서버(star_core.DAILY_COIN_LIMIT)가 정본이고 여기는 «아직 못 받았을 때»의 기본값이다.
   🔴 대표님 확정 대기(60 제안). 두 곳이 갈리면 화면이 거짓말을 하므로 서버 값이 오면 그걸 쓴다. */
const COIN_LIMIT = 60;

/* 배경 테마 5종 — 실제로 바뀌는 것은 CSS 변수 두 개뿐이다(§01.1) */
const GM_THEMES = [
  ["sky", "하늘"], ["lime", "라임"], ["lav", "라벤더"], ["sunset", "선셋"], ["mint", "민트"],
];
function gmTheme() {
  const c = curView();
  const t = (c && c.kid_theme) || S.gmTheme || "sky";
  return "gt-" + (GM_THEMES.some(([k]) => k === t) ? t : "sky");
}

/* 캐릭터가 들어올 자리. 지금은 이모지 — 업데이트 때 **이 칸만** 갈아끼우면 화면을 다시 안 짠다 */
const GM_FACES = ["🦊", "🐻", "🐼", "🐯", "🐸", "🐧", "🦁", "🐨"];
function gmAvatar(c) {
  if (c && c.avatar_slot) return esc(c.avatar_slot);
  const n = String((c && c.nickname) || "나");
  let h = 0; for (let i = 0; i < n.length; i++) h = (h * 31 + n.charCodeAt(i)) % 997;
  return GM_FACES[h % GM_FACES.length];
}

/* 칭호 — **레벨**로 매긴다. 레벨은 「해낸 미션 수」로 오르니 꾸준한 아이는 무조건 오른다.
   ⚠ 잔액으로 매기면 «쓰면 칭호가 내려가서» 모으는 재미가 죽는다(v1 의 실수). */
function gmRank(lv) {
  const R = [[1,"새싹"],[3,"견습"],[6,"일꾼"],[10,"장인"],[16,"달인"],[24,"영웅"],[34,"마스터"]];
  return R.filter(([n]) => lv >= n).pop()[1];
}

/* ── 미션 갈래 ───────────────────────────────────────────────────────
   아침 · 학교 · 방과후는 **항상 있는 기본 틀**이고, 변동하는 건 「오늘의 미션」 하나다.
   그래서 홈은 언제나 4칸이고 매일 같은 자리에 같은 칸이 있다.

   ⚠ 「학교」 칸은 **국내 전용**이다 — 급식·친구·시간표는 학교정보 모듈이 있어야 돈다.
     해외판은 `schoolMissions()` 를 안 끼우면 이 칸만 빠지고 나머지는 그대로 돈다.
     이것이 기획서 v2 §09 가 말하는 «자르는 선 한 곳»의 앱 쪽 구현이다. */
function gameCats() {
  const ms = S.missions || [];
  const at = (slots) => ms.filter((x) => slots.indexOf(x.slot || "any") >= 0);
  const cnt = (list) => ({ done: list.filter((x) => x.status === "done").length, all: list.length,
                           stars: list.reduce((a, x) => a + (x.stars || 0), 0) });

  const morning = cnt(at(["morning"]));
  const after = cnt(at(["after", "evening", "any"]));
  const school = schoolMissionsSummary();
  const q = S.quiz;
  const qDone = !!(q && q.done);

  const out = [
    { key: "morning", icon: "🌅", name: "아침 미션", c: "orange", ...morning },
    // 국내 전용 — 이 한 줄만 빼면 해외판이 된다
    school ? { key: "school", icon: "🏫", name: "학교 미션", c: "cyan", kr: true, ...school } : null,
    { key: "after", icon: "📚", name: "방과후 미션", c: "violet", ...after },
    { key: "today", icon: "⚔️", name: "오늘의 미션", c: "red", boss: true,
      done: qDone ? 1 : 0, all: 1, stars: (q && q.total ? q.total : 10) + 5,
      note: q ? `${q.total || 10}문제 · 한 문제 ${gmSec(q)}초` : "10문제 · 한 문제 5초",
      foot: qDone ? "오늘 다 함" : "아직 안 함" },
  ].filter(Boolean);
  return out;
}
function gmSec(q) {
  const it = (q && q.items && q.items[0]) || null;
  return (it && it.sec) || 5;
}

/* 학교 미션 — 「제공자」. **서버의 school_missions.js 하나가 정본이다.**
   ⚠ 목록·아이콘·문구를 여기에 또 적지 않는다 — 나라를 늘릴 때 두 곳을 고쳐야 한다.
   ⚠ 해외판은 서버에서 그 파일을 빼면 `available:false`(또는 404)가 오고,
     그러면 아래가 null 을 돌려 **홈이 3칸이 된다.** 앱은 고칠 것이 없다. */
function schoolMissionsSummary() {
  const s = S.schoolMs;
  if (!s || s.available === false || !s.items?.length) return null;
  return { done: s.done, all: s.all,
           stars: s.items.reduce((a, x) => a + (x.stars || 0), 0) };
}
function schoolMissionList() {
  const s = S.schoolMs;
  if (!s || !s.items?.length) return [];
  return s.items.map((x) => ({ ...x, go: "#" + x.go }));
}

/* 타일 하나 — 홈에서도 카드 안에서도 이 함수 하나를 쓴다 */
function gameTile(t) {
  const pct = t.all ? Math.round((t.done / t.all) * 100) : 0;
  const clear = t.all > 0 && t.done >= t.all;
  return `
  <button class="gm-tile c-${t.c}${clear ? " clear" : t.done < t.all ? " todo" : ""}${t.boss ? " boss" : ""}"
    ${t.act ? `onclick="${t.act}"`
    : t.go ? `onclick="location.hash='${t.go}'"`
    : t.tap ? `onclick="App.missionDone(${t.tap})"`
    /* ⚠ 여기서 «아무것도 아니면 카드 열기»로 흘려보내면 안 된다.
       미션 타일의 key 는 **미션 id** 라, 끝낸 미션을 누르면 App.gameTab('39') 같은
       없는 화면으로 갔다(08-08 실기). 갈 곳이 없는 타일은 **누를 수 없어야** 한다. */
    : t.leaf ? "disabled"
    : `onclick="App.gameTab('${t.key}')"`}>
    ${t.kr ? `<span class="gm-kr">학교정보</span>` : ""}
    ${clear ? `<span class="gm-stamp">CLEAR</span>` : ""}
    <span class="gm-ti">${t.icon}</span>
    <b class="gm-tt">${esc(t.name)}</b>
    ${t.note ? `<em class="gm-tn">${esc(t.note)}</em>` : ""}
    <span class="gm-bar"><i style="width:${pct}%"></i></span>
    <span class="gm-tb"><em>${esc(t.foot || (clear ? `${t.done} / ${t.all} 완료` : `${t.done} / ${t.all}`))}</em>
      <span class="gm-co">★${t.stars}</span></span>
  </button>`;
}

/* ── 카드를 열면 — 그 갈래의 미션이 «같은 타일»로 ────────────────── */
function gameCard(catKey) {
  const meta = { morning: ["🌅", "아침 미션", ["morning"]],
                 after: ["📚", "방과후 미션", ["after", "evening", "any"]],
                 school: ["🏫", "학교 미션", null] }[catKey];
  if (!meta) return `<p class="gm-empty">없는 화면이에요</p>`;
  const [icon, name, slots] = meta;

  let tiles, done = 0, all = 0, stars = 0;
  if (catKey === "school") {
    const list = schoolMissionList();
    all = list.length; done = list.filter((x) => x.done).length;
    stars = list.reduce((a, x) => a + x.stars, 0);
    tiles = list.map((x) => gameTile({ leaf: true, key: x.key, icon: x.icon, name: x.name, note: x.note,
      c: "cyan", done: x.done ? 1 : 0, all: 1, stars: x.stars, go: x.go,
      foot: x.done ? "했어요" : "30초면 끝" })).join("");
  } else {
    const list = (S.missions || []).filter((x) => slots.indexOf(x.slot || "any") >= 0);
    all = list.length; done = list.filter((x) => x.status === "done").length;
    stars = list.reduce((a, x) => a + (x.stars || 0), 0);
    if (S.missions === null) return gmHead(icon, name, "불러오는 중…") + `<p class="gm-empty">잠시만요…</p>`;
    /* ⚠ 미션마다 «끝내는 방법»이 다르다. 전부 App.missionDone 으로 보내면
       **사진 미션이 사진 없이 그냥 완료로 처리된다**(대표님 지적 08-08).
         photo  → 카메라(App.missionShoot) → 부모 확인 대기
         나머지 → 그 자리에서 완료(App.missionDone) */
    /* ⚠ 카탈로그에 `verify='photo'` 인 미션이 **하나도 없다**(원격 실측 08-08:
       instant 71 · review 73 · endday 13 · photo 0). 그래서 「사진 연결이 왜 안 되냐」였다 —
       사진을 낼 길(POST /missions/{id}/photo)은 서버에 있는데 그걸 쓰는 미션이 없었다.
       **부모가 확인해야 하는 미션(review·endday)은 사진이 붙을 수 있게** 연다.
       사진은 «해야 하는 것»이 아니라 «있으면 부모가 바로 아는 것»이다 — 취소하면 그냥 완료로 간다. */
    tiles = list.map((x) => {
      const shot = x.verify === "photo" || x.verify === "review" || x.verify === "endday";
      const open = x.status === "open";
      return gameTile({
        leaf: true,
        key: x.id, icon: shot ? "📷" : gmMissionIcon(x), name: x.title,
        note: x.minutes ? `${x.minutes}분` : (shot ? "사진 찍어서 보내기" : ""),
        c: catKey === "morning" ? "orange" : "violet",
        done: x.status === "done" ? 1 : 0, all: 1, stars: x.stars || 1,
        foot: x.status === "done" ? "했어요"
            : x.status === "waiting" ? "확인 기다리는 중"
            : shot ? "사진 찍기" : "눌러서 완료",
        act: !open ? null : shot ? `App.missionShotOrDone(${x.id})` : null,
        tap: open && !shot ? x.id : null,
      });
    }).join("");
  }

  /* 세트 보너스 — 다 하면 얹어 준다. «몇 개 남았는지»가 보여야 마지막 하나를 하게 된다.
     ⚠ 학교 세트는 **서버가** 준다(school_missions.js). 화면이 별을 세지 않는다. */
  const left = Math.max(0, all - done);
  /* 「받았나」는 **서버가** 안다. 화면이 기억하면 앱을 껐다 켤 때 어긋난다.
     학교 세트는 school_missions.js, 아침·방과후 세트는 api_mission.js 가 맡는다
     — 학교는 해외판에서 통째로 빠져야 해서 파일을 나눴다. */
  const taken = catKey === "school"
    ? !!(S.schoolMs && S.schoolMs.bonus_taken)
    : !!(S.msets && S.msets[catKey] && S.msets[catKey].taken);
  const ready = all > 0 && left === 0 && !taken;
  const act = !ready ? null
    : catKey === "school" ? "App.schoolBonus()" : `App.setBonus('${catKey}')`;
  const bonus = all > 1 ? gameTile({ leaf: true, key: "bonus", icon: "🎁", name: "세트 보너스",
    note: `${all}개 다 하면`, c: "gold", done: taken ? all : done, all,
    stars: (catKey === "school" ? (S.schoolMs && S.schoolMs.bonus) : (S.msets && S.msets.bonus)) || 2,
    act,
    foot: taken ? "받았어요" : ready ? "눌러서 받기!" : `${left}개 남음` }) : "";

  return `
    ${gmHead(icon, name, `오늘 ${done} / ${all} · 모으면 ★${stars}`)}
    <div class="gm-grid">${tiles || `<p class="gm-empty">오늘 할 게 없어요</p>`}${bonus}</div>`;
    /* ⚠ 상점 바는 **홈에만** 둔다(대표님 지시 08-08). 카드 안에도 두었더니
       같은 것이 두 번 보여서 «여기도 상점이 있나»가 됐다. */
}
function gmMissionIcon(x) {
  const a = String(x.area || "");
  return { body: "🧼", things: "🧺", family: "💛", digital: "📵", study: "📖",
           manner: "🙇", talent: "🎨" }[a] || "⭐";
}
function gmHead(icon, title, sub) {
  return `
  <div class="gm-head">
    <button class="gm-back" onclick="App.gameTab(null)" aria-label="뒤로">‹</button>
    <span class="gm-hi">${icon}</span>
    <div><b class="gm-ht">${esc(title)}</b><em class="gm-hs">${esc(sub)}</em></div>
  </div>`;
}

/* ── 프로필 — 배경색 · 뱃지. 캐릭터 자리는 비워 둔다 ───────────────── */
function gameProfile(c, coin) {
  const lv = coin.level || 1;
  // ⚠ `cur` 로 두면 전역 함수 cur() 를 가린다 — 이 파일에서 실제로 겪은 종류의 사고다
  const curTheme = (c && c.kid_theme) || S.gmTheme || "sky";
  return `
    ${gmHead("🙂", "내 프로필", `Lv.${lv} ${gmRank(lv)}`)}
    <div class="gm-pf">
      <!-- ⚠ 얼굴을 크게 띄우고 이름·레벨을 밑에 세로로 쌓았더니 카드가 화면 절반을 먹고
           빈 곳만 커졌다(대표님 지적 08-08). 가로 한 줄로 눕힌다. -->
      <div class="gm-prow">
        <div class="gm-big">${gmAvatar(c)}<span class="gm-soon">곧</span></div>
        <div class="gm-pinfo">
          <b class="gm-pnm">${esc((c && c.nickname) || "나")}</b>
          <span class="gm-lv2">Lv.${lv} ${gmRank(lv)}</span>
        </div>
      </div>
      <div class="gm-stats">
        <div><b>${coin.stars}</b><em>모은 코인</em></div>
        <div><b>${coin.streak || 0}</b><em>연속 출석</em></div>
        <div><b>${coin.earned_today} / ${coin.limit}</b><em>오늘 획득</em></div>
      </div>
    </div>


    <div class="gm-lab">🎨 배경 바꾸기</div>
    <div class="gm-sw">
      ${GM_THEMES.map(([k, n]) => `
        <button class="gm-swb sw-${k}${curTheme === k ? " on" : ""}" title="${n}"
          onclick="App.gmTheme('${k}')" aria-label="${n}"></button>`).join("")}
    </div>

    <div class="gm-lab">🏅 모은 뱃지</div>
    ${gmBadges(coin)}
    ${gmShopBar()}`;
}

/* 뱃지 — **가진 것만 채우고 나머지는 «조건»을 보여 준다.**
   ⚠ 없는 것을 있는 척 채우지 않는다. 잠긴 칸에 조건을 적어야 «뭘 하면 되는지»가 되고,
     빈 칸으로 두면 그냥 «만들다 만 화면»이다.
   ⚠ 리그 뱃지는 STAGE 2 에서 켠다 — 그때까지는 잠긴 채로 둔다(기획서 v2 §07). */
function gmBadges(coin) {
  const list = [
    { icon: "🔥", name: "연속 30일", on: (coin.streak || 0) >= 30, need: `${Math.max(0, 30 - (coin.streak || 0))}일 더` },
    { icon: "⭐", name: "코인 1000", on: (coin.stars || 0) >= 1000, need: `${Math.max(0, 1000 - (coin.stars || 0))}개 더` },
    { icon: "🎖", name: `Lv.10`, on: (coin.level || 1) >= 10, need: `Lv.${Math.max(0, 10 - (coin.level || 1))} 더` },
    { icon: "🏆", name: "리그 1등", on: false, need: "곧 열려요" },
  ];
  return `
  <div class="gm-bgs">
    ${list.map((b) => `
      <div class="gm-bg2${b.on ? "" : " off"}">
        <span class="gm-bgi">${b.on ? b.icon : "🔒"}</span>
        <em>${esc(b.on ? b.name : b.need)}</em>
      </div>`).join("")}
  </div>`;
}

/* 진열대 그림 — **이름에서 고른다.**
   store_items 에 그림 칸이 없고, 부모에게 이모지를 고르라고 시키면 진열대 세팅이 길어진다
   (첫 설정에서 손을 놓으면 아이 화면이 텅 빈다 — 기획서 v2 §04).
   ⚠ 못 찾으면 🎁 다. 억지로 맞히지 않는다.
   ⚠ 나중에 부모가 직접 고르게 하면 그 값이 이것보다 우선이다. */
const SHOP_ICONS = [
  [/아이스크림|하드|빙수|아이스/, "🍦"], [/치킨|닭/, "🍗"], [/피자/, "🍕"],
  [/햄버거|버거/, "🍔"], [/과자|간식|젤리|사탕|초콜|초코/, "🍬"], [/음료|콜라|주스|음료수/, "🥤"],
  [/떡볶이|분식/, "🌶"], [/라면/, "🍜"], [/케이크|생일/, "🎂"],
  [/게임|플스|닌텐도|로블록스|마크/, "🎮"], [/유튜브|영상|티비|TV|만화|웹툰/, "📺"], [/영화/, "🎬"],
  [/자전거|킥보드/, "🚲"], [/장난감|레고|인형/, "🧸"], [/책|도서|만화책/, "📚"],
  [/용돈|돈|현금/, "💰"], [/문구|스티커|펜/, "✏️"], [/놀이공원|워터파크|키즈카페/, "🎡"],
  [/외식|식당|고기/, "🍖"], [/여행|캠핑/, "⛺"], [/축구|야구|운동/, "⚽"],
  [/폰|핸드폰|스마트폰/, "📱"], [/늦게|자정|밤샘|취침/, "🌙"], [/친구|초대/, "👫"],
];
function shopIcon(title) {
  const t = String(title || "");
  for (const [re, ic] of SHOP_ICONS) if (re.test(t)) return ic;
  return "🎁";
}

/* 상점 바 — 홈과 카드 안이 **같은 것**을 쓴다. 둘로 나누면 반드시 어긋난다.
   withTicket 이면 티켓 줄까지 얹는다(홈에서만). */
function gmShopBar(withTicket) {
  const stars = (S.coin && S.coin.stars) || 0;
  return `
  <div class="gm-shopwrap">
    ${withTicket ? gmTicketBar() : ""}
    <button class="gm-shopbar" onclick="App.gameTab('shop')">
      <span class="gm-si">🏪</span>
      <span class="gm-sb"><b>스타코인 상점</b><em>모은 ★로 바꾸기</em></span>
      <span class="gm-sc">★${stars}</span>
    </button>
  </div>`;
}

/* 기다리는 티켓 — 「바꿔놓고 어디서 받나」가 화면에 있어야 한다 */
function gmTicketBar() {
  const list = S.rewards;
  const wait = list ? list.filter((o) => o.status === "requested").length : 0;
  return `
  <button class="gm-tkbar" onclick="location.hash='#tickets'">
    <span class="gm-si">🎟</span><b>내 티켓</b>
    <span class="gm-tkn${wait ? "" : " zero"}">${list === null ? "…" : wait ? `${wait}장 기다리는 중` : "없어요"}</span>
  </button>`;
}

/* ── 클리어 연출 — 세트를 완주한 «순간»에만 (기획서 v2 §01.3) ────────
   개별 미션 완료는 조용히 체크만 한다. 매번 연출하면 3초 만에 성가신 것이 된다.
   ⚠ 연출은 1.2초면 사라지지만 **딱지는 타일에 하루 종일 남는다**(gameTile 의 gm-stamp). */
function clearView() {
  const v = S.clear;
  if (!v) return "";
  return `
  <div class="gm-veil" onclick="App.clearClose()">
    <div class="gm-vin">
      <div class="gm-ring">${v.icon}</div>
      <div class="gm-big2">CLEAR</div>
      <div class="gm-sub2">${esc(v.name)} 완주!</div>
      ${v.stars ? `<div class="gm-gain">＋★${v.stars}</div>` : ""}
      <div class="gm-tap">아무 데나 누르면 넘어가요</div>
    </div>
  </div>`;
}

// ── 퀴즈 탭 ────────────────────────────────────────────────
function gameQuiz() {
  const q = S.quiz;
  const head = gmHead("⚔️", "오늘의 미션", quizSub(q));
  if (q === null) return head + `<p class="gm-empty">불러오는 중…</p>`;

  // ① 채점 결과
  if (S.quizResult) {
    const r = S.quizResult;
    return head + `
    <div class="gm-body">
      <div class="qz-done">
        <div class="qz-score"><b>${r.correct}</b><span>/ ${r.total}</span></div>
        ${r.perfect ? `<div class="qz-perfect">만점! 보너스 ★${r.perfect_bonus}</div>` : ""}
        <div class="qz-coin">★ ${r.coins} 받았어요</div>
        ${r.capped ? `<p class="qz-cap">코인은 오늘 여기까지예요 — 그래도 기록은 쌓였어요</p>` : ""}
      </div>

      ${quizRetryBtn(r.retry)}
      <button class="gm-go ghost" onclick="App.gameTab(null)">돌아가기</button>
    </div>`;
  }

  // ② 이번 판을 이미 끝냈다
  if (q.done) {
    return head + `
    <div class="gm-body">
      <div class="qz-done">
        <div class="qz-score"><b>${q.correct}</b><span>/ ${q.total}</span></div>
        <div class="qz-coin">★ ${q.coins} 받았어요</div>
      </div>
      ${quizRetryBtn(q.retry)}
      <button class="gm-go ghost" onclick="App.gameTab(null)">돌아가기</button>
    </div>`;
  }

  // ③ 시작 전
  if (!q.items || !q.items.length) return head + `<p class="gm-empty">문제를 준비하지 못했어요</p>`;
  if (S.quizIdx < 0) {
    return head + `
    <div class="gm-body">
      <div class="qz-intro">
        <b>맞힌 만큼 ★</b>
        <p>${q.total}문제 · 한 문제 ${gmSec(q)}초</p>
        <p class="quiet">다 맞히면 보너스 ★${q.perfect_bonus}</p>
        <button class="gm-go" onclick="App.quizStart()">시작하기 ▶</button>
      </div>
    </div>`;
  }

  // ④ 푸는 중
  const item = q.items[S.quizIdx];
  if (!item) return head + `<p class="gm-empty">…</p>`;
  const per = item.sec || 5;
  const ratio = Math.max(0, Math.min(100, (S.quizLeft / per) * 100));
  return `
    <div class="gm-body qz-play">
      <div class="qz-hd">
        <span class="qz-no">${S.quizIdx + 1} / ${q.total}</span>
        <span class="qz-field">${esc(QUIZ_FIELD_KO[item.field] || "")}</span>
      </div>
      <div class="qz-timer"><span style="width:${ratio}%"></span></div>
      <div class="qz-mid">
        ${item.image ? `<div class="qz-img"><img src="${esc(item.image)}" alt=""></div>` : ""}
        <p class="qz-q"><span class="qz-qn">${S.quizIdx + 1})</span>${esc(item.q)}</p>
      </div>
      <div class="qz-opts${item.kind === "ox" ? " ox" : ""}">
        ${item.options.map((o, i) => {
          const f = S.quizFeed;
          /* 누른 순간 표시가 나야 «눌렸나?» 하고 두 번 안 누른다.
             정답 여부는 서버가 말해 줄 때(f) 색으로 갈린다 — 그전엔 «고른 것»만 보여준다. */
          const picked = !f && S.quizMy === (i + 1);
          /* 답한 «직후»에만 색이 붙는다 — 정답은 초록, 내가 고른 오답은 빨강.
             ⚠ 답하기 전에는 서버가 정답을 안 보내므로 여기서 칠할 방법 자체가 없다. */
          const mark = !f ? (picked ? " picked" : "")
            : (i + 1) === f.answer ? " ok" : (i + 1) === f.picked ? " no" : " dim";
          return `
          <button class="qz-op${mark}" ${f ? "disabled" : `onclick="App.quizPick(${i + 1})"`}>
            <span class="qz-k">${i + 1}</span>${esc(o)}
            ${mark === " picked" ? `<span class="qz-mk">✓</span>` : ""}
            ${mark === " ok" ? `<span class="qz-mk">○</span>` : ""}
            ${mark === " no" ? `<span class="qz-mk">✕</span>` : ""}</button>`;
        }).join("")}
      </div>
      ${quizFeedView()}
    </div>`;
}

/* 답안지 — **맞힌 것도 전부 보여 준다.**
   「답을 알려줘야 학습이 된다」는 지시(08-08)라, 틀린 것만 보여주던 방식을 버렸다.
   ⚠ 답이 새어도 이 판은 finished_at 이 찍혀 다시 못 낸다.
     다음 판에서 «외운 답»으로 점수를 버는 구멍은 서버가 막는다 —
     리그 점수는 «그 문제를 처음 맞혔을 때»에만 준다(api_quiz.js 의 seen). */
function quizSheet(rv) {
  if (!rv || !rv.length) return "";
  return `
    <div class="gm-lab">📝 답안지</div>
    <div class="qz-sheet">
      ${rv.map((v) => `
        <div class="qz-rv ${v.ok ? "o" : "x"}">
          <span class="qz-rn">${v.no}</span>
          <div class="qz-rb">
            <b>${esc(v.q || "")}</b>
            <em class="ans">정답 ${v.answer}) ${esc(v.answer_text)}</em>
            ${v.ok ? "" : `<em class="mine">${v.picked
              ? `내 답 ${v.picked}) ${esc(v.picked_text || "")}` : "시간이 지났어요"}</em>`}
            ${v.hint ? `<em class="hint">${esc(v.hint)}</em>` : ""}
          </div>
          <span class="qz-rm">${v.ok ? "○" : "✕"}</span>
        </div>`).join("")}
    </div>`;
}

/* 답한 직후 — «맞았다/틀렸다»와 정답을 그 자리에서 알려 준다(대표님 지시 08-08).
   답안지를 마지막에 몰아 주지 않는다. 틀린 순간에 답을 봐야 남는다. */
function quizFeedView() {
  const f = S.quizFeed;
  if (!f) return "";
  return `
  <div class="qz-feed ${f.ok ? "o" : "x"}" onclick="App.quizNext()">
    <b>${f.ok ? "맞았어요!" : "아쉬워요"}</b>
    ${f.ok ? "" : `<em>정답은 ${f.answer}) ${esc(f.answer_text)}</em>`}
    ${f.hint ? `<i>${esc(f.hint)}</i>` : ""}
    <span class="qz-next">${f.last ? "결과 보기 ▶" : "다음 문제 ▶"}</span>
  </div>`;
}

function quizSub(q) {
  if (!q) return "불러오는 중";
  const a = q.attempt || 1;
  return a > 1 ? `${a}판째 · 틀렸던 문제부터` : `${q.total || 10}문제 · 하루 첫 판은 공짜`;
}

/* 재도전 — 값은 **서버가 준 것만** 쓴다. 화면이 값표를 알고 있으면 반드시 어긋난다.
   ⚠ 5번을 다 쓰려면 3+6+12+24+48 = 93 인데 하루 상한은 60 이다 —
     «모아둔 코인»이 있어야 끝까지 간다. 의도한 설계다. */
function quizRetryBtn(rt) {
  if (!rt) return "";
  if (!rt.can) {
    return rt.used >= rt.max
      ? `<p class="gm-empty">오늘 몴은 다 썼어요 · 내일 또 만나요</p>` : "";
  }
  const have = (S.coin && S.coin.stars) || 0;
  const poor = have < rt.cost;
  return `
    <button class="gm-go retry" ${poor ? "disabled" : ""} onclick="App.quizRetry()">
      한 판 더 · ★${rt.cost}</button>
    <p class="gm-fine">${poor
      ? `★${rt.cost}개가 필요해요 (지금 ${have}개)`
      : `오늘 ${rt.used} / ${rt.max}판 · 할수록 값이 올라가요`}</p>`;
}

const QUIZ_FIELD_KO = { kor: "국어", math: "수학", sci: "과학", world: "나라",
  proverb: "속담", life: "상식", sports: "스포츠", ent: "연예" };

// ── 상점 탭 ────────────────────────────────────────────────
function gameShop() {
  const list = S.store;
  if (list === null) return `<p class="gm-empty">불러오는 중…</p>`;

  /* 부모가 보고 있으면 «진열대 꾸미기» 길을 준다 (2026-08-08 지적: 등록할 데가 없었다).
     ⚠ 아이에게는 안 보인다 — 진열대를 정하는 건 부모의 일이다(기획서 §06).
       아이 토큰·아이 모드·부모의 아이 미리보기 셋 다 아이로 친다.
     ⚠ 등록 화면은 #store 에 이미 있다. 게임 안에 폼을 또 만들지 않는다 — 입구가 둘이면 갈린다. */
  const kid = isChildToken() || S.childView || S.kidMode;
  const setup = kid ? "" : `
      <button class="gm-go ghost" onclick="location.hash='#store'">
        진열대 꾸미기</button>`;

  const stars = (S.coin && S.coin.stars) || 0;
  const head = gmHead("🏪", "스타코인 상점", `내 코인 ★${stars}`);

  if (!list.length) return `${head}
    <div class="gm-body">
      <p class="gm-empty">${kid
        ? "엄마아빠가 무엇과 바꿀 수 있는지<br>정해 주면 여기에 나와요"
        : "아직 바꿀 수 있는 게 없어요<br>무엇과 바꿔 줄지 정해 주세요"}</p>
      ${setup}
    </div>`;

  const why = { limit: "이번엔 다 바꿨어요", stars: "★이 모자라요" };
  /* 진열대 — 2×2 격자. 못 사는 것은 숨기지 않고 «몇 개 더»로 남겨 **목표**로 만든다.
     ⚠ 목표 게이지를 따로 만들지 않는 이유가 이것이다(기획서 v2 §04). */
  return `${head}
    <div class="gm-grid cap">
      ${list.map((it) => {
        const busy = S.storeBusy === it.item_id;
        const short = Math.max(0, (it.stars_required || 0) - stars);
        return `
        <div class="gm-item ${it.can_buy ? "" : "off"}">
          <div class="gm-ph">${esc(it.emoji || shopIcon(it.title))}</div>
          <b class="gm-inm">${esc(it.title)}</b>
          ${it.limit_type ? `<em class="gm-ilm">${it.limit_type === "weekly" ? "주" : "달"} ${it.limit_count}번 중 ${it.used}번</em>` : ""}
          <button class="gm-buy" ${it.can_buy && !busy ? "" : "disabled"}
            onclick="App.storeBuy('${it.item_id}')">★${it.stars_required}</button>
          ${it.can_buy ? "" : `<em class="gm-need">${
            it.reason === "stars" && short ? `${short}개 더!` : (why[it.reason] || "")}</em>`}
        </div>`;
      }).join("")}
    </div>
    <div class="gm-lab">🎟 내 티켓</div>
    <button class="gm-go ghost" onclick="location.hash='#tickets'">티켓 보러 가기</button>
    ${setup}`;
}

/* ═══ 스타코인 상점 · 칭찬 · PIN 의 보조 뷰 (2026-08-07) ═══════════════════
   ⚠ 전부 `function` 선언이다 — Screens 객체가 파일 위쪽에 있어 `const` 로 두면
     화면을 그릴 때 «아직 정의 안 됨»으로 죽는다. 끌어올려지는 형태여야 한다. */

/* 서버가 주는 시각은 ISO 다. `fmtDate` 는 «YYYYMMDD» 문자열용이라 여기 쓰면 엉뚱한 값이 나온다
   (2026-08-07: 티켓 날짜에 그걸 쓸 뻔했다). KST 로 옮겨 «8/7» 로 줄인다. */
function fmtIsoDay(iso) {
  const t = Date.parse(iso);
  if (!t) return "";
  const d = new Date(t + 9 * 3600 * 1000);
  return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
}

/* 진열대에 올리기 — 반쪽 시트지만 §3 «전면 폐지»의 예외가 아니다.
   입력이 세 칸뿐이고 «올린다»는 한 동작이라 화면을 새로 내는 것이 오히려 길이 길어진다. */
function storeAddSheet() {
  if (!S.storeAdd) return "";
  const a = S.storeAdd;
  return `
  <div class="modal sheetwrap" onclick="App.storeAddClose()">
    <div class="sheet" onclick="event.stopPropagation()">
      <div class="sheet-grip"></div>
      <div class="sheet-hd"><b>진열대에 올리기</b></div>
      <label class="st-f"><span>무엇과 바꿔 줄까요</span>
        <input id="st-title" type="text" maxlength="40" value="${esc(a.title)}"
          placeholder="예: 만화 30분 · 아이스크림" oninput="App.storeAddSet('title', this.value)"></label>
      <label class="st-f"><span>스타코인 몇 개</span>
        <input id="st-need" type="number" min="1" max="999" value="${a.need}"
          oninput="App.storeAddSet('need', this.value)"></label>
      <div class="st-f"><span>얼마나 자주 바꿀 수 있나요</span>
        <div class="st-lims">
          ${[["", "제한 없음"], ["weekly", "주에 n번"], ["monthly", "달에 n번"]].map(([v, ko]) => `
            <button class="st-lim-b ${a.limitType === v ? "on" : ""}"
              onclick="App.storeAddSet('limitType', '${v}')">${ko}</button>`).join("")}
        </div>
        ${!a.limitType ? "" : `
        <input class="st-cnt" type="number" min="1" max="99" value="${a.limitCount}"
          oninput="App.storeAddSet('limitCount', this.value)" aria-label="횟수">`}
      </div>
      <div class="sheet-act nodel">
        <button class="act-cancel" onclick="App.storeAddClose()">그만두기</button>
        <button class="act-del" style="background:var(--accent);color:var(--on-accent)"
          onclick="App.storeAddSave()">올리기</button>
      </div>
    </div>
  </div>`;
}

/* 4자리 키패드 — **브라우저 alert 금지**(§11-5). 안내도 이 안에서 한 줄로 말한다. */
function pinPadView() {
  if (!S.pinPad) return "";
  const title = S.pinPad === "unlock" ? "부모 모드로 나가기"
    : S.pinPad === "clear" ? "번호 지우기"
    : S.pinHas && !S.pinPrev ? "지금 쓰는 번호" : "쓸 번호 네 자리";
  const locked = S.pinPad === "unlock" && S.pinLockFor > 0;
  return `
  <div class="modal pinwrap">
    <div class="pin">
      <b class="pin-t">${title}</b>
      <div class="pin-dots" aria-hidden="true">
        ${[0, 1, 2, 3].map((i) => `<i class="${i < S.pinBuf.length ? "on" : ""}"></i>`).join("")}
      </div>
      <p class="pin-msg ${S.pinMsg ? "bad" : ""}">${S.pinMsg ? esc(S.pinMsg) : "숫자 네 자리를 눌러요"}</p>
      <div class="pin-keys">
        ${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `
          <button class="pin-k" ${locked ? "disabled" : ""} onclick="App.pinTap(${n})">${n}</button>`).join("")}
        <button class="pin-k ghost" onclick="App.pinClose()">그만</button>
        <button class="pin-k" ${locked ? "disabled" : ""} onclick="App.pinTap(0)">0</button>
        <button class="pin-k ghost" onclick="App.pinBack()" aria-label="지우기">
          <i aria-hidden="true" class="ti ti-x"></i></button>
      </div>
    </div>
  </div>`;
}

/* 부모가 1초 만에 고르는 칭찬 스티커 (§5⑤) */
function reactSheetView() {
  if (!S.reactSheet) return "";
  return `
  <div class="modal sheetwrap" onclick="App.reactClose()">
    <div class="sheet" onclick="event.stopPropagation()">
      <div class="sheet-grip"></div>
      <div class="sheet-hd"><b>칭찬 보내기</b></div>
      <div class="rc-picks">
        <button class="rc-p" onclick="App.reactSend('thumb_up')"><span>👍</span>잘했어</button>
        <button class="rc-p" onclick="App.reactSend('heart')"><span>❤️</span>사랑해</button>
      </div>
    </div>
  </div>`;
}

/* 아이 화면에 뜨는 큰 칭찬 팝업 — «받았다»는 순간이 이 앱의 봉우리다 */
function stickerView() {
  const s = S.kidSticker;
  if (!s) return "";
  const face = s.sticker_type === "heart" ? "❤️" : s.sticker_type === "bonus_approved" ? "🏅" : "👍";
  const word = s.sticker_type === "bonus_approved" ? "보너스를 받았어요!" : "엄마아빠가 칭찬했어요!";
  return `
  <div class="modal stwrap" onclick="App.stickerClose()">
    <div class="stick">
      <div class="stick-face" aria-hidden="true">${face}</div>
      <b>${word}</b>
      ${s.bonus_stars > 0 ? `<em class="stick-star">★ ${s.bonus_stars}</em>` : ""}
      <button class="btn-primary" onclick="App.stickerClose()">고마워요</button>
    </div>
  </div>`;
}

function subHeader(title, sub) {
  /* ⚠ 뒤로가기가 **항상 홈으로** 가고 있었다(대표님 지적 08-08).
     두 단계 들어갔다가 한 번 누르면 처음으로 튕겨 나와서, 되돌아가려면 다시 두 번을 눌러야 했다.
     이제 «한 걸음 뒤로»다 — 갈 곳이 없을 때만 홈으로 간다(App.goBack). */
  return `
  <div class="sub-top">
    <button class="sub-back" onclick="App.goBack()" aria-label="뒤로">
      <i aria-hidden="true" class="ti ti-chevron-left"></i></button>
    <h1 class="sub-t">${title}${sub ? `<em>${sub}</em>` : ""}</h1>
  </div>`;
}

/* ═══ ☰ 드로어 (2026-08-03 지시서 0803-1 §1) ═══════════════════
   순서가 곧 뜻이다 — 맨 위가 «누구 것을 보고 있나»(자녀 전환),
   그 아래가 상시 메뉴, 맨 아래 작게 내 정보·설정.
   당일 것(오늘·달력·미션)은 여기 없다. 그건 홈과 하단 3버튼이 진다. */
function drawerView(c) {
  /* 아이 모드에서는 서랍이 아예 열리지 않는다 (§5④) — 여는 버튼만 감추면 제스처로 열린다 */
  if (S.kidMode) return "";
  if (!S.drawer) return "";
  const undone = STUB.documents.filter((d) => d.kind === "field" && !d.reported).length;
  const unread = unreadFor("parent");
  /* 그룹 배치 (2026-08-07 마이다이어리 벤치마킹) — 홈에서 뺀 보상 화면들의 정식 입구가 여기다.
     학교(매일 보는 것) → 보상(스타코인 경제) → 소통(오가는 것) 순. ⚠ 아이콘은 서브셋에 있는 것만 */
  const GROUPS = [
    ["학교", [
      ["ti-archive",   "서랍",     "location.hash='#timeline'", ""],
      ["ti-table",     "시간표",   "location.hash='#timetable'", ""],
      ["ti-tools-kitchen-2", "급식", "location.hash='#meal'", ""],
      ["ti-school",    "학교정보", "location.hash='#schoolinfo'", ""],
    ]],
    ["보상", [
      ["ti-discount",  "스타코인 상점", "location.hash='#store'", ""],
      ["ti-receipt",   "내 티켓",   "location.hash='#tickets'", ""],
      ["ti-user",      "아이 모드", "location.hash='#childmode'", ""],
    ]],
    ["소통", [
      ["ti-file-text", "서류",     "location.hash='#docs'", undone ? String(undone) : ""],
      ["ti-message-circle", "대화", "location.hash='#notify'", unread ? String(unread) : ""],
      ["ti-messages",  "커뮤니티", "location.hash='#community'", ""],
    ]],
  ];
  /* 사용기한 줄 — 결제를 붙이기 전이라 **자리만** 잡아 둔다(§4).
     ⚠ 없는 기능을 있는 것처럼 눌리게 두지 않는다. 지금은 누를 수 없는 «표시»다. */
  const pass = passLabel(c);
  return `
  <div class="hv3-dim" onclick="App.drawerClose()">
    <nav class="hv3-drawer" onclick="event.stopPropagation()">
      <div class="hv3-drlogo"><span>★</span>아이서랍</div>

      <!-- ⚠ 아이가 없으면(구경 중) 여기서 자녀 이름을 읽다가 **서랍이 통째로 안 열렸다**
           (2026-08-04 실측). 그 자리에 «아이 등록하기»를 둔다 — 가입 길이 여기 하나면 족하다.
           ⚠ 이 주석에 역따옴표를 쓰지 말 것 — 템플릿 문자열 안이라 그 자리에서 문법이 깨진다. -->
      ${c ? `<button class="hv3-drwho" onclick="App.drawerClose();location.hash='#switch'">
        ${childFace(c, "hd-face")}
        <span class="nm"><b>${esc(c.nickname)}</b><em>${[esc(schoolName(c)), c.grade ? `${c.grade}학년` : ""].filter(Boolean).join(" · ")}</em></span>
        <i aria-hidden="true" class="ti ti-chevron-right"></i>
      </button>

      <div class="hv3-drpass">${esc(pass?.t || "무료 사용 중")}</div>`
      : `<button class="hv3-drwho" onclick="App.drawerClose();location.hash='#register'">
        <span class="nm"><b>아이 등록하기</b></span>
        <i aria-hidden="true" class="ti ti-chevron-right"></i>
      </button>`}

      <button class="hv3-dritem" onclick="App.drawerClose();location.hash='#theme'">
        <i aria-hidden="true" class="ti ti-palette"></i>테마</button>

      <div class="hv3-drhr"></div>

      <div class="hv3-drscroll">
        ${GROUPS.map(([cap, items], gi) => `
          ${gi ? `<div class="hv3-drhr"></div>` : ""}
          <div class="hv3-drcap">${cap}</div>
          ${items.map(([ic, nm, go, bd]) => `
          <button class="hv3-dritem" onclick="App.drawerClose();${go}">
            <i aria-hidden="true" class="ti ${ic}"></i>${nm}
            ${bd ? `<span class="hd-badge" style="position:static;margin-left:auto">${bd}</span>` : ""}</button>`).join("")}`).join("")}
      </div>
      <div class="hv3-drfoot">
        <button class="hv3-dritem sub" onclick="App.drawerClose();location.hash='#mypage'">
          <i aria-hidden="true" class="ti ti-settings"></i>내 정보 · 설정</button>
      </div>
    </nav>
  </div>`;
}

/* ⚠ ＋ 퀵입력 «반쪽 시트»는 폐지했다(2026-08-03 §3 «팝업·반쪽 시트 전면 폐지»).
   같은 일을 **전체 화면 편집기**(Screens.edit)가 한다 — 날짜를 미니 달력으로 고르고
   시간·반복 칩까지 한 화면에서 끝난다. 시트는 화면의 절반을 가려서 «지금 뭘 고르는지»가 안 보였다. */
/* ═══ 코치마크 (§5) ═══════════════════════════════════════════
   새 화면을 **한 번만** 짚어 준다. 기존 사용자는 설문 없이 이것만 본다.
   마지막 장은 설명이 아니라 «첫 행동»이다 — 미션 하나를 실제로 내보게 한다. */
/* 첫 장은 설문 ③(need)에 따라 갈린다 — 「제일 필요하다」고 한 것을 제일 먼저 짚어 준다 */
const COACH_FIRST = {
  school: { t: "학교에서 오는 건 여기 모여요", p: "급식 · 시간표 · 학사일정이 자동으로 들어와요. 눌러서 자세히 볼 수 있어요." },
  habit:  { t: "아이 습관은 이 줄에서", p: "미션 도장이 여기 쌓여요. 아이가 해내면 «확인해 주세요»가 뜹니다." },
  record: { t: "기록은 오른쪽 위 서랍에", p: "상장 · 통지표는 사진 한 장이면 끝. 12년치가 학년별로 쌓여요." },
};
const COACH = [
  { t: "오늘 하루가 여기 다 있어요", p: "급식 · 시간표 · 일정 · 내일 준비물까지. 눌러서 자세히 볼 수 있어요.", spot: ".hv3-grp" },
  { t: "아래 세 개만 기억하세요", p: "왼쪽은 달력, 가운데 ＋는 새로 넣기, 오른쪽 별은 미션이에요.", spot: ".hv3-fab" },
  { t: "나머지는 ☰ 안에", p: "서랍 · 시간표 · 급식 · 학교정보 · 서류 · 대화 · 커뮤니티가 들어 있어요.", spot: ".hv3-ham" },
  { t: "달력과 하루는 옆으로 밀어요", p: "달력에서 밀면 달이 넘어가고, 하루 화면에서 밀면 날짜가 넘어가요. 항목을 꾹 누르면 고칠 수 있어요.", spot: ".hv3-cal" },
  { t: "미션 하나 내볼까요?", p: "아이가 해내면 도장이 찍혀요. 지금 하나만 내보면 감이 와요.", spot: ".hv3-star", cta: "미션 내보기" },
];
function coachView() {
  const i = S.coach;
  if (i === null || i === undefined) return "";
  let c = COACH[i];
  if (!c) return "";
  // 첫 장만 설문 답으로 갈아 끼운다 — 자리(spot)는 그대로다
  if (i === 0) {
    const v = COACH_FIRST[(S.onboard || {}).need];
    if (v) c = { ...c, ...v, spot: (S.onboard.need === "record") ? ".hd-box" : c.spot };
  }
  const last = i === COACH.length - 1;
  /* 구멍은 실제 요소 자리에 낸다 — 좌표를 손으로 박으면 화면 크기가 달라질 때 엉뚱한 곳을 짚는다.
     요소를 못 찾으면(그 카드가 꺼져 있으면) 구멍 없이 설명만 띄운다. */
  const el = document.querySelector(c.spot);
  const r = el?.getBoundingClientRect();
  const pad = 8;
  const hole = r ? `<div class="cm-hole" style="left:${Math.max(4, r.left - pad)}px;top:${Math.max(4, r.top - pad)}px;
    width:${r.width + pad * 2}px;height:${r.height + pad * 2}px"></div>` : "";
  const below = !r || r.top < window.innerHeight / 2;
  const pos = below ? `top:${r ? Math.min(window.innerHeight - 210, r.bottom + 16) : 120}px` : `bottom:${window.innerHeight - r.top + 16}px`;
  return `
  <div class="cm-dim" onclick="App.coachNext()">
    ${hole}
    <div class="cm-card" style="${pos}" onclick="event.stopPropagation()">
      <b>${c.t}</b><p>${c.p}</p>
      <div class="cm-act">
        <span class="cm-dots">${COACH.map((_, k) => `<i class="${k === i ? "on" : ""}"></i>`).join("")}</span>
        <button class="cm-skip" onclick="App.coachDone()">${last ? "나중에" : "건너뛰기"}</button>
        <button class="cm-next" onclick="${last ? "App.coachDone();App.missionPickOpen()" : "App.coachNext()"}">${c.cta || "다음"}</button>
      </div>
    </div>
  </div>`;
}

function nowDoing() {
  const d = new Date();
  const wd = d.getDay();
  if (wd === 0 || wd === 6) return null;
  const tt = ttOf();
  const grid = tt.grid || [];
  /* ⚠ **방학·휴업일이면 수업이 없다.** 시간표는 지난 학기 것이 그대로 남아 있어서,
     이 검사를 빼면 방학 중 오전 10시에 「3교시 국어」라고 말한다 —
     이 화면에서 제일 하면 안 되는 일이 «없는 일을 있다고 하는 것»이다(2026-07-28 사장님 지적).
     방학에도 학원은 간다. 그래서 **수업만 끄고 학원은 그대로 본다.** */
  const onBreak = !!vacationRanges().find(([a0, b0]) => TODAY >= a0 && TODAY < b0)
    || schedulesOf().some((e) => e.date === TODAY && (e.closure_type || "").includes("휴업"));
  const hasClass = !onBreak && grid.some((row) => row.some((v) => v));
  const now = d.getHours() * 60 + d.getMinutes();
  const L = lunchOf();
  const left = (m) => (m >= 60 ? `${Math.floor(m / 60)}시간 ${m % 60 ? `${m % 60}분` : ""}`.trim() : `${m}분`);
  const col = wd - 1;
  const subj = (r) => (grid[r] && grid[r][col]) ? shortSubject(S.ttOverrides[`${r}-${col}`] ?? grid[r][col]) : "";

  const acts = STUB.activities
    .filter((a) => String(a.days_of_week || "").split(",").includes(String(wd)))
    .sort((x, y) => String(x.start_time).localeCompare(String(y.start_time)));
  const inAct = acts.find((a) => a.start_time && a.end_time && now >= toMin(a.start_time) && now < toMin(a.end_time));
  if (inAct) return { t: `${esc(inAct.name)} 중`, s: `${esc(inAct.end_time)}까지`, k: "act" };

  if (hasClass) {
    for (let r = 0; r < grid.length; r++) {
      const p = STUB.periods[r];
      if (!p || !p.start || !p.end) continue;
      const a0 = toMin(p.start), b0 = toMin(p.end);
      if (now >= a0 && now < b0) {
        const v = subj(r);
        return { t: v ? `${r + 1}교시 ${esc(v)}` : `${r + 1}교시`, s: `${esc(p.end)}까지 ${left(b0 - now)}`, k: "class" };
      }
      const np = STUB.periods[r + 1];
      if (np && np.start && now >= b0 && now < toMin(np.start)) {
        if (now >= toMin(L.start) && now < toMin(L.end)) {
          return { t: "점심시간", s: `${esc(L.end)}까지 ${left(toMin(L.end) - now)}`, k: "lunch" };
        }
        const v = subj(r + 1);
        return { t: "쉬는 시간", s: `${left(toMin(np.start) - now)} 뒤 ${r + 2}교시${v ? ` ${esc(v)}` : ""}`, k: "rest" };
      }
    }
    if (now >= toMin(L.start) && now < toMin(L.end)) {
      return { t: "점심시간", s: `${esc(L.end)}까지 ${left(toMin(L.end) - now)}`, k: "lunch" };
    }
    const first = STUB.periods[0];
    if (first && first.start && now < toMin(first.start)) {
      const v = subj(0);
      return { t: "등교 전", s: `${esc(first.start)} 1교시${v ? ` ${esc(v)}` : ""}`, k: "before" };
    }
  }

  const next = acts.find((a) => a.start_time && toMin(a.start_time) > now);
  if (next) {
    // 방학엔 «하교»가 틀린 말이다 — 학교를 안 갔다. 학원 이름만 말한다.
    return onBreak
      ? { t: esc(next.name), s: `${esc(next.start_time)} · ${left(toMin(next.start_time) - now)} 뒤`, k: "out" }
      : { t: "하교", s: `${left(toMin(next.start_time) - now)} 뒤 ${esc(next.name)}`, k: "out" };
  }
  if (!acts.length) return onBreak ? { t: "방학", s: "오늘 학원 없음", k: "done" } : (hasClass ? { t: "오늘 일정 끝", s: "", k: "done" } : null);
  return { t: "오늘 일정 끝", s: `${esc(acts[acts.length - 1].name)}까지 마쳤어요`, k: "done" };
}

function nowCard() {
  const n = nowDoing();
  if (!n) return "";
  return `
  <button class="nowbar ${n.k}" onclick="location.hash='#timetable'">
    <i></i><b>${n.t}</b>${n.s ? `<em>${n.s}</em>` : ""}
  </button>`;
}

function promoteCard(c) {
  const p = needPromote(c);
  if (!p) return "";
  return `
  <button class="hm-promote" onclick="App.promoteOpen(${p.to})">
    <b>${esc(c.nickname)}가 ${p.to}학년이 됐어요</b>
    <em>반을 알려주세요<i aria-hidden="true" class="ti ti-chevron-right"></i></em>
  </button>`;
}
function promoteSheet() {
  const d = S.promote;
  if (!d) return "";
  return `
  <div class="modal sheetwrap" onclick="App.promoteCancel()">
   <div class="sheet" onclick="event.stopPropagation()">
    <div class="sheet-grip"></div>
    <div class="sheet-hd"><b>${d.to}학년 몇 반인가요?</b><span>학년은 올렸어요</span></div>
    <div class="lunch-after">
      ${Array.from({ length: 15 }, (_, i) => i + 1).map((n) => `
        <button class="${String(d.class_name) === String(n) ? "on" : ""}" onclick="App.promotePick(${n})">${n}반</button>`).join("")}
    </div>
    <div class="sheet-act nodel">
      <button class="act-cancel" onclick="App.promoteCancel()">나중에</button>
      <button class="act-save" onclick="App.promoteSave()">저장</button>
    </div>
   </div>
  </div>`;
}

function planKillView() {
  const k = S.planKill;
  if (!k) return "";
  const a = STUB.activities.find((x) => x.id === k.id);
  const days = a ? String(a.days_of_week || "").split(",").filter(Boolean).map((n) => DAY_KO[+n - 1]).join(" ") : "";
  return `
  <div class="killwrap">
    <div class="killcard">
      <div class="kill-hd"><b>이 일정을 지울까요?</b></div>
      <div class="kill-what" style="--tag:${planColor(a?.color).v}">
        <i></i>
        <div>
          <b>${esc(k.name)}${days ? ` · 매주 ${days}` : ""}</b>
          ${a ? `<span>${esc(a.start_time || "")}${a.end_time ? ` – ${esc(a.end_time)}` : ""}</span>` : ""}
        </div>
      </div>
      <div class="kill-act">
        <button class="act-cancel" onclick="App.planKillCancel()">두기</button>
        <button class="act-kill" onclick="App.planKillDo()">지우기</button>
      </div>
    </div>
  </div>`;
}

// ── 급식 — 주간·월간 · 알레르기 알람 · 메뉴 검색 ─────────────
// 지시(2026-07-24): 한 달치를 받아와서, 알레르기 있는 날을 미리 알람 걸 수 있게.
// 검색으로 특정 메뉴가 나오는 날을 찾아서도 알람을 걸 수 있게.
const fmtDate = (d) => `${+d.slice(4, 6)}/${+d.slice(6)}`;
// 학년도 — 3월 시작. 1~2월은 전년도 학년도다(서버와 같은 규칙).
const schoolYearOf = (t) => { const y = +t.slice(0, 4), m = +t.slice(4, 6); return String(m < 3 ? y - 1 : y); };
const ymdDash = (d) => `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6)}`;   // 20260512 → 2026-05-12 (input[type=date]용)
// 서식 이름 — 실제 학교 양식 제목 그대로
const docTitle = () => ({
  field: S.docPhase === "report" ? "교외(개인)체험학습 보고서" : "교외체험학습 신청서",
  absence: "결석신고서", counsel: "학부모 상담 신청서",
}[S.docKind] || "서류");
const weekdayKo = (d) => ["일", "월", "화", "수", "목", "금", "토"][new Date(+d.slice(0, 4), +d.slice(4, 6) - 1, +d.slice(6)).getDay()];

/* ═══ 서류 미리보기 = 진짜 종이 (2026-07-25 지시: "문서 미리보기처럼 제대로, 한 화면에")
   ─────────────────────────────────────────────────────────────
   근거: 대표님이 주신 학교 서식 4종(에듀싱크\*.hwp, 2026학년도 서울숭미초).
   HWP 본문을 그대로 뽑아 제목·결재란·표 칸·안내문·서명줄 위치를 옮겼다.
   앞으로 문구를 고칠 일이 있으면 **hwp를 다시 뽑아서** 맞춘다 — 기억으로 고치지 말 것.
     추출: python scratchpad\hwp_dump.py (olefile + zlib -15, HWPTAG_PARA_TEXT=67)

   화면은 A4 비율 한 장을 통째로 축소해 **한 화면에** 넣는다(render에서 scale 계산).
   읽을 땐 «크게 보기»로 원래 크기. 출력·PDF는 이 DOM을 그대로 쓴다.
   ═══════════════════════════════════════════════════════════ */
const dY = (s) => (s ? `${+s.slice(0, 4)}년 ${+s.slice(5, 7)}월 ${+s.slice(8, 10)}일` : "년    월    일");
// 손으로 적어 넣은 값 — 서식에 들어가는 건 전부 사람이 쓴 글이라 여기서 이스케이프한다
const W = (v) => `<span class="w">${escBr(v)}</span>`;
// 아이콘 이름은 반드시 **통째로** 쓴다. 이름 뒷부분을 template로 만들어 붙이면
// 폰트 서브셋 스크립트가 그 이름을 못 찾아 그 아이콘만 빈칸이 된다(tools/build-icons.mjs가 막는다).
const CK = (on, label) => `<span class="ck"><i class="ti ${on ? "ti-square-check" : "ti-square"}"></i>${label ? " " + label : ""}</span>`;
const 결재란 = `
  <table class="appr">
    <tr><td class="vt" rowspan="2">결재</td><td>담 임</td><td>학년부장</td><td>전결</td></tr>
    <tr><td></td><td></td><td></td></tr>
  </table>`;

function docPaper() {
  const c = curView();
  const d = S.docDraft || {};
  const k = S.docKind, isReport = S.docPhase === "report";
  const school = schoolName(c);
  const guardian = STUB.me.account.display_name;
  const 기간 = `${dY(d.from)} ~ ${dY(d.to)}　기간 중 (${d.days ?? ""})일간`;
  const 서명 = `
    <div class="sign">학　　생　${W(c.nickname)}</div>
    <div class="sign">학 부 모　${W(guardian)}　(인)</div>`;
  // 학교명이 비면 «장 귀하»가 된다 — 인쇄해서 손으로 적을 수 있게 밑줄 자리를 준다
  const 귀하 = `<p class="to">${school ? esc(school) : `<span class="w">&nbsp;</span>`}장 귀하</p>`;

  // ── 교외체험학습 신청서 ───────────────────────────────
  if (k === "field" && !isReport) {
    const plans = (d.planDays || []).filter((p) => p.text);
    return `
    <div class="pghd"><div class="pgtitle">2026학년도 교외체험학습 신청서</div>${결재란}</div>
    <p class="pgnote">※ 교육적 활동 내용으로, 펜으로 작성, 반일 체험학습은 조퇴 또는 등교 시간 기록(3일 전 제출)</p>
    <table class="fm">
      <tr><td class="lb vt" rowspan="2">인적<br>사항</td><td class="lb">성명</td><td>${W(c.nickname)}　( ${d.sex === "남" ? "<b>남</b>" : "남"} · ${d.sex === "여" ? "<b>여</b>" : "여"} )</td>
          <td class="lb">학년-반</td><td>${W(`${c.grade} - ${c.class_name}`)}</td></tr>
      <tr><td class="lb">주소</td><td colspan="3">${W(d.addr)}</td></tr>
      <tr><td class="lb">기간</td><td colspan="4">${W(기간)}
          <div class="tiny">※( )일에는 공휴일 및 학교 자율휴업일을 제외한 학교 출석을 안 하는 날 수만 입력</div></td></tr>
      <tr><td class="lb">장소</td><td colspan="4">${W(d.place)} <span class="tiny">(시·도 기재)</span></td></tr>
      <tr><td class="lb">보호자<br>동행 확인</td><td colspan="4">
          학생 안전 확보를 위하여 반드시 보호자(친권자 및 후견인, 사실상의 보호자) 또는 친족 성인이 동행합니다.
          <div class="cks">${CK(d.accompany === "예", "예,")}　${CK(d.accompany === "아니오", "아니오")}
            <span class="tiny">(아니오의 경우 교외체험학습을 허가할 수 없음)</span></div></td></tr>
      ${d.safety || d.emergency ? `
      <tr><td class="lb">연속 5일<br>초과 시만<br>-안전 확인</td><td colspan="4">
          연속 5일을 초과 시(재량휴업일, 토요일, 공휴일 제외) 학생 안전을 위해 기간 중 1회 이상 반드시 학생이 담임 교사에게 연락하겠습니다.
          <div class="cks">${CK(!!d.safety, "확인하였습니다.")} <span class="tiny">(확인하지 않을 경우 교외체험학습을 허가할 수 없음)</span></div>
          <div class="cks">상시 연락이 가능한 비상 연락처　${W(d.emergency)}</div></td></tr>` : ""}
      <tr><td class="lb vt" rowspan="${plans.length + 1}">학습<br>계획</td><td class="lb">월 일</td>
          <td class="lb" colspan="3">학습할 내용(교육활동 내용이 드러나도록 구체적으로 상세하게 작성)</td></tr>
      ${plans.map((p) => `<tr><td>${W(p.date)}</td><td colspan="3">${W(p.text)}</td></tr>`).join("")
        || `<tr><td>&nbsp;</td><td colspan="3"></td></tr>`}
    </table>
    <p class="stmt">위와 같이 체험학습을 신청하고자 합니다.</p>
    <p class="pgdate">2026.　　.　　.</p>
    ${서명}${귀하}`;
  }

  // ── 교외(개인)체험학습 보고서 ─────────────────────────
  if (k === "field" && isReport) {
    return `
    <div class="pghd"><div class="pgtitle">교외(개인)체험학습 보고서</div></div>
    <p class="pgnote">※ 체험학습 실시 후 7일 이내 제출함</p>
    <table class="fm">
      <tr><td class="lb">학습자</td><td>제 ${W(c.grade)} 학년 ${W(c.class_name)} 반 　 번</td>
          <td class="lb">성명</td><td>${W(c.nickname)}</td></tr>
      <tr><td class="lb">학습일시</td><td colspan="3">${W(기간)}</td></tr>
      <tr><td class="lb vt">체험학습<br>내용</td><td colspan="3" class="big">
          <div class="tiny">(※ 교외체험학습 교육활동 내용이 잘 드러나도록 상세하게 작성합니다.)</div>
          ${W(d.did)}</td></tr>
    </table>
    <p class="stmt">위와 같이 교외체험학습을 하였음을 보고합니다.</p>
    <p class="pgdate">2026.　　.　　.</p>
    ${서명}${귀하}
    <p class="pgnote">※ 체험학습 실시후 7일 이내 제출함(7일 이내 제출하지 않은 경우 ‘미인정 결석처리’됨)</p>`;
  }

  // ── 결석신고서 ────────────────────────────────────────
  if (k === "absence") {
    const t = d.absKind || "sick";
    const days = d.days ?? 0;
    return `
    <div class="pghd"><div class="pgtitle">2026학년도 결석신고서</div>${결재란}</div>
    <table class="fm">
      <tr><td class="lb">학생명</td><td>${W(c.nickname)}</td><td class="lb">학년 반</td><td>${W(c.grade)} 학년 ${W(c.class_name)} 반　번</td>
          <td class="lb">성별</td><td>${d.sex === "남" ? "<b>남</b>" : "남"} / ${d.sex === "여" ? "<b>여</b>" : "여"}</td></tr>
      <tr><td class="lb">기 간</td><td colspan="5">${W(`${dY(d.from)} ～ ${dY(d.to)} (${days}일간)`)}</td></tr>
      <tr><td class="lb vt">결석<br>사유</td><td colspan="5" class="mid">${W(d.reason)}
          <div class="tiny">※병명 또는 사유 구체적으로 기재</div></td></tr>
      <tr><td class="lb vt" rowspan="4">증빙<br>서류</td>
          <td class="lb vt">출석인정<br>결석</td><td colspan="4">
            ${CK(t === "official", "감염병 — 질병명·기간이 확인 가능한 서류(의사소견서·진료확인서·진단서 등)")}<br>
            ${CK(false, "학생선수 — 공문·훈련계획서·결과보고서")}　${CK(false, "생리통(월 1회)")}　${CK(false, "천재지변")}</td></tr>
      <tr><td class="lb">경조사</td><td colspan="4">${CK(t === "family", "관련 증빙자료(청첩장·부고장 등)")}
            ${d.family ? `　→ ${W(d.family)}` : ""}
            <div class="tiny">결혼: 형제⋅자매·부·모 1일 / 사망: 부모·조부모·외조부모 5일, 부모의 (외)조부모·형제자매 및 그 배우자 3일 / 입양: 본인 20일</div></td></tr>
      <tr><td class="lb">질병결석</td><td colspan="4">
            ${CK(t === "sick" && days <= 2, "2일 이내 — 처방전·약봉투·진료확인서 또는 담임 확인")}<br>
            ${CK(t === "sick" && days >= 3, "3일 이상 — 의사의 진단서 또는 의견서")}
            <div class="tiny">※ 인정되지 않는 서류: 약봉투, 처방전 등</div></td></tr>
      <tr><td class="lb">기타·미인정</td><td colspan="4">
            ${CK(t === "etc", "기타 결석 — 담임 교사와 별도 상의 필요")}　${CK(t === "none", "미인정 결석")}
            ${d.proof ? `<div class="cks">증빙: ${W(d.proof)}</div>` : ""}
            <div class="tiny">※ 연속 3일 이상 미인정 결석 시 소재·안전 파악을 위한 면담·가정방문·경찰 협조 요청이 이루어집니다.</div></td></tr>
      <tr><td class="lb vt">안내<br>사항</td><td colspan="5" class="tiny left">
          ※ 결석 사유 해당 칸에 √표시를 한 후 결석신고서와 증빙서류를 결석일부터 5일 이내 제출<br>
          ※ 기간은 주말·공휴일 등을 제외하고 실제 결석한 날수로 작성합니다.<br>
          ※ 수정이 불가능한 펜류로 작성하고, 수정액 사용을 삼가주시기 바랍니다.</td></tr>
    </table>
    <p class="stmt">위와 같이 결석신고서를 제출합니다.</p>
    <p class="pgdate">2026.　　.　　.</p>
    <div class="sign">학 부 모　${W(guardian)}　(인)</div>${귀하}`;
  }

  // ── 학부모 상담 신청서 ────────────────────────────────
  const w = d.wish || [{}, {}, {}];
  return `
  <div class="pghd"><div class="pgtitle">2026학년도 학부모 상담 신청서</div></div>
  <table class="fm">
    <tr><td class="lb">학생 이름</td><td>${W(c.nickname)}</td><td class="lb">학년 반</td><td>${W(c.grade)} 학년 ${W(c.class_name)} 반</td></tr>
    <tr><td class="lb">보호자 연락처</td><td>${W(d.phone)}</td><td class="lb">학생과의 관계</td><td>${W(d.relation)}</td></tr>
    <tr><td class="lb">상담 가능 시간</td><td colspan="3">${STUB.counselHours[c.grade] || ""}
        <div class="tiny">※ 학교 안전 관리의 이유로 야간 상담은 하지 않음을 양해 부탁드립니다.</div></td></tr>
    <tr><td class="lb vt" rowspan="2">상담<br>희망 시간</td>
        ${[0, 1, 2].map((i) => `<td class="lb">${i + 1}희망</td>`).join("")}</tr>
    <tr>${[0, 1, 2].map((i) => `<td>${W(w[i]?.when)}<div class="tiny">${w[i]?.how || "대면/비대면"}</div></td>`).join("")}</tr>
    <tr><td class="lb vt">상담 내용</td><td colspan="3" class="big">
        <div class="tiny">※ 상담을 신청하시는 이유와 자녀에 관한 부모님의 의견을 적어주세요.</div>
        ${W(d.note)}</td></tr>
  </table>
  <p class="stmt">위와 같은 내용으로 상담을 신청합니다.</p>
  <p class="pgdate">2026.　　.　　.</p>
  <div class="sign">보호자　${W(guardian)}　(인)</div>
  <p class="cutline"><i class='ti ti-scissors'></i>-------------------- (이하 담임교사 작성) --------------------</p>
  <p class="tiny left">담임 선생님이 확정하면 <b>상담 확정 통보서</b>로 일정·장소를 알려줍니다.</p>`;
}
// 그 날 급식에서 우리 아이 알레르기에 걸리는 코드들
const hitAllergens = (meal) => [...new Set(meal.dishes.flatMap((d) => d.allergens).filter((a) => S.myAllergens.includes(a)))];

function mealTab() {
  const q = S.mealQuery.trim();
  // 일반 학교는 중식만. 기숙사형이면 조식·석식까지 들어온다(웹과 같은 규칙 — 있는 끼니만 탭에 띄운다).
  /* ⚠ 예전엔 「기숙사형 학교」 스위치(S.dorm)를 **부모가 직접 켜야** 조식·석식이 보였다.
     그런데 그 스위치가 있는 줄 모르면 서울과학고처럼 세 끼를 다 주는 학교에서도
     점심만 보게 된다(2026-08-09 실측: 데이터는 47건인데 화면엔 점심뿐이었다).
     → **급식에 조식·석식이 있으면 알아서 켠다.** 스위치는 끄고 싶을 때만 쓴다.
     ⚠ 사용자가 직접 끈 경우(S.dormTouched)는 그 뜻을 존중한다. */
  const hasOther = mealsOf().some((m) => m.type === "조식" || m.type === "석식");
  if (hasOther && !S.dorm && !S.dormTouched) S.dorm = true;
  const types = [...new Set(mealsOf().map((m) => m.type))]
    .filter((t) => S.dorm || t === "중식")
    .sort((a, b) => MEAL_ORDER[a] - MEAL_ORDER[b]);
  const sel = types.includes(S.mealType) ? S.mealType : "중식";

  let days = mealsOf().filter((m) => m.type === sel);
  // 검색은 "그 메뉴 나오는 날 미리 알람"이 목적이라 주간에 가두면 뜻이 없다 → 검색 중엔 한 달 전체를 본다.
  if (S.mealRange === "week" && !q) {
    /* ⚠ findIndex 는 «오늘 이후 급식이 하나도 없으면» -1 을 준다.
       예전엔 Math.max(0, -1) 로 0 을 만들어서 **제일 오래된 주**를 이번 주인 양 보여줬다.
       방학이라 급식이 7/23에서 끊겼는데 화면엔 7/13 것이 떠 있었다(2026-07-27 실측).
       앞으로 올 급식이 없으면 **없다고 말한다.** 옛날 것을 슬쩍 보여주는 게 제일 나쁘다. */
    const i = days.findIndex((m) => m.date >= TODAY);
    days = i < 0 ? [] : days.slice(i, i + 5);       // 이번 주(오늘부터 5일치)
  }
  if (q) days = days.filter((m) => m.dishes.some((d) => d.name.includes(q)));

  const typeTabs = types.length > 1 ? `
    <div class="seg mealtypes">
      ${types.map((t) => `<button class="${sel === t ? "on" : ""}" onclick="App.mealType('${t}')">${MEAL_KOR[t]}</button>`).join("")}
    </div>` : "";

  /* 시안 10a (2026-07-28) — **메뉴가 주인이다.**
     예전엔 알레르기 상자와 검색창이 화면 절반을 먹고 정작 식단이 안 읽혔다.
     ① 알레르기 18종 고르기 · 메뉴 검색 · 지난 급식은 전부 **아래로 내리거나 접는다**
     ② 알레르기는 **걸린 메뉴에만** 점선 밑줄 + 11px 원인. 한 글자도 밀어내지 않는다
        (예전엔 빨간 상자가 한 줄 통째로 들어가 메뉴를 아래로 밀었다)
     ③ 끼니 알람은 날짜 줄 오른쪽 스위치. 「알람 켜짐」 같은 글자를 안 쓴다
     날짜별로 카드 하나 — 한 날에 중식·석식이 있으면 **같은 카드 안에서** 선으로 나눈다. */
  const byDate = [];
  days.forEach((m) => {
    const g = byDate.find((x) => x.date === m.date);
    (g ? g.meals : (byDate.push({ date: m.date, meals: [] }), byDate[byDate.length - 1].meals)).push(m);
  });
  const evOf = (d) => schedulesOf().find((e) => e.date === d && classifyEvent(e.name, e.closure_type));

  return `
  ${DEV_TOOLS ? `<div class="dormtoggle devtool">
    <label class="check"><input type="checkbox" ${S.dorm ? "checked" : ""} onchange="App.toggleDorm()">
      <span>기숙사형 학교로 보기 <b class="stub">개발용</b></span></label>
  </div>` : ""}
  ${typeTabs}

  <div class="ml-bar">
    ${[["week", "주간"], ["month", "월간"]].map(([k, n]) =>
      `<button class="ml-range ${S.mealRange === k ? "on" : ""}" onclick="App.mealRange('${k}')">${n}</button>`).join("")}
    <span class="ml-gap"></span>
    <button class="ml-alg" onclick="App.toggleAllergenBox()">
      ${S.myAllergens.length
        ? `<b>${S.myAllergens.map((a) => ALLERGEN_KO[a]).join(" · ")}</b> 표시`
        : `알레르기 고르기`}
    </button>
  </div>
  ${S.allergenOpen ? `
    <div class="ml-algbox">
      <div class="chips">
        ${Object.entries(ALLERGEN_KO).map(([code, name]) =>
          `<button class="chip ${S.myAllergens.includes(+code) ? "on" : ""}" onclick="App.toggleAllergen(${code})">${name}</button>`).join("")}
      </div>
    </div>` : ""}

  ${S.mealSearchOpen ? `<input class="ml-search" id="ml-q" placeholder="메뉴 이름 (예: 새우)" value="${esc(q)}"
           oninput="App.mealSearch(this.value)">` : ""}

  ${q
    ? `<div class="ml-lead">"${esc(q)}" — ${days.length}일</div>`
    : `<div class="ml-lead">${days.length
        ? (S.mealRange === "week" ? "이번 주" : "이번 달")
        : (mealsOf().length
            ? `방학 중 · 마지막 급식 ${fmtDate(mealsOf()[mealsOf().length - 1].date)}`
            : "아직 올라오지 않음")}</div>`}

  ${byDate.map((g) => {
    const ev = evOf(g.date);
    const key0 = `${g.date}|${g.meals[0].type}`;
    const on = S.mealAlarms.includes(key0);
    return `
    <div class="ml-day">
      <div class="ml-dhd">
        <b class="ml-dnum">${+g.date.slice(6)}</b>
        <span class="ml-dwd">${weekdayKo(g.date)}</span>
        ${ev ? `<span class="ml-dev">${esc(ev.name)}</span>` : ""}
        <span class="ml-gap"></span>
        <button class="ml-alarm ${on ? "on" : ""}" onclick="App.toggleMealAlarm('${jsq(key0)}')"
                aria-label="${fmtDate(g.date)} 알림 ${on ? "끄기" : "켜기"}">
          <i></i>${on ? `<em>${esc(S.remind?.evening || "18:00")} 알림</em>` : ""}
        </button>
      </div>
      ${g.meals.map((m, i) => `
        <div class="ml-meal ${i ? "sep" : ""}">
          <div class="ml-mhd"><b>${MEAL_KOR[m.type]}</b><span>${esc(m.calorie || "")}</span></div>
          <div class="ml-dishes">
            ${m.dishes.map((d) => {
              const bad = d.allergens.filter((a) => S.myAllergens.includes(a));
              const hit = q && d.name.includes(q);
              /* ⚠ NEIS 는 이름 뒤에 알레르기 번호를 «(5.6.12)» 로 붙여서 준다.
                 그걸 이름과 같은 크기로 두면 「호박잎된장국 (5.6.12)」이 한 덩어리로 읽혀
                 반찬 이름이 눈에 안 들어온다(대표님 지적 08-09).
                 → 번호를 떼어 작고 흐리게. 이름만 굵게 남긴다. */
              /* ⚠ NEIS 는 이름 앞뒤에 «*» 를 붙여 준다(자체 표기라 부모에겐 뜻이 없다).
                 서울과학고 급식에서 「*배추김치」처럼 그대로 노출됐다 — 걷어낸다. */
              const clean = String(d.name).replace(/^[*\s]+|[*\s]+$/g, "");
              const mm = clean.match(/^(.*?)\s*\(([\d.\s]+)\)\s*$/);
              const nm = mm ? mm[1] : clean;
              const no = mm ? mm[2].trim() : "";
              const kd = mealKind(nm);
              const body = `<i class="ml-kd k-${kd.k}" aria-hidden="true"></i>`
                + `${hit ? `<mark>${esc(nm)}</mark>` : esc(nm)}`
                + `${no ? `<em class="ml-no">${esc(no)}</em>` : ""}`
                + `<u class="ml-kdn">${kd.ko}</u>`;
              return bad.length
                ? `<span class="bad">${body}<i>${bad.map((a) => ALLERGEN_KO[a]).join("·")}</i></span>`
                : `<span>${body}</span>`;
            }).join("")}
          </div>
        </div>`).join("")}
    </div>`;
  }).join("")}

  <div class="ml-foot">
    <button onclick="App.mealRange('month')">지난 급식</button>
    <button onclick="App.mealSearchToggle()">${S.mealSearchOpen ? "검색 닫기" : "메뉴 검색"}</button>
  </div>

  <!-- 급식 화면이 **알림·알레르기 설정을 전담한다**(2026-08-03 §4).
       예전엔 알레르기는 여기, 급식 알림은 알림 화면에 있어 둘을 오갔다. 한 곳에 모은다. -->
  <!-- ⚠ 알레르기 고르기는 **이 화면 위쪽에 이미 있다**(App.toggleAllergen).
       여기에 또 만들면 같은 기능에 입구가 둘이 된다(§4 «기능당 입구 하나»). 알림만 여기 둔다. -->
  <div class="mp-sec">알림</div>
  <div class="mp-list">
    <label class="mp-row">
      <span class="mp-l">알레르기 아침 알림</span>
      <input type="checkbox" ${S.remind?.on ? "checked" : ""} onchange="App.remindToggle(this.checked)">
      <i class="mp-swt"></i>
    </label>
  </div>`;
}

// ── 커뮤니티 — 반 단위 짧은 글 ────────────────────────────
/* ── 커뮤니티 = 같은 반 학부모 오픈채팅 (2026-08-01 개편) ─────
   게시판을 접고 **채팅**으로 바꿨다. 규칙은 서버(api_life.js)와 짝이다.
     · 초등만 · 50자 · 30초에 한 번 · **참여한 시점부터만 보임**(이전 대화 안 보임)
     · 신고 = 신고한 사람 눈에서만 사라짐 / 서로 다른 3명이면 모두에게서 내려감 · 차단
   왜 짧고 느리게 만들었나: 감정글은 몇백 자다. 짧고 느리면 싸움이 안 붙는다.
   신고 1건 자동삭제는 안 쓴다 — 「신고 버튼이 곧 삭제 버튼」이 되어 악용된다(사장님 지적). */
const COMM_MAX = 50;

function communityTab() {
  const c = curView();

  // 아직 참여 전 — 규칙을 보여주고 동의를 받는다(구글 UGC 정책의 「작성 전 약관 동의」가 여기서 끝난다)
  if (!S.commJoined) {
    return `
    <div class="cm-intro">
      <span class="cm-ico"><i class='ti ti-messages'></i></span>
      <b>${c.grade}학년 ${c.class_name}반 학부모 대화</b>
      <p>준비물·분실물·급식처럼 <b>오늘 당장 궁금한 것</b>을 짧게 주고받는 곳이에요.</p>
      <ul class="cm-rules">
        <li>한 번에 <b>${COMM_MAX}자</b>까지, <b>30초에 한 마디</b>예요</li>
        <li><b>참여한 다음부터</b> 올라오는 대화가 보여요 — 이전 대화는 볼 수 없어요</li>
        <li>학년·반이 함께 보여요. 이름은 나오지 않아요</li>
        <li>특정 선생님·학생을 지목한 글은 <b>신고 몇 번에 바로 내려갑니다</b></li>
      </ul>
      <button class="btn-primary" onclick="App.commJoin()" ${S.commBusy ? "disabled" : ""}>
        ${S.commBusy ? "들어가는 중…" : "동의하고 참여하기"}</button>
    </div>`;
  }

  const rows = S.commPosts || [];
  return `
  <div class="cm-wrap">
    <div class="cm-hd">
      <span>${c.grade}학년 ${c.class_name}반 · ${COMM_MAX}자 · 30초에 한 마디</span>
      <button class="cm-leave" onclick="App.commLeaveAsk()">나가기</button>
    </div>

    <div class="cm-log" id="cm-log">
      ${rows.length ? rows.map((p) => `
        <div class="cm-msg ${p.mine ? "mine" : ""}">
          ${p.mine ? "" : `<b>${esc(p.display_name || "학부모")}</b>`}
          <span class="cm-bub" ${p.mine ? "" : `onclick="App.commMenu(${p.id})"`}>${esc(p.body)}</span>
          <i>${hhmm(p.created_at)}</i>
        </div>`).join("")
      : `<p class="cm-empty">지금부터 올라오는 대화가 보여요.<br>먼저 한 마디 건네보세요.</p>`}
    </div>

    <div class="cm-bar">
      <input id="cm-input" maxlength="${COMM_MAX}" placeholder="궁금한 걸 짧게 물어보세요"
        value="${esc(S.communityDraft)}" oninput="App.commDraft(this.value)"
        onkeydown="if(event.key==='Enter')App.communityPost()">
      <em class="cm-cnt ${S.communityDraft.length >= COMM_MAX ? "full" : ""}">${S.communityDraft.length}/${COMM_MAX}</em>
      <button class="iconbtn" onclick="App.communityPost()" aria-label="보내기"><i class='ti ti-send'></i></button>
    </div>
  </div>

  ${S.commMenuFor ? `
  <div class="modal sheetwrap" onclick="App.commMenuClose()">
    <div class="sheet" onclick="event.stopPropagation()">
      <div class="sheet-grip"></div>
      <div class="sheet-hd"><b>이 대화</b><span>불편하면 가려드릴게요</span></div>
      <div class="sheet-act nodel" style="flex-direction:column;gap:8px">
        <button class="btn-line" onclick="App.commReport()">신고하기 — 내 화면에서 바로 사라져요</button>
        <button class="btn-line" onclick="App.commBlock()">이 사람 차단 — 앞으로 안 보여요</button>
        <button class="act-cancel" onclick="App.commMenuClose()">취소</button>
      </div>
    </div>
  </div>` : ""}

  ${S.commLeaveAsk ? `
  <div class="modal sheetwrap" onclick="App.commLeaveCancel()">
    <div class="sheet" onclick="event.stopPropagation()">
      <div class="sheet-grip"></div>
      <div class="sheet-hd"><b>대화에서 나갈까요?</b><span>지금까지의 대화는 다시 볼 수 없어요</span></div>
      <div class="sheet-act nodel">
        <button class="act-cancel" onclick="App.commLeaveCancel()">그대로 두기</button>
        <button class="act-del" onclick="App.commLeave()">나가기</button>
      </div>
    </div>
  </div>` : ""}`;
}
const hhmm = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  const h = d.getHours(), m = String(d.getMinutes()).padStart(2, "0");
  return `${h < 12 ? "오전" : "오후"} ${h % 12 || 12}:${m}`;
};

// ── 일정 = 다이어리 (검수 지적 1·3) ──────────────────────
// 달력 한 판 + 날짜를 누르면 그 날 학교 일정과 내 일정이 같이 열린다.
// "이달의 일정"은 항상 맨 위에 고정.
const SUBJECTS = ["국어", "수학", "사회", "과학", "영어", "체육", "음악", "미술", "실과", "도덕", "통합", "창체", "빈칸"];
// 1일 다이어리 시간축 — 등교부터 저녁까지. px = 30분당 높이.
const DAY = { h0: 8, h1: 21, px: 26 };

// 학사일정 중요도 분류 — 웹(templates.js)과 같은 규칙을 쓴다(2026-07-24 지시).
// API에 중요도 필드가 없어 이름으로 분류한다. 토요휴업일처럼 매주 반복되는 건 제외.
const IMPORTANT_EVENTS = [
  ["방학·개학", "ti-umbrella", ["방학식", "개학식", "종업식", "방학선언"]],   // 단순 방학 "기간"은 제외 — 식(式)만
  ["시험", "ti-pencil", ["중간고사", "기말고사", "지필평가", "학력평가", "고사", "시험"]],
  ["입학·졸업", "ti-school", ["입학식", "졸업식"]],
  ["체험학습", "ti-bus", ["수학여행", "현장학습", "체험학습", "소풍", "수련활동", "수련회"]],
  ["행사", "ti-confetti", ["운동회", "학예회", "축제", "발표회", "체육대회", "한마당"]],
  ["참여수업", "ti-hand-stop", ["공개수업", "학부모공개", "참여수업", "수업공개", "공개 수업", "학부모 공개"]],
  ["개교기념", "ti-school", ["개교기념"]],
  ["재량휴업", "ti-home", ["재량휴업"]],
  ["상담", "ti-message-circle", ["학부모상담", "상담주간", "학부모 상담"]],
];
function classifyEvent(name, closureType) {
  const n = name || "";
  if (n.includes("토요휴업일")) return null;                      // 매주 반복 정기휴업 — 알림 가치 없음
  if ((closureType || "").includes("공휴일")) return { cat: "공휴일", icon: "ti-flag" };
  for (const [cat, icon, kws] of IMPORTANT_EVENTS) if (kws.some((k) => n.includes(k))) return { cat, icon };
  return null;
}

// 하루치 타임라인 — 다이어리 팝업과 자녀 화면이 같은 것을 쓴다(엄마가 본 하루 = 아이가 본 하루).
// 홈의 "오늘 하루" — 수업·급식을 빼면 남는 건 학원·내 일정 한둘뿐이라
// 타임라인 격자는 과하다(2026-07-24 실측: 격자 52px에 블록 1개). 목록으로 보여준다.
// 수업은 시간표 탭, 급식은 급식 탭에 이미 있다.
function todayList(date) {
  const wd = new Date(+date.slice(0, 4), +date.slice(4, 6) - 1, +date.slice(6)).getDay();
  const school = wd >= 1 && wd <= 5;
  const items = [];

  schedulesOf().filter((e) => e.date === date && !e.name.includes("토요휴업일")).forEach((e) => {
    const c = classifyEvent(e.name, e.closure_type);
    items.push({ t: null, icon: c ? c.icon : "ti-school", title: e.name, sub: e.content || "학교 일정" });
  });
  if (school) {
    STUB.activities.filter((a) => a.days_of_week.split(",").includes(String(wd)))
      .forEach((a) => items.push({ t: a.start_time, icon: "ti-clock", title: a.name, sub: `${a.start_time}~${a.end_time} · 학원·방과후` }));
  }
  STUB.myEvents.filter((e) => e.date === date).forEach((e) =>
    // icon 은 **클래스 이름만** 넣는다 — 아래 렌더에서 <i>로 감싼다.
    // 태그째 넣어 두어서 «<i class='ti <i class='ti ti-notebook'></i>'>» 로 이중 포장돼
    // 화면에 «'>» 가 찍혀 나왔다(2026-07-27 폰에서 발견).
    // mine=내가 만든 일정 → **고치고 지울 수 있다.** 학교 일정·학원은 우리가 못 건드린다.
    items.push({ t: e.start || null, icon: "ti-notebook", mine: e.id, title: e.title, sub: [e.start ? `${e.start}~${e.end}` : "종일", e.memo].filter(Boolean).join(" · ") }));

  items.sort((a, b) => (a.t || "").localeCompare(b.t || ""));

  if (!items.length) return `<p class="sub" style="margin-top:10px">오늘은 학원도 일정도 없어요. 푹 쉬는 날이에요.</p>`;
  /* 내 일정 줄은 **누르면 수정, 꾹 누르면 삭제 메뉴**다.
     팝업이던 시절엔 붙어 있었는데 하루 상세를 이 목록으로 옮기면서 빠졌다 —
     그 바람에 한동안 «수정도 삭제도 안 되는» 상태였다(2026-07-27 지적받고 되살림).
     꾹 누르기만 두면 있는 줄도 모른다. 오른쪽에 연필을 같이 보여준다. */
  return `<div class="todaylist">${items.map((i) => i.mine ? `
    <div class="trow mine" onclick="if(!App.holdGuard())App.evEdit(${i.mine})" onpointerdown="App.holdEvent(${i.mine})">
      <span class="ticon"><i class='ti ${i.icon}'></i></span>
      <span><b>${esc(i.title)}</b><span class="ntime">${i.sub}</span></span>
      <span class="tedit"><i class='ti ti-pencil'></i></span></div>` : `
    <div class="trow"><span class="ticon"><i class='ti ${i.icon}'></i></span>
      <span><b>${esc(i.title)}</b><span class="ntime">${i.sub}</span></span></div>`).join("")}</div>`;
}

// opts.fit=true → 내용 있는 시간대만(홈). opts.classes=false → 수업 제외.
// 홈에서 수업까지 그리면 매일 뻔한 것이 화면을 먹는다(시간표 탭에 이미 있음, 2026-07-24 지적).
function dayTimeline(date, opts = {}) {
  const fit = opts.fit, withClasses = opts.classes !== false, withMeal = opts.meal !== false;
  const wd = new Date(+date.slice(0, 4), +date.slice(4, 6) - 1, +date.slice(6)).getDay();
  const school = wd >= 1 && wd <= 5;                       // 주말엔 수업·급식·학원 없음
  const dayIdx = wd - 1;

  // 그릴 시간 범위 — fit이면 첫 일정 앞뒤로 30분씩만 남긴다(빈 시간이 화면을 먹지 않게)
  let h0 = DAY.h0, h1 = DAY.h1;
  if (fit) {
    const times = [];
    if (school) {
      if (withClasses) STUB.periods.forEach((p) => { if (ttOf().grid[p.n - 1]?.[dayIdx]) times.push(toMin(p.start), toMin(p.end)); });
      if (withMeal && mealsOf().some((m) => m.date === date && m.type === "중식")) times.push(toMin(lunchOf().start), toMin(lunchOf().end));
      STUB.activities.filter((a) => a.days_of_week.split(",").includes(String(dayIdx + 1)))
        .forEach((a) => times.push(toMin(a.start_time), toMin(a.end_time)));
    }
    STUB.myEvents.filter((e) => e.date === date && e.start).forEach((e) => times.push(toMin(e.start), toMin(e.end)));
    if (times.length) {
      h0 = Math.max(DAY.h0, Math.floor(Math.min(...times) / 60));
      h1 = Math.min(DAY.h1, Math.ceil(Math.max(...times) / 60));
    }
  }
  const sc = schedulesOf().filter((e) => e.date === date && !e.name.includes("토요휴업일"));
  const mine = STUB.myEvents.filter((e) => e.date === date);
  const meal = mealsOf().find((m) => m.date === date && m.type === "중식");
  const acts = school ? STUB.activities.filter((a) => a.days_of_week.split(",").includes(String(dayIdx + 1))) : [];
  const timed = mine.filter((e) => e.start), allday = mine.filter((e) => !e.start);

  // 이 하루에 실제로 무언가 있는 시각들(빈 구간을 찾기 위해)
  const spans = [];
  if (school) {
    if (withClasses) STUB.periods.forEach((p) => { if (ttOf().grid[p.n - 1]?.[dayIdx]) spans.push([toMin(p.start), toMin(p.end)]); });
    if (withMeal && meal) spans.push([toMin(lunchOf().start), toMin(lunchOf().end)]);
    acts.forEach((a) => spans.push([toMin(a.start_time), toMin(a.end_time)]));
  }
  timed.forEach((e) => spans.push([toMin(e.start), toMin(e.end)]));

  // 하교~학원 사이처럼 2시간 이상 비는 구간은 "⋯"" 한 줄로 접는다. 안 그러면 빈 격자가 화면을 먹는다.
  const GAP_MIN_HOURS = 2, GAP_H = 30;
  const busy = (h) => spans.some(([a, b]) => a < (h + 1) * 60 && b > h * 60);
  const rows = [];
  for (let h = h0; h < h1; h++) {
    if (fit && !busy(h)) {
      const run = [];
      while (h < h1 && !busy(h)) { run.push(h); h++; }
      h--;
      if (run.length >= GAP_MIN_HOURS) { rows.push({ gap: run }); continue; }
      run.forEach((x) => rows.push({ h: x }));
    } else rows.push({ h });
  }
  // 시각 → y 좌표. 접힌 구간은 GAP_H 한 칸으로 취급한다.
  const yOf = {};
  let y = 0;
  for (const r of rows) {
    if (r.gap) { y += GAP_H; continue; }
    yOf[r.h] = y; y += DAY.px * 2;
  }
  const top = (t) => {
    const m = toMin(t), h = Math.floor(m / 60);
    const base = yOf[h] ?? yOf[Math.min(...Object.keys(yOf).map(Number).filter((x) => x >= h))] ?? 0;
    return base + ((m % 60) / 30) * DAY.px;
  };
  // onclick을 받으면 누를 수 있는 블록이 된다 — 내 일정만 수정·삭제가 열린다(수업·급식은 학교 값이라 못 고친다)
  const box = (t1, t2, cls, label, sub, onclick, onhold) => `
    <div class="dblk ${cls}${onclick ? " tappable" : ""}" ${onclick ? `onclick="if(!App.holdGuard())${onclick}"` : ""}
         ${onhold ? `onpointerdown="${onhold}"` : ""}
         style="top:${top(t1)}px;height:${Math.max(DAY.px * 0.8, top(t2) - top(t1))}px">
      <b>${esc(label)}</b>${sub ? `<span>${esc(sub)}</span>` : ""}</div>`;

  return `
    ${sc.length || allday.length ? `
      <div class="allday">
        ${sc.map((e) => {
          const c = classifyEvent(e.name, e.closure_type);
          return `<span class="etag"><i class='ti ${c ? c.icon : "ti-school"}'></i> ${esc(e.name)}${e.content ? ` · ${e.content}` : ""}</span>`;
        }).join("")}
        ${allday.map((e) => `<span class="etag mine" onclick="App.evEdit(${e.id})"><i class='ti ti-notebook'></i> ${esc(e.title)}${e.memo ? ` · ${e.memo}` : ""}</span>`).join("")}
      </div>` : ""}

    <div class="daygrid">
      <div class="dayaxis">${rows.map((r) => r.gap
        ? `<div style="height:${GAP_H}px"></div>`
        : `<div style="height:${DAY.px * 2}px"><span>${r.h}시</span></div>`).join("")}</div>
      <div class="daycol">
        ${rows.map((r) => r.gap
          ? `<div class="daygap" style="height:${GAP_H}px">⋯ ${r.gap[0]}시~${r.gap[r.gap.length - 1] + 1}시 비어 있어요</div>`
          : `<div class="wk-slot" style="height:${DAY.px * 2}px"></div>`).join("")}
        ${school && withClasses ? STUB.periods.map((p) => {
          const subject = ttOf().grid[p.n - 1]?.[dayIdx];
          return subject ? box(p.start, p.end, "cls", subject, `${p.n}교시`) : "";
        }).join("") : ""}
        ${school && withMeal && meal ? box(lunchOf().start, lunchOf().end, "meal", "급식", meal.dishes.slice(0, 2).map((x) => x.name).join(" · ")) : ""}
        ${acts.map((a) => box(a.start_time, a.end_time, "act2", a.name, "학원·방과후")).join("")}
        ${timed.map((e) => box(e.start, e.end, "mine", e.title, e.memo, `App.evEdit(${e.id})`, `App.holdEvent(${e.id})`)).join("")}
      </div>
    </div>
    ${!school ? `<p class="sub" style="padding:0 2px">주말이라 수업·급식은 없어요.</p>` : ""}`;
}

/* 방학처럼 «기간»인 일정 — NEIS는 시작일 하루만 준다("여름방학" 7/20 → "2학기 개학" 8/20).
   하루만 칠하면 방학 한 달이 달력에서 안 보인다(2026-07-27 실측: 8월 방학 음영 0칸이었다).
   시작(방학)과 끝(개학)을 짝지어 기간으로 편다. 끝을 못 찾으면 21일에서 끊는다 —
   짝이 안 맞는 데이터 하나 때문에 달력 전체가 방학으로 칠해지는 것을 막는다.
   «방학식»(행사) · «방학중 돌봄교실» · «여름방학 독서교실»은 기간이 아니라 그 날 하루짜리다. */
function vacationRanges() {
  const evs = schedulesOf().slice().sort((a, b) => a.date.localeCompare(b.date));
  const out = [];
  let start = null;
  for (const e of evs) {
    const n = e.name || "";
    if (!start && n.includes("방학") && !/식|교실|돌봄|상담/.test(n)) { start = e.date; continue; }
    if (start && n.includes("개학")) { out.push([start, e.date]); start = null; }
  }
  if (start) out.push([start, ymdPlus(start, 21)]);
  return out;
}

/* 일정 — 구글 캘린더 구조 (시안 8a·8b, 2026-07-27)
   ①월 제목이 곧 접기 손잡이 — 누르면 월(5줄)↔주(1줄)
   ②칸에는 **점 하나만**. 일정 이름을 칸에 넣으면 368px에서 잘린다(전에 그래서 뺐다)
   ③아젠다가 본문 — 날짜를 누르면 왼쪽 막대가 그 날로 가고, 오늘은 검정 원
   ④「내 일정」도 같은 흐름에 산다 — 다이어리를 따로 두지 않는다
   ⑤＋는 우하단 고정(56px) */
function diaryTab() {
  const ym = S.calMonth;
  /* 그 달 «아이 흔적»을 서버에서 받아 온다 — 달을 넘길 때마다 여기를 지난다.
     같은 달은 한 번만 받고(MARKS_GOT), 값이 실제로 바뀌었을 때만 다시 그린다. */
  loadMarks(ym);
  const y = +ym.slice(0, 4), m = +ym.slice(4, 6);
  const first = weekOffset(new Date(y, m - 1, 1).getDay());   // 요일 시작 설정 반영(§4)
  const last = new Date(y, m, 0).getDate();
  const pick = S.calPick || (TODAY.slice(0, 6) === ym ? TODAY : ym + "01");
  const vac = vacationRanges();
  const inVac = (d) => vac.some(([a, b]) => d >= a && d < b);

  const schoolOf = (d) => schedulesOf().filter((e) => e.date === d && !e.name.includes("토요휴업일"));
  const mineOf = (d) => STUB.myEvents.filter((e) => e.date === d);

  // ── 달력 칸 ──────────────────────────────────────────────
  const cells = [];
  for (let i = 0; i < first; i++) cells.push(null);
  for (let d = 1; d <= last; d++) cells.push(ym + String(d).padStart(2, "0"));
  while (cells.length % 7) cells.push(null);
  const rows = [];
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));
  const pickRow = Math.floor((first + (+pick.slice(6)) - 1) / 7);
  const shown = S.calFold ? [rows[pickRow] || rows[0]] : rows;

  const cell = (key, i) => {
    if (!key) return `<div class="gc-cell empty"></div>`;
    const d = +key.slice(6);
    const wd = (first + d - 1) % 7;
    const sc = schoolOf(key), mine = mineOf(key);
    const holi = sc.some((e) => (e.closure_type || "").includes("공휴일"));
    // 점 하나만 — 공휴일 danger · 내 일정 accent · 학교 회색
    const dot = holi ? "holi" : mine.length ? "mine" : sc.length ? "sc" : "";
    /* 아이 흔적 (§3) — 일정 점과 **줄을 나눠** 아래에 단다.
       한 점에 두 가지 뜻을 담으면 「학교 행사」와 「도장 받은 날」이 섞여서 둘 다 안 읽힌다.
       ⚠ 이모지는 «도장 하나라도 있는 날»에만. 0개인 날에 회색 별을 달면 온 달이 별밭이 된다. */
    const mk = marksOf(key);
    const trace = !mk ? "" : `<i class="gc-trace">${mk.stamp ? "★" : ""}${mk.meal ? "🍚" : ""}</i>`;
    return `
    <button class="gc-cell ${key === pick ? "on" : ""} ${key === TODAY ? "today" : ""}" onclick="if(!App.holdGuard())App.calPick('${key}')" onpointerdown="App.holdDay(event, '${key}')">
      <span class="gc-num ${holi || wd === 0 ? "sun" : ""} ${inVac(key) ? "vac" : ""}">${d}</span>
      <i class="gc-dot ${dot}"></i>
      ${trace}
    </button>`;
  };

  // ── 아젠다 — 이 달에서 뭔가 있는 날만, 오늘 이후부터 ──────
  /* ⚠ 방학·상담주간처럼 **기간**인 일정은 NEIS가 날마다 한 줄씩 준다.
     그대로 쌓으면 「여름방학」이 24·25·26·27… 끝없이 반복된다(2026-07-27 실기기).
     이름이 같으면 **처음 나온 날에만** 싣고, 마지막 날을 붙여 «7.24~8.17» 로 보여준다. */
  const runEnd = {};
  for (let d = last; d >= 1; d--) {
    const key = ym + String(d).padStart(2, "0");
    schoolOf(key).forEach((e) => { if (runEnd[e.name] === undefined) runEnd[e.name] = key; });
  }
  const shownName = new Set();
  const days = [];
  /* **지나간 날은 안 보여준다**(2026-07-31 «31일인데 17일이 왜 나와»).
     오늘이 낀 달에서만 걸러낸다 — 지난달을 일부러 펼쳐 봤을 땐 그 달을 통째로 보여줘야 한다.
     ⚠ 기간 일정은 예외다: «여름방학 24일~31일»처럼 **아직 진행 중**이면 시작일이 지났어도 남긴다. */
  const thisMonth = ym === TODAY.slice(0, 6);
  for (let d = 1; d <= last; d++) {
    const key = ym + String(d).padStart(2, "0");
    const sc = schoolOf(key).filter((e) => {
      if (shownName.has(e.name)) return false;
      shownName.add(e.name); return true;
    }).map((e) => ({ ...e, _end: runEnd[e.name] !== key ? runEnd[e.name] : null }))
      // 지난 날짜라도 «오늘까지 이어지는» 일정이면 남긴다
      .filter((e) => !thisMonth || key >= TODAY || (runEnd[e.name] || key) >= TODAY);
    const mine = thisMonth && key < TODAY ? [] : mineOf(key);
    if (!sc.length && !mine.length) continue;
    days.push({ key, d, wd: weekdayKo(key), sc, mine });
  }

  /* 아젠다 = «오늘부터 흐르는 목록»(§2). 달력이 «어느 달인가»를 말하면 이건 «무슨 일이 있나»를 말한다.
     ⚠ 줄을 누르면 **일간 전체 화면**으로 들어간다 — 달력에서 하루를 들여다보는 창을 따로 두지 않는다
       (그 창이 dayPanel 이었는데, 같은 내용을 두 곳에서 그리게 되어 한쪽만 고치는 사고가 났다). */
  const agenda = days.map((r) => `
    <div class="gc-day ${r.key === pick ? "on" : ""}" id="ag-${r.key}" onclick="App.dayOpen('${r.key}')">
      <span class="gc-mark"></span>
      <span class="gc-date">
        <span class="gc-w">${r.wd}</span>
        <span class="gc-n ${r.key === TODAY ? "today" : ""}">${r.d}</span>
      </span>
      <span class="gc-evs">
        ${r.sc.map((e) => {
          const holi = (e.closure_type || "").includes("공휴일");
          return `<span class="gc-ev"><i class="${holi ? "holi" : "sc"}"></i>
            <span class="gc-et"><b>${esc(e.name)}</b>${(() => {
              const period = e._end ? `~ ${+e._end.slice(4, 6)}월 ${+e._end.slice(6)}일` : "";
              const t = [period, e.content].filter(Boolean).join(" · ");
              return t ? `<span>${esc(t)}</span>` : "";
            })()}</span></span>`;
        }).join("")}
        ${r.mine.map((e) => `
          <button class="gc-ev mine" onclick="event.stopPropagation();if(!App.holdGuard())App.evEdit(${e.id})" onpointerdown="event.stopPropagation();App.holdEvent(${e.id})">
            <i class="mine"></i>
            <span class="gc-et"><b>${esc(e.title)}</b><span>${e.start ? `${esc(e.start)}${e.end ? `~${esc(e.end)}` : ""}` : "종일"}${e.memo ? ` · ${esc(e.memo)}` : ""}</span></span>
          </button>`).join("")}
      </span>
    </div>`).join("");

  return `
  <div class="gc-hd">
    <button class="gc-title" onclick="App.calFold()">
      <b>${y}년 ${m}월</b><i class='ti ${S.calFold ? "ti-chevron-down" : "ti-chevron-up"}'></i>
    </button>
    <span class="gc-acts">
      <button class="mv" onclick="App.calMove(-1)" aria-label="지난달"><i class='ti ti-chevron-left'></i></button>
      <button class="mv" onclick="App.calMove(1)" aria-label="다음달"><i class='ti ti-chevron-right'></i></button>
      <button class="today" onclick="App.calToday()">오늘</button>
    </span>
  </div>

  <div class="gc-wk">${weekDays().map((d) => `<span class="${d === "일" ? "sun" : ""}">${d}</span>`).join("")}</div>
  <!-- 달력을 좌우로 밀면 달이 넘어간다(2026-07-31 «위 작은 화살표 누르기 어려워»).
       세로로 미는 건 화면 스크롤이라, 가로가 세로보다 확실히 클 때만 달을 넘긴다(attachCalSwipe). -->
  <div class="gc-grid" id="gcgrid">${shown.map((r) => r.map(cell).join("")).join("")}</div>

  <!-- 아래는 «오늘부터 흐르는» 목록. 달력 칸을 누르면 이 목록이 그 날짜로 옮겨간다(§2) -->
  ${agenda ? `<div class="gc-agenda">${agenda}</div>`
           : `<p class="gc-hint">이 달에는 남은 일정이 없어요</p>`}
  <p class="gc-hint">날짜를 꾹 누르면 일정을 넣어요 · 줄을 누르면 그날을 열어요</p>

  <!-- 일정 입력 모달 폐지(2026-08-03 §3) — 전체 화면 편집기 Screens.edit 이 대신한다.
       모달 안에서 날짜를 바꾸려면 시스템 피커가 또 떠서 창이 두 겹이 됐다. -->
`;
}

// ── 시간표 터치 편집 (검수 지적 2) ────────────────────────
// 셀을 누르면 과목 목록이 올라오고, 손가락으로 고르면 그 자리에 들어간다.
// 고친 셀은 표시해 두고, 반 전체 공유(크라우드소싱)를 물어본다.
function timetableTab() {
  const tt = ttOf();
  /* 지금 어느 쪽을 열어둘까 — **하교 시각**으로 가른다(2026-07-28 지시).
     수업 중이면 학교 시간표가, 하교 뒤면 하교 후가 열린 채로 뜬다.
     엄마가 3시에 앱을 열면 궁금한 건 5교시가 아니라 «오늘 학원 몇 시»다.
     ⚠ 손으로 접거나 편 적이 있으면(S.ttFold) 그 뜻이 이긴다. 자동은 «안 건드렸을 때»만이다. */
  const nowMin = (() => { const d = new Date(); return d.getHours() * 60 + d.getMinutes(); })();
  const last = STUB.periods[Math.max(0, (tt.grid || []).length - 1)] || STUB.periods[STUB.periods.length - 1];
  const outMin = last?.end ? toMin(last.end) : toMin(lunchOf().end) + 120;
  const afterHours = nowMin >= outMin || nowMin < toMin(STUB.periods[0]?.start || "09:00");
  const schoolOpen = S.ttFold?.school ?? !afterHours;
  const afterOpen = S.ttFold?.after ?? afterHours;
  const at = (r, c) => S.ttOverrides[`${r}-${c}`] ?? tt.grid[r][c];
  const changed = Object.keys(S.ttOverrides).length;
  const e = S.ttEdit;
  return `
  <!-- 시안 10b — 카드 껍데기와 「칸을 눌러 과목을 바꿀 수 있어요」 안내문을 뺐다(2026-07-28).
       격자가 이미 «누르는 것»처럼 생겼고(칸 = 56px 버튼), 안내문은 화면마다 쌓여 어지러웠다. -->
  ${nowCard()}
  <button class="tt-hd" onclick="App.ttFold('school')">
    <b>시간표</b>
    <span>${tt.grade}학년 ${tt.class_name}반 · ${tt.semester}학기</span>
    <i class="ttp-caret ${schoolOpen ? "on" : ""}"></i>
  </button>
  <div class="${schoolOpen ? "" : "hide"}">
    ${tt.grid.every((row) => row.every((v) => !v)) ? `
      <!-- 빈 시간표는 «왜 비었는지»를 말해줘야 한다. 웹은 방학/학기말/미제공을 구분해 안내한다(templates.js). -->
      <div class="ml-lead">${+TODAY.slice(4, 6) >= 7 && +TODAY.slice(4, 6) <= 8 ? "방학 중 · 칸을 눌러 미리 채워둘 수 있어요" : "아직 올라오지 않음 · 칸을 눌러 직접 넣기"}</div>` : ""}
    <!-- 교시 칸에 **시각**을 같이 보여준다(웹과 같은 규칙) — 학부모가 궁금한 건 «몇 교시»가 아니라 «몇 시»다.
         점심시간도 한 줄로 끼워 넣는다. 시간표가 «표»가 아니라 «하루»로 읽힌다. -->
    <!-- 오늘 요일만 강조한다 — 「지금 어디쯤인지」가 시간표에서 제일 먼저 궁금한 것이다(시안 10b) -->
    ${(() => {
      const todayCol = new Date(`${TODAY.slice(0,4)}-${TODAY.slice(4,6)}-${TODAY.slice(6)}`).getDay() - 1;
      const head = `<div class="hd"></div>` + DAY_KO.map((d, i) =>
        `<div class="hd ${i === todayCol ? "today" : ""}">${d}</div>`).join("");
      const rows = tt.grid.map((row, r) => {
        const t = STUB.periods[r] || {};
        /* 교시 칸 — 「1교시 / 09:00」 두 줄. 끝 시각까지 넣으면 석 줄이 되어 숫자가 과목보다
           시끄러웠다(2026-07-28 실기기). 끝 시각은 칸을 눌렀을 때 시트가 알려준다. */
        const cells = `<div class="hd tt-period"><b>${r + 1}교시</b>${t.start ? `<span>${t.start}</span>` : ""}</div>` +
          row.map((_, c) => {
            const v = at(r, c);
            const mine = S.ttOverrides[`${r}-${c}`] !== undefined;
            /* 과목 색 — **칸을 칠한다**(2026-07-28 사장님: "칸의 색상을 넣을 수 있으면 좋다고 한 건데").
               점으로 줬다가 되돌린 것이다. 옛 사고를 안 되풀이하려고 두 가지를 지킨다 —
               ① 색은 --cN(테마마다 정의됨)을 카드색에 섞어 쓴다. 값을 박아 넣지 않는다
               ② 글씨는 항상 var(--ink) 다. 예전엔 밝은 칸에 밝은 글씨가 앉아 대비 1.0 이 났다 */
            const ci = subjectCi(v);
            return `<div class="editable ${mine ? "mine" : ""} ${ci === null ? "" : `sj sj${ci}`} ${e && e.r === r && e.c === c ? "picking" : ""}"
                      onclick="App.ttOpen(${r},${c})"
                      aria-label="${DAY_KO[c]}요일 ${r + 1}교시 ${v ? esc(v) : "비어 있음"}">${esc(shortSubject(v))}</div>`;
          }).join("");
        return cells;
      });
      // 점심은 사용자가 정한 교시 뒤. 격자를 끊고 **점선 한 줄**로 — 흰 바를 하나 더 두면 칸처럼 보인다.
      const L = lunchOf();
      const lunchAt = Math.min(L.after, rows.length);
      return `
        <div class="tt-grid">${head}${rows.slice(0, lunchAt).join("")}</div>
        <button class="tt-lunch" onclick="App.lunchOpen()">점심 ${esc(L.start)} – ${esc(L.end)}</button>
        ${rows.length > lunchAt ? `<div class="tt-grid after">${rows.slice(lunchAt).join("")}</div>` : ""}`;
    })()}

    <!-- ── 하교 후 (시안 10b, 2026-07-28) ─────────────────────────
         ⚠ 예전엔 여기가 **5칸 격자**였고, 값을 S.ttPersonal 이라는 **딴 곳**에 담았다.
            그래서 같은 학원을 시간표에도 방과후 화면에도 각각 적어야 했고,
            시간표 쪽은 이 폰에만 남아 기기를 바꾸면 날아갔다(방과후 쪽만 서버에 있었다).
            이제 둘 다 **STUB.activities 하나**를 본다. 어디서 고치든 양쪽이 같이 바뀐다.
         격자를 버리고 목록으로 간 이유 — 학원은 「월·수 15:00~16:00」처럼 한 덩어리인데
         격자에 넣으면 같은 것을 두 칸에 나눠 적게 된다. -->
    <!-- ＋ 를 **머리에** 둔다. 목록 맨 아래 점선 버튼은 화면 끝(905px)에 걸려
         스크롤해야 보였다(2026-07-28 실측·지적). 섹션에 닿자마자 눌리는 자리로 올린다. -->
    <button class="ttp-hd" onclick="App.ttFold('after')">
      <b>하교 후</b>
      <span class="ttp-only">${STUB.activities.length}개</span>
      <i class="ttp-caret ${afterOpen ? "on" : ""}"></i>
    </button>
    <div class="ttp-list ${afterOpen ? "" : "hide"}">
      <div class="ttp-hd2"><button class="ttp-new" onclick="App.planNew()">＋ 추가</button></div>
      ${STUB.activities.slice().sort((x, y) => (x.start_time || "").localeCompare(y.start_time || "")).map((a) => {
        const days = String(a.days_of_week || "").split(",").filter(Boolean)
          .sort().map((n) => DAY_KO[+n - 1]).filter(Boolean).join(" ");
        return `
        <button class="ttp-item" onclick="App.planEdit(${a.id})" style="--tag:${planColor(a.color, a.name).v}">
          <i></i>
          <span class="ttp-name"><b>${esc(a.name)}</b><em>${days}${days && a.start_time ? " · " : ""}${esc(a.start_time || "")}${a.end_time ? ` – ${esc(a.end_time)}` : ""}</em></span>
          <span class="ttp-go"><i aria-hidden="true" class="ti ti-chevron-right"></i></span>
        </button>`;
      }).join("")}
      ${STUB.activities.length ? "" : `<button class="ttp-add" onclick="App.planNew()"><span>＋</span>학원·방과후 넣기</button>`}
    </div>

    <!-- 공유 버튼을 뺐다(2026-07-27 지시). 시간표는 **내가 나만 쓰려고 고치는 것**이지
         다른 학부모에게 내보내는 것이 아니다. 크라우드소싱 문구도 같이 지운다 —
         버튼이 없는데 설명만 남으면 «어디서 공유하지» 하고 찾게 된다. -->
    ${changed ? `
      <div class="tt-reset"><span><i class="tt-minedot"></i>내가 고친 칸 ${changed}개</span><button onclick="App.ttReset()">되돌리기</button></div>` : ""}
  </div>

  <!-- 칸을 고치는 «반쪽 시트» 폐지(2026-08-03 §4) — 전용 화면 Screens.edittt 가 대신한다.
       시트로 열면 화면 절반이 가려서 «지금 어느 칸을 고치는지»가 안 보였다. -->
  `;
}

// 기록 크게 보기 — 탭하면 이게 뜬다(삭제는 여기 ⋯ 메뉴에서). S.viewRecord = 보고 있는 기록 id.
/* ═══ 크게보기 핀치 줌 (2026-07-31) ═══════════════════════════
   두 손가락=확대·축소(가운데 고정), 한 손가락=확대 중 이동, 두 번 탭=2.5배↔원래대로.
   배율 1~5배. 상태는 S.vw 에 있어 다시 그려도 유지되고, 장을 넘기면(키가 바뀌면) 처음으로. */
function attachPinch() {
  const box = document.getElementById("vwimg");
  if (!box) return;
  const key = box.dataset.vwkey;
  if (!S.vw || S.vw.key !== key) S.vw = { key, s: 1, x: 0, y: 0 };
  const img = box.querySelector("img");
  if (!img) return;
  const apply = () => { img.style.transform = `translate(${S.vw.x}px, ${S.vw.y}px) scale(${S.vw.s})`; };
  // 이동 한계 — 사진 밖 검은 데로 끝없이 밀리지 않게
  const clamp = () => {
    const mx = Math.max(0, (img.clientWidth * S.vw.s - box.clientWidth) / 2 + 40);
    const my = Math.max(0, (img.clientHeight * S.vw.s - box.clientHeight) / 2 + 40);
    S.vw.x = Math.min(mx, Math.max(-mx, S.vw.x));
    S.vw.y = Math.min(my, Math.max(-my, S.vw.y));
  };
  apply();
  if (box._pinch) return;                 // 리스너는 노드당 한 번만
  box._pinch = true;

  const ptr = new Map();                  // 지금 눌려 있는 손가락들
  let base = null;                        // 제스처 시작 시점의 값
  const mid = () => { const v = [...ptr.values()]; return { mx: (v[0].x + v[1].x) / 2, my: (v[0].y + v[1].y) / 2, d: Math.hypot(v[0].x - v[1].x, v[0].y - v[1].y) }; };
  box.addEventListener("pointerdown", (e) => {
    // capture 실패(합성 이벤트·이미 뗀 손가락)로 제스처 전체가 죽지 않게
    try { box.setPointerCapture(e.pointerId); } catch (_) {}
    ptr.set(e.pointerId, { x: e.clientX, y: e.clientY });
    base = ptr.size === 2 ? { ...mid(), s: S.vw.s, tx: S.vw.x, ty: S.vw.y }
         : { x: e.clientX, y: e.clientY, tx: S.vw.x, ty: S.vw.y };
  });
  box.addEventListener("pointermove", (e) => {
    if (!ptr.has(e.pointerId)) return;
    ptr.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (ptr.size === 2 && base?.d) {
      const m = mid();
      S.vw.s = Math.min(5, Math.max(1, base.s * (m.d / base.d)));
      const k = S.vw.s / base.s;
      // 처음 두 손가락 가운데 지점이 화면에서 안 움직이게 — 그 점을 기준으로 늘린다
      const r = box.getBoundingClientRect();
      const px = base.mx - (r.left + r.width / 2), py = base.my - (r.top + r.height / 2);
      S.vw.x = px - k * (px - base.tx);
      S.vw.y = py - k * (py - base.ty);
      clamp(); apply();
    } else if (ptr.size === 1 && base && S.vw.s > 1.02) {
      S.vw.x = base.tx + (e.clientX - base.x);
      S.vw.y = base.ty + (e.clientY - base.y);
      clamp(); apply();
      e.preventDefault();
    }
  });
  const up = (e) => { ptr.delete(e.pointerId); base = ptr.size === 1 ? (() => { const v = [...ptr.values()][0]; return { x: v.x, y: v.y, tx: S.vw.x, ty: S.vw.y }; })() : null; };
  box.addEventListener("pointerup", up);
  box.addEventListener("pointercancel", up);
  box.addEventListener("dblclick", () => {
    S.vw = S.vw.s > 1.05 ? { key, s: 1, x: 0, y: 0 } : { key, s: 2.5, x: 0, y: 0 };
    apply();
  });
}

/* ═══ 하루 상세 (2026-07-31 B안) ═══════════════════════════
   날짜를 눌러도 아젠다에서 강조만 되고 «그 날»이 없었다. 여기서 하루치를 한 판에 모은다 —
   학교 일정 · 내 일정 · 급식 · 시간표 · 준비물. 다이어리로 쓰려면 이 판이 있어야 한다.
   ⚠ 없는 것은 **줄을 안 만든다**(빈 줄이 자리를 먹으면 있는 것이 눈에 안 들어온다). */
function dayPanel(key) {
  if (!key) return "";
  const y = +key.slice(0, 4), mo = +key.slice(4, 6), d = +key.slice(6);
  const wd = new Date(y, mo - 1, d).getDay();
  const weekend = wd === 0 || wd === 6;
  const vac = vacationRanges().some(([a, b]) => key >= a && key < b);
  // ⚠ schoolOf/mineOf 는 diaryTab 안에만 있는 지역 함수다 — 여기서 쓰면 «is not defined»로 화면이 통째로 죽는다.
  const sc = schedulesOf().filter((e) => e.date === key && !e.name.includes("토요휴업일"));
  const closed = weekend || vac || sc.some((e) => (e.closure_type || "").includes("휴업") || (e.closure_type || "").includes("공휴일"));
  const mine = STUB.myEvents.filter((e) => e.date === key);
  const meal = mealsOf().find((m) => m.date === key && m.type === "중식");
  const sup = STUB.supplies.filter((x) => x.date === key);
  const dayIdx = wd - 1;
  const subs = closed ? [] : (ttOf().grid || [])
    .map((row, r) => S.ttOverrides[`${r}-${dayIdx}`] ?? row[dayIdx]).filter(Boolean);
  const acts = STUB.activities.filter((a) => String(a.days_of_week || "").split(",").includes(String(wd)));

  const line = (cls, icon, title, sub, onclick) => `
    <${onclick ? "button" : "div"} class="dp-row ${cls}" ${onclick ? `onclick="${onclick}"` : ""}>
      <i class='ti ${icon}'></i>
      <span class="dp-t"><b>${title}</b>${sub ? `<em>${sub}</em>` : ""}</span>
    </${onclick ? "button" : "div"}>`;

  const rows = [
    ...sc.map((e) => line((e.closure_type || "").includes("공휴일") ? "holi" : "sc", "ti-school", esc(e.name), esc(e.content || ""))),
    ...mine.map((e) => line("mine", "ti-notebook", esc(e.title),
      `${e.start ? esc(e.start) : "종일"}${e.memo ? ` · ${esc(e.memo)}` : ""}`, `App.evEdit(${e.id})`)),
    ...acts.map((a) => line("act", "ti-run", esc(a.name), `${esc(a.start_time || "")}${a.end_time ? `~${esc(a.end_time)}` : ""}`)),
    meal ? line("meal", "ti-tools-kitchen-2", "급식", esc(meal.dishes.slice(0, 4).map((x) => x.name).join(" · "))) : "",
    subs.length ? line("tt", "ti-table", "수업", esc(subs.map(shortSubject).join(" "))) : "",
    ...sup.map((s) => line("sup", "ti-backpack", esc(s.item || s.name || "준비물"), s.done ? "챙김" : "챙길 것", "location.hash='#supplies'")),
    /* 아이 흔적 (§3) — 도장 · 사진 · 급식 평가. **본 것만** 적혀 있다(marksOf 주석 참고).
       오늘이면 미션 화면으로 갈 수 있게 하고, 지난 날은 기록으로만 둔다(지난 도장은 못 고친다). */
    ...(() => {
      const mk = marksOf(key);
      if (!mk) return [];
      const out = [];
      if (mk.stamp) out.push(line("stamp", "ti-star", "도장",
        `${mk.stamp}${mk.of ? `/${mk.of}` : ""}개`, key === TODAY ? "location.hash='#mission'" : ""));
      if (mk.photo) out.push(line("shot", "ti-camera", "사진 미션", `${mk.photo}개`,
        key === TODAY ? "location.hash='#mission'" : ""));
      if (mk.meal) out.push(line("rate", "ti-bowl", "급식 평가", `★ ${mk.meal}`, ""));
      return out;
    })(),
  ].filter(Boolean);

  return `
  <div class="dp">
    <div class="dp-hd">
      <b>${mo}월 ${d}일 ${["일","월","화","수","목","금","토"][wd]}요일</b>
      ${key === TODAY ? `<span class="dp-today">오늘</span>` : `<span class="dp-dd">${ddayLabel(key) || ""}</span>`}
    </div>
    ${rows.length ? `<div class="dp-list">${rows.join("")}</div>`
      : `<div class="dp-none">${closed ? "학교 안 가는 날이에요" : "이 날은 아무것도 없어요"}</div>`}

  </div>`;
}

/* 여러 줄 칸이 글자 수만큼 늘어나게 (2026-07-31) — 스크롤 막대 안에서 글을 쓰면
   앞에 쓴 내용이 안 보여서 «긴 글을 어떻게 적냐»가 된다. 화면이 그려질 때도 한 번 맞춘다. */
function autoGrow(el) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 260) + "px";
}
function autoGrowAll() { document.querySelectorAll("textarea.grow, .planrow textarea").forEach(autoGrow); }

/* ═══ 달력 좌우 스와이프 (2026-07-31) ═══════════════════════
   상단 «‹ ›»가 작아 누르기 어렵다고 해서, 달력 판 자체를 밀면 달이 넘어가게 한다.
   ⚠ 세로 스와이프는 **화면 스크롤**이다 — 가로 이동이 세로보다 확실히 클 때만 달을 바꾼다.
      (안 그러면 아젠다를 스크롤하려다 달이 바뀐다.)
   ⚠ 날짜 칸을 «누르는» 동작을 방해하면 안 된다 — 30px 넘게 움직였을 때만 스와이프로 친다. */
function attachCalSwipe() {
  const box = document.getElementById("gcgrid");
  if (!box || box._swipe) return;
  box._swipe = true;
  let x0 = 0, y0 = 0, on = false, fired = false;
  /* ⚠ **pointerup 을 기다리면 안 된다**(2026-07-31 실기기: 합성 이벤트로는 되는데 손가락으로는 안 됐다).
     손가락을 옆으로 끌면 브라우저가 그걸 스크롤로 가져가면서 pointercancel 을 쏘고 up 이 안 온다.
     그래서 **끄는 중(pointermove)에** 문턱을 넘는 순간 바로 달을 넘긴다.
     CSS 의 touch-action:pan-y 와 짝이다 — 세로만 브라우저에 주고 가로는 우리가 쓴다. */
  const start = (e) => { x0 = e.clientX; y0 = e.clientY; on = true; fired = false; };
  const move = (e) => {
    if (!on || fired) return;
    const dx = e.clientX - x0, dy = e.clientY - y0;
    if (Math.abs(dy) > 60 && Math.abs(dy) > Math.abs(dx)) { on = false; return; }   // 세로로 가면 스크롤에 양보
    if (Math.abs(dx) < 45) return;
    fired = true; on = false;
    App.calMove(dx < 0 ? 1 : -1);      // 왼쪽으로 밀면 다음 달(종이를 넘기는 방향)
  };
  const end = () => { on = false; };
  box.addEventListener("pointerdown", start);
  box.addEventListener("pointermove", move);
  box.addEventListener("pointerup", end);
  box.addEventListener("pointercancel", end);
  // 웹뷰가 pointer 대신 touch 만 주는 경우까지 대비(둘 다 오면 fired 로 한 번만 돈다)
  box.addEventListener("touchstart", (e) => start(e.touches[0]), { passive: true });
  box.addEventListener("touchmove", (e) => move(e.touches[0]), { passive: true });
  box.addEventListener("touchend", end);
}

/* 일간 화면 좌우 스와이프 = 날짜 이동 (2026-08-03 §7).
   달력 스와이프(attachCalSwipe)와 **같은 규칙**을 쓴다 — 두 곳에서 손맛이 다르면 그게 더 헷갈린다:
     · 세로가 더 크면 그건 스크롤이다. 가로가 확실히 클 때만 날짜를 넘긴다
     · pointerup 을 기다리지 않는다. 브라우저가 가로 끌기를 스크롤로 가져가며 취소하기 때문이다
   ⚠ 제스처만 두지 않는다 — 화면에 ‹ 오늘 › 버튼이 같이 있다(§7 «버튼 경로 병행»). */
function attachDaySwipe() {
  const box = document.getElementById("dywrap");
  if (!box || box._swipe) return;
  box._swipe = true;
  let x0 = 0, y0 = 0, on = false, fired = false;
  const start = (e) => { x0 = e.clientX; y0 = e.clientY; on = true; fired = false; };
  const move = (e) => {
    if (!on || fired) return;
    const dx = e.clientX - x0, dy = e.clientY - y0;
    if (Math.abs(dx) < 56 || Math.abs(dx) < Math.abs(dy) * 1.6) return;
    fired = true; on = false;
    App.dayMove(dx < 0 ? 1 : -1);      // 왼쪽으로 밀면 다음 날(달력과 같은 방향)
  };
  const end = () => { on = false; };
  box.addEventListener("pointerdown", start);
  box.addEventListener("pointermove", move);
  box.addEventListener("pointerup", end);
  box.addEventListener("pointercancel", end);
  box.addEventListener("touchstart", (e) => start(e.touches[0]), { passive: true });
  box.addEventListener("touchmove", (e) => move(e.touches[0]), { passive: true });
  box.addEventListener("touchend", end);
}

/* 소개 슬라이드 좌우 스와이프 (§5). 달력·일간과 **같은 규칙**을 쓴다 — 손맛이 다르면 그게 더 헷갈린다.
   ⚠ 제스처만 두지 않는다. 「다음」 버튼과 점이 같이 있다. */
function attachIntroSwipe() {
  const box = document.getElementById("obslides");
  if (!box || box._swipe) return;
  box._swipe = true;
  let x0 = 0, y0 = 0, on = false, fired = false;
  const start = (e) => { x0 = e.clientX; y0 = e.clientY; on = true; fired = false; };
  const move = (e) => {
    if (!on || fired) return;
    const dx = e.clientX - x0, dy = e.clientY - y0;
    if (Math.abs(dx) < 56 || Math.abs(dx) < Math.abs(dy) * 1.6) return;
    fired = true; on = false;
    const i = S.introIdx || 0;
    if (dx < 0) { if (i < INTRO_SLIDES.length - 1) App.introNext(); else App.introToSurvey(); }
    else if (i > 0) { S.introIdx = i - 1; App.render(); }
  };
  const end = () => { on = false; };
  box.addEventListener("pointerdown", start);
  box.addEventListener("pointermove", move);
  box.addEventListener("pointerup", end);
  box.addEventListener("pointercancel", end);
  box.addEventListener("touchstart", (e) => start(e.touches[0]), { passive: true });
  box.addEventListener("touchmove", (e) => move(e.touches[0]), { passive: true });
  box.addEventListener("touchend", end);
}

function recordViewer() {
  if (!S.viewRecord) return "";
  const r = STUB.records.find((x) => x.id === S.viewRecord);
  if (!r) return "";
  const c = cur();
  // 수정 모드 — 잘못 들어간 제목·종류·시기를 저장 후에도 고친다(2026-07-24).
  if (S.recordEdit) {
    const TYPES = ["상장", "통지표", "성적표", "자격증", "활동", "기타"];
    const KO2 = { award: "상장", report_card: "통지표", grade_sheet: "성적표", certificate: "자격증", activity: "활동", other: "기타" };
    const curType = S.editType ?? KO2[r.category];
    const curPeriod = S.editPeriod ?? r.period.label;
    const periods = [];
    for (let g = 1; g <= 6; g++) { periods.push(`초${g} 1학기`); periods.push(`초${g} 2학기`); }
    return `
    <div class="overlay viewer" onclick="App.recordEditCancel()">
      <div class="viewer-card" onclick="event.stopPropagation()">
        <div class="viewer-top"><b>기록 수정</b>
          <button class="iconbtn" onclick="App.recordEditCancel()"><i class='ti ti-x'></i></button></div>
        <div style="padding:14px 16px">
          <label class="f">제목</label>
          <input id="ed-title" value="${esc(S.editTitle ?? r.title)}" oninput="S.editTitle=this.value">
          <label class="f">날짜</label>
          <input type="date" value="${(S.editDate ?? r.date) ? ymdDash(S.editDate ?? r.date) : ""}" onchange="S.editDate=this.value.replace(/-/g,'')">
          <label class="f">종류</label>
          <select onchange="S.editType=this.value">
            ${TYPES.map((v) => `<option ${curType === v ? "selected" : ""}>${v}</option>`).join("")}
          </select>
          <label class="f">시기</label>
          <select onchange="S.editPeriod=this.value">
            ${periods.map((v) => `<option ${curPeriod === v ? "selected" : ""}>${v}</option>`).join("")}
          </select>
          <div class="row" style="margin-top:16px">
            <button class="btn-ghost" onclick="App.recordEditCancel()">취소</button>
            <button class="btn-primary" onclick="App.recordEditSave()">저장</button>
          </div>
        </div>
      </div>
    </div>`;
  }
  const imgs = (r.images && r.images.length) ? r.images : (r.image ? [r.image] : []);
  const i = Math.min(S.pageIdx || 0, Math.max(0, imgs.length - 1));
  /* 크게 보기 — 시안 16 (2026-07-27).
     사진이 전부다. 제목은 위가 아니라 **아래**에 있고, 위엔 닫기·페이지·⋯만 있다.
     좌우 88px을 눌러 장을 넘긴다(화살표 버튼을 두면 사진을 가린다).
     「두 번 탭하면 확대」 안내는 뺐다 — 안 써 놔도 해 보는 동작이다. */
  return `
  <div class="overlay viewer" onclick="App.closeRecord()">
    <div class="viewer-card" onclick="event.stopPropagation()">
      <!-- 핀치 줌(2026-07-31 «통지표 확대가 안 된다») — 두 손가락 확대·한 손가락 이동·두 번 탭 토글.
           앱 전체는 확대가 막혀 있어(viewport) 여기서 transform 으로 직접 구현한다. attachPinch()가 붙는다. -->
      <div class="viewer-img" id="vwimg" data-vwkey="${S.viewRecord}|${i}">
        ${(() => {
          if (!imgs.length) return `<div class="viewer-icon"><i class='ti ${r.icon}'></i></div>`;
          /* 장을 넘기는 순간 **이미 받아둔 주소**가 있으면 그걸로 바로 그린다(2026-07-31).
             없으면 그 장의 작은 그림(썸네일)이라도 먼저 깔고, 큰 그림이 오면 hydrateImages 가 바꿔 끼운다.
             예전엔 무조건 빈 칸부터 그려서 넘길 때마다 사진이 «늦게» 나타났다. */
          const full = r._pages?.[i] || r._full;
          const thumb = i === 0 ? r._thumb : null;
          const now = (full && IMG_READY.get(full)) || (thumb && IMG_READY.get(thumb)) || imgs[i] || PLACEHOLDER;
          return `<img src="${now}" ${full ? `data-rec="${full}"` : ""} alt="${esc(r.title)}">`;
        })()}
      </div>

      <div class="vw-top">
        <button class="vw-btn" onclick="App.closeRecord()" aria-label="닫기">×</button>
        <span class="vw-pager">${imgs.length > 1 ? `${i + 1} / ${imgs.length}` : ""}</span>
        <button class="vw-btn" onclick="App.recordMenu()" aria-label="더보기">⋯</button>
      </div>

      <!-- 좌우 88px 은 그대로 누르는 자리로 두되, **화살표를 보이게** 넣는다(2026-07-31
           «안 넘어간다» → 실은 어디를 눌러야 할지 안 보였던 것. 진짜 터치는 정상 동작했다).
           첫 장에선 왼쪽, 마지막 장에선 오른쪽 화살표를 흐리게 — 끝이라는 걸 눈으로 알려준다. -->
      ${imgs.length > 1 ? `
        <button class="vw-side left ${i === 0 ? "end" : ""}" onclick="App.page(-1)" aria-label="이전 장">
          <i class='ti ti-chevron-left'></i></button>
        <button class="vw-side right ${i === imgs.length - 1 ? "end" : ""}" onclick="App.page(1)" aria-label="다음 장">
          <i class='ti ti-chevron-right'></i></button>` : ""}

      <div class="vw-foot">
        <div class="vw-title">${esc(r.title)}</div>
        <div class="vw-meta">${esc(r.period.label)}${r.date ? ` · ${r.date.slice(0, 4)}.${r.date.slice(4, 6)}.${r.date.slice(6)}` : ""}</div>
        ${imgs.length > 1 ? `<div class="vw-dots">${imgs.map((_, k) => `<i class="${k === i ? "on" : ""}"></i>`).join("")}</div>` : ""}
      </div>

      ${S.recordMenuOpen ? `
        <div class="viewer-menu">
          <button onclick="App.recordEditStart()"><i class='ti ti-pencil'></i> 제목·종류·시기 수정</button>
          <button onclick="App.recordShare()"><i class='ti ti-share-2'></i> 공유</button>
          <button class="danger" onclick="App.recordDelete('${jsq(r.title)}')"><i class='ti ti-trash'></i> 삭제</button>
        </div>` : ""}
    </div>
  </div>`;
}

function mealAllergyLine(meal) {
  const hits = meal.dishes.filter((d) => d.allergens.length);
  return hits.length ? `<div style="margin-top:6px"><span class="allergy">알레르기 주의 ${hits.length}품목</span></div>` : "";
}

// ═══ 라우터 · 동작 ════════════════════════════════════════════
// 로그인 전에 열 수 있는 화면 (약관·방침은 가입 «보기»에서 온다. 고객센터는 «가입이 안 돼요»를 물을 자리가 있어야 한다)
const AUTH_FREE = ["intro", "login", "register", "findpw", "childlink", "terms", "policy", "help", "childexpired"];

/* ── 비회원 «둘러보기» (2026-08-03~04 지시) ──────────────────────────
   설문까지 마치면 **로그인 없이** 앱 안으로 들여보낸다. 다만 **쓰지는 못한다** —
   보여주기만 하고, 실제로 쓰려면 가입해야 한다.
   ⚠ 처음엔 «비회원도 학교를 골라 급식·시간표를 본다»로 만들었다가 걷어냈다(2026-08-04 지시).
     ① 둘러보라고 들여보내 놓고 **문 앞에서 검색을 시키는 꼴**이었고
     ② 어차피 자녀 등록에 로그인이 필요해 «반쪽만 되는 앱»이 하나 더 생기는 셈이었다.
     그래서 학교 고르기·비회원용 학교 조회를 **통째로 들어냈다.**
   ⚠ 지금 비회원이 볼 수 있는 화면은 **`guest` 하나뿐**이다. 여기에 화면을 더하는 것은
     «그 기능을 공짜로 준다»는 뜻이므로 함부로 늘리지 않는다(PASS_FREE 와 같은 원칙). */
/* ── 비회원 «구경» (2026-08-04 확정) ─────────────────────────────────
   설문까지 마치면 로그인 없이 **진짜 홈 화면**을 보여준다. 다만 **아무것도 못 한다** —
   말 그대로 구경이고, 뭘 누르든 로그인·가입으로 간다.

   ⚠ 여기까지 오는 데 두 번 뒤집었다. 남겨 둔다:
     ① «비회원도 학교를 골라 급식을 본다» → 걷어냄. 둘러보라고 들여보내 놓고
        문 앞에서 검색을 시키는 꼴이었다.
     ② «잠금 목록만 보여주는 요약 화면» → 걷어냄. 그건 «앱 안»이 아니라 광고지였다.
     지금은 **회원이 보는 그 홈을 그대로** 보여준다. 비어 있는 건 비어 있는 대로 둔다 —
     견본 아이를 지어내면 «지어내지 않는다»가 깨지고, 옛날 견본 학교명 사고를 되풀이한다.
   ⚠ 비회원이 열 수 있는 화면은 **home 하나뿐**이다. 늘리는 것은 «그 기능을 공짜로 준다»는
     뜻이므로 함부로 하지 않는다(PASS_FREE 와 같은 원칙). */
const GUEST_SCREENS = ["home"];
/* 비회원인가 — 소개·설문을 마쳤고, 로그인도 자녀 토큰도 아닌 상태 */
const isGuest = () => !S.loggedIn && !isChildToken() && !!localStorage.getItem("eduthink.introSeen");
/* 자녀 토큰으로 볼 수 있는 화면 — **이 목록 밖은 전부 자녀 화면으로 되돌린다**(2026-08-02).
   자녀 화면이 «결제·삭제·형제 정보는 안 보입니다»라고 적어놓고 뒤로는 다 보여주면 거짓말이다.
   약관·개인정보는 남긴다(법적으로 늘 닿을 수 있어야 한다). login 은 연결을 끊을 길이다. */
const CHILD_SCREENS = ["childlink", "login", "terms", "policy",
  "childtheme", "childshoot", "childexpired", "childtt", "childmealrate", "childfriend", "childsubject", "childlocked",
  // 상점·티켓은 아이가 직접 쓴다(§5③). ⚠ childmode 는 넣지 않는다 — 자녀폰에서 열리면 아이가 제 잠금을 푼다
  "store", "tickets", "game"];
/* §4.5 열람 잠금 — **비웠다**(2026-07-31 «기록 누르면 바로 기록잠금 나오게 하지마»).
   기록을 볼 때마다 지문을 묻는 건 제 폰에서 제 아이 기록을 보는 흐름을 막는다.
   보호는 **앱 잠금**(내정보 → 앱 잠금)이 대신한다 — 그쪽은 앱 전체를 한 번만 막는다.
   화면 이름을 다시 넣으면 그 화면은 예전처럼 진입 때 잠긴다. */
const BIO_LOCKED = [];
/* 이용권 게이트 (2026-07-28 사장님 확정) — **2주 체험 후 전면 유료. 무료 티어 없음.**
   PASS_FREE 만 체험이 끝나도 열린다. 이 목록에 화면을 더하는 것은
   «그 기능을 공짜로 준다»는 뜻이므로 함부로 늘리지 않는다.
     · 이용권/내정보 — 결제하러 가는 길과 로그아웃이 막히면 안 된다
     · 자녀 관련 — 자녀가 없으면 체험 자체가 시작되지 않는다
     · 아이 화면 — 자녀폰은 부모 이용권을 따라간다(아이에게 결제를 물리지 않는다) */
// 약관·방침 읽기는 잠그면 안 된다(법적 고지). 고객센터도 마찬가지 —
// 이용권이 끝나서 막힌 사람이 **결제 문의를 할 길**까지 막으면 돈을 낼 사람을 쫓아내는 셈이다.
const PASS_FREE = ["pay", "mypage", "switch", "child-add", "childlink", "terms", "policy", "help", "ask", "asks"];
// 체험 남은 날 (음수면 끝남). 이용권을 사면 expires_at 이 뒤로 밀린다.
function passDaysLeft(c) {
  const t = c?.pass?.expires_at ? new Date(c.pass.expires_at).getTime() : 0;
  if (!t) return -1;
  return Math.ceil((t - Date.now()) / 86400000);
}
/* 지금 이 아이 화면을 열어도 되는가.
   ⚠ **무료 개방 기한(free_open_until)을 안 보고 있었다**(2026-08-03 발견).
     `active` 만 봐서, 자녀를 막 등록한 사람에게 그 자리에서 «체험이 끝났어요»가 떴다 —
     2주 체험이 남아 있는데도 첫 실행이 통째로 막힌 것이다.
   ⚠ 기한은 **서버가 주는 값**이다. 앱이 지어내지 않는다. 값이 없으면 닫힌 것으로 본다. */
const passOpen = (c) => {
  if (c?.pass?.active) return true;
  const until = String(c?.pass?.free_open_until || "");
  return /^\d{8}$/.test(until) && TODAY <= until;
};
/* 아이 하나의 이용권 상태를 한마디로. 세 화면(내정보·자녀전환·잠금)이 같은 말을 쓴다.
   ⚠ 「무료」라고 쓰지 않는다 — 2026-07-28부터 무료 티어가 없다. 체험이 끝나면 «필요»다. */
function passLabel(c) {
  if (!passOpen(c)) return { t: "이용권 필요", cls: "need" };
  const d = passDaysLeft(c);
  if (d <= 14) return { t: d <= 0 ? "체험 오늘까지" : `체험 ${d}일`, cls: d <= 3 ? "soon" : "" };
  return { t: "쓰는 중", cls: "" };
}

const App = {
  render() {
    /* 🇰🇷 한글 조합 중에는 다시 그리지 않는다 (2026-07-27).
       글자마다 화면을 새로 그리면 조합 중이던 <input> 이 통째로 새 노드로 갈려
       IME 가 잡고 있던 상태가 날아간다 → «김» 이 «ㄱㅣㅁ» 으로 풀려 찍힌다.
       개별 핸들러마다 막으면 한 곳만 빠뜨려도 그 칸이 깨지므로 **여기서 한 번에** 막는다.
       미뤄둔 그리기는 조합이 끝날 때(compositionend) 커서 자리를 지키며 실행된다. */
    if (IME_ON) { IME_DIRTY = true; return; }
    /* ⚠ 주소가 비어 있으면 «로그인»이 아니라 **로그인 여부로** 정한다.
       예전엔 `location.hash || "#login"` 이라 빈 주소가 무조건 login 이 됐다.
       주소를 안 지우던 시절엔 티가 안 났는데, 시작할 때 주소를 비우도록 바꾸자마자
       **로그인한 사람이 로그인 화면에 갇혔다**(2026-07-28 실측·자책). */
    let name = (location.hash || "").slice(1);
    /* 옛 주소 호환 (2026-08-03) — `#school` 은 탭 다섯 개를 한 화면에 몰아넣던 시절의 것이다.
       바깥(위젯·알림·저장된 링크)에서 아직 올 수 있으니, 보던 탭에 맞는 **단독 화면**으로 넘긴다.
       replaceState 라 뒤로가기 기록에 «학교 탭»이 남지 않는다. */
    if (name === "school") {
      /* ⚠ schedule → calendar 매핑을 **뺐다**(08-09). 달력은 #calendar 로 떨어져 나갔는데
         calendar() 가 S.schoolTab="schedule" 을 전역에 써 놓고 나가서, 달력을 본 뒤
         #school 에 닿으면 **주소는 #school 인데 달력이 그려졌다**(스샷 두 장이 픽셀까지 같았다).
         메뉴로 들어오면 go() 가 info 를 넣어 괜찮고 뒤로가기·옛 주소로 올 때만 터졌다.
         ⚠ 라우터가 화면을 고른 뒤에 school() 이 돈다 — school() 안에서 고치려 했다가 안 먹었다. */
      name = { meal: "meal", timetable: "timetable", community: "community" }[S.schoolTab] || "schoolinfo";
      history.replaceState(null, "", "#" + name);
    }
    /* 주소가 비었을 때의 «집» — 회원은 홈, 비회원(설문까지 마친 사람)은 둘러보기,
       아직 아무것도 안 본 사람만 로그인이다(2026-08-03). */
    if (!name || !Screens[name]) name = (S.loggedIn || isGuest()) ? "home" : "login";
    /* 처음 깐 사람에겐 «뭐가 되는 앱인지» 4장부터(2026-08-03). 한 번 보면 다시 안 나온다 */
    if (!S.loggedIn && name === "login" && !localStorage.getItem("eduthink.introSeen")) {
      name = "intro";
      if (!S.introStep) S.introStep = "slides";   // 첫 실행은 **소개 슬라이드부터**(§5)
    }
    /* 비회원은 **전부 볼 수 있다**(2026-08-04 확정). 막지 않는다.
       ⚠ 두 번 좁혔다가 열었다: «학교 골라 급식만» → «홈만» → **다 열기**.
         이유는 하나다 — 어차피 자녀가 없어 **아무것도 실제로 되지는 않는다.**
         그러면 막을 게 아니라 보여주는 편이 «이 앱이 뭐 하는 앱인지»를 훨씬 잘 말한다.
       ⚠ 대신 **자녀가 없어도 안 죽어야 한다.** `cur()` 를 그냥 쓰는 화면은 전부 손봤다
         (아래 화면들의 `c ?` 분기). 새 화면을 만들 때도 이 전제를 지킬 것.
       ⚠ 쓰기(저장·결제·업로드)는 서버 토큰이 없어 어차피 막힌다. 화면에서도
         «가입하면 열려요»로 되돌린다 — 눌렀는데 조용히 실패하면 고장으로 읽힌다. */
    if (!S.loggedIn && !AUTH_FREE.includes(name) && !isGuest()) name = "login";
    /* 🔒 자녀 토큰이면 자녀 화면 밖으로 못 나간다 (2026-08-02 폰 실측으로 잡음).
       주소창이 없는 앱이라 «어차피 못 간다»고 여겼는데, 카메라를 다녀오거나 뒤로가기 한 번이면
       #home 으로 떨어졌고 라우터는 그걸 그대로 부모 홈으로 그렸다.
       주소도 같이 되돌린다 — 안 그러면 뒤로가기가 계속 부모 화면을 두드린다. */
    if (isChildToken() && !CHILD_SCREENS.includes(name)) {
      name = "game";
      if (location.hash !== "#game") history.replaceState(null, "", "#game");
    }
    /* 🎮 **아이 폰의 홈은 게임이다**(대표님 지적 08-08: 「아이폰 화면을 봐봐 이거 아니잖아」).
       옛 자녀 홈(childview — 카드 덱)이 홈으로 남아 있어서, 아이가 앱을 켜면
       게임이 아니라 예전 화면을 봤다. 급식·친구·수업 입력 화면은 그대로 살아 있고,
       이제 «학교 미션» 카드를 눌러 들어간다.
       ⚠ 부모의 «아이 화면 미리보기»(S.kidMode)도 같은 길로 게임을 본다. */
    if ((isChildToken() || S.kidMode) && (name === "home")) {
      name = "game";
      if (location.hash !== "#game") history.replaceState(null, "", "#game");
    }
    /* 🔒 아이 모드 — 열어 줄 화면은 넷뿐(§5④). 서랍만 감추면 주소·뒤로가기로 샌다 */
    if (S.kidMode && !["game", "mission", "store", "tickets"].includes(name)) {
      name = "game";                       // 아이 모드의 홈도 게임이다(위 주석 참조)
      if (location.hash !== "#game") history.replaceState(null, "", "#game");
    }
    // 연결이 끝난 자녀폰 — 로그인으로 조용히 튕기지 않는다(2026-08-02 구멍 2-2)
    if (S.childLinkEnded && !["childexpired", "childlink", "terms", "policy"].includes(name)) {
      name = "childexpired";
      if (location.hash !== "#childexpired") history.replaceState(null, "", "#childexpired");
    }
    // 자녀 앱 첫 실행(연결 직후) — 테마를 먼저 고른다. 고르기 전엔 홈이 없다.
    if (isChildToken() && (name === "game") && !S.kidTheme) {
      name = "childtheme";
      if (location.hash !== "#childtheme") history.replaceState(null, "", "#childtheme");
    }
    // 자녀 테마 스탬프 — 자녀 화면일 때만. 부모 미리보기(S.childView)도 입어본다.
    applyKidTheme((isChildToken() || S.childView) && CHILD_SCREENS.includes(name) && name !== "login");
    /* 자녀 토큰인데 «내가 누군지»를 모르면 자녀 화면이 통째로 죽는다(빈 화면 — 2026-08-02 실측).
       앱을 지웠다 깔거나 저장이 날아간 경우다. 흰 화면 대신 **코드 다시 넣는 화면**으로 보낸다. */
    if (isChildToken() && (name === "game") && !cur()) {
      name = "childlink";
      if (location.hash !== "#childlink") history.replaceState(null, "", "#childlink");
    }
    /* 체험이 끝났고 이용권도 없으면 **잠금 화면**으로 보낸다.
       ⚠ 부팅 중(S.booting)에는 판단하지 않는다 — 아직 자녀를 못 받아온 상태라
          «이용권 없음»으로 잘못 읽고 첫 화면이 잠금으로 뜬다(자녀등록 사고와 같은 함정). */
    if (S.loggedIn && !S.booting && cur() && !passOpen(cur())
        && !AUTH_FREE.includes(name) && !PASS_FREE.includes(name)) {
      // 자녀폰에 결제·내정보·로그아웃을 열어주면 안 된다(2026-08-03 에뮬 실기에서 잡음)
      name = isChildToken() ? "childlocked" : "locked";
    }
    if (name !== "home" && name !== "game") S.chatOpen = false;
    /* 고객센터에 들어올 때 내 문의를 한 번 받아온다. 앱 시작마다 받아오면 쓰지도 않을 요청이
       하나 늘어 첫 화면이 늦어진다 — 필요한 자리에서만 부른다(체감속도 작업과 같은 규칙). */
    if ((name === "help" || name === "asks") && S.loggedIn && S.inquiries === null) this.loadInquiries();
    /* 미션은 **홈에서도** 받아온다 — 홈 카드에 「오늘 2/3」이 떠야 부모가 누를 이유가 생긴다.
       미션·자녀 화면에서도 같은 값을 쓴다. 한 번 받아오면 다시 안 부른다(force 로만 갱신). */
    if (["home", "mission"].includes(name) && S.loggedIn && S.missions === null) this.loadMissions();
    // 보상 화면 로더 (2026-08-07) — 필요한 화면에서만(첫 화면을 늦추지 않게)
    if (["game"].includes(name) && S.loggedIn) { this.loadCoin(); if (S.missions === null) this.loadMissions(); }
    if (["store", "home", "game"].includes(name) && S.loggedIn && S.store === null) this.loadStore();
    if (["tickets", "store"].includes(name) && S.loggedIn && S.rewards === null) this.loadRewards();
    // 게임 화면 — 카드가 하나씩 뒤늦게 뜨면 «고장»으로 읽힌다. 들어올 때 한 번에 부른다
    if (name === "game" && S.loggedIn) this.gameEnter();
    if (["mission", "home"].includes(name) && S.loggedIn && S.verifyPending === null) this.loadVerify();
    if (name === "childmode" && S.loggedIn && S.pinHas === null) this.loadPinState();
    if ((isChildToken() || S.childView || S.kidMode) && ["home", "store"].includes(name)
        && S.loggedIn) this.loadReactions();
    if (name === "report" && S.loggedIn) this.loadReport();
    // 요금은 자녀마다 다르다(둘째부터 싸다) → 이용권 화면에 들어올 때 그 자녀 기준으로 받아온다
    if (name === "pay" && S.loggedIn && this._planFor !== cur()?.server_id) {
      this._planFor = cur()?.server_id; S.planList = null; S.planSeat = 1; this.loadPlans();
    }

    /* 커뮤니티 대화는 **그 화면에 있을 때만** 받아온다(2026-08-01).
       다른 화면에서도 계속 돌면 배터리와 통신을 그냥 태운다 — 채팅은 보고 있을 때만 새로우면 된다. */
    const inComm = name === "school" && S.schoolTab === "community";
    if (inComm && !S.commTimer) {
      S.commTimer = setInterval(() => this.commPoll(false), 8000);
      this.commPoll(true);
    } else if (!inComm && S.commTimer) {
      clearInterval(S.commTimer); S.commTimer = null;
    }
    /* 저장 안 한 사진을 두고 업로드 화면을 떠나면 말해준다(2026-07-31 실사용 사고 —
       스캔→미리보기까지 하고 저장을 안 누른 채 타임라인으로 가서 «저장이 안 된다»가 됐다). */
    if (this._prev === "upload" && name !== "upload" && S.uploadStep === 1 && S.shots.length && !S.uploadBusy) {
      toast(`사진 ${S.shots.length}장이 아직 저장 전이에요 — 기록 넣기에서 「저장」을 눌러주세요`);
    }
    this._prev = name;
    // 자녀가 하나도 없으면 어느 화면도 그릴 수 없다(전부 cur()를 읽는다) → 등록 화면으로 보낸다.
    // 예전엔 여기서 «face를 읽을 수 없다»로 앱이 통째로 멈췄다(2026-07-26 실측).
    /* ⚠ 켜자마자 부르는 loadMe() 가 아직 안 끝났으면 **여기서 판단하지 않는다.**
       그 순간엔 자녀 목록이 비어 있어서 «등록된 아이가 없다»로 잘못 읽힌다. */
    /* ⚠ 자녀폰은 여기서 걸리면 안 된다 — 자녀 화면은 cur()(부모의 자녀 목록)를 안 쓰고
       S.childLinked 로 그린다. 자녀 목록이 비었다고 등록 화면으로 보내면
       아이 폰에 «자녀 등록»이 뜬다(2026-08-02 실측). */
    if (S.loggedIn && !S.booting && !cur() && !isChildToken()
        && !["child-add", "childlink", "register", "findpw"].includes(name)) {
      name = "child-add";
      if (location.hash !== "#child-add") { location.hash = "#child-add"; return; }
    }
    if (S.booting && S.loggedIn && !cur()) {
      // 잠깐이지만 빈 화면을 보여주느니 «불러오는 중»이라고 말한다
      document.getElementById("screen").innerHTML =
        `<div style="padding:60px 20px;text-align:center;color:var(--muted)">불러오는 중…</div>`;
      return;
    }

    // 자녀가 바뀐 «첫 그림»은 캐시로 즉시 — 서버는 아래 LOADED 블록이 뒤에서 받아 다시 그린다(2026-07-31 체감속도)
    if (S.loggedIn && cur()?.server_id && LOADED.childId !== cur().server_id) applyLifeCache(cur());
    /* ⚠ 학원 편집 시트(planBar)·지우기 확인(planKillView)은 **여기서** 붙인다.
       예전엔 방과후 화면 마크업 안에 있어서, 시간표의 「하교 후」 목록을 눌러도
       상태만 바뀌고 창이 안 떴다 — 눌러도 아무 일 없는 것처럼 보였다(2026-07-28 실측). */
    /* 떠 있던 팝업을 기억해 둔다 — 같은 팝업이면 다시 열리는 시늉을 하지 않는다 */
    const POPS = ".sheet, .chatsheet, .overlay, .killwrap, .modal";
    const popKey = (root) => [...root.querySelectorAll(POPS)].map((e) => e.className).join("|");
    const popScroll = [...document.querySelectorAll(POPS)].map((e) => e.scrollTop);
    const popBefore = popKey(document);

    /* 🎮 **아이는 게임 세계 밖으로 안 나간다**(2026-08-08 통일).
       상점에서 「티켓 보러 가기」를 누르면 갑자기 부모 테마 화면이 뜨고, 급식·친구·수업도
       또 다른 색이었다 — 한 앱을 쓰는데 화면마다 다른 세계로 넘어가는 꼴이었다.
       아이가 보는 화면은 **같은 바탕·같은 카드·같은 그림자**로 감싼다.
       ⚠ 게임 화면(game)은 스스로 껍데기를 갖고 있으니 두 번 감싸지 않는다.
       ⚠ 부모가 볼 때는 감싸지 않는다 — 부모 앱은 테마 18종을 그대로 탄다. */
    /* «보상 구획»은 부모가 봐도 같은 세계다 — 미션 관리에서 상점·티켓으로 넘어가는데
       거기만 옛 부모 테마면 또 다른 앱이 된다(대표님 지적 08-08: 「부모페이지 작업 안 된 곳 많어」). */
    const WORLD = ["tickets", "store", "mission"];
    const KID_ONLY = ["childmealrate", "childfriend", "childsubject", "childtt"];
    const kidNow = isChildToken() || S.kidMode;
    const asKid = WORLD.includes(name) || (kidNow && KID_ONLY.includes(name));
    const body = Screens[name]();
    document.getElementById("screen").innerHTML =
      (asKid ? `<div class="gmw">${body}</div>` : body)
      + planBar() + lunchSheet() + promoteSheet() + planKillView() + holdMenuView() + pwAskView();

    if (popBefore && popKey(document) === popBefore) {
      [...document.querySelectorAll(POPS)].forEach((e, i) => {
        e.classList.add("noanim");
        if (popScroll[i]) e.scrollTop = popScroll[i];
      });
    }
    // 대화는 아래가 최신 — 열면 맨 밑부터 보인다
    if (S.chatOpen) { const b = document.getElementById("csbody"); if (b) b.scrollTop = b.scrollHeight; }
    /* 홈 대화바가 아이콘 격자를 덮던 것(2026-08-03 폰 실측 29px) — 실측해서 그만큼 비운다 */
    const cb = document.querySelector(".chatbar");
    document.documentElement.style.setProperty("--chatbar-gap",
      cb ? (cb.offsetHeight + (document.getElementById("tabbar")?.offsetHeight || 0) + 28) + "px" : "0px");
    this.fitPage();   // 서류 미리보기 — 종이 한 장을 화면에 맞춰 축소
    hydrateImages();  // 서버에 있는 기록 사진을 인증 붙여 받아 끼운다
    attachPinch();    // 기록 크게보기가 떠 있으면 핀치 줌을 붙인다(없으면 아무 일 없음)
    attachCalSwipe(); // 일정 달력이 떠 있으면 좌우 스와이프로 달 넘기기
    attachDaySwipe(); // 일간 화면이면 좌우 스와이프로 날짜 넘기기(§7)
    attachIntroSwipe(); // 소개 슬라이드 좌우 스와이프(§5)
    autoGrowAll();    // 여러 줄 칸을 내용 길이에 맞춘다(체험학습 계획 등)
    pushWidget();     // 바탕화면 위젯에 오늘 값 넘기기(앱을 열 때마다 최신으로)
    // 자녀가 바뀌었으면 그 아이 학교 데이터를 받아온다(받고 나면 스스로 다시 그린다)
    if (S.loggedIn && cur()?.school?.slug && SCHOOL.slug !== cur().school.slug) loadSchool();
    // 자녀가 바뀌면 그 아이의 기록·서류·대화·커뮤니티도 다시 받는다(안 하면 앞 아이 것이 그대로 보인다)
    if (S.loggedIn && TOKENS.access && cur()?.server_id && LOADED.childId !== cur().server_id && !LOADED.busy) {
      LOADED.busy = true; LOADED.childId = cur().server_id;
      const forChild = cur();
      Promise.all([loadRecords(), loadLife()])
        .then(() => { if (cur()?.server_id === forChild.server_id) saveLifeCache(forChild); })   // 받은 걸 다음 즉시 그림용으로
        .finally(() => { LOADED.busy = false; });
    }
    /* 하단 탭바 부활(2026-08-02 시안 D) — 2026-07-24에 폐지했던 것을 되돌렸다.
       로그인 전(AUTH_FREE)과 **자녀폰**에는 띄우지 않는다.
       ⚠ 자녀 세션 판별은 반드시 `isChildToken()` 으로 한다 — `S.childView`(부모용 미리보기
          스위치)를 근거로 삼으면 자녀폰에 부모 메뉴가 샌다(2026-08-02 보안 3건과 같은 함정). */
    const onHome = name === "home";
    noteToday();   // 오늘 도장·사진을 달력용으로 적어 둔다(§3). 값이 그대로면 아무 일도 안 한다
    const tabbar = document.getElementById("tabbar");
    /* 탭바 폐기(2026-08-03 홈 v3) — 홈=허브(☰·캘린더·미션 버튼). 되살리려면 아래 false 를 지운다 */
    const showTabs = false && S.loggedIn && !AUTH_FREE.includes(name) && !isChildToken()
      && !(S.childView && CHILD_SCREENS.includes(name));   // 부모의 자녀 미리보기도 실물처럼 — 탭바 없음
    tabbar.classList.toggle("hidden", !showTabs);
    if (showTabs) {
      /* 어느 칸에 불이 들어오나 — 화면 이름이 탭 이름과 1:1이 아니다.
         업로드·기록상세는 「서랍」에서, 서식은 「내정보」에서 들어간 곳이라 그 탭에 불이 남아야
         길을 잃지 않는다. 학교 화면은 일정 탭을 보고 있을 때만 「일정」이 켜진다. */
      const TAB_OF = { home: "home", calendar: "calendar",
                       timeline: "timeline", upload: "timeline", record: "timeline",
                       mission: "mission", report: "mission", docs: "mypage", mypage: "mypage", pay: "mypage",
                       afterschool: "home", supplies: "home", notify: "home" };
      const on = name === "school" ? (S.schoolTab === "schedule" ? "calendar" : "") : (TAB_OF[name] || "");
      tabbar.querySelectorAll("a").forEach((a) => {
        const isOn = a.dataset.tab === on;
        a.classList.toggle("active", isOn);
        // 클래스는 눈에만 보인다. 보조기기에 «지금 여기»를 전하는 건 aria-current 다.
        if (isOn) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
      });
    }
    /* 탭바가 돌아왔으므로 상단 가운데 집버튼은 자리를 내준다 — 돌아가는 길이 둘이면 헷갈린다.
       마크업은 남겨 두되 항상 숨긴다(되살릴 일이 생기면 이 줄만 고치면 된다). */
    document.getElementById("homefab").classList.add("hidden");

    /* 코치마크 (§5) — 홈이 **그려진 뒤** 한 번만 연다.
       구멍 자리를 실제 요소에서 재기 때문에 그리기 전에 열면 짚을 곳을 못 찾는다.
       ⚠ 자녀폰에는 띄우지 않는다 — 부모 화면 설명이다. */
    if (onHome && S.loggedIn && !isChildToken() && S.coach === null
        && !localStorage.getItem(COACH_KEY)) {
      App.coachStart();
    }
    // 전광판 시계 — 홈에서만 돈다. 나가면 다음 tick 이 스스로 멈춘다(§1)
    if (onHome) startBoard();

    /* 캐러셀 자동 스냅은 없앴다(2026-08-03) — 가로 카드 더미를 시간 축으로 바꾸면서
       «어느 카드를 보여줄까»라는 문제 자체가 사라졌다. 축은 언제나 지금 자리를 가리킨다. */

    /* 잠금 화면 — 두 가지가 같은 판을 쓴다(2026-07-31 앱 잠금 배선).
       ① 앱 잠금: 켜두면 앱을 켜거나 오래 자리를 비웠다 돌아올 때 **화면 전체**를 덮는다
       ② 기록 잠금: 기록·업로드 화면 첫 진입 때만 (예전부터 있던 것)
       로그인 전에는 덮지 않는다 — 로그인 화면까지 잠그면 들어갈 길이 없다. */
    const appLockNow = S.appLock && S.appLocked && S.loggedIn;
    const recLockNow = BIO_LOCKED.includes(name) && !S.bioUnlocked;
    const lockOn = appLockNow || recLockNow;
    if (lockOn) {
      document.getElementById("biolock-t").textContent = appLockNow ? "앱 잠금" : "기록 잠금";
      document.getElementById("biolock-p").innerHTML = appLockNow
        ? "잠금을 풀어야 앱을 볼 수 있어요.<br>지문·얼굴 또는 기기 비밀번호로 풀어요."
        : "자녀 기록은 잠금 해제 후 볼 수 있어요.<br>지문·얼굴 또는 기기 비밀번호로 풀어요.";
    }
    document.getElementById("biolock").classList.toggle("hidden", !lockOn);
    /* ⛔ 캐러셀 자동 넘김 타이머를 걸지 않는다(2026-07-28).
       새 홈에 캐러셀이 없는데 3초마다 홈을 통째로 다시 그리고 있었다 — 보이는 것도 없이
       배터리만 쓰고, 그 순간 눌린 것·입력 중인 것을 날릴 수 있는 자리였다.
       startCarousel() 은 캐러셀이 돌아올 때를 위해 남겨둔다. */
    window.scrollTo(0, 0);
  },
  go(key) { const m = menuOf(key); if (m) { m.go(); this.render(); } },   // 원형 메뉴 → 해당 페이지

  /* ── 오늘 캐러셀(2026-08-02) ───────────────────────────
     스크롤 → 도트만 직접 바꾼다. render() 를 부르면 스와이프 중에 화면이 통째로
     다시 그려져 손가락 아래에서 카드가 사라진다. */
  hdCarScroll() {
    const car = document.getElementById("hdcar"), dots = document.getElementById("hddots");
    if (!car || !dots) return;
    const i = Math.round(car.scrollLeft / car.clientWidth);
    [...dots.children].forEach((d, j) => d.classList.toggle("on", j === i));
  },
  recRetry(btn) {
    const box = btn.parentElement, im = box?.querySelector("img[data-rec]");
    btn.remove();
    if (im) { delete im.dataset.done; im.classList.remove("rec-fail"); hydrateImages(); }
  },
  openMessages() { S.childView = false; location.hash = "#home"; this.chatOpen(); },   // 캐러셀 → 대화창 바로 올리기
  // 홈 캐러셀 자동 넘김 — 홈에서만 3초마다 다음 카드
  startCarousel() {
    clearInterval(this._carTimer);
    this._carTimer = setInterval(() => {
      // 대화창을 열어둔 동안은 넘기지 않는다 — 3초마다 다시 그리면 쓰던 글자가 날아간다
      if (S.chatOpen) return;
      if (location.hash === "#home" || location.hash === "") { S.carIdx++; this.render(); }
      else { clearInterval(this._carTimer); this._carTimer = null; }   // 홈 벗어나면 멈춤(재진입 시 다시 시작)
    }, 3000);
  },

  // ── 홈 편집 ────────────────────────────────────────────────
  // 메뉴 하나 끄기/켜기. 전부 끄면 홈이 텅 비니 마지막 하나는 막는다.
  menuToggle(key) {
    const off = S.menuHidden.includes(key);
    if (!off && S.menuHidden.length >= MENU_KEYS.length - 1) return toast("카드는 최소 하나는 남겨두세요");
    S.menuHidden = off ? S.menuHidden.filter((k) => k !== key) : [...S.menuHidden, key];
    saveHome(); this.render();
  },
  carToggle(key) {
    S.carHidden = S.carHidden.includes(key) ? S.carHidden.filter((k) => k !== key) : [...S.carHidden, key];
    S.carIdx = 0; saveHome(); this.render();
  },
  carAutoToggle() {
    S.carAuto = !S.carAuto;
    if (!S.carAuto) { clearInterval(this._carTimer); this._carTimer = null; }
    saveHome(); this.render();
  },
  holiToggle() {
    S.holiOff = !S.holiOff;
    saveHome(); this.render();
  },
  homeReset() {
    S.menuOrder = [...MENU_KEYS]; S.menuHidden = [...MENU_OFF_DEFAULT]; S.carHidden = []; S.carAuto = true; S.holiOff = false;
    saveHome(); this.render(); toast("기본값으로 되돌렸어요");
  },
  // 손잡이를 잡고 끌어 순서 바꾸기 — 방과후 블록(gripDown)과 같은 포인터 방식.
  // 끄는 동안은 다시 그리지 않고 CSS transform으로만 미리 보여주고, 손을 떼는 순간 한 번만 반영한다.
  menuDrag(e, from) {
    e.preventDefault();
    const list = document.getElementById("edlist");
    if (!list) return;
    const rows = [...list.children];
    const step = rows.length > 1 ? rows[1].offsetTop - rows[0].offsetTop : rows[0].offsetHeight;
    const startY = e.clientY;
    let to = from;
    rows[from].classList.add("dragging");
    const move = (ev) => {
      const dy = ev.clientY - startY;
      to = Math.max(0, Math.min(rows.length - 1, from + Math.round(dy / step)));
      rows.forEach((r, i) => {
        if (i === from) { r.style.transform = `translateY(${dy}px)`; return; }
        // 끌려 올라간 자리만큼 나머지가 한 칸씩 비켜선다
        const shift = (from < to && i > from && i <= to) ? -step
                    : (from > to && i >= to && i < from) ? step : 0;
        r.style.transform = shift ? `translateY(${shift}px)` : "";
      });
    };
    const up = () => {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      const order = [...S.menuOrder];
      order.splice(to, 0, order.splice(from, 1)[0]);
      S.menuOrder = order;
      saveHome();
      App.render();
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  },
  setTheme(t) { S.theme = t; document.documentElement.setAttribute("data-theme", t); saveHome(); this.render(); },
  /* 로그인 — 서버가 있으면 **진짜로** 로그인해 토큰을 받는다(2026-07-25).
     토큰이 있어야 기록을 올리고 다시 볼 수 있다. 서버가 없으면 지금까지처럼 목업으로 들어간다. */
  async login(id, pw) {
    if (S.loginBusy) return;
    const userid = (id ?? document.querySelector('#login-id')?.value ?? "").trim();
    const pass = pw ?? document.querySelector('#login-pw')?.value ?? "";
    if (userid && pass) {
      S.loginBusy = true; this.render();
      try {
        // 기기 이름을 같이 보낸다 — 내 정보에서 「엄마 폰 / 아빠 폰」을 알아보게(부모 2대 제한)
        const r = await api("/auth/login", { method: "POST", body: { login_id: userid, password: pass, device_label: deviceLabel() } });
        S.loginBusy = false;
        if (r?.ok) {
          saveTokens(r.data);
          S.loggedIn = true; S.serverAuth = true;
          await loadMe();
          location.hash = "#home"; this.render();
          return toast("로그인했어요");
        }
        // 잠금(10회 실패)·비번 틀림은 사유를 그대로 보여준다
        this.render();
        return toast(r?.error?.message || "로그인하지 못했어요");
      } catch (e) {
        // 서버에 못 닿았다. 검수 중에는 목업으로 들어가고, 배포본은 그냥 알려주고 만다.
        S.loginBusy = false;
        if (!DEV_TOOLS) { this.render(); return toast("서버에 연결하지 못했어요. 잠시 후 다시 시도해 주세요."); }
      }
    }
    /* ⚠ 아이디·비번을 비우고 눌러도 들어가지던 **목업 통로**였다.
       배포본에 그대로 남아 있어서 아무나 로그인 없이 앱에 들어왔다(2026-07-27 사장님이 발견).
       검수용 지름길은 DEV_TOOLS 뒤에만 둔다 — 배포본에서는 절대 열리지 않는다. */
    if (!DEV_TOOLS) {
      this.render();
      return toast(userid || pass ? "아이디와 비밀번호를 모두 입력해 주세요." : "아이디와 비밀번호를 입력해 주세요.");
    }
    S.loggedIn = true; S.serverAuth = false; location.hash = "#home"; this.render();
  },
  // 회원가입 — 입력할 때마다 다시 그려 각 칸 아래 유효성 표시. 포커스는 되돌린다.
  regSet(key, val) {
    S.reg[key] = val;
    if (S.regServerErr[key] || S.regServerErr._) { delete S.regServerErr[key]; delete S.regServerErr._; }   // 고치기 시작하면 서버 사유는 지운다
    renderKeepFocus();
  },
  // 가입 → 자녀 등록(필수).
  // ① 앱이 형식을 본다 → ② **서버가 한 번 더 본다**(중복 아이디·이메일, 약관 동의).
  //    앞칸 검사만 믿으면 직접 POST로 우회된다 — 계약 §3.3이 서버 검사를 요구한다.
  /* 회원가입 — **진짜 계정을 만든다**(2026-07-27 배포).
     검수 중(DEV_TOOLS)에는 dry_run 으로 «검사만» 한다. 클릭 검수가 계정을 쌓으면 안 된다.
     배포본은 dry_run 없이 보내고, 돌아온 토큰을 저장해 그대로 로그인 상태가 된다. */
  async registerDone() {
    if (S.regBusy) return;
    S.regServerErr = {};
    if (!regValid()) { this.render(); return toast("빨간 칸을 확인해 주세요"); }

    S.regBusy = true; this.render();
    const r = S.reg;
    try {
      const res = await api("/auth/register", { method: "POST", body: {
        login_id: r.userid, password: r.pw, name: r.name, birth_ymd: r.birth,
        email: r.email, phone: (r.phone || "").replace(/-/g, ""),
        agree_terms: !!r.t1, agree_privacy: !!r.t2, device_label: deviceLabel(),
        // 광고성 수신(선택) — 안 켰으면 셋 다 false 로 보낸다(미동의도 기록해야 한다)
        marketing: { email: !!(r.t3 && r.m1 !== false), sms: !!(r.t3 && r.m2 !== false), call: !!(r.t3 && r.m3 !== false) },
        ...(DEV_TOOLS ? { dry_run: true } : {}),
      } });
      if (!res?.ok) {
        // 서버가 칸별로 알려준 사유를 그 칸 아래에 붙인다(계약 §1.3 fields)
        const F = { login_id: "userid", password: "pw", birth_ymd: "birth", name: "name", email: "email", phone: "phone" };
        const fields = res?.data?.fields || {};
        const mapped = {};
        for (const [k, v] of Object.entries(fields)) mapped[F[k] || k] = v;
        if (!Object.keys(mapped).length) mapped._ = res?.error?.message || "가입할 수 없어요";
        S.regServerErr = mapped;
        S.regBusy = false; this.render();
        return toast(Object.values(mapped)[0]);
      }
      // 배포본은 여기서 **토큰을 받아 저장**한다 — 안 하면 가입만 되고 로그인이 안 된 채로 들어간다.
      if (!DEV_TOOLS) {
        if (!res.data?.access_token) {
          S.regBusy = false; this.render();
          return toast("가입은 됐는데 로그인에 실패했어요. 로그인 화면에서 다시 시도해 주세요.");
        }
        saveTokens(res.data);
        S.serverAuth = true;
        await loadMe();
      }
    } catch (e) {
      // 서버에 못 닿았다. 검수 중에는 그냥 진행하고, 배포본은 계정이 안 만들어졌음을 분명히 알린다.
      S.regBusy = false;
      if (!DEV_TOOLS) { this.render(); return toast("서버에 연결하지 못했어요. 가입되지 않았습니다."); }
      toast("지금은 인터넷에 연결되지 않았어요");
      S.loggedIn = true; location.hash = "#child-add"; this.render();
      return;
    }
    S.regBusy = false;
    S.loggedIn = true; location.hash = "#child-add"; this.render();
  },
  /* 로그아웃 — 토큰만 지우면 **화면에 앞사람 데이터가 그대로 남는다**(2026-07-26 실측).
     다음 사람이 목업으로 들어오면 남의 아이 이름·기록·대화가 보인다. 흔적을 다 지운다. */
  logout() {
    saveTokens(null);
    S.loggedIn = false; S.serverAuth = false; S.bioUnlocked = false;
    clearKids();   // 로그아웃하면 캐시도 지운다 — 다음 사람 화면에 남의 아이 이름이 뜨면 안 된다
    try { localStorage.removeItem(SCHOOL_CACHE_KEY); } catch (e) {}
    try { localStorage.removeItem(LIFE_CACHE_KEY); } catch (e) {}   // 기록·준비물 목록도 남의 것이다
    try { localStorage.removeItem(CHILD_ME_KEY); } catch (e) {}     // 자녀폰이었다면 그 아이도 지운다
    S.childView = false; S.childLinked = null;
    resetUserData();
    location.hash = "#login"; this.render();
  },

  /* ── 자녀폰 연결 ─────────────────────────────────────────
     코드를 서버에 내고 **자녀 전용 토큰**을 받는다. 부모 토큰은 이 폰에 들어오지 않는다.
     성공하면 이 폰은 자녀 모드로 굳는다(연결 해제는 부모 확인이 필요하게 두는 게 맞다). */
  async childLink() {
    if (S.linkBusy) return;
    const code = (S.linkCode || "").trim();
    S.linkErr = "";
    if (!/^\d{6}$/.test(code)) { S.linkErr = "6자리 숫자를 넣어주세요"; return this.render(); }
    S.linkBusy = true; this.render();
    try {
      const r = await api("/auth/child-claim", { method: "POST", body: { code } });
      S.linkBusy = false;
      if (!r?.ok) { S.linkErr = r?.error?.message || "연결하지 못했어요"; return this.render(); }
      saveTokens({ access_token: r.data.access_token });     // refresh는 안 온다 — 만료되면 새 코드
      /* 🔒 토큰만 바꾸면 안 된다 — 이 폰에 남은 **부모 캐시부터 지운다**(2026-08-02).
         순서가 중요하다: 지우고 나서 자녀 정보를 넣어야 한다. */
      wipeParentData();
      setChildMe(r.data.child);              // 이 폰이 아는 아이는 이제 이 한 명뿐이다
      S.childLinkEnded = false;
      // 테마는 서버가 기억한다 — 기기를 바꿔도 아이가 고른 화면이 따라온다
      api("/child/prefs").then((pr) => {
        if (pr?.ok && pr.data?.theme && KID_THEMES[pr.data.theme]) {
          S.kidTheme = pr.data.theme; S.kidAccent = pr.data.accent;
          localStorage.setItem(KID_PREF_KEY, JSON.stringify({ theme: S.kidTheme, accent: S.kidAccent }));
          this.render();
        }
      }).catch(() => {});
      S.loggedIn = true; S.serverAuth = true; S.childView = true;
      S.linkCode = "";
      location.hash = "#game";
      loadSchool(true);                      // 급식·시간표 — /me 는 자녀에게 막혀 있다
      this.render();
      toast(`${r.data.child.nickname} 폰으로 연결됐어요`);
    } catch (e) {
      S.linkBusy = false; S.linkErr = "서버에 못 붙었어요. 잠시 뒤 다시 해주세요";
      this.render();
    }
  },

  /* 부모 쪽 — 자녀폰에 넣을 코드를 만든다. 10분·1회용.
     ⚠ 아이 1명당 1대다 — 이미 붙은 폰이 있으면 새 폰이 붙는 순간 앞 폰이 끊긴다(서버가 판정). */
  async inviteChild(childId) {
    const c = childId ? STUB.children.find((x) => x.id === childId) : cur();
    if (!TOKENS.access || !c?.server_id) return toast("로그인 후에 쓸 수 있어요");
    if (S.inviteBusy) return;
    S.inviteBusy = true; this.render();
    const r = await api(`/children/${c.server_id}/invite`, { method: "POST" }).catch(() => null);
    S.inviteBusy = false;
    if (!r?.ok) { this.render(); return toast(r?.error?.message || "코드를 만들지 못했어요"); }
    S.inviteCode = r.data.code;
    S.inviteFor = c.nickname;
    S.inviteUntil = Date.now() + (r.data.expires_in || 600) * 1000;
    this.render();
    if (c.child_device) toast(`${c.nickname} 폰을 새로 연결하면 지금 폰은 끊겨요`);
  },
  inviteClose() { S.inviteCode = null; S.inviteFor = null; this.render(); },
  /* 연결 끊기 — 폰을 잃어버렸거나 바꿨을 때. 그 폰은 즉시 아무것도 못 하게 된다. */
  async unlinkChild(childId) {
    const c = STUB.children.find((x) => x.id === childId);
    if (!c?.server_id) return;
    const r = await api(`/children/${c.server_id}/invite`, { method: "DELETE" }).catch(() => null);
    if (!r?.ok) return toast(r?.error?.message || "끊지 못했어요");
    c.child_device = false; c.child_device_at = null;
    saveKids(); this.render();
    toast(`${c.nickname} 폰 연결을 끊었어요`);
  },

  // ── 길게 누르기 메뉴 ──────────────────────────────────────
  holdGuard: () => holdGuard(),
  // 내 일정 — 수정·삭제
  holdEvent(e, id) {
    if (typeof e === "number") { id = e; e = window.event; }
    const ev = STUB.myEvents.find((x) => x.id === id);
    if (!ev || !e) return;
    holdStart(e, ev.title, [
      { label: "수정", icon: "ti-pencil", run: () => App.evEdit(id) },
      { label: "삭제", icon: "ti-trash", danger: true, run: () => { S.evDraft = { id, title: ev.title }; App.evDelete(); } },
    ]);
  },
  // 방과후 — 수정·삭제
  holdPlan(e, id) {
    if (typeof e === "number") { id = e; e = window.event; }
    const a = STUB.activities.find((x) => x.id === id);
    if (!a || !e) return;
    holdStart(e, a.name, [
      { label: "수정", icon: "ti-pencil", run: () => App.planEdit(id) },
      { label: "삭제", icon: "ti-trash", danger: true, run: () => { S.planDraft = { id, name: a.name }; App.planDelete(); } },
    ]);
  },
  // 기록 — 열기·수정·삭제(삭제는 기존대로 본인확인을 거친다)
  holdRecord(e, id) {
    if (typeof e === "number") { id = e; e = window.event; }
    const r = STUB.records.find((x) => x.id === id);
    if (!r || !e) return;
    holdStart(e, r.title, [
      { label: "열어보기", icon: "ti-photo", run: () => App.openRecord(id) },
      { label: "제목·시기 수정", icon: "ti-pencil", run: () => { App.openRecord(id); App.recordEditStart(); } },
      { label: "삭제", icon: "ti-trash", danger: true, run: () => { S.viewRecord = id; App.recordDelete(r.title); } },
    ]);
  },
  holdClose() { S.holdMenu = null; holdFired = false; this.render(); },
  holdRun(i) {
    const a = S.holdMenu?.actions?.[i];
    S.holdMenu = null;
    holdFired = false;                 // 메뉴를 닫는 순간 «다음 클릭 삼키기»를 푼다
    if (a?.run) a.run();
    else this.render();
  },

  /* ── 본인 확인(재인증) ─────────────────────────────────────
     계약 §3.4: **입력은 가볍게, 수정·삭제는 무겁게.** 자녀 정보 수정·기록 삭제·탈퇴가 여기 걸린다.
     흐름: 지문(있으면) → 없으면 비밀번호 → /auth/reauth 로 5분짜리 표를 받아
           그 표를 X-Reauth-Token 에 실어 원래 요청을 다시 보낸다.
     표는 5분이라 잠깐 들고 있다가 버린다(오래 들고 있으면 그게 곧 우회로가 된다). */
  async getReauth(reason) {
    if (S.reauthToken && S.reauthUntil > Date.now() + 5000) return S.reauthToken;   // 아직 살아 있으면 재사용
    const bioOk = await this._bio(reason || "본인 확인");
    const body = { biometric: !!bioOk };
    // 비번 계정이면 서버가 비밀번호를 요구한다 — 생체만으론 안 된다
    let r = await api("/auth/reauth", { method: "POST", body }).catch(() => null);
    if (!r?.ok && r?.data?.fields?.password) {
      const pw = await this.askPassword(reason);
      if (!pw) return null;
      r = await api("/auth/reauth", { method: "POST", body: { password: pw } }).catch(() => null);
    }
    if (!r?.ok) { toast(r?.error?.message || "본인 확인에 실패했어요"); return null; }
    S.reauthToken = r.data.reauth_token;
    S.reauthUntil = Date.now() + (r.data.expires_in || 300) * 1000;
    return S.reauthToken;
  },
  // 비밀번호를 화면 안에서 받는다(크롬 prompt 금지 — 2026-07-24 검수 지적)
  askPassword(reason) {
    return new Promise((res) => { S.pwAsk = { reason: reason || "본인 확인", value: "", resolve: res }; this.render(); });
  },
  pwShow() { S.pwShow = !S.pwShow; this.render(); document.getElementById("login-pw")?.focus(); },
  pwAskSet(v) { if (S.pwAsk) S.pwAsk.value = v; },
  pwAskDone(ok) {
    const a = S.pwAsk; S.pwAsk = null; this.render();
    if (a) a.resolve(ok ? (a.value || "") : null);
  },

  // ── 비밀번호 찾기 ─────────────────────────────────────────
  // 지금은 화면 흐름만. 서버가 붙으면 아래 주석의 두 요청으로 갈아끼운다.
  //   POST /auth/find-password  { login_id, email }        → 코드 메일 발송(성공/실패를 구분해 알려주지 않는다)
  //   POST /auth/reset-password { login_id, code, password } → 비번 교체 + 로그인 잠금 해제 + 기존 토큰 폐기
  findpwSet(k, v) {
    S.findpw[k] = v;
    delete S.findpw.err[k];
    const a = document.activeElement;
    renderKeepFocus();
    if (a && a.tagName === "INPUT") {
      const same = [...document.querySelectorAll("#screen input")].find((i) => i.placeholder === a.placeholder);
      if (same) { same.focus(); try { same.setSelectionRange(v.length, v.length); } catch (e) {} }
    }
  },
  findpwSend() {
    /* 메일 발송이 아직 없다. 코드를 보낸 척하면 사용자는 안 오는 메일을 기다린다. */
    toast("이메일 확인은 준비 중이에요 — 아래 고객센터로 문의해 주세요");
  },
  // 카카오로 본인 확인 — 이미 붙어 있는 소셜 로그인을 그대로 쓴다(추가 비용 0).
  // 실앱: /auth/kakao 로 보내고, 돌아온 카카오 이메일이 계정 이메일과 같으면 통과.
  findpwKakao() {
    /* 카카오 재설정도 서버 배선 전 — 카카오로 가입한 계정이면 그냥 카카오 로그인이 답이다 */
    toast("카카오로 가입하셨다면 로그인 화면에서 카카오 버튼으로 바로 들어올 수 있어요");
  },
  findpwVerify() {
    const f = S.findpw; f.err = {};
    if (!/^\d{6}$/.test(f.code.trim())) { f.err.code = "6자리 숫자를 정확히 넣어주세요"; this.render(); return; }
    f.step = 3; this.render();
  },
  findpwDone() {
    const f = S.findpw; f.err = {};
    if (f.pw.length < 8 || !/[a-zA-Z]/.test(f.pw) || !/[0-9]/.test(f.pw)) f.err.pw = "8자 이상, 영문과 숫자를 함께 넣어주세요";
    if (f.pw !== f.pw2) f.err.pw2 = "비밀번호가 서로 달라요";
    if (Object.keys(f.err).length) { this.render(); return; }
    f.step = 4; this.render();
  },
  // 실제 지문·얼굴 인증(@aparajita/capacitor-biometric-auth). 웹엔 플러그인이 없어 목업 통과.
  async _bio(reason) {
    const B = window.Capacitor?.Plugins?.BiometricAuthNative;
    if (!B) return true;                                   // 브라우저: 바로 통과(목업)
    // 네이티브 메서드명은 internalAuthenticate (JS 래퍼 없이 직접 호출하므로). authenticate는 없다.
    const fn = B.authenticate || B.internalAuthenticate;
    try {
      await fn.call(B, {
        reason, androidTitle: "본인 확인", androidSubtitle: reason,
        cancelTitle: "취소", allowDeviceCredential: true,   // 지문 실패 시 PIN·패턴으로도
      });
      return true;
    } catch (e) { return false; }                          // 취소·실패
  },
  async unlockBio() {
    // 앱 잠금이 걸려 있으면 그것부터 푼다(같은 판을 둘이 쓴다)
    if (S.appLock && S.appLocked) {
      const ok = await this._bio("잠금을 풀어주세요");
      if (ok) { S.appLocked = false; this.render(); }
      else toast("잠금 해제를 취소했어요");
      return;
    }
    const ok = await this._bio("자녀 기록을 보려면 잠금을 풀어주세요");
    if (ok) { S.bioUnlocked = true; this.render(); }
    else toast("잠금 해제를 취소했어요");
  },
  /* 앱 잠금 켜기/끄기 (2026-07-31) — 켤 때 **한 번 확인해 본다.**
     지문이 등록 안 된 기기에서 켜버리면 다음에 앱을 못 여는 사고가 난다. */
  async appLockToggle() {
    if (!S.appLock) {
      const ok = await this._bio("앱 잠금을 켜기 전에 확인해요");
      if (!ok) return toast("지문·얼굴 확인이 안 돼 켜지 않았어요");
      S.appLock = true; toast("앱을 열 때마다 잠금을 물어봐요");
    } else {
      S.appLock = false; S.appLocked = false; toast("앱 잠금을 껐어요");
    }
    saveHome(); this.render();
  },
  // 자녀를 바꾸면 대화방도 바뀐다 — 앞 아이의 대화가 남아 있으면 다른 반 얘기를 보게 된다
  // 자녀를 바꾸면 대화방도 미션도 그 아이 것으로 갈아야 한다 — 안 비우면 앞 아이 것이 남는다
  pickChild(id) {
    S.currentChildId = id;
    S.commJoined = false; S.commPosts = []; S.commSince = 0;
    S.missions = null; S.missionStars = 0;
    // 상점·티켓·확인대기도 자녀마다 다르다 — 안 비우면 앞 아이 것이 남는다(2026-08-07)
    S.store = null; S.rewards = null; S.verifyPending = null;
    location.hash = "#home";
  },
  defChildSet(id) {
    const c = STUB.children.find((x) => x.id === id);
    if (!c) return;
    try { localStorage.setItem(DEF_CHILD_KEY, JSON.stringify(defChildKeyOf(c))); } catch (e) {}
    toast(`이제 앱을 켜면 ${c.nickname}부터 보여요`);
    this.render();
  },
  schoolTab(t) {
    S.schoolTab = t;
    /* ⚠ #calendar 화면은 그릴 때마다 탭을 «일정»으로 되돌린다(아래 calendar: 정의).
       그 위에서 다른 탭을 누르면 render 가 도로 일정으로 밀어 넣어 «안 눌리는» 것처럼 보였다
       (2026-08-03 폰 실기). 탭을 누르는 순간 주소를 #school 로 옮겨 강제 리셋을 벗어난다. */
    if ((location.hash || "") === "#calendar") history.replaceState(null, "", "#school");
    this.render();
  },

  // ── 커뮤니티 ──────────────────────────────────────────
  /* ── 커뮤니티 = 오픈채팅 (2026-08-01) ─────────────────────
     서버가 규칙의 주인이다(50자·30초·참여 시점·신고 3명). 여기서는 화면만 맞춘다 —
     앱에서만 막으면 우회되고, 앱에서 안 막으면 눌러본 뒤에야 거절당해 답답하다. 양쪽 다 건다. */
  commDraft(v) {
    S.communityDraft = v.slice(0, COMM_MAX);
    const el = document.querySelector(".cm-cnt");   // 글자수만 갱신 — 다시 그리면 커서가 튄다
    if (el) { el.textContent = `${S.communityDraft.length}/${COMM_MAX}`; el.classList.toggle("full", S.communityDraft.length >= COMM_MAX); }
  },

  async commJoin() {
    const c = cur();
    if (!c?.server_id) return toast("먼저 로그인해 주세요");
    if (S.commBusy) return;
    S.commBusy = true; this.render();
    try {
      const r = await api(`/children/${c.server_id}/community/join`, { method: "POST", body: { agree: true } });
      if (!r?.ok) throw new Error(r?.error?.message || "");
      S.commJoined = true; S.commPosts = []; S.commSince = 0;
      S.commBusy = false; this.render();
      this.commPoll(true);
    } catch (e) {
      S.commBusy = false; this.render();
      toast(e.message || "참여하지 못했어요");
    }
  },

  // 나가면 여태 대화를 잃는다(다시 들어오면 그 뒤부터 보인다) → 한 번 물어본다
  commLeaveAsk() { S.commLeaveAsk = true; this.render(); },
  commLeaveCancel() { S.commLeaveAsk = false; this.render(); },
  async commLeave() {
    const c = cur();
    S.commLeaveAsk = false;
    try { await api(`/children/${c.server_id}/community/join`, { method: "DELETE" }); } catch (_) {}
    S.commJoined = false; S.commPosts = []; S.commSince = 0;
    this.render();
  },

  // 새 대화 받아오기. since 로 새 것만 이어 받는다(매번 전체를 받으면 화면이 깜빡인다).
  async commPoll(scroll) {
    const c = cur();
    if (!c?.server_id || !TOKENS.access) return;
    try {
      const r = await api(`/children/${c.server_id}/community?since=${S.commSince}`);
      if (!r?.ok) return;
      S.commJoined = r.data.joined !== false;
      const items = r.data.items || [];
      if (items.length) {
        S.commPosts = [...S.commPosts, ...items];
        S.commSince = Math.max(S.commSince, ...items.map((x) => x.id));
        this.render();
        scroll = true;
      }
      if (scroll) { const box = document.getElementById("cm-log"); if (box) box.scrollTop = box.scrollHeight; }
    } catch (_) { /* 못 받아와도 조용히 — 대화는 부가 기능이다 */ }
  },

  async communityPost() {
    const t = (S.communityDraft || "").trim();
    if (!t) return toast("내용을 적어주세요");
    const c = cur();
    if (!c?.server_id) return toast("먼저 로그인해 주세요");
    if (S.commBusy) return;
    S.commBusy = true;
    try {
      const r = await api(`/children/${c.server_id}/community`, { method: "POST", body: { body: t } });
      S.commBusy = false;
      if (!r?.ok) return toast(r?.error?.message || "보내지 못했어요");
      S.communityDraft = "";
      S.commPosts = [...S.commPosts, r.data];
      S.commSince = Math.max(S.commSince, r.data.id);
      this.render();
      const box = document.getElementById("cm-log"); if (box) box.scrollTop = box.scrollHeight;
    } catch (e) {
      S.commBusy = false;
      toast("보내지 못했어요");
    }
  },

  commMenu(id) { S.commMenuFor = id; this.render(); },
  commMenuClose() { S.commMenuFor = null; this.render(); },

  /* 신고 — 누르는 즉시 **내 화면에서만** 사라진다. 서로 다른 3명이 신고해야 모두에게서 내려간다.
     "관리자가 확인합니다"라고 말해주는 게 중요하다 — 아무 일도 안 일어난 것처럼 보이면 또 신고한다. */
  async commReport() {
    const id = S.commMenuFor; S.commMenuFor = null;
    S.commPosts = S.commPosts.filter((p) => p.id !== id);
    this.render();
    try { await api(`/community/${id}/report`, { method: "POST" }); } catch (_) {}
    toast("신고했어요. 확인 후 처리할게요");
  },
  async commBlock() {
    const id = S.commMenuFor; S.commMenuFor = null;
    const target = S.commPosts.find((p) => p.id === id);
    S.commPosts = S.commPosts.filter((p) => !target || p.display_name !== target.display_name || p.mine);
    this.render();
    try { await api(`/community/${id}/block`, { method: "POST" }); } catch (_) {}
    toast("차단했어요. 앞으로 이 사람 대화는 안 보여요");
  },

  // ── 급식 ──────────────────────────────────────────────────
  mealRange(k) { S.mealRange = k; this.render(); },
  supMemoToggle() {
    S.supMemoOpen = !S.supMemoOpen;
    if (!S.supMemoOpen) S.supDraft.memo = "";
    this.render();
    if (S.supMemoOpen) document.getElementById("sup-m")?.focus();
  },
  mealSearchToggle() {
    S.mealSearchOpen = !S.mealSearchOpen;
    if (!S.mealSearchOpen) S.mealQuery = "";   // 닫으면 검색어도 지운다 — 안 그러면 걸러진 화면이 그대로 남는다
    this.render();
    if (S.mealSearchOpen) document.getElementById("ml-q")?.focus();
  },
  mealSearch(v) {
    S.mealQuery = v;
    renderKeepFocus();
    // 다시 그리면 포커스가 날아가므로 검색창으로 되돌린다(커서는 맨 뒤).
    const el = document.querySelector(".mealsearch");
    if (el) { el.focus(); el.setSelectionRange(v.length, v.length); }
  },
  toggleGrades() { S.gradesOpen = !S.gradesOpen; this.render(); },
  // 학년이 바뀌면 반 목록이 그 학년 학급수로 다시 만들어진다 → 1반으로 되돌린다
  childGrade(g) {
    S.childDraft.grade = g; S.childDraft.class_name = "1"; S.classNames = null;
    this.render();
    /* 학년이 정해져야 그 학년의 «실제» 반 이름을 물어볼 수 있다.
       기다리지 않는다 — 받아오면 스스로 다시 그린다(등록을 막지 않는다). */
    const slug = S.childDraft.school && S.childDraft.school.slug;
    if (slug) this.loadClassNames(slug, g);
  },
  // 학교 검색 — GET /api/v1/schools/search?q= (전국 12,563개교, 서버가 찾는다).
  // 타자가 빠르면 요청이 겹친다 → 250ms 쉬고 한 번만 보내고, 늦게 온 옛 응답은 버린다.
  // 다시 그리면 포커스가 날아가니 되돌린다.
  schoolSearch(v) {
    S.schoolQuery = v;
    renderKeepFocus();
    const el = document.querySelector('input[placeholder^="학교 이름"]');
    if (el) { el.focus(); el.setSelectionRange(v.length, v.length); }

    const q = v.trim();
    clearTimeout(this._schoolTimer);
    if (q.length < 2) { S.schoolHits = null; S.schoolBusy = false; return; }
    S.schoolBusy = true;
    const seq = ++this._schoolSeq;
    this._schoolTimer = setTimeout(async () => {
      try {
        const r = await api(`/schools/search?q=${encodeURIComponent(q)}`);
        if (seq !== this._schoolSeq) return;                 // 더 최근 입력이 있으면 이 응답은 버린다
        S.schoolHits = r?.ok ? r.data.items : [];
        S.schoolFrom = "server";
      } catch (e) {
        if (seq !== this._schoolSeq) return;
        /* 서버를 못 붙었다. 예전엔 견본 목록에서 찾아 보여줬지만 그건 **남의 학교**다(2026-08-03).
           결과를 비우고 «지금은 찾을 수 없다»고 말한다 — 없는 것과 못 물어본 것은 다르다. */
        S.schoolHits = [];
        S.schoolFrom = "offline";
      }
      S.schoolBusy = false;
      if (S.schoolQuery.trim() === q) renderKeepFocus();
    }, 250);
  },
  _schoolSeq: 0,
  schoolPick(slug) {
    const s = (S.schoolHits || []).find((x) => x.slug === slug) || STUB.schoolSearch.find((x) => x.slug === slug);
    if (!s) return;
    // 학교가 바뀌면 학년·반은 그 학교 기준으로 다시 골라야 한다
    // 상세(학급수·학생수)는 **그 학교 것**만 쓴다. 없으면 비운다 — 견본을 물려주면 남의 숫자가 남는다
    S.childDraft.school = { ...s, detail: s.detail || null };
    S.childDraft.grade = "3"; S.childDraft.class_name = "1";
    S.schoolQuery = ""; S.schoolHits = null;
    S.classNames = null;
    this.render();
    toast(`${esc(s.name)} (${s.sido}) 선택`);
    /* ⚠ 학교를 고른 직후에 **그 학교의 실제 반 이름**을 받아온다.
       예전엔 «학년을 바꿀 때»만 받아와서, 학교만 고르고 학년을 안 건드리면
       계속 「1반·2반」 숫자로 남았다 — 경기초 4학년은 「난초·매화·장미」다.
       기다리지 않는다. 받아오면 스스로 다시 그린다. */
    this.loadClassNames(s.slug, S.childDraft.grade);
  },
  // 예전엔 등록하기가 화면 이동만 했다 → 고른 학년·반이 사라졌다(2026-07-24 지적). 실제로 만든다.
  // 신규 자녀 추가 — 폼을 비우고 수정 모드 해제
  childAddStart() {
    S.childEditId = null;
    S.childDraft = { grade: "3", class_name: "1", nickname: "", name: "", agree: false, school: null };
    S.schoolQuery = ""; S.schoolHits = null;
    location.hash = "#child-add"; this.render();
  },
  // 자녀 정보 수정 시작 — 기존 값을 폼에 채우고 수정 모드로
  childEditStart(id) {
    const c = STUB.children.find((x) => x.id === id);
    if (!c) return;
    S.childEditId = id;
    S.childDraft = {
      grade: c.grade, class_name: c.class_name, nickname: c.nickname, name: c.name || "",
      agree: true, school: { ...c.school, detail: c.school?.detail || null },
      // 사진을 붙이려면 서버 id 가 필요하다 — 등록된 자녀를 고칠 때만 있다(2026-07-27)
      server_id: c.server_id || null, photo: c.photo || null,
    };
    S.schoolQuery = ""; S.schoolHits = null;
    S.classNames = null;
    location.hash = "#child-add"; this.render();
    /* ⚠ 반 이름 고치기를 «새 등록»에만 넣었더니 **이미 가입한 아이는 그대로 숫자**였다.
       실서버 자녀 11명 전원이 숫자 반이라, 반을 말로 쓰는 학교(「난초·매화·장미」)
       아이는 고친 뒤에도 시간표가 0건이었다(2026-08-09 실측).
       → 고치기 화면에서도 실제 반 이름을 받아온다. 기존 값은 그대로 두고 «고를 길»만 준다. */
    if (S.childDraft.school?.slug && S.childDraft.grade) {
      this.loadClassNames(S.childDraft.school.slug, S.childDraft.grade);
    }
  },
  childSave() {
    const d = S.childDraft;
    if (!d.nickname.trim()) return toast("별명을 넣어주세요");
    if (!d.agree) return toast("보호자 동의가 있어야 기록을 보관할 수 있어요");
    const sc = d.school || schoolInfo();

    if (S.childEditId != null) {
      // ── 수정 ── 진급(학년·반)·별명·캐릭터·학교 갱신
      const c = STUB.children.find((x) => x.id === S.childEditId);
      const prevGrade = c ? +c.grade : null;   // ⚠ 아래에서 c.grade를 덮어쓰므로 **미리** 잡아둔다
      if (c) {
        c.nickname = d.nickname.trim(); c.name = d.name || "";
        c.grade = String(d.grade); c.class_name = String(d.class_name); c.grade_code = +d.grade;
        c.school = { slug: sc.slug, name: sc.name, kind: sc.kind };
      }
      // 서버에도 반영. 자녀 정보 수정은 **재인증이 필요한 요청**이라(계약 §3.4) 막히면 그대로 알려준다.
      if (TOKENS.access && c?.server_id) this.childPatchServer(c.server_id, d, prevGrade);
      S.childEditId = null;
      S.childDraft = { grade: "3", class_name: "1", nickname: "", name: "", agree: false };
      location.hash = "#mypage"; this.render();
      return toast(`${esc(c.nickname)} 수정 완료 — ${d.grade}학년 ${d.class_name}반`);
    }

    // ── 신규 등록 ──
    const id = Math.max(0, ...STUB.children.map((c) => c.id)) + 1;
    const pendingPhoto = d.photoBlob || null;    // 등록 화면에서 미리 고른 사진 — 서버에 아이가 생긴 뒤 올린다
    STUB.children.push({
      id, nickname: d.nickname.trim(), name: d.name || "",
      school: { slug: sc.slug, name: sc.name, kind: sc.kind },
      grade: String(d.grade), class_name: String(d.class_name), grade_code: +d.grade, birth_year: null,
      // 올라가기 전까진 화면에서 보이는 주소(blob)를 쓴다 — 아바타가 이모지로 깜빡이지 않게
      photoLocal: d.photoPreview || null, photo: null,
      pass: { active: false, expires_at: null, free_open_until: "20260820" },
      counts: { records: 0, activities: 0 },
    });
    S.currentChildId = id;                                   // 방금 만든 캐릭터로 바로 전환
    S.childDraft = { grade: "3", class_name: "1", nickname: "", name: "", agree: false };
    /* 설문에서 «두 명»이라고 답했으면 남은 아이도 이어서 등록하게 한다(§5 ②).
       물어 놓고 안 쓰면 그건 그냥 캐묻기다. 강요하지는 않는다 — 홈으로 보내고 한 줄만 알린다. */
    const want = +((S.onboard || {}).kids || 0);
    if (want > STUB.children.length) {
      const nm = esc(STUB.children.find((c) => c.id === id).nickname);
      this.childSaveServer(id, sc, d, pendingPhoto);
      this.childAddStart();                    // 빈 폼으로 다시 — 뒤로 가면 홈이다
      return toast(`${nm} 등록 완료 — 남은 아이도 이어서 등록해요`);
    }
    /* 첫 아이를 막 등록했으면 **테마 고르기**를 한 번 보여준다(§5 흐름).
       두 번째 아이부터는 안 띄운다 — 같은 걸 또 물으면 성가시다. */
    if (STUB.children.length === 1 && !localStorage.getItem("eduthink.themeAsked")) {
      try { localStorage.setItem("eduthink.themeAsked", "1"); } catch (e) {}
      S.themeFirst = true;
      location.hash = "#theme"; this.render();
      return toast(`${esc(STUB.children.find((c) => c.id === id).nickname)} 등록 완료`);
    }
    location.hash = "#home"; this.render();
    toast(`${esc(STUB.children.find((c) => c.id === id).nickname)} 등록 완료 — ${d.grade}학년 ${d.class_name}반`);
    // 🔴 서버에도 만든다. 안 하면 화면에만 생겼다가 **다음 로그인에 사라진다**(2026-07-26 실측).
    this.childSaveServer(id, sc, d, pendingPhoto);
  },

  /* 자녀를 서버에 만든다. 성공하면 화면 자녀에 server_id를 달아준다 —
     그게 있어야 기록·서류·대화가 그 아이 것으로 저장된다. */
  /* 자녀 정보 수정 — 서버가 **본인 확인**을 요구한다(계약 §3.4: 수정·삭제는 무겁게).
     한 번 막히면 지문/비번을 받아 표를 얻고 **자동으로 다시 보낸다**. 사용자는 한 번만 확인하면 된다. */
  async childPatchServer(serverId, d, prevGrade) {
    /* 서버는 학년 변경을 **진급(promote)** 으로만 받는다 — 자녀당 1회, 바로 다음 학년으로만.
       기록의 학년·학기가 어긋나지 않게 하려는 규칙이다(회신19).
       그래서 «다음 학년으로 올리는 경우»에만 promote 를 실어 보내고, 그 외엔 별명만 바뀐다. */
    // 바뀌기 전 학년과 비교해야 «한 학년 올림»인지 안다. 바뀐 뒤 값과 비교하면 늘 같아서 진급이 안 잡힌다.
    const isPromote = prevGrade != null && +d.grade === prevGrade + 1;
    const body = { nickname: d.nickname.trim(), name: d.name || undefined };
    if (isPromote) { body.promote = true; body.grade = +d.grade; body.class_name = String(d.class_name); }
    let r = await api(`/children/${serverId}`, { method: "PATCH", body }).catch(() => null);
    if (r?.error?.code === "REAUTH_REQUIRED") {
      const t = await this.getReauth("자녀 정보 수정");
      if (!t) return toast("본인 확인을 못 해서 서버엔 반영되지 않았어요");
      r = await api(`/children/${serverId}`, { method: "PATCH", body, reauth: t }).catch(() => null);
    }
    if (!r?.ok) return toast(r?.error?.message || "자녀 정보를 서버에 반영 못 했어요");
    toast(isPromote ? "진급 처리했어요 — 서버에도 반영됐습니다" : "자녀 정보를 서버에도 반영했어요");
    await loadMe();
  },

  async childSaveServer(localId, sc, d, pendingPhoto) {
    if (!TOKENS.access || !sc?.slug) return;
    const r = await api("/children", { method: "POST", body: {
      school_slug: sc.slug,
      name: (d.name || d.nickname || "").trim(),      // 서버는 이름을 필수로 본다(기록 기능이 켜져 있을 때)
      nickname: d.nickname.trim(),
      grade: +d.grade, class_name: String(d.class_name), consent: true,
    } }).catch(() => null);
    if (!r?.ok) { toast(r?.error?.message || "서버에 자녀를 못 만들었어요 (이 기기에만 저장됨)"); return; }
    const c = STUB.children.find((x) => x.id === localId);
    const sid = r.data.id ?? r.data.child?.id ?? null;
    if (c) c.server_id = sid;
    this.render();
    // 등록 화면에서 미리 고른 사진을 이제 올린다 — 자녀가 있어야 붙일 자리가 생긴다
    if (pendingPhoto && sid) {
      const url = await this.childPhotoUpload(sid, pendingPhoto);
      if (url) this.render();
    }
  },

  // ── 요청28 ① 서류 ────────────────────────────────────────
  docStart(kind, phase, fromId) {
    S.docKind = kind; S.docPhase = phase;
    const src = fromId && STUB.documents.find((d) => d.id === fromId);
    // 보고서는 신청서에 적었던 기간·장소를 그대로 물려받는다(다시 입력시키지 않는다).
    S.docDraft = src
      ? { from: ymdDash(src.from), to: ymdDash(src.to), days: src.days, place: src.place || "" }
      : { from: "2026-08-24", to: "2026-08-26", days: 3, wish: [{}, {}, {}] };
    this.docDays(true);
    location.hash = "#doc-form"; this.render();
  },
  docSet(key, val) { S.docDraft[key] = val; this.render(); },
  docPlan(i, text) { S.docDraft.planDays[i].text = text; },
  docWish(i, key, val) {
    S.docDraft.wish = S.docDraft.wish || [{}, {}, {}];
    S.docDraft.wish[i] = { ...S.docDraft.wish[i], [key]: val };
    if (key === "how") renderKeepFocus();      // 대면/비대면은 버튼이라 다시 그린다(입력칸은 안 건드림)
  },
  // 기간이 바뀌면 일수와 "날짜별 학습계획" 칸을 다시 만든다(실제 양식이 날짜별로 적게 되어 있음).
  docDays(silent) {
    const d = S.docDraft;
    if (d.from && d.to) {
      d.days = Math.max(1, Math.round((new Date(d.to) - new Date(d.from)) / 86400000) + 1);
      const rows = [];
      for (let i = 0; i < Math.min(d.days, 10); i++) {
        const dt = new Date(d.from); dt.setDate(dt.getDate() + i);
        const label = `${dt.getMonth() + 1}/${dt.getDate()}`;
        rows.push({ date: label, text: (d.planDays || []).find((p) => p.date === label)?.text || "" });
      }
      d.planDays = rows;
    }
    if (!silent) this.render();
  },
  docPreview() { S.docZoom = false; location.hash = "#doc-preview"; this.render(); },
  docZoom() { S.docZoom = !S.docZoom; this.render(); },
  // 종이 한 장(가로 700px 기준)을 남은 화면에 통째로 넣는다.
  // 축소는 transform이라 표 선·글자 위치가 안 흐트러진다(width를 줄이면 칸이 다시 접힌다).
  fitPage() {
    const pg = document.getElementById("docpage");
    if (!pg) return;
    if (S.docZoom) { pg.style.transform = ""; return; }        // 크게 보기 = 원래 크기 + 스크롤
    const box = pg.parentElement;
    const s = Math.min(box.clientWidth / pg.offsetWidth, box.clientHeight / pg.offsetHeight, 1);
    pg.style.transform = `scale(${s})`;
  },
  // 서류를 서버에도 남긴다. 신청서는 새로 만들고, 보고서는 그 신청서를 «냈음»으로 바꾼다.
  docSaveServer() {
    const c = cur(), d = S.docDraft, k = S.docKind, isReport = S.docPhase === "report";
    if (!TOKENS.access || !c?.server_id) return;
    const ymd = (v) => (v || "").replace(/-/g, "") || null;
    if (isReport) {
      const doc = STUB.documents.find((x) => x.kind === "field" && !x.reported);
      if (doc?.id) api(`/documents/${doc.id}`, { method: "PATCH", body: { reported: true, payload: { ...(doc.payload || {}), did: d.did } } }).then(() => loadLife());
      return;
    }
    const title = { field: `체험학습 · ${d.place || ""}`.trim(), absence: `결석 · ${d.reason || ""}`.trim(), counsel: "학부모 상담 신청" }[k];
    api(`/children/${c.server_id}/documents`, { method: "POST", body: {
      kind: k, phase: "apply", title, from_ymd: ymd(d.from), to_ymd: ymd(d.to), days: d.days, payload: d,
    } }).then(() => loadLife());
  },
  /* 서류에 필수값이 비었는지 본다. 학교에 내는 문서라 빈칸이 있으면 **다시 써야 한다** —
     화면에서 막는 게 학교 가서 퇴짜맞는 것보다 낫다.
     (2026-07-26 실측: 상담신청서를 아무것도 안 적고 저장할 수 있었다.) */
  docMissing() {
    const d = S.docDraft || {}, k = S.docKind, isReport = S.docPhase === "report";
    const need = (v) => !String(v ?? "").trim();
    if (k === "field" && isReport) return need(d.did) ? "체험학습 내용을 적어주세요" : null;
    if (k === "field") {
      if (need(d.sex)) return "성별을 골라주세요";
      if (need(d.addr)) return "주소를 적어주세요";
      if (need(d.place)) return "장소를 적어주세요";
      if (need(d.accompany)) return "보호자 동행 여부를 골라주세요";
      if (!(d.planDays || []).some((p) => !need(p.text))) return "학습계획을 하루라도 적어주세요";
      return null;
    }
    if (k === "absence") {
      if (need(d.sex)) return "성별을 골라주세요";
      if (need(d.reason)) return "결석 사유를 적어주세요";
      return null;
    }
    // 상담 신청
    if (need(d.phone)) return "보호자 연락처를 적어주세요";
    if (need(d.relation)) return "학생과의 관계를 적어주세요";
    if (!(d.wish || []).some((x) => !need(x && x.when))) return "희망 시간을 하나라도 적어주세요";
    if (need(d.note)) return "상담 내용을 적어주세요";
    return null;
  },
  docSave() {
    const d = S.docDraft, k = S.docKind, isReport = S.docPhase === "report";
    const missing = this.docMissing();
    if (missing) return toast(missing);
    this.docSaveServer();
    if (k === "field" && isReport) {
      const doc = STUB.documents.find((x) => x.kind === "field" && !x.reported);
      if (doc) doc.reported = true;
      STUB.docRules.fieldUsedDays += 0;                       // 신청 때 이미 셈
    } else if (k === "field") {
      STUB.documents.push({
        id: Math.max(0, ...STUB.documents.map((x) => x.id)) + 1,
        kind: "field", title: d.place || "체험학습",
        from: (d.from || "").replace(/-/g, ""), to: (d.to || "").replace(/-/g, ""),
        days: d.days ?? 3, place: d.place || "", endedDaysAgo: 0, reported: false,
      });
      STUB.docRules.fieldUsedDays += d.days ?? 3;             // 연 19일 한도에서 차감
    }
    // 서류가 곧 기록으로 남는다(요청28의 핵심 — 귀찮은 대행이 축적으로)
    const label = { field: isReport ? "체험학습 보고서" : "체험학습 신청서",
                    absence: "결석신고서", counsel: "학부모 상담 신청서" }[k];
    const detail = d.place || d.reason || d.note || "";
    STUB.records.unshift({
      id: Math.max(0, ...STUB.records.map((r) => r.id)) + 1,
      category: "activity", period: { school_year: 3, semester: 2, label: "초3 2학기" },
      title: label + (detail ? ` · ${detail.slice(0, 16)}` : ""), icon: "ti-receipt",
    });
    S.docDraft = {};
    location.hash = "#timeline"; this.render();
    toast(isReport ? "보고서까지 냈어요 — 기록에 남겼습니다" : `${label}를 기록으로 남겼어요`);
  },

  // ── 요청28 ② 알림 ────────────────────────────────────────
  sendNotice(preset) {
    const text = (preset || S.noticeText).trim();
    if (!text) return toast("보낼 말을 적어주세요");
    STUB.notices.push({ id: Math.max(0, ...STUB.notices.map((n) => n.id)) + 1, from: "parent", text, at: "지금", seen: false });
    S.noticeText = "";
    this.render();
    toast(`보냈어요 — ${esc(cur().nickname)} 앱에 푸시로 뜹니다`);
  },
  /* 아이의 «봤어요» — 서버까지 보낸다(2026-08-02 정리 1단계).
     여태 로컬 변수만 바꿔서 **부모 앱에는 영원히 «보냄»으로 남아 있었다.**

     ⚠ 서버 엔드포인트는 낱개가 아니라 «상대가 보낸 안 본 것 전부»를 한 번에 본 것으로 처리한다
        (POST /messages/seen — chatOpen 도 같은 것을 쓴다). 그래서 화면도 **전부** 본 것으로
        맞춘다 — 하나만 로컬에서 바꿔두면 다음 동기화 때 나머지가 한꺼번에 바뀌며 화면이 튄다.
     ⚠ 실패하면 되돌린다. 안 그러면 «봤어요»를 눌렀는데 엄마 쪽엔 안 갔고, 아이 화면만
        확인함으로 바뀌어 아무도 모르는 채로 끝난다. */
  async ackNotice(id) {
    const c = cur();
    const before = STUB.notices.filter((n) => n.from === "parent" && !n.seen).map((n) => n.id);
    if (!before.length) return;
    STUB.notices.forEach((n) => { if (n.from === "parent") n.seen = true; });
    this.render();

    if (!TOKENS.access || !c?.server_id) { toast("엄마에게 «봤어요»를 보냈어요"); return; }
    const r = await api(`/children/${c.server_id}/messages/seen`, { method: "POST", body: { reader: "child" } });
    if (r?.ok) { toast("엄마에게 «봤어요»를 보냈어요"); return; }
    STUB.notices.forEach((n) => { if (before.includes(n.id)) n.seen = false; });
    this.render();
    toast("지금은 못 보냈어요. 잠시 뒤 다시 눌러주세요");
  },
  toggleChildView() {
    S.childView = !S.childView;
    S.chatOpen = false;                       // 역할이 바뀌면 대화창은 접고 시작
    location.hash = S.childView ? "#game" : "#notify";
    this.render();
  },

  // ── 맨 밑 대화창 ──────────────────────────────────────────
  // 여는 순간 상대가 보낸 말은 읽음 처리한다(대화창을 열었다 = 봤다).
  // 부모 알림의 «확인» 버튼(#game)은 그대로 둔다 — 같은 seen 값을 쓴다.
  chatOpen() {
    const role = myRole();
    STUB.notices.forEach((n) => { if (n.from !== role) n.seen = true; });
    S.chatOpen = true; this.render();
    const c = cur();
    if (TOKENS.access && c?.server_id) api(`/children/${c.server_id}/messages/seen`, { method: "POST", body: { reader: role } });
  },
  chatClose() { S.chatOpen = false; S.chatText = ""; this.render(); },
  chatSend(preset) {
    const text = (preset || S.chatText || "").trim();
    if (!text) return toast("보낼 말을 적어주세요");
    const role = myRole();
    STUB.notices.push({ id: Math.max(0, ...STUB.notices.map((n) => n.id)) + 1, from: role, text, at: "지금", seen: false });
    S.chatText = "";
    this.render();
    // 서버에도 남긴다 — 폰을 바꿔도 대화가 이어지게
    const c = cur();
    if (TOKENS.access && c?.server_id) api(`/children/${c.server_id}/messages`, { method: "POST", body: { sender: role, text } }).then(() => loadLife());
    // 토스트 없음 — 말풍선이 바로 올라오는데 "보냈어요"를 또 띄우면 화면만 가린다.
    // 상대가 봤는지는 말풍선 옆 «1»이 사라지는 걸로 안다(2026-07-25 지시).
  },

  // ── FCM 푸시(@capacitor/push-notifications) ───────────────
  // 권한 요청 → 채널 만들기 → 등록 → registration 이벤트로 토큰 수신. 수신 알림은 토스트로.
  /* ── 매일 알림 (2026-07-27) ────────────────────────────
     리서치에서 스쿨메이트·쌤핀이 공통으로 가진 것. 앱은 «열어야» 보이는데,
     학부모가 하루에 앱을 몇 번이나 열겠나 — 앱이 먼저 말을 걸어야 한다.
     **로컬 알림**을 쓴다(서버 푸시 아님): 폰이 스스로 띄우므로 서버가 죽어도,
     비행기 모드여도 뜬다. 내용도 폰 안 데이터로 만드니 서버에 아이 일과를 또 보낼 일이 없다.
     ⚠ 안드로이드는 «정확한 시각» 알림에 권한이 따로 있다. 우리는 몇 분 늦어도 되는
       내용이라 굳이 요구하지 않는다(allowWhileIdle 없이 반복 예약). */
  NOTI_ID: { evening: 4101, morning: 4102 },

  async remindToggle(on) {
    S.remind.on = !!on;
    saveHome();
    this.render();
    if (S.remind.on) {
      const ok = await this._remindSchedule();
      if (!ok) { S.remind.on = false; saveHome(); this.render(); }
    } else {
      await this._remindCancel();
      toast("매일 알림을 껐어요");
    }
  },
  remindTime(which, v) {
    if (!/^\d{2}:\d{2}$/.test(v || "")) return;
    S.remind[which] = v; saveHome();
    if (S.remind.on) this._remindSchedule();
  },

  async _remindCancel() {
    const L = window.Capacitor?.Plugins?.LocalNotifications;
    if (!L) return;
    try { await L.cancel({ notifications: Object.values(this.NOTI_ID).map((id) => ({ id })) }); } catch (e) {}
  },

  async _remindSchedule() {
    const L = window.Capacitor?.Plugins?.LocalNotifications;
    if (!L) { toast("앱(폰)에서 켜야 매일 알림이 와요"); return false; }
    try {
      const perm = await L.requestPermissions();
      if (perm.display !== "granted") { toast("알림 권한을 허용해야 받을 수 있어요"); return false; }
      // 채널은 푸시와 **따로** 판다. 매일 알림은 조용해도 되는데 푸시 채널(MAX)에 얹으면
      // 매일 밤 화면이 튀어나온다 — 그러면 사용자가 알림 자체를 꺼버린다.
      if (L.createChannel) {
        await L.createChannel({ id: "daily", name: "매일 알림", description: "내일 준비물·오늘 일정", importance: 3, visibility: 0 });
      }
      await this._remindCancel();
      const [eh, em] = S.remind.evening.split(":").map(Number);
      const [mh, mm] = S.remind.morning.split(":").map(Number);
      await L.schedule({ notifications: [
        { id: this.NOTI_ID.evening, channelId: "daily", title: "내일 챙길 것",
          body: this.remindBody("evening"), schedule: { on: { hour: eh, minute: em }, allowWhileIdle: false } },
        { id: this.NOTI_ID.morning, channelId: "daily", title: "오늘 하루",
          body: this.remindBody("morning"), schedule: { on: { hour: mh, minute: mm }, allowWhileIdle: false } },
      ] });
      toast(`매일 ${S.remind.evening} · ${S.remind.morning}에 알려드릴게요`);
      return true;
    } catch (e) { toast("알림 예약 오류: " + (e?.message || e)); return false; }
  },

  /* 알림 문구는 **예약할 때의 데이터**로 만들어진다 — 매일 갱신되지 않는다.
     로컬 알림은 예약 시점에 문구가 굳는 구조라, 내용까지 매일 맞추려면 서버 푸시가 필요하다.
     그래서 «무엇이 있는지»가 아니라 «열어보라»는 쪽으로 쓴다. 거짓말은 안 하게. */
  remindBody(which) {
    if (which === "evening") {
      const tm = ymdPlus(TODAY, 1);
      const n = STUB.supplies.filter((s) => s.date === tm && !s.done).length;
      return n ? `아직 안 챙긴 준비물이 ${n}개 있어요` : "내일 준비물과 일정을 확인해 보세요";
    }
    return "오늘 시간표·급식·일정을 확인해 보세요";
  },

  async pushRegister() {
    const P = window.Capacitor?.Plugins?.PushNotifications;
    if (!P) return toast("앱(폰)에서 눌러야 푸시가 켜져요");
    try {
      const perm = await P.requestPermissions();
      if (perm.receive !== "granted") return toast("알림 권한을 허용해야 받을 수 있어요");
      await this._pushChannel();
      // 리스너는 한 번만 건다
      if (!S._pushWired) {
        S._pushWired = true;
        P.addListener("registration", (t) => { S.pushToken = t.value; App.render(); toast("이 기기 푸시 등록 완료"); });
        P.addListener("registrationError", (e) => toast("등록 실패: " + (e?.error || "")));
        P.addListener("pushNotificationReceived", (n) => toast((n.title || "") + " " + (n.body || "")));
      }
      await P.register();
      toast("등록 중…");
    } catch (e) { toast("푸시 등록 오류: " + (e?.message || e)); }
  },
  // 헤드업 알림 채널 — "학원 끝나면 바로 집으로"는 알림줄에 조용히 쌓이면 의미가 없다.
  // importance 5(MAX) = 화면 위로 튀어나오고 소리·진동. 기본 3은 알림줄에만 들어간다.
  // ⚠ 채널은 만든 뒤 importance를 못 고친다. 값을 바꿔야 하면 id를 새로 파야 한다
  //   (안드로이드가 사용자 설정을 존중하느라 앱이 못 올리게 막는다).
  //   그래서 매니페스트의 default_notification_channel_id 와 이 id가 **같아야** 한다.
  async _pushChannel() {
    const P = window.Capacitor?.Plugins?.PushNotifications;
    if (!P?.createChannel) return;                       // iOS·브라우저엔 채널 개념이 없다
    try {
      await P.createChannel({
        id: "eduthink_urgent", name: "아이 알림",
        description: "엄마·아이가 주고받는 말 — 바로 봐야 하는 알림",
        importance: 5, visibility: 1, vibration: true, lights: true,
      });
    } catch (e) { /* 이미 있으면 조용히 넘어간다 */ }
  },
  copyToken() {
    if (!S.pushToken) return;
    const ta = document.createElement("textarea"); ta.value = S.pushToken;
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); toast("토큰을 복사했어요"); } catch (e) { toast("복사 실패 — 길게 눌러 선택하세요"); }
    ta.remove();
  },
  toggleAllergenBox() { S.allergenOpen = !S.allergenOpen; this.render(); },
  toggleAllergen(code) {
    const i = S.myAllergens.indexOf(code);
    i < 0 ? S.myAllergens.push(code) : S.myAllergens.splice(i, 1);
    this.render();
  },
  mealType(t) { S.mealType = t; this.render(); },
  toggleDorm() { S.dorm = !S.dorm; S.dormTouched = true;   /* 직접 만졌으면 자동으로 안 바꾼다 */ if (!S.dorm) S.mealType = "중식"; this.render(); },
  // key = "YYYYMMDD|끼니" — 기숙사형은 같은 날 아침·점심·저녁 알람을 따로 걸 수 있어야 한다.
  toggleMealAlarm(key) {
    const [date, type] = key.split("|");
    const i = S.mealAlarms.indexOf(key);
    if (i < 0) {
      S.mealAlarms.push(key);
      const hits = hitAllergens(mealsOf().find((m) => m.date === date && m.type === type));
      toast(`${fmtDate(date)} ${MEAL_KOR[type]} 알람 켰어요 — 전날 저녁 8시${hits.length ? ` · ${hits.map((a) => ALLERGEN_KO[a]).join("·")} 주의` : ""}`);
    } else {
      S.mealAlarms.splice(i, 1);
      toast(`${fmtDate(date)} ${MEAL_KOR[type]} 알람 껐어요`);
    }
    this.render();
  },
  // ── 카메라 (@capacitor/camera) ────────────────────────────
  // source: CAMERA=촬영 / PHOTOS=앨범. dataUrl로 받아 바로 미리보기.
  // 카메라 권한을 거부하면 앨범으로 대체한다(2026-07-24 확정: 기록 올리기가 막히지 않게).
  /* 학년·학기를 **미리 채운다**(2026-07-27, 2026-07-31 확장).
     빈칸으로 두면 저장이 «학년·학기를 선택해 주세요»로 막히는데 그 안내가 눈에 안 띈다.
     아이 학년은 이미 안다 — 다르면 고르면 된다. 학기는 3~8월=1학기, 9~2월=2학기.
     ⚠ 처음엔 _capture 에만 있어서 **스캐너·앨범 경로는 빈칸으로 남았다** — 실사용에서
     통지표 2장이 저장 직전에 조용히 막힌 원인(2026-07-31). 세 경로가 다 이걸 부른다. */
  prefillPeriod() {
    if (!S.uploadGrade) S.uploadGrade = String(cur()?.grade || "");
    if (!S.uploadSem) { const mm = +TODAY.slice(4, 6); S.uploadSem = (mm >= 3 && mm <= 8) ? "1" : "2"; }
  },
  // source 생략 시 카메라/앨범 선택 프롬프트(PROMPT). "한 장 더"에서 쓴다.
  async _capture(source) {
    const Camera = window.Capacitor?.Plugins?.Camera;
    if (!Camera) return toast("앱(폰)에서 열면 카메라·앨범이 동작해요");
    try {
      const photo = await Camera.getPhoto({
        ...(source ? { source } : {}), resultType: "uri", quality: 80,   // OCR엔 파일 경로가 필요 → uri로 받는다
        width: 2000, height: 2000, correctOrientation: true,   // 저장 전 리사이즈(§5.3)
        promptLabelHeader: "기록 올리기", promptLabelPhoto: "앨범에서 고르기", promptLabelPicture: "카메라로 찍기",
      });
      S.shots.push({ web: photo.webPath, path: photo.path });   // 앞·뒤 여러 장 누적
      S.ocrText = null;
      S.uploadStep = 1;
      this.prefillPeriod();
      this.render();
      // 첫 장에서만 OCR로 제목·종류·시기 추정(뒷장은 대개 도장·세부라 앞장 기준이 정확)
      if (S.shots.length === 1) this._ocr(photo.path);
    } catch (e) {
      const msg = String(e?.message || e);
      if (/denied|permission/i.test(msg)) {
        if (source !== "PHOTOS") { toast("카메라 권한이 없어요 — 앨범에서 골라볼게요"); return this._capture("PHOTOS"); }
        toast("사진 권한이 필요해요. 설정에서 켜주세요");
      }
      // 사용자가 취소한 경우(cancelled)는 조용히 무시
    }
  },
  // 사진 찍기 = 문서 스캐너(용지 테두리 자동 인식→크롭→그림자 제거, 여러 장 지원).
  // 일반 사진(활동사진 등)은 앨범 버튼으로.
  async _scan(append) {
    const D = window.Capacitor?.Plugins?.DocumentScanner;
    if (!D) return this._capture("CAMERA");   // 플러그인 없으면(웹) 일반 카메라로 폴백
    try {
      // scannerMode BASE = 자르기·회전만(필터 없음) → 원본 색 유지(상장 금박·색이 안 바뀐다 2026-07-24).
      // galleryImportAllowed = 스캐너 안에서 카메라·갤러리 둘 다 되게 → 버튼 하나로 통합.
      const r = await D.scanDocument({ scannerMode: "BASE", galleryImportAllowed: true, pageLimit: 10, resultFormats: "JPEG" });
      const paths = r?.scannedImages || [];
      if (!paths.length) return;              // 취소
      const conv = window.Capacitor.convertFileSrc;
      const added = paths.map((p) => ({ web: conv ? conv(p) : p, path: p }));
      S.shots = append ? [...S.shots, ...added] : added;
      S.ocrText = null; S.uploadStep = 1; this.prefillPeriod(); this.render();
      /* 스캐너의 「저장」을 눌렀는데 앱의 「저장」을 또 눌러야 했다(2026-07-31 실사용 — 두 번 다 여기서 놓침).
         이제 스캔을 마치면 **바로 올린다.** 제목 추정(OCR)만 3초까지 기다렸다가 간다.
         실패하면 미리보기에 그대로 남아 아래 「저장」으로 다시 시도할 수 있다.
         「한 장 더」(append)·앨범은 그대로 수동 — 이어붙이는 중에 올려버리면 안 된다. */
      if (!append) {
        await Promise.race([this._ocr(paths[0]), new Promise((r) => setTimeout(r, 3000))]);
        this.confirmShot();
      }
    } catch (e) {
      const m = String(e?.message || e);
      if (!/cancel/i.test(m)) toast("스캔 오류: " + m);
    }
  },
  shoot() { this._scan(false); },
  // 앨범 = 한 번에 여러 장(2026-07-24). FilePicker로 다중선택(limit:0=무제한).
  async pickAlbum(append) {
    const F = window.Capacitor?.Plugins?.FilePicker;
    if (!F) return this._capture("PHOTOS");   // 폴백(웹/구버전): 한 장
    try {
      const r = await F.pickImages({ limit: 0, readData: false });
      const files = r?.files || [];
      if (!files.length) return;
      const conv = window.Capacitor.convertFileSrc;
      const added = files.map((f) => { const p = f.path || f.webPath; return { web: conv ? conv(p) : p, path: p }; });
      S.shots = append ? [...S.shots, ...added] : added;
      S.ocrText = null; S.uploadStep = 1; this.prefillPeriod(); this.render();
      if (!append && added[0]) this._ocr(added[0].path);
    } catch (e) {
      if (!/cancel/i.test(String(e?.message || e))) toast("사진 선택 오류");
    }
  },
  addShot() { this._scan(true); },        // 한 장 더 — 스캐너로 이어 찍기

  // 찍은 사진에서 글자 인식(ML Kit, 온디바이스·무료). 결과로 종류·시기를 추정해 칸을 채운다.
  // 100%가 아니므로 자동 저장은 안 하고 "채워주되 사용자가 확인·수정"한다.
  async _ocr(path) {
    const T = window.Capacitor?.Plugins?.TextRecognition;
    if (!T || !path) return;
    S.ocrBusy = true; this.render();
    try {
      const r = await T.processImage({ path, script: "KOREAN" });
      const lines = (r?.blocks || []).flatMap((b) => (b.lines || []).map((l) => l.text.trim())).filter(Boolean);
      const text = (r?.text || "").replace(/\s+/g, " ");
      S.ocrText = text;
      const c = cur();

      // ── 종류 추정 ──
      const guessType = [
        [/상장|표창|우수상|최우수|장려|입상|수상|대상/, "상장"],
        [/통지표|생활통지|가정통신|출결|행동특성|생활기록/, "통지표"],
        [/성적|점수|평가|고사/, "성적표"],
        [/자격|급수|인증|수료|합격/, "자격증"],
      ].find(([re]) => re.test(text));
      if (guessType) S.uploadType = guessType[1];

      // ── 날짜 추출 ── "2026년 7월 24일" / "2026. 7. 24" / "2026-07-24" (상장·자격증엔 있음, 통지표엔 없기도)
      const dm = text.match(/(20\d{2})\s*[.\-년]\s*(\d{1,2})\s*[.\-월]\s*(\d{1,2})\s*일?/)
              || text.match(/(20\d{2})\s*[.\-년]\s*(\d{1,2})\s*월?/);
      if (dm && +dm[2] >= 1 && +dm[2] <= 12) {
        S.uploadDate = `${dm[1]}${String(+dm[2]).padStart(2, "0")}${dm[3] ? String(+dm[3]).padStart(2, "0") : "01"}`;
      }
      // 학년·학기는 자동으로 안 채운다(2026-07-24 지시) — 사용자가 직접 선택.

      // ── 제목 추출 ── 문서의 "이름"만 넣는다(학년·학기와 안 겹치게).
      const t = S.uploadType;
      const clean = (l) => l.replace(/^[A-Za-z0-9]\s*/, "").replace(/\s+/g, " ").trim();  // 앞 잡티(D 등) 제거
      let title = "";
      if (t === "상장" || t === "자격증") {
        const award = lines.map(clean).find((l) => /[가-힣]{2,}\s*상$|대상|최우수상|우수상|장려상|금상|은상|동상|[가-힣]\s*\d+\s*급/.test(l));
        if (award) title = award;
      } else {
        // 통지표·성적표류 — 문서에 실제 적힌 이름(생활통지표/통지표/성적표…) 한 줄을 그대로
        const docName = lines.map(clean).find((l) => /통지표|성적표|가정통신|생활기록/.test(l) && l.length <= 12);
        if (docName) title = docName;
      }
      if (!title) title = t;   // 못 찾으면 종류 이름만("통지표"). 학년·학기는 시기 칸에만.
      S.uploadTitle = title;
    } catch (e) {
      S.ocrText = "";                  // 인식 실패해도 흐름은 계속(수동 입력)
    } finally {
      S.ocrBusy = false; this.render();
    }
  },
  retake() { S.shots = []; S.ocrText = null; S.uploadTitle = null; S.uploadStep = 0; this.render(); },
  removeShot(i) {
    S.shots.splice(i, 1);
    if (!S.shots.length) { this.retake(); return; }   // 다 지우면 처음으로
    this.render();
  },
  zoomShot(i) { S.zoomIdx = i; this.render(); },
  closeZoom() { S.zoomIdx = null; this.render(); },
  // 실제로 기록을 만든다(예전엔 화면만 3단계로 넘기고 아무것도 저장 안 했다 — 2026-07-24 지적).
  // 기록 크게 보기
  openRecord(id) {
    S.viewRecord = id; S.recordMenuOpen = false; S.pageIdx = 0; S.zoomed = false;
    prefetchPages(STUB.records.find((r) => r.id === id));   // 뒷장을 미리 받아둔다 — 넘길 때 기다리지 않게
    this.render();
  },
  closeRecord() { S.viewRecord = null; S.recordMenuOpen = false; this.render(); },
  /* 페이지 넘기기 — **범위 밖으로 못 나간다**(2026-07-31 «안 넘어가» 원인).
     예전엔 그냥 더했다: 마지막 장에서 오른쪽을 몇 번 더 누르면 pageIdx 가 3·4로 자라고,
     화면은 clamp 해서 «2/2» 그대로였다. 그 뒤엔 왼쪽을 그 횟수만큼 눌러야 겨우 1장으로 돌아와
     사용자에게는 **아예 안 넘어가는 것처럼** 보였다. 여기서 한계를 지킨다. */
  page(d) {
    const r = STUB.records.find((x) => x.id === S.viewRecord);
    const n = Math.max(1, ((r?.images?.length) || (r?.image ? 1 : 0)) || 1);
    const next = Math.min(n - 1, Math.max(0, (S.pageIdx || 0) + d));
    if (next === S.pageIdx) return;          // 끝이면 아무 일도 안 한다(헛돌지 않게)
    S.pageIdx = next; S.zoomed = false; S.vw = null;   // 장이 바뀌면 확대도 처음으로
    this.render();
  },
  zoomToggle() { S.zoomed = !S.zoomed; this.render(); },                             // 두 번 탭 확대
  recordMenu() { S.recordMenuOpen = !S.recordMenuOpen; this.render(); },
  recordShare() { toast("공유는 실앱에서 붙습니다"); },
  // 저장 후 수정 — 잘못 들어간 제목·종류·시기 고치기
  recordEditStart() { S.recordMenuOpen = false; S.recordEdit = true; S.editTitle = null; S.editType = null; S.editPeriod = null; S.editDate = null; this.render(); },
  recordEditCancel() { S.recordEdit = false; this.render(); },
  recordEditSave() {
    const r = STUB.records.find((x) => x.id === S.viewRecord);
    if (!r) return;
    const KO = { 상장: "award", 통지표: "report_card", 성적표: "grade_sheet", 자격증: "certificate", 활동: "activity", 기타: "other" };
    const ICON = { award: "ti-award", report_card: "ti-file-text", grade_sheet: "ti-chart-bar", certificate: "ti-certificate", activity: "ti-flask", other: "ti-paperclip" };
    if (S.editTitle != null && S.editTitle.trim()) r.title = S.editTitle.trim();
    if (S.editDate != null) r.date = S.editDate || null;
    if (S.editType) { r.category = KO[S.editType]; r.icon = ICON[r.category]; }
    if (S.editPeriod) {
      r.period.label = S.editPeriod;
      r.period.semester = S.editPeriod.includes("2학기") ? 2 : 1;
      const g = S.editPeriod.match(/초(\d)/); if (g) r.period.school_year = +g[1];
    }
    S.recordEdit = false; this.render();
    toast("수정했어요");
  },
  /* 기록 삭제도 본인 확인이 필요하다. 화면에서만 지우고 서버에 남으면 «지웠는데 다시 나타난다». */
  async recordDeleteServer(serverId) {
    if (!TOKENS.access || !serverId) return true;
    // 삭제 확인 창에서 받아둔 reauth 토큰이 살아 있으면 처음부터 실어 보낸다 — 왕복 하나가 준다
    const fresh = S.reauthToken && S.reauthUntil > Date.now() + 5000 ? S.reauthToken : null;
    let r = await api(`/records/${serverId}`, { method: "DELETE", ...(fresh ? { reauth: fresh } : {}) }).catch(() => null);
    if (r?.error?.code === "REAUTH_REQUIRED") {
      const t = await this.getReauth("기록 삭제");
      if (!t) return false;
      r = await api(`/records/${serverId}`, { method: "DELETE", reauth: t }).catch(() => null);
    }
    if (!r?.ok) { toast(r?.error?.message || "서버에서 지우지 못했어요"); return false; }
    return true;
  },
  recordDelete(title) {
    const id = S.viewRecord;
    S.recordMenuOpen = false;
    // 최종 확인까지 통과하면 실제로 기록을 지운다(예전엔 안내만 뜨고 안 지워졌다 — 2026-07-24).
    this.askDelete(`기록 「${title}」 삭제`, async () => {
      const rec = STUB.records.find((r) => r.id === id);
      // 서버에서 먼저 지운다. 서버가 거절하면 화면에서도 안 지운다 —
      // 화면만 지우면 다음에 받아올 때 다시 살아나서 «지웠는데 또 있다»가 된다.
      const ok = await this.recordDeleteServer(rec?.server_id);
      if (!ok) return;
      const i = STUB.records.findIndex((r) => r.id === id);
      if (i >= 0) STUB.records.splice(i, 1);
      const c = cur(); if (c?.counts) c.counts.records = Math.max(0, (c.counts.records || 1) - 1);
      S.viewRecord = null;
      this.render();
      toast("삭제했어요");   // 성공했을 때만 — 서버 거절이면 위에서 이미 사유를 말했다
    });
  },

  /* (uploadShots 는 2026-07-31 _bgUpload 로 흡수됐다 — 전송 전에 화면 상태가 초기화되므로
     전역 S.* 를 읽으면 안 되고, confirmShot 이 붙잡아둔 job 값으로만 보낸다.) */

  /* 저장 = **화면 먼저, 전송은 뒤에서** (2026-07-31 «빠르게 반응해야»).
     전엔 사진 줄이기+업로드 3~5초를 사용자가 통째로 기다렸다. 이제 누르는 즉시
     «저장했어요» 화면이 뜨고, 서버 전송은 뒤에서 돈다. 실패하면 서랍 맨 위에
     「다시 올리기」 배너가 남는다 — 조용히 사라지는 것보다 낫다. */
  confirmShot() {
    const c = cur();
    // 학년·학기는 무조건 직접 선택(2026-07-24 지시) — 안 골랐으면 막는다.
    if (!S.uploadGrade || !S.uploadSem) {
      const miss = !S.uploadGrade && !S.uploadSem ? "학년과 학기" : (!S.uploadGrade ? "학년" : "학기");
      S.uploadErr = 1; this.render();   // 토스트는 사라지지만 빨간 칸은 남는다
      document.querySelector("#screen select")?.scrollIntoView({ block: "center" });
      return toast(`${miss}를 골라주세요 — 위쪽 선택칸이에요`);
    }
    S.uploadErr = 0;
    if (S.uploadBusy) return;
    const type = S.uploadType || "상장";
    const period = `초${S.uploadGrade} ${S.uploadSem}학기`;
    const title = (S.uploadTitle || "").trim() || type;
    const CAT = { 상장: "award", 통지표: "report_card", 성적표: "grade_sheet", 자격증: "certificate", 활동: "activity", 기타: "other" };
    const ICON = { 상장: "ti-award", 통지표: "ti-file-text", 성적표: "ti-chart-bar", 자격증: "ti-certificate", 활동: "ti-flask", 기타: "ti-paperclip" };
    const images = S.shots.map((s) => s.web);       // 앞·뒤 여러 장
    // 전송에 쓸 값을 지금 붙잡아둔다 — 화면 상태는 바로 아래에서 초기화되니까
    const job = {
      shots: S.shots.slice(), child: c,
      meta: { category: CAT[type] || "other", school_year: String(S.uploadGrade), semester: String(S.uploadSem), title: (S.uploadTitle || "").trim() },
    };
    STUB.records.unshift({
      id: Math.max(0, ...STUB.records.map((r) => r.id)) + 1,
      category: CAT[type], period: { school_year: +S.uploadGrade, semester: +S.uploadSem, label: period },
      date: S.uploadDate || null,   // 발급일자 YYYYMMDD
      title, icon: ICON[type], image: images[0], images,   // 대표=첫 장, 전체=images
    });
    if (c.counts) c.counts.records = (c.counts.records || 0) + 1;
    S.savedLabel = `${title}${images.length > 1 ? ` · ${images.length}장` : ""}`;
    S.uploadTitle = null; S.uploadDate = null; S.uploadGrade = ""; S.uploadSem = ""; S.shots = []; S.ocrText = null;   // 다음 업로드는 새로
    S.uploadStep = 2; this.render();
    toast("저장했어요");
    this._bgUpload(job);           // 서버 전송은 뒤에서 — 끝나면 서버 목록으로 조용히 맞춘다
  },
  /* 뒤에서 올리기 — 성공하면 서버 목록으로 갈아끼우고, 실패하면 서랍 배너로 재시도를 남긴다. */
  async _bgUpload(job) {
    if (!TOKENS.access || !job.child?.server_id) return;   // 목업·로그인 전: 화면에만 남는 게 원래 동작
    S.upPending = (S.upPending || 0) + 1;
    try {
      const fd = new FormData();
      fd.append("child_id", job.child.server_id);
      fd.append("category", job.meta.category);
      fd.append("school_year", job.meta.school_year);
      fd.append("semester", job.meta.semester);
      if (job.meta.title) fd.append("title", job.meta.title);
      const prepped = await Promise.all(job.shots.map((s) => prepShot(s.web)));
      prepped.forEach(({ full, thumb }, i) => {
        fd.append("files", full, `shot${i + 1}.jpg`);
        fd.append("files_t", thumb, `shot${i + 1}_t.jpg`);
      });
      const r = await api("/records", { method: "POST", form: fd });
      if (!r?.ok) throw new Error(r?.error?.message || "서버가 거절했어요");
      if (r.data.skipped?.length) toast(`${r.data.skipped.length}장은 너무 커서 건너뛰었어요`);
      S.upFail = null;
      if (cur()?.server_id === job.child.server_id) { await loadRecords(); saveLifeCache(job.child); }
    } catch (e) {
      console.error("[기록 배경 업로드 실패]", e);
      S.upFail = job;              // 서랍 배너가 「다시 올리기」로 잡는다
      toast(`기록이 서버에 안 올라갔어요 — 서랍에서 다시 올릴 수 있어요`);
      this.render();
    } finally {
      S.upPending = Math.max(0, (S.upPending || 1) - 1);
    }
  },
  retryUpload() {
    const job = S.upFail; S.upFail = null; this.render();
    if (job) { toast("다시 올리는 중…"); this._bgUpload(job); }
  },
  /* 자매 사이트로 보내기 — 우리 서비스끼리 오가게 한다.
     ⚠ **앱 안에 띄우지 않는다.** 바깥 브라우저로 연다(권한·쿠키가 섞이지 않게). */
  openSister(key) {
    const site = SISTER_SITES[key];
    if (!site?.url) return;
    openExternal(site.url, site.name);
  },
  /* 내 이름 고치기 (2026-07-27) — 이름은 되돌릴 수 있는 값이라 재인증까지 요구하지 않는다.
     이메일·전화는 여기서 안 건드린다. 그건 비밀번호 찾기·알림 수신처가 걸린 값이다. */
  nameEdit() { S.nameDraft = STUB.me.account.display_name || ""; location.hash = "#editname"; this.render(); document.getElementById("name-edit")?.focus(); },
  nameCancel() { S.nameDraft = null; location.hash = "#mypage"; this.render(); },
  async nameSave() {
    const v = (S.nameDraft || "").trim();
    if (!v) return toast("이름을 적어주세요");
    if (!TOKENS.access) { STUB.me.account.display_name = v; S.nameDraft = null; this.render(); return; }
    const r = await api("/me", { method: "PATCH", body: { display_name: v } });
    if (!r?.ok) return toast(r?.error?.message || "저장하지 못했어요");
    STUB.me.account = { ...STUB.me.account, ...r.data.account };
    S.nameDraft = null; this.render(); toast("이름을 바꿨어요");
  },
  tlToggle(g) {
    const now = +cur()?.grade || 1;
    const open = (S.tlOpen === null ? now : S.tlOpen);
    S.tlOpen = open === g ? -1 : g;      // 같은 걸 또 누르면 접는다
    this.render();
  },
  // 검색 — 아직 없는 기능이다. 있는 척하지 않고 그렇다고 말한다.
  /* 검색칸 열고 닫기. 닫을 때 검색어를 비운다 — 안 비우면 다음에 서랍을 열었을 때
     아코디언이 아니라 옛 검색 결과가 떠 있어 «기록이 사라졌다»로 읽힌다. */
  recordSearch() {
    S.recSearch = !S.recSearch;
    if (!S.recSearch) S.recQ = "";
    this.render();
    if (S.recSearch) { const el = document.getElementById("recq"); if (el) el.focus(); }
  },
  recordQuery(v) { S.recQ = v; renderKeepFocus(); },

  /* ── 미션 (2026-08-01) ────────────────────────────────────
     규칙은 서버가 지킨다. 여기서는 화면만 맞추고, 서버가 거절하면 그 말을 그대로 보여준다. */
  /* ⚠ 앱이 켜지는 순간엔 아직 자녀를 못 받아왔다. 그때 «미션 없음»으로 못 박으면
     다음에 다시 안 부른다 — 홈 카드가 영영 「오늘 미션 없음」으로 남는다(2026-08-01 실측).
     **못 묻는 상태와 물어봤는데 없는 상태는 다르다.** 못 묻겠으면 null 로 두고 그냥 돌아간다. */
  /* 🎲 오늘 미션 바꾸기 — 하루 한 번.
     ⚠ 성공/실패 판정을 앱이 하지 않는다. 「오늘은 이미 바꿨어요」도 서버가 말한다. */
  async msReroll() {
    const c = cur();
    if (!c) return;
    const r = await api(`/children/${c.id}/missions/reroll`, { method: "POST" });
    /* ⚠ 막히는 경우는 거의 «오늘 이미 바꿨다» 하나다. 서버 안내문이 안 실려 오면
       「지금은 바꿀 수 없어요」 같은 맹탕이 뜬다 — 그건 아이에게 아무것도 안 알려준다. */
    if (!r.ok) { toast(r.message || "오늘은 이미 한 번 바꿨어요. 내일 다시 할 수 있어요."); return; }
    toast("오늘 미션을 바꿨어요");
    await this.loadMissions(true);
    this.render();
  },
  /* 그 학교·학년의 «실제» 반 이름을 받아온다 (2026-08-09).
     ⚠ 시간표는 조회만으로 NEIS 를 안 부른다 — 먼저 warm 으로 캐시를 채워야 한다(실측).
     ⚠ 못 받아오면 조용히 숫자 폴백으로 둔다. 등록을 막으면 안 된다 —
       반 이름을 못 읽는 것보다 아이를 못 넣는 게 훨씬 나쁘다. */
  async loadClassNames(slug, grade) {
    if (!slug || !grade) return;
    S.classNames = null; S.classBusy = true; this.render();
    const path = "/schools/" + encodeURIComponent(slug);
    try {
      /* ⚠ 방학에는 **다음 학기 시간표가 아직 NEIS 에 없다.**
         실측(2026-08-09, 경기초): 1학기는 전 학년 「난초·매화·모란·장미」가 다 나오는데
         2학기는 전 학년 0건이다. 그래서 8월에 가입하는 부모는 반 이름을 못 골랐다.
         → 지금 학기로 물어보고 비면 **이전 학기로 한 번 더** 물어본다.
           반 이름은 학기가 바뀌어도 대개 그대로다(꽃 이름·색 이름은 학년 단위로 정해진다). */
      /* ⚠ `classes=1` 은 **반 이름만** 준다. 시간표를 통째로 받아 추리면
         페이징 50건에 잘려서 반이 몇 개 빠진다(경기초 4학년 「장미」가 그렇게 사라졌다). */
      const pull = async (sem) => {
        const q = sem ? `&semester=${sem}` : "";
        await api(`${path}/warm?kind=timetable&grade=${encodeURIComponent(grade)}${q}`, { method: "POST" });
        const r = await api(`${path}/timetable?classes=1&grade=${encodeURIComponent(grade)}${q}`);
        return (r?.ok ? r.data.items : []).filter(Boolean);
      };
      let names = await pull("");
      if (!names.length) names = await pull("1");
      if (!names.length) names = await pull("2");
      S.classNames = names.length ? names.sort() : null;
    } catch (e) { S.classNames = null; }
    S.classBusy = false; this.render();
  },

  async loadMissions(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;        // 아직 못 묻는다 → 다음 그리기에서 다시
    if (S.missions !== null && !force) return;
    if (S._missionBusyLoad) return;                     // 그리기가 잦아 같은 요청이 겹치는 것을 막는다
    S._missionBusyLoad = true;
    try {
      const r = await api(`/children/${c.server_id}/missions`);
      if (r?.ok) {
        S.missions = r.data.items || [];
        S.missionStars = r.data.stars || 0;
      } else if (S.missions === null) {
        S.missions = [];                                 // 서버가 «없다»고 답한 것 — 이건 못 박아도 된다
      }
    } catch (_) {
      /* 통신이 끊긴 것뿐이다. null 로 두어 다음에 다시 묻는다 */
    }
    S._missionBusyLoad = false;
    this.render();
  },
  async _mission(id, path, body) {
    if (S.missionBusy) return null;
    S.missionBusy = id; this.render();
    try {
      const r = await api(`/missions/${id}/${path}`, { method: "POST", ...(body ? { body } : {}) });
      S.missionBusy = null;
      if (!r?.ok) { this.render(); toast(r?.error?.message || "잘 안 됐어요"); return null; }
      await this.loadMissions(true);
      return r.data;
    } catch (_) {
      S.missionBusy = null; this.render(); toast("잘 안 됐어요"); return null;
    }
  },
  async missionDone(id) {
    const m = (S.missions || []).find((x) => x.id === id);
    const d = await this._mission(id, "done");
    if (!d) return;
    /* 의뢰는 부모 확인을 거친다(2026-08-02). 별이 그 자리에서 안 나오는데 축하 오버레이를
       띄우면 «받았다»고 거짓말하는 것이다. 보낸 사실만 알리고, 카드가 «기다리는 중»으로 바뀐다. */
    if (d.status === "waiting") {
      toast(isChildToken() || S.childView
        ? "확인중 — 아침 8시까지는 " + kw("unit") + "이 나와요"
        : "확인 기다림으로 넘어갔어요");
      return;
    }
    /* 자녀 화면에선 토스트 대신 **축하 오버레이** — 완료 순간이 이 앱의 봉우리다(테마 시안 확정). */
    if (isChildToken() || S.childView) { S.kidHooray = { title: m?.title || "", stars: d.got }; this.render(); }
    else toast(`★${d.got} 받았어요!`);
    this.loadMissionSets(true);   // 세트가 완주됐는지는 **서버가** 판단한다
  },
  /* 다음 장으로. 마지막이면 처음으로 돌아온다 — 막다른 끝을 만들지 않는다. */
  deckNext() { const n = deckCards().length; if (n > 1) S.deckIdx = (S.deckIdx + 1) % n; this.render(); },
  /* 자녀폰 미연결 안내 — 상시 경고를 띄우면 「원래 그런 것」이 되어 아무도 안 읽는다.
     물음표를 눌렀을 때만 열고, 푸는 방법까지 같이 말해준다. */
  linkWarnOpen() { S.linkWarn = true; this.render(); },
  linkWarnClose() { S.linkWarn = false; this.render(); },
  kidHoorayClose() { S.kidHooray = null; this.render(); },
  /* 급식 평가 제출 — 즉시판정(2026-08-02 재설계).
     · 부모에게 말을 보내지 않는다. 이건 자녀폰 안에서 끝나는 NPC 미션이다
       (2단계에서 대화로 흘리던 것을 걷어냄 — 부모는 월 1회 리포트로 받는다).
     · 저장은 **원문 + 합친 이름 + 종류**를 다 보낸다. 나중에 사전이 좋아져도
       원문이 있으면 다시 계산할 수 있다.
     · 별은 서버가 원장(star_ledger)에 적는다. 응답의 합계를 그대로 받아 쓴다 —
       앱이 +1 해두면 새로고침 때 서버 값과 어긋난다. */
  async mealRateSubmit() {
    const d = S.mealDraft;
    if (!d.stars || S.mealBusy) return;
    const meal = mealsOf().find((m) => m.date === TODAY && m.type === "중식");
    if (!meal) return;
    /* 1등만 rank=1, 나머지는 null. 스키마는 그대로 두고 값만 덜 채운다 —
       나중에 순위를 더 받고 싶어져도 테이블을 안 고쳐도 된다. */
    const items = meal.dishes.map((x) => ({
      raw: x.name, key: dishKey(x.name), cat: dishCat(x.name),
      rank: d.best === x.name ? 1 : null,
    }));

    S.mealBusy = true; this.render();
    let got = 1;
    if (TOKENS.access) {
      const r = await api("/missions/meal-rate", { method: "POST", body: { stars: d.stars, items } });
      S.mealBusy = false;
      if (!r?.ok) {
        this.render();
        return toast(r?.error?.message || "지금은 못 보냈어요. 잠시 뒤 다시 해줘");
      }
      if (typeof r.data?.total_stars === "number") S.missionStars = r.data.total_stars;
      got = r.data?.got || 1;
    } else {
      S.mealBusy = false;
      S.missionStars = (S.missionStars || 0) + 1;   // 목업 전용 — 서버가 붙으면 위 응답이 이긴다
    }

    noteMark(TODAY, { meal: d.stars });   // 달력 «아이 흔적»에 남긴다(§3) — 실제로 준 별점 그대로
    S.mealRated = true;
    App.loadSchoolMissions(true);   // 학교 미션 카드를 새로 받는다(1/3 → 2/3)
    S.mealDraft = { stars: 0, best: null };
    S.kidHooray = { title: "급식 평가", stars: got };
    location.hash = "#game";
    this.render();
  },

  async subjectSubmit() {
    if (!S.subjectBest || S.subjectBusy) return;
    S.subjectBusy = true; this.render();
    let got = 1;
    if (TOKENS.access) {
      const r = await api("/missions/subject-log", { method: "POST", body: { subject: S.subjectBest } });
      S.subjectBusy = false;
      if (!r?.ok) { this.render(); return toast(r?.error?.message || "지금은 못 보냈어요. 잠시 뒤 다시 해줘"); }
      if (typeof r.data?.total_stars === "number") S.missionStars = r.data.total_stars;
      got = r.data?.got || 1;
    } else {
      S.subjectBusy = false;
      S.missionStars = (S.missionStars || 0) + 1;   // 목업 전용
    }
    S.subjectLogged = true;
    App.loadSchoolMissions(true);   // 학교 미션 카드를 새로 받는다(1/3 → 2/3)
    S.subjectBest = null;
    S.kidHooray = { title: "오늘 재밌었던 것", stars: got };
    location.hash = "#game";
    this.render();
  },

  friendTap(n) {
    const d = S.friendDraft;
    const i = d.picked.indexOf(n);
    if (i >= 0) d.picked.splice(i, 1); else { d.picked.push(n); d.alone = false; }
    this.render();
  },
  friendAlone() {
    const d = S.friendDraft;
    d.alone = !d.alone;
    if (d.alone) d.picked = [];   // 혼자면 친구를 같이 고를 수 없다
    this.render();
  },
  friendAddStart() { S.friendDraft.adding = ""; this.render(); setTimeout(() => document.getElementById("fr-add")?.focus(), 30); },
  friendAddCancel() { S.friendDraft.adding = null; this.render(); },
  friendAddSave() {
    const n = (S.friendDraft.adding || "").trim();
    if (!n) return;
    if (!S.friends.includes(n)) S.friends.push(n);
    if (!S.friendDraft.picked.includes(n)) { S.friendDraft.picked.push(n); S.friendDraft.alone = false; }
    S.friendDraft.adding = null;
    saveFriends();
    this.render();
  },

  /* 제출 — 즉시판정. 급식 평가와 같은 틀이다.
     ⚠ 서버가 붙기 전에도 칩이 남아야 «타이핑은 처음 한 번뿐»이 성립한다 →
        친구 목록은 localStorage 에도 둔다(서버 값이 오면 그게 이긴다). */
  async friendSubmit() {
    const d = S.friendDraft;
    if ((!d.picked.length && !d.alone) || S.friendBusy) return;
    S.friendBusy = true; this.render();
    let got = 1;
    if (TOKENS.access) {
      const r = await api("/missions/play-log", { method: "POST",
        body: { alone: d.alone, friends: d.picked } });
      S.friendBusy = false;
      if (!r?.ok) { this.render(); return toast(r?.error?.message || "지금은 못 보냈어요. 잠시 뒤 다시 해줘"); }
      if (typeof r.data?.total_stars === "number") S.missionStars = r.data.total_stars;
      got = r.data?.got || 1;
    } else {
      S.friendBusy = false;
      S.missionStars = (S.missionStars || 0) + 1;   // 목업 전용
    }
    S.friendLogged = true;
    App.loadSchoolMissions(true);   // 학교 미션 카드를 새로 받는다(1/3 → 2/3)
    S.friendDraft = { picked: [], alone: false, adding: null };
    S.kidHooray = { title: "오늘 논 친구", stars: got };
    location.hash = "#game";
    this.render();
  },

  kidTheme(theme) {
    if (!KID_THEMES[theme]) return;
    S.kidTheme = theme; S.kidAccent = theme;   // 색이 곧 테마다 — 따로 고르지 않는다
    saveKidPrefs(); location.hash = "#game"; this.render();   // 아이 홈은 이제 게임이다
  },
  /* 강조색 따로 고르기는 없앴다(2026-08-03) — 색 12벌 자체가 그 역할을 한다.
     테마×강조색 36가지는 아이에게 고르라고 낼 수가 없다. */
  kidAccentPick(a) { if (KID_THEMES[a]) this.kidTheme(a); },
  // 「못 했어요」에는 벌이 없다. 도장이 안 늘 뿐이고, 말해준 것 자체를 인정해준다.
  async missionSkip(id) {
    const d = await this._mission(id, "skip");
    if (d) toast("괜찮아요. 말해줘서 고마워요");
  },
  /* 사진 제출 — 기록 올릴 때 쓰는 카메라를 그대로 쓴다.
     보내고 나면 기다림이 시작된다. 언제 끝나는지 화면이 말해줘야 재촉을 안 한다. */
  /* 사진을 찍어 보내되, **안 찍으면 그냥 완료**로 간다.
     사진을 강제하면 카메라가 없는 상황에서 미션이 통째로 막히고,
     아예 안 물으면 부모가 «뭘 했는지» 볼 방법이 없다. 둘 다 열어 둔다. */
  async missionShotOrDone(id) {
    const sent = await this.missionShoot(id, true);
    if (!sent) await this.missionDone(id);
  },

  async missionShoot(id, quiet) {
    const C = window.Capacitor?.Plugins?.Camera;
    let blob = null;
    try {
      if (C) {
        const p = await C.getPhoto({ quality: 70, resultType: "uri", source: "CAMERA", width: 900 });
        const url = window.Capacitor.convertFileSrc(p.path || p.webPath);
        blob = await (await fetch(url)).blob();
      } else {
        blob = await new Promise((res) => {
          const i = document.createElement("input");
          i.type = "file"; i.accept = "image/*"; i.capture = "environment";
          i.onchange = () => res(i.files?.[0] || null);
          i.click();
        });
      }
    } catch (_) { return false; }
    if (!blob) return false;          // 취소했다 — 부르는 쪽이 «그냥 완료»로 넘긴다
    S.missionBusy = id; this.render();
    try {
      const fd = new FormData();
      fd.append("photo", blob, "mission.jpg");
      const r = await api(`/missions/${id}/photo`, { method: "POST", form: fd });
      S.missionBusy = null;
      if (!r?.ok) { this.render(); toast(r?.error?.message || "사진을 보내지 못했어요"); return false; }
      await this.loadMissions(true);
      toast("보냈어요! 내일 아침 8시까지는 도장이 나와요");
      return true;
    } catch (_) { S.missionBusy = null; this.render(); toast("사진을 보내지 못했어요"); return false; }
  },
  async missionApprove(id) {
    // 사진은 도장 **찍기 전에** 붙잡아 둔다 — 찍고 나면 그 미션 사진을 서버가 안 내줄 수 있다
    const keep = S.keepShot === id ? (S.missions || []).find((x) => x.id === id) : null;
    const d = await this._mission(id, "approve");
    if (!d) return;
    toast(`확인했어요 — ★${d.got} 줬습니다`);
    S.keepShot = null;
    if (keep) this._keepShotSave(keep);   // 서랍행은 뒤에서 — 도장 찍히는 순간을 붙잡아 두지 않는다
  },
  // 「거짓말했지?」가 아니라 「다시 해볼까?」다. 같은 기능인데 남는 게 완전히 다르다.
  async missionRevert(id) {
    const d = await this._mission(id, "revert");
    if (d) toast("다시 할 수 있게 돌려놨어요");
  },

  /* 리포트 불러오기. 달을 바꾸면 다시 받는다 — 캐시를 두면 «지난달인데 이번달 숫자»가 뜬다. */
  /* ═══ 스타코인 상점 · 2단계 보상 · 아이 모드 (2026-08-07 지시서 §3·§5) ═══════════
     ⚠ **화면은 규칙을 세지 않는다.** 잔액·주간상한·중복·«보너스 한 번만»은 전부 서버가 막는다
       (api_reward.js 머리말 ①~⑥). 여기서 버튼을 가리는 건 «친절»이지 «방어»가 아니다 —
       그래서 서버가 거절하면 그 문구를 그대로 보여 준다. 지어내지 않는다.
     ⚠ 화면에 쓰는 말은 게이밍 언어다(§1.1): 바꾸기 · 🎟 티켓 · 기다리는 중 · 받았어요.
       서버 필드(reward_orders·requested·fulfilled)는 **안 바꾼다** — 출력할 때만 갈아입힌다. */

  async loadStore(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S.store !== null && !force) return;
    if (S._storeBusyLoad) return;
    S._storeBusyLoad = true;
    try {
      const r = await api(`/children/${c.server_id}/store`);
      /* 🐞 2026-08-07 실측: 실패한 응답까지 «없음»으로 못 박고 있었다.
         부팅 중에는 `cur()` 가 아직 **앞 세션의 자녀**를 가리켜 서버가 NOT_FOUND 를 준다.
         그걸 `[]` 로 굳혀 두니 진짜 자녀가 붙은 뒤에도 **진열대가 영영 비어 보였다**
         (서버는 4종을 정상으로 주고 있었다). → **성공했을 때만** 값을 박는다.
         실패면 null 로 두어 다음 그리기에서 다시 묻는다. */
      if (r?.ok) {
        S.store = r.data.items || [];
        // 잔액은 원장 하나 — 상점 응답이 준 값으로 같이 맞춰 둔다(두 숫자를 만들지 않는다)
        if (typeof r.data.stars === "number") S.missionStars = r.data.stars;
      }
    } catch (_) { /* 끊긴 것뿐 — null 로 두면 다음 그리기에서 다시 묻는다 */ }
    S._storeBusyLoad = false;
    this.render();
  },

  async loadRewards(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S.rewards !== null && !force) return;
    if (S._rewardBusyLoad) return;
    S._rewardBusyLoad = true;
    try {
      const r = await api(`/children/${c.server_id}/rewards`);
      // 성공했을 때만 박는다 — 위 loadStore 의 «부팅 중 NOT_FOUND» 함정과 같은 이유
      if (r?.ok) {
        S.rewards = r.data.items || [];
        if (typeof r.data.stars === "number") S.missionStars = r.data.stars;
      }
    } catch (_) {}
    S._rewardBusyLoad = false;
    this.render();
  },

  // 아이가 «★n으로 바꾸기» — 서버가 잔액·상한을 막는다
  async storeBuy(itemId) {
    const c = cur();
    if (!c?.server_id || S.storeBusy) return;
    S.storeBusy = itemId; this.render();
    try {
      const r = await api(`/children/${c.server_id}/store/${itemId}/buy`, { method: "POST" });
      S.storeBusy = null;
      if (!r?.ok) { this.render(); toast(r?.error?.message || "잘 안 됐어요"); return; }
      /* ⚠ 목록을 «지우고 다시 받기»로 두면 그 사이 화면이 빈다 —
         「전체적으로 느리다」의 큰 몫이 이것이었다(대표님 지적 08-08).
         잔액은 서버가 준 값으로 **그 자리에서** 바꾸고, 목록은 뒤에서 조용히 새로 받는다. */
      S.missionStars = r.data.stars_left;
      if (S.coin) S.coin = { ...S.coin, stars: r.data.stars_left };
      toast(`🎟 ${r.data.item_title} 티켓으로 바꿨어요`);
      this.render();
      Promise.all([this.loadStore(true), this.loadRewards(true)]).catch(() => {});
    } catch (_) { S.storeBusy = null; this.render(); toast("잘 안 됐어요"); }
  },

  // 부모가 «바꿔줬어요»
  async rewardFulfill(orderId) {
    if (S.storeBusy) return;
    S.storeBusy = orderId; this.render();
    try {
      const r = await api(`/rewards/${orderId}/fulfill`, { method: "POST" });
      S.storeBusy = null;
      if (!r?.ok) { this.render(); toast(r?.error?.message || "잘 안 됐어요"); return; }
      /* ⚠ **그 자리에서 바꾼다.** 서버를 다시 불러올 때까지 옛 화면이 남으면
         부모가 «안 됐나?» 하고 한 번 더 누르고, 그게 「이미 처리했거나 없는 주문이에요」였다
         (08-08 실기: 세 건 다 이미 fulfilled 였다). 목록 새로고침은 뒤에서 조용히 한다. */
      const o = (S.rewards || []).find((x) => x.reward_order_id === orderId);
      if (o) o.status = "fulfilled";
      toast("바꿔줬어요!");
      this.render();
      this.loadRewards(true);
    } catch (_) { S.storeBusy = null; this.render(); toast("잘 안 됐어요"); }
  },

  // 부모가 진열대에 올리기 / 내리기
  storeAddOpen() { S.storeAdd = { title: "", need: 5, limitType: "", limitCount: 1 }; this.render(); },
  storeAddClose() { S.storeAdd = null; this.render(); },
  storeEditToggle() { S.storeEdit = !S.storeEdit; this.render(); },
  /* ⚠ 글자를 칠 때마다 화면을 다시 그리면 **한글 조합이 깨진다**(render() 머리말의 그 함정).
     값만 담아 두고 그리지 않는다 — 시트는 이미 떠 있고 바뀔 모습도 없다.
     ⚠ 예외로 «제한 종류»는 칸이 하나 나타났다 사라지므로 그때만 다시 그린다. */
  storeAddSet(k, v) {
    if (!S.storeAdd) return;
    S.storeAdd[k] = k === "need" || k === "limitCount" ? (parseInt(v, 10) || 0) : v;
    if (k === "limitType") this.render();
  },
  async storeAddSave() {
    const a = S.storeAdd;
    if (!a) return;
    const title = String(a.title || "").trim();
    // 서버도 막지만, 여기서 먼저 말해 주면 왕복 한 번을 아낀다(막는 건 어차피 서버다)
    if (!title) { toast("무엇과 바꿔 줄지 적어 주세요"); return; }
    if (!(a.need >= 1 && a.need <= 999)) { toast("스타코인 수를 확인해 주세요"); return; }
    const c = cur();
    if (!c?.server_id) return;
    const r = await api(`/children/${c.server_id}/store`, { method: "POST", body: {
      title, stars_required: a.need,
      ...(a.limitType ? { limit_type: a.limitType, limit_count: a.limitCount || 1 } : {}),
    } });
    if (!r?.ok) { toast(r?.error?.message || "올리지 못했어요"); return; }
    S.storeAdd = null;
    await this.loadStore(true);
    toast("진열대에 올렸어요");
  },
  async storeDel(itemId) {
    const r = await api(`/store/${itemId}`, { method: "DELETE" });
    if (!r?.ok) { toast(r?.error?.message || "내리지 못했어요"); return; }
    await this.loadStore(true);
    toast("진열대에서 내렸어요");
  },

  // ── 2단계 검증 ────────────────────────────────────────────────
  // 1차: 아이가 «했어요»를 낸다 → 서버가 그 자리에서 도장 1개
  async verifyStep1(missionCode, data) {
    const c = cur();
    if (!c?.server_id || S.verifyBusy) return;
    S.verifyBusy = missionCode; this.render();
    try {
      const r = await api(`/children/${c.server_id}/verify`, { method: "POST",
        body: { mission_code: missionCode, ...(data ? { step1_data: data } : {}) } });
      S.verifyBusy = null; S.step1For = null;
      if (!r?.ok) { this.render(); toast(r?.error?.message || "잘 안 됐어요"); return; }
      if (typeof r.data.stars === "number") S.missionStars = r.data.stars;
      S.verifyPending = null;
      /* 하루 한 번 — 이미 낸 것이면 서버가 `already` 로 알려 준다.
         «이미 했어요»가 벌처럼 읽히지 않게 부드럽게 말한다(아이가 잘못 누른 것뿐이다). */
      if (r.data.already) { this.render(); toast("오늘 건 이미 냈어요"); return; }
      this.render();
      toast("★1 받았어요! 엄마아빠가 보고 보너스를 줄 수도 있어요");
    } catch (_) { S.verifyBusy = null; this.render(); toast("잘 안 됐어요"); }
  },
  async loadVerify(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S.verifyPending !== null && !force) return;
    if (S._verifyBusyLoad) return;
    S._verifyBusyLoad = true;
    try {
      const r = await api(`/children/${c.server_id}/verify?pending=1`);
      if (r?.ok) S.verifyPending = r.data.items || [];   // 실패면 null 로 둔다(다시 묻는다)
    } catch (_) {}
    S._verifyBusyLoad = false;
    this.render();
  },
  // 2차: 부모가 보고 보너스. 서버가 «한 번만»을 지킨다
  async verifyBonus(verifyId, bonus) {
    if (S.verifyBusy) return;
    S.verifyBusy = verifyId; this.render();
    try {
      const r = await api(`/verify/${verifyId}/bonus`, { method: "POST", body: { bonus_stars: bonus } });
      S.verifyBusy = null;
      if (!r?.ok) { this.render(); toast(r?.error?.message || "잘 안 됐어요"); return; }
      if (typeof r.data.stars === "number") S.missionStars = r.data.stars;
      await this.loadVerify(true);
      toast(bonus > 0 ? `보너스 ★${bonus} 줬어요` : "확인했어요");
    } catch (_) { S.verifyBusy = null; this.render(); toast("잘 안 됐어요"); }
  },

  // ── 칭찬 스티커 ───────────────────────────────────────────────
  reactOpen(childId) { S.reactSheet = childId; this.render(); },
  reactClose() { S.reactSheet = null; this.render(); },
  async reactSend(type) {
    const c = cur();
    if (!c?.server_id) return;
    S.reactSheet = null; this.render();
    const r = await api(`/children/${c.server_id}/reactions`, { method: "POST", body: { sticker_type: type } });
    toast(r?.ok ? "칭찬을 보냈어요" : (r?.error?.message || "보내지 못했어요"));
  },
  /* 아이 화면이 «안 본 칭찬»을 가져와 팝업으로 띄운다.
     ⚠ 본 시각을 기기에 적어 둔다 — 안 그러면 앱을 켤 때마다 옛 칭찬이 다시 튀어나온다. */
  async loadReactions() {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S._reactBusyLoad) return;
    S._reactBusyLoad = true;
    try {
      if (S.reactSeen === null) { try { S.reactSeen = localStorage.getItem("eduthink.reactSeen") || ""; } catch (e) { S.reactSeen = ""; } }
      const q = S.reactSeen ? `?since=${encodeURIComponent(S.reactSeen)}` : "";
      const r = await api(`/children/${c.server_id}/reactions${q}`);
      if (r?.ok && (r.data.items || []).length) {
        const newest = r.data.items[0];
        S.kidSticker = newest;
        S.reactSeen = newest.created_at;
        try { localStorage.setItem("eduthink.reactSeen", newest.created_at); } catch (e) {}
        this.render();
      }
    } catch (_) {}
    S._reactBusyLoad = false;
  },
  stickerClose() { S.kidSticker = null; this.render(); },

  // ── 아이 모드 + 4자리 PIN ─────────────────────────────────────
  async loadPinState(force) {
    if (!TOKENS.access) return;
    if (S.pinHas !== null && !force) return;
    if (S._pinBusyLoad) return;
    S._pinBusyLoad = true;
    try {
      const r = await api("/child-mode");
      if (r?.ok) { S.pinHas = r.data.has_pin ? 1 : 0; S.pinLockFor = r.data.locked_for || 0; }
      else if (S.pinHas === null) S.pinHas = 0;
    } catch (_) {}
    S._pinBusyLoad = false;
    this.render();
  },
  /* 키패드 열기. 용도는 셋 — 'set'(걸기·바꾸기) · 'unlock'(부모 모드로 나가기) · 'clear'(지우기).
     ⚠ **아이 모드로 들어갈 때는 안 묻는다.** 들어가는 건 아이가 하는 일이다.
       나올 때만 묻는다 — 그게 이 잠금의 전부다. */
  pinOpen(mode) { S.pinPad = mode; S.pinBuf = ""; S.pinPrev = ""; S.pinMsg = ""; this.render(); },
  pinClose() { S.pinPad = null; S.pinBuf = ""; S.pinPrev = ""; S.pinMsg = ""; this.render(); },
  pinTap(d) {
    if (!S.pinPad || S.pinBuf.length >= 4) return;
    S.pinBuf += String(d); S.pinMsg = "";
    this.render();
    if (S.pinBuf.length === 4) setTimeout(() => this.pinSubmit(), 120);
  },
  pinBack() { S.pinBuf = S.pinBuf.slice(0, -1); S.pinMsg = ""; this.render(); },
  async pinSubmit() {
    const pin = S.pinBuf, mode = S.pinPad;
    if (pin.length !== 4) return;
    S.pinBuf = "";
    try {
      if (mode === "set") {
        // 이미 걸려 있으면 «지금 번호»를 먼저 받는다 — 두 번에 나눠 누른다
        if (S.pinHas && !S.pinPrev) { S.pinPrev = pin; S.pinMsg = "새로 쓸 번호를 눌러 주세요"; this.render(); return; }
        const r = await api("/child-mode/pin", { method: "POST",
          body: { pin, ...(S.pinPrev ? { current_pin: S.pinPrev } : {}) } });
        if (!r?.ok) { S.pinPrev = ""; S.pinMsg = r?.error?.message || "잘 안 됐어요"; this.render(); return; }
        S.pinHas = 1; this.pinClose(); toast("아이 모드 번호를 정했어요");
      } else if (mode === "unlock") {
        const r = await api("/child-mode/pin/verify", { method: "POST", body: { pin } });
        if (!r?.ok) {
          /* ⚠ 서버가 덧붙이는 값(`locked_for`·`left`)은 **`data` 에 온다.** `error.details` 가 아니다
             (api_core.js `apiErr` 는 extra 를 `body.data` 에 넣는다 — 2026-08-07 확인). */
          S.pinLockFor = r?.data?.locked_for || 0;
          S.pinMsg = r?.error?.message || "번호가 달라요";
          this.render(); return;
        }
        S.kidMode = false; this.pinClose(); this.render();
      } else if (mode === "clear") {
        const r = await api("/child-mode/pin", { method: "DELETE", body: { pin } });
        if (!r?.ok) { S.pinMsg = r?.error?.message || "번호가 달라요"; this.render(); return; }
        S.pinHas = 0; S.kidMode = false; this.pinClose(); toast("아이 모드 번호를 지웠어요");
      }
    } catch (_) { S.pinMsg = "잘 안 됐어요"; this.render(); }
  },
  /* 아이 모드 켜기 — PIN 이 없으면 먼저 정하게 한다.
     ⚠ 번호 없이 켜면 «나가기»를 아무나 누를 수 있어 잠금이 아무 뜻이 없다. */
  kidModeOn() {
    if (!S.pinHas) { toast("먼저 나갈 때 쓸 번호를 정해 주세요"); this.pinOpen("set"); return; }
    S.kidMode = true;
    if (location.hash !== "#home") location.hash = "#home";
    this.render();
    toast("아이 모드예요. 나갈 땐 번호를 눌러요");
  },
  kidModeOff() { this.pinOpen("unlock"); },

  /* ═══ 🎮 미션 게임 동작 (2026-08-08) ═══════════════════════════════
     ⚠ 코인·채점은 전부 서버가 한다. 여기서는 «받은 값을 보여주는 것»만 한다. */

  /* 카드를 연다/닫는다. `null` 이면 홈(2×2 타일)이다.
     ⚠ 탭이 아니라 «들어갔다 나오는» 문법이라 뒤로가기가 곧 홈이다. */
  gameTab(k) {
    S.gameTab = k || null;
    if (k === "today" && S.quiz === null) this.loadQuiz();
    if (k === "shop" && S.store === null) this.loadStore();
    if (k === "morning" || k === "after") {
      if (S.missions === null) this.loadMissions();
      if (S.msets === null) this.loadMissionSets();
    }
    if (k === "school" && S.schoolMs === null) this.loadSchoolMissions();
    this.render();
  },

  /* 배경색 — 아이 화면에서 실제로 바뀌는 것은 CSS 변수 두 개뿐이다.
     ⚠ 부모 테마(--surf/--card-a)는 **건드리지 않는다**. 8/4 사고의 재발 방지선이다. */
  async gmTheme(k) {
    S.gmTheme = k;
    const c = cur();
    if (c) c.kid_theme = k;                       // 화면은 즉시 바뀐다
    this.render();
    if (!TOKENS.access || !c?.server_id) return;  // 서버에 못 남겨도 화면은 이미 바뀌었다
    try { await api(`/children/${c.server_id}`, { method: "PATCH", body: { kid_theme: k } }); }
    catch (_) {}
  },

  /* 한 걸음 뒤로. 뒤로 갔는데 주소가 그대로면 «갈 곳이 없던 것»이라 홈으로 보낸다 —
     history.length 만 보면 앱 밖(빈 페이지)으로 나가 흰 화면이 된다. */
  goBack() {
    const from = location.hash;
    history.back();
    setTimeout(() => { if (location.hash === from) App.goHome(); }, 120);
  },

  clearClose() { S.clear = null; this.render(); },

  /* 부모가 «아이 화면»을 일부러 들여다본다. 기본은 관리 화면이다 — 부모에게 아이 세계를
     기본으로 띄우면 «내 화면이 왜 애들 것이지»가 된다(대표님 지적 08-08). */
  pmTab(k) { if (k === "preview") return this.gamePreviewOn(); S.pmTab = k || null; this.render(); },
  gameReload() { S._gameTried = null; this.gameEnter(); },
  gamePreviewOn() { S.gamePreview = true; S.gameTab = null; S.pmTab = null; this.gameEnter(); this.render(); },
  gamePreviewOff() { S.gamePreview = false; S.gameTab = null; this.render(); },

  /* 해낸 미션 하나에 ＋1 을 얹어 준다. ⚠ 몇 개가 실제로 들어갔는지는 **서버가** 말한다 —
     하루 상한에 걸리면 깎여서 들어가고, 화면이 미리 세어 두면 거짓말이 된다.
     ⚠ 자유 지급(＋3·＋5)은 없앴다 — 대표님 지시(08-08). */
  async missionBonus(assignId) {
    const c = cur();
    if (!c?.server_id || S.giveBusy) return;
    S.giveBusy = true; this.render();
    try {
      const r = await api(`/children/${c.server_id}/mission-bonus`, { method: "POST", body: { assign_id: assignId } });
      if (!r?.ok) toast(r?.error?.message || "못 줬어요");
      else {
        if (r.data.coin) S.coin = r.data.coin;
        S.bonusGiven = [...(S.bonusGiven || []), assignId];
        toast(r.data.already ? "이미 줬어요"
          : r.data.capped ? "오늘은 여기까지예요" : "★1 얹어 줬어요!");
      }
    } catch (_) { toast("못 줬어요"); }
    S.giveBusy = false;
    this.render();
  },

  async loadBonusGiven(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S.bonusGiven && !force) return;
    try {
      const r = await api(`/children/${c.server_id}/mission-bonus`);
      if (r?.ok) S.bonusGiven = r.data.given || [];
    } catch (_) {}
    this.render();
  },

  /* 학교 미션 오늘 상태 — **서버가 정본**이다. 화면이 «했나»를 스스로 세지 않는다.
     ⚠ 실패하면 null 로 두어 다시 묻는다. `[]` 로 굳히면 카드가 영영 안 뜬다(08-07 사고). */
  async loadSchoolMissions(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S.schoolMs && !force) return;
    if (S._schoolBusy) return;
    S._schoolBusy = true;
    try {
      const r = await api(`/children/${c.server_id}/school-missions`);
      if (r?.ok) S.schoolMs = r.data;
      else if (r?.status === 404) S.schoolMs = { available: false, items: [], done: 0, all: 0 };
    } catch (_) {}
    S._schoolBusy = false;
    this.render();
  },

  /* 아침·방과후 세트 완주 — 학교 세트와 같은 규칙이되 파일이 다르다(위 주석 참조) */
  async loadMissionSets(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S.msets && !force) return;
    try {
      const r = await api(`/children/${c.server_id}/mission-sets`);
      if (r?.ok) S.msets = { ...r.data.sets, bonus: r.data.sets?.morning?.bonus || 2 };
    } catch (_) {}
    this.render();
  },

  async setBonus(slot) {
    const c = cur();
    if (!c?.server_id) return;
    try {
      const r = await api(`/children/${c.server_id}/mission-sets/bonus`, { method: "POST", body: { slot } });
      if (r?.ok && r.data.granted > 0) {
        if (r.data.coin) S.coin = r.data.coin;
        await this.loadMissionSets(true);
        this.clearShow(slot === "morning" ? "🌅" : "📚",
                       slot === "morning" ? "아침 미션" : "방과후 미션", r.data.granted);
        return;
      }
      if (r?.ok && r.data.already) toast("이미 받았어요");
      else if (!r?.ok) toast(r?.error?.message || "지금은 받을 수 없어요");
    } catch (_) { toast("지금은 받을 수 없어요"); }
    this.render();
  },

  /* 세트 완주 보너스 — 셋 다 했을 때만 서버가 준다. 화면은 «달라고» 할 뿐이다.
     주고 나면 클리어 연출을 띄운다(기획서 v2 §01.3 — 세트를 완주한 «순간»에만). */
  async schoolBonus() {
    const c = cur();
    if (!c?.server_id || S._schoolBusy) return;
    S._schoolBusy = true;
    try {
      const r = await api(`/children/${c.server_id}/school-missions/bonus`, { method: "POST", body: {} });
      if (r?.ok && r.data.granted > 0) {
        if (r.data.coin) S.coin = r.data.coin;
        S._schoolBusy = false;
        await this.loadSchoolMissions(true);
        this.clearShow("🏫", "학교 미션", r.data.granted);
        return;
      }
      if (r?.ok && r.data.already) toast("이미 받았어요");
      else if (r?.ok && !r.data.cleared) toast("아직 다 못 했어요");
      else if (!r?.ok) toast(r?.error?.message || "지금은 받을 수 없어요");
    } catch (_) { toast("지금은 받을 수 없어요"); }
    S._schoolBusy = false;
    this.render();
  },

  /* 세트를 완주한 «순간»에만 연출한다. 개별 완료는 조용히 — 매번 띄우면 성가신 것이 된다.
     1.2초 뒤 저절로 닫힌다(누르면 즉시). 딱지는 타일에 하루 종일 남는다. */
  clearShow(icon, name, stars) {
    S.clear = { icon, name, stars };
    this.render();
    clearTimeout(CLEAR_TIMER);
    CLEAR_TIMER = setTimeout(() => { if (S.clear) { S.clear = null; App.render(); } }, 1200);
  },

  /* 한 판 더 — 코인을 내고 문제를 다시 받는다.
     ⚠ 금액을 보내지 않는다. **값은 서버가 매긴다** — 화면이 값을 정하면 우회된다. */
  async quizRetry() {
    const c = cur();
    if (!c?.server_id || S._quizBusy) return;
    S._quizBusy = true;
    try {
      const r = await api(`/children/${c.server_id}/quiz/retry`, { method: "POST", body: {} });
      if (!r?.ok) { toast(r?.error?.message || "한 판 더 열지 못했어요"); }
      else {
        S.quiz = { ...r.data, done: false, correct: 0, coins: 0,
                   perfect_bonus: S.quiz?.perfect_bonus ?? 5 };
        S.quizResult = null; S.quizIdx = -1; S.quizPick = {};
        if (r.data.coin) S.coin = r.data.coin;
      }
    } catch (_) { toast("한 판 더 열지 못했어요"); }
    S._quizBusy = false;
    this.render();
  },

  async loadCoin(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S.coin && !force) return;
    try {
      // 코인 상태는 퀴즈 응답이 같이 준다 — 따로 부르는 길이 없으므로 상점 응답으로 대신한다
      const r = await api(`/children/${c.server_id}/store`);
      if (r?.ok && typeof r.data.stars === "number") {
        S.coin = { stars: r.data.stars, earned_today: S.coin?.earned_today || 0,
                   limit: S.coin?.limit || COIN_LIMIT, room: S.coin?.room ?? COIN_LIMIT,
                   level: S.coin?.level || 1, streak: S.coin?.streak || 0 };
      }
    } catch (_) {}
    this.render();
  },

  /* 게임 화면에 들어올 때 한 번에 불러온다 — 카드가 하나씩 뒤늦게 뜨면 «고장»으로 읽힌다 */
  /* 게임·관리 화면에 들어올 때 필요한 것을 **한꺼번에** 받는다.
     ⚠ 하나씩 끝날 때마다 다시 그리면 화면이 여섯 번 덜컹인다 — 그게 「느리다」로 읽힌다.
        각 로더의 render 는 그대로 두되(먼저 온 것부터 보이는 게 낫다), 요청은 동시에 나간다. */
  gameEnter() {
    /* 🔴 **여기서 무조건 render 를 부르면 앱이 멈춘다.**
       라우터가 게임 화면을 그릴 때마다 gameEnter 를 부르는데, 받을 게 하나도 없어도
       마지막에 render 를 부르면 → 라우터 → gameEnter → render … 로 서로를 무한히 부른다
       (08-08 실기에서 화면이 얼어붙었다). **받을 게 있을 때만** 다시 그린다. */
    /* 🔴 **한 번 시도한 것은 다시 안 부른다.**
       「받을 게 있으면 다시 그린다」만으로는 부족했다 — 어떤 로더가 **실패해서 값이 계속 null**
       이면 그릴 때마다 다시 부르고, 부르면 또 그려서 **무한히 돈다.**
       화면은 마지막 그림이 남아 멀쩡해 보이는데 JS 가 멈춰 있어 원인을 찾기가 아주 어렵다
       (08-08: 자녀 폰이 이 상태였다. 웹소켓은 열리는데 응답이 없어서 잡았다).
       그래서 «값이 없나»가 아니라 «부른 적 있나»로 막는다. */
    if (S._gameLoading) return;
    S._gameTried = S._gameTried || {};
    const once = (k, fn) => { if (S._gameTried[k]) return null; S._gameTried[k] = 1; return fn(); };
    const jobs = [];
    const c0 = once("coin", () => this.loadCoin()); if (c0) jobs.push(c0);
    { const j = once("missions", () => this.loadMissions()); if (j) jobs.push(j); }
    { const j = once("schoolMs", () => this.loadSchoolMissions()); if (j) jobs.push(j); }
    { const j = once("msets", () => this.loadMissionSets()); if (j) jobs.push(j); }
    { const j = once("store", () => this.loadStore()); if (j) jobs.push(j); }
    { const j = once("rewards", () => this.loadRewards()); if (j) jobs.push(j); }
    { const j = once("quiz", () => this.loadQuiz()); if (j) jobs.push(j); }
    if (!isChildToken() && !S.kidMode) {          // 부모 관리 화면에만 필요한 둘
      { const j = once("verify", () => this.loadVerify()); if (j) jobs.push(j); }
      { const j = once("bonus", () => this.loadBonusGiven()); if (j) jobs.push(j); }
    }
    if (!jobs.length) return;              // 받을 게 없다 — 다시 그리지 않는다(위 주석)
    S._gameLoading = true;
    Promise.all(jobs.map((p) => Promise.resolve(p).catch(() => null)))
      .then(() => { S._gameLoading = false; this.render(); });
  },

  async loadQuiz(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S.quiz !== null && !force) return;
    if (S._quizBusy) return;
    S._quizBusy = true;
    try {
      const r = await api(`/children/${c.server_id}/quiz`);
      if (r?.ok) {
        S.quiz = r.data;
        S.quizIdx = -1;            // -1 = 시작 전 화면
        S.quizPick = {};
        if (r.data.coin) S.coin = r.data.coin;
      }
    } catch (_) { /* 실패면 null 로 두어 다시 묻는다 */ }
    S._quizBusy = false;
    this.render();
  },

  quizStart() {
    if (!S.quiz?.items?.length) return;
    S.quizIdx = 0; S.quizPick = {};
    this.quizTick();
    this.render();
  },

  /* 문제당 제한 시간. **시간이 다 되면 그 문제는 못 푼 것으로 넘어간다**(기획서 §04).
     ⚠ 타이머는 화면을 통째로 다시 그리지 않는다 — 막대만 갈아끼운다.
       전체 렌더를 1초마다 돌리면 누르는 순간 버튼이 갈려 오답이 찍힌다. */
  quizTick() {
    clearInterval(QUIZ_TIMER);
    const per = S.quiz?.sec_per_q || 5;
    S.quizLeft = per;
    const started = Date.now();
    QUIZ_TIMER = setInterval(() => {
      const left = per - (Date.now() - started) / 1000;
      S.quizLeft = Math.max(0, left);
      const bar = document.querySelector(".qz-timer span");
      if (bar) bar.style.width = Math.max(0, (S.quizLeft / per) * 100) + "%";
      if (S.quizLeft <= 0) { clearInterval(QUIZ_TIMER); App.quizPick(null); }
    }, 100);
  },

  /* 한 문제를 낸다 — **그 자리에서 채점되고 답이 온다**(대표님 지시 08-08).
     ⚠ 서버가 그 문제를 잠근 뒤에 답을 주므로, 답을 보고 고쳐 낼 수 없다.
       잠금은 quiz_answer_log 의 UNIQUE 가 DB 수준에서 강제한다. */
  async quizPick(n) {
    const q = S.quiz;
    if (!q?.items?.length || S.quizIdx < 0 || S.quizFeed || S._answering) return;
    const item = q.items[S.quizIdx];
    if (!item) return;
    clearInterval(QUIZ_TIMER);
    S.quizMy = n;            // 누른 것을 그 자리에서 보여준다
    this.render();
    S._answering = true;
    const c = cur();
    try {
      const r = await api(`/children/${c.server_id}/quiz/answer`,
        { method: "POST", body: { code: item.code, picked: n } });
      if (!r?.ok) { toast(r?.error?.message || "채점이 안 됐어요"); S._answering = false; this.render(); return; }
      const d = r.data;
      S.quizFeed = { ok: d.ok, answer: d.answer, answer_text: d.answer_text,
                     picked: d.picked, hint: d.hint, last: !!d.final };
      if (d.final) {
        S.quizResult = d.final;                 // 마지막 문제였다 — 결과를 들고 있다가 보여 준다
        if (d.final.coin) S.coin = d.final.coin;
      }
    } catch (_) { toast("채점이 안 됐어요"); }
    S._answering = false;
    this.render();
    /* 아이가 답을 읽을 시간을 준다. 누르면 바로 넘어간다. */
    clearTimeout(FEED_TIMER);
    FEED_TIMER = setTimeout(() => App.quizNext(), S.quizFeed && S.quizFeed.ok ? 1100 : 2200);
  },

  /* 다음 문제로 — 피드백을 지우고 타이머를 다시 켠다 */
  quizNext() {
    clearTimeout(FEED_TIMER);
    if (!S.quizFeed) return;
    const last = S.quizFeed.last;
    S.quizFeed = null;
    S.quizMy = null;
    if (last) { S.quizIdx = -1; this.render(); return; }   // 결과 화면으로
    S.quizIdx += 1;
    this.quizTick();
    this.render();
  },

  async quizSubmit() {
    const c = cur();
    if (!c?.server_id) return;
    const answers = (S.quiz?.items || []).map((it) => ({ code: it.code, picked: S.quizPick[it.code] ?? null }));
    try {
      const r = await api(`/children/${c.server_id}/quiz`, { method: "POST", body: { answers } });
      if (!r?.ok) { toast(r?.error?.message || "채점이 안 됐어요"); this.render(); return; }
      S.quizResult = r.data;
      if (r.data.coin) S.coin = r.data.coin;
      S.quizIdx = -1;
      S.missionStars = r.data.coin?.stars ?? S.missionStars;
    } catch (_) { toast("채점이 안 됐어요"); }
    this.render();
  },

  async loadReport(force) {
    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    if (S.report && !force) return;
    /* ⚠ 아래 render() 가 이 함수를 또 부른다(리포트 화면이면). 이 줄이 없으면
       await 에 닿기도 전에 서로를 무한히 불러 스택이 터진다(2026-08-03 전수검사). */
    if (S.reportBusy) return;
    S.reportBusy = true; this.render();
    const mm = S.reportMonth || TODAY.slice(0, 6);
    const r = await api(`/children/${c.server_id}/report?month=${mm}`).catch(() => null);
    S.reportBusy = false;
    S.report = r?.ok ? r.data : { meal: {}, play: {}, subject: {} };
    this.render();
  },
  reportMove(step) {
    const mm = S.reportMonth || TODAY.slice(0, 6);
    const d = new Date(+mm.slice(0, 4), +mm.slice(4) - 1 + step, 1);
    const next = d.getFullYear() + String(d.getMonth() + 1).padStart(2, "0");
    if (next > TODAY.slice(0, 6)) return;               // 오지 않은 달은 없다
    S.reportMonth = next; S.report = null;
    this.loadReport(true);
  },

  /* 미션 고르기 — 전용 화면으로 연다. 학년대는 **자녀 학년으로 기본 선택**. */
  async missionPickOpen() {
    S.missionPick = (S.missions || []).filter((x) => x.status === "open").map((x) => x.code);
    S.pickBand = bandOf(cur());
    S.missionCatalog = S.missionCatalog || {};
    location.hash = "#missionpick"; this.render();
    await this.loadBand(S.pickBand);
  },
  /* 학년대를 바꾸면 그 밴드를 받아온다. **한 번 받은 밴드는 다시 안 받는다** —
     탭을 오갈 때마다 요청하면 느리고, 목록이 자주 바뀌지도 않는다. */
  async pickBand(b) {
    S.pickBand = b; this.render();
    await this.loadBand(b);
  },
  async loadBand(b) {
    S.missionCatalog = S.missionCatalog || {};
    if (Array.isArray(S.missionCatalog[b])) return;
    try {
      const wd = new Date().getDay();
      const season = (wd === 0 || wd === 6) ? "weekend" : "weekday";
      const r = await api(`/missions?band=${b}&season=${season}`);
      S.missionCatalog[b] = r?.ok ? (r.data.items || []) : [];
    } catch (_) { S.missionCatalog[b] = []; }
    this.render();
  },
  missionPickClose() { S.missionPick = []; S.missionNew = null; location.hash = "#mission"; this.render(); },

  // 우리 집 미션 — 한 번 만들면 계속 재사용한다. 매일 타자를 치는 게 아니다.
  missionNewOpen() { S.missionNew = { title: "", minutes: 10, verify: "instant", area: "study" }; this.render(); document.getElementById("mn-t")?.focus(); },
  /* 미션 화면에서 바로 「만들기」로 들어온 길 — 목록을 불러오되 폼을 먼저 펴 준다.
     missionPickOpen 은 await 뒤에 render 를 한 번 더 하므로, 폼 상태를 먼저 세워야 안 지워진다. */
  async missionMakeOpen() { this.missionNewOpen(); await this.missionPickOpen(); this.missionNewOpen(); },
  missionNewClose() { S.missionNew = null; this.render(); },
  async missionNewSave() {
    const d = S.missionNew || {};
    if ((d.title || "").trim().length < 2) { toast("미션 이름을 적어 주세요"); return false; }
    try {
      const r = await api("/missions", { method: "POST", body: {
        title: d.title.trim(), minutes: d.minutes, verify: d.verify, area: d.area || "study" } });
      if (!r?.ok) { toast(r?.error?.message || "만들지 못했어요"); return false; }
      S.missionNew = null;
      const code = r.data.mission.code;
      await this.missionPickReload();
      if (S.missionPick.length < 3) S.missionPick.push(code);   // 만들자마자 오늘 것에 넣어준다
      this.render();
      toast("우리 집 미션을 만들었어요");
      return true;   // ⚠ 퀵입력(§4)이 이 값을 보고 시트를 닫는다 — 실패했는데 닫으면 «넣었다»는 거짓말이 된다
    } catch (_) { toast("만들지 못했어요"); return false; }
  },
  async missionCustomDelete(code) {
    try {
      await api(`/missions/${code}`, { method: "DELETE" });
      S.missionPick = S.missionPick.filter((x) => x !== code);
      await this.missionPickReload();
      toast("지웠어요");
    } catch (_) { toast("지우지 못했어요"); }
  },
  async missionPickReload() {
    const c = cur();
    const band = (+c.grade <= 2) ? "low" : (+c.grade <= 4) ? "mid" : "high";
    const wd = new Date().getDay();
    const season = (wd === 0 || wd === 6) ? "weekend" : "weekday";
    try {
      const r = await api(`/missions?band=${band}&season=${season}`);
      S.missionCatalog = r?.ok ? (r.data.items || []) : [];
    } catch (_) { S.missionCatalog = S.missionCatalog || []; }
    this.render();
  },
  drawerOpen() { S.drawer = true; this.render(); },
  drawerClose() { S.drawer = false; this.render(); },

  /* ← 는 언제나 오늘 화면으로 (2026-08-03 «탈출 불가» 수정).
     ⚠ history.back() 을 쓰면 안 된다 — 드로어→시간표→급식 처럼 옆으로 옮겨 다녔으면
       뒤로가 또 다른 하위 화면이라 계속 미로에 있게 된다. 목적지를 하나로 못 박는다.
     ⚠ 하위 화면에서 열어 둔 것(서랍·시트)이 남아 있으면 홈에 겹쳐 뜬다 — 같이 닫는다. */
  goHome() {
    S.drawer = false; S.edit = null; S.msDetail = null; S.holdMenu = null;
    // 비회원의 «홈»은 둘러보기 화면이다 — #home 으로 보내면 라우터가 다시 튕겨 낸다
    location.hash = "#home"; this.render();
  },
  /* ── 메신저식 입력바 (§3) — 제목만 치고 엔터면 들어간다 ── */
  async ibAdd(kind) {
    const t = String(S.ibText || "").trim();
    if (!t) return;
    S.ibText = "";
    const date = kind === "sup" ? (S.day || ymdPlus(TODAY, 1)) : (S.day || TODAY);
    if (kind === "sup") {
      const keep = { ...S.supDraft };
      S.supDraft = { date, item: t, memo: "" };
      await this.supplyAdd();
      S.supDraft = keep;
    } else {
      S.evDraft = { date, title: t, memo: "", start: "", end: "", remind: "" };
      await this.evSave();
    }
    rememberTitle(kind, t);
    this.render();
    document.getElementById("ib-t")?.focus();
  },
  /* 치던 글자를 그대로 들고 «제대로 입력»으로 넘어간다 — 다시 치게 하면 안 쓴다 */
  ibToEditor(kind) {
    const t = String(S.ibText || "").trim();
    S.ibText = "";
    this.editOpen(kind);
    if (S.edit) { S.edit.title = t; S.edit.from = location.hash === "#edit" ? "#day" : location.hash; }
    this.render();
    document.getElementById("ed-t")?.focus();
  },

  /* ── 전체 화면 편집기 (§3) ────────────────────────────────────
     기본값이 다르다: **일정 = 오늘 · 준비물 = 내일**(§3). 저녁에 챙기는 건 내일 것이다. */
  editOpen(kind, id) {
    const K = String(kind || "plan");
    let base = { kind: K, id: null, title: "", memo: "", repeat: false, busy: false,
                 date: K === "sup" ? ymdPlus(TODAY, 1) : (S.day || TODAY),
                 time: "", timeOpen: false, minutes: 10, verify: "instant" };
    if (id != null) {
      if (K === "plan") {
        const e = (STUB.myEvents || []).find((x) => x.id === id);
        if (e) base = { ...base, id, title: e.title || "", memo: e.memo || "", date: e.date, time: e.start || "" };
      } else if (K === "sup") {
        const x = STUB.supplies.find((v) => v.id === id);
        if (x) base = { ...base, id, title: x.item || x.name || "", memo: x.memo || "", date: x.date };
      }
    }
    S.edit = base;
    location.hash = "#edit"; this.render();
    document.getElementById("ed-t")?.focus();
  },
  editSet(k, v) {
    if (!S.edit) return;
    S.edit[k] = v;
    if (k === "time") S.edit.timeOpen = false;
    this.render();
  },
  editTimeOpen() { if (S.edit) { S.edit.timeOpen = !S.edit.timeOpen; this.render(); } },

  /* ── 내보내기 · 가져오기 (§4) ────────────────────────────────
     ⚠ 아직 **만들지 않은 기능**이다. 눌렀을 때 «곧 열려요»라고 정직하게 말한다 —
       버튼만 있고 아무 일도 안 일어나면 사용자는 앱이 고장 났다고 읽는다. */
  backupSet(k, v) { S.backup = { ...(S.backup || {}), [k]: v }; this.render(); },
  /* TXT 내보내기 — 이 폰이 들고 있는 것을 글자 파일로 만든다(2026-08-03 지시).
     ⚠ **사진은 안 넣는다**(그건 PDF 몫이고 결제를 붙일 때 연다).
     ⚠ 서버에 다시 묻지 않는다 — 화면에 보이는 것과 파일이 달라지면 그게 더 나쁘다.
     ⚠ 파일 저장은 폰(Capacitor)과 브라우저(검수)가 길이 다르다. 둘 다 받아 준다. */
  async backupRun() {
    const b = S.backup || {};
    if (b.fmt === "pdf") return toast("PDF 내보내기는 이용권이 있어야 해요");
    const c = cur();
    const DAYS = { "1m": 31, "6m": 183, "1y": 365, all: 3650 }[b.range || "1y"];
    const from = ymdPlus(TODAY, -DAYS);
    const dLabel = (k) => `${k.slice(0, 4)}-${k.slice(4, 6)}-${k.slice(6)}`;
    const L = [];
    L.push(`아이서랍 내보내기`);
    L.push(`아이: ${c?.nickname || ""}${schoolName(c) ? ` (${schoolName(c)}${c?.grade ? ` ${c.grade}학년` : ""})` : ""}`);
    L.push(`기간: ${dLabel(from)} ~ ${dLabel(TODAY)}`);
    L.push(`만든 날: ${dLabel(TODAY)}`);
    L.push("");

    const evs = (STUB.myEvents || []).filter((e) => e.date >= from).sort((a, z) => a.date.localeCompare(z.date));
    L.push(`■ 일정 (${evs.length}건)`);
    evs.forEach((e) => L.push(`  ${dLabel(e.date)}  ${e.start || "종일"}  ${e.title}${e.memo ? ` — ${e.memo}` : ""}`));
    if (!evs.length) L.push("  (없음)");
    L.push("");

    const sup = STUB.supplies.filter((x) => x.date >= from).sort((a, z) => a.date.localeCompare(z.date));
    L.push(`■ 준비물 (${sup.length}건)`);
    sup.forEach((x) => L.push(`  ${dLabel(x.date)}  [${x.done ? "챙김" : "  "}] ${x.item || x.name || ""}`));
    if (!sup.length) L.push("  (없음)");
    L.push("");

    // 도장 — 이 폰이 본 날만 있다(marksOf 주석 참고). 없는 날을 0 으로 적지 않는다
    const marks = Object.entries(DAY_MARKS)
      .filter(([k, v]) => k.startsWith(`${S.currentChildId}|`) && k.slice(k.indexOf("|") + 1) >= from && (v.stamp || v.meal))
      .map(([k, v]) => [k.slice(k.indexOf("|") + 1), v]).sort();
    L.push(`■ 도장 · 급식 평가 (${marks.length}일)`);
    marks.forEach(([d, v]) => L.push(`  ${dLabel(d)}  ${v.stamp ? `도장 ${v.stamp}${v.of ? `/${v.of}` : ""}개` : ""}${v.meal ? `  급식 ★${v.meal}` : ""}`));
    if (!marks.length) L.push("  (없음)");
    L.push("");

    const recs = (STUB.records || []);
    L.push(`■ 서랍 기록 (${recs.length}건 · 사진은 PDF 에서)`);
    recs.forEach((r) => L.push(`  ${r.period?.label || ""}  ${CATEGORY_KO[r.category] || ""}  ${r.title}`));
    if (!recs.length) L.push("  (없음)");

    const text = L.join("\n");
    const name = `아이서랍_${c?.nickname || "기록"}_${TODAY}.txt`;
    try {
      const FS = window.Capacitor?.Plugins?.Filesystem;
      if (FS?.writeFile) {
        await FS.writeFile({ path: name, data: text, directory: "DOCUMENTS", encoding: "utf8" });
        return toast(`${name} — 폰의 «문서»에 저장했어요`);
      }
      // 브라우저(검수) — 내려받기
      const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
      const a = document.createElement("a");
      a.href = url; a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 3000);
      toast(`${name} 을(를) 내려받았어요`);
    } catch (e) {
      console.error("[내보내기 실패]", e);
      toast("파일을 만들지 못했어요");
    }
  },
  backupImport() { toast("가져오기는 곧 열려요"); },

  /* 시간 옵션 (§4) — 요일 시작·날짜 형식·시간 형식 */
  timeOpt(k, v) {
    S.timeOpt = { ...(S.timeOpt || {}), [k]: v };
    saveHome(); this.render();
  },

  /* ── 테마 화면 (§4·§6) — 고르는 것과 «쓰기»를 나눈다 ── */
  themePick(k, v) {
    const cur0 = { art: S.art, theme: DARK_THEMES.includes(S.theme) ? "dark" : "light" };
    S.themePick = { ...cur0, ...(S.themePick || {}), [k]: v };
    this.render();
  },
  themeLater() { S.themeFirst = false; S.themePick = null; location.hash = "#home"; this.render(); },
  themeApply() {
    const p = S.themePick; if (!p) return;
    if (p.theme) this.setTheme(p.theme);
    if (p.art) this.setArt(p.art);
    S.themePick = null; S.themeFirst = false;
    toast("테마를 바꿨어요");
    location.hash = "#home"; this.render();
  },
  editMonth(d) {
    if (!S.edit) return;
    const ym = S.edit.month || S.edit.date.slice(0, 6);
    const y = +ym.slice(0, 4), m = +ym.slice(4, 6) + d;
    const nd = new Date(y, m - 1, 1);
    S.edit.month = `${nd.getFullYear()}${String(nd.getMonth() + 1).padStart(2, "0")}`;
    this.render();
  },
  editCancel() {
    const back = S.edit?.from || "#day";
    S.edit = null; location.hash = back; this.render();
  },
  async editSave() {
    const e = S.edit;
    if (!e || e.busy) return;
    const title = String(e.title || "").trim();
    if (!title) return;
    e.busy = true; this.render();
    try {
      if (e.kind === "plan") {
        S.evDraft = { id: e.id || undefined, date: e.date, title, memo: e.memo || "",
                      start: e.time || "", end: "", remind: "" };
        await this.evSave();
        /* 「매주 이 요일」 — 다음 7주치를 같은 요일에 넣는다.
           ⚠ 서버에 반복 규칙이 없다. 그래서 **실제 항목을 만들어 둔다** —
             «반복이라고 말만 하고 안 생기는 것»보다 낫다. 지울 때는 하나씩 지워야 한다. */
        if (e.repeat && !e.id) {
          for (let i = 1; i <= 7; i++) {
            S.evDraft = { date: ymdPlus(e.date, i * 7), title, memo: e.memo || "",
                          start: e.time || "", end: "", remind: "" };
            await this.evSave();
          }
          toast(`${title} · 다음 7주까지 넣었어요`);
        }
      } else if (e.kind === "sup") {
        if (e.id) {
          const x = STUB.supplies.find((v) => v.id === e.id);
          if (x) { x.item = title; x.memo = e.memo || ""; x.date = e.date; }
          saveLifeCache(cur());
        } else {
          const keep = { ...S.supDraft };
          S.supDraft = { date: e.date, item: title, memo: e.memo || "" };
          await this.supplyAdd();
          if (e.repeat) {
            for (let i = 1; i <= 7; i++) {
              S.supDraft = { date: ymdPlus(e.date, i * 7), item: title, memo: e.memo || "" };
              await this.supplyAdd();
            }
          }
          S.supDraft = keep;
        }
      } else {
        S.missionNew = { title, minutes: e.minutes, verify: e.verify, area: "study" };
        const ok = await this.missionNewSave();
        if (!ok) { S.missionNew = null; e.busy = false; this.render(); return; }
      }
      rememberTitle(e.kind, title);
      const back = e.from || "#day";
      S.edit = null; location.hash = back; this.render();
    } catch (_) {
      if (S.edit) S.edit.busy = false;
      this.render(); toast("넣지 못했어요");
    }
  },
  editDelete() {
    const e = S.edit;
    if (!e?.id) return;
    // 지우기는 **확인을 받는다** — 되돌릴 수 없는 것에만 창을 띄운다(§3 예외)
    this.holdMenuOpen?.();
    if (e.kind === "plan") { S.evDraft = { id: e.id, title: e.title }; this.evDelete(); }
    else if (e.kind === "sup") { this.supplyDelete?.(e.id); }
    const back = e.from || "#day";
    S.edit = null; location.hash = back; this.render();
  },

  /* 일간 화면 열기 (§2). 날짜를 들고 간다 — 어느 날을 보는지가 이 화면의 전부다. */
  dayOpen(ymd) {
    S.day = /^\d{8}$/.test(String(ymd || "")) ? String(ymd) : TODAY;
    location.hash = "#day"; this.render();
  },
  dayMove(delta) {
    S.day = ymdPlus(S.day || TODAY, delta);
    this.render();
  },

  /* ── 첫 실행 설문 (§5) — 물은 것은 **반드시 앱에 쓰인다.** 그 외는 묻지 않는다.
     ① 호칭 → 앱 전체 말투 · 나중에 자녀 앱 «엄마한테 보내기» 에도 쓴다
     ② 자녀 수 → 끝나면 곧바로 등록으로 보낸다
     ③ 뭐가 제일 필요한가 → 코치마크 첫 장을 그쪽으로 돌린다 */
  /* 고르기와 «계속»을 나눈다(§5) — 고르자마자 넘어가면 잘못 눌렀을 때 되돌릴 틈이 없다 */
  obSet(key, val) {
    S.onboard = { ...(S.onboard || {}), [key]: val };
    saveHome(); this.render();
  },
  obNext() {
    if (S.introIdx >= OB_Q.length - 1) return this.introToNotify();
    S.introIdx = (S.introIdx || 0) + 1;
    this.render();
  },
  introToSurvey() { S.introStep = "survey"; S.introIdx = 0; this.render(); },
  introToNotify() { S.introStep = "notify"; this.render(); },
  /* 알림 권한 — 네이티브 창은 **한 번뿐**이다. 그래서 이유를 먼저 말하고 나서 띄운다.
     웹(검수)에서는 권한 API 가 없으니 조용히 넘어간다. */
  async introAskPush() {
    try {
      const P = window.Capacitor?.Plugins?.PushNotifications;
      if (P?.requestPermissions) await P.requestPermissions();
      else if (window.Notification?.requestPermission) await Notification.requestPermission();
    } catch (e) {}
    this.introDone();
  },
  introNext() { S.introIdx = (S.introIdx || 0) + 1; this.render(); },   // 소개 슬라이드 넘기기
  introBack() { if (S.introIdx > 0) { S.introIdx--; this.render(); } },
  /* 설문이 끝나면 **로그인 화면이 아니라 앱 안으로** 들여보낸다(2026-08-03 지시).
     사기 전에 안을 보게 하는 것이 목적이라, 여기서 로그인을 세우면 그 자리에서 다 나간다. */
  introDone() {
    try { localStorage.setItem("eduthink.introSeen", "1"); } catch (e) {}
    S.introIdx = 0; S.introStep = null;
    location.hash = "#home"; this.render();
  },

  /* ── 코치마크 — 새 화면을 한 번만 짚어 준다.
     ⚠ 홈이 **그려진 다음에** 열어야 한다. 구멍 자리를 실제 요소에서 재기 때문에,
       그리기 전에 열면 요소가 없어서 구멍 없이 설명만 뜬다. */
  coachStart() {
    if (S.coach !== null) return;
    S.coach = 0;
    requestAnimationFrame(() => this.render());
  },
  coachNext() {
    if (S.coach === null) return;
    if (S.coach >= COACH.length - 1) return this.coachDone();
    S.coach += 1; this.render();
  },
  coachDone() {
    S.coach = null;
    try { localStorage.setItem(COACH_KEY, "1"); } catch (e) {}
    this.render();
  },

  /* ── ＋ 퀵입력 (§4) — 기존 저장 길(일정·준비물·미션)을 그대로 탄다.
     여기서 새 저장 경로를 만들면 두 곳이 갈라져서 한쪽만 고치는 사고가 난다. */

  // ── 테마 세트 (§6) — 라이트/다크와 따로 논다. 둘을 섞으면 «어두운 벚꽃»을 못 만든다
  setArt(k) {
    if (!ART_SETS.some((a) => a.key === k)) return;
    S.art = k;
    document.documentElement.setAttribute("data-art", k);
    saveHome(); this.render();
  },
  // 오늘 화면 줄 켜기/끄기 (§2)
  todayToggle(k) {
    if (!(k in S.todayCards)) return;
    S.todayCards[k] = !S.todayCards[k];
    saveHome(); this.render();
  },
  todayReset() {
    Object.keys(S.todayCards).forEach((k) => { S.todayCards[k] = true; });
    saveHome(); this.render(); toast("모두 켰어요");
  },
  msOpen(id) { S.msDetail = id; location.hash = "#missionone"; this.render(); hydrateImages(); },
  msClose() { S.msDetail = null; S.keepShot = null; location.hash = "#mission"; this.render(); },

  /* ── «서랍에 보관» (§2) — 사진 확인 시트에서 도장과 나란히 선다.
     여기서 바로 올리지 않고 **찍기로 예약만** 한다. 도장을 안 찍고 「다시 해볼까?」로 돌려보낼 수도
     있는데, 미리 올려 두면 안 받아준 사진이 서랍에 남는다. */
  keepShot(id) { S.keepShot = S.keepShot === id ? null : id; this.render(); },
  /* 도장이 찍힌 뒤에 부른다. 기록 저장은 **업로드 화면과 같은 길**(_bgUpload)을 탄다 —
     여기에 따로 만들면 한쪽만 고치는 사고가 난다.
     ⚠ 사진은 이미 받아 둔 blob 을 쓴다(IMG_READY). 아직 안 받았으면 그때 받아온다 —
       도장을 찍는 순간 서버에서 그 미션 사진이 내려갈 수 있어서, 늦게 가면 빈손이 된다. */
  async _keepShotSave(m) {
    const c = cur();
    if (!m || !c) return;
    const path = `/api/v1/missions/${m.id}/photo`;
    try {
      const web = IMG_READY.get(path) || await fetchImage(path);
      if (!web) return;
      const now = new Date();
      await this._bgUpload({
        shots: [{ web }], child: c,
        meta: { category: "activity", school_year: String(c.grade || ""),
                semester: String(now.getMonth() + 1 < 8 ? 1 : 2),
                title: (m.title || "미션 사진").slice(0, 30) },
      });
      toast("서랍에 넣었어요");
    } catch (_) { toast("서랍에 못 넣었어요 — 미션 사진에서 다시 해주세요"); }
  },
  /* ⚠ 하루에 주는 것은 **세 개까지**다(서버 DAY_PICK). 그보다 많이 담아도 서버가 잘라내므로,
     담는 자리에서 막고 왜 막았는지 말해 준다 — 잘려 나간 걸 나중에 알면 «저장이 안 됐다»로 읽힌다. */
  missionToggle(code) {
    const i = S.missionPick.indexOf(code);
    if (i >= 0) S.missionPick.splice(i, 1);
    else if (S.missionPick.length >= 3) return toast("하루에 세 개까지예요");
    else S.missionPick.push(code);
    this.render();
  },
  async missionSave() {
    const c = cur();
    if (!S.missionPick.length) return toast("미션을 골라 주세요");
    try {
      const r = await api(`/children/${c.server_id}/missions`, { method: "PUT", body: { codes: S.missionPick } });
      if (!r?.ok) return toast(r?.error?.fields?.codes || r?.error?.message || "저장하지 못했어요");
      S.missionPick = [];
      await this.loadMissions(true);
      location.hash = "#mission"; this.render();
      toast("오늘 미션을 바꿨어요");
    } catch (_) { toast("저장하지 못했어요"); }
  },

  // ── 고객센터 ──────────────────────────────────────────────
  faqQuery(v) { S.faqQ = v; renderKeepFocus(); },
  faqToggle(k) { S.faqOpen = S.faqOpen === k ? null : k; this.render(); },
  faqSecToggle(k) { S.faqSec = S.faqSec === k ? null : k; S.faqOpen = null; this.render(); },
  askSet(k, v) { S.askDraft = { ...S.askDraft, [k]: v }; },   // 다시 그리지 않는다 — 타이핑 중 커서가 튄다

  /* 문의 목록은 고객센터에 들어올 때 한 번 받아온다. 홈에서 매번 받아오면
     쓰지도 않을 요청이 앱 시작마다 하나 늘어난다(체감속도 작업의 취지와 어긋난다). */
  /* ⚠ 미션에서 겪은 것과 같은 함정(2026-08-02) — 통신이 잠깐 끊긴 것을 «없음»으로 못 박으면
     다시 안 부른다. **서버가 답한 「없음」과 못 물어본 것은 다르다.** */
  async loadInquiries(force) {
    if (S.inquiries !== null && !force) return;
    if (!TOKENS.access) return;                 // 로그인 전이면 물을 수 없다 — null 로 둔다
    try {
      const r = await api("/inquiries");
      if (r?.ok) S.inquiries = r.data.items || [];
      else if (r?.error?.code === "AUTH_REQUIRED") S.inquiries = [];
    } catch (_) { /* 통신 문제 — 다음에 다시 묻는다. FAQ는 어차피 읽힌다 */ }
    this.render();
  },

  async askSend() {
    const d = S.askDraft || {};
    const title = (d.title || "").trim();
    const body = (d.body || "").trim();
    if (title.length < 2) return toast("제목을 적어 주세요");
    if (body.length < 5) return toast("문의 내용을 조금만 더 적어 주세요");
    if (S.askBusy) return;
    S.askBusy = true; this.render();
    const c = cur();
    try {
      const r = await api("/inquiries", { method: "POST", body: {
        category: d.category || "other", title, body,
        contact_email: (d.contact_email || "").trim() || undefined,
        child_id: c?.server_id ?? undefined,
        meta: { app: APP_VERSION, device: deviceLabel(), school: c?.school?.name || null },
      } });
      if (!r?.ok) throw new Error(r?.error?.message || "");
      S.askDraft = { category: "data", title: "", body: "", contact_email: "" };
      S.inquiries = null;                 // 다음에 목록을 다시 받아온다
      S.askBusy = false;
      location.hash = "#asks";
      this.loadInquiries();
      toast("문의를 보냈어요");
    } catch (e) {
      S.askBusy = false; this.render();
      toast(e.message || "보내지 못했어요. 잠시 후 다시 시도해 주세요");
    }
  },

  /* 문의 하나를 펼친다. 답이 달린 것을 처음 열면 서버가 읽음으로 표시한다(seen_at) —
     그래야 「답변 왔어요」 배지가 사라진다. 목록에 본문이 없으므로 상세를 받아 채운다. */
  async askOpenOne(id) {
    if (S.askOpen === id) { S.askOpen = null; return this.render(); }
    S.askOpen = id; this.render();
    try {
      const r = await api(`/inquiries/${id}`);
      if (!r?.ok) return;
      const it = r.data.inquiry;
      S.inquiries = (S.inquiries || []).map((x) => (x.id === id ? { ...x, ...it } : x));
      this.render();
    } catch (_) { /* 못 받아와도 목록에 있는 만큼은 보여준다 */ }
  },
  tlLevel(i) { S.tlLevel = i; S.tlOpen = null; this.render(); },
  // 자녀 전환 — 기존 칩과 같은 동작
  childMenu() { location.hash = "#switch"; },   // 다른 화면의 자녀 칩과 같은 곳으로
  /* 빈 학기 칸에서 바로 올리기 — 그 학년·학기를 미리 정해두고 카메라를 연다.
     아무 데서나 올린 뒤 학년을 고르게 하면, 아까처럼 안 고르고 막힌다. */
  addRecordAt(grade, sem) {
    S.uploadGrade = String(grade); S.uploadSem = String(sem);
    this.shoot();
  },
  /* 자녀 사진 (2026-07-27) — 카메라·앨범에서 골라 480px로 줄여 올린다.
     썸네일은 안 만든다. 프로필은 원래 작게 쓰므로 한 장이면 충분하다. */
  /* ⚠ **아직 등록하지 않은 아이도 사진을 고를 수 있어야 한다**(2026-07-27 사장님 지적).
     예전엔 server_id 가 없으면 「먼저 등록하세요」 토스트만 띄우고 끝냈다 —
     그런데 사진을 넣는 자리가 바로 그 **등록 화면**이라, 신규 등록에선 아무 일도 안 일어났다.
     이제는 **일단 들고 있다가**(photoBlob) 자녀가 서버에 만들어진 직후에 올린다. */
  async childPhotoPick() {
    const Camera = window.Capacitor?.Plugins?.Camera;
    if (!Camera) return toast("앱(폰)에서 열면 카메라·앨범이 동작해요");
    let thumb;
    try {
      const photo = await Camera.getPhoto({
        resultType: "uri", quality: 85, width: 960, height: 960, correctOrientation: true,
        promptLabelHeader: "아이 사진", promptLabelPhoto: "앨범에서 고르기", promptLabelPicture: "카메라로 찍기",
      });
      ({ thumb } = await prepShot(photo.webPath));   // 480px 한 장만 쓴다
    } catch (e) {
      if (!/cancel/i.test(String(e?.message || e))) toast("사진을 넣지 못했어요");
      return;
    }
    // 화면엔 바로 보여준다 — 올라가기를 기다리게 하지 않는다
    if (S.childDraft.photoPreview) URL.revokeObjectURL(S.childDraft.photoPreview);
    S.childDraft.photoBlob = thumb;
    S.childDraft.photoPreview = URL.createObjectURL(thumb);
    this.render();

    const id = S.childDraft?.server_id;
    if (!id) return toast("등록을 마치면 사진도 같이 올라가요");   // 아직 서버에 없는 아이 — childSaveServer 가 마저 올린다
    toast("사진을 올리는 중이에요");
    const ok = await this.childPhotoUpload(id, thumb);
    if (ok) { S.childDraft.photo = ok; this.render(); toast("사진을 넣었어요"); }
  },
  /* 실제 업로드 한 곳 — 등록 직후(childSaveServer)와 수정 화면 둘 다 여기로 들어온다.
     성공하면 사진 주소를 돌려주고 화면 자녀(STUB)에도 반영한다. */
  async childPhotoUpload(serverId, blob) {
    const fd = new FormData();
    fd.append("file", blob, "child.jpg");
    const r = await api(`/children/${serverId}/photo`, { method: "POST", form: fd }).catch(() => null);
    if (!r?.ok) { toast(r?.error?.message || "사진을 올리지 못했어요"); return null; }
    const c = STUB.children.find((x) => x.server_id === serverId);
    if (c) { c.photo = r.data.photo; c.photoLocal = null; }
    IMG_CACHE.delete?.(r.data.photo);
    return r.data.photo;
  },
  async childPhotoClear() {
    if (S.childDraft.photoPreview) URL.revokeObjectURL(S.childDraft.photoPreview);
    S.childDraft.photoBlob = null; S.childDraft.photoPreview = null;
    const id = S.childDraft?.server_id;
    if (!id || !S.childDraft.photo) { S.childDraft.photo = null; return this.render(); }
    const r = await api(`/children/${id}/photo`, { method: "DELETE" });
    if (!r?.ok) return toast(r?.error?.message || "사진을 빼지 못했어요");
    S.childDraft.photo = null;
    const c = STUB.children.find((x) => x.server_id === id);
    if (c) { c.photo = null; c.photoLocal = null; }
    this.render(); toast("사진을 뺐어요");
  },
  pickPlan(m) { S.planSel = m; this.render(); },
  /* 요금표는 **자녀마다 다르다**(둘째부터 싸다) → 이용권 화면에 들어올 때 그 자녀 기준으로 받아온다.
     못 받아오면 STUB.plans(정가)로 그린다 — 빈 화면보다는 정가가 낫다. */
  async loadPlans() {
    const c = cur();
    if (!c?.server_id || !TOKENS.access) return;
    try {
      const r = await api(`/plans?child_id=${c.server_id}`);
      if (!r?.ok) return;
      S.planList = r.data.items || null;
      S.planSeat = r.data.seat || 1;
      this.render();
    } catch (_) { /* 정가 폴백 */ }
  },
  // ── 일정 다이어리 ─────────────────────────────────────
  /* 날짜 고르기 — **끄지 않는다.** 상세가 팝업이던 시절엔 다시 누르면 닫혔지만,
     이제 상세는 달력 아래에 늘 붙어 있다. 여기서 null로 되돌리면 «오늘»로 튕겨서 오히려 헷갈린다. */
  /* 달력 칸을 누르면 **아래 목록이 그 날짜로 옮겨간다**(§2). 화면을 바꾸지 않는다 —
     들어가는 건 목록 줄을 누를 때다. 두 동작이 갈려 있어야 «훑기»와 «들어가기»가 안 섞인다. */
  calPick(d) {
    S.calPick = d; S.evDraft = null; this.render();
    requestAnimationFrame(() => {
      const el = document.getElementById("ag-" + d);
      if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
    });
  },
  /* 날짜를 꾹 — 그 날짜로 새 일정. 탭은 선택만(다른 날짜 지정이 돼야 한다, 2026-08-03) */
  holdDay(e, key) {
    if (!e) e = window.event;
    S.calPick = key;
    holdDirect(e, () => this.evStart(key));
  },
  calFold() { S.calFold = !S.calFold; saveHome(); this.render(); },

  /* 위젯에 띄울 줄 고르기 (2026-07-27) — 홈 메뉴 편집과 같은 조작법.
     끄면 목록에서 빠지고, 켜면 **맨 아래**에 붙는다(원래 자리로 돌아가면 순서를 바꾼 뜻이 사라진다). */
  widgetToggle(key) {
    const i = S.widgetRows.indexOf(key);
    if (i >= 0) S.widgetRows.splice(i, 1);
    else if (S.widgetRows.length >= WIDGET_MAX) return toast(`위젯에는 ${WIDGET_MAX}줄까지 넣을 수 있어요`);
    else S.widgetRows.push(key);
    saveHome(); WIDGET_LAST = ""; this.render();   // 값이 같아도 다시 밀어야 위젯이 바뀐다
  },
  widgetMove(key, step) {
    const i = S.widgetRows.indexOf(key);
    const j = i + step;
    if (i < 0 || j < 0 || j >= S.widgetRows.length) return;
    [S.widgetRows[i], S.widgetRows[j]] = [S.widgetRows[j], S.widgetRows[i]];
    saveHome(); WIDGET_LAST = ""; this.render();
  },
  // 다른 달을 보다가 오늘로 한 번에 — 표준 캘린더가 다 가진 버튼
  calToday() { S.calMonth = TODAY.slice(0, 6); S.calPick = TODAY; this.render(); },
  calMove(step) {
    let y = +S.calMonth.slice(0, 4), m = +S.calMonth.slice(4, 6) + step;
    if (m < 1) { m = 12; y--; } else if (m > 12) { m = 1; y++; }
    S.calMonth = `${y}${String(m).padStart(2, "0")}`;
    S.calPick = null; S.evDraft = null;
    this.render();
  },
  evStart(date) { S.evDraft = { date, title: "", memo: "", start: "16:00", end: "17:00", remind: "" }; this.render(); document.getElementById("ev-t")?.focus(); },
  /* 고른 «몇 분 전»을 실제 시각(ISO)으로 바꾼다 — 서버 크론이 이 시각을 보고 알림을 쏜다.
     이미 지난 시각이면 보내지 않는다(넣자마자 울리는 알림은 사고다). */
  _remindAtOf(d) {
    if (!d?.remind) return null;
    const [Y, M, D] = [d.date.slice(0, 4), d.date.slice(4, 6), d.date.slice(6)].map(Number);
    let t;
    if (d.remind === "prev") t = new Date(Y, M - 1, D - 1, 20, 0, 0);
    else {
      const [hh, mm] = String(d.start || "00:00").split(":").map(Number);
      t = new Date(Y, M - 1, D, hh, mm - (+d.remind || 0), 0);
    }
    return t.getTime() > Date.now() ? t.toISOString() : null;
  },
  // 이미 있는 일정을 눌렀을 때 — 같은 창을 값이 채워진 채로 연다(id가 있으면 수정 모드)
  /* 일정 고치기 — **전체 화면 편집기**로 보낸다(2026-08-03 §3).
     예전엔 가운데 모달을 띄웠는데, 날짜를 바꾸려면 시스템 피커가 또 떠서 창이 두 겹이 됐다. */
  evEdit(id) {
    const from = location.hash || "#calendar";
    this.editOpen("plan", id);
    if (S.edit) S.edit.from = from;
    this.render();
  },
  evDelete() {
    const d = S.evDraft;
    const i = STUB.myEvents.findIndex((x) => x.id === d.id);
    const gone = i >= 0 ? STUB.myEvents[i] : null;
    if (i >= 0) STUB.myEvents.splice(i, 1);
    if (TOKENS.access && gone?.server_id) api(`/events/${gone.server_id}`, { method: "DELETE" });
    S.evDraft = null; this.render();
    toast(`「${d.title}」 일정을 지웠어요`);   // 내 일정은 가벼운 값이라 재인증 없이 바로(계약 §3.4)
  },
  evCancel() { S.evDraft = null; this.render(); },
  evSave() {
    const e = S.evDraft;
    if (!e.title.trim()) return toast("일정 이름을 넣어주세요");
    const remindAt = this._remindAtOf(e);
    const 알림말 = { "": "", "0": " · 시작할 때 알림", "10": " · 10분 전 알림", "30": " · 30분 전 알림",
      "60": " · 1시간 전 알림", prev: " · 전날 저녁 알림" }[e.remind || ""] || "";
    if (e.id) {                                   // 수정
      const t = STUB.myEvents.find((x) => x.id === e.id);
      if (t) Object.assign(t, { title: e.title.trim(), memo: (e.memo || "").trim(), start: e.start, end: e.end, remind: e.remind || "" });
      if (TOKENS.access && t?.server_id) {
        api(`/events/${t.server_id}`, { method: "PATCH", body: {
          title: e.title.trim(), memo: e.memo, start: e.start, remind_at: remindAt,
        } });
      }
      S.evDraft = null; this.render();
      return toast(`「${e.title.trim()}」 일정을 고쳤어요${알림말}`);
    }
    const nid = Math.max(0, ...STUB.myEvents.map((x) => x.id)) + 1;
    STUB.myEvents.push({ id: nid,
      date: e.date, title: e.title.trim(), memo: e.memo.trim(), start: e.start, end: e.end, remind: e.remind || "" });
    const c1 = cur();
    if (TOKENS.access && c1?.server_id) {
      api(`/children/${c1.server_id}/events`, { method: "POST", body: {
        date: e.date, title: e.title.trim(), memo: e.memo, start: e.start, remind_at: remindAt,
      } }).then((r) => { if (r?.ok) { const t = STUB.myEvents.find((x) => x.id === nid); if (t) t.server_id = r.data.id; } });
    }
    S.evDraft = null; this.render();
    // 알림을 골랐는데 그 시각이 이미 지났으면 말해준다 — 조용히 안 오면 «고장»으로 읽힌다
    if (e.remind && !remindAt) toast("알림 시각이 이미 지나서 알림은 안 걸었어요");
    else toast(`${+e.date.slice(4, 6)}/${+e.date.slice(6)} ${e.start} 일정을 넣었어요${알림말}`);
  },

  /* ── 준비물 (2026-07-27) ──────────────────────────────
     체크는 «화면부터 바꾸고 서버로 보낸다» — 체크박스가 손가락을 따라오지 않으면
     사용자는 눌린 건지 몰라서 두 번 누른다. 실패하면 되돌리고 말해준다.
     삭제는 반대로 «서버가 먼저» — 지워진 줄 알았는데 살아 있는 게 제일 나쁘다(기록 삭제와 같은 규칙). */
  supDate(v) { S.supDraft.date = String(v || "").replace(/-/g, ""); },
  // 다이어리에서 그 날짜를 들고 준비물 화면으로 넘어간다 — 날짜를 다시 고르게 하지 않는다
  supFrom(ymd) { S.supDraft = { date: ymd, item: "", memo: "" }; S.calPick = null; location.hash = "#supplies"; },

  /* 자녀가 넣는 준비물 (2026-07-28) — 부모용 supplyAdd 와 나누는 이유:
     ① 날짜가 **내일로 고정**이다(아이는 날짜를 안 고른다)
     ② 넣고 나서 **엄마에게 알림**을 보낸다. 이게 이 기능의 핵심이다 —
        아이가 적어도 엄마가 모르면 아무 소용이 없다. */
  async childSupplyAdd() {
    const item = (S.supDraft.item || "").trim();
    if (!item) return toast("준비물 이름을 넣어주세요");
    const c = cur();
    const date = ymdPlus(TODAY, 1);
    const nid = Math.min(0, ...STUB.supplies.map((x) => x.id)) - 1;
    STUB.supplies.push({ id: nid, date, item, memo: "", done: false, by: "child" });
    S.supDraft.item = "";
    this.render();
    document.getElementById("csup")?.focus();
    toast(`「${item}」 넣었어요`);

    if (!TOKENS.access || !c?.server_id) return;
    const r = await api(`/children/${c.server_id}/supplies`, { method: "POST", body: { date, item, memo: "" } });
    const got = r?.ok && r.data.items && r.data.items[0];
    if (!got) {
      STUB.supplies = STUB.supplies.filter((x) => x.id !== nid);
      this.render(); return toast(r?.error?.message || "저장하지 못했어요. 다시 넣어주세요");
    }
    const t = STUB.supplies.find((x) => x.id === nid);
    if (t) { t.server_id = got.id; t.id = got.id; }
    // 엄마에게 알린다 — 대화로 보내면 부모 홈의 안 읽음 배지가 바로 뜬다
    await api(`/children/${c.server_id}/messages`, { method: "POST", body: { sender: "child", text: `내일 준비물에 「${item}」 넣었어요` } }).catch(() => null);
    this.render();
  },

  supRepeatToggle() { S.supDraft.repeat = !S.supDraft.repeat; this.render(); },
  /* 항목 꾹 — 날짜·반복·삭제가 다 여기로 모였다(2026-08-03 간단판) */
  holdSupply(e, id) {
    if (typeof e === "number") { id = e; e = window.event; }
    const s = STUB.supplies.find((x) => x.id === id);
    if (!s || !e) return;
    holdStart(e, s.item, [
      { label: "내일로", icon: "ti-calendar", run: () => App.supplyMove(id, ymdPlus(TODAY, 1)) },
      { label: "날짜 고르기", icon: "ti-calendar", run: () => App.supplyPickDate(id) },
      { label: "매주 × 4주 만들기", icon: "ti-arrow-back-up", run: () => App.supplyRepeatItem(id) },
      { label: "지우기", icon: "ti-trash", danger: true, run: () => App.supplyDelete(id) },
    ]);
  },
  async supplyMove(id, date) {
    const s = STUB.supplies.find((x) => x.id === id);
    if (!s) return;
    s.date = date; this.render();
    toast(`${+date.slice(4, 6)}/${+date.slice(6)}로 옮겼어요`);
    const c = cur();
    if (TOKENS.access && c?.server_id && s.server_id)
      api(`/supplies/${s.server_id}`, { method: "PATCH", body: { date } }).catch(() => {});
  },
  supplyPickDate(id) {
    /* 숨은 date 입력을 만들어 네이티브 달력을 연다 — 화면에 상시 노출하지 않으려고 */
    const inp = document.createElement("input");
    inp.type = "date"; inp.style.cssText = "position:fixed;opacity:0;pointer-events:none";
    const s = STUB.supplies.find((x) => x.id === id);
    inp.value = s ? ymdDash(s.date) : "";
    document.body.appendChild(inp);
    inp.onchange = () => { const v = inp.value.replace(/-/g, ""); if (/^\d{8}$/.test(v)) this.supplyMove(id, v); inp.remove(); };
    inp.showPicker ? inp.showPicker() : inp.click();
  },
  async supplyRepeatItem(id) {
    const s = STUB.supplies.find((x) => x.id === id);
    if (!s) return;
    const keep = { ...S.supDraft };
    S.supDraft = { date: s.date, item: s.item, memo: s.memo || "" };
    await this.supplyRepeat(4);
    S.supDraft = keep;
  },
  async supplyAdd() {
    const d = S.supDraft;
    if (!/^\d{8}$/.test(d.date)) d.date = ymdPlus(TODAY, 1);   // 기본 = 내일(간단판) — 날짜 칸이 사라졌다
    const item = (d.item || "").trim();
    if (!item) return toast("준비물 이름을 넣어주세요");
    /* 매주 반복이 켜져 있으면 — 추가 한 번이 4주치. 넣고 나면 끈다(다음 것까지 4주로 가는 사고 방지) */
    if (d.repeat) { d.repeat = false; return this.supplyRepeat(4); }
    const memo = (d.memo || "").trim();
    /* ⚠️ 임시 id는 **음수**로 만든다. 양수로 매기면 서버가 돌려준 id와 부딪힌다 —
       화면에 id가 같은 줄이 둘 생기고, 체크·삭제가 엉뚱한 줄을 건드린다(2026-07-27 실측). */
    const nid = Math.min(0, ...STUB.supplies.map((x) => x.id)) - 1;
    STUB.supplies.push({ id: nid, date: d.date, item, memo, done: false });
    S.supDraft = { date: d.date, item: "", memo: "" };   // 날짜는 남긴다 — 보통 같은 날 것을 연달아 적는다
    this.render();
    document.getElementById("sup-i")?.focus();
    toast(`${+d.date.slice(4, 6)}/${+d.date.slice(6)} 「${item}」 넣었어요`);

    const c = cur();
    if (!TOKENS.access || !c?.server_id) return;
    const r = await api(`/children/${c.server_id}/supplies`, { method: "POST", body: { date: d.date, item, memo } });
    const got = r?.ok && r.data.items && r.data.items[0];
    if (got) { const t = STUB.supplies.find((x) => x.id === nid); if (t) { t.server_id = got.id; t.id = got.id; } this.render(); }
    else { STUB.supplies = STUB.supplies.filter((x) => x.id !== nid); this.render(); toast(r?.error?.message || "저장하지 못했어요. 다시 넣어주세요"); }
  },

  // 같은 요일로 n주치. 이미 있는 날짜는 건너뛴다(두 번 눌러도 안 겹치게).
  async supplyRepeat(n) {
    const d = S.supDraft;
    const item = (d.item || "").trim();
    if (!/^\d{8}$/.test(d.date)) return toast("날짜를 골라주세요");
    if (!item) return toast("반복할 준비물 이름을 먼저 넣어주세요");
    const memo = (d.memo || "").trim();
    const dates = [];
    for (let i = 0; i < n; i++) {
      const day = ymdPlus(d.date, i * 7);
      if (!STUB.supplies.some((s) => s.date === day && s.item === item)) dates.push(day);
    }
    if (!dates.length) return toast("이미 다 넣어져 있어요");

    const c = cur();
    if (TOKENS.access && c?.server_id) {
      const r = await api(`/children/${c.server_id}/supplies`, {
        method: "POST", body: { items: dates.map((date) => ({ date, item, memo })) },
      });
      if (!r?.ok) return toast(r?.error?.message || "저장하지 못했어요. 잠시 후 다시 해주세요");
      r.data.items.forEach((s) => STUB.supplies.push({ id: s.id, server_id: s.id, date: s.date, item: s.item, memo: s.memo || "", done: false }));
    } else {
      let nid = Math.min(0, ...STUB.supplies.map((x) => x.id));
      dates.forEach((date) => STUB.supplies.push({ id: --nid, date, item, memo, done: false }));
    }
    S.supDraft = { date: d.date, item: "", memo: "" };
    this.render();
    toast(`「${item}」 ${dates.length}주치를 넣었어요`);
  },

  async supplyToggle(id) {
    const s = STUB.supplies.find((x) => x.id === id);
    if (!s) return;
    s.done = !s.done;
    this.render();
    if (!TOKENS.access || !s.server_id) return;
    const r = await api(`/supplies/${s.server_id}`, { method: "PATCH", body: { done: s.done } });
    if (!r?.ok) { s.done = !s.done; this.render(); toast(r?.error?.message || "바꾸지 못했어요"); }
  },

  async supplyDelete(id) {
    const s = STUB.supplies.find((x) => x.id === id);
    if (!s) return;
    if (TOKENS.access && s.server_id) {
      const r = await api(`/supplies/${s.server_id}`, { method: "DELETE" });
      if (!r?.ok) return toast(r?.error?.message || "지우지 못했어요. 잠시 후 다시 해주세요");
    }
    STUB.supplies = STUB.supplies.filter((x) => x.id !== id);
    this.render();
    toast(`「${s.item}」 지웠어요`);
  },

  // ── 시간표 터치 편집 ──────────────────────────────────
  // 칸을 누르면 가운데 창이 뜬다. 지금 값이 목록에 없는 과목이면 직접입력 칸에 미리 채워 놓는다.
  ttOpen(r, c) {
    const v = S.ttOverrides[`${r}-${c}`] ?? ttOf().grid[r][c] ?? "";
    S.ttEdit = { r, c, v };            // v = 지금 값. 화면이 입력칸에 그대로 채운다
    location.hash = "#edittt"; this.render();
    document.getElementById("tt-v")?.focus();
  },
  /* 칩을 누르면 입력칸에 «채우기만» 한다. 저장은 [저장]이 한다(§3: 넣기·취소를 화면에 둔다).
     ⚠ 아래 ttPick(subject) 는 «고르는 즉시 저장»하는 옛 함수다 — 이름이 겹치면 뒤엣것이 이겨
       칩만 눌러도 창이 닫혀 버린다. 그래서 이건 ttSet 이다. */
  ttSet(v) { if (S.ttEdit) { S.ttEdit.v = v; this.render(); } },
  // [저장] — 입력칸에 있는 값을 그 칸에 넣는다. 비우면 빈 칸이 된다
  ttSave() {
    if (!S.ttEdit) return;
    const v = String(S.ttEdit.v || "").trim();
    this.ttPick(v || "빈칸");
    location.hash = "#timetable"; this.render();
  },
  ttClose() { S.ttEdit = null; S.ttOwn = ""; S.ttOwnOpen = false; location.hash = "#timetable"; this.render(); },
  ttOwnToggle() {
    S.ttOwnOpen = !S.ttOwnOpen;
    if (!S.ttOwnOpen) S.ttOwn = "";
    this.render();
    if (S.ttOwnOpen) document.getElementById("tt-own")?.focus();
  },
  /* 저장 — 직접 적은 것이 있으면 그걸 쓰고, 없으면 **지금 칸 값 그대로** 둔다.
     ⚠ 예전엔 빈 입력을 「빈칸」으로 읽어서, 칩으로 과목을 고른 뒤 저장을 누르면
        방금 고른 것이 도로 지워졌다. 비우는 건 「비우기」 버튼이 한다. */
  ttPickOwn() {
    const v = (S.ttOwn || "").trim();
    if (v) return this.ttPick(v);
    const { r, c } = S.ttEdit;
    this.ttPick(S.ttOverrides[`${r}-${c}`] ?? ttOf().grid[r][c] ?? "빈칸");
  },
  ttPick(subject) {
    const { r, c } = S.ttEdit;
    const orig = ttOf().grid[r][c];
    const v = subject === "빈칸" ? "" : subject;
    // 원래 값으로 되돌리면 수정 표시를 지운다(고친 칸만 공유 대상이 되게)
    if (v === orig) delete S.ttOverrides[`${r}-${c}`];
    else S.ttOverrides[`${r}-${c}`] = v;
    S.ttEdit = null; S.ttOwn = ""; S.ttOwnOpen = false; this.render();
    toast(v ? `${DAY_KO[c]}요일 ${r + 1}교시를 «${v}»로 바꿨어요` : `${DAY_KO[c]}요일 ${r + 1}교시를 비웠어요`);
  },
  /* 아코디언 — 한 번 손대면 그 뜻을 기억한다. 자동(시각 기준)은 «안 건드렸을 때»만 돈다.
     ⚠ 지금 값을 그대로 뒤집는다. 자동으로 열려 있었으면 «닫기»가, 닫혀 있었으면 «열기»가 된다 —
       안 그러면 처음 누를 때 아무 일도 안 일어난 것처럼 보인다. */
  ttFold(which) {
    const el = document.querySelector(which === "school" ? ".tt-hd .ttp-caret" : ".ttp-hd .ttp-caret");
    const nowOpen = !!el?.classList.contains("on");
    S.ttFold = { ...S.ttFold, [which]: !nowOpen };
    this.render();
  },
  ttReset() { S.ttOverrides = {}; this.render(); toast("원래 시간표로 되돌렸어요"); },

  // 내 정보 — 테마 시트·간단 안내(2026-07-28)
  // ── 진급 (2026-07-28) ────────────────────────────────────
  promoteOpen(to) {
    const c = cur();
    S.promote = { id: c.id, to, class_name: c.class_name };
    this.render();
  },
  promotePick(n) { S.promote.class_name = String(n); this.render(); },
  promoteCancel() {
    // 「나중에」 — 이번 실행에서만 접는다. 다음에 켜면 다시 묻는다(반을 모르면 시간표가 남의 반 것이다).
    S.promote = null; this.render();
  },
  async promoteSave() {
    const d = S.promote;
    const c = STUB.children.find((x) => x.id === d.id);
    if (c) { c.grade = String(d.to); c.class_name = String(d.class_name); c.grade_code = d.to; }
    S.promoteDone = [...(S.promoteDone || []), d.id];
    S.promote = null;
    SCHOOL.slug = null;               // 학년·반이 바뀌었으니 시간표·급식을 다시 받는다
    this.render();
    toast(`${esc(c?.nickname || "")} ${d.to}학년 ${d.class_name}반`);
    // 서버는 학년 변경을 **진급(promote)** 으로만 받는다 — 자녀당 1회, 바로 다음 학년으로만(회신19)
    if (TOKENS.access && c?.server_id) {
      this.childPatchServer(c.server_id, { nickname: c.nickname, name: c.name,
        grade: String(d.to), class_name: String(d.class_name) }, d.to - 1);
    }
  },
  toast0(msg) { toast(msg); },
  openPolicy() { location.hash = "#policy"; },
  /* 그 폰 끊기 — 지우는 즉시 그쪽 토큰이 죽는다. 「지금 이 폰」은 화면에 끊기 버튼을 안 그려서
     실수로 자기를 로그아웃시킬 수 없다(서버는 그것까지 막지 않는다 — 웹에서 부를 수도 있으니). */
  async deviceRemove(id) {
    const before = S.devices;
    S.devices = S.devices.filter((d) => d.id !== id);
    this.render();
    const r = await api(`/me/devices/${id}`, { method: "DELETE" });
    if (!r?.ok) { S.devices = before; this.render(); return toast("끊지 못했어요"); }
    toast("그 폰의 연결을 끊었어요");
  },
  /* 광고성 수신 채널 토글 — 화면 먼저 바꾸고 서버에 반영. 실패하면 되돌리고 말해준다. */
  async mkToggle(ch) {
    const before = { email: false, sms: false, call: false, ...(S.marketing || {}) };
    S.marketing = { ...before, [ch]: !before[ch] };
    this.render();
    if (!TOKENS.access) return;
    const r = await api("/me/marketing", { method: "PATCH", body: { marketing: S.marketing } });
    if (!r?.ok) { S.marketing = before; this.render(); return toast("수신 설정을 저장하지 못했어요"); }
    S.marketing = r.data.marketing;
  },

  // ── 점심시간 고치기 (2026-07-28) ─────────────────────────
  // NEIS 가 안 주는 값이라 학교 기본값(4교시 뒤 12:10~13:00)으로 시작하고 사용자가 고친다.
  lunchOpen() { const L = lunchOf(); S.lunchEdit = { after: L.after, start: L.start, end: L.end }; this.render(); },
  lunchAfter(n) { S.lunchEdit.after = n; this.render(); },
  lunchCancel() { S.lunchEdit = null; this.render(); },
  lunchSave() {
    const d = S.lunchEdit;
    if (d.start >= d.end) return toast("끝나는 시각이 시작보다 늦어야 해요");
    S.lunchAfter = d.after; S.lunchTime = { start: d.start, end: d.end };
    S.lunchEdit = null; saveHome(); this.render();
    toast(`점심 ${d.after}교시 뒤 · ${d.start}~${d.end}`);
  },

  /* ── 하교 후 개인 일정 (2026-07-27) ──────────────────────
     웹에 있던 「+ 줄 추가」를 앱에 옮긴 것. 학교 시간표와 저장소가 다르다 —
     이건 override(반 전체 공유 후보)가 아니라 **나만 보는 값**이라 공유 대상이 아니다. */
  /* ── 구매 (2026-07-31) — 어댑터 하나로 «진짜/모의»를 가른다 ─────────
     플러그인이 붙어 있으면 구글 결제창을 띄우고, 없으면(브라우저·플러그인 전) 예전처럼 안내만 한다.
     Play 개발자 계정이 열리면 ①BILLING.on = true ②상품 ID 확인 만 하면 이 흐름 그대로 돈다.
     ⚠ 이용권을 켜는 쪽은 **서버**다 — 앱이 «샀다»고 말한 걸 믿으면 누구나 켤 수 있다.
        앱은 구매 토큰만 넘기고, 서버가 구글에 물어 확인한 뒤 기간을 늘린다. */
  async buyPlan() {
    const c = cur();
    const months = S.planSel;
    if (!months) return toast("기간을 골라주세요");
    if (S.payBusy) return;
    const productId = BILLING.products[months];
    if (!BILLING.on || !billingPlugin() || !productId) {
      return toast("결제 준비 중이에요 — 스토어 등록이 끝나면 열려요");
    }
    S.payBusy = true; this.render();
    try {
      const P = billingPlugin();
      // 플러그인마다 이름이 조금씩 다르다 — 있는 것을 쓴다(계정 열리면 실제 플러그인에 맞춰 한 줄만 남길 것)
      const res = await (P.purchase ? P.purchase({ productId }) : P.buy({ productId }));
      const token = res?.purchaseToken || res?.purchase?.purchaseToken || res?.token;
      if (!token) throw new Error("구매 정보를 받지 못했어요");
      const r = await api("/billing/verify", { method: "POST", body: {
        child_id: c.server_id, product_id: productId, purchase_token: token, platform: "google",
      } });
      if (!r?.ok) throw new Error(r?.error?.message || "결제 확인에 실패했어요");
      // 서버가 새 만료일을 준다 — 그걸 그대로 화면에 반영(앱이 계산하지 않는다)
      if (r.data?.expires_at && c) c.pass = { active: true, expires_at: r.data.expires_at };
      saveKids();
      toast("이용권이 켜졌어요");
      location.hash = "#home";
    } catch (e) {
      if (!/cancel/i.test(String(e?.message || e))) toast(String(e?.message || e).slice(0, 60));
    } finally { S.payBusy = false; this.render(); }
  },
  mockPay() { this.buyPlan(); },   // 옛 이름 — 남아 있는 호출을 위해
  // 재인증(§4.5) — 수정·삭제·탈퇴 앞에 이 시트가 선다. 삭제는 되돌릴 수 없으니 두 번 확인한다(2026-07-24).
  // action이 있으면 최종 확인까지 통과했을 때 그걸 실행한다(없으면 목업 안내만).
  /* 삭제 = **창 하나 + 지문 한 번** (2026-07-31 «팝업이 5번» 지적).
     전엔 본인확인 창 → 지문 → 최종확인 창 → (서버가 또 요구) → 지문 … 다섯 번이었다.
     이제 「지우기」를 누르면 지문 한 번으로 서버 토큰(5분)까지 받아두고 바로 지운다 —
     이어지는 DELETE 요청이 그 토큰을 그대로 써서 두 번째 지문이 없다. */
  withdrawAsk() {
    this.askDelete("회원 탈퇴 — 로그인이 막히고, 데이터는 3개월 보관 후 완전히 파기됩니다.", async () => {
      /* reauthConfirm 이 방금 getReauth 를 통과시켰으므로 S.reauthToken 이 살아 있다 */
      const r = await api("/me", { method: "DELETE", reauth: S.reauthToken }).catch(() => null);
      if (!r?.ok) return toast(r?.error?.message || "탈퇴 처리에 실패했어요 — 고객센터로 문의해 주세요");
      toast("탈퇴됐어요. 데이터는 3개월 보관 후 완전히 삭제됩니다");
      try { localStorage.clear(); } catch (e) {}
      TOKENS.access = null; TOKENS.refresh = null;
      S.loggedIn = false; S.serverAuth = false;
      location.hash = "#login"; this.render();
    });
  },
  askDelete(what, action) {
    S.reauthThen = what;
    S.reauthAction = action || null;
    this._renderReauth();
    document.getElementById("reauth").classList.remove("hidden");
  },
  _renderReauth() {
    document.getElementById("reauth-title").textContent = "정말 삭제할까요?";
    document.getElementById("reauth-msg").innerHTML =
      `<b>${S.reauthThen}</b><br>지우면 <b class="bad">되돌릴 수 없어요.</b><br>「지우기」를 누르면 지문·얼굴 확인 한 번으로 바로 지워요.`;
    /* 시안 7f — 두기 1 : 지우기 1. **남기는 쪽이 왼쪽**, 지우는 쪽만 채운다. */
    document.getElementById("reauth-actions").innerHTML =
      `<button class="btn-ghost" onclick="App.reauthCancel()">그대로 두기</button>
       <button class="btn-danger fill" onclick="App.reauthConfirm()">지우기</button>`;
  },
  async reauthConfirm() {
    document.getElementById("reauth").classList.add("hidden");
    const act = S.reauthAction; S.reauthAction = null;
    // 본인 확인 한 번 — 서버 계정이면 reauth 토큰까지 받아둔다(비번 계정은 getReauth가 비번을 묻는다)
    const ok = TOKENS.access ? !!(await this.getReauth(S.reauthThen)) : await this._bio(S.reauthThen);
    if (!ok) return toast("본인 확인을 취소했어요");
    if (typeof act === "function") await act();
    else toast("본인 확인이 끝났어요");   // 아직 배선 안 된 목업 항목
  },
  reauthCancel() { document.getElementById("reauth").classList.add("hidden"); S.reauthAction = null; },

  // ── 방과후 주간 타임그리드 ────────────────────────────────
  // 빈 칸을 누른 지점의 y로 시작 시각을 잡고(10분 단위) 입력 바를 올린다. 기본 1시간.
  planTap(e, day) {
    const box = e.currentTarget.getBoundingClientRect();
    const mins = snap10(GRID.h0 * 60 + ((e.clientY - box.top) / GRID.px) * 30);
    S.planDraft = { day, days: [day], name: "", start: toHHMM(mins), end: toHHMM(Math.min(mins + 60, GRID.h1 * 60)), color: 0 };
    this.render();
    document.getElementById("pb-name")?.focus();
  },
  // 시간표의 「＋ 줄 추가」 — 방과후 격자를 거치지 않고 바로 새 학원을 만든다
  planNew() {
    S.planDraft = { day: null, days: [], name: "", start: "15:00", end: "16:00", color: 0 };
    this.render();
    document.getElementById("pb-name")?.focus();
  },
  planColor(i) { S.planDraft.color = i; this.render(); },
  planDay(n) {
    const d = S.planDraft;
    d.days = (d.days || []).includes(n) ? d.days.filter((x) => x !== n) : [...(d.days || []), n].sort();
    this.render();
  },
  planCancel() {
    location.hash = "#afterschool"; S.planDraft = null; this.render(); },
  // 블록을 누르면 같은 창을 값이 채워진 채로 — 이름·시간·색을 고치거나 지운다
  planEdit(id) {
    const a = STUB.activities.find((x) => x.id === id);
    if (!a) return;
    const days = String(a.days_of_week || "").split(",").filter(Boolean).map(Number).sort();
    S.planDraft = { id: a.id, day: days[0] || 1, days, name: a.name,
      start: a.start_time, end: a.end_time, color: a.color ?? 0 };
    location.hash = "#editact"; this.render();
    document.getElementById("pb-name")?.focus();
  },
  /* 시안 10f (2026-07-28) — **바로 지우지 않는다.** 되돌릴 수 없는 일이라 한 번 더 묻는다.
     확인 창은 L4(400)라 무엇도 가리지 못하고, 가림막을 눌러도 안 닫힌다 —
     실수로 바깥을 스쳐서 «지웠나 안 지웠나» 모르게 되는 일이 없어야 한다. */
  planDelete() {
    S.planKill = { id: S.planDraft.id, name: S.planDraft.name };
    this.render();
  },
  planKillCancel() { S.planKill = null; this.render(); },
  planKillDo() {
    const k = S.planKill;
    const i = STUB.activities.findIndex((a) => a.id === k.id);
    const gone = i >= 0 ? STUB.activities[i] : null;
    if (i >= 0) STUB.activities.splice(i, 1);
    S.planKill = null; S.planDraft = null; this.render();
    this._planPush(gone, "DELETE");   // 서버에도 — 안 지우면 되살아난다(2026-08-03 검수학원 사건)
    toast(`「${k.name}」 을(를) 지웠어요`);
  },
  /* 학원 수정·삭제를 서버에 반영. 서버는 재인증을 요구한다(되돌릴 수 없는 축) —
     생체/비번 한 번 받고 재시도한다. 실패해도 화면은 이미 바뀌어 있으니 말로만 알린다. */
  async _planPush(a, method) {
    if (!a?.server_id || !TOKENS.access) return;
    const body = method === "PATCH" ? { name: a.name, days_of_week: a.days_of_week,
      start_time: a.start_time, end_time: a.end_time } : undefined;
    let r = await api(`/activities/${a.server_id}`, { method, ...(body ? { body } : {}) }).catch(() => null);
    if (r?.error?.code === "REAUTH_REQUIRED") {
      const t = await this.getReauth(method === "DELETE" ? "학원 삭제" : "학원 수정");
      if (!t) return toast("본인 확인을 못 해서 서버엔 반영되지 않았어요");
      r = await api(`/activities/${a.server_id}`, { method, ...(body ? { body } : {}), reauth: t }).catch(() => null);
    }
    if (!r?.ok) toast(r?.error?.message || "서버에 반영하지 못했어요 — 앱을 다시 켜면 되돌아올 수 있어요");
  },
  planSave() {
    const d = S.planDraft;
    if (!d?.name.trim()) return toast("이름을 넣어주세요");
    // 요일이 곧 «언제 가는지»다. 비면 시간표·방과후 어디에도 안 나타나므로 저장을 막는다.
    const days = (d.days && d.days.length ? d.days : (d.day ? [d.day] : [])).slice().sort();
    if (!days.length) return toast("요일을 하나는 골라주세요");
    if (d.id) {                                   // 수정
      const a = STUB.activities.find((x) => x.id === d.id);
      if (a) Object.assign(a, { name: d.name.trim(), color: d.color, start_time: d.start, end_time: d.end,
                                days_of_week: days.join(",") });
      S.planDraft = null; this.render();
      this._planPush(a, "PATCH");   // 서버에도 — 안 보내면 앱을 다시 켤 때 옛 이름이 돌아온다(2026-08-03)
      return toast(`${d.name.trim()} 을(를) 고쳤어요`);
    }
    const newId = Math.max(0, ...STUB.activities.map((a) => a.id)) + 1;
    STUB.activities.push({
      id: newId,
      type: "academy", name: d.name.trim(), color: d.color,
      days_of_week: days.join(","), start_time: d.start, end_time: d.end,
    });
    S.planDraft = null;
    this.render();
    // 서버에도 — 안 하면 앱을 지우거나 폰을 바꿀 때 사라진다
    const c0 = cur();
    if (TOKENS.access && c0?.server_id) {
      // 서버는 **다니는 기간**(start_date~end_date)도 요구한다 — 학기 중에만 다니는 학원이 있어서다.
      // 앱에선 안 물어보니 «오늘부터 학년말(다음해 2월)»로 기본값을 넣는다.
      const ay = +schoolYearOf(TODAY);
      api(`/children/${c0.server_id}/activities`, { method: "POST", body: {
        type: "academy", name: d.name.trim(), days_of_week: days.join(","),
        start_time: d.start, end_time: d.end,
        start_date: TODAY, end_date: `${ay + 1}0228`,
      } }).then((r) => {
        if (!r?.ok) return toast(r?.error?.message || "학원을 서버에 저장 못 했어요");
        const a = STUB.activities.find((x) => x.id === newId);
        if (a) a.server_id = r.data.id ?? r.data.activity?.id ?? null;   // 없으면 수정·삭제를 서버에 못 보낸다
      });
    }
    toast("추가했어요");
  },
  // 블록 아래 손잡이를 끌어 끝 시각을 조정한다. 실앱에서도 같은 제스처를 쓴다.
  gripDown(e, id) {
    e.preventDefault(); e.stopPropagation();
    const blk = e.currentTarget.parentElement;
    const act = STUB.activities.find((a) => a.id === id);
    const startY = e.clientY, h0 = blk.offsetHeight;
    const move = (ev) => { blk.style.height = Math.max(GRID.px, h0 + (ev.clientY - startY)) + "px"; };
    const up = (ev) => {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
      const mins = snap10(toMin(act.start_time) + (Math.max(GRID.px, h0 + (ev.clientY - startY)) / GRID.px) * 30);
      act.end_time = toHHMM(Math.min(mins, GRID.h1 * 60));
      App.render();
      toast(`${esc(act.name)} ${act.start_time}~${act.end_time}`);
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  },
};

// 화면 안 알림 — 시스템 alert 대신(요청27 검수 지적). 실앱도 이 자리를 그대로 쓴다.
let toastTimer = null;
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 2200);
}

// 홈 편집 설정 — 목업은 이 브라우저(localStorage)에만. 실앱은 계정 설정(서버)에 담는다.
/* 지난번 자녀 목록 (2026-07-28) — 켜자마자 **바로 홈을 그리기 위해** 담아둔다.
   ⚠ 예전엔 서버가 /me 를 줄 때까지 「불러오는 중…」이 떴다. 실측 **2.4초**였고,
      그 뒤 기록·학교까지 받느라 홈이 다 차기까지 **7.5초**였다(사장님: "3~5초 떠 있다가").
   담는 것은 **내 아이 목록**뿐이다 — 기록·사진은 안 담는다(민감하고, 금방 낡는다).
   서버 응답이 오면 통째로 갈아끼운다. 캐시는 «먼저 보여줄 것»이지 «정답»이 아니다. */
const KIDS_CACHE_KEY = "eduthink.kids";
/* ═══ 자녀별 생활 데이터 캐시 (2026-07-31 «빠르게 반응해야») ═══════
   전환·재시작 때 서버 응답(요청당 ~1초)을 기다리며 빈 화면을 보였다.
   마지막으로 받아둔 것을 **즉시** 그리고, 서버는 뒤에서 갱신한다(도착하면 조용히 다시 그림).
   사진 blob은 안 담는다 — 목록 메타만. 사진은 hydrateImages()가 제 캐시로 채운다. */
const LIFE_CACHE_KEY = "eduthink.life";
function saveLifeCache(c) {
  if (!c?.server_id) return;
  try {
    const all = JSON.parse(localStorage.getItem(LIFE_CACHE_KEY) || "{}");
    // 기록의 blob 주소(blob:…)는 다음 실행에서 죽는다 — 서버 경로만 남긴다
    const recs = STUB.records.map((r) => ({ ...r, image: r._thumb ? PLACEHOLDER : null, images: (r._pages || []).map(() => PLACEHOLDER) }));
    all[c.server_id] = {
      records: recs, documents: STUB.documents, notices: STUB.notices, supplies: STUB.supplies,
      activities: STUB.activities, myEvents: STUB.myEvents, communityPosts: STUB.communityPosts, t: Date.now(),
    };
    // 자녀 3명 한도라 통도 3개면 된다 — 오래된 것 정리 없이 그대로 둔다
    localStorage.setItem(LIFE_CACHE_KEY, JSON.stringify(all));
  } catch (e) {}
}
function applyLifeCache(c) {
  if (!c?.server_id) return false;
  try {
    const v = JSON.parse(localStorage.getItem(LIFE_CACHE_KEY) || "{}")[c.server_id];
    if (!v) return false;
    STUB.records = v.records || []; STUB.documents = v.documents || []; STUB.notices = v.notices || [];
    STUB.supplies = v.supplies || []; STUB.activities = v.activities || []; STUB.myEvents = v.myEvents || [];
    STUB.communityPosts = v.communityPosts || [];
    return true;
  } catch (e) { return false; }
}

/* 기본 자녀(2026-07-31 지시) — 형제가 있으면 앱을 켰을 때 누구부터 보여줄지 고른다.
   server_id 로 기억한다(자녀 순서·로컬 id는 다시 받으면 바뀔 수 있다). 미등록 목업 자녀는 로컬 id로. */
const DEF_CHILD_KEY = "eduthink.defaultChild";
const defChildKeyOf = (c) => c?.server_id ?? `local:${c?.id}`;
function defChildGet() { try { return JSON.parse(localStorage.getItem(DEF_CHILD_KEY) || "null"); } catch (e) { return null; } }
function pickDefaultChild(list) {
  const d = defChildGet();
  return list.find((c) => defChildKeyOf(c) === d) || list[0];
}
function saveKids() {
  try {
    localStorage.setItem(KIDS_CACHE_KEY, JSON.stringify(STUB.children.map((c) => ({
      id: c.id, server_id: c.server_id, nickname: c.nickname, name: c.name,
      grade: c.grade, class_name: c.class_name, grade_code: c.grade_code,
      school: c.school, counts: c.counts, pass: c.pass, photo: c.photo,
      child_device: !!c.child_device, child_device_at: c.child_device_at || null,
    }))));
  } catch (e) {}
}
function loadKids() {
  try {
    const v = JSON.parse(localStorage.getItem(KIDS_CACHE_KEY) || "null");
    if (!Array.isArray(v) || !v.length) return false;
    STUB.children = v;
    S.currentChildId = pickDefaultChild(v).id;   // 기본 자녀부터 — 없으면 첫째
    return true;
  } catch (e) { return false; }
}
const clearKids = () => { try { localStorage.removeItem(KIDS_CACHE_KEY); } catch (e) {} };

/* 학교 데이터(급식·학사일정·시간표)도 담는다 (2026-07-28).
   자녀 목록만 담았더니 홈이 **두 번** 그려졌다 — 처음엔 「7월 31일 금요일」만,
   1~2초 뒤 「여름방학 8일째」와 일정 목록이 들어오며 화면이 바뀌었다
   (사장님: "순간적으로 다른 화면이 보이고 메인화면이 나온다").
   ⚠ 자녀마다 다르므로 **slug+학년+반**을 열쇠로 쓴다. 형제를 바꾸면 그 아이 것이 나온다.
   ⚠ 하루가 지나면 버린다 — 급식은 날마다 바뀐다. 낡은 걸 보여주느니 잠깐 비는 게 낫다. */
const SCHOOL_CACHE_KEY = "eduthink.school";
const schoolKey = (c) => `${c?.school?.slug || ""}|${c?.grade || ""}|${c?.class_name || ""}`;
function saveSchool(c) {
  try {
    localStorage.setItem(SCHOOL_CACHE_KEY, JSON.stringify({
      k: schoolKey(c), day: TODAY,
      info: SCHOOL.info, meals: SCHOOL.meals, schedules: SCHOOL.schedules, timetable: SCHOOL.timetable,
    }));
  } catch (e) {}
}
function loadSchoolCache(c) {
  try {
    const v = JSON.parse(localStorage.getItem(SCHOOL_CACHE_KEY) || "null");
    if (!v || v.k !== schoolKey(c) || v.day !== TODAY) return false;
    SCHOOL.slug = c.school.slug; SCHOOL.from = "cache";
    SCHOOL.info = v.info; SCHOOL.meals = v.meals; SCHOOL.schedules = v.schedules; SCHOOL.timetable = v.timetable;
    return true;
  } catch (e) { return false; }
}

/* 🔒 이 폰에서 **부모 흔적을 전부 지운다** — 자녀폰으로 연결할 때 부른다(2026-08-02 폰 실측).
   토큰만 바꾸고 캐시를 놔뒀더니, 자녀 화면 뒤로 형제 이름(때윤)·학교·이용권·서랍 썸네일이
   그대로 살아 있었다. 화면 게이트(isChildToken)로 «못 보게» 막았지만,
   **폰에 남겨두는 것 자체가 문제**다 — 아이가 쓰는 폰이고, 앱을 지우기 전까지 계속 남는다.
   ⚠ 홈 설정(eduthink.home)은 테마·카드 순서라 부모 정보가 아니다 — 남긴다.
   ⚠ IMG_CACHE 는 메모리라 지우지 않으면 «연결 직후»에만 사진이 살아 있다(실제로 그랬다). */
function wipeParentData() {
  for (const k of [KIDS_CACHE_KEY, LIFE_CACHE_KEY, DEF_CHILD_KEY, SCHOOL_CACHE_KEY]) {
    try { localStorage.removeItem(k); } catch (e) {}
  }
  IMG_CACHE.clear();
  STUB.children = []; STUB.records = []; STUB.documents = []; STUB.supplies = [];
  STUB.notices = []; STUB.myEvents = []; STUB.activities = []; STUB.communityPosts = [];
  S.currentChildId = null; S.devices = null; S.planList = null; S.inquiries = null;
  SCHOOL.slug = null; SCHOOL.info = SCHOOL.meals = SCHOOL.schedules = SCHOOL.timetable = null;
  SCHOOL.from = "stub";
  LOADED.childId = null; LOADED.busy = false;
}

/* 자녀폰이 아는 **유일한 아이** — 자기 자신 (2026-08-02).
   부모 캐시를 지우고 나니 자녀 화면이 cur() 를 못 읽어 깨졌다. 자녀 화면은 원래
   «형제 목록»이 아니라 «나»만 있으면 되는데, 그동안 부모 목록에 얹혀 돌고 있었다. */
/* ═══ 자녀 앱 테마 (2026-08-02 확정: 파스텔·퀘스트 2종 선택형) ═══
   토큰 두 개(data-kid-theme / data-kid-accent)를 html 에 스탬프하면 CSS 가 자녀 화면을
   통째로 갈아입는다. 파랑 계열 없음(부모 앱과 한눈에 갈리게). 값은 서버(/child/prefs)에
   저장하고 localStorage 는 즉시 반응용 캐시다 — 기기를 바꿔도 서버 값이 이긴다. */
const KID_PREF_KEY = "eduthink.kidPrefs";
/* ── 자녀 화면 6종 (2026-08-03) ────────────────────────────────
   여덟 살과 열세 살을 **한 화면으로 맞추려던 게 애초에 무리**였다. 평균을 잡으면
   둘 다 어색해진다. 그래서 나이가 아니라 **취향으로 고르게** 한다 — 위에서 아래로
   대략 어린 쪽 → 큰 쪽이지만, 열 살이 「종이」를 골라도 이상하지 않다.
   ⚠ 나이로 자동 배정하지 않는다. 「너는 여덟 살이니까 이거」는 아이가 제일 싫어하는 말이다.

/* ── 자녀 화면 색 12벌 (2026-08-03) ─────────────────────────────
   여덟 살과 열세 살을 **한 화면으로 맞추려던 게 애초에 무리**였다. 평균을 잡으면 둘 다 어색해진다.
   그래서 **색만** 여러 벌 두고 아이가 고르게 한다 — 구조도 말도 하나다(별 · 별의 길).
   ⚠ 나이·성별로 자동 배정하지 않는다. 두 줄로 묶어 놓았을 뿐 어느 줄에서 골라도 된다.
      「너는 여덟 살이니까 이거」는 아이가 제일 싫어하는 말이다.
   ⚠ 이 표와 style.css 의 :root[data-kid-theme=…] 는 **짝이다.**
      둘 다 scripts/gen-themes.mjs 가 뽑는다. 손으로 고치지 말 것. */
const KID_THEMES = {
  rose:     { name: "로즈", group: "a" },
  lilac:    { name: "라일락", group: "a" },
  mint:     { name: "민트", group: "a" },
  peach:    { name: "피치", group: "a" },
  butter:   { name: "버터", group: "a" },
  aqua:     { name: "아쿠아", group: "a" },
  gold:     { name: "골드", group: "b" },
  cyan:     { name: "시안", group: "b" },
  lime:     { name: "라임", group: "b" },
  magenta:  { name: "마젠타", group: "b" },
  orange:   { name: "오렌지", group: "b" },
  violet:   { name: "바이올렛", group: "b" },
};
const KID_THEME_KEYS = Object.keys(KID_THEMES);
/* 말은 한 벌뿐이다. 색이 바뀐다고 세는 단위가 바뀌면 아이가 헷갈리고,
   서버 star_ledger·「별의 길」과도 어긋난다. */
const KID_WORDS = { unit: "별", collect: "모은 별", board: "별의 길",
  done: "오늘 끝!", submit: "보내기", act: "" };
const kw = (k) => KID_WORDS[k] || "";
const kidBoard = () => "path";

/* 급식 메뉴 분류(2026-08-02) — **이름 끝만 보면 거의 다 잡힌다.**
   개별 메뉴는 한 주에 거의 안 겹쳐서(밥·김치 빼고) 순위를 매겨도 표본이 안 된다.
   종류로 묶어야 «볶음을 좋아하고 나물을 싫어한다»가 한 주 만에 나온다.
   ⚠ 순서가 중요하다 — 「볶음밥」은 밥(주식)이지 볶음이 아니다. 위에서부터 먼저 걸린다. */
const DISH_CATS = [
  [/(볶음밥|비빔밥|덮밥|김밥|밥|국수|우동|라면|떡국|만두국|면)$/, "주식"],
  [/(김치|깍두기|겉절이)$/, "김치"],
  [/(국|탕|찌개|전골)$/, "국물"],
  [/(튀김|까스|가스|강정)$/, "튀김"],
  [/(볶음|불고기|제육)$/, "볶음"],
  [/(구이|조림|찜)$/, "구이조림"],
  [/(무침|나물|생채|샐러드)$/, "나물"],
  [/(전|부침|만두)$/, "전"],
  [/(우유|주스|음료|요구르트|과일|사과|바나나|귤|수박|참외|방울토마토)$/, "후식"],
];
const dishCat = (name) => (DISH_CATS.find(([re]) => re.test(name)) || [, "기타"])[1];

/* 합친 이름 — 「돈육김치볶음」과 「돼지고기김치볶음」은 같은 것이다.
   ⚠ 지금은 **확실한 것만** 합친다(괄호·공백·널리 쓰이는 재료 동의어).
     진짜 사전은 쌓인 식단표를 실제로 훑어봐야 나온다 — 지레짐작으로 묶으면
     잘못 묶인 데이터가 쌓여 되돌리기 더 어려워진다. 그래서 **원문도 같이 저장**한다. */
const MEAT_SYN = [[/돼지고기|저육/g, "돈육"], [/쇠고기|소고기/g, "우육"], [/닭고기/g, "계육"]];
function dishKey(name) {
  let s = String(name || "").replace(/\([^)]*\)/g, "").replace(/[\s*·]/g, "");
  MEAT_SYN.forEach(([re, to]) => { s = s.replace(re, to); });
  return s;
}

/* 친구 칩 — 서버가 붙기 전에도 «타이핑은 처음 한 번»이 성립해야 한다.
   ⚠ 자녀폰 전용이다. wipeParentData() 가 지우는 대상에 넣지 않는다 —
     부모 캐시가 아니라 이 아이 자신의 것이다. */
const FRIENDS_KEY = "eduthink.kidFriends";
function loadFriends() {
  try { const v = JSON.parse(localStorage.getItem(FRIENDS_KEY) || "null");
    if (Array.isArray(v)) S.friends = v.filter((x) => typeof x === "string").slice(0, 40); } catch (e) {}
}
function saveFriends() { localStorage.setItem(FRIENDS_KEY, JSON.stringify(S.friends)); }

/* 오늘 배운 과목 — 시간표(ttOf)를 그대로 쓴다. 새로 받을 게 없다.
   같은 과목이 하루에 두 번 있어도 고르는 칸은 하나여야 한다 → 중복 제거. */
/* 오늘 남은 카드 한 벌. 순서가 곧 난이도다 —
   고르기만 하면 되는 것(즉시 별)을 앞에 두고, 몸을 움직여야 하는 의뢰를 뒤에 둔다.
   첫 장을 못 넘기면 아무것도 안 한다. */
function deckCards() {
  const out = [];
  const meal = mealsOf().find((m) => m.date === TODAY && m.type === "중식");
  if (meal && !S.mealRated) out.push({
    key: "meal", title: "오늘 급식 어땠어?", stars: 1, now: true,
    sub: meal.dishes.slice(0, 3).map((x) => x.name).join(" · "),
    go: "location.hash='#childmealrate'", goLabel: kw("act") || "고르기",
  });
  if (!S.friendLogged) out.push({
    key: "friend", title: "오늘 누구랑 놀았어?", stars: 1, now: true,
    go: "location.hash='#childfriend'", goLabel: kw("act") || "고르기",
  });
  if (todaySubjects().length && !S.subjectLogged) out.push({
    key: "subject", title: "오늘 제일 재밌었던 건?", stars: 1, now: true,
    sub: todaySubjects().slice(0, 4).join(" · "),
    go: "location.hash='#childsubject'", goLabel: kw("act") || "고르기",
  });
  (S.missions || []).filter((x) => x.status === "open").forEach((x) => out.push({
    key: "m" + x.id, id: x.id, title: x.title, stars: x.stars, now: false,
    sub: [x.minutes ? x.minutes + "분" : "", x.caution || ""].filter(Boolean).join(" · "),
    go: x.verify === "review" ? `S.kidShootId=${x.id};location.hash='#childshoot'` : `App.missionDone(${x.id})`,
    goLabel: x.verify === "review" ? "사진 찍기"
           : x.verify === "endday" ? "오늘 지킬게요" : "완료 보고",
    skip: `App.missionSkip(${x.id})`,
  }));
  return out;
}

function todaySubjects() {
  const wd = new Date(`${TODAY.slice(0,4)}-${TODAY.slice(4,6)}-${TODAY.slice(6)}`).getDay();
  const col = wd - 1;
  if (col < 0 || col > 4) return [];                    // 주말은 수업이 없다
  const grid = ttOf()?.grid || [];
  const names = grid.map((r) => String(r?.[col] || "").trim()).filter(Boolean);
  return [...new Set(names)];
}

/* 옛 이름 → 새 이름 (2026-08-03, 색 2벌 → 12벌).
   ⚠ 이걸 안 두면 **이미 pastel·quest 를 저장해 둔 아이는 색이 통째로 날아간다** —
      --k 가 정의되지 않아 버튼이 회색이 된다. 실제로 스크린샷에서 그 상태를 봤다.
      옛 키를 지우지 않고 매다는 것은 테마 6종→2종 때와 같은 규칙이다. */
const KID_THEME_OLD = { pastel: "mint", quest: "gold" };
const kidThemeFix = (t) => (KID_THEMES[t] ? t : KID_THEME_OLD[t] || null);

function loadKidPrefs() {
  try { const v = JSON.parse(localStorage.getItem(KID_PREF_KEY) || "null");
    const t = kidThemeFix(v && v.theme);
    if (t) { S.kidTheme = t; S.kidAccent = t; if (t !== v.theme) saveKidPrefs(); } } catch (e) {}
}
function saveKidPrefs() {
  localStorage.setItem(KID_PREF_KEY, JSON.stringify({ theme: S.kidTheme, accent: S.kidAccent }));
  // 서버에도 — 실패해도 화면은 이미 바뀌어 있다(다음 접속 때 다시 시도)
  if (TOKENS.access) api("/child/prefs", { method: "PUT", body: { theme: S.kidTheme, accent: S.kidAccent } }).catch(() => {});
}
function applyKidTheme(on) {
  const el = document.documentElement;
  const t = kidThemeFix(S.kidTheme);
  if (on && t) { el.dataset.kidTheme = t; el.dataset.kidAccent = t; }
  else { delete el.dataset.kidTheme; delete el.dataset.kidAccent; }
}

const CHILD_ME_KEY = "eduthink.childMe";
function setChildMe(child) {
  if (!child) return;
  try { localStorage.setItem(CHILD_ME_KEY, JSON.stringify(child)); } catch (e) {}
  S.childLinked = child;
  STUB.children = [{
    id: 1, server_id: child.id, nickname: child.nickname, name: child.nickname,
    grade: child.grade, class_name: child.class_name,
    school: child.school || null, counts: {},
    /* 이용권 — 서버가 준 기한으로 판정한다. 기한을 모르면(옛 저장본) **잠그지 않는다** —
       진짜 만료면 서버가 요청을 거절하니, 여기서 억울하게 잠그는 것보다 낫다(2026-08-03 전수검사 10번). */
    pass: child.pass_expires_at
      ? { active: new Date(child.pass_expires_at).getTime() > Date.now(), expires_at: child.pass_expires_at }
      : { active: true, expires_at: null },
    photo: null,
  }];
  S.currentChildId = 1;
}
function loadChildMe() {
  try {
    const v = JSON.parse(localStorage.getItem(CHILD_ME_KEY) || "null");
    if (!v?.id) return false;
    setChildMe(v);
    return true;
  } catch (e) { return false; }
}

const HOME_PREF_KEY = "eduthink.home";
/* v2(2026-07-28) — menuHidden 의 뜻이 «홈에서 숨김» → «카드에서 내려 아래 줄로» 로 바뀌었다.
   v 가 없는 저장본은 옛 뜻으로 적힌 값이라 그대로 읽으면 카드가 10개가 된다 → 기본값으로 한 번 되돌린다. */
// v3 (2026-08-02): 메뉴 개편으로 항목이 11→5개. 옛 숨김 목록을 그대로 받으면
// 격자가 알림 하나만 남을 수 있어 버전을 올려 숨김만 리셋한다(순서는 살아남는다).
const HOME_PREF_V = 3;
function saveHome() {
  try {
    localStorage.setItem(HOME_PREF_KEY, JSON.stringify({
      v: HOME_PREF_V,
      menuOrder: S.menuOrder, menuHidden: S.menuHidden, carHidden: S.carHidden, carAuto: S.carAuto, theme: S.theme, holiOff: S.holiOff,
      remind: S.remind, calFold: S.calFold, widgetRows: S.widgetRows, appLock: S.appLock,
      lunchAfter: S.lunchAfter, lunchTime: S.lunchTime,
      art: S.art, todayCards: S.todayCards, onboard: S.onboard, timeOpt: S.timeOpt,
    }));
  } catch (e) {}
}
function loadHome() {
  try {
    const p = JSON.parse(localStorage.getItem(HOME_PREF_KEY) || "null");
    if (!p) return;
    // 저장 뒤에 메뉴가 늘거나 줄 수 있다 — 있는 key만 살리고, 새로 생긴 건 뒤에 붙인다.
    if (Array.isArray(p.menuOrder)) {
      const kept = p.menuOrder.filter((k) => MENU_KEYS.includes(k));
      S.menuOrder = [...kept, ...MENU_KEYS.filter((k) => !kept.includes(k))];
    }
    if (p.v === HOME_PREF_V && Array.isArray(p.menuHidden)) S.menuHidden = p.menuHidden.filter((k) => MENU_KEYS.includes(k));
    if (Array.isArray(p.carHidden)) S.carHidden = p.carHidden.filter((k) => CAR_CARDS.some((c) => c.key === k));
    if (typeof p.carAuto === "boolean") S.carAuto = p.carAuto;
    if (typeof p.holiOff === "boolean") S.holiOff = p.holiOff;
    // 앱 잠금 — 켜져 있었으면 켜자마자 잠근 채로 시작한다
    if (typeof p.appLock === "boolean") { S.appLock = p.appLock; S.appLocked = p.appLock; }
    if (Number.isInteger(p.lunchAfter)) S.lunchAfter = p.lunchAfter;
    if (p.lunchTime && p.lunchTime.start && p.lunchTime.end) S.lunchTime = p.lunchTime;
    // 월간/주간 선택은 취향이라 기억한다 — 탭에 들어올 때마다 다시 접게 하면 안 된다
    if (typeof p.calFold === "boolean") S.calFold = p.calFold;
    // 위젯 줄 — 저장 뒤에 항목이 늘거나 줄 수 있다. 있는 key만 살린다(홈 메뉴와 같은 규칙).
    if (Array.isArray(p.widgetRows)) S.widgetRows = p.widgetRows.filter((k) => WIDGET_KEYS.includes(k));
    // 하교 후 개인 줄 — 값이 깨져 있어도 화면이 죽지 않게 형태만 확인하고 받는다
    if (p.theme) S.theme = p.theme;
    // 테마 세트 — 없는 키가 저장돼 있으면 기본으로 (§6). 모르는 값을 그대로 박으면 색이 안 바뀐다
    if (ART_SETS.some((a) => a.key === p.art)) S.art = p.art;
    /* 오늘 카드 켜기/끄기 — 저장 뒤에 줄이 늘 수 있다. **있는 키만** 덮어쓰고
       새로 생긴 줄은 기본값(켜짐)으로 남긴다. 통째로 바꾸면 새 줄이 안 보인다. */
    if (p.todayCards && typeof p.todayCards === "object") {
      Object.keys(S.todayCards).forEach((k) => {
        if (typeof p.todayCards[k] === "boolean") S.todayCards[k] = p.todayCards[k];
      });
    }
    if (p.onboard && typeof p.onboard === "object") S.onboard = p.onboard;
    if (p.timeOpt && typeof p.timeOpt === "object") S.timeOpt = { ...S.timeOpt, ...p.timeOpt };
    if (p.remind && typeof p.remind === "object") {
      // 값을 통째로 믿지 않는다 — 형식이 깨진 시각을 그대로 쓰면 예약이 조용히 실패한다
      const t = (v, d) => (/^\d{2}:\d{2}$/.test(v) ? v : d);
      S.remind = { on: !!p.remind.on, evening: t(p.remind.evening, "20:30"), morning: t(p.remind.morning, "07:30") };
    }
  } catch (e) {}
}

window.addEventListener("hashchange", () => App.render());
// 폴더블을 펼치거나 접으면 화면 폭이 바뀐다 — 서류 종이 축소율을 다시 계산해야 한 화면에 맞는다(2026-07-25).
window.addEventListener("resize", () => App.fitPage());
loadHome();
loadDayMarks();   // 달력에 남길 «아이 흔적»(§3) — 이 폰이 본 것만 들어 있다
loadKidPrefs();   // 자녀 테마 로컬 캐시 — 서버 값은 연결 때 덮는다
loadFriends();    // 친구 칩 목록(자녀폰 전용)                                                     // 저장해둔 홈 설정·테마 복원
loadTokens();                                                   // 지난번 로그인 토큰이 있으면 이어서
if (TOKENS.access) {
  S.loggedIn = true; S.serverAuth = true;
  /* 서버 응답이 오기 전 한순간 목업 «첫째·둘째»가 스쳐 보였다 — 자기 아이가 아닌 게 깜빡인다.
     토큰이 있으면 처음부터 비워 두고, loadMe() 가 진짜 목록으로 채운다(2026-07-27). */
  STUB.children = []; STUB.records = []; STUB.documents = []; STUB.supplies = [];
  STUB.notices = []; STUB.myEvents = []; STUB.activities = []; STUB.communityPosts = [];
  S.currentChildId = null;
  if (isChildToken()) {
    /* 🔒 자녀폰이다 — 부모 캐시는 **복원하지 않는다**(2026-08-02).
       loadKids() 를 부르면 형제 이름·학교·이용권이 그대로 살아나고, loadMe() 는 어차피 403이다.
       아는 아이는 저장해둔 «나» 하나뿐. 그걸로 급식·시간표까지 스스로 받아온다. */
    wipeParentData();
    loadChildMe();
    S.childView = true; S.booting = false;
    history.replaceState(null, "", "#game");   /* 옛 자녀 홈은 08-09 에 지웠다 */
    if (cur()) { loadSchoolCache(cur()); loadSchool(); }
  } else {
    /* 지난번 자녀 목록이 있으면 **그걸로 먼저 그린다.** 서버를 기다리지 않는다.
       기록·급식은 아직 비어 있지만 «내 아이 이름과 학년»만 있어도 홈은 제 모양이 된다.
       캐시가 없으면(첫 로그인) 예전처럼 「불러오는 중…」을 띄운다 — 그때는 정말 아무것도 없다. */
    S.booting = !loadKids();
    if (!S.booting) { loadSchoolCache(cur()); applyLifeCache(cur()); }   // 급식·일정·기록·준비물까지 채워야 홈이 «완성된 채»로 뜬다
    loadMe().finally(() => { S.booting = false; App.render(); });
  }
}
document.documentElement.setAttribute("data-theme", S.theme);   // 시작 테마 적용
document.documentElement.setAttribute("data-art", S.art);       // 시작 테마 세트(§6)
/* ⚠ 앱은 **늘 첫 화면에서 시작한다**(2026-07-28 사장님 지적: "왜 기록 부분이 처음에 나와?").
   웹뷰는 지난번 주소를 그대로 되살린다 — 끄기 전이 #timeline 이었으면 다시 켜도 기록이 뜬다.
   앱을 여는 사람은 «이어보기»가 아니라 «오늘 뭐 있나»를 보러 온다.
   ⚠ 자녀폰 연결(#childlink)은 남긴다 — 코드를 넣다 앱이 꺼지면 처음부터 다시 해야 한다.
   위젯으로 켠 경우는 아래 widgetGo() 가 그 화면으로 다시 옮긴다(이 줄보다 뒤에 돈다). */
if (location.hash && location.hash !== "#childlink") {
  history.replaceState(null, "", location.pathname + location.search);
}
App.render();
// 위젯을 눌러서 앱이 켜졌다면 네이티브가 값을 먼저 넣어 뒀을 수 있다 — 첫 그리기 뒤에 확인한다
widgetGo();
drainWidgetChecks();
// 앱을 다시 앞으로 가져올 때도 확인한다 — 위젯에서 체크하고 앱으로 넘어오는 흐름이 가장 흔하다
/* 앱을 다시 앞으로 가져올 때 (2026-07-28 사장님 재지적: "어플을 새로 켰는데 기록부터 보였어")
   ⚠ 아이콘을 다시 눌러도 안드로이드는 **앱을 새로 켜지 않는다.** 뒤에 있던 화면을 그대로 살린다.
      그래서 시작 주소를 비우는 것만으로는 부족했다 — 그 코드는 아예 다시 안 돈다.
   뒤에 갔다 돌아오면 **홈으로 되돌린다.**
   ⚠ 문턱을 1분으로 뒀더니 여전히 기록에서 시작한다는 말을 들었다(2026-07-28 재지적) —
      잠깐 나갔다 오는 게 대부분이라 1분을 넘길 일이 거의 없었다. **5초**로 줄인다.
      화면이 잠깐 꺼졌다 켜지는 것(5초 안쪽)만 그대로 둔다.
   ⚠ 무언가 하는 중이면 건드리지 않는다 — 쓰던 게 날아가는 게 더 나쁘다.
      상태(편집 시트·촬영)뿐 아니라 **화면 자체가 작업 화면**인 경우도 지킨다:
      갤러리에서 사진을 고르는 동안엔 아직 아무 상태도 안 잡혀 있기 때문이다. */
const AWAY_RESET_MS = 5000;
const BUSY_SCREENS = ["#upload", "#child-add", "#childlink", "#doc-form", "#register", "#findpw"];
let hiddenAt = 0;
/* 앱 잠금은 자리를 **오래** 비웠을 때만 다시 건다(2026-07-31).
   카메라·앨범을 여는 것도 «앱을 벗어남»이라, 짧은 이탈까지 잠그면 사진 한 장 넣을 때마다 지문을 물어본다. */
const APP_LOCK_AWAY_MS = 60000;
document.addEventListener("visibilitychange", () => {
  if (document.hidden) { hiddenAt = Date.now(); return; }
  drainWidgetChecks();
  const away = hiddenAt ? Date.now() - hiddenAt : 0;
  const busy = S.planDraft || S.lunchEdit || S.promote || S.ttEdit || S.promoteSheet
    || S.uploadStep || S.viewRecord || S.nameDraft !== null
    || BUSY_SCREENS.includes(location.hash);
  if (S.appLock && away > APP_LOCK_AWAY_MS) S.appLocked = true;
  /* 자리를 비웠다 돌아오면 첫 화면으로 되돌린다 — 다만 **자녀폰의 첫 화면은 자녀 화면**이다.
     여기서 #home 으로 보내는 바람에 카메라(5초 초과)를 다녀온 자녀폰에 부모 홈이 떴다(2026-08-02). */
  const homeHash = isChildToken() ? "#game" : "#home";   /* 아이의 홈은 게임 세계다(08-09) */
  if (!busy && away > AWAY_RESET_MS && location.hash && location.hash !== homeHash) {
    location.hash = homeHash;
  }
  hiddenAt = 0;
  App.render();
});
