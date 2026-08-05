# -*- coding: utf-8 -*-
# 본죽 (slug=bonjuk, brdCd=BF101)
# 공식 API 두 주소만 사용 (주소 조합 금지):
#   카테고리: GET https://api.bonif.co.kr/brand/v1/category?brdCd=BF101
#   메뉴:     GET https://api.bonif.co.kr/brand/v1/menu?brdCd=BF101&cmdtCateIdx=<idx>&orderBy=
# cmdtNm=이름, cmdtPrice=가격
import sys, json, urllib.request
from datetime import date
sys.stdout.reconfigure(encoding="utf-8")

BRD = "BF101"
CAT_URL = "https://api.bonif.co.kr/brand/v1/category?brdCd=" + BRD
MENU_URL = "https://api.bonif.co.kr/brand/v1/menu?brdCd={}&cmdtCateIdx={}&orderBy="


def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=25))


def main():
    cats_raw = get(CAT_URL)["data"]["categoryList"]
    cats = [{"name": c["cateNm"].strip(), "parent": None, "ext_id": str(c["cmdtCateIdx"])} for c in cats_raw]

    menus = {}   # cmdtIdx -> menu dict (dedupe across categories)
    order = []   # keep first-seen order
    for c in cats_raw:
        idx = c["cmdtCateIdx"]
        cate_nm = c["cateNm"].strip()
        try:
            lst = get(MENU_URL.format(BRD, idx))["data"]["menuList"]
        except Exception as e:
            print("cat", idx, "err", e)
            continue
        for pos, it in enumerate(lst):
            key = it["cmdtIdx"]
            price = it.get("cmdtPrice") or None
            sale = it.get("cmdtSalePrice") or 0
            note = None
            if sale and price and sale != price:
                note = f"할인가 {sale}"
            if key not in menus:
                menus[key] = {
                    "name": it["cmdtNm"].strip(),
                    "price": price,
                    "price_source": "official",
                    "price_note": note,
                    "compose_raw": None,
                    "weight_raw": None,
                    "origin_raw": None,
                    "allergy_raw": None,
                    "detail_url": f"https://www.bonif.co.kr/brand/menu/detail?brdCd={BRD}&cmdtIdx={key}",
                    "image_url": None,
                    "ext_id": str(key),
                    "cats": [],
                }
                order.append(key)
            menus[key]["cats"].append([cate_nm, pos])

    out = {
        "brand": "본죽", "slug": "bonjuk",
        "source": "공식 API api.bonif.co.kr/brand/v1 (category + menu, 카테고리별 조회)",
        "collected_at": str(date.today()), "origin_note": None,
        "cats": cats,
        "menus": [menus[k] for k in order],
    }
    with open("data/brand_menu_list/bonjuk.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    prices = sum(1 for k in order if menus[k]["price"])
    print(f"cats {len(cats)} · menus {len(order)} · prices {prices}")


if __name__ == "__main__":
    main()
