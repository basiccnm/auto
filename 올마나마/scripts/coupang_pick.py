# -*- coding: utf-8 -*-
"""쿠팡 검색 결과에서 레시피 페이지에 걸 상품 하나를 고른다.

고르는 기준 (대표 지시, 2026-07-24):
  ① **로켓배송**일 것 — 배송이 확실해야 링크를 걸 값어치가 있다
  ② **용량이 가장 작은 것** — 집에서 한 번 해먹을 사람이 대상이라 업소용 대용량은 안 맞는다
  ③ 그중 **가장 싼 것**

②를 위해 상품명에서 수량을 뽑아 정규화한다. 쿠팡 상품명은 규격이 제각각이라
(`3kg`, `200g, 3개`, `30개입`, `1박스 5kg`) 파싱이 실패하면 **버린다** —
잘못 읽은 수량으로 고르면 엉뚱한 상품이 걸린다.

⚠️ 여기서 고른 가격은 **소비자가**다. 우리 원가(도매)로 쓰면 안 된다.
   원가는 식자재몰(업소용)에서 따로 받는다.
"""
import json, io, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "data", "research", "coupang")
OUT = os.path.join(BASE, "data", "research", "coupang_picked.json")

# 수량 표기: 12.5kg / 200g / 1.8L / 500ml
WT = re.compile(r"([\d.]+)\s*(kg|g|l|ml)\b", re.I)
# '200g, 3개' 처럼 개수가 따로 붙는 경우
CNT = re.compile(r"(\d+)\s*(?:개|입|팩|봉|롤|병|캔)\b")


def size_kg(name):
    """상품명에서 총 중량(kg 또는 L)을 뽑는다. 못 뽑으면 None."""
    m = WT.findall(name)
    if not m:
        return None
    # 여러 개면 가장 큰 값을 총량으로 본다 ('200g, 3개입 600g' → 0.6)
    vals = []
    for v, u in m:
        try:
            v = float(v)
        except ValueError:
            continue
        u = u.lower()
        if u in ("g", "ml"):
            v /= 1000.0
        vals.append(v)
    if not vals:
        return None
    total = max(vals)
    # '200g, 3개' → 단위중량 × 개수
    c = CNT.search(name)
    if c and total == min(vals):
        try:
            total *= int(c.group(1))
        except ValueError:
            pass
    return total


HAN = re.compile(r"[가-힣]{2,}")

# 재료가 다른 물건으로 바뀐 형태 — 이게 걸리면 그 재료의 시세가 아니다
BAD = ["말랭이", "스틱", "칩", "과자", "빵", "케이크", "쿠키", "샐러드", "김밥",
       "볶음밥", "만두", "돈까스", "고로케", "크로켓", "동그랑땡", "후라이",
       "음료", "주스", "라떼", "에이드", "차 ", "티백", "세트", "선물"]


def core_token(kw):
    """검색어에서 가장 긴 한글 토큰 = 그 재료의 핵심어.
    'CJ 다담 부대찌개 양념' → '부대찌개',  '곰곰 매콤 떡볶이 양념' → '떡볶이'"""
    toks = HAN.findall(kw)
    return max(toks, key=len) if toks else None


def pick(kw, items):
    core = core_token(kw)
    cand = []
    for it in items:
        if not it.get("rocket"):          # ① 로켓배송만
            continue
        nm = (it.get("name") or "").replace(" ", "")
        # ⚠️ 이름 검증 없이 고르면 엉뚱한 상품이 그 재료로 둔갑한다.
        #    (부대찌개양념 → 순두부찌개소스 / 고구마 → 고구마말랭이 로 실제 걸렸다)
        if core and core.replace(" ", "") not in nm:
            continue
        if any(b.strip() in nm for b in BAD if b.strip() not in (core or "")):
            continue
        kg = size_kg(it.get("name") or "")
        if not kg or kg <= 0:             # 수량을 못 읽으면 버린다
            continue
        cand.append((kg, it.get("price") or 0, it))
    if not cand:
        return None
    # ② 용량 최소 → ③ 그중 최저가
    cand.sort(key=lambda x: (x[0], x[1]))
    kg, price, it = cand[0]
    return {"name": it["name"], "price": price, "size_kg": round(kg, 3),
            "won_per_kg": round(price / kg), "url": it["url"],
            "image": it.get("image"), "id": it.get("id"), "rocket": True}


def main():
    out, none_rocket, no_size = {}, [], []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".json"):
            continue
        d = json.load(io.open(os.path.join(SRC, f), encoding="utf-8"))
        kw, items = d["keyword"], d["items"]
        p = pick(kw, items)
        if p:
            out[kw] = p
        elif not any(i.get("rocket") for i in items):
            none_rocket.append(kw)
        else:
            no_size.append(kw)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))

    print("고름 %d종 / 로켓없음 %d종 / 수량파싱실패 %d종\n" % (
        len(out), len(none_rocket), len(no_size)))
    for kw, p in list(out.items()):
        print("%-16s %8s원  %6skg  %s" % (kw, f"{p['price']:,}", p["size_kg"], p["name"][:44]))
    if none_rocket:
        print("\n[로켓배송 상품 없음]", ", ".join(none_rocket))
    if no_size:
        print("\n[수량 못 읽음]", ", ".join(no_size))


main()
