# -*- coding: utf-8 -*-
# 용우동 (slug=yongwoodong) — http://www.yongwoodong.co.kr
# 메뉴: /2013html/home/subpage/menu.html?category=<code>
# 목록 HTML 의 <ul class="menu-list"> 는 비어 있고(원본 li 는 주석처리),
# JS 가 카테고리별로 li 를 채운다 → 실브라우저 렌더 후 .item-nm 를 카테고리별로 수집.
# 가격은 페이지에 전부 "0 원" 으로만 표기(공개 안 함) → price=null.
# 아래 데이터는 브라우저로 11개 카테고리를 렌더해 수집한 것(화면 순서 그대로).
import sys, json, os
from datetime import date
sys.stdout.reconfigure(encoding="utf-8")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "brand_menu_list", "yongwoodong.json")

# (카테고리코드, 이름, [메뉴명, ...])  — 화면 순서
CATS = [
    ("001", "메뉴소개", []),
    ("002", "우동의맛", ["용우동", "새우튀김우동", "스페셜 어묵우동", "제육볶음우동+밥",
                       "간짬뽕우동+밥", "해물짬뽕우동+밥", "해물백짬뽕우동+밥", "소고기짬뽕우동+밥",
                       "우동알밥세트", "우동돈까스세트"]),
    ("003", "면의맛", ["신선야채쫄면", "쫄면돈까스세트"]),
    ("005", "돈까스의 맛", ["등심돈까스", "고구마치즈돈까스", "치즈돈까스", "왕돈까스"]),
    ("006", "밥의맛", ["순두부찌개", "양푼이 비빔밥", "돌솥육개장", "돌솥김치알밥", "얼큰소고기만두국밥", "돌솥비빔밥"]),
    ("007", "덮밥의맛", ["치킨마요", "제육덮밥", "매운치즈삼겹살덮밥", "돌솥콘치즈닭갈비", "돌솥쭈꾸미덮밥"]),
    ("009", "간식의맛", ["튀김범벅국물떡볶이", "새우볼꼬치", "왕교자튀김만두", "안심치킨까스"]),
    ("010", "짜글이의 맛", ["김치짜글이", "소고기된장짜글이", "버섯불고기짜글이", "제육짜글이", "부대짜글이"]),
    ("011", "여름메뉴", ["물냉면", "비빔냉면", "냉모밀", "냉모밀알밥세트", "냉모밀돈까스세트"]),
    ("014", "오무라이스의 맛", ["오무라이스", "돈까스오무라이스"]),
    ("015", "볶음밥의 맛", ["새우볶음밥", "김치볶음밥", "새우볶음밥돈까스세트", "김치볶음밥돈까스세트"]),
]


def main():
    cats = [{"name": n, "parent": None, "ext_id": c} for c, n, _ in CATS]
    menus = []
    for c, name, items in CATS:
        for pos, mnm in enumerate(items):
            menus.append({
                "name": mnm, "price": None, "price_source": None, "price_note": None,
                "compose_raw": None, "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                "detail_url": None, "image_url": None, "ext_id": None,
                "cats": [[name, pos]],
            })
    out = {
        "brand": "용우동", "slug": "yongwoodong",
        "source": "공식 yongwoodong.co.kr menu.html?category=<code> — 브라우저 렌더 후 .item-nm 수집. 가격은 사이트에 비공개(전부 0원)",
        "collected_at": str(date.today()), "origin_note": None,
        "cats": cats, "menus": menus,
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"cats {len(cats)} · menus {len(menus)} · prices 0 (사이트 비공개)")


if __name__ == "__main__":
    main()
