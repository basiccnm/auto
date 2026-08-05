# -*- coding: utf-8 -*-
"""**새 재료를 등록할 때 이 순서로 한다.** 2026-08-03 (대표 지시)

레시피·메뉴에서 처음 보는 재료가 나왔을 때, 아래를 **순서대로** 확인한다.
⛔ 이 순서를 건너뛰면 오늘 하루 종일 반복한 사고가 그대로 재현된다.

    python scripts/ingredient_new.py "흑마늘즙"       # 어떻게 할지 알려준다
    python scripts/ingredient_new.py "흑마늘즙" --json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ① 이미 DB에 있나          이름·화면이름·별칭을 다 본다. **90%가 여기서 끝난다**
 ② 표기만 다른가           띄어쓰기·「다진」·「생」·「국산」 같은 수식어를 떼고 다시 본다
 ③ 가공형태가 다른가        **즙·가루·분말·퓨레·시럽은 다른 재료다.** 원물에 붙이지 마라
 ④ 한 칸에 둘인가          `소금, 후추` → 둘 다 잡고 **양도 반씩 나눈다**
 ⑤ 물인가                물·얼음·생수·면수 → `water`(0원)
 ⑥ 제철인가              `ingredient_seasonal` 에 있으면 **「없는 것」이 아니다.** 철이 오면 받는다
 ⑦ 그래도 없으면 식봄에서 받는다  **카테고리 먼저**, 검색은 폴백. 도매=식봄 / 소매=쿠팡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**등록할 때 지킬 것**
  · `name` 은 **실제 쓰는 말**로 (「붉은고추」❌ → 「홍고추」⭕)
  · **띄어쓰기 없앤다** (「다진 소고기」 → 「다진소고기」)
  · `base_unit` 을 먼저 정한다 — **개·마리에 kg 시세를 넣으면 원가가 통째로 틀린다**
  · 도매는 **대용량 기준**, 소매는 **로켓 최소금액**
  · `wholesale_basis` 에 **상품명을 그대로** 남긴다 (나중에 값을 재검증한다)
  · `subcat` 을 반드시 채운다 (32개 중 하나)
"""
import io
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recipe_mapping import normalize, split_pair, WATER_PAT   # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

MOD = re.compile(r"^(흰|흑|생|햇|국산|국내산|수입|냉동|냉장|다진|간|썬|채썬|손질|삶은|불린|"
                 r"구운|볶은|말린|건조|얇게|굵게|잘게|송송|어슷|채|슬라이스|저민|편|통)\s*")
PAR = re.compile(r"\(.*?\)|또는.*$|혹은.*$")
PROC = re.compile(r"(즙|가루|분말|파우더|퓨레|시럽|잼)$")


def look(raw):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = [(r["ingredient_key"], r["name"], r["display_name"] or r["name"], r["wholesale_price"],
             r["base_unit"], r["subcat"])
            for r in c.execute("""SELECT ingredient_key,name,display_name,wholesale_price,
                                  base_unit,subcat FROM ingredients""")]
    alias = {r["alias_norm"]: r["ingredient_key"]
             for r in c.execute("SELECT alias_norm, ingredient_key FROM ingredient_alias")}
    byk = {x[0]: x for x in rows}
    out = {"raw": raw, "steps": []}

    def add(step, verdict, detail):
        out["steps"].append({"step": step, "verdict": verdict, "detail": detail})

    n = normalize(raw)
    # ① 그대로 있나
    hit = [x for x in rows if normalize(x[1]) == n or normalize(x[2]) == n]
    if hit or n in alias:
        k = hit[0][0] if hit else alias[n]
        x = byk[k]
        add("① DB에 있나", "✅ 있다", "%s  %s원/%s  [%s]"
            % (x[2], format(x[3] or 0, ","), x[4], x[5] or "분류없음"))
        out["key"] = k
        return out
    add("① DB에 있나", "없다", "이름·화면이름·별칭 어디에도 없다")

    # ⑤ 물
    if WATER_PAT.search(raw):
        add("⑤ 물인가", "✅ 물이다", "water(0원)로 붙인다 — 얼음·생수·면수도 물")
        out["key"] = "water"
        return out

    # ④ 한 칸에 둘
    pair = split_pair(raw)
    if pair:
        add("④ 한 칸에 둘인가", "✅ 둘이다",
            "%s → **둘 다** 잡고 양도 반씩 나눈다 (5g이면 2.5g씩)" % " + ".join(pair))
        out["parts"] = pair
        return out

    # ⑥ 제철
    try:
        se = {r["name"]: (r["season"], r["note"])
              for r in c.execute("SELECT name,season,note FROM ingredient_seasonal")}
    except sqlite3.OperationalError:
        se = {}
    for s, (season, note) in se.items():
        if s in raw:
            add("⑥ 제철인가", "🌱 제철이다",
                "%s · %s — **「없는 것」이 아니다.** 철이 오면 받는다" % (season, note))
            return out

    # ② 표기만 다른가
    core = PAR.sub("", raw).strip()
    for _ in range(3):
        core = MOD.sub("", core).strip()
    core = re.sub(r"\s+", "", core)
    ck = normalize(core)
    hit2 = [x for x in rows if normalize(x[2]) == ck or normalize(x[1]) == ck]
    if hit2 and core != raw:
        x = hit2[0]
        # ③ 가공형태 검사
        if PROC.search(raw) and not PROC.search(x[2]):
            add("③ 가공형태가 다른가", "⛔ 다른 재료다",
                "「%s」는 %s 의 가공품이다 — **붙이지 말고 따로 등록**한다 "
                "(흑마늘즙≠다진마늘 · 마늘가루≠다진마늘)" % (raw, x[2]))
            return out
        add("② 표기만 다른가", "✅ 같다",
            "「%s」 → %s  %s원/%s — **별칭으로 붙인다**"
            % (raw, x[2], format(x[3] or 0, ","), x[4]))
        out["key"] = x[0]
        return out

    # ③ 가공형태
    if PROC.search(raw):
        root = PROC.sub("", raw).strip()
        h = [x for x in rows if normalize(x[2]) == normalize(root)]
        add("③ 가공형태가 다른가", "⛔ 따로 등록",
            "원물 「%s」%s 이 있어도 **붙이지 마라** — 값이 다르다"
            % (root, ("(=%s)" % h[0][2]) if h else ""))

    # ⑦ 받는다
    add("⑦ 식봄에서 받는다", "→ 받아야 한다",
        "카테고리 먼저(`_가공카테고리.json`), 없으면 검색. 도매=식봄 / 소매=쿠팡. "
        "base_unit 을 먼저 정하고, wholesale_basis 에 상품명을 남긴다")
    out["ask"] = True          # 자동 판정이 안 된 것 — 물어볼 후보
    return out


def log_ask(raw, why):
    """🔴 **판정이 안 된 것은 묻지 말고 여기 쌓는다** (대표 지시 2026-08-03).
       *"물어보는 건 또 스크립트에 넣어서 추가로 넣어라"*
       한 건씩 대화로 묻지 말고 모아뒀다가 **한 번에** 확인받는다.
       `python scripts/ingredient_new.py --asks` 로 쌓인 목록을 본다."""
    p = os.path.join(BASE, "data", "wtable", "ingredient_ask.json")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        d = []
    if any(x["name"] == raw for x in d):
        return
    d.append({"name": raw, "why": why, "at": __import__("time").strftime("%Y-%m-%d %H:%M")})
    json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def show_asks():
    p = os.path.join(BASE, "data", "wtable", "ingredient_ask.json")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        d = []
    todo = [x for x in d if not x.get("answer")]
    done = [x for x in d if x.get("answer")]
    print("■ 물어볼 것 %d건 — **모아서 한 번에**" % len(todo))
    for x in todo:
        print("   %-24s %s  (%s)" % (x["name"][:24], x["why"], x["at"]))
    if not todo:
        print("   (없음)")
    if done:
        print()
        print("■ 답 받은 것 %d건 — 다음부터 자동 판정된다" % len(done))
        for x in done[:15]:
            print("   %-24s → %s" % (x["name"][:24], x["answer"]))


def answer(raw, ans):
    """🔴 **대표 답을 풀이법으로 저장한다** (지시 2026-08-03: *"묻고 그거에 대한 풀이법을 넣으라고"*)
       같은 재료를 두 번 묻지 않는다. 답이 「별칭:○○」이면 별칭까지 자동으로 넣는다.

           python scripts/ingredient_new.py --answer "황태" "별칭:북어"
           python scripts/ingredient_new.py --answer "레드와인" "식봄에 없다. 주류라 안 판다"
           python scripts/ingredient_new.py --answer "두릅"   "제철:봄(4~5월)"
    """
    p = os.path.join(BASE, "data", "wtable", "ingredient_ask.json")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        d = []
    c = sqlite3.connect(DB)
    applied = ""
    if ans.startswith("별칭:"):
        tgt = ans.split(":", 1)[1].strip()
        r = c.execute("SELECT ingredient_key FROM ingredients WHERE name=? OR display_name=?",
                      (tgt, tgt)).fetchone()
        if r:
            c.execute("""INSERT INTO ingredient_alias(alias_norm,alias_raw,ingredient_key,source,created_at)
                         VALUES(?,?,?,'answer',date('now'))
                         ON CONFLICT(alias_norm) DO UPDATE SET ingredient_key=excluded.ingredient_key""",
                      (normalize(raw), raw, r[0]))
            c.commit()
            applied = " → 별칭 등록 (%s)" % r[0]
        else:
            applied = " ⚠️ 대상 「%s」 가 DB에 없다" % tgt
    elif ans.startswith("제철:"):
        season = ans.split(":", 1)[1].strip()
        c.execute("""CREATE TABLE IF NOT EXISTS ingredient_seasonal(
                     name TEXT PRIMARY KEY, season TEXT, note TEXT, checked_at TEXT)""")
        c.execute("""INSERT OR REPLACE INTO ingredient_seasonal(name,season,note,checked_at)
                     VALUES(?,?,?,date('now'))""", (raw, season, "대표 확인", ))
        c.commit()
        applied = " → 제철 표에 등록"
    found = False
    for x in d:
        if x["name"] == raw:
            x["answer"] = ans; found = True
    if not found:
        d.append({"name": raw, "why": "직접 답함", "at": __import__("time").strftime("%Y-%m-%d %H:%M"),
                  "answer": ans})
    json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("✅ 「%s」 → %s%s" % (raw, ans, applied))


def main():
    if "--asks" in sys.argv:
        show_asks()
        return
    if "--answer" in sys.argv:
        i = sys.argv.index("--answer")
        answer(sys.argv[i + 1], sys.argv[i + 2])
        return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return
    asks = []
    for raw in args:
        r = look(raw)
        if r.get("ask"):
            log_ask(raw, "식봄에서 받아야 함 — 물건이 맞는지 사람이 봐야 한다")
            asks.append(raw)
        if "--json" in sys.argv:
            print(json.dumps(r, ensure_ascii=False, indent=1))
            continue
        print("■ 「%s」" % raw)
        for s in r["steps"]:
            print("   %-16s %-12s %s" % (s["step"], s["verdict"], s["detail"]))
        print()
    if asks:
        print("🔴 자동 판정 안 됨 %d건 — `ingredient_ask.json` 에 쌓았다." % len(asks))
        print("   ⛔ 한 건씩 묻지 마라. **모아서 한 번에** 대표에게 확인받는다:")
        print("      python scripts/ingredient_new.py --asks")


if __name__ == "__main__":
    main()
