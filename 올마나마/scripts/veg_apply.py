# -*- coding: utf-8 -*-
"""채소·과일 도매값을 **식봄 기준**으로 ingredient_price 표에 담는다. (2026-07-25)

대표 지시: 식봄을 채소 주력 소스로 삼는다. 미트박스(육류)·식자재왕몰(채소)은
별도 파일로 남겨 비교/백업용으로만 둔다(이 스크립트는 식봄만 반영).

원칙:
  - 원산지로 나눈다(국산/수입/중국산…). 당근 국산 vs 중국산이 크게 갈린다.
  - salePrice = 상시 판매가. 쿠폰가·정가 아님.
  - kg 규격만 원/kg. 단·개·망·포기는 환산 못 하니 뺀다(추측 금지).
  - **핵심어**(재료명)가 상품명에 있어야 인정. + **가공품 배제**.
    (오렌지→주스, 옥수수→물엿, 참깨→드레싱, 콩→두부 같은 오매칭을 막는다.)
  - 현장 실거래(우리 DB) 값이 이미 있으면 참고로 표에 함께 남긴다(대체로 최저).

ingredients.wholesale_price 는 표의 기본행(is_default)으로 동기화 — 기존 코드가 안 깨진다.
"""
import json, io, os, re, sqlite3, sys, shutil
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
FS = os.path.join(BASE, "data", "research", "foodspring", "_수집.json")
STAMP = "2026-07-25"

# 가공품 배제 — 원물이 아닌 것. (건고추·시래기·무말랭이 등 '말린 원물'은 살려야 하니
# 건조/말랭이는 넣지 않는다. 가공·조리된 것만 막는다.)
BAD = re.compile(
    r"주스|음료|물엿|조청|드레싱|소스|양념|퓨레|페이스트|두부|묵|캔|통조림|홀\b|다이스|"
    r"빙수|절임|피클|장아찌|짱아찌|즙|청\b|차\b|과자|젤리|시럽|잼|파우더|배터믹스|믹스|"
    r"국수|소면|파스타|라면|우동|만두|튀김|전\b|볶음|무침|조림|찜|탕|국\b|스프|수프|"
    r"육수|다시|진액|엑기스|농축|칩|스낵|건빵|빵|케이크|쿠키|아이스|생수|오일|식용유|"
    r"차씨|씨앗|모종|화분|비료|세트")


def norm(s):
    return (s or "").replace(" ", "")


def load_veg_ingredients(cur):
    rows = cur.execute(
        "select ingredient_key, name, base_unit, wholesale_price, wholesale_basis "
        "from ingredients where subcat like '농산물%' or subcat like '%채소%' "
        "or subcat like '%버섯%' or subcat like '%과일%' or subcat like '%곡물%'").fetchall()
    return rows


def core_kw(name):
    """재료명에서 핵심어. 괄호·용량 제거 후 남는 말."""
    k = re.sub(r"[\(\[].*?[\)\]]", "", name).strip()
    k = re.sub(r"\s*\d.*$", "", k).strip()
    return k or name


def main():
    dry = "--apply" not in sys.argv
    fs = json.load(io.open(FS, encoding="utf-8"))

    if not dry:
        shutil.copy2(DB, DB + ".bak-20260725-veg")

    con = sqlite3.connect(DB)
    cur = con.cursor()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    print("%-14s %8s %10s   %s" % ("재료", "지금", "식봄최저", "원산지별(국산/수입)"))
    print("-" * 78)

    n_rows = n_ing = 0
    for key, name, unit, wp_old, basis_old in load_veg_ingredients(cur):
        if unit != "kg":                       # 개/포기는 이번엔 건드리지 않는다
            continue
        kw = core_kw(name)
        cand = fs.get(kw) or fs.get(name) or []
        core = norm(kw)
        # 핵심어 포함 + 가공품 배제 + kg 환산된 것
        good = [r for r in cand
                if r.get("won_per_kg") and core in norm(r["name"]) and not BAD.search(r["name"])]
        if not good:
            print("  ! %-12s 후보 없음 (검색어 %s)" % (name, kw))
            continue

        # 이상치 컷 — 식봄은 업체경쟁이라 지금값보다 대체로 싸다.
        # 지금값의 5배를 넘으면 오매칭(마늘양파 395,375 등)이라 버린다.
        cap = (wp_old or 0) * 5
        good = [r for r in good if not cap or r["won_per_kg"] <= cap]
        if not good:
            print("  ! %-12s 후보가 전부 이상치(오매칭 의심) — 건너뜀" % name)
            continue

        # 원산지별 최저
        byo = {}
        for r in good:
            o = r.get("origin") or "미표기"
            if o not in byo or r["won_per_kg"] < byo[o]["won_per_kg"]:
                byo[o] = r
        lo = min(good, key=lambda r: r["won_per_kg"])

        summ = " · ".join("%s %s" % (o, f"{v['won_per_kg']:,}")
                          for o, v in sorted(byo.items(), key=lambda x: x[1]["won_per_kg"]))
        print("%-14s %8s %10s   %s" % (
            name, f"{wp_old or 0:,}", f"{lo['won_per_kg']:,}", summ[:44]))

        if not dry:
            cur.execute("delete from ingredient_price where ingredient_key=? and source='식봄'", (key,))
            for o, r in byo.items():
                b = "식봄 %s %s / %s원 · %skg = %s원/kg" % (
                    STAMP, r["name"], f"{r['sale_price']:,}", r["pack_kg"],
                    f"{r['won_per_kg']:,}")
                cur.execute(
                    "insert or replace into ingredient_price(ingredient_key,tier,kind,origin,"
                    "part,grade,brand,form,price,pack_kg,source,basis,is_default,checked_at) "
                    "values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (key, "도매", None, o, None, r.get("grade"), None, "식봄",
                     r["won_per_kg"], r["pack_kg"], "식봄", b, 0, STAMP))
                n_rows += 1
            # 기본값 = 식봄 최저. 단, 지금값이 이미 더 싸면 그대로 둔다(현장실거래 등).
            # 식봄이 지금보다 비싸면 덮지 않는다 — 덮으면 오히려 원가가 올라간다.
            keep = wp_old and wp_old <= lo["won_per_kg"]
            if not keep:
                cur.execute("update ingredients set wholesale_price=?, wholesale_basis=?, "
                            "updated_at=? where ingredient_key=?",
                            (lo["won_per_kg"],
                             "식봄 %s %s = %s원/kg" % (STAMP, lo["name"][:30], f"{lo['won_per_kg']:,}"),
                             STAMP, key))
        n_ing += 1

    if dry:
        print("\n※ 미리보기다. 쓰려면  python scripts/veg_apply.py --apply")
    else:
        con.commit()
        print("\n채소 %d종 · 표 %d행 반영." % (n_ing, n_rows))


main()
