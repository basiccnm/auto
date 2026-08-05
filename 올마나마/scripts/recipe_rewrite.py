# -*- coding: utf-8 -*-
"""레시피 본문을 **재료 목록과 맞춘다.** 2026-08-03

## 왜
본문과 재료 목록이 서로 다른 재료를 말하고 있다(74개 중 **71개**).
```
간장치킨  본문: 닭 날개·봉 600g · 감자전분 80g
          재료: 생닭 1kg · 튀김가루 200g · 식용유 300ml     ← 완전히 다르다
```
재료 목록은 **사서 담는 것**이고 본문은 **만드는 것**인데, 둘이 다르면
「이 값이 어디서 나왔냐」는 말을 듣는다. 원가는 재료 목록으로 계산되니
**본문이 재료 목록을 따라야** 한다.

## 규칙 (`.claude/skills/recipe-rewrite/`)
1. **각 단계에 재료명 + 양을 다 적는다** — 위 목록으로 올라갈 일이 없어야 한다
2. 계량은 `reports/계량환산표-2026-08-02.md` — 같은 1큰술도 재료마다 4배 차이
3. 같은 재료가 두 단계에 걸치면 **양을 나눠 적는다**
4. ⛔ 「밥숟가락」 금지 — 규격이 없다
5. 화면 이름(`display_name`)을 쓴다 — 상표·용량 금지

    python scripts/recipe_rewrite.py                 # 어긋난 것 진단
    python scripts/recipe_rewrite.py --dish 김밥      # 한 요리 자세히
    python scripts/recipe_rewrite.py --md            # 다시 쓸 목록을 MD로
"""
import io
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
sys.stdout.reconfigure(encoding="utf-8")

# 계량환산 — 같은 1큰술도 재료마다 무게가 다르다(reports/계량환산표-2026-08-02.md)
TBSP = {"고추장": 30, "된장": 30, "다진마늘": 30, "물엿": 30, "쌈장": 30,
        "소금": 18, "꽃소금": 18, "맛소금": 18,
        "물": 15, "간장": 15, "진간장": 15, "국간장": 15, "식초": 15,
        "맛술": 15, "청주": 15, "참기름": 15, "들기름": 15, "식용유": 15,
        "설탕": 12, "황설탕": 12, "흑설탕": 12,
        "밀가루중력분": 8, "밀가루강력분": 8, "밀가루박력분": 8, "튀김가루": 8, "부침가루": 8,
        "옥수수전분": 7.5, "감자전분": 7.5, "고구마전분": 7.5,
        "고춧가루": 7}
AMT = re.compile(r"\d+\s*(g|ml|개|장|큰술|작은술|컵|모|대|쪽|줌|마리|알|봉|팩|캔|조각)")


def hint(name, amount, unit):
    """양에 가늠할 거리를 붙인다 — 「감자전분 80g(종이컵 ½)」."""
    if unit not in ("g", "ml") or not amount:
        return ""
    t = TBSP.get(name)
    if t and amount <= t * 6:                     # 6큰술 이하면 큰술로
        n = amount / t
        if n >= 0.9:
            return "(약 %s큰술)" % (int(n) if abs(n - round(n)) < .2 else round(n, 1))
        if n >= 0.4:
            return "(½큰술)"
    if amount >= 90:                              # 종이컵 180ml 기준
        cup = amount / 180
        if cup >= 0.45:
            lab = {0.5: "½", 1.0: "1", 1.5: "1½", 2.0: "2"}.get(round(cup * 2) / 2)
            if lab:
                return "(종이컵 %s)" % lab
    return ""


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    only = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--dish=")), None)
    if "--dish" in sys.argv:
        i = sys.argv.index("--dish")
        if i + 1 < len(sys.argv):
            only = sys.argv[i + 1]

    dishes = c.execute("SELECT id, name, recipe_steps rs FROM dishes ORDER BY name").fetchall()
    if only:
        dishes = [d for d in dishes if only in d["name"]]

    bad, nolines = [], []
    for d in dishes:
        ings = [dict(r) for r in c.execute("""
            SELECT i.display_name dn, di.amount, di.unit
            FROM dish_ingredients di JOIN ingredients i ON i.ingredient_key=di.ingredient_key
            WHERE di.dish_id=? ORDER BY di.sort_order""", (d["id"],))]
        rs = d["rs"] or ""
        miss = [x["dn"] for x in ings if x["dn"] and x["dn"] not in rs]
        lines = [l for l in rs.splitlines() if l.strip()]
        noamt = [l for l in lines if not AMT.search(l)]
        if miss or noamt:
            bad.append((d, ings, miss, len(noamt), len(lines)))
        if not lines:
            nolines.append(d["name"])

        if only:
            print("■ %s" % d["name"])
            print()
            print("  [재료 목록 — 원가는 이걸로 계산된다]")
            for x in ings:
                h = hint(x["dn"], x["amount"], x["unit"])
                print("     %-16s %s%s %s" % (x["dn"], x["amount"], x["unit"] or "", h))
            print()
            print("  [지금 본문]")
            for l in lines:
                print("     %s %s" % ("  " if AMT.search(l) else "⚠️", l))
            if miss:
                print()
                print("  ⛔ 본문에 안 나오는 재료: %s" % " · ".join(miss))
            return

    print("요리 %d개 · 손봐야 할 것 %d개" % (len(dishes), len(bad)))
    print("   본문에 재료가 빠짐 / 양이 없는 단계가 있음")
    print()
    for d, ings, miss, noamt, nl in bad[:30]:
        print("  %-16s 재료 %2d개 · 양 없는 단계 %d/%d %s"
              % (d["name"], len(ings), noamt, nl,
                 ("· 빠진 재료 " + " · ".join(miss[:4])) if miss else ""))

    if "--md" in sys.argv:
        p = os.path.join(BASE, "reports", "레시피-다시쓰기-2026-08-03.md")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write("# 레시피 다시 쓰기 — 재료 목록에 맞춘다\n\n")
            f.write("본문과 재료 목록이 다른 요리 **%d개**. 규칙은 `.claude/skills/recipe-rewrite/`.\n\n" % len(bad))
            for d, ings, miss, noamt, nl in bad:
                f.write("## %s\n\n" % d["name"])
                f.write("**재료(원가 기준)**\n\n")
                for x in ings:
                    f.write("- %s %s%s %s\n" % (x["dn"], x["amount"], x["unit"] or "",
                                                hint(x["dn"], x["amount"], x["unit"])))
                f.write("\n**지금 본문**\n\n")
                for l in (d["rs"] or "").splitlines():
                    if l.strip():
                        f.write("%s %s\n" % ("-" if AMT.search(l) else "- ⚠️", l))
                if miss:
                    f.write("\n⛔ 본문에 없는 재료: %s\n" % " · ".join(miss))
                f.write("\n")
        print()
        print("→ %s" % p)


if __name__ == "__main__":
    main()
