# -*- coding: utf-8 -*-
"""롯데리아(lotteria) 메뉴판 — **JSON 파일 하나만** 만든다. 2026-07-28

    python scripts/brand_lotteria.py                 # 전체 (골격 + 상세)
    python scripts/brand_lotteria.py --no-detail     # 골격만 (상세 78쪽 안 받음)
    python scripts/brand_lotteria.py --no-qsv        # 세트 가격·원산지 단계를 뺀다
    python scripts/brand_lotteria.py --cache         # 받아둔 HTML 재사용 (개발용)

만드는 것 → data/brand_menu_list/lotteria.json   ⛔ DB 는 건드리지 않는다(import 조차 안 한다)

🔴 어디서 오나
   `https://www.lotteeatz.com/brand/ria` **페이지 인라인 스크립트**에 전역 배열이 통째로 있다.
     · `cList` = 탭(카테고리)  — `sortSno` 가 화면 탭 순서다
     · `pList` = 상품          — `presPrdNm`·`sellPrice`·`displayCategoryNm`·`imgPath`
   탭을 눌러도 네트워크 요청이 없다. DOM 을 긁을 필요가 없다.
   ⚠️ 헤드리스 크롬도 필요 없다 — 브라우저 UA 만 붙이면 평문 HTTP 로 같은 506KB 가 온다.

🔴 상세쪽(`/products/introductions/{presPrdId}`)에만 있는 것
     · 설명문(`compose_raw`) · 총중량(`weight_raw`) · 알러지 정보(`allergy_raw`)
     · **연관상품 = 단품/세트 짝.** 세트는 브랜드 탭 목록에 **이름조차 없다**

🔴 세트 가격은 «주문» 쪽에 있다 — 버거킹 `dineInprc` 와 같은 갈래
   브랜드 페이지 `pList` 에는 단품만 있고 세트가 없다. 그런데 **매장 주문 화면**이 세트를 판다:
     ① `GET  /api/v1/stores/search?storeName=…&orderType=QSV`   → 매장코드(`storecd`)
     ② `POST /products/{divcd}/{storecd}/menu?orderType=QSV`     → 그 탭의 메뉴 목록(`menuId`)
        body = `{"categories":[<페이지의 template2.category.children[i].data>]}`
     ③ `GET  /qsv/products/{divcd}/{storecd}/menu/{menuId}?parentCategoryId=..&categoryId=..`
        → 인라인 `var menu = {...}` 의 `products[]` 에 **단품·세트가 나란히** 들어 있다
          `sellUpc` = 판매가 · `code.setSeCode` = `1` 단품 / `2` 세트
   ⚠️ **QSV = 매장(픽업) 주문**이다. HSV(배달) 는 배달가라 쓰지 않는다.
   ✅ 검증: 이 경로의 단품가가 `pList` 본사 기준가와 **한 원도 안 틀리게** 같다(안 같으면 그 매장을 버린다).

🔴 원산지도 «주문» 쪽에만 있다
   원산지 **전용 페이지는 없다**(브랜드 페이지·상세페이지·푸터 링크 전수 확인, 롯데GRS 소개 페이지도 0건).
   상세페이지의 표는 **영양성분**이지 원산지가 아니다 — 여기에 속으면 안 된다.
   진짜 원산지는 ③ 주문 화면 응답의 `detail.originInfoContents` 다:
     `쇠고기 국내산 한우` · `쇠고기 호주산 / 돼지고기 외국산` · `닭고기 국내산`
   ⛔ 「국내산/수입산」으로 바꿔 적지 말고 **원문 그대로** 넣는다(표기가 제각각인 것도 원문이다).
   브랜드 공통 한 장이 아니라 **메뉴마다 다르므로** `origin_note` 는 비우고 `origin_raw` 에 넣는다.

⚠️ Incapsula(WAF) 가 앞에 있다. 간격을 두고 한 건씩 받는다. 몰아 치지 말 것.
⚠️ `pList` 를 못 찾으면 **사이트 구조가 바뀐 것** — 파일을 저장하지 않고 그렇게 알린다.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "lotteria.json")
CACHE = os.path.join(os.environ.get("TEMP") or "/tmp", "lotteria_html")

SRC = "https://www.lotteeatz.com/brand/ria"
DETAIL = "https://www.lotteeatz.com/products/introductions/%s?rccode=brnd_main&brandCode=RIA"
DIVCD = "10"                                # 롯데리아
STORE_Q = "강남일원"                          # 1차 매장(값은 본사 기준가와 대조해 검증한다)
STORE_Q2 = "노원역"                           # 2차 — 1차가 안 파는 세트만 여기서 확인한다
                                            # (두 매장 세트가가 16/16 똑같았다 → 매장별 할인이 아니라 체인 표준가)
STORE_API = "https://www.lotteeatz.com/api/v1/stores/search?storeName=%s&page=1&size=5&orderType=QSV&brandList=10&brandCodeList=LOTTERIA"
QSV_PAGE = "https://www.lotteeatz.com/qsv/products/%s/%s"
QSV_LIST = "https://www.lotteeatz.com/products/%s/%s/menu?orderType=QSV&reservationTime=%s"
QSV_MENU = "https://www.lotteeatz.com/qsv/products/%s/%s/menu/%s?parentCategoryId=%s&categoryId=%s"
IMG = "https://img.lotteeatz.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
GAP = 3.0                                   # WAF — 상세 한 건마다 쉰다
TODAY = "2026-07-28"


# ── 받아오기 ────────────────────────────────────────────────────────────
def get(url, cache_key=None, use_cache=False):
    """받아온다. **실제로 망을 탄 뒤에는 반드시 쉰다** — 캐시가 있어도 없는 것만 새로 받으니
    «캐시 모드니까 안 쉬어도 된다» 로 짜면 그 순간 몰아치게 된다(WAF)."""
    p = os.path.join(CACHE, cache_key) if cache_key else None
    if use_cache and p and os.path.exists(p):
        return open(p, encoding="utf-8").read()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    for tries in range(2):
        try:
            body = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
            break
        except Exception as e:
            if tries:
                print("  ! 실패 %s — %s" % (url[-28:], str(e)[:60]))
                return ""
            time.sleep(GAP * 2)
    if p:
        os.makedirs(CACHE, exist_ok=True)
        open(p, "w", encoding="utf-8").write(body)
    time.sleep(GAP)
    return body


def post(url, payload, referer):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": UA, "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest", "Referer": referer, "Accept": "*/*"})
    try:
        out = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        print("  ! POST 실패 %s" % str(e)[:70])
        out = ""
    time.sleep(GAP)
    return out


def js_object(dom, name):
    """인라인 `var <name> = {...}` 를 중괄호 짝을 세어 꺼낸다."""
    m = re.search(r"(?:var|let|const)\s+" + name + r"\s*=\s*(\{)", dom)
    if not m:
        return None
    i = m.start(1)
    depth, j = 0, i
    while j < len(dom):
        ch = dom[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    try:
        return json.loads(dom[i:j + 1])
    except Exception:
        return None


def js_array(dom, name):
    """인라인 스크립트의 `var <name> = [...]` 를 대괄호 짝을 세어 통째로 꺼낸다."""
    m = re.search(r"(?:var|let|const)?\s*" + name + r"\s*=\s*(\[)", dom)
    if not m:
        return None
    i = m.start(1)
    depth, j = 0, i
    while j < len(dom):
        ch = dom[j]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        j += 1
    try:
        return json.loads(dom[i:j + 1])
    except Exception as e:
        print("  ! %s 파싱 실패: %s" % (name, str(e)[:80]))
        return None


# ── 상세페이지 ──────────────────────────────────────────────────────────
def txt(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&amp;", "&").replace("&nbsp;", " ").replace("&quot;", '"')
    return re.sub(r"\s+", " ", s).strip()


def parse_detail(html):
    """설명문 · 총중량 · 알러지 · 연관상품(단품/세트 짝)"""
    d = {"compose_raw": None, "weight_raw": None, "allergy_raw": None, "related": []}
    head = re.search(r'class="prod-detail-header".*?</div>\s*</div>\s*</div>', html, re.S)
    seg = head.group(0) if head else html
    m = re.search(r'<p class="btext">(.*?)</p>', seg, re.S)
    if m:
        d["compose_raw"] = txt(m.group(1)) or None
    m = re.search(r"<th>\s*총중량\s*</th>\s*<td[^>]*>(.*?)</td>", html, re.S)
    if m:
        v = txt(m.group(1))
        d["weight_raw"] = ("총중량 " + v) if v else None
    m = re.search(r'<div class="btext-tit">\s*알러지 정보\s*</div>\s*<p class="btext">(.*?)</p>', html, re.S)
    if m:
        d["allergy_raw"] = txt(m.group(1)) or None
    rel = re.search(r"이 상품의 연관상품입니다.*?</ul>", html, re.S)
    if rel:
        for mm in re.finditer(r'<span id="([^"]*)" class="opt-name">(.*?)</span>', rel.group(0), re.S):
            nm = txt(mm.group(2))
            if nm:
                d["related"].append((mm.group(1).strip() or None, nm))
    return d


# ── 메뉴 아닌 것 걸러내기 ────────────────────────────────────────────────
def qsv_prices(use_cache, store_q=None, want=None):
    """매장(QSV) 주문 화면에서 **단품·세트 판매가**를 긁어 `{상품코드: (이름, 가격, 세트여부)}` 로 준다.
    ⚠️ 배달(HSV) 이 아니라 매장 픽업(QSV) 이다 — 우리 기준은 홀 매장가다."""
    store_q = store_q or STORE_Q
    js = get(STORE_API % urllib.parse.quote(store_q), "stores_%s.json" % store_q, use_cache)
    try:
        stores = json.loads(js)["content"]
    except Exception:
        print("  ! 매장 검색 실패 — 세트 가격 단계를 건너뛴다")
        return {}, None
    # ⚠️ «SELECT» 같은 컨셉 매장은 취급 품목이 줄어 세트가 통째로 빠진다(강남역SELECT 에서 16/42 밖에 못 채웠다).
    #    이름에 영문 대문자가 섞인 특수 매장을 빼고 **평범한 매장**을 고른다.
    ok = [s for s in stores if s.get("storecd") and s["divcd"] == DIVCD
          and not re.search(r"[A-Z]{2,}", s.get("storeNm") or "")]
    store = (ok or [s for s in stores if s.get("storecd")] or [None])[0]
    if not store:
        print("  ! 롯데리아 매장을 못 찾았다 — 세트 가격 단계를 건너뛴다")
        return {}, None
    scd = store["storecd"]
    print("  매장 %s(%s) 주문화면에서 가격을 읽는다" % (store["storeNm"], scd), flush=True)

    page = get(QSV_PAGE % (DIVCD, scd), "qsv_%s.html" % scd, use_cache)
    tmpl = js_object(page, "template2")               # template2 = QSV(매장) 템플릿 · template = HSV(배달)
    if not tmpl:
        print("  ! QSV 템플릿(template2)을 못 찾았다 — 구조가 바뀌었다")
        return {}, scd
    kids = tmpl.get("category", {}).get("children") or []
    print("  주문 탭 %d개 · %s" % (len(kids), " > ".join(k["data"]["displayCategoryNm"] for k in kids)))

    menus, now = [], time.strftime("%H%M")
    for k in kids:                                    # 화면이 탭을 누를 때마다 하나씩 보낸다 — 그대로 흉내
        key = "qsvlist_%s_%s.json" % (scd, k["data"]["displayCategoryId"])
        p = os.path.join(CACHE, key)
        if use_cache and os.path.exists(p):
            body = open(p, encoding="utf-8").read()
        else:
            body = post(QSV_LIST % (DIVCD, scd, now), {"categories": [k["data"]]},
                        QSV_PAGE % (DIVCD, scd))
            if body:
                os.makedirs(CACHE, exist_ok=True)
                open(p, "w", encoding="utf-8").write(body)
        try:
            menus += json.loads(body)
        except Exception:
            pass

    prices, seen = {}, set()
    print("  주문 메뉴 %d칸 → 상세를 연다" % len(menus), flush=True)
    for n, mm in enumerate(menus, 1):
        mid = mm.get("menuId")
        if not mid or mid in seen:
            continue
        seen.add(mid)
        if want is not None:          # 2차 매장은 **못 채운 것만** 연다 — 몰아 치지 않는다
            base = re.sub(r"\s+", "", mm.get("menuNm") or "")
            if not base or not any(w.startswith(base) for w in want):
                continue
        html = get(QSV_MENU % (DIVCD, scd, mid, mm.get("upperDisplayCategoryId") or "",
                               mm.get("displayCategoryId") or ""),
                   "qsvmenu_%s_%s.html" % (scd, mid), use_cache)
        obj = js_object(html, "menu") if html else None
        if not obj:
            continue
        for p in [obj.get("repProduct")] + (obj.get("products") or []):
            if not p:
                continue
            cd = p.get("prdtcd")
            nm = ((p.get("name") or {}).get("productKorNm") or "").strip()
            up = p.get("sellUpc")
            det = p.get("detail") or {}
            # 🔴 원산지가 여기 있다 — 브랜드 페이지·상세페이지 어디에도 없던 값이다
            org = (det.get("originInfoContents") or "").strip() or None
            alg = (det.get("allergyInfoContents") or "").strip() or None
            if not cd:
                continue
            old = prices.get(cd)
            if old:                                  # 같은 코드가 또 나오면 빈 칸만 메운다
                prices[cd] = (old[0], old[1] or (int(up) if up else None), old[2],
                              old[3] or org, old[4] or alg)
                continue
            prices[cd] = (nm, int(up) if up else None,
                          (p.get("code") or {}).get("setSeCode") == "2", org, alg)
        if n % 25 == 0:
            print("    … %d/%d" % (n, len(menus)), flush=True)
    print("  주문화면에서 얻은 상품가 %d개(세트 %d개)"
          % (len(prices), sum(1 for v in prices.values() if v[2])))
    print("  └ 그 안에 원산지 %d건 · 알러지 %d건이 같이 들어 있다"
          % (sum(1 for v in prices.values() if v[3]), sum(1 for v in prices.values() if v[4])))
    return prices, scd


def suspicious(name, catnames):
    """기준: 문장부호로 끝나거나 · 18자 이상이거나 · 카테고리 이름과 같으면 메뉴가 아니다.
    ⚠️ 걸린 것은 **지우기 전에 반드시 출력**한다. 롯데리아는 진짜 메뉴가 18자를 넘는다
       (`통다리 크리스피치킨버거(그릭랜치)` 18자) — 그래서 상품코드가 있으면 살린다."""
    if name in catnames:
        return "카테고리 이름과 같다"
    if re.search(r"[.!?…]$", name):
        return "문장부호로 끝난다"
    if len(name) >= 18:
        return "18자 이상"
    return None


def main():
    use_cache = "--cache" in sys.argv
    want_detail = "--no-detail" not in sys.argv
    want_qsv = "--no-qsv" not in sys.argv

    print("■ 롯데리아  %s" % SRC, flush=True)
    dom = get(SRC, "brand_ria.html", use_cache)
    if not dom:
        print("🔴 브랜드 페이지를 못 받았다 — 저장하지 않는다")
        return 1
    cl = js_array(dom, "cList")
    pl = js_array(dom, "pList")
    if not pl:
        print("🔴 `pList` 를 못 찾았다 — **사이트 구조가 바뀐 것이다.** 파일을 저장하지 않는다")
        return 1
    if not cl:
        print("🔴 `cList`(탭) 를 못 찾았다 — 카테고리 없이 저장하지 않는다")
        return 1

    # ① 카테고리 — sortSno 가 화면 탭 순서다 (배열 순서보다 우선)
    cl = sorted(cl, key=lambda c: (c.get("sortSno") or 0))
    cats = [{"name": (c.get("displayCategoryNm") or "").strip(), "parent": None,
             "ext_id": c.get("displayCategoryId")} for c in cl]
    catnames = [c["name"] for c in cats]
    print("  탭 %d개 · %s" % (len(cats), " > ".join(catnames)))

    # ② 메뉴 — 같은 상품이 여러 탭에 진열된다(추천메뉴 ↔ 버거). 경로+자리로 이어 붙인다
    menus, by_key, dropped, flagged, seen_cat = [], {}, [], [], {}
    for it in pl:
        name = (it.get("presPrdNm") or it.get("productNm") or "").strip()
        cat = (it.get("displayCategoryNm") or "").strip()
        if not name:
            dropped.append(("(이름 없음)", "presPrdNm 이 비었다"))
            continue
        why = suspicious(name, catnames)
        code = it.get("prdtcd") or it.get("presPrdId")
        if why:
            if not code:
                dropped.append((name, why + " · 상품코드도 없다"))
                continue
            flagged.append((name, why, code))
        pos = seen_cat.get(cat, 0)
        seen_cat[cat] = pos + 1
        key = it.get("presPrdId") or name
        if key in by_key:
            by_key[key]["cats"].append([cat, pos])
            continue
        price = it.get("sellPrice") or it.get("aplyPrice")
        img = None
        if it.get("imgPath") and it.get("imgSystemFileNm"):
            img = "%s%s%s.%s" % (IMG, it["imgPath"], it["imgSystemFileNm"], it.get("imgExtsn") or "png")
        m = {"name": name,
             "price": int(price) if price else None,
             "price_source": "official", "price_note": None,
             "compose_raw": None, "weight_raw": None, "origin_raw": None, "allergy_raw": None,
             "detail_url": DETAIL % it["presPrdId"] if it.get("presPrdId") else None,
             "image_url": img, "ext_id": it.get("prdtcd") or it.get("presPrdId"),
             "cats": [[cat, pos]]}
        by_key[key] = m
        menus.append(m)
    print("  진열 %d칸 → 메뉴 %d개 (가격 있는 것 %d개)"
          % (len(pl), len(menus), sum(1 for m in menus if m["price"])))

    # ③ 상세 — 설명문 · 총중량 · 알러지 · 세트(연관상품)
    sets, seen_set, alias = [], set(), []
    board_names = {m["name"] for m in menus}
    board_codes = {m["ext_id"]: m["name"] for m in menus if m["ext_id"]}
    if want_detail:
        print("  상세 %d쪽 (간격 %.0f초 — WAF)" % (len(menus), GAP), flush=True)
        for n, m in enumerate(menus, 1):
            if not m["detail_url"]:
                continue
            pid = m["detail_url"].split("/")[-1].split("?")[0]
            html = get(m["detail_url"], "d_%s.html" % pid, use_cache)
            if not html:
                continue
            d = parse_detail(html)
            m["compose_raw"] = d["compose_raw"]
            m["weight_raw"] = d["weight_raw"]
            m["allergy_raw"] = d["allergy_raw"]
            for code, nm in d["related"]:
                # ⚠️ 연관상품에는 **탭에 이미 있는 상품이 다른 이름으로** 섞여 온다
                #    (`콜라` = `펩시콜라(R)` LD0009 · `아이스 아메리카노` = `아이스아메리카노(R)` LD0020).
                #    이름은 다르지만 **상품코드가 같으면 같은 메뉴**다 → 탭 쪽 이름을 남기고 버린다.
                if nm == m["name"] or nm in seen_set or nm in board_names:
                    continue
                if code and code in board_codes:
                    alias.append((nm, code, board_codes[code]))
                    continue
                if nm in seen_set:
                    continue
                seen_set.add(nm)
                # 🔴 부모(이 상세페이지의 단품)를 적어둔다 — 나중에 **그 단품의 탭을 물려받는다**
                sets.append({"name": nm, "price": None, "price_source": "official",
                             "price_note": None,
                             "compose_raw": "「%s」 상세의 연관상품" % m["name"],
                             "weight_raw": None, "origin_raw": None,
                             "allergy_raw": None, "detail_url": None, "image_url": None,
                             "ext_id": code, "cats": [], "_parents": [m["name"]]})
            for code, nm in d["related"]:      # 같은 세트가 여러 단품에 걸리면 부모를 전부 모은다
                for s in sets:
                    if s["name"] == nm and m["name"] not in s["_parents"]:
                        s["_parents"].append(m["name"])
            if n % 20 == 0:
                print("    … %d/%d" % (n, len(menus)), flush=True)
        print("  상세: 구성 %d · 중량 %d · 알러지 %d · 연관상품 중 탭에 없는 것 %d"
              % (sum(1 for m in menus if m["compose_raw"]),
                 sum(1 for m in menus if m["weight_raw"]),
                 sum(1 for m in menus if m["allergy_raw"]), len(sets)))
        if alias:
            print("  ♻️ 상품코드가 같아 탭 이름을 남기고 버린 별칭 %d개:" % len(alias))
            for nm, code, keep in alias:
                print("      · %-24s → %s (코드 %s)" % (nm, keep, code))
        n_set = sum(1 for m in sets if "세트" in m["name"] or "콤보" in m["name"])
        print("  └ 그 중 «세트·콤보» %d개 · 그 밖(규격·옵션 이름) %d개" % (n_set, len(sets) - n_set))

    # ④ 세트 가격 — 매장(QSV) 주문 화면. 브랜드 탭에는 없지만 주문 쪽에는 값이 있다
    if want_detail and sets and want_qsv:
        prices, scd = qsv_prices(use_cache)
        if prices:
            bycode = {c: v for c, v in prices.items()}
            byname = {}
            for c, v in prices.items():
                byname.setdefault(re.sub(r"\s+", "", v[0]), v)
            # 검증 — 단품가가 본사 기준가와 같아야 그 매장을 믿을 수 있다
            same = diff = 0
            for m in menus:
                v = bycode.get(m["ext_id"]) or byname.get(re.sub(r"\s+", "", m["name"]))
                if not v or not m["price"]:
                    continue
                if v[1] == m["price"]:
                    same += 1
                else:
                    diff += 1
                    if diff <= 5:
                        print("    ⚠️ 단품가 불일치 %s 본사 %s ≠ 매장 %s" % (m["name"], m["price"], v[1]))
            print("  검증: 단품가 일치 %d · 불일치 %d" % (same, diff))
            # 🔴 원산지 — 브랜드 페이지에도 상세페이지에도 없고 **주문 화면에만** 있다. 원문 그대로 넣는다
            no, na = 0, 0
            for m in menus + sets:
                v = bycode.get(m["ext_id"]) or byname.get(re.sub(r"\s+", "", m["name"]))
                if not v:
                    continue
                if v[3] and not m["origin_raw"]:
                    m["origin_raw"] = v[3]
                    no += 1
                if v[4] and not m["allergy_raw"]:
                    m["allergy_raw"] = v[4]
                    na += 1
            print("  🥩 원산지 %d개 · 알러지 %d개를 주문화면에서 채웠다" % (no, na))
            if diff > same:
                print("  🔴 이 매장 가격이 본사 기준가와 어긋난다 — 세트 가격을 넣지 않는다")
            else:
                got = 0
                for s in sets:
                    v = bycode.get(s["ext_id"]) or byname.get(re.sub(r"\s+", "", s["name"]))
                    if not v:
                        continue
                    s["price"] = v[1]
                    s["price_note"] = ("매장(QSV) 주문 화면 판매가 — 브랜드 메뉴판 탭에는 이 메뉴가 없다 "
                                       "· 배달(HSV)가 아님 · 매장코드 %s" % scd)
                    got += 1
                print("  💰 세트·옵션 가격 %d/%d개를 채웠다 (매장 %s)" % (got, len(sets), scd))
                miss = [s for s in sets if not s["price"]]
                if miss:
                    # 매장마다 취급 품목이 다르다 — **못 채운 것만** 다른 매장에서 확인한다
                    print("  ↻ 못 채운 %d개를 2차 매장에서 확인한다: %s"
                          % (len(miss), " / ".join(s["name"] for s in miss)))
                    want = {re.sub(r"\s+", "", s["name"]) for s in miss}
                    p2, scd2 = qsv_prices(use_cache, STORE_Q2, want)
                    b2c = dict(p2)
                    b2n = {}
                    for c, v in p2.items():
                        b2n.setdefault(re.sub(r"\s+", "", v[0]), v)
                    got2 = 0
                    for s in miss:
                        v = b2c.get(s["ext_id"]) or b2n.get(re.sub(r"\s+", "", s["name"]))
                        if not v:
                            continue
                        s["price"] = v[1]
                        s["price_note"] = ("매장(QSV) 주문 화면 판매가 — 브랜드 메뉴판 탭에는 이 메뉴가 없다 "
                                           "· 배달(HSV)가 아님 · 매장코드 %s" % scd2)
                        got2 += 1
                    print("  💰 2차 매장에서 %d개 추가" % got2)
                left = [s["name"] for s in sets if not s["price"]]
                if left:
                    print("  ❌ 두 매장 다 안 파는 것 %d개(가격 비움): %s" % (len(left), " / ".join(left)))

    # ⑤ 세트 카테고리 — **부모 단품의 탭을 물려받아** 그 탭 맨 뒤에 붙인다
    #    ⛔ 없는 카테고리를 지어내지 않는다. 부모를 못 찾은 것만 남겨 두고 보고한다
    tail = {c["name"]: 0 for c in cats}
    for m in menus:
        for cn, i in m["cats"]:
            tail[cn] = max(tail.get(cn, 0), i + 1)
    by_name = {m["name"]: m for m in menus}
    orphan = []
    for s in sets:
        want = []
        for pn in s.get("_parents", []):
            for cn, _ in by_name.get(pn, {}).get("cats", []):
                if cn not in want:
                    want.append(cn)
        for cn in want:
            s["cats"].append([cn, tail[cn]])
            tail[cn] += 1
        if not s["cats"]:
            orphan.append(s["name"])
    for s in sets:
        s.pop("_parents", None)
    if orphan:
        print("  ⚠️ 부모를 못 찾아 `cats` 가 빈 채로 남은 것 %d개: %s" % (len(orphan), " / ".join(orphan)))
    menus += sets

    # ④ 걸러낸 것 — 지운 것도, 살린 것도 반드시 눈에 보이게
    if flagged:
        flagged = sorted(set(flagged))          # 같은 상품이 두 탭에 진열되면 두 번 걸린다
        print("  ⚠️ 기준에 걸렸지만 **상품코드가 있어 살렸다** %d개:" % len(flagged))
        for nm, why, code in flagged:
            print("      · %-34s %s (코드 %s)" % (nm, why, code))
    if dropped:
        print("  🗑 버린 줄 %d개:" % len(dropped))
        for nm, why in dropped:
            print("      · %-34s %s" % (nm, why))
    else:
        print("  🗑 버린 줄 없음 — pList 는 상품 배열이라 네비 글자가 섞이지 않는다")

    doc = {"brand": "롯데리아", "slug": "lotteria", "source": SRC, "collected_at": TODAY,
           "origin_note": None, "cats": cats, "menus": menus}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("  ✅ %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
