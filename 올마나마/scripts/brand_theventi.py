# -*- coding: utf-8 -*-
"""더벤티 메뉴판 — 공식 홈페이지에서 카테고리·메뉴를 긁어 **JSON 한 장**을 만든다. 2026-07-28

    python scripts/brand_theventi.py

⛔ 이 스크립트는 **DB 를 건드리지 않는다.** 만드는 건 `data/brand_menu_list/theventi.json` 뿐이다.

━━ ① 앱(APK) 경로 — **막다른 길이었다.** 다음에 또 파지 말 것 ━━━━━━━━━━━━━━━━━━━━
`kr.co.theventi` (폰에 설치됨) 를 뽑아 뒤졌다. React Native 앱 · `assets/index.android.bundle`(3.5MB).

    https://theventi-apis.softment.co.kr/v1     ← 앱 API 베이스(softment 제작)
    https://app.theventi.co.kr                  ← 앱 웹뷰
    https://theventi.multicon.co.kr/login       ← 로그인(멀티콘)
    https://theventi.co.kr/bridge/appstore.html

번들 문자열 풀에 남아 있던 엔드포인트는 **전부 주문·회원용**이다:
`/order/pickup/shops` · `/order/deliveryOrders` · `/order/reserve` · `/ord/orderResult` ·
`/shop/status` · `/shop/deliveryStatus` · `/product/mycup` · `/coupon/hold` · `/stamp/hold` ·
`/main/banner` · `/menu/event` · `/user?scope=MYINFO` · `/view/payco/shop/pickupOrder`
🔴 **메뉴판(카테고리+상품) 목록 엔드포인트가 없다.** 주문 화면은 payco 웹뷰로 넘긴다.
   번들에 있던 `/v1/menu` 를 한 번 확인했더니 `{"success":false,"code":-9000,"Cannot GET /v1/menu"}` —
   **더 찔러보지 않았다**(주소 조합·추측 호출 금지).
→ 그래서 ② 홈페이지로 갔다.

━━ ② 홈페이지 (실제로 쓴 경로) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
서버 렌더. **헤드리스 불필요, `urllib` 로 다 읽힌다.**

🔴 `theventi.co.kr` 루트는 `/new2022/main/intro.html` 로 튄다. 전체메뉴는
       https://www.theventi.co.kr/new2022/menu/all.html?mode=N   (N = 1~8)
   탭 이름·순서는 그 페이지 `<ul class="tab box">` 의 `?mode=N` 링크 그대로다.

🔴 목록의 `<p class="type">` 안 `<i class='hot'>` / `<i class='ice'>` 아이콘이
   그 메뉴의 HOT/ICE 제공 여부다 → `type_raw` 에 원문 그대로 남긴다.
   ⚠️ **HOT/ICE 를 별개 메뉴로 쪼개지 않았다.** 사이트가 한 줄로 진열하고 **가격이 없어서**
      쪼갤 근거가 없기 때문이다(가격이 다르면 쪼갠다는 규칙의 전제가 성립 안 함).
      크기 구분은 이름에 이미 `(라지/점보)` 로 박혀 있어 **이름을 그대로 둔다.**

🔴 상세는 팝업 조각이다(레이아웃 없는 1~2KB HTML):
       https://www.theventi.co.kr/new2022/menu/all-view.new.html?uid=<uid>
   여기서 설명문(`div.txt`) · 1회 제공량(`ICE : 600ml / HOT : 600ml`) · 알레르기를 얻는다.

🔴 **가격은 사이트 어디에도 없다.** 목록·상세 모두 없음 → `price:null`. 카페는 원래 그렇다.
🔴 원산지 표기도 없다 → `origin_raw:null` (없는 것을 지어내지 않는다).

이름은 **다듬지 않는다.** `(라지/점보)`·`(디카페인)` 을 지우면 검증이 안 된다.
"""
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "theventi.json")

BRAND = "더벤티"
SLUG = "theventi"
ROOT = "https://www.theventi.co.kr"
LIST = ROOT + "/new2022/menu/all.html"
DETAIL = ROOT + "/new2022/menu/all-view.new.html"
COLLECTED_AT = time.strftime("%Y-%m-%d")

SOURCE = ("홈페이지(서버렌더). 탭·메뉴 = GET %s?mode=1~8 (탭 이름·순서는 그 페이지 ul.tab box) · "
          "설명/제공량/알레르기 = GET %s?uid=<uid> (팝업 조각). "
          "앱(kr.co.theventi)은 RN 주문·회원앱이라 메뉴판 API 없음 — "
          "번들에 theventi-apis.softment.co.kr/v1 의 order/shop/coupon 계열만 있음"
          % (LIST, DETAIL))

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}
GAP = 1.5

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

RX_COMMENT = re.compile(r"(?s)<!--.*?-->")
RX_TABBOX = re.compile(r"(?s)<ul class=\"tab box\">.*?</ul>")
RX_TAB_A = re.compile(r"\?mode=(\d+)\"[^>]*>([^<]*)</a>")
RX_ITEM = re.compile(r"(?s)<li class=\"[^\"]*item\"><a href=\"([^\"]*all-view\.new\.html\?uid=(\d+))\""
                     r".*?<img src=\"([^\"]*)\".*?<p class=\"type\">(.*?)</p>"
                     r"\s*<p class=\"tit\">(.*?)</p>")
RX_TYPE_I = re.compile(r"<i class='([a-z]+)'")
RX_D_TIT = re.compile(r"(?s)<p class=\"tit\">(.*?)</p>")
RX_D_TXT = re.compile(r"(?s)<div class=\"txt scroll-con-y\">(.*?)</div>")
RX_D_TABLE = re.compile(r"(?s)<table class=\"table\">(.*?)</table>")
RX_TR = re.compile(r"(?s)<tr>(.*?)</tr>")
RX_TD = re.compile(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>")


def _decode(raw):
    for enc in ("utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return RX_COMMENT.sub("", _decode(urllib.request.urlopen(req, timeout=30, context=CTX).read()))


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                 ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def blank(v):
    v = (v or "").strip()
    return None if v in ("", "-", "–", "—") else v


def parse_detail(html):
    """(compose_raw, weight_raw, allergy_raw) — 팝업 조각에서"""
    tx = RX_D_TXT.search(html)
    compose = blank(strip(tx.group(1))) if tx else None

    weight = allergy = None
    tb = RX_D_TABLE.search(html)
    if tb:
        rows = [[strip(c) for c in RX_TD.findall(tr)] for tr in RX_TR.findall(tb.group(1))]
        rows = [r for r in rows if r]
        if len(rows) >= 2:
            head, body = rows[0], rows[1]
            for i, h in enumerate(head):
                if i >= len(body):
                    break
                k = h.replace(" ", "")
                if "제공량" in k:
                    weight = blank(body[i])
                elif "알레르기" in k:
                    allergy = blank(body[i])
    return compose, weight, allergy


def main():
    first = get(LIST + "?mode=1")
    tb = RX_TABBOX.search(first)
    if not tb:
        print("🔴 탭 0개 — **화면 구조가 바뀌었다.** 파일을 쓰지 않는다")
        return
    tabs = [(m, strip(n)) for m, n in RX_TAB_A.findall(tb.group(0))]
    tabs = [(m, n) for m, n in tabs if n]
    print("  탭 %d개: %s" % (len(tabs), " · ".join(n for _, n in tabs)))

    cats = [{"name": n, "parent": None, "ext_id": m} for m, n in tabs]

    items, order, dropped = {}, [], []
    for k, (mode, name) in enumerate(tabs):
        html = first if mode == "1" else get("%s?mode=%s" % (LIST, mode))
        rows = RX_ITEM.findall(html)
        n_in = 0
        for href, uid, img, typ, tit in rows:
            nm = strip(tit)
            if not nm:
                dropped.append((name, "(이름 없음) uid=%s" % uid, "p.tit 이 비었다"))
                continue
            it = items.get(uid)
            if it is None:
                kinds = [x.upper() for x in RX_TYPE_I.findall(typ)]
                it = {"name": nm, "price": None, "price_source": None,
                      "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                      "compose_raw": None, "type_raw": "/".join(kinds) or None,
                      "detail_url": "%s?uid=%s" % (DETAIL, uid),
                      "image_url": img.replace("http://", "https://") if img else None,
                      "ext_id": uid, "cats": []}
                items[uid] = it
                order.append(uid)
            it["cats"].append([name, n_in])
            n_in += 1
        print("  %-16s %3d개" % (name, n_in), flush=True)
        if mode != "1" or k:
            time.sleep(GAP)

    if not order:
        print("🔴 메뉴 0건 — **화면 구조가 바뀌었다.** 조용히 빈 JSON 을 쓰지 않는다")
        return

    print("\n  상세 %d건 읽는 중 (약 %d초)…" % (len(order), int(len(order) * GAP)))
    n_c = n_w = n_a = 0
    for k, uid in enumerate(order):
        it = items[uid]
        try:
            c, w, a = parse_detail(get(it["detail_url"]))
        except Exception as e:
            dropped.append(("-", it["name"], "상세 실패 %r" % (e,)))
            time.sleep(GAP)
            continue
        it["compose_raw"], it["weight_raw"], it["allergy_raw"] = c, w, a
        n_c += bool(c)
        n_w += bool(w)
        n_a += bool(a)
        if (k + 1) % 25 == 0:
            print("    %d/%d" % (k + 1, len(order)), flush=True)
        time.sleep(GAP)

    cat_names = {c["name"] for c in cats}
    suspicious = []
    for uid in order:
        nm = items[uid]["name"]
        why = ("카테고리 이름과 같다" if nm in cat_names else
               "문장부호로 끝난다" if re.search(r"[.!?~]$", nm) else
               "18자 이상" if len(nm) >= 18 else None)
        if why:
            suspicious.append((nm, why))

    doc = {"brand": BRAND, "slug": SLUG, "source": SOURCE, "collected_at": COLLECTED_AT,
           "cats": cats, "menus": [items[u] for u in order]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    chk = json.load(io.open(OUT, encoding="utf-8"))
    sub_n = sum(1 for c in chk["cats"] if c.get("parent"))
    n_price = sum(1 for m in chk["menus"] if m.get("price") is not None)
    links = sum(len(m["cats"]) for m in chk["menus"])
    print("\n■ %s — 카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (BRAND, len(chk["cats"]), sub_n, len(chk["menus"]), n_price))
    print("  설명 %d · 제공량 %d · 알레르기 %d · 원산지 0 (사이트에 표기가 없다)" % (n_c, n_w, n_a))
    # ℹ️ 실측(2026-07-28) 중복 0건 — 「신메뉴」 탭은 다른 탭과 **uid 가 겹치지 않는다**
    #    (신메뉴는 `upload/menu_new/` 로 따로 등록된 별개 행이다). 겹치면 여기 숫자가 올라간다.
    print("  카테고리 배치 %d자리 · 중복 진열 %d건" % (links, links - len(chk["menus"])))
    print("  💰 가격 = 0개. 더벤티 홈페이지는 판매가를 **아예 공개하지 않는다**(목록·상세 모두 없음)")
    if suspicious:
        print("  ⚠️ 길이·형태 규칙에 걸린 이름 %d개 — **지우지 않고 남겼다.** 눈으로 볼 것:" % len(suspicious))
        for nm, why in suspicious:
            print("     · %-44s %s" % (nm[:44], why))
    if dropped:
        print("  ⛔ 버린 줄 %d개:" % len(dropped))
        for where, nm, why in dropped:
            print("     · [%s] %s — %s" % (where, nm, why))
    else:
        print("  ⛔ 버린 줄 없음")
    print("\n  → %s" % OUT)


if __name__ == "__main__":
    main()
