# -*- coding: utf-8 -*-
"""소매 상품 = **그 재료인 상품 중 가격이 제일 싼 것**. 2026-07-26

대표 지시 (그대로 옮긴다)
  *"그냥 최소가격을 찾으라고"*
  *"상한을 정하지 말라고 가정용은"*
  *"1~2인분 해먹을껀데 단가는 높더라도 버리는것보다 작은거 써서 돈덜쓰는게 중요한데"*
  *"도매는 반대겠지?? 무조건 싼거 용량이 크더라도 팔수 있을 정도의 용량이 큰거를 사는게 이치"*

  소매와 도매는 기준이 **반대**다.
    소매(집에서 1~2인분) = **가격 최저**. 제일 싼 게 제일 작은 것이고 그게 가정용이다
    도매(매장)          = 대용량 중 **kg당 단가 최저** — 이건 식봄 쪽에서 따로 한다

🔴 내가 걸었다가 뺀 조건들 (전부 대표 지시로 삭제)
  · "용량 ≥ 레시피 필요량"  → 이 조건 때문에 용량 모르는 상품이 전부 탈락하고
                            족발 2.5kg 29,800원 같은 큰 게 올라왔다
  · "품목별 가정용 상한"     → 내가 정하는 추측이다. 상한을 두지 말라는 지시
  남는 조건은 **하나뿐이다 — 그 재료가 맞는지.**

🔴 사람이 확정한 건 건드리지 않는다
  `ingredient_retail.decided_at` 이 있는 재료는 대표가 화면에서 직접 고른 정본이다.

오매칭 방지 (어제 건두부→쌈두부 · 튀김가루→돌자반볶음 사고)
  · 검색어는 `generic()` — 재료명에서 **브랜드를 떼고 품목명만** 남긴다
    (참마시 쏘드레 치킨양념소스 10kg → 치킨양념소스)
  · 채택 전에 **상품명에 그 품목명이 실제로 들어있는지** 검증한다

    python scripts/coupang_minbuy.py --collect     # API 수집 + 선정 (2초 간격)
    python scripts/coupang_minbuy.py               # 캐시만 읽어 선정
    python scripts/coupang_minbuy.py --apply       # 미확정 재료만 DB 반영
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
CACHE = os.path.join(BASE, "data", "research", "coupang_ing")
OUT = os.path.join(BASE, "data", "research", "coupang_minbuy.json")
SLEEP = 2.0          # 분당 30회. 쿠팡 API 가 정지되면 복구가 어렵다(대표 경고)

sys.path.insert(0, os.path.join(BASE, "scripts"))
import coupang_ingredient as CI   # noqa: E402
from mealkit_run import load_env  # noqa: E402

_UNIT = {"kg": 1000.0, "g": 1.0, "l": 1000.0, "ml": 1.0}
# ⚠️ 배수 표기를 반영한다("75g x 4" = 300g). 식봄 캐시가 이걸 안 해서 3,260행이 틀렸다.
_MULT = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*[*xX×]\s*(\d+)", re.I)
_MULT2 = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)\s*,?\s*(\d+)\s*(?:개입|개|입|팩|봉|매|장)", re.I)
_ONE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|l|ml)(?![a-z가-힣])", re.I)
# 먹는 게 아닌 것 — 검색에 섞여 들어온다(오뎅바 테이블, 미니어처 등 실제로 걸렸다)
JUNK = re.compile(r"미니어처|장난감|DIY|테이블|포차|노점|인덕션|냄비|용기|그릇|받침|트레이|"
                  r"주방|식기|도마|칼\b|장바구니|보관함", re.I)


def grams(name):
    n = (name or "").replace(",", "")
    for rx in (_MULT, _MULT2):
        m = rx.search(n)
        if m:
            return float(m.group(1)) * _UNIT[m.group(2).lower()] * int(m.group(3))
    m = _ONE.search(n)
    if m:
        return float(m.group(1)) * _UNIT[m.group(2).lower()]
    return None


def generic(name):
    """브랜드를 떼고 품목명만 남긴다. 재료명은 `브랜드 + 수식 + 품목명 + 용량` 꼴이 대부분이다."""
    s = CI.plain(name)
    s = re.sub(r"[·/]", " ", s)
    toks = [t for t in s.split() if len(t) >= 2]
    return toks[-1] if toks else s.strip()


def core_words(g):
    """상품명 검증용. '치킨양념소스'처럼 붙어 있으면 끝 2~3자도 본다."""
    out = {g}
    if len(g) >= 4:
        out |= {g[-3:], g[-2:]}
    return {w for w in out if len(w) >= 2}


def cpath(kw):
    return os.path.join(CACHE, re.sub(r"[^0-9A-Za-z가-힣]+", "_", kw)[:60] + ".json")


def main():
    collect = "--collect" in sys.argv
    apply = "--apply" in sys.argv
    budget = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--budget=")), 400)

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    env = load_env()
    ak, sk = env.get("COUPANG_ACCESS_KEY"), env.get("COUPANG_SECRET_KEY")

    decided = {r[0] for r in c.execute(
        "SELECT ingredient_key FROM ingredient_retail WHERE decided_at IS NOT NULL")}
    rows = [r for r in c.execute("""
        SELECT i.ingredient_key k, i.name, i.manual_price mp,
               (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=i.ingredient_key) uses
        FROM ingredients i
        WHERE (SELECT COUNT(*) FROM menu_ingredients mi WHERE mi.ingredient_key=i.ingredient_key) > 0
        ORDER BY uses DESC""")]
    todo = [r for r in rows if r["k"] not in decided]
    print("메뉴에 쓰이는 재료 %d종 · 대표 확정 %d종(제외) · 대상 %d종"
          % (len(rows), len(rows) - len(todo), len(todo)))
    print("기준: 그 재료인 상품 중 **가격 최저** (로켓 우선 · 용량 조건 없음)")
    print()

    used, picked, failed = 0, [], []
    for r in todo:
        k, nm = r["k"], r["name"]
        g0 = generic(nm)
        items = None
        fp = cpath(g0)
        if os.path.exists(fp):
            try:
                items = json.load(io.open(fp, encoding="utf-8")).get("items") or []
            except Exception:
                items = None
        if items is None and collect and used < budget:
            try:
                d = CI.api_search(g0, ak, sk)
            except Exception as e:
                print("   ! %-20s 호출실패 %s" % (g0[:20], str(e)[:44]))
                items = []
            else:
                if d.get("rCode") not in (0, "0"):
                    print("   !! rCode=%s — 즉시 중단(쿠팡 한도 보호)" % d.get("rCode"))
                    collect, items = False, []
                else:
                    items = (d.get("data") or {}).get("productData") or []
                    io.open(fp, "w", encoding="utf-8").write(
                        json.dumps({"keyword": g0, "items": items}, ensure_ascii=False))
            used += 1
            time.sleep(SLEEP)
        if not items:
            failed.append({"key": k, "name": nm, "generic": g0, "uses": r["uses"], "why": "후보 없음"})
            continue

        cores = core_words(g0)
        cands = []
        for p in items:
            pn, price = p.get("productName") or "", p.get("productPrice")
            if not price or JUNK.search(pn):
                continue
            # 그 재료가 맞는지 — 유일하게 남은 조건
            if not any(w in re.sub(r"\s+", "", pn) for w in cores):
                continue
            # 가공형태가 다르면 다른 물건이다(양파즙·양파가루는 양파가 아니다)
            if CI.PROCESSED_RE.search(pn) if hasattr(CI, "PROCESSED_RE") else False:
                pass
            bad = [w for w in CI.PROCESSED if re.search(w, pn) and not re.search(w, nm)]
            if bad:
                continue
            cands.append({
                "price": price, "pack_g": grams(pn), "product": pn,
                "rocket": 1 if p.get("isRocket") else 0,
                "premium": 1 if CI.PREMIUM.search(pn) and not CI.PREMIUM.search(nm) else 0,
                "url": p.get("productUrl"), "product_id": p.get("productId")})
        # 로켓 우선(배송비 없음) → 프리미엄 후순위 → **가격 최저**
        cands.sort(key=lambda x: (not x["rocket"], x["premium"], x["price"]))
        if not cands:
            failed.append({"key": k, "name": nm, "generic": g0, "uses": r["uses"],
                           "why": "품목 검증 통과 상품 없음"})
            continue
        b = dict(cands[0])
        b.update({"key": k, "name": nm, "generic": g0, "uses": r["uses"],
                  "old_manual": r["mp"], "alts": cands[1:3]})
        picked.append(b)

    picked.sort(key=lambda x: -x["uses"])
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(
        {"picked": picked, "failed": failed}, ensure_ascii=False, indent=1))

    novol = [p for p in picked if not p["pack_g"]]
    print("✅ 선정 %d종  ·  ❌ 못 찾음 %d종  ·  API %d회" % (len(picked), len(failed), used))
    print("   그중 용량이 상품명에 있는 것 %d종 / 없어서 대표 확인 필요 %d종"
          % (len(picked) - len(novol), len(novol)))
    print()
    print("%-22s %5s %9s %8s  %s" % ("재료", "쓰는곳", "최소가격", "용량", "상품"))
    print("-" * 112)
    for p in picked[:30]:
        print("%-22s %4d개 %8s원 %7s  %s" % (
            p["name"][:22], p["uses"], format(p["price"], ","),
            ("%.0fg" % p["pack_g"]) if p["pack_g"] else "?",
            p["product"][:44]))
    print("-" * 112)
    if failed:
        print("못 찾은 재료 %d종:" % len(failed))
        for f in failed[:20]:
            print("   %-24s (검색어 %s · %s)" % (f["name"][:24], f["generic"][:16], f["why"]))
    print()
    print("→ %s" % os.path.relpath(OUT, BASE))
    if not apply:
        print("  DB 미반영. 반영은 --apply")
    c.close()


if __name__ == "__main__":
    main()
