# -*- coding: utf-8 -*-
"""우리 육류 재료에 식봄 원산지 티어(수입/육우/한우·국산/수입) 가격을 ingredient_price 에 추가. (2026-07-25)

카테고리 기반(_정육전체.json). 부위×원산지 잎(원물+세절)에서 교차종·가공·소포장·이상치 필터 후 최저.
**추가(additive)** — 기본값 wholesale_price 는 안 건드린다(미트박스 등 유지). 계산기 원산지선택용 옵션 행만 넣는다.
미리보기(인자없음) → --apply
"""
import json, io, os, re, sqlite3, sys, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
CACHE = os.path.join(BASE, "data", "research", "foodspring", "_정육전체.json")
STAMP = "2026-07-25"
BAD = re.compile(r"세트|선물|샘플|양념|훈제|햄|소시지|만두|까스|너겟|볶음밥|찌개|스프|육수|다시|"
                 r"엑기스|우거지|곰탕|사골탕|설렁탕|국밥|탕수?육|꿔바로우|샤브|지방|우지|기름|"
                 r"염통|무침|육포|장조림|불고기양념|떡갈비")
BLOCK = {"돼지": re.compile(r"소[고기]|우[육양]|육우|한우|쇠고기"),
         "소": re.compile(r"돼지|돈[육민등항목삼갈사]|포크"),
         "닭": re.compile(r"돼지|소고기|우육")}
PLAUS = {"돼지": (1500, 20000), "소": (3000, 90000), "닭": (2000, 15000)}

PORK = {
 "삼겹살": {"국산": [520, 530], "수입": [548, 564]}, "앞다리": {"국산": [511, 527], "수입": [560, 572]},
 "등심": {"국산": [509, 529], "수입": [559, 576]}, "목심": {"국산": [524, 537], "수입": [552, 574]},
 "다짐육": {"국산": [528], "수입": [578]}, "항정살": {"국산": [514, 531], "수입": [553, 568]},
 "갈비": {"국산": [523, 535], "수입": [558, 567]}, "돈등뼈": {"국산": [513, 536], "수입": [557, 577]},
 "족발": {"국산": [543], "수입": [582]}}
BEEF = {
 "다짐육": {"수입": [610], "육우": [642, 665], "한우": [690, 713]},
 "등심": {"수입": [596, 627], "육우": [654, 677], "한우": [702, 725]},
 "양지": {"수입": [603, 617], "육우": [645, 668], "한우": [693, 716]},
 "갈비": {"수입": [588, 618], "육우": [653, 676], "한우": [701, 724]},
 "차돌박이": {"수입": [599, 611], "육우": [648, 671], "한우": [696, 719]},
 "불고기용": {"수입": [632], "육우": [681], "한우": [729]},
 "사골": {"육우": [639, 662], "한우": [687, 710]}, "잡뼈": {"수입": [630], "육우": [640, 663], "한우": [688, 711]},
 "우족": {"수입": [607], "육우": [637, 660], "한우": [685, 708]}}
CHICKEN = {
 "가슴살": {"국산": [740], "수입": [758]}, "다리살": {"국산": [741], "수입": [760]},
 "발": {"국산": [742], "수입": [762]}, "목살": {"국산": [746]},
 "절단닭": {"국산": [745], "수입": [759]}, "통닭": {"국산": [736], "수입": [756, 755]}}

# 우리 재료명 → (종, 부위)
ITEM = {
 "소고기 다짐육": ("소", "다짐육"), "소다짐육": ("소", "다짐육"), "소고기 등심": ("소", "등심"),
 "소고기 양지": ("소", "양지"), "우삼겹": ("소", "양지"), "차돌박이": ("소", "차돌박이"),
 "소불고기용 쇠고기": ("소", "불고기용"), "소고기 큐브스테이크": ("소", "불고기용"),
 "한우 갈비": ("소", "갈비"), "사골": ("소", "사골"), "잡뼈": ("소", "잡뼈"), "우족": ("소", "우족"),
 "수입 삼겹살": ("돼지", "삼겹살"), "돼지 등심": ("돼지", "등심"), "돈까스용 등심": ("돼지", "등심"),
 "탕수돈육등심": ("돼지", "등심"), "등심돈육": ("돼지", "등심"), "오돌뼈용등심살": ("돼지", "등심"),
 "제육용 돼지 앞다리살": ("돼지", "앞다리"), "전지돈육": ("돼지", "앞다리"),
 "돼지고기 다짐육": ("돼지", "다짐육"), "돈육다짐만두소": ("돼지", "다짐육"), "라이스페이퍼만두돈육": ("돼지", "다짐육"),
 "항정살": ("돼지", "항정살"), "감자탕돈뼈": ("돼지", "돈등뼈"), "족발 생육": ("돼지", "족발"), "돈족/머리고기": ("돼지", "족발"),
 "닭가슴살": ("닭", "가슴살"), "닭다리살 정육": ("닭", "다리살"), "닭발": ("닭", "발"), "무뼈닭발": ("닭", "발"),
 "닭목살": ("닭", "목살"), "절단닭 10호": ("닭", "절단닭"), "닭 콤보육": ("닭", "절단닭"),
 "태국산 조각 닭정육 12kg": ("닭", "절단닭"), "통닭 8호": ("닭", "통닭"), "생닭(치킨용)": ("닭", "통닭"),
}
MAPS = {"돼지": PORK, "소": BEEF, "닭": CHICKEN}
c = json.load(io.open(CACHE, encoding="utf-8"))


def cutmin(nids, sp):
    lo, hi = PLAUS[sp]; blk = BLOCK[sp]; cand = []
    for nid in nids:
        for r in c.get(str(nid), {}).get("rows", []):
            w = r.get("won_per_kg"); nm = r["name"]
            if not w or not r.get("pack_kg") or r["pack_kg"] < 1: continue
            if BAD.search(nm) or blk.search(nm) or not (lo <= w <= hi): continue
            cand.append((w, r))
    if not cand: return None
    # 중앙값 트림 후 최저 — 여러 통계 중 garbage 가 가장 적었다(2026-07-25 검증).
    # 저측 파싱오류·초고측 소포장을 함께 눌러 방어 가능한 대표 최저를 준다.
    # (한계: 진짜 싼 대용량이 lone-low면 살짝 높게 나올 수 있음. 추가옵션 행이라 무해)
    ws = sorted(x[0] for x in cand); med = ws[len(ws) // 2]
    trimmed = [x for x in cand if med * 0.4 <= x[0] <= med * 2.5]
    return min(trimmed, key=lambda x: x[0])[1] if trimmed else min(cand, key=lambda x: x[0])[1]


def main():
    dry = "--apply" not in sys.argv
    if not dry:
        shutil.copy2(DB, DB + ".bak-20260725-meatorigin")
    con = sqlite3.connect(DB); cur = con.cursor()
    n_ing = n_row = 0
    print("%-18s %-6s %s" % ("재료", "부위", "식봄 원산지 티어(원/kg)"))
    print("-" * 70)
    for iname, (sp, cut) in ITEM.items():
        row = cur.execute("select ingredient_key from ingredients where name=?", (iname,)).fetchone()
        if not row:
            continue
        key = row[0]
        origins = MAPS[sp].get(cut, {})
        got = {}
        for o, nids in origins.items():
            r = cutmin(nids, sp)
            if r:
                got[o] = r
        if not got:
            print("%-18s %-6s (식봄 데이터 없음 — 건너뜀)" % (iname[:18], cut)); continue
        summ = " · ".join("%s %s" % (o, f"{r['won_per_kg']:,}") for o, r in got.items())
        print("%-18s %-6s %s" % (iname[:18], cut, summ))
        if not dry:
            cur.execute("delete from ingredient_price where ingredient_key=? and source='식봄정육'", (key,))
            for o, r in got.items():
                b = "식봄정육(카테고리) %s %s / %s원·%skg = %s원/kg" % (
                    STAMP, r["name"][:22], f"{r['sale_price']:,}", r["pack_kg"], f"{r['won_per_kg']:,}")
                cur.execute("insert or replace into ingredient_price(ingredient_key,tier,kind,origin,part,"
                            "grade,brand,form,price,pack_kg,source,basis,is_default,checked_at) "
                            "values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (key, "도매", None, o, cut, r.get("grade"), None, None,
                             r["won_per_kg"], r["pack_kg"], "식봄정육", b, 0, STAMP))
                n_row += 1
        n_ing += 1
    if dry:
        print("\n※ 미리보기 %d종. 쓰려면 --apply" % n_ing)
    else:
        con.commit()
        print("\n반영 완료: %d종 · 원산지티어 %d행 추가(기본값 미변경)." % (n_ing, n_row))


main()
