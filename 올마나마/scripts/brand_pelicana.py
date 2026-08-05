# -*- coding: utf-8 -*-
"""페리카나 메뉴판 — 공식 홈페이지 **자체 API** 로 카테고리·메뉴·가격·원산지를 받아 JSON 한 장을 만든다. 2026-07-28

    python scripts/brand_pelicana.py

⛔ 이 스크립트는 **DB 를 건드리지 않는다.** 만드는 건 `data/brand_menu_list/pelicana.json` 뿐이다.
   적재는 `brand_menu_import.py` 가 따로 한다.

사이트 실측 (2026-07-28)
------------------------
🔴 `https://pelicana.co.kr/` 은 **Nuxt SPA** 다. HTML(907KB)을 긁으면 안 된다 —
   `__NUXT__` 안에는 `codeList`·약관 따위만 있고 **메뉴는 0건**이다(`goodsNm` 0회, `치폴릭` 0회).
   `/menu/list` 원문의 메뉴 자리는 `<ul></ul>` 로 비어 있다.

🔴 화면이 실제로 부르는 주소는 **브라우저 콘솔**에서 잡았다(`read_network_requests` 는 비어 있었다):

       performance.getEntriesByType('resource').map(x=>x.name)
         .filter(u=>/api|json|menu|goods|product/i.test(u))

   그렇게 나온 것이 아래 4개다. 전부 GET·인증 없음·`urllib` 로 그냥 읽힌다(SSL 검증만 끈다).

   | 주소 | 주는 것 |
   |---|---|
   | `/api/goods/category`                      | 카테고리 8개 (배열 순서 = 화면 탭 순서) |
   | `/api/goods/list?scmNo=1&cateCd=<코드>`     | 그 탭의 메뉴 + **판매가** |
   | `/api/goods/list/new`                      | 「신제품」탭 (아래 ⚠️) |
   | `/api/goods/detail?goodsNo=<번호>&scmNo=1`  | **원산지·조리전중량·알레르기** |
   | `/api/goods/allergie`                      | `/menu/origin` 페이지 = 메뉴별 원산지 표 (대조용) |

⚠️ **「신제품」(cateCd `001001`) 은 `/api/goods/list` 가 빈 배열을 준다.** 사이트가 막은 게 아니라
   그 탭만 화면 컴포넌트가 다르다 — `/api/goods/list/new` → `result_data.special[]` 에서 온다.
   그쪽에는 가격이 없고 `menuCode`(= goodsNo) 만 있으므로 **가격은 상세 API 에서 가져온다.**
   (같은 상품이라 다른 탭의 값과 동일하다. 스크립트가 어긋나면 ⚠️ 로 출력한다)

⚠️ 카테고리 `cateCd` 는 계층 코드처럼 생겼다(`001002007` 의 상위가 `001002`) 지만
   **`001002` 는 API 가 주지도 않고 화면에도 없다.** 화면 탭은 8개가 **평평하게** 한 줄이다.
   없는 상위 카테고리(「치킨」)를 지어내지 않는다 → `parent` 는 전부 null.

⚠️ **순서 필드가 없다.** `cateSort` 는 `001001`=0, `001003`=7, 하위들은 0~5 로 따로 매겨져 있어
   그것만으로는 화면 순서가 안 나온다. 대신 **API 배열 순서가 화면 순서와 정확히 일치**한다
   (화면: 신제품·오리지널·순살치킨·다리치킨·날개치킨·페리윙봉·스페셜치킨·사이드 — 실측 확인).
   그래서 배열 순서를 쓴다.

⚠️ 가격 `goodsPrice` 는 **옵션이 있는 메뉴에서도 기본 옵션가와 같다**(화이트딥 치폴릭치킨 24,000 =
   옵션 「오리지날(뼈)」 24,000. 순살·다리는 26,000). `optionPrice` 는 **증감이 아니라 절대가**다.
   bhc 처럼 «본품 + 옵션» 으로 더하면 안 된다.

⚠️ 원산지 `originNm` 은 **메뉴마다 따로** 들어 있다(`닭고기: 국내산` · `근위: 국내산` · `닭발: 국내산`).
   원산지가 아예 없는 메뉴(치즈볼·떡볶이 등 닭 안 들어가는 사이드)는 **빈칸으로 둔다.**
⚠️ 알레르기는 상세의 `goodsSearchWord` 에 들어 있다(검색어 칸을 돌려쓴 것). 화면 「알레르기 정보」와 일치.
   `/api/goods/allergie` 표와 대조해 어긋나면 출력한다.
⚠️ 이름 끝에 공백이 붙어 오는 것이 여럿이다(`순살후라이드 `·`페리치즈볼 `). **공백만** 정리하고
   글자는 다듬지 않는다.
⚠️ 이미지 호스트는 `https://pcdn.pelicana.co.kr` 다(`imagePath` + `imageName`). `imagePath` 는
   `/data/TB_MENU_MAIN/` 과 `/uploadFiles/TB_MENU_MAIN/` 두 가지가 섞여 있다.

가격은 매장/채널을 고르기 전 **공식 메뉴 페이지가 그대로 보여주는 값**이다. 배달가가 아니다.
다만 사이트가 «매장별/판매 채널별로 가격이 상이할 수 있습니다» 라고 스스로 밝혀두고 있다.
"""
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")     # 콘솔이 cp949 라 이모지에서 죽는다

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "pelicana.json")

BRAND = "페리카나"
SLUG = "pelicana"
API = "https://www.pelicana.co.kr/api/goods"
SOURCE = API + "/list?scmNo=1&cateCd=001002007"    # 실제로 쓴 주소(대표 1개)
SOURCES = [API + "/category",                      # 실제로 부른 것 전부
           API + "/list?scmNo=1&cateCd=<cateCd>",
           API + "/list/new",
           API + "/detail?goodsNo=<goodsNo>&scmNo=1",
           API + "/allergie"]
IMG_HOST = "https://pcdn.pelicana.co.kr"
DETAIL = "https://www.pelicana.co.kr/menu/detail?goodsNo=%s"
COLLECTED_AT = time.strftime("%Y-%m-%d")

NEW_CATE = "001001"          # 「신제품」 — goods/list 가 0건, list/new 로 온다
GAP = 0.6

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept": "application/json"}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def api(path):
    req = urllib.request.Request(API + path, headers=UA)
    d = json.load(urllib.request.urlopen(req, timeout=30, context=CTX))
    if d.get("result_code") != "200":
        raise RuntimeError("%s → %s" % (path, d.get("result_message")))
    return d["result_data"]


def sp(s):
    """공백만 정리한다. 글자는 건드리지 않는다."""
    return re.sub(r"\s+", " ", (s or "")).strip()


def blank(v):
    """사이트가 «없음» 을 `-` 로 적는 칸이 있다. 값이 아니라 빈칸이다."""
    v = sp(v)
    return None if v in ("", "-", "–", "—") else v


def img(o):
    p, n = o.get("imagePath"), o.get("imageName")
    return IMG_HOST + p + n if p and n else None


def is_menu(name, cat_names):
    """메뉴가 아닌 줄 거르기 — 문장부호로 끝남 / 18자 이상 / 카테고리 이름과 같음."""
    if not name:
        return False, "이름이 비었다"
    if name[-1] in ".!?…~":
        return False, "문장부호로 끝난다"
    if len(name) >= 18:
        return False, "18자 이상"
    if name in cat_names:
        return False, "카테고리 이름과 같다"
    return True, None


def main():
    # ── ① 카테고리 — 배열 순서가 곧 화면 탭 순서다 ────────────────────
    raw_cats = api("/category")
    cats = [{"name": sp(c["cateNm"]), "parent": None, "ext_id": c["cateCd"]}
            for c in raw_cats]
    if not cats:
        print("🔴 카테고리 0개 — 저장하지 않는다")
        return
    cat_names = {c["name"] for c in cats}
    print("카테고리 %d개: %s" % (len(cats), " · ".join(c["name"] for c in cats)))

    # ── ② 탭마다 메뉴 ─────────────────────────────────────────────
    items, order, dropped = {}, [], []

    def take(cat_name, rows):
        """rows = [(goodsNo, name, price_or_None, image_url)] — 나온 순서 그대로"""
        kept = 0
        for r in rows:
            gno, name, price, image = r
            ok, why = is_menu(name, cat_names)
            if not ok:
                dropped.append((cat_name, name, why))
                continue
            it = items.get(gno)
            if it is None:
                it = {"name": name, "ext_id": str(gno), "price": price,
                      "price_source": "official" if price is not None else None,
                      "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                      "detail_url": DETAIL % gno, "image_url": image, "cats": []}
                items[gno] = it
                order.append(gno)
            else:
                # 「신제품」이 먼저 잡히는데 그쪽엔 가격·이미지가 없다 → 뒤 탭에서 채운다
                if price is not None and it["price"] is None:
                    it["price"], it["price_source"] = price, "official"
                if image and not it["image_url"]:
                    it["image_url"] = image
            it["cats"].append([cat_name, kept])
            kept += 1

    for c in cats:
        cd = c["ext_id"]
        if cd == NEW_CATE:
            # ⚠️ 이 탭만 화면 컴포넌트가 다르다 — goods/list 는 0건을 준다
            sp_list = (api("/list/new") or {}).get("special") or []
            rows = [(int(x["menuCode"]), sp(x["title"]), None, None) for x in sp_list]
            note = "  (list/new · 가격 없음 → 상세에서)"
        else:
            rows = [(g["goodsNo"], sp(g["goodsNm"]),
                     int(g["goodsPrice"]) if g.get("goodsPrice") is not None else None,
                     img(g)) for g in api("/list?scmNo=1&cateCd=" + cd)]
            note = ""
        take(c["name"], rows)
        print("  %-8s %2d개%s" % (c["name"], len(rows), note), flush=True)
        time.sleep(GAP)

    if not order:
        print("🔴 메뉴 0건 — 화면 구조가 바뀌었다. 빈 JSON 을 쓰지 않는다")
        return

    # ── ③ 원산지 대조표 (`/menu/origin` 이 부르는 것) ──────────────────
    origin_tbl = {}
    for grp in api("/allergie"):
        for r in grp.get("cateList") or []:
            origin_tbl[sp(r["menuNm"])] = (blank(r.get("originNm")),
                                           blank(r.get("menuAllergie")))
    print("\n  원산지 표(/menu/origin) %d행" % len(origin_tbl))

    # ── ④ 상세 — 원산지·조리전중량·알레르기 (+ 신제품 가격) ─────────────
    print("  상세 %d건 (간격 %.1f초)" % (len(order), GAP), flush=True)
    failed, price_conflict = [], []
    for n, gno in enumerate(order, 1):
        it = items[gno]
        try:
            d = api("/detail?goodsNo=%s&scmNo=1" % gno)["goodsDetail"]
        except Exception as e:
            failed.append((it["name"], str(e)[:60]))
            time.sleep(GAP)
            continue
        it["origin_raw"] = blank(d.get("originNm"))
        it["weight_raw"] = blank(d.get("goodsBeforeWeight"))
        it["allergy_raw"] = blank(d.get("goodsSearchWord"))
        if it["image_url"] is None:
            it["image_url"] = img(d)
        p = d.get("goodsPrice")
        p = int(p) if p is not None else None
        if it["price"] is None and p is not None:
            it["price"], it["price_source"] = p, "official"
        elif p is not None and it["price"] != p:
            price_conflict.append((it["name"], it["price"], p))
        if n % 15 == 0:
            print("    … %d/%d" % (n, len(order)), flush=True)
        time.sleep(GAP)

    # ── ⑤ 저장 ────────────────────────────────────────────────────
    doc = {"brand": BRAND, "slug": SLUG, "source": SOURCE, "sources": SOURCES,
           "collected_at": COLLECTED_AT,
           "cats": cats, "menus": [items[k] for k in order]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    # ── ⑥ 요약 — **만든 파일을 다시 읽어서** 센다 ──────────────────────
    chk = json.load(io.open(OUT, encoding="utf-8"))
    sub_n = sum(1 for c in chk["cats"] if c.get("parent"))
    n_p = sum(1 for m in chk["menus"] if m.get("price") is not None)
    n_w = sum(1 for m in chk["menus"] if m.get("weight_raw"))
    n_o = sum(1 for m in chk["menus"] if m.get("origin_raw"))
    n_a = sum(1 for m in chk["menus"] if m.get("allergy_raw"))
    links = sum(len(m["cats"]) for m in chk["menus"])
    print("\n■ %s — 카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (BRAND, len(chk["cats"]), sub_n, len(chk["menus"]), n_p))
    print("  중량 %d · 원산지 %d · 알레르기 %d · 카테고리 배치 %d자리" % (n_w, n_o, n_a, links))

    # 원산지 갈래 세기 — 국내산/수입이 섞이면 원가가 갈린다
    tally = {}
    for m in chk["menus"]:
        tally[m["origin_raw"] or "(없음)"] = tally.get(m["origin_raw"] or "(없음)", 0) + 1
    print("  원산지 갈래:")
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("     · %-16s %d개" % (k, v))

    # 상세 원산지 ↔ /menu/origin 표 대조
    miss, diff = [], []
    for m in chk["menus"]:
        t = origin_tbl.get(m["name"])
        if t is None:
            miss.append(m["name"])
        elif t[0] != m["origin_raw"]:
            diff.append((m["name"], m["origin_raw"], t[0]))
    print("  대조 — 표에 없는 메뉴 %d · 값이 다른 메뉴 %d" % (len(miss), len(diff)))
    for nm in miss:
        print("     · 표에 없음: %s" % nm)
    for nm, a, b in diff:
        print("     · 다름: %s  상세=%s  표=%s" % (nm, a, b))

    if price_conflict:
        print("  ⚠️ 목록가≠상세가 %d건:" % len(price_conflict))
        for nm, a, b in price_conflict:
            print("     · %s  목록=%s  상세=%s" % (nm, a, b))
    if failed:
        print("  ⚠️ 상세 실패 %d건: %s" % (len(failed), failed[:5]))
    if dropped:
        print("  ⛔ 버린 줄 %d개 (지우기 전에 눈으로 확인할 것):" % len(dropped))
        for where, nm, why in dropped:
            print("     · [%s] %s — %s" % (where, nm, why))
    else:
        print("  ⛔ 버린 줄 없음")
    print("\n  → %s" % OUT)


if __name__ == "__main__":
    main()
