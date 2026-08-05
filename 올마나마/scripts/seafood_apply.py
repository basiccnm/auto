# -*- coding: utf-8 -*-
"""수산물 도매값을 **식봄 카테고리** 기준으로 ingredient_price 표에 담는다. (2026-07-25)

검색어는 형태(마른↔냉동↔생)가 섞이지만 카테고리는 형태별로 나뉜다(대표 지시).
소스 = data/research/foodspring/_카테고리.json (nid로 긁은 것).

가드(자동, 확인 없이 적용 — 대표 지시 "그냥 해"):
  - 핵심어(재료명)가 상품명에 있어야 인정.
  - 가공품 BAD 배제(타코야끼·치즈·튀김·젓·조림·볶음·양념·죽·전·만두·염장…).
  - 원산지별 최저. 식봄이 지금값보다 3배↑면 오매칭이라 버림.
  - 식봄이 지금값보다 비싸면 기본값을 안 덮는다(원가가 오르면 안 됨).
  - 카테고리에 없는 것(어묵·참치·김·연어·해물믹스)은 손대지 않는다.
"""
import json, io, os, re, sqlite3, sys, shutil
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
CAT = os.path.join(BASE, "data", "research", "foodspring", "_카테고리.json")
STAMP = "2026-07-25"

# 마른/건조 재료엔 '염장'도 배제(마른미역에 염장미역줄기가 섞임).
BAD = re.compile(r"타코야끼|치즈|튀김|젓갈|젓\b|조림|볶음|무침|양념|죽\b|전\b|만두|어묵|"
                 r"통조림|캔|드레싱|소스|퓨레|과자|스낵|피클|장아찌|육수|다시|찌개|즉석|"
                 r"간편|김치|깻잎|주먹밥|김밥|샐러드|파전|꼬치|맛살|후리가케")
BAD_DRIED = re.compile(r"염장|자숙|냉동활|생물")   # 마른/건조 재료에서 추가 배제

# 우리 재료 → (식봄 카테고리 라벨, 핵심어, 마른여부)
MAP = [
    ("고등어필렛",  "고등어", "고등어", False),
    ("자반고등어",  "고등어", "고등어", False),
    ("꽁치",       "꽁치",   "꽁치",   False),
    ("꽃게",       "게",     "꽃게",   False),
    ("낙지",       "낙지",   "낙지",   False),
    ("데친낙지해물믹스", "낙지", "낙지", False),
    ("대왕오징어",  "오징어", "오징어", False),
    ("마른오징어",  "마른오징어", "오징어", True),
    ("마른멸치",   "마른멸치", "멸치",  True),
    ("볶음멸치",   "마른멸치", "멸치",  True),
    ("마른미역",   "마른미역", "미역",  True),
    ("건다시마",   "건다시마", "다시마", True),
    ("명태",      "동태",   "동태",   False),
    ("흰살생선 필렛", "동태", "동태",   False),
    ("바지락",    "바지락", "바지락", False),
    ("홍합",      "홍합",   "홍합",   False),
    ("새우",      "새우",   "새우",   False),
    ("새우살",    "새우",   "새우살", False),
    ("슬라이스문어", "문어", "문어",  False),
    ("전복",      "전복",   "전복",   False),
]


def norm(s):
    return (s or "").replace(" ", "")


def main():
    dry = "--apply" not in sys.argv
    cat = json.load(io.open(CAT, encoding="utf-8"))
    if not dry:
        shutil.copy2(DB, DB + ".bak-20260725-seafood")
    con = sqlite3.connect(DB)
    cur = con.cursor()

    print("%-14s %8s %10s   %s" % ("재료", "지금", "식봄", "원산지별"))
    print("-" * 74)
    n_ing = n_row = 0
    for name, catlabel, kw, dried in MAP:
        row = cur.execute("select ingredient_key, base_unit, wholesale_price "
                          "from ingredients where name=?", (name,)).fetchone()
        if not row:
            print("  ! %s — DB에 없음" % name); continue
        key, unit, wp = row
        if unit != "kg":
            continue
        cand = cat.get(catlabel) or []
        core = norm(kw)
        good = []
        for r in cand:
            nm = r["name"]
            if not r.get("won_per_kg") or core not in norm(nm):
                continue
            if BAD.search(nm) or (dried and BAD_DRIED.search(nm)):
                continue
            if wp and r["won_per_kg"] > wp * 3:      # 이상치
                continue
            good.append(r)
        if not good:
            print("  ! %-12s 후보 없음(필터 통과 0)" % name); continue

        byo = {}
        for r in good:
            o = r.get("origin") or "미표기"
            if o not in byo or r["won_per_kg"] < byo[o]["won_per_kg"]:
                byo[o] = r
        lo = min(good, key=lambda r: r["won_per_kg"])
        summ = " · ".join("%s %s" % (o, f"{v['won_per_kg']:,}")
                          for o, v in sorted(byo.items(), key=lambda x: x[1]["won_per_kg"]))
        print("%-14s %8s %10s   %s" % (name, f"{wp or 0:,}", f"{lo['won_per_kg']:,}", summ[:40]))

        if not dry:
            cur.execute("delete from ingredient_price where ingredient_key=? and source='식봄'", (key,))
            for o, r in byo.items():
                b = "식봄(카테고리) %s %s / %s원 · %skg = %s원/kg" % (
                    STAMP, r["name"], f"{r['sale_price']:,}", r["pack_kg"], f"{r['won_per_kg']:,}")
                cur.execute("insert or replace into ingredient_price(ingredient_key,tier,kind,"
                            "origin,part,grade,brand,form,price,pack_kg,source,basis,is_default,"
                            "checked_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (key, "도매", None, o, None, r.get("grade"), None, "식봄",
                             r["won_per_kg"], r["pack_kg"], "식봄", b, 0, STAMP))
                n_row += 1
            # 식봄이 더 싸면 기본값 교체. 비싸면 유지.
            # ⚠️ 70% 넘게 싸지면(형태 다름/소포장 특가 의심) 표엔 남기되 기본값은 안 덮는다.
            #    (낙지 14,460→2,363, 흰살생선필렛 22,240→2,603 = 동태 통 오매칭 방지)
            too_cheap = wp and lo["won_per_kg"] < wp * 0.35
            if (not wp or lo["won_per_kg"] < wp) and not too_cheap:
                cur.execute("update ingredients set wholesale_price=?, wholesale_basis=?, "
                            "updated_at=? where ingredient_key=?",
                            (lo["won_per_kg"], "식봄 %s %s = %s원/kg" % (STAMP, lo["name"][:28],
                             f"{lo['won_per_kg']:,}"), STAMP, key))
        n_ing += 1

    if dry:
        print("\n※ 미리보기. 쓰려면  python scripts/seafood_apply.py --apply")
    else:
        con.commit()
        print("\n수산 %d종 · 표 %d행 반영." % (n_ing, n_row))


main()
