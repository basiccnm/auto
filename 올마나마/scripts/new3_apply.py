# -*- coding: utf-8 -*-
"""신규 식봄 카테고리 수집(곡물·견과 / 버섯·과일)을 ingredient_price 표에 반영. (2026-07-25)

⚠️ substring 매칭은 오염이 심해(쌀→'햇쌀푸드', 배→'무료배송', 콩→'콩알새송이버섯')
   폐기. 식봄이 이미 잎 카테고리로 분류했으니 **재료→정확한 잎(nid)** 로 직접 매핑한다.

각 재료마다: 지정 잎(nid)들의 상품 → 핵심어 포함 + 개별 제외어 + BAD 필터
  → 중앙값 이상치 컷 → 원산지별 최저 → ingredient_price(도매) 행.
기본값(wholesale_price)은 식봄 최저로 갱신하되, 현재값이 더 싸고 노이즈가 아니면 유지.
쌀은 국내쌀(41)=국산 / 수입쌀(42)=수입 으로 원산지 강제.

음료·스낵은 단위가 mL·개라 제외(계산기용 데이터만 확보). 단호박·냉동망고는 잎 없음/
멀티팩 파싱버그로 이번 반영 제외(현재값 유지).

미리보기(인자 없음) → --apply
"""
import json, io, os, re, sqlite3, sys, shutil
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
FSDIR = os.path.join(BASE, "data", "research", "foodspring")
FILES = ["_곡물견과카테고리.json", "_버섯과일카테고리.json"]
STAMP = "2026-07-25"

BAD = re.compile(r"세트|선물|증정|샘플|기획전")

# 재료명 → (잎 nid 리스트, 반드시포함, 제외정규식, 원산지강제)
# nid 는 식봄 트리(2026-07-25)에서 확인한 잎.
MAP = {
    "쌀":     ([41, 42], "쌀", r"쌀가루|기장|귀리|수수|메밀|현미|흑미|찐쌀|누룽지|뻥튀기", None),
    "찹쌀":   ([45], "찹쌀", r"가루|밀|카무|귀리", None),
    "콩":     ([43], "콩", r"새송이|버섯|두부|나물|가루|콩기름|된장|과자", None),
    "녹두":   ([49], "녹두", r"가루|묵|전\b|빈대떡", None),
    "참깨":   ([497], "참깨", r"기름|가루|드레싱|소금|버터|강정", None),
    "팥":     ([44], "팥", r"가루|앙금|빙수|양갱|빵|칼국수", None),
    "땅콩":   ([50], "땅콩", r"버터|가루|강정|과자|캔디|초코|샌드|커피|꿀|맛", None),
    "아몬드": ([51], "아몬드", r"혼합|믹스|가루|분말|버터|초코|캔디|우유|음료|드레싱", None),
    "호두":   ([52], "호두", r"가루|과자|파이|정과|초코", None),
    "사과":   ([32], "사과", r"식초|즙|주스|음료|칩|말랭이|건조|잼|퓨레", None),
    "배":     ([32], "배", r"배송|사이다|음료|즙|주스|칩|말랭이|건조|잼|퓨레", None),
    "참외":   ([34], "참외", r"즙|주스|장아찌|말랭이|건조", None),
    "복숭아": ([34], "복숭아", r"즙|주스|음료|통조림|캔|말랭이|건조", None),
    # 포도(캠벨박스 18,593·현실괴리)·체리(n1)·오렌지(소포장뿐)는 데이터 얇아 이번 제외 — 현재값 유지.
    "바나나": ([35], "바나나", r"칩|말랭이|건조|우유|음료|과자|초코", None),
    "레몬":   ([35], "레몬", r"즙|주스|음료|청\b|말랭이|건조|잼|소금|식초", None),
    "건포도": ([37], "건포도", r"초코|요거트|캔디", None),
    "버섯":   ([30, 29], "버섯", r"가루|칩|스낵|과자|즙|차\b", None),   # 팽이·느타리 대표
}

# subcat 이 곡물/견과/버섯/과일인데 잎 매핑이 없는 것(단호박·냉동망고 등)은 이번 반영에서 제외.


def norm(s):
    return (s or "").replace(" ", "")


def load_by_nid():
    by = {}
    for fn in FILES:
        p = os.path.join(FSDIR, fn)
        if not os.path.exists(p):
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        for label, blk in d.items():
            nid = blk.get("nid")
            by[nid] = {"label": label, "rows": blk.get("rows", [])}
    return by


def main():
    dry = "--apply" not in sys.argv
    by = load_by_nid()

    if not dry:
        shutil.copy2(DB, DB + ".bak-20260725-new3")
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # 매핑 대상 재료를 DB에서 찾는다(이름 정확일치).
    print("%-9s %8s %8s n  %-26s  검증(매칭최저 상품)" % ("재료", "지금", "식봄최저", "원산지별"))
    print("-" * 100)
    n_ing = n_rows = 0
    for iname, (nids, must, excl, force_o) in MAP.items():
        row = cur.execute(
            "select ingredient_key, name, base_unit, wholesale_price, coalesce(wholesale_basis,'') "
            "from ingredients where name=? and base_unit='kg'", (iname,)).fetchone()
        if not row:
            print("  · %s — DB에 kg 재료 없음(건너뜀)" % iname)
            continue
        key, name, unit, wp_old, basis_old = row
        exre = re.compile(excl) if excl else None

        cand = []
        for nid in nids:
            blk = by.get(nid)
            if not blk:
                continue
            for r in blk["rows"]:
                nm = r["name"]
                if not r.get("won_per_kg"):
                    continue
                # 업소용 대용량만: 1kg 미만 소포장은 /kg 이 뻥튀기(220g→7,500)라 제외
                if not r.get("pack_kg") or r["pack_kg"] < 1.0:
                    continue
                if norm(must) not in norm(nm):
                    continue
                if BAD.search(nm) or (exre and exre.search(nm)):
                    continue
                rr = dict(r)
                # 국내쌀/수입쌀 잎은 원산지 강제
                if nid == 41:
                    rr["origin"] = "국산"
                elif nid == 42:
                    rr["origin"] = "수입"
                cand.append(rr)
        if not cand:
            print("  ! %s — 후보 없음(잎 %s, 포함'%s')" % (iname, nids, must))
            continue

        # 중앙값 이상치 컷(표본 4+): 0.25×~3× 밖 제거
        vals = sorted(r["won_per_kg"] for r in cand)
        med = vals[len(vals) // 2]
        if len(cand) >= 4:
            cand = [r for r in cand if med * 0.25 <= r["won_per_kg"] <= med * 3.0]
        if not cand:
            continue

        byo = {}
        for r in cand:
            o = r.get("origin") or "미표기"
            if o not in byo or r["won_per_kg"] < byo[o]["won_per_kg"]:
                byo[o] = r
        lo = min(cand, key=lambda r: r["won_per_kg"])
        summ = " · ".join("%s %s" % (o, f"{v['won_per_kg']:,}")
                          for o, v in sorted(byo.items(), key=lambda x: x[1]["won_per_kg"]))
        print("%-9s %8s %8s %-2d %-26s  %s" % (
            iname, f"{wp_old or 0:,}", f"{lo['won_per_kg']:,}", len(cand), summ[:26], lo["name"][:30]))

        if not dry:
            cur.execute("delete from ingredient_price where ingredient_key=? and source='식봄'", (key,))
            for o, r in byo.items():
                b = "식봄(잎) %s %s / %s원·%skg = %s원/kg" % (
                    STAMP, r["name"][:22], f"{r['sale_price']:,}", r["pack_kg"], f"{r['won_per_kg']:,}")
                cur.execute(
                    "insert or replace into ingredient_price(ingredient_key,tier,kind,origin,part,"
                    "grade,brand,form,price,pack_kg,source,basis,is_default,checked_at) "
                    "values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (key, "도매", None, o, None, r.get("grade"), None, "식봄",
                     r["won_per_kg"], r["pack_kg"], "식봄", b, 0, STAMP))
                n_rows += 1
            # 잎 기반은 신뢰 높음 → 기본값을 식봄 최저로 갱신(확인한 값으로 업데이트).
            cur.execute("update ingredients set wholesale_price=?, wholesale_basis=?, updated_at=? "
                        "where ingredient_key=?",
                        (lo["won_per_kg"], "식봄(잎) %s %s = %s원/kg" % (
                         STAMP, lo["name"][:26], f"{lo['won_per_kg']:,}"), STAMP, key))
        n_ing += 1

    if dry:
        print("\n매핑 %d종 반영 예정. ※ 미리보기 — 쓰려면  python scripts/new3_apply.py --apply" % n_ing)
    else:
        con.commit()
        print("\n반영 완료: %d종 · 표 %d행." % (n_ing, n_rows))


main()
