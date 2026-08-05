# DB → 쇼츠 메뉴 데이터 (2026-07-22)
#
# 🔴 왜 필요한가: 지금까지 재료명·가격을 **손으로** config.js에 옮겨 적었다.
#    DB가 바뀌면 또 손으로 해야 하고, 실제로 식용유가 2,640→2,800으로 오른 걸 놓칠 뻔했다.
#    이 스크립트가 `menu.json`을 쓰고 config.js가 그걸 읽는다. 이제 옮겨 적을 일이 없다.
#
# 🔴 반드시 **menu_ingredients**(매장 원가 축)를 본다.
#    `dishes`/`dish_ingredients`는 "집에서 만들면" 축이라 분량이 다르다.
#    닭이 매장 0.85kg인데 집밥 1.0kg이라, 잘못 가져오면 원가가 1,200원 튄다.
#
# 🔴 화면에 쓰는 **짧은 이름**은 DB 제품명과 다르다(제조사·용량이 붙어 있어서 너무 길다).
#    SHORT에 매핑을 둔다. 여기 없으면 DB 이름을 그대로 쓴다.
#    원본 제품명은 menu.json의 `full`에 남겨둔다 — 나중에 가격 재검증할 때 필요하다.
#
#   python make_menu.py 허니콤보
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent          # 올마나마
DB = ROOT / "data" / "eolmanama.db"
OUT = Path(__file__).parent / "remotion" / "src" / "shorts" / "menu.json"

# 화면용 짧은 이름 (ingredient_key 기준)
SHORT = {
    "chicken_parts": "닭 정육(윙·봉)",
    "breading_kyochon": "치킨 브레딩믹스",
    "frying_oil": "식용유",
    "sauce_honey_ganjang": "허니 간장소스",
    "sidedish_set": "치킨무",
}


# 🔴 **단위 환산은 반드시 표로 처리한다**(2026-07-22 실제로 당함).
#    ml→L만 처리하고 g→kg를 빼먹었더니 굽네 파우더가 496원 대신 **496,000원**으로 나왔다.
#    교촌은 재료가 전부 kg·ml이라 안 드러났고, g 단위가 있는 브랜드에서 터졌다.
#    새 단위가 나오면 여기 추가하고, 표에 없으면 그대로 곱한다(1:1로 본다).
UNIT = {
    ("g", "kg"): 0.001,
    ("kg", "g"): 1000,
    ("ml", "L"): 0.001,
    ("L", "ml"): 1000,
    ("세트", "개"): 1,
    ("개", "세트"): 1,
}


def to_base(amount, unit, base_unit):
    """재료 분량을 단가의 기준 단위로 바꾼다."""
    if unit == base_unit:
        return amount
    k = UNIT.get((unit, base_unit))
    if k is None:
        print(f"⚠️ 모르는 단위 조합: {unit} → {base_unit}. 1:1로 계산한다. UNIT 표에 추가할 것")
        return amount
    return amount * k


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "허니콤보"
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    m = c.execute(
        "select id, name, brand_id, sell_price, store_cost, store_ratio from menus where name=?", (name,)
    ).fetchone()
    if not m:
        print(f"메뉴를 못 찾음: {name}")
        return
    brand = c.execute("select name from brands where id=?", (m["brand_id"],)).fetchone()

    rows = c.execute(
        """select i.ingredient_key, i.name, i.wholesale_price, i.base_unit,
                  mi.amount, mi.unit
           from menu_ingredients mi
           join ingredients i on i.ingredient_key = mi.ingredient_key
           where mi.menu_id = ? order by mi.sort_order""",
        (m["id"],),
    ).fetchall()

    items = []
    for r in rows:
        amt = to_base(r["amount"], r["unit"], r["base_unit"])
        price = round(amt * r["wholesale_price"])
        items.append({
            "key": r["ingredient_key"],
            "name": SHORT.get(r["ingredient_key"], r["name"]),
            "full": r["name"],                       # DB 원본 제품명 — 지우지 말 것
            "price": price,
            "amount": r["amount"],
            "unit": r["unit"],
            "unitPrice": r["wholesale_price"],
        })

    cost = sum(x["price"] for x in items)
    data = {
        "brand": brand["name"] if brand else "",
        "menu": m["name"],
        "sell": m["sell_price"],
        "cost": cost,
        "diff": m["sell_price"] - cost,
        "items": items,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{data['brand']} {data['menu']}  판매 {m['sell_price']:,}원")
    for x in items:
        print(f"  {x['name']:<16} {x['price']:>6,}원   ({x['amount']}{x['unit']} × {x['unitPrice']:,})")
    print(f"  {'재료비':<16} {cost:>6,}원   ({cost / m['sell_price'] * 100:.1f}%)")
    print(f"  {'남는 돈':<16} {data['diff']:>6,}원")

    # DB가 따로 들고 있는 값과 어긋나면 알려준다 — 둘 중 하나가 틀린 것이다
    if m["store_cost"] and abs(m["store_cost"] - cost) > 1:
        print(f"\n⚠️ menus.store_cost({m['store_cost']:,})와 계산값({cost:,})이 다르다. DB를 확인할 것")
    print(f"\n→ {OUT.relative_to(ROOT)}")


main()
