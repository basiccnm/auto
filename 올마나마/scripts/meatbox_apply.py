# -*- coding: utf-8 -*-
"""미트박스 도매값을 ingredients 에 반영한다. (2026-07-25)

정책 (오늘 확정):
  도매   = 미트박스 **원물(대량 박스)** — 없으면 식자재왕몰 → 오늘얼마
  도소매 = 미트박스 낱개·육마트(1kg)     ← 아직 컬럼이 없어 이번엔 안 넣는다
  소매   = 쿠팡 로켓 → 쿠팡 일반 → 외부  ← 별도 작업

대량조건(최소 N박스) 상품도 도매 후보에 넣는다 — 도매는 원래 대량으로 받는 자리다.
조건 문구는 근거에 그대로 남긴다.

그룹 키는 `(축종·원산지)(부위)(등급·브랜드)`. **축종을 빼면 소·돼지가 같은 '미국' 칸에 섞인다.**
"""
import json, io, os, sqlite3, sys, shutil, collections
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "research", "meatbox", "_전량.json")
STAMP = "2026-07-25"
LABEL = "미트박스"          # 육류 도매 기준 소스. 거래처 상호 아님(플랫폼)

DROP_PARTS = {"잡육", "지방", "지방(A)", "지방돈피/돼지껍데기", "돈피/돼지껍데기",
              # 반골 계열 제외 — 꼬리를 뺀 등뼈라 소꼬리도 아니고 사골·잡뼈와도 다르다.
              # 최저가(1,000원)라 그냥 두면 뼈류 최저가를 계속 가로챈다.
              "반골(꼬리제외)", "알꼬리(반골제외)", "꼬리반골"}
BEEF_KINDS = {"한우암소", "한우거세", "한우수소", "육우암소", "육우거세", "수입소"}

# 기존 재료 → (후보 부위, 가공방법)
UPDATE = [
    ("beef_slices",     "우삼겹",           ["삼겹양지", "차돌양지"], "세절&분쇄"),
    ("beef_stew",       "소고기 양지",       ["삼겹양지", "차돌양지", "양지"], "원물"),
    ("x_chadol",        "차돌박이",          ["차돌박이"], "원물"),
    ("beef_patty",      "소고기 다짐육",      ["분쇄육"], "원물"),
    ("x_ffd92fa2a9",    "소다짐육",          ["분쇄육"], "원물"),
    ("beef_bulgogi",    "소불고기용 쇠고기",   ["앞다리/전각", "알전각/볼라전각", "설도", "우둔"], "원물"),
    ("beef_cube_steak", "소고기 큐브스테이크",  ["알목심"], "원물"),
    # ⚠️ 등심은 수입소로 한정한다. 전 축종을 열면 한우 3등급(28,000)이 최저로 잡히는데,
    #    이 재료는 origin=수입산이라 국산으로 바뀌면 재료 성격 자체가 달라진다.
    ("kv_4401",         "소고기 등심",        ["등심"], "원물"),
]
LOIN_KINDS = {"수입소"}

# 신설 재료 — 뼈는 국산을 쓴다(대표 확인). 사골육수베이스만 있고 뼈 원물이 없었다.
NEW = [
    ("beef_bone_sagol", "사골",   ["사골"], "원물", "국산"),
    ("beef_bone_misc",  "잡뼈",   ["잡뼈", "갈비잡뼈"], "원물", "국산"),
    ("beef_bone_foot",  "우족",   ["우족"], "원물", "국산"),
    # ⚠️ '반골(꼬리제외)'는 꼬리가 아니라 꼬리를 뺀 등뼈다(1,000원). 섞으면 소꼬리가 아니게 된다.
    ("beef_oxtail",     "소꼬리", ["꼬리"], "원물", "국산"),
]
KOR_KINDS = {"한우암소", "한우거세", "한우수소", "육우암소", "육우거세"}


def grade(name):
    p = (name or "").split(" - ")
    if len(p) < 2:
        return None
    last = p[-1].strip()
    return None if ("|" in last or not last) else last


def best_of(rows, parts, proc, kinds):
    c = [r for r in rows if r.get("부위") in parts and r.get("가공방법") == proc
         and r.get("축종") in kinds and r.get("원per_kg")
         and r.get("부위") not in DROP_PARTS]
    if not c:
        return None, 0
    c.sort(key=lambda r: r["원per_kg"])
    return c[0], len(c)


def basis(r):
    s = "%s %s (%s·%s)(%s)(%s·%s) — %s / %s" % (
        LABEL, STAMP, r.get("축종"), r.get("원산지"), r.get("부위"),
        grade(r.get("상품명")) or "등급없음", r.get("브랜드") or "-",
        r.get("상품명"), r.get("가격표기") or "")
    if r.get("총중량kg"):
        s += " · 총 %skg" % r["총중량kg"]
    s += " = %s원/kg" % f"{r['원per_kg']:,}"
    if r.get("대량상품"):
        s += " ⚠️대량조건: %s" % (r.get("대량조건") or "최소수량 있음")
    return s


def main():
    dry = "--apply" not in sys.argv
    rows = json.load(io.open(SRC, encoding="utf-8"))

    if not dry:
        bak = DB + ".bak-20260725-meatbox-apply"
        shutil.copy2(DB, bak)
        print("백업:", os.path.basename(bak), "\n")

    c = sqlite3.connect(DB)
    cur = c.cursor()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    print("%-20s %10s %10s %8s   %s" % ("재료", "전", "후", "변화", "근거 키"))
    print("-" * 108)
    for key, name, parts, proc in UPDATE:
        r, n = best_of(rows, parts, proc, LOIN_KINDS if key == "kv_4401" else BEEF_KINDS)
        if not r:
            print("  ! %s — 후보 없음" % name)
            continue
        old = cur.execute("select name, base_unit, wholesale_price, manual_price "
                          "from ingredients where ingredient_key=?", (key,)).fetchone()
        if not old:
            print("  ! %s(%s) — DB에 없는 재료키" % (name, key))
            continue
        dbname, unit, wp_old, mp = old
        if unit != "kg":
            print("  ! %s — base_unit 이 '%s' 다. kg 단가 못 넣는다" % (dbname, unit))
            continue
        new = r["원per_kg"]
        pct = (new - (wp_old or 0)) / (wp_old or 1) * 100
        print("%-20s %10s %10s %+7.0f%%   (%s·%s)(%s)(%s) 후보%d" % (
            dbname, f"{wp_old or 0:,}", f"{new:,}", pct,
            r.get("축종"), r.get("원산지"), r.get("부위"),
            grade(r.get("상품명")) or "-", n))
        if not dry:
            cur.execute("update ingredients set wholesale_price=?, wholesale_basis=?, "
                        "origin=?, updated_at=? where ingredient_key=?",
                        (new, basis(r), r.get("원산지"), STAMP, key))
            # retail_price 는 NOT NULL 이다. 이번 반영은 도매 축이라 소매는 기존 값을 그대로 싣는다.
            cur.execute("insert into price_history(ingredient_key, price_date, retail_price,"
                        " source, created_at, wholesale_price) values(?,?,?,?,?,?)",
                        (key, STAMP, mp or 0, "meatbox", now, new))

    print("\n[신설]")
    for key, name, parts, proc, origin in NEW:
        r, n = best_of(rows, parts, proc, KOR_KINDS)
        if not r:
            print("  ! %s — 후보 없음" % name)
            continue
        exists = cur.execute("select 1 from ingredients where ingredient_key=? or name=?",
                             (key, name)).fetchone()
        if exists:
            print("  ! %s — 이미 있다. 건너뛴다" % name)
            continue
        print("%-20s %10s %10s %8s   (%s·%s)(%s) 후보%d" % (
            name, "-", f"{r['원per_kg']:,}", "신설",
            r.get("축종"), r.get("원산지"), r.get("부위"), n))
        if not dry:
            cur.execute(
                "insert into ingredients(ingredient_key, name, class, type, subcat, "
                "base_unit, wholesale_price, wholesale_basis, origin, is_retail, "
                "markup_factor, updated_at) values(?,?,?,?,?,?,?,?,?,?,?,?)",
                (key, name, "농축산물", "manual", "축산물/소", "kg",
                 r["원per_kg"], basis(r), origin, 0, 1.0, STAMP))
            cur.execute("insert into price_history(ingredient_key, price_date, retail_price,"
                        " source, created_at, wholesale_price) values(?,?,?,?,?,?)",
                        (key, STAMP, 0, "meatbox", now, r["원per_kg"]))

    if dry:
        print("\n※ 미리보기다. 쓰려면  python scripts/meatbox_apply.py --apply")
    else:
        c.commit()
        print("\n반영 완료.")


main()
