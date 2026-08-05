# -*- coding: utf-8 -*-
"""미스터피자 메뉴·가격 수집 — 공식 홈페이지(그누보드). 2026-07-31 신설

    python scripts/brand_mrpizza.py

경로 (화면 링크에서 그대로 읽은 것. 추측 아님)
    목록  /bbs/board.php?bo_table=menu&sca={탭}          ← `bo_tit` 에 메뉴명, `wr_id` 가 상세 키
    상세  /bbs/board.php?bo_table=menu&wr_id={id}        ← `price_info` 안에 「M 21,900원 L 28,900원」

🔴 **목록에는 가격이 없다. 상세에만 있다.**(2026-07-31 확인 — 목록 33,166자에 「원」 0건)
🔴 한 상세에 M/L 이 **여러 쌍** 온다 — 도우(오리지널·씬·골드)별 가격이다.
   **첫 쌍이 기본(오리지널)** 이다. 나머지는 도우 업그레이드라 메뉴판에 따로 싣지 않는다.
   → 메뉴는 「더블치즈 (M)」·「더블치즈 (L)」 두 줄로 만든다. 피자는 크기가 곧 다른 상품이다.

⛔ 배달앱으로 받지 않는다 — 대표 지시(2026-07-31): *"미스터 피자 홈페이지로"*.
   쿠팡이츠 수유점은 화면에서 2개밖에 안 잡혀 폐기했다.

결과: data/brand_menu_list/mrpizza.json
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
ROOT = "https://www.mrpizza.co.kr"
LIST = "/bbs/board.php?bo_table=menu&sca="
# 화면의 sca 값 그대로 (공백이 `+` 로 오는 것도 그대로 되돌려 쓴다)
TABS = ["클래식 피자", "프리미엄 피자", "씬크러스트 피자", "1인용 피자", "피자샌드",
        "파스타&라이스", "샐러드&사이드", "음료",
        "특가세트-피치세트", "특가세트-보너스파우치"]
GAP = 1.0
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

RX_ITEM = re.compile(r'wr_id=(\d+)[^"]*"\s+class="bo_tit">\s*(.*?)\s*<', re.S)
# 🔴 실제 마크업은 `<li …><span>M</span>21,900원</li>` — **태그가 사이에 낀다.**
#    「M 21,900원」 처럼 붙어 있을 거라 보고 짠 정규식은 0건이었다(2026-07-31).
RX_PRICE = re.compile(r'<span>\s*([ML])\s*</span>\s*([\d,]{4,})\s*원', re.I)


def get(path):
    req = urllib.request.Request(ROOT + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def txt(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s.replace("&amp;", "&").replace("&nbsp;", " ")).strip()


def prices_of(wr_id):
    """상세에서 **첫 M/L 한 쌍**만 쓴다 — 뒤엣것은 도우 업그레이드 가격이다."""
    d = get("/bbs/board.php?bo_table=menu&wr_id=%s" % wr_id)
    out = {}
    for sz, v in RX_PRICE.findall(d):
        if sz not in out:                       # 처음 나온 것 = 기본 도우
            out[sz] = int(v.replace(",", ""))
        if len(out) == 2:
            break
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cats, menus, seen = [], [], set()
    for tab in TABS:
        try:
            html = get(LIST + urllib.parse.quote(tab))
        except Exception as e:
            print("   - %-16s 못 열었다: %s" % (tab[:16], e))
            time.sleep(GAP)
            continue
        items = [(i, txt(n)) for i, n in RX_ITEM.findall(html)]
        items = [(i, n) for i, n in items if n]
        if not items:
            print("   - %-16s 0개" % tab[:16])
            time.sleep(GAP)
            continue
        cats.append({"name": tab, "parent": None, "ext_id": tab})
        k = 0
        for wr_id, name in items:
            pr = {}
            try:
                pr = prices_of(wr_id)
            except Exception as e:
                print("      ! %s 상세 실패: %s" % (name[:14], e))
            time.sleep(GAP)
            if pr:
                for sz in ("M", "L"):            # 피자는 크기가 곧 다른 상품이다
                    if sz not in pr:
                        continue
                    nm = "%s (%s)" % (name, sz)
                    if nm in seen:
                        continue
                    seen.add(nm)
                    menus.append({"name": nm, "price": pr[sz], "price_source": "official",
                                  "cats": [[tab, k]]})
                    k += 1
            else:                                # 가격이 없는 것도 **이름은 남긴다**
                if name in seen:
                    continue
                seen.add(name)
                menus.append({"name": name, "price": None, "price_source": None,
                              "cats": [[tab, k]]})
                k += 1
        print("   · %-16s 메뉴 %2d개 → 줄 %d개" % (tab[:16], len(items), k))

    # 🔴 실패가 기존 자료를 지우면 안 된다 (2026-07-31 빕스 빈 JSON 사고)
    if not menus:
        print("🔴 0개 — 저장하지 않는다. 화면 구조가 바뀐 것이다.")
        return 1
    p = os.path.join(OUT, "mrpizza.json")
    if os.path.exists(p):
        try:
            old_n = len(json.load(io.open(p, encoding="utf-8")).get("menus") or [])
        except Exception:
            old_n = 0
        if old_n and len(menus) < old_n * 0.7:
            print("🔴 %d개 → %d개로 줄었다. 덮지 않는다." % (old_n, len(menus)))
            return 1
    doc = {"brand": "미스터피자", "slug": "mrpizza", "source": ROOT + "/bbs/board.php?bo_table=menu",
           "collected_at": time.strftime("%Y-%m-%d"),
           "note": "공식 홈페이지(그누보드). 가격은 **상세 페이지**에만 있다 — 목록엔 없다. "
                   "M/L 을 각각 한 줄로 만들었고, 상세의 첫 M/L 쌍(기본 도우)만 썼다. "
                   "가격은 날마다 달라질 수 있다.",
           "cats": cats, "menus": menus}
    os.makedirs(OUT, exist_ok=True)
    json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    got = sum(1 for m in menus if m.get("price"))
    print("\n✅ 탭 %d · 줄 %d개 (가격 %d개) → %s" % (len(cats), len(menus), got, p))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
