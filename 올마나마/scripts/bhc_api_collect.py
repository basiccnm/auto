# -*- coding: utf-8 -*-
"""bhc 공식 메뉴를 **홈페이지 자체 API** 에서 읽어 `brand_menu_official` 에 적재한다. 2026-07-27

🔴 왜 별도 스크립트인가
   `brand_menu_list.py` 가 bhc 에서 6개(그나마 'Chicken' 'Side' 같은 탭 이름)만 가져왔다.
   이유 두 가지 —
     ① `brands.homepage_url` 이 **영문 글로벌 사이트**(`bhcchicken.global`) 였다. → 이 스크립트가 고친다.
     ② 한국 사이트(`www.bhc.co.kr`)는 Next.js 라 **가격·중량·원산지·알레르기가 DOM 에 없다.**
        전부 XHR 로 온다. 헤드리스 `--dump-dom` 으로는 영원히 안 잡힌다.

✅ 엔드포인트는 **추측하지 않았다.** 브라우저 네트워크 탭에서 실제 호출을 보고,
   JS 번들(`f9229a4d….js`)의 `axios.create({baseURL:"/api/v1/web"})` 와 경로 템플릿에서 확인했다:
       GET /api/v1/web/categories/list
       GET /api/v1/web/categories/{cateIdx}/products
       GET /api/v1/web/products/{productCd}
   (`API 명세는 추측하지 말고 물어봐라` — 여기서는 소스에 적힌 값을 그대로 읽었다)

📦 이 API 가 주는 것 — 브랜드 대조에 필요한 3종이 전부 들어 있다
   price(본품가) · optionList[].optionPrice(옵션 추가금) · optionList[].weight("10호(951g~1,050g)")
   · optionList[].origin("닭고기:국내산") · allergenInfo[](재료별 알레르기) · optionNutrition

⛔ 판매가는 **본품가 + 옵션 추가금**이다. 한마리는 +1,000, 콤보·윙·스틱·순살은 +3,000 식이다.
   `price` 컬럼에는 **한마리 기준가**(없으면 최저 옵션가)를 넣고, 옵션별 가격은 원문 json 에 남긴다.
⛔ 중량이 g 으로 안 적혀 있으면(예: "다리 10조각") `weight_g` 는 비운다 — 추정 금지.

    python scripts/bhc_api_collect.py          # 수집 + 적재
    python scripts/bhc_api_collect.py --dry    # 적재 없이 요약만
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")     # 콘솔이 cp949 라 ✅·⚠️ 에서 죽는다
import brand_menu_store as store                                    # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "eolmanama.db")
OUT = os.path.join(BASE, "data", "brand_menu_list", "bhcchicken_api.json")

API = "https://www.bhc.co.kr/api/v1/web"
HOME = "https://www.bhc.co.kr"
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": HOME + "/menu/1", "Accept": "application/json"}
GAP = 0.4                      # 호출 간격 — 브랜드 한 곳이라 넉넉히

RX_HOSU = re.compile(r"(\d{1,2})\s*호\s*\(?\s*([\d,]+)\s*g?\s*~\s*([\d,]+)\s*g")
RX_G = re.compile(r"([\d,.]+)\s*(kg|g)\b", re.I)


def get(path):
    r = urllib.request.Request(API + path, headers=HDRS)
    d = json.load(urllib.request.urlopen(r, timeout=25))
    if d.get("code") != 200:
        raise RuntimeError("%s → %s" % (path, d.get("message")))
    return d["body"]


def weight_g(raw):
    """'10호(951g~1,050g)' → 1000.5 / '다리 10조각' → None (추정하지 않는다)"""
    if not raw:
        return None
    m = RX_HOSU.search(raw)
    if m:
        return (int(m.group(2).replace(",", "")) + int(m.group(3).replace(",", ""))) / 2.0
    m = RX_G.search(raw)
    if m:
        v = float(m.group(1).replace(",", ""))
        return v * 1000 if m.group(2).lower() == "kg" else v
    return None


def main():
    dry = "--dry" in sys.argv

    # 🔴 순서는 배열 순서가 아니라 `sortSeq` 다 (2026-07-28).
    #    배열대로 쓰면 「치킨」이 첫 탭이 되는데, bhc 홈페이지의 첫 탭은 「뿌링클유니버스」다.
    # 🔴 `subCateList` 에 **하위 카테고리**가 들어 있다 — 「치킨 > 후라이드/양념/뿌링클/킹/핫」.
    cats = sorted(get("/categories/list"), key=lambda x: x.get("sortSeq") or 0)
    print("카테고리 %d개: %s" % (len(cats), " → ".join(
        "%s(%s)" % (c["cateNm"], "·".join(s["cateNm"] for s in sorted(
            c.get("subCateList") or [], key=lambda x: x.get("sortSeq") or 0)) or "-")
        for c in cats)), flush=True)

    # ① 카테고리별 상품 목록 → productCd 별로 어느 카테고리에 **몇 번째로** 걸렸는지 모은다
    #    🔴 자리(번호)를 같이 담는다 — 같은 메뉴가 「치킨」 3번째이면서 「시그니처」 1번째일 수 있다.
    #       브랜드가 깔아둔 진열 순서를 그대로 보여주는 게 목적이다(대표 지시 2026-07-28).
    #    하위는 `/categories/{하위idx}/products` 로는 **0개가 온다.** 대신 상위 목록의 각 상품에
    #    `cateSortList:[{cateNm, sortKey}]` 가 붙어 오고, `sortKey % 10000` 이 그 하위 안에서의 자리다.
    #    (sortKey 가 0 인 항목이 몇 개 있어 그때는 나온 순서를 쓴다)
    prods, order = {}, []
    for c in cats:
        time.sleep(GAP)
        top = c["cateNm"]
        items = get("/categories/%d/products" % c["cateIdx"])
        subs = {s["cateNm"] for s in (c.get("subCateList") or [])}
        for pos, it in enumerate(items):
            cd = it["productCd"]
            if cd not in prods:
                prods[cd] = {"cats": [], "list": it, "cateIdx": c["cateIdx"]}
                order.append(cd)
            prods[cd]["cats"].append((top, pos))
            for e in (it.get("cateSortList") or []):
                sn = (e.get("cateNm") or "").strip()
                if sn not in subs:
                    continue
                k = e.get("sortKey") or 0
                prods[cd]["cats"].append(("%s/%s" % (top, sn), k % 10000 if k else 9000 + pos))
        print("  %-12s 상품 %d개 (하위 %d)" % (top, len(items), len(subs)), flush=True)
    print("고유 상품 %d개" % len(prods), flush=True)
    print("", flush=True)

    # ② 상품 상세 — 가격·중량·원산지·알레르기
    recs = []
    for i, cd in enumerate(order, 1):
        time.sleep(GAP)
        try:
            b = get("/products/%s" % cd)
        except Exception as e:
            print("  ✗ %s 실패: %s" % (cd, str(e)[:60]), flush=True)
            continue
        p = prods[cd]
        opts = b.get("optionList") or []
        base = b.get("price") or 0
        # 한마리 기준가 — 없으면 최저 옵션가, 옵션이 아예 없으면 본품가
        one = next((o for o in opts if (o.get("optionNm") or "").strip() == "한마리"), None)
        if one:
            price, pbasis = base + (one.get("optionPrice") or 0), "한마리"
        elif opts:
            lo = min(opts, key=lambda o: o.get("optionPrice") or 0)
            price, pbasis = base + (lo.get("optionPrice") or 0), (lo.get("optionNm") or "").strip()
        else:
            price, pbasis = base or None, "본품"
        wsrc = one or (opts[0] if opts else None)
        wraw = ((wsrc or {}).get("weight") or "").strip() or None
        if wraw:
            wraw = re.split(r"\n\s*\n", wraw)[0].strip()      # 뒤에 붙는 안내문 잘라냄
        origins = sorted({(o.get("origin") or "").strip() for o in opts if (o.get("origin") or "").strip()})
        allerg = ["%s:%s" % (a.get("item", "").strip(), a.get("allergen", "").strip())
                  for a in (b.get("allergenInfo") or [])
                  if (a.get("item") or "").strip() or (a.get("allergen") or "").strip()]

        recs.append({
            "productCd": cd,
            "name": re.sub(r"\s*\n\s*", " ", (b.get("productNm") or "")).strip(),
            # cats = [("치킨",3), …] 원본 그대로. category 는 원본이 없는 화면을 위한 요약일 뿐이다
            "cats": p["cats"],
            "category": " · ".join(dict.fromkeys(n for n, _ in p["cats"] if "/" not in n)),
            "price": price, "price_basis": pbasis, "base_price": base,
            "weight_raw": wraw, "weight_g": weight_g(wraw),
            "origin_raw": " | ".join(origins) or None,
            "allergy_raw": " | ".join(allerg) or None,
            "detail_url": "%s/menu/%d" % (HOME, p["cateIdx"]),
            "image_url": p["list"].get("mainImg"),
            "description": (b.get("description") or "").strip(),
            "isBest": b.get("isBest"), "isNew": b.get("isNew"),
            "options": [{"optionNm": (o.get("optionNm") or "").strip(),
                         "price": base + (o.get("optionPrice") or 0),
                         "weight": (o.get("weight") or "").strip() or None,
                         "origin": (o.get("origin") or "").strip() or None,
                         "desc": re.sub(r"\s+", " ", (o.get("optionDesc") or "")).strip() or None,
                         "nutrition": o.get("optionNutrition")} for o in opts],
        })
        if i % 10 == 0:
            print("  … %d/%d" % (i, len(order)), flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps({"brand": "bhc치킨", "slug": "bhcchicken", "src": API,
                    "menus": recs}, ensure_ascii=False, indent=1))

    n_p = sum(1 for r in recs if r["price"])
    n_w = sum(1 for r in recs if r["weight_raw"])
    n_g = sum(1 for r in recs if r["weight_g"])
    n_o = sum(1 for r in recs if r["origin_raw"])
    n_a = sum(1 for r in recs if r["allergy_raw"])
    print("", flush=True)
    print("공식메뉴 %d개 · 가격 %d · 중량원문 %d(g환산 %d) · 원산지 %d · 알레르기 %d"
          % (len(recs), n_p, n_w, n_g, n_o, n_a), flush=True)
    print("원문 → %s" % os.path.relpath(OUT, BASE), flush=True)

    if dry:
        print("(dry — DB 미반영)")
        return

    # 🔴 적재는 **공통 뼈대**를 통해서만 한다 (`brand_menu_store.replace_brand`).
    #    자기 brand_id 밖을 못 건드리고, 사람이 확정한 값은 보존되며, 누가 넣었는지 기록된다.
    c = store.connect()
    store.ensure(c)
    bid = store.brand_id(c, slug="bhcchicken")
    c.execute("UPDATE brands SET homepage_url=? WHERE id=?", (HOME + "/main", bid))

    ours = {re.sub(r"[\s·,\-_.()\[\]/]+", "", r[1]).lower(): r[0]
            for r in c.execute("SELECT id,name FROM menus WHERE brand_id=?", (bid,))}
    items = []
    for r in recs:
        d = dict(r)
        d["price_source"] = "official"
        d["_menu_id"] = ours.get(re.sub(r"[\s·,\-_.()\[\]/]+", "", r["name"]).lower())
        items.append(d)

    # 상위를 먼저, 그 뒤에 자식 — `replace_brand` 는 부모가 이미 들어가 있어야 이어붙인다
    tree = []
    for x in cats:
        tree.append({"name": x["cateNm"], "ext_id": str(x["cateIdx"])})
        for s in sorted(x.get("subCateList") or [], key=lambda y: y.get("sortSeq") or 0):
            tree.append({"name": s["cateNm"], "parent": x["cateNm"],
                         "ext_id": str(s["cateIdx"])})
    store.replace_brand(c, bid, tree, items, collector="bhc_api_collect")

    # 우리 원가 메뉴와 잇기 — 사람이 이어둔 게 있으면 그건 `replace_brand` 가 이미 물려줬다
    linked = 0
    for d in items:
        if d["_menu_id"]:
            linked += c.execute("""UPDATE brand_menu_official SET menu_id=?
                                   WHERE brand_id=? AND name=? AND menu_id IS NULL""",
                                (d["_menu_id"], bid, d["name"])).rowcount
    c.commit()
    print("우리 메뉴 자동연결 %d개 추가 (나머지는 사람이 잇는다)" % linked)
    c.close()


if __name__ == "__main__":
    main()
