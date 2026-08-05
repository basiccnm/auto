# -*- coding: utf-8 -*-
"""표준 탭(`menu_tab.py`)을 메뉴판 전체에 적용한다. 2026-07-28
(대표 지시: *"각 브랜드별 탭메뉴 동일하게 적용해"*)

    python scripts/menu_tab_apply.py            # 미리보기
    python scripts/menu_tab_apply.py --apply

🔴 원본을 지우지 않는다 — 브랜드가 준 카테고리는 `category_raw` 에 남긴다.
   판정이 틀렸을 때 되돌릴 근거가 사라지면 안 된다.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
from menu_tab import order_key, tab_of                          # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")


def main():
    apply_ = "--apply" in sys.argv
    c = sqlite3.connect(DB, timeout=90)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    have = {r[1] for r in cur.execute("PRAGMA table_info(brand_menu_official)")}
    if "category_raw" not in have:
        cur.execute("ALTER TABLE brand_menu_official ADD COLUMN category_raw TEXT")
        cur.execute("UPDATE brand_menu_official SET category_raw=category")
        c.commit()
        print("· category_raw 신설 — 브랜드가 준 원본을 보존했다\n")

    # 🔴 브랜드 업종을 함께 넘긴다 — 이름으로 못 정한 메뉴의 마지막 폴백
    #    (피자집의 「옥수동 새우집」은 피자다. 「기타」보다 낫다)
    # 🔴 `COALESCE(category_raw, category)` 로 두면 **이미 표준화한 값이 다시 입력**이 되어
    #    규칙을 고쳐도 «0줄 변경» 이 나온다(2026-07-28. 「레드콘 피자」가 디저트에 고정됐다).
    #    원본이 없으면 **빈 값**을 넘겨 이름으로만 다시 판정하게 한다.
    rows = cur.execute("""SELECT o.rowid rid, b.name bn, o.name, o.category,
                          o.category_raw craw,
                          COALESCE(c.name,'') bcat
                          FROM brand_menu_official o
                          JOIN brands b ON b.id=o.brand_id
                          LEFT JOIN categories c ON c.id=b.category_id""").fetchall()
    n, by = 0, {}
    for r in rows:
        t = tab_of(r["name"], r["craw"], r["bcat"])
        by.setdefault(r["bn"], {}).setdefault(t, 0)
        by[r["bn"]][t] += 1
        if r["category"] != t:
            n += 1
            if apply_:
                cur.execute("UPDATE brand_menu_official SET category=? WHERE rowid=?",
                            (t, r["rid"]))
    if apply_:
        c.commit()

    for bn, d in sorted(by.items(), key=lambda x: -sum(x[1].values()))[:12]:
        print("● %-15s %s" % (bn[:15], " / ".join(
            "%s %d" % (t, d[t]) for t in sorted(d, key=order_key))))
    tot = {}
    for d in by.values():
        for t, v in d.items():
            tot[t] = tot.get(t, 0) + v
    print("\n전체 %s" % " / ".join("%s %d" % (t, tot[t]) for t in sorted(tot, key=order_key)))
    print("\n%d줄 탭 변경%s" % (n, " ✅ 반영" if apply_ else " (미적용 — --apply)"))


if __name__ == "__main__":
    main()
