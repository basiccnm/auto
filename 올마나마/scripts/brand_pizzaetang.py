# -*- coding: utf-8 -*-
"""피자에땅 메뉴·가격 수집 — 공식 홈페이지 상세페이지(카페24). 2026-07-31 신설

    python scripts/brand_pizzaetang.py

경로 (화면에서 그대로 확인. 추측 아님)
    상세  /etang_product/menu{N}.html      ← 여기 **텍스트로** 이름·가격이 다 있다
          (목록 /etang/etang_menu.html 에는 이름·설명만 있고 가격이 없다)

🔴 가격은 **이미지가 아니라 텍스트**다(2026-07-31 대표 확인 — 글자 선택됨).
   상세 우측 박스에 이렇게 온다:
       POTATO PIZZA / 포테이토피자
       R 20,900(1판) / 35,800 (1+1할인)
       L 23,900(1판) / 41,800 (1+1할인)
   → R·L 을 각각 한 줄로 만들고, **1판가를 기본**으로 넣는다. 1+1 할인가는 note 로 남긴다.

🔴 이름은 **영문 대문자 제목 다음의 한글**이다(POTATO PIZZA → 포테이토피자).
🔴 menu{N} 은 띄엄띄엄이라 없는 번호가 있다 — 404·가격없음이면 건너뛴다.

결과: data/brand_menu_list/pizzaetang.json
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
ROOT = "https://www.pizzaetang.com"
MAXN = 80
GAP = 0.5
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

# R 20,900(1판) / 35,800 (1+1할인)
# R 20,900(1판) / 35,800 <span>(1+1할인)</span> — 1+1 앞에 태그가 낀다. `[^(]*` 로 넘긴다.
# R/L 라벨이 없는 피자(사이즈 하나)도 있다(menu27) → 라벨은 선택.
RX_PRICE = re.compile(r'(?:([RL])\s*)?([\d,]{4,})\s*\(1판\)\s*/\s*([\d,]{4,})[^(]*\(1\+1', re.I)
# 한글 메뉴명 — 가격 줄 **앞쪽**에서 가장 가까운 한글명을 쓴다(POTATO PIZZA → 포테이토피자)
RX_NAME = re.compile(r'>\s*([가-힣][가-힣A-Za-z0-9 ]{1,18})\s*<')
NAME_SKIP = re.compile(r'주요토핑|^도우$|할인|가격|판$|원산지|영양|알레르|피자에땅|주문|매장|이벤트|브랜드|메뉴$')


def get(path):
    try:
        with urllib.request.urlopen(urllib.request.Request(ROOT + path, headers=UA), timeout=15) as r:
            raw = r.read()
    except Exception:
        return None
    for enc in ("utf-8", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def parse(html):
    """한 상세페이지 → (이름, [(사이즈, 1판가, 1+1가), …]) 또는 None."""
    mp = RX_PRICE.search(html)
    if not mp:
        return None
    prices = RX_PRICE.findall(html)
    # 가격 줄 **앞**에서 가장 가까운 한글명 (설명·라벨은 건너뛴다)
    name = None
    for m in RX_NAME.finditer(html[:mp.start()]):
        cand = m.group(1).strip()
        if not NAME_SKIP.search(cand) and len(cand) >= 2:
            name = cand
    if not name:
        return None
    return name, [(sz, int(a.replace(",", "")), int(b.replace(",", ""))) for sz, a, b in prices]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    menus, seen = [], set()
    for n in range(1, MAXN + 1):
        html = get("/etang_product/menu%d.html" % n)
        time.sleep(GAP)
        if not html:
            continue
        r = parse(html)
        if not r:
            continue
        name, sizes = r
        for sz, base, oneplus in sizes:
            nm = "%s (%s)" % (name, sz) if (sz and len(sizes) > 1) else name
            if nm in seen:
                continue
            seen.add(nm)
            menus.append({"name": nm, "price": base, "price_source": "official",
                          "price_note": "1판 가격. 1+1 할인가 %s원(2판)." % format(oneplus, ","),
                          "cats": [["메뉴", len(menus)]]})
        print("   menu%-3d %s (%d규격)" % (n, name, len(sizes)), flush=True)

    if not menus:
        print("🔴 0개 — 저장하지 않는다. 상세페이지 구조가 바뀐 것이다.")
        return 1
    p = os.path.join(OUT, "pizzaetang.json")
    if os.path.exists(p):
        try:
            old_n = len(json.load(io.open(p, encoding="utf-8")).get("menus") or [])
        except Exception:
            old_n = 0
        if old_n and len(menus) < old_n * 0.7:
            print("🔴 %d개 → %d개로 줄었다. 덮지 않는다." % (old_n, len(menus)))
            return 1
    doc = {"brand": "피자에땅", "slug": "pizzaetang", "source": ROOT + "/etang_product/",
           "collected_at": time.strftime("%Y-%m-%d"),
           "note": "공식 홈페이지 상세(카페24). R/L 각각 한 줄, **1판가 기준**. 1+1 할인가는 각 줄 메모에 있다. "
                   "특수상권(리조트·휴게소·섬)은 가격이 다를 수 있고, 가격은 날마다 달라질 수 있다.",
           "cats": [{"name": "메뉴", "parent": None, "ext_id": "메뉴"}], "menus": menus}
    os.makedirs(OUT, exist_ok=True)
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n✅ 메뉴 %d줄 → %s" % (len(menus), p))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
