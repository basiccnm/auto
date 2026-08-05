# -*- coding: utf-8 -*-
"""요리(dish) 하나의 **재료·양·조리법**을 만개의레시피 조사값으로 교체한다. 2026-08-01 신설

    python scripts/dish_recipe_apply.py <recipe.json>          # 미리보기(매핑 확인)
    python scripts/dish_recipe_apply.py <recipe.json> --apply  # DB 반영

recipe.json (요리 하나) — 만개의레시피에서 확인해 채운다:
    {
      "slug": "jjajangmyeon",            # dish_def.slug (없으면 name 으로 찾음)
      "name": "짜장면",
      "serving": "1인분",                # 바뀌면 갱신, 없으면 유지
      "source": "https://www.10000recipe.com/recipe/XXXX",
      "ingredients": [
        {"name": "중화면", "amount": 200, "unit": "g"},
        {"name": "돼지고기 다짐육", "amount": 80, "unit": "g"},
        {"key": "cg_soy_sauce_jin", "amount": 15, "unit": "ml"}   # key 직접 지정도 가능
      ],
      "recipe": ["문장1", "문장2", "문장3", "문장4"]              # 우리 말투로
    }

매핑 규칙
  · `key` 가 있으면 그대로 쓴다. `name` 만 있으면 우리 `ingredients` 에서 찾는다
    (정확일치 → 동의어(SYN) → 부분일치). **못 찾으면 넣지 않고 목록으로 보여준다.**
  · ⛔ 지어내지 않는다 — 못 찾은 재료는 사용자가 확인해 등록하거나 다른 재료로 바꾼다.
  · 양 단위는 g 이 기본(무게·부피). 개·장·마리 등은 그대로.

반영
  · `dish_def_ingredient` 를 통째로 교체(그 slug 만 DELETE 후 INSERT).
  · `dishes.recipe_steps` 를 갱신(줄바꿈으로 이은 문장).
  · 원가는 등록 세션이 `compute_line_costs.py` 로 재계산한다(여기선 안 만짐).
⛔ 브랜드 시그니처(뿌링클·황금올리브·허니콤보 등)는 대상이 아니다 — 이미 검수됐다(대표 지시).
"""
import io
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")

# 이름이 조금 달라도 같은 재료 — 만개의레시피 표기 → 우리 재료
SYN = {
    "닭": "생닭", "생닭": "생닭", "닭고기": "생닭", "통닭": "생닭",
    "다진마늘": "마늘", "다진 마늘": "마늘", "간마늘": "마늘",
    "대파": "대파", "쪽파": "대파", "파": "대파",
    "설탕": "설탕", "백설탕": "설탕",
    "진간장": "간장", "양조간장": "간장", "국간장": "간장",
    "식용유": "식용유", "포도씨유": "식용유", "카놀라유": "식용유",
    "청양고추": "청양고추", "홍고추": "홍고추", "풋고추": "풋고추",
    "돼지고기": "돼지고기 다짐육", "다진돼지고기": "돼지고기 다짐육", "간돼지고기": "돼지고기 다짐육",
    "달걀": "신선 계란", "계란": "신선 계란", "달갈": "신선 계란",
    "양파": "양파", "당근": "당근", "감자": "감자", "애호박": "애호박",
}


def norm(s):
    return re.sub(r"[\s()（）·・,\-_/]+", "", (s or "")).lower()


def build_index(cur):
    """이름·정규화이름 → key. manual_price 있는 것을 우선(원가계산 가능)."""
    exact, part = {}, []
    for k, nm, mp in cur.execute("SELECT ingredient_key, name, manual_price FROM ingredients"):
        exact.setdefault(norm(nm), (k, nm, mp is not None))
        part.append((norm(nm), k, nm, mp is not None))
    return exact, part


def resolve(name, exact, part):
    """재료명 → (key, 우리이름) 또는 None. 정확 → 동의어 → 부분."""
    n = norm(name)
    if n in exact:
        return exact[n][0], exact[n][1]
    syn = SYN.get(name.strip()) or SYN.get(name.replace(" ", ""))
    if syn and norm(syn) in exact:
        return exact[norm(syn)][0], exact[norm(syn)][1]
    # 부분일치 — 우리 이름이 재료명을 포함하거나 그 반대. manual_price 있는 것 우선, 짧은 이름 우선
    cands = [(pk, pn, pr) for pn0, pk, pn, pr in part if n and (n in pn0 or pn0 in n)]
    if cands:
        cands.sort(key=lambda x: (not x[2], len(norm(x[1]))))
        return cands[0][0], cands[0][1]
    return None, None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("사용법: python scripts/dish_recipe_apply.py <recipe.json> [--apply]")
    apply = "--apply" in sys.argv
    d = json.load(io.open(args[0], encoding="utf-8"))
    con = sqlite3.connect(DB)
    cur = con.cursor()
    exact, part = build_index(cur)

    slug = d.get("slug")
    row = None
    if slug:
        row = cur.execute("SELECT slug, name FROM dish_def WHERE slug=?", (slug,)).fetchone()
    if not row and d.get("name"):
        row = cur.execute("SELECT slug, name FROM dish_def WHERE name=?", (d["name"],)).fetchone()
    if not row:
        print("🔴 요리를 못 찾았다: %s / %s" % (slug, d.get("name")))
        return 1
    slug, name = row

    resolved, missing = [], []
    for it in d["ingredients"]:
        k = it.get("key")
        if k:
            nm = cur.execute("SELECT name FROM ingredients WHERE ingredient_key=?", (k,)).fetchone()
            if not nm:
                missing.append(it.get("name") or k)
                continue
            resolved.append((k, nm[0], it["amount"], it.get("unit", "g")))
            continue
        rk, rn = resolve(it["name"], exact, part)
        if rk:
            resolved.append((rk, rn, it["amount"], it.get("unit", "g")))
        else:
            missing.append(it["name"])

    print("■ %s (%s)" % (name, slug))
    print("  재료 %d개 매핑:" % len(resolved))
    for k, rn, amt, u in resolved:
        print("     %-26s %s%-4s  → %s" % (k, amt, u or "", rn[:20]))
    if missing:
        print("  🔴 못 찾은 재료 %d개 (넣지 않음 — 확인 필요): %s" % (len(missing), missing))
    steps = d.get("recipe") or []
    print("  조리법 %d문장" % len(steps))

    if not apply:
        print("\n(미리보기 — 반영하려면 --apply)")
        return 0

    if not resolved:
        print("🔴 매핑된 재료가 없어 반영하지 않는다.")
        return 1
    cur.execute("DELETE FROM dish_def_ingredient WHERE slug=?", (slug,))
    for i, (k, rn, amt, u) in enumerate(resolved):
        cur.execute("INSERT INTO dish_def_ingredient(slug, ingredient_key, amount, unit, sort_order, grp)"
                    " VALUES(?,?,?,?,?,'')", (slug, k, amt, u, i))
    # dish_def_ingredient 가 정본. dishes 쪽 재료·조리법도 함께 맞춘다
    if steps:
        cur.execute("UPDATE dishes SET recipe_steps=? WHERE slug=?", ("\n".join(steps), slug))
    if d.get("serving"):
        cur.execute("UPDATE dish_def SET serving=? WHERE slug=?", (d["serving"], slug))
        cur.execute("UPDATE dishes SET serving=? WHERE slug=?", (d["serving"], slug))
    con.commit()
    print("\n✅ 반영: 재료 %d개 · 조리법 %d문장%s"
          % (len(resolved), len(steps), " · 못 찾은 %d개는 제외" % len(missing) if missing else ""))
    print("   원가 재계산:  python scripts/compute_line_costs.py")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
