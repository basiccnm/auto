-- 얼마남아 (음식 원가 계산기) B2C DB 스키마
-- SQLite 로컬 개발 / Cloudflare D1 배포 공용
--
-- ⚠️ 이 파일은 **자동 생성**된다. 손으로 고치지 말 것.
--    실제 DB에서 뽑는다:  python scripts/gen_schema.py
--    손으로 관리하다 실제 DB와 벌어져서, D1에 시딩하면 요리사전(dish 4테이블)과
--    매장원가(store_cost/store_ratio) 등 11개 컬럼이 통째로 빠지는 상태였다(2026-07-17 발견).
--
-- 생성일: 2026-07-24 (UTC)
-- 구조: categories → brands → menus → menu_ingredients ← ingredients → price_history
--       dishes → dish_ingredients / dish_menus  (요리사전 축)

-- table: banners
CREATE TABLE banners (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slot INTEGER NOT NULL CHECK (slot IN (1, 2, 3)),
  category_slug TEXT,               -- NULL이면 전체 매칭
  image_url TEXT NOT NULL,
  link_url TEXT NOT NULL,
  alt_text TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

-- table: brand_origins
CREATE TABLE brand_origins(
  brand_id INTEGER PRIMARY KEY REFERENCES brands(id),
  chicken TEXT, pork TEXT, beef TEXT, seafood TEXT, rice TEXT);

-- table: brands
CREATE TABLE brands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category_id INTEGER NOT NULL REFERENCES categories(id),
  name TEXT NOT NULL,              -- "교촌치킨"
  slug TEXT NOT NULL,              -- "kyochon" (URL: /chicken/kyochon/)
  homepage_url TEXT,              -- 로고 클릭 시 이동. 없으면 미노출 대상
  logo_url TEXT,                  -- 헤더/배너 로고 이미지 (핫링크)
  sort_order INTEGER NOT NULL DEFAULT 0,  -- 유명순 (작을수록 상위)
  created_at TEXT NOT NULL
, fftc_yr TEXT, fftc_brand_nm TEXT, fftc_corp_nm TEXT, frcs_cnt INTEGER, avrg_sls_amt INTEGER, ar_unit_avrg_sls INTEGER, logo_rejected INTEGER DEFAULT 0, logo_pending INTEGER DEFAULT 0);

-- table: categories
CREATE TABLE categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,              -- "치킨"
  slug TEXT NOT NULL,              -- "chicken" (URL: /chicken/)
  tier TEXT NOT NULL DEFAULT '중형' CHECK (tier IN ('대형','중형','소형')),  -- 개수 배분 티어
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

-- table: dish_def
CREATE TABLE dish_def(
  slug TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  serving TEXT NOT NULL DEFAULT '1인분',
  match_pattern TEXT,              -- 브랜드 메뉴 매칭 정규식. 비우면 아무것도 안 잡음
  category TEXT,                   -- DISH_CAT 분류. 없으면 목록에서 고아가 된다
  icon TEXT,
  sort_order INTEGER DEFAULT 999,
  main_keys_json TEXT,             -- 메인 재료 지정 (MAIN_KEYS)
  mealkit_json TEXT,
  source TEXT DEFAULT 'admin',     -- 'literal'=dish_data에서 옮겨온 것, 'admin'=관리페이지 생성
  active INTEGER DEFAULT 1,
  created_at TEXT, updated_at TEXT);

-- table: dish_def_ingredient
CREATE TABLE dish_def_ingredient(
  slug TEXT NOT NULL,
  ingredient_key TEXT NOT NULL,
  amount REAL NOT NULL,
  unit TEXT NOT NULL,
  sort_order INTEGER DEFAULT 0, grp TEXT,
  PRIMARY KEY(slug, ingredient_key));

-- table: dish_ingredients
CREATE TABLE dish_ingredients(
  id INTEGER PRIMARY KEY AUTOINCREMENT, dish_id INTEGER NOT NULL REFERENCES dishes(id),
  ingredient_key TEXT NOT NULL REFERENCES ingredients(ingredient_key),
  amount REAL NOT NULL, unit TEXT NOT NULL, sort_order INTEGER DEFAULT 0);

-- table: dish_menus
CREATE TABLE dish_menus(
  dish_id INTEGER NOT NULL REFERENCES dishes(id), menu_id INTEGER NOT NULL REFERENCES menus(id),
  PRIMARY KEY(dish_id, menu_id));

-- table: dishes
CREATE TABLE dishes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
  serving TEXT NOT NULL DEFAULT '1인분', note TEXT, sort_order INTEGER DEFAULT 0, recipe_steps TEXT, tips_json TEXT, faq_json TEXT, seo_title TEXT, seo_intro TEXT, ing_json TEXT, recipe_serving TEXT);

-- table: gen_job
CREATE TABLE gen_job(
  id TEXT PRIMARY KEY, kind TEXT, slug TEXT, state TEXT, step TEXT,
  log TEXT, cost_usd REAL DEFAULT 0, started_at TEXT, ended_at TEXT);

-- table: ingredient_alias
CREATE TABLE ingredient_alias(
  alias_norm TEXT PRIMARY KEY,
  alias_raw TEXT,
  ingredient_key TEXT NOT NULL,
  source TEXT DEFAULT 'human',     -- seed | human
  hits INTEGER DEFAULT 0,
  created_at TEXT);

-- table: ingredient_pack
CREATE TABLE ingredient_pack(
  ingredient_key TEXT PRIMARY KEY, qty REAL NOT NULL, label TEXT NOT NULL);

-- table: ingredient_subst
CREATE TABLE ingredient_subst(
  ingredient_key TEXT PRIMARY KEY, note TEXT NOT NULL);

-- table: ingredients
CREATE TABLE ingredients (
  ingredient_key TEXT PRIMARY KEY,  -- Gemini 키코드 "raw_chicken_10", "pork_belly_import" ...
  name TEXT NOT NULL,               -- "염지닭 10호"
  class TEXT NOT NULL CHECK (class IN ('농축산물','가공품')),
  type TEXT NOT NULL CHECK (type IN ('live','live_composite','manual')),
  -- live: KAMIS/축평원 직접 조회
  kamis_cat TEXT,                   -- "500" (축산) 등
  kamis_item_code TEXT,             -- "4402"
  kamis_kind_code TEXT,             -- 품종코드 (nullable)
  ekape_item TEXT,                  -- 축평원 품목 (닭 정밀화용, nullable)
  -- live_composite: 여러 KAMIS 품목 가중평균 (예: "신선 야채")
  composite_formula TEXT,           -- JSON [{"code":"245","w":0.4}, ...]
  -- manual: 참가격 연동 or 고정 추정값
  chamgagyeok_key TEXT,             -- 참가격 goodId (승격 시, nullable)
  manual_price INTEGER,             -- 고정 추정 단가 (원)
  base_unit TEXT NOT NULL DEFAULT 'kg',   -- 단가 기준 단위 (kg / L / 개)
  markup_factor REAL NOT NULL DEFAULT 1.0, -- 염지·가공 마크업 (원물가 × factor)
  updated_at TEXT
, is_retail INTEGER DEFAULT 0, wholesale_price INTEGER, wholesale_basis TEXT, subcat TEXT, origin TEXT, naver_price INTEGER, naver_pack REAL, naver_unit TEXT, naver_title TEXT, naver_mall TEXT, naver_kw TEXT, naver_n INTEGER, naver_checked_at TEXT, piece_g REAL, name_note TEXT
-- 2026-07-27 대표 지시: 화면에는 상표를 안 쓴다. `name` 은 값이 다른 재료를 구분하려고 남기고
--   (bhc 파우더 4,575원 / BBQ 2,350원), 화면·주소에는 아래 둘만 쓴다.
--   둘 다 `scripts/display_name_build.py` 한 곳에서 만든다 — 생성기마다 계산하면 어긋난다.
, display_name TEXT      -- 화면에 나갈 이름. 재료가 달라도 하나로 통일한다("치킨파우더")
, page_slug TEXT);       -- 재료 페이지 주소. 표시명이 겹치면 뒤에 번호를 붙인다

-- table: menu_ingredients
CREATE TABLE menu_ingredients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  menu_id INTEGER NOT NULL REFERENCES menus(id),
  ingredient_key TEXT NOT NULL REFERENCES ingredients(ingredient_key),
  amount REAL NOT NULL,             -- 소요량 (base_unit 기준, 예: 1.0)
  unit TEXT NOT NULL,               -- 표기 단위 (kg/g/L/ml/개/세트)
  line_cost INTEGER,                -- 이 재료 줄 비용 캐시 (amount × 단가)
  sort_order INTEGER NOT NULL DEFAULT 0
, composition TEXT, wholesale_cost INTEGER);

-- table: menus
CREATE TABLE menus (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id INTEGER NOT NULL REFERENCES brands(id),
  name TEXT NOT NULL,              -- "허니콤보"
  slug TEXT NOT NULL,              -- "honey-combo" (URL: /chicken/kyochon/honey-combo/)
  sell_price INTEGER,             -- 배달앱 판매가 (원)
  est_cost INTEGER,               -- 추정 재료비 합계 (원). ingredients로 재계산도 가능하나 캐시
  cost_ratio REAL,                -- 추정 원가율 (%). 파생값 캐시
  recipe_steps TEXT,              -- 따라만들기 3~5단계 (JSON 배열 or 줄바꿈 텍스트)
  source TEXT,                    -- 출처 (유튜버명 등)
  gemini_id INTEGER,              -- Gemini 원본 데이터의 ID (1~412), 추적용
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
, store_cost INTEGER, store_ratio REAL, uncosted_note TEXT);

-- table: naver_offer
CREATE TABLE naver_offer (
  ingredient_key TEXT NOT NULL,
  keyword        TEXT,
  title          TEXT,
  mall           TEXT,
  price          INTEGER,      -- 판매가(원)
  pack_qty       REAL,         -- 파싱한 용량
  pack_unit      TEXT,         -- kg | L
  per_unit       REAL,         -- 원/kg 또는 원/L
  tier           TEXT,         -- 소포장 | 가정용 | 대용량 | 업소용
  rank_sim       INTEGER,      -- 정확도순 순위 (1이 최상위 = 많이 찾는 것)
  product_id     TEXT,
  link           TEXT,
  checked_at     TEXT
, origin TEXT, grade TEXT, pieces INTEGER, opt_multi INTEGER, variant_flag TEXT, usable INTEGER, grade_class TEXT, irrelevant INTEGER DEFAULT 0);

-- table: price_history
CREATE TABLE price_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ingredient_key TEXT NOT NULL REFERENCES ingredients(ingredient_key),
  price_date TEXT NOT NULL,         -- YYYY-MM-DD
  retail_price INTEGER NOT NULL,    -- 소매가 (base_unit 기준 원)
  source TEXT NOT NULL,             -- 'kamis' / 'ekape' / 'chamgagyeok'
  created_at TEXT NOT NULL, wholesale_price INTEGER,
  UNIQUE (ingredient_key, price_date, source)
);

-- table: recipe_draft
CREATE TABLE recipe_draft(
  slug TEXT PRIMARY KEY, name TEXT, gen_name TEXT,
  status TEXT DEFAULT 'draft',     -- draft | mapped | applied
  mapping_json TEXT, cost_usd REAL DEFAULT 0,
  img_status TEXT, created_at TEXT, updated_at TEXT);

-- index: idx_banners_lookup
CREATE INDEX idx_banners_lookup ON banners (slot, active, category_slug);

-- index: idx_brands_category
CREATE INDEX idx_brands_category ON brands (category_id, sort_order);

-- index: idx_brands_slug
CREATE UNIQUE INDEX idx_brands_slug ON brands (slug);

-- index: idx_categories_slug
CREATE UNIQUE INDEX idx_categories_slug ON categories (slug);

-- index: idx_menuing_ing
CREATE INDEX idx_menuing_ing ON menu_ingredients (ingredient_key);

-- index: idx_menuing_menu
CREATE INDEX idx_menuing_menu ON menu_ingredients (menu_id, sort_order);

-- index: idx_menus_brand
CREATE INDEX idx_menus_brand ON menus (brand_id, sort_order);

-- index: idx_menus_slug
CREATE UNIQUE INDEX idx_menus_slug ON menus (slug);

-- index: idx_pricehist_ing_date
CREATE INDEX idx_pricehist_ing_date ON price_history (ingredient_key, price_date);

-- index: ix_naver_offer_key
CREATE INDEX ix_naver_offer_key  ON naver_offer(ingredient_key, tier);

-- index: ix_naver_offer_pid
CREATE INDEX ix_naver_offer_pid  ON naver_offer(ingredient_key, product_id);
