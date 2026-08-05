# -*- coding: utf-8 -*-
# 관리페이지용 신규 테이블 정의·CRUD (2026-07-20)
#
# 🔴 왜 별도 테이블인가:
#   gen_dishes.py는 매 실행 dishes/dish_ingredients/dish_menus를 DELETE하고 재생성한다.
#   관리페이지가 거기에 직접 쓰면 다음 실행에 전부 사라진다.
#   그래서 **dish_def / dish_def_ingredient가 정본**이고, gen_dishes가 이걸 읽어 dishes를 만든다.
#   → 관리페이지는 dishes/dish_ingredients에 절대 직접 쓰지 않는다.
import os
import sqlite3
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

SCHEMA = """
-- 요리 정의 (dish_data.DISHES의 DB판). gen_dishes가 리터럴과 병합해 읽는다.
CREATE TABLE IF NOT EXISTS dish_def(
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

CREATE TABLE IF NOT EXISTS dish_def_ingredient(
  slug TEXT NOT NULL,
  ingredient_key TEXT NOT NULL,
  amount REAL NOT NULL,
  unit TEXT NOT NULL,
  sort_order INTEGER DEFAULT 0,
  PRIMARY KEY(slug, ingredient_key));   -- 동일 키는 합산 후 저장하므로 중복 불가가 맞다

-- 재료명 별칭 학습. 사람이 한 번 이어주면 다음 요리에서 자동 매칭된다.
CREATE TABLE IF NOT EXISTS ingredient_alias(
  alias_norm TEXT PRIMARY KEY,
  alias_raw TEXT,
  ingredient_key TEXT NOT NULL,
  source TEXT DEFAULT 'human',     -- seed | human
  hits INTEGER DEFAULT 0,
  created_at TEXT);

-- 포장 단위·대체 안내를 DB로 승격 (dish_data.PACK/SUBST와 병합)
CREATE TABLE IF NOT EXISTS ingredient_pack(
  ingredient_key TEXT PRIMARY KEY, qty REAL NOT NULL, label TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ingredient_subst(
  ingredient_key TEXT PRIMARY KEY, note TEXT NOT NULL);

-- 검수 중인 레시피 (Flask 재시작해도 상태가 살아남게)
CREATE TABLE IF NOT EXISTS recipe_draft(
  slug TEXT PRIMARY KEY, name TEXT, gen_name TEXT,
  status TEXT DEFAULT 'draft',     -- draft | mapped | applied
  mapping_json TEXT, cost_usd REAL DEFAULT 0,
  img_status TEXT, created_at TEXT, updated_at TEXT);

CREATE TABLE IF NOT EXISTS gen_job(
  id TEXT PRIMARY KEY, kind TEXT, slug TEXT, state TEXT, step TEXT,
  log TEXT, cost_usd REAL DEFAULT 0, started_at TEXT, ended_at TEXT);

-- 메뉴별 밀키트·냉동 완제품 (관리페이지에서 사람이 고른 것이 정본). 2026-07-25
--  🔴 자동매칭은 폐기했다: 421건 중 50%가 중복(한 상품이 최대 14개 메뉴에 붙음).
--     키워드 폴백('양념 치킨 냉동')이 여러 메뉴에 같은 결과를 줬다.
--     그래서 사람이 하나씩 고르고, 그 결정만 여기 남는다. 재생성에도 살아남는다.
CREATE TABLE IF NOT EXISTS menu_mealkit(
  menu_id INTEGER PRIMARY KEY,
  product_id INTEGER,
  name TEXT, price REAL, rocket INTEGER DEFAULT 0,
  image TEXT, url TEXT,
  match_type TEXT,                 -- 정품 | 대체  (브랜드명이 상품명에 있으면 정품)
  status TEXT DEFAULT 'ok',        -- ok = 노출 / none = 해당없음(노출 안 함)
  decided_at TEXT);

-- X로 지운 후보 (다시 안 뜨게). 메뉴별로 따로 관리한다.
CREATE TABLE IF NOT EXISTS mealkit_rejected(
  menu_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  rejected_at TEXT,
  PRIMARY KEY(menu_id, product_id));

-- 메뉴명 전수검사 결과 (2026-07-25). 웹검색으로 브랜드 공식 메뉴명과 대조한 것.
--  🔴 왜 필요한가: "자메이카소떡적구이"처럼 두 메뉴가 뭉친 이름, 구메뉴명, 축약명이 섞여 있었다.
--     제안만 담고, 적용은 관리페이지에서 사람이 클릭할 때 menus.name 에 쓴다.
CREATE TABLE IF NOT EXISTS menu_name_audit(
  menu_id INTEGER PRIMARY KEY,
  current_name TEXT,
  verdict TEXT,           -- 오타 | 뒤섞임 | 없는메뉴 | 판단불가 | 가격의심
  suggest TEXT,           -- 제안 이름 (없으면 NULL = 사람이 직접 판단)
  note TEXT,              -- 근거
  confidence TEXT,        -- high | mid | low
  status TEXT DEFAULT 'open',   -- open | applied | dismissed
  checked_at TEXT);

-- 재료별 쿠팡 소매 상품 (2026-07-26 신설)
--  🔴 왜 필요한가: 소매가를 "도매 × 계수"로 만들면 ①실제 소매가가 아니고
--     ②**최소 판매 단위를 알 수 없다.** 그래서 장보기 화면의 "500g 팩"이 전부
--     pack_of() 기본값(추측)이었다. 쿠팡 상품을 붙이면 소매가·팩용량·딥링크가 한꺼번에 나온다.
--  · 여기 저장된 pack_kg 는 `ingredient_pack` 으로 반영돼 "장보기 단위"가 된다
--  · status='none' 이면 쿠팡에 마땅한 상품이 없다는 뜻(사람이 판단)
CREATE TABLE IF NOT EXISTS ingredient_retail(
  ingredient_key TEXT PRIMARY KEY,
  product_id INTEGER,
  name TEXT,
  price REAL,             -- 상품 판매가(원)
  pack_kg REAL,           -- 상품 총 중량(kg/L) — 상품명에서 파싱
  -- 🔴 kg 단가 칼럼을 두지 않는다(대표 지시 2026-07-26). 소매는 **총 지출**이 기준이다.
  --    "쌈장 12,667원/kg" 은 실제로 낼 돈과 무관하다 — 7,500원짜리 한 통을 사는 것이다.
  --    칼럼을 남겨두면 또 채워지므로 아예 없앴다.
  rocket INTEGER DEFAULT 0,
  image TEXT,
  url TEXT,
  status TEXT DEFAULT 'ok',   -- ok = 채택 / none = 쿠팡에 마땅한 상품 없음
  decided_at TEXT);

-- 소매 상품 매칭 미인정 (2026-07-26 신설)
--  🔴 왜 필요한가: 자동으로 고른 상품이 그 재료가 아닌 경우가 있다
--     (건두부→쌈두부 · 해찬들 쌈장→저당 알룰로스 쌈장 · 감자튀김→1kg 3개 묶음).
--     반려만 하면 그 재료는 빈 채로 남는다. 그래서 **미인정한 상품을 기억하고
--     같은 검색 결과에서 다음 후보로 바로 갈아끼운다.**
--  · 여기 쌓인 product_id 는 다시 채택되지 않는다
CREATE TABLE IF NOT EXISTS retail_rejected(
  ingredient_key TEXT,
  product_id INTEGER,
  name TEXT,
  price REAL,
  reason TEXT,
  rejected_at TEXT,
  PRIMARY KEY(ingredient_key, product_id));

-- 메뉴에서 뺀 재료 라인 보관 (2026-07-26 신설) — **되돌리기용**
--  🔴 왜 필요한가: 화면에서 ×로 라인을 빼는데 되돌릴 방법이 없었다. 잘못 누르면 복구 불가다
--     (실제로 버거킹 불고기와퍼에서 소불고기양념장이 지워졌다).
--     여기에 지운 줄을 그대로 보관해 한 번 클릭으로 되살린다.
CREATE TABLE IF NOT EXISTS mi_removed(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  menu_id INTEGER,
  ingredient_key TEXT,
  amount REAL,
  unit TEXT,
  sort_order INTEGER,
  composition TEXT,
  removed_at TEXT);

-- 메뉴 검수 도장 (2026-07-26 신설)
--  🔴 왜 필요한가: 재료 파이프라인(도매=식봄 / 소매=쿠팡)은 잡혔지만 **양·부위**는
--     사람 눈을 거쳐야 하는 값이다. 실제로 검수를 몇 바퀴 돌려도 계속 틀린 게 나왔다
--     (콤보육→장각, 900g→700g 등). 어디까지 봤는지 표시가 없으면 같은 메뉴를 또 본다.
--  · 도장이 찍힌 메뉴는 목록에서 걸러내고 **안 찍힌 것만** 본다
--  · menus 를 ALTER 하지 않고 별도 테이블로 둔다 — 생성기가 menus 를 건드려도 도장은 남는다
--  · 나중에 양·부위를 또 고치면 도장을 떼야 한다(unverify) — 고쳤는데 도장이 남아 있으면
--    "검수됨"이 거짓이 된다
CREATE TABLE IF NOT EXISTS menu_verified(
  menu_id INTEGER PRIMARY KEY,
  verified_at TEXT,
  note TEXT);            -- 무엇을 확인했는지 (부위·양·판매가 등)

-- 브랜드 공식 메뉴 (2026-07-27 신설) — 본사 홈페이지에서 긁은 **원문 그대로**
--  🔴 왜 필요한가: 우리 `menus` 는 우리가 원가를 낸 메뉴만 있다. 그런데 공식 메뉴는 훨씬 많다
--     (설빙 공식 31개 vs 우리 8개). 무슨 메뉴를 파는지 모르면 재료 비교도 누락 확인도 못 한다.
--  · 사이트 브랜드 페이지에는 **공식 메뉴를 다 보여주고** `menu_id` 가 있는 것만 링크를 건다.
--    없는 건 이름만(비활성) → 원가가 붙으면 활성화된다(대표 지시)
--  · `menus` 로 자동 승격하지 않는다 — 사이드·음료까지 밀려들어와 메뉴 수가 급증한다.
--    대표가 목록 보고 고른 것만 잇는다
--  · ⛔ 파싱된 값만 넣는다. 중량이 안 적혀 있으면 비운다(`ingredients-evidence-only`)
CREATE TABLE IF NOT EXISTS brand_menu_official(
  brand_id INTEGER,
  name TEXT,              -- 공식 메뉴명 (원문)
  category TEXT,          -- 사이드·음료 같은 분류 (있으면)
  price INTEGER,          -- 본품 판매가
  weight_raw TEXT,        -- "10호(951~1050g) 이상" 같은 원문 — 절대 버리지 않는다
  weight_g REAL,          -- 위에서 계산한 g (범위면 중간값)
  origin_raw TEXT,        -- 원산지 표시 원문
  allergy_raw TEXT,       -- 알레르기 성분 원문
  detail_url TEXT,
  image_url TEXT,
  menu_id INTEGER,        -- 우리 원가 메뉴와 연결되면 채워짐 = 사이트에서 활성
  collected_at TEXT,
  PRIMARY KEY(brand_id, name));

-- 메뉴별 쿠팡(소매) 후보 (2026-07-27 신설)
--  🔴 왜 재료 단위가 아니라 **메뉴 단위**인가 (대표 지시 2026-07-26):
--     `ingredient_retail` 은 재료 1개당 1행이라 "떡볶이 양념" 하나가 9개 브랜드를 덮었다.
--     브랜드마다 소스 맛이 다른데 같은 상품이 붙고, 붙일 쿠팡 링크도 1개뿐이라 레퍼럴이 깎였다.
--     메뉴별로 쪼개면 신전 소스·엽떡 소스가 각자 자기 상품을 갖는다.
--  · **같은 product_id 가 여러 메뉴에 붙는 중복은 정상이다. 막지 말 것**
--  · `ingredient_retail` 은 재료 기본값으로 남기고, 메뉴별 값이 있으면 그게 우선
--  · 대상은 **`menu_verified` 에 도장이 찍힌 메뉴만**(대표 결정) — 재료가 확정 안 된 메뉴를 뒤지면 헛수고다
CREATE TABLE IF NOT EXISTS menu_coupang(
  menu_id INTEGER,
  ingredient_key TEXT,
  product_id INTEGER,
  name TEXT,
  price REAL,
  pack_g REAL,
  rocket INTEGER DEFAULT 0,
  url TEXT,
  image TEXT,
  kw TEXT,                -- 어떤 검색어로 찾았나 (재현용)
  collected_at TEXT,
  PRIMARY KEY(menu_id, ingredient_key, product_id));

-- 메뉴별 식봄(도매) 후보 (2026-07-27 신설) — menu_coupang 과 같은 이유
--  · 식봄은 **카테고리 우선**으로 찾는다. 검색부터 하면 섞인다(2026-07-24 사고)
CREATE TABLE IF NOT EXISTS menu_sikbom(
  menu_id INTEGER,
  ingredient_key TEXT,
  goods_id TEXT,
  name TEXT,
  price REAL,
  pack TEXT,              -- "5kg 2팩" 같은 원문
  unit_price REAL,        -- 단위당 단가 (배수 반영해서 계산한 값)
  url TEXT,
  kw TEXT,
  collected_at TEXT,
  PRIMARY KEY(menu_id, ingredient_key, goods_id));
"""


def conn():
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    return c


def init(c=None):
    own = c is None
    c = c or conn()
    c.executescript(SCHEMA)
    c.commit()
    if own:
        c.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 내린 요리 ────────────────────────────────────────────────────
def load_disabled_slugs(c=None):
    """active=0 인 요리 slug 집합.

    🔴 왜 필요한가: gen_dishes.py는 dish_data.DISHES(파이썬 리터럴 68종)를 항상 먼저 깐다.
       dish_def를 active=0으로 내려도 리터럴이 살아 있으면 페이지가 계속 나온다.
       리터럴을 지우는 대신 여기서 걸러야 '되돌리기'가 active=1 한 줄로 끝난다.
    """
    own = c is None; c = c or conn()
    try:
        s = {r[0] for r in c.execute("SELECT slug FROM dish_def WHERE active=0")}
    except sqlite3.OperationalError:
        s = set()
    if own: c.close()
    return s


# ── dish_def 읽기 — gen_dishes.py가 부른다 ──────────────────────────
def load_dish_defs(c=None):
    """DB에 정의된 요리 → {slug: (name, slug, serving, pattern, [(key,amt,unit)...])} + 메타.

    gen_dishes.py의 DISHES 튜플과 같은 모양으로 돌려줘서 병합이 쉽게 한다.
    테이블이 없으면 빈 dict — 마이그레이션 전에도 기존 동작이 그대로 유지된다.
    """
    own = c is None
    c = c or conn()
    try:
        rows = c.execute("""SELECT * FROM dish_def WHERE active=1 ORDER BY sort_order, slug""").fetchall()
    except sqlite3.OperationalError:
        return {}
    out = {}
    for r in rows:
        ings = [(x["ingredient_key"], x["amount"], x["unit"]) for x in c.execute(
            "SELECT ingredient_key, amount, unit FROM dish_def_ingredient "
            "WHERE slug=? ORDER BY sort_order", (r["slug"],))]
        out[r["slug"]] = {
            "tuple": (r["name"], r["slug"], r["serving"], r["match_pattern"] or r"(?!)", ings),
            "category": r["category"], "icon": r["icon"], "sort_order": r["sort_order"],
            "main_keys_json": r["main_keys_json"], "mealkit_json": r["mealkit_json"],
            "source": r["source"],
        }
    if own:
        c.close()
    return out


def load_dish_groups(c=None):
    """{(slug, ingredient_key): 그룹명} — dish_def_ingredient.grp 에 손으로 지정한 것만.

    2026-07-24 §A3: 재료 그룹을 4개(메인·부재료·야채·양념)로 늘리면서, 자동 판정으로는
    못 가르는 것들을 대표 승인으로 지정했다. NULL이면 기존 자동 판정을 그대로 쓴다.
    ⚠️ 튜플 (key, amount, unit) 모양은 건드리지 않는다 — 쓰는 곳이 많아 깨진다.
    """
    own = c is None
    c = c or conn()
    try:
        rows = c.execute("SELECT slug, ingredient_key, grp FROM dish_def_ingredient "
                         "WHERE grp IS NOT NULL AND grp != ''").fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        pass
    out = {(r["slug"], r["ingredient_key"]): r["grp"] for r in rows}
    if own:
        c.close()
    return out


def load_pack(c=None):
    own = c is None; c = c or conn()
    try:
        d = {r["ingredient_key"]: (r["qty"], r["label"])
             for r in c.execute("SELECT * FROM ingredient_pack")}
    except sqlite3.OperationalError:
        d = {}
    if own: c.close()
    return d


def load_subst(c=None):
    own = c is None; c = c or conn()
    try:
        d = {r["ingredient_key"]: r["note"] for r in c.execute("SELECT * FROM ingredient_subst")}
    except sqlite3.OperationalError:
        d = {}
    if own: c.close()
    return d
