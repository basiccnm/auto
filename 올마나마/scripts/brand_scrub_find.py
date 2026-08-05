# -*- coding: utf-8 -*-
"""화면에 나가는 값 중 **상표가 박힌 곳을 전부 찾는다**. 2026-07-27

🔴 왜 — 재료명만 고쳐도 화면에 상표가 남았다. `뫼루니 베이직 치킨용파우더 5kg` 이
   37개 페이지에 있었는데 `ingredients.name` 에는 없었다. 다른 칼럼에 박혀 있던 것이다.
   그래서 **DB 전체 TEXT 칼럼을 훑는다.** 추측하지 않는다.

대표 지시 (2026-07-27):
   *"곰곰으로 나오면서 나오는 재료 로켓프레시 나오면서 나오는 재료 그다음 뫼루니 나오면서
     나오는 재료 싹제거하고 이런게 또있나만 확인하고 수정하면 됨"*

    python scripts/brand_scrub_find.py
    python scripts/brand_scrub_find.py --word 곰곰       # 한 낱말만
"""
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
sys.stdout.reconfigure(encoding="utf-8")

# 화면에서 보이면 안 되는 낱말 — 몰 이름 · 쿠팡 PB · 제조사
WORDS = [
    "로켓프레시", "로켓배송", "로켓와우", "쿠팡", "곰곰", "탐사", "코멧",
    "뫼루니", "움트리", "곰표", "사조오양", "아이엠소스", "어나더소스", "금양식품",
    "백설", "해표", "큐원", "오뚜기", "청정원", "샘표", "해찬들", "다담", "비셰프",
    "썬리취", "쉐프원", "밀락", "무화당", "하인즈", "마니커", "하림", "지도표성경",
    "태영", "이슬나라", "미나토", "하오츠", "한울식품", "춘풍접객", "송림푸드", "선인",
]

# 화면에 나가는 칼럼만 본다 — 내부 근거(wholesale_basis)는 상표가 있어야 재검증이 된다
SCREEN = {
    ("ingredients", "display_name"),
    ("ingredients", "name"),
    ("menu_ingredients", "composition"),
    ("menus", "recipe_steps"),
    ("menus", "name"),
    ("menus", "uncosted_note"),
    ("menu_mealkit", "name"),
    ("ingredient_retail", "name"),
    ("dish_def", "name"),
    ("dish_def", "recipe_steps"),
    ("brand_menu_official", "name"),
}


def main():
    only = None
    if "--word" in sys.argv:
        only = sys.argv[sys.argv.index("--word") + 1]
    words = [only] if only else WORDS

    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    c.row_factory = sqlite3.Row

    tabs = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]

    print("=" * 96)
    print("상표가 박힌 곳 — 화면에 나가는 칼럼")
    print("=" * 96)
    total = 0
    for t in sorted(tabs):
        try:
            cols = [r[1] for r in c.execute("PRAGMA table_info(%s)" % t)]
        except Exception:
            continue
        for col in cols:
            if (t, col) not in SCREEN:
                continue
            for w in words:
                try:
                    n = c.execute("SELECT COUNT(*) FROM %s WHERE %s LIKE ?" % (t, col),
                                  ("%" + w + "%",)).fetchone()[0]
                except Exception:
                    continue
                if not n:
                    continue
                total += n
                print()
                print("🔴 %s.%s  «%s»  %d건" % (t, col, w, n))
                for r in c.execute("SELECT %s v FROM %s WHERE %s LIKE ? LIMIT 4"
                                   % (col, t, col), ("%" + w + "%",)):
                    print("     %s" % (r["v"] or "").replace("\n", " ⏎ ")[:88])

    print()
    print("=" * 96)
    print("합계 %d건" % total)

    # 화면에 안 나가는 곳(근거·내부)에도 있는지 — 여긴 **지우지 않는다**. 있어야 재검증이 된다
    print()
    print("── 참고: 근거·내부 칼럼 (여긴 상표를 남긴다) ──")
    for t, col in (("ingredients", "wholesale_basis"), ("ingredients", "name_note"),
                   ("ingredient_retail", "url"), ("menu_coupang", "name"),
                   ("menu_sikbom", "name")):
        try:
            n = c.execute("SELECT COUNT(*) FROM %s WHERE %s IS NOT NULL AND %s<>''"
                          % (t, col, col)).fetchone()[0]
            print("   %s.%s  %d행" % (t, col, n))
        except Exception as e:
            print("   %s.%s  ERR %s" % (t, col, str(e)[:30]))


if __name__ == "__main__":
    main()
