# -*- coding: utf-8 -*-
"""레시피 원가를 막고 있는 재료를 뽑는다. 2026-08-03

**제철 재료는 빼고 보여준다.** `ingredient_seasonal` 표에 있으면 「없는 것」이 아니라
«지금 철이 아니라 식봄에 안 올라오는 것»이다 — 목록에 올리지 않는다.
2026-08-03 에 달래·봄동·산딸기·두릅을 계속 「없다」고 보고해서 대표가 매번 정정해야 했다.

    python scripts/recipe_gap.py           # 막는 재료 상위
    python scripts/recipe_gap.py --all     # 제철 포함 전부
"""
import collections
import io
import json
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
WTMAP = os.path.join(BASE, "data", "wtable", "ing_map_auto.json")
RECIPES = os.path.join(BASE, "data", "wtable", "merged_recipes.jsonl")
sys.stdout.reconfigure(encoding="utf-8")


def main():
    show_all = "--all" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        seasonal = {r["name"]: (r["season"], r["note"])
                    for r in c.execute("SELECT name, season, note FROM ingredient_seasonal")}
    except sqlite3.OperationalError:
        seasonal = {}
    mp = json.load(io.open(WTMAP, encoding="utf-8"))
    wp = {k: v for k, v in c.execute("SELECT ingredient_key, wholesale_price FROM ingredients")}

    ok, blocked = [], collections.Counter()
    for line in io.open(RECIPES, encoding="utf-8"):
        r = json.loads(line)
        ings = [i for g in (r.get("groups") or []) for i in (g.get("ings") or [])
                if (i.get("n") or "").strip()]
        if not ings:
            continue
        bad = []
        for i in ings:
            nm = (i.get("n") or "").strip()
            k = mp.get(nm, {}).get("key")
            if not k:
                bad.append(nm)
            elif k != "water" and not wp.get(k):
                bad.append(nm + "(가격없음)")
        if bad:
            for b in bad:
                blocked[b] += 1
        else:
            ok.append(r["title"])

    tot = sum(v["count"] for v in mp.values())
    hit = sum(v["count"] for v in mp.values() if v.get("key"))
    print("재료 매칭 %.1f%%  ·  원가 나오는 레시피 %d개 / %d"
          % (100 * hit / tot, len(ok), len(ok) + len(set())))
    print()

    def is_seasonal(nm):
        base = nm.replace("(가격없음)", "").strip()
        return any(s in base for s in seasonal)

    shown = [(n, c2) for n, c2 in blocked.most_common() if show_all or not is_seasonal(n)]
    print("■ 막고 있는 재료 상위 25%s" % ("" if show_all else "  (제철 제외)"))
    for nm, cnt in shown[:25]:
        print("   %4d개  %s" % (cnt, nm))

    if seasonal and not show_all:
        skipped = [(n, c2) for n, c2 in blocked.most_common() if is_seasonal(n)]
        if skipped:
            print()
            print("■ 제철이라 뺀 것 %d종 — **없는 게 아니다**" % len(skipped))
            for nm, cnt in skipped[:10]:
                base = next((s for s in seasonal if s in nm), None)
                se, note = seasonal.get(base, ("", ""))
                print("   %4d개  %-10s %s · %s" % (cnt, nm, se, note))


if __name__ == "__main__":
    main()
