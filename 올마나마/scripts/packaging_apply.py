# -*- coding: utf-8 -*-
"""배달 포장재를 재료로 추가한다. (2026-07-25) — 배달 계산기 원가 항목.

포장재는 kg이 아니라 **개당**이다. 상품명에서 입수(N개입/N매/NP/N개)를 파싱해
개당 단가(원/개)를 낸다. 대표값 = 중앙값(광고·특가·대용량 안 탐).

소스 = data/research/foodspring/_포장카테고리.json
단위 = base_unit '개', subcat '포장/일회용품'
"""
import json, io, os, re, sqlite3, sys, shutil

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
PK = os.path.join(BASE, "data", "research", "foodspring", "_포장카테고리.json")
STAMP = "2026-07-25"

# 배달에 실제 쓰는 포장재 → (식봄 잎 라벨, 재료키, 재료명)
ADD = [
    ("포장_일회용그릇",  "pkg_bowl",     "배달용기(그릇)"),
    ("포장_일회용도시락", "pkg_lunch",    "배달 도시락용기"),
    ("포장_기타포장용기", "pkg_lid",      "용기 뚜껑"),
    ("포장_일회용컵",   "pkg_cup",      "일회용 컵"),
    ("포장_숟가락",    "pkg_spoon",    "일회용 숟가락"),
    ("포장_젓가락",    "pkg_chopstick", "일회용 젓가락"),
    ("포장_빨대",     "pkg_straw",    "빨대"),
    ("포장_비닐봉투",   "pkg_bag",      "비닐봉투"),
    ("포장_종이봉투",   "pkg_paperbag", "종이봉투"),
    ("포장_비닐장갑",   "pkg_glove",    "위생장갑"),
]

# 입수 파싱: "100개입" "100매" "10P" "1통750개" "50개" "200입"
CNT = re.compile(r"(\d[\d,]*)\s*(?:개입|매입|매|입|개|P\b|EA|장)", re.I)
BAD = re.compile(r"세트|증정|샘플|단독구매불가|포스터|박판지|드라이아이스")


def pieces(name):
    n = name.replace(",", "")
    cnts = [int(x.replace(",", "")) for x in CNT.findall(n)]
    cnts = [c for c in cnts if 1 <= c <= 5000]
    return max(cnts) if cnts else None      # 총 입수 = 가장 큰 수(1통750개 → 750)


def main():
    dry = "--apply" not in sys.argv
    pk = json.load(io.open(PK, encoding="utf-8"))
    if not dry:
        shutil.copy2(DB, DB + ".bak-20260725-packaging")
    con = sqlite3.connect(DB)
    cur = con.cursor()

    print("%-18s %8s %8s %8s  n  %s" % ("재료", "최저", "중앙", "최고", "근거"))
    print("-" * 74)
    n_ing = 0
    for leaf, key, name in ADD:
        items = pk.get(leaf) or []
        per = []
        for r in items:
            nm = r["name"]
            if BAD.search(nm):
                continue
            sp = r.get("sale_price")
            cnt = pieces(nm)
            if sp and cnt:
                pc = round(sp / cnt)
                if 1 <= pc <= 2000:           # 개당 1~2000원 벗어나면 파싱오류
                    per.append((pc, nm))
        if not per:
            print("  ! %s — 파싱 0" % name); continue
        per.sort()
        vals = [p for p, _ in per]
        med = vals[len(vals) // 2]
        lo, hi = vals[0], vals[-1]
        best = per[len(per) // 2][1]
        print("%-18s %8s %8s %8s %3d  %s" % (name, f"{lo:,}", f"{med:,}", f"{hi:,}",
                                             len(per), best[:30]))
        if not dry:
            basis = "식봄 포장 %s 개당 중앙값 %s원 (범위 %s~%s, n=%d) / %s" % (
                STAMP, f"{med:,}", f"{lo:,}", f"{hi:,}", len(per), best[:30])
            cur.execute("insert or replace into ingredients(ingredient_key, name, class, type, "
                        "subcat, base_unit, wholesale_price, manual_price, wholesale_basis, "
                        "is_retail, markup_factor, updated_at) "
                        "values(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (key, name, "가공품", "manual", "포장/일회용품", "개",
                         med, med, basis, 0, 1.0, STAMP))
        n_ing += 1

    if dry:
        print("\n※ 미리보기. 쓰려면  python scripts/packaging_apply.py --apply")
    else:
        con.commit()
        print("\n포장재 %d종 추가." % n_ing)


main()
