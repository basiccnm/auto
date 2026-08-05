# -*- coding: utf-8 -*-
"""재료 표 건강검진 — **쓰레기가 다시 쌓이는 것을 막는다.** 2026-08-03

왜 만들었나 (대표 지시: *"저거 다신 말 안 나오게"*)
  하루 종일 같은 게 반복해서 튀어나왔다 —
  「속재료」·「매운고기」·「기본겉절이」처럼 **뜻도 불분명하고 아무 데도 안 쓰는 재료**,
  없는 재료를 가리키는 **고아 별칭**, `naver`·`coef`·미트박스 같은 **폐기된 근거**.
  그때마다 대표가 하나씩 짚어줘야 했다. 그래서 **한 줄로 전부 뽑아 보는 것**을 만든다.

  2026-08-03 정리 결과: 재료 764 → 424종 (미사용 340종 삭제)

    python scripts/ingredient_audit.py          # 검사만
    python scripts/ingredient_audit.py --clean   # 미사용·고아 정리(백업 뒤)
"""
import collections
import io
import json
import os
import shutil
import sqlite3
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
WTMAP = os.path.join(BASE, "data", "wtable", "ing_map_auto.json")
sys.stdout.reconfigure(encoding="utf-8")

# 🔴 **지우면 안 되는 재료** — 「아직 안 쓴다」와 「쓸모없다」는 다르다 (2026-08-03 사고)
#    `mb_` 267종은 **대표가 직접 긁어 올린 마라탕 도매 상품 목록**이다.
#    메뉴에 아직 안 붙었다는 이유로 지웠다가 되돌렸다 — 대표: *"내가 올려둔 거 그냥 두라고"*
#    ⛔ 사람이 모아둔 원천 데이터는 미사용이어도 건드리지 않는다.
KEEP_PREFIX = ("mb_",)      # 마라탕 도매 원본


def protected(key):
    return key.startswith(KEEP_PREFIX)


# 🔴 **제철 재료는 「없는 것」이 아니다** — 지금 철이 아니라 식봄에 안 올라올 뿐이다.
#    2026-08-03: 달래·봄동·산딸기·두릅을 「없다」고 계속 보고해서 대표가 매번 정정해야 했다.
#    *"제철이라고 해서 안 보이게 하라고 왜 말할 때마다 갖고 와"*
#    → `ingredient_seasonal` 표에 있으면 **목록에서 뺀다.** 제철이 오면 그때 받는다.
def seasonal_names(c):
    try:
        return {r[0] for r in c.execute("SELECT name FROM ingredient_seasonal")}
    except Exception:
        return set()


# 🔴 폐기된 도매 근거 — 이게 붙어 있으면 식봄으로 다시 받아야 한다
DEAD_BASIS = (
    ("미트박스", "2026-07-27 «쓰지 말 것» 방침 — 고기도 식봄"),
    ("kamis", "KAMIS 는 지표 전용. 개별 원가에 쓰지 않는다"),
    ("naver", "옛 방식. 도매 정본은 식봄"),
    ("네이버", "옛 방식. 도매 정본은 식봄"),
    ("coef", "계수 추정 — 실측이 아니다"),
    ("계수", "계수 추정 — 실측이 아니다"),
)


def recipe_use():
    """우리의식탁 레시피가 쓰는 재료 — 매칭 결과 파일에서."""
    if not os.path.exists(WTMAP):
        return collections.Counter()
    c = collections.Counter()
    for nm, v in json.load(io.open(WTMAP, encoding="utf-8")).items():
        if v.get("key"):
            c[v["key"]] += v.get("count", 0)
    return c


def main():
    clean = "--clean" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    wt = recipe_use()

    rows = c.execute("""SELECT ingredient_key k, name, display_name dn, base_unit bu,
        wholesale_price wp, manual_price mp, wholesale_basis wb,
        (SELECT COUNT(*) FROM menu_ingredients m WHERE m.ingredient_key=i.ingredient_key) mu,
        (SELECT COUNT(*) FROM dish_ingredients d WHERE d.ingredient_key=i.ingredient_key) du,
        (SELECT COUNT(*) FROM dish_def_ingredient dd WHERE dd.ingredient_key=i.ingredient_key) dd
        FROM ingredients i""").fetchall()
    print("재료 %d종" % len(rows))
    print()

    # ① 아무 데도 안 쓰이는 재료
    dead = [r for r in rows if not (r["mu"] or r["du"] or r["dd"] or wt.get(r["k"], 0))]
    print("① 미사용 재료 %d종  (메뉴·요리·요리정의·레시피 어디에도 없음)" % len(dead))
    for r in dead[:12]:
        print("     %-24s %s" % (r["k"], r["name"]))
    if len(dead) > 12:
        print("     … 외 %d종" % (len(dead) - 12))

    # ② 없는 재료를 가리키는 별칭 — 매칭은 «성공»인데 값이 없어 조용히 빠진다
    orphan = c.execute("""SELECT alias_raw, ingredient_key FROM ingredient_alias a
        WHERE NOT EXISTS(SELECT 1 FROM ingredients i WHERE i.ingredient_key=a.ingredient_key)""").fetchall()
    print()
    print("② 고아 별칭 %d건  (없는 재료를 가리킨다 — 레시피 252개가 이것 때문에 빠진 적 있다)" % len(orphan))
    for r in orphan[:10]:
        print("     %-24s → %s" % (r["alias_raw"], r["ingredient_key"]))

    # ③ 값이 없는 재료
    nowp = [r for r in rows if not r["wp"] and r["k"] != "water"]
    print()
    print("③ 도매가 없는 재료 %d종" % len(nowp))
    for r in nowp[:10]:
        print("     %-24s %s" % (r["k"], r["name"]))

    # ④ 폐기된 근거
    print()
    print("④ 폐기된 도매 근거")
    for pat, why in DEAD_BASIS:
        xs = [r for r in rows if pat.lower() in (r["wb"] or "").lower()]
        if xs:
            print("     %-8s %3d종 — %s" % (pat, len(xs), why))
            for r in xs[:4]:
                print("         %-22s %-16s %s원" % (r["k"], (r["dn"] or r["name"])[:16],
                                                     format(r["wp"] or 0, ",")))

    # ⑤ 단위가 개·마리인데 값이 kg 시세처럼 큰 것 — 계란 사고 유형
    print()
    piece = [r for r in rows if r["bu"] in ("개", "마리", "장", "모", "세트") and (r["wp"] or 0) > 3000]
    print("⑤ 개수 단위인데 값이 큰 재료 %d종  (kg 시세를 잘못 넣었을 수 있다)" % len(piece))
    for r in piece[:10]:
        print("     %-24s %-14s %-3s %s원" % (r["k"], (r["dn"] or r["name"])[:14], r["bu"],
                                              format(r["wp"], ",")))

    # ⑥ 이름 겹침
    print()
    dup = {k: v for k, v in collections.Counter(r["name"] for r in rows).items() if v > 1}
    print("⑥ 이름이 겹치는 재료 %d개" % len(dup))
    for nm, n in dup.items():
        print("     %-18s %d개  %s" % (nm, n, [r["k"] for r in rows if r["name"] == nm]))

    if not clean:
        print()
        print("→ 정리하려면 `--clean` (①미사용 · ②고아 별칭만 지운다. 값은 안 건드린다)")
        return

    bak = os.path.join(BASE, "data", "eolmanama_bak_audit_%s.db" % time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy(DB, bak)
    print()
    print("백업 → %s" % os.path.basename(bak))
    tabs = [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for r in dead:
        for t in tabs:
            cols = [x[1] for x in c.execute("PRAGMA table_info(%s)" % t)]
            if "ingredient_key" in cols and t != "ingredients":
                c.execute("DELETE FROM %s WHERE ingredient_key=?" % t, (r["k"],))
        c.execute("DELETE FROM ingredients WHERE ingredient_key=?", (r["k"],))
    c.execute("""DELETE FROM ingredient_alias WHERE ingredient_key NOT IN
                 (SELECT ingredient_key FROM ingredients)""")
    c.commit()
    print("✅ 미사용 %d종 · 고아 별칭 %d건 삭제 → 재료 %d종"
          % (len(dead), len(orphan), c.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0]))


if __name__ == "__main__":
    main()
