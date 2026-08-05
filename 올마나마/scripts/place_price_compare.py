# -*- coding: utf-8 -*-
"""네이버 플레이스에서 읽은 메뉴판을 **우리 DB 판매가와 대조**한다. 2026-07-27

`place_menu_emu.py` 가 만든 `data/place_menu/<브랜드>_menu.txt` 를 읽는다.
형식은 탭 구분: 메뉴명 \t 가격 \t 구성설명

🔴 왜 플레이스인가 — 브랜드 홈페이지 49곳을 훑었더니 **가격을 공개하는 곳이 15곳뿐**이었다.
   플레이스 메뉴판은 **홀 매장가**라 배달앱(배달비 포함)보다 우리 기준에 맞는다.
   대표 확인: *"프랜차이즈는 가격이 틀리면 안돼 … 대체로는 거의 다 비슷하잖아"*
   → 지역차는 예외이므로 **검색 첫 매장 값을 그대로 쓴다.** 여러 매장을 볼 필요 없다.

⛔ 여기서 바로 DB 를 고치지 않는다. 대조 결과만 보여주고 반영은 사람이 고른 것만.

    python scripts/place_price_compare.py            # 전체
    python scripts/place_price_compare.py 맘스터치
"""
import io
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
SRC = os.path.join(BASE, "data", "place_menu")


def norm(s):
    """이름 비교용 — 공백·괄호·꼬리표를 턴다."""
    s = re.sub(r"\((?:행사|NEW|신메뉴)\)", "", s)
    s = re.sub(r"\s+|[·,]", "", s)
    return s.lower()


def main():
    global STRICT, n_part
    STRICT = "--strict" in sys.argv
    n_part = 0
    only = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    if not os.path.isdir(SRC):
        print("수집분이 없다 — 먼저 place_menu_emu.py 를 돌려라")
        return

    files = {f[:-len("_menu.txt")]: os.path.join(SRC, f)
             for f in os.listdir(SRC) if f.endswith("_menu.txt")}
    n_hit = n_diff = n_miss = 0
    for r in c.execute("""SELECT b.id, b.name FROM brands b WHERE b.published=1
                          ORDER BY b.frcs_cnt DESC"""):
        key = re.sub(r"[^0-9A-Za-z가-힣]+", "", r["name"])
        if key not in files:
            continue
        if only and only not in r["name"]:
            continue
        place = {}
        for line in io.open(files[key], encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2 and p[1].isdigit():
                place[norm(p[0])] = (p[0], int(p[1]), p[2] if len(p) > 2 else "")
        menus = c.execute("SELECT id, name, sell_price FROM menus WHERE brand_id=?",
                          (r["id"],)).fetchall()
        if not menus:
            continue
        print("\n● %s  (플레이스 %d개)" % (r["name"], len(place)))
        for m in menus:
            k = norm(m["name"])
            hit = place.get(k)
            exact = hit is not None
            if not hit and not STRICT:       # 부분 일치도 본다(--strict 면 안 본다)
                for pk, pv in place.items():
                    if k and (k in pk or pk in k):
                        hit = pv
                        break
            if hit and not exact:
                # 🔴 부분 일치는 다른 메뉴를 물 수 있다 (2026-07-27).
                #    «리아 불고기 단품»(5,100)이 «리아»(9,900) 세트를 물었다.
                #    표시는 하되 반영 후보에서 뺀다.
                print("   ~ %-22s 우리 %7s ≈ 플레이스 %7s  «%s»  ← 부분일치, 확인 필요"
                      % (m["name"][:22], format(m["sell_price"] or 0, ","),
                         format(hit[1], ","), hit[0][:22]))
                n_part += 1
                continue
            if not hit:
                n_miss += 1
                print("   ⚪ %-22s 우리 %7s  — 플레이스에 같은 이름이 없다"
                      % (m["name"][:22], format(m["sell_price"] or 0, ",")))
            elif hit[1] == m["sell_price"]:
                n_hit += 1
                print("   ✅ %-22s %7s  일치" % (m["name"][:22], format(hit[1], ",")))
            else:
                n_diff += 1
                print("   ❗ %-22s 우리 %7s → 플레이스 %7s  «%s»"
                      % (m["name"][:22], format(m["sell_price"] or 0, ","),
                         format(hit[1], ","), hit[0][:24]))
    print("\n%s\n✅ 일치 %d · ❗ 값 다름 %d · ~ 부분일치 %d · ⚪ 이름 없음 %d"
          % ("=" * 70, n_hit, n_diff, n_part, n_miss))
    print("⚠️ 반영은 사람이 고른 것만. 세트/단품·사이즈가 섞이니 이름을 눈으로 확인할 것")


if __name__ == "__main__":
    main()
