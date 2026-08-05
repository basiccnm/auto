# -*- coding: utf-8 -*-
"""소매 상품의 **용량**을 채우고, 없는 재료는 가정용 상품을 찾는다. 2026-07-27

🔴 왜 필요한가 (2026-07-27 발견)
   `compute_line_costs` 가 드디어 `ingredient_retail` 을 읽게 됐는데, **pack_g 가 없으면 못 쓴다.**
   요리 74종에 쓰이는 재료 138종 중
     · 소매 상품은 있는데 **용량이 없는 것 47종** (식용유 15개 요리 · 대파 12 · 쌀 11 …)
     · 소매 상품이 **아예 없는 것 54종** (고추장 10개 요리 · 설탕 8 · 고춧가루 8 …)
   용량이 없으면 옛 `manual_price` 로 조용히 폴백해서, 쿠팡 상품을 바꿔도 원가가 안 바뀐다.

방법
   ① 쿠팡 상품명에 용량이 있으면 그걸 쓴다
   ② 없으면 **검색어에 용량을 붙여** 다시 찾는다 ("식용유 900ml", "고추장 500g")
      — 쿠팡 API 는 용량 필드를 안 준다. 상품명에 적힌 것만 알 수 있다.
   ③ 그래도 없으면 **비워둔다.** 표준 규격을 추측해 넣지 않는다(`ingredients-evidence-only`)

⛔ 업소용 대용량은 소매로 쓰지 않는다 — 가정용은 **총 지출 최저**가 기준이다.
   5kg·10kg·18L 이 붙은 상품은 후보에서 뺀다.

    python scripts/retail_packfill.py --dry          # 찾기만
    python scripts/retail_packfill.py --apply
"""
import io
import json
import os
import re
import sqlite3
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "research", "retail_packfill.json")
SLEEP = 2.0

sys.path.insert(0, os.path.join(BASE, "scripts"))
import coupang_ingredient as CI      # noqa: E402
import retail_fill as RF             # noqa: E402
from mealkit_run import load_env     # noqa: E402

# 상품명에서 용량 읽기
RX_V = re.compile(r"(\d[\d,.]*)\s*(kg|g|l|ml)\b", re.I)
# 업소용 대용량 — 가정용 소매에서 뺀다
RX_BULK = re.compile(r"(\d[\d,.]*)\s*(kg|l)\b", re.I)
# 가정용으로 흔한 규격 — 검색어에 붙여 쓴다
SIZES = {
    "L": ["900ml", "1L", "500ml", "1.8L"],
    "kg": ["500g", "1kg", "300g", "200g", "800g"],
    "개": ["", "1개"],
}


def pack_from_name(nm):
    """상품명의 용량을 g/ml 로. 못 읽으면 None."""
    m = RX_V.search(nm or "")
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    u = m.group(2).lower()
    return v * 1000 if u in ("kg", "l") else v


def too_big(nm):
    """업소용 대용량인가 (2kg·2L 이상)."""
    for a, b in RX_BULK.findall(nm or ""):
        try:
            if float(a.replace(",", "")) >= 2:
                return True
        except ValueError:
            pass
    return False


def keywords(name, base_unit):
    """검색어 — 재료명에서 브랜드·용량을 떼고, 가정용 규격을 붙인다."""
    s = re.sub(r"\([^)]*\)", " ", name or "")
    s = re.sub(r"\d+(\.\d+)?\s*(kg|g|l|ml|호|개입|개|매|장|봉|팩)", " ", s, flags=re.I)
    s = re.sub(r"[·/]", " ", s)
    core = " ".join(t for t in s.split() if len(t) >= 2) or (name or "")
    sizes = SIZES.get((base_unit or "").strip(), SIZES["kg"])
    out = [core]
    out += ["%s %s" % (core, z) for z in sizes if z]
    return list(dict.fromkeys(out))[:5]


def pick(items, rej, need_g=None):
    """가정용 후보를 고른다.

    🔴 고르는 순서 (대표 확정 2026-07-27 · `retail-pick-rules`)
       ① 물건이 맞나 — 여기서 막히면 아무리 싸도 안 쓴다(JUNK·is_food 로 1차, 판정은 사람)
       ② **필요량을 덮는 최소 규격** — 고추장 30g 쓰는데 500g 은 되고 3kg 는 안 된다
       ③ 그 안에서 **총 지출 최저**
    ⛔ 단가(원/kg)로 정렬하면 안 된다. 소매는 **실제 낼 돈**이 기준이다.
       전에 단가순·용량순으로 정렬해서 업소용 10kg 가 올라왔다.
    """
    cands = []
    for p in items:
        nm, pr, pid = p.get("productName") or "", p.get("productPrice"), p.get("productId")
        if not pr or not p.get("isRocket") or pid in rej:
            continue
        if not RF.is_food(p) or RF.JUNK.search(nm):
            continue
        if too_big(nm):
            continue
        g = pack_from_name(nm)
        cands.append({"pid": pid, "name": nm, "price": pr, "pack_g": g,
                      "image": p.get("productImage"), "url": p.get("productUrl")})

    def key(x):
        g = x["pack_g"]
        if not g:
            return (3, x["price"])                 # 용량 모르면 뒤로
        if need_g and g < need_g:
            return (2, x["price"])                 # 필요량을 못 덮으면 뒤로
        # 필요량을 덮는 것 중 **남는 양이 적은 것** → 같으면 총 지출 최저
        waste = (g - need_g) if need_g else g
        return (1, waste, x["price"])
    cands.sort(key=key)
    return cands


def main():
    apply = "--apply" in sys.argv
    lim = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--budget=")), 400)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY"), env.get("COUPANG_SECRET_KEY")

    rej = {}
    for r in c.execute("SELECT ingredient_key, product_id FROM retail_rejected"):
        rej.setdefault(r[0], set()).add(r[1])

    # 요리에 쓰이는 재료 중 ①용량 없음 ②소매 없음
    # 메뉴와 요리 양쪽에서 쓰이는 재료 전부. `need_g` = 한 번에 쓰는 최대량(그 양을 덮는 규격이 필요하다)
    rows = [dict(r) for r in c.execute("""
        SELECT i.ingredient_key k, i.name, i.base_unit bu,
               x.name pn, x.price pp, x.pack_g pg, x.status st,
               (SELECT COUNT(*) FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
                  JOIN brands b ON b.id=m.brand_id
                WHERE mi.ingredient_key=i.ingredient_key AND b.published=1) nm,
               (SELECT COUNT(*) FROM dish_ingredients d WHERE d.ingredient_key=i.ingredient_key) nd,
               (SELECT MAX(amount) FROM dish_ingredients d WHERE d.ingredient_key=i.ingredient_key
                  AND d.unit IN ('g','ml')) need_d,
               (SELECT MAX(amount) FROM menu_ingredients mi WHERE mi.ingredient_key=i.ingredient_key
                  AND mi.unit IN ('g','ml')) need_m
        FROM ingredients i LEFT JOIN ingredient_retail x ON x.ingredient_key=i.ingredient_key
        WHERE COALESCE(x.status,'') NOT IN ('store','none')
          AND (x.pack_g IS NULL OR x.price IS NULL)
          AND ((SELECT COUNT(*) FROM menu_ingredients mi JOIN menus m ON m.id=mi.menu_id
                  JOIN brands b ON b.id=m.brand_id
                WHERE mi.ingredient_key=i.ingredient_key AND b.published=1) > 0
            OR (SELECT COUNT(*) FROM dish_ingredients d WHERE d.ingredient_key=i.ingredient_key) > 0)
        ORDER BY (nm + nd) DESC""")]
    for r in rows:
        r["need_g"] = max([v for v in (r.get("need_d"), r.get("need_m")) if v] or [0]) or None
    print("대상 %d종 (용량 없음 또는 소매 없음) · API 예산 %d회" % (len(rows), lim), flush=True)
    print("", flush=True)

    used, done, fail = 0, [], []
    for r in rows:
        if used >= lim:
            print("예산 소진 — 중단", flush=True)
            break
        best = None
        for kw in keywords(r["name"], r["bu"]):
            if used >= lim:
                break
            try:
                d = CI.api_search(kw, ak, sk)
            except Exception as e:
                used += 1
                time.sleep(SLEEP)
                continue
            used += 1
            if d.get("rCode") not in (0, "0"):
                print("!! 쿠팡 한도 — 중단", flush=True)
                rows = []
                break
            cands = pick((d.get("data") or {}).get("productData") or [], rej.get(r["k"], set()),
                         r.get("need_g"))
            time.sleep(SLEEP)
            withpack = [x for x in cands if x["pack_g"]]
            if withpack:
                best = dict(withpack[0], kw=kw)
                break
            if cands and not best:
                best = dict(cands[0], kw=kw)     # 용량 없어도 후보는 잡아둔다
        if not best:
            fail.append(r)
            print("   ✗ %-24s 메뉴%2d 요리%2d 후보 없음" % (r["name"][:24], r["nm"], r["nd"]), flush=True)
            continue
        done.append({"k": r["k"], "name": r["name"], "nd": r["nd"],
                     "need_g": r.get("need_g"), "nm": r["nm"],
                     "old": {"name": r["pn"], "price": r["pp"], "pack_g": r["pg"]},
                     "new": best})
        need = r.get("need_g")
        print("   %s %-24s 메뉴%2d 요리%2d 필요%6s → %8s원 %8s  %s" % (
            "✅" if best["pack_g"] else "△", r["name"][:24], r["nm"], r["nd"],
            ("%gg" % need) if need else "-",
            format(best["price"], ","),
            ("%.0fg" % best["pack_g"]) if best["pack_g"] else "용량?",
            best["name"][:34]), flush=True)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"done": done, "fail": [{"k": r["k"], "name": r["name"], "nd": r["nd"]} for r in fail]},
        ensure_ascii=False, indent=1))

    if apply:
        cur = c.cursor()
        n = 0
        for d in done:
            b = d["new"]
            if not b["pack_g"]:
                continue          # 용량 없는 건 넣지 않는다 — 원가 계산이 안 된다
            cur.execute("""INSERT OR REPLACE INTO ingredient_retail
                (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
                VALUES(?,?,?,?,?,1,?,?, 'pending', NULL)""",
                        (d["k"], b["pid"], b["name"], b["price"], b["pack_g"], b["image"], b["url"]))
            n += 1
        c.commit()
        print("", flush=True)
        print("✅ 용량 있는 %d종 반영(검수 대기) · 용량 없는 %d종은 넣지 않았다" % (
            n, sum(1 for d in done if not d["new"]["pack_g"])), flush=True)
    else:
        print("", flush=True)
        print("DB 미반영. 반영은 --apply", flush=True)
    print("찾음 %d · 실패 %d · API %d회 → %s" % (len(done), len(fail), used, OUT), flush=True)


if __name__ == "__main__":
    main()
