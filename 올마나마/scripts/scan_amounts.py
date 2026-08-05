# -*- coding: utf-8 -*-
# 재료 '양' 상식범위 스캔 — 메뉴 유형별 룰로 이상치 플래그 (DB 미변경, 목록만)
import sqlite3, re

DB = r"C:\Users\hardb\Desktop\블로그수입관련\올마나마\data\eolmanama.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

def g(amount, unit):
    u = (unit or "").strip()
    if u == "kg": return amount * 1000
    if u == "g": return amount
    if u == "L": return amount * 1000
    if u == "ml": return amount
    return None  # 개/세트/장 등

MEAT = re.compile(r"닭|치킨|돼지|소고기|우삼겹|양지|족발|삼겹|곱창|대창|막창|특양|순대|패티|정육|다짐|등심|전지|스테이크|햄|소시지|새우살|연어|참치|광어|생선|오징어|문어|낙지|해물|도가니|돈뼈|닭발|오소리|수육|머리고기|염통|위내장|큐브")

flags = []
menus = cur.execute("""SELECT m.id,m.name,b.name bn,c.slug cs,m.sell_price FROM menus m
    JOIN brands b ON m.brand_id=b.id JOIN categories c ON b.category_id=c.id ORDER BY m.id""").fetchall()
for m in menus:
    ings = cur.execute("""SELECT i.ingredient_key k,i.name,mi.amount,mi.unit,mi.line_cost FROM menu_ingredients mi
        JOIN ingredients i ON mi.ingredient_key=i.ingredient_key WHERE mi.menu_id=?""", (m["id"],)).fetchall()
    tot = 0; meat_g = 0; notes = []
    for r in ings:
        w = g(r["amount"], r["unit"])
        # 라인 단위 룰
        if r["amount"] == 0: notes.append(f"양=0: {r['name']}")
        if w is not None:
            tot += w
            if MEAT.search(r["name"] or ""): meat_g += w
            if r["k"] == "frying_oil" and w > 350: notes.append(f"식용유 {w:.0f}ml 과다")
            if r["k"] == "milk" and m["cs"] == "cafe" and w > 400: notes.append(f"우유 {w:.0f}ml 과다(음료)")
            if "소스" in (r["name"] or "") and w > 300: notes.append(f"소스 {w:.0f}g 과다: {r['name']}")
            if r["k"] == "mozzarella_cheese" and m["cs"] != "pizza" and w > 250: notes.append(f"치즈 {w:.0f}g 과다")
            if r["k"] == "rice_uncooked" and w > 160 and not re.search(r"볶음밥|2인|한상|세트", m["name"]): notes.append(f"생쌀 {w:.0f}g 과다(1인 90~130)")
        else:
            if r["unit"] in ("개","세트","장") and r["amount"] > 4 and r["k"] not in ("egg_fresh",): notes.append(f"{r['name']} {r['amount']:g}{r['unit']} (개수 확인)")
    # 메뉴 단위 룰 (총중량·육류량)
    cs = m["cs"]; nm = m["name"]
    def rng(lo, hi, label, val):
        if val and (val < lo or val > hi): notes.append(f"{label} {val:.0f}g (기준 {lo}~{hi})")
    if cs == "burger": rng(120, 450, "버거 총중량", tot)
    elif cs == "chicken" and re.search(r"콤보|후라이드|양념|반반|순살|치킨|바사삭|볼케이노|킹|클", nm): rng(500, 1600, "치킨 총중량", tot)
    elif cs == "pizza": rng(500, 1400, "피자 총중량", tot)
    elif cs in ("hansik",) and re.search(r"국밥|해장국|탕|찌개|설렁탕|곰탕", nm): rng(80, 320, "국밥 육류", meat_g)
    elif cs == "jokbal": rng(500, 2200, "족발/보쌈 육류", meat_g)
    elif cs == "gopchang" and "볶음밥" not in nm: rng(120, 450, "곱창 육류", meat_g)
    elif cs == "bunsik" and "떡볶이" in nm:
        tteok = sum(g(r["amount"],r["unit"]) or 0 for r in ings if "떡" in (r["name"] or ""))
        if tteok: rng(150, 700, "떡 양", tteok)
    elif cs == "cafe" and re.search(r"아메리카노|라떼|치노|프라페|스무디|주스|피지오|마키아또", nm): rng(150, 600, "음료 총량", tot)
    elif cs == "ilsik" and re.search(r"덮밥", nm): rng(80, 280, "덮밥 육류", meat_g)
    if notes:
        flags.append((m["id"], m["bn"], nm, m["sell_price"], notes,
                      " + ".join(f"{r['name']}{r['amount']:g}{r['unit']}" for r in ings)))

print(f"플래그 {len(flags)}개 메뉴 / 전체 {len(menus)}")
for mid, bn, nm, sp, notes, ing in flags:
    print(f"\n[{mid}] {bn} {nm} (판매 {sp:,})")
    for n in notes: print(f"   ⚠ {n}")
    print(f"   재료: {ing[:110]}")
con.close()
