# -*- coding: utf-8 -*-
"""미트박스 육류 시세 수집 — 낮은단가순 전량.

앞선 수집(2026-07-25)은 사이트 기본 정렬(추천순) + 카테고리당 300건 상한이라
진짜 최저가가 빠졌을 수 있었다. 이 스크립트는 **낮은단가순으로 전 페이지**를 받는다.

엔드포인트·body 형식은 사이트 프런트엔드가 실제로 쓰는 것을 그대로 쓴다(경로 추측 금지).
  POST https://mb-api.meatbox.co.kr/product/api/v1/search/filter?page=N&size=100
  body {"displayCategorySeq":["10005"],"procCd":"P001","operator":"or","sort":"price_asc"}
  가공방법 코드: P001 원물 / P002 세절&분쇄 / P006 낱개

⚠️ 요청 간격 3초 고정. 과거 다른 사이트에서 0.4초로 긁다가 IP 차단당한 적이 있다.
"""
import json, os, re, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(BASE, "data", "research", "meatbox")
API = "https://mb-api.meatbox.co.kr/product/api/v1/search/filter?page=%d&size=100"
GAP = 3.0

CATS = [("10000", "한우암소"), ("10001", "한우거세"), ("10002", "한우수소"),
        ("10003", "육우암소"), ("10004", "육우거세"), ("10005", "수입소"),
        ("10010", "한돈"), ("10011", "수입돼지"),
        ("10016", "국산닭"), ("10017", "수입닭")]
PROCS = [("P001", "원물"), ("P002", "세절&분쇄"), ("P006", "낱개")]


def call(seq, proc, page):
    body = {"displayCategorySeq": [seq], "procCd": proc,
            "operator": "or", "sort": "price_asc"}
    req = urllib.request.Request(
        API % page, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "Origin": "https://www.meatbox.co.kr",
                 "Referer": "https://www.meatbox.co.kr/",
                 "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    s = j["data"]["search"]
    return s["total"], s["items"]


def won(s):
    m = re.search(r"([\d,]+)\s*원", s or "")
    return int(m.group(1).replace(",", "")) if m else None


def per_kg(x):
    """원/kg 과 총중량. 사이트가 준 값만 쓴다 — 없으면 None(추정하지 않는다)."""
    d = x.get("displayPriceForKg") or ""
    if d:                                    # "kg당 7,330원 | 총 20kg"
        p = won(d)
        m = re.search(r"총\s*([\d.]+)\s*kg", d, re.I)
        return p, (float(m.group(1)) if m else None)
    if "kg당" in (x.get("priceUnitTypeText") or ""):
        return won(x.get("priceText")), None
    return None, None


def row(x, catname, procname):
    p, kg = per_kg(x)
    return {
        "축종원산지": x.get("originName") if x.get("itemKindName", "").startswith("수입")
                    else (x.get("itemKindName") or catname),
        "부위": x.get("itemCatName"),
        "등급": (x.get("productName") or "").split(" - ")[-1]
                if " - " in (x.get("productName") or "") else None,
        "브랜드": x.get("brandName"),
        "원산지": x.get("originName"),
        "축종": x.get("itemKindName"),
        "가공방법": procname,
        "원per_kg": p,
        "총중량kg": kg,
        "가격표기": x.get("priceText"),
        "단위표기": x.get("priceUnitTypeText"),
        "두께mm": x.get("thickness") or None,
        "보관": {"F001": "냉장", "F002": "냉동"}.get(x.get("keepingCd"), x.get("keepingCd")),
        "대량상품": x.get("largePurchaseGbn") == "Y",
        "대량조건": x.get("eventMsg") or None,
        "재고": x.get("stockAmount"),
        "상품명": x.get("productName"),
        "링크": "https://www.meatbox.co.kr/fo/product/productViewPage.do?productSeq=%s&itemSeq=%s"
                % (x.get("productSeq"), x.get("itemSeq")),
    }


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    allrows, req_n = [], 0
    for seq, catname in CATS:
        got = []
        for proc, procname in PROCS:
            page = 1
            while True:
                try:
                    total, items = call(seq, proc, page)
                except urllib.error.HTTPError as e:
                    print("  !! %s %s p%d HTTP %s — 중단" % (catname, procname, page, e.code))
                    break
                except Exception as e:
                    print("  !! %s %s p%d %s — 중단" % (catname, procname, page, e))
                    break
                req_n += 1
                got += [row(x, catname, procname) for x in items]
                if page * 100 >= total or not items:
                    break
                page += 1
                time.sleep(GAP)
            time.sleep(GAP)
        allrows += got
        print("%-8s %4d건" % (catname, len(got)), flush=True)
        json.dump(got, open(os.path.join(OUTDIR, "%s_전량.json" % catname), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=1)

    json.dump(allrows, open(os.path.join(OUTDIR, "_전량.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n총 %d건 / 요청 %d회" % (len(allrows), req_n))

    # 그룹 최저가 — (축종/원산지)(부위)(등급·브랜드) × 가공방법
    grp = {}
    for r in allrows:
        if not r["원per_kg"]:
            continue
        k = (r["축종원산지"], r["부위"], r["등급"], r["가공방법"])
        grp.setdefault(k, []).append(r)

    low = []
    for k, rows in grp.items():
        rows.sort(key=lambda r: r["원per_kg"])
        normal = [r for r in rows if not r["대량상품"]]
        pick = (normal or rows)[0]
        ps = [r["원per_kg"] for r in (normal or rows)]
        low.append({"표시키": "(%s)(%s)(%s·%s)" % (k[0], k[1], k[2] or "-", pick["브랜드"] or "-"),
                    "축종원산지": k[0], "부위": k[1], "등급": k[2], "가공방법": k[3],
                    "원per_kg": pick["원per_kg"], "n": len(rows),
                    "중앙값": ps[len(ps) // 2], "최고": ps[-1],
                    "대량상품만": not normal,
                    "상품명": pick["상품명"], "총중량kg": pick["총중량kg"],
                    "두께mm": pick["두께mm"], "링크": pick["링크"]})
    low.sort(key=lambda r: (r["축종원산지"], r["부위"] or "", r["원per_kg"]))
    json.dump(low, open(os.path.join(OUTDIR, "_lowest_price_asc.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)

    with open(os.path.join(OUTDIR, "_lowest_price_asc.md"), "w", encoding="utf-8") as f:
        f.write("# 미트박스 그룹별 최저가 (낮은단가순 전량, 2026-07-25)\n\n")
        f.write("`대량상품`(20박스 등 최소수량 조건)은 최저가 후보에서 뺐다. "
                "그룹 전체가 대량뿐이면 `*` 표시.\n\n")
        f.write("| 키 | 원/kg | n | 중앙 | 최고 | 형태 |\n|---|---:|---:|---:|---:|---|\n")
        for r in low:
            form = r["가공방법"]
            if r["두께mm"]:
                form += " %smm" % r["두께mm"]
            if r["총중량kg"]:
                form += " · %skg" % r["총중량kg"]
            f.write("| %s%s | %s | %d | %s | %s | %s |\n" % (
                r["표시키"], "*" if r["대량상품만"] else "", f"{r['원per_kg']:,}",
                r["n"], f"{r['중앙값']:,}", f"{r['최고']:,}", form))
    print("그룹 %d개 → _lowest_price_asc.md" % len(low))


main()
