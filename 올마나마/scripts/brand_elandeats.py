# -*- coding: utf-8 -*-
"""이랜드이츠 브랜드 메뉴 수집 — 자체 API. 2026-07-31 신설

    python scripts/brand_elandeats.py              # 애슐리
    python scripts/brand_elandeats.py AL RU JB     # 브랜드코드 직접 지정

뚫은 API (2026-07-31 확인 · 브라우저가 실제로 부르는 그대로)
    GET https://app.elandeats.co.kr/s/menucategory/api/{브랜드코드}?_={ms}
    GET https://app.elandeats.co.kr/s/menu/api/{브랜드코드}/{menuCategoryNo}?_={ms}

브랜드코드 — 사이트 하단 브랜드 전환 링크(`/home/AL` 등)에서 확인한 것만 쓴다.
    AL 애슐리퀸즈 · RU 로운 샤브샤브 · JB 자연별곡 · PM 피자몰 · RI 리미니

⛔ **파라미터를 바꾸지 마라.** 같은 날 파리바게트에서 `per_page` 를 12→100 으로 바꿨다가
   Wordfence 에 503 으로 막혔다. 사이트가 보내는 모양 그대로 보내고, 사이 간격을 둔다.

🔴 뷔페라 **개별 메뉴엔 가격이 거의 없다** — `price` 가 있는 건 별도주문 스테이크·탭비어뿐이다.
   이용요금(성인/청소년/어린이 × 런치/디너)은 `PRICE(가격)` 카테고리에 **이미지로만** 있어
   API 로는 못 받는다. 요금은 3단계(블로그·검색)에서 채운다.

결과: data/brand_menu_list/<slug>.json  (등록은 brand_menu_import.py 가 한다)
"""
import io
import json
import os
import ssl
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
DOMAIN = "https://app.elandeats.co.kr"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Referer": DOMAIN + "/s/menu?brand=AL",
      "X-Requested-With": "XMLHttpRequest",
      "Accept": "application/json, text/javascript, */*; q=0.01"}

# 브랜드코드 → (우리 브랜드명, slug). 확인한 것만 적는다 — 추측 금지.
BRANDS = {
    "AL": ("애슐리", "ashley"),
}
GAP = 0.5          # 요청 간격 — 몰아치지 않는다


def get(path):
    req = urllib.request.Request(DOMAIN + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25,
                                context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def collect(code):
    name, slug = BRANDS[code]
    cats = get("/s/menucategory/api/%s?_=%d" % (code, int(time.time() * 1000)))
    if str(cats.get("resultCode")) != "200":
        raise RuntimeError("카테고리 응답 오류: %s" % cats.get("resultMessage"))
    out_cats, out_menus, seen = [], [], set()
    for c in cats.get("data") or []:
        cno, cname = c["menuCategoryNo"], (c["menuCategoryName"] or "").strip()
        time.sleep(GAP)
        m = get("/s/menu/api/%s/%s?_=%d" % (code, cno, int(time.time() * 1000)))
        items = m.get("data") or []
        if not items:
            # 메뉴가 0인 카테고리(이미지로만 안내하는 «PRICE(가격)» 등)는 탭을 만들지 않는다
            print("   - %-34s 0개 (이미지 안내로 보임 — 건너뜀)" % cname[:34])
            continue
        out_cats.append({"name": cname, "parent": None, "ext_id": str(cno)})
        for i, it in enumerate(items):
            nm = (it.get("menuName") or "").strip()
            if not nm:
                continue
            # 같은 이름이 두 탭에 있으면 뒤엣것에 탭 이름을 붙인다(UNIQUE 충돌 방지)
            if nm in seen:
                nm = "%s (%s)" % (nm, cname)
            seen.add(nm)
            pr = it.get("price")
            out_menus.append({
                "name": nm,
                "price": pr if pr else None,
                "price_source": "official" if pr else None,
                "compose_raw": (it.get("menuDescCon") or "").strip(),
                "image_url": it.get("imageUrl") or "",
                "ext_id": str(it.get("menuNo") or ""),
                "cats": [[cname, i]],
            })
        print("   · %-34s %3d개" % (cname[:34], len(items)))
    return name, slug, out_cats, out_menus


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    codes = [a for a in sys.argv[1:] if not a.startswith("--")] or ["AL"]
    os.makedirs(OUT, exist_ok=True)
    for code in codes:
        if code not in BRANDS:
            print("모르는 브랜드코드: %s (아는 것: %s)" % (code, ", ".join(BRANDS)))
            continue
        print("■ %s (%s)" % (BRANDS[code][0], code), flush=True)
        name, slug, cats, menus = collect(code)
        doc = {
            "brand": name, "slug": slug,
            "source": DOMAIN + "/s/menu?brand=" + code,
            "collected_at": time.strftime("%Y-%m-%d"),
            "note": "이랜드이츠 자체 API. 뷔페라 개별 메뉴엔 가격이 거의 없다 — "
                    "이용요금(성인/청소년/어린이 × 런치/디너)은 「PRICE(가격)」 카테고리에 "
                    "이미지로만 있어 API 로는 못 받는다. 요금은 3단계에서 채울 것.",
            "cats": cats, "menus": menus,
        }
        p = os.path.join(OUT, slug + ".json")
        json.dump(doc, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        npr = sum(1 for m in menus if m["price"])
        print("✅ 탭 %d · 메뉴 %d개 (가격 %d) → %s\n" % (len(cats), len(menus), npr, p))


if __name__ == "__main__":
    main()
