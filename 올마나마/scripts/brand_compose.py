# -*- coding: utf-8 -*-
"""컴포즈커피 메뉴판 — **앱 API**에서 카테고리·메뉴·가격·원산지·알레르기를 받아 **JSON 한 장**을 만든다. 2026-07-28

    python scripts/brand_compose.py

⛔ 이 스크립트는 **DB 를 건드리지 않는다.** 만드는 건 `data/brand_menu_list/composecoffee.json` 뿐이다.
   `brand_menu_store` 를 import 하지 않는다.

━━━ ① 앱(APK) — **여기가 정본이다** ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
폰에 깔린 APK 를 뽑아 문자열만 읽었다(앱을 실행하지 않았고, 외부에서 받지도 않았다):

    adb -s <기기> shell pm path ci.dvn.composecoffee.app
    adb -s <기기> pull .../base.apk

    `assets/app.config`            → Expo(React Native) 앱, `ci.dvn.composecoffee.app` v1.0.89
    `assets/index.android.bundle`  → **Hermes 바이트코드**. 문자열 테이블을 그대로 읽어
                                     (헤더 128B → 함수헤더 → stringKinds → identifierHashes →
                                      stringTable → overflow → stringStorage) 61,911개 문자열을 얻었다.

    거기 적힌 주소 —
        SERVER_BASE_URL   https://prod-api.composecoffee.cloud
        WEBVIEW_BASE_URL  https://webview.composecoffee.cloud
        경로              /product-categories · /products · /products/{productId} ·
                          /home/product-categories · /shops/{shopId} …
        함수명            getProductCategories · getProductsByProductId · getProductsTodayChoice

    🔴 GET /product-categories          → 앱 「메뉴」 탭 12개 (화면 순서 그대로)
    🔴 GET /products?categoryId={id}    → 그 탭의 상품 (화면 순서 그대로) + `salePrice`
    🔴 GET /products/{productId}        → `serveType`(HOT/ICE) · `ingredients`(원산지·알레르기·컵용량) ·
                                          `description` · `options`
    인증 헤더가 필요 없다(비로그인으로 열린다). 코드값을 넣는 곳도 없다.

    💰 `salePrice` 는 **앱 주문(매장 픽업) 가격** = 홀 매장가다. 배달가가 아니다.
       옵션(샷추가 500 · 디카페인 원두 1,000 …)은 뺀 기본가다.

    ⚠️ HOT/ICE 는 상품이 **따로 등록**돼 있다(`H-아메리카노`·`I-아메리카노`처럼 이름에 이미 붙어 있고
       `serveType` 으로도 온다). 합치지 않는다.

    ⚠️ `/product-categories` 의 `subCategories`(푸드/디저트 밑 와플&케이크·스낵&MD·베이커리)는
       **앱 번들 어디에도 쓰이는 흔적이 없고**(`subCategor…` 문자열 0개) 상품을 하위로 나눠주는
       파라미터도 없다 → 하위 카테고리는 **만들지 않는다.** 없는 것을 지어내지 않는다.

    ⚠️ `GET /products`(전체)에는 메뉴 탭에 없는 그룹이 더 있다 —
       `내맘대로 …`(커스텀 주문용)·`… 컴포즈콤보`(주문화면 세트)·`기타`.
       메뉴판이 아니므로 `menus` 에 넣지 않고 **`extra_menus` 로 따로** 담는다(버리지도 않는다).

━━━ ② 홈페이지는 쓰지 않는다 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`composecoffee.com/index.php?…act=dispCafemenuGalleryList` 도 서버렌더라 읽히지만
**가격이 없고** 앱보다 항목이 적다. 앱이 원산지까지 주므로 홈페이지를 겹쳐 읽지 않는다.
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")     # 콘솔이 cp949 라 이모지에서 죽는다

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "composecoffee.json")

BRAND = "컴포즈커피"
SLUG = "composecoffee"
API = "https://prod-api.composecoffee.cloud"
HDR = {"Accept": "application/json", "User-Agent": "okhttp/4.12.0"}
GAP = 0.35

SOURCE = ("앱 APK(ci.dvn.composecoffee.app, adb 로 폰에서 추출)의 "
          "assets/index.android.bundle(Hermes) 문자열 테이블에서 얻은 주소 — "
          "GET %s/product-categories (메뉴 탭) · GET %s/products?categoryId={id} (탭별 상품·salePrice) · "
          "GET %s/products/{productId} (serveType·원산지·알레르기·컵용량). 인증 불필요"
          % (API, API, API))
COLLECTED_AT = time.strftime("%Y-%m-%d")


def get(path, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(API + path, headers=HDR)
            return json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            if k == tries - 1:
                raise
            print("   ↻ 재시도 %s (%s)" % (path, e), flush=True)
            time.sleep(1.5)


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def blank(v):
    v = (v or "").strip()
    return None if v in ("", "-", "–", "—") else v


def ing_map(detail):
    """`ingredients` → (컵용량, 원산지, 알레르기, 컵안내) — **원문 그대로**, 고쳐 적지 않는다.

    ⚠️ `kind` 가 브랜드 데이터마다 흔들린다 — 알레르기는 `알레르기` 와 `알레르기 정보` 두 가지다.
       `==` 로 잡으면 **절반이 빈칸으로 남는다**(실제로 217/328 만 잡혔었다) → 접두어로 본다.
    ⚠️ `kind:원산지` 안에 `label:컵 용량 안내` 가 섞여 있다 —
       *"일반 음료는 591mL 용량의 컵…"* 는 **원산지가 아니다.** `label` 로 갈라낸다.
    """
    weight = origin = allergy = cupnote = None
    for g in detail.get("ingredients") or []:
        kind = (g.get("kind") or "").strip()
        label = (g.get("label") or "").strip()
        val = (g.get("value") or "").strip()
        if not val:
            continue
        if kind.startswith("원산지"):
            if "원산지" in label or not label:
                origin = val if origin is None else origin + " / " + val
            else:                                # `컵 용량 안내` 같은 다른 안내문
                cupnote = val if cupnote is None else cupnote + "\n" + val
        elif kind.startswith("알레르기"):
            allergy = val if allergy is None else allergy + "\n" + val
        elif "컵용량" in label or "중량" in label or "용량" in label:
            unit = re.search(r"\(([^)]+)\)", label)
            weight = "%s%s" % (val, unit.group(1) if unit else "")     # 예: `591mL`
    return blank(weight), blank(origin), blank(allergy), blank(cupnote)


def main():
    print("① 앱 API — %s" % API)
    cats_raw = get("/product-categories")["data"]
    if not cats_raw:
        print("🔴 카테고리 0개 — **응답 구조가 바뀌었다.** 파일을 쓰지 않는다")
        return
    print("  메뉴 탭 %d개: %s" % (len(cats_raw), " · ".join(c["name"] for c in cats_raw)))
    dropped_sub = [(c["name"], s.get("name"))
                   for c in cats_raw for s in (c.get("subCategories") or []) if s.get("name")]

    cats = [{"name": clean(c["name"]), "parent": None, "ext_id": str(c["id"])} for c in cats_raw]

    items, order, empty_cats = {}, [], []
    for c in cats_raw:
        name = clean(c["name"])
        got = get("/products?categoryId=%s" % c["id"])["data"]
        n = 0
        for grp in got:
            for i, p in enumerate(grp.get("products") or []):
                pid = p["id"]
                it = items.get(pid)
                if it is None:
                    it = {"name": clean(p["name"]),
                          "price": p.get("salePrice"),
                          "price_source": "app",
                          "weight_raw": None, "origin_raw": None,
                          "allergy_raw": None, "compose_raw": blank(p.get("shortDescription")),
                          "detail_url": None,
                          "image_url": p.get("thumbnail") or None,
                          "ext_id": pid,
                          "serve_type": None, "cup_note_raw": None,
                          "sale_state": p.get("saleState"),
                          "cats": []}
                    items[pid] = it
                    order.append(pid)
                it["cats"].append([name, i])
                n += 1
        if n == 0:
            empty_cats.append(name)
        print("  %-14s %-4s %3d개" % (name, c["id"], n), flush=True)
        time.sleep(GAP)

    if not order:
        print("🔴 메뉴 0건 — 조용히 빈 JSON 을 쓰지 않는다")
        return

    # ─── 메뉴 탭 밖의 그룹(주문화면 전용) — 버리지 않고 따로 담는다 ───
    extra_cats, extra_items, extra_order = [], {}, []
    try:
        allp = get("/products")["data"]
        board = set(items)
        for grp in allp:
            gname = clean(grp.get("categoryName"))
            fresh = [p for p in (grp.get("products") or []) if p["id"] not in board]
            if not fresh or len(fresh) != len(grp.get("products") or []):
                continue          # 메뉴 탭에 이미 있는 그룹이다
            extra_cats.append({"name": gname, "parent": None, "ext_id": None})
            for i, p in enumerate(grp["products"]):
                pid = p["id"]
                if pid not in extra_items:
                    extra_items[pid] = {"name": clean(p["name"]), "price": p.get("salePrice"),
                                        "price_source": "app", "weight_raw": None,
                                        "origin_raw": None, "allergy_raw": None,
                                        "compose_raw": blank(p.get("shortDescription")),
                                        "detail_url": None,
                                        "image_url": p.get("thumbnail") or None,
                                        "ext_id": pid, "serve_type": None, "cup_note_raw": None,
                                        "sale_state": p.get("saleState"), "cats": []}
                    extra_order.append(pid)
                extra_items[pid]["cats"].append([gname, i])
        print("  ※ 메뉴 탭 밖 그룹 %d개 · 항목 %d개 → extra_menus 로 분리"
              % (len(extra_cats), len(extra_order)))
    except Exception as e:
        print("  ⚠️ 전체 목록(/products) 실패 — extra 는 비운다: %s" % e)

    # ─── 상세 (serveType·원산지·알레르기·컵용량) ───
    todo = order + extra_order
    pool = dict(items)
    pool.update(extra_items)
    print("② 상세 %d건 — GET /products/{id}" % len(todo))
    n_o = n_a = n_w = n_d = fail = 0
    for k, pid in enumerate(todo):
        try:
            det = get("/products/%s" % pid)["data"]
        except Exception as e:
            fail += 1
            print("   ⛔ 상세 실패 %s (%s)" % (pid, e))
            continue
        it = pool[pid]
        w, o, a, cup = ing_map(det)
        it["weight_raw"], it["origin_raw"], it["allergy_raw"] = w, o, a
        it["cup_note_raw"] = cup
        it["serve_type"] = det.get("serveType") or None
        it["compose_raw"] = it["compose_raw"] or blank(det.get("description"))
        n_w += bool(w)
        n_o += bool(o)
        n_a += bool(a)
        n_d += bool(it["compose_raw"])
        if (k + 1) % 50 == 0:
            print("   … %d/%d" % (k + 1, len(todo)), flush=True)
        time.sleep(GAP)

    # ─── 메뉴가 아닌 것 걸러내기 (지우기 전에 목록으로 출력) ───
    cat_names = {c["name"] for c in cats} | {c["name"] for c in extra_cats}
    removed, flagged = [], []

    def sift(keys, store):
        keep = []
        for pid in keys:
            it = store[pid]
            nm = it["name"]
            if nm in cat_names:
                removed.append((nm, "카테고리 이름과 같다"))
                continue
            # ⚠️ 문장부호·길이는 **지우지 않고 표시만** 한다 — 앱 API 의 `name` 필드라
            #    홍보문구가 섞일 자리가 없다. 지우면 진짜 메뉴가 날아간다.
            if re.search(r"[.!?~]$", nm):
                flagged.append((nm, "문장부호로 끝난다 — 앱 name 이라 남겼다"))
            elif len(nm) >= 18:
                flagged.append((nm, "18자 이상 — 앱 name 이라 남겼다"))
            keep.append(it)
        return keep

    menus = sift(order, items)
    extras = sift(extra_order, extra_items)

    doc = {"brand": BRAND, "slug": SLUG, "source": SOURCE, "collected_at": COLLECTED_AT,
           "price_note": "앱 주문(매장 픽업) 가격 = 홀 매장가. 배달가 아님. "
                         "옵션(샷추가 500원·디카페인 원두 1,000원 등)은 뺀 기본가",
           "temperature_note": "HOT/ICE 는 상품이 따로 등록돼 있다(이름의 `H-`/`I-` + serveType). 합치지 않았다",
           "extra_note": "extra_cats/extra_menus = 앱 「메뉴」 탭에는 없고 주문화면에만 있는 그룹"
                         "(내맘대로 커스텀·컴포즈콤보·기타). 메뉴판이 아니라 따로 담았다",
           "cats": cats, "menus": menus,
           "extra_cats": extra_cats, "extra_menus": extras}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    # ─── 요약 — **만든 파일을 다시 읽어서** 센다 ───
    chk = json.load(io.open(OUT, encoding="utf-8"))
    sub_n = sum(1 for c in chk["cats"] if c.get("parent"))
    n_price = sum(1 for m in chk["menus"] if m.get("price") is not None)
    links = sum(len(m["cats"]) for m in chk["menus"])
    print("\n■ %s — 카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (BRAND, len(chk["cats"]), sub_n, len(chk["menus"]), n_price))
    print("  경로: **앱 API**(홈페이지는 안 씀 — 가격이 없다)")
    print("  원산지 %d · 알레르기 %d · 컵용량 %d · 설명 %d%s"
          % (n_o, n_a, n_w, n_d, " · 상세실패 %d" % fail if fail else ""))
    print("  카테고리 배치 %d자리 · 중복 진열 %d건" % (links, links - len(chk["menus"])))
    print("  extra(주문화면 전용) 카테고리 %d · 항목 %d — 메뉴판에는 넣지 않았다"
          % (len(chk["extra_cats"]), len(chk["extra_menus"])))
    if empty_cats:
        print("  ⚠️ 상품이 0개인 탭: %s (앱에도 비어 있다)" % " · ".join(empty_cats))
    if dropped_sub:
        print("  ⚠️ API 가 주지만 **만들지 않은 하위 카테고리** %d개 — 상품을 나눌 파라미터가 없다:"
              % len(dropped_sub))
        for a, b in dropped_sub:
            print("     · %s > %s" % (a, b))
    if removed:
        print("  ⛔ 지운 줄 %d개:" % len(removed))
        for nm, why in removed:
            print("     · %-40s %s" % (nm[:40], why))
    else:
        print("  ⛔ 지운 줄 없음")
    if flagged:
        print("  ⚠️ 규칙에 걸렸으나 **남긴** 이름 %d개 — 눈으로 볼 것:" % len(flagged))
        for nm, why in flagged:
            print("     · %-44s %s" % (nm[:44], why))
    print("\n  → %s" % OUT)


if __name__ == "__main__":
    main()
