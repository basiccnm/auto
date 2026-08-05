# eolmanama.db → 실제 미리보기 HTML 생성 (메뉴 상세 + 카테고리 + 브랜드 페이지)
# 모바일 우선(360px), clamp 폰트. 나중에 Worker templates.js로 포팅.
import sqlite3, os, html, json

BASE = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마"

# ── 배너 스위치 (사용자 지시 2026-07-17: 배포 전까지 숨김, 슬롯은 유지) ──
SHOW_ADSENSE = False   # True로 바꾸면 애드센스 자리 다시 노출
SHOW_COUPANG_BANNER = False  # 쿠팡 파트너스 iframe 배너 (재료명 복사버튼과 별개)

def ad_slot(slot_id, inner):
    # 꺼져 있을 때는 **HTML 주석**으로 남긴다 (2026-07-24 사용자 지시 "제거는 아니고 주석").
    #  🔴 예전엔 display:none인 div를 그대로 뒀는데, 그러면 소스에 "광고 영역 (애드센스)"라는
    #     문구와 빈 광고 슬롯이 379개 페이지에 살아 있다. 애드센스 심사 봇은 렌더링이 아니라
    #     소스를 읽으므로 "광고 자리만 깔아둔 사이트"로 오해할 소지가 있다.
    #     주석으로 두면 삽입 지점은 그대로 보존되면서 심사 대상 콘텐츠에서는 빠진다.
    #  승인 후 SHOW_ADSENSE=True로 바꾸면 원래 자리에 그대로 살아난다.
    shown = (SHOW_ADSENSE if slot_id.startswith("ad") else SHOW_COUPANG_BANNER)
    if not shown:
        return f'<!-- banner-slot:{slot_id} (숨김 — 승인 후 SHOW_ADSENSE/SHOW_COUPANG_BANNER=True) -->'
    return f'<div class="banner-slot" id="{slot_id}">{inner}</div>'
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview")
os.makedirs(OUT, exist_ok=True)

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

def esc(s):
    return html.escape(str(s)) if s is not None else ""

# 재료 4분류(농/축/수/가)는 ingredient_cat.py 단일 출처. 옛날엔 여기 하드코딩 12키뿐이라
#  차돌박이·항정살이 '농'으로 잘못 표시됐다(2026-07-18). 시세 페이지와 같은 규칙을 쓴다.
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from ingredient_cat import cls4 as _cls4
from theme import BODY_CSS, TYPO_CSS, gnav, P2_CSS, CSS_VARS, HEAD_SCRIPT, BTN, AUTH_BTN, TOGGLE_JS, SHARE_BTN, SHARE_BTM, HEAD_TAGS, FOOTER_LINKS, FOOTER_CSS, ADFIT, ADFIT_CSS, CPSEARCH, CPSEARCH_CSS, SOURCES, SOURCES_CSS, GNAV, GNAV_CSS, WRAP_CSS, CHAR_DEFS, CHAR

def cls4(key, klass, name="", is_retail=0):
    return _cls4(key, name, klass, is_retail)

# 재료 키코드 → 원산지 종류 (brand_origins 컬럼)
KEY_ORIGIN = {}
for k in ["raw_chicken_10","chicken_parts","chicken_boneless"]: KEY_ORIGIN[k]="chicken"
for k in ["pork_trotter","pork_belly_import","pork_loin_tangsuyuk","pork_loin_donkasu"]: KEY_ORIGIN[k]="pork"
for k in ["beef_patty","beef_slices","beef_stew"]: KEY_ORIGIN[k]="beef"
for k in ["seafood_mix","salmon_raw","white_fish_raw"]: KEY_ORIGIN[k]="seafood"

# 소스 배합은 이제 menu_ingredients.composition(메뉴별 큐레이션, sauce_data.py)에서 읽는다.
# composition 이 있는 재료줄만 "양념·소스 구성" 블록으로, 없으면 일반 재료 행으로 표시.
import re as _re
def parse_comp(comp):
    # 괄호가 짧은 명칭이면 제목, 재료 나열(·/: 포함)이면 부가설명으로 분리.
    #  "체다치즈분말 · 파마산 · 소금 (뿌링클 스노윙)" → 제목="뿌링클 스노윙", 토큰=[…]
    #  "빅맥소스(마요·피클렐리시·머스터드) · 다진양파" → 제목="", 토큰=[빅맥소스,다진양파], 설명=["마요·피클렐리시·머스터드"]
    parens = _re.findall(r"\(([^)]*)\)", comp)
    base = _re.sub(r"\([^)]*\)", "", comp)
    tokens = [t.strip() for t in base.split("·") if t.strip()]
    header = " · ".join(p for p in parens if "·" not in p and ":" not in p)
    notes = [p for p in parens if "·" in p or ":" in p]
    return header, tokens, notes

def won(n):
    return f"{n:,}원" if n is not None else "-"


# ── 재료 양 표기 ───────────────────────────────────────────────
#  DB는 무게를 **g으로만** 저장한다(kg 혼용 금지, 2026-07-25 규칙).
#  화면에서만 1,000g 이상을 kg으로 접어 보여준다 — "1600g"보다 "1.6kg"이 읽힌다.
def fmt_amt(amount, unit):
    if amount is None:
        return ""
    if unit in ("g", "ml") and amount >= 1000:
        big = "kg" if unit == "g" else "L"
        v = amount / 1000.0
        # 1.6kg / 2.2kg 처럼 소수 한 자리까지. 정수면 1kg 으로.
        return (f"{v:.1f}".rstrip("0").rstrip(".")) + big
    return f"{amount:g}{unit}"

# 🔴 화면에 나가는 글에서 **상표를 가린다** (2026-07-27 대표 지시)
#    *"로켓프래시로 나오는건 다 없애야지"* · *"곰곰 도"*
#    *"우리가 저걸 다 알려주면 저거 다 알아서 검색해서 살거 아니야? 정보가 다 돈이야"*
#    규칙은 `namemask.py` 한 곳에 있다 — 생성기마다 브랜드 목록을 따로 두면 또 어긋난다.
#    ⚠️ 파트너스 고지 문구(`쿠팡 파트너스 활동으로…`)는 법적 의무라 지우지 않는다.
from namemask import mask as strip_mall
# 메뉴판 탭 — **브랜드 원본이 1순위**(`brand_menu_cat`), 없는 브랜드만 표준 탭으로 떨어진다
import brand_menu_store as bmstore
from menu_tab import order_key as tab_order, tab_of


# ── 밀키트 배너 ────────────────────────────────────────────────
#  🔴 정본은 **DB의 menu_mealkit** 이다(관리페이지에서 사람이 고른 것).
#     옛 mealkit_all.json 자동매칭은 50%가 중복이라 폐기했다(2026-07-25).
#     status='none' 이면 그 메뉴는 배너를 안 띄운다("해당 없음" 처리).
MEALKIT = {}
for _r in cur.execute("SELECT menu_id, product_id, name, price, rocket, image, url, "
                      "match_type, status FROM menu_mealkit WHERE status='ok'"):
    MEALKIT[str(_r["menu_id"])] = {
        "status": "found", "product_name": _r["name"], "price": _r["price"],
        "isRocket": bool(_r["rocket"]), "productImage": _r["image"],
        "productUrl": _r["url"], "match_type": _r["match_type"],
    }

# 밀키트 배너 스위치 — 매칭 재조정(v2) 검수 완료 후 True.
#  2026-07-25: 초기 데이터가 50% 중복 매칭(한 상품이 최대 14개 메뉴에 붙음)이라 끔.
SHOW_MEALKIT = True

def mealkit_card(menu_id):
    if not SHOW_MEALKIT:
        return ""
    it = MEALKIT.get(str(menu_id))
    if not it or it.get("status") != "found":
        return ""
    # 4단 구성: 동일브랜드/대체브랜드 × 로켓/배달 — 라벨로 명확히 구분해서 보여준다.
    #  숨기지 않는다(대체브랜드가 421건 중 386건으로 대부분). 2026-07-25 확정.
    is_official = it.get("match_type") == "정품"
    is_rocket = bool(it.get("isRocket"))
    kind_label = "동일 브랜드" if is_official else "대체 상품"
    kind_cls = "mkofficial" if is_official else "mkalt"
    price = it.get("price")
    price_txt = won(round(price)) if price else "-"
    ship_label = "빠른배송" if is_rocket else "일반배송"
    ship_cls = "mkrocket" if is_rocket else "mkship"
    img = esc(it.get("productImage") or "")
    nm = esc(strip_mall(it.get("product_name") or "")[:44])
    url = esc(it.get("productUrl") or "#")
    return f'''<div class="card mkcard">
<div class="mkh">이 메뉴, 밀키트로 사 먹으면?<span class="mktag {kind_cls}">{kind_label}</span></div>
<a class="mkbody" href="{url}" target="_blank" rel="nofollow sponsored noopener">
<img class="mkimg" src="{img}" alt="{nm}" loading="lazy">
<div class="mkinfo"><div class="mknm">{nm}</div><div class="mkpr">{price_txt}<span class="{ship_cls}">{ship_label}</span></div></div>
</a>
<a class="mkbtn" href="{url}" target="_blank" rel="nofollow sponsored noopener">쿠팡에서 보기</a>
<div class="mknote">쿠팡 파트너스 활동으로 일정액의 수수료를 제공받습니다</div>
</div>'''

# ── 시세 등락 (live 재료: 최신 시세일 vs 직전 시세일) ──
_dates = [r[0] for r in cur.execute("SELECT DISTINCT price_date FROM price_history ORDER BY price_date DESC LIMIT 2")]
from datetime import date as _date
TODAY_YMD = _date.today().isoformat()   # 홈 비교 카드 로테이션 기준일
LIVE_DELTA = {}   # key -> (최신가, 직전가)
# 🔴 2026-07-22 수정: 예전엔 '최신 2개 날짜'를 통째로 잡아 비교했는데, KAMIS는 도매시장 시세라
#    토·일·공휴일엔 경매가 없어 몇 건만 들어온다. 하필 주말 두 날이 잡히면 겹치는 재료가
#    4종밖에 안 돼 홈 미니 카드가 통째로 비었다(실제 발생).
#    → 날짜를 고정하지 말고 **재료마다 값이 있는 최근 두 시점**을 각각 찾아 비교한다.
#    ② 주말·공휴일 수집분은 아예 비교에서 뺀다. KAMIS는 경매가 없는 날 값이 튄다
#       (계란이 07-19 일요일에 7,042원으로 잡혀 다음 평일 대비 -42%로 표시됐다. 실제 시세는 4,000원대).
#       요일로 자르지 않고 **수집 건수**로 거른다 — 그래야 공휴일도 같이 걸러진다.
_SPARSE = {r[0] for r in cur.execute(
    "SELECT price_date FROM price_history WHERE retail_price>0 GROUP BY price_date HAVING COUNT(*)<20")}
#    ③ 🔴 **직전 시점이 너무 오래됐으면 아예 비교하지 않는다**(2026-08-01 신설).
#       07-16 수집분에 단위 버그가 있었다 — 배가 46,820원/kg 로 들어갔다(상자값을 kg 로 넣은 것).
#       그건 나중에 고쳐졌는데, 재료마다 «값이 있는 최근 두 시점» 을 찾다 보니 07-24 를
#       **8일 전 07-16 버그값과** 비교했다. 그 결과 홈 카드가 이렇게 나갔다:
#           배 -92.2% · 사과 -63.4% · 참외 -68.1% · 전복 +180.0%
#       다섯 칸 중 네 칸이 시세 등락이 아니라 **«고쳐진 버그»** 였다.
#       시세 등락은 **가까운 두 시점**을 비교해야 뜻이 있다. 멀리 떨어진 값은 등락이 아니라
#       그냥 다른 데이터다. 그래서 간격에 상한을 둔다.
#       ⚠️ 이 상한 때문에 카드가 비면 «변동이 없다» 가 아니라 **수집기가 안 돈 것**이다.
_MAX_GAP = 7        # 일. 최신 시점과 이만큼 넘게 벌어진 직전 시점은 비교 대상에서 뺀다


def _gap_days(a, b):
    """'YYYY-MM-DD' 두 날짜의 간격(일)."""
    return abs((_date(*map(int, a.split("-"))) - _date(*map(int, b.split("-")))).days)


_prev_label = {}
_last_date = {}
for r in cur.execute("""SELECT ingredient_key k, price_date d, retail_price p FROM price_history
    WHERE retail_price>0 ORDER BY ingredient_key, price_date DESC"""):
    if r["d"] in _SPARSE:
        continue
    e = LIVE_DELTA.get(r["k"])
    if e is None:
        LIVE_DELTA[r["k"]] = (r["p"], None)          # 최신가만 먼저
        _last_date[r["k"]] = r["d"]
    elif e[1] is None:
        if _gap_days(_last_date[r["k"]], r["d"]) > _MAX_GAP:
            continue                                 # 너무 오래된 값 — 비교하지 않는다
        LIVE_DELTA[r["k"]] = (e[0], r["p"])          # 그다음이 직전가
        _prev_label[r["k"]] = r["d"]
LIVE_DELTA = {k: v for k, v in LIVE_DELTA.items() if v[1]}   # 비교값 없는 건 버린다
# 라벨은 '직전 시점'이 가장 많이 걸린 날짜로 쓴다(재료마다 다를 수 있어서)
_lb = sorted(((sum(1 for x in _prev_label.values() if x == d), d)
              for d in set(_prev_label.values())), reverse=True)
DELTA_LABEL = f"{_lb[0][1][5:].replace('-', '.')} 대비" if _lb else ""

# ── 시세 기준일 (2026-07-24) ────────────────────────────────────────────
#  🔴 화면이 "오늘 재료 시세"·"매일 오전 7시 갱신"이라고 말하는데 실제 최신 시세는 07-21이었다
#     (수집기가 사흘째 안 돎). 추정치 고지를 철저히 해온 사이트가 갱신 주기만 사실과 다르게
#     말하고 있었던 것 → 문구를 **실제 최신 시세일에 연동**한다. 수집기를 다시 돌리는 건 별건.
#  _SPARSE(주말·공휴일 소량 수집분)는 비교에서 뺀 것과 같은 이유로 기준일에서도 뺀다.
_pd = [r[0] for r in cur.execute(
    "SELECT DISTINCT price_date FROM price_history WHERE retail_price>0 ORDER BY price_date DESC")]
PRICE_DATE = next((d for d in _pd if d not in _SPARSE), (_pd[0] if _pd else ""))
PRICE_DATE_LABEL = PRICE_DATE[5:].replace("-", ".") if PRICE_DATE else ""
# "며칠 전 조사분인지"를 문구에 쓴다. 오래됐으면 오래됐다고 그대로 보여준다.
import datetime as _dt
try:
    _age = (_dt.date.today() - _dt.date(*map(int, PRICE_DATE.split("-")))).days
except Exception:
    _age = None
#  당일이면 "오늘", 아니면 날짜를 박는다. 어느 쪽이든 "매일 갱신"이라고 주장하지 않는다.
PRICE_FRESH = ("오늘 조사" if _age == 0 else
               f"{PRICE_DATE_LABEL} 조사" if PRICE_DATE_LABEL else "조사일 미상")

def arrow_html(pct, size=12):
    # 한국 관례: 상승 빨강▲ / 하락 파랑▼
    if abs(pct) < 0.05: return f'<span style="font-size:{size}px;color:var(--muted)">— 보합</span>'
    if pct > 0: return f'<span style="font-size:{size}px;color:var(--up);font-weight:700">▲ {pct:+.1f}%</span>'
    return f'<span style="font-size:{size}px;color:var(--infotext);font-weight:700">▼ {pct:+.1f}%</span>'

def menu_delta_pct(menu_id):
    # 메뉴 재료비의 시세 등락: live 재료만 직전가로 치환해 재계산
    rows = cur.execute("""SELECT mi.ingredient_key k, mi.line_cost FROM menu_ingredients mi WHERE mi.menu_id=?""", (menu_id,)).fetchall()
    cur_t = prev_t = 0; has_live = False
    for r in rows:
        lc = r["line_cost"] or 0; cur_t += lc
        if r["k"] in LIVE_DELTA and LIVE_DELTA[r["k"]][0]:
            c, p = LIVE_DELTA[r["k"]]
            prev_t += round(lc * p / c); has_live = True
        else:
            prev_t += lc
    if not has_live or prev_t == 0: return None
    return (cur_t - prev_t) / prev_t * 100

def wholesale_line(it):
    # 재료 1줄의 매장(도매) 원가 = compute_line_costs.py가 저장한 값을 그대로 읽는다.
    #  여기서 다시 계산하면(소매 line_cost × 비율) 반올림이 두 번 일어나 표 합계와
    #  헤드라인 store_cost가 어긋난다. 계산은 한 곳에서만.
    return it["wholesale_cost"]

def logo_html(url, name):
    # 실제 로고 파일 있으면 이미지, 없으면 텍스트 배지 폴백
    if url:
        return f'<img class="blogo" src="{esc(url)}" alt="{esc(name)} 로고" loading="lazy" decoding="async" width="44" height="44">'
    return f'<div class="badge">{esc(name[:2])}</div>'

def fmt_sales(chwon):
    # 공정위 avrgSlsAmt 단위 = 천원 → 억/만원 표기
    won_ = (chwon or 0) * 1000
    if won_ >= 1e8:
        return f"{won_/1e8:.1f}억원"
    if won_ >= 1e4:
        return f"{round(won_/1e4):,}만원"
    return None

def _fc(row):
    keys = row.keys()
    return (row["frcs_cnt"] if "frcs_cnt" in keys else None,
            row["avrg_sls_amt"] if "avrg_sls_amt" in keys else None,
            row["fftc_yr"] if "fftc_yr" in keys else None)

def fftc_block(row):
    # 브랜드 페이지용 카드형 (매장수 + 평균 연매출)
    fc, av, yr = _fc(row)
    if not fc or fc <= 0:
        return ""
    cells = f'<div class="fs"><div class="k">전국 가맹점</div><div class="v">{fc:,}<small>개</small></div></div>'
    sales = fmt_sales(av)
    if sales:
        cells += f'<div class="fs"><div class="k">가맹점당 평균 연매출</div><div class="v">{sales}</div></div>'
    return (f'<div class="fstat">{cells}</div>'
            f'<div class="fsrc">※ {esc(yr)}년 공정거래위원회 가맹사업 정보공개서 기준 · 가맹점 1곳당 연평균 매출액</div>')

def fftc_inline(row):
    # 메뉴 페이지용 한 줄 pill
    fc, av, yr = _fc(row)
    if not fc or fc <= 0:
        return ""
    parts = [f'전국 {fc:,}개 가맹점']
    sales = fmt_sales(av)
    if sales:
        parts.append(f'평균 연매출 {sales}')
    return f'<div class="finline">{" · ".join(parts)}<span class="fy">({esc(yr)} 공정위)</span></div>'

HEAD = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 올마나마</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title} · 올마나마">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:image" content="{ogimg}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{ogimg}">
<link rel="canonical" href="{canon}">
<!--HEAD_TAGS--><!--HEADSCRIPT--><style>
/*THEMEVARS*/
/*FOOTERCSS*/
*{{box-sizing:border-box;margin:0;padding:0}}
/*BODYCSS*/
/*WRAPCSS*/
header.top{{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}}
.top .in{{flex-wrap:wrap}}
.logo{{font-weight:800;font-size:18px;color:var(--ink)}}
.logo small{{color:var(--muted);font-weight:500;font-size:12px;margin-left:8px;padding-left:8px;border-left:1px solid var(--line)}}
.crumb{{font-size:12px;color:var(--muted);padding:12px 0 4px}}
.crumb a{{color:var(--muted);text-decoration:none}}
.brandhead{{display:flex;align-items:center;gap:10px;padding:10px 0 4px}}
.brandhead .blogo{{width:44px;height:44px;border-radius:10px;object-fit:contain;background:var(--card);border:1px solid var(--line)}}
.badge{{width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:var(--grad);color:#fff;font-weight:800;font-size:16px;flex-shrink:0}}
.brandhead .btxt{{font-weight:800;font-size:15px}}
h1{{margin:6px 0 2px}}
.src{{font-size:12.5px;color:var(--muted);margin-bottom:14px;line-height:1.7}}
.src .pill{{display:inline-block;background:var(--line);border-radius:6px;padding:2px 8px;margin-right:6px;font-weight:600;color:var(--muted);font-size:12.5px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin-bottom:12px}}
.mkcard{{padding:14px}}
.mkh{{font-size:13px;font-weight:800;margin-bottom:10px}}
.mkbody{{display:flex;gap:10px;text-decoration:none;color:inherit;align-items:center}}
.mkimg{{width:64px;height:64px;object-fit:cover;border-radius:10px;flex:none;background:var(--line)}}
.mkinfo{{min-width:0}}
.mknm{{font-size:12.5px;line-height:1.4;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}}
.mkpr{{font-size:15px;font-weight:800;margin-top:4px}}
.mkrocket{{font-size:10.5px;font-weight:700;color:#fff;background:#2563eb;border-radius:5px;padding:2px 5px;margin-left:6px;vertical-align:middle}}
.mkship{{font-size:10.5px;font-weight:700;color:var(--muted);background:var(--line);border-radius:5px;padding:2px 5px;margin-left:6px;vertical-align:middle}}
.mktag{{float:right;font-size:10.5px;font-weight:700;border-radius:5px;padding:2px 6px}}
.mkofficial{{color:#fff;background:#16a34a}}
.mkalt{{color:var(--muted);background:var(--line)}}
.mkbtn{{display:block;text-align:center;margin-top:10px;background:var(--brand,#111);color:#fff;border-radius:10px;padding:9px;font-size:13px;font-weight:700;text-decoration:none}}
.mknote{{font-size:10.5px;color:var(--muted);margin-top:8px;text-align:center}}
.summary{{display:flex;align-items:flex-end;justify-content:space-between;gap:8px}}
.summary .lab{{font-size:12.5px;color:var(--muted);margin-bottom:2px}}
.summary .big{{font-size:clamp(26px,21px+2vw,34px);font-weight:800;line-height:1.1}}
.summary .sell{{text-align:right}}
.summary .sell .v{{font-size:19px;font-weight:700}}
.ratio{{display:inline-block;margin-top:10px;padding:5px 12px;border-radius:999px;font-size:13.5px;font-weight:700}}
.ratio.hi{{background:var(--redbg);color:var(--red)}}
.ratio.lo{{background:var(--greenbg);color:var(--green)}}
.estnote{{font-size:13px;color:var(--muted);margin-top:10px;padding-top:10px;border-top:1px dashed var(--line);line-height:1.5;display:flex;gap:6px;align-items:flex-start}}
.estnote .ico{{flex-shrink:0}}
.estnote b{{color:var(--ink)}}
.sect-t{{font-size:15.5px;font-weight:800;margin:2px 0 11px;display:flex;align-items:center;gap:6px}}
.cir{{width:20px;height:20px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12.5px;font-weight:800;flex-shrink:0;color:#fff;font-style:normal}}
.cir.nong{{background:#16a34a}}
.cir.chuk{{background:#e11d48}}
.cir.su{{background:#0891b2}}
.cir.ga{{background:#7c3aed}}
/* 🔴 border-collapse:collapse면 CSS 규격상 **표 자체의 padding이 무시**된다(2026-07-19 실측 확인).
   .ingcard>*{{padding:0 15px}}를 줘도 표만 카드 끝에 붙어 나왔다 → padding 대신 margin으로 여백을 준다. */
.itbl{{width:calc(100% - 30px);margin:0 15px;border-collapse:collapse;font-size:13px}}
.itbl th{{font-size:12.5px;color:var(--muted);font-weight:600;padding:0 0 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
.itbl th.l{{text-align:left}}
.itbl td{{padding:12px 0;border-bottom:1px solid var(--line);vertical-align:middle}}
.itbl td.c{{width:26px;text-align:center;padding-right:6px}}
.itbl td.nm{{line-height:1.75;font-weight:500}}
.itbl td.r{{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}}
/* 양은 재료명 뒤에 붙는 인라인 배지다(칸 아님) — 2026-07-25 */
.itbl .amt{{color:var(--muted);font-size:12px;font-weight:600;margin-left:5px;white-space:nowrap;font-variant-numeric:tabular-nums}}
.itbl td.somae{{font-weight:800;width:62px;font-size:13px}}
.itbl td.domae{{color:var(--muted);width:56px;font-weight:600;font-size:12px}}
.itbl .sep{{color:var(--muted);margin:0 3px}}
.otag{{display:inline-block;background:var(--infobg);color:var(--infotext);font-size:12px;font-weight:600;padding:1px 6px;border-radius:5px;margin-left:6px;vertical-align:middle;white-space:nowrap}}
.itbl tfoot td{{padding-top:13px;font-weight:800;font-size:14px;border-bottom:0}}
.copy{{font-size:12.5px;background:var(--line);color:var(--muted);border:0;padding:3px 9px;border-radius:6px;font-weight:600;cursor:pointer;margin-left:5px;vertical-align:middle}}
.copy:active,.copy.done{{background:var(--greenbg);color:var(--green)}}
.srcrow td{{background:var(--panel)}}
.buyrow{{margin:2px 0 4px}}
.buyrow .sc{{font-weight:700;font-size:14px;background:var(--softbg);border:1px solid var(--softline);border-radius:7px;padding:3px 8px}}
.srcname{{font-weight:600;margin-bottom:4px}}
/* 시판 블록 — 배합 아래에 두고 **조금 크게** 보이게 (2026-07-27 대표 지시).
   소스는 집에서 만드는 배합이 기본이고, 시판은 «간편하게» 쪽이다. */
.srcbuy{{margin-top:9px;padding-top:8px;border-top:1px dashed var(--softline)}}
.srcbuyt{{font-size:12.5px;font-weight:700;color:var(--muted);margin-bottom:4px}}
.srcbuy .sc{{font-size:15px}}
.schips{{display:flex;flex-wrap:wrap;gap:3px 4px;align-items:center}}
.schips .sc{{font-size:13px}}
.snote{{font-size:13px;color:var(--muted);margin-top:7px;line-height:1.5}}
.unc{{background:var(--infobg);border:1px solid var(--infoline);border-radius:10px;padding:10px 12px;margin-top:10px}}
.unc .uh{{font-size:13px;font-weight:800;color:var(--infotext)}}
.unc .uh span{{font-weight:600;color:var(--infotext);font-size:13px}}
.unc .ub{{font-size:13px;color:var(--infotext);line-height:1.6;margin-top:4px}}
.pcard{{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:12px}}
.pcard .hl{{font-size:13px;color:var(--muted);font-weight:600}}
.pcard .hv{{font-size:clamp(30px,26px+2vw,40px);font-weight:800;font-variant-numeric:tabular-nums;line-height:1}}
.bar{{height:14px;background:var(--line);border-radius:99px;overflow:hidden}}
.bar .fill{{display:block;height:100%;border-radius:99px}}
.bar .fill.lo{{background:var(--green)}} .bar .fill.hi{{background:var(--red)}}
.barlab{{display:flex;justify-content:space-between;font-size:12.5px;margin-top:7px;flex-wrap:wrap;gap:4px}}
.barlab b.lo{{color:var(--green)}} .barlab b.hi{{color:var(--red)}}
.barlab .rest{{color:var(--muted)}}
.restnote{{font-size:13px;color:var(--muted);background:var(--panel);border-radius:8px;padding:8px 10px;margin-top:8px;line-height:1.55}}
.home{{display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:11px;border-top:1px dashed var(--line);font-size:13px}}
.home span{{color:var(--muted)}} .home b{{font-size:16px}}
/* 메뉴상세 재설계 (Design 2026-07-18): 2단 막대 + 안쪽 강조 + 집밥 스트립 + 스텝카드 */
.pbar2{{display:flex;height:38px;border-radius:10px;overflow:hidden;margin-bottom:10px}}
.pbar2 .pf{{background:var(--grad);display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;min-width:46px;padding:0 4px}}
.pbar2 .pf .l{{font-size:12px;font-weight:700;opacity:.9;line-height:1.1}} .pbar2 .pf .p{{font-size:12px;font-weight:900;line-height:1.15}}
.pbar2 .pr{{flex:1;background:var(--track);display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--muted)}}
.pbar2 .pr .l{{font-size:12px;font-weight:700;line-height:1.1}} .pbar2 .pr .p{{font-size:12px;font-weight:900;line-height:1.15}}
.pcostrow{{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:13px;margin-bottom:14px}}
.pcostrow .a{{color:var(--ink);font-weight:800;font-variant-numeric:tabular-nums}} .pcostrow .b{{color:var(--muted);font-weight:700}}
.pemph{{background:var(--accentsoft);border-radius:12px;padding:12px 13px;font-size:12px;line-height:1.6;color:var(--muted)}}
.pemph b.a{{color:var(--accent)}} .pemph b.t{{color:var(--ink)}}
/* 원가 카드 표 (2026-07-24 통합지시서 §A1) — 금액을 양옆으로 벌리지 않고 3줄 표로.
   "나머지"·"재료비 빼면" 혼재를 대표 결정으로 **"수익"**으로 통일했다.
   ⚠️ 그래서 "순수익이 아니다"라는 고지가 더 중요해졌다 — 아래 .pwarn은 지울 수 없는 짝이다. */
.ptab{{margin-bottom:12px}}
.prow2{{display:flex;align-items:baseline;gap:10px;padding:9px 0;border-bottom:1px solid var(--line)}}
.prow2:last-child{{border-bottom:0}}
.prow2 .k{{font-size:13.5px;color:var(--muted);font-weight:700}}
.prow2 .k em{{font-style:normal;color:var(--accent);font-weight:800;margin-left:2px}}
.prow2 .v{{margin-left:auto;font-size:17px;font-weight:800;font-variant-numeric:tabular-nums}}
.prow2.pf2 .k{{color:var(--ink);font-weight:800}}
.prow2.pf2 .v{{font-size:22px;font-weight:900}}
/* 강조 박스 ⓐ안(기본) — accentsoft 주황. ⓑ안(빨강)은 시세 ▲와 혼동 여지가 있어 권장하지 않는다.
   ⓑ로 바꾸려면 아래 .pwarn 블록을 .pwarn-b 값으로 교체하면 된다(대표 선택 대기). */
.pwarn{{background:var(--accentsoft);border:1px solid var(--softline);border-radius:12px;
padding:12px 14px;font-size:13px;line-height:1.65;color:var(--ink)}}
.pwarn b{{font-weight:900;color:var(--accent)}}
.homestrip{{display:flex;align-items:center;gap:11px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:14px}}
a.homestrip{{text-decoration:none;color:inherit}}
.homestrip .hgo{{margin-left:auto;font-size:12px;font-weight:700;color:var(--accent);white-space:nowrap}}
.homestrip .hi{{flex:0 0 34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:var(--accentsoft);color:var(--accent)}}.homestrip .hi svg{{width:18px;height:18px}} .homestrip .k{{font-size:12px;color:var(--muted)}} .homestrip .v{{font-size:18px;font-weight:900}}
.rstep{{display:flex;gap:11px;padding:13px 14px;background:var(--card);border:1px solid var(--line);border-radius:13px;margin-bottom:10px}}
.rstep .n{{flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--grad);color:#fff;font-size:12px;font-weight:900}}
.rstep .t{{font-size:13px;line-height:1.55}}
/* 브랜드상세 메뉴 카드 + 카테고리상세 브랜드 리스트 (Design 2026-07-18) */
.bhead{{display:flex;align-items:center;gap:12px;margin:6px 0 14px}}
.bhead .blogo,.bhead .badge{{width:52px;height:52px;border-radius:14px}}
.bhead .badge{{font-size:17px}}
.bhead h1{{font-size:20px;margin:0}} .bhead .off{{font-size:12px;color:var(--accent);text-decoration:none;font-weight:700}}
.mcard{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px;display:block;text-decoration:none;color:inherit}}
.mcard .r1{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}}
.mcard .mnm{{font-size:15px;font-weight:800}} .mcard .mrt{{font-size:14px;font-weight:900;color:var(--accent)}}
.mcard .msub{{font-size:12px;color:var(--muted);margin-bottom:8px}}
.mcard .mbar{{height:6px;background:var(--track);border-radius:3px;overflow:hidden}}
.mcard .mbar span{{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:3px}}
/* 브랜드 전체 메뉴판 (2026-07-27) — 원가를 낸 메뉴는 재료비+링크, 나머지는 이름·가격만 */
/* 🛵 배달앱 가격 안내 배너 (2026-08-01) — 배달로 받은 브랜드 메뉴판 위에 뜬다 */
.dlvnote{{margin:16px 0 0;padding:10px 13px;border:1px solid var(--line);border-left:3px solid #ff7043;
  border-radius:10px;background:rgba(255,112,67,.07);font-size:12.5px;line-height:1.6;color:var(--ink)}}
.board{{margin:22px 0 6px;border:1px solid var(--line);border-radius:14px;background:var(--card);overflow:hidden}}
.board .bdh{{padding:13px 15px;border-bottom:1px solid var(--line)}}
.board .bdh b{{font-size:15px;font-weight:900}}
.board .bdn{{display:block;font-size:11.5px;color:var(--muted);margin-top:3px;line-height:1.6}}
/* 🔴 브랜드 페이지는 «메뉴판 먼저» (2026-07-27 대표 지시)
   전에는 보정 공지 + 분석 문단이 위를 다 차지해 정작 메뉴가 안 보였다.
   설명은 아래 「이 브랜드 정보」로 접어 둔다 — 업체 홈페이지처럼 메뉴명·가격이 주인공이다. */
.binfo{{margin:22px 0 6px;border:1px solid var(--line);border-radius:13px;background:var(--card)}}
/* 브랜드 페이지에서는 로고 옆자리라 위 여백이 필요 없다(2026-07-28) */
/* 메뉴판 요약 — 로고 옆자리. 이 페이지의 주인공은 메뉴판이니 메뉴 얘기만 한다 */
.bsum{{border:1px solid var(--line);border-radius:13px;background:var(--card);padding:15px 17px}}
.bsumt{{font-size:14px;font-weight:900;margin:0 0 10px}}
.bsum ul{{list-style:none;margin:0;padding:0;display:grid;gap:7px}}
.bsum li{{display:flex;align-items:baseline;gap:10px;font-size:13px}}
.bsum .k{{color:var(--muted);font-weight:700;min-width:74px}}
.bsum .v{{font-weight:800;font-variant-numeric:tabular-nums}}
.bsumn{{margin:11px 0 0;font-size:11.5px;color:var(--muted);line-height:1.6}}
@media(min-width:840px){{ .bsum ul{{grid-template-columns:1fr 1fr}} }}
/* 원가 섹션 안의 «어떻게 계산했나» — 접힌 원가를 펼쳐야 보인다 */
.brhow{{margin-top:16px;padding-top:14px;border-top:1px solid var(--line)}}
.brhow h3{{font-size:13.5px;font-weight:900;margin:0 0 9px}}
.brhow .bintro{{border:0;background:transparent;padding:0}}
.binfo>summary{{padding:12px 15px;font-size:13px;font-weight:800;cursor:pointer;color:var(--muted);
               list-style:none}}
.binfo>summary::-webkit-details-marker{{display:none}}
.binfo>summary::after{{content:" ⌄";float:right}}
.binfo[open]>summary::after{{content:" ⌃"}}
.binfo>*:not(summary){{margin-left:15px;margin-right:15px}}
.binfo .bintro{{border:0;background:transparent;padding:0 0 10px}}
/* 카테고리 탭 — 메뉴 100개 넘는 브랜드는 탭 없이는 못 본다.
   🔴 옆으로 흐르게 두면 **오른쪽 탭이 화면 밖에 숨는다** (2026-07-28 대표 지적).
      BBQ 는 탭이 8개고 이름도 「소스&시즈닝&무」 처럼 길어서 모바일에선 절반이 안 보였다.
      → 가로 스크롤을 버리고 **줄바꿈**한다. 안 보이는 탭이 없어야 누를 생각을 한다. */
.bdtabs{{display:flex;flex-wrap:wrap;gap:6px;padding:9px 12px;border-bottom:1px solid var(--line)}}
.bdt{{flex:0 1 auto;min-width:0;padding:5px 11px;border:1px solid var(--line);border-radius:999px;
     background:transparent;font-size:12px;font-weight:700;color:var(--muted);cursor:pointer;
     font-family:inherit;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bdt em{{font-style:normal;opacity:.65;margin-left:3px}}
.bdt.on{{background:var(--accent);border-color:var(--accent);color:#fff}}
.bdt.on em{{opacity:.8}}
/* 모바일 — 탭이 많아도 **두 줄** 안에 들어오도록 줄인다.
   BBQ 8개 탭이 375px 에서 620px 를 먹어 세 줄이 됐다(한 줄에 325px). 여기까지 줄이면 두 줄이다. */
@media(max-width:520px){{
  .bdtabs{{gap:5px;padding:8px 10px}}
  .bdt{{padding:4px 8px;font-size:11px;max-width:calc(100% - 2px)}}
  .bdsubs{{gap:5px;padding:7px 10px}}
  .bds{{padding:4px 8px;font-size:10.5px}}}}
/* 🔴 한 줄에 하나씩만 깔면 오른쪽이 텅 빈다 (2026-07-28 대표 지적 "배치가 섭섭한데")
   → 넓은 화면에서는 2열 + 내부 스크롤. 모바일은 1열.
   🔴 모바일에서 **내부 스크롤 박스는 쓰지 않는다** — 페이지 스크롤과 겹쳐 답답하다.
      대신 12개만 보이고 「더 보기」로 편다. */
/* 🔴 `:nth-child` 는 **h3 도 센다** (2026-07-28).
   SEO 로 탭마다 `<h3 class="sronly">` 를 넣으면서 각 pane 의 첫 자식이 h3 가 됐다.
   그래서 `n+13` 이 «12번째 메뉴부터» 를 가리켜 **11개만 보였고**, `odd` 도 한 칸 밀려
   2열에서 세로선이 엉뚱한 열에 붙었다. h3 는 항상 있으니 **한 칸씩 밀어** 맞춘다.
   (h3 는 `position:absolute` 라 자리는 안 차지하지만 **선택자에서는 세어진다**) */
.bdp{{display:none}} .bdp.on{{display:grid;grid-template-columns:1fr;gap:0}}
.board .bdlist{{overflow:visible}}
/* 하위 카테고리 — 브랜드가 한 겹 더 나눠놨으면 우리도 나눈다 (2026-07-28 대표 지시).
   bhc 는 「치킨 > 후라이드/양념/뿌링클/킹/핫」 처럼 두 겹이다. */
.bdp.has.on{{display:block}}                       /* 이 경우 격자는 .bdsb 가 만든다 */
.bdsubs{{display:flex;flex-wrap:wrap;gap:6px;padding:8px 12px;
        border-bottom:1px solid var(--line);background:var(--track)}}
.bds{{flex:0 1 auto;padding:5px 11px;border:1px solid var(--line);border-radius:999px;
     background:transparent;color:var(--muted);font-size:12px;font-weight:700;
     cursor:pointer;font-family:inherit;white-space:nowrap}}
.bds em{{font-style:normal;opacity:.7;margin-left:3px}}
.bds.on{{background:var(--ink);border-color:var(--ink);color:var(--bg)}}
.bdsb{{display:none}} .bdsb.on{{display:grid;grid-template-columns:1fr;gap:0}}
.board.searching .bdsubs{{display:none}}
/* 맛 목록 — 배스킨라빈스처럼 «가격은 사이즈, 맛은 골라만» 인 곳 (2026-07-28) */
.flvn{{padding:10px 15px;border-bottom:1px solid var(--line);background:var(--track);
      font-size:12.5px;color:var(--muted);font-weight:700;line-height:1.5}}
.flvn b{{color:var(--ink)}}
.flvd{{border-top:1px solid var(--line)}}
.flvd>summary{{list-style:none;cursor:pointer;padding:12px 15px;font-size:13px;
              font-weight:800;color:var(--accent)}}
.flvd>summary::-webkit-details-marker{{display:none}}
.flvd>summary::after{{content:" ▾";font-size:11px}}
.flvd[open]>summary::after{{content:" ▴"}}
.flvd>summary:hover{{background:var(--track)}}
.flvs{{display:flex;flex-wrap:wrap;gap:7px;padding:2px 15px 15px}}
.flv{{padding:7px 12px;border:1px solid var(--line);border-radius:999px;
     background:var(--card);font-size:13px;font-weight:700;color:var(--ink)}}
/* 🔴 페이지 넘김 — 「＋ 전체 보기」를 대체했다(2026-07-28). 배스킨 297개처럼 긴 탭은
   한 번에 펼치면 끝없이 스크롤해야 해서 메뉴판으로 안 보인다. */
.bdpg{{display:flex;flex-wrap:wrap;align-items:center;gap:5px;padding:11px 14px;
      border-top:1px solid var(--line)}}
.pgb{{min-width:32px;height:32px;padding:0 9px;border:1px solid var(--line);border-radius:9px;
     background:var(--card);color:var(--ink);font-size:12.5px;font-weight:800;
     cursor:pointer;font-family:inherit}}
.pgb:hover:not(:disabled){{background:var(--track)}}
.pgb.on{{background:var(--accent);border-color:var(--accent);color:#fff}}
.pgb:disabled{{opacity:.35;cursor:default}}
.pgd{{color:var(--muted);padding:0 2px}}
.pgn{{margin-left:auto;font-size:11.5px;color:var(--muted);font-weight:700;
     font-variant-numeric:tabular-nums}}
@media(min-width:700px){{
  .bdp.on{{grid-template-columns:1fr 1fr}}
  .bdsb.on{{grid-template-columns:1fr 1fr}}
  .bmit:nth-child(even){{border-right:1px solid var(--line)}}   /* h3 가 1번이라 왼쪽 열이 짝수다 */
  .bdsb .bmit:nth-child(odd){{border-right:1px solid var(--line)}}  /* .bdsb 안엔 h3 가 없다 */
  .bdsb .bmit:nth-child(even){{border-right:0}}
  .board .bdlist{{max-height:620px;overflow:auto}}
}}
/* 🔴 모바일에서 메뉴판을 제일 많이 본다(대표 지시 2026-07-28).
   38px 은 손가락으로 누르기 빠듯하고 긴 이름이 잘렸다 → 44px 로 키운다. */
.bmit{{display:flex;align-items:center;gap:10px;padding:11px 15px;border-bottom:1px solid var(--line);
      font-size:13px;color:var(--ink);text-decoration:none;min-width:0}}
.bdht{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.bdtt{{font-size:15px;font-weight:900;margin:0;line-height:1.3}}
.sronly{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}}
.bdq{{flex:1;min-width:150px;max-width:280px;padding:6px 11px;border:1px solid var(--line);
     border-radius:999px;background:var(--bg);color:var(--ink);font-size:12.5px;font-family:inherit}}
.bdq:focus{{outline:2px solid var(--accent);outline-offset:-1px}}
.board.searching .bdtabs{{display:none}}
/* 🔴 이름은 **자기 길이만** 차지한다 — flex:1 이면 「원가」 칩이 오른쪽 끝까지 밀려
   판매가에 붙어 보인다(2026-07-28 대표 지적). 빈자리는 `.bmp` 의 margin-left:auto 가 민다. */
.bmit .bmn{{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.bmit .bmp{{margin-left:auto;font-weight:800;white-space:nowrap}}
/* 가격을 아직 못 구한 메뉴 — 이름은 보여주되 값처럼 보이면 안 된다(2026-07-28 대표 지시) */
.bmit .bmx{{font-weight:700;font-size:11.5px;color:var(--muted)}}
/* 판매가를 아직 못 구한 브랜드 — 목록에서 그렇다고 알린다(2026-07-28 대표 지시) */
.bwait{{display:inline-block;margin-left:5px;padding:1px 6px;border-radius:999px;
       border:1px solid var(--line);color:var(--muted);font-size:10.5px;font-weight:700}}
.bmit.on{{background:var(--track)}}
/* 원가를 낸 메뉴 — ★ 는 뺐고 「원가」 를 **메뉴명 바로 오른쪽**에 붙인다(2026-07-28 대표 지시) */
.bmit.on .bmk{{flex:none;font-size:11px;font-weight:800;color:var(--accent);white-space:nowrap;
              padding:2px 7px;border:1px solid var(--accent);border-radius:999px}}
.board .bdf{{padding:11px 15px;font-size:11.5px;color:var(--muted);border-top:1px solid var(--line)}}
.cathead{{display:flex;align-items:center;gap:11px;margin:6px 0 12px}} .cathead .ce{{font-size:30px}} .cathead h1{{margin:0}}
/* 브랜드·카테고리 페이지 분석 문단 (2026-07-24) — 목록만 있던 얇은 페이지 보강 */
/* 🔴 업종 설명은 **접어둔다** (2026-07-31 대표 지시). 글이 다섯 줄 깔려 있으면
   정작 브랜드 목록이 안 보인다. 닫힌 채로 시작하고 궁금한 사람만 편다.
   ⚠️ details 가 아닌 곳(브랜드 원가 설명 등)에도 .bintro 를 쓰므로 패딩은 details 에만 준다. */
.bintro{{margin:0 0 16px;padding:14px 15px;background:var(--card);border:1px solid var(--line);border-radius:13px}}
details.bintro{{padding:0}}
details.bintro>summary{{list-style:none;cursor:pointer;padding:13px 15px;font-size:13.5px;
                       font-weight:800;color:var(--ink)}}
details.bintro>summary::-webkit-details-marker{{display:none}}
details.bintro>summary::after{{content:" ▾";font-size:11px;color:var(--muted)}}
details.bintro[open]>summary::after{{content:" ▴"}}
details.bintro>summary:hover{{background:var(--track);border-radius:13px}}
.bintroin{{padding:0 15px 14px}}
.bintro p{{font-size:13.5px;line-height:1.75;margin:0 0 9px;color:var(--ink)}}
.bintro p:last-child{{margin-bottom:0}}
.bintro b{{font-weight:800}}
.bintro .bintro-note{{font-size:12px;color:var(--muted);line-height:1.65;
padding-top:9px;border-top:1px solid var(--line)}}
/* 데이터 보정중 안내 (2026-07-24 사용자 지시) — 시세 자동화가 값을 계속 보정하는 중이라
   지금 보이는 금액이 나중과 다를 수 있다는 걸 원가가 나오는 자리에 명시한다. */
.wipbox{{margin:0 0 14px;padding:11px 13px;background:var(--warnbg);border:1px solid var(--warnline);
border-radius:12px;font-size:12.5px;line-height:1.7;color:var(--warntext)}}
.wipbox b{{font-weight:800}}
/* 단가 확정도 배지 (2026-07-23) — 계수추정이 아닌 '실제 조사한 단가' 비율 */
.cfd{{display:flex;align-items:baseline;flex-wrap:wrap;gap:4px 9px;margin:8px 0 12px;
padding:9px 12px;border-radius:11px;font-size:12.5px;line-height:1.6}}
.cfd .cfdl{{font-weight:800;white-space:nowrap}}
.cfd .cfdd{{color:var(--muted);font-size:12px}}
.cfd-ok{{background:var(--goodbg);border:1px solid var(--good)}} .cfd-ok .cfdl{{color:var(--good)}}
.cfd-mid{{background:var(--infobg);border:1px solid var(--infoline)}} .cfd-mid .cfdl{{color:var(--infotext)}}
.cfd-wip{{background:var(--panel);border:1px solid var(--line)}} .cfd-wip .cfdl{{color:var(--muted)}}
.blist{{background:var(--card);border:1px solid var(--line);border-radius:15px;overflow:hidden}}
.brow{{display:flex;align-items:center;gap:12px;padding:14px;border-top:1px solid var(--line);text-decoration:none;color:inherit}}
.brow:first-child{{border-top:0}}
.brow .be{{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:9px;background:var(--track);font-size:16px;flex-shrink:0}}
.brow .bmid{{flex:1;min-width:0}} .brow .bn{{font-size:15px;font-weight:800}} .brow .bc{{font-size:12px;color:var(--muted)}}
.brow .bchev{{color:var(--muted);font-size:18px}}
.lead{{font-size:14px;color:var(--muted);line-height:1.6;margin:6px 0 12px}}
.lead b{{color:var(--ink)}}
.dnote{{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:10px 0}}
.dnote summary{{padding:11px 13px;font-size:12.5px;font-weight:700;color:var(--muted);cursor:pointer;list-style:none}}
.dnote summary::-webkit-details-marker{{display:none}}
.dnote summary::after{{content:'▾';float:right}}
.dnote[open] summary::after{{content:'▴'}}
.dnote>div{{padding:0 13px 12px;font-size:13px;color:var(--muted);line-height:1.7}}
.ingcard{{padding:0}}
.ingcard>summary{{padding:15px;font-size:15px;font-weight:800;cursor:pointer;list-style:none}}
.ingcard>summary::-webkit-details-marker{{display:none}}
.ingcard>summary::after{{content:'▾';float:right;color:var(--muted);font-weight:400}}
.ingcard[open]>summary::after{{content:'▴'}}
.ingcard>*:not(summary){{padding-left:15px;padding-right:15px}}
.ingcard[open]{{padding-bottom:14px}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin-bottom:13px}}
.legend span{{display:inline-flex;align-items:center;gap:5px}}
.legend .cir{{width:17px;height:17px;font-size:12px}}
.total{{display:flex;justify-content:space-between;padding-top:12px;margin-top:4px;font-weight:800;font-size:15px}}
.recipe li{{margin:0 0 10px 20px;font-size:14.5px;line-height:1.6}}
.disc{{font-size:13px;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-top:16px;line-height:1.6}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}
.bcard{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 14px;text-decoration:none;color:inherit;display:flex;flex-direction:column;gap:6px}}
.bcard .nm{{font-weight:700;font-size:15.5px}}
.bcard .mt{{font-size:12.5px;color:var(--muted)}}
.mrow{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 15px;margin-bottom:9px;text-decoration:none;color:inherit;display:flex;justify-content:space-between;align-items:center;gap:10px}}
.mrow .mn{{font-weight:700;font-size:15px}}
.mrow .mr{{font-size:12.5px;color:var(--muted);margin-top:2px}}
.mrow .rt{{font-weight:800;font-size:17px}}
.hero{{text-align:center;padding:8px 0 4px}}
.searchbox{{position:relative;margin:12px 0 4px}}
.searchbox input{{width:100%;box-sizing:border-box;padding:13px 14px 13px 40px;font-size:15px;border:1.5px solid var(--line);border-radius:12px;background:var(--card);color:var(--ink);outline:none;font-family:inherit}}
.searchbox input::placeholder{{color:var(--muted)}}
.searchbox input:focus{{border-color:var(--accent)}}
.searchbox .si{{position:absolute;left:13px;top:50%;transform:translateY(-50%);font-size:16px;opacity:.6}}
#sresult{{margin-top:8px}}
#sresult .mrow{{margin-bottom:6px}}
#sempty{{font-size:13px;color:var(--muted);text-align:center;padding:14px}}
.tiles{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.navbtns{{display:flex;flex-direction:column;gap:8px;margin-top:14px}}
.nbtn{{display:flex;align-items:center;gap:11px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:13px 15px;text-decoration:none;color:inherit}}
.nbtn .ni{{flex:0 0 38px;height:38px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:var(--accentsoft);color:var(--accent)}}
.nbtn .ni svg{{width:19px;height:19px}}
.nbtn.main .ni,.nbtn.hi .ni{{background:rgba(255,255,255,.22);color:#fff}}
.nbtn .nt{{flex:1;font-weight:800;font-size:14.5px;display:flex;flex-direction:column;gap:2px}}
.nbtn .nt small{{font-weight:500;font-size:13px;color:var(--muted)}}
.nbtn .nc{{color:var(--muted);font-size:18px}}
.nbtn.hi,.nbtn.main{{background:var(--grad);border-color:transparent;color:#fff}}
.nbtn.hi .nt small,.nbtn.main .nt small{{color:rgba(255,255,255,.92)}}
.nbtn.hi .nc,.nbtn.main .nc{{color:rgba(255,255,255,.8)}}
.nbtn.main{{padding:16px 15px}} .nbtn.main .nt{{font-size:16px}}
.tile{{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:16px 14px;text-decoration:none;color:inherit;display:flex;flex-direction:column;align-items:flex-start;gap:1px}}
.tile .ic{{font-size:30px}}
.tile .tn{{font-size:15px;font-weight:800;margin-top:8px}}
.tile .tc{{font-size:12px;color:var(--muted)}}
.ad{{background:var(--panel);
border:1px dashed var(--line);border-radius:12px;padding:18px;text-align:center;color:var(--muted);font-size:12px;margin:12px 0}}
.cpbanner{{margin:12px 0;text-align:center}}
.cpbanner iframe{{border-radius:10px;max-width:100%}}
.cpnote{{font-size:12px;color:var(--muted);text-align:center;margin-top:4px}}
.fstat{{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 3px}}
.fstat .fs{{background:var(--infobg);border:1px solid var(--infoline);border-radius:12px;padding:9px 13px;flex:1;min-width:132px}}
.fstat .fs .k{{font-size:12.5px;color:var(--muted);font-weight:600;margin-bottom:3px;display:flex;align-items:center;gap:4px}}
.fstat .fs .v{{font-size:17px;font-weight:800;color:var(--infotext);line-height:1.1}}
.fstat .fs .v small{{font-size:13px;font-weight:600;color:var(--muted)}}
.fsrc{{font-size:12.5px;color:var(--muted);margin:0 0 8px;line-height:1.5}}
.finline{{display:inline-flex;flex-wrap:wrap;gap:4px 10px;font-size:12px;color:var(--infotext);background:var(--infobg);border:1px solid var(--infoline);border-radius:8px;padding:6px 10px;margin:2px 0 10px;font-weight:600}}
.finline .fy{{color:var(--muted);font-weight:500}}
/* 홈 히어로 — 🎨 2026-08-02 «브랜드 존» (2구역 규칙에서 캐릭터·크림·모눈이 허용되는 **딱 한 곳**)
   ⛔ 이 블록 밖으로 크림·모눈·검은고딕을 내보내지 말 것. */
.homehero{{border-radius:16px;padding:22px 18px 18px;margin:12px 0 0;
background-color:var(--bz-cream);background-image:
repeating-linear-gradient(0deg,transparent 0 55px,color-mix(in srgb,var(--bz-grid) 28%,transparent) 55px 56px),
repeating-linear-gradient(90deg,transparent 0 55px,color-mix(in srgb,var(--bz-grid) 28%,transparent) 55px 56px);
border:1px solid var(--line)}}
.homehero h2{{margin:0 0 14px;font-size:clamp(21px,6.2vw,27px);line-height:1.35;letter-spacing:-.02em;
color:#111;font-family:"Black Han Sans",sans-serif;font-weight:400}}
:root[data-theme=dark] .homehero h2{{color:#F4EDE6}}
.homehero h2 span{{color:var(--accent)}}
/* 캐릭터 2인 — 핑크 올마(주인공) + 노랑 사장님(보조) */
.hchars{{display:flex;justify-content:center;align-items:flex-end;gap:18px;margin:0 0 10px}}
.hchars svg{{width:84px;height:84px}}
@media(max-width:520px){{.hchars svg{{width:66px;height:66px}}}}
/* 🎨 빈 상태 — «브랜드 존». 캐릭터 한 컷 + 안내 문구 */
#sempty{{display:flex;align-items:center;gap:14px;padding:18px 16px;background:var(--panel);
border:1px solid var(--line);border-radius:14px;font-size:14px;color:var(--muted);line-height:1.6}}
#sempty .emptychar{{width:60px;height:60px;flex-shrink:0}}
.homehero .searchbox{{margin:0}}
.homehero .searchbox input{{box-shadow:0 4px 14px -8px rgba(20,22,25,.2)}}
/* 원가율 순위 (Design 홈 2026-07-18) */
.rankhead{{display:flex;align-items:baseline;justify-content:space-between;margin:22px 0 10px}}
.rankhead .rt2{{font-size:17px;font-weight:900}}
.rankhead .info{{font-size:12px;color:var(--muted);cursor:pointer}}
.seg{{display:flex;gap:6px;background:var(--seg);border-radius:12px;padding:4px;margin-bottom:12px}}
.seg button{{flex:1;padding:9px 8px;border-radius:9px;border:none;font-size:13px;font-weight:700;color:var(--muted);background:transparent;cursor:pointer;font-family:inherit;white-space:nowrap}}
.seg button.on{{background:var(--grad);color:#fff;font-weight:900}}
.ranklist{{background:var(--card);border:1px solid var(--line);border-radius:15px;overflow:hidden}}
.rrow{{display:flex;align-items:center;gap:12px;padding:13px 14px;border-bottom:1px solid var(--line);cursor:pointer;width:100%;text-align:left;background:none;border-left:0;border-right:0;border-top:0;font-family:inherit;color:inherit;text-decoration:none}}
.rrow:last-of-type{{border-bottom:0}}
.rrow .rk{{width:20px;text-align:center;font-weight:900;font-size:15px;color:var(--faint)}}
.rrow .rmid{{flex:1;min-width:0;display:block}}
.rrow .rmn{{display:block;font-size:14px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rrow .rsub{{display:block;font-size:12px;color:var(--muted);margin:1px 0 6px}}
.rrow .rbar{{display:block;height:5px;background:var(--track);border-radius:3px;overflow:hidden}}
.rrow .rbar span{{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:3px}}
.rrow .rratio{{font-size:15px;font-weight:900;color:var(--accent);min-width:52px;text-align:right}}
.rrow .rlg{{flex:0 0 26px;width:26px;height:26px;border-radius:7px;object-fit:contain;background:#fff;border:1px solid var(--line)}}
.rrow .rlg.rbg{{display:flex;align-items:center;justify-content:center;font-size:9.5px;font-weight:900;color:var(--accent);background:var(--accentsoft);border-color:transparent}}
.rrow .rinfo{{flex:0 0 22px;text-align:center;color:var(--muted);font-size:13px}}
.rall{{text-align:center;padding:13px;font-size:13px;font-weight:800;color:var(--muted);text-decoration:none;display:block}}
.sheetbg{{position:fixed;inset:0;z-index:50;background:rgba(10,12,15,.5);display:none;align-items:flex-end}}
.sheetbg.on{{display:flex}}
.sheet{{width:100%;max-width:520px;margin:0 auto;background:var(--card);border-radius:22px 22px 0 0;padding:8px 20px 24px;animation:sheetUp .3s cubic-bezier(.22,1,.36,1)}}
@keyframes sheetUp{{from{{transform:translateY(100%)}}to{{transform:none}}}}
.sheet .grip{{width:40px;height:4px;border-radius:2px;background:var(--line);margin:8px auto 16px}}
.sheet .sbrand{{font-size:12px;font-weight:700;color:var(--muted)}}
.sheet .smenu{{font-size:20px;font-weight:900;margin:2px 0 16px}}
.sheet .sprow{{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:10px}}
.sheet .sprow .k{{font-size:13px;color:var(--muted)}} .sheet .sprow .v{{font-size:22px;font-weight:900}}
.sheet .sbar{{display:flex;height:28px;border-radius:8px;overflow:hidden;margin-bottom:8px}}
.sheet .sbar .f{{background:var(--grad);display:flex;align-items:center;justify-content:center;color:#fff;font-size:12.5px;font-weight:800;min-width:44px}}
.sheet .sbar .rr{{flex:1;background:var(--track);display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:12.5px;font-weight:700}}
.sheet .skv{{display:flex;gap:10px;margin-bottom:14px}}
.sheet .skv>div{{flex:1;border-radius:11px;padding:11px 12px}}
.sheet .skv .a{{background:var(--accentsoft)}} .sheet .skv .a .k{{font-size:12.5px;color:var(--accent)}} .sheet .skv .a .v{{font-size:16px;font-weight:900;color:var(--accent)}}
.sheet .skv .b{{background:var(--track)}} .sheet .skv .b .k{{font-size:12.5px;color:var(--muted)}} .sheet .skv .b .v{{font-size:16px;font-weight:900}}
.sheet .snote{{font-size:12px;color:var(--muted);line-height:1.6;background:var(--track);border-radius:10px;padding:11px 12px;margin-bottom:16px}}
.sheet .sgo{{display:block;text-align:center;padding:15px;border-radius:13px;background:var(--grad);color:#fff;font-size:15px;font-weight:900;text-decoration:none}}
/* ── PC 반응형 (Design PC 레이아웃, 2026-07-18): 좁은 모바일 컬럼 → 넓은 다단 ── */
/* 사이드 '실시간 재료 가격' 카드의 빈자리 안내문 (2026-07-22 사용자 지시).
   홈 카드 숫자를 순이익으로 오해할 수 있어 여기서 한 번 풀어준다.
   2026-07-24 오전: '수익'→'재료비 빼면'으로 바꿨다가,
   같은 날 대표 결정으로 **'수익'으로 되돌렸다**(통합지시서 §A1 — 표현 혼재 정리).
   대신 '순수익이 아니다' 고지를 더 눈에 띄게 키웠다. 둘은 짝이라 한쪽만 지우지 말 것. */
.rmnote{{font-size:12px;line-height:1.65;color:var(--muted);background:var(--panel);
  border:1px solid var(--line);border-radius:10px;padding:10px 11px;margin:2px 0 10px}}
.rmnote b{{color:var(--ink);font-weight:800}}
/* 🔴 홈 «브랜드 메뉴판» 롤링 (2026-07-31) — 10초마다 브랜드가 하나씩 바뀐다.
   원가 카드가 있던 자리다. 메뉴판이 메인이 되면서 홈 본문도 메뉴판으로 갈아탔다. */
.bboard{{background:var(--card);border:1px solid var(--line);border-radius:15px;
  padding:14px 15px;min-height:236px}}
.bbhd{{display:flex;align-items:center;gap:9px;padding-bottom:10px;
  border-bottom:1px solid var(--line);margin-bottom:4px}}
.bblogo{{width:30px;height:30px;flex:none;border-radius:8px;object-fit:contain;
  background:#fff;border:1px solid var(--line)}}
.bblogo.nolg{{display:flex;align-items:center;justify-content:center;
  background:var(--accentsoft);color:var(--accent);font-weight:800;font-size:14px}}
.bbnm{{flex:1;font-weight:800;font-size:15px;display:flex;flex-direction:column;gap:1px}}
.bbnm small{{font-weight:500;font-size:12px;color:var(--muted)}}
.bbgo{{font-size:12.5px;color:var(--accent);font-weight:700;white-space:nowrap}}
.bbrow{{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px dashed var(--line)}}
.bbrow:last-child{{border-bottom:0}}
.bbrow .m{{flex:1;font-size:13.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.bbrow .p{{font-weight:800;font-size:13.5px;white-space:nowrap}}
/* 지금 몇 번째 브랜드인지 — 점으로만. 눌러서 넘길 수도 있다 */
.bbdots{{display:flex;flex-wrap:wrap;gap:5px;justify-content:center;margin-top:10px}}
.bbdots i{{width:6px;height:6px;border-radius:50%;background:var(--line);cursor:pointer}}
.bbdots i.on{{background:var(--accent);width:16px;border-radius:3px}}
/* 우측 «많이 찾는 검색어» 아래 주의문 — 실시간이 아니라는 걸 반드시 보이게 */
.rmnote2{{font-size:11.5px;color:var(--muted);line-height:1.5;margin-top:8px;
  padding-top:8px;border-top:1px solid var(--line)}}
/* 홈 원가 점검 카드 (2026-07-22) — 메뉴 상세의 판매가/재료비/나머지 막대를 홈용으로 줄인 것 */
.cclist{{display:flex;flex-direction:column;gap:9px}}
.ccard{{display:block;padding:13px 14px;border-radius:14px;background:var(--card);
  border:1px solid var(--line);text-decoration:none;color:inherit}}
.ccard .cch{{display:flex;align-items:center;gap:9px;margin-bottom:9px}}
.ccard .cclogo{{width:26px;height:26px;flex:none;border-radius:7px;object-fit:contain;
  background:#fff;border:1px solid var(--line)}}
/* 로고가 없는 브랜드(20곳, 예전 수집분이 반려됨)는 첫 글자 배지로 자리를 채운다 */
.ccard .cclogo.nolg{{display:flex;align-items:center;justify-content:center;background:var(--panel);
  color:var(--muted);font-size:13px;font-weight:900}}
.ccard .ccnm{{flex:1;min-width:0}}
/* 메뉴명과 판매가를 붙여 쓴다(2026-07-22) — 양 끝에 떨어뜨렸더니 짝이 안 읽혔다 */
.ccard .ccnm b{{display:block;font-size:14.5px;font-weight:800;line-height:1.35}}
/* 판매가는 '판매가' 라벨을 붙이고 막대(주황)와 다른 색으로 — 같은 색이면 뭘 가리키는지 헷갈린다 */
.ccard .ccnm b em{{font-style:normal;font-weight:900;color:var(--ink);white-space:nowrap;
  background:#eef1f5;border-radius:6px;padding:1px 7px;font-size:13px;margin-left:2px}}
.ccard .ccnm small{{display:block;font-size:12px;color:var(--muted);margin-top:1px}}
/* 판매가는 오른쪽 정렬 — 카드가 세로로 쌓일 때 가격끼리 줄이 맞아 비교하기 쉽다 */
.ccard .ccsp{{flex:none;text-align:right;font-size:15px;font-weight:900;color:var(--ink);line-height:1.25}}
.ccard .ccsp small{{display:block;font-size:12px;font-weight:700;color:var(--muted)}}
/* 막대는 글자 없이 얇게 — 수치는 아래 한 줄로 몰아 쓴다 */
.ccard .ccbar{{display:flex;height:10px;border-radius:5px;overflow:hidden;background:#eef1f5}}
.ccard .ccf{{background:linear-gradient(90deg,var(--accent),var(--accent2));min-width:2px}}
/* 수치는 가운데로 모은다. 글자색은 막대와 같은 주황을 피해 검정 계열로 둔다 */
.ccard .ccrow{{display:flex;justify-content:center;gap:14px;margin-top:9px;
  font-size:13.5px;font-weight:800;color:var(--ink);flex-wrap:wrap}}
.ccard .ccrow .a::before{{content:"";display:inline-block;width:9px;height:9px;border-radius:3px;
  background:linear-gradient(90deg,var(--accent),var(--accent2));margin-right:5px;vertical-align:-1px}}
.ccard .ccrow .b::before{{content:"";display:inline-block;width:9px;height:9px;border-radius:3px;
  background:#dfe4ea;margin-right:5px;vertical-align:-1px}}
/* 홈 유튜브 카드 (2026-07-22) — 프랜차이즈 가격비교 자리를 대체 */
.ytcard{{display:flex;align-items:center;gap:12px;padding:15px 14px;border-radius:14px;
  background:var(--card);border:1px solid var(--line);text-decoration:none;color:inherit}}
.ytcard .ytico{{flex:none;width:42px;height:42px;border-radius:11px;background:#ff0033;color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:17px}}
.ytcard .yttx{{flex:1;min-width:0}}
.ytcard .yttx b{{display:block;font-size:14.5px;font-weight:800}}
.ytcard .yttx small{{display:block;margin-top:3px;font-size:12.5px;color:var(--muted);line-height:1.5}}
.ytcard .ytgo{{flex:none;color:var(--muted);font-size:16px}}
.ytcard.promo + .ytcard.promo{{margin-top:8px}}
/* 배너는 본문 아래에 둔다(2026-07-22) — 메인 자리를 차지하면 콘텐츠보다 먼저 보인다 */
.promowrap{{margin-top:22px;padding-top:16px;border-top:1px solid var(--line)}}
.ytcard .pmico{{background:linear-gradient(135deg,#3b82f6,#6366f1);font-size:19px}}
/* 홈 본문 = 프랜차이즈 가격비교 (2026-07-19). 요리 칩으로 전환, 기본 선택은 날짜별 로테이션 */
.fclist{{position:relative}}
.fcbox{{display:none;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;
animation:fcin .35s ease}}
.fcbox.on{{display:block}}
@keyframes fcin{{from{{opacity:0}}to{{opacity:1}}}}
.fchd{{display:flex;align-items:center;gap:10px;padding:11px 14px;background:var(--panel);
border-bottom:1px solid var(--line);font-size:12px;color:var(--muted);font-weight:700}}
.fchd .fb{{flex:1;font-size:13.5px;color:var(--ink);font-weight:900}}
.fcnote{{margin-top:8px;font-size:13px;color:var(--muted);line-height:1.6}}
.fcrow{{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--line);
text-decoration:none;color:inherit}}
.flg{{flex:0 0 28px;width:28px;height:28px;border-radius:7px;object-fit:contain;background:#fff;
border:1px solid var(--line)}}
.flg.fbg{{display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;
color:var(--accent);background:var(--accentsoft);border-color:transparent}}
.fcrow .fb{{flex:1;min-width:0;font-size:14.5px;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.fcrow .fb small{{display:block;font-size:13px;color:var(--muted);font-weight:600}}
.fcrow .fp{{font-size:14px;font-weight:800;font-variant-numeric:tabular-nums}}
.fcfoot{{padding:11px 14px;background:var(--panel);font-size:12px;color:var(--muted);line-height:1.6}}
.infobox .ago{{font-weight:500;font-size:12px;color:var(--muted)}}
.btnmore{{display:block;margin-top:10px;padding:8px;border:1px solid var(--line);border-radius:9px;
text-align:center;font-size:13px;font-weight:700;color:var(--ink);text-decoration:none}}
/* 홈 본문 = 오늘의 재료 시세 (2026-07-19, 원가율 순위와 자리 교체) */
.tklist{{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}}
.tkrow{{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--line);
text-decoration:none;color:inherit}}
.tkrow:last-child{{border-bottom:0}}
.tkrow .tn{{flex:1;font-size:13.5px;font-weight:700;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.tkrow .tp{{font-size:13.5px;font-weight:800;font-variant-numeric:tabular-nums}}
.tkrow .tp small{{font-size:12px;color:var(--muted);font-weight:600;margin-left:1px}}
.tkrow .tc{{flex:0 0 62px;text-align:right}}
.ranklink{{margin-top:10px}}
.rpager{{display:flex;align-items:center;justify-content:center;gap:12px;margin:14px 0 4px}}
.pbtn{{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:9px;
padding:8px 14px;font-size:12.5px;font-weight:700;cursor:pointer;font-family:inherit}}
.pbtn:disabled{{opacity:.4;cursor:default}}
.pinfo{{font-size:12.5px;color:var(--muted);font-weight:700;font-variant-numeric:tabular-nums}}
/* 우측 사이드바로 축소한 원가율 순위 */
.rankmini .rmrow{{display:flex;align-items:center;gap:8px;padding:8px 0;border-top:1px solid var(--line);
text-decoration:none;color:inherit}}
.rankmini .rmrow .k{{flex:0 0 16px;font-size:12.5px;font-weight:900;color:var(--faint)}}
.rankmini .rmrow .n{{flex:1;font-size:12.5px;font-weight:700;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.rankmini .rmrow .n small{{display:block;font-size:12px;color:var(--muted);font-weight:500}}
.rankmini .rmrow .r{{font-size:12.5px;font-weight:800;color:var(--ink);font-variant-numeric:tabular-nums}}
.rmall{{display:block;margin-top:9px;font-size:13px;color:var(--muted);text-decoration:none;text-align:right}}
.brow .blogo{{width:34px;height:34px;border-radius:9px;object-fit:contain;background:#fff;border:1px solid var(--line)}}
.brow .bp{{font-size:13px;color:var(--muted);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.nxtwrap{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.nxt{{display:flex;flex-direction:column;gap:2px;padding:12px 13px;background:var(--card);
border:1px solid var(--line);border-radius:12px;text-decoration:none;color:inherit}}
.nxt .nt{{font-size:13px;font-weight:800}} .nxt .nd{{font-size:12.5px;color:var(--muted)}}
.pcside{{display:flex;flex-direction:column;gap:14px;margin-top:16px}}
.brmain,.mmain{{min-width:0}}
/* 🔴 브랜드 페이지 뼈대 (2026-07-28 대표 지시로 두 번 바뀜)
     ① 원가 카드가 메뉴판보다 눈에 띈다 → 원가를 **메뉴판 아래**로 내리고 접었다
     ② 그랬더니 좌측 기둥이 휑해졌다 → **로고 옆에 「브랜드 정보」** 를 놓고
        메뉴판은 그 아래 **전체 폭**으로 내렸다
   구조:  [로고·가맹정보][브랜드 정보]   ← .brtop (PC 2단 / 모바일 세로)
          [        메뉴판         ]   ← .brmain (항상 전체 폭)
          [      원가(접힘)       ]   ← .brcost
   HTML 순서 자체가 이 순서라 CSS 가 안 먹어도 뒤집히지 않는다(옛 `order` 트릭은 없앴다). */
.brtop{{display:flex;flex-direction:column;gap:12px}}
/* 🔴 가맹점·연매출과 메뉴판 요약을 **한 번에 접었다 폈다** (2026-07-28 대표 지시).
   이 페이지 주인공은 메뉴판이라 기본은 접힘 — 메뉴판이 바로 위로 올라온다. */
.brfold{{border:1px solid var(--line);border-radius:13px;background:var(--card)}}
.brfold>summary{{cursor:pointer;list-style:none;padding:12px 16px;
                font-size:13.5px;font-weight:800;color:var(--muted);
                display:flex;align-items:center;gap:8px}}
.brfold>summary::-webkit-details-marker{{display:none}}
.brfold>summary::after{{content:"▾";margin-left:auto;font-weight:700}}
.brfold[open]>summary{{content:"";border-bottom:1px solid var(--line);color:var(--ink)}}
.brfold[open]>summary::after{{content:"▴"}}
.brfold>summary:hover{{background:var(--track);border-radius:13px}}
.brfoldin{{padding:14px 16px 16px;display:grid;gap:14px}}
.brfoldin .bsum{{border:0;background:transparent;padding:0}}
.brfoldin .bsumt{{font-size:13px}}
@media(min-width:840px){{ .brfoldin{{grid-template-columns:1fr 1fr;gap:26px;align-items:start}} }}
.brmain{{margin-top:14px}}
.brcost{{margin-top:20px}}
/* 접힌 상태가 기본 — 제목만 보이고 누르면 펼쳐진다.
   🔴 맨 텍스트로 두니 **누를 수 있는 줄로 안 보였다**(2026-07-28). 옆의 요약·메뉴판이 다
      흰 카드라 원가만 허공에 떠 보인다 → 같은 카드로 맞춘다. */
/* ⚠️ 카드 옷은 **접히는 것(details)** 에만 입힌다. 원가가 0개인 브랜드는 `<div>` 에
   점선 안내(`.brnc`)가 들어 있어, 여기에도 테두리를 주면 **테두리가 이중으로 겹친다**. */
details.brcost{{border:1px solid var(--line);border-radius:13px;background:var(--card)}}
.brcost>summary{{cursor:pointer;list-style:none;padding:13px 16px;
                font-size:15px;font-weight:900;display:flex;align-items:center;gap:8px}}
.brcost>summary::-webkit-details-marker{{display:none}}
.brcost>summary::after{{content:"▾";margin-left:auto;color:var(--muted);font-weight:700}}
.brcost[open]>summary::after{{content:"▴"}}
.brcost>summary:hover{{background:var(--track);border-radius:13px}}
.brcost[open]>summary{{border-bottom:1px solid var(--line);border-radius:13px 13px 0 0}}
details.brcost>*:not(summary){{margin:14px 16px 16px}}
.brct{{font-size:15px;font-weight:900;margin:0}}
.brct em{{font-style:normal;color:var(--accent)}}
.brnc{{border:1px dashed var(--line);border-radius:13px;padding:14px 15px;font-size:12.5px;
      color:var(--muted);line-height:1.7;background:var(--card)}}
.infobox{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}}
.infobox .t{{font-size:13px;font-weight:900;margin-bottom:6px}} .infobox .d{{font-size:12px;color:var(--muted);line-height:1.6}}
@media(min-width:840px){{
  /* 폭(.wrap/.top .in)은 theme.py WRAP_CSS 단일 출처가 정한다 — 여기서 다시 쓰지 말 것 */
  .homehero{{padding:30px 34px}} .homehero h2{{font-size:31px;margin-bottom:18px}}
  .navbtns{{flex-direction:row;gap:12px}} .navbtns .nbtn{{flex:1}}
  .grid{{grid-template-columns:repeat(3,1fr)}}
  .tiles{{grid-template-columns:repeat(4,1fr)}}
  .pcgrid{{display:grid;grid-template-columns:1fr 280px;gap:26px;align-items:start}}
  .pcside{{display:flex;flex-direction:column;gap:14px;position:sticky;top:74px}}
  .pcgrid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}} .pcgrid2 .mcard{{margin-bottom:0}}
  .blist{{display:grid;grid-template-columns:1fr 1fr;gap:10px;background:none;border:0}} .blist .brow{{border:1px solid var(--line);border-radius:13px}}
  .brcost{{margin-top:22px}}
  /* 🔴 원가는 이제 사이드가 아니라 **메뉴판 아래**에 있다. 폭이 넓으니 2열로 편다
     (사이드에 있을 땐 300px 이라 1열이었다). */
  .brcost .pcgrid2{{grid-template-columns:1fr 1fr}}
  .mpc{{display:grid;grid-template-columns:1fr 300px;gap:26px;align-items:start}} .mside{{position:sticky;top:74px}}
  /* 넓은 화면에선 표를 늘이지 않고 가운데로 모은다 — 안 그러면 재료명은 왼쪽 끝, 금액은 오른쪽 끝에
     붙고 가운데가 텅 빈다(사용자 지적 2026-07-19). */
  .itbl{{max-width:480px;margin:0 auto}}
  /* 같은 이유로 프랜차이즈 비교도 안쪽 여백으로 내용을 모은다. 테두리·구분선은 카드 전체 폭을
     유지해야 카드처럼 보이므로, 폭을 줄이는 대신 좌우 padding을 키운다. */
  .fchd,.fcrow,.fcfoot{{padding-left:calc((100% - 400px)/2);padding-right:calc((100% - 400px)/2)}}
  .sheet{{max-width:460px;border-radius:18px;margin-bottom:8vh}}
  .sheetbg{{align-items:center}}
}}
</style></head><body>
<header class="top"><div class="in"><a class="logo" href="index.html" style="text-decoration:none"><span class="lbadge">올</span>올마나마<small>브랜드 메뉴판 한 곳에서</small></a><!--SHARE--><!--BTN--><!--AUTH--><!--GNAV--></div></header>
<div class="wrap">
"""
def next_block(dish=None, dish_nm=None, cat_slug=None, cat_nm=None):
    """페이지 하단 회유 블록. 있는 링크만 넣는다(없는 링크를 만들면 깨진 링크가 된다)."""
    items = []
    if dish:
        items.append((f'dish_{dish}.html', '집에서 만들면', f'{dish_nm} 재료비·만드는 법'))
    if cat_slug:
        items.append((f'cat_{cat_slug}.html', '같은 카테고리', f'{cat_nm} 다른 브랜드 보기'))
    items.append(('ranking.html', '원가율 순위', '판매가 대비 재료비 TOP'))
    items.append(('prices.html', '재료 가격', f'{PRICE_FRESH} 기준 단가'))
    cells = "".join(f'<a class="nxt" href="{h}"><span class="nt">{t}</span>'
                    f'<span class="nd">{d}</span></a>' for h, t, d in items[:4])
    return f'<div class="sect-t" style="margin-top:20px">이어서 볼 만한 것</div><div class="nxtwrap">{cells}</div>'


FOOT = ADFIT + SHARE_BTM + """<div class="disc">※ 재료 소요량은 공개 레시피·유튜버 원가분석 기반 <b>추정치</b>입니다. <b>매장 원가율은 식자재 도매 공급가 추정치</b>로, <b>“집에서 만들면”은 대형마트·온라인몰 소매가(B2C)</b>로 계산했습니다. 실제 매장이 본사에서 받는 공급가와는 다를 수 있습니다. 본 사이트는 각 브랜드와 무관한 정보 제공 사이트이며, 상표·로고는 각 사의 자산입니다. 소매가는 대형마트·온라인몰 판매가를 조사해 인용한 값이며, 그 자체는 제휴 링크가 아닙니다. 제휴 링크가 있는 자리에는 링크 옆에 따로 표시합니다.<br><br><b>가격 데이터 출처</b>: 농산물유통정보(KAMIS, 한국농수산식품유통공사)·한국소비자원 참가격 등 공공데이터포털(data.go.kr) 제공자료를 활용하였으며, 본 저작물은 공공누리 제1유형(출처표시) 조건에 따라 이용합니다. 제3자 권리가 포함될 수 있습니다.</div>
""" + SOURCES + FOOTER_LINKS + """
</div>
<script>
function cpDone(btn){{
  var o=btn.getAttribute('data-label')||btn.textContent;
  btn.setAttribute('data-label',o);
  btn.textContent='복사됨'; btn.classList.add('done');
  setTimeout(function(){{btn.textContent=o; btn.classList.remove('done');}},1200);
}}
function cpFallback(txt,btn){{
  var ta=document.createElement('textarea');
  ta.value=txt; ta.style.position='fixed'; ta.style.opacity='0';
  document.body.appendChild(ta); ta.select();
  try{{ document.execCommand('copy'); cpDone(btn); }}catch(e){{ btn.textContent='복사 실패'; }}
  document.body.removeChild(ta);
}}
document.addEventListener('click',function(e){{
  var btn=e.target.closest('.copy'); if(!btn) return;
  var txt=btn.getAttribute('data-copy'); if(!txt) return;
  if(navigator.clipboard&&navigator.clipboard.writeText){{
    navigator.clipboard.writeText(txt).then(function(){{cpDone(btn);}},function(){{cpFallback(txt,btn);}});
  }} else {{ cpFallback(txt,btn); }}
}});
</script>
""" + TOGGLE_JS + "</body></html>"


# ── SEO (2026-07-17) ──────────────────────────────────────────────
#  pSEO 사이트인데 meta description이 489개 중 488개 없었고 canonical·og·sitemap·robots도 전무했다.
#  검색 노출이 이 사이트의 자산인데 구글이 페이지를 알 방법도, 스니펫을 뽑을 근거도 없던 상태.
#  ⚠️ title 중복 21종도 있었다 — 메뉴 title에 브랜드명이 없어 브랜드 페이지와 겹치고
#     (예: '홍익돈까스'가 브랜드명이자 메뉴명), 서로 다른 브랜드의 '볶음밥'끼리도 겹쳤다.
#     → 메뉴 title은 반드시 "{브랜드} {메뉴}" 로 만든다.
# 배포 주소는 site_config.py 한 곳에서만 관리(= wrangler.toml의 SITE_ORIGIN)
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from site_config import SITE, clean_urls, ingredient_kinds

# 올마나마 유튜브 채널 (2026-07-22 사용자 지시로 홈에 카드 노출)
YT_URL = "https://www.youtube.com/channel/UCAkJRKVm5BYK2uffLbTypCw"
# 자사 서비스 배너 (2026-07-22). 광고가 아니라 우리 다른 사이트로 보내는 자리다.
#  여기에 추가/삭제만 하면 홈 카드가 늘고 준다. 아이콘 배경색은 grad 값으로 지정.
PROMOS = [
    {"url": "https://www.youtube.com/channel/UCAkJRKVm5BYK2uffLbTypCw",
     "icon": "▶", "title": "올마나마 채널",
     "desc": "메뉴 하나에 재료가 얼마나 들어가는지, 영상으로 짧게 보여드려요",
     "grad": "#ff0033,#e6002e"},
    {"url": "https://academy-site-renderer.dndmotor1.workers.dev/",
     "icon": "🎒", "title": "우리아이학원정보",
     "desc": "우리 아이에게 맞는 학원, 수강료까지 한눈에",
     "grad": "#3b82f6,#6366f1"},
    {"url": "https://bangpharmacy.blogspot.com/",
     "icon": "💊", "title": "방구석 약국",
     "desc": "영양제·건강식품, 뭘 언제 먹어야 할지 정리해드려요",
     "grad": "#10b981,#059669"},
]


def seo_head(title, desc, path, here=""):
    """here = 네비에서 활성화할 항목 키(dishes/categories/prices/ranking/malatang-price).
    2026-07-24 지시서 §3-1 — 현재 위치 표시. 모든 페이지가 이 함수를 거치므로 여기 한 곳이면 된다."""
    return (HEAD.format(title=esc(title), desc=esc(_clip(desc)), canon=f"{SITE}/{path}",
                        ogimg=f"{SITE}/og/share.png")
            .replace('/*THEMEVARS*/', CSS_VARS).replace('/*BODYCSS*/', BODY_CSS + TYPO_CSS).replace('/*WRAPCSS*/', WRAP_CSS + P2_CSS).replace('/*FOOTERCSS*/', FOOTER_CSS + ADFIT_CSS + CPSEARCH_CSS + SOURCES_CSS + GNAV_CSS).replace('<!--HEADSCRIPT-->', HEAD_SCRIPT)
            .replace('<!--BTN-->', BTN).replace('<!--AUTH-->', AUTH_BTN).replace('<!--SHARE-->', SHARE_BTN).replace('<!--HEAD_TAGS-->', HEAD_TAGS).replace('<!--GNAV-->', gnav(here)))

def _clip(t, n=155):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n-1] + "…"


# Recipe JSON-LD의 recipeCuisine (2026-07-23, Search Console 구조화 데이터 필드 누락 대응).
#  브랜드 카테고리 slug → 요리 계열. categories 테이블 슬러그 기준(chicken/pizza/burger/...).
CATEGORY_CUISINE = {
    "jungsik": "중식", "ilsik": "일식",
    "pizza": "양식", "burger": "양식", "cafe": "양식", "salad": "양식", "bakery": "양식",
    "chicken": "한식", "bunsik": "한식", "jokbal": "한식", "hansik": "한식",
    "gopchang": "한식", "pub": "한식",
}

# ── 구조화 데이터(JSON-LD) 2026-07-17 ─────────────────────────────
#  레시피 349개를 갖고도 JSON-LD가 0개라 구글 리치결과(재료·조리단계)를 통째로 못 받고 있었다.
#  ⚠️ Recipe 스키마에 **판매가(offers)를 넣지 않는다** — 우리는 그 메뉴를 파는 주체가 아니다.
#     남의 브랜드 메뉴에 가격 마크업을 하면 구글에 우리가 판매자인 것처럼 잡힌다.
#     원가·판매가는 본문에만 두고, 구조화 데이터는 '집에서 만드는 레시피'로만 선언한다.
#  2026-07-23: Search Console이 image·keywords·author·recipeCuisine·recipeInstructions[].url
#  누락을 지적(13건, image는 심각도 high). 메뉴별 실사진이 없어 image는 사이트 공용 이미지로
#  채운다. nutrition(칼로리)은 DB에 근거 데이터가 없어 이번에도 넣지 않는다 — 원산지 미표시와
#  같은 원칙("근거 없는 값을 지어내지 않는다"). 심각도 낮은 권고 항목이라 검색 노출엔 영향 없다.
def recipe_jsonld(m, ings, recipe_text):
    import json as _json
    # 🔴 구조화 데이터(JSON-LD)도 화면이다 — 구글이 그대로 보여준다.
    #    2026-07-27: 본문은 상표를 가렸는데 여기가 원문이라 `곰곰 떡볶이 양념`이 그대로 나갔다.
    steps = [strip_mall(x.strip()) for x in (recipe_text or "").split("\n") if x.strip()]
    if not steps: return ""
    # 🔴 2026-08-02: 재료가 0개인데 Recipe 를 내보내 `"recipeIngredient": []` 가 나갔다.
    #    구글이 「'recipeIngredient' 입력란이 누락되었습니다」로 잡는다(menu_424·426·431).
    #    재료가 없으면 그건 레시피가 아니다 — 스키마 자체를 안 내보낸다.
    if not ings: return ""
    items = []
    for it in ings:
        items.append(f'{strip_mall(it["name"])} {fmt_amt(it["amount"], it["unit"])}')
    _page_url = f'{SITE}/menu_{m["id"]}.html'
    _keywords = ", ".join(dict.fromkeys(
        [strip_mall(it["name"]) for it in ings] + [m["bname"], m["name"], "레시피", "만들기"]))
    d = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": f'{m["bname"]} {m["name"]} 따라 만들기',
        "description": f'{m["bname"]} {m["name"]}을(를) 집에서 만드는 표준 레시피와 재료비.',
        "image": [f"{SITE}/og/share.png"],
        "author": {"@type": "Organization", "name": "올마나마", "url": SITE},
        "keywords": _keywords,
        "recipeCategory": m["cname"],
        "recipeCuisine": CATEGORY_CUISINE.get(m["cslug"], "한식"),
        "recipeIngredient": items,
        "recipeInstructions": [{"@type": "HowToStep", "position": i + 1, "text": t,
                                "url": f"{_page_url}#mstep{i+1}"}
                               for i, t in enumerate(steps)],
        "recipeYield": "1인분",
        "isAccessibleForFree": True,
    }
    return ('<script type="application/ld+json">'
            + _json.dumps(d, ensure_ascii=False) + '</script>')

def ratio_cls(r):
    return "hi" if (r or 0) >= 45 else "lo"

# ── 메뉴 상세 페이지 ──
def menu_page(menu_id):
    m = cur.execute("""SELECT m.*, b.name bname, b.slug bslug, b.logo_url, b.homepage_url,
        b.frcs_cnt, b.avrg_sls_amt, b.fftc_yr,
        c.name cname, c.slug cslug FROM menus m JOIN brands b ON m.brand_id=b.id
        JOIN categories c ON b.category_id=c.id WHERE m.id=?""", (menu_id,)).fetchone()
    # 🔴 화면에 쓰는 재료명은 `display_name` 이다 (2026-07-27 대표 지시).
    #    *"재료명에는 홍보나 그런거 없이 … 그냥 치킨파우더. 절대 kg 상품명 없이 하나로 통일
    #      각메뉴별 쓰이는 상품명이 달라도"*
    #    DB `name` 은 브랜드별로 값이 다른 재료를 구분하려고 남긴다(bhc 4,575 / BBQ 2,350).
    #    실제 상품명(뫼루니 베이직 …)은 이름이 아니라 **근거 칸**에 따로 보여준다.
    ings = cur.execute("""SELECT i.ingredient_key, COALESCE(i.display_name, i.name) AS name,
        i.class, i.type, i.is_retail, mi.amount, mi.unit, mi.line_cost, mi.composition,
        mi.wholesale_cost, i.wholesale_price, i.wholesale_basis, i.manual_price, i.base_unit,
        (SELECT retail_price FROM price_history WHERE ingredient_key=i.ingredient_key AND retail_price>0 ORDER BY price_date DESC LIMIT 1) AS live_retail
        FROM menu_ingredients mi JOIN ingredients i ON mi.ingredient_key=i.ingredient_key
        WHERE mi.menu_id=? ORDER BY mi.sort_order""", (menu_id,)).fetchall()
    # 헤드라인=매장 원가(도매). 도매 계산 실패 시 소매값으로 폴백.
    _store = m["store_cost"] if m["store_cost"] else m["est_cost"]
    _sratio = m["store_ratio"] if m["store_ratio"] else m["cost_ratio"]
    diff = (m["sell_price"] or 0) - (_store or 0)
    _pct = menu_delta_pct(menu_id)
    _delta_html = f'<div style="margin-top:3px">{arrow_html(_pct)} <span style="font-size:12.5px;color:var(--muted)">{esc(DELTA_LABEL)}</span></div>' if _pct is not None else ''
    # 원산지 태그는 표시하지 않는다 (2026-07-17 사용자 지시: "원산지 표시는 우리가 할 필요 없어.
    #  수입산/국산 이것만 알면 됨" — 그건 단가를 가르는 내부 정보일 뿐 화면에 낼 값이 아니다).
    #  ⚠️ 게다가 brand_origins(31개 브랜드)는 **출처 기록이 전혀 없다.** add_origins.py는 주석에
    #  "원산지표시법 공개정보"라 써놨지만 근거 파일이 없고 하드코딩 dict다 = 미검증 자동생성 데이터.
    #  로고가 22% 틀렸던 것과 같은 계열인데, 이건 "명랑핫도그 돼지고기 국내산"처럼 실존 브랜드를
    #  대신해 사실 주장을 하는 것이라 리스크가 더 크다. 근거를 확보하기 전엔 화면에 내지 않는다.
    #  (brand_origins 테이블/데이터는 지우지 않고 남겨둠 — 나중에 검증되면 되살릴 수 있게)
    orig_map = {}

    def copy_chip(p, after=""):
        # 복사할 값은 속성으로만 넘긴다(JS 문자열에 심지 않는다) → 따옴표 이스케이프 함정 제거
        #  after: 이름과 복사버튼 **사이**에 끼울 것(양 배지). 버튼 뒤로 가면 "생닭 복사 1kg"으로 읽힌다.
        return (f'<span class="sc">{esc(p)}{after}'
                f'<button class="copy" data-copy="{esc(p)}">복사</button></span>')

    def name_with_copy(nm, amt_html=""):
        # "닭날개/다리 정육" → 닭날개(복사) / 다리 정육(복사)
        parts = [p.strip() for p in nm.split("/") if p.strip()]
        # 이름이 하나면 양을 복사버튼 앞에 끼운다("생닭(치킨용) 1kg [복사]").
        #  이름이 둘 이상이면 양이 어느 쪽 것인지 애매해지므로 묶음 뒤에 붙인다.
        if len(parts) == 1:
            return copy_chip(parts[0], amt_html)
        return '<span class="sep">/</span>'.join(copy_chip(p) for p in parts) + amt_html

    body_rows = ""
    sauces = []
    # 도매 합계는 헤드라인 store_cost와 반드시 일치해야 한다.
    #  · 도매가 없는 재료의 소매가를 대신 더하면 합계가 부풀고 헤드라인과 어긋난다(2026-07-17 허니콤보 400원 오차).
    #  · 하나라도 도매가가 없으면 합계는 '-'. compute_line_costs.py가 store_cost를 스킵하는 조건과 같은 규칙.
    somae_tot, domae_tot, domae_all = 0, 0, True
    for it in ings:
        if it["composition"]:
            sauces.append(it)
            continue
        ccls, clab = cls4(it["ingredient_key"], it["class"], it["name"], it["is_retail"])
        somae = it["line_cost"]
        domae = wholesale_line(it)
        if domae is None:
            domae_cell, domae_all = "-", False
        else:
            domae_cell = f"{domae:,}"
            domae_tot += domae
        if somae:
            somae_tot += somae
        otag = ""
        ot = KEY_ORIGIN.get(it["ingredient_key"])
        if ot and orig_map.get(ot):
            otag = f'<span class="otag">{esc(orig_map[ot])}</span>'
        # 양은 별도 칸이 아니라 **재료명 뒤에 바로 붙인다**(2026-07-25 지시).
        #  칸을 따로 두니 이름과 양이 눈으로 안 붙어 읽혔다.
        _amt = f'<span class="amt">{esc(fmt_amt(it["amount"], it["unit"]))}</span>'
        body_rows += f'''<tr><td class="c"><span class="cir {ccls}">{clab}</span></td>
<td class="nm">{name_with_copy(it["name"], _amt)}{otag}</td>
<td class="r domae">{domae_cell}</td>
<td class="r somae">{won(somae)}</td></tr>'''
    for it in sauces:
        # 배합 문구에도 상표가 섞인다 — 화면에서만 가린다(2026-07-27 대표 지시)
        header, tokens, notes = parse_comp(strip_mall(it["composition"]))
        s = it["line_cost"] or 0
        somae_tot += s
        # 소스도 도매단가가 있는 정상 재료다. '-'로 비워두면 헤드라인과 합계가 어긋난다.
        sdomae = wholesale_line(it)
        if sdomae is None:
            sdomae_cell, domae_all = "-", False
        else:
            sdomae_cell = f"{sdomae:,}"
            domae_tot += sdomae
        is_retail = bool(it["is_retail"])
        # 🔴 쓰는 양을 반드시 보여준다 (2026-07-27 대표: *"소스용량이 얼마로 잡힌건지도 모르겠고"*)
        #    소스 줄만 양이 빠져 있어서 시즈닝이 30g 인지 300g 인지 알 수 없었다.
        #    다른 재료 줄은 이름 옆에 `200g`·`144ml` 을 붙이는데 여기만 없었다.
        _samt = f'<span class="amt">{esc(fmt_amt(it["amount"], it["unit"]))}</span>'
        if is_retail:
            # 🔴 **배합이 위, 시판이 아래**다 (2026-07-27 대표 지시):
            #    *"기본적으로 소스는 집에서 만드는 배합을 적고 그아래나 조금 크게 시판을 붙여주는게 좋아"*
            #    *"없으면 소스배합 / 시판이 있으면 시판용"*
            #    전에는 시판이 위였다 — 소스는 집에서 만드는 게 기본이고 시판은 «간편하게» 쪽이다.
            buy = copy_chip(it["name"], _samt)
            chips = "".join(copy_chip(t) for t in tokens)
            # 🔴 헤더는 «<재료명> 만들기» 다 (2026-07-27 대표: *"뿌링클 스노윙 이거 아니고
            #    뿌링클 시즈닝 만들기"*). `composition` 헤더(«뿌링클 스노윙»)는 매장 메뉴 이름이라
            #    손님이 무엇을 만드는지 알 수 없다.
            hdr = esc(it["name"]) + " 만들기 " + _samt
            note_html = f'<div class="snote">{esc(" · ".join(notes))}</div>' if notes else ''
            body_rows += f'''<tr class="srcrow"><td class="c"><span class="cir ga">가</span></td>
<td class="nm"><div class="srcname">{hdr}</div><div class="schips">{chips}</div>{note_html}<div class="srcbuy"><div class="srcbuyt">시판으로 간편하게</div><div class="schips buyrow">{buy}</div></div></td>
<td class="r domae">{sdomae_cell}</td><td class="r somae">{won(it["line_cost"])}</td></tr>'''
        else:
            chips = "".join(copy_chip(t) for t in tokens)
            srcname = (esc(header) if header else '양념·소스 구성') + " " + _samt
            note_html = f'<div class="snote">{esc(" · ".join(notes))}</div>' if notes else ''
            body_rows += f'''<tr class="srcrow"><td class="c"><span class="cir ga">가</span></td>
<td class="nm"><div class="srcname">{srcname}</div><div class="schips">{chips}</div>{note_html}<div class="snote">※ 가정용 배합 예시로, 집에 있는 재료로 대체 가능합니다. 매장 실제 배합과 다를 수 있습니다.</div></td>
<td class="r domae">{sdomae_cell}</td><td class="r somae">{won(it["line_cost"])}</td></tr>'''

    dfoot = f'{domae_tot:,}원' if domae_all else '-'
    _ncount = len(ings)   # 접이식 재료 카드 요약("재료 N가지 자세히 보기")용
    rows = f'''<table class="itbl"><thead><tr><th></th><th class="l">재료</th><th class="r">도매가</th><th class="r">소매가</th></tr></thead>
<tbody>{body_rows}</tbody>
<tfoot><tr><td></td><td class="l">추정 재료비 합계</td><td class="r domae">{dfoot}</td><td class="r stot">{somae_tot:,}원</td></tr></tfoot></table>'''

    # 품목은 공식 근거로 확정됐는데 **중량만** 공개되지 않은 재료.
    #  숨기면 "감자핫도그에 감자가 없는" 표가 되어 그 자체가 틀린 정보다.
    #  g을 지어내면 '양파값 사고'의 재발이라, 있다는 사실만 밝히고 원가엔 넣지 않는다.
    unc = ""
    if "uncosted_note" in m.keys() and m["uncosted_note"]:
        _item, _why = m["uncosted_note"].split("|", 1)
        unc = (f'<div class="unc"><div class="uh">{esc(_item)} <span>— 원가에 미포함</span></div>'
               f'<div class="ub">{esc(_why)}</div></div>')

    legend = '''<div class="legend"><span><i class="cir chuk">축</i>축산물</span><span><i class="cir nong">농</i>농산물</span><span><i class="cir su">수</i>수산물</span><span><i class="cir ga">가</i>가공품</span></div>'''
    logo = logo_html(m["logo_url"], m["bname"])
    recipe = m["recipe_steps"] or ""
    recipe_html = ""
    if recipe:
        # 레시피 본문에도 상표가 박혀 있다 — `곰곰 떡볶이 양념`·`CJ 다담 김치찌개 양념`.
        #  DB 원문은 그대로 두고 화면에서만 가린다(2026-07-27 대표 지시).
        steps = [strip_mall(s) for s in recipe.split("\n") if s.strip()]
        recipe_html = '<div class="sect-t" style="margin-top:18px">집에서 따라 만들기</div>' + "".join(
            f'<div class="rstep" id="mstep{i+1}"><span class="n">{i+1}</span><span class="t">{esc(s)}</span></div>' for i, s in enumerate(steps))
    else:
        recipe_html = '<div class="sect-t" style="margin-top:18px">집에서 따라 만들기</div><p style="font-size:13px;color:var(--muted)">레시피 준비 중</p>'
    # 이 메뉴가 속한 요리(dish) — 있으면 '집에서 만들면' 카드를 그 요리 페이지로 연결한다(B-3).
    _d = cur.execute("""SELECT d.name, d.slug FROM dish_menus dm JOIN dishes d ON d.id=dm.dish_id
        WHERE dm.menu_id=? LIMIT 1""", (menu_id,)).fetchone()
    if _d:
        home_strip = (f'<a class="homestrip" href="dish_{esc(_d["slug"])}.html"><span class="hi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V21h13V9.5"/></svg></span>'
                      f'<div><div class="k">집에서 직접 만들면</div>'
                      f'<div class="v">재료비 {won(m["est_cost"])}</div></div>'
                      f'<span class="hgo">{esc(_d["name"])} 만드는 법 ›</span></a>')
    else:
        home_strip = ('<div class="homestrip"><span class="hi"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V21h13V9.5"/></svg></span><div>'
                      f'<div class="k">집에서 직접 만들면</div><div class="v">재료비 {won(m["est_cost"])}</div></div></div>')
    body = f'''<div class="crumb"><a href="index.html">홈</a> › <a href="categories.html">브랜드</a> › <a href="cat_{m["cslug"]}.html">{esc(m["cname"])}</a> › <a href="brand_{m["brand_id"]}.html">{esc(m["bname"])}</a></div>
<div class="brandhead"><a href="{esc(m["homepage_url"])}" target="_blank">{logo}</a><span class="btxt">{esc(m["bname"])}</span></div>
{fftc_inline(m)}
<h1>{esc(m["name"])} 원가</h1>
<p class="lead">{esc(m["bname"])} {esc(m["name"])}, 판매가 <b>{won(m["sell_price"])}</b>. 재료비 <b>{won(_store)}</b>으로 <b>판매가의 {_sratio}%</b>입니다.</p>
{confidence_badge(menu_id)}
<div class="mpc"><div class="mmain">
<div class="card">
  <div class="ptab">
    <div class="prow2"><span class="k">판매가</span><span class="v">{won(m["sell_price"])}</span></div>
    <div class="prow2"><span class="k">재료비 <em>{_sratio}%</em></span><span class="v">{won(_store)}{_delta_html}</span></div>
    <div class="prow2 pf2"><span class="k">수익</span><span class="v">{won(diff)}</span></div>
  </div>
  <div class="pbar2"><div class="pf" style="width:{min(_sratio, 100)}%"><span class="l">재료비</span><span class="p">{_sratio}%</span></div><div class="pr"><span class="l">수익</span><span class="p">{round(100 - _sratio, 1)}%</span></div></div>
  <div class="pwarn">이 수익은 <b>순수익이 아닙니다.</b> 여기서 임대료·인건비·배달수수료·본사 로열티를 냅니다.</div>
</div>
{WIP_NOTICE}
{home_strip}
<details class="dnote"><summary>이 숫자는 어떻게 계산했나요?</summary>
<div><b>재료비 {won(_store)}</b> = 식자재 <b>도매 공급가</b>로 계산한 추정치입니다. 실제 본사 공급가·물류비·로스는 반영되지 않아 매장 실제 원가와 다를 수 있습니다.<br>
<b>집에서 만들면 {won(m["est_cost"])}</b> = 마트·온라인몰 <b>소매가</b>로 <b>실제 쓴 양만큼만</b> 환산한 값입니다. 포장 단위로 사는 실제 장보기 비용은 이보다 큽니다.<br>
재료 소요량은 {esc(m["source"])} 등 공개 자료 기반 추정입니다.</div></details>
{ad_slot("ad-menu-top", '<div class="ad">광고 영역 (애드센스)</div>')}
{ad_slot("cp-menu", '<div class="cpbanner"><iframe src="https://coupa.ng/cn579f" width="100%" height="75" frameborder="0" scrolling="no" referrerpolicy="unsafe-url" browsingtopics></iframe></div>')}
<details class="card ingcard" open><summary>재료 {_ncount}가지 자세히 보기</summary>
<p class="lead" style="margin:6px 0 8px;font-size:12px">같은 재료라도 <b>매장은 도매가</b>, <b>집에서는 마트 소매가</b>로 삽니다.</p>
{rows}{unc}
{CPSEARCH}</details>
</div><div class="mside">{mealkit_card(menu_id)}{recipe_html}</div></div>
{next_block(_d["slug"] if _d else None, _d["name"] if _d else None, m["cslug"], m["cname"])}'''
    # 🔴 검색어 타깃(2026-07-28 네이버 실측으로 재조정).
    #    '원가'만 넣으면 월 10회짜리 말에 걸린다. **가격**이 압도적으로 많이 검색된다.
    #    그래서 `가격`을 먼저, `원가율`을 뒤에 둔다 — 두 검색어를 같이 먹는다.
    _t = f'{m["bname"]} {m["name"]} 가격 · 원가율'
    # 🔴 **`est_cost`(집에서 만들면)가 없어도 페이지는 나와야 한다**(2026-08-01 사고).
    #    한솥 6메뉴가 소매값 없는 재료를 써서 `est_cost`가 비었는데, 여기서
    #    `{None:,}` 로 `TypeError` 가 나 **생성기가 통째로 죽고 배포가 멈췄다.**
    #    도매와 소매는 별도 트랙이라 한쪽만 있는 메뉴는 앞으로도 생긴다 — 없으면 그 문장만 뺀다.
    _home = f'집에서 만들면 {m["est_cost"]:,}원. ' if m["est_cost"] else ''
    _d = (f'{m["bname"]} {m["name"]} 판매가 {m["sell_price"]:,}원, '
          f'재료비 {_store:,}원으로 원가율 {_sratio}%. ' if _store and _sratio else
          f'{m["bname"]} {m["name"]} 판매가 {m["sell_price"]:,}원. ')
    _d += _home + '재료 구성·레시피·시세 근거까지 공개.'
    return seo_head(_t, _d, f'menu_{menu_id}.html', here='categories') + body + recipe_jsonld(m, ings, recipe) + FOOT

# ── 브랜드 페이지 (메뉴 목록) ──
# ── 얇은 페이지 보강용 분석 문단 (2026-07-24) ────────────────────────────
#  brand_*(약 1,050자)·cat_*(약 1,245자)는 목록만 있고 설명이 없어 "자동생성 저품질"로 보일
#  소지가 있었다(애드센스 심사 반려 1순위 사유). 그래서 문단을 붙이되 —
#
#  🔴 원칙: **DB에서 계산되는 사실만 쓴다.** 브랜드의 사업 방식·품질·원산지처럼 우리가 검증할 수
#     없는 주장은 한 줄도 넣지 않는다. brand_origins를 화면에서 내린 것과 같은 이유다
#     (실존 브랜드를 대신해 사실 주장을 하면 그 자체가 리스크).
#  🔴 모든 수치는 우리 추정 원가율이라는 점을 문단 안에서 다시 밝힌다.
# 데이터 보정중 안내 (2026-07-24 사용자 지시) — 원가 금액이 나오는 페이지 상단에 붙인다.
#  "재료가 들어간 건 틀린 게 거의 없지만 아직 추가 안 된 재료가 있을 수 있다"는 것까지 밝힌다.
WIP_NOTICE = ('<div class="wipbox"><b>데이터 보정 중입니다.</b> 재료 시세를 DB 자동 연동으로 '
              '계속 보정하고 있어서, 지금 보이는 금액이 다시 방문했을 때와 다를 수 있습니다. '
              '표시된 재료 구성은 대체로 정확하지만, <b>아직 반영되지 않은 재료가 있을 수 있어</b> '
              '실제 원가는 이보다 조금 높을 수 있습니다.</div>')

# ── 단가 확정도 (2026-07-24 사용자 지시 "확정된 거는 확정으로 표시") ──────────
#  기준: wholesale_basis가 `coef*`면 **소매가 × 계수로 추정**한 값이고(=확정 아님),
#        그 외(마켓봄·현장 실거래 · 네이버 조사 · 미트박스 · KAMIS 일일시세)는 실제로 조사한 단가다.
#  ⚠️ 처음엔 '실거래' 문자열만으로 세려 했는데, 그 기준으로는 100%인 메뉴가 378개 중 0개라
#     배지가 어디에도 안 붙었다. coef 여부로 가르니 100%가 149개로 제대로 갈린다(2026-07-24 실측).
def cost_confidence(menu_id):
    r = cur.execute("""SELECT COUNT(*) tot,
        SUM(CASE WHEN i.wholesale_basis IS NULL OR i.wholesale_basis LIKE 'coef%' THEN 0 ELSE 1 END) src
        FROM menu_ingredients mi JOIN ingredients i ON i.ingredient_key=mi.ingredient_key
        WHERE mi.menu_id=?""", (menu_id,)).fetchone()
    tot, src = (r["tot"] or 0), (r["src"] or 0)
    if not tot:
        return None
    pct = round(src / tot * 100)
    if pct == 100:
        lv, lab, desc = "ok", "단가 확정", f"재료 {tot}개 전부 실제 조사한 단가로 계산했습니다"
    elif pct >= 80:
        lv, lab, desc = "mid", f"대부분 확정 {pct}%", f"재료 {tot}개 중 {src}개가 실제 조사한 단가입니다"
    else:
        lv, lab, desc = "wip", f"보정중 {pct}%", f"재료 {tot}개 중 {src}개만 실제 조사한 단가이고, 나머지는 추정값입니다"
    return {"pct": pct, "tot": tot, "src": src, "lv": lv, "lab": lab, "desc": desc}

def confidence_badge(menu_id):
    c = cost_confidence(menu_id)
    if not c:
        return ""
    return (f'<div class="cfd cfd-{c["lv"]}"><span class="cfdl">{esc(c["lab"])}</span>'
            f'<span class="cfdd">{esc(c["desc"])}</span></div>')

def _ratio_of(m):
    return (m["store_ratio"] or m["cost_ratio"]) or 0

def josa(word, pair="이/가"):
    """받침 유무로 조사를 고른다. '자메이카소떡적구이이(가)' 같은 표기를 없애기 위함.
    한글이 아닌 문자(숫자·영문)로 끝나면 안전하게 병기형으로 둔다."""
    a, b = pair.split("/")
    if not word:
        return a
    ch = word.strip()[-1]
    if not ("가" <= ch <= "힣"):
        return f"{a}({b})"
    return a if (ord(ch) - 0xAC00) % 28 else b

def brand_intro(b, menus):
    """브랜드 페이지 분석 문단 — 전부 계산값."""
    rs = [(_ratio_of(m), m) for m in menus if _ratio_of(m)]
    if not rs:
        return ""
    rs.sort(key=lambda x: x[0])
    lo_r, lo_m = rs[0]
    hi_r, hi_m = rs[-1]
    avg = round(sum(r for r, _ in rs) / len(rs), 1)
    # 같은 카테고리 평균과 비교 (해석이 아니라 두 계산값의 대소 비교)
    cat_avg = cur.execute("""SELECT ROUND(AVG(COALESCE(m.store_ratio,m.cost_ratio)),1) a
        FROM menus m JOIN brands br ON m.brand_id=br.id
        WHERE br.category_id=? AND br.published=1 AND COALESCE(m.store_ratio,m.cost_ratio) IS NOT NULL""",
        (b["category_id"],)).fetchone()["a"] or 0
    prices = [m["sell_price"] for _, m in rs if m["sell_price"]]
    gap = round(avg - cat_avg, 1)
    if gap > 1:
        cmp_txt = (f'같은 {esc(b["cname"])} 업종 평균 <b>{cat_avg}%</b>보다 <b>{abs(gap)}%p 높습니다</b>. '
                   f'판매가에서 재료비가 차지하는 몫이 상대적으로 큰 편이라는 뜻입니다.')
    elif gap < -1:
        cmp_txt = (f'같은 {esc(b["cname"])} 업종 평균 <b>{cat_avg}%</b>보다 <b>{abs(gap)}%p 낮습니다</b>. '
                   f'판매가 대비 재료비 비중이 상대적으로 작은 편입니다.')
    else:
        cmp_txt = f'같은 {esc(b["cname"])} 업종 평균 <b>{cat_avg}%</b>와 거의 같은 수준입니다.'
    price_txt = ""
    if prices and len(prices) > 1 and min(prices) != max(prices):
        price_txt = (f' 다루는 메뉴의 판매가는 {won(min(prices))}부터 {won(max(prices))}까지입니다.')
    elif prices:
        price_txt = f' 판매가는 {won(prices[0])}입니다.'
    menu_txt = ""
    if len(rs) > 1:
        menu_txt = (f'<p>메뉴별로 보면 <b>{esc(hi_m["name"])}</b>의 원가율이 <b>{hi_r}%</b>로 가장 높고, '
                    f'<b>{esc(lo_m["name"])}</b>{josa(lo_m["name"])} <b>{lo_r}%</b>로 가장 낮습니다. '
                    f'같은 브랜드 안에서도 어떤 재료를 얼마나 쓰느냐에 따라 '
                    f'{round(hi_r - lo_r, 1)}%p 차이가 납니다.</p>')
    fftc_txt = ""
    if b["frcs_cnt"] and b["avrg_sls_amt"]:
        fftc_txt = (f'<p>공정거래위원회 가맹사업 정보공개서({esc(b["fftc_yr"])}년 기준)에 따르면 '
                    f'{esc(b["name"])}의 가맹점은 전국 <b>{b["frcs_cnt"]:,}개</b>, '
                    f'가맹점 1곳당 연평균 매출액은 <b>{b["avrg_sls_amt"]/10000:,.1f}억원</b>입니다. '
                    f'이 매출에서 아래 재료비와 임대료·인건비·배달수수료·본사 로열티를 낸 나머지가 '
                    f'점주 몫으로 남습니다.</p>')
    return (f'<div class="bintro">'
            f'<p>{esc(b["name"])}에서 다루는 메뉴 <b>{len(rs)}개</b>의 매장 원가율은 평균 <b>{avg}%</b>로, '
            f'{cmp_txt}{price_txt}</p>'
            f'{menu_txt}{fftc_txt}'
            f'<p class="bintro-note">여기서 말하는 원가율은 <b>재료비만</b> 판매가로 나눈 값입니다. '
            f'식자재 도매 공급가를 기준으로 한 추정치라 실제 매장이 본사에서 받는 공급가와는 다를 수 있고, '
            f'임대료·인건비 같은 다른 비용은 포함되지 않았습니다.</p></div>')

def cat_intro(c, brands, rows):
    """업종 페이지 설명 — **접어둔다.** 2026-07-31 대표 지시로 다시 씀.

    🔴 무엇이 바뀌었나
       · **원가율 얘기를 뺐다.** *"치킨 업종에 관련한거 원가율 이부분은 빼고"* —
         브랜드 원가 트랙을 접기로 한 결정(`소매계산기-설계-2026-07-31.md`)과도 맞다.
         이 페이지의 주인공은 **메뉴판**이지 원가가 아니다.
       · **아코디언으로 접었다.** 글이 다섯 줄 깔려 있으면 정작 브랜드 목록이 안 보인다.
         닫힌 채로 시작하고, 궁금한 사람만 편다.

    ⛔ 숫자는 전부 DB 계산값이다. 손으로 적지 않는다.
    """
    r = cur.execute("""SELECT count(*) n, sum(o.price IS NOT NULL) np,
                              min(o.price) lo, max(o.price) hi
                       FROM brand_menu_official o JOIN brands b ON b.id=o.brand_id
                       WHERE b.category_id=? AND b.published=1""", (c["id"],)).fetchone()
    n_menu = (r["n"] or 0) if r else 0
    if not brands and not n_menu:
        return ""
    n_pr = (r["np"] or 0) if r else 0

    line1 = (f'{esc(c["name"])} 업종에서 모은 브랜드는 <b>{len(brands)}곳</b>, '
             f'메뉴는 <b>{n_menu}개</b>입니다.')
    if n_pr and r["lo"] and r["hi"] and r["lo"] != r["hi"]:
        line1 += (f' 가격이 확인된 <b>{n_pr}개</b>는 '
                  f'{won(r["lo"])}~{won(r["hi"])} 구간입니다.')

    body = (f'<p>{line1}</p>'
            f'<p>메뉴판은 <b>브랜드 공식 홈페이지 그대로</b> 옮겼습니다 — 탭 이름도, '
            f'메뉴 순서도, 같은 메뉴가 두 곳에 걸린 것도 브랜드가 그렇게 보여주기 때문입니다. '
            f'브랜드를 누르면 전체 메뉴판을 볼 수 있습니다.</p>')
    if n_pr < n_menu:
        body += (f'<p class="bintro-note">아직 가격을 확인하지 못한 메뉴가 '
                 f'<b>{n_menu - n_pr}개</b> 있습니다 — 이름과 순서는 공식 홈페이지 그대로 '
                 f'올려두고, 가격은 확인되는 대로 채웁니다.</p>')
    body += ('<p class="bintro-note">가격은 <b>홀 매장 기준</b>이며 매장·시기에 따라 '
             '다를 수 있습니다. 배달앱 가격은 배달비가 포함돼 더 높습니다.</p>')

    return (f'<details class="bintro"><summary>이 업종 메뉴판은 어떻게 모았나</summary>'
            f'<div class="bintroin">{body}</div></details>')


def board_summary(brand_id, b):
    """로고 옆에 놓는 **메뉴판 요약** — 이 페이지의 주인공은 메뉴판이니 메뉴 얘기만 한다.

    🔴 전에는 이 자리에 「원가를 어떻게 계산했나」가 있었는데, 대표 지적대로
       *"여기는 지금 메뉴판이니깐"* 원가 설명은 원가 섹션으로 내렸다(2026-07-28).
    """
    r = cur.execute("""SELECT count(*) n, sum(price IS NOT NULL) np,
                              min(price) lo, max(price) hi, max(collected_at) at
                       FROM brand_menu_official WHERE brand_id=?""", (brand_id,)).fetchone()
    if not r or not r["n"]:
        return ""
    tabs = cur.execute("""SELECT count(*) n FROM brand_menu_cat
                          WHERE brand_id=? AND parent_id IS NULL AND hidden=0""",
                       (brand_id,)).fetchone()["n"]
    org = cur.execute("""SELECT count(*) n FROM brand_menu_official
                         WHERE brand_id=? AND origin_raw IS NOT NULL""", (brand_id,)).fetchone()["n"]
    li = [f'<li><span class="k">메뉴</span><span class="v">{r["n"]}개</span></li>']
    if tabs:
        li.append(f'<li><span class="k">분류</span><span class="v">{tabs}개 탭</span></li>')
    if r["np"]:
        li.append(f'<li><span class="k">가격 확인</span><span class="v">{r["np"]}개</span></li>')
        if r["lo"] and r["hi"] and r["lo"] != r["hi"]:
            li.append(f'<li><span class="k">가격대</span>'
                      f'<span class="v">{won(r["lo"])}~{won(r["hi"])}</span></li>')
    else:
        li.append('<li><span class="k">가격</span><span class="v">확인 중</span></li>')
    if org:
        li.append(f'<li><span class="k">원산지 표기</span><span class="v">{org}개</span></li>')
    day = (r["at"] or "")[:10]
    return (f'<div class="bsum"><h2 class="bsumt">메뉴판 요약</h2><ul>{"".join(li)}</ul>'
            f'<p class="bsumn">공식 표기 기준{f" · {day} 수집" if day else ""} · '
            f'가격은 매장·시점에 따라 달라질 수 있어요</p></div>')


def menu_board(brand_id, menus):
    """브랜드 **전체 메뉴판** — 공식에서 모은 메뉴명·가격을 다 보여준다. (2026-07-27 신설)

    🔴 왜 필요한가 (대표 지시)
       *"브랜드별 들어갔을 때 메뉴는 다 보여주고, 우리가 원가로 하는 메뉴만 별도 표시"*
       지금 브랜드 페이지엔 **우리가 원가를 낸 2~8개만** 나온다. 공식 메뉴는 수십 개인데
       나머지는 사이트에 아예 없어서, 「브랜드 가격」으로 검색해 온 사람이 볼 게 없다.

    · 원가를 낸 메뉴는 **★ 표시 + 상세 링크**, 나머지는 이름·가격만(비활성)
    · 근거는 `brand_menu_official`(공식 홈페이지·자체 API·네이버 플레이스 수집분)
    · 가격은 시세라 날마다 달라진다 — 수집 시점을 함께 적는다
    """
    import re
    # 🔴 **브랜드가 보여주는 그대로** 가 1순위다 (2026-07-28 대표 지시:
    #    *"우리 입맛대로 카테고리를 설정하면 추후에 데이터 관리가 더 어려울 것 같다"*).
    #    전용 수집기가 원본 카테고리·순서를 담아둔 브랜드는 `brand_menu_cat` 을 그대로 쓴다.
    #    없는 브랜드만 표준 탭(`menu_tab`)으로 떨어진다.
    board = bmstore.board_of(cur, brand_id)
    # 🔴 배달앱(쿠팡이츠)으로 받은 가격은 **배달 안내**를 메뉴판 위에 띄운다 (2026-08-01 대표 지시:
    #    *"가격이 비쌀 수 있고, 지점에 따라 메뉴가 다를 수 있다"*). 배달비·수수료가 얹혀 매장가보다 높다.
    is_dlv = cur.execute("SELECT 1 FROM brand_menu_official WHERE brand_id=? "
                         "AND price_source='delivery_coupangeats' LIMIT 1", (brand_id,)).fetchone()
    banner = (
        '<div class="dlvnote">🛵 <b>배달앱 가격</b>입니다 — 배달비·수수료가 포함돼 '
        '<b>매장 가격보다 비쌀 수 있고</b>, <b>지역·지점에 따라 메뉴와 가격이 다를 수 있습니다.</b></div>'
    ) if is_dlv else ""
    if board:
        return banner + _board_native(brand_id, menus, board)
    # 🔴 «가격 있는 것만» 은 골격만 받은 브랜드를 통째로 빈 화면으로 만들었다(2026-07-28
    #    노모어피자·유로코피자·고피자 — 페이지는 생겨도 board 가 안 나왔다).
    #    가격 없는 메뉴도 이름은 보여준다(`won(None)` 이 「-」 로 안전하게 나온다).
    rows = cur.execute("""SELECT name, price, category, collected_at FROM brand_menu_official
                          WHERE brand_id=?
                          ORDER BY price IS NULL, price DESC""", (brand_id,)).fetchall()
    if not rows:
        return ""
    # 우리가 원가를 낸 메뉴 → 링크를 걸 수 있게 이름으로 찾는다
    def norm(s):
        """이름 비교용. **사이즈·규격 꼬리표만** 털어낸다.
        우리 `치즈 피자 L` ↔ 공식 `치즈` 처럼 꼬리표만 다른 경우가 많다.
        ⚠️ 너무 헐겁게 자르면 세트·변형까지 물어 ★ 가 부풀려진다(BBQ 3개→16개 사고)."""
        s = re.sub(r"™|®", "", s)
        s = re.sub(r"\((?:소|중|대|R|L|M)\)", "", s, flags=re.I)
        s = re.sub(r"\s+(?:피자|치킨)?\s*[LMR]$", "", s, flags=re.I)
        # 🔴 「오리지널」도 꼬리표다 (2026-07-28 대표 지시).
        #    피자스쿨은 같은 피자가 `치즈피자 오리지널`(15,900) / `치즈피자 치즈크러스트`(18,900)
        #    로 갈린다. 오리지널이 기본이고 치즈크러스트는 3,000원짜리 옵션이라,
        #    우리 원가 메뉴 `치즈피자` 는 **오리지널**에 붙는 게 맞다.
        #    ⚠️ 「치즈크러스트」는 떼지 않는다 — 떼면 한 메뉴에 둘이 붙어 원가가 부풀려진다.
        s = re.sub(r"\s*(단품|한마리|1인분|오리지널)$", "", s)
        return _re.sub(r"\s+|[·,]", "", s).lower()

    def dedup_key(s):
        """**중복 제거용** — 사이즈를 남긴다.

        🔴 `norm()` 을 중복 제거에도 쓰다가 **사이즈만 다른 메뉴가 합쳐졌다**(2026-07-28).
           청년피자 35개가 화면에 20개로, 59쌀피자 60개가 43개로 줄었다.
           피자는 L/R 가격이 다르니 **다른 메뉴**다. 잇기용(`norm`)과 목적이 다르다.
        """
        s = re.sub(r"™|®", "", s or "")
        return _re.sub(r"\s+|[·,]", "", s).lower()

    # 🔴 값까지 들고 간다 — ★ 대신 **재료비를 메뉴명 옆에 붙인다**(2026-07-28 대표 지시:
    #    *"별 표시는 삭제하고 원가를 메뉴명 옆에 부착"*). 원가는 도매 기준(`store_cost`)이다.
    mine = {}
    for m in menus:
        mine[norm(m["name"])] = (m["id"], m["store_cost"] or m["est_cost"])

    # 카테고리별로 나눠 담는다 — 메뉴가 100개 넘는 브랜드는 탭이 없으면 못 본다.
    # ⚠️ 카테고리는 217/822 만 있고, bhc 처럼 «치킨 · 시그니처 · 뿌링클» 로 여러 개가 붙기도 한다
    #    → **첫 조각만** 쓰고, 없으면 「기타」로 묶는다.
    groups, order = {}, []
    seen, n_hit = set(), 0
    for r in rows:
        nm = (r["name"] or "").strip()
        k = dedup_key(nm)                  # 중복 판정은 사이즈까지 본다
        if not nm or k in seen:
            continue
        seen.add(k)
        # 🔴 탭 이름은 **브랜드가 준 것을 그대로 쓰지 않는다** (2026-07-28 대표 지시).
        #    그러면 BBQ 「반마리」, bhc 「뿌링클유니버스」, 롯데리아 「아이스샷」 처럼
        #    브랜드마다 달라져 페이지를 옮길 때마다 다시 읽어야 한다.
        #    `menu_tab.tab_of()` 가 표준 9개로 통일한다 — 규칙은 그 파일 한 곳에만 둔다.
        ct = tab_of(nm, r["category"]) or "기타"
        # 🔴 부분 일치를 헐겁게 잡으면 **세트·변형 메뉴까지 물어** ★ 가 부풀려진다.
        #    BBQ 에서 우리 메뉴 3개인데 ★ 가 16개로 잡혔다(2026-07-27).
        #    → 이름이 정확히 같을 때만 잇는다. 꼬리표(단품/세트/™) 정도만 털어낸다.
        mid, cost = mine.get(norm(nm)) or (None, None)   # 잇기는 사이즈 꼬리표를 턴 이름으로
        if ct not in groups:
            groups[ct] = ""
            order.append(ct)
        if mid:
            n_hit += 1
            groups[ct] += _bmit(nm, won(r["price"]), mid, cost)
        else:
            groups[ct] += _bmit(nm, won(r["price"]))
    if not groups:
        return ""

    # 탭 순서도 브랜드마다 같아야 한다 — `menu_tab.TABS` 순서를 따르고, 「기타」는 맨 뒤.
    #    (원본 카테고리가 없는 브랜드에만 해당한다. 있으면 위에서 `_board_native` 로 빠진다)
    order.sort(key=lambda x: (x == "기타", tab_order(x), -len(groups[x])))
    day = (rows[0]["collected_at"] or "")[:10]
    _dlv = cur.execute("SELECT 1 FROM brand_menu_official WHERE brand_id=? "
                       "AND price_source='delivery_coupangeats' LIMIT 1", (brand_id,)).fetchone()
    _bn = ('<div class="dlvnote">🛵 <b>배달앱 가격</b>입니다 — 배달비·수수료가 포함돼 '
           '<b>매장 가격보다 비쌀 수 있고</b>, <b>지역·지점에 따라 메뉴와 가격이 다를 수 있습니다.</b></div>') if _dlv else ""
    return _bn + _board_html(order, groups, len(seen), n_hit, day)


def _size_split(rows):
    """맛 × 사이즈로만 채워진 탭이면 **사이즈 9줄 + 맛 목록** 으로 접는다.

    🔴 2026-07-28 대표 지시 — 배스킨라빈스 「아이스크림」 탭이 **297줄**이었다.
       `고무고무 블루베리 마카롱 (싱글레귤러)` … 33가지 맛 × 9사이즈이고,
       **가격은 사이즈로만 정해진다**(싱글레귤러는 어느 맛이든 3,900원).
       맛마다 9줄을 반복하면 메뉴판이 아니라 목록이 된다 —
       *"싱글레귤러~하프갤론까지는 공통이잖아 … 맛으로 줄이면 9개 사이즈 + 맛 33개"*.

    ⛔ **DB 는 건드리지 않는다.** 297행은 브랜드가 실제로 그렇게 파는 것이고,
       재수집·가격갱신이 그 단위로 들어온다. 접는 것은 **화면에서만** 한다.

    아래를 전부 만족할 때만 접는다 — 하나라도 어긋나면 원본 그대로 그린다:
      · 모든 줄이 `이름 (사이즈)` 꼴이다
      · 서로 다른 이름이 3개 이상이다   ← 「이달의 맛」(1가지 × 9사이즈)은 접지 않는다
      · 사이즈마다 모든 이름이 다 있고, 그 사이즈의 가격이 **하나로 같다**
    """
    import collections
    import re
    bases, sizes = [], collections.OrderedDict()
    for r in rows:
        m = re.match(r"^(.*\S)\s*\(([^()]+)\)$", (r["name"] or "").strip())
        if not m:
            return None
        b, s = m.group(1), m.group(2)
        if b not in bases:
            bases.append(b)
        sizes.setdefault(s, collections.OrderedDict())[b] = r
    if len(bases) < 3:
        return None
    for s, d in sizes.items():
        if len(d) != len(bases):
            return None
        if len({r["price"] for r in d.values()}) != 1:
            return None
    out = []
    for s, d in sizes.items():
        rs = list(d.values())
        r0 = rs[0]
        # 사람이 원가 메뉴를 이어둔 줄이 하나라도 있으면 그 연결을 살린다
        linked = next((r for r in rs if r["menu_id"]), None)
        out.append({"name": s, "price": r0["price"],
                    "menu_id": linked["menu_id"] if linked else None,
                    "collected_at": r0["collected_at"]})
    return out, bases


def _board_native(brand_id, menus, board):
    """**브랜드 홈페이지 그대로** 메뉴판을 그린다 — 탭 이름·탭 순서·탭 안의 진열 순서 전부 원본.

    · 중복 진열도 그대로 둔다 — 「치킨」과 「시그니처」 양쪽에 나오는 건 브랜드가 그렇게 밀고 있어서다
    · 가격이 아직 없는 메뉴도 **이름은 보여준다**(대표 지시 2026-07-28). 가격 자리는 비워 둔다
    · 정렬을 하지 않는다. `menu_cat_link.sort_order` 가 곧 브랜드가 깔아둔 순서다
    """
    import re

    def norm(s):
        s = re.sub(r"™|®", "", s or "")
        s = re.sub(r"\((?:소|중|대|R|L|M)\)", "", s, flags=re.I)
        s = re.sub(r"\s+(?:피자|치킨)?\s*[LMR]$", "", s, flags=re.I)
        # 🔴 「오리지널」도 꼬리표다 (2026-07-28 대표 지시).
        #    피자스쿨은 같은 피자가 `치즈피자 오리지널`(15,900) / `치즈피자 치즈크러스트`(18,900)
        #    로 갈린다. 오리지널이 기본이고 치즈크러스트는 3,000원짜리 옵션이라,
        #    우리 원가 메뉴 `치즈피자` 는 **오리지널**에 붙는 게 맞다.
        #    ⚠️ 「치즈크러스트」는 떼지 않는다 — 떼면 한 메뉴에 둘이 붙어 원가가 부풀려진다.
        s = re.sub(r"\s*(단품|한마리|1인분|오리지널)$", "", s)
        return _re.sub(r"\s+|[·,]", "", s).lower()

    mine = {norm(m["name"]): (m["id"], m["store_cost"] or m["est_cost"]) for m in menus}
    bycost = {m["id"]: (m["store_cost"] or m["est_cost"]) for m in menus}
    seen, hit, day = set(), set(), [""]

    def line(r):
        nm = (r["name"] or "").strip()
        if not nm:
            return ""
        seen.add(nm)
        day[0] = day[0] or (r["collected_at"] or "")[:10]
        mid, cost = mine.get(norm(nm)) or (None, None)
        if r["menu_id"]:                       # 사람이 이어둔 게 우선이다
            mid, cost = r["menu_id"], bycost.get(r["menu_id"], cost)
        # 가격이 없으면 «-» 대신 조용히 비운다. 「가격 미확인」 이라고 쓰면 그 글자가 메뉴판을 덮는다
        pr = won(r["price"]) if r["price"] else '<span class="bmx">가격 확인 중</span>'
        if mid:
            hit.add(nm)
        return _bmit(nm, pr, mid, cost)

    groups, order, counts = {}, [], {}
    for ct in board:
        nm = ct["name"]
        order.append(nm)
        # 🔴 메뉴를 **하위에만** 걸어놓는 브랜드가 있다 (2026-07-28 메가MGC·공차·이디야).
        #    그대로 두면 상위 탭이 「음료 0」 으로 나온다 — 눌러도 빈 화면이다.
        #    상위에 직접 걸린 게 없으면 **하위를 합쳐** 그 탭의 「전체」로 쓴다.
        rows = ct["rows"]
        if not rows and ct["subs"]:
            seen_r = set()
            rows = [r for s in ct["subs"] for r in s["rows"]
                    if not (r["name"] in seen_r or seen_r.add(r["name"]))]
        # 맛 × 사이즈로만 된 탭은 **사이즈 줄 + 「맛」 탭**으로 접는다(배스킨라빈스 297줄)
        flavors = None
        if not ct["subs"]:
            sp = _size_split(rows)
            if sp:
                rows, flavors = sp
        counts[nm] = len(rows)
        body = "".join(line(r) for r in _price_first(rows))
        if flavors:
            # 🔴 탭을 하나 더 만들지 않는다 (2026-07-28 대표 지시 — *"탭버튼으로 따로 해서
            #    어지럽게 해야해?"*). 가격 보러 온 사람은 사이즈 9줄만 보면 끝이고,
            #    맛은 «뭐가 있나» 훑는 것뿐이라 **접어서 같은 탭 안에** 둔다.
            body = (f'<div class="flvn">어느 맛을 골라도 <b>가격은 같아요</b> — '
                    f'아래 사이즈로 정해집니다</div>' + body
                    + f'<details class="flvd"><summary>맛 {len(flavors)}가지 보기</summary>'
                      f'<div class="flvs">'
                    + "".join(f'<span class="flv">{esc(x)}</span>' for x in flavors)
                    + '</div></details>')
        # 하위 카테고리가 있으면 **같은 방식으로 한 겹 더 나눈다** (2026-07-28 대표 지시).
        #  · 「전체」 를 맨 앞에 두어 처음엔 지금까지처럼 그 탭 전부가 보인다
        #  · 하위 안의 순서는 브랜드가 준 자리(`menu_cat_link.sort_order`) 그대로다
        #  · 한 메뉴가 하위 둘에 걸리면 양쪽에 다 나온다 — 브랜드가 그렇게 걸어둔 것이다
        if ct["subs"]:
            chips = f'<button class="bds on" data-j="0">전체 <em>{len(rows)}</em></button>'
            blocks = f'<div class="bdsb on" data-j="0">{body}</div>'
            for j, s in enumerate(ct["subs"], 1):
                chips += (f'<button class="bds" data-j="{j}">{esc(s["name"])} '
                          f'<em>{len(s["rows"])}</em></button>')
                blocks += (f'<div class="bdsb" data-j="{j}">'
                           f'{"".join(line(r) for r in _price_first(s["rows"]))}</div>')
            body = f'<div class="bdsubs">{chips}</div>{blocks}'
        groups[nm] = body
    if not groups:
        return ""
    return _board_html(order, groups, len(seen), len(hit), day[0], counts)


def _price_first(rows):
    """가격이 **있는** 메뉴를 앞으로 — 같은 그룹 안에서는 원본 순서 유지(stable). 2026-07-31 대표 지시:
       *"가격확인된거 먼저 처음으로, 가격확인해야 할거는 다 뒤로"*."""
    return sorted(rows, key=lambda r: 0 if r["price"] else 1)


# 배달앱 프로모션 배지·영업표기 — 화면에서만 뗀다(DB 원본은 그대로 둔다). 2026-07-31 대표 지시
_PROMO = _re.compile(r'\[[^\]]*(?:할인|한정|NEW|MD|공식|단골|썸머|특급|이벤트|추천|BEST|신메뉴|기간|사은|증정|무료)[^\]]*\]', _re.I)
_OPEN24 = _re.compile(r'\(\s*24시\s*\)')


def _disp_name(nm):
    """화면에 보일 이름 — 「[특급할인] …」·「(24시) …」 같은 배달 배지를 뗀다."""
    s = _PROMO.sub('', nm or '')
    s = _OPEN24.sub('', s)
    return _re.sub(r'\s{2,}', ' ', s).strip() or nm


def _bmit(nm, price_html, mid=None, cost=None):
    """메뉴판 한 줄.

    🔴 2026-07-28 대표 지시 — **★ 는 뺀다. 「원가 ›」 는 그대로 두되 메뉴명 옆에 붙인다.**
       ★ 는 무슨 뜻인지 따로 설명이 필요했고, 오른쪽 끝에 있던 「원가 ›」 는 가격과 떨어져 있어
       어느 메뉴를 누르는 건지 눈이 헤맸다. 이름 바로 옆에 두면 누를 것이 분명해진다.
    """
    kk = '<span class="bmk">원가</span>' if mid else ""
    body = f'<span class="bmn">{esc(_disp_name(nm))}</span>{kk}<span class="bmp">{price_html}</span>'
    if mid:
        return f'<a class="bmit on" href="menu_{mid}.html">{body}</a>'
    return f'<div class="bmit">{body}</div>'


def _board_html(order, groups, n_seen, n_hit, day, counts=None):
    """탭·칸 HTML 은 원본 방식과 표준 탭 방식이 **똑같이** 쓴다 — 두 벌로 만들지 않는다.

    `counts` 는 탭에 적을 개수. 하위 카테고리가 있는 탭은 같은 메뉴가 「전체」와 하위에
    두 번 그려지므로 **글자 세기로는 못 센다** — 부르는 쪽이 정확한 수를 준다.
    """
    tabs = panes = ""
    for i, ct in enumerate(order):
        cnt = (counts or {}).get(ct) or groups[ct].count('class="bmit')
        has = ' has' if 'class="bdsubs"' in groups[ct] else ''
        tabs += (f'<button class="bdt{" on" if i == 0 else ""}" data-i="{i}">'
                 f'{esc(ct)} <em>{cnt}</em></button>')
        panes += (f'<div class="bdp{has}{" on" if i == 0 else ""}" data-i="{i}">'
                  f'<h3 class="sronly">{esc(ct)} 메뉴 가격</h3>{groups[ct]}</div>')
    tabbar = f'<div class="bdtabs">{tabs}</div>' if len(order) > 1 else ""
    # 메뉴가 많으면 화면 안에서 찾기 어렵다 — 검색창을 단다(대표 지시 2026-07-28)
    srch = (f'<input class="bdq" type="search" placeholder="메뉴 검색 ({n_seen}개)" '
            f'aria-label="메뉴 검색">' if n_seen >= 12 else "")
    return f'''<div class="board">
<div class="bdh"><div class="bdht"><h2 class="bdtt">전체 메뉴판 {n_seen}개</h2>{srch}</div>
<span class="bdn">공식 표기 기준{f" · {day} 수집" if day else ""} · 가격은 매장·시점에 따라 달라질 수 있어요</span></div>
{tabbar}
<div class="bdlist">{panes}</div>
<div class="bdpg"></div>
<div class="bdf">「원가」 가 붙은 {n_hit}개는 재료를 하나씩 확인해 원가를 냈어요</div>
</div>
<script>(function(){{var b=document.currentScript.previousElementSibling;
var T=b.querySelectorAll('.bdt'),P=b.querySelectorAll('.bdp'),Q=b.querySelector('.bdq');
var PG=b.querySelector('.bdpg'),SIZE=25,page=1;
/* 🔴 「＋ 전체 보기」 를 **페이지 넘김**으로 바꿨다 (2026-07-28 대표 지시:
   *"메뉴가 길어지면 페이지로 넘기게 … 너무 길면 보기 어려워"*).
   배스킨 아이스크림 297개처럼 한 탭이 거대한 곳이 있어 한 번에 펼치면 끝없이 스크롤해야 했다.
   ⚠️ 스크립트가 안 돌면 **전부 보인다** — 아무것도 안 숨기는 게 기본이라 안전하다. */
function cur(){{var p=b.querySelector('.bdp.on');if(!p)return null;
return p.querySelector('.bdsb.on')||p;}}
function items(){{var p=cur();return p?[].slice.call(p.querySelectorAll('.bmit')):[];}}
function draw(){{
var it=items(),n=it.length,last=Math.max(1,Math.ceil(n/SIZE));
if(page>last)page=last;
it.forEach(function(e,i){{
  var lo=(page-1)*SIZE,hi=page*SIZE;
  e.style.display=(i>=lo&&i<hi)?'':'none';}});
if(!PG)return;
if(n<=SIZE){{PG.innerHTML='';PG.style.display='none';return;}}
PG.style.display='';
var h='<button class="pgb" data-p="'+(page-1)+'"'+(page<=1?' disabled':'')+'>‹</button>';
// 페이지가 많으면 현재 앞뒤만 — 1 … 4 5 6 … 12
var nums=[];
for(var k=1;k<=last;k++){{
  if(k===1||k===last||Math.abs(k-page)<=1)nums.push(k);
  else if(nums[nums.length-1]!=='…')nums.push('…');}}
nums.forEach(function(k){{
  h+=(k==='…')?'<span class="pgd">…</span>'
     :'<button class="pgb'+(k===page?' on':'')+'" data-p="'+k+'">'+k+'</button>';}});
h+='<button class="pgb" data-p="'+(page+1)+'"'+(page>=last?' disabled':'')+'>›</button>';
h+='<span class="pgn">'+n+'개 중 '+((page-1)*SIZE+1)+'~'+Math.min(page*SIZE,n)+'</span>';
PG.innerHTML=h;
PG.querySelectorAll('.pgb').forEach(function(x){{x.onclick=function(){{
  var v=+x.dataset.p;if(v<1||v>last)return;page=v;draw();
  b.scrollIntoView({{block:'start',behavior:'smooth'}});}};}});
}}
function reset(){{page=1;draw();}}
T.forEach(function(t){{t.onclick=function(){{
T.forEach(function(x){{x.classList.remove('on')}});P.forEach(function(x){{x.classList.remove('on')}});
t.classList.add('on');b.querySelector('.bdp[data-i="'+t.dataset.i+'"]').classList.add('on');
if(Q&&Q.value){{Q.value='';Q.oninput();}} else reset();}}}});
b.querySelectorAll('.bds').forEach(function(s){{s.onclick=function(){{
var p=s.closest('.bdp');
p.querySelectorAll('.bds').forEach(function(x){{x.classList.remove('on')}});
p.querySelectorAll('.bdsb').forEach(function(x){{x.classList.remove('on')}});
s.classList.add('on');p.querySelector('.bdsb[data-j="'+s.dataset.j+'"]').classList.add('on');
reset();}}}});
if(Q)Q.oninput=function(){{var v=Q.value.trim().toLowerCase();
// 검색 중엔 **탭을 넘어 전체**에서 찾고 페이지를 끄다 — 어느 탭에 있는지 모르니까
if(v){{P.forEach(function(p){{p.querySelectorAll('.bmit').forEach(function(e){{
  e.style.display=e.querySelector('.bmn').textContent.toLowerCase().indexOf(v)>=0?'':'none';}});
  p.classList.add('on');}});
  b.classList.add('searching');if(PG){{PG.innerHTML='';PG.style.display='none';}}}}
else{{P.forEach(function(p){{p.classList.toggle('on',p.dataset.i===b.querySelector('.bdt.on').dataset.i);}});
  b.classList.remove('searching');reset();}}}};
reset();}})();</script>'''


def brand_page(brand_id):
    b = cur.execute("SELECT b.*, c.name cname, c.slug cslug FROM brands b JOIN categories c ON b.category_id=c.id WHERE b.id=?", (brand_id,)).fetchone()
    menus = cur.execute("SELECT * FROM menus WHERE brand_id=? ORDER BY sort_order", (brand_id,)).fetchall()
    logo = logo_html(b["logo_url"], b["name"])
    rows = ""
    for m in menus:
        ratio = (m["store_ratio"] or m["cost_ratio"]) or 0
        rows += f'''<a class="mcard" href="menu_{m["id"]}.html"><div class="r1"><span class="mnm">{esc(m["name"])}</span><span class="mrt">{ratio}%</span></div>
<div class="msub">판매가 {won(m["sell_price"])} · 재료비 {won(m["store_cost"] or m["est_cost"])}</div>
<div class="mbar"><span style="width:{min(round(ratio), 100)}%"></span></div></a>'''
    off = f'<a class="off" href="{esc(b["homepage_url"])}" target="_blank">공식 홈페이지 ↗</a>' if b["homepage_url"] else ''
    board = menu_board(brand_id, menus)
    # 🔴 원가를 낸 메뉴가 **0개인 브랜드**가 생겼다 (2026-07-28 대표 지시:
    #    *"다 열고 원가는 비공개 메뉴명은 다 나오고 가격까지"*).
    #    한솥도시락·빽다방·투썸은 원가를 못 내지만(레토르트 원팩·커피 제외) 검색량이 월 18만이다.
    #    메뉴판은 이름·가격만 있으면 서므로 **메뉴판 전용으로 연다.**
    #    이때 «원가를 낸 메뉴 0» 이라는 빈 상자를 두면 어색하니 통째로 빼고 안내로 바꾼다.
    # 🔴 원가 카드가 552px 로 메뉴판보다 먼저 눈에 들어왔다(2026-07-28 대표 지적:
    #    *"원가 자체가 너무 커서 메뉴보다 눈에 띄여 … 메뉴판 보러온건데"*).
    #    → **접어둔다.** 제목은 남아 존재를 알리고, 원하는 사람만 펼친다.
    if menus:
        # 🔴 「원가를 어떻게 계산했나」는 **원가 섹션 안**에 둔다 (2026-07-28 대표 지시:
        #    *"여기는 지금 메뉴판이니깐"*). 전에는 페이지 위쪽 브랜드 정보에 있었다.
        costbox = (f'<details class="brcost"><summary class="brct">원가를 낸 메뉴 '
                   f'<em>{len(menus)}</em></summary>'
                   f'<div class="pcgrid2">{rows}</div>'
                   f'<div class="brhow"><h3>원가를 어떻게 계산했나</h3>'
                   f'{WIP_NOTICE}{brand_intro(b, menus)}</div></details>')
    else:
        costbox = ('<div class="brcost"><div class="brnc">이 브랜드는 <b>메뉴·가격만</b> 정리했어요.'
                   '<br>재료 원가는 아직 공개하지 않습니다.</div></div>')
    body = f'''<div class="crumb"><a href="index.html">홈</a> › <a href="categories.html">브랜드</a> › <a href="cat_{b["cslug"]}.html">{esc(b["cname"])}</a> › {esc(b["name"])}</div>
<div class="brtop">
<div class="bhead"><a href="{esc(b["homepage_url"])}" target="_blank">{logo}</a><div><h1>{esc(b["name"])} 메뉴 가격표</h1>{off}</div></div>
<details class="brfold"><summary>브랜드 정보 · 메뉴판 요약</summary>
<div class="brfoldin"><div class="brfftc">{fftc_block(b)}</div>
{board_summary(b["id"], b)}</div></details>
</div>
<div class="brmain">
{board}
{costbox}
</div>
{next_block(cat_slug=b["cslug"], cat_nm=b["cname"])}'''
    # 🔴 제목은 **사람이 실제로 검색하는 말**로 짓는다(2026-07-28 네이버 검색량 실측).
    #      "BHC메뉴" 9,370/월 · "BHC가격" 670/월  vs  "뿌링클원가" 10/월 · "BHC원가" 사실상 0
    #    전엔 '○○ 원가'로만 지어서 아무도 안 찾는 말에 걸려 있었다. 노출 28일 99회가 그 결과다.
    #    → **메뉴 · 가격 · 원가율** 세 단어를 제목에 다 넣는다. 하나가 아니라 셋을 먹는다.
    _price = [m["sell_price"] for m in menus if m["sell_price"]]
    _range = (f'{min(_price):,}~{max(_price):,}원 ' if _price else '')
    # 메뉴판 목록 — 설명문과 구조화 데이터가 **같은 목록**을 봐야 해서 여기서 한 번만 만든다
    _seen, _items = set(), []
    for r in cur.execute("""SELECT name, price FROM brand_menu_official
                            WHERE brand_id=? AND price>0 ORDER BY rowid""", (brand_id,)):
        k = _re.sub(r"\s+", "", r["name"])
        if k in _seen:
            continue
        _seen.add(k)
        _items.append((r["name"], r["price"]))
    if not _items:                       # 공식 메뉴판이 없는 브랜드는 우리 메뉴로
        _items = [(m["name"], m["sell_price"]) for m in menus if m["sell_price"]]
    # 🔴 «메뉴판» 을 앞에 붙이는 브랜드 (2026-08-01 네이버 검색광고 실측)
    #    21개 브랜드를 재보니 «브랜드+메뉴» 가 «브랜드+메뉴판» 보다 늘 컸다 — **KFC 하나만 빼고.**
    #      KFC메뉴판 34,370 > KFC메뉴 13,110   (맥도날드는 334,100 > 5,920 으로 정반대)
    #    그래서 전 브랜드에 일괄 적용하지 않고 뒤집힌 브랜드만 여기 적는다.
    #    ⚠️ 새 브랜드를 넣을 땐 `python scripts/naver_keyword.py <브랜드>메뉴 <브랜드>메뉴판` 으로 재보고 판단할 것.
    _MENUBOARD_FIRST = {"KFC"}
    _t = (f'{b["name"]} 메뉴판 · 메뉴 가격표 · 원가율' if b["name"] in _MENUBOARD_FIRST
          else f'{b["name"]} 메뉴 가격표 · 원가율')
    # 🔴 원가 메뉴가 0개인 브랜드는 설명문이 «전메뉴 가격 과 … 메뉴 0개의 판매가 대비» 로 나갔다
    #    (2026-08-01 발견 — 공개 103곳 중 **42곳**. 배스킨라빈스 479건·디저트39 472건처럼
    #     메뉴판은 꽉 찼는데 설명만 «0개» 라 검색결과 스니펫이 그대로 망가져 있었다).
    #    메뉴판만 있는 브랜드는 **메뉴판 기준으로** 설명을 짓는다 — 없는 원가를 말하지 않는다.
    _bprice = [p for (_n, p) in _items if p]
    if menus:
        _d = (f'{b["name"]} 전메뉴 가격 {_range}과 재료비 원가율을 한 번에. '
              f'메뉴 {len(menus)}개의 판매가 대비 재료비가 몇 %인지, 집에서 만들면 얼마인지 공개합니다.')
    elif _bprice:
        _d = (f'{b["name"]} 메뉴 {len(_items)}개의 가격을 '
              f'{min(_bprice):,}~{max(_bprice):,}원까지 한눈에 정리했습니다. '
              f'메뉴판 전체 가격표를 확인하세요.')
    else:
        _d = f'{b["name"]} 메뉴판. 메뉴 구성과 가격 정보를 정리하고 있습니다.'
    # 🔴 구조화 데이터 — 브랜드 페이지에 하나도 없었다(2026-07-28).
    #    가격이 붙은 목록이라 ItemList + Offer 가 맞다. 검색결과에 가격이 직접 뜰 수 있다.
    #
    #    🔴 담을 것은 **메뉴판 전체**다. 우리가 원가를 낸 메뉴(3개)만 넣으면
    #       화면엔 114개가 보이는데 구조화 데이터엔 3개뿐 — 본문과 어긋나면 무시당한다.
    #       «BHC메뉴» 9,370 을 먹으러 가는 자산이 바로 이 목록이다.
    #    (목록 `_items` 는 위 제목·설명문과 공유한다 — 둘이 어긋나면 안 된다)
    _ld = {"@context": "https://schema.org", "@type": "ItemList",
           "name": f'{b["name"]} 메뉴 가격표',
           "numberOfItems": len(_items),
           "itemListElement": [
               {"@type": "ListItem", "position": i + 1,
                "item": {"@type": "MenuItem", "name": nm,
                         "offers": {"@type": "Offer", "price": pr,
                                    "priceCurrency": "KRW"}}}
               for i, (nm, pr) in enumerate(_items)]}
    _ldjs = ('<script type="application/ld+json">'
             + json.dumps(_ld, ensure_ascii=False) + '</script>')
    return seo_head(_t, _d, f'brand_{brand_id}.html', here='categories') + body + _ldjs + FOOT

# ── 카테고리 페이지 (브랜드 목록) ──
def cat_page(cat_id):
    c = cur.execute("SELECT * FROM categories WHERE id=?", (cat_id,)).fetchone()
    # 🔴 `HAVING mc>0` 만 두면 **메뉴판만 있는 브랜드가 목록에서 빠진다**(2026-07-28).
    #    원가를 낸 메뉴(`mc`) 가 없어도 메뉴판(`bc`) 이 있으면 보여준다.
    brands = cur.execute("""SELECT b.*, COUNT(m.id) mc,
        (SELECT COUNT(*) FROM brand_menu_official o
           WHERE o.brand_id=b.id AND o.price>0) bc,
        -- 🔴 «가격이 있어야 목록에 넣는다» 는 골격만 받은 브랜드를 통째로 숨겼다 (2026-07-28).
        --    이디야 478개·자담 73개가 브랜드 페이지는 있는데 카테고리에서 링크가 안 됐다.
        (SELECT COUNT(*) FROM brand_menu_official o WHERE o.brand_id=b.id) bm
        FROM brands b LEFT JOIN menus m ON m.brand_id=b.id
        WHERE b.category_id=? AND b.published=1
        GROUP BY b.id HAVING mc>0 OR bc>0 OR bm>0 ORDER BY b.sort_order""", (cat_id,)).fetchall()
    CAT_EMOJI = {"chicken": "🍗", "pizza": "🍕", "burger": "🍔", "bunsik": "🥘", "jokbal": "🥓",
                 "hansik": "🍚", "jungsik": "🍜", "ilsik": "🍤", "cafe": "☕", "salad": "🥗",
                 "bakery": "🥐", "gopchang": "🔥", "pub": "🍻"}
    emoji = CAT_EMOJI.get(c["slug"], "🍽️")
    cards = ""
    _tops = []          # cat_intro()용 — 브랜드별 대표 메뉴 모음
    for b in brands:
        # 대표 메뉴 = 그 브랜드에서 원가율이 가장 높은(=재료를 많이 쓰는) 메뉴 하나
        top = cur.execute("""SELECT name, sell_price sp, COALESCE(store_ratio,cost_ratio) sr
            FROM menus WHERE brand_id=? AND COALESCE(store_ratio,cost_ratio) IS NOT NULL
            ORDER BY sr DESC LIMIT 1""", (b["id"],)).fetchone()
        if top:
            _tops.append({"name": top["name"], "sp": top["sp"], "sr": top["sr"], "bn": b["name"]})
        # 로고 파일이 있으면 이미지, 없으면 카테고리 이모지로 폴백(브랜드 20/87곳은 로고가 없다)
        icon = (f'<img class="be blogo" src="{esc(b["logo_url"])}" alt="{esc(b["name"])} 로고"'
                f' loading="lazy" decoding="async" width="34" height="34">'
                if b["logo_url"] else f'<span class="be">{emoji}</span>')
        prev = (f'<div class="bp">{esc(top["name"])} {won(top["sp"])} · 원가율 <b>{top["sr"]}%</b></div>'
                if top else '')
        # 🔴 원가를 낸 메뉴가 0개면 «메뉴 0개» 로 뜬다 — 메뉴판 개수를 대신 보여준다
        # 판매가를 아직 못 구한 브랜드는 **그렇다고 적는다** — 빈 값으로 두면 «없는 집» 으로 읽힌다
        if b["mc"]:
            _cnt = f'원가 {b["mc"]}개'
        elif b["bc"]:
            _cnt = f'메뉴판 {b["bc"]}개'
        else:
            _cnt = f'메뉴판 {b["bm"]}개 <span class="bwait">판매가 확인 중</span>'
        cards += (f'<a class="brow" href="brand_{b["id"]}.html">{icon}'
                  f'<div class="bmid"><div class="bn">{esc(b["name"])}</div>'
                  f'<div class="bc">{_cnt}</div>{prev}</div>'
                  f'<span class="bchev">›</span></a>')
    body = f'''<div class="crumb"><a href="index.html">홈</a> › <a href="categories.html">브랜드</a> › {esc(c["name"])}</div>
<div class="cathead"><span class="ce">{emoji}</span><div><h1>{esc(c["name"])}</h1><div class="sub">브랜드 {len(brands)}곳 · 메뉴 {sum(b["bc"] for b in brands):,}개</div></div></div>
{cat_intro(c, brands, _tops)}
<p style="font-size:13px;color:var(--muted);margin:0 0 14px">브랜드를 선택하면 메뉴별 매장 원가율을 볼 수 있어요</p>
<div class="blist">{cards}</div>'''
    _d = (f'{c["name"]} 프랜차이즈 브랜드별 메뉴 원가. 판매가 대비 재료비가 몇 %인지, '
          f'집에서 만들면 얼마인지 브랜드별로 비교합니다.')
    # 🔴 구조화 데이터 — 업종 페이지 13장에 JSON-LD 가 하나도 없었다(2026-08-01 전수검사).
    #    브랜드 목록이라 ItemList + Organization 이 맞다. 여기엔 **가격을 넣지 않는다** —
    #    한 브랜드가 메뉴 수백 개라 대표 가격 하나를 고르면 그게 곧 잘못된 정보가 된다.
    #    가격 마크업은 브랜드 페이지(ItemList + MenuItem + Offer)가 담당한다.
    _ld = {"@context": "https://schema.org", "@type": "ItemList",
           "name": f'{c["name"]} 브랜드별 메뉴 가격표',
           "numberOfItems": len(brands),
           "itemListElement": [
               {"@type": "ListItem", "position": i + 1,
                "item": {"@type": "Organization", "name": b["name"],
                         "url": f'{SITE}/brand_{b["id"]}'}}
               for i, b in enumerate(brands)]}
    _ldjs = ('<script type="application/ld+json">'
             + json.dumps(_ld, ensure_ascii=False) + '</script>')
    return seo_head(f'{c["name"]} 브랜드별 메뉴 가격 · 원가율', _d, f'cat_{c["slug"]}.html', here='categories') + body + _ldjs + FOOT

CAT_ICON = {"chicken":"🍗","pizza":"🍕","burger":"🍔","bunsik":"🥘","jokbal":"🥓",
            "hansik":"🍚","jungsik":"🍜","ilsik":"🍤","cafe":"☕","bakery":"🥐",
            "salad":"🥗","gopchang":"🔥","pub":"🍻"}

# ── 카테고리 목록 페이지 (홈에서 버튼으로 진입) ──
def categories_page():
    # 🔴 `JOIN menus` 로 두면 **원가를 낸 메뉴가 없는 업종이 목록에서 통째로 빠진다**
    #    (2026-07-28 「고기/스테이크」 신설 후 아웃백 148개가 있는데도 안 보였다).
    #    브랜드 페이지·카테고리 페이지와 **같은 기준**으로 — 메뉴판만 있어도 센다.
    # 🔴 **「메뉴 N」 은 메뉴판 개수다 — `menus`(원가 낸 메뉴) 를 세지 말 것**(2026-08-01).
    #    2026-07-28에 «업종이 목록에서 통째로 빠지는» 것만 고치고 **개수는 원가 기준 그대로** 뒀다.
    #    그래서 아웃백 148개가 있는데도 「고기/스테이크 · 메뉴 0」 으로 나갔다(일식·뷔페도 0).
    #    전체로는 254 라고 썼는데 실제 메뉴판은 7,368개 — 29배 차이였다.
    #    기준은 브랜드 줄의 「메뉴판 N개」(`bc`, price>0) 와 **같아야 한다.** 안 그러면
    #    업종 카드와 그 안의 브랜드 합이 안 맞는다.
    cats = cur.execute("""SELECT c.id,c.name,c.slug,COUNT(DISTINCT b.id) bc,
               (SELECT COUNT(*) FROM brand_menu_official o JOIN brands b2 ON b2.id=o.brand_id
                 WHERE b2.category_id=c.id AND b2.published=1 AND o.price>0) mc
        FROM categories c
        JOIN brands b ON b.category_id=c.id
        WHERE b.published=1
          AND (EXISTS(SELECT 1 FROM menus x WHERE x.brand_id=b.id)
            OR EXISTS(SELECT 1 FROM brand_menu_official o WHERE o.brand_id=b.id))
        GROUP BY c.id ORDER BY c.sort_order""").fetchall()
    tiles = ""
    for c in cats:
        ic = CAT_ICON.get(c["slug"], "🍽️")
        tiles += f'''<a class="tile" href="cat_{c["slug"]}.html"><span class="ic">{ic}</span>
<span class="tn">{esc(c["name"])}</span><span class="tc">브랜드 {c["bc"]} · 메뉴 {c["mc"]:,}</span></a>'''
    tot_b = sum(c["bc"] for c in cats); tot_m = sum(c["mc"] for c in cats)
    # 🔴 «브랜드» 가 아니라 «메뉴판» 이다(2026-07-31 대표 지시).
    #    «브랜드» 는 우리 내부 분류 이름이지 사람들이 찾는 말이 아니다.
    body = f'''<div class="crumb"><a href="index.html">홈</a> › 메뉴판</div>
<h1>메뉴판</h1>
<p style="font-size:13px;color:var(--muted);margin:4px 0 14px">{len(cats)}개 업종 · 브랜드 {tot_b}곳 · 메뉴 {tot_m:,}개</p>
<div class="tiles">{tiles}</div>'''
    return seo_head("프랜차이즈 메뉴판 · 브랜드별 메뉴 가격표",
                    f"치킨·피자·버거·분식 등 프랜차이즈 브랜드 {tot_b}곳의 전메뉴 가격표. "
                    "브랜드를 고르면 메뉴별 판매가와 재료비 원가율을 한 번에 볼 수 있습니다.",
                    "categories.html", here="categories") + body + FOOT

def home_page():
    # 🔴 `JOIN menus` 로 두면 **원가를 낸 메뉴가 없는 업종이 목록에서 통째로 빠진다**
    #    (2026-07-28 「고기/스테이크」 신설 후 아웃백 148개가 있는데도 안 보였다).
    #    브랜드 페이지·카테고리 페이지와 **같은 기준**으로 — 메뉴판만 있어도 센다.
    cats = cur.execute("""SELECT c.id,c.name,c.slug,COUNT(DISTINCT b.id) bc,
               COUNT(DISTINCT m.id) mc FROM categories c
        JOIN brands b ON b.category_id=c.id
        LEFT JOIN menus m ON m.brand_id=b.id
        WHERE b.published=1
          AND (EXISTS(SELECT 1 FROM menus x WHERE x.brand_id=b.id)
            OR EXISTS(SELECT 1 FROM brand_menu_official o WHERE o.brand_id=b.id))
        GROUP BY c.id ORDER BY c.sort_order""").fetchall()
    cat_n, brand_n = len(cats), sum(c["bc"] for c in cats)
    # ⚠️ 2026-08-01: 여기 있던 `cat_names` · `hot`/`hotrows` · `total` 을 지웠다.
    #    본문 f-string 어디에서도 안 쓰는데 매번 쿼리를 돌리고 HTML 을 만들고 있었다
    #    (홈이 «원가 리스트» 였던 시절의 잔재 — 07-31에 메뉴판으로 갈아엎으며 자리만 뺐다).
    # 시세 페이지가 담는 재료 종수 = 실제로 메뉴에 쓰이며 단가가 있는 것. prices.html 로직과 동일.
    #  ⚠️ 홈에 "47종"이 하드코딩돼 있었다(시세 페이지는 257종인데). 하드코딩 금지 — DB에서 센다.
    # 종수는 site_config.ingredient_kinds() 단일 출처 (2026-07-24) — 예전엔 여기 쿼리가 따로 있어
    #  홈 261 / 시세 352 / 소개 280여로 세 값이 달랐다.
    price_kinds = ingredient_kinds(cur)
    # ⚠️ 2026-08-01: 여기 있던 `TICKER_NAME`/`cells`/`ticker`(재료 시세 4칸 위젯) 도 지웠다.
    #    본문에 안 들어간다. 우측 «재료 시세» 미니 카드(`price_mini`)가 같은 일을 하고 있다.
    # 검색용 메뉴 인덱스 (JSON)
    allm = cur.execute("""SELECT m.id,m.name,b.name bn,COALESCE(m.store_ratio,m.cost_ratio) sr
        FROM menus m JOIN brands b ON m.brand_id=b.id WHERE b.published=1 AND m.sell_price>0 ORDER BY sr DESC""").fetchall()
    import json as _json
    idx = _json.dumps([{"i": r["id"], "n": r["name"], "b": r["bn"],
        "r": r["sr"]} for r in allm], ensure_ascii=False)
    # ── 홈 본문 = 오늘의 재료 시세 (2026-07-19 사용자 지시로 원가율 순위와 자리 교체) ──
    #  순위는 한 번 보면 끝이라 재방문 유인이 없다. 시세는 매일 아침 갱신되니 다시 올 이유가 된다.
    #  순위는 우측 사이드바에 3줄로 축소 + 모바일(사이드바 숨김)에서는 아래 링크 한 줄로 남긴다.
    _mv = cur.execute("""SELECT i.name, i.base_unit bu, i.ingredient_key k,
        (SELECT retail_price FROM price_history WHERE ingredient_key=i.ingredient_key AND retail_price>0
         ORDER BY price_date DESC LIMIT 1) p FROM ingredients i
        WHERE i.type IN ('live','live_composite')""").fetchall()
    movers = []
    for r in _mv:
        if r["k"] not in LIVE_DELTA or not r["p"]:
            continue
        c, p = LIVE_DELTA[r["k"]]
        movers.append((abs((c - p) / p * 100) if p else 0, r["name"], r["p"], r["bu"],
                       ((c - p) / p * 100) if p else 0))
    movers.sort(reverse=True)
    # ⚠️ 2026-08-01: `mrows`/`ticker_main`(본문 재료 시세 목록) 과 `_hi`/`rank_mini`(원가율 순위
    #    미니) 를 지웠다. 둘 다 본문에 안 들어간다 — 07-31에 그 자리를 «메뉴판 롤링» 과
    #    «많이 찾는 검색어» 가 가져갔는데 만드는 코드만 남아 있었다.
    # 우측 미니 시세 — «이런 것도 있다»만 보여주고 자세히는 시세 페이지로
    price_mini = "".join(
        f'<a class="rmrow" href="prices.html"><span class="n">{esc(n)}<small>{p:,}원/{esc(u)}</small></span>'
        f'<span class="r">{arrow_html(pct, 11)}</span></a>' for _, n, p, u, pct in movers[:5])
    # ⚠️ 2026-08-01: 여기 있던 **두 덩어리를 지웠다** — 둘 다 본문 f-string 이 안 쓴다.
    #    ① 프랜차이즈 가격비교(`_cmp`) — 07-22에 «홈에서 뺐다» 고 주석만 달고 **만드는 코드는
    #       그대로 뒀다.** 요리 8개마다 쿼리를 돌려 HTML 을 짓고 그대로 버리고 있었다.
    #    ② 원가 카드(`cost_cards`) — 07-31에 그 자리를 «메뉴판 롤링» 이 가져갔는데 역시 남아 있었다.
    #    자리를 뺄 때는 **만드는 코드까지** 지운다. 안 그러면 다음 사람이 «이게 왜 안 보이지» 를 판다.
    # 🔴 **홈 본문은 «원가 리스트» 가 아니라 «브랜드 메뉴판» 이다**(2026-07-31 방향 전환).
    #    메뉴판이 메인이 됐으니 홈에서도 그걸 보여준다. 원가 카드는 여기서 뺐다 —
    #    원가는 메뉴 상세·순위 페이지에서 본다.
    #    브랜드를 10초마다 하나씩 자동으로 넘긴다(사용자 지시: "랜덤으로 돌아가면서 10초정도씩").
    _bm = cur.execute("""SELECT b.id, b.name bn, b.logo_url lu, b.slug,
        (SELECT COUNT(*) FROM brand_menu_official o WHERE o.brand_id=b.id AND o.price IS NOT NULL) pn
        FROM brands b WHERE b.published=1
          AND (SELECT COUNT(*) FROM brand_menu_official o WHERE o.brand_id=b.id
               AND o.price IS NOT NULL) >= 5
        ORDER BY b.id""").fetchall()
    # 🔴 우측 «많이 찾는 검색어» — 옛 «원가율 높은 메뉴» 자리를 대신한다(2026-07-31).
    #    ⚠️ **실시간이 아니다.** 구글 서치콘솔은 2~3일 지연이라 그 사실을 화면에 반드시 적는다.
    #    데이터는 scripts/gsc_keywords.py 가 data/gsc_keywords.json 에 미리 받아둔다(2일에 한 번).
    _kwf = os.path.join(BASE, "data", "gsc_keywords.json")
    kw_mini = ""
    if os.path.exists(_kwf):
        _kw = json.loads(open(_kwf, encoding="utf-8").read())
        _rows = "".join(
            f'<div class="rmrow"><span class="k">{i+1}</span>'
            f'<span class="n">{esc(x["q"])}</span></div>'
            for i, x in enumerate(_kw.get("rows", [])[:10]))
        if _rows:
            # 🔴 «구글 서치콘솔 집계라 2~3일 지연» 같은 긴 주석은 뺐다(2026-07-31 지시).
            #    라벨의 «07.23 ~ 07.29 구글 검색 기준» 이 기간·출처를 이미 말해준다.
            kw_mini = (f'<div class="infobox rankmini"><div class="t">많이 찾는 검색어 '
                       f'<small class="ago">{esc(_kw["label"])}</small></div>{_rows}</div>')

    _boards = []
    for r in _bm:
        rows = cur.execute("""SELECT name, price, sort_order FROM brand_menu_official
            WHERE brand_id=? AND price IS NOT NULL AND price>0
            ORDER BY price""", (r["id"],)).fetchall()
        if len(rows) < 3:
            continue
        # 🔴 **가격 높은 순 5개로 뽑으면 세트·곱빼기만 나온다**(2026-08-01 수정).
        #    BBQ 가 「[NEW] 필크런치 트리플 PICK 52,000」, 교촌이 「반반윙박스 20PCS 24,000」 으로
        #    시작했다. 97곳 중 29곳이 첫 줄부터 세트였다 — 메뉴판 미리보기인데 간판이 안 보인다.
        #    → ① 가격 35~85 퍼센타일 **가운데 값대**만 남긴다(위의 세트·아래의 소스를 둘 다 자른다)
        #      ② 그 안에서 **브랜드 자기 순서**(sort_order)대로 앞 5개 — 브랜드가 먼저 거는 게 간판이다.
        #    이렇게 바꾸니 황금올리브치킨 23,000 · 뿌링클 21,000 이 첫 줄로 올라온다.
        _lo = rows[int(len(rows) * .35)]["price"]
        _hi = rows[min(len(rows) - 1, int(len(rows) * .85))]["price"]
        band = [x for x in rows if _lo <= x["price"] <= _hi] or list(rows)
        band.sort(key=lambda x: x["sort_order"] if x["sort_order"] is not None else 9999)
        _boards.append({"i": r["id"], "b": r["bn"], "lu": r["lu"] or "", "n": r["pn"],
                        "m": [[x["name"][:22], x["price"]] for x in band[:5]]})
    boards_json = json.dumps(_boards, ensure_ascii=False, separators=(",", ":"))
    # 🔴 헤더에 «브랜드 N곳» 을 쓰지 않는다(2026-08-01). 배너가 바로 위에서 «브랜드 101곳» 이라
    #    말하는데 여기는 «97곳» 이었다. 롤링판은 가격 5개 이상만 담으니 수가 다른 게 맞지만,
    #    한 화면에 다른 숫자가 둘 있으면 둘 다 못 믿는다. 개수는 배너 한 곳에서만 말한다.
    board_main = ('''<div class="rankhead"><span class="rt2">메뉴판</span></div>
<div class="bboard" id="bboard"></div>
<div class="bbdots" id="bbdots"></div>''' if _boards else '')

    # 섹션 제목 없이 배너 카드만 나열한다(2026-07-22 사용자 지시).
    cmp_main = "".join(
        f'''<a class="ytcard promo" href="{p["url"]}" target="_blank" rel="noopener">
<span class="ytico" style="background:linear-gradient(135deg,{p["grad"]})">{p["icon"]}</span>
<span class="yttx"><b>{esc(p["title"])}</b>
<small>{esc(p["desc"])}</small></span>
<span class="ytgo">→</span></a>''' for p in PROMOS)
    #  비교 카드 아래에 "크게 보기" 버튼을 두지 않는다(2026-07-19): 우측 미니 카드가 이미
    #  '원가율 순위'·'재료 시세' 두 버튼을 갖고 있어 같은 화면에 같은 링크가 두 번 나왔다.
    # 🎨 2026-08-02: 히어로가 «브랜드 존» 이다 — 캐릭터 2인 + 크림 모눈 + 검은고딕 카피.
    #    올마(핑크)가 주인공, 사장님(노랑)은 보조. 카피는 기존 문구를 그대로 둔다.
    body = f'''{CHAR_DEFS}<div class="homehero">
<div class="hchars">{CHAR % "olma"}{CHAR % "boss"}</div>
<h2>그 메뉴, 지금 얼마?<br><span>브랜드 {brand_n}곳 메뉴판을 한 곳에서</span></h2>
<div class="searchbox"><span class="si"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" style="width:16px;height:16px"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg></span><input id="sinput" type="text" placeholder="메뉴·브랜드·재료 검색" autocomplete="off"></div></div>
<div id="sresult"></div>
<div id="home">
<div class="pcgrid"><div class="pcmain">
<div class="navbtns" style="margin-top:14px">
<a class="nbtn main" href="categories.html"><span class="ni"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 9 4.5 4h15L21 9"/><path d="M4 9v11h16V9"/><path d="M9 20v-6h6v6"/></svg></span><span class="nt">메뉴판<small>치킨·피자·버거·카페 등 {cat_n}개 · 브랜드 {brand_n}곳 전메뉴 가격</small></span><span class="nc">›</span></a>
<a class="nbtn" href="dishes.html"><span class="ni"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 21h10"/><path d="M6 17h12l.6-6.2A4.5 4.5 0 1 0 12 6a4.5 4.5 0 1 0-6.6 4.8z"/></svg></span><span class="nt">레시피<small>짜장면·김치찌개·탕수육… 집에서 만들면 얼마?</small></span><span class="nc">›</span></a>
<a class="nbtn" href="prices.html"><span class="ni"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3v18h18"/><path d="m7 14 4-4 3 3 5-6"/></svg></span><span class="nt">재료 가격<small>재료 {price_kinds}종 · {PRICE_FRESH}</small></span><span class="nc">›</span></a>
</div>
{ad_slot("ad-home", '<div class="ad" style="margin:14px 0">광고 영역 (애드센스)</div>')}
{board_main}
</div><aside class="pcside">{kw_mini}
<div class="infobox rankmini"><div class="t">재료 시세 <small class="ago">{esc(PRICE_FRESH)} · {esc(DELTA_LABEL)}</small></div>{price_mini}<a class="rmall btnmore" href="prices.html">재료 {price_kinds}종 크게 보기 →</a></div></aside></div>
<div class="promowrap">{cmp_main}</div></div>
<script>
var MENUS={idx};
/* 🔴 홈 «브랜드 메뉴판» 롤링 (2026-07-31)
   · 10초마다 다음 브랜드로. 순서는 **날짜로 섞는다** — 매번 새로고침할 때마다 뒤집히면
     "아까 그거 뭐였지" 하고 못 찾는다. 하루 동안은 같은 순서로 돈다.
   · 탭을 안 보고 있을 땐 멈춘다(hidden). 백그라운드에서 헛돌 이유가 없다.
   · 점을 누르면 그 브랜드로 바로 간다. */
var BOARDS={boards_json};
(function(){{
  var el=document.getElementById('bboard'), dots=document.getElementById('bbdots');
  if(!el||!BOARDS.length) return;
  var seed=Math.floor(Date.now()/864e5), n=BOARDS.length, ord=[];
  for(var i=0;i<n;i++) ord.push(BOARDS[(i*7+seed)%n]);
  var at=0,timer=null;
  dots.innerHTML=ord.map(function(_,i){{return '<i data-i="'+i+'"></i>';}}).join('');
  function draw(){{
    var b=ord[at];
    var logo=b.lu? '<img class="bblogo" src="'+b.lu+'" alt="" loading="lazy">'
                 : '<span class="bblogo nolg">'+b.b.slice(0,1)+'</span>';
    el.innerHTML='<a href="brand_'+b.i+'.html" style="text-decoration:none;color:inherit">'+
      '<div class="bbhd">'+logo+'<span class="bbnm">'+b.b+'<small>메뉴 '+b.n+'개</small></span>'+
      '<span class="bbgo">전체 보기 ›</span></div>'+
      b.m.map(function(m){{return '<div class="bbrow"><span class="m">'+m[0]+'</span>'+
        '<span class="p">'+m[1].toLocaleString('ko-KR')+'원</span></div>';}}).join('')+'</a>';
    var ds=dots.children;
    for(var i=0;i<ds.length;i++) ds[i].className=(i===at?'on':'');
    /* 점이 많으면 지금 자리가 화면 밖으로 나간다 — 보이게 끌어온다 */
    if(ds[at]&&ds[at].scrollIntoView) ds[at].scrollIntoView({{block:'nearest',inline:'nearest'}});
  }}
  function next(){{at=(at+1)%ord.length; draw();}}
  function play(){{ if(timer) clearInterval(timer); timer=setInterval(next,10000); }}
  dots.addEventListener('click',function(e){{
    var i=e.target.getAttribute&&e.target.getAttribute('data-i');
    if(i!==null&&i!==undefined){{ at=+i; draw(); play(); }}
  }});
  document.addEventListener('visibilitychange',function(){{
    if(document.hidden){{ if(timer) clearInterval(timer); timer=null; }} else play();
  }});
  draw(); play();
}})();
/* ⚠️ 2026-08-01: 여기 있던 죽은 JS 를 지웠다 — 부를 곳이 하나도 없었다.
     · var RANK / rWon / rMode / rRender / rSheet / rInfo / rClose — 순위 목록(#ranklist)과
       바텅시트(#sheet)는 07-19·07-31에 홈에서 빠졌는데 코드만 남아 있었다.
       순위 데이터(HIGH/LOW) 를 매번 박아서 보내기까지 했다.
     · .fcbox 로테이션 — 비교 블록은 07-22에 빠졌다. boxes.length<2 로 조용히 return 하고
       있었고, 그 가드가 없었으면 #fclist 가 null 이라 그 자리에서 터졌다.
     순위·바텅시트가 다시 필요하면 ranking_page() 에 온전한 것이 있다. */
var si=document.getElementById('sinput'),sr=document.getElementById('sresult'),hm=document.getElementById('home');
si.addEventListener('input',function(){{
  var q=si.value.trim().toLowerCase();
  if(!q){{sr.innerHTML='';hm.style.display='';return;}}
  hm.style.display='none';
  var hit=MENUS.filter(function(m){{return (m.b+' '+m.n).toLowerCase().indexOf(q)>=0;}}).slice(0,40);
  // 🎨 2026-08-02: 빈 상태는 «브랜드 존» — 올마 한 컷을 붙인다(2구역 규칙에서 허용된 자리)
  if(!hit.length){{sr.innerHTML='<div id="sempty"><svg class="emptychar" viewBox="28 14 144 180" aria-hidden="true"><use href="#ch-olma"/></svg><span>검색 결과가 없어요.<br>다른 키워드로 찾아보세요.</span></div>';return;}}
  sr.innerHTML=hit.map(function(m){{
    var col=(m.r>=45)?'var(--bad)':'var(--good)';
    return '<a class="mrow" href="menu_'+m.i+'.html"><div><div class="mn">'+m.b+' '+m.n+'</div></div>'+
    '<div class="rt" style="color:'+col+'">'+(m.r!=null?m.r+'%':'')+'</div></a>';
  }}).join('');
}});
</script>'''
    # 사이트 스키마 — 홈에 JSON-LD가 아예 없었다(2026-07-24 확인).
    #  alternateName에 옛 이름 '얼마남아'를 넣는다. 도메인·브랜드를 올마나마로 바꾸기 전
    #  쓰던 이름이라, 그 이름으로 찾는 사람이 우리 사이트를 못 찾고 있었다.
    site_ld = ('<script type="application/ld+json">' + _json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "올마나마",
        "alternateName": ["얼마남아", "olmanama", "eolmanama"],
        "url": SITE + "/",
        "description": "프랜차이즈 메뉴 원가율과 집밥 재료비를 공공데이터 시세로 계산하는 정보 사이트.",
        "inLanguage": "ko-KR",
        "publisher": {"@type": "Organization", "name": "올마나마",
                      "alternateName": "얼마남아", "url": SITE + "/"},
    }, ensure_ascii=False) + "</script>")
    # 🔴 **메뉴판이 메인이다**(2026-07-31 방향 전환). 전엔 「원가율」을 앞세웠는데,
    #    검색 실측을 보니 사람들은 «원가» 로 안 찾고 **브랜드+메뉴명**으로 찾는다
    #    (교촌허니콤보 19,720 / 버거킹와퍼 18,740 vs 마라탕원가 460).
    #    그래서 제목·설명·버튼 순서를 «메뉴판·가격» 중심으로 바꿨다. 원가는 부가 정보로 내린다.
    return seo_head("프랜차이즈 메뉴판 · 가격표 한눈에",
        f"치킨·피자·버거·카페… 브랜드 {brand_n}곳 전메뉴 가격을 한 곳에서. "
        "메가커피·교촌치킨·도미노피자·맘스터치 메뉴판과 가격, 원가율까지 확인하세요.",
        "index.html") + '<h1 class="sronly">프랜차이즈 메뉴판 · 가격표</h1>' + body + site_ld + FOOT

def ranking_page():
    import json as _json
    rs = cur.execute("""SELECT m.id,b.name bn,b.logo_url lu,m.name,m.sell_price sp,m.store_cost sc,m.store_ratio sr
        FROM menus m JOIN brands b ON m.brand_id=b.id WHERE b.published=1 AND m.store_ratio IS NOT NULL
        ORDER BY m.store_ratio DESC""").fetchall()
    data = _json.dumps([{"i": r["id"], "b": r["bn"], "n": r["name"], "p": r["sp"], "c": r["sc"],
                         "r": r["sr"], "l": r["lu"] or ""} for r in rs], ensure_ascii=False)
    body = f'''<div class="crumb"><a href="index.html">홈</a> › 순위</div>
<h1>원가율 순위</h1>
<p class="sub" style="margin-bottom:12px">판매가 대비 매장 재료비 비중 (도매가 기준 추정) · 전체 {len(rs)}개</p>
<div class="seg"><button id="segHi" class="on" onclick="rMode('high')">원가율 높은 순</button><button id="segLo" onclick="rMode('low')">낮은 순</button></div>
<div class="ranklist" id="ranklist"></div>
<div class="rpager" id="rpager"></div>
<div class="sheetbg" id="sheet" onclick="rClose()"><div class="sheet" id="sheetC" onclick="event.stopPropagation()"></div></div>
<script>
var RANKALL={data},rmode='high';
function rWon(n){{return n.toLocaleString('ko-KR')+'원';}}
function rList(){{return rmode==='high'?RANKALL:RANKALL.slice().reverse();}}
function rMode(m){{rmode=m;var a=document.getElementById('segHi'),b=document.getElementById('segLo');
  if(a)a.classList.toggle('on',m==='high'); if(b)b.classList.toggle('on',m==='low'); rpage=0; rRender();}}
var RPP=10, rpage=0;   // 페이지당 10개
function rRender(){{
  var all=rList(), st=rpage*RPP;
  document.getElementById('ranklist').innerHTML=all.slice(st,st+RPP).map(function(x,i){{
    var bar=Math.max(6,Math.round(x.r)), n=st+i;
    var lg = x.l ? '<img class="rlg" src="'+x.l+'" alt="" loading="lazy" width="26" height="26">'
                 : '<span class="rlg rbg">'+x.b.slice(0,2)+'</span>';
    return '<a class="rrow" href="menu_'+x.i+'"><span class="rk">'+(n+1)+'</span>'+lg+
    '<span class="rmid"><span class="rmn">'+x.n+'</span><span class="rsub">'+x.b+' · '+rWon(x.p)+'</span>'+
    '<span class="rbar"><span style="width:'+bar+'%"></span></span></span>'+
    '<span class="rratio">'+x.r.toFixed(1)+'%</span>'+
    '<span class="rinfo" onclick="event.preventDefault();rSheet('+n+')">ⓘ</span></a>';
  }}).join('');
  var last=Math.ceil(all.length/RPP)-1;
  document.getElementById('rpager').innerHTML=
    '<button class="pbtn" '+(rpage<=0?'disabled':'')+' onclick="rGo('+(rpage-1)+')">‹ 이전</button>'+
    '<span class="pinfo">'+(rpage+1)+' / '+(last+1)+'</span>'+
    '<button class="pbtn" '+(rpage>=last?'disabled':'')+' onclick="rGo('+(rpage+1)+')">다음 ›</button>';
}}
function rGo(n){{rpage=n; rRender(); window.scrollTo({{top:0,behavior:'smooth'}});}}
function rSheet(i){{
  var x=rList()[i],bar=Math.max(6,Math.round(x.r)),rem=x.p-x.c;
  document.getElementById('sheetC').innerHTML='<div class="grip"></div><div class="sbrand">'+x.b+'</div><div class="smenu">'+x.n+'</div>'+
   '<div class="sprow"><span class="k">판매가</span><span class="v">'+rWon(x.p)+'</span></div>'+
   '<div class="sbar"><div class="f" style="width:'+bar+'%">재료비</div><div class="rr">나머지</div></div>'+
   '<div class="skv"><div class="a"><div class="k">재료비(도매) · '+x.r.toFixed(1)+'%</div><div class="v">'+rWon(x.c)+'</div></div>'+
   '<div class="b"><div class="k">나머지</div><div class="v">'+rWon(rem)+'</div></div></div>'+
   '<div class="snote">원가율은 <b style="color:var(--ink)">재료비만</b> 본 값이라, 임대료·인건비·배달수수료·본사 로열티는 빠져 있어요. 나머지에서 그 비용을 내고 매장 마진이 남습니다.</div>'+
   '<a class="sgo" href="menu_'+x.i+'.html">메뉴 상세 보기 →</a>';
  document.getElementById('sheet').classList.add('on');
}}
function rClose(){{document.getElementById('sheet').classList.remove('on');}}
rRender();
</script>'''
    return seo_head("프랜차이즈 메뉴 원가율·마진율 순위", f"프랜차이즈 인기 메뉴 {len(rs)}개를 매장 원가율(판매가 대비 재료비 비중) 높은 순·낮은 순으로 전체 순위. 도매가 기준 추정.", "ranking.html", here="ranking") + body + FOOT


def privacy_page():
    # 애드센스 승인 필수 페이지 (2026-07-19). 수집항목·목적·광고쿠키·보관파기·문의처.
    body = '''<div class="crumb"><a href="index.html">홈</a> › 개인정보처리방침</div>
<h1>개인정보처리방침</h1>
<p class="sub" style="margin-bottom:14px">시행일: 2026년 7월 19일</p>
<div class="card"><div class="sect-t">1. 수집하는 정보</div>
<p style="font-size:13.5px;line-height:1.7">올마나마는 <b>회원가입 없이 이용하는 정보 제공 사이트</b>로, 이름·연락처 등 개인정보를 직접 입력받지 않습니다. 서비스 이용 과정에서 아래 정보가 자동으로 수집될 수 있습니다.</p>
<ul style="font-size:13.5px;line-height:1.8;margin:8px 0 0 20px">
<li>쿠키(Cookie)</li><li>접속 IP, 브라우저 종류·OS, 방문 일시, 조회한 페이지 등 접속 기록</li></ul></div>
<div class="card"><div class="sect-t">2. 이용 목적</div>
<ul style="font-size:13.5px;line-height:1.8;margin:0 0 0 20px">
<li>서비스 운영·개선 및 이용 통계 분석</li>
<li>맞춤형 광고 제공(아래 3항)</li></ul></div>
<div class="card"><div class="sect-t">3. 광고 및 쿠키 (Google 애드센스·카카오 애드핏·쿠팡 파트너스)</div>
<p style="font-size:13.5px;line-height:1.7">본 사이트는 <b>Google 애드센스</b> 및 <b>카카오 애드핏(Kakao AdFit)</b> 광고를 게재할 수 있습니다. Google·카카오를 포함한 제3자 광고 사업자는 쿠키 및 광고 식별자를 사용해 이용자의 이전 방문 기록에 기반한 맞춤 광고를 제공합니다.</p>
<ul style="font-size:13.5px;line-height:1.8;margin:8px 0 0 20px">
<li>Google의 광고 쿠키 사용에 대한 자세한 내용과 차단(옵트아웃)은 <a href="https://policies.google.com/technologies/ads?hl=ko" target="_blank" rel="noopener" style="color:var(--accent)">Google 광고 정책</a> 및 <a href="https://adssettings.google.com" target="_blank" rel="noopener" style="color:var(--accent)">Google 광고 설정</a>에서 확인할 수 있습니다.</li>
<li>카카오 애드핏의 개인정보 처리에 관한 사항은 <a href="https://policy.kakao.com/kr/privacy" target="_blank" rel="noopener" style="color:var(--accent)">카카오 개인정보처리방침</a>을 참고해 주세요. 카카오는 광고 게재 과정에서 쿠키·광고 식별자 등 비식별 정보를 수집할 수 있습니다.</li>
<li>본 사이트는 <b>쿠팡 파트너스</b> 활동의 일환으로, 일부 링크를 통해 일정액의 수수료를 제공받습니다.</li>
<li>이용자는 브라우저 설정에서 쿠키 저장을 거부하거나 삭제할 수 있습니다. 이 경우 일부 기능·광고가 제한될 수 있습니다.</li></ul></div>
<div class="card"><div class="sect-t">4. 보관 및 파기</div>
<p style="font-size:13.5px;line-height:1.7">자동 수집되는 접속 기록은 호스팅 사업자(Cloudflare)의 정책에 따라 일정 기간 보관 후 자동 파기되며, 본 사이트가 별도의 데이터베이스에 개인정보를 저장하지 않습니다.</p></div>
<div class="card"><div class="sect-t">5. 운영자 및 문의처</div>
<p style="font-size:13.5px;line-height:1.8">운영자: <b>베이직씨엔엠</b><br>문의: <a href="mailto:dndmotor1@gmail.com" style="color:var(--accent)">dndmotor1@gmail.com</a><br>방침이 변경되는 경우 본 페이지를 통해 고지합니다.</p></div>'''
    return seo_head("개인정보처리방침", "올마나마 개인정보처리방침 — 수집 항목, 이용 목적, 광고·쿠키 고지, 보관·파기, 문의처.", "privacy.html") + body + FOOT


def terms_page():
    # 카카오 애드핏 매체 심사 대비 이용약관 (2026-07-19). privacy_page와 같은 레이아웃·톤 재사용.
    #  ★ 2항(면책)이 핵심 — 우리 수치는 전부 추정치라 사업 판단 근거로 쓰였을 때를 명시적으로 배제.
    body = '''<div class="crumb"><a href="index.html">홈</a> › 이용약관</div>
<h1>이용약관</h1>
<p class="sub" style="margin-bottom:14px">시행일: 2026년 7월 19일</p>
<div class="card"><div class="sect-t">1. 서비스 개요</div>
<p style="font-size:13.5px;line-height:1.7">올마나마(olmanama.com, 이하 "본 사이트")는 프랜차이즈 메뉴의 <b>원가율 추정 정보</b>와 <b>식재료 시세 정보</b>를 제공하는 정보 제공 서비스입니다. 회원가입 없이 누구나 무료로 이용할 수 있으며, 이용자가 본 사이트에 접속하는 시점부터 본 약관이 적용됩니다.</p>
<p style="font-size:13.5px;line-height:1.7;margin-top:8px">본 사이트는 상품·용역을 판매하거나 중개하지 않으며, 어떠한 브랜드·가맹본부와도 제휴·후원 관계가 없습니다.</p></div>
<div class="card"><div class="sect-t">2. 정보의 성격과 면책</div>
<p style="font-size:13.5px;line-height:1.7">본 사이트에 표시되는 <b>모든 원가·원가율·재료비·시세는 공공데이터에 기반한 추정치</b>이며, 실제 매장의 원가·공급가·수익과는 <b>다를 수 있습니다</b>.</p>
<ul style="font-size:13.5px;line-height:1.8;margin:8px 0 0 20px">
<li>식자재 도매 공급가는 공개 시세로부터 산출한 <b>추정값</b>이며, 실제 가맹본부 공급가와 일치하지 않습니다.</li>
<li>원가율은 <b>재료비만</b>을 기준으로 하며 임대료·인건비·배달수수료·본사 로열티·부가세 등은 포함되지 않습니다.</li>
<li>재료 소요량(그램 등)은 공개 레시피·원가분석 자료에 근거한 <b>추정치</b>입니다.</li>
<li>원본 공공데이터의 오류·지연·중단이 그대로 반영될 수 있습니다.</li></ul>
<p style="font-size:13.5px;line-height:1.7;margin-top:10px">따라서 본 사이트의 정보는 <b>참고용</b>이며, 창업·투자·가격 결정 등 <b>사업상 의사결정의 근거로 사용해서는 안 됩니다</b>. 이용자가 본 사이트의 정보를 신뢰하여 내린 판단 및 그로 인해 발생한 직접·간접의 손해에 대하여 본 사이트는 <b>어떠한 책임도 지지 않습니다</b>.</p></div>
<div class="card"><div class="sect-t">3. 데이터 출처 및 갱신</div>
<ul style="font-size:13.5px;line-height:1.8;margin:0 0 0 20px">
<li>농산물유통정보 <b>KAMIS</b>(한국농수산식품유통공사) — 농산물 일일 시세</li>
<li><b>축산물품질평가원</b> — 축산물 시세</li>
<li>한국소비자원 <b>참가격</b> — 가공식품 소비자가, <b>주간</b> 조사분 반영</li>
<li><b>공정거래위원회</b> 가맹사업 정보공개서 — 가맹점 수·평균 매출</li></ul>
<p style="font-size:13.5px;line-height:1.7;margin-top:8px">시세 정보는 공공데이터를 수집해 반영하며, <b>화면에 표시된 조사일 기준</b>입니다. 수집 주기와 원본 데이터 사정에 따라 최신 영업일이 아닌 확정치가 표시될 수 있습니다.</p>
<p style="font-size:12px;color:var(--muted);line-height:1.7;margin-top:8px">공공데이터포털(data.go.kr) 제공자료를 공공누리 제1유형(출처표시) 조건에 따라 이용합니다.</p></div>
<div class="card"><div class="sect-t">4. 광고 게재</div>
<p style="font-size:13.5px;line-height:1.7">본 사이트는 서비스 운영을 위해 <b>제3자 광고</b>를 게재하며, 이용자의 화면에 광고가 노출될 수 있습니다. 광고의 내용과 광고주가 제공하는 상품·용역에 관한 책임은 <b>해당 광고주에게 있으며</b>, 본 사이트는 이에 대해 보증하거나 책임지지 않습니다.</p>
<p style="font-size:13.5px;line-height:1.7;margin-top:8px">광고 및 쿠키에 관한 자세한 사항은 <a href="privacy.html" style="color:var(--accent);font-weight:700">개인정보처리방침</a>을 참고해 주시기 바랍니다.</p></div>
<div class="card"><div class="sect-t">5. 콘텐츠 저작권</div>
<p style="font-size:13.5px;line-height:1.7">본 사이트가 작성·가공한 원가 분석, 재료 구성, 화면 구성 및 디자인에 대한 권리는 운영자에게 있습니다. 사전 서면 동의 없이 아래 행위를 금지합니다.</p>
<ul style="font-size:13.5px;line-height:1.8;margin:8px 0 0 20px">
<li>자동화된 수단(크롤러·스크래퍼·봇 등)을 이용한 <b>대량 수집</b></li>
<li>콘텐츠의 <b>복제·전재·재배포</b> 및 2차적 저작물 작성</li>
<li>상업적 목적의 데이터베이스 구축·판매</li>
<li>서버에 과도한 부하를 유발하는 반복 요청</li></ul>
<p style="font-size:12px;color:var(--muted);line-height:1.7;margin-top:8px">각 브랜드명·상표·로고는 해당 권리자의 자산이며, 본 사이트는 정보 제공 목적의 인용 범위에서만 이를 표시합니다. 개인적·비상업적 목적의 인용 시에는 출처를 밝혀 주시기 바랍니다.</p></div>
<div class="card"><div class="sect-t">6. 약관 변경 및 문의</div>
<p style="font-size:13.5px;line-height:1.9">운영자: <b>베이직씨엔엠</b><br>
문의: <a href="mailto:dndmotor1@gmail.com" style="color:var(--accent);font-weight:700">dndmotor1@gmail.com</a><br>
<span style="font-size:12.5px;color:var(--muted)">본 약관은 관련 법령 또는 서비스 변경에 따라 개정될 수 있으며, 개정 시 본 페이지를 통해 시행일과 함께 고지합니다.</span></p>
<p style="font-size:13.5px;line-height:1.7;margin-top:8px">시행일: <b>2026년 7월 19일</b></p></div>'''
    return seo_head("이용약관", "올마나마 이용약관 — 서비스 개요, 원가·시세 추정치 면책, 공공데이터 출처와 갱신 주기, 광고 게재, 저작권, 문의처.", "terms.html") + body + FOOT


def about_page():
    # 소개 + 문의 (2026-07-19). 서비스 설명·데이터 출처·운영자·연락처.
    #  2026-07-24: 재료 종수를 하드코딩("280여 종")에서 계산값으로 바꾸며 f-string으로 전환.
    body = f'''<div class="crumb"><a href="index.html">홈</a> › 소개</div>
<h1>올마나마 소개</h1>
<div class="card"><div class="sect-t">올마나마는</div>
<p style="font-size:13.5px;line-height:1.75">프랜차이즈 인기 메뉴의 <b>원가율</b>과 <b>집에서 만들 때 재료비</b>를 알려주는 정보 사이트입니다. "내가 시킨 그 메뉴, 원가가 얼마일까?"라는 궁금증에서 출발했습니다.</p>
<p style="font-size:12.5px;line-height:1.7;color:var(--muted);margin-top:6px">2026년 7월까지는 <b>얼마남아</b>라는 이름으로 운영했습니다. 도메인(olmanama.com)과 이름을 맞추면서 <b>올마나마</b>로 바꿨고, 서비스 내용은 그대로입니다.</p>
<ul style="font-size:13.5px;line-height:1.8;margin:8px 0 0 20px">
<li><b>매장 원가율</b> — 판매가 대비 재료비(식자재 도매 공급가 <b>추정치</b>) 비중. 임대료·인건비·배달수수료·본사 로열티는 포함되지 않습니다.</li>
<li><b>집에서 만들면</b> — 같은 메뉴를 집에서 만들 때 드는 재료비(대형마트·온라인몰 소매가 기준).</li>
<li><b>재료 시세</b> — 원가 계산에 실제 쓰는 재료 {ingredient_kinds(cur)}종의 단가와 등락.</li></ul></div>
<div class="card"><div class="sect-t">비싸다고 말하려는 게 아닙니다</div>
<p style="font-size:13.5px;line-height:1.75"><b>식당은 재료를 대량으로 삽니다.</b> 그래서 단가가 낮은 게 당연합니다. 마트 소포장 값과 비교하면 안 됩니다. 폭리가 아니라 유통 구조입니다.</p>
<p style="font-size:13.5px;line-height:1.75;margin-top:8px">저희 숫자에는 <b>인건비·임대료·배달수수료·포장재가 빠져 있습니다.</b> 실제로 남는 돈은 이보다 훨씬 적습니다.</p>
<p style="font-size:13.5px;line-height:1.75;margin-top:8px"><b>집에서 따라 만들라는 뜻도 아닙니다.</b> 한 끼 먹자고 말통을 사면 오히려 손해입니다.</p>
<p style="font-size:13.5px;line-height:1.75;margin-top:10px">내가 먹는 게 뭘로 이루어졌는지 <b>숫자로 보여드릴 뿐</b>이고, 판단은 보시는 분 몫입니다.</p>
<p style="font-size:12.5px;color:var(--muted);margin-top:8px">※ 재료값은 시세라 날마다 달라집니다.</p></div>
<div class="card"><div class="sect-t">데이터 출처</div>
<ul style="font-size:13.5px;line-height:1.8;margin:0 0 0 20px">
<li>농산물유통정보 <b>KAMIS</b>(한국농수산식품유통공사) — 농산물 일일 시세</li>
<li><b>축산물품질평가원</b> — 축산물 시세</li>
<li>한국소비자원 <b>참가격</b> — 가공식품 소비자가(주간 조사)</li>
<li><b>공정거래위원회</b> 가맹사업 정보공개서 — 가맹점 수·평균 매출</li>
<li>재료 소요량은 공개 레시피·유튜버 원가분석 기반 <b>추정치</b>입니다.</li></ul>
<p style="font-size:12px;color:var(--muted);line-height:1.7;margin-top:8px">공공데이터포털(data.go.kr) 제공자료를 공공누리 제1유형(출처표시) 조건에 따라 이용합니다. 본 사이트의 모든 수치는 추정치로, 실제 매장의 원가·공급가와 다를 수 있습니다. 본 사이트는 각 브랜드와 무관하며, 상표·로고는 각 사의 자산입니다.</p></div>
<div class="card" id="contact"><div class="sect-t">운영자 · 문의</div>
<p style="font-size:13.5px;line-height:1.9">운영자: <b>베이직씨엔엠</b><br>
문의·제보·정정 요청: <a href="mailto:dndmotor1@gmail.com" style="color:var(--accent);font-weight:700">dndmotor1@gmail.com</a><br>
<span style="font-size:12.5px;color:var(--muted)">잘못된 가격·재료 정보를 알려주시면 확인 후 바로잡겠습니다.</span></p></div>'''
    return seo_head("소개·문의", "올마나마 — 프랜차이즈 메뉴 원가율과 집밥 재료비 정보 사이트. 데이터 출처와 운영자·문의처 안내.", "about.html") + body + FOOT


# 생성: 메뉴 전부 + 브랜드 전부 + 카테고리 전부
def w(fn, content):
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write(clean_urls(content))

# id를 먼저 리스트로 확보 (커서 재사용 충돌 방지)
menu_ids = [r["id"] for r in cur.execute(
    "SELECT m.id FROM menus m JOIN brands b ON b.id=m.brand_id WHERE b.published=1").fetchall()]
# 🔴 전에는 `menus`(우리가 원가를 낸 메뉴)와 **조인**해서, 원가가 0개면 페이지가
#    아예 안 만들어졌다 — 피자마루·59쌀피자가 메뉴판 60개를 넣고도 라이브 404 였다(2026-07-28).
#    **메뉴판(`brand_menu_official`)만 있어도** 페이지를 만든다. 메뉴판이 곧 콘텐츠다.
#    🔴 «가격이 있어야 한다»(`price>0`)도 좁았다 — 자담치킨은 카테고리 4탭·메뉴 73개를 받았는데
#       홈페이지가 가격을 공개하지 않아 **페이지가 통째로 안 만들어졌다**(2026-07-28).
#       수집은 «골격 먼저, 가격은 나중에 에뮬로» 두 단계다. 골격만 있어도 메뉴판은 선다.
brand_ids = [r["id"] for r in cur.execute("""
    SELECT b.id FROM brands b WHERE b.published=1
      AND (EXISTS(SELECT 1 FROM menus m WHERE m.brand_id=b.id)
        OR EXISTS(SELECT 1 FROM brand_menu_official o
                  WHERE o.brand_id=b.id AND o.price>0)
        OR EXISTS(SELECT 1 FROM brand_menu_cat c WHERE c.brand_id=b.id)
        -- 🔴 탭도 없이 골격만 있는 브랜드가 있다(2026-07-28 노모어피자·고피자·유로코피자).
        --    카테고리 없이 brand_menu_official 만 채워진 경우도 페이지는 서야 한다 —
        --    표준 탭 폴백으로 그려진다. 메뉴가 하나라도 있으면 만든다.
        OR EXISTS(SELECT 1 FROM brand_menu_official o WHERE o.brand_id=b.id))""").fetchall()]
cat_rows = [(r["id"], r["slug"]) for r in cur.execute("SELECT id, slug FROM categories").fetchall()]

for mid in menu_ids:
    w(f"menu_{mid}.html", menu_page(mid))
for bid in brand_ids:
    w(f"brand_{bid}.html", brand_page(bid))
for cid, cslug in cat_rows:
    w(f"cat_{cslug}.html", cat_page(cid))

# 홈 화면을 index로
w("index.html", home_page())
w("categories.html", categories_page())
w("ranking.html", ranking_page())
w("privacy.html", privacy_page())
w("terms.html", terms_page())
w("about.html", about_page())
# ❌ sample_menu.html 은 만들지 않는다 (2026-07-17 제거)
#  개발 초기에 '대표 메뉴 보존'용으로 menu_6(허니콤보)을 통째로 복사해 두던 파일인데,
#  ① 어디서도 링크되지 않는 고아 파일이고 ② menu_6.html과 바이트 단위로 동일해
#  검색엔진에 **중복 콘텐츠**로 잡힌다. pSEO 사이트에서 중복 콘텐츠는 순위에 해가 된다.
#  샘플이 필요하면 menu_6.html을 직접 열면 된다.
print("생성 완료:", len(os.listdir(OUT)), "개 파일 →", OUT)
con.close()
