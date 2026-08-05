# -*- coding: utf-8 -*-
"""brand_price_fill — 브랜드 메뉴 JSON(`brand_menu_list/<slug>.json`)의 **빈 가격**을
{메뉴명: 가격} 맵으로 채우는 범용 헬퍼. 2026-07-31 신설.

올마나마 가격 채우기 세션에서 브랜드마다 같은 코드를 재작성하던 것(fill_*.py 12개)을 하나로 모았다.
블로그·다이닝코드·네이버 등에서 뽑은 «이름→가격» 을 넣으면, 정규화 매칭으로 골격을 보존한 채
가격 필드만 채운다.

핵심 규칙 (그동안의 교훈이 그대로 코드로):
  · **빈(null) 가격만 채운다.** 기존 값은 덮지 않는다(overwrite=True 로만 강제).
  · **골격(메뉴목록·카테고리·순서)은 안 건드린다.** price/price_source/price_note 만 손댄다.
  · **지어내지 않는다** — 맵에 없는 메뉴는 그대로 null. 매칭 안 된 맵 key 는 unmatched 로 돌려줘 확인.
  · DB 에 쓰지 않는다. JSON 파일만. (등록·반영은 등록 세션이 한다)

사용:
    from brand_price_fill import fill
    price_map = {"후라이드 치킨": 20900, "간지치킨": 22900}
    r = fill(r"...\\data\\brand_menu_list\\60gye.json", price_map,
             source="blog_estimate",
             note="매장마다 가격 편차 있음 · 표시가는 최저가 기준(블로그 조사 2026-07-31)",
             source_urls=["https://23expo.com/60gye-menu/"])
    print(r)   # {'filled':15,'skipped_existing':0,'unmatched':[...],'priced':15,'total':48}
"""
import io
import json
import re


def norm(s, strip_size=True):
    """메뉴명 정규화 — 공백·괄호·상표기호 제거. strip_size 면 (소/중/대/R/L/M)·꼬리 사이즈도 제거.
    두 이름이 같은 메뉴인지 «느슨하게» 보기 위한 키다."""
    s = re.sub(r"™|®", "", s or "")
    if strip_size:
        s = re.sub(r"\((?:소|중|대|특대|R|L|M|S|라지|점보|레귤러)\)", "", s, flags=re.I)
        s = re.sub(r"\s*[\(（](?:핫|아이스|hot|ice|iced)[\)）]", "", s, flags=re.I)
    return re.sub(r"[\s()（）·・,\-_/]+", "", s).lower()


def fill(json_path, price_map, source="blog_estimate", note=None,
         source_urls=None, overwrite=False, strip_size=True, dry=False):
    """json_path 의 메뉴에 price_map({이름:가격}) 을 채운다.

    반환: {filled, skipped_existing, unmatched(맵에서 안 붙은 이름들), priced, total, still_null}
    """
    d = json.load(io.open(json_path, encoding="utf-8"))
    menus = d.get("menus", [])
    pn = {norm(k, strip_size): (k, v) for k, v in price_map.items()}
    used = set()
    filled = skipped = 0
    for m in menus:
        key = norm(m.get("name", ""), strip_size)
        hit = pn.get(key)
        if not hit:
            continue
        used.add(key)
        if m.get("price") and not overwrite:
            skipped += 1
            continue
        price = hit[1]
        if price in (None, 0):
            continue
        m["price"] = price
        m["price_source"] = source
        if note:
            m["price_note"] = note
        filled += 1
    unmatched = [orig for k, (orig, _) in pn.items() if k not in used]
    if source_urls:
        prev = d.get("price_note_source")
        arr = prev if isinstance(prev, list) else ([prev] if prev else [])
        for u in source_urls:
            if u not in arr:
                arr.append(u)
        d["price_note_source"] = arr
    priced = sum(1 for m in menus if m.get("price"))
    still_null = [m["name"] for m in menus if not m.get("price")]
    if not dry:
        json.dump(d, io.open(json_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {"filled": filled, "skipped_existing": skipped, "unmatched": unmatched,
            "priced": priced, "total": len(menus), "still_null": still_null}


def count(json_path):
    """(총 메뉴수, 가격 채운 수) — 반영 검증용."""
    d = json.load(io.open(json_path, encoding="utf-8"))
    ms = d.get("menus", [])
    return len(ms), sum(1 for m in ms if m.get("price"))


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 2:
        n, p = count(sys.argv[1])
        print("메뉴 %d · 가격 %d" % (n, p))
    else:
        print("사용(카운트): python brand_price_fill.py <json>")
        print("채우기는 import 해서 fill(json, {이름:가격}, source=..., note=...) 로 호출")
