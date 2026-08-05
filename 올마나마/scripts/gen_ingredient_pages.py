# -*- coding: utf-8 -*-
"""재료 하나당 페이지 하나 — `/price_양파` 꼴.

왜 쪼개나 (2026-07-24):
  1. **보안** — 지금 시세 페이지 한 장에 가격 1,042개가 들어 있다. 봇이 그 한 장만 받으면
     우리 DB 대부분을 가져간다. Cloudflare 속도 제한(10초 3장)을 걸어도 1장은 통과한다.
     543장으로 쪼개면 다 받는 데 1시간이 걸려 실익이 없어진다.
  2. **SEO** — 한 장이 684개 키워드를 동시에 노리면 아무것도 못 잡는다.
     "양파 도매 시세" 같은 검색어는 그 재료만 다루는 페이지가 잡는다.

페이지에 담는 것 (빈약한 페이지로 색인 제외되지 않게):
  · 도매·소매 단가와 등락      · 값의 근거(상품명·규격·조사일)
  · 이 재료를 쓰는 메뉴 목록    · 100g/500g/1kg 환산표
  · 같은 분류 재료로 가는 링크  ← 페이지끼리 연결돼야 크롤러가 잘 돈다

⚠️ URL에 한글을 쓴다. 지금까지 이 사이트에 한글 파일명이 하나도 없었으므로
   **한 장만 먼저 배포해 라이브에서 200이 뜨는지 확인하고** 전체를 돌릴 것.
   (`--limit 1` 로 한 장만 만든다)
"""
import os, sys, sqlite3, html, re, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUTDIR = os.path.join(BASE, "_preview")

from site_config import SITE, clean_urls
from theme import (CSS_VARS, HEAD_SCRIPT, BTN, AUTH_BTN, TOGGLE_JS, SHARE_BTN, HEAD_TAGS,
                   FOOTER_LINKS, FOOTER_CSS, ADFIT, ADFIT_CSS, GNAV_CSS,
                   WRAP_CSS, BODY_CSS, TYPO_CSS, gnav)


# ── 화면에 나가는 근거에서 쿠팡을 지운다 (2026-07-26 대표 지시) ──────────────
#  🔴 왜: 파트너스 정책상 "쿠팡"을 내세워 파는 것처럼 쓰면 걸린다. 우리가 쓰는 글에는
#     쿠팡이라는 말을 넣지 않는다. 하단 **파트너스 고지 문구는 필수라 그건 건드리지 않는다**
#     (그건 theme.py 의 별도 템플릿이다).
#  DB 의 wholesale_basis 는 그대로 둔다 — 그건 우리 감사 기록이고 화면에 나가는 건 이 필터를 거친 것.
#  실제로 4장의 재료 페이지에 "소매는 쿠팡 [로켓프레시] …" 가 그대로 나가 있었다.
# ── 화면에 나가는 근거에서 **제조사·유통사 상표**를 지운다 (2026-07-27 대표 지시) ──────
#  🔴 왜: "상표가 안보이게 저게 파우더면 치킨용 파우더 이런식으로."
#     상표가 박혀 있으면 손님이 '그 제품만 사야 하나' 싶어 이탈한다. 우리 링크에서 고르게 한다.
#  ⛔ DB 의 `wholesale_basis` 는 **그대로 둔다** — 나중에 어느 상품이었는지 대조해야 한다
#     (`keep-product-names`). 지우는 건 화면에 나가는 문자열뿐이다.
#  규격·가격·날짜는 남긴다. 그게 "이 값이 진짜다"라는 근거다.
_MAKERS = (
    "뫼루니식품|뫼루니|상경식품|상경|태원식품|태원|태영식품|태영|금양식품|금양|아이엠소스|"
    "사조오양|사조해표|사조대림|사조안심|사조|오뚜기|청정원|동원홈푸드|동원|곰표|해표|백설|"
    "CJ제일제당|CJ|청우식품|청우|움트리|다이찌식품|다이찌|샘표|풀무원|비셰프|코다노|이슬나라|"
    "코리아제니스|제니스|미담채|쿠즈락|흥국|칸스타|삼립|첫맛|쉐프원|올품|나비촌|요리스케치|"
    "춘풍접객|어나더소스|다봄|밀락|썬리취|비에이치푸드|고추명가|곰곰|신영|레벤|바로소스|소스야|"
    "비비드키친|몽크슈|하인즈|앵커|남양|서울우유|롯데웰푸드|농심|글로벌냉동|프레시원|굿딜|"
    "당당한닭|제이푸드서비스|신선약초|비이츠|쿡스타|해광식품|스위트페이지|까르페|델링|미래식품|"
    "델리시우스|에스파뇰라|만토바|안달루니아|도나파올라|골든필드|페페브루노|보베다|프리올리바|"
    "식자재왕|장사의신"
)
# ⛔ `식봄`·`미트박스`는 지우지 않는다 — 소비자 상표가 아니라 **우리가 어디서 값을 가져왔는지**
#    를 말하는 조달처다. 그게 빠지면 "이 값이 진짜다"라는 근거가 사라진다.

_CP = [
    # 상표는 뒤에 낱말이 이어질 때만 지운다(문장 속 같은 글자를 잘못 지우지 않게)
    (re.compile(r"(?<![가-힣A-Za-z])(?:" + _MAKERS + r")(?=[\s가-힣A-Za-z0-9])\s*"), ""),
    (re.compile(r"\[?로켓프레시\]?\s*"), ""),
    (re.compile(r"\(\s*로켓\s*[·,]?\s*"), "("),          # "(로켓 · 소매 기준)" → "(소매 기준)"
    (re.compile(r"[·,]?\s*로켓\s*\)"), ")"),
    (re.compile(r"\(\s*로켓\s*\)"), ""),
    (re.compile(r"쿠팡\s*파트너스"), "제휴 검색"),          # 근거 안에 들어간 경우만
    (re.compile(r"쿠팡"), "온라인 소매몰"),
    (re.compile(r"\s*로켓배송\s*"), " "),
    (re.compile(r"\s{2,}"), " "),
]


def clean_basis(s):
    # 🔴 근거 문구에도 상품명·제조사가 박혀 있다. 화면에서만 가린다 — DB 원문은 그대로 둔다
    #    (가격을 재검증하려면 어느 상품이었는지 알아야 한다).
    s = _mask(s or "")
    for rx, rep in _CP:
        s = rx.sub(rep, s)
    return s.strip()


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def won(v):
    return "{:,}원".format(int(round(v)))


# 파일명·URL에 못 쓰는 문자를 없앤다.
#  '초코잼/스프레드' 처럼 슬래시가 든 재료명이 있어서 저장이 터졌다(2026-07-24).
#  URL·파일명에 안전한 문자만 남긴다. 한글·영숫자·밑줄만 통과시키고 나머지는 버린다.
#  ▲◆丝等 같은 기호가 들어간 재료명이 있어 링크 검사·URL 처리가 계속 깨졌다(2026-07-24).
_KEEP = re.compile(r'[^0-9A-Za-z가-힣]+')


def safe_slug(name):
    return _KEEP.sub("", name)


# 상표 마스킹 — 규칙은 namemask.py 한 곳에만 둔다(2026-07-27 대표 지시)
from namemask import mask as _mask


con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# 등락 — 최신 시세일 vs 직전 시세일
_d = [r[0] for r in cur.execute(
    "SELECT DISTINCT price_date FROM price_history ORDER BY price_date DESC LIMIT 2")]
DELTA = {}
if len(_d) == 2:
    for r in cur.execute("""SELECT a.ingredient_key k, a.retail_price c, b.retail_price p
        FROM price_history a JOIN price_history b ON a.ingredient_key=b.ingredient_key
        WHERE a.price_date=? AND b.price_date=? AND a.retail_price>0 AND b.retail_price>0""",
        (_d[0], _d[1])):
        DELTA[r["k"]] = (r["c"], r["p"])
PREV_LABEL = _d[1] if len(_d) == 2 else ""

STYLE = ("<style>" + CSS_VARS + FOOTER_CSS + ADFIT_CSS + GNAV_CSS + WRAP_CSS
         + BODY_CSS + TYPO_CSS + """
.crumb{font-size:12.5px;color:var(--muted);margin:14px 0 10px}
.crumb a{color:var(--muted);text-decoration:none}
.pcard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
.ptop{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:4px}
.pnow{font-size:30px;font-weight:900;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.punit{font-size:14px;color:var(--muted);font-weight:700}
.pdelta{font-size:13px;font-weight:800}
.pdelta.up{color:var(--up)} .pdelta.dn{color:var(--dn)} .pdelta.flat{color:var(--muted)}
.prow{display:flex;justify-content:space-between;padding:9px 0;border-top:1px solid var(--line);font-size:13.5px}
.prow b{font-variant-numeric:tabular-nums}
.psrc{font-size:12.5px;color:var(--muted);line-height:1.6;margin-top:10px;
padding-top:10px;border-top:1px solid var(--line)}
.mlist{display:grid;gap:6px}
.mrow2{display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid var(--line);
border-radius:9px;text-decoration:none;color:inherit;font-size:13px}
.mrow2 .bn{color:var(--muted);font-size:12px;flex:none}
.mrow2 .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mrow2 .rt{font-weight:800;font-variant-numeric:tabular-nums;flex:none}
.chips2{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}
.chips2 a{border:1px solid var(--line);background:var(--card);border-radius:999px;
padding:6px 11px;font-size:12.5px;font-weight:600;color:var(--ink);text-decoration:none}
.sect3{font-size:15px;font-weight:800;margin:20px 0 9px}
</style>""")


def page(row, siblings, menus, slug):
    # 화면 이름·주소 둘 다 표시명 기준이다. 주소는 호출부에서 중복을 풀어 넘겨준다.
    name = _mask(row["display_name"] or row["name"])
    unit = row["base_unit"] or "kg"
    wp, mp = row["wholesale_price"], row["manual_price"]
    # 등락
    d = DELTA.get(row["ingredient_key"])
    dhtml = ""
    if d and d[1]:
        pct = (d[0] - d[1]) / d[1] * 100
        cls = "up" if pct > 0.5 else ("dn" if pct < -0.5 else "flat")
        arrow = "▲" if pct > 0.5 else ("▼" if pct < -0.5 else "–")
        dhtml = (f'<span class="pdelta {cls}">{arrow} {abs(pct):.1f}%</span>'
                 f'<span class="punit">{esc(PREV_LABEL[5:].replace("-", "."))} 대비</span>')

    main = wp or mp
    conv = ""
    if unit in ("kg", "L") and main:
        conv = "".join(
            f'<div class="prow"><span>{lab}</span><b>{won(main*mul)}</b></div>'
            for lab, mul in (("100g", .1), ("500g", .5), ("1kg", 1), ("5kg", 5)))

    mrows = "".join(
        f'<a class="mrow2" href="menu_{m["id"]}.html"><span class="bn">{esc(m["bn"])}</span>'
        f'<span class="nm">{esc(m["mn"])}</span>'
        f'<span class="rt">{(m["r"]*100 if m["r"] and m["r"]<1.5 else (m["r"] or 0)):.0f}%</span></a>'
        for m in menus[:12])
    more = (f'<div class="psrc">이 재료를 쓰는 메뉴 {len(menus)}개 중 12개를 보여드립니다.</div>'
            if len(menus) > 12 else "")

    # 형제 재료 링크 — 주소·글자 모두 상표가 없다(2026-07-27)
    sib = "".join(f'<a href="{esc(sslug)}.html">{esc(disp)}</a>'
                  for sslug, disp, _k in siblings[:16])

    desc = (f"{name} 도매가 {won(wp) if wp else '-'}, 소매가 {won(mp) if mp else '-'} "
            f"({unit} 기준). 실제 거래처 조사값과 등락, 이 재료를 쓰는 프랜차이즈 메뉴 "
            f"{len(menus)}개의 원가율을 함께 봅니다.")

    ld = {"@context": "https://schema.org", "@type": "WebPage",
          "name": f"{name} 도매·소매 시세", "description": desc,
          "url": f"{SITE}/{slug}", "inLanguage": "ko-KR"}

    body = f'''<div class="crumb"><a href="index.html">홈</a> › <a href="prices.html">재료 가격</a> › {esc(name)}</div>
<h1>{esc(name)} 가격</h1>
<div class="pcard">
<div class="ptop"><span class="pnow">{won(main) if main else "-"}</span>
<span class="punit">/{esc(unit)} · 도매</span>{dhtml}</div>
{f'<div class="prow"><span>소매(소포장)</span><b>{won(mp)}</b></div>' if mp else ""}
{conv}
<div class="psrc">{esc(clean_basis(row["wholesale_basis"]) or "조사 근거 정리 중")}</div>
</div>
{ADFIT}
{f'<h2 class="sect3">{esc(name)}를 쓰는 메뉴</h2><div class="mlist">{mrows}</div>{more}' if mrows else ""}
{f'<h2 class="sect3">같은 분류 재료</h2><div class="chips2">{sib}</div>' if sib else ""}
'''
    head = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(name)} 가격·시세 — 도매가·소매가 · 올마나마</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/{slug}">
<meta property="og:title" content="{esc(name)} 가격·시세 · 올마나마">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}/og/share.png">
{HEAD_TAGS}{HEAD_SCRIPT}{STYLE}</head><body>
<header class="top"><div class="in"><a class="logo" href="index.html" style="text-decoration:none">
<span class="lbadge">올</span>올마나마</a>{SHARE_BTN}{BTN}{AUTH_BTN}{gnav("prices")}</div></header>
<div class="wrap">'''
    foot = (f'</div>{FOOTER_LINKS}'
            f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
            f'{TOGGLE_JS}</body></html>')
    return slug, head + body + foot


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    # 시세 페이지(prices.html) 목록에 뜨는 재료만 만든다.
    #  목록에 없는 재료로 페이지를 만들면 **아무도 링크하지 않는 고아 페이지**가 되고,
    #  구글은 그런 페이지를 색인하지 않는다(healthcheck도 537건으로 잡아냈다).
    #  조건은 gen_prices_page.py 의 rows 쿼리와 같아야 한다.
    rows = list(cur.execute("""
        SELECT i.ingredient_key, i.name, i.display_name, i.page_slug, i.base_unit,
               i.wholesale_price, i.manual_price,
               i.wholesale_basis, COALESCE(i.subcat, i.class, '') sub
        FROM ingredients i LEFT JOIN menu_ingredients mi ON mi.ingredient_key=i.ingredient_key
        WHERE (i.wholesale_price>0 OR i.manual_price>0) AND i.type <> 'live_composite'
        GROUP BY i.ingredient_key
        HAVING COUNT(DISTINCT mi.menu_id)>0 OR i.chamgagyeok_key IS NOT NULL
            OR i.type IN ('live','live_composite')"""))
    # ⚠️ 여기서 이름을 더 거르면 안 된다. 시세 목록(prices.html)이 348종 전부에 링크를 걸기
    #    때문에, 조건이 다르면 그 차이만큼 **링크가 빈 곳을 가리킨다**(실제로 73건 발생).
    #    목록과 생성 대상은 항상 같은 집합이어야 한다.
    bysub = {}
    # 🔴 주소는 **DB의 `page_slug`** 를 쓴다 — `display_name_build.py` 가 한 곳에서 정한다.
    #    여기서 따로 계산하면 `gen_prices_page` 의 링크와 어긋나 링크가 빈 곳을 가리킨다.
    SLUG = {r["ingredient_key"]: r["page_slug"] for r in rows if r["page_slug"]}
    if not SLUG:
        print("⚠️ page_slug 가 비어 있다 — 먼저 `python scripts/display_name_build.py --apply`")
        return

    for r in rows:
        # (주소, 화면용 표시명) — 링크는 안 깨지고 글자에는 상표가 없다
        if r["ingredient_key"] not in SLUG:
            continue
        bysub.setdefault(r["sub"], []).append(
            (SLUG[r["ingredient_key"]], _mask(r["display_name"] or r["name"]),
             r["ingredient_key"]))

    # 사용 메뉴가 많은 순 — 중요한 것부터 만든다
    def uses(k):
        return cur.execute("SELECT COUNT(DISTINCT menu_id) c FROM menu_ingredients "
                           "WHERE ingredient_key=?", (k,)).fetchone()["c"]
    rows.sort(key=lambda r: -uses(r["ingredient_key"]))
    if limit:
        rows = rows[:limit]

    n = 0
    for r in rows:
        menus = list(cur.execute("""
            SELECT m.id, m.name mn, b.name bn, COALESCE(m.store_ratio,m.cost_ratio) r
            FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
            JOIN brands b ON b.id=m.brand_id
            WHERE mi.ingredient_key=? AND b.published=1 ORDER BY r DESC""", (r["ingredient_key"],)))
        if r["ingredient_key"] not in SLUG:
            continue          # 이름이 전부 기호인 재료 — 페이지를 만들지 않는다
        sibs = [x for x in bysub.get(r["sub"], []) if x[2] != r["ingredient_key"]]
        slug, htmlstr = page(r, sibs, menus, SLUG[r["ingredient_key"]])
        htmlstr = clean_urls(htmlstr)
        with open(os.path.join(OUTDIR, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(htmlstr)
        n += 1
    print("재료 페이지 %d장 생성" % n)


main()
