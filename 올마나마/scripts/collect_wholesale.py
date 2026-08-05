# KAMIS 도매가(p_product_cls_code=02) 수집 → price_history.wholesale_price 갱신
#
# 농산물(곡물·채소·과일) 원물만. 축산(cat 500)은 KAMIS가 cls=01/02 동일 응답 =
# 실질 도매가 없음이므로 건드리지 않는다(NULL 유지). 닭(축평원)·가공품도 도매 없음.
# 단위 환산·등급 선택 규칙은 kamis_kg 모듈 주석 참조.
#
# 사용법: python collect_wholesale.py [YYYY-MM-DD]
import json
import sqlite3
import sys

from kamis_kg import WHOLESALE, fetch_many

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
LIVESTOCK_CAT = "500"  # KAMIS 축산 = 도매 미제공. 설계서 §8.3-4
VEG_CAT = "200"        # 야채지수(live_composite) 바스켓 카테고리


def wholesale_of(catmap, typ, kcat, kcode, comp):
    """재료 1건의 원/kg 도매가. 값 없으면 None."""
    if typ == "live":
        if kcat == LIVESTOCK_CAT:
            return None  # 축산 도매 없음
        if kcat and kcode:
            return catmap.get(kcat, {}).get(kcode)
        return None
    if typ == "live_composite" and comp:
        veg = catmap.get(VEG_CAT, {})
        parts = json.loads(comp)
        vals = [veg[p["code"]] * p["w"] for p in parts if veg.get(p["code"])]
        if len(vals) != len(parts):
            # 바스켓 일부 결측 → 가중치 합이 1 미만이라 조용히 과소집계된다. 기록 안 함.
            have = [p["code"] for p in parts if veg.get(p["code"])]
            print(f"    [스킵] 야채지수 바스켓 결측: {len(have)}/{len(parts)}종만 조회됨 {have}")
            return None
        return round(sum(vals))
    return None


def main():
    regday = sys.argv[1] if len(sys.argv) > 1 else "2026-07-15"
    con = sqlite3.connect(DB)
    cur = con.cursor()
    ings = cur.execute(
        "SELECT ingredient_key,kamis_cat,kamis_item_code,composite_formula,markup_factor,type "
        "FROM ingredients WHERE type IN ('live','live_composite')").fetchall()

    cats = set()
    for _, kcat, _, _, _, typ in ings:
        if typ == "live" and kcat and kcat != LIVESTOCK_CAT:
            cats.add(kcat)
        if typ == "live_composite":
            cats.add(VEG_CAT)
    catmap = fetch_many(cats, WHOLESALE, regday, verbose=True)

    n = 0
    for key, kcat, kcode, comp, markup, typ in ings:
        w = wholesale_of(catmap, typ, kcat, kcode, comp)
        if w is None:
            continue
        w = round(w * (markup or 1.0))
        cur.execute("UPDATE price_history SET wholesale_price=? "
                    "WHERE ingredient_key=? AND price_date=? AND source='kamis'", (w, key, regday))
        if cur.rowcount == 0:
            print(f"  {key}: 도매 {w}/kg — {regday} 소매행 없음, 기록 안 함")
            continue
        n += cur.rowcount
        print(f"  {key}: 도매 {w}/kg")
    con.commit()
    print(f"도매가 갱신 {n}건 ({regday})")
    con.close()


if __name__ == "__main__":
    main()
