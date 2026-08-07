-- 프로덕션 D1 마이그레이션 (2026-07-17 세션 변경분)
-- 보존: schools / children / payments / free_trials / community_posts / notif_settings / push_subscriptions
-- 폐기·재생성: timetables, timetable_overrides (날짜기반 → 요일기반, 프로덕션 overrides 0행이라 손실 없음)
-- 추가: personal_events 컬럼(detail·remind_at·remind_sent), users, sync_state

-- 1) 개인 일정: 상세내용 + 알림 시각(프로덕션 0행이라 ALTER 안전)
ALTER TABLE personal_events ADD COLUMN detail TEXT;
ALTER TABLE personal_events ADD COLUMN remind_at TEXT;
ALTER TABLE personal_events ADD COLUMN remind_sent INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_personal_events_remind ON personal_events (remind_sent, remind_at);

-- 2) 시간표: 날짜별 → 학기 × 요일(월~금) 1벌로 축약(~12배 감소). 기존 행은 방문 시 재수집됨.
DROP TABLE IF EXISTS timetables;
CREATE TABLE timetables (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  school_year TEXT NOT NULL,
  semester TEXT NOT NULL,
  day_night TEXT,
  track_name TEXT,
  department_name TEXT,
  classroom_name TEXT,
  weekday INTEGER NOT NULL,
  grade TEXT NOT NULL,
  class_name TEXT,
  period TEXT NOT NULL,
  subject TEXT NOT NULL,
  last_synced_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_timetables_lookup ON timetables (school_id, school_year, semester, grade, weekday, period, COALESCE(class_name,''), COALESCE(classroom_name,''));
CREATE INDEX idx_timetables_school_class ON timetables (school_id, grade, COALESCE(class_name,''));

-- 3) 시간표 수정(오버라이드): 요일 기준으로 전환(프로덕션 0행 확인)
DROP TABLE IF EXISTS timetable_overrides;
CREATE TABLE timetable_overrides (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  grade TEXT NOT NULL,
  class_name TEXT,
  weekday INTEGER NOT NULL,
  period TEXT NOT NULL,
  subject TEXT NOT NULL,
  edited_by TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_timetable_overrides_lookup ON timetable_overrides (school_id, grade, COALESCE(class_name,''), weekday, period);

-- 4) 소셜 로그인 계정(카카오·구글) — owner_token 매핑으로 다기기 복원
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  provider_uid TEXT NOT NULL,
  nickname TEXT,
  owner_token TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_identity ON users (provider, provider_uid);
CREATE INDEX IF NOT EXISTS idx_users_owner ON users (owner_token);

-- 5) 학사일정 롤링 자동 갱신 상태
CREATE TABLE IF NOT EXISTS sync_state (
  school_id INTEGER PRIMARY KEY,
  schedules_synced_at TEXT
);
