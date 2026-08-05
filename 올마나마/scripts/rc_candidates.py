# -*- coding: utf-8 -*-
"""대표메뉴 **후보**를 브랜드 메뉴판 빈도에서 뽑는다 — 읽기 전용. 2026-07-31 신설

    python scripts/rc_candidates.py              # 상위 후보
    python scripts/rc_candidates.py --all        # 전부
    python scripts/rc_candidates.py --cat 분식    # 그 업종만

왜 빈도인가
----------
여러 브랜드가 같은 이름으로 파는 메뉴 = **시장에서 표준으로 통하는 메뉴**다.
「뿌링클」처럼 한 곳에만 있는 시그니처는 자동으로 걸러진다 — 대표메뉴로 쓸 수 없다.
근거는 우리가 이미 모아둔 브랜드 메뉴판 7,346줄이다.

⛔ 이 목록이 곧 확정은 아니다. **관리자 페이지에서 사람이 고른다.**
   빈도만 보면 카페 음료·사이드가 위를 다 차지한다(아메리카노 13곳) — 집에서
   «해먹는» 메뉴가 아니면 계산기로 쓸모가 적다.
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")
import brand_menu_store as store                                    # noqa: E402

# 🔴 옛 범용 수집기가 남긴 UI 글자 — 메뉴가 아니다(2026-07-31 15곳 정리했지만 잔재가 남았다)
JUNK = re.compile(r"로그아웃|로그인|회원|이메일|무단수집|커뮤니티|인스타|페이스북|블로그|"
                  r"프로필|공지|이벤트당첨|고객센터|가맹문의|채용|오시는길|매장찾기|더보기|"
                  r"이용약관|개인정보|사이트맵|바로가기|홈페이지|주문하기|배달주문")
# 완제품을 사서 붓기만 하는 것 — 계산기로 만들 게 없다
BUYONLY = re.compile(r"^(콜라|사이다|스프라이트|환타|제로콜라|생수|아이스티|"
                     r"코카콜라|펩시|웰치스|맥주|소주|음료수?)")


def scan(c, min_brands=3):
    def norm(s):
        s = re.sub(r"\([^)]*\)", "", s or "")
        s = re.sub(r"\[[^\]]*\]", "", s)
        s = re.sub(r"[0-9]+\s*(인분|개|조각|pcs|p|ml|L|g|kg)\b", "", s, flags=re.I)
        s = re.sub(r"\s*(단품|세트|신메뉴|추천|BEST|NEW)\s*$", "", s, flags=re.I)
        return re.sub(r"\s+", "", s).strip()

    hit = collections.defaultdict(lambda: {"brands": set(), "cats": collections.Counter(),
                                           "raw": collections.Counter(), "prices": []})
    for r in c.execute("""SELECT o.name, o.price, b.name bn, cc.name cat
                          FROM brand_menu_official o
                          JOIN brands b ON b.id=o.brand_id
                          JOIN categories cc ON cc.id=b.category_id
                          WHERE b.published=1"""):
        n = norm(r["name"])
        if not (2 <= len(n) <= 14) or JUNK.search(n) or BUYONLY.match(n):
            continue
        d = hit[n]
        d["brands"].add(r["bn"])
        d["cats"][r["cat"]] += 1
        d["raw"][r["name"]] += 1
        if r["price"]:
            d["prices"].append(r["price"])

    out = []
    for n, d in hit.items():
        if len(d["brands"]) < min_brands:
            continue
        pr = sorted(d["prices"])
        out.append({
            "name": n,
            "n_brand": len(d["brands"]),
            "cat": d["cats"].most_common(1)[0][0],
            "brands": sorted(d["brands"]),
            "mid_price": pr[len(pr) // 2] if pr else None,
            "sample": d["raw"].most_common(1)[0][0],
        })
    out.sort(key=lambda x: (-x["n_brand"], x["name"]))
    return out


def main():
    c = store.connect()
    rows = scan(c)
    only = None
    if "--cat" in sys.argv:
        only = sys.argv[sys.argv.index("--cat") + 1]
        rows = [r for r in rows if only in r["cat"]]
    lim = len(rows) if ("--all" in sys.argv or only) else 50

    print("=" * 72)
    print("대표메뉴 후보 %d종 (3개 브랜드 이상에서 같은 이름으로 판다)%s"
          % (len(rows), " · %s" % only if only else ""))
    print("=" * 72)
    cur = None
    for r in sorted(rows[:lim], key=lambda x: (x["cat"], -x["n_brand"])):
        if r["cat"] != cur:
            cur = r["cat"]
            print("\n[%s]" % cur)
        print("   %-16s %2d곳  중앙가 %-7s  예: %s"
              % (r["name"], r["n_brand"],
                 ("%s원" % format(int(r["mid_price"]), ",")) if r["mid_price"] else "-",
                 r["sample"][:26]))
    if lim < len(rows):
        print("\n(상위 %d개만 — 전부 보려면 --all)" % lim)


if __name__ == "__main__":
    main()
