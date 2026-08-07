PRAGMA defer_foreign_keys=TRUE;
CREATE TABLE schools (
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
  slug TEXT NOT NULL,
  last_synced_at TEXT NOT NULL
, founded_ymd TEXT, est_type TEXT, coedu TEXT, sem2_start TEXT);
CREATE TABLE meals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  meal_date TEXT NOT NULL,          -- MLSV_YMD (YYYYMMDD)
  meal_type_code TEXT NOT NULL,     -- MMEAL_SC_CODE (1=조식/2=중식/3=석식)
  meal_type_name TEXT NOT NULL,     -- MMEAL_SC_NM
  dishes TEXT NOT NULL,             -- DDISH_NM (원문, <br/>구분자 유지)
  calorie_info TEXT,                -- CAL_INFO
  origin_info TEXT,                 -- ORPLC_INFO
  nutrition_info TEXT,              -- NTR_INFO
  last_synced_at TEXT NOT NULL
, dishes_parsed TEXT);
CREATE TABLE academic_schedules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  event_date TEXT NOT NULL,         -- AA_YMD
  event_name TEXT NOT NULL,         -- EVENT_NM
  event_content TEXT,               -- EVENT_CNTNT
  closure_type TEXT,                -- SBTR_DD_SC_NM (휴업일/공휴일 등)
  grade_flags TEXT NOT NULL,        -- JSON 배열, 학년별 대상여부 원문 유지
  last_synced_at TEXT NOT NULL
);
CREATE TABLE kindergartens (
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
CREATE TABLE kindergarten_disclosures (
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
CREATE TABLE children (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token TEXT NOT NULL,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  grade TEXT NOT NULL,
  class_name TEXT,
  nickname TEXT NOT NULL,
  created_at TEXT NOT NULL
, is_test INTEGER NOT NULL DEFAULT 0, trial_expires_at TEXT, grade_promoted INTEGER NOT NULL DEFAULT 0, community_nickname TEXT, community_nickname_changed_at TEXT, birth_year INTEGER, consent_at TEXT, regranted_at TEXT, consent_method TEXT, family_verify_status TEXT, photo_key TEXT, child_device TEXT, child_device_at TEXT, kid_theme TEXT, kid_accent TEXT);
CREATE TABLE etl_error_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  target_school_id INTEGER,
  error_message TEXT NOT NULL,
  occurred_at TEXT NOT NULL
);
CREATE TABLE etl_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_name TEXT NOT NULL,
  total INTEGER,
  completed INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'running',
  started_at TEXT NOT NULL,
  finished_at TEXT
);
CREATE TABLE admin_edit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL,
  record_id INTEGER NOT NULL,
  field_name TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  edited_at TEXT NOT NULL
);
CREATE TABLE banners (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slot INTEGER NOT NULL,
  banner_type TEXT NOT NULL,
  code_snippet TEXT,
  image_url TEXT,
  link_url TEXT,
  alt_text TEXT,
  advertiser_name TEXT,
  region_office_code TEXT,
  starts_at TEXT,
  ends_at TEXT,
  paid INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE school_details (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  school_id INTEGER NOT NULL REFERENCES schools(id),
  source_school_code TEXT,
  student_count INTEGER, class_count INTEGER, teacher_count INTEGER, school_days INTEGER,
  disclosure_round TEXT, last_synced_at TEXT NOT NULL
, week_class_hours INTEGER, grade_breakdown TEXT, afterschool_program_count INTEGER, afterschool_student_count INTEGER, care_class_yn TEXT, male_count INTEGER, female_count INTEGER);
CREATE TABLE info_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER NOT NULL REFERENCES schools(id), category TEXT, message TEXT NOT NULL, owner_token TEXT, status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved')), created_at TEXT NOT NULL);
CREATE TABLE personal_schedule (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_token TEXT NOT NULL, child_id INTEGER NOT NULL, weekday INTEGER NOT NULL, period INTEGER NOT NULL, label TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE schedule_settings (child_id INTEGER PRIMARY KEY, owner_token TEXT NOT NULL, settings_json TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_token TEXT NOT NULL, child_count INTEGER NOT NULL, months INTEGER NOT NULL, amount INTEGER NOT NULL, method TEXT NOT NULL, auto_renew INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'paid', new_expiry TEXT, created_at TEXT NOT NULL, payer_name TEXT);
CREATE TABLE notif_settings (owner_token TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
CREATE TABLE push_subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_token TEXT NOT NULL, endpoint TEXT NOT NULL UNIQUE, p256dh TEXT NOT NULL, auth TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE community_posts (id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER NOT NULL REFERENCES schools(id), child_id INTEGER NOT NULL REFERENCES children(id), owner_token TEXT NOT NULL, body TEXT NOT NULL, report_count INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, display_name TEXT, author_grade TEXT, author_class TEXT);
CREATE TABLE community_reports (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER NOT NULL REFERENCES community_posts(id), owner_token TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE (post_id, owner_token));
CREATE TABLE free_trials (owner_token TEXT PRIMARY KEY, first_used_at TEXT NOT NULL);
CREATE TABLE personal_events (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_token TEXT NOT NULL, child_id INTEGER NOT NULL, event_date TEXT NOT NULL, label TEXT NOT NULL, created_at TEXT NOT NULL, detail TEXT, remind_at TEXT, remind_sent INTEGER NOT NULL DEFAULT 0, start_time TEXT);
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
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  provider_uid TEXT NOT NULL,
  nickname TEXT,
  owner_token TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);
CREATE TABLE sync_state (
  school_id INTEGER PRIMARY KEY,
  schedules_synced_at TEXT
);
CREATE TABLE beta_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT,
  message TEXT NOT NULL,
  owner_token TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
  created_at TEXT NOT NULL
);
CREATE TABLE identifiers (
  child_id   INTEGER PRIMARY KEY REFERENCES children(id),  -- unique 겸용
  name       TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE records (
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
CREATE TABLE activity_schedules (
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
CREATE TABLE app_state (
  key        TEXT PRIMARY KEY,
  value      TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE accounts (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token    TEXT NOT NULL UNIQUE,
  display_name   TEXT,
  email          TEXT,
  phone          TEXT,
  phone_verified INTEGER NOT NULL DEFAULT 0,
  birth_ymd      TEXT,
  status         TEXT NOT NULL DEFAULT 'active',   -- active | suspended | withdrawn
  created_at     TEXT NOT NULL,
  last_login_at  TEXT
, marketing TEXT, withdrawn_at TEXT);
CREATE TABLE auth_methods (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id   INTEGER NOT NULL REFERENCES accounts(id),
  kind         TEXT NOT NULL,
  identifier   TEXT NOT NULL,
  secret       TEXT,
  verified     INTEGER NOT NULL DEFAULT 0,
  created_at   TEXT NOT NULL,
  last_used_at TEXT
);
CREATE TABLE orders (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id   INTEGER NOT NULL REFERENCES accounts(id),
  child_id     INTEGER REFERENCES children(id),
  months       INTEGER NOT NULL,
  amount       INTEGER NOT NULL,
  method       TEXT NOT NULL,
  status       TEXT NOT NULL,
  payer_name   TEXT,
  external_ref TEXT,          -- PG 거래번호 · IAP 영수증
  confirmed_by TEXT,          -- 입금 확인한 admin
  confirmed_at TEXT,
  activated_at TEXT,
  expires_at   TEXT,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
, provider_token TEXT, payment_channel TEXT DEFAULT 'inapp', child_limit INTEGER DEFAULT 1);
CREATE TABLE revoked_tokens (
  jti        TEXT PRIMARY KEY,
  account_id INTEGER,
  expires_at TEXT NOT NULL,
  revoked_at TEXT NOT NULL
);
CREATE TABLE login_attempts (
  identifier   TEXT PRIMARY KEY,   -- 로그인 아이디 (있는 아이디든 없는 아이디든 똑같이 센다)
  fails        INTEGER NOT NULL DEFAULT 0,
  first_fail   INTEGER,            -- 이번 실패 묶음이 시작된 시각(epoch 초)
  locked_until INTEGER             -- 이 시각까지 잠금(epoch 초). NULL이면 안 잠김
);
CREATE TABLE documents (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id   INTEGER NOT NULL,
  kind       TEXT NOT NULL,                     -- field 교외체험학습 · absence 결석신고 · counsel 상담신청
  phase      TEXT NOT NULL DEFAULT 'apply',     -- apply 신청서 · report 보고서(교외체험학습만)
  title      TEXT,
  from_ymd   TEXT,                              -- 기간 시작 YYYYMMDD (연 19일 한도 계산에 쓴다)
  to_ymd     TEXT,
  days       INTEGER,                           -- 공휴일 뺀 실제 일수
  payload    TEXT NOT NULL DEFAULT '{}',        -- 서식 값 전체(JSON)
  reported   INTEGER NOT NULL DEFAULT 0,        -- 보고서까지 냈는가(안 내면 미인정 결석)
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id   INTEGER NOT NULL,
  sender     TEXT NOT NULL,                     -- parent | child
  text       TEXT NOT NULL,
  seen_at    TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE child_invites (
  code       TEXT PRIMARY KEY,        -- 6자리 숫자. 짧아서 불러주기 쉽다 — 그래서 10분·1회용이다
  child_id   INTEGER NOT NULL,
  account_id INTEGER NOT NULL,        -- 발급한 부모 계정(감사용)
  expires_at INTEGER NOT NULL,        -- epoch 초
  used_at    TEXT,                    -- 쓰이면 채운다. 한 번 쓰면 끝
  created_at TEXT NOT NULL
);
CREATE TABLE supplies (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_token TEXT NOT NULL,                    -- 다른 계정 것을 못 만지게 하는 열쇠(다른 표와 같은 규칙)
  child_id    INTEGER NOT NULL,
  due_ymd     TEXT NOT NULL,                    -- 챙겨 가는 날 YYYYMMDD
  item        TEXT NOT NULL,                    -- 준비물 이름 (예: 실내화, 리코더)
  memo        TEXT,                             -- 선택 (예: 이름표 붙이기)
  done        INTEGER NOT NULL DEFAULT 0,       -- 챙겼는가
  created_at  TEXT NOT NULL
);
CREATE TABLE record_images (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  record_id  INTEGER NOT NULL REFERENCES records(id),
  ord        INTEGER NOT NULL DEFAULT 0,     -- 0부터. 앞장·뒷장 순서가 곧 이 값
  image_key  TEXT NOT NULL UNIQUE,           -- R2 키. 썸네일은 같은 키 + "_t"
  bytes      INTEGER,
  created_at TEXT NOT NULL
);
CREATE TABLE inquiries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  child_id INTEGER,                    -- 어느 자녀 얘기인지(선택). 자녀가 지워져도 문의는 남는다
  category TEXT NOT NULL DEFAULT 'other',   -- data|record|payment|account|bug|other
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  meta TEXT,                           -- 앱 버전·기기·학교 (JSON) — 「제 폰에선 안 돼요」를 되묻지 않으려고
  contact_email TEXT,                  -- 답을 메일로도 받고 싶을 때만
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'answered', 'closed')),
  answer TEXT,
  answered_at TEXT,
  seen_at TEXT,                        -- 사용자가 답을 읽은 시각 — 안 읽은 답이 있으면 앱이 배지를 띄운다
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE community_members (
  child_id INTEGER PRIMARY KEY REFERENCES children(id) ON DELETE CASCADE,
  owner_token TEXT NOT NULL,
  joined_at TEXT NOT NULL,     -- 이 시각 **이후** 글만 보인다
  agreed_at TEXT NOT NULL,     -- 참여할 때 「지켜야 할 것」에 동의한 시각(구글 UGC 정책 요건)
  left_at TEXT                 -- 나가면 기록. 다시 들어오면 joined_at 이 갱신된다
);
CREATE TABLE community_blocks (
  owner_token TEXT NOT NULL,
  blocked_token TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (owner_token, blocked_token)
);
CREATE TABLE account_devices (
  id TEXT PRIMARY KEY,                -- 토큰에 실리는 기기 식별자(uuid)
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  label TEXT,                         -- 「안드로이드 16 · SM-S911N」 — 내 정보에서 어느 폰인지 알아보게
  created_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL
);
CREATE TABLE community_bans (
  owner_token TEXT PRIMARY KEY,
  until TEXT,                 -- NULL 이면 무기한. 보통은 며칠짜리로 둔다
  reason TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE missions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,          -- 안정된 식별자. 문구가 바뀌어도 이건 안 바꾼다
  band TEXT NOT NULL,                 -- low(초1~2) | mid(초3~4) | high(초5~6)
  season TEXT NOT NULL,               -- weekday | weekend | vacation | patience(기다림)
  title TEXT NOT NULL,                -- 아이가 읽을 문장. 15자 이내, 평어체
  area TEXT NOT NULL,                 -- body|things|study|family|outside|digital|mind|money
  minutes INTEGER NOT NULL DEFAULT 0,
  cycle TEXT NOT NULL DEFAULT 'daily',-- daily | weekly | anytime
  verify TEXT NOT NULL,               -- instant | review | endday
  verify_hint TEXT,                   -- instant면 타이머·접속 방식, review면 「무엇을 찍나」
  slot TEXT NOT NULL DEFAULT 'any',   -- morning | after | evening | any  (유효 시간대)
  stars INTEGER NOT NULL DEFAULT 1,   -- 1~3. 소요시간 기준
  why TEXT,                           -- 왜 이 학년이 확실히 해낼 수 있는지
  caution TEXT,                       -- 「불을 써요」처럼 부모가 **알고** 골라야 하는 것
                                      -- (위험하다고 우리가 미리 빼면 그건 과보호를 강제하는 것이다)
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
, owner_token TEXT);
CREATE TABLE mission_banned (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  reason TEXT NOT NULL
);
CREATE TABLE mission_assign (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  mission_code TEXT NOT NULL,
  ymd TEXT NOT NULL,                  -- 어느 날 것인가 (YYYYMMDD)
  status TEXT NOT NULL DEFAULT 'open',-- open | done | waiting | skipped | undone
  --   waiting = 사진 내고 부모 확인 대기 / skipped = 아이가 「못 했어요」 / undone = 부모가 되돌림
  photo_key TEXT,                     -- R2 키. 승인 7일 뒤 지운다(서랍과 별도)
  claimed_at TEXT,                    -- 아이가 완료를 누른 시각
  decided_at TEXT,                    -- 부모가 확인했거나 자동 승인된 시각
  auto_at TEXT,                       -- 자동 승인 예정 시각(다음날 08:00)
  stars INTEGER NOT NULL DEFAULT 0,   -- 실제로 준 도장
  created_at TEXT NOT NULL,
  UNIQUE (child_id, mission_code, ymd)
);
CREATE TABLE star_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
  delta INTEGER NOT NULL,             -- +획득 / -사용 / 되돌림은 음수
  reason TEXT NOT NULL,               -- mission:<code> | buy:<item> | revert:<code>
  created_at TEXT NOT NULL
);
CREATE TABLE meal_ratings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,               -- 평가한 날 (KST)
  stars INTEGER NOT NULL,          -- 1~5 (오늘 급식이 얼마나 맛있었나)
  created_at TEXT NOT NULL,
  UNIQUE (child_id, ymd)           -- 하루 한 번
);
CREATE TABLE meal_rating_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,
  dish_raw TEXT NOT NULL,          -- 「돈육김치볶음」
  dish_key TEXT NOT NULL,          -- 「돈육김치볶음」(합친 이름)
  dish_cat TEXT NOT NULL,          -- 볶음 | 국물 | 튀김 | 나물 | 김치 | 주식 | …
  rank INTEGER,                    -- 아이가 매긴 순위(1등부터). 안 고르면 NULL
  created_at TEXT NOT NULL
);
CREATE TABLE kid_friends (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (child_id, name)
);
CREATE TABLE play_days (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,
  alone INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  UNIQUE (child_id, ymd)
);
CREATE TABLE play_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE subject_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  child_id INTEGER NOT NULL,
  ymd TEXT NOT NULL,
  subject TEXT NOT NULL,           -- 시간표에 있던 과목명 그대로
  created_at TEXT NOT NULL,
  UNIQUE (child_id, ymd)           -- 하루 한 번
);
CREATE TABLE parent_mission_templates ( template_id TEXT PRIMARY KEY, child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE, title TEXT NOT NULL, stars INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL );
CREATE TABLE store_items ( item_id TEXT PRIMARY KEY, child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE, title TEXT NOT NULL, stars_required INTEGER NOT NULL, limit_type TEXT, limit_count INTEGER, created_at TEXT NOT NULL );
CREATE TABLE reward_orders ( reward_order_id TEXT PRIMARY KEY, child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE, item_id TEXT NOT NULL, item_title TEXT NOT NULL, stars_spent INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'requested', created_at TEXT NOT NULL );
CREATE TABLE reactions ( reaction_id TEXT PRIMARY KEY, child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE, sticker_type TEXT NOT NULL, bonus_stars INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL );
CREATE TABLE mission_verifications ( verify_id TEXT PRIMARY KEY, child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE, mission_code TEXT NOT NULL, step1_data TEXT, step1_granted_at TEXT, step2_approved_at TEXT, step2_bonus_stars INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL );
CREATE TABLE child_mode_config (
  owner_token  TEXT PRIMARY KEY REFERENCES accounts(owner_token) ON DELETE CASCADE,
  pin_hash     TEXT NOT NULL,          -- pbkdf2$반복수$솔트$해시 (auth_core.js 와 같은 형식)
  fail_count   INTEGER NOT NULL DEFAULT 0,   -- 연속 실패. 맞히면 0 으로 되돌린다
  locked_until TEXT,                   -- ISO. 이 시각까지는 맞아도 안 열어 준다
  updated_at   TEXT NOT NULL
);
DELETE FROM sqlite_sequence;
CREATE UNIQUE INDEX idx_schools_office_code ON schools (office_code, school_code);
CREATE INDEX idx_schools_name ON schools (name);
CREATE INDEX idx_schools_slug ON schools (slug);
CREATE UNIQUE INDEX idx_meals_school_date_type ON meals (school_id, meal_date, meal_type_code);
CREATE INDEX idx_meals_date ON meals (meal_date);
CREATE UNIQUE INDEX idx_academic_schedules_lookup ON academic_schedules (school_id, event_date, event_name);
CREATE INDEX idx_academic_schedules_school_date ON academic_schedules (school_id, event_date);
CREATE INDEX idx_kindergartens_region ON kindergartens (office_edu, suboffice_edu);
CREATE INDEX idx_kindergartens_name ON kindergartens (name);
CREATE INDEX idx_kindergartens_geo ON kindergartens (lat, lng);
CREATE INDEX idx_kindergartens_slug ON kindergartens (slug);
CREATE UNIQUE INDEX idx_kinder_disclosures_lookup
  ON kindergarten_disclosures (kindergarten_id, disclosure_round);
CREATE INDEX idx_children_owner ON children (owner_token);
CREATE INDEX idx_etl_error_log_time ON etl_error_log (occurred_at);
CREATE INDEX idx_admin_edit_log_record ON admin_edit_log (table_name, record_id);
CREATE INDEX idx_banners_lookup ON banners (slot, active, region_office_code);
CREATE UNIQUE INDEX idx_school_details_school ON school_details (school_id);
CREATE INDEX idx_info_reports_school ON info_reports (school_id, created_at);
CREATE UNIQUE INDEX idx_personal_sched ON personal_schedule (child_id, weekday, period);
CREATE INDEX idx_payments_owner ON payments (owner_token, created_at);
CREATE INDEX idx_push_owner ON push_subscriptions (owner_token);
CREATE INDEX idx_community_posts_school ON community_posts (school_id, created_at);
CREATE INDEX idx_personal_events ON personal_events (child_id, event_date);
CREATE INDEX idx_personal_events_remind ON personal_events (remind_sent, remind_at);
CREATE UNIQUE INDEX idx_timetables_lookup ON timetables (school_id, school_year, semester, grade, weekday, period, COALESCE(class_name,''), COALESCE(classroom_name,''));
CREATE INDEX idx_timetables_school_class ON timetables (school_id, grade, COALESCE(class_name,''));
CREATE UNIQUE INDEX idx_timetable_overrides_lookup ON timetable_overrides (school_id, grade, COALESCE(class_name,''), weekday, period);
CREATE UNIQUE INDEX idx_users_identity ON users (provider, provider_uid);
CREATE INDEX idx_users_owner ON users (owner_token);
CREATE INDEX idx_beta_feedback_created ON beta_feedback (created_at);
CREATE INDEX idx_records_child_period ON records (child_id, school_year DESC, semester DESC, id DESC);
CREATE INDEX idx_records_child_cat ON records (child_id, category);
CREATE INDEX idx_actsched_child_range ON activity_schedules (child_id, end_date, start_date);
CREATE INDEX idx_schools_sem2 ON schools (sem2_start);
CREATE INDEX idx_children_regrant ON children (regranted_at, is_test);
CREATE UNIQUE INDEX idx_accounts_email ON accounts(email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX idx_auth_kind_ident ON auth_methods(kind, identifier);
CREATE INDEX idx_auth_account ON auth_methods(account_id);
CREATE INDEX idx_orders_account ON orders(account_id, created_at DESC);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_child ON orders(child_id);
CREATE INDEX idx_revoked_exp ON revoked_tokens(expires_at);
CREATE INDEX idx_login_attempts_locked ON login_attempts(locked_until);
CREATE INDEX idx_documents_child ON documents(child_id, id DESC);
CREATE INDEX idx_messages_child ON messages(child_id, id DESC);
CREATE INDEX idx_child_invites_child ON child_invites(child_id);
CREATE INDEX idx_supplies_child ON supplies(child_id, due_ymd, id);
CREATE INDEX idx_record_images_rec ON record_images(record_id, ord);
CREATE UNIQUE INDEX idx_orders_ptoken ON orders(provider_token) WHERE provider_token IS NOT NULL;
CREATE INDEX idx_inquiries_account ON inquiries(account_id, created_at DESC);
CREATE INDEX idx_inquiries_status ON inquiries(status, created_at DESC);
CREATE INDEX idx_cposts_room
  ON community_posts(school_id, author_grade, author_class, id);
CREATE INDEX idx_adev_account ON account_devices(account_id, last_seen_at);
CREATE INDEX idx_missions_pick ON missions(band, season, active);
CREATE INDEX idx_massign_day ON mission_assign(child_id, ymd);
CREATE INDEX idx_massign_wait ON mission_assign(status, auto_at);
CREATE INDEX idx_ledger_child ON star_ledger(child_id, created_at);
CREATE INDEX idx_missions_owner ON missions(owner_token);
CREATE INDEX idx_mri_child_ymd ON meal_rating_items (child_id, ymd);
CREATE INDEX idx_mri_child_cat ON meal_rating_items (child_id, dish_cat);
CREATE INDEX idx_playlog_child ON play_log (child_id, ymd);
CREATE INDEX idx_playlog_name ON play_log (child_id, name);
CREATE INDEX idx_subjlog_child ON subject_log (child_id, subject);
CREATE INDEX idx_pmt_child ON parent_mission_templates(child_id);
CREATE INDEX idx_store_child ON store_items(child_id);
CREATE INDEX idx_rorders_child ON reward_orders(child_id, created_at DESC);
CREATE INDEX idx_rorders_status ON reward_orders(status);
CREATE INDEX idx_reactions_child ON reactions(child_id, created_at DESC);
CREATE INDEX idx_mv_child ON mission_verifications(child_id, created_at DESC);
CREATE INDEX idx_mv_pending ON mission_verifications(child_id, step2_approved_at);
