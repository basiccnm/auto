# -*- coding: utf-8 -*-
# 한솥도시락 (slug=hansot) — https://www.hsd.co.kr/menu/menu_list
#
# 수집 방법: 목록 페이지의 메뉴 데이터는 AJAX 로 온다.
#   POST https://www.hsd.co.kr/api/menu/menu_list/{cate1}/{cate2}  (JSON)
# 이 API 는 urllib/headless fetch 에 403 (WAF). 실브라우저에서 페이지의
# 전역 함수 showMenuList(cate1, cate2) 를 카테고리별로 호출하면 200 으로 렌더된다.
# 브라우저로 19개 하위카테고리를 전부 렌더해 DOM 을 긁은 원본을 _raw/hansot_raw.json 에 저장했고
# 이 스크립트는 그것을 표준 JSON 으로 변환한다. (재수집은 브라우저 단계 필요)
import sys, json, os
from datetime import date
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "brand_menu_list", "_raw", "hansot_raw.json")
OUT = os.path.join(HERE, "..", "data", "brand_menu_list", "hansot.json")


def won(s):
    s = (s or "").replace(",", "").strip()
    return int(s) if s.isdigit() else None


def main():
    raw = json.load(open(RAW, encoding="utf-8"))
    # cats: 상위(parent None) + 하위(parent=상위명), 화면 순서 그대로
    cats = []
    sub_parent = {}      # 하위명 -> 상위명
    for t in raw["tree"]:
        cats.append({"name": t["top"], "parent": None, "ext_id": None})
        for s in t["subs"]:
            cats.append({"name": s["name"], "parent": t["top"], "ext_id": s["cate2"]})
            sub_parent[s["cate2"]] = (s["name"], t["top"])

    menus = []
    for grp in raw["lists"]:
        sub_name = grp["h3"]
        for pos, (name, price, mid) in enumerate(grp["items"]):
            menus.append({
                "name": name.strip(),
                "price": won(price),
                "price_source": "official",
                "price_note": None,
                "compose_raw": None, "weight_raw": None,
                "origin_raw": None, "allergy_raw": None,
                "detail_url": None,
                "image_url": None,
                "ext_id": mid,
                "cats": [[sub_name, pos]],
            })

    out = {
        "brand": "한솥도시락", "slug": "hansot",
        "source": "공식 hsd.co.kr/menu/menu_list — showMenuList AJAX(POST /api/menu/menu_list/{cate1}/{cate2}) 브라우저 렌더 후 DOM 수집",
        "collected_at": str(date.today()), "origin_note": None,
        "cats": cats, "menus": menus,
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    prices = sum(1 for m in menus if m["price"] is not None)
    print(f"cats {len(cats)}(sub {len(sub_parent)}) · menus {len(menus)} · prices {prices}")


if __name__ == "__main__":
    main()
