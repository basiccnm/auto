# -*- coding: utf-8 -*-
"""레시피 본문 자가검수 — DB 에 쓰기 전에 «재료가 실제로 잡히는지» 먼저 본다. (읽기 전용)

왜 필요한가
-----------
`recipe_apply.py` 는 본문에서 「이름 + 양 + 단위」를 정규식으로 뽑는다.
그 정규식에 안 걸리는 표기(`섞고 65g`·`찬물 60ml`·`육수 30ml`)나
base_unit 과 안 맞는 단위(`고추기름 30ml` — DB 는 kg 기준)를 써 두면
**조용히 원가에서 빠지거나 단위가 뒤바뀐다.** 적재하고 나서야 알게 된다.

그래서 본문을 쓰는 단계에서 **같은 정규식으로 미리 돌려본다.**
DB 는 읽기만 하고 아무것도 바꾸지 않는다.

사용법
------
    python scripts/recipe_check.py                    # data/recipes_new/ 전체
    python scripts/recipe_check.py kimchi-jjigae ...  # 슬러그만 골라서

출력의 ❌ 두 종류
    미매칭 : 재료처럼 생겼는데 DB 이름·화면이름·별칭 어디에도 안 붙는 것
    단위   : 붙긴 했는데 base_unit 과 어긋나는 것 (개·마리에 g 등)
"""
import glob
import io
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "eolmanama.db")
SRC = os.path.join(ROOT, "data", "recipes_new")

# ⚠️ recipe_apply.py 와 **같은 정규식**이어야 의미가 있다. 거기가 바뀌면 여기도 바꾼다.
UNIT = r"(?:g|ml|kg|L|개|장|모|대|쪽|줌|마리|알|봉|팩|캔|조각|큰술|작은술|컵|세트)"
AMT = r"(\d+(?:\.\d+)?|[½¼¾])\s*(" + UNIT + r")(?![A-Za-z0-9])"
ING_ANY = re.compile(r"(?<![가-힣])([가-힣A-Za-z][가-힣A-Za-z0-9]{0,13})\s*" + AMT)

# base_unit 이 왼쪽일 때 본문에 써도 되는 단위
#
# 🔴 **여기 기준은 `compute_line_costs.to_base()` 와 같아야 한다.**
#    처음엔 이보다 좁게 잡았다가 기존 74편에서 8건을 오탐했다(2026-08-14) —
#    `치킨무 1세트`(base=개)·`냉면육수 500ml`(base=kg). 둘 다 원가는 이미
#    정상으로 계산되고 있었다. `to_base` 가 kg↔ml(밀도 1 가정)과 개↔세트를
#    허용하기 때문이다. **파이프라인이 받는 표기를 검수기가 막으면 안 된다.**
#    ⚠️ `to_base` 를 고치면 이 표도 같이 고칠 것.
OK_UNIT = {
    "kg": {"kg", "g", "ml", "L"},
    "L": {"L", "ml", "g", "kg"},
    "개": {"개", "세트", "장", "마리"},
}
# base_unit 이 위에 없으면(마리·포기 등) `to_base` 가 그대로 통과시키므로 검사하지 않는다


def load_names(conn):
    """DB 이름·화면이름·별칭 → ingredient_key, 그리고 key → base_unit."""
    key_of, unit_of = {}, {}
    for k, n, u in conn.execute(
            "SELECT ingredient_key,name,base_unit FROM ingredients"):
        key_of[n] = k
        unit_of[k] = u
    for k, d in conn.execute(
            "SELECT ingredient_key,display_name FROM ingredients WHERE display_name<>''"):
        key_of.setdefault(d, k)
    for k, a in conn.execute(
            "SELECT ingredient_key,alias_raw FROM ingredient_alias WHERE alias_raw<>''"):
        key_of.setdefault(a, k)
    return key_of, unit_of


def main(slugs):
    conn = sqlite3.connect(DB)
    key_of, unit_of = load_names(conn)
    # 긴 이름부터 — 「무」가 「무뼈닭발」을 가로채지 않게
    alt = "|".join(re.escape(v) for v in sorted(key_of, key=len, reverse=True))
    name_rx = re.compile(r"(?<![가-힣])(" + alt + r")\s*" + AMT)

    files = ([os.path.join(SRC, s + ".txt") for s in slugs] if slugs
             else sorted(glob.glob(os.path.join(SRC, "*.txt"))))

    bad = 0
    for path in files:
        slug = os.path.splitext(os.path.basename(path))[0]
        txt = io.open(path, encoding="utf-8").read()
        steps = [l for l in txt.splitlines() if l.strip()]

        hits = {m.group(1) for m in name_rx.finditer(txt)}
        miss, unitbad = set(), set()
        for m in ING_ANY.finditer(txt):
            nm, amt, un = m.group(1), m.group(2), m.group(3)
            if any(nm.endswith(h) or h.endswith(nm) for h in hits):
                continue
            miss.add("%s %s%s" % (nm, amt, un))
        for m in name_rx.finditer(txt):
            nm, un = m.group(1), m.group(3)
            bu = unit_of[key_of[nm]]
            if bu in OK_UNIT and un not in OK_UNIT[bu]:
                unitbad.add("%s %s (base=%s)" % (nm, un, bu))

        flag = "  ❌" if (miss or unitbad) else ""
        if flag:
            bad += 1
        print("%-24s 단계 %2d · 재료 %2d%s" % (slug, len(steps), len(hits), flag))
        if miss:
            print("    미매칭:", ", ".join(sorted(miss)))
        if unitbad:
            print("    단위:", ", ".join(sorted(unitbad)))

    print("\n검수 끝 — 문제 파일 %d개 / %d개" % (bad, len(files)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
