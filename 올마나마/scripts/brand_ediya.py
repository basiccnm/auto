# -*- coding: utf-8 -*-
"""이디야커피 메뉴판 — 공식 홈페이지에서 카테고리·메뉴를 긁어 **JSON 한 장**을 만든다. 2026-07-28

    python scripts/brand_ediya.py

⛔ 이 스크립트는 **DB 를 건드리지 않는다.** 만드는 건 `data/brand_menu_list/ediya.json` 뿐이다.

━━ ① 앱(APK) 경로 — **막다른 길이었다.** 다음에 또 파지 말 것 ━━━━━━━━━━━━━━━━━━━━
`com.ediya.coupon` (폰에 설치됨) 을 뽑아 뒤졌다. **네이티브 WebView 껍데기**다
(`assets/fingeWebInerface.js` = Finger 사의 웹↔앱 브리지. RN 번들 없음).
dex·resources 전체에서 나온 이디야 주소는 이게 전부다:

    https://memapp.ediya.com/          ← 앱이 띄우는 웹뷰(멤버십)
    https://members.ediya.com/
    https://sso.ediyastore.com/sso/ediya?token=
    https://www.ediya.com/contents/{coupon,catering,hanacard}.html
    https://ediya-members.firebaseio.com

🔴 `apiHost`·`apiCode`·`Headquarters-Code`·`__NUXT__` 문자열 **0건.** 설빙 방식은 안 통한다.
🔴 `https://memapp.ediya.com/` 를 한 번 열어봤더니 `{"result":{"code":"E0400","message":"잘못된 페이지 요청"}}` —
   로그인 뒤에야 들어가는 멤버십 앱이고 **메뉴판 API 가 아니다.** 더 찔러보지 않았다(추측 호출 금지).
→ 그래서 ② 홈페이지로 갔다.

━━ ② 홈페이지 (실제로 쓴 경로) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
서버 렌더 PHP. **헤드리스 불필요, `urllib` 로 다 읽힌다.**

🔴 상위 탭은 GNB 「메뉴」의 하위 3개다 — 음료 `/contents/drink.html` · 푸드 `/contents/bakery.html` ·
   MD `/contents/product.html`. (`/contents/md.html` 은 GNB 에서 주석 처리돼 **화면에 없다** → 안 쓴다)
🔴 각 페이지의 하위 카테고리는 `#blockcate` 안 체크박스다(`name="chkList"` 의 `value` = 코드).
   음료 10개 · 푸드 4개 · MD 는 체크박스가 없어 하위 없음.
🔴 카테고리로 거르는 주소는 페이지 JS `change_cate()` 에 적혀 있다(추측 아님):
       /contents/drink.html?chked_val=<코드>,&skeyword=
   **첫 화면(1쪽)은 그 HTML 안 `#menu_ul` 에 이미 들어 있고**, 그 다음 쪽은 `show_more()` 의
       POST /inc/ajax_brand.php?gubun=menu_more&product_cate=<7|8|9>&chked_val=<코드>,&skeyword=&page=<N>
   응답이 `none` 이면 끝이다.
🔴 `product_cate` 는 각 페이지 소스에 박혀 있다 — 음료 7 · 푸드 8 · MD 9.

🔴 상세를 따로 열 필요가 없다. **목록 `<li>` 안에 상세 팝업이 통째로 숨어 있다**(`div.pro_detail`):
   설명(`div.detail_txt`) · 영양(`div.pro_nutri`) · 용량/중량(`div.pro_size`) · 알레르기(`div.pro_allergy`).

🔴 **가격은 사이트 어디에도 없다** → `price:null`. 카페는 원래 그렇다.
🔴 원산지 표기도 없다 → `origin_raw:null`.

🔴 이름을 **합치지 마라.** 이디야는 사이즈·온도를 아예 다른 메뉴로 진열한다 —
   `(L) HOT 카페 아메리카노` · `(EX) ICED 카라멜 마끼아또`. 접두어를 지우면 다른 메뉴와 겹친다.
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
OUT = os.path.join(BASE, "data", "brand_menu_list", "ediya.json")

BRAND = "이디야커피"
SLUG = "ediya"
ROOT = "https://www.ediya.com"
AJAX = ROOT + "/inc/ajax_brand.php"
COLLECTED_AT = time.strftime("%Y-%m-%d")

# GNB 「메뉴」 하위 3개 — (탭이름, 페이지, product_cate)
TABS = [("음료", "/contents/drink.html", "7"),
        ("푸드", "/contents/bakery.html", "8"),
        ("MD", "/contents/product.html", "9")]

SOURCE = ("홈페이지(서버렌더). 상위탭 = GNB「메뉴」의 drink/bakery/product.html · "
          "하위카테고리 = 각 페이지 #blockcate 의 chkList 체크박스 value · "
          "1쪽 = <page>?chked_val=<코드>,&skeyword= 의 #menu_ul · "
          "2쪽부터 = POST %s?gubun=menu_more&product_cate=<7|8|9>&chked_val=<코드>,&skeyword=&page=N "
          "(그 페이지 JS 의 change_cate()/show_more()). "
          "앱(com.ediya.coupon)은 memapp.ediya.com 웹뷰 껍데기라 메뉴 API 없음" % AJAX)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}
GAP = 1.5
MAX_PAGE = 40                      # 안전판 — `none` 이 안 와도 무한루프 하지 않는다

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

RX_COMMENT = re.compile(r"(?s)<!--.*?-->")
RX_CATE = re.compile(r"<input type=\"checkbox\"\s+name=\"chkList\"\s+id=\"([^\"]+)\"\s+value=\"(\d+)\"")
RX_PCATE = re.compile(r"product_cate=(\d+)")
RX_LI = re.compile(r"(?s)<li>\s*<div class=\"pro_detail\"[^>]*id=\"nutri_(\d+)\"(.*?)</li>")
RX_NAME = re.compile(r"(?s)<div class=\"menu_tt\">\s*<a[^>]*>\s*<span>(.*?)</span>")
RX_H2 = re.compile(r"(?s)<h2>(.*?)</h2>")
RX_H2_EN = re.compile(r"(?s)<span>(.*?)</span>")
RX_DESC = re.compile(r"(?s)<div class=\"detail_txt\">(.*?)</div>")
RX_SIZE = re.compile(r"(?s)<div class=\"pro_size\">(.*?)</div>")
RX_ALLERGY = re.compile(r"(?s)<div class=\"pro_allergy\">(.*?)</div>")
RX_IMG = re.compile(r"<a href=\"#c\" onClick=\"show_nutri\('\d+'\)\"><img src=\"([^\"]+)\"", re.I)


def _decode(raw):
    for enc in ("utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return _decode(urllib.request.urlopen(req, timeout=30, context=CTX).read())


def post(url, referer):
    hdr = dict(UA, **{"X-Requested-With": "XMLHttpRequest", "Referer": referer,
                      "Content-Type": "application/x-www-form-urlencoded"})
    req = urllib.request.Request(url, data=b"", headers=hdr)
    return _decode(urllib.request.urlopen(req, timeout=30, context=CTX).read())


def strip(s):
    s = re.sub(r"(?is)<br\s*/?>", " ", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&nbsp;", " "), ("&#39;", "'"),
                 ("&quot;", '"'), ("&lt;", "<"), ("&gt;", ">"), ("&acute;", "'")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def blank(v):
    v = (v or "").strip()
    return None if v in ("", "-", "–", "—") else v


def parse_items(html):
    """`#menu_ul` 조각 → [{...}] · 버린 줄. 상세 팝업이 같은 `<li>` 안에 들어 있다."""
    rows, dropped = [], []
    for pid, body in RX_LI.findall(html):
        nm = RX_NAME.search(body)
        name = strip(nm.group(1)) if nm else ""
        if not name:                                     # 목록 표기가 없으면 팝업 h2 로 대체
            h2 = RX_H2.search(body)
            if h2:
                name = strip(RX_H2_EN.sub("", h2.group(1)))
        if not name:
            dropped.append(("(이름 없음) id=%s" % pid, "menu_tt·h2 둘 다 비었다"))
            continue
        d = RX_DESC.search(body)
        sz = RX_SIZE.search(body)
        al = RX_ALLERGY.search(body)
        im = RX_IMG.search(body)
        rows.append({
            "name": name, "price": None, "price_source": None,
            "weight_raw": blank(strip(sz.group(1))) if sz else None,
            "origin_raw": None,
            "allergy_raw": blank(strip(al.group(1))) if al else None,
            "compose_raw": blank(strip(d.group(1))) if d else None,
            "detail_url": None,                          # 상세 URL 이 없다(같은 페이지 팝업)
            "image_url": ROOT + im.group(1) if im and im.group(1).startswith("/") else
                         (im.group(1) if im else None),
            "ext_id": pid, "cats": [],
        })
    return rows, dropped


def menu_ul(html):
    i = html.find('id="menu_ul"')
    return html[i:] if i >= 0 else ""


def main():
    cats, groups, dropped_all = [], [], []
    for top, page, pcate in TABS:
        html = RX_COMMENT.sub("", get(ROOT + page))
        subs = [(strip(nm), code) for nm, code in RX_CATE.findall(html)]
        pc = RX_PCATE.search(html)
        if pc and pc.group(1) != pcate:
            print("  ⚠️ %s 의 product_cate 가 %s → %s 로 바뀌었다" % (top, pcate, pc.group(1)))
            pcate = pc.group(1)
        cats.append({"name": top, "parent": None, "ext_id": pcate})
        for nm, code in subs:
            cats.append({"name": nm, "parent": top, "ext_id": code})
        groups.append((top, page, pcate, subs))
        print("  %-6s(product_cate=%s) %s" % (top, pcate, " · ".join(n for n, _ in subs) or "(하위 없음)"))
        time.sleep(GAP)

    if not cats:
        print("🔴 카테고리 0개 — **화면 구조가 바뀌었다.** 파일을 쓰지 않는다")
        return

    items, order = {}, []

    def take(path, rows):
        for i, r in enumerate(rows):
            it = items.get(r["ext_id"])
            if it is None:
                it = dict(r)
                items[r["ext_id"]] = it
                order.append(r["ext_id"])
            it["cats"].append([path, i])

    for top, page, pcate, subs in groups:
        targets = subs if subs else [(None, "")]
        for nm, code in targets:
            path = "%s/%s" % (top, nm) if nm else top
            ref = "%s%s?chked_val=%s&skeyword=" % (ROOT, page, code + "," if code else "")
            rows, drop = parse_items(menu_ul(RX_COMMENT.sub("", get(ref))))
            dropped_all += [(path, a, b) for a, b in drop]
            time.sleep(GAP)
            for pg in range(2, MAX_PAGE + 1):
                url = ("%s?gubun=menu_more&product_cate=%s&chked_val=%s&skeyword=&page=%d"
                       % (AJAX, pcate, code + "," if code else "", pg))
                more = post(url, ref).strip()
                if not more or more == "none":
                    break
                got, drop = parse_items(RX_COMMENT.sub("", more))
                dropped_all += [(path, a, b) for a, b in drop]
                if not got:
                    break
                rows += got
                time.sleep(GAP)
            take(path, rows)
            print("  %-22s %3d개%s" % (path, len(rows), "  ⛔버림 %d" % len(drop) if drop else ""),
                  flush=True)

    if not order:
        print("🔴 메뉴 0건 — **화면 구조가 바뀌었다.** 조용히 빈 JSON 을 쓰지 않는다")
        return

    cat_names = {c["name"] for c in cats}
    suspicious = []
    for pid in order:
        nm = items[pid]["name"]
        why = ("카테고리 이름과 같다" if nm in cat_names else
               "문장부호로 끝난다" if re.search(r"[.!?~]$", nm) else
               "18자 이상" if len(nm) >= 18 else None)
        if why:
            suspicious.append((nm, why))

    doc = {"brand": BRAND, "slug": SLUG, "source": SOURCE, "collected_at": COLLECTED_AT,
           "cats": cats, "menus": [items[p] for p in order]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    chk = json.load(io.open(OUT, encoding="utf-8"))
    sub_n = sum(1 for c in chk["cats"] if c.get("parent"))
    n_price = sum(1 for m in chk["menus"] if m.get("price") is not None)
    n_c = sum(1 for m in chk["menus"] if m.get("compose_raw"))
    n_w = sum(1 for m in chk["menus"] if m.get("weight_raw"))
    n_a = sum(1 for m in chk["menus"] if m.get("allergy_raw"))
    links = sum(len(m["cats"]) for m in chk["menus"])
    print("\n■ %s — 카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (BRAND, len(chk["cats"]), sub_n, len(chk["menus"]), n_price))
    print("  설명 %d · 용량/중량 %d · 알레르기 %d · 원산지 0 (사이트에 표기가 없다)" % (n_c, n_w, n_a))
    print("  카테고리 배치 %d자리 · 중복 진열 %d건" % (links, links - len(chk["menus"])))
    print("  💰 가격 = 0개. 이디야 홈페이지는 판매가를 **아예 공개하지 않는다**")
    print("  ℹ️ 사이즈·온도가 이름에 그대로 있다((L)/(EX) · HOT/ICED) — **합치지 않았다**")
    if suspicious:
        print("  ⚠️ 길이·형태 규칙에 걸린 이름 %d개 — **지우지 않고 남겼다.** 눈으로 볼 것:" % len(suspicious))
        for nm, why in suspicious:
            print("     · %-44s %s" % (nm[:44], why))
    if dropped_all:
        print("  ⛔ 버린 줄 %d개:" % len(dropped_all))
        for where, nm, why in dropped_all[:20]:
            print("     · [%s] %s — %s" % (where, nm, why))
    else:
        print("  ⛔ 버린 줄 없음")
    print("\n  → %s" % OUT)


if __name__ == "__main__":
    main()
