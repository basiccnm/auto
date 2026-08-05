# -*- coding: utf-8 -*-
# 샐러디 (slug=salady) — https://salady.com/menu/list_1
# 목록 페이지는 서버렌더. 각 메뉴는 <li> 안 .info h6 = 한글명, a[href=/menu/view_1?idx=..&ca_id=..].
# 가격은 목록·상세 어디에도 공개 안 함 → price=null.
# 카테고리 = 화면 섹션 순서: 새로운 메뉴 · 베스트 메뉴(브랜드가 미는 하이라이트, 중복 진열 그대로) +
#            샐러디(01)·그레인볼(02)·누들볼(03)·프로틴 박스(04)·랩&샌드위치(05)·나만의 샐러디(07).
# 원본 idx/이름은 브라우저 렌더 후 수집해 _raw/salady_raw.json 에 저장. 이 스크립트가 변환한다.
import sys, json, os
from datetime import date
sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "brand_menu_list", "_raw", "salady_raw.json")
OUT = os.path.join(HERE, "..", "data", "brand_menu_list", "salady.json")


def main():
    raw = json.load(open(RAW, encoding="utf-8"))
    names = raw["names"]
    cats = [{"name": c["name"], "parent": None, "ext_id": c["ca"]} for c in raw["cats"]]

    menus = {}   # idx -> menu dict
    order = []
    for c in raw["cats"]:
        for pos, idx in enumerate(c["items"]):
            if idx not in menus:
                ca = c["ca"]
                menus[idx] = {
                    "name": names[idx], "price": None, "price_source": None, "price_note": None,
                    "compose_raw": None, "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                    "detail_url": f"https://salady.com/menu/view_1?idx={idx}" + (f"&ca_id={ca}" if ca else ""),
                    "image_url": None, "ext_id": idx, "cats": [],
                }
                order.append(idx)
            menus[idx]["cats"].append([c["name"], pos])

    out = {
        "brand": "샐러디", "slug": "salady",
        "source": "공식 salady.com/menu/list_1 — 서버렌더 DOM(.info h6). 가격 비공개",
        "collected_at": str(date.today()), "origin_note": None,
        "cats": cats, "menus": [menus[k] for k in order],
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"cats {len(cats)} · menus {len(order)} · prices 0 (비공개)")


if __name__ == "__main__":
    main()
