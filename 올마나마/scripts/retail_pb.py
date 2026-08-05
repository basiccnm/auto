# -*- coding: utf-8 -*-
"""소매 상품을 **곰곰(쿠팡 PB) 우선 · 1개짜리 최저가**로 다시 고른다. 2026-07-26

🔴 대표 지시
  *"왠만한거 곰곰<<PB쿠팡 상품으로 일단 한번 찾아봐 / 곰곰 시저드레싱 · 곰곰 우유 이런식으로"*
  *"1개짜리 있다고 / 왜 안찾고 니생각만 이야기해"*

무엇이 잘못됐었나
  ① 쿠팡 API 는 **같은 상품의 옵션(개수)마다 별도 행**을 주는데 **상품명이 똑같다.**
     곰곰 우유 productId 1232968322 → 2,230 / 3,690 / 7,380 / 11,070 / 18,450 / 22,140원
     이름만 보면 1개인지 6개인지 알 수 없다. 그래서 6개 묶음이 최저가로 잡혔다.
  ② **검색어에 따라 나오는 옵션이 다르다.**
     `곰곰 우유` → 3,690원부터.  `곰곰 신선한 1A 우유 900ml` → **2,230원** 이 나온다.
     내가 "API 에 1개짜리가 없다"고 단정한 게 틀렸다 — 검색어를 안 바꿔봤을 뿐이다.
  ③ 배수로 역산해도 안 된다. 3,690÷2=1,845 인데 실제 1개는 2,230원(묶음이 개당 더 싸다).

그래서 이렇게 찾는다
  ① **곰곰 + 품목명** 을 1순위로 검색 (쿠팡 PB 가 대체로 최저가다)
  ② 곰곰이 없으면 품목명·용량 붙인 검색어로 확장
  ③ **같은 productId 안에서는 최저 가격 = 1개짜리**
  ④ 묶음 표기(", 6개" 등)가 있는 것은 후순위
  ⑤ 로켓배송·먹는 것(categoryName)만

    python scripts/retail_pb.py                # 캐시만 (보고)
    python scripts/retail_pb.py --collect      # 곰곰 검색어 수집 후 보고
    python scripts/retail_pb.py --collect --apply
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
SLEEP = 2.0

sys.path.insert(0, os.path.join(BASE, "scripts"))
import coupang_ingredient as CI    # noqa: E402
import retail_fill as RF           # noqa: E402
import retail_retry as RR          # noqa: E402
from retail_single import bundle_count  # noqa: E402
from mealkit_run import load_env   # noqa: E402

PB = "곰곰"          # 쿠팡 PB. 대체로 최저가다(대표 방침 2026-07-26)


def kw_for(name):
    """곰곰을 1순위로, 그다음 넓은 검색어들."""
    base = RR.kw_candidates(name)
    head = base[0] if base else RF.keyword(name)
    out = ["%s %s" % (PB, head)]
    if len(base) > 1:
        out.append("%s %s" % (PB, base[1]))
    return list(dict.fromkeys(out + base))


def pick(key, name, rej, collect, ak, sk, budget):
    """이 재료의 후보를 모아 1개짜리 최저가를 고른다. (best, used) 반환"""
    used, pool, seen = 0, [], set()
    for kw in kw_for(name)[:6]:
        fp = RF.cpath(kw)
        items = None
        if os.path.exists(fp):
            try:
                items = json.load(io.open(fp, encoding="utf-8")).get("items") or []
            except Exception:
                items = None
        if items is None:
            if not collect or used >= budget:
                continue
            try:
                d = CI.api_search(kw, ak, sk)
            except Exception:
                used += 1
                time.sleep(SLEEP)
                continue
            if d.get("rCode") not in (0, "0"):
                return None, -1        # 한도 신호
            items = (d.get("data") or {}).get("productData") or []
            io.open(fp, "w", encoding="utf-8").write(
                json.dumps({"keyword": kw, "items": items}, ensure_ascii=False))
            used += 1
            time.sleep(SLEEP)
        cw = [t for t in kw.replace(PB, " ").split() if len(t) >= 2]
        for p in items:
            pid, pn, pr = p.get("productId"), p.get("productName") or "", p.get("productPrice")
            if not pr or not p.get("isRocket"):
                continue
            if pid in rej or not RF.is_food(p) or RF.JUNK.search(pn):
                continue
            if cw and not any(w in re.sub(r"\s+", "", pn) for w in cw):
                continue
            if [x for x in CI.PROCESSED if re.search(x, pn) and not re.search(x, name)]:
                continue
            k2 = (pid, pr)
            if k2 in seen:
                continue
            seen.add(k2)
            pool.append({"pid": pid, "name": pn, "price": pr, "kw": kw,
                         "bundle": bundle_count(pn),
                         "pb": 0 if PB in pn else 1,
                         "premium": 1 if CI.PREMIUM.search(pn) else 0,
                         "pack_g": RF.pack_g(pn),
                         "image": p.get("productImage"), "url": p.get("productUrl")})
    if not pool:
        return None, used
    # 🔴 같은 productId 는 **최저 가격이 1개짜리**다. 그것만 남긴다.
    lowest = {}
    for x in pool:
        if x["pid"] not in lowest or x["price"] < lowest[x["pid"]]["price"]:
            lowest[x["pid"]] = x
    cands = list(lowest.values())
    # ① 곰곰(PB) 우선 → ② 묶음 후순위 → ③ 프리미엄 후순위 → ④ 가격 최저
    cands.sort(key=lambda x: (x["pb"], 1 if x["bundle"] else 0, x["premium"], x["price"]))
    return cands[0], used


def main():
    collect = "--collect" in sys.argv
    apply = "--apply" in sys.argv
    budget = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--budget=")), 500)

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY"), env.get("COUPANG_SECRET_KEY")

    rej = {}
    for r in c.execute("SELECT ingredient_key, product_id FROM retail_rejected"):
        rej.setdefault(r[0], set()).add(r[1])

    rows = [r for r in c.execute("""
        SELECT x.ingredient_key k, x.name pn, x.price pr, x.product_id pid, x.status,
               i.name inm,
               (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=x.ingredient_key) uses
        FROM ingredient_retail x JOIN ingredients i ON i.ingredient_key=x.ingredient_key
        WHERE x.status IN ('ok','pending','skip') ORDER BY uses DESC""")]
    print("대상 %d종 · 곰곰(PB) 1순위 · 같은 상품은 최저 옵션 = 1개짜리" % len(rows), flush=True)
    print("", flush=True)

    used, changed, kept = 0, [], 0
    for r in rows:
        if used >= budget:
            print("예산 소진 — 중단", flush=True)
            break
        b, u = pick(r["k"], r["inm"], rej.get(r["k"], set()), collect, ak, sk, budget - used)
        if u < 0:
            print("!! 쿠팡 한도 — 중단", flush=True)
            break
        used += u
        if not b:
            continue
        if r["status"] == "skip":          # 로켓 매치가 없던 것 → 찾았으면 무조건 올린다
            changed.append((r, b))
            continue
        if b["pid"] == r["pid"] and b["price"] >= (r["pr"] or 0) * 0.98:
            kept += 1
            continue
        if b["price"] < (r["pr"] or 10 ** 9) * 0.98:
            changed.append((r, b))
        else:
            kept += 1

    changed.sort(key=lambda t: -t[0]["uses"])
    print("바꿀 것 %d종 · 그대로 %d종 · API %d회" % (len(changed), kept, used))
    print()
    print("%-20s %4s %10s %-30s %10s %-30s" % ("재료", "메뉴", "지금", "지금 상품", "바꿈", "바꿀 상품"))
    print("-" * 132)
    for r, b in changed[:45]:
        print("%-20s %3d개 %9s원 %-30s %9s원 %-30s" % (
            r["inm"][:20], r["uses"], format(round(r["pr"] or 0), ","), (r["pn"] or "")[:30],
            format(b["price"], ","), b["name"][:30]))
    print("-" * 132)

    if apply:
        cur = c.cursor()
        for r, b in changed:
            cur.execute("""INSERT OR REPLACE INTO ingredient_retail
                (ingredient_key,product_id,name,price,pack_g,rocket,image,url,status,decided_at)
                VALUES(?,?,?,?,?,1,?,?, 'pending', NULL)""",
                        (r["k"], b["pid"], b["name"], b["price"], b["pack_g"],
                         b["image"], b["url"]))
        c.commit()
        print()
        print("✅ %d종 갈아끼움 — 검수 대기로 올렸습니다" % len(changed))
    else:
        print()
        print("DB 미반영. 반영은 --apply")
    c.close()


if __name__ == "__main__":
    main()
