# -*- coding: utf-8 -*-
"""가공·소스·장류·면 등을 식봄 카테고리 기준으로 반영. (2026-07-25)

가공은 브랜드·용량이 많아 최저가 하나로 못 잡는다 → **중앙값(대표값)**.
  - 범위(최저~최고)는 참고, 대표값=중앙값(광고·미끼최저·소포장튐 안 탐).
  - 핵심어 매칭 + 가공 BAD 필터.
  - 식봄이 지금값보다 3배↑면 오매칭이라 버림. 식봄이 비싸면 기본값 안 덮음.
  - 카테고리 잎 이름이 재료 핵심어에 걸리는 것만. 애매하면 건너뜀(정확성 우선).

소스 = data/research/foodspring/_가공카테고리.json  (대분류>잎)
"""
import json, io, os, re, sqlite3, sys, shutil

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
CAT = os.path.join(BASE, "data", "research", "foodspring", "_가공카테고리.json")
STAMP = "2026-07-25"

BAD = re.compile(r"세트|선물|증정|샘플|기획전")


def norm(s):
    return (s or "").replace(" ", "")


def core(name):
    k = re.sub(r"[\(\[].*?[\)\]]", "", name).strip()
    k = re.sub(r"\s*\d.*$", "", k).strip()
    return k or name


def main():
    dry = "--apply" not in sys.argv
    cat = json.load(io.open(CAT, encoding="utf-8"))
    # 잎 이름 → 상품들
    leaves = {}
    for label, items in cat.items():
        leaf = label.split(">")[-1]
        leaves.setdefault(leaf, []).extend(items)

    if not dry:
        shutil.copy2(DB, DB + ".bak-20260725-processed")
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # 반영 대상 = 아직 식봄/미트박스 아닌 kg 재료 (마라탕 mb_ 제외 — 별도 처리)
    rows = cur.execute(
        "select ingredient_key, name, wholesale_price from ingredients "
        "where base_unit='kg' and ingredient_key not like 'mb_%' "
        "and coalesce(wholesale_basis,'') not like '식봄%' "
        "and coalesce(wholesale_basis,'') not like '미트박스%'").fetchall()

    print("%-20s %8s %8s %8s  n  %s" % ("재료", "지금", "중앙", "범위", "잎"))
    print("-" * 78)
    n_ing = n_row = 0
    for key, name, wp in rows:
        kw = core(name)
        k2 = norm(kw)
        # 잎 이름이 핵심어에 들어가거나(간장→간장), 핵심어가 잎에(진간장→간장)
        best = None
        for leaf, items in leaves.items():
            if len(leaf) < 2:
                continue
            # 잎 이름이 재료명에 들어가는 경우만(진간장⊃간장). 반대방향(김가루⊂튀김가루,
            # 새우⊂새우튀김, 낙지⊂낙지젓)은 오매칭이라 뺀다.
            if leaf in kw or norm(leaf) in k2:
                g = [r for r in items if r.get("won_per_kg") and k2 in norm(r["name"])
                     and not BAD.search(r["name"])]
                if g:
                    best = (leaf, g)
                    break
        if not best:
            continue
        leaf, g = best
        # 이상치 컷: 지금값 3배 초과 제거
        if wp:
            g = [r for r in g if r["won_per_kg"] <= wp * 3]
        if not g:
            continue
        vals = sorted(r["won_per_kg"] for r in g)
        med = vals[len(vals) // 2]
        lo, hi = vals[0], vals[-1]

        # 원산지별 최저(표에 여러 줄) — 가공은 원산지 거의 없어 대부분 미표기
        byo = {}
        for r in g:
            o = r.get("origin") or "미표기"
            if o not in byo or r["won_per_kg"] < byo[o]["won_per_kg"]:
                byo[o] = r

        print("%-20s %8s %8s %s  %2d  %s" % (
            name[:20], f"{wp or 0:,}", f"{med:,}", "%s~%s" % (f"{lo:,}", f"{hi:,}"),
            len(g), leaf))

        if not dry:
            cur.execute("delete from ingredient_price where ingredient_key=? and source='식봄'", (key,))
            for o, r in byo.items():
                b = "식봄(카테고리·%s) %s 중앙값 %s원 (범위 %s~%s, n=%d) / %s" % (
                    leaf, STAMP, f"{med:,}", f"{lo:,}", f"{hi:,}", len(g), r["name"][:26])
                cur.execute("insert or replace into ingredient_price(ingredient_key,tier,kind,"
                            "origin,part,grade,brand,form,price,pack_kg,source,basis,is_default,"
                            "checked_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (key, "도매", None, o, None, r.get("grade"), None, "식봄",
                             r["won_per_kg"], r.get("pack_kg"), "식봄", b, 0, STAMP))
                n_row += 1
            # 기본값 = 중앙값. 지금값이 더 싸면 유지.
            if not wp or med < wp:
                cur.execute("update ingredients set wholesale_price=?, wholesale_basis=?, "
                            "updated_at=? where ingredient_key=?",
                            (med, "식봄 %s %s 중앙값 %s원/kg (범위 %s~%s)" % (
                             STAMP, leaf, f"{med:,}", f"{lo:,}", f"{hi:,}"), STAMP, key))
        n_ing += 1

    if dry:
        print("\n자동매칭 %d종. ※ 미리보기. 쓰려면  --apply" % n_ing)
    else:
        con.commit()
        print("\n가공 %d종 · 표 %d행 반영." % (n_ing, n_row))


main()
