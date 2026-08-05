# -*- coding: utf-8 -*-
"""쿠팡 수집분 → 우리 재료의 **소매값** 후보를 뽑는 미리보기. DB는 건드리지 않는다.

소매 우선순위 (2026-07-25 확정): 쿠팡 로켓 → 쿠팡 일반 → 외부 사이트

⚠️ 쿠팡은 상품명에 중량이 없는 게 많다. **중량을 못 읽으면 원/kg을 만들지 않는다.**
   추정해서 채우면 "로켓 최저가"가 엉뚱한 소포장으로 잡힌다(실제로 한우 소포장이
   64,500원/kg으로 1위에 올라온 적 있다).
"""
import json, io, os, re, sys, collections

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "data", "research", "coupang")
OUT = os.path.join(BASE, "data", "research", "coupang_소매_소고기.md")

# 재료 → 검색어들. 상품명 필터는 아래 BAD 로 거른다.
MAP = [
    ("우삼겹",           ["우삼겹", "차돌양지"]),
    ("소고기 양지",       ["소고기 양지", "소고기 국거리"]),
    ("차돌박이",         ["차돌박이"]),
    ("소고기 다짐육",     ["소고기 다짐육"]),
    ("소불고기용 쇠고기",  ["소고기 불고기용"]),
    ("소고기 등심",       ["소고기 등심"]),
    ("사골",            ["사골"]),
    ("잡뼈",            ["소 잡뼈"]),
    ("우족",            ["우족"]),
    ("소꼬리",           ["소꼬리"]),
]

# 원물이 아닌 것 — 가공·완제품이 섞여 들어온다
BAD = re.compile(r"곰탕|육수|진국|사골국|만두|라면|즉석|레토르트|파우치|캔|소스|양념장|"
                 r"세트선물|선물세트|건강식품|영양제|사료|간식|개껌|면도기|갈고리|부추")


def weight_kg(name):
    """상품명에서 총 중량(kg). 못 읽으면 None — 추정하지 않는다."""
    s = name.replace(",", "")
    # "800g, 1개" / "1kg" / "300g, 2개" / "5kg, 2세트" 형태
    m = re.findall(r"(\d+(?:\.\d+)?)\s*(kg|g)\b", s, re.I)
    if not m:
        return None
    v, u = m[-1]
    kg = float(v) / (1000.0 if u.lower() == "g" else 1.0)
    # 뒤에 "N개" / "N세트" 가 붙으면 곱한다
    m2 = re.search(r"(\d+)\s*(?:개|세트|팩)\b", s)
    if m2 and kg < 5:
        kg *= int(m2.group(1))
    return kg if 0.05 <= kg <= 50 else None


def origin(name):
    for k in ("국내산", "국산", "한우", "육우", "미국산", "호주산", "뉴질랜드산",
              "멕시코산", "캐나다산", "브라질산"):
        if k in name:
            return k
    return None


def main():
    f = io.open(OUT, "w", encoding="utf-8")
    f.write("# 쿠팡 소매값 후보 — 소고기 (2026-07-25)\n\n")
    f.write("DB 미반영. **로켓 우선**, 중량을 못 읽은 상품은 원/kg 없이 `중량미상`으로 남겼다.\n\n")

    for label, kws in MAP:
        items = []
        for kw in kws:
            p = os.path.join(SRC, kw + ".json")
            if not os.path.exists(p):
                continue
            for it in json.load(io.open(p, encoding="utf-8"))["items"]:
                nm = it["name"]
                if BAD.search(nm):
                    continue
                kg = weight_kg(nm)
                items.append({"kw": kw, "name": nm, "price": it["price"],
                              "rocket": bool(it["rocket"]), "kg": kg,
                              "per_kg": round(it["price"] / kg) if kg else None,
                              "origin": origin(nm), "url": it["url"]})
        f.write("\n## %s\n\n" % label)
        if not items:
            f.write("**후보 없음** — 검색어 자체가 없거나 전부 가공품이었다.\n")
            print("%-16s 후보 없음" % label)
            continue

        prc = [x for x in items if x["per_kg"]]
        rk = sorted([x for x in prc if x["rocket"]], key=lambda x: x["per_kg"])
        gn = sorted([x for x in prc if not x["rocket"]], key=lambda x: x["per_kg"])
        f.write("| 배송 | 원/kg | 원산지 | 가격 | 중량 | 상품명 |\n|---|---:|---|---:|---:|---|\n")
        for x in (rk[:4] + gn[:4]):
            f.write("| %s | %s | %s | %s | %skg | %s |\n" % (
                "로켓" if x["rocket"] else "일반", f"{x['per_kg']:,}", x["origin"] or "-",
                f"{x['price']:,}", x["kg"], x["name"][:52]))
        miss = [x for x in items if not x["per_kg"]]
        if miss:
            f.write("\n중량미상 %d건: %s\n" % (
                len(miss), " / ".join(x["name"][:30] for x in miss[:4])))

        best = rk[0] if rk else (gn[0] if gn else None)
        print("%-16s %s %8s원/kg  %-6s  %s" % (
            label, "로켓" if (best and best["rocket"]) else "일반",
            f"{best['per_kg']:,}" if best else "-",
            (best["origin"] or "-") if best else "-",
            "중량미상 %d건" % len(miss) if miss else ""))
    f.close()
    print("\n→", OUT)


main()
