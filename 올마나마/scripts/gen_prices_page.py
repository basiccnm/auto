# -*- coding: utf-8 -*-
# 재료 시세 페이지: _preview/prices.html
#  구조 = 검색·선택형 (2026-07-17 사용자 확정, 목업 A안)
#   이전에는 47종을 세로로 쭉 나열 → 360px에서 4.3화면. "이 밑으로 너무 내려간다"는 지적.
#   지금은 재료를 골라 하나를 크게 본다 → 257종 전부 담고도 항상 1.2화면.
#   기본값은 '오늘 가장 많이 움직인 재료'라 아무것도 안 눌러도 볼 게 있다.
#  홈의 "📈 오늘의 재료 시세" 위젯에서 눌러 들어오는 상세 페이지.
import sqlite3, os, html, json
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from site_config import SITE, clean_urls


BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview", "prices.html")
def esc(s): return html.escape(str(s)) if s is not None else ""

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

# ── 등락 (최신 시세일 vs 직전 시세일) ──
dates = [r[0] for r in cur.execute(
    "SELECT DISTINCT price_date FROM price_history ORDER BY price_date DESC LIMIT 2").fetchall()]
DELTA = {}
if len(dates) == 2:
    for r in cur.execute("""SELECT a.ingredient_key k,a.retail_price c,b.retail_price p FROM price_history a
        JOIN price_history b ON a.ingredient_key=b.ingredient_key
        WHERE a.price_date=? AND b.price_date=? AND a.retail_price>0 AND b.retail_price>0""",
        (dates[0], dates[1])).fetchall():
        DELTA[r["k"]] = (r["c"], r["p"])
LABEL = f"{dates[1][5:].replace('-','.')} 대비" if len(dates) == 2 else ""
TODAY = dates[0] if dates else ""
# 고정단가(사람이 조사한 값)의 최종 조사일. "매일 갱신"이 아닌 종을 정직하게 구분해 표기하기 위함.
import json as _json, os as _os2
_FXP = _os2.path.join(BASE, "data", "research", "fx_usdkrw.json")
try:
    _fx = _json.load(open(_FXP, encoding="utf-8"))
    FX_NOTE = f' · 수입 통관단가는 <b>USD/KRW {_fx["rate"]:,.0f}원</b>({_fx["date"]} 기준) 환산'
except Exception:
    FX_NOTE = ""
MANUAL_CHECKED = (cur.execute("SELECT MAX(date(updated_at)) FROM ingredients WHERE type='manual'").fetchone()[0] or "")

# 재료 4분류는 ingredient_cat.py 단일 출처를 쓴다 (두 곳에 복붙하다 어긋난 적 있음, 2026-07-18)
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from ingredient_cat import cat_of
from theme import CSS_VARS, HEAD_SCRIPT, BTN, AUTH_BTN, TOGGLE_JS, SHARE_BTN, SHARE_BTM, HEAD_TAGS, FOOTER_LINKS, FOOTER_CSS, ADFIT, ADFIT_CSS, CPSEARCH, CPSEARCH_CSS, SOURCES, SOURCES_CSS, GNAV, GNAV_CSS, BODY_CSS, TYPO_CSS, gnav, P2_CSS, WRAP_CSS

# 실제로 메뉴에 쓰이는 재료만. 원가 영향 큰 순.
#  ⚠️ 바깥 루프는 .fetchall() — 안에서 top_menus()가 같은 커서를 다시 쓰면 순회가 첫 행에서 끊긴다.
rows = cur.execute("""SELECT i.ingredient_key k,
    COALESCE(i.display_name, i.name) name, i.page_slug pslug,
    i.class, i.type, i.base_unit bu,
    i.manual_price mp, i.wholesale_price wp, COALESCE(i.is_retail,0) ir, i.subcat sub, i.origin org,
    COUNT(DISTINCT mi.menu_id) uses,
    (SELECT retail_price FROM price_history WHERE ingredient_key=i.ingredient_key AND retail_price>0
     ORDER BY price_date DESC LIMIT 1) live_p
    FROM ingredients i LEFT JOIN menu_ingredients mi ON mi.ingredient_key=i.ingredient_key
    GROUP BY i.ingredient_key
    HAVING COUNT(DISTINCT mi.menu_id)>0 OR i.chamgagyeok_key IS NOT NULL
        OR i.type IN ('live','live_composite')
    ORDER BY (i.type NOT IN ('live','live_composite')), COALESCE(SUM(mi.line_cost),0) DESC""").fetchall()

# 합성 지수 재료는 "무엇의 평균인지" 반드시 밝힌다.
#  vegetables_fresh는 KAMIS 245 양파0.4 + 246 파0.3 + 212 양배추0.3 가중평균인데,
#  그 사실이 어디에도 없어 홈 첫 화면 숫자를 우리조차 설명 못 했다(2026-07-17).
#  코드표: data/research/kamis_item_codes.json
BASIS = {
    "vegetables_fresh": "양파 40% + 파 30% + 양배추 30% 가중평균",
    "salad_greens": "상추 시세 기준",
}

DATA = []
for r in rows:
    k = r["k"]
    # 🔴 합성 지수는 목록에서 뺀다(2026-07-19 사용자 지시 "합쳐진 거 없애고 각각").
    #    vegetables_fresh = 양파40%+파30%+양배추30% 가중평균 = 실제로는 살 수 없는 지수라
    #    "양파 시세" 찾아온 사람에게 보여줄 값이 아니다. 개별 품목은 kv_* 로 따로 올라간다.
    #    단, 원가 계산에는 계속 쓰이므로 DB에서 삭제하지는 않는다.
    if r["type"] == "live_composite":
        continue
    is_live = r["type"] in ("live", "live_composite")
    price = r["live_p"] if (is_live and r["live_p"]) else r["mp"]
    if not price: continue
    d = None
    if k in DELTA:
        c, p = DELTA[k]
        d = round((c - p) / p * 100, 1) if p else 0
    tops = cur.execute("""SELECT m.id, m.name, b.name bn FROM menu_ingredients mi JOIN menus m ON mi.menu_id=m.id
        JOIN brands b ON m.brand_id=b.id WHERE mi.ingredient_key=? AND b.published=1 ORDER BY mi.line_cost DESC LIMIT 3""",
        (k,)).fetchall()
    DATA.append({"k": k, "n": r["name"], "slug": r["pslug"], "u": r["bu"], "p": price, "w": r["wp"],
                 "c": r["uses"], "d": d, "live": 1 if is_live else 0, "ir": r["ir"],
                 "b": BASIS.get(k), "org_db": r["org"],
                 "g": cat_of(k, r["name"], r["class"], r["ir"]), "sub": r["sub"] or "",
                 "m": [[t["id"], f'{t["bn"]} {t["name"]}'] for t in tops]})

# 🔴 상위 분류는 subcat(공공API 대분류)을 우선한다 (2026-07-20).
#    이름 기반 cat_of()는 '미역 도매(경락)'·'한우 양지(경락)'을 농산으로 넣어버려
#    농산 칩 안에 수산 18종·축산 3종이 섞여 나왔다.
# subcat = "축산물/소" 형식(reclassify_ingredients.py가 전수 부여). 대분류는 여기서 갈라 쓴다.
_TOP4 = {"축산물": "축산", "농산물": "농산", "수산물": "수산", "가공식품": "가공"}
for x in DATA:
    sc = x.get("sub") or ""
    if "/" in sc:
        top, sub = sc.split("/", 1)
        if top in _TOP4:
            x["g"] = _TOP4[top]
            x["sub"] = sub

# 리스트 행·바텀시트용 필드 + 분류별 카운트 (Design 재료시세 2026-07-18)
_EMOJI = {"축산": "🥩", "농산": "🥬", "수산": "🐟", "가공": "🧂"}
cnt_all = cnt_c = cnt_n = cnt_s = cnt_g = cnt_r = cnt_d = cnt_live = 0
for x in DATA:
    x["e"] = "🛒" if x["ir"] else _EMOJI.get(x["g"], "📦")
    x["cl"] = x["g"] + " · " + ("시판" if x["ir"] else x["u"]) + ("" if x["d"] is None else " · 변동시세")
    if x["d"] is None: x["chf"], x["chc"] = "고정", "var(--muted)"
    elif abs(x["d"]) < 0.05: x["chf"], x["chc"] = "—", "var(--muted)"
    else: x["chf"], x["chc"] = (("▲" if x["d"] > 0 else "▼") + f"{abs(x['d']):.1f}%"), ("var(--up)" if x["d"] > 0 else "var(--dn)")
    # 하위 분류(2026-07-19 사용자 지시): 축산 → 소/돼지/닭, 그 아래 국산/수입산.
    #  이름 키워드로만 판정한다. 애매하면 '기타'·'미표기'로 두고 억지로 분류하지 않는다.
    nm = x["n"]
    # 농산·수산은 수집 단계에서 저장한 subcat(공공API 대분류 기반)을 그대로 쓴다.
    #  축산만 이름 기반으로 소/돼지/닭을 나눈다(축평원·KAMIS가 축종을 따로 안 주는 품목이 있어서).
    if x["g"] != "축산" and x["sub"]:
        x["g2"] = x["sub"]
    elif any(w in nm for w in ("한우", "소고기", "우삼겹", "차돌", "양지", "사태", "우둔", "설도",
                               "채끝", "안심", "사골", "우족", "갈비", "다짐육", "불고기감")):
        x["g2"] = "소"
    elif any(w in nm for w in ("돼지", "삼겹", "목살", "등심", "앞다리", "족발", "지육", "돈까스용",
                               "베이컨", "햄", "소시지", "순대", "대창", "곱창", "막창")):
        x["g2"] = "돼지"
    elif any(w in nm for w in ("닭", "치킨", "계란", "달걀", "염지")):
        x["g2"] = "닭"
    else:
        x["g2"] = "기타"
    # 축종(소/돼지/닭)으로 판정됐으면 상위 분류도 축산이어야 한다 — 안 그러면 '농산 > 닭'
    #  같은 모순이 생긴다(2026-07-20 사용자 지적).
    if x["g2"] in ("소", "돼지", "닭"):
        x["g"] = "축산"
    # 원산지: DB origin 컬럼 우선(A단계 2026-07-20, cleanup_master가 이름 단서로 부여).
    #  없으면 기존 이름 키워드 폴백(태국·베트남 등 추가 — 태국산 닭발이 미표기로 새던 버그).
    if x.get("org_db"):
        x["og"] = x["org_db"]
    elif any(w in nm for w in ("수입", "미국", "호주", "캐나다", "브라질", "스페인", "칠레",
                               "태국", "베트남", "중국", "노르웨이", "러시아", "페루", "냉동 벌크")):
        x["og"] = "수입산"
    # '경락·지육·도체'는 국산 단서에서 제외(2026-07-20): aT 경락엔 수입 과일도 상장된다
    #  (바나나 도매(경락)→국산 오표기). 축평원 국산분은 DB origin(ek_→국산)이 이미 커버.
    elif any(w in nm for w in ("한우", "국내산", "국산")):
        x["og"] = "국산"
    else:
        x["og"] = "미표기"
    x["pf"] = f'{x["p"]:,}원' if x["ir"] else f'{x["p"]:,}원/{x["u"]}'
    x["wf"] = f'{x["w"]:,}원' if x["w"] else "—"
    cnt_all += 1
    if x["g"] == "축산": cnt_c += 1
    elif x["g"] == "농산": cnt_n += 1
    elif x["g"] == "수산": cnt_s += 1
    elif x["g"] == "가공": cnt_g += 1
    if x["ir"]: cnt_r += 1
    if x["d"] is not None: cnt_d += 1
    if x["live"]: cnt_live += 1

# 🔴 화면에 심는 데이터에서 **가격을 뺀다** (2026-07-24).
#  여기 심던 D 배열에 재료 348종의 도매가(w)·소매가(p)가 통째로 들어 있었다(11만자).
#  목록에서 가격을 지워도 이게 남아 있으면 소용이 없다 — 오히려 JSON이라 더 긁기 쉽다.
#  검색·필터에 필요한 것(이름·분류·단위·사용 메뉴 수·등락 방향)만 남기고,
#  실제 값은 재료별 페이지(price_*)에서 본다. 목록에서 고르면 그 페이지로 이동한다.
import re as _re2
_BADCH2 = _re2.compile(r'[^0-9A-Za-z가-힣]+')
_SAFE = [{
    "n": x["n"],
    "u": x["u"],
    "c": x["c"],
    "g": x["g"],
    "g2": x["g2"],
    "og": x["og"],
    "ir": x["ir"],
    # 🔴 live 는 반드시 남긴다 (2026-07-25 버그수정).
    #  위에서 가격을 뺄 때 이 필드까지 같이 빠져서, '자동갱신' 칩이 84종이라고
    #  써놓고 누르면 0건이 나왔다(inG의 x.live===1 이 항상 거짓). 값이 아니라
    #  분류 플래그라 심어도 가격 유출이 아니다.
    "live": x["live"],
    "e": x["e"],
    "chf": x["chf"],          # ▲2.1% 같은 등락 라벨 — 방향은 콘텐츠라 남긴다
    "chc": x["chc"],
    "slug": "price_" + _BADCH2.sub("", x["n"]),
} for x in DATA]
J = json.dumps(_SAFE, ensure_ascii=False)

# ── 전체 목록(정적 HTML). 기본은 접혀 있어 화면 길이에 영향 없음.
#  화면은 JS가 그리지만, 링크까지 JS가 만들면 (1) 검색엔진이 못 타고 (2) 링크 검사기가
#  깨진 링크를 못 잡는다. pSEO 사이트라 크롤 가능한 <a href>가 반드시 정적으로 있어야 한다.
# 전체 목록 — **가격을 찍지 않는다.** (2026-07-24)
#  한 장에 가격 1,042개가 그대로 있어서, 봇이 이 페이지 하나만 받아도 우리 DB가 통째로
#  복제됐다. Cloudflare 속도 제한을 걸어도 '한 장'은 통과하므로 소용이 없었다.
#  → 여기서는 이름·사용 메뉴 수만 두고, 값은 재료별 페이지(price_*)에서 본다.
#     링크는 그대로 남아 크롤러가 543장을 다 찾아간다(SEO는 오히려 좋아짐).
import re as _re
_KEEPCH = _re.compile(r'[^0-9A-Za-z가-힣]+')
def _pslug(n):
    return _KEEPCH.sub("", n)

# 🔴 주소는 **DB의 `page_slug`** 를 쓴다 (2026-07-27). 여기서 이름으로 다시 만들면
#    `gen_ingredient_pages` 가 만든 파일명과 어긋나 링크가 빈 곳을 가리킨다.
#    `page_slug` 는 `display_name_build.py` 한 곳에서 정한다.
all_rows = ""
for x in DATA:
    tag = '<span class="tag">시판</span>' if x["ir"] else ''
    _sl = x.get("slug") or ("price_" + _pslug(x["n"]))
    all_rows += (f'<li><a href="{esc(_sl)}.html"><b>{esc(x["n"])}</b></a>{tag} '
                 f'<span class="sub">{x["c"]}개 메뉴</span></li>')

# 최근 변동 재료 — 오늘 변동이 0일 때 대신 보여줄 것(없는 변동을 지어내지 않는다)
recent = cur.execute("""SELECT i.name, a.price_date d,
    ROUND((a.retail_price - b.retail_price) * 100.0 / b.retail_price, 1) pct
    FROM price_history a JOIN price_history b
      ON a.ingredient_key = b.ingredient_key AND b.price_date < a.price_date
    JOIN ingredients i ON i.ingredient_key = a.ingredient_key
    WHERE a.retail_price > 0 AND b.retail_price > 0
      AND ABS((a.retail_price - b.retail_price) * 100.0 / b.retail_price) >= 0.5
    GROUP BY a.ingredient_key HAVING a.price_date = MAX(a.price_date)
    ORDER BY a.price_date DESC, ABS(pct) DESC LIMIT 3""").fetchall()

up = sum(1 for x in DATA if x["d"] and x["d"] > 0.05)
dn = sum(1 for x in DATA if x["d"] and x["d"] < -0.05)
flat = sum(1 for x in DATA if x["d"] is not None and abs(x["d"]) <= 0.05)

if up or dn:
    summary_html = (f'<div class="sm u"><b>{up}</b><span>▲ 오름</span></div>'
                    f'<div class="sm d"><b>{dn}</b><span>▼ 내림</span></div>'
                    f'<div class="sm"><b>{flat}</b><span>— 보합</span></div>')
elif recent:
    _r = "".join(f'<span class="rc">{esc(r["name"])} '
                 f'<b style="color:{"var(--up)" if r["pct"]>0 else "var(--dn)"}">'
                 f'{"+" if r["pct"]>0 else ""}{r["pct"]}%</b></span>' for r in recent)
    summary_html = (f'<div class="smflat">오늘은 큰 변동이 없습니다 · <b>최근 변동</b> {_r}</div>')
else:
    summary_html = '<div class="smflat">오늘은 큰 변동이 없습니다</div>'


page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>식자재 도매 시세 · 업소용 식자재 가격표 · 올마나마</title>
<meta name="description" content="프랜차이즈 메뉴 원가 계산에 실제 쓰는 재료 단가 {len(DATA)}종. 공공데이터 및 도매시장 업소용 실판매가 조사 기반 시세와 등락.">
<meta property="og:title" content="식자재 가격표 · 업소용 도매가 · 올마나마">
<meta property="og:description" content="원가 계산에 실제 쓰는 재료 단가 {len(DATA)}종. 공공데이터 기반 시세와 등락.">
<meta property="og:type" content="website">
<meta property="og:image" content="{SITE}/og/share.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE}/og/share.png">
<link rel="canonical" href="{SITE}/prices.html">
{HEAD_TAGS}{HEAD_SCRIPT}<style>
{CSS_VARS}
{FOOTER_CSS}{ADFIT_CSS}{CPSEARCH_CSS}{SOURCES_CSS}{GNAV_CSS}
*{{box-sizing:border-box;margin:0;padding:0}}
{BODY_CSS}
{TYPO_CSS}
{WRAP_CSS}
{P2_CSS}
header.top{{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}}
.logo{{font-weight:800;font-size:18px;color:var(--ink);text-decoration:none}}
.logo small{{color:var(--muted);font-weight:500;font-size:12px;margin-left:8px;padding-left:8px;border-left:1px solid var(--line)}}
.crumb{{font-size:12px;color:var(--muted);padding:12px 0 0}}
.crumb a{{color:var(--muted);text-decoration:none}}
h1{{margin:8px 0 3px}}
.sub{{font-size:12.5px;color:var(--muted)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;margin:12px 0}}
/* 갱신 시각·고정단가 구분 표기 (2026-07-19) — "매일 바뀐다"고 뭉뚱그리면 사실과 다르다 */
.freshbox{{margin:10px 0 2px;padding:9px 11px;background:var(--infobg);border:1px solid var(--infoline);
border-radius:11px;font-size:13px;color:var(--infotext);line-height:1.6}}
.freshbox span{{display:block;color:var(--muted)}}
/* 오늘 요약 */
.smry{{display:flex;gap:8px;margin:12px 0}}
.sm{{flex:1;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:9px 6px;text-align:center}}
.sm b{{display:block;font-size:19px;font-variant-numeric:tabular-nums}}
.sm span{{font-size:12.5px;color:var(--muted)}}
.sm.u b{{color:var(--up)}} .sm.d b{{color:var(--dn)}}
.smflat{{flex:1;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:11px 13px;
font-size:12.5px;color:var(--muted);line-height:1.7}}
.smflat .rc{{display:inline-block;margin-left:8px;font-weight:700;color:var(--ink)}}
/* 검색 */
.sbox{{position:relative;margin:10px 0}}
.sinp{{width:100%;border:2px solid var(--ink);border-radius:12px;padding:12px 14px;font-size:15px;
font-family:inherit;background:var(--card);color:var(--ink)}}
.sinp::placeholder{{color:var(--muted)}}
.sinp:focus{{outline:none;border-color:var(--accent)}}
.slist{{position:absolute;top:calc(100% + 4px);left:0;right:0;background:var(--card);border:1px solid var(--line);
border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.12);max-height:260px;overflow-y:auto;z-index:20;display:none}}
.slist.on{{display:block}}
.sitem{{padding:10px 13px;font-size:13.5px;cursor:pointer;border-bottom:1px solid var(--line);
display:flex;justify-content:space-between;gap:8px;align-items:center;background:none;border-left:0;
border-right:0;border-top:0;width:100%;text-align:left;font-family:inherit}}
.sitem:last-child{{border-bottom:0}}
.sitem:hover,.sitem.hi{{background:var(--hover)}}
.sitem .sn{{font-weight:700}} .sitem .sp{{font-size:12px;color:var(--muted);white-space:nowrap}}
/* 칩 */
/* 가로 스크롤 대신 줄바꿈 — 옆으로 밀려 안 보이던 칩(수산가공 등)이 잘렸다(2026-07-24 대표 지시) */
.chips{{display:flex;flex-wrap:wrap;gap:6px;padding-bottom:4px}}
.chip{{flex:0 0 auto;border:1px solid var(--line);background:var(--card);border-radius:999px;
padding:7px 12px;font-size:12.5px;font-weight:700;color:var(--muted);cursor:pointer;white-space:nowrap;font-family:inherit}}
.chip.on{{background:var(--grad);color:#fff;border-color:transparent}}
.chips.sub{{margin-top:5px}} .chips.sub:empty{{display:none;margin:0}}
.chips.sub .chip{{padding:5px 10px;font-size:13px}}
.chips.sub .chip.on{{background:var(--accentsoft);color:var(--accent);border-color:var(--accent)}}
/* 상세 */
.big{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin:12px 0}}
.peers{{margin:12px 0 0}}
.peers .pt{{font-size:13px;color:var(--muted);font-weight:700;margin-bottom:6px}}
.pchip{{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:6px 11px;font-size:12.5px;font-weight:600;color:var(--ink);cursor:pointer;font-family:inherit;margin:0 5px 5px 0}}
.pchip.on{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.bnm{{font-size:clamp(17px,15px+1vw,21px);font-weight:800;display:flex;align-items:center;flex-wrap:wrap;gap:4px}}
.bpr{{display:flex;align-items:baseline;gap:6px;margin:8px 0 2px}}
.bpr b{{font-size:clamp(28px,24px+2vw,36px);font-weight:800;font-variant-numeric:tabular-nums;line-height:1.15}}
.bpr .un{{font-size:13px;color:var(--muted)}}
.bdl{{font-size:13px;margin-bottom:10px}}
/* 합성 지수 재료는 무엇의 평균인지 화면에 밝힌다 */
.basis{{font-size:13px;color:var(--warntext);background:var(--warnbg);border:1px solid var(--warnline);
border-radius:8px;padding:6px 9px;margin-top:6px;line-height:1.45}}
.kv{{display:flex;gap:8px;margin-top:12px}}
.kvi{{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 10px}}
.kvi .k{{font-size:12.5px;color:var(--muted)}}
.kvi .v{{font-size:15px;font-weight:800;font-variant-numeric:tabular-nums}}
.kvi .v small{{font-size:12.5px;font-weight:500}}
.mlist{{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}}
.mlist .t{{font-size:13px;color:var(--muted);margin-bottom:5px}}
.mlist a{{display:block;font-size:13.5px;color:var(--infotext);text-decoration:none;padding:6px 0;font-weight:600}}
/* 오늘 움직인 재료 */
.movers{{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px;-webkit-overflow-scrolling:touch}}
.mv{{flex:0 0 auto;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 11px;
cursor:pointer;text-align:left;font-family:inherit}}
.mv.on{{border-color:var(--accent);background:var(--hover)}}
.mv .n{{font-size:12px;font-weight:700}} .mv .p{{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}}
.dl{{font-weight:700}} .dl.up{{color:var(--up)}} .dl.dn{{color:var(--dn)}} .dl.flat{{color:var(--muted);font-weight:500}}
.tag{{font-size:12px;background:var(--softbg);color:var(--accent);border:1px solid var(--softline);border-radius:5px;
padding:1px 5px;margin-left:5px;font-weight:700}}
.note{{font-size:13px;color:var(--muted);background:var(--panel);border:1px solid var(--line);
border-radius:10px;padding:11px 13px;margin-top:14px;line-height:1.6}}
/* 전체 목록 — 접힘이 기본(화면 길이 유지), 열면 크롤 가능한 정적 링크가 그대로 보인다 */
.allbox{{padding:0}}
.allbox summary{{padding:13px 14px;font-size:13px;font-weight:800;cursor:pointer;list-style:none}}
.allbox summary::-webkit-details-marker{{display:none}}
.allbox summary::after{{content:'▾';float:right;color:var(--muted)}}
.allbox[open] summary::after{{content:'▴'}}
.alllist{{list-style:none;padding:0 14px 12px;margin:0;max-height:340px;overflow-y:auto}}
.alllist li{{font-size:12.5px;padding:7px 0;border-top:1px solid var(--line);line-height:1.5}}
.alllist a{{color:var(--infotext);text-decoration:none}}
/* 재료시세 리스트 재설계 (Design 2026-07-18) */
.sm.u{{background:var(--badbg)}} .sm.d{{background:var(--infobg)}}
.chip .pchipcount{{opacity:.7;font-weight:800;margin-left:1px}}
.pcount{{font-size:12px;color:var(--muted);margin:12px 2px 8px}}
.plist{{background:var(--card);border:1px solid var(--line);border-radius:15px;overflow:hidden}}
/* 한 재료 = 한 줄 (§A5). 이름 | 가격 | 등락 3칸 그리드 */
.prow{{display:grid;grid-template-columns:minmax(0,1fr) auto 62px;align-items:baseline;gap:10px;
width:100%;padding:11px 14px;border:0;border-top:1px solid var(--line);background:none;
cursor:pointer;font-family:inherit;text-align:left;color:inherit}}
.prow:first-child{{border-top:0}}
.prow:hover{{background:var(--hover)}}
.prow .pn{{font-size:13.5px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.prow .pp{{font-size:13.5px;font-weight:800;font-variant-numeric:tabular-nums;white-space:nowrap;text-align:right}}
.prow .pch{{font-size:12.5px;font-weight:800;text-align:right;white-space:nowrap}}
@media(min-width:840px){{
  /* PC 2열 — 세로로 길게 흐르지 않게 (마라탕 단가표와 같은 방식) */
  .plist{{display:grid;grid-template-columns:1fr 1fr;column-gap:0}}
  .prow:nth-child(2){{border-top:0}}
  .plist>.prow:nth-child(odd){{border-right:1px solid var(--line)}}
}}
.ppager{{display:flex;justify-content:center;align-items:center;gap:5px;flex-wrap:wrap;margin:16px 0 4px}}
.pgb{{min-width:34px;height:34px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:9px;font-size:13px;font-weight:800;cursor:pointer;font-family:inherit;padding:0 8px}}
.pgb.on{{background:var(--grad);color:#fff;border-color:transparent}}
.pgb:disabled{{opacity:.4;cursor:default}}
.pgd{{color:var(--muted);padding:0 2px}}
.psheetbg{{position:fixed;inset:0;z-index:50;background:rgba(10,12,15,.5);display:none;align-items:flex-end}}
.psheetbg.on{{display:flex}}
.psheet{{width:100%;max-width:520px;margin:0 auto;background:var(--card);border-radius:22px 22px 0 0;padding:8px 20px 24px;animation:psheetUp .3s cubic-bezier(.22,1,.36,1);max-height:88vh;overflow-y:auto}}
@keyframes psheetUp{{from{{transform:translateY(100%)}}to{{transform:none}}}}
.psheet .grip{{width:40px;height:4px;border-radius:2px;background:var(--line);margin:8px auto 16px}}
.psheet .ph{{display:flex;align-items:center;gap:8px;margin-bottom:4px}}
.psheet .ph .pe{{font-size:22px}}
.psheet .ph .cat{{font-size:12.5px;font-weight:800;color:var(--muted);background:var(--track);border-radius:20px;padding:3px 9px}}
.psheet .pnm{{font-size:20px;font-weight:900;margin:2px 0 14px}}
.psheet .pbig{{display:flex;align-items:flex-end;gap:10px;margin-bottom:14px}}
.psheet .pbig .pv{{font-size:30px;font-weight:900;color:var(--ink);line-height:1;font-variant-numeric:tabular-nums}}
.psheet .pbig .pch{{font-size:14px;font-weight:800;padding-bottom:3px}}
.psheet .pkv{{display:flex;gap:10px;margin-bottom:14px}}
.psheet .pkv>div{{flex:1;border-radius:11px;padding:11px 12px}}
.psheet .pkv .a{{background:var(--track)}} .psheet .pkv .a .k{{font-size:12.5px;color:var(--muted)}} .psheet .pkv .a .v{{font-size:15px;font-weight:900}}
.psheet .pkv .b{{background:var(--accentsoft)}} .psheet .pkv .b .k{{font-size:12.5px;color:var(--accent)}} .psheet .pkv .b .v{{font-size:15px;font-weight:900;color:var(--accent)}}
.psheet .pused{{font-size:12px;font-weight:800;color:var(--muted);margin-bottom:8px}}
.psheet .ptop{{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;background:var(--track);border-radius:10px;margin-bottom:6px;text-decoration:none;color:inherit}}
.psheet .ptop .ptn{{font-size:13px;font-weight:700}}
.psheet .sgo{{display:block;width:100%;margin-top:8px;padding:15px;border:0;border-radius:13px;background:var(--grad);color:#fff;font-size:15px;font-weight:900;cursor:pointer;font-family:inherit;text-align:center}}
/* 폭(.wrap/.top .in)은 theme.py WRAP_CSS 단일 출처가 정한다 — 여기서 다시 쓰지 말 것 */
@media(min-width:840px){{.psheet{{max-width:460px;border-radius:18px;margin-bottom:8vh}}.psheetbg{{align-items:center}}}}
</style></head><body>
<header class="top"><div class="in"><a class="logo" href="index.html"><span class="lbadge">올</span>올마나마<small>브랜드 메뉴판 한 곳에서</small></a>{SHARE_BTN}{BTN}{AUTH_BTN}{gnav("prices")}</div></header>
<div class="wrap">
<div class="crumb"><a href="index.html">홈</a> › 재료 가격</div>
<h1>재료 가격표</h1>
<p class="sub">{esc(TODAY)} 기준 · 원가 계산에 실제 쓰는 단가 <b>{len(DATA)}종</b></p>
<div class="freshbox">업소용 실판매가를 매일 수집해 반영합니다 · 최신 반영 <b>{esc(TODAY)}</b>
<span>· 공공데이터 및 도매시장 <b>{cnt_live}종</b>(업소용판매가 가공 및 실판매가 조사) · 조사 단가 <b>{cnt_all - cnt_live}종</b>(최종조사 {esc(MANUAL_CHECKED)}) · 값이 움직인 재료 <b>{cnt_d}종</b>{FX_NOTE}</span></div>

<div class="smry">
{summary_html}
</div>

<div class="sbox">
  <input class="sinp" id="q" type="text" placeholder="재료명 검색 (예: 닭, 양파, 삼겹살)"
         autocomplete="off" aria-label="재료 검색">
</div>

<div class="chips" id="chips">
  <button class="chip on" data-g="축산">축산물 <span class="pchipcount">{cnt_c}</span></button>
  <button class="chip" data-g="농산">농산물 <span class="pchipcount">{cnt_n}</span></button>
  <button class="chip" data-g="수산">수산물 <span class="pchipcount">{cnt_s}</span></button>
  <button class="chip" data-g="가공">가공식품 <span class="pchipcount">{cnt_g}</span></button>
  <button class="chip" data-g="시판">시판 <span class="pchipcount">{cnt_r}</span></button>
  <button class="chip" data-g="시세">자동갱신 <span class="pchipcount">{cnt_live}</span></button>
</div>
<div class="chips sub" id="subchips"></div>
<div class="chips sub" id="subchips2"></div>

<div class="pcount" id="pcount"></div>
<div class="plist" id="plist"></div>
<div class="ppager" id="ppager"></div>

<details class="card allbox" style="margin-top:14px">
  <summary>전체 재료 {len(DATA)}종 링크 목록 (검색엔진용)</summary>
  <ul class="alllist">{all_rows}</ul>
</details>

{ADFIT}
{SHARE_BTM}
<div class="note"><b>⚠️ 표시 가격은 조사 시점의 최저가 기준입니다.</b> 구매 지역·용량(대용량/소포장)·시기·거래처에 따라 실제 구매가는 달라질 수 있으며, <b>참고용</b>으로만 활용하세요. 특정 상품·판매처의 실제 판매가와 다를 수 있습니다.<br><br>※ <b>변동 시세</b>는 공공데이터 및 도매시장의 업소용 판매가·실판매가를 조사해 매일 반영합니다. <b>고정 단가</b>는 온라인 식자재몰 판매가를 조사한 값으로, 프랜차이즈가 통상 쓰는 등급(대부분 수입산·냉동)을 기준으로 했습니다. 실제 매장이 본사에서 받는 공급가와는 다를 수 있습니다. <b>매장 도매가</b>는 조사값 기준 추정치입니다.</div>
{SOURCES}
{FOOTER_LINKS}
</div>
<div class="psheetbg" id="psheet" onclick="pClose()"><div class="psheet" id="psheetC" onclick="event.stopPropagation()"></div></div>
<script>
const D = {J};
let g = '축산';   // '전체' 칩 제거(2026-07-19 사용자 지시) → 항상 분류별로 본다
let g2 = '', og = '';   // 2단계(소/돼지/닭) · 3단계(국산/수입산)
const $ = i => document.getElementById(i);
function inG(x){{
  if (g==='시세') return x.live===1;
  if (g==='시판') return x.ir===1;
  if (x.g!==g) return false;
  if (g2 && x.g2!==g2) return false;
  if (og && x.og!==og) return false;
  return true;
}}
// 하위 칩은 **지금 보이는 목록에 실제로 있는 값만** 만든다(빈 칩을 눌러 0건 나오는 일 방지).
function subChips(){{
  const base = D.filter(x => (g==='시세'? x.live===1 : g==='시판'? x.ir===1 : x.g===g));
  const c1 = {{}}; base.forEach(x => c1[x.g2]=(c1[x.g2]||0)+1);
  // ⚠️ 실제 DB의 g2 값과 글자가 정확히 같아야 정렬에 걸린다.
  //  전엔 '닭·계란'·'곡식'·'패류'·'육가공' 처럼 없는 이름이 들어 있어서
  //  대부분이 매칭 실패 → 칩이 삽입 순서대로 뒤죽박죽 나왔다(2026-07-25 수정).
  const ORDER_ALL = ['소','돼지','닭','채소','과일','곡물','버섯·견과',
                     '어류','연체류','조개류','갑각류','해조류','수산가공',
                     '면·떡','햄·소시지','유제품','두부·묵','빵·디저트','빙과',
                     '소스·드레싱','양념·소스','양념·다대기','장·조미료','설탕·시럽',
                     '기름','분말·가루','가루·전분','절임·김치','냉동·간편식',
                     '커피·음료','기타','기타/소모품'];
  const order = ORDER_ALL.filter(k => c1[k]).concat(Object.keys(c1).filter(k => k && ORDER_ALL.indexOf(k)<0));
  $('subchips').innerHTML = (order.length>1)
    ? '<button class="chip sc'+(g2===''?' on':'')+'" data-s="">전체 <span class="pchipcount">'+base.length+'</span></button>'
      + order.map(k=>'<button class="chip sc'+(g2===k?' on':'')+'" data-s="'+k+'">'+k+' <span class="pchipcount">'+c1[k]+'</span></button>').join('')
    : '';
  const lv2 = base.filter(x => !g2 || x.g2===g2);
  const c2 = {{}}; lv2.forEach(x => c2[x.og]=(c2[x.og]||0)+1);
  const ord2 = ['국산','수입산','미표기'].filter(k => c2[k]);
  $('subchips2').innerHTML = (g==='축산' && g2 && ord2.length>1)   // 원산지 구분은 축산에서만 의미
    ? '<button class="chip sc2'+(og===''?' on':'')+'" data-o="">전체</button>'
      + ord2.map(k=>'<button class="chip sc2'+(og===k?' on':'')+'" data-o="'+k+'">'+k+' <span class="pchipcount">'+c2[k]+'</span></button>').join('')
    : '';
}}
function pView(){{ const q=$('q').value.trim(); return D.filter(x => inG(x) && (q===''||x.n.includes(q))); }}
// 2026-07-24 §A5: 행이 2줄→1줄로 얇아지고 PC는 2열이라 10개는 너무 적다 → 30개.
//  ⚠️ 페이지네이션 유지/삭제는 대표님이 화면 보고 결정하기로 함(지시서 §A5).
const PAGE_SIZE=30; let pPage=1;
// 2026-07-24 통합지시서 §A5 — 마라탕 단가표식 촘촘한 한 줄 표(이름|가격|등락).
//  분류 라벨(x.cl)은 행에서 빼고 상세 시트로 넘겼다. 한 줄에 다 넣으면 좁은 폰에서 줄바꿈이 난다.
// 행을 눌러 바텀시트에서 값을 보여주던 구조를 **링크로** 바꿨다(2026-07-24).
//  시트에 값을 뿌리려면 가격을 페이지에 심어야 하는데, 그게 통째로 긁혀 나갔다.
//  이제 값은 재료별 페이지에서만 본다.
function pRow(x){{ return '<a class="prow" href="'+x.slug+'.html">'+
  '<span class="pn">'+x.n+'</span>'+
  '<span class="pp">'+x.c+'개 메뉴</span>'+
  '<span class="pch" style="color:'+x.chc+'">'+x.chf+'</span></a>'; }}
function pRender(){{
  const list=pView(), total=list.length, pages=Math.max(1,Math.ceil(total/PAGE_SIZE));
  if(pPage>pages) pPage=1;
  const start=(pPage-1)*PAGE_SIZE, slice=list.slice(start,start+PAGE_SIZE);
  $('pcount').textContent = total + '종 · ' + pPage + ' / ' + pages + ' 페이지';
  $('plist').innerHTML = slice.map(pRow).join('') || '<div style="padding:18px;text-align:center;color:var(--muted);font-size:13px">찾는 재료가 없어요</div>';
  pPager(pages);
}}
function pPager(pages){{
  if(pages<=1){{ $('ppager').innerHTML=''; return; }}
  let h='<button class="pgb" data-pg="'+(pPage-1)+'"'+(pPage<=1?' disabled':'')+'>‹</button>', last=0;
  for(let i=1;i<=pages;i++){{ if(i===1||i===pages||Math.abs(i-pPage)<=1){{ if(i-last>1)h+='<span class="pgd">…</span>'; h+='<button class="pgb'+(i===pPage?' on':'')+'" data-pg="'+i+'">'+i+'</button>'; last=i; }} }}
  h+='<button class="pgb" data-pg="'+(pPage+1)+'"'+(pPage>=pages?' disabled':'')+'>›</button>';
  $('ppager').innerHTML=h;
}}
function pSheet(k){{ /* 시트 제거 — 재료별 페이지로 이동한다 */ }}
function pClose(){{ $('psheet').classList.remove('on'); }}
$('q').addEventListener('input', () => {{ pPage=1; pRender(); }});
$('chips').addEventListener('click', e => {{ const c=e.target.closest('.chip'); if(!c) return;
  document.querySelectorAll('#chips .chip').forEach(x=>x.classList.remove('on')); c.classList.add('on');
  g=c.dataset.g; g2=''; og=''; pPage=1; subChips(); pRender(); }});
$('subchips').addEventListener('click', e => {{ const c=e.target.closest('.chip'); if(!c) return;
  g2=c.dataset.s; og=''; pPage=1; subChips(); pRender(); }});
$('subchips2').addEventListener('click', e => {{ const c=e.target.closest('.chip'); if(!c) return;
  og=c.dataset.o; pPage=1; subChips(); pRender(); }});
$('ppager').addEventListener('click', e => {{ const b=e.target.closest('.pgb'); if(!b||b.disabled) return;
  pPage=+b.dataset.pg; pRender(); document.getElementById('pcount').scrollIntoView({{behavior:'smooth',block:'start'}}); }});
$('plist').addEventListener('click', e => {{ const b=e.target.closest('.prow'); if(b&&b.dataset.k) pSheet(b.dataset.k); }});
$('psheetC').addEventListener('click', e => {{ const b=e.target.closest('.sgo');
  if(b&&b.dataset.copy&&navigator.clipboard){{navigator.clipboard.writeText(b.dataset.copy).then(()=>{{b.textContent='복사됨 — 쿠팡에 붙여넣기';}});}} }});
subChips(); pRender();
</script>
{TOGGLE_JS}</body></html>"""

open(OUT, "w", encoding="utf-8").write(clean_urls(page))
print(f"생성: _preview/prices.html — 검색·선택형 · 재료 {len(DATA)}종 (오름 {up}/내림 {dn}/보합 {flat})")
con.close()
