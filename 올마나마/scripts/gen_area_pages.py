# -*- coding: utf-8 -*-
"""지역별 **식자재 배송업체 + 도매 시세** 페이지 18장. 2026-07-28

    python scripts/gen_area_pages.py            # _preview/area_*.html
    python scripts/gen_area_pages.py --refresh  # 업체 목록을 식봄에서 다시 받고 생성

왜 18장인가 (네이버 검색광고 키워드도구 실측 · `메뉴판-SEO-뼈대-2026-07-28.md`)
------------------------------------------------------------------
    식자재마트 54,090 / 부산식자재마트 1,190 / 대구식자재마트 1,060
    인천 990 / 대전 980            ← 광역시 하나에 월 1,000쯤
    부산정육도매 10 / 대구채소도매 10  ← **지역 × 품목은 곱하지 않는다**

  · **시·도 17 + 「그 외(택배배송)」 1 = 18장.** 그 이상은 만들지 않는다
  · **시·군·구 247장 금지** — 검색량 0에 가깝고, 내용 비슷한 페이지 대량 생성은
    저품질로 잡힌다. 지금 애드센스 심사 중이라 특히 위험하다
  · 품목은 **페이지를 쪼개지 말고 h2 로 나눈다**(축산/수산/농산/가공).
    그래야 «부산 식자재마트» 로 들어온 사람이 정육까지 같이 본다
  · 품목 단독 페이지도 필요 없다 — 재료 페이지가 이미 먹고 있다
    (`계란 가격` 16,320 vs `계란도매` 840, 20배)

⛔ **가격은 «전국 기준» 이라고 반드시 밝힌다.** 식봄은 비로그인 상태에서 전국 통합 목록을
   주고(2026-07-28 실측: 서울·대전·대구·제주 결과 동일), 지역별로 갈리지 않는다.
   갈라내려면 로그인 세션이 필요한데 세션이 끊기면 수집이 통째로 멈춘다 — 얻는 것보다 잃는 게 크다.
   **지역마다 다른 건 «업체 목록»** 이고, 그것만으로 페이지 내용은 충분히 갈라진다
   (실측: 서울 40곳 · 부산 17곳 중 13곳이 부산에만 · 제주 1곳).

⛔ **«쿠팡»·«로켓배송» 을 제목·설명에 쓰지 않는다** — 파트너스 약관상 상표 사용 제한.
   본문에서 사실 서술은 괜찮지만 title·description·h1 에는 넣지 않는다.
"""
import io
import json
import re
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import gen_preview_html as G                                    # noqa: E402
from ingredient_cat import cat_of                               # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "_preview")
RES = os.path.join(BASE, "data", "research", "foodspring")
F_AREA = os.path.join(RES, "_지역.json")
F_SELLER = os.path.join(RES, "_지역별업체.json")

# 검색어는 «부산식자재마트» 처럼 «시» 를 뗀 형태로 친다
SHORT = {"서울시": "서울", "부산시": "부산", "대구시": "대구", "인천시": "인천",
         "대전시": "대전", "울산시": "울산", "세종시": "세종", "경기도": "경기",
         "강원도": "강원", "충청북도": "충북", "충청남도": "충남",
         "경상북도": "경북", "경상남도": "경남", "전라북도": "전북",
         "전남광주통합특별시": "광주전남", "제주도": "제주",
         "그 외(택배배송)": "택배배송"}
SLUG = {"서울시": "seoul", "부산시": "busan", "대구시": "daegu", "인천시": "incheon",
        "대전시": "daejeon", "울산시": "ulsan", "세종시": "sejong", "경기도": "gyeonggi",
        "강원도": "gangwon", "충청북도": "chungbuk", "충청남도": "chungnam",
        "경상북도": "gyeongbuk", "경상남도": "gyeongnam", "전라북도": "jeonbuk",
        "전남광주통합특별시": "gwangju", "제주도": "jeju", "그 외(택배배송)": "taekbae"}
CAT_ORDER = ("축산", "수산", "농산", "가공")
CAT_LABEL = {"축산": "정육 · 육류", "수산": "수산물", "농산": "채소 · 곡물",
             "가공": "가공식품 · 소스"}

CSS = """
.arhd{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;margin-bottom:16px}
.arhd h1{font-size:21px;font-weight:900;margin:0 0 6px}
.arhd .sub{font-size:13px;color:var(--muted);line-height:1.6}
.arnote{display:flex;gap:8px;align-items:flex-start;margin-top:12px;padding:10px 12px;
        border:1px solid var(--line);border-radius:11px;font-size:12.5px;color:var(--muted);line-height:1.6}
.vlist{display:grid;grid-template-columns:1fr;gap:0;border:1px solid var(--line);border-radius:14px;background:var(--card);overflow:hidden;margin-bottom:8px}
@media(min-width:700px){.vlist{grid-template-columns:1fr 1fr}
 .vrow:nth-child(odd){border-right:1px solid var(--line)}}
.vrow{display:flex;gap:9px;align-items:baseline;padding:8px 13px;border-bottom:1px solid var(--line)}
.vrow:last-child{border-bottom:0}
.vmeta{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:2px}
.vtag{flex:none;font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:999px;
      background:var(--bg);border:1px solid var(--line);color:var(--muted)}
.vtag.nat{background:var(--accent);border-color:var(--accent);color:#fff}
.vmid{min-width:0}
.vnm{font-size:13.5px;font-weight:800;line-height:1.35}
.vin{font-size:12px;color:var(--muted);line-height:1.55;margin-top:2px;
     display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.vcat{font-size:11.5px;color:var(--muted)}
.vfx{font-size:11px;color:#5B4A40;background:#F2E6DE;border-radius:999px;padding:2px 9px}
.arh2{font-size:16px;font-weight:900;margin:24px 0 9px}
.arh2 em{font-style:normal;color:var(--muted);font-size:12.5px;font-weight:700;margin-left:6px}
.ptbl{width:100%;border-collapse:collapse;font-size:13px;background:var(--card);
      border:1px solid var(--line);border-radius:13px;overflow:hidden}
.ptbl th,.ptbl td{padding:8px 13px;border-bottom:1px solid var(--line);text-align:left}
.ptbl th{font-size:11.5px;color:var(--muted);font-weight:800;background:var(--bg)}
.ptbl td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ptbl tr:last-child td{border-bottom:0}
.ptbl a{color:inherit;text-decoration:none;font-weight:700}
.arlinks{display:flex;flex-wrap:wrap;gap:7px;margin:18px 0 6px}
.pgo{display:flex;align-items:center;gap:10px;margin:14px 0 4px;padding:14px 18px;
     background:var(--accent);border-radius:14px;color:#fff;text-decoration:none;
     font-weight:900;font-size:15px;box-shadow:0 2px 10px rgba(224,85,117,.28)}
.pgo small{display:block;font-weight:700;font-size:12px;opacity:.9;margin-top:2px}
.pgo .ar{margin-left:auto;font-size:18px}
.arlinks a{font-size:12.5px;font-weight:700;padding:6px 11px;border:1px solid var(--line);
           border-radius:999px;background:var(--card);color:var(--ink);text-decoration:none}
"""


def load_sellers(refresh=False):
    if refresh or not os.path.exists(F_SELLER):
        import foodspring_area as A
        tree = json.load(io.open(F_AREA, encoding="utf-8"))
        got = {}
        for s in tree:
            gid = "area_%s" % s["id"]
            r = A.sellers(gid, first=40)
            if (r.get("error") or not r.get("list")) and s["children"]:
                r = A.sellers("area_%s" % s["children"][0]["id"], first=40)
            if r.get("error"):
                print("  ! %s %s" % (s["name"], r["error"][:60]))
                continue
            got[s["name"]] = r["list"]
            print("  %-16s 업체 %d곳" % (s["name"], len(r["list"])), flush=True)
        io.open(F_SELLER, "w", encoding="utf-8").write(
            json.dumps(got, ensure_ascii=False, indent=1))
        return got
    raw = json.load(io.open(F_SELLER, encoding="utf-8"))
    # 옛 파일은 이름 문자열 목록이다 — 그때는 이름만 쓴다
    return {k: ([{"name": x} for x in v] if v and isinstance(v[0], str) else v)
            for k, v in raw.items()}


def is_nationwide(v):
    """업체명·소개에 배송 범위가 그대로 적혀 있다 — 「전국배송」·「택배배송」."""
    t = (v.get("name") or "") + " " + (v.get("introduction") or "")
    return ("전국" in t) or ("택배" in t)


def price_rows(cur):
    """재료 시세 — 4분류별. 재료 페이지가 있는 것만 링크한다(고아 링크 금지)."""
    rows = list(cur.execute("""
        SELECT i.ingredient_key k, i.name, i.display_name, i.page_slug, i.base_unit,
               i.wholesale_price wp, i.manual_price mp, i.class, i.is_retail,
               COUNT(DISTINCT mi.menu_id) uses
        FROM ingredients i LEFT JOIN menu_ingredients mi ON mi.ingredient_key=i.ingredient_key
        WHERE (i.wholesale_price>0 OR i.manual_price>0) AND i.type <> 'live_composite'
          AND COALESCE(i.page_slug,'') <> ''
        GROUP BY i.ingredient_key
        HAVING uses>0 OR i.chamgagyeok_key IS NOT NULL"""))
    by = {c: [] for c in CAT_ORDER}
    for r in rows:
        nm = G.strip_mall(r["display_name"] or r["name"])
        cat = cat_of(r["k"], nm, r["class"], r["is_retail"])
        by[cat].append((r["uses"], nm, r["page_slug"], r["wp"] or r["mp"], r["base_unit"]))
    for c in by:
        by[c].sort(key=lambda x: -x[0])
    return by


def wide_vendors(all_sellers, min_regions=8):
    """**여러 지역에서 함께 잡히는 업체** = 사실상 전국 물류업체.

    🔴 근거는 우리가 직접 받은 지역별 목록이다 — 상호에 「전국」 이 있다고 넣지 않는다.
       «17개 지역 중 N곳에서 확인» 이라고 셀 수 있는 것만 쓴다.
    """
    cnt, name_of = {}, {}
    for region, vs in all_sellers.items():
        for v in vs:
            nm = v.get("name") or ""
            if not nm:
                continue
            k = nm.strip()
            cnt[k] = cnt.get(k, 0) + 1
            name_of[k] = v
    out = [(c, name_of[k]) for k, c in cnt.items() if c >= min_regions]
    out.sort(key=lambda x: -x[0])
    return out


# ── 업체 소개글 정리 (2026-07-28) ─────────────────────────────
#
# 🔴 식봄 `introduction` 을 **그대로 쓰지 않는다.**
#    ① 남의 사이트와 같은 글이라 중복 콘텐츠다
#    ② ❤️ 도배·"초특가 세일중" 같은 광고 문구가 그대로 딸려온다
#    ③ 우리가 남의 광고를 대신 실어주는 꼴이 된다
#    → **사실만 뽑아 배지로** 만든다. 못 뽑으면 아무것도 안 보여준다.
CAT_KO = {
    "KOREAN": "한식", "CHINESE": "중식", "JAPANESE": "일식", "WESTERN": "양식",
    "SEAFOOD": "수산", "DELI": "반찬", "POULTRY": "닭·오리", "FAST_FOOD": "패스트푸드",
    "BAKERY": "베이커리", "PUB": "주점", "FUSION": "퓨전", "BEVERAGE": "음료",
    "DELIVERY": "배달", "BUFFET": "뷔페", "OTHERS": "기타",
}

_RX_CUT = re.compile(r"(\d{1,2})\s*시[^0-9]{0,8}(?:마감|이전|까지)")
_RX_WHEN = [("새벽배송", "새벽배송"), ("당일배송", "당일배송"), ("다음날", "익일배송"),
            ("익일", "익일배송"), ("콜드체인", "콜드체인"), ("냉장", "냉장배송"),
            ("주 6일", "주 6일"), ("주6일", "주 6일")]


def vendor_facts(intro):
    """소개글에서 **사실**만 뽑는다 — 주문마감 시각과 배송 방식뿐. 홍보 문구는 버린다."""
    t = (intro or "").replace("\n", " ")
    out = []
    # 🔴 마감 시각은 **안 쓴다**(2026-07-28). "오후 6시까지"를 6시로 읽어 12시간이 틀렸다.
    #    오전·오후가 섞여 있고 «결제 마감»·«배송 마감»도 구분이 안 된다.
    #    애매하면 지운다 — 틀린 정보는 없느니만 못하다.
    for key, label in _RX_WHEN:
        if key in t and label not in out:
            out.append(label)
    return out[:3]


def page(area_name, sellers, prices, others, wide=(), n_regions=0):
    short = SHORT.get(area_name, area_name)
    slug = SLUG.get(area_name, area_name)
    taekbae = area_name == "그 외(택배배송)"
    nat = [v for v in sellers if is_nationwide(v)]
    loc = [v for v in sellers if not is_nationwide(v)]

    vrows = ""
    for v in (nat + loc):
        tag = "전국" if is_nationwide(v) else "지역"
        cats = ", ".join(CAT_KO.get(c, c) for c in (v.get("sellerCategoryList") or [])[:5])
        facts = vendor_facts(v.get("introduction"))
        fhtml = "".join(f'<span class="vfx">{G.esc(x)}</span>' for x in facts)
        vrows += (f'<div class="vrow"><span class="vtag{" nat" if tag == "전국" else ""}">{tag}</span>'
                  f'<div class="vmid"><div class="vnm">{G.esc(v.get("name") or "")}</div>'
                  + (f'<div class="vmeta">{fhtml}'
                     + (f'<span class="vcat">{G.esc(cats)}</span>' if cats else "")
                     + '</div>' if (fhtml or cats) else "")
                  + '</div></div>')

    # 업체가 적은 지역(제주 1곳)은 그것만으론 페이지가 얇다.
    # **다른 지역에서 널리 잡히는 업체**를 «참고» 로 붙이되,
    # ⛔ 그 업체가 이 지역에 배송한다고 쓰지 않는다 — 확인된 사실이 아니다.
    widebox = ""
    if len(sellers) < 5 and wide:
        here = {(v.get("name") or "").strip() for v in sellers}
        rows2 = ""
        for c, v in wide[:8]:
            nm = (v.get("name") or "").strip()
            if nm in here:
                continue
            rows2 += (f'<div class="vrow"><span class="vtag">{c}개 지역</span>'
                      f'<div class="vmid"><div class="vnm">{G.esc(nm)}</div></div></div>')
        if rows2:
            widebox = (f'<h2 class="arh2">전국 단위로 움직이는 업체<em>참고</em></h2>'
                       f'<p style="font-size:12.5px;color:var(--muted);line-height:1.7;margin:0 0 9px">'
                       f'우리가 확인한 {n_regions}개 지역 중 여러 곳에서 함께 잡힌 업체입니다. '
                       f'<b>{G.esc(short)} 배송 여부는 확인되지 않았습니다</b> — '
                       f'주문 전에 각 업체 배송권역을 확인하세요.</p>'
                       f'<div class="vlist">{rows2}</div>')

    tbls = ""
    # 🔴 시세 표는 지역 페이지에도 안 넣는다(2026-07-28 지시).
    #    `prices.html` 과 재료 326장이 이미 답한다. 여기는 «어디서 사냐» 만 답한다.
    #    표를 넣었을 땐 서울 페이지가 5,400px 였다 — 업체를 보러 온 사람에게 너무 길다.
    n_kind = sum(len(v) for v in (prices or {}).values())
    pgo = (f'<a class="pgo" href="prices.html"><span>재료 가격 {n_kind}종 보기'
           f'<small>정육·수산·채소·가공식품 도매 단가</small></span>'
           f'<span class="ar">›</span></a>')
    tbls = ""

    links = "".join(f'<a href="area_{SLUG[o]}.html">{SHORT.get(o, o)} 식자재</a>'
                    for o in others[:12])

    if taekbae:
        h1 = "택배로 받는 식자재 도매"
        lead = ("직배송이 안 닿는 지역은 택배로 받습니다. 택배는 배송비가 따로 붙으니 "
                "대용량으로 한 번에 받는 쪽이 유리합니다.")
    else:
        h1 = f"{short} 식자재마트 · 도매 배송업체"
        lead = (f"{short}에 배송하는 식자재 업체 {len(sellers)}곳입니다. "
                f"전국 물류업체 {len(nat)}곳, {short} 지역업체 {len(loc)}곳.")

    body = f'''<div class="crumb"><a href="index.html">홈</a> › <a href="areas.html">식자재마트</a> › {G.esc(short)}</div>
<div class="arhd"><h1>{G.esc(h1)}</h1>
<div class="sub">{G.esc(lead)}</div>
<div class="arnote">💡 아래 <b>도매 시세는 전국 기준</b>입니다. 식봄에 올라온 상품 전체에서 뽑은 값이라
지역에 따라 실제 구매가·배송비가 달라질 수 있어요. 가격은 날마다 바뀝니다.</div></div>

<div class="arlinks">{links}</div>
{pgo}

<h2 class="arh2">{G.esc(short)} 배송 업체<em>{len(sellers)}곳</em></h2>
<div class="vlist">{vrows or '<div class="vrow"><div class="vmid">업체 정보를 준비 중입니다.</div></div>'}</div>
{widebox}
{tbls}

<div class="arlinks">{links}</div>'''

    _t = f"{short} 식자재마트 도매 배송업체 · 재료값"
    _d = (f"{short} 식자재 도매 배송업체 {len(sellers)}곳과 정육·수산·채소·가공식품 "
          f"도매 시세를 한 번에. 전국 물류업체 {len(nat)}곳, 지역업체 {len(loc)}곳의 "
          f"취급 품목을 정리했습니다.")
    ld = {"@context": "https://schema.org", "@type": "ItemList",
          "name": f"{short} 식자재 도매 배송업체",
          "numberOfItems": len(sellers),
          "itemListElement": [
              {"@type": "ListItem", "position": i + 1,
               "item": {"@type": "Organization", "name": v.get("name") or ""}}
              for i, v in enumerate(nat + loc)]}
    ldjs = ('<script type="application/ld+json">'
            + json.dumps(ld, ensure_ascii=False) + '</script>')
    return (G.seo_head(_t, _d, f"area_{slug}.html", here="areas")
            + f"<style>{CSS}</style>" + body + ldjs + G.FOOT)


def index_page(names, sellers, prices=None, wide=()):
    """식자재마트 대문 — **「식자재마트」(월 54,090) 를 받는 페이지다.**

    🔴 전에는 지역 카드 16개만 있는 목록이었다. 그건 한 단계만 늘리는 페이지라
       «없애자» 는 이야기가 나왔는데, 없애면 그 검색어를 받을 자리가 사라진다.
       → **없애지 말고 내용을 채운다.** 지역 선택은 칩 한 줄로 줄이고,
         전국 물류업체와 도매 시세를 이 페이지에서 바로 보여준다.
    """
    chips = "".join(
        f'<a href="area_{SLUG[n]}.html">{G.esc(SHORT.get(n, n))} '
        f'<em>{len(sellers.get(n) or [])}</em></a>' for n in names)

    # 여러 지역에서 함께 잡히는 업체 = 어디서나 받을 수 있는 곳. 대문에 이게 제일 쓸모 있다
    wrows = ""
    for c, v in (wide or [])[:12]:
        cats = ", ".join(CAT_KO.get(x, x) for x in (v.get("sellerCategoryList") or [])[:5])
        facts = vendor_facts(v.get("introduction"))
        fh = "".join(f'<span class="vfx">{G.esc(x)}</span>' for x in facts)
        wrows += (f'<div class="vrow"><span class="vtag nat">{c}개 지역</span>'
                  f'<div class="vmid"><div class="vnm">{G.esc(v.get("name") or "")}</div>'
                  + (f'<div class="vmeta">{fh}'
                     + (f'<span class="vcat">{G.esc(cats)}</span>' if cats else "")
                     + '</div>' if (fh or cats) else "") + '</div></div>')

    # 🔴 시세 표는 여기 안 넣는다(2026-07-28 지시) — `prices.html` 과 재료 326장이 이미 답한다.
    #    식자재마트는 «어디서 사냐», 시세 페이지는 «얼마냐». 같은 표를 두 군데 두면
    #    검색엔진도 어느 페이지를 올릴지 헷갈린다. 링크 한 줄만 남긴다.
    n_kind = sum(len(v) for v in (prices or {}).values())
    tbls = (f'<a class="pgo" href="prices.html"><span>재료 가격 {n_kind}종 보기'
            f'<small>정육·수산·채소·가공식품 도매 단가</small></span>'
            f'<span class="ar">›</span></a>')

    body = f'''<div class="crumb"><a href="index.html">홈</a> › 식자재마트</div>
<div class="arhd"><h1>식자재마트 · 도매 배송업체와 재료값</h1>
<div class="sub">지역마다 배송하는 업체가 다릅니다. 내 지역을 고르면 그 지역에 오는 업체를 볼 수 있어요.</div>
<div class="arnote">💡 <b>도매 시세는 전국 기준</b>입니다. 식봄에 올라온 상품 전체에서 뽑은 값이라
지역에 따라 실제 구매가·배송비가 달라질 수 있어요. 가격은 날마다 바뀝니다.</div></div>

<div class="arlinks">{chips}</div>
{tbls}

<h2 class="arh2">여러 지역에 배송하는 업체<em>{len(wide or [])}곳</em></h2>
<div class="vlist">{wrows or '<div class="vrow"><div class="vmid">준비 중입니다.</div></div>'}</div>'''
    return (G.seo_head("식자재마트 · 도매 배송업체와 재료값",
                       "전국 16개 시·도별 식자재 도매 배송업체와 정육·수산·채소·가공식품 도매 시세. "
                       "여러 지역에 배송하는 업체를 한눈에 보고, 내 지역 업체는 지역별로 확인하세요. "
                       "시세는 전국 기준이고 날마다 바뀝니다.",
                       "areas.html", here="areas")
            + f"<style>{CSS}</style>" + body + G.FOOT)


def main():
    refresh = "--refresh" in sys.argv
    sellers = load_sellers(refresh)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    prices = price_rows(c.cursor())
    # 🔴 「그 외(택배배송)」 페이지는 **만들지 않는다** (대표 결정 2026-07-28).
    #    · 검색량이 없다 — `식자재택배` 10 · `전국식자재배송` 10
    #    · 식봄 GraphQL 이 `area_0` 을 거부한다("배송지 정보를 찾을 수 없습니다") → 업체 0곳
    #    · **업체 0곳인 빈 페이지를 사이트맵에 넣으면 색인 품질만 깎인다.** 애드센스 심사 중이다
    #    ⛔ 상호에 「택배배송」 이 박힌 업체를 모아 채우지 마라 —
    #       상호에 그 글자가 있다고 전국 배송이라는 **근거가 되지 않는다**
    #       (`ingredients-evidence-only`: 빈칸이 가짜보다 낫다).
    names = [n for n in SLUG if n in sellers and n != "그 외(택배배송)"]
    stale = os.path.join(OUT, "area_taekbae.html")
    if os.path.exists(stale):        # 전에 만들어둔 게 남아 있으면 지운다(고아 방지)
        os.remove(stale)
        print("  · 옛 택배배송 페이지 삭제")
    wide = wide_vendors(sellers)
    n = 0
    for nm in names:
        others = [o for o in names if o != nm]
        html = page(nm, sellers.get(nm) or [], prices, others,
                    wide=wide, n_regions=len(names))
        io.open(os.path.join(OUT, "area_%s.html" % SLUG[nm]), "w",
                encoding="utf-8").write(html)
        n += 1
    io.open(os.path.join(OUT, "areas.html"), "w", encoding="utf-8").write(
        index_page(names, sellers, prices, wide))
    print("지역 페이지 %d장 + 목록 1장 → _preview/area_*.html" % n)
    print("  품목 h2: %s" % " · ".join(
        "%s %d종" % (CAT_LABEL[k], len(v)) for k, v in prices.items() if v))


if __name__ == "__main__":
    main()
