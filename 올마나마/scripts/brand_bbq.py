# -*- coding: utf-8 -*-
"""BBQ치킨(slug `bbq`) 공식 홈페이지 메뉴판 → `data/brand_menu_list/bbq.json`. 2026-07-28

    python scripts/brand_bbq.py

⛔ DB 에 쓰지 않는다. `menu_price_store` 를 import 하지 않는다. **JSON 파일 하나만** 만든다.
⛔ 범용 수집기(brand_menu_list / brand_site_collect / brand_official_import / brand_list_import)를 쓰지 않는다.
   전용 수집기 하나 = 브랜드 하나.

────────────────────────────────────────────────────────────────────────
bbq.co.kr 은 Next.js CSR 이다. `__NEXT_DATA__` 의 `pageProps` 가 **비어 있어**
HTML 을 긁으면 아무것도 안 나온다. 화면이 실제로 부르는 주소만 쓴다
(브라우저 `performance.getEntriesByType('resource')` 로 잡은 것):

    GET /api/delivery/menu/category      ← 카테고리 목록
    GET /api/delivery/menu/{카테고리id}   ← 그 카테고리의 메뉴

`/api/delivery/menu/recommend?searchCategoryList=recommended|new` 는 **빈 배열**을
돌려준다(2026-07-28 실측) → 쓰지 않는다.
⛔ 주소를 추측해 늘리지 마라. 위 둘만이 확인된 주소다.

🔴 가격이 홀 매장가인가 (2026-07-28 확인)
   엔드포인트 이름은 `delivery` 지만 **채널별로 가격을 나누지 않는다**.
   가격 필드는 셋뿐이다:
     menuPrice     본품 판매가. 104개 전부 0 아님          → **이걸 쓴다**
     addPrice      소스·옵션 추가금(0/500/1000/2000)       → 안 씀
     displayPrice  103개가 0, 유일한 예외도 menuPrice 와 같은 값 → 안 씀
   배달가/포장가/매장가가 따로 오지 않고, 대신 불리언 `canDeliver`·`canTakeout` 이
   **104개 전부 true** 다. 기존 `data/research/bbq_official.json` · DB
   `brand_menu_official` 과 대조해도 +N원 같은 일괄 차이가 없다
   (황금올리브치킨™ 23,000 / 황.양.반 24,000 / 자메이카 통다리구이 24,000 …).
   → `price_source:"official"` 로 그대로 쓴다.

⚠️ 「18자 이상은 메뉴가 아니다」 필터는 **끈다**(대표 승인 2026-07-28).
   HTML 긁기 부산물을 거르려던 규칙인데 API 응답엔 부산물이 안 섞이고,
   켜면 진짜 세트 메뉴 4개(`[NEW] 필크런치 더블 PICK 세트` 등)가 죽는다.
   대신 길이로 걸렸을 항목을 **목록으로 출력**해 눈으로 확인한다.

⚠️ 카테고리 순서는 배열 순서를 믿지 말고 `priority` 로 정렬한다
   (bhc 에서 배열 순서를 믿었다가 첫 탭이 틀린 적이 있다).
   BBQ 는 priority 2 가 두 개(17·18)고 3 은 결번이라 **안정정렬**이 필수다.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "bbq.json")

BRAND = "BBQ치킨"
SLUG = "bbq"
ROOT = "https://bbq.co.kr"
CAT_URL = ROOT + "/api/delivery/menu/category"
MENU_URL = ROOT + "/api/delivery/menu/%s"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Referer": ROOT + "/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

GAP = 2.5          # 요청 간격(초). 지시 «2초 이상»
RETRY = 2
LONG_NAME = 18     # 참고용 경고 기준. 거르지는 않는다


def get(url):
    """GET → 파싱된 JSON. 실패하면 RETRY 회까지 재시도."""
    last = None
    for i in range(RETRY + 1):
        if i:
            time.sleep(GAP * 2)
            print("      재시도 %d/%d …" % (i, RETRY))
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, OSError) as e:
            last = e
    raise RuntimeError("GET 실패: %s (%s)" % (url, last))


def weight_of(menu):
    """weightList 는 옵션별 배열이다. 중복 제거 후 등장 순서대로 ' | ' 로 잇는다.
       접두어 '* 조리전 중량 : ' 도 **원문 그대로** 남긴다(다듬지 말 것)."""
    out = []
    for w in menu.get("weightList") or []:
        t = (w.get("weight") or "").strip()
        if t and t not in out:
            out.append(t)
    return " | ".join(out) or None


def origin_of(menu):
    """origin 은 [{"name":"닭고기","region":"국내산"}, …] 구조다."""
    out = []
    for o in menu.get("origin") or []:
        n, r = (o.get("name") or "").strip(), (o.get("region") or "").strip()
        t = ("%s: %s" % (n, r)) if (n and r) else (n or r)
        if t and t not in out:
            out.append(t)
    return ", ".join(out) or None


def main():
    # ── 1) 카테고리 ────────────────────────────────────────────────
    print("[1] 카테고리 목록 …")
    raw_cats = get(CAT_URL)
    if not isinstance(raw_cats, list) or not raw_cats:
        raise RuntimeError("카테고리 응답이 비었다: %r" % (raw_cats,))

    # 배열 순서를 믿지 말고 순서 필드로 정렬. 없으면 배열 순서 유지(안정정렬).
    ORDER_KEYS = ("priority", "sort", "sortSeq", "order")
    okey = next((k for k in ORDER_KEYS if k in raw_cats[0]), None)
    print("    순서 필드: %s" % (okey or "없음 → 배열 순서 사용"))
    if okey:
        raw_cats = sorted(raw_cats, key=lambda c: c.get(okey) or 0)   # stable
    print("    카테고리 %d개: %s" % (
        len(raw_cats), " / ".join(c["categoryName"] for c in raw_cats)))

    cat_names = {c["categoryName"] for c in raw_cats}
    cats = [{"name": c["categoryName"], "parent": None, "ext_id": str(c["id"])}
            for c in raw_cats]   # 응답에 parent/children 필드가 없다 → 전부 None

    # ── 2) 카테고리별 메뉴 ─────────────────────────────────────────
    menus = {}          # 메뉴id → 레코드 (같은 메뉴가 여러 카테고리면 한 줄)
    order = []          # 처음 만난 순서
    dropped, longs = [], []
    rows = 0

    for c in raw_cats:
        time.sleep(GAP)
        print("[2] %s (id=%s) …" % (c["categoryName"], c["id"]), end=" ")
        items = get(MENU_URL % c["id"])
        if not isinstance(items, list):
            raise RuntimeError("메뉴 응답이 배열이 아니다: %s" % c["id"])
        print("%d개" % len(items))

        idx = 0
        for m in items:
            name = m.get("menuName") or ""

            # 메뉴가 아닌 것 거르기 — 문장부호로 끝남 / 카테고리 이름과 동일
            # (길이 기준은 끈다. 아래 longs 로 목록만 남긴다)
            if re.search(r"[.!?…]$", name) or name.strip() in cat_names:
                dropped.append((c["categoryName"], name))
                continue
            if len(name) >= LONG_NAME and name not in longs:
                longs.append(name)          # 같은 메뉴가 여러 카테고리에 있어도 한 번만

            rows += 1
            mid = m["id"]
            if mid not in menus:
                menus[mid] = {
                    "name": name,                       # 원문 그대로(™ 유지)
                    "price": m.get("menuPrice"),        # 🔴 홀/배달 구분 없음. 위 주석 참고
                    "price_source": "official",
                    "weight_raw": weight_of(m),
                    "origin_raw": origin_of(m),
                    "allergy_raw": (m.get("allergy") or "").strip() or None,
                    "detail_url": None,                 # 응답에 상세 URL 필드가 없다
                    "image_url": m.get("menuImageUrl") or None,
                    "ext_id": str(mid),
                    "cats": [],
                }
                order.append(mid)
            menus[mid]["cats"].append([c["categoryName"], idx])
            idx += 1

    # ── 3) 저장 ────────────────────────────────────────────────────
    doc = {
        "brand": BRAND,
        "slug": SLUG,
        "source": CAT_URL,
        "collected_at": time.strftime("%Y-%m-%d"),
        "cats": cats,
        "menus": [menus[i] for i in order],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    if longs:
        print("\n⚠️ 이름이 %d자 이상 — 필터를 켰다면 죽었을 항목 %d개 (살려뒀다):"
              % (LONG_NAME, len(longs)))
        for n in longs:
            print("     %2d자  %s" % (len(n), n))
    if dropped:
        print("\n⚠️ 메뉴가 아니라 판단해 뺀 것 %d개:" % len(dropped))
        for cn, n in dropped:
            print("     [%s] %s" % (cn, n))

    # ── 4) 만든 파일을 **다시 읽어서** 센다 ────────────────────────
    with open(OUT, encoding="utf-8") as f:
        d = json.load(f)
    sub = sum(1 for c in d["cats"] if c["parent"])
    priced = sum(1 for m in d["menus"] if m["price"])
    print("\n" + "─" * 60)
    print("카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (len(d["cats"]), sub, len(d["menus"]), priced))
    print("카테고리 줄 합계 %d → 중복 병합 후 %d개" % (rows, len(d["menus"])))
    print(OUT)


if __name__ == "__main__":
    main()
