# -*- coding: utf-8 -*-
"""폴바셋(paulbassett) 공식 홈페이지 메뉴 수집 — 골격(카테고리·메뉴명·순서) 전용.

■ 도메인 주의: 지시받은 `paulbassett.co.kr` 은 **DNS 가 없다**(getaddrinfo failed, www 도 동일).
   실제 공식 사이트는 **https://www.baristapaulbassett.co.kr** (엠즈씨드㈜, 사업자 211-88-95935).
   WebSearch 로 확인했고, 그 페이지의 네비게이션 링크만 따라간다.

■ 경로: 홈페이지 (서버 렌더링 JSP — urllib 로 그대로 읽힌다). 앱은 폰에 미설치.
     /menu/List.pb                     상단 탭(cid1) 목록이 여기 적혀 있다
     /menu/List.pb?cid1=A|B|C|D|E      대분류 (전체)
     /menu/List.pb?cid1=A&cid2=B ...   소분류 — 각 대분류 페이지의 ul.listTab 에 적힌 링크만 따라간다
     /menu/new/List.pb                 NEW
     /menu/View.pb?dpid=PB######       상세 — 구분/우유선택/알레르기/제공사이즈/제공량(ml·g)
   목록 항목은 onclick="goView('PB######')" 로 dpid 가 박혀 있다.

■ 가격: **홈페이지 어디에도 없다.** 목록·상세 모두 판매가 표기가 없고,
   /js/common.js · ui.js · efusioni.js 에도 price/prc/amt 류 문자열이 0건 — 부를 API 가 없다.
   → price 는 전부 null. (앱이 깔리면 그쪽에서 채울 것)

⛔ DB 를 import 하지 않는다. 결과는 data/brand_menu_list/paulbassett.json 한 장.
"""
import sys, os, re, json, time, html, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://www.baristapaulbassett.co.kr"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
SLEEP = 1.6
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "brand_menu_list", "paulbassett.json")

_last = [0.0]


def get(url):
    dt = time.time() - _last[0]
    if dt < SLEEP:
        time.sleep(SLEEP - dt)
    _last[0] = time.time()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as f:
        b = f.read()
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("euc-kr", "replace")


def nocmt(h):
    return re.sub(r"<!--[\s\S]*?-->", "", h)


def text(s):
    s = re.sub(r"<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def read_top_cats():
    """상단 탭(cid1) — /menu/List.pb 의 대분류 ul 순서 그대로. NEW 를 맨 앞에 둔다."""
    h = nocmt(get(BASE + "/menu/List.pb"))
    seen, out = set(), []
    # ⛔ NEW(/menu/new/List.pb) 는 메뉴 목록이 아니다 — div.newMenuList 에 날짜(span.date)가 붙은
    #    «신제품 소개» 홍보 배너 글이다(«SWEET YELLOW, SUMMER 2026.07.14» 같은). 그래서 넣지 않는다.
    for cid, label in re.findall(r'href="/menu/List\.pb\?cid1=([A-Z])"[^>]*>([^<]+)</a>', h):
        lab = text(label)
        if cid in seen or not lab or lab == "전체":
            continue
        seen.add(cid)
        out.append((lab, "/menu/List.pb?cid1=%s" % cid, cid))
    return out


def read_sub_tabs(page, cid1):
    """대분류 페이지의 소분류 링크만.
    ⚠️ 페이지에 ul.listTab 이 두 개다 — 앞의 것은 대분류(cid1)뿐이라 그걸 잡으면 하위가 0개가 된다.
       cid2 링크가 실제로 들어 있는 ul 을 골라야 한다."""
    out = []
    for blk in re.findall(r'<ul class="listTab[^"]*">([\s\S]*?)</ul>', page):
        pairs = re.findall(
            r'href="/menu/List\.pb\?cid1=%s&(?:amp;)?cid2=([A-Z])"[^>]*>([^<]+)</a>' % cid1, blk)
        if not pairs:
            continue
        for cid2, label in pairs:
            out.append((text(label), cid2))
        break
    return out


def read_items(page):
    """목록의 li — goView('dpid') + 한글명 + 영문명(span.sTxt) + 썸네일."""
    if "newMenuList" in page:        # 신제품 «홍보 배너» 목록 — 메뉴가 아니다
        return []
    m = re.search(r'<div class="menuList">([\s\S]*?)</div>\s*<!--\s*//?\s*menuList|'
                  r'<div class="menuList">([\s\S]*)', page)
    block = (m.group(1) or m.group(2)) if m else page
    out = []
    for it in re.finditer(
            r"goView\('([^']+)'\)[\s\S]*?<img[^>]+src=\"([^\"]*)\"[\s\S]*?"
            r'<div class="txtArea">([\s\S]*?)</div>', block):
        dpid, img, txt = it.group(1), it.group(2), it.group(3)
        en = ""
        m2 = re.search(r'<span class="sTxt">([\s\S]*?)</span>', txt)
        if m2:
            en = text(m2.group(1))
        ko = text(re.sub(r'<span class="sTxt">[\s\S]*?</span>', "", txt))
        if not ko:
            continue
        out.append({"dpid": dpid, "name": ko, "en": en or None, "img": img or None})
    return out


def read_detail(dpid):
    h = nocmt(get("%s/menu/View.pb?dpid=%s" % (BASE, dpid)))
    i = h.find('class="menuInfoWrap"')
    body = h[i:h.find("bestMenu", i)] if i > 0 else h
    d = {"desc": None, "allergy": None, "origin": None, "info": [], "sizes": []}
    m = re.search(r"<dd>([\s\S]*?)</dd>", body)
    if m:
        d["desc"] = text(m.group(1)) or None
    m = re.search(r'<ul class="info">([\s\S]*?)</ul>', body)
    if m:
        for li in re.findall(r"<li>([\s\S]*?)</li>", m.group(1)):
            mm = re.match(r"\s*<span>([\s\S]*?)</span>([\s\S]*)", li)
            if not mm:
                continue
            k, v = text(mm.group(1)), text(mm.group(2))
            if not v:
                continue
            if "알레르기" in k:
                d["allergy"] = v
            elif "원산지" in k:
                d["origin"] = v
            else:
                d["info"].append("%s: %s" % (k, v))
    for opt, label in re.findall(r'<option value="([^"]*)"[^>]*>([^<]*)</option>', body):
        mm = re.search(r'id="pSize_%s"[\s\S]*?class="sizeMl">([\s\S]*?)</span>\s*</span>' % re.escape(opt), body)
        amt = text(mm.group(1)) if mm else ""
        d["sizes"].append("%s %s" % (text(label), amt) if amt else text(label))
    return d


def main():
    top = read_top_cats()
    print("상단 탭: " + " / ".join(c for c, _, _ in top))

    cats, menus = [], []
    by_dpid = {}          # dpid -> menu dict (한 메뉴가 여러 소분류에 걸린다)
    dropped, flagged = [], []
    catnames = {c for c, _, _ in top}

    for cname, path, cid1 in top:
        cats.append({"name": cname, "parent": None, "ext_id": cid1})
        page = nocmt(get(BASE + path))
        items = read_items(page)
        pos = 0
        for it in items:
            nm = it["name"]
            if nm in catnames:
                dropped.append("%s / %s ← 카테고리 이름과 같음" % (cname, nm))
                continue
            if re.search(r"[.!?]$", nm):
                dropped.append("%s / %s ← 문장부호로 끝남" % (cname, nm))
                continue
            if len(nm) >= 18:
                flagged.append("%s / %s (%d자 — 사이트 메뉴명이라 남김)" % (cname, nm, len(nm)))
            m = by_dpid.get(it["dpid"])
            if m is None:
                m = {"name": nm, "price": None, "price_source": None,
                     "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                     "compose_raw": None, "name_en": it["en"],
                     "detail_url": "%s/menu/View.pb?dpid=%s" % (BASE, it["dpid"]),
                     "image_url": (BASE + it["img"]) if it["img"] else None,
                     "ext_id": it["dpid"], "cats": []}
                by_dpid[it["dpid"]] = m
                menus.append(m)
            m["cats"].append([cname, pos])
            pos += 1
        print("  %s : %d개" % (cname, pos))

        if not cid1:
            continue
        for sname, cid2 in read_sub_tabs(page, cid1):
            sub_path = "%s/%s" % (cname, sname)
            cats.append({"name": sname, "parent": cname, "ext_id": "%s%s" % (cid1, cid2)})
            sp = nocmt(get("%s/menu/List.pb?cid1=%s&cid2=%s" % (BASE, cid1, cid2)))
            spos = 0
            for it in read_items(sp):
                m = by_dpid.get(it["dpid"])
                if m is None:
                    continue
                m["cats"].append([sub_path, spos])
                spos += 1
            print("     └ %s : %d개" % (sname, spos))

    if not menus:
        print("메뉴 0건 — 파일을 저장하지 않는다.")
        return 1

    print("\n상세 %d건 읽는 중 (약 %d초)..." % (len(menus), int(len(menus) * SLEEP)))
    for n, m in enumerate(menus, 1):
        try:
            d = read_detail(m["ext_id"])
        except Exception as e:
            print("   ⚠️ 상세 실패 %s %r" % (m["ext_id"], e))
            continue
        m["allergy_raw"] = d["allergy"]
        m["origin_raw"] = d["origin"]
        m["weight_raw"] = " · ".join(d["sizes"]) or None
        parts = [p for p in ([d["desc"]] + d["info"]) if p]
        m["compose_raw"] = " | ".join(parts) or None
        if n % 25 == 0:
            print("   %d/%d" % (n, len(menus)))

    doc = {
        "brand": "폴바셋", "slug": "paulbassett",
        "source": "공식 홈페이지 https://www.baristapaulbassett.co.kr — /menu/List.pb 의 대분류 탭과 "
                  "각 대분류 페이지 ul.listTab 의 소분류 링크를 따라가 목록을 읽고, 각 항목의 "
                  "goView('dpid') 로 /menu/View.pb?dpid=… 상세(구분·우유선택·알레르기·제공사이즈·제공량)를 "
                  "urllib 로 파싱. ⚠️ 지시받은 paulbassett.co.kr 은 DNS 가 없어 이 도메인을 썼다. "
                  "홈페이지·JS 어디에도 판매가가 없어 price 는 전부 null.",
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
    for d in flagged[:30]:
        print("   ⚠ " + d)
    sub = sum(1 for c in cats if c["parent"])
    print("\n카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (len(cats), sub, len(menus), sum(1 for m in menus if m["price"])))
    print("→ " + OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
