# -*- coding: utf-8 -*-
"""쿠팡 수집분 → 재료별 '구매하기' 링크 1건 확정.

우리 재료 이름으로 검색해 받아둔 결과(data/research/coupang/*.json)에서
재료마다 **걸 만한 상품 하나**를 고른다. 결과는 gen_dishes 등이 읽어 버튼을 만든다.

고르는 기준 (대표 지시):
  ① 로켓배송 우선 — 배송이 확실해야 링크를 걸 값어치가 있다
  ② 용량이 작은 것 — 집에서 한 번 해먹을 사람이 대상
  ③ 그중 싼 것

⚠️ 이름 검증을 반드시 한다. 검증 없이 최저가만 집으면 엉뚱한 상품이 걸린다
   (실제로 겪음: 연어→갈치, 계란→계란동그랑땡, 아몬드→다이아몬드새우).

⚠️ 쿠팡 응답의 productUrl은 **이미 제휴 추적이 붙은 주소**다. 뒤에 코드를 덧붙이면 안 된다.
   화면에는 파트너스 고지 문구를 반드시 함께 노출할 것(쿠팡 응답 메시지의 요구사항).
"""
import io, os, re, json, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "data", "research", "coupang")
OUT = os.path.join(BASE, "data", "research", "coupang_links.json")

WT = re.compile(r"([\d.]+)\s*(kg|g|l|ml)\b", re.I)
CNT = re.compile(r"(\d+)\s*(?:개|입|팩|봉|병|캔|박스)\b")
HAN = re.compile(r"[가-힣]{2,}")

# 재료가 다른 물건으로 바뀐 형태 — 걸면 안 된다
BAD = ["말랭이", "스틱", "칩", "과자", "쿠키", "케이크", "샐러드", "김밥", "볶음밥",
       "만두", "돈까스", "고로케", "크로켓", "동그랑땡", "후라이", "지단", "너겟",
       "음료", "주스", "라떼", "에이드", "시럽", "잼", "세트", "선물", "베이글",
       "곤약", "컵밥", "즉석", "밀키트", "튀김", "구이", "조림", "무침", "장아찌"]


def core(kw):
    t = HAN.findall(kw)
    return max(t, key=len) if t else None


def size_kg(name):
    m = WT.findall(name)
    if not m:
        return None
    vals = []
    for v, u in m:
        try:
            v = float(v)
        except ValueError:
            continue
        u = u.lower()
        vals.append(v / 1000 if u in ("g", "ml") else v)
    if not vals:
        return None
    total = max(vals)
    c = CNT.search(name)
    if c and total == min(vals):
        try:
            total *= int(c.group(1))
        except ValueError:
            pass
    return total


def pick(kw, items):
    c = core(kw)
    ok = []
    for it in items:
        nm = (it.get("name") or "").replace(" ", "")
        if c and c not in nm:
            continue
        if any(b in nm for b in BAD if b not in (c or "")):
            continue
        kg = size_kg(it.get("name") or "")
        ok.append((0 if it.get("rocket") else 1, kg or 999, it.get("price") or 0, it))
    if not ok:
        return None
    ok.sort(key=lambda x: (x[0], x[1], x[2]))
    _, kg, price, it = ok[0]
    return {"name": it["name"], "price": price,
            "kg": None if kg == 999 else round(kg, 3),
            "rocket": bool(it.get("rocket")), "url": it.get("url"),
            "image": it.get("image"), "id": it.get("id")}


def main():
    out, miss = {}, []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".json"):
            continue
        d = json.load(io.open(os.path.join(SRC, f), encoding="utf-8"))
        p = pick(d["keyword"], d["items"])
        if p:
            out[d["keyword"]] = p
        else:
            miss.append(d["keyword"])
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    rk = sum(1 for v in out.values() if v["rocket"])
    print("링크 확정 %d종 (로켓 %d) / 후보없음 %d종" % (len(out), rk, len(miss)))
    print("저장: %s\n" % os.path.relpath(OUT))
    for k, v in list(out.items())[:12]:
        print("  %-14s %8s원 %s %s" % (k, "{:,}".format(v["price"]),
                                       "🚀" if v["rocket"] else "  ", v["name"][:40]))
    if miss:
        print("\n[후보없음] " + ", ".join(miss[:20]))


main()
