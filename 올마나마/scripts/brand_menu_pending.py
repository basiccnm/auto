# -*- coding: utf-8 -*-
"""수집 JSON 과 DB 를 대조해 **아직 안 넣은 것**을 찾는다. 2026-07-28 신설

    python scripts/brand_menu_pending.py

🔴 왜 필요한가 (2026-07-28 사고)
   수집 세션이 JSON 을 **여러 번 갱신한다.** 처음엔 골격만 주고, 나중에 가격을 채워 다시 준다.
   그런데 «메뉴 수가 같으면 이미 반영된 것» 으로 판정하다가 **가격만 채워진 갱신을 통째로 놓쳤다.**
   호식이지두마리치킨은 JSON 에 가격 24개가 있는데 DB 는 0개인 채로 라이브에 나가 있었다.
   → **메뉴 수와 가격 수를 둘 다** 본다.

⛔ 브랜드가 DB 에 없으면 그것도 알려준다 — 등록부터 해야 적재된다.
"""
import glob
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                    # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(BASE, "data", "brand_menu_list")


def main():
    c = store.connect()
    todo, miss, ok = [], [], 0
    for f in sorted(glob.glob(os.path.join(DIR, "*.json"))):
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue
        if "cats" not in d or "menus" not in d:
            continue
        r = c.execute("""SELECT b.id,b.name,b.published,
              (SELECT count(*) FROM brand_menu_official o WHERE o.brand_id=b.id) n,
              (SELECT count(*) FROM brand_menu_official o
                 WHERE o.brand_id=b.id AND o.price IS NOT NULL) np
              FROM brands b WHERE b.slug=? OR b.name=?""",
                      (d.get("slug"), d.get("brand"))).fetchone()
        base = os.path.basename(f)
        mt = time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(f)))
        jn = len(d["menus"])
        jp = sum(1 for m in d["menus"] if m.get("price"))
        if not r:
            miss.append((base, d.get("slug"), d.get("brand"), jn, jp, mt))
            continue
        # 🔴 메뉴 수만 보면 «가격만 채워진 갱신» 을 놓친다
        if r["n"] != jn or r["np"] != jp:
            todo.append((base, r["name"], "공개" if r["published"] else "비공개",
                         jn, jp, r["n"], r["np"], mt))
        else:
            ok += 1

    if miss:
        print("■ 브랜드가 DB 에 없다 — 먼저 등록해야 한다 (%d건)" % len(miss))
        for x in miss:
            print("   %-24s slug=%-16s %-16s 메뉴 %3d 가격 %3d  %s" % x)
        print()
    print("■ 적재 필요 %d건  (이미 맞는 것 %d건)" % (len(todo), ok))
    if todo:
        print("   %-24s %-14s %-4s %6s %6s %6s %6s  %s"
              % ("파일", "브랜드", "공개", "J메뉴", "J가격", "DB메뉴", "DB가격", "JSON시각"))
        for x in todo:
            print("   %-24s %-14s %-4s %6d %6d %6d %6d  %s" % x)
        print()
        print("넣으려면:")
        for x in todo:
            print("   python scripts/brand_menu_import.py data/brand_menu_list/%s --apply" % x[0])


if __name__ == "__main__":
    main()
