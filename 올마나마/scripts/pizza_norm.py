# -*- coding: utf-8 -*-
"""피자 L 사이즈 기본 3종(도우·치즈·소스)을 확립된 기준으로 맞춘다. (2026-07-27)

기준은 대표에게 다시 묻지 않는다 — **파파존스 세션에서 이미 확정된 값**이다:
    L 사이즈 = 피자도우 400g · 모차렐라 치즈 260g · 토마토소스 120g (정수)

왜 필요한가 — 같은 L 사이즈인데 브랜드·메뉴마다 값이 달랐다.
    도우 425 / 413 / 413.194 / 400 / 372   치즈 315.714 / 260 / 259.722 / 372
소수점 3자리는 **비율로 계산한 값**이 그대로 남은 것이다(실측이 아니다).

그리고 `양배추`·`당근` 은 피자에서 뺀다. 옛 «신선 채소»(3종 뭉치)를 양파50%·양배추30%·당근20%
로 자동 분해한 흔적이라(`cleanup_master2_20260720.py` ⑤) 피자 토핑 근거가 아니다.
`양파` 는 공식 토핑에 있는 브랜드가 있어(파파존스 수퍼파파스 40g) **자동으로 지우지 않는다.**

    python scripts/pizza_norm.py --brand 반올림피자          # 미리보기
    python scripts/pizza_norm.py --brand 반올림피자 --apply
    python scripts/pizza_norm.py --all                      # 피자 업종 전체 미리보기
"""
import argparse
import io
import os
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

# L 사이즈 기준 (파파존스 확정값)
STD_L = {"pizza_dough": 400.0, "cheese": 260.0, "sauce": 120.0, "pepperoni": 70.0}
# 피자에서 근거 없이 붙은 채소
DROP = ("양배추", "당근")


def keys(cur):
    """이름으로 재료 키를 찾는다 — 키가 브랜드마다 다를 수 있어 이름으로 잡는다."""
    out = {}
    for label, nm in (("pizza_dough", "피자도우"), ("cheese", "모차렐라 치즈"),
                      ("sauce", "토마토소스"), ("pepperoni", "페퍼로니")):
        r = cur.execute("SELECT ingredient_key FROM ingredients WHERE name=?", (nm,)).fetchone()
        if r:
            out[label] = r["ingredient_key"]
    drop = []
    for nm in DROP:
        r = cur.execute("SELECT ingredient_key FROM ingredients WHERE name=?", (nm,)).fetchone()
        if r:
            drop.append((nm, r["ingredient_key"]))
    return out, drop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--apply", action="store_true")
    # 🔴 기본값이 «안 지움» 이다 (2026-07-27 엽떡 사고).
    #    기본 구성에서 재료를 빼려면 «빠졌다는 근거» 가 있어야 한다. 5:3:2 패턴이 의심스럽다는
    #    것만으로는 부족하다 — 공식 설명문에서 그 브랜드 메뉴 구성을 확인한 뒤에만 지운다.
    ap.add_argument("--drop-veg", action="store_true",
                    help="양배추·당근 삭제. 공식 구성을 확인한 브랜드에만 쓸 것")
    a = ap.parse_args()
    if not a.brand and not a.all:
        ap.error("--brand <이름> 또는 --all 중 하나가 필요하다")

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    K, DROPK = keys(cur)

    q = ("SELECT m.id, m.name mn, b.name bn FROM menus m JOIN brands b ON b.id=m.brand_id "
         "WHERE b.category_id=(SELECT id FROM categories WHERE name='피자')")
    args = []
    if a.brand:
        q += " AND b.name=?"
        args.append(a.brand)
    q += " ORDER BY b.name, m.id"
    menus = cur.execute(q, args).fetchall()
    if not menus:
        print("대상 메뉴가 없다."); return

    n_up = n_del = 0
    for m in menus:
        # L 사이즈만 손댄다. 이름에 L 이 없으면(피자스쿨 등 단일 규격) 건드리지 않는다 —
        # 규격이 다른데 같은 값을 넣으면 그게 더 큰 오류다.
        is_L = m["mn"].strip().endswith(" L") or "(L)" in m["mn"]
        # 🔴 페퍼로니 70g 은 «페퍼로니가 주토핑인 메뉴» 기준이다 (2026-07-27 사고).
        #    복합 토핑 피자에 밀어 넣었다가 파파존스 수퍼파파스의 **공식 확인값 50g** 을 덮었다.
        #    수퍼디럭스 45 · 수퍼슈프림 43 처럼 여러 토핑 중 하나일 땐 그 값이 맞다.
        is_pep = ("페퍼로니" in m["mn"]) or ("페페로니" in m["mn"])
        # 🔴 치즈가 «주인» 인 메뉴는 치즈를 더 넣는다 (2026-07-27 사고).
        #    원래 데이터에 두 패턴이 있었다 — 치즈 피자류 `425 / 315.714 / 109.286`,
        #    나머지 `413.194 / 259.722 / 106.25`. 전부 260 으로 밀어서 그 구분을 날렸다.
        #    `치즈 피자`·`치즈 러버`·`리얼치즈` = 320g(315.714 정수화). `치즈후라이` 는 아니다 —
        #    거기서 치즈는 토핑 이름의 일부일 뿐이다.
        is_cheese = any(w in m["mn"] for w in ("치즈 피자", "치즈 러버", "리얼치즈"))
        lines = []
        for label, key in K.items():
            if label == "pepperoni" and not is_pep:
                continue
            r = cur.execute("SELECT amount FROM menu_ingredients WHERE menu_id=? AND ingredient_key=?",
                            (m["id"], key)).fetchone()
            if not r:
                continue
            old = r["amount"]
            new = 320.0 if (label == "cheese" and is_cheese) else STD_L[label]
            if is_L and abs(old - new) > 0.001:
                lines.append((label, key, old, new))
        drops = []
        for nm, key in (DROPK if a.drop_veg else []):
            r = cur.execute("SELECT amount FROM menu_ingredients WHERE menu_id=? AND ingredient_key=?",
                            (m["id"], key)).fetchone()
            if r:
                drops.append((nm, key, r["amount"]))
        # 남은 토핑의 소수점도 턴다. `47.222`·`88.542` 같은 값은 실측이 아니라
        # 비율 계산 잔재다 — 정수로 만들어야 화면·검수에서 실측처럼 읽히지 않는다.
        rounds = []
        for r in cur.execute("""SELECT mi.ingredient_key k, mi.amount, i.name nm
                                  FROM menu_ingredients mi
                                  JOIN ingredients i ON i.ingredient_key=mi.ingredient_key
                                 WHERE mi.menu_id=?""", (m["id"],)).fetchall():
            if r["k"] in K.values() or r["k"] in [k for _, k in DROPK]:
                continue
            if abs(r["amount"] - round(r["amount"])) > 0.001:
                rounds.append((r["nm"], r["k"], r["amount"], float(round(r["amount"]))))

        if not lines and not drops and not rounds:
            continue
        print(f"\n[{m['bn']}] {m['mn']}" + ("" if is_L else "   (L 아님 — 3종은 그대로 둔다)"))
        for label, key, old, new in lines:
            print(f"    {label:<12} {old:>10} → {new}")
            if a.apply:
                cur.execute("UPDATE menu_ingredients SET amount=? WHERE menu_id=? AND ingredient_key=?",
                            (new, m["id"], key))
                n_up += 1
        for nm, key, old, new in rounds:
            print(f"    {nm:<12} {old:>10} → {new:g}  (소수점 정리)")
            if a.apply:
                cur.execute("UPDATE menu_ingredients SET amount=? WHERE menu_id=? AND ingredient_key=?",
                            (new, m["id"], key))
                n_up += 1
        for nm, key, old in drops:
            print(f"    ✂ {nm} {old} 삭제 (피자 토핑 근거 없음) → mi_removed 보관")
            if a.apply:
                # 지우기 전에 되돌리기용으로 옮긴다 — bhc 맛초킹 야채 3종과 같은 방식
                cur.execute("""INSERT INTO mi_removed(menu_id,ingredient_key,amount,unit,
                                                     sort_order,composition,removed_at)
                               SELECT menu_id,ingredient_key,amount,unit,sort_order,composition,
                                      datetime('now')
                                 FROM menu_ingredients WHERE menu_id=? AND ingredient_key=?""",
                            (m["id"], key))
                cur.execute("DELETE FROM menu_ingredients WHERE menu_id=? AND ingredient_key=?",
                            (m["id"], key))
                n_del += 1

    if a.apply:
        c.commit()
        print(f"\n✅ 양 수정 {n_up}건 · 재료 삭제 {n_del}건")
        print("   이어서: python scripts/compute_line_costs.py")
    else:
        print("\n미적용 — 반영하려면 --apply")


if __name__ == "__main__":
    main()
