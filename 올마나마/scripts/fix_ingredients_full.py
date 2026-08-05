# -*- coding: utf-8 -*-
# 재료 오매핑 전면 교정 (13개 카테고리 병렬 감사 결과 반영, 72개 메뉴)
#  - NEW 재료 14종 마스터 추가
#  - REPLACE: 특정 menu_ingredients 행(mid)의 재료키/양 교체
#  - ADD: 누락 주재료/토핑 행 삽입
#  - DELETE: 중복/오매핑 행 삭제
# 실행 후 compute_line_costs.py 로 원가 재계산 필요.
import sqlite3, os
DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

# ── NEW 재료 (key, 이름, 분류, 원/kg) ──
NEW = [
    ("shrimp_meat","새우살","농축산물",25000),
    ("chicken_breast","닭가슴살","농축산물",9000),
    ("chicken_feet_bone","닭발(뼈있는)","가공품",10000),
    ("dangmyeon","당면","가공품",4000),
    ("beef_dogani","도가니(소 무릎연골)","농축산물",20000),
    ("soba_noodles","메밀면(소바)","가공품",3000),
    ("mint_syrup","민트시럽","가공품",6000),
    ("sundae_boiled","삶은 순대","가공품",7000),
    ("beef_cube_steak","소고기 큐브스테이크","농축산물",18000),
    ("rice_tteok","쌀떡(떡볶이떡)","가공품",3500),
    ("pork_stomach","오소리감투(돼지 위내장)","농축산물",15000),
    ("cheese_seasoning","치즈시즈닝 파우더","가공품",15000),
    ("pepperoni","페퍼로니","가공품",12000),
    ("potato_fresh","감자","농축산물",3000),
]
for k,n,cl,p in NEW:
    ex=cur.execute("SELECT 1 FROM ingredients WHERE ingredient_key=?",(k,)).fetchone()
    if not ex:
        cur.execute("INSERT INTO ingredients(ingredient_key,name,class,type,manual_price,base_unit,markup_factor,updated_at) "
                    "VALUES(?,?,?,'manual',?, 'kg',1.0,datetime('now'))",(k,n,cl,p))
        print(f"  +재료 {k} ({n}) {p}원/kg")

# ── REPLACE (mid, 새키, 양, 단위) ──
REPLACE = [
    # 분식
    (2604,'sundae_boiled',250,'g'),(2623,'sundae_boiled',250,'g'),
    (2634,'dangmyeon',80,'g'),(2638,'dangmyeon',80,'g'),(2660,'dangmyeon',150,'g'),
    (2617,'rice_tteok',250,'g'),(2652,'french_fries_frozen',200,'g'),(2656,'french_fries_frozen',200,'g'),
    (2562,'hotdog_bread',1,'개'),(2566,'hotdog_bread',1,'개'),(2570,'hotdog_bread',1,'개'),(2575,'hotdog_bread',1,'개'),
    (2580,'hotdog_bread',1,'개'),(2585,'hotdog_bread',1,'개'),(2589,'hotdog_bread',1,'개'),(2594,'hotdog_bread',1,'개'),
    # 베이커리
    (2064,'dangmyeon',30,'g'),
    # 버거
    (245,'shrimp_meat',80,'g'),(229,'chicken_breast',120,'g'),
    # 카페
    (2696,'x_024d11c694',30,'g'),(2034,'x_9fa5626527',30,'g'),(2037,'x_52d5d550ac',50,'g'),
    # 치킨
    (6,'sauce_normal',180,'g'),(41,'cheese_seasoning',30,'g'),
    # 곱창/포차
    (2221,'chicken_feet_bone',600,'g'),(2224,'chicken_feet',450,'g'),(2227,'raw_chicken_10',1000,'g'),
    # 한식
    (2408,'x_a0ada5ee05',160,'g'),(2423,'pork_stomach',150,'g'),(2376,'x_2458074f8e',350,'g'),
    (2392,'x_a0ada5ee05',220,'g'),(2449,'beef_dogani',200,'g'),
    # 일식
    (1744,'soba_noodles',180,'g'),(1896,'beef_cube_steak',180,'g'),(1872,'beef_cube_steak',180,'g'),
    (1876,'beef_cube_steak',150,'g'),(1884,'x_ed9421040a',150,'g'),
    # 중식/아시안
    (2323,'x_0efb9306fb',60,'g'),(2344,'chicken_parts',160,'g'),(2347,'noodles_rice',140,'g'),
    (2351,'noodles_rice',140,'g'),(2352,'beef_slices',100,'g'),(2355,'noodles_rice',120,'g'),
    (2290,'x_0efb9306fb',80,'g'),(2308,'noodles_rice',120,'g'),
    # 샐러드
    (2210,'shrimp_meat',80,'g'),(2213,'beef_slices',80,'g'),(2165,'x_197bdf2ccd',120,'g'),(2194,'shrimp_meat',80,'g'),
]
for mid,k,a,u in REPLACE:
    n=cur.execute("UPDATE menu_ingredients SET ingredient_key=?,amount=?,unit=?,composition=NULL WHERE id=? AND ingredient_key NOT IN ('sauce_honey','sauce_normal')",(k,a,u,mid)).rowcount
    # 소스행(composition 유지 대상: 6,41,2696,2034,2449)은 composition 보존해야 하므로 별도 처리
    if n==0:
        cur.execute("UPDATE menu_ingredients SET ingredient_key=?,amount=?,unit=? WHERE id=?",(k,a,u,mid))

# ── ADD (menu_id, 키, 양, 단위, sort_order) ──
ADD = [
    (441,'x_b1ea1c0f4b',10,'g',50),(434,'x_f6d7d76b4f',35,'g',50),(436,'cream_fresh',40,'ml',50),
    (427,'cream_fresh',100,'ml',50),(430,'x_cb52df78e9',40,'g',50),
    (26,'gim',3,'g',0),(26,'rice_uncooked',80,'g',0),(571,'x_118ff29a25',40,'g',0),
    (584,'mint_syrup',15,'g',50),(588,'milk',200,'g',0),(601,'coffee_bean',10,'g',0),(607,'milk',200,'g',0),
    (517,'x_a2f018ad7b',80,'g',50),
    (34,'potato_fresh',150,'g',50),(36,'pepperoni',50,'g',50),(41,'x_7bac62f60f',120,'g',50),
    (42,'french_fries_frozen',100,'g',50),(48,'pepperoni',50,'g',50),(44,'egg_fresh',60,'g',50),
    (46,'pepperoni',50,'g',50),(47,'x_7bac62f60f',100,'g',50),(37,'pepperoni',50,'g',50),
]
for mid,k,a,u,so in ADD:
    cur.execute("INSERT INTO menu_ingredients(menu_id,ingredient_key,amount,unit,line_cost,sort_order) VALUES(?,?,?,?,0,?)",(mid,k,a,u,so))

# ── DELETE (mid) ── 중복/이물 행
DELETE = [2028, 2278,2283,2288, 2229, 2357,2291]
for mid in DELETE:
    cur.execute("DELETE FROM menu_ingredients WHERE id=?",(mid,))

con.commit()
print(f"\n적용: REPLACE {len(REPLACE)} / ADD {len(ADD)} / DELETE {len(DELETE)} / NEW재료 {len(NEW)}")

# 검증 샘플
for M in (54,51,9,560,517,531,504,472,34,478):
    ings=cur.execute("""SELECT i.name,mi.amount,mi.unit FROM menu_ingredients mi JOIN ingredients i
        ON mi.ingredient_key=i.ingredient_key WHERE mi.menu_id=? ORDER BY mi.sort_order""",(M,)).fetchall()
    nm=cur.execute("SELECT m.name,b.name bn FROM menus m JOIN brands b ON m.brand_id=b.id WHERE m.id=?",(M,)).fetchone()
    print(f"  [{M}] {nm['bn']} {nm['name']}: " + " + ".join(f"{r['name']}({r['amount']:g}{r['unit']})" for r in ings))
con.close()
