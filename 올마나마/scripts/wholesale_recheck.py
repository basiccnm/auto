# -*- coding: utf-8 -*-
"""도매가를 새 기준으로 다시 잡는다 — **단위당 단가 최저 · 용량 조건 없음 · 배송비 없음**. 2026-07-26

대표가 확정한 도매 기준
  · 매장은 한 주문에 10만원 이상 담아 사니 **배송비가 없다.** 1kg 단품을 배제할 이유가 없다
  · **"대용량"은 조건이 아니다.** 단가가 싸서 결과적으로 대용량이 잡히는 것일 뿐이다
    (70~80%는 대용량이 싸지만, 소용량을 묶어 파는 상품이 더 싼 경우도 있다)
  · 단가의 단위는 재료마다 다르다 — kg / L / 개 / 장 / 세트
  내가 "5kg 이상만" 걸러 고른 게 틀렸다. 봉어묵이 그래서 1kg 3,050원 대신 2.5kg 4,360원이 됐다.

🔴 이름으로 새로 매칭하지 않는다 (세 번 실패했다)
  재료명으로 식봄을 검색하면 양배추→적채, 모차렐라 치즈→치즈떡, 분말→콩국수용분말이 잡힌다.
  그래서 **지금 확정된 상품이 속한 카테고리 안에서만** 후보를 찾는다.
  카테고리가 품목을 묶어주니 다른 물건이 들어올 수 없다.

    python scripts/wholesale_recheck.py            # 보고만
    python scripts/wholesale_recheck.py --apply    # 더 싼 것으로 갱신
"""
import glob
import io
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SB = os.path.join(BASE, "data", "research", "foodspring")
OUT = os.path.join(BASE, "data", "research", "wholesale_recheck.json")


def norm(s):
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", s or "")


def load_sikbom():
    """카테고리 → 상품목록. 상품에 자기 카테고리를 심어 둔다."""
    cats = {}
    for fp in glob.glob(os.path.join(SB, "*.json")):
        try:
            d = json.load(io.open(fp, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        for cat, v in d.items():
            items = []

            def walk(o):
                if isinstance(o, dict):
                    if "name" in o and "won_per_kg" in o:
                        items.append(o)
                    else:
                        for x in o.values():
                            walk(x)
                elif isinstance(o, list):
                    for x in o:
                        walk(x)
            walk(v)
            if items:
                cats.setdefault(cat, []).extend(items)
    return cats


def main():
    apply = "--apply" in sys.argv
    cats = load_sikbom()
    byname = {}
    for cat, items in cats.items():
        for o in items:
            byname.setdefault(norm(o["name"]), []).append((cat, o))
    print("식봄 카테고리 %d개 · 상품 %d건" % (cats and len(cats) or 0, sum(len(v) for v in cats.values())))

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [r for r in c.execute("""
        SELECT i.ingredient_key k, i.name, i.base_unit bu, i.wholesale_price wp, i.wholesale_basis wb,
               (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=i.ingredient_key) uses
        FROM ingredients i
        WHERE (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=i.ingredient_key) > 0
          AND i.wholesale_basis LIKE '%식봄%'
        ORDER BY uses DESC""")]
    print("식봄 근거로 잡힌 재료 %d종이 대상" % len(rows))
    print()

    # 근거 문장에서 **채택한 상품명**을 뽑는다. 그 상품이 있는 카테고리가 곧 후보 범위다.
    changed, same, nofind = [], 0, []
    for r in rows:
        wb = r["wb"] or ""
        # 식봄 근거는 "… 2026-07-26 <상품명> = 12,345원/kg" 꼴이다
        m = re.search(r"\d{4}-\d{2}-\d{2}\s*(.+?)\s*=\s*[\d,]+\s*원", wb)
        cand_name = m.group(1).strip() if m else None
        pool, cat_used = [], None
        if cand_name:
            key = norm(cand_name)
            hit = byname.get(key)
            if not hit:      # 상품명이 조금 달라졌을 수 있다 → 앞 12자로 찾는다
                for nk, v in byname.items():
                    if key[:12] and key[:12] in nk:
                        hit = v
                        break
            if hit:
                cat_used = hit[0][0]
                pool = [o for o in cats.get(cat_used, [])
                        if o.get("won_per_kg") and not o.get("suspect")]
        if not pool:
            nofind.append(r["name"])
            continue
        # 같은 카테고리 안에서도 품목이 섞여 있다 → 확정 상품명과 **핵심 토큰**을 공유해야 한다
        base_toks = {t for t in re.split(r"[\s_\-\(\)\[\],/]+", cand_name or "") if len(t) >= 2}
        best = None
        for o in pool:
            on = norm(o["name"])
            if not any(norm(t) and norm(t) in on for t in base_toks):
                continue
            if best is None or o["won_per_kg"] < best["won_per_kg"]:
                best = o
        if not best:
            nofind.append(r["name"])
            continue
        cur = round(r["wp"] or 0)
        new = round(best["won_per_kg"])
        if new < cur * 0.98:
            changed.append({"key": r["k"], "name": r["name"], "uses": r["uses"], "unit": r["bu"],
                            "old": cur, "new": new, "cat": cat_used,
                            "old_product": cand_name, "new_product": best["name"],
                            "pack_kg": best.get("pack_kg"), "sale_price": best.get("sale_price")})
        else:
            same += 1

    changed.sort(key=lambda x: -x["uses"])
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"changed": changed, "nofind": nofind}, ensure_ascii=False, indent=1))
    print("더 싼 게 있는 재료 %d종 · 지금이 이미 최저 %d종 · 후보 못 찾음 %d종"
          % (len(changed), same, len(nofind)))
    print()
    print("%-20s %4s %9s %9s %6s  %s" % ("재료", "메뉴", "지금", "더 싼 것", "차이", "상품"))
    print("-" * 112)
    for x in changed[:30]:
        print("%-20s %3d개 %8s원 %8s원 %5.0f%%  %s" % (
            x["name"][:20], x["uses"], format(x["old"], ","), format(x["new"], ","),
            (x["new"] / x["old"] - 1) * 100 if x["old"] else 0, x["new_product"][:40]))
    print("-" * 112)
    if nofind:
        print("후보를 못 찾은 재료 %d종 (근거에서 상품명 추출 실패): %s"
              % (len(nofind), " · ".join(nofind[:12])))

    if apply:
        cur = c.cursor()
        for x in changed:
            basis = ("식봄 %s 2026-07-26 %s = %s원/%s. "
                     "🔴 기준 변경: **용량 조건 없이 단위당 단가 최저**로 다시 골랐다(대표 확정 2026-07-26). "
                     "매장은 한 주문에 10만원 이상 담아 사니 배송비가 없어 1kg 단품을 배제할 이유가 없다. "
                     "이전 값 %s원/%s(%s)은 내가 '대용량 5kg 이상'만 후보로 놓고 고른 것이다."
                     % (x["cat"], x["new_product"], format(x["new"], ","), x["unit"],
                        format(x["old"], ","), x["unit"], x["old_product"]))
            cur.execute("UPDATE ingredients SET wholesale_price=?, wholesale_basis=?, updated_at=?"
                        " WHERE ingredient_key=?", (x["new"], basis, "2026-07-26", x["key"]))
        c.commit()
        print()
        print("✅ %d종 갱신" % len(changed))
    else:
        print()
        print("DB 미반영. 반영은 --apply")
    c.close()


if __name__ == "__main__":
    main()
