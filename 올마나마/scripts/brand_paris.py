# -*- coding: utf-8 -*-
"""파리바게트 메뉴 수집 — 공식 홈페이지 자체 AJAX. 2026-07-31 신설

    python scripts/brand_paris.py

경로 (사이트 자체 스크립트가 부르는 것 **그대로**. 추측 아님)
    GET /products/?cat1={대}                                   첫 화면 · 소분류 링크
    GET /wp-admin/admin-ajax.php?action=pb_get_product_list
        &cat1={대}&cat2={소}&per_page=12&paged={N}              목록 (12개씩)
        → 더 없으면 상품이 0개로 온다. 그때 멈춘다.

🚨 **`per_page` 를 바꾸지 마라.** 2026-07-31 한 번에 받으려고 12→100 으로 바꿨다가
   Wordfence 가 **503 「이 사이트에 대한 액세스가 제한되었습니다」** 로 막았다.
   원래 값으로 되돌려도 한동안 계속 503 이었다(몇 시간 뒤 풀림).
   → 사이트가 보내는 요청과 **값 하나까지 똑같이** 보낸다. 사이 간격도 넉넉히 둔다.

🔴 **가격이 없다.** 파리바게트 공식은 제품명·설명만 싣는다 → 이름만. 가격은 뒤 단계에서.
🔴 카테고리는 2단이다(브레드 → 식빵/간식빵/건강빵/도넛/페스츄리-파이 …).
   소분류 이름은 **첫 화면 링크의 `cat2` 값**에서 읽는다.

결과: data/brand_menu_list/paris.json
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
ROOT = "https://www.paris.co.kr"
AJAX = "/wp-admin/admin-ajax.php?action=pb_get_product_list"
TOPS = ["브레드", "케이크", "샌드위치-샐러드", "선물", "디저트-스낵", "커피-음료", "퍼스트클래스키친"]
GAP = 1.4                # 🚨 방화벽에 한 번 막힌 사이트다. 넉넉히 쉰다
MAX_PAGE = 40

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Referer": ROOT + "/products/", "X-Requested-With": "XMLHttpRequest",
      "Accept": "*/*", "Accept-Language": "ko-KR,ko;q=0.9"}

RX_NAME = re.compile(r'class="product-name"[^>]*>(.*?)<', re.S | re.I)
RX_CAT2 = re.compile(r'cat1=([^&"\']+)&(?:amp;)?cat2=([^&"\'#]+)', re.I)


def get(path):
    req = urllib.request.Request(ROOT + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def txt(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))
    return re.sub(r"\s+", " ", s).strip()


def subs_of(html, top):
    """첫 화면에서 그 대분류의 소분류 이름을 읽는다. 번호를 지어내지 않는다."""
    out, seen = [], set()
    for c1, c2 in RX_CAT2.findall(html):
        c1 = urllib.parse.unquote(c1)
        c2 = urllib.parse.unquote(c2)
        if c1 != top or c2 in seen:
            continue
        seen.add(c2)
        out.append(c2)
    return out


def page_items(top, sub, paged):
    q = (AJAX + "&cat1=" + urllib.parse.quote(top)
         + "&cat2=" + urllib.parse.quote(sub)
         + "&per_page=12&paged=%d" % paged)      # 🚨 per_page 는 12 고정
    return [txt(x) for x in RX_NAME.findall(get(q))]


def all_items(top, sub):
    got, page = [], 0
    while page < MAX_PAGE:
        page += 1
        names = page_items(top, sub, page)
        if not names:
            break
        before = len(got)
        for n in names:
            if n and n not in got:
                got.append(n)
        if len(got) == before:
            break
        time.sleep(GAP)
    return got


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cats, menus, seen = [], [], set()
    for top in TOPS:
        head = get("/products/?cat1=" + urllib.parse.quote(top))
        subs = subs_of(head, top)
        print("■ %s — 소분류 %d개" % (top, len(subs)), flush=True)
        time.sleep(GAP)
        if not subs:
            print("   - 소분류를 못 읽었다 — 건너뜀")
            continue
        made = False
        for sub in subs:
            got = all_items(top, sub)
            if not got:
                print("   - %-20s 0개" % sub[:20])
                time.sleep(GAP)
                continue
            if not made:
                cats.append({"name": top, "parent": None, "ext_id": top})
                made = True
            cats.append({"name": sub, "parent": top, "ext_id": sub})
            path = "%s/%s" % (top, sub)
            for i, n in enumerate(got):
                nm = n if n not in seen else "%s (%s)" % (n, sub)
                seen.add(nm)
                menus.append({"name": nm, "price": None, "price_source": None,
                              "cats": [[path, i]]})
            print("   · %-20s %3d개" % (sub[:20], len(got)))
            time.sleep(GAP)

    # 🔴 실패가 기존 자료를 지우면 안 된다 (2026-07-31 빕스 빈 JSON 사고)
    if not menus:
        print("🔴 0개 — 저장하지 않는다. 차단됐거나 화면 구조가 바뀐 것이다.")
        return 1
    p = os.path.join(OUT, "paris.json")
    if os.path.exists(p):
        try:
            old_n = len(json.load(io.open(p, encoding="utf-8")).get("menus") or [])
        except Exception:
            old_n = 0
        if old_n and len(menus) < old_n * 0.7:
            print("🔴 %d개 → %d개로 줄었다. 덮지 않는다." % (old_n, len(menus)))
            return 1
    doc = {"brand": "파리바게트", "slug": "paris", "source": ROOT + "/products/",
           "collected_at": time.strftime("%Y-%m-%d"),
           "note": "공식 홈페이지 자체 AJAX(pb_get_product_list). **가격은 공식에 없다** — 이름만. "
                   "🚨 per_page 를 바꾸면 Wordfence 에 막힌다(2026-07-31 실제 차단). 12 고정.",
           "cats": cats, "menus": menus}
    os.makedirs(OUT, exist_ok=True)
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n✅ 탭 %d · 메뉴 %d개 → %s" % (len(cats), len(menus), p))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
