# -*- coding: utf-8 -*-
"""쿠팡 후보 중 **상품명에 용량이 박힌 것**만 골라 보여준다. 2026-07-27

🔴 왜 — 소매 상품에 용량(`pack_g`)이 없으면 단위당 단가를 못 내고, 원가 계산이 옛
   `manual_price` 로 조용히 넘어간다. 지금 그 상태가 125종이다.
   전에는 상품을 먼저 붙이고 나중에 폰 크롬으로 용량을 읽었다 — 1건당 6초 + 차단 위험
   (2026-07-27 실제로 11건에서 막혔다).
   **고르는 단계에서 용량이 있는 것만 채택하면** 폰이 필요 없다.

🔴 상품을 자동으로 확정하지 않는다 (대표 지시). 사람이 보고 고른다 —
   자동 판정으로 세 번 다른 물건이 붙었다(포마스 혼합유 · 리코타 치즈 · 알룰로스).
   그래서 이 스크립트는 **보여주기만** 한다. 확정은 `--set <재료키> <번호>`.

고르는 순서 (대표 확정)
   ① 물건이 맞나        ② 필요량을 덮는 최소 규격      ③ 총지출 최저      ④ 못 찾으면 비운다

    python scripts/retail_pick_sized.py 다진마늘 붉은고추 청양고추
    python scripts/retail_pick_sized.py --set garlic_minced 2
"""
import io
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
CAND = os.path.join(BASE, "data", "research", "ingredient_retail.json")
sys.stdout.reconfigure(encoding="utf-8")

# 상품명에서 용량을 읽는다. **배수 표기를 반드시 반영한다** —
#  "500g 2개입" 은 1kg 이다. 식봄 캐시가 이걸 안 해서 562건이 틀렸다(2026-07-25 사고).
RX_MULT = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\s*[x×*]\s*(\d+)\s*(?:개|입|봉|팩|병)?", re.I)
RX_CNT = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\s*,\s*(\d+)\s*(?:개|입|봉|팩|병)", re.I)
# 🔴 **개수가 먼저 오는 표기** — `도시락김, 40개, 4g` (2026-08-03 사고).
#    위 두 패턴은 「용량 다음 개수」만 잡는다. 역순이면 배수를 놓치고 **한 봉 용량**만 읽어서
#    조미김 2g 라인이 8,550원(판매가 3,900원)으로 튀었다. 07-25 「5kg 2팩」과 같은 유형이다.
RX_CNT_REV = re.compile(r"(\d+)\s*(?:개|입|봉|팩|병)\s*,\s*([\d,.]+)\s*(kg|g|l|ml)\b", re.I)
RX_ONE = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\b", re.I)
RX_BAD = re.compile(r"선물|기프트|세트박스|체험|샘플")


def g_of(v, u):
    v = float(str(v).replace(",", ""))
    return v * 1000 if u.lower() in ("kg", "l") else v


def pack_of(it):
    """후보 하나의 (총 g, 설명). `coupang_ingredient.py` 가 이미 `pack_kg` 를 계산해 둔다.
    그게 없으면 상품명에서 직접 읽는다. 둘 다 안 되면 (None, "")."""
    kg = it.get("pack_kg")
    try:
        if kg not in (None, "", "None"):
            return float(kg) * 1000, (it.get("pack_how") or "%gkg" % float(kg))
    except (TypeError, ValueError):
        pass
    return read_pack(it.get("name"))


def read_pack(name):
    """(총 g, 설명). 못 읽으면 (None, "")."""
    if not name:
        return None, ""
    m = RX_CNT_REV.search(name)          # 개수가 먼저 — `40개, 4g`
    if m:
        one = g_of(m.group(2), m.group(3))
        n = int(m.group(1))
        if 1 <= n <= 300 and 1 <= one <= 30000:
            return one * n, "%g%s × %d" % (float(m.group(2).replace(",", "")),
                                           m.group(3), n)
    for rx in (RX_MULT, RX_CNT):
        m = rx.search(name)
        if m:
            one = g_of(m.group(1), m.group(2))
            n = int(m.group(3))
            if 1 <= n <= 60 and 1 <= one <= 30000:
                return one * n, "%g%s × %d" % (float(m.group(1).replace(",", "")),
                                               m.group(2), n)
    m = RX_ONE.search(name)
    if m:
        one = g_of(m.group(1), m.group(2))
        if 1 <= one <= 60000:
            return one, "%g%s" % (float(m.group(1).replace(",", "")), m.group(2))
    return None, ""


def load_cand():
    if not os.path.exists(CAND):
        print("✗ 후보 파일이 없다 — 먼저 `python scripts/coupang_ingredient.py --only=<이름>`")
        return {}
    d = json.load(io.open(CAND, encoding="utf-8"))
    return d if isinstance(d, dict) else {}


# 🔴 `--all` — 용량 필터를 끈다 (2026-08-03 신설)
#    로켓 상품은 상품명에 용량을 거의 안 쓴다(`[로켓프레시] 깐양파 2개입`).
#    기본 화면은 «용량이 상품명에 박힌 것»만 보여주므로 **로켓 소포장이 통째로 숨는다** —
#    실제로 진간장이 그랬다: 같은 pageKey 안에 로켓 3,740원이 있는데 화면엔 일반 13,480원만 떴다.
#    `coupang_ingredient.py:170` 에 «용량 못 읽어도 버리지 않는다» 고 적혀 있는데
#    이 화면이 그걸 되돌려놨었다. 용량은 나중에 폰/옵션으로 채운다.
SHOW_ALL = False


def sized_of(items):
    """보여줄 후보 목록. `--all` 이면 용량 없는 것도 남긴다.
    ⚠️ `--set` 의 번호와 맞아야 하므로 **반드시 이 함수 하나만** 쓴다."""
    out = []
    for it in items:
        nm = it.get("name") or ""
        if RX_BAD.search(nm):
            continue
        pg, desc = pack_of(it)
        if pg or SHOW_ALL:
            out.append((it, pg, desc))
    return out


def main():
    global SHOW_ALL
    SHOW_ALL = "--all" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()
    cand = load_cand()

    if "--store" in sys.argv:
        # 🔴 소매에서 뺄 재료 — 치킨무처럼 **한 개 단위로 못 사는 것**.
        #    도매(매장 원가)에는 그대로 들어가고 소매에서만 빠진다.
        #    ⛔ `'none'` 을 쓰면 안 된다 — 그건 「소매값 없음」이라 뜻이 다르고,
        #       07-27 에 그걸로 90개 메뉴의 소매 총액이 통째로 재계산 안 됐다.
        i = sys.argv.index("--store")
        for key in [a for a in sys.argv[i + 1:] if not a.startswith("--")]:
            r = cur.execute("SELECT name, display_name FROM ingredients "
                            "WHERE ingredient_key=?", (key,)).fetchone()
            if not r:
                print("✗ 그런 재료가 없다 — %s" % key)
                continue
            cur.execute("""INSERT INTO ingredient_retail
                           (ingredient_key, status, decided_at) VALUES(?, 'store', date('now'))
                           ON CONFLICT(ingredient_key) DO UPDATE SET
                             status='store', decided_at=date('now')""", (key,))
            print("✅ %-22s %s — 소매에서 뺀다(매장 전용)" % (key, r["display_name"] or r["name"]))
        c.commit()
        print("   이어서 `python scripts/compute_line_costs.py`")
        return

    if "--set" in sys.argv:
        i = sys.argv.index("--set")
        key, no = sys.argv[i + 1], int(sys.argv[i + 2])
        v = cand.get(key) or {}
        items = (v.get("cands") or v.get("refined") or []) if isinstance(v, dict) else v
        # 보여줄 때와 **똑같은 순서·필터**로 골라야 번호가 맞는다
        sized = sized_of(items)
        if not (1 <= no <= len(sized)):
            print("✗ 번호가 범위를 벗어났다 (1~%d)" % len(sized))
            return
        it, pg, desc = sized[no - 1]
        nm = it.get("name")
        price = it.get("price")
        cur.execute("""INSERT INTO ingredient_retail
                       (ingredient_key, product_id, name, price, pack_g, rocket, image, url,
                        status, decided_at)
                       VALUES(?,?,?,?,?,?,?,?, 'ok', date('now'))
                       ON CONFLICT(ingredient_key) DO UPDATE SET
                         product_id=excluded.product_id, name=excluded.name,
                         price=excluded.price, pack_g=excluded.pack_g,
                         rocket=excluded.rocket, image=excluded.image, url=excluded.url,
                         status='ok', decided_at=date('now')""",
                    (key, it.get("product_id"), nm, float(price or 0), pg,
                     1 if str(it.get("rocket")) in ("1", "True") else 0,
                     it.get("image"), it.get("url")))
        c.commit()
        print("✅ %s ← %s / %s원 / %s" % (key, nm[:50], format(int(float(price or 0)), ","), desc))
        print("   이어서 `python scripts/compute_line_costs.py`")
        return

    words = [a for a in sys.argv[1:] if not a.startswith("--")]
    for key, v in cand.items():
        r = cur.execute("""SELECT i.name, i.display_name dn, i.base_unit bu,
                                  i.wholesale_price wp,
                                  (SELECT amount FROM menu_ingredients mi
                                    WHERE mi.ingredient_key=i.ingredient_key LIMIT 1) amt,
                                  (SELECT unit FROM menu_ingredients mi
                                    WHERE mi.ingredient_key=i.ingredient_key LIMIT 1) au
                           FROM ingredients i WHERE i.ingredient_key=?""", (key,)).fetchone()
        if not r:
            continue
        nm_all = (r["name"] or "") + (r["dn"] or "")
        if words and not any(w.replace(" ", "") in nm_all.replace(" ", "") for w in words):
            continue
        items = (v.get("cands") or v.get("refined") or []) if isinstance(v, dict) else v
        if not items:
            continue
        print("=" * 96)
        print("● %s  (%s)  도매 %s원/%s · 쓰는 양 %s%s"
              % (r["dn"] or r["name"], key, format(r["wp"] or 0, ","), r["bu"],
                 r["amt"], r["au"] or ""))
        print("=" * 96)
        sized = sized_of(items)
        unsized = len(items) - len(sized)
        if not sized:
            print("   ⛔ 용량이 상품명에 박힌 후보가 없다 (%d개 전부) — 검색어를 바꾸거나 비워둔다" % unsized)
            print()
            continue
        for n, (it, pg, desc) in enumerate(sized, 1):
            price = float(it.get("productPrice") or it.get("price") or 0)
            # 🔴 로켓 여부는 후보 파일의 `rocket` 에 있다. `isRocket` 은 검색 API 원본 필드라
            #    여기(가공된 후보)엔 없어서 **전부 「일반」으로 찍히고 있었다**(2026-08-03).
            rk = "로켓" if str(it.get("rocket") or it.get("isRocket")) in ("1", "True") else "일반"
            if not pg:
                print("   %d) %8s원 %-7s %8s      %s"
                      % (n, format(int(price), ","), rk, "(용량모름)", ""))
                print("        %s" % nm_trim(it.get("productName") or it.get("name")))
                continue
            per = price / (pg / 1000.0) if (r["bu"] or "").lower() in ("kg", "l") else price / pg
            need = float(r["amt"] or 0)
            packs = 1
            if need and pg:
                import math
                nu = need if (r["au"] or "") in ("g", "ml") else need * 1000
                packs = max(1, math.ceil(nu / pg))
            print("   %d) %8s원 %-7s %8s/%s  ×%d팩=%s원  %s"
                  % (n, format(int(price), ","), rk,
                     format(round(per), ","), r["bu"], packs,
                     format(int(price * packs), ","), desc))
            print("        %s" % nm_trim(it.get("productName") or it.get("name")))
        if unsized:
            print("   (용량 모르는 후보 %d개는 뺐다 — 화면에서 읽어야 하는 것들)" % unsized)
        print()


def nm_trim(s):
    return (s or "")[:82]


if __name__ == "__main__":
    main()
