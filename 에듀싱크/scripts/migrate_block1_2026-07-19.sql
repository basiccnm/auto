-- ============================================================
-- 블록1 「자녀기록」 마이그레이션 — 2026-07-19
-- 근거: docs/블록1-지시서-v4.md 3절 · docs/로드맵-DB마스터-v3.md 4.2
--
-- 원칙: add-only. 기존 테이블 DROP 없음, 기존 컬럼 의미 변경 없음.
-- 보존: children / payments / free_trials / users / personal_schedule
--        / personal_events / schedule_settings / community_posts 등 전부 그대로.
--
-- 실행: npx wrangler d1 execute eduthink-db --remote --file=scripts/migrate_block1_2026-07-19.sql
-- ※ --local 로 먼저 검증 후 --remote 권장.
-- ============================================================


-- ------------------------------------------------------------
-- 1) children 확장 (add-only 2컬럼)
-- ------------------------------------------------------------
-- birth_year : 출생연도(선택). 블록2 발달 AI용 자리. NULL 허용.
-- consent_at : 보호자 동의 시각(ISO8601). 자녀기록 기능 사용 전제.
--              기존 자녀는 NULL → 기록 기능 첫 진입 시 동의를 받고 채운다.
ALTER TABLE children ADD COLUMN birth_year INTEGER;
ALTER TABLE children ADD COLUMN consent_at TEXT;

-- ※ trial_expires_at 의미 명시 (rename 하지 않음 — add-only 원칙, 2026-07-19 결정):
--    컬럼명은 "체험 만료일"이지만 실제 의미는 **이용권 만료일**이다.
--    1주일 무료체험·기간권 결제 연장 모두 이 컬럼 하나로 관리한다.
--    passes 테이블은 신설하지 않는다(조사 결과 기존 구조로 충분 — 조사보고 1절).


-- ------------------------------------------------------------
-- 2) identifiers — 식별자 분리 테이블 (보안 핵심)
-- ------------------------------------------------------------
-- 자녀 실명은 오직 이 테이블에만 존재한다.
-- records/activity_schedules/children/로그/분석 어디에도 이름을 저장하지 않는다.
--
-- 접근 규칙(지시서 v4 3절):
--   · name은 전용 접근 계층(단일 모듈/함수)을 통해서만 읽고 쓴다
--   · 일반 쿼리에서 identifiers 직접 조인 금지 — 화면 표시 시점에만 조인
--   · **이름 검색용 인덱스를 만들지 않는다** (인덱스는 child_id = PK 뿐)
--   · 광고/분석 코드는 이 테이블 접근 경로 자체가 없어야 함
CREATE TABLE IF NOT EXISTS identifiers (
  child_id   INTEGER PRIMARY KEY REFERENCES children(id),  -- unique 겸용
  name       TEXT NOT NULL,
  created_at TEXT NOT NULL
);
-- (의도적으로 name 인덱스 없음)


-- ------------------------------------------------------------
-- 3) records — 기록(이미지) 메타데이터
-- ------------------------------------------------------------
-- category    : award | report_card | grade_sheet | certificate | activity | other
-- school_year : 정수 코드 — 초1=1…초6=6, 중1=7…중3=9, 고1=10…고3=12, 유치원 0 예약
-- semester    : 1 | 2
-- image_key   : R2 오브젝트 키. **연번이 아닌 랜덤 UUID를 넣는다**(경로 추측 방지).
--               id는 INTEGER AUTOINCREMENT(기존 코드 컨벤션)로 두되,
--               외부에 노출되는 스토리지 경로는 이 키를 쓴다.
-- 원본 이미지는 불변, 메타데이터만 수정 가능 → 별도 이력 테이블 없음(지시서 v2·v4).
CREATE TABLE IF NOT EXISTS records (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id    INTEGER NOT NULL REFERENCES children(id),
  category    TEXT NOT NULL CHECK (category IN ('award','report_card','grade_sheet','certificate','activity','other')),
  school_year INTEGER NOT NULL,
  semester    INTEGER NOT NULL CHECK (semester IN (1,2)),
  title       TEXT NOT NULL,
  note        TEXT,
  image_key   TEXT NOT NULL UNIQUE,
  bytes       INTEGER,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
-- 타임라인 기본 조회: 자녀별 → 학년·학기 내림차순
CREATE INDEX IF NOT EXISTS idx_records_child_period ON records (child_id, school_year DESC, semester DESC, id DESC);
-- 종류 필터
CREATE INDEX IF NOT EXISTS idx_records_child_cat ON records (child_id, category);


-- ------------------------------------------------------------
-- 4) activity_schedules — 학원·방과후·활동 (신규 정본)
-- ------------------------------------------------------------
-- 기존 personal_schedule(교시 개인일정, 최대 4행)은 건드리지 않고 유지한다.
-- 데이터 이전 없음 — 표시만 기존대로 유지(지시서 v4 1-6, A-2/A-3).
--
-- type         : academy | afterschool | activity
-- days_of_week : 요일 CSV. 1=월 … 7=일  (예: "1,3" = 월·수)
-- start_date/end_date : 유효기간. 방학 특강과 학기 정규 학원을 같은 구조로 담는 핵심.
--                       종료일이 지나면 주간 뷰·시간표 요약줄에서 자동으로 사라진다.
CREATE TABLE IF NOT EXISTS activity_schedules (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id     INTEGER NOT NULL REFERENCES children(id),
  type         TEXT NOT NULL CHECK (type IN ('academy','afterschool','activity')),
  name         TEXT NOT NULL,
  days_of_week TEXT NOT NULL,
  start_time   TEXT NOT NULL,
  end_time     TEXT NOT NULL,
  start_date   TEXT NOT NULL,
  end_date     TEXT NOT NULL,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);
-- 주간 뷰·시간표 요약줄: 자녀 + 유효기간 필터
CREATE INDEX IF NOT EXISTS idx_actsched_child_range ON activity_schedules (child_id, end_date, start_date);


-- ------------------------------------------------------------
-- 5) app_state — 1회성 배치 실행 기록 (전환일 체험 일괄 재부여용)
-- ------------------------------------------------------------
-- 2026-07-19 결정(Q2=A-2): 유료 전환일이 되면 전원에게 체험 7일을 일괄 재부여한다.
-- **1회성 보장 필수** — 매 요청/매 크론마다 갱신되면 영원히 잠기지 않는다.
--
-- 동작(크론, 이미 매분 실행 중인 트리거 재사용):
--   1. now >= FREE_OPEN_UNTIL 인가?
--   2. app_state에 'free_open_regrant_at' 행이 있는가? → 있으면 아무것도 안 함(재실행 금지)
--   3. 없으면: children SET trial_expires_at = now+7d WHERE is_test = 0
--              → 그 후 app_state에 실행 시각 기록
--   ※ 전환일이 지났는데 미실행이면 다음 크론에서 실행된다(크론 장애 대비).
--   ※ free_trials의 계정당 1회 차단은 **이 일괄 재부여에 한해 무시**한다.
--   ※ 대상은 is_test = 0 인 실제 자녀만.
CREATE TABLE IF NOT EXISTS app_state (
  key        TEXT PRIMARY KEY,
  value      TEXT,
  updated_at TEXT NOT NULL
);


-- ------------------------------------------------------------
-- 6) 예약 자리 (테이블 생성하지 않음 — 주석으로만 예약)
-- ------------------------------------------------------------
-- grades         : 블록1.5 — grade_id, record_id(FK: 원본 이미지 근거), child_id,
--                  subject, score_type(점수|등급|성취도), value, school_year, semester
--                  → 모든 성적 숫자가 원본 이미지에 연결 = AI 환각 방지의 바닥
-- knowledge_base : 블록2 — kb_id, age_band, topic, content, source(근거 출처 필수)
-- reports        : 블록3 — report_id, child_id, period, content_ref, generated_at
-- memories       : 블록4 — memory_id, child_id, kind(관찰|대화요약), content, source_ref
-- chat_state     : 블록4 — child_id, 대화 컨텍스트, updated_at (리셋 시 기본 삭제 대상)
-- guardians      : 결제 고도화 — owner_token, 본인인증 결과(최소), verified_at


-- ============================================================
-- 자녀 삭제 시 파기 대상 (B-11, 지시서 v4 1-13) — 앱 코드에서 처리
-- ============================================================
--   identifiers · records(+ R2 원본) · activity_schedules
--   + 기존 personal_schedule · personal_events · schedule_settings
--   + children 행 자체
-- 순서: R2 객체 삭제 → 자식 테이블 → children
-- (D1은 ON DELETE CASCADE를 쓰지 않고 앱에서 명시 삭제 — 기존 코드 컨벤션 유지)
