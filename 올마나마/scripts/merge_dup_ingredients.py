# -*- coding: utf-8 -*-
# 재료 중복·죽은 행 정리 (2026-07-17)
#  "안 나올 때까지 파라"는 지시로 훑다가 나온 것들.
#
#  ⚠️ 죽은 행을 지울 땐 **dish_ingredients도 반드시 확인**할 것.
#     menu_ingredients 기준으로만 "안 쓰임" 판정하면 요리사전(dish)이 깨진다.
#     실제로 22개 중 6개가 dish에서 쓰이고 있었다.
import sqlite3, os

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
DRY = os.environ.get("DRY") == "1"

def uses(k):
    a = cur.execute("SELECT COUNT(*) FROM menu_ingredients WHERE ingredient_key=?", (k,)).fetchone()[0]
    b = cur.execute("SELECT COUNT(*) FROM dish_ingredients WHERE ingredient_key=?", (k,)).fetchone()[0]
    return a, b

print("── 1) 대왕오징어 5개 키 → 1개로 병합 (단가는 전부 12,000원 동일 = 원가 변화 없음)")
keys = [r[0] for r in cur.execute(
    "SELECT ingredient_key FROM ingredients WHERE name='대왕오징어(수입 냉동)' ORDER BY ingredient_key").fetchall()]
if len(keys) > 1:
    keep, drop = keys[0], keys[1:]
    for k in drop:
        a, b = uses(k)
        cur.execute("UPDATE menu_ingredients SET ingredient_key=? WHERE ingredient_key=?", (keep, k))
        cur.execute("UPDATE dish_ingredients SET ingredient_key=? WHERE ingredient_key=?", (keep, k))
        cur.execute("DELETE FROM ingredients WHERE ingredient_key=?", (k,))
        print(f"     {k} → {keep} (메뉴 {a}줄 · dish {b}줄 이관)")
else:
    print("     이미 병합됨")

print("\n── 2) '해물믹스'(추정 13,000, 1메뉴) → '해물 믹스'(조사값 9,000, 19메뉴)로 병합")
print("     같은 품목인데 한쪽은 웹조사값, 다른 쪽은 계수추정값이라 44% 벌어져 있었다.")
src = cur.execute("SELECT ingredient_key FROM ingredients WHERE name='해물믹스'").fetchone()
dst = cur.execute("SELECT ingredient_key FROM ingredients WHERE name='해물 믹스'").fetchone()
if src and dst:
    a, b = uses(src[0])
    cur.execute("UPDATE menu_ingredients SET ingredient_key=? WHERE ingredient_key=?", (dst[0], src[0]))
    cur.execute("UPDATE dish_ingredients SET ingredient_key=? WHERE ingredient_key=?", (dst[0], src[0]))
    cur.execute("DELETE FROM ingredients WHERE ingredient_key=?", (src[0],))
    print(f"     {src[0]} → {dst[0]} (메뉴 {a}줄 · dish {b}줄 이관)")
else:
    print("     이미 병합됨")
# ※ '황태포해물믹스'·'데친낙지해물믹스'는 별개 품목이라 건드리지 않는다.

print("\n── 3) '찌개용 두부'(3,000, dish 2곳) vs '찌개용두부'(5,000, 메뉴 1곳) → 같은 두부인데 값이 다름")
a1 = cur.execute("SELECT ingredient_key,manual_price FROM ingredients WHERE name='찌개용 두부'").fetchone()
a2 = cur.execute("SELECT ingredient_key,manual_price FROM ingredients WHERE name='찌개용두부'").fetchone()
if a1 and a2:
    # 브랜드 메뉴 쪽(5,000)으로 통일 — dish만 3,000을 쓰면 같은 두부가 페이지마다 값이 달라진다.
    a, b = uses(a1[0])
    cur.execute("UPDATE dish_ingredients SET ingredient_key=? WHERE ingredient_key=?", (a2[0], a1[0]))
    cur.execute("UPDATE menu_ingredients SET ingredient_key=? WHERE ingredient_key=?", (a2[0], a1[0]))
    cur.execute("DELETE FROM ingredients WHERE ingredient_key=?", (a1[0],))
    print(f"     '찌개용 두부'({a1[1]:,}) → '찌개용두부'({a2[1]:,})로 통일 (dish {b}줄 이관)")
else:
    print("     이미 정리됨")

print("\n── 4) 완전히 안 쓰이는 재료 삭제 (menu·dish 양쪽 다 0인 것만)")
dead = cur.execute("""SELECT ingredient_key k, name FROM ingredients i
    WHERE NOT EXISTS(SELECT 1 FROM menu_ingredients WHERE ingredient_key=i.ingredient_key)
      AND NOT EXISTS(SELECT 1 FROM dish_ingredients WHERE ingredient_key=i.ingredient_key)""").fetchall()
for r in dead:
    cur.execute("DELETE FROM ingredients WHERE ingredient_key=?", (r["k"],))
print(f"     {len(dead)}개 삭제: " + ", ".join(r["name"] for r in dead))

print("\n── 5) 메밀면 3건 — 중식 생면(2,500) → 메밀면(소바)(5,000)")
print("     메뉴명이 '메밀면'인데 중식 생면을 쓰고 있었다. 메밀면 재료는 이미 있었다.")
soba = cur.execute("SELECT ingredient_key FROM ingredients WHERE name LIKE '메밀면%'").fetchone()
if soba:
    for mid in (466, 465, 451):
        row = cur.execute("SELECT id,amount,unit FROM menu_ingredients WHERE menu_id=? AND ingredient_key='noodles_fresh'",
                          (mid,)).fetchone()
        if not row:
            print(f"     ⚠️ [{mid}] 중식 생면 줄 없음 — 건너뜀"); continue
        nm = cur.execute("SELECT name FROM menus WHERE id=?", (mid,)).fetchone()[0]
        cur.execute("UPDATE menu_ingredients SET ingredient_key=? WHERE id=?", (soba[0], row["id"]))
        print(f"     [{mid}] {nm}: noodles_fresh → {soba[0]} (양 {row['amount']:g}{row['unit']} 유지)")

if DRY:
    con.rollback(); print("\n[DRY] 롤백함")
else:
    con.commit(); print("\n커밋 완료")

print("""
※ 남은 것 (단가 조사 중이라 보류):
   [347] 바르다김선생 안동국시   — 칼국수면인데 중식 생면
   [540] 이화수전통육개장 육개장칼국수 — 〃
   [360] 홍익돈까스 까르보나라   — 스파게티면인데 중식 생면
""")
con.close()
