# -*- coding: utf-8 -*-
"""우리 메뉴 ↔ 네이버 플레이스 메뉴 **이름 잇기 후보**를 보여준다. 2026-07-27

대조에서 «이름 없음» 이 100건 넘게 남는다 — 우리 메뉴명이 플레이스와 달라서다.
(`싸이버거 단품` vs `싸이버거`, `엄청 큰 양념 치킨` vs `엄청큰 양념치킨` …)

이름을 이어야 판매가·재료가 붙고, 그래야 원가계산기·레시피·딥링크가 선다.

⛔ 자동 반영하지 않는다. 사람이 보고 고른 것만 넣는다
   (`ingredient-match-practical-not-exact` · 가격 ±35% 밖은 후보에서 뺀다).

    python scripts/place_name_suggest.py            # 전체
    python scripts/place_name_suggest.py 맘스터치
"""
import io
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "place_menu")

DROP = ("단품", "세트", "1인분", "(소)", "(중)", "(대)", "(면/밥)", "(뼈)", "(순살)")


def key(s):
    s = re.sub(r"\((?:행사|NEW|신메뉴)\)", "", s)
    for d in DROP:
        s = s.replace(d, "")
    return re.sub(r"\s+|[·,ㆍ]", "", s).lower()


def score(a, b):
    """겹치는 글자 비율 — 0~1"""
    A, B = set(a), set(b)
    return len(A & B) / max(1, len(A | B))


def main():
    only = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    files = {f[:-len("_menu.txt")]: os.path.join(SRC, f)
             for f in os.listdir(SRC) if f.endswith("_menu.txt")} if os.path.isdir(SRC) else {}

    n = 0
    for b in c.execute("""SELECT id, name FROM brands WHERE published=1 ORDER BY frcs_cnt DESC"""):
        k = re.sub(r"[^0-9A-Za-z가-힣]+", "", b["name"])
        if k not in files or (only and only not in b["name"]):
            continue
        place = []
        for line in io.open(files[k], encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2 and p[1].isdigit():
                place.append((p[0], int(p[1])))
        if not place:
            continue
        rows = c.execute("""SELECT m.id, m.name, m.sell_price FROM menus m
                            LEFT JOIN menu_verified v ON v.menu_id=m.id
                            WHERE m.brand_id=? AND v.menu_id IS NULL""", (b["id"],)).fetchall()
        if not rows:
            continue
        head = False
        for m in rows:
            mk, sell = key(m["name"]), m["sell_price"] or 0
            cands = []
            for pn, pv in place:
                s = score(mk, key(pn))
                # 🔴 가격이 크게 벌어지면 다른 메뉴다 — 세트/사이드를 물지 않게 막는다
                if sell and not (sell * 0.65 <= pv <= sell * 1.35):
                    continue
                if s >= 0.45:
                    cands.append((s, pn, pv))
            if not cands:
                continue
            if not head:
                print("\n● %s" % b["name"])
                head = True
            cands.sort(reverse=True)
            n += 1
            print("   [%d] %-22s 우리 %7s" % (m["id"], m["name"][:22], format(sell, ",")))
            for s, pn, pv in cands[:3]:
                mark = "★" if pv == sell else " "
                print("        %s %-26s %7s  (겹침 %.2f)" % (mark, pn[:26], format(pv, ","), s))
    print("\n%s\n후보가 있는 메뉴 %d개  · ★ 는 값까지 같은 것" % ("=" * 66, n))


if __name__ == "__main__":
    main()
