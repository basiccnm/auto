# -*- coding: utf-8 -*-
"""쿠팡 파트너스 API **단독 테스트·확인용 CLI**. (공통모듈 원본 · 2026-07-31)

    python coupang_cli.py "동치미 냉면육수"
    python coupang_cli.py "생크림 500ml" "휘핑크림 200ml"     # 여러 개 (1.3초 간격)
    python coupang_cli.py --max 2500 "고춧가루"               # 용량 상한(g)
    python coupang_cli.py --deeplink "https://www.coupang.com/vp/products/1234567"

⚠️ 이건 **확인용**이다. 프로젝트에서 쓸 때는 `coupang_api.py` 를 복사해 가고,
   저장 형식·경로는 그 프로젝트가 정한다(이 파일은 아무것도 저장하지 않는다).

🔴 여러 키워드를 줄 때 **1.3초 간격**을 둔다(분당 46회). 분당 50회 제한이고,
   2026-07-27 에 3초 간격으로 몰아 읽다 11건에서 차단당한 적이 있다.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from coupang_api import (DISCLOSURE, deeplink, is_fresh, items, keys,  # noqa: E402
                         ok, parse_pack, search)


def won(n):
    return format(int(n or 0), ",")


def show(kw, ak, sk, maxg):
    try:
        body = search(kw, ak, sk)
    except Exception as e:                     # noqa: BLE001
        print("✗ %-20s 호출 실패: %s" % (kw[:20], str(e)[:70]))
        return
    if not ok(body):
        # 🔴 실패해도 HTTP 200 이다 — rCode 를 봐야 «0건 정상» 오독을 안 한다
        print("✗ %-20s rCode=%s %s" % (kw[:20], body.get("rCode"),
                                       str(body.get("rMessage"))[:60]))
        return

    rows = []
    for it in items(body):
        nm = it.get("productName") or ""
        pr = it.get("productPrice") or 0
        g, u = parse_pack(nm)
        rows.append((pr, g, u, nm, it.get("isRocket"), it.get("productUrl")))
    rows.sort(key=lambda x: x[0])

    print("=" * 96)
    print("● %s — %d건" % (kw, len(rows)))
    print("=" * 96)
    n_nosize = 0
    for i, (pr, g, u, nm, rocket, _url) in enumerate(rows, 1):
        if g and u == "g" and maxg and g > maxg:
            n_nosize += 1
            continue
        unit = ""
        if g and u == "g" and g > 0:
            unit = "%9s원/kg" % won(round(pr / (g / 1000.0)))
        elif g:
            unit = "%9s원/%s" % (won(round(pr / g)), u)
        else:
            n_nosize += 1
        badge = "로켓프레시" if is_fresh(nm) else ("로켓" if rocket else "일반")
        print("  %2d) %9s원 %8s %s %-6s %s"
              % (i, won(pr), ("%g%s" % (g, u)) if g else "용량?", unit or " " * 12,
                 badge, nm[:48]))
    if n_nosize:
        print("  (용량을 상품명에서 못 읽었거나 상한 초과 %d건 — **추측하지 않는다**)" % n_nosize)
    print()


def main():
    argv = sys.argv[1:]
    maxg, skip = None, set()
    if "--max" in argv:
        i = argv.index("--max")
        maxg = float(argv[i + 1])
        skip.add(argv[i + 1])

    ak, sk = keys()
    if not ak or not sk:
        print("🔴 키가 없다 — `.env` 에 COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 를 넣거나")
        print("   환경변수로 준다. (`.env` 는 현재 폴더에서 위로 5단계까지 찾는다)")
        return 1

    if "--deeplink" in argv:
        urls = [a for a in argv[argv.index("--deeplink") + 1:] if not a.startswith("--")]
        if not urls:
            print("사용법: --deeplink <쿠팡 상품 주소> [주소2 …]")
            return 1
        r = deeplink(urls, ak, sk)
        if not ok(r):
            print("✗ rCode=%s %s" % (r.get("rCode"), str(r.get("rMessage"))[:70]))
            return 1
        for d in (r.get("data") or []):
            print("  %s\n  → %s\n" % (d.get("originalUrl"), d.get("shortenUrl")))
        print(DISCLOSURE)
        return 0

    kws = [a for a in argv if not a.startswith("--") and a not in skip]
    if not kws:
        print(__doc__)
        return 1
    # 간격은 `coupang_api._throttle()` 이 알아서 지킨다(분당 46회). 여기서 또 재우지 않는다.
    for kw in kws:
        show(kw, ak, sk, maxg)
    print(DISCLOSURE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
