# -*- coding: utf-8 -*-
"""본아이에프 브랜드 공식 메뉴 수집 — 자체 API. 2026-07-27

🔴 엔드포인트는 **브라우저에서 실제 호출을 확인**한 것이다(경로 추측 금지):
   GET https://api.bonif.co.kr/brand/v1/menu?brdCd={코드}&cmdtCateIdx=&orderBy=
   GET https://api.bonif.co.kr/brand/v1/category?brdCd={코드}
   응답 = {status, retCode, retMsg, date, data:{brand, menuList[]}}
   menuList 항목: cmdtNm(이름) · cmdtPrice(정가) · cmdtSalePrice(판매가) · cmdtCateIdx(카테고리)

🔴 찾은 방법 — `read_network_requests` 가 비었을 때 브라우저 콘솔에서:
   performance.getEntriesByType('resource').map(x=>x.name).filter(u=>/api|menu/i.test(u))

본도시락 = **BF104**. 다른 브랜드 코드는 사이트 메뉴에서 확인한 것만 쓴다.

    python scripts/bonif_api_collect.py             # 본도시락
    python scripts/bonif_api_collect.py BF104 BF101 # 코드 직접 지정
"""
import io
import json
import os
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list")
API = "https://api.bonif.co.kr/brand/v1"
GAP = 1.5
sys.stdout.reconfigure(encoding="utf-8")

# 확인된 코드만. 새 브랜드는 사이트에서 brdCd 를 눈으로 보고 추가한다(추측 금지).
KNOWN = {"BF104": ("본도시락", "bondosirak")}

HDR = {"User-Agent": "Mozilla/5.0", "Accept": "application/json",
       "Referer": "https://www.bonif.co.kr/", "Origin": "https://www.bonif.co.kr"}


def get(path):
    req = urllib.request.Request(API + path, headers=HDR)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def collect(code):
    name, slug = KNOWN.get(code, (code, code.lower()))
    cats = {}
    try:
        d = get("/category?brdCd=%s" % code)
        for x in ((d.get("data") or {}).get("cateList")
                  or (d.get("data") or {}).get("list") or []):
            k = str(x.get("cmdtCateIdx") or x.get("cateIdx") or "")
            v = x.get("cateNm") or x.get("cmdtCateNm") or ""
            if k:
                cats[k] = v
    except Exception as e:
        print("  ! 카테고리 실패 %s" % str(e)[:50])
    time.sleep(GAP)

    d = get("/menu?brdCd=%s&cmdtCateIdx=&orderBy=" % code)
    items = (d.get("data") or {}).get("menuList") or []
    menus, nopr = [], 0
    for it in items:
        nm = (it.get("cmdtNm") or "").strip()
        # 판매가가 정본. 정가(cmdtPrice)는 할인 전 값일 수 있다
        pr = it.get("cmdtSalePrice") or it.get("cmdtPrice")
        try:
            pr = int(str(pr).replace(",", "")) if pr else None
        except ValueError:
            pr = None
        if not nm:
            continue
        if not pr:
            nopr += 1
        menus.append({"name": nm, "price": pr, "weight_raw": None, "weight_g": None,
                      "category": cats.get(str(it.get("cmdtCateIdx") or "")),
                      "src": "https://api.bonif.co.kr/brand/v1/menu?brdCd=%s" % code})
    rec = {"brand": name, "slug": slug, "url": "https://www.bonif.co.kr/brand/menu?brdCd=" + code,
           "pages": [API + "/menu?brdCd=" + code], "menus": menus}
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, slug + "_api.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=1))
    print("%-12s 메뉴 %3d개 (가격 %d · 없음 %d) · 카테고리 %d개 → %s"
          % (name, len(menus), len(menus) - nopr, nopr, len(cats), os.path.basename(p)))
    if menus:
        for m in sorted([x for x in menus if x["price"]],
                        key=lambda x: -x["price"])[:8]:
            print("    %-34s %7s  %s" % (m["name"][:34], format(m["price"], ","),
                                        m.get("category") or ""))


def main():
    codes = [a for a in sys.argv[1:] if not a.startswith("--")] or ["BF104"]
    for i, code in enumerate(codes):
        if i:
            time.sleep(GAP)
        try:
            collect(code)
        except Exception as e:
            print("✗ %s 실패: %s" % (code, str(e)[:70]))


if __name__ == "__main__":
    main()
