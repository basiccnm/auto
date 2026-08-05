# -*- coding: utf-8 -*-
"""공차 메뉴판 — 공식 홈페이지에서 카테고리·메뉴를 긁어 **JSON 한 장**을 만든다. 2026-07-28

    python scripts/brand_gongcha.py

⛔ 이 스크립트는 **DB 를 건드리지 않는다.** 만드는 건 `data/brand_menu_list/gongcha.json` 뿐이다.
   `brand_menu_store` 를 import 하지 않는다.

━━ ① 앱(APK) 경로 — **막다른 길이었다.** 다음에 또 파지 말 것 ━━━━━━━━━━━━━━━━━━━━
`com.easymembership.gongcha` (폰에 설치됨) 를 뽑아 뒤졌다.

    adb shell pm path com.easymembership.gongcha
    → /data/app/~~11gofQx8Au7otCxxHgeHwg==/com.easymembership.gongcha-*/base.apk (41MB)

React Native 앱이라 `assets/index.android.bundle`(3.4MB) 한 장에 문자열이 다 있다. 거기서 나온 주소는:

    https://gongcha.apis.flyground.co.kr/v1     ← @flyground-rn/api-client 의 apiUrl (멤버십)
    https://gongcha.logs.flyground.co.kr        ← 로그
    https://id.gong-cha.co.kr                   ← 로그인
    https://www.gong-cha.co.kr/brand/html/21    ← 웹뷰(대량구매)
    https://www.gong-cha.co.kr/brand/customer/  ← 웹뷰(고객센터)

🔴 **메뉴 엔드포인트는 없다.** 리덕스 액션도 `SHOP/…` `MEMBER/…` `PAYCO/…` `BOARD/…` 뿐이고
   `MENU/…` `PRODUCT/…` 가 없다. 즉 이 앱은 **멤버십·매장찾기 앱**이고 메뉴판을 들고 있지 않다.
🔴 설빙을 뚫은 `app-api.easymembership.co.kr` + `Headquarters-Code` 방식은 **여기 안 통한다.**
   패키지 이름만 `easymembership` 이지 번들·dex·resources 어디에도
   `easymembership` · `Headquarters` · `apiHost` · `apiCode` · `__NUXT__` 문자열이 **0건**이다.
   (코드값을 추측해 찔러보지 않았다 — 추측 호출은 금지다)
→ 그래서 ② 홈페이지로 갔다.

━━ ② 홈페이지 (실제로 쓴 경로) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
서버 렌더 PHP. **헤드리스 불필요, `urllib` 로 다 읽힌다.**

🔴 `gong-cha.co.kr` 루트는 「가맹문의 / 브랜드 소개」 두 장짜리 인트로다. 메뉴는 `/brand` 아래에 있다.
   상위 탭(음료·푸드·MD상품)은 `/brand/menu/product?category=001001` 의 `sub-gnb-wrap` 에,
   그 안의 하위 탭은 같은 페이지 `tabWrap` 의 `data-cate` 에 있다.

🔴 하위 탭을 누르면 **페이지가 부르는 AJAX** 로 목록만 갈아끼운다 — 주소는 그 페이지 인라인 JS
   `getList()` 안에 적혀 있다(추측한 주소가 아니다):
       GET /brand/menu/ajaxlist?category=<data-cate>
   같은 자리 `getNutritionList()` 는 `/brand/menu/product_nutrition` 인데
   **카테고리 인자를 무시하고 음료 전체 표를 준다**(메뉴명·구분·사이즈·제공량ml·알레르기).
   → 우리는 메뉴별 상세를 어차피 열어야 해서 이건 쓰지 않는다.

🔴 「New 시즌 메뉴」 탭에만 `<h3>` 시리즈 묶음이 한 겹 더 있다(26' 써머 시리즈 · 저당 밀크티 시리즈 …).
   화면에 그렇게 보이므로 **3단 카테고리로 그대로 남긴다**(음료/New 시즌 메뉴/26' 써머 시리즈).
   같은 메뉴를 상위(탭)에도 함께 걸어 둔다.

🔴 **가격은 사이트 어디에도 없다.** 목록에도 상세에도 없다 → `price:null`. 카페는 원래 그렇다.
   상세(`/brand/menu/product_detail?category=&no=`)에서 얻는 건
   설명문(`p.t2`) · 영양표(제공량 ml/g) · 알레르기(`p.caution`) 뿐이다.

이름은 **다듬지 않는다.** `+펄`·`BIG 컵`·`1L`·`G` 를 지우면 검증이 안 된다.
"""
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")     # 콘솔이 cp949 라 이모지에서 죽는다

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "brand_menu_list", "gongcha.json")

BRAND = "공차"
SLUG = "gongcha"
ROOT = "https://www.gong-cha.co.kr"
ENTRY = ROOT + "/brand/menu/product?category=001001"
LIST_API = ROOT + "/brand/menu/ajaxlist"                # 페이지 인라인 JS 의 getList()
DETAIL = ROOT + "/brand/menu/product_detail"
COLLECTED_AT = time.strftime("%Y-%m-%d")

SOURCE = ("홈페이지(서버렌더). 상위탭·하위탭 = %s 의 sub-gnb-wrap / tabWrap[data-cate] · "
          "메뉴목록 = GET %s?category=<data-cate> (그 페이지 인라인 JS getList()) · "
          "설명/영양/알레르기 = GET %s?category=&no= . "
          "앱(com.easymembership.gongcha)은 RN 멤버십앱이라 메뉴 API 없음 — "
          "번들에 flyground.co.kr/v1(멤버십)만 있고 MENU/PRODUCT 엔드포인트 0건"
          % (ENTRY, LIST_API, DETAIL))

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}
GAP = 1.5

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

RX_COMMENT = re.compile(r"(?s)<!--.*?-->")
RX_GNB = re.compile(r"(?s)<div class=\"sub-gnb-wrap[^\"]*\">.*?</ul>")
RX_GNB_A = re.compile(r"href=\"/brand/menu/product\?category=(\d+)[^\"]*\">([^<]+)</a>")
RX_TABW = re.compile(r"(?s)<div class=\"tabWrap\">.*?</ul>")
RX_TAB_A = re.compile(r"data-cate=\"(\d+)\"[^>]*>([^<]+)<")
RX_H3 = re.compile(r"(?s)<h3[^>]*>(.*?)</h3>")
RX_HREF = re.compile(r"<a href=\"(/brand/menu/product_detail\?category=\d+&no=(\d+)[^\"]*)\"")
RX_IMG = re.compile(r"<img src=\"([^\"]+)\"")
RX_NAME = re.compile(r"(?s)<div class=\"text-a\">\s*<p>(.*?)</p>")
RX_T1 = re.compile(r"(?s)<p class=\"t1[^\"]*\">(.*?)</p>")
RX_T2 = re.compile(r"(?s)<p class=\"t2[^\"]*\">(.*?)</p>")
RX_CAUTION = re.compile(r"(?s)<p class=\"caution[^\"]*\">(.*?)</p>")
RX_TABLE = re.compile(r"(?s)<div class=\"menu-detail-conts\">.*?<table>(.*?)</table>")
RX_TR = re.compile(r"(?s)<tr>(.*?)</tr>")
RX_TD = re.compile(r"(?s)<t[dh]([^>]*)>(.*?)</t[dh]>")
RX_COLSPAN = re.compile(r"colspan=\"?(\d+)")


def cells(tr):
    """`colspan` 을 펼쳐서 돌려준다.

    🔴 음료 영양표 머리글이 `<th colspan="2">구분</th>` 이다. 펼치지 않으면 머리글 8칸 · 본문 9칸이라
       「1회 제공량」 자리가 **한 칸씩 밀려** 사이즈(`L`)를 용량으로 읽는다(실제로 `Cold Lml` 이 나왔다).
    """
    out = []
    for attr, body in RX_TD.findall(tr):
        m = RX_COLSPAN.search(attr)
        out += [strip(body)] * (int(m.group(1)) if m else 1)
    return out


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


# ─────────────────────────────── 카테고리 ───────────────────────────────
def read_page_cats(html):
    """(상위 [(code,이름)], 하위 [(code,이름)]) — 상위는 sub-gnb, 하위는 tabWrap"""
    g = RX_GNB.search(html)
    t = RX_TABW.search(html)
    tops = [(c, strip(n)) for c, n in RX_GNB_A.findall(g.group(0))] if g else []
    subs = [(c, strip(n)) for c, n in RX_TAB_A.findall(t.group(0))] if t else []
    return tops, subs


# ─────────────────────────────── 목록 ───────────────────────────────
def parse_list(html):
    """[(시리즈이름 또는 None, [(no, name, detail_url, image_url)])] — 화면 순서 그대로

    「New 시즌 메뉴」만 `<h3>` 시리즈 묶음이 있다. 없으면 묶음 하나(None)로 본다.
    """
    hits = list(RX_H3.finditer(html))
    if not hits:
        return [(None, _items(html))]
    out = []
    if hits[0].start() > 0:
        head = _items(html[:hits[0].start()])
        if head:
            out.append((None, head))
    for n, m in enumerate(hits):
        end = hits[n + 1].start() if n + 1 < len(hits) else len(html)
        out.append((strip(m.group(1)), _items(html[m.end():end])))
    return out


def _items(chunk):
    rows = []
    for li in re.split(r"(?s)<li[ >]", chunk)[1:]:
        h = RX_HREF.search(li)
        n = RX_NAME.search(li)
        if not h or not n:
            continue
        nm = strip(n.group(1))
        if not nm:
            continue
        img = RX_IMG.search(li)
        src = img.group(1).split("?")[0] if img else None
        rows.append((h.group(2), nm,
                     ROOT + h.group(1).replace("&scroll=y", "").replace("&amp;", "&"),
                     (ROOT + src) if src and src.startswith("/") else src))
    return rows


# ─────────────────────────────── 상세 ───────────────────────────────
def parse_detail(html):
    """(compose_raw, weight_raw, allergy_raw)"""
    t2 = RX_T2.search(html)
    compose = blank(strip(t2.group(1))) if t2 else None

    weight = None
    tb = RX_TABLE.search(html)
    if tb:
        rows = [c for c in (cells(tr) for tr in RX_TR.findall(tb.group(1))) if c]
        if len(rows) >= 2:
            head = rows[0]
            # 제공량 칸이 어디인지 표의 머리글로 찾는다(음료=ml, 푸드=g)
            col = next((i for i, h in enumerate(head) if "제공량" in h.replace(" ", "")), None)
            if col is not None:
                unit = "ml" if "ml" in head[col] else ("g" if "(g)" in head[col] else "")
                # 앞쪽 라벨 칸(구분·사이즈)을 붙여 「Cold L 473ml」 처럼 원문 그대로 남긴다
                got, labels = [], None
                for r in rows[1:]:
                    if len(r) < len(head):          # rowspan 으로 앞 칸이 줄어든 줄
                        pad = len(head) - len(r)
                        r = (labels[:pad] if labels else [""] * pad) + r
                    else:
                        labels = r[:col]
                    if col < len(r) and blank(r[col]):
                        pre = " ".join(x for x in r[:col] if x)
                        got.append(("%s %s%s" % (pre, r[col], unit)).strip())
                weight = blank(" / ".join(got))

    ca = RX_CAUTION.search(html)
    allergy = None
    if ca:
        txt = strip(ca.group(1))
        m = re.search(r"알레르기[^:：]*[:：](.*)$", txt)
        allergy = blank(m.group(1) if m else txt)
    return compose, weight, allergy


# ─────────────────────────────── 본체 ───────────────────────────────
def main():
    home = get(ENTRY)
    tops, subs_drink = read_page_cats(home)
    if not tops or not subs_drink:
        print("🔴 카테고리 0개 — **화면 구조가 바뀌었다.** 파일을 쓰지 않는다")
        return
    print("  상위 탭 %d개: %s" % (len(tops), " · ".join(n for _, n in tops)))

    groups = [(tops[0][1], subs_drink)]
    for code, name in tops[1:]:
        time.sleep(GAP)
        _, subs = read_page_cats(get("%s/brand/menu/product?category=%s" % (ROOT, code)))
        groups.append((name, subs))
    for name, subs in groups:
        print("    › %-8s %s" % (name, " · ".join(n for _, n in subs)))

    cats, cat_paths = [], set()

    def add_cat(name, parent, ext):
        path = "%s/%s" % (parent, name) if parent else name
        if path not in cat_paths:
            cat_paths.add(path)
            cats.append({"name": name, "parent": parent, "ext_id": ext})
        return path

    for top, subs in groups:
        add_cat(top, None, None)
        for code, name in subs:
            add_cat(name, top, code)

    # 메뉴
    items, order, dropped = {}, [], []

    def take(path, rows):
        for i, (no, nm, url, img) in enumerate(rows):
            it = items.get(no)
            if it is None:
                it = {"name": nm, "price": None, "price_source": None,
                      "weight_raw": None, "origin_raw": None, "allergy_raw": None,
                      "compose_raw": None, "detail_url": url, "image_url": img,
                      "ext_id": no, "cats": []}
                items[no] = it
                order.append(no)
            it["cats"].append([path, i])

    for top, subs in groups:
        for code, name in subs:
            html = get("%s?category=%s" % (LIST_API, code))
            path = "%s/%s" % (top, name)
            blocks = parse_list(html)
            n_all = sum(len(r) for _, r in blocks)
            flat = [r for _, rows in blocks for r in rows]
            take(path, flat)                                   # 탭 안에서의 자리(전체 순서)
            for series, rows in blocks:
                if series:
                    take(add_cat(series, path, None), rows)    # 시리즈 안에서의 자리
            print("  %-24s %3d개%s" % (path, n_all,
                                       "  (시리즈 %d)" % sum(1 for s, _ in blocks if s)
                                       if any(s for s, _ in blocks) else ""), flush=True)
            time.sleep(GAP)

    if not order:
        print("🔴 메뉴 0건 — **화면 구조가 바뀌었다.** 조용히 빈 JSON 을 쓰지 않는다")
        return

    # 상세 — 설명·용량·알레르기
    print("\n  상세 %d건 읽는 중 (약 %d초)…" % (len(order), int(len(order) * GAP)))
    n_c = n_w = n_a = 0
    for k, no in enumerate(order):
        it = items[no]
        try:
            c, w, a = parse_detail(get(it["detail_url"]))
        except Exception as e:
            dropped.append((it["name"], "상세 실패 %r" % (e,)))
            time.sleep(GAP)
            continue
        it["compose_raw"], it["weight_raw"], it["allergy_raw"] = c, w, a
        n_c += bool(c)
        n_w += bool(w)
        n_a += bool(a)
        if (k + 1) % 25 == 0:
            print("    %d/%d" % (k + 1, len(order)), flush=True)
        time.sleep(GAP)

    # 저장 — 길이·형태 규칙에 걸린 이름은 **지우지 않고** 목록으로 출력한다
    cat_names = {c["name"] for c in cats}
    suspicious = []
    for no in order:
        nm = items[no]["name"]
        why = ("카테고리 이름과 같다" if nm in cat_names else
               "문장부호로 끝난다" if re.search(r"[.!?~]$", nm) else
               "18자 이상" if len(nm) >= 18 else None)
        if why:
            suspicious.append((nm, why))

    doc = {"brand": BRAND, "slug": SLUG, "source": SOURCE, "collected_at": COLLECTED_AT,
           "cats": cats, "menus": [items[no] for no in order]}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    chk = json.load(io.open(OUT, encoding="utf-8"))
    sub_n = sum(1 for c in chk["cats"] if c.get("parent"))
    n_price = sum(1 for m in chk["menus"] if m.get("price") is not None)
    links = sum(len(m["cats"]) for m in chk["menus"])
    print("\n■ %s — 카테고리 %d개(하위 %d) · 메뉴 %d개 · 가격 있는 것 %d개"
          % (BRAND, len(chk["cats"]), sub_n, len(chk["menus"]), n_price))
    print("  설명 %d · 용량 %d · 알레르기 %d · 원산지 0 (사이트에 표기가 없다)" % (n_c, n_w, n_a))
    print("  카테고리 배치 %d자리 · 중복 진열 %d건" % (links, links - len(chk["menus"])))
    print("  💰 가격 = 0개. 공차 홈페이지는 판매가를 **아예 공개하지 않는다**(목록·상세 모두 없음)")
    if suspicious:
        print("  ⚠️ 길이·형태 규칙에 걸린 이름 %d개 — **지우지 않고 남겼다.** 눈으로 볼 것:" % len(suspicious))
        for nm, why in suspicious:
            print("     · %-44s %s" % (nm[:44], why))
    if dropped:
        print("  ⛔ 버린 줄 %d개:" % len(dropped))
        for nm, why in dropped:
            print("     · %s — %s" % (nm, why))
    else:
        print("  ⛔ 버린 줄 없음")
    print("\n  → %s" % OUT)


if __name__ == "__main__":
    main()
