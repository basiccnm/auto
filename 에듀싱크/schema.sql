-- 에듀싱크(가칭) DB 스키마 (SQLite 로컬 개발 / Cloudflare D1 배포 공용)
-- 2026-07-12 작성 — NEIS(초중고) 4개 API + 유치원알리미 4개 API 실사 결과 반영
-- 원본 설계 근거: Obsidian Vault\사업관리\04_가칭에듀싱크제작(구독플랜)\PROJECT_TECH_OVERVIEW.md

-- ============================================================
-- 초·중·고 (NEIS)
-- ============================================================

-- 학교 기본정보 (schoolInfo)
CREATE TABLE IF NOT EXISTS schools (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  office_code TEXT NOT NULL,        -- ATPT_OFCDC_SC_CODE (시도교육청코드, 예: B10)
  office_name TEXT NOT NULL,        -- ATPT_OFCDC_SC_NM
  school_code TEXT NOT NULL,        -- SD_SCHUL_CODE
  name TEXT NOT NULL,               -- SCHUL_NM
  school_kind TEXT NOT NULL,        -- SCHUL_KND_SC_NM (초등학교/중학교/고등학교)
  sido TEXT NOT NULL,               -- LCTN_SC_NM
  jurisdiction_office TEXT,         -- JU_ORG_NM (교육지원청)
  address_road TEXT,                -- ORG_RDNMA
  address_detail TEXT,              -- ORG_RDNDA
  phone TEXT,                       -- ORG_TELNO
  homepage TEXT,                    -- HMPG_ADRES
  founded_ymd TEXT,                 -- FOND_YMD (개교기념일/설립일 YYYYMMDD)
  est_type TEXT,                    -- FOND_SC_NM (공립/사립/국립)
  coedu TEXT,                       -- COEDU_SC_NM (남녀공학/남/여)
  slug TEXT NOT NULL,
  last_synced_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_schools_office_code ON schools (office_code, school_code);
CREATE INDEX IF NOT EXISTS idx_schools_name ON schools (name);
CREATE INDEX IF NOT EXISTS idx_schools_slug ON schools (slug);

-- 학교 상세 공시(학교알리미 schoolinfo.go.kr OPEN API) — 전교생/학급수/교원수/수업일수.
-- NEIS schoolInfo에 없는 필드라 별도 소스. 학교알리미는 자체 SCHUL_CODE(=source_school_code)를 쓰며
-- NEIS SD_SCHUL_CODE와 다르므로 학교명+주소 매칭으로 school_id를 연결한다(§지시서 6, 2026-07-12 확인).
-- ⚠️ 아직 인증키 미발급 + 사이트 점검중이라 실 필드명 미검증 — ETL이 API응답을 아래 일반 컬럼으로 매핑.
-- 매핑 확정(2026-07-12 실사 + 개발자가이드 코드표): 전교생/학급수=apiType 09(학년별·학급별학생수,
-- COL_S_SUM/COL_C_SUM), 교원수=apiType 22(직위별교원, COL_S=COL_SM+COL_SW), 수업일수/주당시수=apiType 08.
CREATE TABLE IF NOT EXISTS school_details (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  source_school_code TEXT,          -- 학교알리미 SCHUL_CODE (NEIS 코드와 다름, 매칭 추적용)
  student_count INTEGER,            -- 전교생 수 (apiType09 COL_S_SUM)
  male_count INTEGER,               -- 남학생 수 (apiType63 COL_MSUM, 특수학급 포함 → student_count와 합 일치)
  female_count INTEGER,             -- 여학생 수 (apiType63 COL_WSUM)
  class_count INTEGER,              -- 학급 수 (apiType09 COL_C_SUM)
  teacher_count INTEGER,            -- 교원 수 (apiType22 COL_S)
  school_days INTEGER,              -- 수업일수 대표값 (apiType08 학년별 최댓값)
  week_class_hours INTEGER,         -- 주당 총 수업시수 (apiType08 WEEK_TOT_ITRT_HR_FGR)
  grade_breakdown TEXT,             -- JSON [{grade, students, classes, school_days}, ...] (상세정보/학사일정 탭용)
  -- 방과후학교(apiType59) — 강좌 목록이 아니라 집계치라 요약 필드로만 저장(2026-07-12 재설계).
  afterschool_program_count INTEGER, -- SUM_ASL_PGM_FGR (방과후 프로그램 수)
  afterschool_student_count INTEGER, -- ASL_PTPT_STDNT_FGR (참여 학생 수, 실인원)
  care_class_yn TEXT,               -- 돌봄교실 운영여부 Y/N (ECC 운영학급수>0)
  disclosure_round TEXT,            -- 공시 차수(연 단위)
  last_synced_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_school_details_school ON school_details (school_id);

-- (폐기 2026-07-12) afterschool_courses(강좌 목록) — apiType59가 강좌목록이 아니라 집계치라
-- school_details의 afterschool_* 컬럼으로 대체함. 재생성 금지.

-- 일자별 급식 (mealServiceDietInfo) — 초중고 전용, 유치원 데이터 없음
-- dishes_parsed: dishes 원문("옥수수밥 <br/>근대된장국 (5.6.18)<br/>...")을 요리명+알레르기번호 배열로
-- 구조화한 JSON([{name, allergens:[5,6,18]}, ...]). 자녀 알레르기 하이라이트 기능(유료, 클라이언트 매칭)에서
-- 사용 예정 — 서버에는 알레르기 "번호"만 있고 사용자의 실제 알레르기 정보는 저장하지 않음(§결정로그 7 B안).
CREATE TABLE IF NOT EXISTS meals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  meal_date TEXT NOT NULL,          -- MLSV_YMD (YYYYMMDD)
  meal_type_code TEXT NOT NULL,     -- MMEAL_SC_CODE (1=조식/2=중식/3=석식)
  meal_type_name TEXT NOT NULL,     -- MMEAL_SC_NM
  dishes TEXT NOT NULL,             -- DDISH_NM (원문, <br/>구분자 유지)
  dishes_parsed TEXT,               -- JSON [{name, allergens:[int,...]}, ...]
  calorie_info TEXT,                -- CAL_INFO
  origin_info TEXT,                 -- ORPLC_INFO
  nutrition_info TEXT,              -- NTR_INFO
  last_synced_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_meals_school_date_type ON meals (school_id, meal_date, meal_type_code);
CREATE INDEX IF NOT EXISTS idx_meals_date ON meals (meal_date);

-- 학년·반·교시별 시간표 (els/mis/hisTimetable) — 초중고 전용, 학기 단위 스냅샷
-- 주의: 원천 API에 (school,ay,sem,grade,class,date,period) 완전 중복 행이 존재함(2026-07-12 신일고 실사로 확인,
-- 원인 미상). fetch_timetables.py에서 dedup 후 적재.
-- 주의: 공휴일에도 시간표 행이 채워져서 옴(ITRT_CNTNT에 공휴일명이 들어감, 예: "제헌절").
-- 화면 표시 전 academic_schedules의 휴업일 여부와 교차 검증 필수(ETL 단계에서는 원문 그대로 적재).
-- 주의: 고교 선택과목(이동수업) 시간에는 CLASS_NM이 NULL이고 CLRM_NM(강의실명)만 채워짐
-- (2026-07-12 신일고 2학년 실사로 확인). class_name을 NULLABLE로 두고 유니크 인덱스에
-- classroom_name까지 포함해 구분한다.
CREATE TABLE IF NOT EXISTS timetables (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  school_year TEXT NOT NULL,        -- AY
  semester TEXT NOT NULL,           -- SEM
  day_night TEXT,                   -- DGHT_CRSE_SC_NM (주간/야간, 중·고만 존재)
  track_name TEXT,                  -- ORD_SC_NM (계열: 일반계/특성화 등, 고교만 존재)
  department_name TEXT,             -- DDDEP_NM (학과명, 고교만 존재)
  classroom_name TEXT,              -- CLRM_NM (교실명, 고교 선택과목 시간엔 class_name 대신 이 필드로 식별)
  weekday INTEGER NOT NULL,         -- 1=월 … 5=금. 시간표는 학기 내 주 단위로 반복되므로 날짜가 아닌 요일로 1벌만 저장.
  grade TEXT NOT NULL,              -- GRADE
  class_name TEXT,                  -- CLASS_NM (반) — 고교 선택과목 시간엔 NULL일 수 있음
  period TEXT NOT NULL,             -- PERIO (교시)
  subject TEXT NOT NULL,            -- ITRT_CNTNT
  last_synced_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_timetables_lookup
  ON timetables (school_id, school_year, semester, grade, weekday, period,
                 COALESCE(class_name, ''), COALESCE(classroom_name, ''));
CREATE INDEX IF NOT EXISTS idx_timetables_school_class ON timetables (school_id, grade, COALESCE(class_name, ''));

-- 시간표 수정(오버라이드) — 유료 사용자가 보강·변경을 직접 반영. 반 단위 공개(같은 학교·학년·반의
-- 다른 유료 사용자에게도 보임). 개인별이 아니라 학교+학년+반+요일+교시 단위. worker가 직접 쓰는
-- 데이터(sync_to_d1 대상 아님). 요일 기반이라 한 번 고치면 매주 그 요일에 계속 반영된다.
CREATE TABLE IF NOT EXISTS timetable_overrides (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  grade TEXT NOT NULL,
  class_name TEXT,                  -- 반(NULL 가능 → COALESCE로 매칭)
  weekday INTEGER NOT NULL,         -- 1=월 … 5=금
  period TEXT NOT NULL,             -- 교시
  subject TEXT NOT NULL,            -- 수정된 과목명
  edited_by TEXT NOT NULL,          -- owner_token (악용 추적용, 화면 미노출)
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_timetable_overrides_lookup
  ON timetable_overrides (school_id, grade, COALESCE(class_name, ''), weekday, period);

-- 개인 스케줄러 — 부모가 하교 후 학원·방과후 등 개인 일정을 시간표에 직접 추가(본인 자녀에게만 보임).
-- 학교 시간표 오버라이드(반 공개)와 달리 owner_token+child_id로 비공개. weekday 1~5(월~금).
-- worker-owned(sync 대상 아님). 자녀 삭제/학년전환 시 정리 대상.
CREATE TABLE IF NOT EXISTS personal_schedule (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token TEXT NOT NULL,
  child_id INTEGER NOT NULL,
  weekday INTEGER NOT NULL,          -- 1=월 ~ 5=금
  period INTEGER NOT NULL,           -- 교시(하교 후 8~10 등 포함)
  label TEXT NOT NULL,              -- 예: "수학학원", "태권도"
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_personal_sched ON personal_schedule (child_id, weekday, period);

-- 학사일정 달력의 "내 일정"(개인 이벤트) — 사용자가 직접 넣는 연·월 스케줄(가족여행·학원설명회 등).
-- 자녀(child_id) 소유, 학교 일정과 함께 달력에 표시. worker-owned(sync 제외).
CREATE TABLE IF NOT EXISTS personal_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token TEXT NOT NULL,
  child_id INTEGER NOT NULL,
  event_date TEXT NOT NULL,          -- YYYYMMDD
  label TEXT NOT NULL,               -- 예: "가족여행", "학원 설명회"
  detail TEXT,                       -- 상세내용(예: "제주도 여행 3인") — 일정 이름 클릭 시 하단에서 입력
  remind_at TEXT,                    -- 알림 발송 시각(UTC ISO). 사용자가 KST 날짜+시간 지정 → UTC로 저장. NULL=알림 없음
  remind_sent INTEGER NOT NULL DEFAULT 0, -- 발송 완료 플래그(중복 발송 방지). 시각/내용 변경 시 0으로 리셋
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_personal_events_remind ON personal_events (remind_sent, remind_at);

-- 학사일정 롤링 자동 갱신 상태 — 매분 크론이 "30일 지난 학교"를 3곳씩 NEIS에서 다시 받아 교체.
-- 전국 1바퀴 ≈ 3일. 학교당 마지막 갱신 시각만 기록(2.2M 행 스캔 없이 싼 조회). worker-owned.
CREATE TABLE IF NOT EXISTS sync_state (
  school_id INTEGER PRIMARY KEY,
  schedules_synced_at TEXT           -- NULL=미시도(신규 학교 → 최우선 갱신)
);
CREATE INDEX IF NOT EXISTS idx_personal_events ON personal_events (child_id, event_date);

-- 교시/점심 시간 개인 설정 — 자녀별로 벨스케줄을 직접 조정(예: 3교시 후 점심, 4교시 12:00 시작).
-- settings_json = {periods:{"1":{s,e},...}, lunch:{after,s,e}}. 없으면 학교급 표준 사용. worker-owned.
CREATE TABLE IF NOT EXISTS schedule_settings (
  child_id INTEGER PRIMARY KEY,
  owner_token TEXT NOT NULL,
  settings_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- 학사일정 (SchoolSchedule) — 초중고 전용
CREATE TABLE IF NOT EXISTS academic_schedules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  event_date TEXT NOT NULL,         -- AA_YMD
  event_name TEXT NOT NULL,         -- EVENT_NM
  event_content TEXT,               -- EVENT_CNTNT
  closure_type TEXT,                -- SBTR_DD_SC_NM (휴업일/공휴일 등)
  grade_flags TEXT NOT NULL,        -- JSON 배열, 학년별 대상여부 원문 유지
  last_synced_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_academic_schedules_lookup ON academic_schedules (school_id, event_date, event_name);
CREATE INDEX IF NOT EXISTS idx_academic_schedules_school_date ON academic_schedules (school_id, event_date);

-- ============================================================
-- 유치원 (유치원알리미)
-- ============================================================

-- 유치원 기관정보 (basicInfo2)
CREATE TABLE IF NOT EXISTS kindergartens (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kinder_code TEXT NOT NULL UNIQUE,   -- kindercode (UUID 형태)
  office_edu TEXT NOT NULL,           -- officeedu
  suboffice_edu TEXT,                 -- subofficeedu
  name TEXT NOT NULL,                 -- kindername
  establish_type TEXT NOT NULL,       -- establish
  address TEXT,                       -- addr
  phone TEXT,                         -- telno
  fax TEXT,                           -- faxno
  homepage TEXT,                      -- hpaddr
  operating_hours TEXT,               -- opertime
  class_count_age3 INTEGER,           -- clcnt3
  class_count_age4 INTEGER,           -- clcnt4
  class_count_age5 INTEGER,           -- clcnt5
  class_count_mixed INTEGER,          -- mixclcnt
  class_count_special INTEGER,        -- shclcnt
  pupil_count_age3 INTEGER,           -- ppcnt3
  pupil_count_age4 INTEGER,           -- ppcnt4
  pupil_count_age5 INTEGER,           -- ppcnt5
  pupil_count_mixed INTEGER,          -- mixppcnt
  pupil_count_special INTEGER,        -- shppcnt
  director_name TEXT,                 -- ldgrname
  lat REAL,                           -- lttdcdnt
  lng REAL,                           -- lngtcdnt
  disclosure_round TEXT NOT NULL,     -- pbnttmng
  slug TEXT NOT NULL,
  last_synced_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kindergartens_region ON kindergartens (office_edu, suboffice_edu);
CREATE INDEX IF NOT EXISTS idx_kindergartens_name ON kindergartens (name);
CREATE INDEX IF NOT EXISTS idx_kindergartens_geo ON kindergartens (lat, lng);
CREATE INDEX IF NOT EXISTS idx_kindergartens_slug ON kindergartens (slug);

-- 유치원 공시 통계 (schoolMeal + schoolBus + afterSchoolPresent 병합, 공시차수 단위 — 일자별 아님)
CREATE TABLE IF NOT EXISTS kindergarten_disclosures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kindergarten_id INTEGER NOT NULL REFERENCES kindergartens(id),
  disclosure_round TEXT NOT NULL,      -- pbnttmng

  meal_operation_type TEXT,            -- mlsr_oprn_way_tp_cd
  meal_vendor_name TEXT,               -- cons_ents_nm
  meal_total_pupils INTEGER,           -- al_kpcnt
  meal_served_pupils INTEGER,          -- mlsr_kpcnt
  nutrition_teacher_assigned TEXT,     -- ntrt_tchr_agmt_yn

  bus_operating TEXT,                  -- vhcl_oprn_yn
  bus_operating_count INTEGER,         -- opra_vhcnt
  bus_registered_count INTEGER,        -- dclr_vhcnt

  afterschool_class_count INTEGER,     -- pm_rrgn_clcnt
  afterschool_operating_hours TEXT,    -- oper_time
  afterschool_pupil_count INTEGER,     -- pm_rrgn_ptcn_kpcnt

  last_synced_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_kinder_disclosures_lookup
  ON kindergarten_disclosures (kindergarten_id, disclosure_round);

-- ============================================================
-- 유료 백엔드 선작업 (2026-07-12, 비공개 라우트 `/mypage/*` 전용 — §5 참고)
-- 유치원은 1차 범위에서 완전 제외되어 kindergarten_id 참조 없음.
-- 로그인 계정 없이 브라우저 로컬 저장 owner_token(랜덤 UUID, 쿠키)으로 자녀 목록을 구분.
-- 결제 기록(1차 더미 결제) — PG 승인 전까지 DB에만 기록하고 자녀 이용기간(만료일) 연장.
-- worker-owned(sync 제외). new_expiry = 이 결제로 이어붙인 만료일. status: paid/refunded.
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token TEXT NOT NULL,
  child_count INTEGER NOT NULL,
  months INTEGER NOT NULL,
  amount INTEGER NOT NULL,
  method TEXT NOT NULL,              -- card / phone / vbank
  auto_renew INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'paid',
  new_expiry TEXT,
  payer_name TEXT,                   -- 결제자 이름 — 실제 PG 연동 시 결제사가 주는 이름 저장(더미 결제 땐 NULL). 없으면 계정 닉네임/토큰으로 표시.
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_payments_owner ON payments (owner_token, created_at);

-- 알림 설정(웹푸시) — 신청/해제 상태. worker-owned.
CREATE TABLE IF NOT EXISTS notif_settings (
  owner_token TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
-- 웹푸시 구독(브라우저 PushSubscription) — VAPID 발송 대상. endpoint 유니크. worker-owned.
CREATE TABLE IF NOT EXISTS push_subscriptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token TEXT NOT NULL,
  endpoint TEXT NOT NULL UNIQUE,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_push_owner ON push_subscriptions (owner_token);
-- ============================================================

-- 등록 자녀 — 이름 미수집, 학교+학년+반+별명만 저장 (개인정보 최소화, §결정로그 6)
-- 무료 등록 시 1주일 자동 체험(trial_expires_at = 등록+7일). is_test=1은 관리자 QA용(만료 없이 잠금해제).
-- 유료 판정: is_test=1 이거나 trial_expires_at > now 이면 해당 학교 상세가 잠금 해제(§백엔드지시서 2026-07-12).
CREATE TABLE IF NOT EXISTS children (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token TEXT NOT NULL,        -- 브라우저 쿠키에 저장되는 랜덤 식별자 (로그인 없음)
  school_id INTEGER NOT NULL REFERENCES schools(id),
  grade TEXT NOT NULL,
  class_name TEXT,
  nickname TEXT NOT NULL,           -- 사용자 자유입력 (예: "첫째")
  is_test INTEGER NOT NULL DEFAULT 0, -- 관리자 테스트 등록(결제 없이 잠금해제, 목록에 "테스트" 뱃지)
  trial_expires_at TEXT,            -- 무료 1주일 체험 만료(ISO). 이후 자동 잠금(자동결제 안 함)
  grade_promoted INTEGER NOT NULL DEFAULT 0, -- 새 학년도 전환(다음 학년 승급)을 1회 사용했는지
  community_nickname TEXT,          -- 커뮤니티 전용 고정 닉네임(자녀 프로필 닉네임과 별개, §지시서D10). 비우면 익명
  community_nickname_changed_at TEXT, -- 마지막 변경일(ISO). +30일 경과해야 재변경 가능
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_children_owner ON children (owner_token);

-- ============================================================
-- 관리자 페이지 (2026-07-12, `/admin` — 대표님 전용 운영 도구, Basic Auth)
-- ============================================================

-- ETL 실패 로그 — Python 스크립트가 NEIS/유치원알리미 호출 실패 시 기록(local sqlite → sync_to_d1.py로 D1 반영)
CREATE TABLE IF NOT EXISTS etl_error_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,             -- 예: fetch_meals, fetch_timetables
  target_school_id INTEGER,         -- REFERENCES schools(id), 학교 단위 실패가 아니면 NULL
  error_message TEXT NOT NULL,
  occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_etl_error_log_time ON etl_error_log (occurred_at);

-- ETL 실행(특히 전국 단위 배치) 진행률 추적용
CREATE TABLE IF NOT EXISTS etl_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_name TEXT NOT NULL,           -- 예: fetch_schools_nationwide
  total INTEGER,
  completed INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'done', 'failed')),
  started_at TEXT NOT NULL,
  finished_at TEXT
);

-- 수동 데이터 보정 이력 — NEIS 원본이 비었거나 틀렸을 때 관리자가 직접 고친 기록.
-- 나중에 NEIS가 갱신되면서 수동 수정이 덮어써지는 문제를 추적하기 위함(§관리자페이지 지시서 2번).
CREATE TABLE IF NOT EXISTS admin_edit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,         -- meals / timetables / academic_schedules
  record_id INTEGER NOT NULL,
  field_name TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  edited_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_edit_log_record ON admin_edit_log (table_name, record_id);

-- 정보 오류 신고 — 실제 재학생·학부모가 상세정보(학급수/학생수 등)가 실제와 다를 때 제보.
-- 학교알리미 공시 시점과 실제 편성 사이 시차 등으로 값이 어긋날 수 있어(§지시서 대응3),
-- 사용자 제보를 모아 관리자가 검토. 개인정보 수집 안 함(연락처·이름 없음). worker-owned(sync 제외).
CREATE TABLE IF NOT EXISTS info_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  category TEXT,                     -- 학급수 / 학생수 / 시간표 / 급식 / 기타
  message TEXT NOT NULL,             -- 사용자 제보 내용(자유 서술)
  owner_token TEXT,                  -- 등록 사용자면 참고용(선택), 없으면 NULL
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_info_reports_school ON info_reports (school_id, created_at);

-- 베타 의견 — 특정 학교와 무관한 서비스 전반 의견/버그/제안 접수(info_reports는 school_id NOT NULL이라 분리).
-- 개인정보 수집 안 함(연락처·이름 없음). worker-owned(sync 제외).
CREATE TABLE IF NOT EXISTS beta_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT,                     -- 불편·버그 / 기능 제안 / 칭찬 / 기타
  message TEXT NOT NULL,             -- 의견 내용(자유 서술)
  owner_token TEXT,                  -- 등록 사용자면 참고용(선택), 없으면 NULL
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_beta_feedback_created ON beta_feedback (created_at);

-- 무료체험 사용 이력 — 계정(owner_token) 단위로 "무료체험을 이미 1회 썼는지" 영구 기록.
-- children 행은 삭제될 수 있으므로 자녀 수로 판정하면 삭제 후 재체험 허점이 생김 → 이 테이블은
-- 최초 무료 등록 시 1회 기록되고 절대 삭제하지 않는다(계정당 무료체험 1회). worker-owned(sync 제외).
CREATE TABLE IF NOT EXISTS free_trials (
  owner_token TEXT PRIMARY KEY,
  first_used_at TEXT NOT NULL
);

-- 소셜 로그인 계정(카카오·구글·네이버) — 회원가입 없이 쓰던 익명 쿠키(owner_token)를 계정에 묶어
-- 다기기에서 복원하는 용도. 데이터 키는 계속 owner_token이라 기존 테이블(children 등)은 무변경.
-- 최초 로그인 시 현재 기기의 owner_token을 계정에 채택(익명 데이터 승계), 이후 로그인은 그 토큰을 복원.
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,            -- kakao | google | naver
  provider_uid TEXT NOT NULL,        -- 각 사 회원 고유번호(이메일·전화 수집 안 함 — 심사 불필요 범위)
  nickname TEXT,                     -- 표시용 닉네임(각 사 프로필)
  owner_token TEXT NOT NULL,         -- 이 계정의 데이터 키
  created_at TEXT NOT NULL,
  last_login_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_identity ON users (provider, provider_uid);
CREATE INDEX IF NOT EXISTS idx_users_owner ON users (owner_token);

-- 학교별 짧은 커뮤니티 글(리뷰형, 1~3줄) — 유료(등록) 사용자만 작성, 댓글/이미지/링크 없음.
-- worker-owned(sync 제외, children/banners와 동일하게 로컬 재적재 대상에서 제외해야 함).
CREATE TABLE IF NOT EXISTS community_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  child_id INTEGER NOT NULL REFERENCES children(id),  -- 작성자(등록 자녀) — paid 판정과 동일 기준
  owner_token TEXT NOT NULL,                          -- 작성자 본인 삭제 권한 확인용 + 도배 방지 식별
  display_name TEXT,                                  -- 작성 당시 커뮤니티 닉네임 스냅샷(§지시서D11). 없으면 "익명"
  author_grade TEXT,                                  -- 작성 당시 학년 박제(§지시서D13, 이후 승급돼도 글은 그대로)
  author_class TEXT,                                  -- 작성 당시 반 박제
  body TEXT NOT NULL,                                 -- 1~3줄, 최대 90자. 욕설은 서버에서 마스킹 후 저장
  report_count INTEGER NOT NULL DEFAULT 0,
  hidden INTEGER NOT NULL DEFAULT 0,                   -- 신고 3회 누적 시 자동 숨김(1)
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_community_posts_school ON community_posts (school_id, created_at);

-- 글 신고 — 같은 사용자가 같은 글을 중복 신고해 혼자 숨김시키는 것을 막기 위해 (post_id, owner_token) 유니크.
CREATE TABLE IF NOT EXISTS community_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER NOT NULL REFERENCES community_posts(id),
  owner_token TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (post_id, owner_token)
);

-- 광고 배너 (7슬롯: 애드센스/쿠팡파트너스/하우스배너 2종/B2B 학원광고 2종 — §학교상세페이지 디자인지시서)
CREATE TABLE IF NOT EXISTS banners (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slot INTEGER NOT NULL,                    -- 1~7 (디자인 지시서 슬롯 번호)
  banner_type TEXT NOT NULL CHECK (banner_type IN ('adsense', 'coupang', 'house', 'b2b')),
  code_snippet TEXT,                        -- adsense/coupang용 코드 스니펫
  image_url TEXT,                           -- house/b2b용 이미지
  link_url TEXT,                            -- house/b2b용 링크
  alt_text TEXT,
  advertiser_name TEXT,                     -- b2b 학원명
  region_office_code TEXT,                  -- b2b 노출 지역 제한(교육청코드, 예: B10). NULL이면 전체 노출
  starts_at TEXT,                           -- b2b 노출 시작일
  ends_at TEXT,                             -- b2b 노출 종료일
  paid INTEGER NOT NULL DEFAULT 0,          -- 결제 여부(수동 체크, 결제 연동은 범위 밖)
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_banners_lookup ON banners (slot, active, region_office_code);
