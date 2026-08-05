# -*- coding: utf-8 -*-
"""브랜드 **원산지·알레르기·영양성분** 페이지를 찾아 긁는다. 2026-07-26

🔴 왜 필요한가 (대표 지적)
   *"메뉴만 알고 재료는 모르는데?? 어떻게 비교해???"*
   *"재료가 알아야 단가가 나오고 그래야 흐름이 이루어짐"*

   메뉴 이름만으로는 DB 재료와 비교가 안 된다. 프랜차이즈는 법으로 공개 의무가 있는 자료가 있다:
     ① 원산지 표시판   — 메뉴별 주요 재료 + 원산지        (원산지표시법)
     ② 알레르기 성분표 — 메뉴별 숨은 재료(계란·우유·밀…)  (어린이 식생활안전관리법)
     ③ 영양성분표     — **1회 제공량(g)** + 열량          (100개 이상 매장 체인 의무)

   ③이 중량 문제를 푼다. 상위 브랜드는 대부분 대형 체인이라 공개돼 있다.

⛔ 여기서 나온 것만 재료 근거로 쓴다. 없으면 비워둔다 — 지어내지 않는다.
   (`ingredients-evidence-only` 규칙: 빈칸이 가짜보다 낫다)

    python scripts/brand_nutrition_crawl.py            # 상위 30곳
    python scripts/brand_nutrition_crawl.py --top 50
    python scripts/brand_nutrition_crawl.py --only BBQ
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
OUT = os.path.join(BASE, "data", "brand_nutrition")
REPORT = os.path.join(BASE, "data", "research", "brand_nutrition.json")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BUDGET = "10000"
WORKERS = 4
MAX_PAGES = 12

# 링크·주소에서 찾을 말
HUNT = ("원산지", "알레르", "알러지", "영양", "성분", "칼로리", "열량",
        "nutrition", "nutrient", "allerg", "origin", "calorie")
JUNK_TAG = re.compile(r"(?is)<(script|style|noscript|svg|head|iframe)[^>]*>.*?</\1>")
# 추측 경로 — 브랜드 사이트에서 흔한 위치
GUESS = ("nutrition", "nutrition.html", "nutrition.php", "allergy", "allergy.html",
         "origin", "origin.html", "menu/nutrition", "brand/nutrition",
         "customer/nutrition", "info/nutrition", "menu/origin", "html/origin.html",
         "sub/nutrition.html", "customer/origin")


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


def hunt_links(dom, base_url):
    """원산지·알레르기·영양 쪽 링크만 고른다."""
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
        if any(w.lower() in blob for w in HUNT):
            seen.add(u)
            out.append(u)
    return out


def marks(text):
    return {"원산지": "원산지" in text,
            "알레르기": ("알레르" in text or "알러지" in text),
            "영양": ("영양" in text or "kcal" in text.lower() or "열량" in text),
            "중량표기": bool(re.search(r"\d+\s*g\b|1회\s*제공량|제공량", text))}


def do_brand(b):
    url = b["u"]
    dom = render(url)
    texts, pages = [], []
    if dom:
        texts.append(to_text(dom))
        pages.append(url)
        root = "%s://%s/" % urllib.parse.urlparse(url)[:2]
        queue = hunt_links(dom, url) + [urllib.parse.urljoin(root, g) for g in GUESS]
        seen = {url}
        while queue and len(pages) < MAX_PAGES:
            u2 = queue.pop(0)
            if u2 in seen:
                continue
            seen.add(u2)
            d2 = render(u2)
            if not d2:
                continue
            t2 = to_text(d2)
            if not marks(t2)["원산지"] and not marks(t2)["알레르기"] and not marks(t2)["영양"]:
                continue                      # 관계없는 쪽은 버린다
            texts.append("=== %s\n%s" % (u2, t2))
            pages.append(u2)
            for u3 in hunt_links(d2, u2):
                if u3 not in seen:
                    queue.append(u3)
    allt = "\n".join(texts)
    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "%s.txt" % (b["slug"] or b["name"])), "w",
            encoding="utf-8").write(allt)
    mk = marks(allt)
    rec = {"brand": b["name"], "slug": b["slug"], "pages": pages,
           "chars": len(allt), "marks": mk}
    print("  %-16s %7d자 %2d쪽  %s" % (
        b["name"][:16], len(allt), len(pages),
        " ".join(k for k, v in mk.items() if v) or "없음"), flush=True)
    return rec


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 30
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("""
        SELECT b.name, b.slug, b.homepage_url u, b.frcs_cnt f
        FROM brands b WHERE b.published=1
          AND (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) > 0
        ORDER BY COALESCE(b.frcs_cnt,0) DESC LIMIT ?""", (top,))]
    if only:
        rows = [r for r in rows if only in r["name"]]
    print("가맹점수 상위 %d곳 · 원산지·알레르기·영양성분 페이지 수집" % len(rows), flush=True)
    print("", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(do_brand, rows))
    io.open(REPORT, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    got = sum(1 for r in res if any(r["marks"].values()))
    print("", flush=True)
    print("끝. 자료 확보 %d/%d곳 → %s" % (got, len(res), REPORT), flush=True)


if __name__ == "__main__":
    main()
