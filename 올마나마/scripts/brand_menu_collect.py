# -*- coding: utf-8 -*-
"""브랜드 공식 메뉴를 **링크 글자 그대로** 수집한다. 2026-07-27

🔴 왜 다시 쓰나 (2026-07-27 실패)
   `brand_menu_detail.py` 는 상세페이지 **본문에서 메뉴명을 추측**했다. 그래서 BBQ 에서
   `양념` `구이` `시즈닝` `세트` `음료 선택` 처럼 **옵션 라벨**이 메뉴명으로 잡혔고,
   우리 DB(`BBQ 양념치킨`)와 연결률이 2% 였다. 이름을 추측한 것이 잘못이다.

   ✅ 제대로 된 방법: **메뉴 목록의 링크 글자가 곧 메뉴명이다.**
      `<a href="/products/30392">황금올리브치킨</a>` — 이름과 주소가 짝으로 있다.
      전에는 href 만 쓰고 글자를 버렸다.

   그리고 0쪽이던 48곳은 **상세페이지가 없는 사이트**다(목록 한 장에 다 표시).
   그런 곳은 목록 페이지에서 **이름+가격 짝**을 직접 읽는다.

저장물 (브랜드당 1개 json)
   data/brand_menu/<slug>.json
     {brand, slug, lists:[{url,text}], details:[{url,label,text}]}
   이름을 여기서 판정하지 않는다 — 원문과 라벨만 담고 판정은 `brand_official_import.py` 가 한다.

    python scripts/brand_menu_collect.py --only BBQ
    python scripts/brand_menu_collect.py --top 100
    python scripts/brand_menu_collect.py --only-empty      # 우리 DB에 메뉴 0인 신규 브랜드
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
OUT = os.path.join(BASE, "data", "brand_menu")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BUDGET = "9000"
WORKERS = 4
MAX_LIST = 10            # 목록·카테고리 페이지 상한
MAX_DETAIL = 45          # 상세페이지 상한

JUNK_TAG = re.compile(r"(?is)<(script|style|noscript|svg|head|iframe)[^>]*>.*?</\1>")
LISTWORD = ("메뉴", "menu", "product", "goods", "카테고리", "categor", "brand", "제품")
GUESS = ("menu/", "menu", "menu.html", "html/menu.html", "sub/menu.html", "brand/",
         "product", "products", "menu/index.php")
# 메뉴명이 될 수 없는 링크 글자
BADLABEL = re.compile(
    r"^(홈|메뉴|전체|더보기|다음|이전|닫기|검색|로그인|회원가입|장바구니|주문|주문하기|"
    r"매장\s*찾기|매장찾기|이벤트|쿠폰|공지사항|고객센터|브랜드|브랜드\s*소개|메뉴\s*소개|"
    r"회사소개|채용|창업|창업문의|가맹문의|이용안내|전화주문|마이\s*페이지|"
    r"menu|home|all|more|next|prev|close|search|login|join|order|cart)$", re.I)


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


def anchors(dom, base_url):
    """(주소, 링크글자) 짝. **글자를 버리지 않는다** — 그게 메뉴명이다."""
    host = urllib.parse.urlparse(base_url).netloc
    out, seen = [], set()
    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', dom):
        href = m.group(1)
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        u = urllib.parse.urljoin(base_url, href).split("#")[0].replace("&amp;", "&")
        if urllib.parse.urlparse(u).netloc != host:
            continue
        t = re.sub(r"<[^>]+>", " ", m.group(2))
        t = re.sub(r"&[a-z]+;|&#\d+;", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        k = (u, t)
        if k in seen:
            continue
        seen.add(k)
        out.append({"url": u, "label": t})
    return out


def deeper(u, base):
    """base 목록 페이지보다 아래로(또는 쿼리가 더 붙어) 뻗은 링크인가."""
    if u == base:
        return False
    bp, up = base.split("?")[0].rstrip("/"), u.split("?")[0].rstrip("/")
    if up == bp:
        return "?" in u
    return up.startswith(bp + "/")


def good_label(t):
    if not t or not (2 <= len(t) <= 40):
        return False
    if BADLABEL.match(t.strip()):
        return False
    return bool(re.search(r"[가-힣A-Za-z]", t))


def do_brand(b):
    try:
        return _do(b)
    except Exception as e:
        print("  ✗ %-16s 실패: %s" % (b["name"][:16], str(e)[:60]), flush=True)
        return {"brand": b["name"], "slug": b["slug"], "lists": [], "details": [],
                "error": str(e)[:120]}


def _do(b):
    url = b["u"]
    dom = render(url)
    rec = {"brand": b["name"], "slug": b["slug"], "url": url, "lists": [], "details": []}
    if not dom:
        print("  ✗ %-16s 홈 렌더 실패" % b["name"][:16], flush=True)
        return rec

    root = "%s://%s/" % urllib.parse.urlparse(url)[:2]
    # ① 목록 후보 = 홈의 메뉴 관련 링크 + 흔한 경로
    cand = [a["url"] for a in anchors(dom, url)
            if any(w.lower() in (a["url"] + " " + a["label"]).lower() for w in LISTWORD)]
    cand += [urllib.parse.urljoin(root, g) for g in GUESS]
    cand = list(dict.fromkeys(cand))[:MAX_LIST]

    seen_list, detail = {url}, {}
    for lu in cand:
        if lu in seen_list or len(rec["lists"]) >= MAX_LIST:
            continue
        seen_list.add(lu)
        d2 = render(lu)
        if not d2:
            continue
        rec["lists"].append({"url": lu, "text": to_text(d2)})
        for a in anchors(d2, lu):
            if a["url"] in seen_list or a["url"] == lu:
                continue
            if not deeper(a["url"], lu) and not re.search(
                    r"/products?/\d+|_view\.php|[?&](?:code|idx|no|seq|goods_?no|menu_?id|pcode)=",
                    a["url"], re.I):
                # 목록 아래가 아니면 카테고리 탭일 수 있으니 목록 후보로만 둔다
                if (len(cand) < MAX_LIST * 2
                        and any(w.lower() in a["url"].lower() for w in LISTWORD)):
                    cand.append(a["url"])
                continue
            if good_label(a["label"]) and a["url"] not in detail:
                detail[a["url"]] = a["label"]
            elif a["url"] not in detail:
                detail[a["url"]] = ""       # 라벨이 없어도 주소는 담는다

    # ② 상세페이지 — 라벨 있는 것 먼저
    order = sorted(detail.items(), key=lambda kv: 0 if kv[1] else 1)[:MAX_DETAIL]
    for u, lab in order:
        dd = render(u)
        if not dd:
            continue
        rec["details"].append({"url": u, "label": lab, "text": to_text(dd)})

    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "%s.json" % (b["slug"] or b["name"])), "w",
            encoding="utf-8").write(json.dumps(rec, ensure_ascii=False))
    nl = sum(1 for d in rec["details"] if d["label"])
    print("  %-16s 목록 %2d쪽 · 상세 %2d쪽 · 라벨 %2d개%s" % (
        b["name"][:16], len(rec["lists"]), len(rec["details"]), nl,
        "  ⚠️ 상세 없음(목록에서 읽어야 함)" if not rec["details"] else ""), flush=True)
    return rec


def main():
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 100
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    cond = "= 0" if "--only-empty" in sys.argv else (
        ">= 0" if "--include-empty" in sys.argv else "> 0")
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute("""
        SELECT b.name, b.slug, b.homepage_url u
        FROM brands b WHERE b.published=1 AND COALESCE(b.homepage_url,'') <> ''
          AND (SELECT COUNT(*) FROM menus m WHERE m.brand_id=b.id) %s
        ORDER BY COALESCE(b.frcs_cnt,0) DESC LIMIT ?""" % cond, (top,))]
    if only:
        rows = [r for r in rows if only in r["name"]]
    print("브랜드 %d곳 · 목록 링크 글자로 메뉴명 수집" % len(rows), flush=True)
    print("", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = list(ex.map(do_brand, rows))
    nd = sum(1 for r in res if r["details"])
    nlab = sum(1 for r in res for d in r["details"] if d["label"])
    print("", flush=True)
    print("끝. 상세 있는 브랜드 %d/%d · 라벨 붙은 상세 %d쪽 → data/brand_menu/" % (
        nd, len(res), nlab), flush=True)


if __name__ == "__main__":
    main()
