# -*- coding: utf-8 -*-
"""던킨도너츠 메뉴 수집 — 공식 홈페이지(서버 렌더). 2026-07-31 신설

    python scripts/brand_dunkin.py

경로 (2026-07-31 확인 · 화면의 링크에서 그대로 읽은 것. 추측 아님)
    GET /menu?cat={대}                    대분류 첫 장 + 소분류 링크 + 페이지 버튼
    GET /menu?cat={대}&sub={소}&page=N     소분류 N번째 장
    상품 링크는 `/menu/view?cat=..&sub=..&id=..`

  대분류 cat: 1 DONUT · 2 FOOD · 6 COFFEE · 3 BEVERAGE · 5 SNACK & MORE
  소분류 sub 는 **첫 장에서 읽는다.** 번호를 추측해 찔러보지 않는다.
  총 장수는 **페이지 버튼(`&page=N`)의 최대값**으로 안다 — 없는 장을 부르지 않는다.

🔴 **가격이 없다.** 던킨 공식은 제품명·설명만 싣는다 → 이름만 넣고 가격은 뒤 단계에서.
⚠️ 요청 간격 1초 이상. 같은 날 파리바게트에서 파라미터를 바꿔 방화벽에 막혔다.

결과: data/brand_menu_list/dunkin.json
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
ROOT = "https://www.dunkindonuts.co.kr"
TOPS = [("DONUT", 1), ("FOOD", 2), ("COFFEE", 6), ("BEVERAGE", 3), ("SNACK & MORE", 5)]
GAP = 1.1
MAX_PAGE = 20

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Referer": ROOT + "/menu"}

# 🔴 상품 링크가 **두 가지**다 (2026-07-31 확인) — 커피만 `viewProductCat` 를 쓴다.
#    `view` 만 보다가 COFFEE 카테고리를 통째로 0개로 놓쳤다.
RX_VIEW = re.compile(
    r'<a[^>]+href="[^"]*?/menu/(?:view|viewProductCat)\?cat=(\d+)&(?:amp;)?sub=(\d+)'
    r'&(?:amp;)?id=(\d+)"[^>]*>(.*?)</a>', re.S | re.I)
RX_SUB = re.compile(r'href="[^"]*?/menu\?cat=(\d+)&(?:amp;)?sub=(\d+)"[^>]*>(.*?)</a>', re.S | re.I)
RX_PAGE = re.compile(r'/menu\?cat=\d+(?:&(?:amp;)?sub=\d+)?&(?:amp;)?page=(\d+)', re.I)
RX_ALT = re.compile(r'\salt="([^"]{2,60})"')


def get(path):
    req = urllib.request.Request(ROOT + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def txt(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'"))
    return re.sub(r"\s+", " ", s).strip()


def items_of(html):
    """상품 링크 덩이에서 이름을 뽑는다. 링크 글자가 비면 `img alt` 를 쓴다."""
    out = []
    for cat, sub, pid, inner in RX_VIEW.findall(html):
        name = txt(inner)
        if not name:
            m = RX_ALT.search(inner)
            name = txt(m.group(1)) if m else ""
        if name and len(name) >= 2:
            out.append((name, pid))
    seen, res = set(), []
    for n, pid in out:
        if pid in seen:
            continue
        seen.add(pid)
        res.append((n, pid))
    return res


def subs_of(html, cat):
    out, seen = [], set()
    for c, sub, inner in RX_SUB.findall(html):
        if c != str(cat):
            continue
        lb = txt(inner)
        if lb and lb.upper() != "ALL" and sub not in seen:
            seen.add(sub)
            out.append((lb, sub))
    return out


def last_page(html):
    ns = [int(x) for x in RX_PAGE.findall(html)]
    return min(max(ns), MAX_PAGE) if ns else 1


def all_items(cat, sub=None):
    q = "/menu?cat=%d" % cat + ("&sub=%s" % sub if sub else "")
    html = get(q)
    got = items_of(html)
    last = last_page(html)
    for p in range(2, last + 1):
        time.sleep(GAP)
        more = items_of(get(q + "&page=%d" % p))
        if not more:
            break
        have = {pid for _, pid in got}
        got += [(n, pid) for n, pid in more if pid not in have]
    return got


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cats, menus, seen = [], [], set()
    for top, cat in TOPS:
        head = get("/menu?cat=%d" % cat)
        subs = subs_of(head, cat)
        print("■ %s (cat=%d) — 소분류 %d개" % (top, cat, len(subs)), flush=True)
        time.sleep(GAP)
        targets = subs or [(None, None)]
        made_top = False
        for lb, sub in targets:
            got = all_items(cat, sub)
            label = lb or top
            if not got:
                print("   - %-18s 0개" % label[:18])
                time.sleep(GAP)
                continue
            if not made_top:
                cats.append({"name": top, "parent": None, "ext_id": str(cat)})
                made_top = True
            if lb:
                cats.append({"name": lb, "parent": top, "ext_id": sub})
                path = "%s/%s" % (top, lb)
            else:
                path = top
            for i, (n, pid) in enumerate(got):
                nm = n if n not in seen else "%s (%s)" % (n, label)
                seen.add(nm)
                menus.append({"name": nm, "price": None, "price_source": None,
                              "ext_id": pid,
                              "detail_url": "%s/menu/view?cat=%d&sub=%s&id=%s"
                                            % (ROOT, cat, sub or "", pid),
                              "note": "",
                              "cats": [[path, i]]})
            print("   · %-18s %3d개" % (label[:18], len(got)))
            time.sleep(GAP)

    # 🔴 실패가 기존 자료를 지우면 안 된다 (2026-07-31 빕스 빈 JSON 사고)
    if not menus:
        print("🔴 0개 — 저장하지 않는다. 화면 구조를 확인할 것.")
        return 1
    p = os.path.join(OUT, "dunkin.json")
    if os.path.exists(p):
        try:
            old_n = len(json.load(io.open(p, encoding="utf-8")).get("menus") or [])
        except Exception:
            old_n = 0
        if old_n and len(menus) < old_n * 0.7:
            print("🔴 %d개 → %d개로 줄었다. 덮지 않는다." % (old_n, len(menus)))
            return 1
    doc = {"brand": "던킨도너츠", "slug": "dunkin", "source": ROOT + "/menu?cat=1",
           "collected_at": time.strftime("%Y-%m-%d"),
           "note": "공식 홈페이지 메뉴 목록. 던킨은 공식에 **가격을 싣지 않는다** — 이름만.",
           "cats": cats, "menus": menus}
    os.makedirs(OUT, exist_ok=True)
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n✅ 탭 %d · 메뉴 %d개 → %s" % (len(cats), len(menus), p))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
