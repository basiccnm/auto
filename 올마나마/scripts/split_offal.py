# -*- coding: utf-8 -*-
# '한우곱창/대창/염통' 3종 묶음 분리 (2026-07-17)
#
# 문제: 곱창·대창·염통을 한 재료(25,000/kg)로 묶어놨는데 셋은 단가 대역이 완전히 다르다.
#       게다가 이름의 '한우'가 단가와 맞지 않는다.
#
# 조사 결과 (미트박스·식봄 B2B 실측):
#   · **대창**: 자숙 소대창 벌크 24,450~26,667/kg → **현재 25,000이 정확하다. 손대지 않는다.**
#   · **곱창**: 구이용 자숙/손질 완제품 29,000/kg (삶은 소곱창 4kg 116,000 / 국산 곱창 50mm 서해F&D 2kg 58,000)
#              → 25,000은 약 16% 과소. 29,000으로 조정.
#   · **염통**: 6,750~8,750/kg. **어느 메뉴에도 안 쓰인다** → 이름에서 제거(안 쓰는 걸 묶어두면 오해만 부른다).
#
# '한우' 표기를 빼는 이유:
#   ① 브랜드의 한우 주장을 검증하지 못했다 — 곱창고 공식 도메인 4개가 전부 404/DNS 실패, 핵밥도 근거 없음(low).
#   ② **가격 구조가 한우를 부정한다**: 한우 자숙곱창 65,000/kg인데 곱창고 한우곱창구이는 200g 20,900원이다.
#      65,000이면 원가 13,000 = 원가율 62%로 장사가 성립하지 않는다. 29,000이면 5,800 = 27.8%로 비로소 맞는다.
#      (조사팀이 찾은 65,000은 미트박스 '자숙곱창' 검색의 **단일 상품·단일 출처**이고, 같은 미트박스에서
#       '한우' 명시 자숙곱창전골은 16kg 벌크 27,500/kg이다. 65,000은 프리미엄 소분가로 보인다.)
#   ③ 원산지표시법상 '한우'는 육우·젖소와 구분되는 표시라, 근거 없이 우리가 붙일 값이 아니다.
#   → 재료명에서 '한우'를 빼되 **메뉴명(곱창고 한우곱창구이)은 브랜드 표기이므로 건드리지 않는다.**
import sqlite3, os

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
DRY = os.environ.get("DRY") == "1"

OLD = "x_c213e61e77"   # '한우곱창/대창/염통' 25,000

# 곱창용 재료 신설 (구이용 자숙 완제품)
if not cur.execute("SELECT 1 FROM ingredients WHERE ingredient_key='x_gopchang'").fetchone():
    cur.execute("""INSERT INTO ingredients(ingredient_key,name,class,type,manual_price,base_unit,markup_factor)
        VALUES('x_gopchang','소곱창(자숙·구이용)','농축산물','manual',29000,'kg',1.0)""")
    print("  + 신규: 소곱창(자숙·구이용) 29,000원/kg")

# 기존 키는 대창 전용으로 이름·단가 정리 (25,000 유지 — 조사값과 일치)
cur.execute("UPDATE ingredients SET name='소대창(자숙·구이용)', manual_price=25000 WHERE ingredient_key=?", (OLD,))
print("  · '한우곱창/대창/염통' → '소대창(자숙·구이용)' 25,000원/kg 유지 (자숙 소대창 벌크 24,450~26,667과 일치)")

# 곱창 메뉴만 새 키로 이관. 대창 메뉴는 그대로 둔다.
GOP = [
    (486, "곱창고 한우곱창구이 — 곱창"),
    (487, "곱창고 곱창모듬구이 — 곱창"),
]
for mid, why in GOP:
    r = cur.execute("SELECT id,amount,unit FROM menu_ingredients WHERE menu_id=? AND ingredient_key=?",
                    (mid, OLD)).fetchone()
    if not r:
        print(f"  ⚠️ [{mid}] 해당 줄 없음 — 건너뜀"); continue
    nm = cur.execute("SELECT m.name,b.name bn FROM menus m JOIN brands b ON m.brand_id=b.id WHERE m.id=?", (mid,)).fetchone()
    cur.execute("UPDATE menu_ingredients SET ingredient_key='x_gopchang' WHERE id=?", (r["id"],))
    print(f"  [{mid}] {nm['bn']} {nm['name']}: → 소곱창 29,000 (양 {r['amount']:g}{r['unit']} 유지)")

print("\n  대창 유지(25,000이 정확):")
for r in cur.execute("""SELECT m.id,m.name,b.name bn,mi.amount,mi.unit FROM menu_ingredients mi
    JOIN menus m ON mi.menu_id=m.id JOIN brands b ON m.brand_id=b.id WHERE mi.ingredient_key=?""", (OLD,)):
    print(f"    [{r['id']}] {r['bn']} {r['name']} {r['amount']:g}{r['unit']}")

if DRY:
    con.rollback(); print("\n[DRY] 롤백함")
else:
    con.commit(); print("\n커밋 완료")
con.close()
