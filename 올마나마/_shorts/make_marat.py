# 마라탕 재료 100g 단가 뽑기 (2026-07-22)
#
# 🔴 마라탕은 프랜차이즈 편과 구조가 다르다.
#    프랜차이즈  = 메뉴 하나의 재료를 합쳐 원가를 낸다  → make_menu.py
#    마라탕      = **재료별 100g 단가**를 나열한다      → 이 파일
#
# 🔴 마라탕집은 무게로 판다(보통 100g당 균일가). 그래서 무게 측정이 필요 없다.
#    같은 100g을 사는데 재료마다 원가가 10배씩 차이 나는 게 이 편의 이야기다.
#    무겁고 싼 재료(분모자·당면류)가 가게에 제일 좋고, 무겁고 비싼 것(고기)이 제일 나쁘다.
#
# 🔴 재료 목록은 KEYS에 적는다. 새 데이터가 들어오면 여기에 추가한다.
#    (2026-07-22 현재 야채 쪽을 다른 세션에서 정리 중)
#
#   python make_marat.py            → 전체, 비싼 순
#   python make_marat.py 2000       → 매장 100g 단가를 2,000원으로 놓고 마진까지
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB = ROOT / "data" / "eolmanama.db"
OUT = Path(__file__).parent / "remotion" / "src" / "shorts" / "marat.json"

# 화면에 쓸 짧은 이름 (없으면 DB 이름 그대로)
SHORT = {
    "마라탕 소스 (제품 미정·대표 실측)": "마라탕 소스",
}

# 🔴 마라탕에 담는 재료들. **새 데이터가 오면 여기에 ingredient_key를 추가한다.**
#    비워두면 '마라탕 기본형' 메뉴에 연결된 재료를 쓴다.
KEYS = []

UNIT_TO_KG = {"kg": 1, "g": 0.001, "L": 1, "ml": 0.001, "개": None, "세트": None}


def main():
    sell100 = int(sys.argv[1]) if len(sys.argv) > 1 else None
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    if KEYS:
        q = "select * from ingredients where ingredient_key in (%s)" % ",".join("?" * len(KEYS))
        rows = c.execute(q, KEYS).fetchall()
    else:
        rows = c.execute("""select i.* from ingredients i
            join menu_ingredients mi on mi.ingredient_key = i.ingredient_key
            join menus m on m.id = mi.menu_id
            where m.name = '마라탕 기본형' group by i.ingredient_key""").fetchall()

    items = []
    for r in rows:
        # 🔴 100g 원가 = kg 단가 ÷ 10. 개수로 파는 재료는 마라탕에 안 쓰므로 건너뛴다
        if r["base_unit"] not in ("kg", "L"):
            print(f"건너뜀(무게 단위 아님): {r['name']} [{r['base_unit']}]")
            continue
        per100 = round(r["wholesale_price"] / 10)
        items.append({
            "key": r["ingredient_key"],
            "name": SHORT.get(r["name"], r["name"]),
            "full": r["name"],
            "per100": per100,
            "perKg": r["wholesale_price"],
            "cat": r["subcat"],
        })

    items.sort(key=lambda x: -x["per100"])
    data = {"sell100": sell100, "items": items}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    head = f"{'재료':<20}{'100g 원가':>10}"
    if sell100:
        head += f"{'마진':>10}{'마진율':>8}"
    print("\n" + head)
    print("─" * len(head))
    for x in items:
        line = f"{x['name'][:20]:<20}{x['per100']:>9,}원"
        if sell100:
            m = sell100 - x["per100"]
            line += f"{m:>9,}원{m / sell100 * 100:>7.0f}%"
        print(line)
    if sell100:
        print(f"\n매장 100g 판매가 {sell100:,}원 기준")
        loss = [x["name"] for x in items if x["per100"] > sell100]
        if loss:
            print(f"⚠️ 원가가 판매가를 넘는 재료: {', '.join(loss)}  ← 담을수록 가게가 손해")
    print(f"\n→ {OUT.relative_to(ROOT)}  ({len(items)}종)")


main()
