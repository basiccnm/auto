# -*- coding: utf-8 -*-
"""브랜드 홈페이지를 **헤드리스 크롬으로 렌더링해서** 메뉴·공급방식을 긁는다. 2026-07-26

🔴 왜 다시 만드나 (대표 지적)
   *"설빙 홈페이지 들어갔는데 메뉴 다 나오는데?"* / *"너가 나한테 준거는 홈페이지 내용 거의 없음 이야"*

   `brand_site_crawl.py` 는 urllib 로 HTML 원문만 받았다. 그런데 요즘 사이트는 **메뉴를 JS로 그린다.**
   설빙 `/menu/` 는 원문에 배너 5개만 있고 실제 메뉴 31개는 안 들어 있었다.
   그래서 내가 "홈페이지에 내용이 없다"고 잘못 보고했다. 사이트 잘못이 아니라 **내 수집 방식 잘못**이다.

   교촌·bhc·BBQ·도미노·피자헛·맥도날드·스타벅스·투썸도 같은 이유로 0건이었다.

✅ 고친 방법 — 이미 깔려 있는 크롬을 헤드리스로 돌려 **렌더링된 DOM**을 받는다. 설치 필요 없다.
     chrome --headless=new --dump-dom --virtual-time-budget=9000 <url>

    python scripts/brand_site_render.py              # 89곳 전부
    python scripts/brand_site_render.py --only 설빙
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
OUT = os.path.join(BASE, "data", "brand_pages_rendered")
REPORT = os.path.join(BASE, "data", "research", "brand_render_signals.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BUDGET = "9000"        # JS 가 그릴 시간(ms)
WORKERS = 4            # 크롬 4개까지만 — 대표도 PC를 쓴다
PER_SITE = 8           # 첫 페이지에서 뽑을 후보 링크 수
MAX_PAGES = 16         # 한 브랜드당 렌더링 상한(카테고리 탭까지)

SIG = {
    "완제품": ("완조리", "완제품", "완전조리", "조리완료", "원팩", "레토르트", "간편조리", "조리 없이"),
    "반제품": ("반조리", "반제품", "소스 공급", "양념 공급", "1차 가공", "전처리", "손질 완료", "밀키트"),
    "원물": ("매장에서 직접", "매일 손질", "직접 손질", "당일 조리", "수제", "생면", "매일 아침", "직접 반죽"),
    "물류": ("물류센터", "자체공장", "생산공장", "제조시설", "HACCP", "직배송", "물류시스템",
           "물류 시스템", "중앙집중", "센트럴키친", "센트럴 키친"),
}
LINKWORD = ("메뉴", "menu", "brand", "브랜드", "물류", "system", "시스템", "product", "제품")
JUNK_TAG = re.compile(r"(?is)<(script|style|noscript|svg|head|iframe)[^>]*>.*?</\1>")


def render(url):
    """렌더링된 DOM. 실패하면 빈 문자열."""
    try:
        r = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--mute-audio",
             "--disable-extensions", "--hide-scrollbars", "--window-size=1280,2400",
             "--virtual-time-budget=" + BUDGET, "--dump-dom", url],
            capture_output=True, timeout=70)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def to_text(dom):
    s = JUNK_TAG.sub(" ", dom)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|td|h[1-6]|a|span|dt|dd)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t　]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def pick_links(dom, base_url, guess=True):
    """실제 링크를 먼저, 흔한 경로 추측은 뒤에.
    🔴 추측 경로는 **첫 페이지에서만** 붙인다(2026-07-26): 2단계에서도 붙였더니
       `/menu/menu/` `/menu/product` 같은 가짜 주소가 16쪽을 다 잡아먹고
       정작 진짜 탭인 `/menu/?type=사이드` `?type=음료` 가 큐에 못 들어갔다."""
    host = urllib.parse.urlparse(base_url).netloc
    out, seen = [], set()
    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', dom):
        href, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        u = urllib.parse.urljoin(base_url, href).split("#")[0]
        if urllib.parse.urlparse(u).netloc != host or u in seen:
            continue
        blob = (href + " " + label).lower()
        if any(w.lower() in blob for w in LINKWORD):
            seen.add(u)
            out.append(u)
    out.sort(key=lambda u: 0 if re.search(r"(menu|메뉴|product)", u, re.I) else 1)
    if not guess:
        return out
    # 링크에 메뉴 쪽이 없을 때를 대비한 흔한 경로 (큰맘할매순대국의 /html/menu.html 이 이렇게 잡혔다)
    root = "%s://%s/" % urllib.parse.urlparse(base_url)[:2]
    pre = []
    for g in ("menu/", "menu", "menu.html", "html/menu.html", "sub/menu.html", "brand/"):
        u = urllib.parse.urljoin(root, g)
        if u not in seen:
            seen.add(u)
            pre.append(u)
    return out + pre


def scan(text):
    hits = {}
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for kind, words in SIG.items():
        for w in words:
            for l in lines:
                if w in l and 6 <= len(l) <= 220:
                    hits.setdefault(kind, []).append({"word": w, "line": l})
                    break
    return hits


def do_brand(b):
    """🔴 2단계로 돈다(2026-07-26 사고).
    전에는 **첫 페이지에서만** 링크를 뽑았다. 그런데 카테고리 탭은 **메뉴 페이지 안에** 있다.
    설빙: /menu/ 안에 `<a href="/menu/?type=사이드">` `?type=음료` 가 있어서
    첫 페이지만 보면 사이드·음료 메뉴를 영원히 못 본다(대표 지적: "사이드도 있고 음료도 있는데").
    그래서 메뉴·상품 페이지에서는 **거기 링크를 한 번 더** 따라간다."""
    url = b["u"]
    dom = render(url)
    texts, pages = [], []
    if not dom:
        allt = ""
    else:
        texts.append(to_text(dom))
        pages.append(url)
        queue = pick_links(dom, url)[:PER_SITE]
        seen = set(pages)
        while queue and len(pages) < MAX_PAGES:
            u2 = queue.pop(0)
            if u2 in seen:
                continue
            seen.add(u2)
            d2 = render(u2)
            if not d2:
                continue
            texts.append(to_text(d2))
            pages.append(u2)
            # 메뉴·상품 페이지면 그 안의 카테고리 탭을 더 따라간다
            if re.search(r"(menu|메뉴|product)", u2, re.I):
                for u3 in pick_links(d2, u2, guess=False):
                    if u3 not in seen and re.search(r"(menu|product)", u3, re.I):
                        queue.append(u3)
        allt = "\n".join(texts)
    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "%s.txt" % (b["slug"] or b["name"])), "w",
            encoding="utf-8").write(allt)
    rec = {"brand": b["name"], "slug": b["slug"], "url": url, "menus": b["n"],
           "pages": pages, "chars": len(allt), "signals": scan(allt)}
    tag = " ".join("%s%d" % (k, len(v)) for k, v in rec["signals"].items()) or "신호없음"
    print("  ✓ %-16s %7d자 %2d쪽  %s" % (b["name"][:16], rec["chars"], len(pages), tag), flush=True)
    return rec


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("""
        SELECT b.name, b.slug, b.homepage_url u,
               (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) n
        FROM brands b WHERE (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) > 0
        ORDER BY n DESC""")]
    if only:
        rows = [r for r in rows if only in r["name"]]
    print("브랜드 %d곳 · 헤드리스 크롬 렌더링 (동시 %d개, 쪽당 최대 %d)" % (len(rows), WORKERS, PER_SITE),
          flush=True)
    print("", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(do_brand, rows))
    io.open(REPORT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    thin = sum(1 for r in res if r["chars"] < 2000)
    print("", flush=True)
    print("끝. 내용 부실 %d곳 · → %s" % (thin, REPORT), flush=True)


if __name__ == "__main__":
    main()
