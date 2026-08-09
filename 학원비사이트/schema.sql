-- 학원비사이트 DB 스키마 (SQLite 로컬 개발 / Cloudflare D1 배포 공용)

CREATE TABLE IF NOT EXISTS academies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  aca_asnum TEXT NOT NULL,
  office_code TEXT NOT NULL,
  office_name TEXT NOT NULL,
  sido TEXT NOT NULL,
  sigungu TEXT NOT NULL,
  inst_type TEXT,
  name TEXT NOT NULL,
  status TEXT,
  closed_at TEXT,
  realm_raw TEXT,
  category_name TEXT NOT NULL,
  category_slug TEXT NOT NULL,
  course_name TEXT,
  course_list_raw TEXT,
  fee_raw TEXT,
  fee_parsed TEXT,
  has_fee_data INTEGER NOT NULL DEFAULT 0,
  capacity_total INTEGER,
  capacity_hourly INTEGER,
  address_road TEXT,
  address_detail TEXT,
  zipcode TEXT,
  phone TEXT,
  reg_date TEXT,
  lat REAL,
  lng REAL,
  geocoded_at TEXT,
  dong TEXT,
  slug TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  last_changed_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_academies_office_asnum ON academies (office_code, aca_asnum);
CREATE INDEX IF NOT EXISTS idx_academies_region ON academies (sido, sigungu);
CREATE INDEX IF NOT EXISTS idx_academies_dong ON academies (sido, sigungu, dong);
CREATE INDEX IF NOT EXISTS idx_academies_category ON academies (sido, sigungu, category_slug);
CREATE INDEX IF NOT EXISTS idx_academies_status ON academies (status);

-- 별점 (학원/도장 공용, academy_id FK 대신 tip_offs와 동일한 entity_type+entity_slug 패턴)
CREATE TABLE IF NOT EXISTS ratings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('academy', 'dojo')),
  entity_slug TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
  voter_key TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (entity_type, entity_slug, voter_key)
);

CREATE INDEX IF NOT EXISTS idx_ratings_entity ON ratings (entity_type, entity_slug);

-- 체육도장업 (행안부 생활_체육도장업 조회서비스, apis.data.go.kr/1741000/martial_arts_dojo)
CREATE TABLE IF NOT EXISTS dojos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mng_no TEXT NOT NULL,
  opn_atmy_grp_cd TEXT NOT NULL,
  name TEXT NOT NULL,
  sport_name TEXT,
  sido TEXT NOT NULL,
  sigungu TEXT NOT NULL,
  status_code TEXT,
  status_name TEXT,
  detail_status_name TEXT,
  is_open INTEGER NOT NULL DEFAULT 1,
  license_ymd TEXT,
  closed_ymd TEXT,
  address_road TEXT,
  address_lot TEXT,
  zipcode TEXT,
  phone TEXT,
  leader_count INTEGER,
  member_capacity INTEGER,
  category_name TEXT NOT NULL,
  category_slug TEXT NOT NULL,
  lat REAL,
  lng REAL,
  geocoded_at TEXT,
  dong TEXT,
  slug TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  last_changed_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dojos_grp_mngno ON dojos (opn_atmy_grp_cd, mng_no);
CREATE INDEX IF NOT EXISTS idx_dojos_region ON dojos (sido, sigungu);
CREATE INDEX IF NOT EXISTS idx_dojos_dong ON dojos (sido, sigungu, dong);
CREATE INDEX IF NOT EXISTS idx_dojos_category ON dojos (sido, sigungu, category_slug);

-- 정보 제보 (전화번호 없는 페이지의 "정보 등록 요청" 폼 제출, 검토 대기 → 승인/거절)
CREATE TABLE IF NOT EXISTS tip_offs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('academy', 'dojo')),
  entity_slug TEXT NOT NULL,
  entity_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  submitter_type TEXT NOT NULL CHECK (submitter_type IN ('관계자', '이용자')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  submitted_ip_hash TEXT,
  created_at TEXT NOT NULL,
  reviewed_at TEXT,
  reviewed_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_tipoffs_status ON tip_offs (status, created_at);

-- 광고 슬롯에 우선 노출할 직접 배너 (지역/분야 지정, NULL이면 전체 매칭)
CREATE TABLE IF NOT EXISTS banners (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slot INTEGER NOT NULL CHECK (slot IN (1, 2, 3)),
  sido TEXT,
  sigungu TEXT,
  category_slug TEXT,
  image_url TEXT NOT NULL,
  link_url TEXT NOT NULL,
  alt_text TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_banners_lookup ON banners (slot, active, sido, sigungu, category_slug);
