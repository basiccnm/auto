# -*- coding: utf-8 -*-
"""맘스터치 **버거 세트** 가격을 만들어 넣는다. 2026-07-28

    python scripts/momstouch_set.py            # 미리보기
    python scripts/momstouch_set.py --apply

근거 (대표 확인 2026-07-28)
--------------------------
앱 상세 화면에 «옵션 선택 / 단품 6,700원 / 세트 9,200원» 이 함께 뜬다.
차액이 **정확히 2,500원**이고, 그게 «음료 + 감자튀김» 값이다.

    어메이징매콤마요버거   단품 6,700  →  세트 9,200   (+2,500)

🔴 그래서 메뉴를 100번 눌러 상세를 열 필요가 없다. **단품가 + 2,500** 이면 된다.

⛔ **버거에만 적용한다.** 치킨·사이드·음료·디저트는 세트 구성이 다르거나 없다.
⛔ 이미 이름에 «세트» 가 붙은 메뉴(커플세트·싱글세트 등)는 건드리지 않는다 —
   그건 앱이 준 실제 값이다.
⛔ 사람이 확정한 행(`decided_at`)은 자동으로 덮지 않는다.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import menu_price_store as PS                                    # noqa: E402

BRAND = "맘스터치"
SET_ADD = 2500          # 음료 + 감자튀김
NOTE = "단품가 + 2,500원(음료·감자튀김) — 앱 상세 기준"


def main():
    apply_ = "--apply" in sys.argv
    db = PS.connect()
    cur = db.cursor()
    br = cur.execute("SELECT id FROM brands WHERE name=?", (BRAND,)).fetchone()
    if not br:
        print("🔴 DB 에 «%s» 브랜드가 없다" % BRAND)
        return

    rows = cur.execute("""SELECT name, price FROM brand_menu_official
                          WHERE brand_id=? AND price>0 ORDER BY name""", (br["id"],)).fetchall()
    # 버거 단품만 — 이름에 «세트» 가 이미 있으면 제외
    targets = [r for r in rows
               if "버거" in r["name"] and not re.search(r"세트", r["name"])]
    print("● %s — 버거 단품 %d개 → 세트 만들기 (+%s원)\n"
          % (BRAND, len(targets), format(SET_ADD, ",")))

    now = __import__("datetime").datetime.now().isoformat(" ", "seconds")
    new = same = skip = 0
    for r in targets:
        nm = r["name"].strip() + " 세트"
        pr = r["price"] + SET_ADD
        exist = cur.execute("""SELECT price, decided_at FROM brand_menu_official
                               WHERE brand_id=? AND name=?""", (br["id"], nm)).fetchone()
        mark = " "
        if exist and exist["decided_at"]:
            skip += 1
            mark = "·"                      # 사람이 확정 — 건드리지 않는다
        elif exist:
            same += 1
            mark = "="
        else:
            new += 1
            mark = "+"
        print("  %s %-30s %8s원  ← 단품 %s원"
              % (mark, nm[:30], format(pr, ","), format(r["price"], ",")))
        if apply_ and not (exist and exist["decided_at"]):
            PS.put(cur, br["id"], nm, pr, source=PS.SRC_OFFICIAL, note=NOTE, now=now)
            db.commit()

    print("\n새로 %d · 이미 있던 것 %d · 사람확정이라 건너뜀 %d" % (new, same, skip))
    if not apply_:
        print("(미저장 — --apply)")
    else:
        n = cur.execute("""SELECT COUNT(*) n FROM brand_menu_official
                           WHERE brand_id=? AND price>0""", (br["id"],)).fetchone()["n"]
        print("✅ 반영 — %s 가격 있는 메뉴 %d개" % (BRAND, n))


if __name__ == "__main__":
    main()
