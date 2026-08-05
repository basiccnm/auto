# -*- coding: utf-8 -*-
# 일반 메뉴(dish) 축 구축: 짜장면·김치찌개·탕수육 등 요리 단위 페이지
#  - dishes / dish_ingredients(표준 1인분 레시피) / dish_menus(브랜드 메뉴 연결) 테이블
#  - 페이지: ①집에서 만들면 재료비(우리 단가) ②브랜드별 비교표 ③시판소스 추천(is_retail 자동)
#  - 산출: _preview/dish_{slug}.html + dishes.html(목록)
import sqlite3, os, re, html, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apply_dish_recipes import RECIPES as DISH_RECIPES   # slug → (인분, [단계])

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview")
def esc(s): return html.escape(str(s)) if s is not None else ""

# ── 요리 일러스트 (2026-07-25) ──────────────────────────────────
#  쇼츠용으로 그려둔 일러 118장 중 음식 72장을 요리 페이지에 붙인다.
#  원본: _shorts/remotion/public/food/  → 웹용으로 축소·최적화해 _preview/illust/ 에 복사됨
#  매핑: data/research/dish_illust.json (slug → png). 일러 없는 요리는 빈칸으로 둔다.
try:
    with open(os.path.join(BASE, "data", "research", "dish_illust.json"), encoding="utf-8") as _f:
        DISH_ILLUST = {k: v for k, v in json.load(_f).items() if not k.startswith("_")}
except FileNotFoundError:
    DISH_ILLUST = {}


# 🔴 2026-08-02 «상비 재료» — 거의 모든 집에 있고 이 요리 때문에 사러 가지 않는 것.
#   설계·근거: reports/설계-재료-장보기-2026-08-02.md §3-2 (대표 확정)
#   > *"기본적인 소금 후추 설탕 양이 많은거는 있는거야. 그러니깐 이건 애초에 빼버리면 되"*
#   > *"참기름 고춧가루 고추장 된장 있어. 왠만하면 다 오래 먹을수 있는거라서"*
#   ⛔ 여기 넣으면 **화면에도 금액에도 안 나온다.** 늘릴 땐 신중할 것 —
#      정말 «거의 모든 집에 있는가» 만 기준이다. 애매하면 넣지 말고 접힘(체크)으로 둔다.
#  ⚠️ 「후춧가루」는 사이시옷이라 「후추」로 안 잡힌다 → 「후춧」 을 따로 넣는다
PANTRY_NAMES = (
    "소금", "후추", "후춧",
    "설탕", "식용유", "간장", "식초", "다진 마늘", "다진마늘",
    "참기름", "고춧가루", "고추장", "된장", "물",
)
# 위 낱말에 걸리지만 **상비가 아닌 것** — 먼저 걸러낸다
PANTRY_EXCLUDE = ("장아찌", "고추장아찌", "물엿", "물만두", "간장게장", "간장치킨")
# 🔴 이름이 **잘려서** 위 낱말로 안 잡히는 것 — DB 재료명이 깨져 있다(2026-08-02 발견).
#    「탕」 은 subcat 이 `가공식품/설탕·시럽` 인 걸로 보아 **설탕**이다. 8개 요리에 쓰인다.
#    ⚠️ 근본 수정은 재료명을 고치는 것이다. 여기서는 화면만 막는다.
PANTRY_NAMES_EXACT = ("탕",)
# 상품명이 섞여 낱말로 못 잡는 것 대비 — 키로도 잡는다
PANTRY_KEYS = set()


def is_pantry(key, name):
    """상비 재료인가. 이름은 `display_name`(화면 이름) 기준이다."""
    if key in PANTRY_KEYS:
        return True
    n = (name or "").replace(" ", "")
    #  ⚠️ 낱말이 겹치지만 상비가 아닌 것을 **먼저** 걸러낸다(고추장아찌·물엿·간장치킨 …)
    if any(x in n for x in PANTRY_EXCLUDE):
        return False
    if n in PANTRY_NAMES_EXACT:
        return True
    for w in PANTRY_NAMES:
        if w.replace(" ", "") in n:
            #  ⚠️ 「물」은 정확히 «물» 일 때만. 안 그러면 물냉면·물회까지 사라진다.
            if w == "물" and n != "물":
                continue
            return True
    return False


def _png_size(path):
    """PNG 실제 크기(IHDR). 의존성 없이 헤더만 읽는다. 못 읽으면 None."""
    try:
        with open(path, "rb") as fp:
            head = fp.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))
    except Exception:
        return None


def illust(slug, name, cls="dill", w=480, h=340, eager=False):
    """요리 일러스트 <img>. 파일이 실제로 있을 때만 넣는다(깨진 이미지 방지).

    🔴 2026-08-02 두 가지를 고쳤다 — 둘 다 「제목 아래 226px 빈칸」의 원인이었다.
      ① **첫 화면 일러스트에 `loading="lazy"` 가 걸려 있었다.** 뷰포트 최상단인데도
         브라우저가 아예 안 불러와 자리만 남았다. 상세는 `eager=True` 로 부른다.
         목록 카드는 스크롤 아래라 lazy 를 그대로 둔다.
      ② **width/height 가 실제 비율과 달랐다**(속성 480x340 · 실제 480x425).
         예약 공간과 그림 크기가 어긋나 뜨는 순간 레이아웃이 밀렸다(CLS).
         이제 PNG 헤더에서 실제 값을 읽어 쓴다.
    """
    f = DISH_ILLUST.get(slug)
    if not f:
        return ""
    p = os.path.join(OUT, "illust", f)
    if not os.path.exists(p):
        return ""
    real = _png_size(p)
    if real:
        w, h = real
    load = ('decoding="async" fetchpriority="high"' if eager
            else 'loading="lazy" decoding="async"')
    return (f'<img class="{cls}" src="illust/{f}" alt="{esc(name)} 일러스트"'
            f' {load} width="{w}" height="{h}">')

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
# apply_recipe_md.py가 만든 확장 컬럼(팁·FAQ·사진 메타) 유무 — 없으면 예전 렌더로 동작한다.
_HAS_RECIPE_COLS = "tips_json" in {r[1] for r in cur.execute("PRAGMA table_info(dishes)")}
cur.executescript("""
CREATE TABLE IF NOT EXISTS dishes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
  serving TEXT NOT NULL DEFAULT '1인분', note TEXT, sort_order INTEGER DEFAULT 0, recipe_steps TEXT);
CREATE TABLE IF NOT EXISTS dish_ingredients(
  id INTEGER PRIMARY KEY AUTOINCREMENT, dish_id INTEGER NOT NULL REFERENCES dishes(id),
  ingredient_key TEXT NOT NULL REFERENCES ingredients(ingredient_key),
  amount REAL NOT NULL, unit TEXT NOT NULL, sort_order INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS dish_menus(
  dish_id INTEGER NOT NULL REFERENCES dishes(id), menu_id INTEGER NOT NULL REFERENCES menus(id),
  PRIMARY KEY(dish_id, menu_id));
""")
# 🔴 이 스크립트는 dishes를 통째로 지우고 다시 만든다(알려진 함정).
#    apply_recipe_md.py가 넣어둔 레시피 확장분(팁·FAQ·SEO·사진메타)은 여기서 살렸다가 되돌린다.
#    안 그러면 매 실행마다 검수해서 넣은 레시피가 사라진다.
_KEEP = {}
if _HAS_RECIPE_COLS:
    for r in cur.execute("""SELECT slug, recipe_steps, tips_json, faq_json, seo_title,
                            seo_intro, ing_json, recipe_serving FROM dishes""").fetchall():
        if any(r[i] for i in range(1, 8)):
            _KEEP[r["slug"]] = tuple(r[i] for i in range(1, 8))
cur.execute("DELETE FROM dish_menus"); cur.execute("DELETE FROM dish_ingredients"); cur.execute("DELETE FROM dishes")

# 신선 채소(뭉뚱그림)는 2026-07-20 사용자 지시로 분해: 양파50%/양배추30%/당근20%
# 김치 재료 없으면 추가(시판 포기김치 소매 ~4,000/kg)
cur.execute("""INSERT OR IGNORE INTO ingredients(ingredient_key,name,class,type,manual_price,base_unit,markup_factor,updated_at)
  VALUES('kimchi_fresh','포기김치(시판)','가공품','manual',4000,'kg',1.0,datetime('now'))""")

# 요리 정의 데이터는 dish_data.py로 분리(2026-07-20) — 관리페이지가 DB로 요리를 다루기 위한 사전작업.
#  healthcheck.py도 같은 모듈을 import해 재료키를 검증한다.
from dish_data import (DISHES as _LIT_DISHES, PRIORITY, MAIN_KEYS as _LIT_MAIN,
                       SUBST as _LIT_SUBST, PACK as _LIT_PACK,
                       MEALKIT, ICON as _LIT_ICON, DISH_CAT as _LIT_CAT)
import admin_store as _st

# ── DB 정본 + 리터럴 폴백 (2026-07-20) ────────────────────────────────
#  관리페이지가 만든 요리는 dish_def에 있다. DB가 비어 있거나 테이블이 없으면
#  리터럴 68종이 그대로 돌아간다 — 마이그레이션이 실패해도 사이트는 안 죽는다.
_DB_DEFS = _st.load_dish_defs(con)
_OFF = _st.load_disabled_slugs(con)          # active=0 = 내린 요리 (리터럴에 있어도 뺀다)
_lit_by_slug = {d[1]: d for d in _LIT_DISHES}
DISHES = []
for d in _LIT_DISHES:                       # 기존 68종은 순서를 그대로 지킨다
    if d[1] in _OFF:
        continue
    DISHES.append(_DB_DEFS[d[1]]["tuple"] if d[1] in _DB_DEFS else d)
for slug, meta in _DB_DEFS.items():         # DB에만 있는 신규 요리를 뒤에 붙인다
    if slug not in _lit_by_slug:
        DISHES.append(meta["tuple"])

# ★ ORDER는 병합 결과에서 만든다. dish_data.ORDER를 쓰면 신규 요리에서
#   ORDER.index(name)이 ValueError를 내고 gen_dishes 전체가 죽는다(68종 페이지 전멸).
ORDER = [d[0] for d in DISHES]

# ICON / DISH_CAT / MAIN_KEYS / PACK / SUBST — 리터럴에 DB분을 덮어씌운다
ICON = dict(_LIT_ICON)
DISH_CAT = {k: list(v) for k, v in _LIT_CAT.items()}
MAIN_KEYS = dict(_LIT_MAIN)
PACK = dict(_LIT_PACK); PACK.update(_st.load_pack(con))
SUBST = dict(_LIT_SUBST); SUBST.update(_st.load_subst(con))
# 2026-07-24 §A3 — 대표 승인으로 손지정한 재료 그룹 (없으면 자동 판정)
GRP_FIX = _st.load_dish_groups(con)
import json as _j
for slug, meta in _DB_DEFS.items():
    _nm = meta["tuple"][0]
    if meta["icon"]:
        ICON[_nm] = meta["icon"]
    if meta["main_keys_json"]:
        _mk = _j.loads(meta["main_keys_json"])
        if _mk:
            MAIN_KEYS[slug] = tuple(_mk)
    # 카테고리 누락 = 목록에서 고아 페이지 → healthcheck 실패. 미분류로라도 반드시 넣는다.
    _cat = meta["category"] or "기타"
    if not any(_nm in names for names in DISH_CAT.values()):
        DISH_CAT.setdefault(_cat, []).append(_nm)

def dish_rank(name):
    try: return PRIORITY.index(name)
    except ValueError: return 100 + ORDER.index(name)

def price_of(key):
    r = cur.execute("SELECT type,manual_price,base_unit FROM ingredients WHERE ingredient_key=?", (key,)).fetchone()
    if not r: return None, "kg"
    if r["type"] in ("live","live_composite"):
        h = cur.execute("SELECT retail_price FROM price_history WHERE ingredient_key=? AND retail_price>0 ORDER BY price_date DESC LIMIT 1", (key,)).fetchone()
        return (h["retail_price"] if h else r["manual_price"]), r["base_unit"]
    return r["manual_price"], r["base_unit"]

def line_cost(key, amount, unit):
    p, base = price_of(key)
    if p is None: return 0
    if base in ("kg","L"):
        q = amount/1000 if unit in ("g","ml") else amount
        return round(p*q)
    return round(p*amount)  # 개


# ── 재료 양 표기 ───────────────────────────────────────────────
#  DB는 무게를 **g으로만** 저장한다(kg 혼용 금지, 2026-07-25 규칙).
#  화면에서만 1,000g 이상을 kg으로 접어 보여준다 — "1600g"보다 "1.6kg"이 읽힌다.
#  gen_preview_html.py 의 fmt_amt 와 같은 규칙을 쓴다. 한쪽만 바꾸지 말 것.
def fmt_amt(amount, unit):
    if amount is None:
        return ""
    if unit in ("g", "ml") and amount >= 1000:
        big = "kg" if unit == "g" else "L"
        return (f"{amount/1000.0:.1f}".rstrip("0").rstrip(".")) + big
    return f"{amount:g}{unit}"


import os as _os2
import sys as _sys2
_sys2.path.insert(0, _os2.path.dirname(_os2.path.abspath(__file__)))
from namemask import mask as _mask     # 상표 마스킹은 namemask.py 한 곳에서 관리한다


def plain_name(nm):
    """화면에 쓸 재료 이름 — 브랜드·용량을 뗀다(2026-07-20 사용자 지시).

    🔴 2026-07-27: 여기 브랜드 목록이 생성기마다 달라서 `곰곰`·`뫼루니`·`로켓프레시` 가
       화면에 그대로 나갔다. 이제 `namemask.mask()` 를 먼저 통과시킨다 — 목록은 한 곳에만 둔다.

    "고추장(해찬들 태양초 1kg)" → "고추장"  ·  "백설탕(백설 1kg)" → "백설탕"
    "청정원 맛있는 중화 춘장 250g" → "중화 춘장"
    가격 계산은 원래 키로 하고, 표기만 바꾼다. 어떤 제품 기준인지는 최소구매 줄에 남는다.
    """
    s = re.sub(r"\s*\([^)]*\)\s*$", "", nm or "").strip()      # 끝의 괄호 통째로
    s = re.sub(r"\s*\d+(\.\d+)?\s*(kg|g|ml|L)\s*$", "", s, flags=re.I).strip()   # 끝 용량
    # ⚠️ 브랜드는 **뒤에 공백이 있을 때만** 뗀다. 안 그러면 "백설탕"에서 "백설"이 떨어져
    #   "탕"이 된다(2026-07-20 실측). 브랜드명은 보통 뒤에 띄어쓰기가 온다.
    for brand in ("청정원", "해찬들", "백설", "오뚜기", "샘표", "CJ", "동원", "풀무원",
                  "하인즈", "롯데", "종가집", "큐원", "곰표", "미나토", "고추명가", "코다노",
                  "아이엠소스", "하오츠", "친수", "삼립", "서울우유", "매일", "해표", "이츠웰"):
        if s.startswith(brand + " "):
            s = s[len(brand):].strip()
            break
    s = _mask(s)                    # 위 목록에 없는 상표(곰곰·뫼루니·로켓프레시…)까지 가린다
    return s or nm


#  🔴 **최소 구매 = 우리가 고른 쿠팡 상품 그 자체다** (2026-08-03 대표 지적).
#     `ingredient_pack` 은 업소용 규격이 섞여 있어 화면이 실제 소매와 어긋났다 —
#     참기름 소매는 **412g 8,890원**인데 화면엔 **1.8L 24,199원**, 쌀은 4.2kg인데 10kg.
#     쿠팡 링크로 사는 물건과 화면 숫자가 다르면 그 순간 신뢰가 깨진다.
_RETAIL_PACK = {}
try:
    for _r in cur.execute("SELECT ingredient_key k, price, pack_g FROM ingredient_retail "
                          "WHERE status='ok' AND COALESCE(pack_g,0)>0 AND COALESCE(price,0)>0"):
        _RETAIL_PACK[_r["k"]] = (_r["pack_g"] / 1000.0, _r["price"])
except Exception:
    pass


def pack_of(key, name, base):
    # ① 소매 상품이 있으면 **그 규격이 최소 구매다**
    #    ⛔ 단 **개·마리·세트 단위는 제외** — `pack_g` 는 무게라 그대로 쓰면
    #       「계란 0.9개」가 된다(2026-08-03). 그건 아래 PACK(개수)이 답이다.
    if key in _RETAIL_PACK and base in ("kg", "L", "g", "ml"):
        q = _RETAIL_PACK[key][0]
        big, sml = ("L", "ml") if base == "L" else ("kg", "g")
        return q, (f"{q:.1f}".rstrip("0").rstrip(".") + big if q >= 1
                   else f"{round(q*1000):g}{sml}")
    # ★ PACK(수동 지정)이 그다음 — 이름 파싱보다 정확하다(2026-07-20).
    #   예전엔 이름을 먼저 봐서 '식용유(해표 900ml)'의 라벨이 '900ml)'로 깨졌고,
    #   PACK에 적어둔 값이 무시됐다.
    if key in PACK: return PACK[key]
    m = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|L|ml)\b', name or '')
    if m:
        q = float(m.group(1)); u = m.group(2)
        qty = q if u in ('kg','L') else q/1000
        return qty, m.group(0)
    if base == '개': return 6, "6개입"
    if base == 'L': return 0.9, "900ml"
    return 0.5, "500g 팩"

# 시세 등락(live 재료): 최신 vs 직전 시세일
_dates = [r[0] for r in cur.execute("SELECT DISTINCT price_date FROM price_history ORDER BY price_date DESC LIMIT 2")]
LIVE_DELTA = {}
if len(_dates) == 2:
    for r in cur.execute("""SELECT a.ingredient_key k,a.retail_price c,b.retail_price p FROM price_history a
        JOIN price_history b ON a.ingredient_key=b.ingredient_key
        WHERE a.price_date=? AND b.price_date=? AND a.retail_price>0 AND b.retail_price>0""", (_dates[0], _dates[1])):
        LIVE_DELTA[r["k"]] = (r["c"], r["p"])
DELTA_LABEL = f"{_dates[1][5:].replace('-','.')} 대비" if len(_dates) == 2 else ""
def arrow(pct):
    if abs(pct) < 0.05: return '<span style="font-size:12px;color:var(--muted)">— 보합</span>'
    col, sym = ('#dc2626','▲') if pct > 0 else ('#1a56b0','▼')
    return f'<span style="font-size:12px;color:{col};font-weight:700">{sym} {pct:+.1f}%</span>'

# 시드 + 메뉴 매핑
menus = cur.execute("SELECT m.id,m.name,b.name bn,b.id bid,m.sell_price,m.est_cost,m.cost_ratio FROM menus m JOIN brands b ON m.brand_id=b.id WHERE b.published=1").fetchall()
dish_ids = {}
for name, slug, serving, pat, recipe in DISHES:
    # 자체 레시피(구글드라이브 35종)가 있으면 인분 표기도 그쪽을 따른다.
    #  ⚠️ 이 테이블은 매 실행마다 통째로 재생성되므로 **삽입 시점에** 심어야 한다.
    _r = DISH_RECIPES.get(slug)
    cur.execute("INSERT INTO dishes(name,slug,serving,sort_order,recipe_steps) VALUES(?,?,?,?,?)",
                (name, slug, serving, ORDER.index(name),
                 chr(10).join(_r[1]) if _r else None))
    did = cur.lastrowid; dish_ids[name] = (did, pat, recipe)
    # 검수 완료 레시피 확장분 복원(위 _KEEP 스냅샷) — OpenAI 생성분이 재실행에도 살아남게
    if slug in _KEEP:
        cur.execute("""UPDATE dishes SET recipe_steps=COALESCE(?,recipe_steps), tips_json=?,
            faq_json=?, seo_title=?, seo_intro=?, ing_json=?, recipe_serving=? WHERE id=?""",
            _KEEP[slug] + (did,))
    for i,(k,a,u) in enumerate(recipe):
        cur.execute("INSERT INTO dish_ingredients(dish_id,ingredient_key,amount,unit,sort_order) VALUES(?,?,?,?,?)", (did,k,a,u,i))
assigned = {}
for m in menus:
    cands = [(dish_rank(nm), nm) for nm,(did,pat,_) in dish_ids.items() if re.search(pat, m["name"])]
    if not cands: continue
    nm = min(cands)[1]
    cur.execute("INSERT OR IGNORE INTO dish_menus(dish_id,menu_id) VALUES(?,?)", (dish_ids[nm][0], m["id"]))
    assigned[m["id"]] = nm
con.commit()

# ── 페이지 생성 ──
from theme import CSS_VARS, HEAD_SCRIPT, BTN, AUTH_BTN, TOGGLE_JS, SHARE_BTN, SHARE_BTM, HEAD_TAGS, FOOTER_LINKS, FOOTER_CSS, ADFIT, ADFIT_CSS, CPSEARCH, CPSEARCH_CSS, SOURCES, SOURCES_CSS, GNAV, GNAV_CSS, WRAP_CSS, BODY_CSS, TYPO_CSS, gnav, P2_CSS
STYLE = "<style>" + CSS_VARS + FOOTER_CSS + ADFIT_CSS + CPSEARCH_CSS + SOURCES_CSS + GNAV_CSS + WRAP_CSS + P2_CSS + """
*{box-sizing:border-box;margin:0;padding:0}"""+BODY_CSS+TYPO_CSS+"""
header.top{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}
.logo{font-weight:800;font-size:18px;color:var(--ink);text-decoration:none}
.logo small{color:var(--muted);font-weight:500;font-size:12px;margin-left:8px;padding-left:8px;border-left:1px solid var(--line)}
h1{margin:14px 0 4px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin-bottom:12px}
.sect{font-size:15.5px;font-weight:800;margin:2px 0 10px}
table{width:100%;border-collapse:collapse;font-size:14px}
td,th{padding:9px 0;border-bottom:1px solid var(--line);text-align:left}
td.r,th.r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
tfoot td{font-weight:800;border-bottom:0;padding-top:12px}
.big{font-size:clamp(24px,20px+2vw,32px);font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums}
.sub{font-size:12.5px;color:var(--muted)}
.mrow{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 15px;margin-bottom:8px;text-decoration:none;color:inherit;display:flex;justify-content:space-between;align-items:center;gap:10px}
.mrow .mn{font-weight:700;font-size:14.5px}.mrow .mr{font-size:12px;color:var(--muted);margin-top:2px}.mrow .rt{font-weight:800;font-size:16px}
.buy{background:var(--softbg);border:1px solid var(--softline);border-radius:10px;padding:10px 12px;margin:6px 0;font-size:13.5px;font-weight:700}
.dhdr{display:flex;align-items:center;gap:9px;margin:2px 0}
.dhdr .di{flex:0 0 40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:var(--accentsoft);color:var(--accent)}.dhdr .di svg{width:21px;height:21px}
.dhdr h1{font-size:clamp(20px,17px+1.4vw,26px);font-weight:900;margin:0;letter-spacing:-.02em}
.dhdr .dsub{font-size:12px;color:var(--muted);margin-top:1px}
.dcount{font-size:12px;color:var(--muted);margin:14px 2px 8px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:2px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;text-decoration:none;color:inherit;display:block}
.tile .ti{font-size:24px;line-height:1}
/* 완성 사진 썸네일 — 사진이 있는 요리만. 없으면 요소 자체가 안 나가므로
   사진 있는 카드만 키가 커진다(2026-07-20). 비율 고정으로 CLS 방지. */
.tile .tt{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:10px;
  margin:-4px 0 8px;background:var(--line);display:block}
/* 일러스트 — 처음 크기에서 20% 줄인 것(2026-07-25 지시).
   카드: 100% → 80% 폭 / 상세: 340px → 272px */
.til{display:block;width:80%;height:auto;aspect-ratio:4/3;object-fit:contain;background:var(--bg);border-radius:10px;margin:0 auto 2px}
.dillwrap{text-align:center;margin:6px 0 14px}
.dill{width:80%;max-width:272px;height:auto;object-fit:contain}
.tile .tn{font-size:14px;font-weight:800;margin-top:8px}
.tile .tp{font-size:13px;font-weight:900;color:var(--ink);margin-top:6px;font-variant-numeric:tabular-nums}
.tile .tb{font-size:12px;color:var(--muted);font-weight:700;margin-top:1px}
.tc{font-size:12.5px;color:var(--muted);margin-top:1px}
.dsort{display:flex;align-items:center;gap:6px;margin:8px 0 2px;font-size:13px;color:var(--muted)}
.dsb{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:5px 10px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit}
.dsb.on{background:var(--accentsoft);color:var(--accent);border-color:var(--accent)}
.dchips{display:flex;gap:7px;overflow-x:auto;padding-bottom:4px;-webkit-overflow-scrolling:touch;margin-top:12px}
.dchip{flex:0 0 auto;border:1px solid var(--line);background:var(--card);border-radius:20px;padding:7px 13px;font-size:13px;font-weight:700;color:var(--muted);cursor:pointer;white-space:nowrap;font-family:inherit}
.dchip.on{background:var(--grad);color:#fff;border-color:transparent;font-weight:800}
.copy{font-size:12.5px;background:var(--line);color:var(--muted);border:0;padding:3px 9px;border-radius:6px;font-weight:600;cursor:pointer;margin-left:5px}
.disc{font-size:13px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-top:16px;line-height:1.6}
/* 요리상세 재설계 (Design 2026-07-18) */
.dh2{font-size:clamp(22px,6vw,28px);font-weight:900;letter-spacing:-.02em;margin:8px 0 12px}
.dcard{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px 18px;margin-bottom:18px}
.dcard .dcl{font-size:13px;color:var(--muted);margin-bottom:4px}
.dcard .dbig{font-size:clamp(30px,9vw,38px);font-weight:900;color:var(--ink);letter-spacing:-.02em;line-height:1;font-variant-numeric:tabular-nums}
.dcard .dcsub{font-size:12px;color:var(--muted);margin-top:8px}
.sect2{font-size:15px;font-weight:900;margin:0 0 10px}
/* 레시피 존 — B안(2026-07-20): 하단 전체폭, 이 페이지의 주인공이라 단계를 크게 쓴다 */
.rzone{margin-top:22px;padding-top:18px;border-top:2px solid var(--line)}
.sect2.big{font-size:clamp(18px,4.5vw,21px);margin-bottom:14px}
.rstep{display:flex;gap:12px;align-items:flex-start;background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:14px 15px;margin-bottom:8px}
.rstep .n{flex:0 0 26px;height:26px;border-radius:50%;background:var(--accentsoft);color:var(--accent);
font-size:13px;font-weight:900;display:flex;align-items:center;justify-content:center}
.rstep .t{font-size:14.5px;line-height:1.75}
.rsrc{font-size:12.5px;color:var(--muted);line-height:1.6;margin-top:6px}
.dlist{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-bottom:10px}
.dirow{display:flex;align-items:center;gap:10px;padding:12px 14px;border-top:1px solid var(--line)}
.dirow:first-child{border-top:0}
.dirow .dinfo{flex:1;min-width:0} .dirow .dinm{font-size:13px;font-weight:700} .dirow .diamt{font-size:12.5px;color:var(--muted)}
.dirow .dip{font-size:13px;font-weight:800}
.dsub{font-size:12.5px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:10px;line-height:1.6}
.dsub b{color:var(--ink);font-weight:800} .dsub small{display:block;color:var(--muted);font-size:12.5px;margin-top:2px}
.dshop{font-size:12px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:12px;line-height:1.5}
.cmp{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-bottom:14px}
/* 우측 카드 안에 들어갈 땐 카드가 이미 테두리를 그리므로 자기 테두리를 지우고,
   행이 카드 안쪽 여백까지 꽉 차게 좌우로 늘린다 */
.cmpbox{padding-bottom:0;overflow:hidden}
.cmpbox .cmp{border:0;border-radius:0;margin:0 -14px -1px;background:none}
.cmpbox .cmphead{padding-left:14px;padding-right:14px}
.cmpbox .cmprow,.cmpbox .cmpfoot,.cmpbox .cmpmore{padding-left:14px;padding-right:14px}
/* 브랜드가 최대 19곳이라 그대로 두면 화면을 다 잡아먹는다 — 줄을 얇게, 6곳까지만
   (2026-07-24 대표 지시: "필요도 없는 게 왜 이리 길어") */
.cmphead,.cmprow{display:flex;align-items:center;gap:8px;padding:7px 12px;border-top:1px solid var(--line)}
.cmphead{border-top:0;font-size:11.5px;font-weight:800;color:var(--muted);padding:6px 12px}
.cmprow{text-decoration:none;color:inherit}
.cmp .clogo{width:17px;height:17px;flex:none;border-radius:4px;object-fit:contain;background:#fff;border:1px solid var(--line)}
.cmp .cbrand{flex:1;font-size:12.5px;font-weight:700;min-width:0;overflow:hidden;
text-overflow:ellipsis;white-space:nowrap}
.cmp .cprice{width:78px;text-align:right;font-size:12.5px;font-weight:800}
.cmp .cmult{width:52px;text-align:right;font-size:11.5px;font-weight:800;color:var(--muted)}
.cmpfoot{padding:8px 12px;border-top:1px solid var(--line);font-size:11.5px;color:var(--muted);line-height:1.45}
.cmp.cut .cmprow:nth-of-type(n+6){display:none}
.cmpmore{display:block;width:100%;padding:8px;border:0;border-top:1px solid var(--line);
background:none;font:inherit;font-size:12px;font-weight:700;color:var(--muted);cursor:pointer}
.cmp:not(.cut) .cmpmore{display:none}
.dpc>div{min-width:0}
/* ── 요리상세 새 레이아웃 (2026-07-20 확정 구조) ────────────────── */
.sumgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:10px;margin-top:14px;
padding-top:14px;border-top:1px solid var(--line)}
.sumgrid .sl{font-size:12.5px;color:var(--muted);font-weight:700}
.sumgrid .sv{font-size:clamp(16px,4.2vw,19px);font-weight:900;margin:2px 0 1px;font-variant-numeric:tabular-nums}
.sumgrid .sn{font-size:12px;color:var(--muted)}
.sumnote{margin-top:10px}
.dirow .dip{text-align:right;line-height:1.35}
.dirow .dip small{display:block;font-size:12.5px;color:var(--muted);font-weight:600}
/* 재료 3열 그리드 — 좌우로 벌어져 가운데가 비던 표를 대체(2026-07-20) */
.grp{margin-bottom:16px}
.ghead{display:flex;align-items:baseline;font-size:13px;font-weight:800;margin:0 0 8px}
.ghead span{font-weight:600;color:var(--muted);font-size:13px;margin-left:5px}
.ghead em{margin-left:auto;font-style:normal;font-size:12.5px;font-weight:800;color:var(--muted);
font-variant-numeric:tabular-nums}
.grp.gstock .icell{background:var(--panel)}
.igrid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}
.icell{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 10px;position:relative}
/* 그룹 표시 — 그리드를 끊는 대신 카드 안에 색점+라벨 (2026-07-24 §A2)
   메인=주황 · 야채=초록 · 양념=회색 */
/* 이름 왼쪽 · 그룹표시 오른쪽 끝 (2026-07-24 대표 지시) */
.icell .ihead{display:flex;align-items:flex-start;justify-content:space-between;gap:6px;margin-bottom:5px}
.icell .gtag{display:inline-flex;align-items:center;gap:4px;font-size:11.5px;font-weight:700;
color:var(--muted);line-height:1.35;flex:none;white-space:nowrap}
.icell .gtag::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;flex:none}
.icell.g-main .gtag{color:var(--accent)}
.icell.g-sub .gtag{color:var(--dn)}      /* 부재료 = 파랑 (2026-07-24 대표 지시, 4그룹) */
.icell.g-veg .gtag{color:var(--good)}
.icell.g-stock .gtag{color:var(--faint)}
/* 🛒 장보기 선택 — **카드를 눌러 켜고 끈다.** 체크박스는 자리를 먹어 이름이 잘렸다(2026-08-03) */
.ipick{cursor:pointer;transition:border-color .12s,opacity .12s,background .12s}
.ipick:not(.on){opacity:.5;background:var(--panel)}
.ipick.on{border-color:var(--accent);background:var(--accentsoft)}
.ipick:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.ipick .copy{cursor:pointer}
/* ＋ 접힘 — 첫 줄 4칸만 보이고 나머지는 「집에 있을 만한 것」으로 접는다 (설계 §3-2-2) */
.imore{display:block;width:100%;margin:8px 0 0;padding:10px;border:1px dashed var(--line);
border-radius:10px;background:var(--panel);color:var(--muted);font-size:13px;font-weight:800;
cursor:pointer;font-family:inherit}
.imore:hover{border-color:var(--accent);color:var(--accent)}
.igrid.ihide{display:none;margin-top:7px}
.igrid.ihide.open{display:grid}
/* 이름이 길면 그룹 라벨을 밀어내 줄이 깨졌다("토마토 페이스트") — 한 줄로 자르고
   전체 이름은 title 툴팁으로 남긴다. 카드 높이도 이걸로 균일해진다. */
.icell .inm{font-size:13px;font-weight:800;line-height:1.35;min-width:0;flex:1;
overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* 조리법 위 재료 요약 — 만들면서 스크롤 안 올려도 되게 */
.ingrecap{background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:11px 13px;margin:0 0 12px;font-size:12.5px;line-height:1.9}
.ingrecap b{font-size:12.5px;font-weight:800;margin-right:8px;color:var(--muted)}
.ingrecap span{display:inline-block;margin-right:12px;white-space:nowrap}
.ingrecap i{font-style:normal;font-weight:800;font-variant-numeric:tabular-nums}
.icell .iuse{font-size:12.5px;color:var(--ink)}
.icell .iuse b{font-variant-numeric:tabular-nums}
.icell .ibuy{font-size:12.5px;color:var(--muted);margin-top:3px;line-height:1.4}
/* 카드 안 복사 버튼 — 공용 .copy의 margin-left를 지워야 가운데로 온다(2026-07-20) */
.icell .copy{display:block;margin:7px 0 0;width:100%;font-size:12.5px;padding:5px 0;text-align:center}
.dmore{display:block;width:100%;margin:14px 0 2px;padding:13px;border:1px solid var(--line);
border-radius:12px;background:var(--card);color:var(--ink);font-size:14px;font-weight:800;
cursor:pointer;font-family:inherit}
.dmore:hover{border-color:var(--accent);color:var(--accent)}
.gsum{display:flex;align-items:baseline;gap:6px;justify-content:flex-end;font-size:13px;
font-weight:800;margin:9px 2px 0}
.gsum span{font-size:13px;font-weight:600;color:var(--muted)}
.stockbox{margin-top:14px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 13px}
.stockbox summary{font-size:12.5px;font-weight:800;cursor:pointer;list-style:none}
.stockbox summary::-webkit-details-marker{display:none}
.stockbox summary::before{content:"▸ ";color:var(--muted)}
.stockbox[open] summary::before{content:"▾ "}
.stockbox summary span{font-weight:600;color:var(--muted)}
.stockbox .igrid{margin-top:11px}
.gnote{font-size:13px;color:var(--muted);line-height:1.6;margin-top:9px}
/* 📦 세트 상품 구성 — 「김밥재료세트」처럼 여러 재료가 한 봉지로 오는 것.
   안에 뭐가 들었는지 밝혀야 «김이 세트에 있는데 김밥김을 또 넣는» 중복을 막는다(2026-08-03) */
.dsetbox{margin-top:14px}
.dset{background:#f6f8fa;border:1px solid #e3e8ee;border-radius:9px;padding:10px 13px;
      font-size:13px;color:#4a5462;line-height:1.6;margin-bottom:7px}
.dset b{color:#1a1d21;font-weight:700}
.dtotbar{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-top:16px;padding:13px 15px;
background:var(--accentsoft);border:1px solid var(--accent);border-radius:12px}
.dtotbar span{font-size:12.5px;font-weight:700;flex:1}
.dtotbar b{font-size:19px;font-weight:900;color:var(--ink);font-variant-numeric:tabular-nums}
.dtotbar small{font-size:12.5px;color:var(--muted);white-space:nowrap;width:100%;text-align:right;margin-top:2px}
/* 재료 그리드 반응형 — 4열은 본문이 넓을 때만. 좁아지면 3→2열로 (2026-07-20) */
@media(max-width:840px){.igrid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:560px){.igrid{grid-template-columns:1fr 1fr}}
.dirow.dtot{background:var(--panel);font-weight:900}
.dirow.dtot .dinm{font-size:13.5px} .dirow.dtot .dip{font-size:15px}
.sect2 .sh{font-size:12px;font-weight:600;color:var(--muted)}
.stepcard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:6px 16px 14px}
.stepcard .rstep{background:transparent;border:0;border-radius:0;padding:14px 0 0;margin:0;
border-top:1px solid var(--line)}
.stepcard .rstep:first-child{border-top:0}
.stepcard .rstep .t{display:flex;flex-direction:column;gap:5px}
.stepcard .rstep .ln{display:block;font-size:14.5px;line-height:1.7}
.dside{display:flex;flex-direction:column;gap:12px}
.sidebox{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:13px 14px}
.sidet{font-size:13px;font-weight:800;margin-bottom:9px}
.rphotos{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:18px}
.rphotos img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:12px;display:block;border:1px solid var(--line)}
.rphotos figure{margin:0} .rphotos figcaption{font-size:12.5px;color:var(--muted);text-align:center;margin-top:5px}
.tipbox{display:flex;gap:10px;align-items:flex-start;background:var(--goodbg);border:1px solid var(--line);
border-radius:11px;padding:11px 13px;margin-bottom:7px}
.tipbox .n{flex:0 0 20px;height:20px;border-radius:50%;background:var(--good);color:#fff;font-size:12.5px;
font-weight:900;display:flex;align-items:center;justify-content:center}
.tipbox .t{font-size:13.5px;line-height:1.65}
.faq{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:12px 14px;margin-bottom:7px}
.faq summary{font-size:13.5px;font-weight:800;cursor:pointer;list-style:none}
.faq summary::-webkit-details-marker{display:none}
.faq summary::before{content:"Q ";color:var(--accent);font-weight:900}
.faq .a{font-size:13.5px;line-height:1.7;color:var(--muted);margin-top:8px;padding-top:8px;border-top:1px solid var(--line)}
.substbox{background:var(--infobg);border:1px solid var(--infoline);border-radius:12px;padding:6px 14px}
.substbox .srow{display:flex;gap:10px;align-items:baseline;padding:10px 0;border-top:1px solid var(--infoline)}
.substbox .srow:first-child{border-top:0}
.substbox .srow b{flex:0 0 110px;font-size:13px}
.substbox .srow span{font-size:13.5px;line-height:1.6;color:var(--ink)}
@media(max-width:520px){.substbox .srow{flex-direction:column;gap:3px}.substbox .srow b{flex:none}}
.ractions{display:flex;gap:8px;margin-top:22px}
.ract{flex:1;padding:13px;border:1px solid var(--line);border-radius:12px;background:var(--card);
color:var(--ink);font-size:14px;font-weight:800;cursor:pointer;font-family:inherit}
.ract:hover{background:var(--hover)}
@media(max-width:520px){.rphotos{grid-template-columns:1fr}}
/* 폭(.wrap/.top .in)은 theme.py WRAP_CSS 단일 출처가 정한다 — 여기서 다시 쓰지 말 것 */
/* 🎨 2026-08-02 대표 지시: **모바일 카드는 한 줄에 3개** (2열은 너무 컸다) */
@media(max-width:520px){
.grid{grid-template-columns:repeat(3,1fr);gap:8px}
.tile{padding:8px;border-radius:11px}
.tile .tn{font-size:12px;line-height:1.3}
.tile .tp{font-size:13.5px}
.tile .tb{font-size:11px}}
/* 🔴 2026-08-02 2차 보강 — 「재료비(쓴 만큼)」 vs 「장 보면(최소 구매)」 구분.
   숫자만 두면 오해가 생기고 그건 신뢰 문제다(대표 지시). 데이터 존이라 글로만 설명한다. */
.slx{font-weight:600;color:var(--muted);font-size:.86em}
.amtnote{margin:10px 0 0;font-size:12.5px;line-height:1.65;color:var(--muted);
background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 11px}
.amtnote b{color:var(--ink);font-weight:700}
/* 일러스트 — 모바일은 폭만 줄인다(중앙 정렬 유지) */
.dillwrap{text-align:center}
@media(max-width:520px){.dill{max-width:210px}}
@media(min-width:840px){.grid{grid-template-columns:repeat(4,1fr)}.mrow{max-width:none}
/* 🎨 2026-08-02 지시서 2차 §1 «3번안» — 상세 PC 는 **2열**이다.
     좌: 일러(360) → 가격카드 → 프랜차이즈 비교(.dside 를 좌열 아래로 **이동**)
     우: 재료 표(넓게)
   ⚠️ 비교 블록은 **위치만 옮겼다.** 마크업·내용은 그대로다(콘텐츠 삭제 금지 규칙).
   모바일은 단일 열이라 자연 순서가 «일러 → 가격 → 재료표 → 비교» 로 지시와 같다. */
.dpc{display:block}
.dtop{display:grid;grid-template-columns:360px minmax(0,1fr);gap:22px;align-items:start;
grid-template-areas:"l r" "a r"}
.dtop-l{grid-area:l}
.dtop-r{grid-area:r}
.dtop .dside{grid-area:a;margin-top:14px}
.dtop-l .dill{max-width:360px;width:100%}
.dtop-r .sect2{margin-top:0}}
</style><script>
function cpDone(b){var o=b.getAttribute('data-label')||b.textContent;b.setAttribute('data-label',o);
  b.textContent='복사됨';setTimeout(function(){b.textContent=o;},1200);}
function cpFallback(t,b){var ta=document.createElement('textarea');ta.value=t;
  ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();
  try{document.execCommand('copy');cpDone(b);}catch(e){b.textContent='복사 실패';}
  document.body.removeChild(ta);}
document.addEventListener('click',function(e){
  var b=e.target.closest('.copy');if(!b)return;
  var t=b.getAttribute('data-copy');if(!t)return;
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(t).then(function(){cpDone(b);},function(){cpFallback(t,b);});
  }else{cpFallback(t,b);}
});
document.addEventListener('click',function(e){
  var m=e.target.closest('.cmpmore');if(!m)return;
  m.closest('.cmp').classList.remove('cut');
});
/* 🛒 장보기 선택 — 카드를 눌러 켜고 끈다. 켠 것만 합산 (설계 §3-2) */
function shopSum(){
  var s=0;document.querySelectorAll('.ipick.on').forEach(function(c){
    s+=parseInt(c.getAttribute('data-shop'),10)||0;});
  document.querySelectorAll('.js-shopsum').forEach(function(el){
    el.textContent=s.toLocaleString('ko-KR')+'원';});
}
document.addEventListener('click',function(e){
  if(e.target.closest('.copy'))return;          /* 복사 버튼은 선택과 무관 */
  var c=e.target.closest('.ipick');if(!c)return;
  c.classList.toggle('on');shopSum();
});
document.addEventListener('keydown',function(e){
  if(e.key!==' '&&e.key!=='Enter')return;
  var c=e.target.closest&&e.target.closest('.ipick');if(!c)return;
  e.preventDefault();c.classList.toggle('on');shopSum();
});
/* ＋ 집에 있을 만한 것 펼치기/접기 */
document.addEventListener('click',function(e){
  var b=e.target.closest('.imore');if(!b)return;
  var h=b.nextElementSibling;if(!h)return;
  h.classList.toggle('open');
  if(!b.getAttribute('data-label'))b.setAttribute('data-label',b.textContent);
  b.textContent=h.classList.contains('open')?'− 접기':b.getAttribute('data-label');
});
</script>"""
# 배포 주소는 site_config.py 한 곳에서만 관리(= wrangler.toml의 SITE_ORIGIN)
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from site_config import SITE, clean_urls

def _clip(t, n=155):
    t = " ".join(str(t).split()); return t if len(t) <= n else t[:n-1] + "…"
# pSEO 사이트인데 meta description·canonical·og가 전무했다(2026-07-17). 검색 노출이 이 사이트의 자산이다.
HEAD = lambda title, desc="", path="": f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)} · 올마나마</title><meta name="description" content="{esc(_clip(desc))}"><meta property="og:title" content="{esc(title)} · 올마나마"><meta property="og:description" content="{esc(_clip(desc))}"><meta property="og:type" content="website"><meta property="og:image" content="{SITE}/og/share.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE}/og/share.png"><link rel="canonical" href="{SITE}/{path}">{HEAD_TAGS}{HEAD_SCRIPT}{STYLE}</head><body><header class="top"><div class="in"><a class="logo" href="index.html"><span class="lbadge">올</span>올마나마<small>브랜드 메뉴판 한 곳에서</small></a>{SHARE_BTN}{BTN}{AUTH_BTN}{gnav("dishes")}</div></header><div class="wrap">'
FOOT = ADFIT + SHARE_BTM + '<div class="disc">※ 표준 레시피는 일반적인 가정용 기준 <b>추정치</b>이며, 가격은 대형마트·온라인몰 소매가입니다. 소매가는 대형마트·온라인몰 판매가를 조사해 인용한 값이며, 그 자체는 제휴 링크가 아닙니다. 제휴 링크가 있는 자리에는 링크 옆에 따로 표시합니다.</div>' + SOURCES + FOOTER_LINKS + '</div>' + TOGGLE_JS + '</body></html>'

def won(n): return f"{n:,}원"

# ── 튀김 요리 공통 팁 (2026-07-21 사용자 지시) ──────────────────────────
#  원가에는 기름 **흡수분만** 잡는다(1.5L를 부어도 닭이 먹는 건 144ml, 나머지는 남는다).
#  매장은 한 솥으로 수십 마리를 튀기지만 집은 사정이 다르니, 집에서 기름을 아끼는 법을
#  팁으로 알려준다. 이 문장이 없으면 "기름값이 왜 이것뿐이냐"로 읽힌다.
# ── 부재료 묶음 정의 (slug → [(ingredient_key, 그램)]) ─────────────────
#  DB에 재료로 등록하지 않고 화면에만 한 줄로 합쳐 보여준다.
#  흑임자는 통깨와 다른 재료라 대체하지 않고 뺐다(토핑이라 원가 영향도 거의 없다).
SUB_ING = {
    "matchoking": [("garlic_minced", 20), ("sp_d5eda193b6", 30), ("pepper_cheongyang", 20)],
}

# Recipe JSON-LD의 recipeCuisine (2026-07-23, Search Console 구조화 데이터 필드 누락 대응).
#  요리 72종 슬러그 → 요리 계열. DB에 근거 컬럼이 없어 요리명 기준으로 직접 분류했다.
#  없는 슬러그는 기본값 "한식"으로 폴백(dish_page()의 Recipe JSON-LD 조립부에서 처리).
CUISINE_MAP = {
    "buncha": "베트남식", "pho": "베트남식",
    "donkatsu": "일식", "omurice": "일식", "sushi": "일식", "udon": "일식",
    "jjajangmyeon": "중식", "jjamppong": "중식", "malatang": "중식",
    "malaxiangguo": "중식", "tangsuyuk": "중식",
    "burger": "양식", "caffe-latte": "양식", "cream-pasta": "양식", "hotdog": "양식",
    "pizza": "양식", "poke": "양식", "salad": "양식", "steak": "양식",
    "tomato-pasta": "양식", "waffle": "양식", "bingsu": "양식",
}

FRY_OIL_TIP = ("매장처럼 기름을 가득 붓지 않아도 돼요. 냄비에 반 정도만 두르고 조금씩 "
               "나눠 여러 번 튀기면 기름을 훨씬 적게 쓰고, 쓴 기름은 체에 걸러 두었다가 "
               "다음에 또 쓰면 돼요.")
_FRY_OIL_KEYS = {"frying_oil", "cg_cooking_oil", "olive_blend_oil", "olive_oil"}

def _is_fried(steps_text, ing_rows):
    """튀김 요리인가 — 재료에 튀김기름이 있고 조리법에 '튀'가 나오면 튀김으로 본다."""
    if not any(k in _FRY_OIL_KEYS for k, _a, _u in ing_rows):
        return False
    return "튀" in (steps_text or "")

tiles = []
for name, slug, serving, pat, recipe in DISHES:
    did = dish_ids[name][0]
    # 1인분 식사류는 4인분(가족 기준)으로 스케일 — 포장 단위 구매와 현실적으로 맞음
    # ★ 단, **검수된 자체 레시피가 있는 요리는 스케일하지 않는다**(2026-07-20 사용자 지시:
    #   "조리는 1인분 기준"). 레시피 분량과 재료표 분량이 어긋나면 안 되기 때문.
    _has_own = _HAS_RECIPE_COLS and cur.execute(
        "SELECT 1 FROM dishes WHERE id=? AND COALESCE(recipe_serving,'')<>''", (did,)).fetchone()
    scale = 1 if _has_own else (4 if serving == "1인분" else 1)
    if scale == 4:
        serving_label = "4인분 · 가족 기준"
        recipe = [(k, a*4, u) for k, a, u in recipe]
    else:
        serving_label = serving
    rows = ""; main_cells = ""; veg_cells = ""; stock_cells = ""; all_cells = "";
    cells_by_g = {"main": [], "sub": [], "veg": [], "flour": [], "stock": [], "pantry": []}; sub_total = 0; subst_list = []; total = 0; prev_total = 0; buy = ""; ing_ld = []
    shop_total = 0; possible_min = None; tip_example = None
    w_total = 0        # 매장(도매) 재료비 합계
    stock_total = 0    # 양념·소스 구매액
    main_total = 0     # 메인 재료 구매액
    veg_total = 0      # 야채 구매액
    pantry_list = []   # 🔴 2026-08-02 상비 — 화면에서 아예 뺀 것(아래 「안 보임」 안내에만 쓴다)

    # ── 🥇 메인 재료 판정 (2026-08-03 대표 지시 «메인 재료 제대로 선택하게 해라») ──────
    #  전엔 `축산물·수산물이면 메인` 이라 **간장치킨 참깨 2g·탕수육 계란**이 메인이었고,
    #  반대로 **김밥재료세트·자반고등어·해물믹스·삶은순대·피자치즈**는 가공식품이라 소스로 갔다.
    #  → ①메인이 될 수 있는 성격인지(subcat·이름) ②그 요리에서 **돈이 실제로 나가는지**(비중)
    #    두 가지를 함께 본다. 양념·가루·채소는 아무리 비싸도 메인이 아니다.
    MAIN_CAT = ("축산물", "수산물")
    MAIN_TAIL = ("면·떡", "두부·묵", "곡물", "햄·소시지", "수산가공",
                 "유제품", "빵·디저트", "냉동·간편식", "절임·김치", "기타")
    NOT_MAIN_WORD = ("소스", "양념", "드레싱", "시즈닝", "파우더", "가루", "스톡",
                     "농축", "다시", "식초", "시럽", "올리고당", "물엿", "케첩", "육수")
    _cand, _lc = {}, {}
    for _k, _a, _u in recipe:
        _r = cur.execute("SELECT COALESCE(display_name,name) dn, COALESCE(subcat,'') s "
                         "FROM ingredients WHERE ingredient_key=?", (_k,)).fetchone()
        if not _r or _k == "water":
            continue
        _lc[_k] = line_cost(_k, _a, _u)
        _t0 = _r["s"].split("/")[0]; _t1 = _r["s"].split("/")[-1]
        _nm = _r["dn"]
        if any(w in _nm for w in NOT_MAIN_WORD):
            continue                              # 양념·가루는 메인 후보가 아니다
        if is_pantry(_k, _nm):
            continue                              # 상비도 아니다
        if _t0 in MAIN_CAT or _t1 in MAIN_TAIL:
            _cand[_k] = _lc[_k]
    _sum = sum(_lc.values()) or 1
    #  비중 12% 이상이면 메인. 하나도 없으면 **후보 중 제일 비싼 것 하나**를 메인으로 —
    #  「메인 없는 요리」가 생기면 첫 줄이 비어 화면이 무너진다(고등어구이·물회·해물찜이 그랬다).
    AUTO_MAIN = {k for k, v in _cand.items() if v * 100.0 / _sum >= 12}
    if not AUTO_MAIN and _cand:
        AUTO_MAIN = {max(_cand, key=lambda x: _cand[x])}

    for k,a,u in recipe:
        # 🔴 `display_name` 이 화면 이름이다 (2026-07-27 대표 지시) —
        #    `뫼루니 베이직 치킨용파우더 5kg` 이 그대로 나가던 자리다. 상품명은 이름이 아니다.
        ing = cur.execute("SELECT COALESCE(display_name, name) AS name, COALESCE(is_retail,0) ir,"
                          " base_unit FROM ingredients WHERE ingredient_key=?", (k,)).fetchone()
        c = line_cost(k,a,u); total += c
        if k in LIVE_DELTA and LIVE_DELTA[k][0]:
            prev_total += round(c * LIVE_DELTA[k][1] / LIVE_DELTA[k][0])
        else:
            prev_total += c
        # 화면엔 브랜드·용량을 뗀 이름을 쓴다. 쿠팡 검색 복사도 이 이름이 더 잘 맞는다.
        nm_ing = plain_name(ing["name"]); nm_e = esc(nm_ing)
        # 장보기(포장 단위) 계산
        p, base = price_of(k)
        usage = a/1000 if u in ("g","ml") else a          # base_unit 수량
        pk_qty, pk_label = pack_of(k, nm_ing, ing["base_unit"])
        import math
        packs = max(1, math.ceil(usage/pk_qty)) if pk_qty else 1
        # 🔴 소매 상품이 있으면 **그 상품 가격**을 쓴다 — 단가×규격으로 되짚으면
        #    쿠팡에서 실제로 결제하는 금액과 어긋난다(2026-08-03).
        line_shop = (round(_RETAIL_PACK[k][1] * packs)
                     if (k in _RETAIL_PACK and ing["base_unit"] in ("kg", "L", "g", "ml"))
                     else round((p or 0) * pk_qty * packs))
        # 🔴 shop_total 은 여기서 더하지 않는다 — **메인·부재료만** 센다(2026-07-26 대표 지시).
        #    전엔 전 재료의 포장값을 다 더해서 양념치킨 장보기가 53,908원으로 나왔다.
        #    그 금액의 대부분이 양념이었다(고추장 500g 6,625 · 통깨 1kg 5,900 · 계란 30구 11,970 …).
        #    양념·기름은 집에 이미 있거나 한 번 사서 여러 요리에 쓰는 것이라, 한 끼 장보기
        #    비용으로 제시하면 숫자가 거짓이 된다. 그룹 판정 뒤(아래)에서 main/sub 만 더한다.
        if usage > 0 and pk_qty:
            ratio = (pk_qty*packs)/usage
            possible_min = ratio if possible_min is None else min(possible_min, ratio)
        if tip_example is None and ing["ir"]:
            tip_example = nm_ing
        # 모든 재료에 복사 버튼 (쿠팡 검색용)
        # 복사값은 data 속성으로만 넘긴다. onclick에 심으면 esc()가 '를 &#x27;로 바꾸고
        # HTML 파서가 그걸 다시 '로 풀어 JS 문자열이 깨진다("쉐프's 소스" 같은 제품명).
        ing_ld.append({"nm": nm_ing, "a": a, "u": u})
        # 도매(매장) 라인가 — 재료별 도매 단가 × 사용량
        _wp = cur.execute("SELECT wholesale_price FROM ingredients WHERE ingredient_key=?", (k,)).fetchone()
        w_line = round((_wp["wholesale_price"] or 0) * usage) if _wp and _wp["wholesale_price"] else None
        w_total += w_line or 0
        # 재료 카드 — 좌우로 벌어져 가운데가 비던 표 대신 3열 그리드로 압축(2026-07-20).
        #  한 칸에 ①1인분 양·비용 ②최소 구매 단위·가격을 같이 담는다.
        if k != "water":
            # 3번째 줄에서 재료명 반복을 뗀다 (2026-07-24 통합지시서 §A2).
            #  "진간장 500ml 3,006원" → "500ml 3,006원". 카드 제목에 이미 이름이 있고,
            #  좁은 폰에서 이 줄이 줄바꿈되며 카드 높이가 널뛰던 원인이었다.
            #  ⚠️ DB의 재료명(제조사·용량)은 건드리지 않는다 — 표시 계층에서만 자른다.
            #  재료명이 DB명과 조금만 달라도(치즈 vs 피자치즈, 백설탕 vs 설탕) startswith가
            #  안 걸려 이름이 그대로 남았다. 그래서 **첫 숫자 앞을 통째로 자른다** —
            #  포장 라벨은 늘 "<이름> <수량><단위>" 꼴이라 이게 확실하다.
            _pk = esc(pk_label)
            _cut = re.sub(r"^[^\d]*", "", _pk).strip()
            if _cut:
                _pk = _cut
            # 🔴 2026-08-03 대표 지시 — 규격은 숫자+단위만. 「15구(900g)」→「15구」·「500g 팩」→「500g」
            _pk = re.sub(r"\(.*?\)", "", _pk)
            _pk = re.sub(r"\s*팩\s*$", "", _pk).strip()
            # 🔴 **위아래 단위를 맞춘다** (2026-08-03 대표 지시) —
            #    위가 「1개」인데 아래가 「15구 900g」이면 몇 개를 사야 하는지 못 읽는다.
            #    `base_unit` 이 개·마리·세트면 규격도 그 단위로 통일한다.
            #    ⛔ 부피↔무게도 섞지 않는다 — 「참기름 5ml 인데 1.8kg」 (2026-08-03).
            _bu = ing["base_unit"]
            if _bu not in ("kg", "L", "g", "ml"):
                _n = re.match(r"\s*(\d+(?:\.\d+)?)", _pk)
                _pk = (f'{_n.group(1).rstrip("0").rstrip(".")}{_bu}' if _n else f'1{_bu}')
            elif pk_qty:
                # 사용량이 ml 이면 규격도 ml·L, g 이면 g·kg 으로 (1:1 환산 — 조리용 액체 관례)
                _big, _sml = ("L", "ml") if u == "ml" or _bu == "L" else ("kg", "g")
                _pk = ((f'{pk_qty:.1f}'.rstrip("0").rstrip(".") + _big) if pk_qty >= 1
                       else f'{round(pk_qty * 1000):g}{_sml}')
            # 🔴 2026-08-03 대표 지시 — 카드 재료명은 **최대 6글자**. 10글자 넘어도 6글자.
            #    전체 이름은 title 툴팁·복사 버튼에 남는다.
            _nm6 = esc(nm_ing[:6])
            # 이름이 먼저, 그룹표시(●메인)는 같은 줄 오른쪽 끝 — 2026-07-24 대표 지시.
            #  gtag는 아래 _cellhtml에서 .ihead 안으로 끼워넣는다.
            _cell = (f'<div class="icell"><div class="ihead"><div class="inm" title="{nm_e}">{_nm6}</div></div>'
                     f'<div class="iuse">{esc(fmt_amt(a, u))} · <b>{won(c)}</b></div>'
                     + (f'<div class="ibuy">{_pk} {won(line_shop)}</div>'
                        if pk_qty and p else '<div class="ibuy">—</div>')
                     # 대체안내는 재료 카드에 안 넣는다(2026-07-20 사용자 지시) — 카드가 길어지고
                     #  칸마다 높이가 들쭉날쭉해진다. 레시피 영역의 '재료가 없을 때'로만 모은다.
                     + f'<button class="copy" data-copy="{nm_e}">복사</button></div>')
            if k in SUBST:
                subst_list.append((nm_ing, SUBST[k]))
            # 3그룹 분류(2026-07-20 사용자 지시): ①메인 재료 ②야채 ③양념·소스
            #  "춘장은 짜장면의 메인인데 왜 집에 있을 만한 것으로 내려가나" 지적 반영.
            #  요리의 정체성을 만드는 재료는 소스여도 메인이다 → MAIN_KEYS로 요리별 지정.
            _sc = cur.execute("SELECT COALESCE(subcat,'') s FROM ingredients WHERE ingredient_key=?",
                              (k,)).fetchone()["s"]
            _tail = _sc.split("/")[-1] if "/" in _sc else ""
            _top = _sc.split("/")[0] if "/" in _sc else ""
            #  2026-07-24 §A2: 그룹별로 그리드를 끊지 않고 **한 그리드에 연속 배치**한다.
            #   대신 카드 안에 색점+라벨을 넣어 어느 그룹인지 알린다.
            # 🔴 대표 승인 지정(dish_def_ingredient.grp)이 있으면 그게 최우선.
            #    없을 때만 아래 자동 판정을 쓴다. (2026-07-24 §A3 — 4그룹)
            # 🔴 2026-08-02 «상비» — 거의 모든 집에 있고 이 요리 때문에 사러 가지 않는 것.
            #    설계: reports/설계-재료-장보기-2026-08-02.md §3-2
            #    대표: *"기본적인 소금 후추 설탕 양이 많은거는 있는거야. 애초에 빼버리면 되"*
            # 🔴 2026-08-03 대표 지시 — 상비(꽃소금·참기름·조미료·소스류)도 **숨기지 않는다.**
            #    접힘 목록 맨 뒤에, 꺼진 채로 넣는다. 「집에 있는 것으로 봤어요」 안내문도 폐지.
            _pantry = is_pantry(k, nm_ing)
            _fix = GRP_FIX.get((slug, k))
            if _fix:
                _g = {"메인": "main", "부재료": "sub", "야채": "veg", "양념": "stock"}.get(_fix, "stock")
            elif k in MAIN_KEYS.get(slug, ()):
                _g = "main"                      # 사람이 지정한 것이 최우선
            elif k in AUTO_MAIN:                 # 위에서 «성격 + 비중»으로 고른 것
                _g = "main"
            elif k in _cand:
                # 메인 성격인데 비중이 작아 주인공은 못 된 것 → **부재료**.
                #  ⛔ 소스로 보내면 안 된다 — 비빔밥 쌀·탕수육 계란이 「소스」로 찍혔다(2026-08-03)
                _g = "sub"
            elif _tail in ("채소",):
                _g = "veg"
            # 🔴 2026-08-02: 「양념」을 **가루**와 **소스**로 가른다(대표 지시).
            #    *"가루류는 더 많이 없을수 있는거라서. 소스류는 다 들어가도 가루류는 다 안들어가잖아"*
            #    subcat 에 `가공식품/분말·가루` 가 이미 있어 태그를 새로 붙일 필요가 없다.
            elif _tail in ("분말·가루",) or any(
                    w in nm_ing for w in ("가루", "전분", "분말", "믹스")):
                _g = "flour"
            else:
                _g = "stock"
            if _pantry and _g in ("main", "sub"):   # 상비가 메인으로 판정되는 일은 없어야 한다
                _pantry = False
            if _g == "main":    main_total += line_shop
            elif _g == "sub":   sub_total += line_shop
            elif _g == "veg":   veg_total += line_shop
            else:               stock_total += line_shop
            # 장보기 총액 = 메인 + 부재료만 (야채·가루·소스 제외). 위 주석 참고.
            #  🔴 나머지는 화면에서 **꺼진 채로** 나가고, 방문자가 켜면 그때 더해진다.
            if _g in ("main", "sub"):
                shop_total += line_shop
            _lab = {"main": "메인", "sub": "부재료", "veg": "야채",
                    "flour": "가루", "stock": "소스"}[_g]
            # 🛒 체크 — 켠 것만 「장 보면」에 합산 (설계 §3-2 · ⛔ 수정 기능 없이 진행 금지).
            #    기본 켜짐 = 메인·부재료(서버 렌더 금액과 같아야 한다) · 나머지 꺼짐.
            #    ⛔ **체크박스를 쓰지 않는다** (2026-08-03 대표 지시) — 아이콘이 자리를 먹어
            #       재료명이 4~5글자에서 잘렸다. **카드를 눌러 켜고 끄는** 방식으로 바꿨다.
            _on = _g in ("main", "sub")
            _cellhtml = (_cell
                         .replace('<div class="icell">',
                                  f'<div class="icell g-{_g} ipick{" on" if _on else ""}"'
                                  f' role="button" tabindex="0"'
                                  f' data-shop="{line_shop if (pk_qty and p) else 0}">', 1)
                         .replace('</div></div>', f'</div><span class="gtag">{_lab}</span></div>', 1))
            # 표시 순서: 메인 → 부재료 → 야채 → 양념 (대표 지시 2026-07-24)
            # 상비는 그룹 라벨은 그대로 두고 **자리만 접힘 맨 뒤**로 뺀다(2026-08-03)
            # 🔴 **메인 안에서는 재료비가 큰 것이 앞이다** (2026-08-03 대표 지시 —
            #    *"김밥재료세트면 제일 처음에 있어야지"*). 요리의 주인공이 첫 칸에 온다.
            #    ⚠️ 다른 그룹은 **레시피 순서 그대로** — 가격순 정렬 금지 규칙은 그대로 산다.
            cells_by_g["pantry" if _pantry else _g].append(
                (-_lc.get(k, 0), _cellhtml) if _g == "main" else (0, _cellhtml))
        if ing["ir"]:
            buy += '<div class="buy">' + nm_e + ' <button class="copy" data-copy="' + nm_e + '">복사→쿠팡검색</button></div>'
    ms = cur.execute("""SELECT m.id,m.name,b.name bn,b.logo_url lg,m.sell_price,m.est_cost,m.cost_ratio
        FROM dish_menus dm
        JOIN menus m ON dm.menu_id=m.id JOIN brands b ON m.brand_id=b.id WHERE dm.dish_id=? AND b.published=1 ORDER BY m.sell_price""", (did,)).fetchall()
    # 만드는 법 — 요리마다 **자체 레시피**를 갖는다(2026-07-20, 구글드라이브 35종 반영).
    #  자체 레시피는 재료표와 분량이 맞춰져 있어 점검지시서 A-3(단계↔재료표 불일치)이 해소된다.
    #  없을 때만 예전처럼 연결된 브랜드 메뉴 것을 빌리고, 그때는 어느 메뉴 기준인지 밝힌다.
    _rserv = (DISH_RECIPES.get(slug) or ("", []))[0] or serving_label
    _own = cur.execute("SELECT recipe_steps rs FROM dishes WHERE id=?", (did,)).fetchone()
    if _own and (_own["rs"] or "").strip():
        _rc = {"rs": _own["rs"], "bn": None, "mn": None}
    else:
        _rc = cur.execute("""SELECT m.name mn, b.name bn, m.recipe_steps rs FROM dish_menus dm
            JOIN menus m ON dm.menu_id=m.id JOIN brands b ON m.brand_id=b.id
            WHERE dm.dish_id=? AND b.published=1 AND m.recipe_steps IS NOT NULL AND m.recipe_steps<>''
            ORDER BY m.sell_price LIMIT 1""", (did,)).fetchone()
    recipe_html = ""
    if _rc:
        # 레시피 본문에 박힌 상표를 화면에서 가린다(2026-07-27 대표 지시) — DB 원문은 그대로
        _steps = [_mask(s) for s in _rc["rs"].split("\n") if s.strip()]
        # 단계는 **카드 하나 안에** 쭉 넣는다(2026-07-20 사용자 지시). 카드 6개로 쪼개지 않는다.
        #  한 단계에 문장이 3개씩 붙어 글이 뭉쳐 보였다 → **문장 단위로 줄바꿈**해서 읽기 쉽게.
        def _sentences(t):
            parts = re.split(r'(?<=[.!?요다])\s+', t.strip())
            return [p.strip() for p in parts if p.strip()]
        # 조리법 바로 위에 재료를 한 번 더 — 재료 카드가 화면 위쪽에 있어서
        #  만들면서 보기 어렵다는 지적(2026-07-24 대표). 스크롤 없이 여기서 바로 확인.
        _recap = ('<div class="ingrecap"><b>재료</b>'
                  + "".join(f'<span>{esc(x["nm"])} <i>{esc(fmt_amt(x["a"], x["u"]))}</i></span>'
                            for x in ing_ld) + '</div>') if ing_ld else ''
        recipe_html = (f'<h2 class="sect2 big">{esc(name)} 만드는 법 — {esc(serving_label)} 레시피</h2>'
                       + _recap
                       + '<div class="stepcard">'
                       + "".join(f'<div class="rstep" id="dstep{i+1}"><span class="n">{i+1}</span>'
                                 f'<span class="t">'
                                 + "".join(f'<span class="ln">{esc(x)}</span>' for x in _sentences(s))
                                 + '</span></div>' for i, s in enumerate(_steps))
                       + '</div>'
                       + ((f'<div class="rsrc">※ {esc(_rc["bn"])} {esc(_rc["mn"])} 기준 조리법입니다. '
                          '가정에서 만들 때의 참고용이며 실제 매장 조리법과는 다릅니다.</div>')
                          if _rc["bn"] else
                          '<div class="rsrc">※ 가정용 조리법입니다. 매장 조리법과는 다릅니다.</div>'))
    # 브랜드 로고 표시(2026-07-21 사용자 지시). 로고가 없는 브랜드는 이미지를 빼고 이름만 낸다.
    _lg = lambda r: (f'<img class="clogo" src="{esc(r["lg"])}" alt="" loading="lazy">'
                     if r["lg"] else '')
    comp = "".join(f'<a class="cmprow" href="menu_{r["id"]}.html">{_lg(r)}<span class="cbrand">{esc(r["bn"])} {esc(r["name"])}</span>'
                   f'<span class="cprice">{won(r["sell_price"])}</span>'
                   f'</a>' for r in ms if total)
    # 평균은 1인분(4,000)과 2~3인용(20,900)이 섞여 왜곡 → 중앙값 사용
    _p = sorted(r["sell_price"] for r in ms)
    avg = (_p[len(_p)//2] if len(_p) % 2 else round((_p[len(_p)//2-1]+_p[len(_p)//2])/2)) if _p else 0
    save = (avg * scale - total) if avg else 0
    per1 = round(total / scale) if scale > 1 else None
    save_txt = ''
    if save > 0:
        if scale > 1:
            save_txt = f'<p class="sub" style="margin-top:8px">프랜차이즈 {scale}그릇 {won(avg*scale)}<span style="font-size:12.5px">(중간가 {won(avg)} 기준)</span> → 집에서 {scale}인분 {won(total)} = <b style="color:var(--good)">약 {won(save)} 절약</b></p>'
        else:
            save_txt = f'<p class="sub" style="margin-top:8px">프랜차이즈 중간가 {won(avg)} → 집에서 만들면 <b style="color:var(--good)">약 {won(save)} 절약</b></p>'
    # 3단 가격: 소매가(1인분) / 소매가(기준량) / 장보기 비용(조리가능)
    # 단위는 scale이 아니라 **요리의 기준 표기**에서 뽑는다(2026-07-20: "2인분이면 2인분이라고 적어").
    #  예전엔 scale==1이면 무조건 '회'가 되어 '2회 분량'처럼 나왔다.
    unit_word = next((w for w in ("인분", "개", "잔", "줄", "판", "마리", "그릇", "피스")
                      if w in serving), "회")
    possible = int(possible_min * scale) if (possible_min and scale > 1) else (int(possible_min) if possible_min else 0)
    shop_per1 = round(shop_total / possible) if possible else 0
    price3 = f'''<table style="margin-top:10px;font-size:13.5px"><tr><td>소매가 (1인분)</td><td class=r><b>{won(per1)}</b></td></tr>''' if per1 else '<table style="margin-top:10px;font-size:13.5px">'
    price3 += f'''<tr><td>소매가 ({esc(serving_label.split(" ")[0] if scale>1 else serving)})</td><td class=r><b style="color:var(--accent)">{won(total)}</b></td></tr>
<tr><td>장보기 비용 <span style="font-size:12.5px;color:var(--muted)">(담은 재료만)</span></td><td class=r><b class="js-shopsum">{won(shop_total)}</b><div style="font-size:13px;color:var(--muted)">약 {possible}{unit_word} 조리 가능 · 1{unit_word}당 {won(shop_per1)}</div></td></tr></table>'''
    # 소량(1~2인)만 필요할 땐 밀키트가 대안 (사용자 아이디어)
    mk = MEALKIT.get(name)
    mk_html = ""
    if mk:
        mk_nm, mk_serv, mk_price = mk
        mk_e = esc(mk_nm)
        mk_html = ('<div class="buy" style="background:var(--infobg);border-color:var(--infoline)"><b>1~2인분만 필요하면 밀키트</b>: '
                   + mk_e + f' <span style="color:var(--muted);font-weight:500">({esc(mk_serv)} · 약 {won(mk_price)})</span> '
                   + '<button class="copy" data-copy="' + mk_e + '">복사→쿠팡검색</button></div>')
    tip_ex = f"예: {esc(tip_example)} 한 개" if tip_example else "예: 소스 한 통, 식용유 한 병"
    icon = ICON.get(name, "🍽️")
    # 2026-07-19 사용자 지시로 "밀키트 쿠팡에서 보기" 버튼 삭제.
    #  (재료별 '복사' 버튼 + 아래 쿠팡 검색 위젯으로 동선이 대체됨)
    # 재료 3그룹 블록 — 메인 / 야채 / 양념·소스 (2026-07-20 사용자 확정 구조)
    def _grp(title, sub, cells, tot, cls=""):
        if not cells:
            return ""
        return (f'<div class="grp {cls}"><div class="ghead">{title}<span> · {sub}</span>'
                + (f'<em>{won(tot)}</em>' if tot else '') + '</div>'
                + f'<div class="igrid">{cells}</div></div>')
    #  🔴 2026-07-24 §A2: 그룹 소계(예: "야채 19,482원")를 없앴다.
    #     그건 **장보기 총액**이라 1인분 재료비(1,922원) 옆에 붙으면 같은 성격의 숫자로 오해된다.
    #     합계는 하단 바(dtotbar) 하나만 남긴다.
    # 🔴 2026-08-02 설계 §3-2-3 — 목록 정렬은 «메인 → 야채 → 가루 → 소스».
    #    장 볼 때 머릿속 순서다. 같은 분류끼리 붙인다.
    #    ⛔ 가격순 금지 — *"양파는 1번에 있는데 당근은 8번에 있으면 안됨"*
    # 🔴 2026-08-03 설계 §3-2-2 — **첫 줄 4칸 + 나머지 접힘.**
    #    메인은 무조건 보인다(4개를 넘겨도 다 보인다 — 부대찌개).
    #    첫 줄 채우기 순서는 «메인 → 가루 → 야채 → 소스» (사야 할 가능성 순),
    #    접힌 목록 안 순서는 «야채 → 가루 → 소스» (목록 정렬 규칙 그대로).
    # 메인만 재료비 내림차순(위 주석), 나머지는 레시피 순서 그대로
    _pull = lambda g, s=False: [c for _, c in (sorted(cells_by_g[g], key=lambda x: x[0])
                                              if s else cells_by_g[g])]
    _vis = _pull("main", True) + _pull("sub")
    _rest = {"flour": _pull("flour"), "veg": _pull("veg"), "stock": _pull("stock")}
    for _gg in ("flour", "veg", "stock"):        # 첫 줄 4칸을 채운다
        while len(_vis) < 4 and _rest[_gg]:
            _vis.append(_rest[_gg].pop(0))
    _hid = _rest["veg"] + _rest["flour"] + _rest["stock"] + _pull("pantry")
    ing_blocks = (f'<div class="igrid">{"".join(_vis)}</div>' if _vis else '')
    if _hid:
        ing_blocks += (f'<button class="imore" type="button">＋ 집에 있을 만한 것 {len(_hid)}가지 — '
                       f'없으면 체크해서 담으세요</button>'
                       f'<div class="igrid ihide">{"".join(_hid)}</div>')

    # 🔴 **세트 상품은 무엇이 들어 있는지 밝힌다** (2026-08-03 대표 지시)
    #    「김밥재료세트」처럼 여러 재료가 한 봉지로 오는 것은, 그 안에 뭐가 들었는지
    #    안 적으면 «김이 세트에 있는데 김밥김을 또 넣는» 중복이 생긴다.
    #    `ingredients.name_note` 에 「세트 5종: …」 형태로 적어두면 여기 뜬다.
    _sets = []
    for _k, _a, _u in recipe:
        _row = cur.execute("SELECT COALESCE(display_name,name) nm, COALESCE(name_note,'') note "
                           "FROM ingredients WHERE ingredient_key=?", (_k,)).fetchone()
        if not _row:
            continue
        _note = (_row["note"] or "").strip()
        if _note and ("세트" in _note or "구성" in _note):
            _sets.append('<b>%s</b> — %s' % (esc(_row["nm"]), esc(_note)))
    set_html = ('<div class="dsetbox">' +
                ''.join('<div class="dset">📦 %s</div>' % s for s in _sets) +
                '</div>') if _sets else ''
    # ⛔ 2026-08-03 대표 지시 — 「집에 있는 것으로 봤어요」·「양념·기름은 한 번 사면…」
    #    하단 안내문은 **넣지 않는다.** 상비도 접힘에 다 보이니 설명할 게 없다.
    stock_block = ""   # (구 블록 폐지 — 위 3그룹으로 통합)
    shop_note = ""
    # ── 부재료 묶음 (2026-07-21 사용자 지시) ──────────────────────────────
    #  마늘·대파·깨처럼 몇 g씩만 들어가는 것들을 재료마다 한 줄씩 늘어놓으면 표가 지저분해진다.
    #  **화면에서만** 한 줄로 합쳐 보여준다. DB(dish_def_ingredient)에는 넣지 않는다.
    sub_html = ""
    _subs = SUB_ING.get(slug)
    if _subs:
        _tot_g, _tot_won, _names = 0, 0, []
        for _k, _g in _subs:
            _r = cur.execute("SELECT COALESCE(display_name, name) AS name, manual_price mp"
                             " FROM ingredients WHERE ingredient_key=?", (_k,)).fetchone()
            if not _r:
                continue
            _tot_g += _g
            _tot_won += round(_r["mp"] * _g / 1000)
            _names.append(re.sub(r"\(.*?\)", "", _r["name"]).strip())
        if _names:
            sub_html = (f'<div class="dsub">부재료({esc(" · ".join(_names))}) '
                        f'<b>{_tot_g}g</b> · 합계 <b>{won(_tot_won)}</b>'
                        f'<small>조금씩만 들어가서 한 줄로 묶었어요</small></div>')
    cmp_html = ''
    if ms:
        _cut = ' cut' if len(ms) > 5 else ''
        _more = (f'<button class="cmpmore" type="button">{len(ms)-5}곳 더 보기</button>'
                 if _cut else '')
        # 우측 카드 안에 넣고 맨 위 고정 (2026-07-24 대표 지시 — "꼭 있어야 하는 것")
        cmp_html = (f'<div class="sidebox cmpbox"><div class="sidet">프랜차이즈 비교</div>'
                    f'<div class="cmp{_cut}">'
                    '<div class="cmphead"><span class="cbrand">브랜드</span><span class="cprice">판매가</span></div>'
                    + comp + _more
                    + f'<div class="cmpfoot">집에서 만들면 <b>{esc(serving_label)}</b> 기준 재료비 <b>{won(total)}</b>'
                    f' · 판매가는 브랜드별 1인분/1개 기준입니다</div></div></div>')
    import json as _json
    # B안 구조(2026-07-20 확정): 원가는 상단 요약 · 브랜드 비교는 우측 · 레시피가 하단 주인공.
    #  "N곳에서 판매"는 방문자가 뜻을 모른다는 지적(2026-07-20)에 따라 문장으로 풀어 쓴다.
    _sold = (f'<div class="dcsub">이 메뉴를 파는 프랜차이즈 <b>{len(ms)}곳</b>의 판매가와 비교했어요</div>'
             if ms else '<div class="dcsub">프랜차이즈 판매 정보가 없는 요리예요</div>')
    # ── 레시피 부가 블록: 사진 3장 · 팁 · FAQ (2026-07-20 지시서 §4·§5) ──
    _ex = cur.execute("""SELECT tips_json, faq_json, seo_title, recipe_serving
        FROM dishes WHERE id=?""", (did,)).fetchone() if _HAS_RECIPE_COLS else None
    photos_html = tips_html = faq_html = ""
    _rserv_label = serving_label
    _ph = []  # 실사진 경로(있는 요리만) — JSON-LD image 필드에도 그대로 씀
    if _ex:
        if _ex["recipe_serving"]:
            _rserv_label = _ex["recipe_serving"]
        # 🔴 2026-08-02: PNG(사진 30장 53.4MB) → **WebP 2.7MB**(95% 감소).
        #    원본 PNG 는 `data/recipe_png_원본/` 에 보관했다(삭제 아님).
        _ph = [f"recipe/{slug}_{i}.webp" for i in (1, 2, 3)
               if os.path.exists(os.path.join(OUT, "recipe", f"{slug}_{i}.webp"))]
        if _ph:
            _cap = ["재료", "조리", "완성"]
            photos_html = ('<div class="rphotos">' + "".join(
                f'<figure><img src="{p}" alt="{esc(name)} {_cap[i]} 사진" loading="lazy">'
                f'<figcaption>{_cap[i]}</figcaption></figure>' for i, p in enumerate(_ph))
                + '</div>')
        _t = _json.loads(_ex["tips_json"] or "[]")
        # 튀김 요리엔 기름 팁을 자동으로 한 줄 붙인다 (2026-07-21 사용자 지시).
        #  원가는 흡수분만 잡는데(1.5L 부어도 닭이 먹는 건 144ml), 그 이유와 절약법을
        #  안 적어두면 "기름값이 왜 이것뿐이냐"로 읽힌다.
        if _is_fried(_rc["rs"] if _rc else "", recipe):
            _t = _t + [FRY_OIL_TIP]
        if _t:
            tips_html = (f'<h2 class="sect2" style="margin-top:22px">{esc(name)} 실패 없이 만드는 요령</h2>'
                         + "".join(f'<div class="tipbox"><span class="n">{i+1}</span>'
                                   f'<span class="t">{esc(t)}</span></div>'
                                   for i, t in enumerate(_t)))
    # ── Recipe JSON-LD (2026-07-23, Search Console 구조화 데이터 필드 누락 대응) ──
    #  image·author·keywords·recipeCuisine·recipeInstructions[].url을 추가로 채운다.
    #  nutrition(칼로리)은 DB에 근거 데이터가 전혀 없어 이번엔 넣지 않는다 — 원산지 미표시와
    #  같은 원칙("근거 없는 값을 지어내지 않는다"). 심각도 낮은 권고 항목이라 검색 노출엔 영향 없다.
    _dish_page_url = f"{SITE}/dish_{slug}.html"
    _ld_images = [f"{SITE}/{p}" for p in _ph] if _ph else [f"{SITE}/og/share.png"]
    _ld_keywords = ", ".join(dict.fromkeys(
        [i["nm"] for i in ing_ld] + [name, "레시피", "만들기"]))
    _ld = {"@context": "https://schema.org", "@type": "Recipe", "name": name,
           "description": f"{name} 집에서 만들면 재료비 {total:,}원({serving_label} 기준).",
           "image": _ld_images,
           "author": {"@type": "Organization", "name": "올마나마", "url": SITE},
           "keywords": _ld_keywords,
           "recipeCuisine": CUISINE_MAP.get(slug, "한식"),
           "recipeYield": serving_label,
           "recipeIngredient": [f'{i["nm"]} {i["a"]:g}{i["u"]}' for i in ing_ld],
           "estimatedCost": {"@type": "MonetaryAmount", "currency": "KRW", "value": total}}
    if _rc:
        _ld_steps = [t for t in _rc["rs"].splitlines() if t.strip()]
        _ld["recipeInstructions"] = [
            {"@type": "HowToStep", "position": i + 1, "text": t,
             "url": f"{_dish_page_url}#dstep{i+1}"}
            for i, t in enumerate(_ld_steps)]
    jsonld = '<script type="application/ld+json">' + _json.dumps(_ld, ensure_ascii=False) + '</script>'

    # 재료 대체 안내 — 레시피 영역에 모아서(2026-07-20)
    subst_html = ""
    if subst_list:
        subst_html = (f'<h2 class="sect2" style="margin-top:22px">{esc(name)} 재료가 없을 때</h2>'
                      '<div class="substbox">'
                      + "".join(f'<div class="srow"><b>{esc(n)}</b><span>{esc(t)}</span></div>'
                                for n, t in subst_list) + '</div>')

    if _ex:
        _f = _json.loads(_ex["faq_json"] or "[]")
        if _f:
            faq_html = (f'<h2 class="sect2" style="margin-top:22px">{esc(name)} 자주 묻는 질문</h2>'
                        + "".join(f'<details class="faq"><summary>{esc(q["q"])}</summary>'
                                  f'<div class="a">{esc(q["a"])}</div></details>' for q in _f))

    # 우측 고정 열 — 쿠팡 검색 위젯을 빼고 프랜차이즈 비교를 올린다(2026-07-24 대표 지시).
    #  위젯은 배너로 교체 예정. 비교표는 본문에서 자리를 너무 잡아먹어 옆으로 뺐다.
    # 🔴 사이드 배너를 뺐다(2026-07-25). ADFIT_SIDE 가 **하단과 같은 광고단위**를 쓰고 있어서
    #    한 페이지에 같은 단위가 두 번 들어갔다 — 애드핏은 중복 게재를 안 채워준다.
    #    좁은 열이라 단가도 낮아, 새 단위를 발급받기보다 빼는 쪽을 골랐다.
    aside = f'''<aside class="dside">
{cmp_html}
</aside>'''

    # 제목 — 우리 시세로 숫자를 채운다(지시서: "N은 우리 시세로 자동")
    # 🔴 2026-08-02: `<title>` 을 「레시피」로 여는 정책에 H1 도 맞췄다.
    #    실측 월간 검색량 — 레시피 93,150 vs 원가 860(108배). 옛 형태는
    #    「○○ 원가, 집에서 해먹으면 N원? (레시피)」 로 「원가」가 앞머리였다.
    # 🔴 2026-08-02 2차 보강: 숫자 앞에 **「재료비」**를 붙인다.
    #    숫자만 두면 「장 보면」 금액으로 오해받는다("7,324원이라더니 장보니 14,250원").
    #    그 오해가 곧 신뢰 문제다 — 대표 지시.
    page_title = f"{name} 레시피 — 집에서 만들면 재료비 {total:,}원?"

    # 장보기 분량 라벨 — 최소 구매로 실제 몇 인분이 나오는지 계산해 그대로 쓴다
    #  (2026-07-20 사용자 지시: "2인분이면 2인분이라고 적어". 임의로 4인분이라 하지 않는다.)
    buy_serv_label = f"{possible}{unit_word}" if possible else "1회"

    # 상단 요약 — 레시피 페이지는 **집밥 축**만 다룬다(2026-07-20 사용자 확정).
    #  "브랜드 원가율은 브랜드 페이지에서 보면 된다. 레시피에서 브랜드를 볼 이유가 없다."
    #  → 프랜차이즈 판매가·매장 재료비·매장 원가율·브랜드 비교표를 전부 뺐다.
    summary_html = ('<div class="sumgrid">'
                    f'<div><div class="sl">집에서 만들면</div>'
                    f'<div class="sv" style="color:var(--good)">{won(total)}</div>'
                    f'<div class="sn">{esc(serving_label)} 재료비</div></div>'
                    # "분량"만 쓰니 무엇을 산 금액인지 안 읽혔다 → 기준을 밝힌다(2026-07-26).
                    # 🔴 2026-08-02 2차 보강: 라벨에 **기준**을 못박는다.
                    + (f'<div><div class="sl">장 보면 <span class="slx">(최소 구매 기준)</span></div>'
                       f'<div class="sv js-shopsum">{won(shop_total)}</div>'
                       f'<div class="sn">담은 재료 · 약 {buy_serv_label} 분량</div></div>' if shop_total else '')
                    + '</div>'
                    # 🔴 두 금액의 관계를 화면에서 설명한다. 데이터 존이라 캐릭터 없이 글로만.
                    + (f'<p class="amtnote">재료비는 <b>실제 사용한 분량</b> 기준이에요. '
                       f'장보기는 <b>최소 구매 단위</b> 합계라 더 크고, '
                       f'남는 재료는 다른 요리에 쓸 수 있어요.</p>' if shop_total else ''))

    _ill = illust(slug, name, eager=True)   # 상세 첫 화면 — lazy 금지(§illust 주석 ①)
    body = f"""{jsonld}<div class="crumb"><a href="index.html">홈</a> › <a href="dishes.html">레시피</a> › {esc(name)}</div>
<h1 class="dh2">{esc(page_title)}</h1>
<div class="dpc">
<div class="dmain">

<!-- 🎨 2026-08-02: PC 2열 — 좌(일러+가격카드) · 우(재료표).
     「첫 화면에 그림·가격·재료가 같이 보여야 한다」(대표 지시). 모바일은 세로 스택. -->
<div class="dtop">
<div class="dtop-l">
{f'<div class="dillwrap">{_ill}</div>' if _ill else ''}
<div class="dcard"><div class="dcl">{esc(serving_label)} 재료비 <span class="slx">(쓴 만큼)</span></div>
<div class="dbig">{won(total)}</div>{_sold}
{summary_html}
</div>
</div>
<div class="dtop-r">
<h2 class="sect2">{esc(name)} {esc(serving_label)} 비용과 최소 장보기 비용</h2>
{ing_blocks}
{set_html}
<div class="dtotbar"><span>{esc(serving_label)}에 실제로 들어가는 재료비</span>
<b>{won(total)}</b></div>
{sub_html}
{shop_note}
</div>
{aside}
</div>

</div>
</div>

<div class="rzone">
{photos_html}
{recipe_html}
{tips_html}
{subst_html}
{faq_html}
<div class="ractions">
<button class="ract" id="saveCard">레시피 카드 저장</button>
<button class="ract" id="shareLink">링크 공유</button>
</div>
</div>
<script>
// 레시피 카드 저장 — 캔버스로 요약 카드를 그려 PNG 다운로드(외부 라이브러리 없음)
document.getElementById('saveCard').addEventListener('click',function(){{
 var W=800,H=1000,cv=document.createElement('canvas');cv.width=W;cv.height=H;
 var x=cv.getContext('2d');
 x.fillStyle='#fff';x.fillRect(0,0,W,H);
 x.fillStyle='#f4511e';x.fillRect(0,0,W,8);
 x.fillStyle='#1a1d21';x.font='700 34px Malgun Gothic,sans-serif';
 x.fillText({_json.dumps(name, ensure_ascii=False)},48,80);
 x.font='600 17px Malgun Gothic,sans-serif';x.fillStyle='#6b7280';
 x.fillText({_json.dumps(serving_label + ' 기준 · 올마나마', ensure_ascii=False)},48,112);
 x.fillStyle='#f4511e';x.font='900 52px Malgun Gothic,sans-serif';
 x.fillText({_json.dumps(won(total), ensure_ascii=False)},48,182);
 x.fillStyle='#6b7280';x.font='600 16px Malgun Gothic,sans-serif';
 x.fillText('집에서 만들면 재료비',48,210);
 var y=262;
 x.fillStyle='#1a1d21';x.font='800 20px Malgun Gothic,sans-serif';x.fillText('재료',48,y);y+=34;
 var ings={_json.dumps([f'{i["nm"]} {i["a"]:g}{i["u"]}' for i in ing_ld], ensure_ascii=False)};
 x.font='400 17px Malgun Gothic,sans-serif';x.fillStyle='#333';
 ings.forEach(function(s){{ if(y<560){{x.fillText('· '+s,56,y);y+=27;}} }});
 y+=18;x.fillStyle='#1a1d21';x.font='800 20px Malgun Gothic,sans-serif';x.fillText('만드는 법',48,y);y+=32;
 var steps={_json.dumps([s for s in (_rc["rs"].split(chr(10)) if _rc else []) if s.strip()], ensure_ascii=False)};
 x.font='400 16px Malgun Gothic,sans-serif';x.fillStyle='#333';
 steps.forEach(function(s,i){{
   var t=(i+1)+'. '+s, line='', words=t.split(' ');
   words.forEach(function(w){{
     if(x.measureText(line+w).width>690){{ if(y<950){{x.fillText(line,56,y);y+=25;}} line=w+' '; }}
     else line+=w+' ';
   }});
   if(line&&y<950){{x.fillText(line,56,y);y+=25;}}
   y+=6;
 }});
 x.fillStyle='#9aa1ac';x.font='600 14px Malgun Gothic,sans-serif';
 x.fillText('olmanama.com — 프랜차이즈 메뉴 원가 계산',48,H-28);
 var a=document.createElement('a');
 a.download={_json.dumps(slug + '_레시피.png', ensure_ascii=False)};
 a.href=cv.toDataURL('image/png');a.click();
}});
// 링크 공유 — 모바일은 네이티브 공유 시트, 데스크탑은 클립보드 복사
document.getElementById('shareLink').addEventListener('click',function(){{
 var u=location.href,t={_json.dumps(page_title, ensure_ascii=False)};
 if(navigator.share){{navigator.share({{title:t,url:u}}).catch(function(){{}});}}
 else{{navigator.clipboard.writeText(u).then(function(){{
   var b=document.getElementById('shareLink'),o=b.textContent;
   b.textContent='링크 복사됨';setTimeout(function(){{b.textContent=o;}},1500);
 }});}}
}});
</script>"""
    # 🔴 제목은 「레시피」로 연다 (2026-08-02, `reports/SEO키워드분석-2026-08-02.md`).
    #    실측 월간 검색량 — 레시피 93,150 · 만들기 36,255 vs **원가 860**. 108배 차이다.
    #    이 페이지는 「집에서 만들면 얼마」가 컨셉인데 정작 「레시피」가 제목에 한 번도 없었다.
    #    ⛔ URL·슬러그(`dish_{slug}.html`)는 바꾸지 않는다 — 색인·링크가 끊긴다.
    _t = f"{name} 레시피 — 집에서 만들면 원가 얼마?"
    _d = (f"{name} 집에서 만들기. 표준 레시피와 재료비 {won(total)}"
          f"({serving_label} 기준). 프랜차이즈 판매가와 비교하고 시판 밀키트까지 한 번에.")
    open(os.path.join(OUT, f"dish_{slug}.html"), "w", encoding="utf-8").write(clean_urls(HEAD(_t, _d, f"dish_{slug}.html")+body+FOOT))
    tiles.append((name, slug, total, len(ms), serving_label))

tile_map = {n:(s,t,c,sv) for n,s,t,c,sv in tiles}
# ICON은 위(루프 앞)에서 정의됨
# 섹션(7개) 제목마다 여백이 세로를 잡아먹어 2.1화면으로 길었다(2026-07-18).
#  → 카테고리는 상단 칩 필터로 옮기고, 타일은 아이콘 카드 격자 하나로. 검색+칩으로 좁힌다.
def _thumb(slug, name):
    """목록 카드 썸네일. 완성 사진(_1.png)이 실제로 있는 요리만 넣는다.

    ⚠️ 파일 존재를 확인하고 넣는다 — 68종 중 사진이 있는 건 9종뿐이라
       무조건 넣으면 나머지 59칸이 깨진 이미지가 된다.
    """
    if not os.path.exists(os.path.join(OUT, "recipe", f"{slug}_1.webp")):
        return ""
    return (f'<img class="tt" src="recipe/{slug}_1.webp" alt="{esc(name)} 완성 사진"'
            f' loading="lazy" decoding="async" width="400" height="300">')


sections = ""
for cat, names in DISH_CAT.items():
    cells = "".join(
        f'<a class="tile" data-n="{esc(n)}" data-c="{esc(cat)}" data-p="{tile_map[n][1]}" '
        f'data-pl="{tile_map[n][2]}" href="dish_{tile_map[n][0]}.html">'
        # 컴팩트 카드(2026-07-20 B안): 이모티콘·"N곳 판매" 제거 — 요리명 + 재료비만.
        #  "N곳 판매"는 브랜드 수라는 걸 방문자가 못 알아본다는 지적 반영.
        #  2026-07-25: 일러스트 있는 요리는 카드에 그림을 얹는다(57종).
        + illust(tile_map[n][0], n, cls="til", w=240, h=170) +
        f'<div class="tn">{esc(n)}</div>'
        f'<div class="tp">{tile_map[n][1]:,}원</div>'
        f'<div class="tb">{esc(tile_map[n][3])}</div></a>'
        for n in names if n in tile_map)
    sections += cells
sections = f'<div class="grid" id="dgrid">{sections}</div>'
# 카테고리 칩 (전체 + 각 섹션)
_chips = '<button class="dchip on" data-c="전체">전체</button>' + "".join(
    f'<button class="dchip" data-c="{esc(cat)}">{esc(cat)}</button>' for cat in DISH_CAT)
chips_html = (f'<div class="dchips">{_chips}</div>'
              # 정렬 기본 = 많이 파는 순(=대중적인 요리 위로). "판매처 많은 순"이라는 말이
              #  브랜드 수라는 걸 못 알아본다는 지적(2026-07-20)에 따라 라벨만 쉬운 말로.
              '<div class="dsort"><span>정렬</span>'
              '<button class="dsb on" data-s="places">인기순</button>'
              '<button class="dsb" data-s="price">재료비 낮은 순</button>'
              '<button class="dsb" data-s="name">가나다</button></div>')
search_js = """<div style="position:relative;margin:12px 0 4px">
<span style="position:absolute;left:13px;top:50%;transform:translateY(-50%);opacity:.6"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" style="width:16px;height:16px"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg></span>
<input id="dq" type="text" placeholder="레시피 검색 (예: 짜장, 찌개)" autocomplete="off"
 style="width:100%;padding:13px 14px 13px 40px;font-size:15px;border:1.5px solid var(--line);border-radius:12px;background:var(--card);color:var(--ink);outline:none;font-family:inherit"></div>
<script>
// ⚠️ 이 스크립트가 칩·타일 HTML보다 먼저 삽입되므로, DOM이 다 그려진 뒤 바인딩한다.
//    (search_js가 chips_html·sections보다 앞이라 즉시 실행하면 .dchip이 아직 없다 — 2026-07-18 버그)
document.addEventListener('DOMContentLoaded',function(){
 var DQ=document.getElementById('dq'),CAT='전체',DC=document.getElementById('dcount');
 // 정렬: 타일을 DOM에서 재배치한다(필터와 독립적으로 동작).
 var GRID=document.getElementById('dgrid');
 function dsort(mode){
   var ts=[].slice.call(GRID.querySelectorAll('.tile'));
   ts.sort(function(a,b){
     if(mode==='name') return a.dataset.n.localeCompare(b.dataset.n,'ko');
     if(mode==='places') return (+b.dataset.pl)-(+a.dataset.pl);
     return (+a.dataset.p)-(+b.dataset.p);
   });
   ts.forEach(function(t){GRID.appendChild(t);});
 }
 document.querySelectorAll('.dsb').forEach(function(b){
   b.addEventListener('click',function(){
     document.querySelectorAll('.dsb').forEach(function(x){x.classList.remove('on');});
     b.classList.add('on'); dsort(b.dataset.s); if(typeof dreset==='function'){dreset();dfilter();}
   });
 });
 dsort('places');   // 기본 = 인기순(2026-07-20)
 // 더보기 (2026-07-24 통합지시서 §A4) — 74종을 다 깔면 모바일 5,300px.
 //  🔴 링크는 HTML에 **전부 그대로 두고 CSS(display)로만 숨긴다.** JS로 링크를 만들면
 //     크롤러가 못 보므로 SEO가 죽는다. 여기서는 이미 있는 타일을 감출 뿐이다.
 var STEP=20, LIMIT=STEP, MORE=document.getElementById('dmore');
 function dfilter(){
  var q=DQ.value.trim(),match=0,shown=0;
  document.querySelectorAll('.tile').forEach(function(t){
    var okq=!q||t.dataset.n.indexOf(q)>=0, okc=CAT==='전체'||t.dataset.c===CAT;
    var on=okq&&okc;
    if(on){match++; if(match<=LIMIT){t.style.display='';shown++;} else {t.style.display='none';}}
    else t.style.display='none';});
  if(DC)DC.textContent='레시피 '+match+'종 · 집밥 재료비 기준';
  if(MORE){
    var rest=match-shown;
    MORE.style.display=rest>0?'':'none';
    MORE.textContent='더보기 ('+rest+'종 더)';
  }
 }
 function dreset(){LIMIT=STEP;}          // 필터·정렬이 바뀌면 카운트를 처음으로
 if(MORE)MORE.addEventListener('click',function(){LIMIT+=STEP;dfilter();});
 DQ.addEventListener('input',function(){dreset();dfilter();});
 document.querySelectorAll('.dchip').forEach(function(c){c.addEventListener('click',function(){
  document.querySelectorAll('.dchip').forEach(function(x){x.classList.remove('on')});
  c.classList.add('on');CAT=c.dataset.c;dreset();dfilter();});
 });
 dfilter();
});</script>"""
dhdr = ('<div class="crumb"><a href="index.html">홈</a> › 레시피</div>'
        '<div class="dhdr"><span class="di"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 21h10"/><path d="M6 17h12l.6-6.2A4.5 4.5 0 1 0 12 6a4.5 4.5 0 1 0-6.6 4.8z"/></svg></span><div><h1>레시피</h1><div class="dsub">집에서 만들면 재료비 얼마?</div></div></div>')
dmore = '<button class="dmore" id="dmore" type="button">더보기</button>'
dcount = f'<div class="dcount" id="dcount">레시피 {len(tiles)}종 · 집밥 재료비 (기준량은 카드마다 다름)</div>'
open(os.path.join(OUT, "dishes.html"), "w", encoding="utf-8").write(clean_urls(
    HEAD("집밥 재료비 · 프랜차이즈 메뉴 가격 비교", f"짜장면·김치찌개·탕수육 등 인기 요리 {len(tiles)}종을 집에서 만들면 재료비가 얼마인지, 같은 메뉴를 프랜차이즈에서 사면 얼마인지 가격을 나란히 비교합니다.", "dishes.html")+f'{dhdr}{search_js}{chips_html}{dcount}{sections}{dmore}'+FOOT))
print(f"dish 페이지 {len(tiles)}개 + dishes.html 생성 / 메뉴 매핑 {len(assigned)}개")
con.close()
