# -*- coding: utf-8 -*-
# 재료 오매핑 1차 교정 (확실한 것만). 추측 필요한 건 제외하고 사용자 확인 후 진행.
#  - 소곱창/소대창/한우대창 → 돼지등심 오매핑을 실제 곱창 재료로 교정
#  - 한우곱창구이/한우대창구이 → 고기 누락 → 곱창 재료 추가(양념줄 1개를 곱창으로 전환)
import sqlite3, os
DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

SOGOPCHANG = "x_10a10b8b9e"   # 자숙소곱창/전골곱창 (25000/kg)
HANWOO_OFF = "x_c213e61e77"   # 한우곱창/대창/염통 (25000/kg)

# (1) 돼지등심 → 올바른 곱창 재료 (menu_id, 새 키)
remap = [
    (481, SOGOPCHANG),   # 곱창이야기 소곱창(200g)
    (396, SOGOPCHANG),   # 핵밥 소곱창덮밥
    (482, HANWOO_OFF),   # 곱창이야기 소대창(200g)
    (398, HANWOO_OFF),   # 핵밥 한우대창덮밥
]
for mid, newkey in remap:
    n = cur.execute("UPDATE menu_ingredients SET ingredient_key=? WHERE menu_id=? AND ingredient_key='pork_loin_tangsuyuk'",
                    (newkey, mid)).rowcount
    print(f"  menu {mid}: 돼지등심 → {newkey} ({n}줄)")

# (2) 고기 누락 메뉴: 양념소스 줄(mid) 하나를 곱창 재료로 전환(200g), composition 제거
convert = [(2252, HANWOO_OFF), (2261, HANWOO_OFF)]  # 486 한우곱창구이 / 489 한우대창구이
for mid, newkey in convert:
    cur.execute("UPDATE menu_ingredients SET ingredient_key=?, amount=200, unit='g', composition=NULL WHERE id=?",
                (newkey, mid))
    print(f"  mid {mid}: 양념소스 → {newkey} 200g (고기 추가)")

con.commit()
print("\n교정 후 확인:")
for mid in (481, 482, 396, 398, 486, 489):
    ings = cur.execute("""SELECT i.name,mi.amount,mi.unit FROM menu_ingredients mi JOIN ingredients i
        ON mi.ingredient_key=i.ingredient_key WHERE mi.menu_id=? ORDER BY mi.sort_order""", (mid,)).fetchall()
    nm = cur.execute("SELECT m.name,b.name bn FROM menus m JOIN brands b ON m.brand_id=b.id WHERE m.id=?", (mid,)).fetchone()
    print(f"  [{mid}] {nm['bn']} {nm['name']}: " + " + ".join(f"{r['name']}({r['amount']:g}{r['unit']})" for r in ings))
con.close()
