# -*- coding: utf-8 -*-
"""잘려 저장된 상품명을 **원문에서 되찾아** 용량을 복원한다. 2026-07-27

🔴 2026-07-27 사고 — DB 에는 `백설 콩기름` 으로만 있었는데 실제 상품명은
   `백설 콩기름, 1.5L, 1개` 였다. 상품을 붙일 때 이름을 다듬으면서 **용량 표기를 지웠고**,
   그래서 `pack_g` 를 못 채워 폰 크롬으로 다시 읽어야 했다(1건당 6초 + 차단 위험).
   같은 이유로 용량이 빈 재료가 123종이다.

🔴 대표 지시: *"우리 그럼 용량을 별도 칼럼에 넣어서 세트로 붙여야 겠네"*
   → 상품명·가격·**용량**은 항상 함께 저장한다. 원문 상품명도 `name_raw` 에 남긴다.

여기서는 **읽기만** 해서 되찾을 수 있는 것을 세고, `--apply` 로만 채운다.
   근거는 `product_id` 가 같은 검색 결과다 — 이름이 비슷한 다른 상품을 붙이지 않는다.

    python scripts/retail_packsize_recover.py
    python scripts/retail_packsize_recover.py --apply
"""
import io
import json
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
DIRS = [os.path.join(BASE, "data", "research", "coupang"),
        os.path.join(BASE, "data", "research", "coupang_ing")]
JSONS = [os.path.join(BASE, "data", "research", "ingredient_retail.json"),
         os.path.join(BASE, "data", "research", "retail_manual.json")]
sys.stdout.reconfigure(encoding="utf-8")

RX_MULT = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\s*[x×*]\s*(\d+)", re.I)
RX_CNT = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\s*,\s*(\d+)\s*(?:개|입|봉|팩|병)", re.I)
RX_ONE = re.compile(r"([\d,.]+)\s*(kg|g|l|ml)\b", re.I)


def g_of(v, u):
    v = float(str(v).replace(",", ""))
    return v * 1000 if u.lower() in ("kg", "l") else v


def read_pack(name):
    """상품명에서 (총 g, 표기 원문). 배수 표기를 반드시 반영한다 —
    '500g 2개입' 은 1kg 이다(2026-07-25 식봄 캐시 562건 오류의 원인)."""
    if not name:
        return None, ""
    for rx in (RX_MULT, RX_CNT):
        m = rx.search(name)
        if m:
            one, n = g_of(m.group(1), m.group(2)), int(m.group(3))
            if 1 <= n <= 60 and 1 <= one <= 30000:
                return one * n, m.group(0).strip()
    m = RX_ONE.search(name)
    if m:
        one = g_of(m.group(1), m.group(2))
        if 1 <= one <= 60000:
            return one, m.group(0).strip()
    return None, ""


def collect():
    """product_id → 원문 상품명. 모든 수집 파일을 훑는다."""
    by_pid, by_name = {}, {}

    def take(it):
        nm = it.get("productName") or it.get("name")
        pid = it.get("productId") or it.get("product_id")
        if not nm:
            return
        if pid:
            by_pid.setdefault(str(pid), nm)
        # 이름 앞부분으로도 찾을 수 있게 — 잘린 이름은 원문의 접두사다
        by_name.setdefault(re.sub(r"[\s,]+", "", nm)[:16], nm)

    for d in DIRS:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.endswith(".json"):
                continue
            try:
                data = json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
            except Exception:
                continue
            items = data if isinstance(data, list) else []
            if isinstance(data, dict):
                for k in ("productData", "items", "data", "cands", "refined"):
                    v = data.get(k)
                    if isinstance(v, list):
                        items = v
                        break
            for it in items:
                if isinstance(it, dict):
                    take(it)

    for p in JSONS:
        if not os.path.exists(p):
            continue
        try:
            data = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, dict):
                    for k in ("cands", "refined"):
                        for it in (v.get(k) or []):
                            if isinstance(it, dict):
                                take(it)
                elif isinstance(v, list):
                    for it in v:
                        if isinstance(it, dict):
                            take(it)
    return by_pid, by_name


def main():
    apply = "--apply" in sys.argv
    by_pid, by_name = collect()
    print("수집 파일에서 원문 상품명 %d개(pid) · %d개(이름) 확보" % (len(by_pid), len(by_name)))
    print()

    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(ingredient_retail)")]
    if "name_raw" not in cols and apply:
        cur.execute("ALTER TABLE ingredient_retail ADD COLUMN name_raw TEXT")
        c.commit()
        print("• ingredient_retail.name_raw 칼럼 추가 (원문 상품명 보존용)")
        print()

    rows = [dict(r) for r in cur.execute("""
        SELECT x.ingredient_key k, x.name pn, x.product_id pid, x.price p,
               COALESCE(i.display_name, i.name) inm
        FROM ingredient_retail x JOIN ingredients i ON i.ingredient_key=x.ingredient_key
        WHERE (x.pack_g IS NULL OR x.pack_g = 0) AND x.price > 0
          AND COALESCE(x.status,'') NOT IN ('store','none')
        ORDER BY i.name""")]

    got, miss = [], []
    for r in rows:
        raw = None
        if r["pid"]:
            raw = by_pid.get(str(r["pid"]))
        if not raw and r["pn"]:
            raw = by_name.get(re.sub(r"[\s,]+", "", r["pn"])[:16])
        pg, desc = read_pack(raw) if raw else (None, "")
        if not pg and r["pn"]:                 # DB 이름 자체에 용량이 남아 있을 수도
            pg, desc = read_pack(r["pn"])
            raw = raw or r["pn"]
        if pg:
            got.append((r, raw, pg, desc))
        else:
            miss.append(r)

    print("되찾음 %d종 · 못 찾음 %d종 (전체 %d종)" % (len(got), len(miss), len(rows)))
    print()
    for r, raw, pg, desc in got:
        print("  ✅ %-22s %-46s → %gg  (%s)" % (r["inm"][:22], (raw or "")[:46], pg, desc))
    if miss:
        print()
        print("  ── 폰으로 읽어야 하는 것 ──")
        for r in miss[:20]:
            print("  ⚠️ %-22s %-46s pid %s" % (r["inm"][:22], (r["pn"] or "")[:46],
                                              r["pid"] or "없음"))
        if len(miss) > 20:
            print("     … 외 %d종" % (len(miss) - 20))

    if not apply:
        print()
        print("← 미반영. --apply 를 붙여라")
        return
    for r, raw, pg, desc in got:
        cur.execute("UPDATE ingredient_retail SET pack_g=?, name_raw=? WHERE ingredient_key=?",
                    (pg, raw, r["k"]))
    c.commit()
    print()
    print("✅ %d종 용량 채움. 이어서 `python scripts/compute_line_costs.py`" % len(got))


if __name__ == "__main__":
    main()
