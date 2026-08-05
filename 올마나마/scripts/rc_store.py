# -*- coding: utf-8 -*-
"""소매 계산기(Retail Calculator) 데이터 — 표·조회·쓰기 한 곳. 2026-07-31 신설

설계 정본: `소매계산기-설계-2026-07-31.md`

왜 표를 새로 만드나
------------------
기존 `dishes`·`dish_def`·`menus` 는 **브랜드 원가 트랙**의 것이다. 2026-07-31 대표 결정으로
그 트랙은 화면에서 내려가지만 **DB 는 보존**한다(301 봉합 · 재료 시드로 재활용).
새 트랙은 성격이 달라 섞으면 둘 다 망가진다 — 그래서 `rc_` 로 따로 둔다.

  · 브랜드 원가  = «이 브랜드가 이 재료를 쓴다» 는 주장 → 근거가 필요
  · 소매 계산기  = «집에서 만들면 이만큼 든다»   → 표준 레시피면 충분

표 셋
----
  rc_dish     대표메뉴. 계보는 3단 — group(냉면) / kind(함흥냉면) / variant(물냉면)
  rc_ing      그 메뉴에 들어가는 재료 한 줄. 우리 재료(`ingredients`)에 매핑
  rc_pick     그 재료에 붙은 **쿠팡 최소용량 상품** 하나 (파트너스 링크)
  rc_request  손님이 넣어달라고 한 메뉴 (익명 가능)

⛔ 사람이 확정한 것(`picked_by='human'`)은 자동 갱신이 덮지 않는다.
"""
import os
import re
import sqlite3
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

DDL = [
    """CREATE TABLE IF NOT EXISTS rc_dish(
        id INTEGER PRIMARY KEY,
        grp TEXT NOT NULL,               -- 검색 묶음 (냉면)
        kind TEXT NOT NULL,              -- 종류 칩 (함흥냉면)  ← 1단계
        variant TEXT NOT NULL DEFAULT '',-- 갈래 토글 (물냉면)  ← 2단계
        name TEXT NOT NULL,              -- 화면 제목 (함흥 물냉면)
        slug TEXT UNIQUE NOT NULL,
        serving_g INTEGER,               -- 1인분 기준 g (제목 옆 표기)
        minutes INTEGER,                 -- 조리 시간
        how_to TEXT,                     -- 만드는 법 — 우리 문장. 줄바꿈으로 구분
        source_url TEXT,                 -- 참고 원본 레시피
        source_n INTEGER DEFAULT 0,      -- 참고한 레시피 개수
        published INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT, updated_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS rc_ing(
        id INTEGER PRIMARY KEY,
        dish_id INTEGER NOT NULL,
        name TEXT NOT NULL,              -- 화면 표시명 (냉면 육수(봉지))
        need_amount REAL,                -- 1인분에 필요한 양
        need_unit TEXT DEFAULT 'g',
        ingredient_key TEXT,             -- ingredients 매핑 (없으면 NULL)
        match_kw TEXT,                   -- 🔴 쿠팡 검색어. 종류별로 다르다(함흥 육수≠평양 육수)
        is_main INTEGER DEFAULT 0,       -- 「남는 그릇 수」를 이걸로 센다
        optional INTEGER DEFAULT 0,      -- 없어도 되는 것(고명 등)
        sort_order INTEGER DEFAULT 0,
        note TEXT,
        UNIQUE(dish_id, name))""",
    """CREATE TABLE IF NOT EXISTS rc_pick(
        ing_id INTEGER PRIMARY KEY,
        product_id TEXT, title TEXT, price REAL,
        pack_amount REAL, pack_unit TEXT,   -- 상품 총 용량 → 몇 인분 커버인지 계산
        url TEXT, image TEXT,
        item_id TEXT,                       -- 🔴 옵션 식별자. 같은 상품도 옵션마다 다르다
        rocket INTEGER DEFAULT 0,           -- 로켓배송
        fresh INTEGER DEFAULT 0,            -- 로켓프레시(신선)
        picked_by TEXT DEFAULT 'auto',      -- auto | human  ← human 은 자동이 못 덮는다
        picked_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS rc_request(
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        cnt INTEGER DEFAULT 1,
        status TEXT DEFAULT 'new',          -- new | doing | done | drop
        note TEXT, created_at TEXT, last_at TEXT)""",
]

# 🔴 완성품 신호 — 이런 상품은 «재료» 가 아니다 (2026-07-31 둥지냉면 사고).
#    브랜드 완성품을 재료로 붙이면 계산기 전체가 우스워진다. 자동 1순위 금지.
DONE_PRODUCT = re.compile(
    r"둥지|즉석|컵라면|컵밥|밀키트|간편식|HMR|도시락|완조리|레토르트|"
    r"전자레인지|3분|봉지라면|용기면", re.I)


# 규격·포장 말은 «재료 이름» 이 아니다 — 검색어에서 이걸 빼고 핵심어만 남긴다
_SIZEWORD = re.compile(r"^\d+(?:입|개|구|팩|봉|포|kg|g|ml|l|박스|세트)$|^(입|개|구|팩|봉|포|"
                       r"박스|세트|대용량|업소용|국내산|수입산|냉장|냉동|특상품|무항생제|"
                       r"로켓프레시|당일수확)$", re.I)


def core_words(kw):
    """검색어에서 «그 재료를 가리키는 말» 만 남긴다. 「백오이 3입」 → {백오이}"""
    out = []
    for w in re.split(r"[\s,·/()]+", kw or ""):
        w = w.strip()
        if len(w) >= 2 and not _SIZEWORD.match(w):
            out.append(w)
    return out


# 같은 재료를 부르는 다른 말 — 이게 없으면 「대란」 이 계란이 아니게 된다.
#    ⚠️ 넉넉히 넣되 **애매한 건 안 넣는다.** 틀린 매칭이 빈칸보다 나쁘다.
SYN = {
    "계란": ["계란", "달걀", "대란", "왕란", "특란", "중란", "유정란", "생란", "초란"],
    "오이": ["오이"],
    "대파": ["대파", "쪽파"],
    "돼지고기": ["돼지", "삼겹", "목살", "앞다리", "뒷다리", "전지", "후지"],
    "소고기": ["소고기", "우삼겹", "양지", "사태", "차돌"],
    "닭고기": ["닭", "계육"],
    "면": ["면", "사리"],
    "육수": ["육수", "스프", "국물"],
}


def name_hit(kws, title):
    """상품명이 그 재료가 맞나. 🔴 **핵심어가 하나도 없으면 다른 물건이다.**

    2026-07-31 실제 사고 — 「백오이 3입」 으로 검색했더니 「감숙왕 바나나 3입」 이
    단위도 맞고 제일 싸서 1순위로 올라왔고, 자동으로 오이 자리에 **바나나가 붙었다.**

    ⚠️ 반대 사고도 있다 — 좁게 잡으면 「취청오이」·「대란」 이 탈락한다.
       *"「없다」는 90%가 내 필터 탓"* 이라 **표시명과 검색어를 둘 다** 보고 동의어도 본다.
    ⛔ 이 판정으로 **수동 검색 결과를 숨기지 않는다.** 순서만 뒤로 밀고 표시만 한다.
       자동 갱신에서만 통과 못한 것을 안 붙인다.
    """
    t = re.sub(r"\s+", "", title or "")
    if isinstance(kws, str):
        kws = [kws]
    words = []
    for kw in kws:
        words += core_words(kw)
    for w in list(words):
        for base, alts in SYN.items():
            if base in w or w in base:
                words += alts
    for w in words:
        w2 = re.sub(r"\s+", "", w)
        if len(w2) < 2:
            continue
        if w2 in t:
            return True
        if len(w2) >= 4 and (w2[:3] in t or w2[-3:] in t):
            return True
    return False


def connect():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c


def ensure(c):
    for q in DDL:
        c.execute(q)
    # 이미 만들어진 표에 칸을 덧붙인다 — 기존 데이터를 지우지 않는다
    have = {r[1] for r in c.execute("PRAGMA table_info(rc_pick)")}
    for col, ddl in (("item_id", "TEXT"), ("rocket", "INTEGER DEFAULT 0"),
                     ("fresh", "INTEGER DEFAULT 0")):
        if col not in have:
            c.execute("ALTER TABLE rc_pick ADD COLUMN %s %s" % (col, ddl))
    c.commit()


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def slugify(s):
    s = re.sub(r"\s+", "-", (s or "").strip())
    return re.sub(r"[^0-9A-Za-z가-힣\-]", "", s) or "dish"


# ── 조회 ─────────────────────────────────────────────────────────
def dish_full(c, did):
    """계산기 화면 한 벌 — 메뉴 + 재료 + 붙은 상품."""
    d = c.execute("SELECT * FROM rc_dish WHERE id=?", (did,)).fetchone()
    if not d:
        return None
    rows = c.execute("""SELECT g.*, p.product_id, p.title, p.price, p.pack_amount,
                               p.pack_unit, p.url, p.image, p.picked_by,
                               p.rocket, p.fresh, p.item_id,
                               i.name ing_name
                        FROM rc_ing g
                        LEFT JOIN rc_pick p ON p.ing_id=g.id
                        LEFT JOIN ingredients i ON i.ingredient_key=g.ingredient_key
                        WHERE g.dish_id=? ORDER BY g.sort_order, g.id""", (did,)).fetchall()
    return {"dish": d, "ings": rows}


# 🔴 ml 과 g 는 **같은 쪽으로 본다** (대표 판단 2026-07-31).
#    *"액체류는 대부분 L, g은 액체류가 아닌 곳으로 들어가지"* — 육수를 300g 으로 파는 곳이 있고
#    액체는 1ml ≈ 1g 이라 «몇 병 사야 하나» 를 세는 데는 차이가 없다.
#    (기름 0.92 · 간장 1.1 정도로 조금 다르지만 봉지 개수는 안 바뀐다)
# ⛔ 다만 **개수(개·구·입)는 끝까지 따로** 둔다 — 계란 0.5개 ÷ 1.56kg = 3,120인분 사고가 났다.
UNIT_ALIAS = {"g": "g", "kg": "g", "ml": "g", "l": "g", "리터": "g", "cc": "g",
              "개": "개", "구": "개", "입": "개", "알": "개", "장": "개", "판": "개",
              "봉": "개", "포": "개", "ea": "개"}


def unit_ok(a, b):
    """두 단위를 나눠도 되나. **무게·부피 ↔ 개수** 는 절대 섞지 않는다."""
    return bool(a) and bool(b) and UNIT_ALIAS.get(a.lower()) == UNIT_ALIAS.get(b.lower())


def to_base(amount, unit):
    """kg·L 을 g·ml 로 펴서 비교할 수 있게 한다."""
    if amount is None or not unit:
        return None
    u = unit.lower()
    if u == "kg":
        return float(amount) * 1000
    if u in ("l", "리터"):
        return float(amount) * 1000
    return float(amount)


def cover_of(need_amount, need_unit, pack_amount, pack_unit):
    """상품 하나가 **몇 인분**을 덮나. 못 세면 None → 화면에서 「?」 로 두고 사람이 본다.

    🔴 **단위가 다르면 계산하지 않는다.** 「계란 0.5개」 에 「1.56kg 상품」 을 붙이면
       0.5 ÷ 1560 = 3,120인분 이라는 헛소리가 나온다(2026-07-31 실제로 나왔다).
       옛 레시피 관리에서도 단위 불일치로 부대찌개가 17만원이 된 적이 있다.
       틀린 숫자는 빈칸보다 나쁘다 — 못 세면 안 센다.
    """
    try:
        if not need_amount or not pack_amount:
            return None
        if not unit_ok(need_unit, pack_unit):
            return None
        n = int(to_base(pack_amount, pack_unit) // to_base(need_amount, need_unit))
        return n if n >= 1 else 1
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def siblings(c, did):
    """같은 kind 안의 갈래(물냉/비냉) + 같은 grp 안의 종류 칩."""
    d = c.execute("SELECT grp,kind FROM rc_dish WHERE id=?", (did,)).fetchone()
    if not d:
        return [], []
    kinds = c.execute("""SELECT kind, min(id) id FROM rc_dish
                         WHERE grp=? AND published=1 GROUP BY kind
                         ORDER BY min(sort_order), min(id)""", (d["grp"],)).fetchall()
    vars_ = c.execute("""SELECT id, variant FROM rc_dish
                         WHERE grp=? AND kind=? AND published=1
                         ORDER BY sort_order, id""", (d["grp"], d["kind"])).fetchall()
    return kinds, vars_


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    c = connect()
    ensure(c)
    n = {t: c.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
         for t in ("rc_dish", "rc_ing", "rc_pick", "rc_request")}
    print("표 준비 완료 —", " · ".join("%s %d" % (k, v) for k, v in n.items()))
