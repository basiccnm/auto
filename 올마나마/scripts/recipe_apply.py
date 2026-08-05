# -*- coding: utf-8 -*-
"""레시피 본문을 넣고 → 재료를 본문에서 뽑아 → DB에 매칭해 넣고 → 옛 재료는 지운다. 2026-08-03

## 왜 (대표 지시)
> *"레시피 우리 말투로 바꾸는 거 스크립트 만들고 저장해. 재료 뽑아서 우리 메뉴에 넣고
>   DB에서 매칭시키고, 그전에 재료에 있던 거랑 매칭 안 되는 건 삭제 처리 하면서
>   페이지 잘 닫으면 되잖아"*

**본문이 정본이다.** 재료 목록이 본문을 따라간다 — 반대로 하면
「간장치킨 본문엔 닭날개 600g인데 재료엔 생닭 1kg」 같은 어긋남이 생긴다(74개 중 71개가 그랬다).

## 하는 일 (한 번에)
```
① 본문(MD/JSON)을 읽는다
② 본문에서 «재료명 + 양 + 단위» 를 뽑는다        ← 정규식
③ 우리 재료로 매칭한다                          ← recipe_mapping.Matcher
④ dish_def_ingredient · dish_data 를 본문 기준으로 갈아끼운다
⑤ 본문에 없는 옛 재료는 지운다
⑥ 못 매칭된 재료를 보고한다                      ← 여기만 사람이 본다
```

⚠️ **재료는 두 곳에 있다.** DB(`dish_def_ingredient`)가 우선이고 `dish_data.py` 는 폴백이라,
   DB만 고치면 `gen_dishes.py` 가 리터럴로 되돌린다 → **둘 다** 고친다.

## 본문 형식 (`data/recipes_new/<slug>.txt`)
한 줄 = 한 단계. 재료는 `이름 양단위` 로 쓴다.
```
쌀 90g(종이컵 ½)을 씻어 밥을 짓고, 소금 2g·참기름 5ml를 섞어 한 김 식히세요
당근 20g은 채 썰어 기름 두른 팬에 1분 볶고, 시금치 30g은 끓는 물에 30초 데쳐 물기를 짜세요
```

    python scripts/recipe_apply.py --export              # 지금 본문 + 재료를 파일로 꺼낸다
    python scripts/recipe_apply.py                      # 뽑힌 재료 미리보기
    python scripts/recipe_apply.py --slug gimbap        # 하나만
    python scripts/recipe_apply.py --apply              # 반영
    python scripts/gen_dishes.py                        # 페이지 다시 만들기
    python scripts/preview_orphans.py                   # 남은 옛 페이지 닫기
"""
import io
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "recipes_new")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recipe_mapping import Matcher, normalize            # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# 「쌀 90g」 「소갈비(수입) 300g」 「닭날개·봉(원물) 250g」 「계란 1개」
#
# 🔴 **이름은 DB 목록으로 찾는다.** 「이름처럼 생긴 것」을 정규식으로 훑으면
#    「팬에 담고 물 200ml」 에서 이름이 **「팬에 담고 물」** 로 잡히고,
#    괄호·가운뎃점이 든 진짜 이름(`소갈비(수입)`)은 반대로 못 잡는다.
#    → **본문은 사람이 읽는 글이다.** 이름을 억지로 붙여 쓰게 만들지 않는다.
# ⚠️ **끝에 `\b` 를 쓰지 마라.** 「5ml를」·「20g은」처럼 뒤에 한글이 붙으면
#    `l`↔`를` 둘 다 단어문자라 경계가 안 서서 **통째로 안 잡힌다**(김밥 8종 중 6종을 놓쳤다).
UNIT = r"(?:g|ml|kg|L|개|장|모|대|쪽|줌|마리|알|봉|팩|캔|조각|큰술|작은술|컵|세트)"
AMT = r"(\d+(?:\.\d+)?|[½¼¾])\s*(" + UNIT + r")(?![A-Za-z0-9])"
# 목록에 없는 이름도 잡아서 **미매칭으로 보고**한다(모르는 채 지나가지 않게)
ING_ANY = re.compile(r"(?<![가-힣])([가-힣A-Za-z][가-힣A-Za-z0-9]{0,13})\s*" + AMT)
FRAC = {"½": 0.5, "¼": 0.25, "¾": 0.75}
# 재료가 아닌 말 — 도구·불세기. ⚠️ **물은 여기 넣지 않는다** — `water`(0원)로 매칭돼
#    재료 목록에 「물 550ml」로 그대로 보여야 한다. 원가에는 0원으로 들어간다
NOT_ING = re.compile(r"^(불|중불|센불|약불|기름|팬|냄비|접시|그릇"
                     r"|한|약|총|각|양면|앞뒤|남짓|정도)$")


def name_rx(conn):
    """DB 의 재료명·화면이름·별칭으로 «이 이름들만» 찾는 정규식을 만든다."""
    names = set()
    for sql in ("SELECT name FROM ingredients",
                "SELECT display_name FROM ingredients WHERE display_name<>''",
                "SELECT alias_raw FROM ingredient_alias WHERE alias_raw<>''"):
        for (v,) in conn.execute(sql):
            v = (v or "").strip()
            if len(v) >= 1:
                names.add(v)
    # 긴 이름부터 — 「무」가 「무뼈닭발」을 가로채지 않게
    alt = "|".join(re.escape(v) for v in sorted(names, key=len, reverse=True))
    return re.compile(r"(?<![가-힣])(" + alt + r")\s*" + AMT)


def _norm_amt(amt, unit):
    v = FRAC.get(amt)
    if v is None:
        v = float(amt)
    if unit == "kg":
        v, unit = v * 1000, "g"
    elif unit == "L":
        v, unit = v * 1000, "ml"
    return v, unit


def parse(text, rx=None):
    """본문에서 (재료명, 양, 단위) 를 뽑는다. 같은 재료가 여러 단계면 합산."""
    out, order, spans = {}, [], []

    def add(nm, amt, unit):
        nm = nm.strip(" ·,")
        if not nm or NOT_ING.match(nm):            # 「쌀」·「김」처럼 한 글자도 재료다
            return
        v, unit = _norm_amt(amt, unit)
        k = (nm, unit)
        if k in out:
            out[k] += v
        else:
            out[k] = v
            order.append(k)

    if rx is not None:                             # ① DB 에 있는 이름 먼저
        for mm in rx.finditer(text):
            spans.append(mm.span())
            add(mm.group(1), mm.group(2), mm.group(3))
    for mm in ING_ANY.finditer(text):              # ② 나머지 — 미매칭으로 보고된다
        if any(s <= mm.start() < e or s < mm.end() <= e for s, e in spans):
            continue
        add(mm.group(1), mm.group(2), mm.group(3))
    return [(nm, out[(nm, u)], u) for nm, u in order]


def main():
    apply = "--apply" in sys.argv
    only = next((sys.argv[i + 1] for i, a in enumerate(sys.argv)
                 if a == "--slug" and i + 1 < len(sys.argv)), None)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    m = Matcher()

    os.makedirs(SRC, exist_ok=True)

    if "--export" in sys.argv:
        # 지금 본문을 파일로 꺼낸다. **이 파일을 우리 말투로 고쳐 쓰고** --apply 한다
        out = os.path.join(BASE, "reports", "레시피-다시쓰기-원본.md")
        with io.open(out, "w", encoding="utf-8") as f:
            f.write("# 레시피 다시 쓰기 — 지금 본문과 재료\n\n")
            f.write("본문을 고쳐 `data/recipes_new/<slug>.txt` 에 넣고 "
                    "`python scripts/recipe_apply.py --apply` 한다.\n\n")
            f.write("규칙 — 한 줄 = 한 단계 · **모든 재료에 이름+양을 적는다** · "
                    "이름은 **띄어쓰기 없이** · 물은 안 적는다.\n\n")
            for d in c.execute("SELECT id, name, slug, recipe_steps rs FROM dishes ORDER BY name"):
                f.write("## %s `%s`\n\n" % (d["name"], d["slug"]))
                f.write("**지금 재료**\n\n")
                for x in c.execute("""SELECT COALESCE(i.display_name,i.name) dn, di.amount a, di.unit u
                                      FROM dish_ingredients di
                                      JOIN ingredients i ON i.ingredient_key=di.ingredient_key
                                      WHERE di.dish_id=? ORDER BY di.sort_order""", (d["id"],)):
                    f.write("- %s %s%s\n" % (x["dn"], x["a"], x["u"] or ""))
                f.write("\n**지금 본문**\n\n```\n%s\n```\n\n" % (d["rs"] or "(없음)"))
        print("→ %s" % out)
        return

    files = sorted(f for f in os.listdir(SRC) if f.endswith(".txt"))
    if only:
        files = [f for f in files if f[:-4] == only]
    if not files:
        print("data/recipes_new/ 에 본문이 없다.")
        return

    RX = name_rx(c)
    print("본문 %d개%s" % (len(files), "" if apply else "  (미리보기 — 반영하려면 --apply)"))
    print()
    unmatched = []
    for f in files:
        slug = f[:-4]
        text = io.open(os.path.join(SRC, f), encoding="utf-8").read().strip()
        d = c.execute("SELECT id, name FROM dishes WHERE slug=?", (slug,)).fetchone()
        if not d:
            print("  ✗ %-16s dishes 에 없는 slug" % slug)
            continue

        # 🔴 **그 요리가 쓰던 키를 먼저 본다.** `치킨파우더` 는 화면 이름이 같아도
        #    브랜드마다 다른 재료다(`breading_kyochon`·`breading_bhc`…). 전체 매칭에 맡기면
        #    다섯 브랜드가 **같은 파우더**를 쓰게 되어 원가가 같아진다(07-27 사고 재발).
        mine = {}
        for x in c.execute("""SELECT di.ingredient_key k, COALESCE(i.display_name,i.name) dn
                              FROM dish_ingredients di
                              JOIN ingredients i ON i.ingredient_key=di.ingredient_key
                              WHERE di.dish_id=?""", (d["id"],)):
            mine.setdefault(re.sub(r"[^가-힣A-Za-z0-9]", "", x["dn"]), x["k"])

        got = parse(text, RX)
        rows, miss = [], []
        for nm, amt, unit in got:
            key = mine.get(re.sub(r"[^가-힣A-Za-z0-9]", "", nm))
            if not key:
                key = m.match(nm)["key"]
            if not key:
                miss.append(nm); unmatched.append((d["name"], nm)); continue
            rows.append((key, amt, unit, nm))

        old = [x["ingredient_key"] for x in
               c.execute("SELECT ingredient_key FROM dish_def_ingredient WHERE slug=?", (slug,))]
        new = [x[0] for x in rows]
        drop = [k for k in old if k not in new]

        print("  %-16s 본문 %d단계 · 재료 %d종 · 새로 %d · 뺄 것 %d %s"
              % (d["name"], len([l for l in text.splitlines() if l.strip()]),
                 len(got), len(new), len(drop),
                 ("· ⛔미매칭 " + " · ".join(miss)) if miss else ""))

        if not apply:
            continue
        # 🔴 **`dish_def` 에 행이 없으면 `dish_data.py` 리터럴이 이긴다** — `gen_dishes.py:152`
        #    가 «DB 에 있으면 DB, 없으면 리터럴» 로 고르기 때문이다. 재료만 갈아끼우고
        #    `dish_def` 를 안 만들면 페이지 생성 때 **조용히 옛 재료로 되돌아간다**
        #    (2026-08-03: 간장치킨에 소스 7종을 넣었는데 3종으로 되돌아갔다).
        if not c.execute("SELECT 1 FROM dish_def WHERE slug=?", (slug,)).fetchone():
            from dish_data import DISHES as _LIT, ICON as _IC, DISH_CAT as _CAT
            lit = next((x for x in _LIT if x[1] == slug), None)
            cat = next((k for k, v in _CAT.items() if d["name"] in v), None)
            c.execute("""INSERT INTO dish_def(slug,name,serving,match_pattern,category,icon,
                            sort_order,source,active,created_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,'recipe_apply',1,datetime('now'),datetime('now'))""",
                      (slug, d["name"], (lit[2] if lit else "1인분"),
                       (lit[3] if lit else None), cat, _IC.get(d["name"]),
                       (c.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM dish_def")
                        .fetchone()[0])))
            print("     ↑ dish_def 에 없어서 새로 등록했다(리터럴이 이기지 않게)")

        # ④⑤ 본문 기준으로 갈아끼운다
        c.execute("UPDATE dishes SET recipe_steps=? WHERE id=?", (text, d["id"]))
        c.execute("DELETE FROM dish_def_ingredient WHERE slug=?", (slug,))
        c.execute("DELETE FROM dish_ingredients WHERE dish_id=?", (d["id"],))
        for i, (k, amt, unit, _raw) in enumerate(rows):
            c.execute("""INSERT INTO dish_def_ingredient(slug,ingredient_key,amount,unit,sort_order,grp)
                         VALUES(?,?,?,?,?,'')""", (slug, k, amt, unit, i))
            c.execute("""INSERT INTO dish_ingredients(dish_id,ingredient_key,amount,unit,sort_order)
                         VALUES(?,?,?,?,?)""", (d["id"], k, amt, unit, i))

    if apply:
        c.commit()
        print()
        print("✅ 반영 완료. 이어서 페이지를 다시 만든다:")
        print("   python scripts/gen_dishes.py")
        print()
        print("⚠️ `dish_data.py` 리터럴은 **`dish_def` 에 행이 없을 때만** 이긴다.")
        print("   위에서 없는 것은 등록했으니 이제 DB 가 정본이다.")
    if unmatched:
        print()
        print("🔴 매칭 안 된 재료 %d건 — **이것만 사람이 본다**" % len(unmatched))
        for dish, nm in unmatched:
            print("   %-16s %s" % (dish, nm))
        print()
        print("   → `python scripts/ingredient_new.py \"<재료명>\"` 로 판정한다")


if __name__ == "__main__":
    main()
