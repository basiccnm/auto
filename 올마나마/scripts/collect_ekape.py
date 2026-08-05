# -*- coding: utf-8 -*-
# 축산물품질평가원(축평원) 도매시세 수집 → ingredients / price_history (2026-07-19)
#
# 왜: 자동 갱신되는 재료가 27종뿐이고 그중 축산은 '염지닭' 하나여서, 시세 화면이
#     매일 같은 얼굴이었다("염지닭만 맨날 1등"). 축평원은 소 16부위·돼지 등급·닭 도매를
#     매 경매일 주는데 우리는 닭 소매 하나만 쓰고 있었다.
#
# 🔴 설계 원칙 — 기존 원가 계산은 건드리지 않는다
#   축평원 경락가는 **국산(한우/국내산 돼지·닭) 도매** 기준이다. 우리 메뉴 재료의
#   상당수는 **수입 냉동**(수입 삼겹살·돼지 등심·소고기 다짐육 등)이라, 여기에 한우
#   경락가를 갖다 붙이면 원가가 3~4배로 튄다. 실제로 "양지에 한우값" 사고가 있었다.
#   → 그래서 이 수집기는 **새 재료(ek_*)를 따로 만든다**. 메뉴에 연결하지 않으므로
#     원가·원가율은 그대로고, 재료시세 화면의 "자동 갱신" 종수만 늘어난다.
#     특정 메뉴를 국산 기준으로 바꾸려면 그때 menu_ingredients를 명시적으로 옮길 것.
#
# 사용법: python scripts/collect_ekape.py
import os, sqlite3, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from publicdata import ekape

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

# 소 부분육: 16부위 중 **식자재로 의미 있는 것만**. 잡뼈·꼬리 등은 제외.
#  값은 hanAvgT(한우 전체평균, 원/kg). 육우(yukAvgT)는 비어 오는 날이 많아 안 쓴다.
BEEF_CUTS = ["안심", "등심", "채끝", "목심", "앞다리", "우둔", "설도", "양지", "사태", "갈비", "사골", "우족"]

# 돼지 지육 등급 — 축평원은 돼지에 대해 **부분육(삼겹·목살) 경락을 제공하지 않는다**.
#  소(beefGrade)는 16부위를 주는데 돼지(pigGrade)는 지육 등급별뿐이라 종수 차이가 크다.
#  그래서 대표값 하나만 쓰지 말고 **등급별로 전부 올린다**(시세 자체가 콘텐츠라는 방침).
#  ⚠️ 지육(도체) 단가라 삼겹살 같은 부분육 가격과 직접 비교 금지 → 이름에 '지육' 명시.
PIG_GRADES = [("등외제외", "돼지 지육(등외제외 평균)"), ("1+", "돼지 지육 1+등급"),
              ("1", "돼지 지육 1등급"), ("2", "돼지 지육 2등급"),
              ("평균", "돼지 지육(전체 평균)"), ("모돈", "돼지 지육(모돈)")]


def upsert(cur, key, name, cls, price, day):
    d = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
    if cur.execute("SELECT 1 FROM price_history WHERE ingredient_key=? AND price_date=?",
                   (key, d)).fetchone():
        cur.execute("DELETE FROM price_history WHERE ingredient_key=? AND price_date=?", (key, d))
    cur.execute("""INSERT INTO ingredients(ingredient_key,name,class,type,manual_price,base_unit,
        markup_factor,is_retail,updated_at)
        VALUES(?,?,?,'live',?,'kg',1.0,0,datetime('now'))
        ON CONFLICT(ingredient_key) DO UPDATE SET
          name=excluded.name, manual_price=excluded.manual_price, type='live',
          updated_at=datetime('now')""", (key, name, cls, price))
    cur.execute("""INSERT INTO price_history(ingredient_key,price_date,retail_price,
        wholesale_price,source,created_at) VALUES(?,?,?,?,'ekape',datetime('now'))""",
        (key, f"{day[:4]}-{day[4:6]}-{day[6:8]}", price, price))


def main():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
    ymd = date.today().strftime("%Y%m%d")
    n = 0

    day, beef = ekape.fetch_wholesale_recent("beefGrade", ymd, max_back=14)
    if beef:
        for cut in BEEF_CUTS:
            row = beef.get(cut)
            v = (row or {}).get("hanAvgT")
            if isinstance(v, int) and v > 0:
                upsert(cur, f"ek_beef_{cut}", f"한우 {cut}(경락)", "농축산물", v, day); n += 1
        print(f"  소 부분육 {day}: {n}종")

    day2, pig = ekape.fetch_wholesale_recent("pigGrade", ymd, max_back=14)
    if pig:
        pn = 0
        for grade, label in PIG_GRADES:
            v = (pig.get(grade) or {}).get("CTotAmt")
            if isinstance(v, int) and v > 0:
                key = "ek_pig_carcass" if grade == "등외제외" else f"ek_pig_{grade}"
                upsert(cur, key, label, "농축산물", v, day2); n += 1; pn += 1
        print(f"  돼지 지육 {day2}: {pn}등급")

    day3, chick = ekape.fetch_wholesale_recent("chickenDomae", ymd, max_back=14)
    row = (chick or {}).get("도체") or {}
    for field, label, key in (("avg", "닭 도체(경락 평균)", "ek_chicken_avg"),   # '도매' 표기 제거(2026-07-20)
                              ("franchise", "닭 도체(프랜차이즈 납품)", "ek_chicken_fr")):
        v = row.get(field)
        if isinstance(v, int) and v > 0:
            upsert(cur, key, label, "농축산물", v, day3); n += 1
    if row:
        print(f"  닭 도매 {day3}: avg {row.get('avg')} · 프랜차이즈 {row.get('franchise')}")

    con.commit(); con.close()
    print(f"축평원 갱신 완료: {n}종")


if __name__ == "__main__":
    main()
