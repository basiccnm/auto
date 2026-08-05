# -*- coding: utf-8 -*-
"""우리 메뉴 ↔ 공식 메뉴를 **잇는 후보**를 보여준다. 2026-07-27

🔴 왜 — 공식 수집분에 가격이 있는데 이름 형식이 달라 못 붙은 것이 34건이다.
   `마가리타 피자 L` ↔ `마가리타 오리지널 라지 x 1 ( 23,500 원)` 처럼.
   이걸 이으면 **판매가가 자동으로 검증**된다.

🔴 자동으로 붙이는 것은 **가격이 완전히 같고 핵심 이름이 겹칠 때만**이다(`--apply-safe`).
   그 밖은 후보를 나란히 보여주고 사람이 고른다 — 억지로 붙이면 오매칭이 난다
   (2026-07-27: `BBQ 양념치킨 24,500` 에 1,000원짜리 소스가 붙었다).

    python scripts/menu_link_suggest.py                # 후보 보기
    python scripts/menu_link_suggest.py --apply-safe   # 가격 일치 + 이름 겹침만 반영
    python scripts/menu_link_suggest.py --set <메뉴id> "<공식 메뉴명>"
"""
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
sys.stdout.reconfigure(encoding="utf-8")

RX_SIZE = re.compile(r"\b[LMRSF]\b|라지|미디엄|레귤러|패밀리|파티|스몰|오리지널|씬|thin|"
                     r"x\s*\d+|\(\s*[\d,]+\s*원\s*\)|[\d,]+원|\d+\s*p\b|한마리|반마리|"
                     r"곱빼기|\d+인용|\d+cm|단품|세트", re.I)
RX_GEN = re.compile(r"피자|치킨|버거|초밥|도시락|떡볶이|반상|한상")


def norm(s):
    return re.sub(r"[\s·,\-_.()\[\]/™®]+", "", (s or "")).lower()


def core(s):
    return norm(RX_GEN.sub(" ", RX_SIZE.sub(" ", s or "")))


def overlap(a, b):
    """두 이름의 핵심 글자가 얼마나 겹치나 (0~1)."""
    ca, cb = core(a), core(b)
    if not ca or not cb:
        return 0.0
    sa, sb = set(ca), set(cb)
    return len(sa & sb) / max(len(sa), len(sb))


def main():
    safe = "--apply-safe" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    cur = c.cursor()

    if "--set" in sys.argv:
        i = sys.argv.index("--set")
        mid, oname = int(sys.argv[i + 1]), sys.argv[i + 2]
        m = cur.execute("SELECT brand_id, name, sell_price FROM menus WHERE id=?",
                        (mid,)).fetchone()
        o = cur.execute("SELECT name, price FROM brand_menu_official "
                        "WHERE brand_id=? AND name=?", (m["brand_id"], oname)).fetchone()
        if not o:
            print("✗ 공식 메뉴 «%s» 없음" % oname)
            return
        cur.execute("UPDATE brand_menu_official SET menu_id=? WHERE brand_id=? AND name=?",
                    (mid, m["brand_id"], oname))
        c.commit()
        print("✅ [%s] %s (%s원) ← 공식 «%s» (%s원)"
              % (mid, m["name"], format(m["sell_price"] or 0, ","), oname,
                 format(o["price"], ",")))
        if (m["sell_price"] or 0) != o["price"]:
            print("   ⚠️ 판매가가 다르다 — 공식 값으로 고칠지 판단할 것")
        return

    linked = 0
    # ⚠️ 바깥 루프는 반드시 `.fetchall()` — 안에서 같은 커서를 또 쓰면 **첫 행에서 끊긴다**
    #    (CLAUDE.md 커서 재사용 경고. 2026-07-27 이 스크립트가 실제로 그래서 출력이 비었다)
    brands = cur.execute("""SELECT b.id, b.name FROM brands b WHERE b.published=1
                            AND (SELECT COUNT(*) FROM brand_menu_official o
                                  WHERE o.brand_id=b.id AND o.price>0) > 0
                            ORDER BY b.frcs_cnt DESC""").fetchall()
    for b in brands:
        offs = [dict(r) for r in cur.execute(
            "SELECT name, price, menu_id FROM brand_menu_official "
            "WHERE brand_id=? AND price>0", (b["id"],))]
        ours = [dict(r) for r in cur.execute(
            "SELECT id, name, sell_price sp FROM menus WHERE brand_id=? ORDER BY id", (b["id"],))]
        todo = [x for x in ours
                if not any(o["menu_id"] == x["id"] for o in offs)]
        if not todo:
            continue
        print("=" * 100)
        print("● %s  (공식 %d개 · 못 이은 우리 메뉴 %d개)" % (b["name"], len(offs), len(todo)))
        print("=" * 100)
        for x in todo:
            sp = x["sp"] or 0
            cands = sorted(offs, key=lambda o: (abs(o["price"] - sp), -overlap(x["name"], o["name"])))
            print("   [%s] %-22s 우리 %7s원" % (x["id"], x["name"][:22], format(sp, ",")))
            auto = None
            for o in cands[:4]:
                ov = overlap(x["name"], o["name"])
                same = o["price"] == sp
                tag = "★가격일치" if same else ""
                if same and ov >= 0.55 and not auto:
                    auto = o
                    tag += " ←자동연결"
                print("        %7s원 겹침%3d%%  %-42s %s"
                      % (format(o["price"], ","), round(ov * 100), o["name"][:42], tag))
            if auto and safe:
                cur.execute("UPDATE brand_menu_official SET menu_id=? "
                            "WHERE brand_id=? AND name=?", (x["id"], b["id"], auto["name"]))
                linked += 1
        print()

    if safe:
        c.commit()
        print("✅ 자동 연결 %d건 (가격 일치 + 이름 겹침 55%% 이상)" % linked)
    else:
        print("← 미반영. `--apply-safe` 로 «★가격일치 ←자동연결» 만 반영, 나머지는 `--set` 으로")


if __name__ == "__main__":
    main()
