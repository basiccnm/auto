# -*- coding: utf-8 -*-
"""브랜드 **메뉴 상세페이지를 하나씩 들어가서** 중량·재료·원산지·가격을 긁는다. 2026-07-26

🔴 왜 이 방식인가 (대표 지시)
   *"홈페이지에서 메뉴목록을 보여주는데 그걸 하나씩 눌러서 들어가게 해서 봐야지"*
   *"메뉴만 알고 재료는 모르는데?? 어떻게 비교해???"*

   실제로 확인했다 — 중량은 **별도 영양성분 페이지가 아니라 상품 상세페이지**에 있다.
     BBQ `bbq.co.kr/products/30392` → "* 조리전 중량 : 10호(951~1050g) 이상" + "영양정보 보기"
   목록 페이지만 긁으면 메뉴 이름만 얻고 끝난다. 그래서 상세 URL 을 모아 전부 렌더링한다.

⛔ 여기서 나온 것만 재료 근거로 쓴다. 안 나오면 비워둔다 — 지어내지 않는다
   (`ingredients-evidence-only`: 빈칸이 가짜보다 낫다).

중량 우선순위(대표 확정): ①상세페이지·영양성분 표기값 → ②정해진 규격(치킨 10호 등) → ③업태 기본중량

    python scripts/brand_menu_detail.py --only BBQ
    python scripts/brand_menu_detail.py --top 30
"""
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "brand_menu_detail")
REPORT = os.path.join(BASE, "data", "research", "brand_menu_detail.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BUDGET = "9000"
WORKERS = 4
MAX_DETAIL = 40          # 브랜드당 상세페이지 상한
JUNK_TAG = re.compile(r"(?is)<(script|style|noscript|svg|head|iframe)[^>]*>.*?</\1>")

# 상세페이지로 보이는 주소 꼴 — 실제로 확인한 것들
DETAIL_PAT = re.compile(
    r"/products?/\d+"                    # BBQ  /products/30392
    r"|menu_view\.php\?"                 # 설빙  menu_view.php?menu=163
    r"|[?&](?:code|idx|no|seq|goods_?no|menu_?id|pcode)=\d+"   # ...asp?code=21
    r"|/menu/[\w\-]+/\d+"
    r"|/detail", re.I)
LISTWORD = ("메뉴", "menu", "product", "goods", "카테고리", "categor", "brand")

# 상세페이지에서 뽑을 것
RX_WEIGHT = re.compile(r"(?:조리\s*전\s*)?중량\s*[:：]\s*([^\n|]{2,50})")
# 메뉴명 — 이게 없으면 우리 DB 메뉴와 못 맞춘다(2026-07-26: 40쪽 다 긁고 이름이 없어서 대조 불가)
RX_TITLE = re.compile(r"(?is)<title[^>]*>(.*?)</title>")
RX_H1 = re.compile(r"(?is)<h[12][^>]*>(.*?)</h[12]>")
RX_OG = re.compile(r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)')
RX_HOSU = re.compile(r"(\d{1,2})\s*호\s*\(?\s*([\d,]+)\s*~\s*([\d,]+)\s*g")
RX_GRAM = re.compile(r"(\d[\d,.]*)\s*(?:g|kg|ml|L)\b", re.I)
RX_PRICE = re.compile(r"([\d,]{3,9})\s*원")


def render(url):
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1280,3000",
             "--virtual-time-budget=" + BUDGET, "--dump-dom", url],
            capture_output=True, timeout=80)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def to_text(dom):
    s = JUNK_TAG.sub(" ", dom)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|td|th|h[1-6]|a|span|dt|dd)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t　]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def all_links(dom, base_url):
    host = urllib.parse.urlparse(base_url).netloc
    out, seen = [], set()
    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\']', dom):
        href = m.group(1)
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        u = urllib.parse.urljoin(base_url, href).split("#")[0]
        if urllib.parse.urlparse(u).netloc != host or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def menu_name(dom, brand):
    """상세페이지의 메뉴명. og:title → h1 → <title> 순."""
    for rx in (RX_OG, RX_H1, RX_TITLE):
        m = rx.search(dom)
        if not m:
            continue
        t = re.sub(r"<[^>]+>", " ", m.group(1))
        t = re.sub(r"&[a-z]+;|&#\d+;", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        # "메뉴명 | 브랜드" 꼴에서 브랜드·사이트명을 떼낸다
        for sep in ("|", "-", "–", "::", ">"):
            if sep in t:
                parts = [p.strip() for p in t.split(sep) if p.strip()]
                parts = [p for p in parts if brand not in p] or parts
                if not parts:          # 구분자만 있는 제목이면 건너뛴다(IndexError 로 30곳 수집이 죽었다)
                    t = ""
                    break
                t = parts[0]
        if not t:
            continue
        if 1 < len(t) <= 40:
            return t
    return None


def parse_detail(text, url, dom="", brand=""):
    """상세페이지 한 장에서 뽑을 수 있는 것만 뽑는다."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    d = {"url": url, "name": menu_name(dom, brand), "weight": None, "hosu": None,
         "grams": [], "prices": [], "origin": [], "allergy": [], "nutrition": False}
    m = RX_WEIGHT.search(text)
    if m:
        d["weight"] = m.group(1).strip()[:60]
    m = RX_HOSU.search(text)
    if m:
        d["hosu"] = {"ho": int(m.group(1)),
                     "lo": int(m.group(2).replace(",", "")),
                     "hi": int(m.group(3).replace(",", ""))}
    d["grams"] = list(dict.fromkeys(RX_GRAM.findall(text)))[:12]
    d["prices"] = list(dict.fromkeys(RX_PRICE.findall(text)))[:8]
    for l in lines:
        if "원산지" in l and len(l) <= 200:
            d["origin"].append(l)
        if ("알레르" in l or "알러지" in l) and len(l) <= 200:
            d["allergy"].append(l)
        if "영양" in l:
            d["nutrition"] = True
    d["origin"] = d["origin"][:6]
    d["allergy"] = d["allergy"][:6]
    return d


def do_brand(b):
    """🔴 한 브랜드에서 예외가 나도 나머지는 계속 간다.
    2026-07-26: menu_name 의 IndexError 하나 때문에 30곳 수집이 통째로 죽었다."""
    try:
        return _do_brand(b)
    except Exception as e:
        print("  ✗ %-16s 실패: %s" % (b["name"][:16], str(e)[:60]), flush=True)
        return {"brand": b["name"], "slug": b["slug"], "details": [], "error": str(e)[:120]}


def _do_brand(b):
    url = b["u"]
    dom = render(url)
    if not dom:
        print("  ✗ %-16s 홈페이지 렌더 실패" % b["name"][:16], flush=True)
        return {"brand": b["name"], "slug": b["slug"], "details": [], "error": "render"}

    # ① 목록·카테고리 쪽을 돌며 상세 URL 을 모은다
    #
    # 🔴 주소 꼴로 상세를 알아내려 하면 브랜드마다 깨진다(2026-07-26: 30곳 중 23곳이 0쪽).
    #    실제로 본 꼴이 다 다르다 —
    #      BBQ      /products/30392
    #      피자스쿨   /menu/치킨타코피자/
    #      bhc      /menu-category/chicken/?slide_id=slide-116
    #      설빙      /menu/?type=사이드 · menu_view.php?menu=163
    #    그래서 **"목록 페이지 아래로 더 뻗은 링크는 상세로 본다"** 로 바꿨다. 꼴을 안 가린다.
    seen_pages = {url}
    detail = []

    def deeper(u, base):
        """base 목록 페이지보다 아래로(또는 쿼리가 더 붙어) 뻗은 같은 계열 링크인가."""
        if u == base:
            return False
        bp = base.split("?")[0].rstrip("/")
        up = u.split("?")[0].rstrip("/")
        if up == bp:                       # 같은 경로 + 쿼리만 다름 → 카테고리 탭/상세
            return "?" in u
        return up.startswith(bp + "/")     # 한 단계 아래 경로

    queue = [u for u in all_links(dom, url)
             if any(w.lower() in u.lower() for w in LISTWORD)][:10]
    for u in all_links(dom, url):
        if DETAIL_PAT.search(u):
            detail.append(u)
    while queue and len(detail) < MAX_DETAIL:
        u2 = queue.pop(0)
        if u2 in seen_pages:
            continue
        seen_pages.add(u2)
        d2 = render(u2)
        if not d2:
            continue
        for u3 in all_links(d2, u2):
            if u3 in detail or u3 in seen_pages:
                continue
            if DETAIL_PAT.search(u3) or deeper(u3, u2):
                detail.append(u3)
            elif (any(w.lower() in u3.lower() for w in LISTWORD)
                  and len(seen_pages) < 14):
                queue.append(u3)
    detail = detail[:MAX_DETAIL]

    # ② 상세페이지를 하나씩 들어간다
    recs, texts = [], []
    for u in detail:
        dd = render(u)
        if not dd:
            continue
        t = to_text(dd)
        texts.append("=== %s\n%s" % (u, t))
        recs.append(parse_detail(t, u, dd, b["name"]))

    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "%s.txt" % (b["slug"] or b["name"])), "w",
            encoding="utf-8").write("\n".join(texts))
    nn = sum(1 for r in recs if r["name"])
    nw = sum(1 for r in recs if r["weight"] or r["hosu"])
    no = sum(1 for r in recs if r["origin"])
    na = sum(1 for r in recs if r["allergy"])
    print("  %-16s 상세 %2d쪽 · 이름 %2d · 중량 %2d · 원산지 %2d · 알레르기 %2d" % (
        b["name"][:16], len(recs), nn, nw, no, na), flush=True)
    return {"brand": b["name"], "slug": b["slug"], "details": recs}


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 30
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    # 🔴 신규 브랜드는 우리 DB에 메뉴가 0개다. 기본 조건(menus>0)이면 영원히 수집되지 않는다.
    #    --include-empty 로 그놈들만(또는 같이) 돌린다. 결과는 brand_menu_official 에만 쌓고
    #    menus 로 자동 승격하지 않는다(대표 결정 — 사이드·음료까지 밀려들어온다).
    empty = "--include-empty" in sys.argv
    only_empty = "--only-empty" in sys.argv
    cond = "> 0"
    if only_empty:
        cond = "= 0"
    elif empty:
        cond = ">= 0"
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("""
        SELECT b.name, b.slug, b.homepage_url u
        FROM brands b WHERE b.published=1 AND COALESCE(b.homepage_url,'') <> ''
          AND (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) %s
        ORDER BY COALESCE(b.frcs_cnt,0) DESC LIMIT ?""" % cond, (top,))]
    if only:
        rows = [r for r in rows if only in r["name"]]
    print("상위 %d곳 · 메뉴 상세페이지 수집 (브랜드당 최대 %d쪽)" % (len(rows), MAX_DETAIL), flush=True)
    print("", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(do_brand, rows))
    io.open(REPORT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    tot = sum(len(r.get("details") or []) for r in res)
    wt = sum(1 for r in res for d in (r.get("details") or []) if d["weight"] or d["hosu"])
    print("", flush=True)
    print("끝. 상세 %d쪽 · 중량 확보 %d쪽 → %s" % (tot, wt, REPORT), flush=True)


if __name__ == "__main__":
    main()
