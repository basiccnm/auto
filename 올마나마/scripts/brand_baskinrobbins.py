# -*- coding: utf-8 -*-
"""배스킨라빈스(baskinrobbins) 메뉴 수집 — 골격 + 가격.

■ 경로 1: 앱(APK) — 가격 출처
   패키지 kr.co.baskinrobbins.client (Flutter). 폰에서 뽑은 APK 안에서 읽은 주소다.
     split_config.arm64_v8a.apk / lib/arm64-v8a/libapp.so 문자열:
       호스트  https://bra-brus.baskinrobbins.co.kr        (dev/stg 도 있으나 운영은 이것)
       경로    /api  +  /pd/product/list · /pd/product/get · /pd/flavor/list · /pd/search
     → POST https://bra-brus.baskinrobbins.co.kr/api/pd/product/list  body {}  (인증 불필요)
       응답 {"code":"00","data":[{"cd","nm","imgUrl","prc","ctgCd","bdgCd"}, ...]}  215건
   ⚠️ GET 은 405 다. POST + Content-Type: application/json 이어야 한다.
   ⚠️ 이 목록은 제품정보(pd)용이라 매장 판매가다. 주문(od)·배달가가 아니다.

■ 경로 2: 공식 홈페이지 https://www.baskinrobbins.co.kr — 카테고리·순서·규격·중량·알레르기
   (WebSearch 로 확인한 공식 도메인. 상단 네비 「Menu」 드롭다운의 링크만 따라간다)
     /menu/list.php?category=A|F|B|E        → /menu/view.php?seq=N
     /menu/list_subcategory.php?category=C|D → /menu/view_subcategory.php?seq=N
     /menu/fom.php (이달의 맛)
   아이스크림 상세의 SELECT SIZE 표(싱글레귤러…하프갤론)가 규격별 가격을 그대로 준다.

⛔ DB 를 import 하지 않는다. 결과는 data/brand_menu_list/baskinrobbins.json 한 장.
"""
import sys, os, re, json, time, html, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

WEB = "https://www.baskinrobbins.co.kr"
API = "https://bra-brus.baskinrobbins.co.kr/api"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
SLEEP = 1.6
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "baskinrobbins.json")

_last = [0.0]


def _wait():
    dt = time.time() - _last[0]
    if dt < SLEEP:
        time.sleep(SLEEP - dt)
    _last[0] = time.time()


def get(url):
    _wait()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as f:
        b = f.read()
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("euc-kr", "replace")


def post_json(path, body):
    _wait()
    h = dict(UA)
    h["Content-Type"] = "application/json"
    h["Accept"] = "application/json"
    req = urllib.request.Request(API + path, headers=h, data=json.dumps(body).encode())
    with urllib.request.urlopen(req, timeout=40) as f:
        return json.loads(f.read().decode("utf-8"))


def nocmt(h):
    return re.sub(r"<!--[\s\S]*?-->", "", h)


def text(s):
    s = re.sub(r"<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def content(h):
    i = h.find('id="content"')
    j = h.find("site-footer", i if i > 0 else 0)
    return h[i:j if j > i else len(h)] if i > 0 else h


def won(s):
    m = re.search(r"([\d,]+)\s*원", s or "")
    return int(m.group(1).replace(",", "")) if m else None


def norm(s):
    """가격 대조용 이름 정규화 — POS 접두(I_R) H_L) I_RD) I_ …)·괄호·공백·기호 제거.
    ⚠️ R/L·HOT/ICED 같은 규격 표기는 **지우지 않는다.** 지우면 라지 값에 레귤러 가격이 붙는다."""
    s = html.unescape(s or "")
    s = re.sub(r"^[A-Z]{1,3}(_[A-Z]{1,3})?\s*\)", "", s)     # I_R) H_L) I_RD) D)
    s = re.sub(r"^[A-Z]{1,3}_", "", s)                        # I_납작복숭아아샷추
    s = re.sub(r"[\(\)\[\]{}\s\-_,./&]", "", s)
    return s.lower()


# ── 카테고리 (홈 상단 네비 「Menu」 드롭다운 순서 그대로) ────────────────────
def read_cats():
    h = nocmt(get(WEB + "/"))
    i = h.find("site-menu-list__list")
    block = h[i:h.find("</ul>", i)]
    out = []
    for href, label in re.findall(r'href="(/menu/[^"]+)"[^>]*>\s*([^<]+?)\s*<', block):
        out.append((text(label), href))
    return out


# ── 목록 페이지 ─────────────────────────────────────────────────────────────
def read_list(path):
    h = nocmt(get(WEB + path))
    body = content(h)
    items = []
    for m in re.finditer(
            r'<li class="menu-list__item[\s\S]*?href="(view[^"]*\?seq=(\d+))"[\s\S]*?'
            r'<img src="([^"]*)"[\s\S]*?menu-list__hash"[^>]*>([\s\S]*?)</span>'
            r'[\s\S]*?menu-list__title">([\s\S]*?)</strong>', body):
        items.append({"url": m.group(1), "seq": m.group(2), "img": m.group(3),
                      "hash": text(m.group(4)), "name": text(m.group(5))})
    return items


def read_fom(path):
    h = nocmt(get(WEB + path))
    body = content(h)
    m = re.search(r'class="menu-fom__title">([\s\S]*?)</', body)
    if not m:
        return []
    nm = text(m.group(1))
    d = re.search(r'class="menu-fom__text">([\s\S]*?)</', body)
    u = re.search(r'href="[^"]*(view\.php\?seq=(\d+))"', html.unescape(body))
    return [{"url": u.group(1) if u else None, "seq": u.group(2) if u else None,
             "img": None, "hash": "", "name": nm, "desc": text(d.group(1)) if d else None}]


# ── 상세 페이지 ─────────────────────────────────────────────────────────────
def read_view(seq):
    """view.php — 단일 제품. 가격 1개 또는 SELECT SIZE 표."""
    body = content(nocmt(get("%s/menu/view.php?seq=%s" % (WEB, seq))))
    d = {"en": None, "desc": None, "price": None, "weight": None,
         "allergy": None, "sizes": []}
    m = re.search(r'menu-view-header__title--en">([\s\S]*?)</span>', body)
    if m:
        d["en"] = text(m.group(1)) or None
    m = re.search(r'menu-view-header__text">([\s\S]*?)</p>', body)
    if m:
        d["desc"] = text(m.group(1)) or None
    m = re.search(r'menu-view-header__price">([\s\S]*?)</', body)
    if m:
        d["price"] = won(text(m.group(1)))

    nut = []
    for a, b in re.findall(r'menu-view-nutrition__name">([\s\S]*?)</dt>'
                           r'[\s\S]*?menu-view-nutrition__text"[^>]*>([\s\S]*?)</dd>', body):
        a, b = text(a), text(b)
        if "알레르기" in a:
            d["allergy"] = b
        else:
            nut.append("%s %s" % (a, b))
    if nut:
        d["weight"] = " · ".join(nut)
    # 디저트류는 영양정보가 한 줄 텍스트다
    m = re.search(r'(1회제공량[\s\S]{0,300}?)</', body)
    if m and not d["weight"]:
        t = text(m.group(1))
        d["weight"] = t
        if "알레르기" in t:
            d["allergy"] = t.split("알레르기 성분 :")[-1].strip() or d["allergy"]

    for grp in re.finditer(r'menu-view-list__title">([\s\S]*?)</h4>([\s\S]*?)</ul>', body):
        gname = text(grp.group(1))
        for it in re.finditer(r'menu-view-list__name">([\s\S]*?)</span>\s*'
                              r'<span class="menu-view-list__weight">([\s\S]*?)</span>\s*'
                              r'<strong class="menu-view-list__price">([\s\S]*?)</strong>', grp.group(2)):
            d["sizes"].append({"group": gname, "name": text(it.group(1)),
                               "weight": text(it.group(2)), "price": won(text(it.group(3)))})
    return d


def read_view_sub(seq):
    """view_subcategory.php — 묶음 안에 규격/변형이 여러 개."""
    body = content(nocmt(get("%s/menu/view_subcategory.php?seq=%s" % (WEB, seq))))
    d = {"en": None, "desc": None, "items": []}
    m = re.search(r'menu-view-header__title--en">([\s\S]*?)</span>', body)
    if m:
        d["en"] = text(m.group(1)) or None
    m = re.search(r'menu-view-header__text">([\s\S]*?)</p>', body)
    if m:
        d["desc"] = text(m.group(1)) or None
    for blk in re.split(r'<div class="subcategory-view__product">', body)[1:]:
        m = re.search(r"<h4>([\s\S]*?)</h4>", blk)
        if not m:
            continue
        nm = text(m.group(1))
        nut, allergy = [], None
        for a, b in re.findall(r'menu-view-nutrition__name">([\s\S]*?)</dt>'
                               r'[\s\S]*?menu-view-nutrition__text"[^>]*>([\s\S]*?)</dd>', blk):
            a, b = text(a), text(b)
            if "알레르기" in a:
                allergy = b
            else:
                nut.append("%s %s" % (a, b))
        d["items"].append({"name": nm, "weight": " · ".join(nut) or None, "allergy": allergy})
    return d


def main():
    # 1) 앱 API — 가격표
    prices, api_n = {}, 0
    try:
        data = post_json("/pd/product/list", {})["data"]
        api_n = len(data)
        for x in data:
            prices.setdefault(norm(x["nm"]), x["prc"])
        print("앱 API 상품 %d건 (가격 보유 %d)" % (api_n, len(prices)))
    except Exception as e:
        print("⚠️ 앱 API 실패 — 홈페이지 가격만 쓴다: %r" % (e,))

    cat_defs = read_cats()
    print("카테고리(네비 순서): " + " / ".join(c for c, _ in cat_defs))

    cats = [{"name": c, "parent": None, "ext_id": None} for c, _ in cat_defs]
    catnames = {c for c, _ in cat_defs}
    menus, dropped, flagged = [], [], []
    by_name = {}     # 이달의 맛 ↔ 아이스크림처럼 같은 메뉴가 두 탭에 걸린다 → cats 만 늘린다
    api_hit = 0

    for cname, path in cat_defs:
        items = read_fom(path) if path.endswith("fom.php") else read_list(path)
        pos = 0
        for it in items:
            nm = it["name"]
            if nm in catnames:
                dropped.append("%s / %s ← 카테고리 이름과 같음" % (cname, nm))
                continue
            if re.search(r"[.!?]$", nm) and not nm.endswith("!"):
                dropped.append("%s / %s ← 문장부호로 끝남" % (cname, nm))
                continue
            if len(nm) >= 18:
                flagged.append("%s / %s (%d자 — 사이트 메뉴명이라 남김)" % (cname, nm, len(nm)))

            rows = []
            if it.get("url", "").startswith("view_subcategory"):
                d = read_view_sub(it["seq"])
                durl = "%s/menu/view_subcategory.php?seq=%s" % (WEB, it["seq"])
                if not d["items"]:
                    rows.append({"name": nm, "price": None, "weight": None, "allergy": None,
                                 "compose": d["desc"], "en": d["en"], "ext": it["seq"]})
                for sub in d["items"]:
                    rows.append({"name": sub["name"], "price": None, "weight": sub["weight"],
                                 "allergy": sub["allergy"],
                                 "compose": "%s | %s" % (nm, d["desc"] or ""),
                                 "en": d["en"], "ext": "%s#%s" % (it["seq"], sub["name"])})
            elif it.get("seq"):
                d = read_view(it["seq"])
                durl = "%s/menu/view.php?seq=%s" % (WEB, it["seq"])
                if d["sizes"]:
                    for s in d["sizes"]:
                        rows.append({"name": "%s (%s)" % (nm, s["name"]), "price": s["price"],
                                     "weight": s["weight"], "allergy": d["allergy"],
                                     "compose": "%s | %s" % (s["group"], d["desc"] or ""),
                                     "en": d["en"], "ext": "%s#%s" % (it["seq"], s["name"])})
                else:
                    rows.append({"name": nm, "price": d["price"], "weight": d["weight"],
                                 "allergy": d["allergy"], "compose": d["desc"],
                                 "en": d["en"], "ext": it["seq"]})
            else:
                durl = WEB + path
                rows.append({"name": nm, "price": None, "weight": None, "allergy": None,
                             "compose": it.get("desc"), "en": None, "ext": None})

            for r in rows:
                src = None
                if r["price"]:
                    src = "official-web"
                else:
                    p = prices.get(norm(r["name"]))
                    if p:
                        r["price"], src, _ = p, "app-api", api_hit
                        api_hit += 1
                m = by_name.get(r["name"])
                if m is None:
                    m = {"name": r["name"], "price": r["price"], "price_source": src,
                         "weight_raw": r["weight"], "origin_raw": None,
                         "allergy_raw": r["allergy"],
                         "compose_raw": (r["compose"] or "").strip(" |") or None,
                         "name_en": r["en"],
                         "detail_url": durl,
                         "image_url": (WEB + it["img"]) if it.get("img") else None,
                         "ext_id": r["ext"], "cats": []}
                    by_name[r["name"]] = m
                    menus.append(m)
                m["cats"].append([cname, pos])
                pos += 1
        print("  %s : %d행" % (cname, pos))

    if not menus:
        print("메뉴 0건 — 파일을 저장하지 않는다.")
        return 1

    doc = {
        "brand": "배스킨라빈스", "slug": "baskinrobbins",
        "source": "① 앱 API(가격) — kr.co.baskinrobbins.client APK 의 libapp.so 에서 읽은 주소 "
                  "POST https://bra-brus.baskinrobbins.co.kr/api/pd/product/list body {} (무인증, 매장 판매가) · "
                  "② 공식 홈페이지(카테고리·순서·규격·중량·알레르기) https://www.baskinrobbins.co.kr "
                  "— 네비 Menu 드롭다운의 /menu/list.php?category=A|F|B|E · "
                  "/menu/list_subcategory.php?category=C|D · /menu/fom.php 와 각 상세(view.php/view_subcategory.php). "
                  "아이스크림 가격은 상세의 SELECT SIZE 표(규격별) 그대로.",
        "collected_at": time.strftime("%Y-%m-%d"),
        "cats": cats, "menus": menus,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    print("\n버린 줄 %d개" % len(dropped))
    for d in dropped:
        print("   ✂ " + d)
    print("18자 이상이라 걸렸지만 남긴 것 %d개" % len(flagged))
    for d in flagged[:40]:
        print("   ⚠ " + d)
    p = sum(1 for m in menus if m["price"])
    print("\n카테고리 %d개 · 메뉴 %d개 · 가격 있는 것 %d개 (홈페이지 %d · 앱API %d)"
          % (len(cats), len(menus), p, p - api_hit, api_hit))
    print("→ " + OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
